# Titan Platform Constitution

> *"The plate is the customer. The mover is the taxi. The device is the service provider. The customer is always in charge of their itinerary."*

**Version:** 1.0.0
**Established:** 2024-12-24
**Status:** RATIFIED

---

## Preamble

This Constitution establishes the foundational principles, architectural patterns, and inviolable rules that govern the design and implementation of Titan, the XPlanar Workflow Orchestrator (part of the SaturnOne suite). These principles emerged from analysis of laboratory automation requirements and the recognition that **distributed, actor-based control** provides superior flexibility, maintainability, and user experience compared to centralized control architectures.

All contributors, including AI assistants, shall adhere to these principles. Amendments require explicit ratification.

---

## Article I: Core Philosophy

### Section 1.1: Distributed Over Centralized

**RATIFIED:** The system SHALL use a distributed actor-based architecture. There SHALL NOT be a central controller that orchestrates all system behavior.

**Rationale:** Centralized control creates:
- Single points of failure
- State explosion as complexity grows
- Spaghetti code with interleaved decision logic
- Impediments to advanced UI/UX features
- Testing and debugging nightmares

### Section 1.2: Actors Decide, Services Inform

**RATIFIED:** Autonomous actors (PlateActors) make decisions about their own behavior. Shared services (PathPlanner, StationManager, ResourcePools) answer questions but do not issue commands.

```
CORRECT:   PlateActor asks StationManager "Is Station 1 available?"
           StationManager responds "No, occupied by Plate 7"
           PlateActor decides to wait in queue

INCORRECT: Controller commands "Mover 1, wait. Mover 2, proceed."
```

### Section 1.3: Knowledge in the World

**RATIFIED:** Following Don Norman's principle, system state SHALL be visible in the interface. Users should not need to recall hidden state or modes. The UI reflects reality; it does not compute it.

---

## Article II: The Actor Model

### Section 2.1: PlateActor is the Autonomous Agent

**RATIFIED:** The PlateActor (representing a plate/sample and its workflow) is the primary autonomous agent in the system. The PlateActor:

1. **Owns the workflow** (itinerary of steps)
2. **Tracks its own progress** through the workflow
3. **Knows its physical location** (on mover, in device, in storage)
4. **Requests resources** when needed (movers, devices, stations)
5. **Releases resources** when done
6. **Manages its own state machine**
7. **Emits events** for UI and logging

### Section 2.2: MoverActor is a Transport Resource

**RATIFIED:** The MoverActor represents a physical mover (XPlanar tile-based transport). The MoverActor:

1. **Executes transport commands** (move to position, follow track)
2. **Tracks physical state** (position, track, velocity)
3. **Has NO workflow knowledge**
4. **Is assigned by MoverPool**, released back when transport complete
5. Is **interchangeable** - any mover can serve any plate (within physical constraints)

The mover is a taxi. It does not know or care about the passenger's itinerary.

### Section 2.3: DeviceActor is a Service Provider

**RATIFIED:** The DeviceActor represents a laboratory device (pipetter, incubator, washer, etc.). The DeviceActor:

1. **Executes processing commands** (pipette, incubate, wash)
2. **Can hold plate(s)** during processing
3. **Notifies plate** when processing complete
4. **Has NO workflow knowledge**
5. **Is assigned by DevicePool**, released when processing complete

### Section 2.4: The Taxi Metaphor

**RATIFIED:** The following metaphor SHALL guide all architectural decisions:

| Concept | System Element | Behavior |
|---------|----------------|----------|
| Passenger | PlateActor | Has itinerary, decides where to go, hails transport |
| Taxi | MoverActor | Provides transport, doesn't know itinerary |
| Buildings | DeviceActors | Provide services, don't know customer's day |
| Taxi Dispatcher | MoverPool | Assigns available taxis, doesn't control passengers |
| Traffic Signals | StationManager | Provides access control, doesn't route taxis |
| GPS | PathPlanner | Answers "how to get there", doesn't command movement |

---

## Article III: Resource Management

### Section 3.1: Resource Pools are Dispatchers, Not Controllers

**RATIFIED:** Resource pools (MoverPool, DevicePool) dispatch available resources to requesting actors. They do not:
- Track workflow state
- Make decisions about workflow progression
- Command actors to perform actions

### Section 3.2: Request-Release Lifecycle

**RATIFIED:** Resources follow a strict request-release lifecycle:

```
PlateActor                    ResourcePool                 Resource
    │                              │                           │
    │──── request_resource() ─────▶│                           │
    │                              │──── assign() ────────────▶│
    │◀─── resource_ref ───────────│                           │
    │                              │                           │
    │══════════════ USE RESOURCE ══════════════════════════════│
    │                              │                           │
    │──── release_resource() ─────▶│                           │
    │                              │◀─── available ───────────│
    │                              │                           │
```

### Section 3.3: Movers Released During Device Processing

**RATIFIED:** When a plate enters a device (incubator, hotel, etc.), the mover SHALL be released back to the pool. The plate requests a new mover when ready to continue.

**Rationale:** This maximizes mover utilization. A 30-minute incubation should not idle a mover.

### Section 3.4: Queue-Based Station Gating

**RATIFIED:** Station access uses queue-based gating:

1. Plates request station access via StationManager
2. If station occupied, plate joins queue at designated queue point
3. When station available, next plate in queue is granted access
4. Physical queue points prevent collisions

---

## Article IV: State Management

### Section 4.1: Dual-State Model

**RATIFIED:** System state has two layers:

1. **Physical State** - Ground truth from hardware (PLC, sensors)
   - Mover position, track, velocity
   - Device operational state
   - Actual plate location

2. **Semantic State** - Interpreted meaning from planning
   - Current workflow step
   - Intended destination
   - Processing context

Both states SHALL be visible in the UI.

### Section 4.2: Actor Owns Its State

**RATIFIED:** Each actor is the authority on its own state. The UI queries actors directly; it does not compute state from a central store.

```
UI asks: "What is Plate 7 doing?"
PlateActor7: "I'm processing at Incubator 2, step 4 of 8, 14:30 remaining"
```

### Section 4.3: Event-Driven State Propagation

**RATIFIED:** State changes are propagated via events on the EventBus. Actors emit events; the UI and other interested parties subscribe.

---

## Article V: User Interface Principles

### Section 5.1: Plate-Centric Primary View

**RATIFIED:** The primary UI perspective is plate-centric. Users care about samples/plates, not movers. Movers are infrastructure.

### Section 5.2: Drill-Down Capability

**RATIFIED:** Users SHALL be able to drill down from any visual element to see the underlying actor state, mailbox, history, and metrics.

### Section 5.3: Tiered Access

**RATIFIED:** The UI supports role-based access:

| Role | Capabilities |
|------|--------------|
| Operator | Run, pause, stop workflows; monitor; handle errors |
| Engineer | Design workflows; configure devices; debug; full actor inspection |
| Admin | User management; system configuration; audit logs |

### Section 5.4: Design-Time Only Workflow Editing

**RATIFIED:** Workflows are edited at design-time only. Running workflows cannot be modified. This simplifies state management and prevents race conditions.

---

## Article VI: Sample Tracking

### Section 6.1: Worklist-Based Assignment

**RATIFIED:** Sample/plate identity is assigned via:
1. Worklist import (CSV, Excel)
2. Manual accessioning interface

### Section 6.2: Barcode Confirmation

**RATIFIED:** Barcode scanning provides confirmation, not primary assignment. Scanned barcode is verified against expected plate ID.

### Section 6.3: LIMS Integration Hooks

**RATIFIED:** The system SHALL provide hooks for LIMS integration:
- Event emission for plate lifecycle events
- API endpoints for plate status queries
- Webhook support for external notifications

LIMS integration is not required for MVP but architecture must support it.

---

## Article VII: Technology Decisions

### Section 7.1: Backend: Python with asyncio

**RATIFIED:** The backend uses Python with asyncio for actor implementation. This aligns with existing XPlanar codebase and provides native async primitives.

### Section 7.2: Frontend: Nuxt 3 + Vue 3

**RATIFIED:** The frontend uses Nuxt 3 with Vue 3. This provides:
- Consistency with DeviceHub
- Vue Flow for workflow designer
- Strong TypeScript support

### Section 7.3: API-First Design

**RATIFIED:** The backend exposes a well-defined API (REST + WebSocket). The frontend is replaceable. API specification is the contract.

### Section 7.4: Lightweight Actor Implementation

**RATIFIED:** Actors are implemented using Python asyncio primitives (Queue, Task, Event). Full Akka/actor frameworks are not required for MVP.

---

## Article VIII: Physical Layout

### Section 8.1: Stator Grid System

**RATIFIED:** The XPlanar deck is composed of stator tiles arranged in a perfect grid:

| Property | Value |
|----------|-------|
| Stator tile size | 240mm × 240mm |
| Grid alignment | Perfect edge-to-edge mating |
| Extensibility | Grid can extend in any direction |

### Section 8.2: Movement Constraints

**RATIFIED:** Movers can ONLY traverse the surface of stator tiles. The stator grid defines the navigable area.

### Section 8.3: Device Footprints

**RATIFIED:** All devices that dock to the XPlanar system share the standard 240mm × 240mm footprint. This allows:
- Uniform grid-based placement
- Predictable station positions
- Modular deck reconfiguration

### Section 8.4: Coordinate System

**RATIFIED:** The deck uses a millimeter-based coordinate system:
- Origin (0,0) at top-left corner of the deck
- X-axis increases to the right
- Y-axis increases downward
- Positions can be expressed as grid coordinates (tile indices) or absolute mm coordinates

```
Grid Position (1, 2) = Absolute Position (240mm, 480mm)
```

### Section 8.5: Visualization Fidelity

**RATIFIED:** The 2D deck visualization SHALL accurately reflect physical layout:
- 1:1 aspect ratio for tiles
- Stator tiles clearly distinguished from non-traversable areas
- Device positions locked to grid
- Mover positions shown at actual mm coordinates (within grid)

---

## Article IX: Naming Conventions

### Section 9.1: Actor Naming

| Entity | Naming Pattern | Example |
|--------|----------------|---------|
| PlateActor | `plate-{plate_id}` | `plate-ELISA_001` |
| MoverActor | `mover-{mover_id}` | `mover-1` |
| DeviceActor | `device-{device_type}-{id}` | `device-pipetter-1` |

### Section 9.2: Event Naming

Events use dot-notation: `{actor_type}.{event_name}`

Examples:
- `plate.workflow_started`
- `plate.step_completed`
- `plate.error_occurred`
- `mover.transport_started`
- `device.processing_complete`

---

## Article X: Amendment Process

### Section 10.1: Proposing Amendments

Amendments to this Constitution may be proposed by any contributor. Proposals must include:
1. The specific article/section to amend
2. Rationale for the change
3. Impact analysis

### Section 10.2: Ratification

Amendments require explicit approval before being incorporated. Approved amendments are added with:
- Amendment number
- Date ratified
- Brief description

---

## Amendments

*No amendments yet.*

---

## Signatories

- **Imad Mansour** - Project Lead
- **Claude (Opus 4.5)** - AI Architecture Consultant

---

*This Constitution is a living document. It captures hard-won architectural insights and prevents regression to inferior patterns. Respect it.*
