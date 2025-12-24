# PlateActor Specification

**Version:** 1.0.0
**Last Updated:** 2024-12-24

---

## Overview

The PlateActor is the autonomous agent at the heart of HoverLabs. It represents a physical plate (microplate, assay plate, etc.) along with its assigned samples and workflow. The PlateActor manages its own journey through the laboratory automation system.

## The Taxi Passenger Metaphor

Think of the PlateActor as a passenger with a full day of appointments:

| Real World | HoverLabs |
|------------|-----------|
| Passenger with itinerary | PlateActor with workflow |
| Hails a taxi | Requests mover from MoverPool |
| Rides to destination | In transit on mover |
| Exits taxi at building | Loads into device |
| Receives service | Processing at device |
| Taxi leaves (fare complete) | Mover released to pool |
| Hails new taxi for next stop | Requests new mover |

The passenger (plate) is always in charge. Taxis (movers) are interchangeable transport.

---

## State Machine

```
                              [Created]
                                  │
                                  │ AssignWorkflow
                                  ▼
    ┌────────────────────────▶[Ready]◀────────────────────────────┐
    │                             │                                │
    │                             │ next step requires transport   │
    │                             ▼                                │
    │                    [Requesting Mover]                        │
    │                             │                                │
    │                             │ mover assigned                 │
    │                             ▼                                │
    │                       [In Transit]                           │
    │                             │                                │
    │                             │ arrived at station             │
    │                             ▼                                │
    │                   [Requesting Device]                        │
    │                             │                                │
    │                             │ device available               │
    │                             ▼                                │
    │                        [Loading]                             │
    │                             │                                │
    │                             │ loaded, mover released         │
    │                             ▼                                │
    │                      [Processing]                            │
    │                             │                                │
    │                             │ processing complete            │
    │                             ▼                                │
    │                [Requesting Mover for Pickup]                 │
    │                             │                                │
    │                             │ mover assigned                 │
    │                             ▼                                │
    │                       [Unloading]                            │
    │                             │                                │
    │       more steps? ──────────┴────────── no more steps?       │
    │            │                                  │              │
    └────────────┘                                  ▼              │
                                            [Completed]            │
                                                                   │
    [Paused] ◀──── Pause ─────────────────────────────────────────┤
         │                                                         │
         └──────── Resume ─────────────────────────────────────────┘

    [Error] ◀──── Any error ──────────────────────────────────────┐
         │                                                         │
         └──────── Operator resolution ────────────────────────────┘
```

---

## Data Model

```python
from dataclasses import dataclass, field
from typing import Optional, List, Literal
from datetime import datetime

@dataclass
class PlateLocation:
    """Physical location of the plate."""
    type: Literal["unassigned", "on_mover", "in_device", "in_storage"]
    mover_id: Optional[int] = None
    device_id: Optional[str] = None
    storage_slot: Optional[str] = None
    station_id: Optional[str] = None

@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    id: str
    name: str
    station_id: str
    device_id: str
    device_type: str  # pipetter, incubator, washer, etc.
    duration: Optional[float] = None  # seconds, None for event-driven
    parameters: dict = field(default_factory=dict)

@dataclass
class Workflow:
    """Complete workflow definition."""
    id: str
    name: str
    version: str
    steps: List[WorkflowStep]

@dataclass
class PlateState:
    """Complete state of a PlateActor."""
    plate_id: str
    sample_ids: List[str]
    barcode: Optional[str]

    # Workflow state
    workflow_id: Optional[str]
    workflow_name: Optional[str]
    current_step: int
    total_steps: int

    # Phase and location
    phase: str
    location: PlateLocation
    assigned_mover: Optional[str]

    # Timing
    workflow_start_time: Optional[datetime]
    step_start_time: Optional[datetime]
    estimated_completion: Optional[datetime]

    # History (last N events)
    recent_history: List[dict]

    # Error state
    last_error: Optional[str]
    error_step: Optional[int]
```

---

## Messages

### Inbound Messages (to PlateActor)

```python
@dataclass
class AssignWorkflow:
    """Assign a workflow and samples to this plate."""
    workflow: Workflow
    sample_ids: List[str]
    barcode: Optional[str] = None

@dataclass
class Pause:
    """Pause workflow execution at next safe point."""
    reason: str = ""

@dataclass
class Resume:
    """Resume paused workflow execution."""
    pass

@dataclass
class Abort:
    """Abort workflow execution."""
    reason: str = ""

@dataclass
class GetState:
    """Request current state."""
    pass

@dataclass
class SkipStep:
    """Skip current step and proceed to next."""
    reason: str = ""

@dataclass
class RetryStep:
    """Retry the current/failed step."""
    pass

# Callbacks from resources
@dataclass
class MoverArrived:
    """Mover has arrived for pickup/dropoff."""
    mover_ref: ActorRef

@dataclass
class DeviceReady:
    """Device is ready to accept plate."""
    device_ref: ActorRef

@dataclass
class ProcessingComplete:
    """Device processing is complete."""
    device_id: str
    result: dict
```

### Outbound Events (from PlateActor)

```python
# Event types emitted to EventBus
PLATE_EVENTS = {
    "plate.created": "Plate actor created",
    "plate.workflow_assigned": "Workflow assigned to plate",
    "plate.mover_requested": "Requesting mover for transport",
    "plate.mover_assigned": "Mover assigned to plate",
    "plate.transport_started": "Transport to destination started",
    "plate.arrived": "Arrived at destination station",
    "plate.device_requested": "Requesting device access",
    "plate.loading": "Loading into device",
    "plate.mover_released": "Mover released back to pool",
    "plate.processing_started": "Device processing started",
    "plate.processing_progress": "Processing progress update",
    "plate.processing_completed": "Device processing completed",
    "plate.unloading": "Unloading from device",
    "plate.step_completed": "Workflow step completed",
    "plate.paused": "Workflow execution paused",
    "plate.resumed": "Workflow execution resumed",
    "plate.error": "Error occurred",
    "plate.workflow_completed": "Workflow completed successfully",
    "plate.aborted": "Workflow aborted",
}
```

---

## Behavior Patterns

### 1. Normal Step Execution

```python
async def _execute_next_step(self) -> None:
    step = self.workflow.steps[self.current_step]

    # Phase 1: Transport (if needed)
    if self._needs_transport(step):
        await self._travel_to(step.station_id)

    # Phase 2: Device processing
    await self._process_at_device(step)

    # Phase 3: Advance
    self.current_step += 1
    self.phase = "ready"
```

### 2. Mover Request and Release

```python
async def _travel_to(self, station_id: str) -> None:
    # REQUEST mover (I'm the customer)
    self.phase = "requesting_mover"
    self.assigned_mover = await self.mover_pool.request_mover(
        plate_id=self.plate_id,
        destination=station_id
    )

    # TRAVEL with mover
    self.phase = "in_transit"
    self.location = PlateLocation(type="on_mover", mover_id=self.assigned_mover.id)
    await self.assigned_mover.transport_to(station_id)

    # Mover is still assigned - will be released after device load

async def _process_at_device(self, step: WorkflowStep) -> None:
    device = await self.device_pool.request_device(step.device_id)

    # Load into device
    await device.load(self.plate_id, self.assigned_mover)

    # RELEASE mover - critical pattern!
    if self.assigned_mover:
        await self.mover_pool.release_mover(self.assigned_mover)
        self.assigned_mover = None

    self.location = PlateLocation(type="in_device", device_id=step.device_id)

    # Process (mover is free to serve others)
    await device.process(step.parameters)

    # Request NEW mover for pickup
    self.assigned_mover = await self.mover_pool.request_mover(
        plate_id=self.plate_id,
        pickup_from=step.device_id
    )

    # Unload onto mover
    await device.unload(self.plate_id, self.assigned_mover)
    self.location = PlateLocation(type="on_mover", mover_id=self.assigned_mover.id)
```

### 3. Pause/Resume Handling

```python
async def _on_pause(self, reason: str) -> dict:
    previous_phase = self.phase
    self.phase = "paused"
    self._paused_from = previous_phase

    await self._emit_event("plate.paused", {"reason": reason})
    return {"success": True, "paused_from": previous_phase}

async def _on_resume(self) -> dict:
    if self.phase != "paused":
        return {"success": False, "error": "Not paused"}

    self.phase = self._paused_from or "ready"
    await self._emit_event("plate.resumed", {})
    return {"success": True}
```

### 4. Error Handling

```python
async def _execute_next_step(self) -> None:
    try:
        # ... execution logic ...
    except TransportError as e:
        self.phase = "error"
        self.last_error = str(e)
        self.error_step = self.current_step
        await self._emit_event("plate.error", {
            "error_type": "transport",
            "error": str(e),
            "step": self.current_step,
            "recoverable": True
        })
        # Wait for operator intervention (Retry, Skip, Abort)
    except DeviceError as e:
        # Similar handling
    except Exception as e:
        # Unexpected error - log and wait
```

---

## Lifecycle Events

### Creation

```python
# PlateActor is created when a plate enters the system
actor = PlateActor(
    plate_id="ELISA_001",
    mover_pool=mover_pool,
    device_pool=device_pool,
    path_planner=path_planner,
    event_bus=event_bus
)
await actor.start()

# Assign workflow (could be immediate or later)
await actor.ref.tell(AssignWorkflow(
    workflow=elisa_workflow,
    sample_ids=["S001", "S002", ..., "S096"],
    barcode="ELISA_001_BC"
))
```

### Completion

```python
async def _complete_workflow(self) -> None:
    self.phase = "completed"

    await self._emit_event("plate.workflow_completed", {
        "total_steps": len(self.workflow.steps),
        "total_time": (datetime.now() - self.workflow_start_time).total_seconds(),
        "sample_count": len(self.sample_ids)
    })

    # Release any held resources
    if self.assigned_mover:
        await self.mover_pool.release_mover(self.assigned_mover)
        self.assigned_mover = None

    # Actor continues running (can be queried for state)
    # Eventually stopped by system when plate exits
```

### Shutdown

```python
# When plate exits system (removed, archived)
await actor.stop()
```

---

## UI Integration

### State Query for Inspector Panel

```python
# UI subscribes to events for real-time updates
event_bus.subscribe("plate.*", plate_id="ELISA_001", callback=update_ui)

# UI can also query current state directly
state = await plate_actor.ref.ask(GetState())
```

### Inspector Panel Data

```json
{
  "plate_id": "ELISA_001",
  "sample_ids": ["S001", "S002", "...", "S096"],
  "barcode": "ELISA_001_BC",

  "workflow_id": "elisa_v2.3",
  "workflow_name": "ELISA Protocol v2.3",
  "current_step": 4,
  "total_steps": 8,

  "phase": "processing",
  "location": {
    "type": "in_device",
    "device_id": "incubator-2",
    "station_id": "STATION_3"
  },
  "assigned_mover": null,

  "workflow_start_time": "2024-12-24T14:00:00Z",
  "step_start_time": "2024-12-24T14:15:00Z",
  "estimated_completion": "2024-12-24T14:45:00Z",

  "recent_history": [
    {"type": "plate.processing_started", "device_id": "incubator-2", "timestamp": "..."},
    {"type": "plate.mover_released", "mover_id": "mover-1", "timestamp": "..."},
    {"type": "plate.loading", "device_id": "incubator-2", "timestamp": "..."}
  ]
}
```

---

## Best Practices

1. **Plate owns workflow state** - Never let external systems modify step progress
2. **Release movers promptly** - Don't hold movers during device processing
3. **Emit events for everything** - UI and audit depend on event stream
4. **Handle all error cases** - Graceful degradation, operator intervention
5. **Immutable messages** - Never mutate messages after sending

---

## References

- [Constitution](./CONSTITUTION.md) - Article II: The Actor Model
- [Actor Model Implementation](./actor-model.md)
