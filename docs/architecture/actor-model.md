# Actor Model Implementation

**Version:** 1.0.0
**Last Updated:** 2024-12-24

---

## Overview

HoverLabs implements a lightweight actor model using Python's asyncio primitives. This document describes the implementation patterns, message passing, and lifecycle management.

## Why Not Full Akka?

Akka provides:
| Feature | Our Need | Decision |
|---------|----------|----------|
| Actor lifecycle | Yes | Implement with asyncio.Task |
| Mailbox/messaging | Yes | Implement with asyncio.Queue |
| Supervision trees | Nice to have | Simple parent-child |
| Location transparency | No | Single machine |
| Cluster support | No | Single machine |
| Persistence | No | Database sufficient |

**Decision:** Build lightweight actors in Python. The concepts matter more than the framework.

---

## Core Components

### ActorRef

A reference for sending messages to an actor without direct access.

```python
from dataclasses import dataclass
from typing import Any
import asyncio

@dataclass
class ActorRef:
    """Reference to an actor for message passing."""
    actor_id: str
    mailbox: asyncio.Queue

    async def tell(self, message: Any) -> None:
        """Fire-and-forget message send."""
        await self.mailbox.put(message)

    async def ask(self, message: Any, timeout: float = 30.0) -> Any:
        """Request-response pattern with timeout."""
        response_queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        await self.mailbox.put((message, response_queue))
        return await asyncio.wait_for(response_queue.get(), timeout)
```

### BaseActor

Abstract base class for all actors.

```python
from abc import ABC, abstractmethod
from typing import Optional
import asyncio

class BaseActor(ABC):
    """Base class for all actors in the system."""

    def __init__(self, actor_id: str):
        self.actor_id = actor_id
        self.mailbox: asyncio.Queue = asyncio.Queue()
        self.ref = ActorRef(actor_id, self.mailbox)
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the actor's message processing loop."""
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """Gracefully stop the actor."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self) -> None:
        """Main actor loop."""
        while self._running:
            try:
                # Process mailbox
                await self._process_mailbox()

                # Actor-specific behavior
                await self._tick()

                # Prevent busy-waiting
                await asyncio.sleep(0.05)

            except Exception as e:
                await self._handle_error(e)

    async def _process_mailbox(self) -> None:
        """Process pending messages."""
        try:
            while True:
                message = self.mailbox.get_nowait()
                await self._handle_message(message)
        except asyncio.QueueEmpty:
            pass

    async def _handle_message(self, message: Any) -> None:
        """Route messages to handlers."""
        if isinstance(message, tuple) and len(message) == 2:
            # Request-response pattern
            msg, response_queue = message
            try:
                result = await self._process_message(msg)
                await response_queue.put(result)
            except Exception as e:
                await response_queue.put(e)
        else:
            # Fire-and-forget
            await self._process_message(message)

    @abstractmethod
    async def _process_message(self, message: Any) -> Any:
        """Process a single message. Override in subclass."""
        pass

    @abstractmethod
    async def _tick(self) -> None:
        """Called each iteration. Override for autonomous behavior."""
        pass

    async def _handle_error(self, error: Exception) -> None:
        """Handle errors. Override for custom error handling."""
        # Default: log and continue
        print(f"Actor {self.actor_id} error: {error}")
```

---

## Message Types

Define messages as dataclasses for type safety and clarity.

```python
from dataclasses import dataclass
from typing import Optional, List

# System messages
@dataclass
class Pause:
    reason: str = ""

@dataclass
class Resume:
    pass

@dataclass
class GetState:
    pass

@dataclass
class Shutdown:
    pass

# PlateActor messages
@dataclass
class AssignWorkflow:
    workflow: 'Workflow'
    sample_ids: List[str]

@dataclass
class MoverAssigned:
    mover_ref: 'ActorRef'

@dataclass
class ProcessingComplete:
    device_id: str
    result: dict

# MoverActor messages
@dataclass
class TransportTo:
    station_id: str
    plate_id: str

@dataclass
class ReleaseFromPlate:
    plate_id: str
```

---

## Actor Implementations

### PlateActor

The autonomous agent managing a plate's workflow journey.

```python
from dataclasses import dataclass, field
from typing import Optional, List, Literal
from datetime import datetime

@dataclass
class PlateLocation:
    type: Literal["unassigned", "on_mover", "in_device", "in_storage"]
    mover_id: Optional[int] = None
    device_id: Optional[str] = None
    storage_slot: Optional[str] = None

PlatePhase = Literal[
    "created",
    "ready",
    "requesting_mover",
    "in_transit",
    "requesting_device",
    "loading",
    "processing",
    "unloading",
    "paused",
    "error",
    "completed"
]

class PlateActor(BaseActor):
    """Autonomous agent managing a plate's workflow journey."""

    def __init__(
        self,
        plate_id: str,
        mover_pool: 'MoverPool',
        device_pool: 'DevicePool',
        path_planner: 'PathPlanner',
        event_bus: 'EventBus'
    ):
        super().__init__(f"plate-{plate_id}")
        self.plate_id = plate_id
        self.sample_ids: List[str] = []
        self.workflow: Optional['Workflow'] = None
        self.current_step: int = 0

        # Physical location
        self.location = PlateLocation(type="unassigned")

        # Current resources
        self.assigned_mover: Optional[ActorRef] = None

        # State
        self.phase: PlatePhase = "created"
        self.history: List[dict] = []

        # Dependencies (services, not controllers)
        self.mover_pool = mover_pool
        self.device_pool = device_pool
        self.path_planner = path_planner
        self.event_bus = event_bus

    async def _process_message(self, message: Any) -> Any:
        """Handle incoming messages."""
        match message:
            case AssignWorkflow(workflow, sample_ids):
                return await self._on_assign_workflow(workflow, sample_ids)
            case Pause(reason):
                return await self._on_pause(reason)
            case Resume():
                return await self._on_resume()
            case GetState():
                return self._get_state()
            case MoverAssigned(mover_ref):
                return await self._on_mover_assigned(mover_ref)
            case ProcessingComplete(device_id, result):
                return await self._on_processing_complete(device_id, result)
            case _:
                raise ValueError(f"Unknown message: {message}")

    async def _tick(self) -> None:
        """Autonomous behavior - execute workflow when ready."""
        if self.phase == "ready" and self.workflow:
            if self.current_step < len(self.workflow.steps):
                await self._execute_next_step()
            else:
                await self._complete_workflow()

    async def _on_assign_workflow(self, workflow: 'Workflow', sample_ids: List[str]) -> str:
        """Assign workflow to this plate."""
        self.workflow = workflow
        self.sample_ids = sample_ids
        self.current_step = 0
        self.phase = "ready"

        await self._emit_event("plate.workflow_assigned", {
            "workflow_id": workflow.id,
            "sample_count": len(sample_ids)
        })

        return "assigned"

    async def _execute_next_step(self) -> None:
        """Execute the next workflow step - THE CORE AUTONOMY."""
        step = self.workflow.steps[self.current_step]

        try:
            # 1. Travel to destination if needed
            if self._needs_transport(step):
                await self._travel_to(step.station_id)

            # 2. Process at device
            await self._process_at_device(step)

            # 3. Advance to next step
            self.current_step += 1
            self.phase = "ready"

            await self._emit_event("plate.step_completed", {
                "step_index": self.current_step - 1,
                "step_name": step.name,
                "device_id": step.device_id
            })

        except Exception as e:
            self.phase = "error"
            await self._emit_event("plate.error", {
                "step_index": self.current_step,
                "error": str(e)
            })

    async def _travel_to(self, station_id: str) -> None:
        """Request mover and travel to destination."""
        self.phase = "requesting_mover"

        # I request a mover (I'm the customer)
        self.assigned_mover = await self.mover_pool.request_mover(
            plate_id=self.plate_id,
            destination=station_id
        )

        self.phase = "in_transit"
        self.location = PlateLocation(type="on_mover", mover_id=self.assigned_mover.actor_id)

        await self._emit_event("plate.transport_started", {
            "mover_id": self.assigned_mover.actor_id,
            "destination": station_id
        })

        # The mover transports me
        await self.assigned_mover.ask(TransportTo(
            station_id=station_id,
            plate_id=self.plate_id
        ))

        await self._emit_event("plate.arrived", {"station_id": station_id})

    async def _process_at_device(self, step: 'WorkflowStep') -> None:
        """Load into device, process, unload."""
        device = await self.device_pool.request_device(step.device_id)

        # Load into device
        self.phase = "loading"
        await device.ask(LoadPlate(plate_id=self.plate_id, mover=self.assigned_mover))

        # RELEASE THE MOVER - key insight from Constitution
        if self.assigned_mover:
            await self.mover_pool.release_mover(self.assigned_mover)
            self.assigned_mover = None

        self.location = PlateLocation(type="in_device", device_id=step.device_id)

        # Process
        self.phase = "processing"
        await self._emit_event("plate.processing_started", {
            "device_id": step.device_id,
            "duration": step.duration
        })

        # Wait for completion (device will notify)
        await device.ask(WaitForCompletion(plate_id=self.plate_id))

        await self._emit_event("plate.processing_completed", {
            "device_id": step.device_id
        })

        # Request mover for pickup
        self.phase = "requesting_mover"
        self.assigned_mover = await self.mover_pool.request_mover(
            plate_id=self.plate_id,
            pickup_from=step.device_id
        )

        # Unload from device onto mover
        self.phase = "unloading"
        await device.ask(UnloadPlate(plate_id=self.plate_id, mover=self.assigned_mover))
        self.location = PlateLocation(type="on_mover", mover_id=self.assigned_mover.actor_id)

        await self.device_pool.release_device(device)

    async def _complete_workflow(self) -> None:
        """Mark workflow as complete."""
        self.phase = "completed"
        await self._emit_event("plate.workflow_completed", {
            "total_steps": len(self.workflow.steps),
            "sample_count": len(self.sample_ids)
        })

    def _get_state(self) -> dict:
        """Return current state for inspection."""
        return {
            "plate_id": self.plate_id,
            "sample_ids": self.sample_ids,
            "phase": self.phase,
            "location": self.location,
            "workflow_id": self.workflow.id if self.workflow else None,
            "current_step": self.current_step,
            "total_steps": len(self.workflow.steps) if self.workflow else 0,
            "assigned_mover": self.assigned_mover.actor_id if self.assigned_mover else None,
            "history": self.history[-10:]  # Last 10 events
        }

    async def _emit_event(self, event_type: str, data: dict) -> None:
        """Emit event to event bus."""
        event = {
            "type": event_type,
            "plate_id": self.plate_id,
            "timestamp": datetime.now().isoformat(),
            **data
        }
        self.history.append(event)
        await self.event_bus.emit(event)
```

### MoverActor

Transport resource - just a taxi.

```python
class MoverActor(BaseActor):
    """Transport resource - no workflow knowledge."""

    def __init__(
        self,
        mover_id: int,
        controller: 'XPlanarController',
        path_planner: 'PathPlanner',
        event_bus: 'EventBus'
    ):
        super().__init__(f"mover-{mover_id}")
        self.mover_id = mover_id
        self.assigned_plate: Optional[str] = None

        # Physical state (from PLC)
        self.position: Optional['Position'] = None
        self.track_id: Optional[int] = None
        self.track_position: float = 0.0

        # Dependencies
        self.controller = controller
        self.path_planner = path_planner
        self.event_bus = event_bus

    async def _process_message(self, message: Any) -> Any:
        match message:
            case TransportTo(station_id, plate_id):
                return await self._transport_to(station_id, plate_id)
            case ReleaseFromPlate(plate_id):
                return await self._release_from_plate(plate_id)
            case GetState():
                return self._get_state()
            case _:
                raise ValueError(f"Unknown message: {message}")

    async def _tick(self) -> None:
        """Refresh physical state from PLC."""
        await self._refresh_state()

    async def _transport_to(self, station_id: str, plate_id: str) -> dict:
        """Execute transport to destination."""
        self.assigned_plate = plate_id

        # Get route from GPS service
        plan = await self.path_planner.plan_journey(
            mover_id=self.mover_id,
            destination=station_id
        )

        # Execute each command in the plan
        for command in plan.commands:
            result = await self.controller.execute_command(self.mover_id, command)
            if not result.success:
                return {"success": False, "error": result.error}

        return {"success": True}

    async def _release_from_plate(self, plate_id: str) -> dict:
        """Release from plate assignment."""
        if self.assigned_plate == plate_id:
            self.assigned_plate = None
            return {"success": True}
        return {"success": False, "error": "Not assigned to this plate"}

    def _get_state(self) -> dict:
        return {
            "mover_id": self.mover_id,
            "assigned_plate": self.assigned_plate,
            "position": self.position,
            "track_id": self.track_id,
            "track_position": self.track_position
        }
```

---

## Actor Lifecycle

```
                    [Created]
                        │
                        │ start()
                        ▼
    ┌──────────────▶[Running]◀──────────────┐
    │                   │                    │
    │                   │ message/tick       │
    │                   ▼                    │
    │              [Processing]──────────────┘
    │                   │
    │                   │ error
    │                   ▼
    │              [Error]
    │                   │
    │                   │ recover
    │                   │
    └───────────────────┘
                        │
                        │ stop()
                        ▼
                   [Stopped]
```

---

## Testing Actors

```python
import pytest
import asyncio

@pytest.fixture
def mock_services():
    return {
        "mover_pool": MockMoverPool(),
        "device_pool": MockDevicePool(),
        "path_planner": MockPathPlanner(),
        "event_bus": MockEventBus()
    }

@pytest.mark.asyncio
async def test_plate_actor_workflow_execution(mock_services):
    # Arrange
    actor = PlateActor("TEST_001", **mock_services)
    workflow = create_test_workflow()

    await actor.start()

    # Act
    result = await actor.ref.ask(AssignWorkflow(workflow, ["S001", "S002"]))

    # Wait for workflow to complete
    await asyncio.sleep(0.5)

    # Assert
    state = await actor.ref.ask(GetState())
    assert state["phase"] == "completed"
    assert state["current_step"] == len(workflow.steps)

    await actor.stop()
```

---

## Best Practices

1. **Message immutability** - Messages should be immutable dataclasses
2. **No shared mutable state** - Actors communicate via messages only
3. **Fail fast, recover gracefully** - Errors are caught and handled
4. **Log everything** - Events provide audit trail
5. **Test in isolation** - Mock dependencies, test actor behavior

---

## References

- [Akka Actor Model](https://doc.akka.io/libraries/guide/concepts/akka-actor.html)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
- [Constitution](./CONSTITUTION.md)
