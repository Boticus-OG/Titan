# CLAUDE.md

This file provides guidance to Claude Code when working with the Titan codebase.

## Project Overview

Titan is the XPlanar workflow orchestration platform, part of the SaturnOne suite. It enables users to design, execute, and monitor workflows that coordinate multiple movers, devices, and sample processing operations on Beckhoff XPlanar magnetic levitation systems.

**Read the Constitution first:** `docs/architecture/CONSTITUTION.md`

## Architectural Principles (Summary)

These are inviolable. See Constitution for full details.

1. **Distributed, not centralized** - No central controller. Actors are autonomous.
2. **PlateActor is the agent** - The plate/sample owns the workflow, not the mover.
3. **Movers are taxis** - Transport resources, released when not transporting.
4. **Services inform, actors decide** - PathPlanner, StationManager answer questions.
5. **Knowledge in the World** - UI shows state, doesn't compute it.

## Project Structure

```
Titan/
├── docs/
│   ├── architecture/          # Architectural decisions and designs
│   │   ├── CONSTITUTION.md    # THE governing document - READ FIRST
│   │   ├── actor-model.md     # Actor implementation details
│   │   ├── plate-actor.md     # PlateActor specification
│   │   └── ui-ux-concept.md   # UI/UX design documentation
│   ├── api/                   # API documentation
│   └── guides/                # Developer and user guides
├── frontend/                  # Nuxt 3 + Vue 3 application
│   ├── components/            # Vue components
│   ├── pages/                 # Nuxt pages
│   ├── composables/           # Vue composables
│   ├── layouts/               # Nuxt layouts
│   ├── stores/                # Pinia stores
│   └── types/                 # TypeScript types
├── backend/                   # Python FastAPI backend
│   ├── src/
│   │   ├── actors/            # Actor implementations
│   │   │   ├── plate_actor.py
│   │   │   ├── mover_actor.py
│   │   │   └── device_actor.py
│   │   ├── services/          # Shared services
│   │   │   ├── path_planner.py
│   │   │   ├── station_manager.py
│   │   │   └── event_bus.py
│   │   ├── pools/             # Resource pools
│   │   │   ├── mover_pool.py
│   │   │   └── device_pool.py
│   │   ├── api/               # FastAPI routes
│   │   └── models/            # Pydantic models
│   └── tests/
├── shared/                    # Shared types and constants
│   ├── types/
│   └── constants/
└── .vscode/                   # VS Code configuration
```

## Development Commands

### Backend (Python)

```bash
# Navigate to backend
cd backend

# Install dependencies
uv sync

# Run development server
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
uv run pytest

# Type checking
uv run pyright
```

### Frontend (Nuxt 3)

```bash
# Navigate to frontend
cd frontend

# Install dependencies
pnpm install

# Run development server
pnpm dev

# Build for production
pnpm build

# Type checking
pnpm type-check
```

## Key Concepts

### PlateActor

The autonomous agent representing a plate/sample and its workflow journey.

```python
class PlateActor:
    plate_id: str
    sample_ids: List[str]
    workflow: Workflow
    current_step: int
    location: PlateLocation  # on_mover, in_device, in_storage
    phase: PlatePhase        # ready, requesting_mover, in_transit, processing, etc.

    async def run(self):
        """Autonomous execution loop - plate manages its own journey."""
        while self.phase != "completed":
            await self._process_mailbox()
            if self.phase == "ready":
                await self._execute_next_step()
```

### MoverActor

Transport resource - a taxi, not an agent with a workflow.

```python
class MoverActor:
    mover_id: int
    physical_state: MoverPhysicalState  # position, track, velocity
    assigned_plate: Optional[str]       # current passenger

    async def transport_to(self, station_id: str):
        """Execute transport command - no workflow knowledge."""
```

### Resource Pools

Dispatchers that assign available resources to requesting actors.

```python
class MoverPool:
    async def request_mover(self, plate_id: str, destination: str) -> MoverRef:
        """Assign available mover to requesting plate."""

    async def release_mover(self, mover: MoverRef) -> None:
        """Return mover to available pool."""
```

## Common Patterns

### Actor Message Handling

```python
async def _process_mailbox(self):
    try:
        message = self.mailbox.get_nowait()
        match message:
            case Pause():
                await self._on_pause()
            case Resume():
                await self._on_resume()
            case GetState():
                # Return current state
    except asyncio.QueueEmpty:
        pass
```

### Event Emission

```python
await self.event_bus.emit(PlateEvent(
    type="plate.step_completed",
    plate_id=self.plate_id,
    step=step.name,
    timestamp=datetime.now()
))
```

## Anti-Patterns (DO NOT DO)

### ❌ Central Controller

```python
# WRONG - This violates the Constitution
class CentralController:
    def run_system(self):
        for mover in self.movers:
            if mover.idle and has_work(mover):
                next_step = compute_next_step(mover)  # Central decision
                mover.execute(next_step)
```

### ❌ Mover Owns Workflow

```python
# WRONG - Mover is just transport
class MoverActor:
    workflow: Workflow  # NO! Plate owns workflow

    async def execute_workflow(self):  # NO! Plate executes its workflow
        ...
```

### ❌ Services Issuing Commands

```python
# WRONG - Services answer questions, don't command
class StationManager:
    def route_mover_to_station(self, mover, station):  # NO!
        mover.go_to(station)
```

## Testing Strategy

- **Unit tests**: Test individual actors in isolation with mocked dependencies
- **Integration tests**: Test actor interactions with real resource pools
- **E2E tests**: Full workflow execution with simulated hardware

## Related Projects

- **DeviceHub**: Device management platform (separate repo, LabSync account)
- **XPlanar-test**: Prototype codebase with Path Planner and multi-mover coordination
- **D15 Driver**: HoverLabs pipetter driver (in DeviceHub)
- **HoverLabs**: Original HoverLabs repo (separate from Titan)

## Questions?

Refer to the Constitution: `docs/architecture/CONSTITUTION.md`

If the Constitution doesn't cover it, discuss with the team before implementing.
