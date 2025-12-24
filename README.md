# Titan

**XPlanar Workflow Orchestration Platform**

*Part of the SaturnOne suite*

A distributed, actor-based system for orchestrating laboratory automation workflows on Beckhoff XPlanar magnetic levitation transport systems.

---

## Vision

Enable laboratory scientists and automation engineers to design, execute, and monitor complex multi-step workflows across multiple movers and devices—with real-time visibility and robust error handling.

## Architecture

Titan uses a **distributed actor model** where:

- **PlateActors** are autonomous agents that manage their own workflow journey
- **MoverActors** are transport resources (taxis) assigned on-demand
- **DeviceActors** are service providers (pipetters, incubators, washers)
- **Resource Pools** dispatch available resources without central control

> *"The plate is the customer. The mover is the taxi. The customer is always in charge of their itinerary."*

See [CONSTITUTION.md](docs/architecture/CONSTITUTION.md) for complete architectural principles.

## Features

### Workflow Designer
- Visual node-based workflow builder
- Drag-and-drop stations, devices, and actions
- Validation and simulation before execution

### Live Monitoring
- 2D deck visualization with real-time mover positions
- Plate-centric tracking (where is my sample?)
- Device status and queue visualization

### Execution Dashboard
- System health and throughput metrics
- Per-plate progress tracking
- Error handling with operator intervention

### Sample Tracking
- Worklist import (CSV, Excel)
- Barcode confirmation
- Complete audit trail
- LIMS integration hooks

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Nuxt 3, Vue 3, TypeScript, Vue Flow |
| Backend | Python, FastAPI, asyncio |
| Communication | REST API, WebSocket |
| Hardware | Beckhoff XPlanar (ADS protocol) |

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- pnpm
- uv (Python package manager)

### Installation

```bash
# Clone the repository
git clone https://github.com/Boticus-OG/Titan.git
cd Titan

# Backend setup
cd backend
uv sync

# Frontend setup
cd ../frontend
pnpm install
```

### Development

```bash
# Terminal 1: Backend
cd backend
uv run uvicorn src.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
pnpm dev
```

### Open in VS Code

```bash
code .
```

## Project Structure

```
Titan/
├── docs/                      # Documentation
│   ├── architecture/          # Architectural decisions
│   │   └── CONSTITUTION.md    # Governing principles
│   ├── api/                   # API documentation
│   └── guides/                # User and developer guides
├── frontend/                  # Nuxt 3 application
├── backend/                   # Python FastAPI backend
├── shared/                    # Shared types and constants
├── CLAUDE.md                  # AI assistant instructions
└── README.md                  # This file
```

## Documentation

- [Constitution](docs/architecture/CONSTITUTION.md) - Architectural principles and decisions
- [Actor Model](docs/architecture/actor-model.md) - Actor implementation details
- [UI/UX Concept](docs/architecture/ui-ux-concept.md) - Interface design

## Contributing

1. Read the [Constitution](docs/architecture/CONSTITUTION.md)
2. Understand the actor model before making changes
3. Follow the established patterns in CLAUDE.md
4. Write tests for new functionality

## License

Proprietary - SaturnOne / Titan

---

*Built with precision for laboratory automation.*
