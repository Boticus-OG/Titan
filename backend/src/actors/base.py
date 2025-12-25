"""Base Actor implementation using asyncio primitives.

This module provides the foundational actor infrastructure for Titan.
Actors are autonomous agents that communicate via message passing.

See: docs/architecture/actor-model.md
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class ActorRef:
    """Reference to an actor for message passing.

    ActorRef provides a way to send messages to an actor without
    direct access to the actor instance. This enables loose coupling
    and location transparency.
    """

    actor_id: str
    _mailbox: asyncio.Queue = field(repr=False)

    async def tell(self, message: Any) -> None:
        """Fire-and-forget message send.

        The message is queued for processing. This method returns
        immediately without waiting for the message to be processed.
        """
        await self._mailbox.put(message)

    async def ask(self, message: Any, timeout: float = 30.0) -> Any:
        """Request-response pattern with timeout.

        Sends a message and waits for a response. The actor must
        recognize this as a request and send a response.

        Args:
            message: The message to send
            timeout: Maximum time to wait for response (seconds)

        Returns:
            The response from the actor

        Raises:
            asyncio.TimeoutError: If no response within timeout
            Exception: If the actor returns an error
        """
        response_queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        await self._mailbox.put((message, response_queue))
        result = await asyncio.wait_for(response_queue.get(), timeout)
        if isinstance(result, Exception):
            raise result
        return result


@dataclass
class ActorEvent:
    """Base class for events emitted by actors."""

    event_type: str
    actor_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert event to dictionary for serialization."""
        return {
            "event_type": self.event_type,
            "actor_id": self.actor_id,
            "timestamp": self.timestamp.isoformat(),
            **self.data,
        }


# Message types
@dataclass
class GetState:
    """Request the actor's current state."""
    pass


@dataclass
class Shutdown:
    """Request the actor to shut down gracefully."""
    pass


class BaseActor(ABC):
    """Base class for all actors in Titan.

    Actors are autonomous agents that:
    - Process messages from their mailbox
    - Maintain internal state
    - Emit events for observers
    - Run independently in their own asyncio task

    Subclasses must implement:
    - _process_message(): Handle incoming messages
    - _tick(): Autonomous behavior each iteration
    """

    def __init__(
        self,
        actor_id: str,
        event_callback: Optional[Callable[[ActorEvent], Any]] = None,
    ):
        """Initialize the actor.

        Args:
            actor_id: Unique identifier for this actor
            event_callback: Optional callback for emitted events
        """
        self.actor_id = actor_id
        self._mailbox: asyncio.Queue = asyncio.Queue()
        self._ref = ActorRef(actor_id, self._mailbox)
        self._event_callback = event_callback

        # Lifecycle state
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._started_at: Optional[datetime] = None

        # Metrics
        self._messages_processed = 0
        self._errors_count = 0

    @property
    def ref(self) -> ActorRef:
        """Get a reference to this actor for message passing."""
        return self._ref

    @property
    def is_running(self) -> bool:
        """Check if the actor is currently running."""
        return self._running

    async def start(self) -> None:
        """Start the actor's message processing loop.

        This spawns an asyncio task that runs until stop() is called.
        """
        if self._running:
            logger.warning(f"Actor {self.actor_id} already running")
            return

        self._running = True
        self._started_at = datetime.now()
        self._task = asyncio.create_task(self._run(), name=f"actor-{self.actor_id}")
        logger.info(f"Actor {self.actor_id} started")

    async def stop(self) -> None:
        """Gracefully stop the actor.

        Signals the actor to stop and waits for the task to complete.
        """
        if not self._running:
            return

        self._running = False

        if self._task:
            # Give the actor a chance to finish current work
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning(f"Actor {self.actor_id} did not stop gracefully, cancelling")
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass

        logger.info(f"Actor {self.actor_id} stopped")

    async def _run(self) -> None:
        """Main actor loop - processes messages and executes autonomous behavior."""
        logger.debug(f"Actor {self.actor_id} entering main loop")

        while self._running:
            try:
                # Process all pending messages
                await self._process_mailbox()

                # Execute autonomous behavior
                await self._tick()

                # Yield to other tasks
                await asyncio.sleep(0.05)

            except asyncio.CancelledError:
                logger.debug(f"Actor {self.actor_id} cancelled")
                break
            except Exception as e:
                self._errors_count += 1
                await self._handle_error(e)

    async def _process_mailbox(self) -> None:
        """Process all pending messages in the mailbox."""
        while True:
            try:
                message = self._mailbox.get_nowait()
                await self._handle_message(message)
                self._messages_processed += 1
            except asyncio.QueueEmpty:
                break

    async def _handle_message(self, message: Any) -> None:
        """Route messages to appropriate handlers."""
        # Check for request-response pattern (tuple with response queue)
        if isinstance(message, tuple) and len(message) == 2:
            msg, response_queue = message
            if isinstance(response_queue, asyncio.Queue):
                try:
                    result = await self._process_message(msg)
                    await response_queue.put(result)
                except Exception as e:
                    await response_queue.put(e)
                return

        # Fire-and-forget message
        await self._process_message(message)

    async def _process_message(self, message: Any) -> Any:
        """Process a single message.

        Override in subclasses to handle specific message types.
        Default implementation handles GetState and Shutdown.
        """
        match message:
            case GetState():
                return self.get_state()
            case Shutdown():
                await self.stop()
                return {"status": "shutdown"}
            case _:
                return await self._handle_custom_message(message)

    @abstractmethod
    async def _handle_custom_message(self, message: Any) -> Any:
        """Handle application-specific messages. Override in subclasses."""
        pass

    @abstractmethod
    async def _tick(self) -> None:
        """Autonomous behavior executed each iteration.

        Override in subclasses to implement autonomous behavior.
        This is called repeatedly while the actor is running.
        """
        pass

    async def _handle_error(self, error: Exception) -> None:
        """Handle errors during message processing or tick.

        Override in subclasses for custom error handling.
        Default logs the error and continues.
        """
        logger.exception(f"Actor {self.actor_id} error: {error}")
        await self._emit_event("actor.error", {"error": str(error)})

    async def _emit_event(self, event_type: str, data: Optional[dict] = None) -> None:
        """Emit an event to observers.

        Args:
            event_type: Type of event (e.g., "plate.step_completed")
            data: Additional event data
        """
        event = ActorEvent(
            event_type=event_type,
            actor_id=self.actor_id,
            data=data or {},
        )

        if self._event_callback:
            try:
                result = self._event_callback(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Error in event callback: {e}")

    def get_state(self) -> dict:
        """Get the actor's current state.

        Override in subclasses to include application-specific state.
        """
        return {
            "actor_id": self.actor_id,
            "running": self._running,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "messages_processed": self._messages_processed,
            "errors_count": self._errors_count,
        }
