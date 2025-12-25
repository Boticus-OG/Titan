"""EventBus - Publish-subscribe event propagation.

The EventBus provides a way for actors to emit events and for
observers (like the UI) to subscribe to those events.

Key principle (from Constitution):
"State changes are propagated via events on the EventBus.
Actors emit events; the UI and other interested parties subscribe."

See: docs/architecture/CONSTITUTION.md, Article IV, Section 4.3
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """An event emitted by an actor."""
    event_type: str
    actor_id: str
    data: dict
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: str(uuid4())[:8])

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "actor_id": self.actor_id,
            "timestamp": self.timestamp.isoformat(),
            **self.data,
        }


# Callback type for subscribers
EventCallback = Callable[[Event], Coroutine[Any, Any, None] | None]


@dataclass
class Subscription:
    """A subscription to events."""
    subscription_id: str
    pattern: str  # Event type pattern (e.g., "plate.*", "mover.transport_*")
    callback: EventCallback
    actor_filter: Optional[str] = None  # Optional actor_id filter


class EventBus:
    """Publish-subscribe event bus for actor events.

    Features:
    - Pattern-based subscriptions (e.g., "plate.*" matches all plate events)
    - Actor filtering (subscribe to events from specific actor)
    - Event history for new subscribers
    - Async-safe with proper locking
    """

    def __init__(self, history_size: int = 1000):
        """Initialize the event bus.

        Args:
            history_size: Number of recent events to keep for replay
        """
        self._subscriptions: dict[str, Subscription] = {}
        self._history: list[Event] = []
        self._history_size = history_size
        self._lock = asyncio.Lock()

    async def emit(self, event: Event | dict) -> None:
        """Emit an event to all matching subscribers.

        Args:
            event: Event object or dict with event data
        """
        # Convert dict to Event if needed
        if isinstance(event, dict):
            event = Event(
                event_type=event.get("event_type", event.get("type", "unknown")),
                actor_id=event.get("actor_id", "unknown"),
                data={k: v for k, v in event.items()
                      if k not in ("event_type", "type", "actor_id", "timestamp")},
            )

        async with self._lock:
            # Add to history
            self._history.append(event)
            if len(self._history) > self._history_size:
                self._history = self._history[-self._history_size:]

            # Find matching subscriptions
            matching = []
            for sub in self._subscriptions.values():
                if self._matches(event, sub):
                    matching.append(sub)

        # Notify subscribers (outside lock)
        for sub in matching:
            try:
                result = sub.callback(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Error in event subscriber {sub.subscription_id}: {e}")

    def _matches(self, event: Event, sub: Subscription) -> bool:
        """Check if an event matches a subscription pattern."""
        # Check actor filter
        if sub.actor_filter and event.actor_id != sub.actor_filter:
            return False

        # Check pattern
        pattern = sub.pattern

        # Exact match
        if pattern == event.event_type:
            return True

        # Wildcard matching
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return event.event_type.startswith(prefix)

        # Double wildcard (match any)
        if pattern == "**" or pattern == "*":
            return True

        return False

    def subscribe(
        self,
        pattern: str,
        callback: EventCallback,
        actor_id: Optional[str] = None,
    ) -> str:
        """Subscribe to events matching a pattern.

        Args:
            pattern: Event type pattern (e.g., "plate.*", "**" for all)
            callback: Async or sync function to call with event
            actor_id: Optional filter for specific actor

        Returns:
            subscription_id for later unsubscribe
        """
        sub_id = str(uuid4())[:8]
        self._subscriptions[sub_id] = Subscription(
            subscription_id=sub_id,
            pattern=pattern,
            callback=callback,
            actor_filter=actor_id,
        )
        logger.debug(f"EventBus: New subscription {sub_id} for pattern '{pattern}'")
        return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription.

        Args:
            subscription_id: ID returned from subscribe()

        Returns:
            True if subscription was found and removed
        """
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]
            logger.debug(f"EventBus: Removed subscription {subscription_id}")
            return True
        return False

    def get_history(
        self,
        pattern: Optional[str] = None,
        actor_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """Get recent events from history.

        Args:
            pattern: Optional event type filter
            actor_id: Optional actor filter
            limit: Maximum events to return

        Returns:
            List of event dictionaries
        """
        events = self._history[-limit:]

        # Apply filters
        if pattern:
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                events = [e for e in events if e.event_type.startswith(prefix)]
            elif pattern not in ("**", "*"):
                events = [e for e in events if e.event_type == pattern]

        if actor_id:
            events = [e for e in events if e.actor_id == actor_id]

        return [e.to_dict() for e in events]

    @property
    def subscription_count(self) -> int:
        """Number of active subscriptions."""
        return len(self._subscriptions)


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
