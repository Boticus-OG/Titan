#!/usr/bin/env python3
"""Demo script for Titan actor system.

This script demonstrates the PlateActor executing a workflow
with mover transport and device processing.

Run with: uv run python demo.py
"""

import asyncio
import logging
from datetime import datetime

from src.actors.plate_actor import PlateActor
from src.actors.mover_actor import MoverActor
from src.actors.messages import AssignWorkflow, WorkflowStep
from src.actors.base import ActorEvent
from src.services.mover_pool import MoverPool
from src.services.event_bus import EventBus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def format_event(event: ActorEvent) -> str:
    """Format an event for display."""
    return f"[{event.event_type}] {event.actor_id}: {event.data}"


async def main():
    """Run the demo."""
    print("\n" + "=" * 70)
    print("🚀 TITAN ACTOR SYSTEM DEMO")
    print("=" * 70 + "\n")

    # Create event bus
    event_bus = EventBus()

    # Event handler for logging
    async def on_event(event: ActorEvent):
        await event_bus.emit(event)
        print(f"  📢 {format_event(event)}")

    # Create mover pool and movers
    print("🔧 Initializing movers...")
    mover_pool = MoverPool()

    movers = []
    for i in range(1, 4):
        mover = MoverActor(
            mover_id=i,
            event_callback=on_event,
            transport_speed=200.0,  # Fast for demo
        )
        movers.append(mover)
        mover_pool.register_mover(mover)
        await mover.start()
        print(f"  ✓ Mover {i} started")

    # Create plate
    print("\n📦 Creating plate...")
    plate = PlateActor(
        plate_id="ELISA_001",
        mover_pool=mover_pool,
        event_callback=on_event,
    )
    await plate.start()
    print(f"  ✓ Plate {plate.plate_id} created")

    # Define workflow
    print("\n📋 Defining workflow...")
    workflow_steps = (
        WorkflowStep(
            step_id="step-1",
            name="Delid",
            station_id="STATION_1",
            device_id="lidmate-1",
            device_type="lidmate",
            duration=1.0,
        ),
        WorkflowStep(
            step_id="step-2",
            name="Pipette",
            station_id="STATION_1",
            device_id="pipetter-1",
            device_type="pipetter",
            duration=2.0,
        ),
        WorkflowStep(
            step_id="step-3",
            name="Dispense",
            station_id="STATION_2",
            device_id="dispenser-1",
            device_type="dispenser",
            duration=1.5,
        ),
        WorkflowStep(
            step_id="step-4",
            name="Incubate",
            station_id="STATION_3",
            device_id="incubator-1",
            device_type="incubator",
            duration=3.0,
        ),
    )

    for i, step in enumerate(workflow_steps):
        print(f"  {i+1}. {step.name} @ {step.station_id}/{step.device_id} ({step.duration}s)")

    # Assign workflow
    print("\n▶️  Assigning workflow and starting execution...\n")
    print("-" * 70)

    result = await plate.ref.ask(AssignWorkflow(
        workflow_id="ELISA-v2.3",
        workflow_steps=workflow_steps,
        sample_ids=("S001", "S002", "S003", "S004"),
        barcode="ELISA_001_BC",
    ))

    print(f"\n  Workflow assigned: {result}")

    # Wait for workflow to complete
    print("\n⏳ Workflow executing...\n")

    start_time = datetime.now()
    while True:
        state = plate.get_state()
        phase = state["phase"]

        if phase == "completed":
            break
        if phase in ("error", "aborted"):
            print(f"\n❌ Workflow failed: {state.get('error')}")
            break

        await asyncio.sleep(0.5)

        # Timeout after 60 seconds
        if (datetime.now() - start_time).total_seconds() > 60:
            print("\n⚠️ Timeout waiting for workflow completion")
            break

    # Final state
    print("-" * 70)
    print("\n📊 FINAL STATE\n")

    state = plate.get_state()
    print(f"  Plate ID:      {state['plate_id']}")
    print(f"  Phase:         {state['phase']}")
    print(f"  Workflow:      {state['workflow']['workflow_id']}")
    print(f"  Steps:         {state['workflow']['current_step']}/{state['workflow']['total_steps']}")
    print(f"  Progress:      {state['workflow']['progress_percent']:.0f}%")

    # Show mover pool state
    print("\n  Mover Pool:")
    pool_state = mover_pool.get_state()
    print(f"    Available:   {pool_state['available_movers']}/{pool_state['total_movers']}")
    print(f"    Pending:     {pool_state['pending_requests']}")

    # Recent history
    print("\n  Recent History:")
    for entry in state["history"][-5:]:
        print(f"    - {entry['type']}")

    # Cleanup
    print("\n🛑 Shutting down...")
    await plate.stop()
    for mover in movers:
        await mover.stop()

    print("\n" + "=" * 70)
    print("✅ DEMO COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
