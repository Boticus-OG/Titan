"""MoverActor - Transport resource (the taxi).

The MoverActor represents a physical mover on the XPlanar system.
It is a TRANSPORT RESOURCE, not an autonomous agent with a workflow.

Key principles (from Constitution):
- Mover is a taxi - it doesn't know the passenger's itinerary
- Mover executes transport commands
- Mover tracks physical state (position, track, velocity)
- Mover is assigned by MoverPool, released when transport complete
- Any mover can serve any plate (within physical constraints)

See: docs/architecture/CONSTITUTION.md, Article II, Section 2.2
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Optional

from .base import BaseActor, ActorRef, ActorEvent
from .messages import TransportTo, ReleaseMover, TransportComplete

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Physical position in XPlanar coordinates."""
    x: float
    y: float
    c: float = 0.0  # Rotation

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "c": self.c}


@dataclass
class MoverPhysicalState:
    """Physical state from hardware (PLC)."""
    position: Position
    track_id: Optional[int] = None
    track_position: float = 0.0
    velocity: float = 0.0
    state: str = "idle"  # idle, moving, error

    def to_dict(self) -> dict:
        return {
            "position": self.position.to_dict(),
            "track_id": self.track_id,
            "track_position": self.track_position,
            "velocity": self.velocity,
            "state": self.state,
        }


class MoverActor(BaseActor):
    """Transport resource - a taxi, not an agent with a workflow.

    The MoverActor:
    - Executes transport commands (TransportTo)
    - Tracks physical state (position, track)
    - Has NO workflow knowledge
    - Is assigned by MoverPool, released when transport complete
    """

    # Simulated station positions for mock transport
    STATION_POSITIONS = {
        "STATION_1": Position(100, 100),
        "STATION_2": Position(300, 100),
        "STATION_3": Position(200, 300),
        "HOME": Position(0, 0),
    }

    def __init__(
        self,
        mover_id: int,
        event_callback: Optional[Callable[[ActorEvent], Any]] = None,
        transport_speed: float = 100.0,  # mm/s for simulation
    ):
        """Initialize the MoverActor.

        Args:
            mover_id: Numeric identifier (1, 2, 3, etc.)
            event_callback: Optional callback for emitted events
            transport_speed: Simulated transport speed in mm/s
        """
        super().__init__(f"mover-{mover_id}", event_callback)

        self.mover_id = mover_id
        self._transport_speed = transport_speed

        # Physical state
        self._physical = MoverPhysicalState(
            position=Position(0, 0),
            state="idle",
        )

        # Assignment state
        self._assigned_plate_id: Optional[str] = None
        self._plate_actor_ref: Optional[ActorRef] = None

        # Transport state
        self._current_transport: Optional[str] = None  # destination station_id
        self._transport_task: Optional[asyncio.Task] = None

    @property
    def is_available(self) -> bool:
        """Check if mover is available for assignment."""
        return (
            self._assigned_plate_id is None
            and self._physical.state == "idle"
        )

    @property
    def assigned_plate_id(self) -> Optional[str]:
        return self._assigned_plate_id

    async def assign_to_plate(
        self,
        plate_id: str,
        plate_ref: ActorRef,
        destination: str,
    ) -> bool:
        """Assign this mover to a plate for transport.

        Called by MoverPool when assigning a mover.
        """
        if not self.is_available:
            logger.warning(f"Mover {self.mover_id}: Cannot assign, not available")
            return False

        self._assigned_plate_id = plate_id
        self._plate_actor_ref = plate_ref
        self._current_transport = destination
        self._physical.state = "assigned"

        await self._emit_event("mover.assigned", {
            "mover_id": self.mover_id,
            "plate_id": plate_id,
            "destination": destination,
        })

        logger.info(f"Mover {self.mover_id}: Assigned to plate {plate_id} → {destination}")

        # Start transport
        self._transport_task = asyncio.create_task(
            self._execute_transport(destination)
        )

        return True

    def release(self) -> None:
        """Release this mover from plate assignment.

        Called by MoverPool when releasing a mover.
        """
        plate_id = self._assigned_plate_id
        self._assigned_plate_id = None
        self._plate_actor_ref = None
        self._current_transport = None
        self._physical.state = "idle"

        logger.info(f"Mover {self.mover_id}: Released from plate {plate_id}")

    async def _handle_custom_message(self, message: Any) -> Any:
        """Handle mover-specific messages."""
        match message:
            case TransportTo(station_id, plate_id):
                # Direct transport command (alternative to assign_to_plate)
                return await self._on_transport_to(station_id, plate_id)
            case ReleaseMover(plate_id):
                if self._assigned_plate_id == plate_id:
                    self.release()
                    return {"status": "released"}
                return {"error": "Not assigned to this plate"}
            case _:
                logger.warning(f"Mover {self.mover_id}: Unknown message {type(message)}")
                return {"error": f"Unknown message: {type(message)}"}

    async def _on_transport_to(self, station_id: str, plate_id: str) -> dict:
        """Handle direct transport command."""
        if self._physical.state != "idle":
            return {"error": f"Mover busy: {self._physical.state}"}

        self._current_transport = station_id
        self._assigned_plate_id = plate_id
        await self._execute_transport(station_id)
        return {"status": "transport_complete", "station_id": station_id}

    async def _tick(self) -> None:
        """Periodic state update (would refresh from PLC in real system)."""
        # In real system: await self._refresh_from_plc()
        pass

    async def _execute_transport(self, destination: str) -> None:
        """Execute transport to destination (simulated).

        In real system, this would:
        1. Call PathPlanner for route
        2. Execute movement commands via XPlanar controller
        3. Update position from PLC
        """
        self._physical.state = "moving"

        # Get destination position
        dest_pos = self.STATION_POSITIONS.get(destination)
        if not dest_pos:
            # Unknown station - simulate position
            dest_pos = Position(
                x=random.uniform(0, 400),
                y=random.uniform(0, 400),
            )

        start_pos = self._physical.position

        # Calculate travel time
        distance = (
            (dest_pos.x - start_pos.x) ** 2 +
            (dest_pos.y - start_pos.y) ** 2
        ) ** 0.5
        travel_time = distance / self._transport_speed

        await self._emit_event("mover.transport_started", {
            "mover_id": self.mover_id,
            "plate_id": self._assigned_plate_id,
            "from": start_pos.to_dict(),
            "to": dest_pos.to_dict(),
            "destination": destination,
            "estimated_time": travel_time,
        })

        logger.info(
            f"Mover {self.mover_id}: Transport started to {destination} "
            f"(distance={distance:.0f}mm, time={travel_time:.1f}s)"
        )

        # Simulate travel (in real system: poll PLC for completion)
        await asyncio.sleep(travel_time)

        # Update position
        self._physical.position = dest_pos
        self._physical.state = "idle"

        await self._emit_event("mover.transport_complete", {
            "mover_id": self.mover_id,
            "plate_id": self._assigned_plate_id,
            "destination": destination,
            "position": dest_pos.to_dict(),
        })

        logger.info(f"Mover {self.mover_id}: Arrived at {destination}")

        # Notify plate of arrival
        if self._plate_actor_ref:
            await self._plate_actor_ref.tell(
                TransportComplete(station_id=destination, success=True)
            )

    def get_state(self) -> dict:
        """Get mover state for UI inspection."""
        base_state = super().get_state()
        return {
            **base_state,
            "mover_id": self.mover_id,
            "available": self.is_available,
            "assigned_plate_id": self._assigned_plate_id,
            "current_transport": self._current_transport,
            "physical": self._physical.to_dict(),
        }
