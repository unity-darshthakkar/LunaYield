# LunaYield Mission Lab

**IBM Space Exploration Hackathon** — Lunar rover operations and mission-planning platform.

A rover has limited battery, storage, communication windows, and multiple science targets. The system forecasts resource risks, detects anomalies, generates alternative mission strategies, converts them into executable plans, deterministically rejects unsafe plans, and recommends the plan that returns the greatest scientific value — with mandatory human operator approval before execution.

---

## Current Capability: Phase 1 Vertical MVP ✅ IMPLEMENTED

| Capability | Status |
|------------|--------|
| Deterministic mission lifecycle (IDLE → RUNNING → ANOMALY → PLANNING → AWAITING_APPROVAL → EXECUTING) | ✅ |
| Live telemetry via WebSocket (battery, storage, temp, comm, op time) | ✅ |
| Deterministic anomaly injection (battery) | ✅ |
| 3 deterministic candidate plans with fixed properties | ✅ |
| Deterministic safety verification (`RETURN_BATTERY_MIN_20PCT`) | ✅ |
| Rejected plans visible but non-actionable | ✅ |
| Exactly one VALID+RECOMMENDED plan per scenario | ✅ |
| Human operator approval required | ✅ |
| Active route updates after approval | ✅ |
| Immutable audit trail | ✅ |
| Full deterministic reset for repeatable demos | ✅ |
| Frontend React/TypeScript/Tailwind with WebSocket reconnection | ✅ |
| Backend FastAPI/Python with authoritative state | ✅ |
| E2E Playwright test suite | ✅ |

---

## Planned (Future Phases) 📋 PLANNED

| Capability | Phase |
|------------|-------|
| SQLite persistence (SQLModel) | Phase 2 |
| IBM Granite TTM forecasting adapter | Phase 2 |
| IBM Granite structured strategy generation | Phase 2 |
| OR-Tools / NetworkX optimization | Phase 2 |
| Three.js / React Three Fiber lunar terrain | Phase 2 |
| Real NASA lunar datasets (DEM, slope, traversability) | Phase 2 |
| DINOv2 embeddings for science target ranking | Phase 2 |
| Docker / Cloud deployment | Phase 2 |
| Z3 formal verification | Phase 2+ |
| Multi-rover coordination | Phase 3 |
| Authentication / multi-user | Phase 3 |

> **Clear distinction**: Everything in "IMPLEMENTED" works today in the demo. Everything in "PLANNED" is explicitly deferred and not implemented.

---

## Architecture

```
LunaYield Mission Lab
├── backend/        # FastAPI, WebSockets, domain services, safety, telemetry
├── frontend/       # React, Vite, TypeScript, Tailwind, TanStack Query
├── docs/           # Architecture, demo instructions, Bob evidence log
├── datasets/       # Small processed demo assets only
└── preprocessing/  # Offline-only data prep (never in deployed backend)
```

**Tech Stack**
- Backend: Python 3.12 · FastAPI · Pydantic · SQLite (planned) · FastAPI WebSockets
- Frontend: React 18 · TypeScript · Vite · Tailwind CSS · Zustand · TanStack Query · Recharts
- Testing: Pytest (backend) · Vitest (frontend) · Playwright (E2E)

---

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 20+
- npm

### Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Health check: `http://127.0.0.1:8000/api/health`

### Frontend
```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```
App: `http://127.0.0.1:5173` (proxies `/api` → backend:8000, WebSocket upgraded)

### Run the Demo
1. Start backend (Terminal 1)
2. Start frontend (Terminal 2)
3. Open `http://127.0.0.1:5173`
4. Follow [Demo Walkthrough](docs/phase-1-demo.md#demo-walkthrough-22-steps)

### Run Tests
```powershell
# Backend
cd backend
.\.venv\Scripts\Activate.ps1
python -m ruff check app tests
python -m ruff format --check app tests
python -m pytest -v

# Frontend
cd ../frontend
npm run build
npm run lint
npm run test

# E2E (requires both servers running)
cd frontend && npx playwright test
```

---

## Safety Architecture

- **Backend is authoritative** for all mission state and plan validity
- **Frontend never calculates safety** — display only
- **LLM/AI never mutates state** — no LLM in Phase 1; Phase 2+ requires Pydantic validation + fallback
- **SafetyVerifier** is a pure Python module, separate from any future model reasoning
- **Rejected plans** are displayed for auditability with violations, but:
  - Never recommended
  - Never have an active approval button
  - Never executable
- **Approval re-runs** deterministic safety verification independently

---

## Demo Scenario

**Mission**: Shackleton Rim Survey — Alpha (`luna-mission-001`)
- 5 waypoints: Base Camp → Crater A Rim → Ice Deposit Site → Ridge Observation Point → Base Camp (Return)
- Seed resources: 100% battery, 0% storage, -40°C, 2h comm window, 8h op time

**Candidate Plans (deterministic)**:
1. **Minimal Survey** — 34% return battery, 45 yield — VALID
2. **Extended Survey** — 42% return battery, 78 yield — VALID + **RECOMMENDED**
3. **Aggressive Survey** — 11% return battery, 92 yield — **REJECTED** (violates 20% minimum)

---

## Documentation

- [Phase 1 Demo Walkthrough](docs/phase-1-demo.md) — Complete operator guide
- [Bob Development Log](docs/bob-development-log.md) — Honest tool usage evidence
- [AGENTS.md](AGENTS.md) — Agent guidance and constraints

---

## License

IBM Space Exploration Hackathon project.