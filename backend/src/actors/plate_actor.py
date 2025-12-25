"""PlateActor - The autonomous agent managing a plate's workflow journey.

The PlateActor is the heart of Titan. It represents a physical plate
(microplate, assay plate) along with its assigned samples and workflow.

Key principles (from Constitution):
- The plate owns the workflow, not the mover
- The plate requests resources (movers, devices) when needed
- The plate releases resources when done
- Movers are taxis - released during device processing

See: docs/architecture/plate-actor.md
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Optional

from .base import BaseActor, ActorRef, ActorEvent
from .messages import (
    AssignWorkflow,
    WorkflowStep,
    Pause,
    Resume,
    Abort,
    SkipStep,
    RetryStep,
    MoverAssigned,
    TransportComplete,
    ProcessingComplete,
)

if TYPE_CHECKING:
    from ..services.mover_pool import MoverPool

logger = logging.getLogger(__name__)


class PlatePhase(str, Enum):
    """Phases of the plate lifecycle."""

    CREATED = "created"
    READY = "ready"
    REQUESTING_MOVER = "requesting_mover"
    AWAITING_MOVER = "awaiting_mover"
    IN_TRANSIT = "in_transit"
    AT_STATION = "at_station"
    PROCESSING = "processing"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"
    ABORTED = "aborted"


@dataclass
class PlateLocation:
    """Physical location of the plate."""

    location_type: str  # "unassigned", "on_mover", "in_device", "at_station"
    mover_id: Optional[str] = None
    device_id: Optional[str] = None
    station_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "type": self.location_type,
            "mover_id": self.mover_id,
            "device_id": self.device_id,
            "station_id": self.station_id,
        }


@dataclass
class WorkflowState:
    """State of workflow execution."""

    workflow_id: Optional[str] = None
    steps: list[WorkflowStep] = field(default_factory=list)
    current_step: int = 0
    started_at: Optional[datetime] = None
    step_started_at: Optional[datetime] = None

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def current_step_info(self) -> Optional[WorkflowStep]:
        if 0 <= self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None

    @property
    def progress_percent(self) -> float:
        if not self.steps:
            return 0.0
        return (self.current_step / len(self.steps)) * 100


class PlateActor(BaseActor):
    """Autonomous agent managing a plate's workflow journey.

    The PlateActor embodies the "taxi passenger" metaphor from the Constitution:
    - It has an itinerary (workflow steps)
    - It hails transport (requests movers)
    - It decides where to go next
    - Taxis (movers) don't know the itinerary
    """

    def __init__(
        self,
        plate_id: str,
        mover_pool: MoverPool,
        event_callback: Optional[Callable[[ActorEvent], Any]] = None,
    ):
        """Initialize the PlateActor.

        Args:
            plate_id: Unique identifier for this plate
            mover_pool: Pool for requesting movers
            event_callback: Optional callback for emitted events
        """
        super().__init__(f"plate-{plate_id}", event_callback)

        self.plate_id = plate_id
        self.sample_ids: list[str] = []
        self.barcode: Optional[str] = None

        # Services (not controllers - they answer questions, don't command)
        self._mover_pool = mover_pool

        # State
        self._phase = PlatePhase.CREATED
        self._location = PlateLocation(location_type="unassigned")
        self._workflow = WorkflowState()

        # Current resources
        self._assigned_mover: Optional[ActorRef] = None
        self._assigned_mover_id: Optional[str] = None

        # Error state
        self._last_error: Optional[str] = None
        self._error_step: Optional[int] = None

        # Pause state
        self._paused_from: Optional[PlatePhase] = None

        # History (for UI drill-down)
        self._history: list[dict] = []
        self._max_history = 100

    @property
    def phase(self) -> PlatePhase:
        return self._phase

    @property
    def location(self) -> PlateLocation:
        return self._location

    async def _handle_custom_message(self, message: Any) -> Any:
        """Handle plate-specific messages."""
        match message:
            case AssignWorkflow(workflow_id, workflow_steps, sample_ids, barcode):
                return await self._on_assign_workflow(
                    workflow_id, list(workflow_steps), list(sample_ids), barcode
                )
            case Pause(reason):
                return await self._on_pause(reason)
            case Resume():
                return await self._on_resume()
            case Abort(reason):
                return await self._on_abort(reason)
            case SkipStep(reason):
                return await self._on_skip_step(reason)
            case RetryStep():
                return await self._on_retry_step()
            case MoverAssigned(mover_id, plate_id):
                return await self._on_mover_assigned(mover_id)
            case TransportComplete(station_id, success, error):
                return await self._on_transport_complete(station_id, success, error)
            case ProcessingComplete(device_id, plate_id, success, result, error):
                return await self._on_processing_complete(device_id, success, error)
            case _:
                logger.warning(f"Unknown message type: {type(message)}")
                return {"error": f"Unknown message type: {type(message)}"}

    async def _tick(self) -> None:
        """Autonomous behavior - execute workflow when ready."""
        if self._phase == PlatePhase.READY:
            if self._workflow.current_step < self._workflow.total_steps:
                await self._execute_next_step()
            else:
                await self._complete_workflow()

    # ========================================================================
    # Message Handlers
    # ========================================================================

    async def _on_assign_workflow(
        self,
        workflow_id: str,
        steps: list[WorkflowStep],
        sample_ids: list[str],
        barcode: Optional[str],
    ) -> dict:
        """Handle workflow assignment."""
        if self._phase != PlatePhase.CREATED:
            return {"error": f"Cannot assign workflow in phase {self._phase}"}

        self.sample_ids = sample_ids
        self.barcode = barcode

        self._workflow = WorkflowState(
            workflow_id=workflow_id,
            steps=steps,
            current_step=0,
            started_at=datetime.now(),
        )

        self._phase = PlatePhase.READY
        self._add_history("workflow_assigned", {
            "workflow_id": workflow_id,
            "total_steps": len(steps),
            "sample_count": len(sample_ids),
        })

        await self._emit_event("plate.workflow_assigned", {
            "plate_id": self.plate_id,
            "workflow_id": workflow_id,
            "total_steps": len(steps),
            "sample_count": len(sample_ids),
        })

        logger.info(f"Plate {self.plate_id}: Workflow '{workflow_id}' assigned with {len(steps)} steps")
        return {"status": "assigned", "workflow_id": workflow_id}

    async def _on_pause(self, reason: str) -> dict:
        """Handle pause request."""
        if self._phase in (PlatePhase.COMPLETED, PlatePhase.ABORTED):
            return {"error": f"Cannot pause in phase {self._phase}"}

        self._paused_from = self._phase
        self._phase = PlatePhase.PAUSED

        self._add_history("paused", {"reason": reason, "from_phase": self._paused_from.value})
        await self._emit_event("plate.paused", {
            "plate_id": self.plate_id,
            "reason": reason,
            "from_phase": self._paused_from.value,
        })

        logger.info(f"Plate {self.plate_id}: Paused from {self._paused_from.value}")
        return {"status": "paused", "from_phase": self._paused_from.value}

    async def _on_resume(self) -> dict:
        """Handle resume request."""
        if self._phase != PlatePhase.PAUSED:
            return {"error": f"Cannot resume from phase {self._phase}"}

        previous = self._paused_from or PlatePhase.READY
        self._phase = previous
        self._paused_from = None

        self._add_history("resumed", {"to_phase": previous.value})
        await self._emit_event("plate.resumed", {
            "plate_id": self.plate_id,
            "to_phase": previous.value,
        })

        logger.info(f"Plate {self.plate_id}: Resumed to {previous.value}")
        return {"status": "resumed", "to_phase": previous.value}

    async def _on_abort(self, reason: str) -> dict:
        """Handle abort request."""
        previous = self._phase
        self._phase = PlatePhase.ABORTED

        # Release any held resources
        if self._assigned_mover:
            await self._release_mover()

        self._add_history("aborted", {"reason": reason, "from_phase": previous.value})
        await self._emit_event("plate.aborted", {
            "plate_id": self.plate_id,
            "reason": reason,
            "step": self._workflow.current_step,
        })

        logger.info(f"Plate {self.plate_id}: Aborted - {reason}")
        return {"status": "aborted", "reason": reason}

    async def _on_skip_step(self, reason: str) -> dict:
        """Handle skip step request."""
        if self._phase not in (PlatePhase.ERROR, PlatePhase.PAUSED):
            return {"error": f"Cannot skip step in phase {self._phase}"}

        skipped_step = self._workflow.current_step
        self._workflow.current_step += 1
        self._phase = PlatePhase.READY
        self._last_error = None

        self._add_history("step_skipped", {"step": skipped_step, "reason": reason})
        await self._emit_event("plate.step_skipped", {
            "plate_id": self.plate_id,
            "step": skipped_step,
            "reason": reason,
        })

        logger.info(f"Plate {self.plate_id}: Skipped step {skipped_step}")
        return {"status": "skipped", "step": skipped_step}

    async def _on_retry_step(self) -> dict:
        """Handle retry step request."""
        if self._phase != PlatePhase.ERROR:
            return {"error": f"Cannot retry in phase {self._phase}"}

        step = self._workflow.current_step
        self._phase = PlatePhase.READY
        self._last_error = None

        self._add_history("step_retry", {"step": step})
        await self._emit_event("plate.step_retry", {
            "plate_id": self.plate_id,
            "step": step,
        })

        logger.info(f"Plate {self.plate_id}: Retrying step {step}")
        return {"status": "retrying", "step": step}

    async def _on_mover_assigned(self, mover_id: str) -> dict:
        """Handle mover assignment from pool."""
        if self._phase != PlatePhase.AWAITING_MOVER:
            logger.warning(f"Plate {self.plate_id}: Mover assigned in unexpected phase {self._phase}")

        self._assigned_mover_id = mover_id
        self._location = PlateLocation(
            location_type="on_mover",
            mover_id=mover_id,
        )
        self._phase = PlatePhase.IN_TRANSIT

        self._add_history("mover_assigned", {"mover_id": mover_id})
        await self._emit_event("plate.mover_assigned", {
            "plate_id": self.plate_id,
            "mover_id": mover_id,
        })

        logger.info(f"Plate {self.plate_id}: Mover {mover_id} assigned")
        return {"status": "mover_assigned"}

    async def _on_transport_complete(
        self, station_id: str, success: bool, error: Optional[str]
    ) -> dict:
        """Handle transport completion."""
        if not success:
            self._phase = PlatePhase.ERROR
            self._last_error = error or "Transport failed"
            self._error_step = self._workflow.current_step

            await self._emit_event("plate.transport_failed", {
                "plate_id": self.plate_id,
                "station_id": station_id,
                "error": self._last_error,
            })
            return {"status": "error", "error": self._last_error}

        self._location = PlateLocation(
            location_type="at_station",
            station_id=station_id,
            mover_id=self._assigned_mover_id,
        )
        self._phase = PlatePhase.AT_STATION

        self._add_history("arrived", {"station_id": station_id})
        await self._emit_event("plate.arrived", {
            "plate_id": self.plate_id,
            "station_id": station_id,
        })

        logger.info(f"Plate {self.plate_id}: Arrived at {station_id}")

        # Continue to processing
        await self._process_at_current_station()
        return {"status": "arrived"}

    async def _on_processing_complete(
        self, device_id: str, success: bool, error: Optional[str]
    ) -> dict:
        """Handle device processing completion."""
        if not success:
            self._phase = PlatePhase.ERROR
            self._last_error = error or "Processing failed"
            self._error_step = self._workflow.current_step

            await self._emit_event("plate.processing_failed", {
                "plate_id": self.plate_id,
                "device_id": device_id,
                "error": self._last_error,
            })
            return {"status": "error", "error": self._last_error}

        self._add_history("processing_complete", {"device_id": device_id})
        await self._emit_event("plate.processing_complete", {
            "plate_id": self.plate_id,
            "device_id": device_id,
            "step": self._workflow.current_step,
        })

        # Advance to next step
        self._workflow.current_step += 1
        self._phase = PlatePhase.READY

        await self._emit_event("plate.step_completed", {
            "plate_id": self.plate_id,
            "step": self._workflow.current_step - 1,
            "total_steps": self._workflow.total_steps,
        })

        logger.info(f"Plate {self.plate_id}: Step {self._workflow.current_step - 1} completed")
        return {"status": "step_completed"}

    # ========================================================================
    # Workflow Execution
    # ========================================================================

    async def _execute_next_step(self) -> None:
        """Execute the next workflow step - THE CORE AUTONOMY."""
        step = self._workflow.current_step_info
        if not step:
            await self._complete_workflow()
            return

        self._workflow.step_started_at = datetime.now()

        self._add_history("step_started", {
            "step": self._workflow.current_step,
            "name": step.name,
            "station_id": step.station_id,
        })

        await self._emit_event("plate.step_started", {
            "plate_id": self.plate_id,
            "step": self._workflow.current_step,
            "step_name": step.name,
            "station_id": step.station_id,
            "device_id": step.device_id,
        })

        logger.info(f"Plate {self.plate_id}: Starting step {self._workflow.current_step} - {step.name}")

        # Do I need transport?
        if self._needs_transport(step):
            await self._request_mover(step.station_id)
        else:
            # Already at station, go straight to processing
            self._phase = PlatePhase.AT_STATION
            await self._process_at_current_station()

    def _needs_transport(self, step: WorkflowStep) -> bool:
        """Check if we need transport to reach the step's station."""
        # Need transport if not at the station
        if self._location.location_type == "unassigned":
            return True
        if self._location.station_id != step.station_id:
            return True
        return False

    async def _request_mover(self, destination: str) -> None:
        """Request a mover from the pool."""
        self._phase = PlatePhase.REQUESTING_MOVER

        self._add_history("mover_requested", {"destination": destination})
        await self._emit_event("plate.mover_requested", {
            "plate_id": self.plate_id,
            "destination": destination,
        })

        logger.info(f"Plate {self.plate_id}: Requesting mover to {destination}")

        # Request from pool (async - we'll get MoverAssigned message)
        self._phase = PlatePhase.AWAITING_MOVER
        await self._mover_pool.request_mover(self.plate_id, destination, self.ref)

    async def _process_at_current_station(self) -> None:
        """Process at the current station's device."""
        step = self._workflow.current_step_info
        if not step:
            return

        self._phase = PlatePhase.PROCESSING

        # Release mover during processing (Constitution Section 3.3)
        if self._assigned_mover_id:
            await self._release_mover()

        self._location = PlateLocation(
            location_type="in_device",
            device_id=step.device_id,
            station_id=step.station_id,
        )

        self._add_history("processing_started", {
            "device_id": step.device_id,
            "duration": step.duration,
        })

        await self._emit_event("plate.processing_started", {
            "plate_id": self.plate_id,
            "device_id": step.device_id,
            "duration": step.duration,
        })

        logger.info(f"Plate {self.plate_id}: Processing at {step.device_id} for {step.duration}s")

        # Simulate processing (in real system, device would notify completion)
        if step.duration > 0:
            await asyncio.sleep(step.duration)

        # Auto-complete processing (mock device)
        await self._on_processing_complete(step.device_id, True, None)

    async def _release_mover(self) -> None:
        """Release the assigned mover back to the pool."""
        if self._assigned_mover_id:
            mover_id = self._assigned_mover_id
            await self._mover_pool.release_mover(mover_id)

            self._add_history("mover_released", {"mover_id": mover_id})
            await self._emit_event("plate.mover_released", {
                "plate_id": self.plate_id,
                "mover_id": mover_id,
            })

            logger.info(f"Plate {self.plate_id}: Released mover {mover_id}")

            self._assigned_mover_id = None
            self._assigned_mover = None

    async def _complete_workflow(self) -> None:
        """Mark workflow as complete."""
        if self._assigned_mover_id:
            await self._release_mover()

        self._phase = PlatePhase.COMPLETED

        duration = None
        if self._workflow.started_at:
            duration = (datetime.now() - self._workflow.started_at).total_seconds()

        self._add_history("workflow_completed", {
            "total_steps": self._workflow.total_steps,
            "duration": duration,
        })

        await self._emit_event("plate.workflow_completed", {
            "plate_id": self.plate_id,
            "workflow_id": self._workflow.workflow_id,
            "total_steps": self._workflow.total_steps,
            "duration": duration,
        })

        logger.info(f"Plate {self.plate_id}: Workflow completed in {duration:.1f}s")

    # ========================================================================
    # State & History
    # ========================================================================

    def _add_history(self, event_type: str, data: dict) -> None:
        """Add entry to history."""
        entry = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            **data,
        }
        self._history.append(entry)

        # Keep history bounded
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def get_state(self) -> dict:
        """Get complete plate state for UI inspection."""
        base_state = super().get_state()

        step_info = None
        if self._workflow.current_step_info:
            s = self._workflow.current_step_info
            step_info = {
                "step_id": s.step_id,
                "name": s.name,
                "station_id": s.station_id,
                "device_id": s.device_id,
                "device_type": s.device_type,
                "duration": s.duration,
            }

        return {
            **base_state,
            "plate_id": self.plate_id,
            "sample_ids": self.sample_ids,
            "barcode": self.barcode,
            "phase": self._phase.value,
            "location": self._location.to_dict(),
            "workflow": {
                "workflow_id": self._workflow.workflow_id,
                "current_step": self._workflow.current_step,
                "total_steps": self._workflow.total_steps,
                "progress_percent": self._workflow.progress_percent,
                "started_at": self._workflow.started_at.isoformat() if self._workflow.started_at else None,
                "current_step_info": step_info,
            },
            "assigned_mover_id": self._assigned_mover_id,
            "error": {
                "message": self._last_error,
                "step": self._error_step,
            } if self._last_error else None,
            "history": self._history[-20:],  # Last 20 events for UI
        }
