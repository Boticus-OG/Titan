"""Message types for actor communication.

All messages are immutable dataclasses. This ensures thread-safety
and makes the system easier to reason about.

See: docs/architecture/actor-model.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# ============================================================================
# Plate Actor Messages
# ============================================================================

@dataclass(frozen=True)
class AssignWorkflow:
    """Assign a workflow and samples to a plate."""
    workflow_id: str
    workflow_steps: tuple  # Tuple of WorkflowStep
    sample_ids: tuple[str, ...]
    barcode: Optional[str] = None


@dataclass(frozen=True)
class WorkflowStep:
    """A single step in a workflow."""
    step_id: str
    name: str
    station_id: str
    device_id: str
    device_type: str
    duration: float = 0.0  # seconds, 0 = instant
    parameters: tuple = ()  # Tuple of (key, value) pairs


@dataclass(frozen=True)
class Pause:
    """Pause workflow execution at next safe point."""
    reason: str = ""


@dataclass(frozen=True)
class Resume:
    """Resume paused workflow execution."""
    pass


@dataclass(frozen=True)
class Abort:
    """Abort workflow execution."""
    reason: str = ""


@dataclass(frozen=True)
class SkipStep:
    """Skip current step and proceed to next."""
    reason: str = ""


@dataclass(frozen=True)
class RetryStep:
    """Retry the current/failed step."""
    pass


# ============================================================================
# Mover Actor Messages
# ============================================================================

@dataclass(frozen=True)
class TransportTo:
    """Transport plate to a destination."""
    station_id: str
    plate_id: str


@dataclass(frozen=True)
class TransportComplete:
    """Notification that transport is complete."""
    station_id: str
    success: bool = True
    error: Optional[str] = None


@dataclass(frozen=True)
class ReleaseMover:
    """Release mover from plate assignment."""
    plate_id: str


# ============================================================================
# Resource Pool Messages
# ============================================================================

@dataclass(frozen=True)
class RequestMover:
    """Request a mover for transport."""
    plate_id: str
    destination: str
    pickup_from: Optional[str] = None


@dataclass(frozen=True)
class MoverAssigned:
    """Notification that a mover has been assigned."""
    mover_id: str
    plate_id: str


@dataclass(frozen=True)
class MoverReleased:
    """Notification that a mover has been released."""
    mover_id: str
    plate_id: str


# ============================================================================
# Device Messages (for future DeviceActor)
# ============================================================================

@dataclass(frozen=True)
class ProcessAtDevice:
    """Request processing at a device."""
    plate_id: str
    device_id: str
    parameters: tuple = ()


@dataclass(frozen=True)
class ProcessingComplete:
    """Notification that device processing is complete."""
    device_id: str
    plate_id: str
    success: bool = True
    result: tuple = ()  # Tuple of (key, value) pairs
    error: Optional[str] = None
