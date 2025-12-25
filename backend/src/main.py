"""Titan API - FastAPI application with WebSocket support.

This is the main entry point for the Titan backend.
It provides REST endpoints and WebSocket for real-time events.
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .actors.base import GetState, ActorEvent
from .actors.plate_actor import PlateActor
from .actors.mover_actor import MoverActor
from .actors.messages import AssignWorkflow, WorkflowStep, Pause, Resume
from .services.mover_pool import MoverPool
from .services.event_bus import EventBus, Event, get_event_bus
from .models.deck import DeckConfig, create_demo_deck, GridPosition, TILE_SIZE_MM

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ============================================================================
# Application State
# ============================================================================

class TitanApp:
    """Application state container."""

    def __init__(self):
        self.event_bus = EventBus()
        self.mover_pool = MoverPool()
        self.plates: dict[str, PlateActor] = {}
        self.movers: dict[str, MoverActor] = {}
        self.websockets: list[WebSocket] = []
        self.deck: DeckConfig = create_demo_deck()

    async def startup(self) -> None:
        """Initialize the application."""
        logger.info("Titan: Starting up...")

        # Create movers
        for i in range(1, 4):  # 3 movers
            mover = MoverActor(
                mover_id=i,
                event_callback=self._on_event,
            )
            self.movers[f"mover-{i}"] = mover
            self.mover_pool.register_mover(mover)
            await mover.start()

        logger.info(f"Titan: {len(self.movers)} movers initialized")

    async def shutdown(self) -> None:
        """Clean up on shutdown."""
        logger.info("Titan: Shutting down...")

        # Stop all plates
        for plate in self.plates.values():
            await plate.stop()

        # Stop all movers
        for mover in self.movers.values():
            await mover.stop()

        # Close websockets
        for ws in self.websockets:
            try:
                await ws.close()
            except Exception:
                pass

        logger.info("Titan: Shutdown complete")

    async def _on_event(self, event: ActorEvent) -> None:
        """Handle events from actors."""
        # Emit to event bus
        await self.event_bus.emit(Event(
            event_type=event.event_type,
            actor_id=event.actor_id,
            data=event.data,
            timestamp=event.timestamp,
        ))

        # Broadcast to websockets
        await self._broadcast_event(event.to_dict())

    async def _broadcast_event(self, event: dict) -> None:
        """Broadcast event to all connected websockets."""
        if not self.websockets:
            return

        message = json.dumps(event)
        disconnected = []

        for ws in self.websockets:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        # Remove disconnected
        for ws in disconnected:
            self.websockets.remove(ws)


# Global app state
titan = TitanApp()


# ============================================================================
# FastAPI Lifespan
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    await titan.startup()
    yield
    await titan.shutdown()


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Titan",
    description="XPlanar Workflow Orchestration Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# REST Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Health check."""
    return {
        "name": "Titan",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/api/status")
async def get_status():
    """Get overall system status."""
    return {
        "plates": {
            "count": len(titan.plates),
            "ids": list(titan.plates.keys()),
        },
        "movers": titan.mover_pool.get_state(),
        "websockets": len(titan.websockets),
        "event_bus": {
            "subscriptions": titan.event_bus.subscription_count,
        },
    }


@app.get("/api/plates")
async def list_plates():
    """List all plates."""
    return {
        plate_id: await plate.ref.ask(GetState())
        for plate_id, plate in titan.plates.items()
    }


@app.get("/api/plates/{plate_id}")
async def get_plate(plate_id: str):
    """Get a specific plate's state."""
    plate = titan.plates.get(plate_id)
    if not plate:
        return {"error": f"Plate {plate_id} not found"}
    return await plate.ref.ask(GetState())


@app.post("/api/plates")
async def create_plate(plate_id: str, sample_ids: list[str] | None = None):
    """Create a new plate."""
    if plate_id in titan.plates:
        return {"error": f"Plate {plate_id} already exists"}

    plate = PlateActor(
        plate_id=plate_id,
        mover_pool=titan.mover_pool,
        event_callback=titan._on_event,
    )
    titan.plates[plate_id] = plate
    await plate.start()

    logger.info(f"API: Created plate {plate_id}")
    return {"status": "created", "plate_id": plate_id}


@app.post("/api/plates/{plate_id}/workflow")
async def assign_workflow(plate_id: str, workflow_id: str, steps: list[dict]):
    """Assign a workflow to a plate."""
    plate = titan.plates.get(plate_id)
    if not plate:
        return {"error": f"Plate {plate_id} not found"}

    # Convert steps to WorkflowStep objects
    workflow_steps = tuple(
        WorkflowStep(
            step_id=s.get("step_id", f"step-{i}"),
            name=s.get("name", f"Step {i}"),
            station_id=s.get("station_id", "STATION_1"),
            device_id=s.get("device_id", "device-1"),
            device_type=s.get("device_type", "generic"),
            duration=s.get("duration", 1.0),
        )
        for i, s in enumerate(steps)
    )

    result = await plate.ref.ask(AssignWorkflow(
        workflow_id=workflow_id,
        workflow_steps=workflow_steps,
        sample_ids=tuple(),
    ))

    return result


@app.post("/api/plates/{plate_id}/pause")
async def pause_plate(plate_id: str, reason: str = ""):
    """Pause a plate's workflow."""
    plate = titan.plates.get(plate_id)
    if not plate:
        return {"error": f"Plate {plate_id} not found"}

    result = await plate.ref.ask(Pause(reason=reason))
    return result


@app.post("/api/plates/{plate_id}/resume")
async def resume_plate(plate_id: str):
    """Resume a paused plate."""
    plate = titan.plates.get(plate_id)
    if not plate:
        return {"error": f"Plate {plate_id} not found"}

    result = await plate.ref.ask(Resume())
    return result


@app.get("/api/movers")
async def list_movers():
    """List all movers."""
    return {
        mover_id: await mover.ref.ask(GetState())
        for mover_id, mover in titan.movers.items()
    }


@app.get("/api/movers/{mover_id}")
async def get_mover(mover_id: str):
    """Get a specific mover's state."""
    mover = titan.movers.get(mover_id)
    if not mover:
        return {"error": f"Mover {mover_id} not found"}
    return await mover.ref.ask(GetState())


@app.get("/api/events")
async def get_events(pattern: str = "**", limit: int = 100):
    """Get recent events from history."""
    return titan.event_bus.get_history(pattern=pattern, limit=limit)


# ============================================================================
# Deck Configuration Endpoints
# ============================================================================

@app.get("/api/deck")
async def get_deck():
    """Get the current deck configuration.

    Returns the full deck layout including:
    - Grid dimensions and tile size
    - All stator tiles with their positions
    - All stations with device types and availability
    """
    return titan.deck.to_dict()


@app.get("/api/deck/stations")
async def get_stations():
    """Get all stations on the deck."""
    return [station.to_dict() for station in titan.deck.stations]


@app.get("/api/deck/stations/{station_id}")
async def get_station(station_id: str):
    """Get a specific station."""
    station = titan.deck.get_station(station_id)
    if not station:
        return {"error": f"Station {station_id} not found"}
    return station.to_dict()


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """WebSocket endpoint for real-time events."""
    await websocket.accept()
    titan.websockets.append(websocket)
    logger.info(f"WebSocket: Client connected (total: {len(titan.websockets)})")

    try:
        # Send initial state
        await websocket.send_json({
            "type": "connected",
            "plates": list(titan.plates.keys()),
            "movers": list(titan.movers.keys()),
        })

        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                # Handle commands from client
                if message.get("type") == "get_state":
                    actor_id = message.get("actor_id")
                    if actor_id in titan.plates:
                        state = await titan.plates[actor_id].ref.ask(GetState())
                        await websocket.send_json({"type": "state", "data": state})
                    elif actor_id in titan.movers:
                        state = await titan.movers[actor_id].ref.ask(GetState())
                        await websocket.send_json({"type": "state", "data": state})

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                continue

    finally:
        if websocket in titan.websockets:
            titan.websockets.remove(websocket)
        logger.info(f"WebSocket: Client disconnected (total: {len(titan.websockets)})")


# ============================================================================
# Demo Endpoint
# ============================================================================

@app.post("/api/demo/run")
async def run_demo():
    """Run a demo workflow to test the system.

    Creates a plate and runs it through a simple workflow.
    """
    plate_id = "DEMO_001"

    # If plate exists and is completed/error, remove it and create fresh
    if plate_id in titan.plates:
        old_plate = titan.plates[plate_id]
        state = old_plate.get_state()
        if state.get("phase") in ("completed", "error", "aborted"):
            await old_plate.stop()
            del titan.plates[plate_id]

    # Create plate if not exists
    if plate_id not in titan.plates:
        plate = PlateActor(
            plate_id=plate_id,
            mover_pool=titan.mover_pool,
            event_callback=titan._on_event,
        )
        titan.plates[plate_id] = plate
        await plate.start()

    plate = titan.plates[plate_id]

    # Define demo workflow
    workflow_steps = (
        WorkflowStep(
            step_id="step-1",
            name="Delid",
            station_id="STATION_1",
            device_id="lidmate-1",
            device_type="lidmate",
            duration=2.0,
        ),
        WorkflowStep(
            step_id="step-2",
            name="Pipette",
            station_id="STATION_1",
            device_id="pipetter-1",
            device_type="pipetter",
            duration=3.0,
        ),
        WorkflowStep(
            step_id="step-3",
            name="Dispense",
            station_id="STATION_2",
            device_id="dispenser-1",
            device_type="dispenser",
            duration=2.0,
        ),
        WorkflowStep(
            step_id="step-4",
            name="Incubate",
            station_id="STATION_3",
            device_id="incubator-1",
            device_type="incubator",
            duration=5.0,
        ),
    )

    # Assign and start workflow
    result = await plate.ref.ask(AssignWorkflow(
        workflow_id="demo-workflow",
        workflow_steps=workflow_steps,
        sample_ids=("S001", "S002", "S003"),
    ))

    return {
        "status": "demo_started",
        "plate_id": plate_id,
        "workflow_id": "demo-workflow",
        "steps": len(workflow_steps),
        "result": result,
    }
