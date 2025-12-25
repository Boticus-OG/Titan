"""MoverPool - Dispatches available movers to requesting plates.

The MoverPool is a SERVICE, not a CONTROLLER. It:
- Assigns available movers to requesting plates
- Tracks which movers are assigned/available
- Does NOT control workflow progression
- Does NOT make decisions about where plates should go

Key principle (from Constitution):
"Resource pools dispatch available resources to requesting actors.
They do not track workflow state or command actors to perform actions."

See: docs/architecture/CONSTITUTION.md, Article III
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Callable, Any
from collections import deque

if TYPE_CHECKING:
    from ..actors.base import ActorRef
    from ..actors.mover_actor import MoverActor

logger = logging.getLogger(__name__)


@dataclass
class MoverRequest:
    """A pending request for a mover."""
    plate_id: str
    destination: str
    plate_ref: 'ActorRef'
    requested_at: datetime = field(default_factory=datetime.now)


class MoverPool:
    """Dispatches available movers to requesting plates.

    This is a taxi dispatcher, not a controller. It:
    - Maintains a pool of MoverActors
    - Assigns available movers to plate requests (FIFO)
    - Tracks assignments for release
    - Does NOT know about plate workflows
    """

    def __init__(self):
        self._movers: dict[str, 'MoverActor'] = {}  # mover_id -> MoverActor
        self._assignments: dict[str, str] = {}  # plate_id -> mover_id
        self._pending_requests: deque[MoverRequest] = deque()
        self._lock = asyncio.Lock()

    def register_mover(self, mover: 'MoverActor') -> None:
        """Register a mover with the pool."""
        mover_id = f"mover-{mover.mover_id}"
        self._movers[mover_id] = mover
        logger.info(f"MoverPool: Registered {mover_id}")

    def unregister_mover(self, mover_id: str) -> None:
        """Remove a mover from the pool."""
        if mover_id in self._movers:
            del self._movers[mover_id]
            logger.info(f"MoverPool: Unregistered {mover_id}")

    @property
    def available_count(self) -> int:
        """Count of available movers."""
        return sum(1 for m in self._movers.values() if m.is_available)

    @property
    def total_count(self) -> int:
        """Total number of movers in pool."""
        return len(self._movers)

    async def request_mover(
        self,
        plate_id: str,
        destination: str,
        plate_ref: 'ActorRef',
    ) -> Optional[str]:
        """Request a mover for a plate.

        This is called by PlateActor when it needs transport.
        If a mover is available, it's assigned immediately.
        If not, the request is queued.

        Args:
            plate_id: ID of the requesting plate
            destination: Where the plate needs to go
            plate_ref: Reference to the plate actor for callbacks

        Returns:
            mover_id if assigned immediately, None if queued
        """
        async with self._lock:
            # Check for already assigned
            if plate_id in self._assignments:
                logger.warning(f"MoverPool: Plate {plate_id} already has mover assigned")
                return self._assignments[plate_id]

            # Try to find available mover
            for mover_id, mover in self._movers.items():
                if mover.is_available:
                    # Assign immediately
                    success = await mover.assign_to_plate(plate_id, plate_ref, destination)
                    if success:
                        self._assignments[plate_id] = mover_id
                        logger.info(
                            f"MoverPool: Assigned {mover_id} to plate {plate_id} "
                            f"→ {destination}"
                        )

                        # Notify plate that mover is assigned
                        from ..actors.messages import MoverAssigned
                        await plate_ref.tell(MoverAssigned(mover_id=mover_id, plate_id=plate_id))

                        return mover_id

            # No mover available - queue the request
            request = MoverRequest(
                plate_id=plate_id,
                destination=destination,
                plate_ref=plate_ref,
            )
            self._pending_requests.append(request)
            logger.info(
                f"MoverPool: Queued request for plate {plate_id} "
                f"(queue length: {len(self._pending_requests)})"
            )
            return None

    async def release_mover(self, mover_id: str) -> None:
        """Release a mover back to the pool.

        Called when a plate no longer needs the mover (e.g., during device processing).

        Args:
            mover_id: ID of the mover to release
        """
        async with self._lock:
            # Find and release the mover
            mover = self._movers.get(mover_id)
            if not mover:
                logger.warning(f"MoverPool: Unknown mover {mover_id}")
                return

            plate_id = mover.assigned_plate_id
            mover.release()

            # Remove from assignments
            if plate_id and plate_id in self._assignments:
                del self._assignments[plate_id]

            logger.info(f"MoverPool: Released {mover_id} (was assigned to {plate_id})")

            # Process pending requests
            await self._process_pending_requests()

    async def _process_pending_requests(self) -> None:
        """Try to fulfill pending requests with available movers."""
        while self._pending_requests:
            # Find an available mover
            available_mover = None
            for mover in self._movers.values():
                if mover.is_available:
                    available_mover = mover
                    break

            if not available_mover:
                break  # No available movers

            # Get next request
            request = self._pending_requests.popleft()
            mover_id = f"mover-{available_mover.mover_id}"

            # Assign mover
            success = await available_mover.assign_to_plate(
                request.plate_id,
                request.plate_ref,
                request.destination,
            )

            if success:
                self._assignments[request.plate_id] = mover_id
                logger.info(
                    f"MoverPool: Fulfilled queued request - {mover_id} → "
                    f"plate {request.plate_id}"
                )

                # Notify plate
                from ..actors.messages import MoverAssigned
                await request.plate_ref.tell(
                    MoverAssigned(mover_id=mover_id, plate_id=request.plate_id)
                )
            else:
                # Put request back at front of queue
                self._pending_requests.appendleft(request)
                break

    def get_state(self) -> dict:
        """Get pool state for monitoring."""
        return {
            "total_movers": self.total_count,
            "available_movers": self.available_count,
            "pending_requests": len(self._pending_requests),
            "assignments": dict(self._assignments),
            "movers": {
                mover_id: {
                    "available": mover.is_available,
                    "assigned_plate": mover.assigned_plate_id,
                }
                for mover_id, mover in self._movers.items()
            },
        }
