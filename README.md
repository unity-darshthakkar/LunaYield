# LunaYield Mission Lab

**IBM Space Exploration Hackathon** — Lunar rover operations and mission-planning platform.

A rover has limited battery, storage, communication windows, and multiple science targets. The system forecasts resource risks, detects anomalies, generates alternative mission strategies, validates them against safety rules, and requires human operator approval — with backend-authoritative deterministic safety guarantees.

---

## Implemented Capabilities: Phases 1–5 ✅ COMPLETE

### Phase 1 — Vertical MVP
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

### Phase 2 — Persistence & Recovery
| Capability | Status |
|------------|--------|
| SQLite persistence with SQLModel ORM | ✅ |
| Mission run lifecycle: create → snapshot → complete/archive | ✅ |
| Run snapshots (full state at each milestone) | ✅ |
| Immutable audit trail persisted per run | ✅ |
| Pagination support for run/snapshot/audit listings | ✅ |
| Graceful shutdown with final snapshot | ✅ |
| Startup restoration from last snapshot | ✅ |
| SQLModel metadata table initialization (no Alembic) | ✅ |

### Phase 3 — Forecasting & Anomaly Detection
| Capability | Status |
|------------|--------|
| Deterministic resource forecasting (battery, storage, temperature, comm, op time) | ✅ |
| Configurable forecast horizon (10 min – 8 hours) | ✅ |
| Forecast interval control with validation | ✅ |
| Deterministic anomaly detection on current/forecast resources | ✅ |
| Anomaly classification: resource_depletion / thermal / comm / performance | ✅ |
| Anomaly severity levels: info / warning / critical | ✅ |
| Provenance tracking: current-state vs forecast-derived | ✅ |
| Forecast time-ahead for predicted anomalies | ✅ |
| Forecast + anomaly sharing same horizon in UI | ✅ |
| **No LLM/ML model integration** — pure deterministic calculations | ✅ |

### Phase 4 — Strategy Generation, Validation & Approval
| Capability | Status |
|------------|--------|
| Deterministic strategy generation from anomalies (Conserve/Monitor/Offload/Schedule/Thermal/Comms/Expedite/Optimize) | ✅ |
| Multiple candidate strategies per request (one per unique anomaly resource+severity) | ✅ |
| Structured strategy IDs, titles, rationales, priorities, actions, source anomalies | ✅ |
| Deterministic prioritization and deduplication | ✅ |
| Pydantic schema validation for all generated strategies | ✅ |
| StrategyValidationService: validates schema, required fields, priority bounds, action whitelist, resource consistency, approval requirement | ✅ |
| Invalid strategies rejected with structured reasons | ✅ |
| Forecast-aware strategy generation (optional) | ✅ |
| Explicit operator approval via `POST /api/strategies/{strategy_id}/approve` | ✅ |
| Mandatory re-validation at approval time | ✅ |
| Approval does not execute or mutate resources | ✅ |
| **No LLM/Granite model integration** — deterministic rule-based generation | ✅ |

### Phase 5 — Operator UX & Integration
| Capability | Status |
|------------|--------|
| Forecast horizon selector shared across forecast/anomaly/strategy | ✅ |
| Forecast panel with color-coded resource timeline | ✅ |
| Anomaly panel with severity badges, resource labels, provenance | ✅ |
| NOMINAL state handling (no false positives) | ✅ |
| Panel independence (one failing doesn't crash others) | ✅ |
| Strategy panel with priority-sorted cards (Priority 1–5) | ✅ |
| Strategy title, rationale, affected resources, recommended actions | ✅ |
| Source anomalies with forecast provenance badges | ✅ |
| Per-strategy validation states: VALID, INVALID, VALIDATION PENDING, AWAITING VALIDATION, VALIDATION UNAVAILABLE | ✅ |
| Rejection reasons displayed for invalid strategies | ✅ |
| **Fail-closed approval**: approve button only when backend returns explicit `is_valid=true` | ✅ |
| Missing/loading/unavailable/incomplete validation → no approval controls | ✅ |
| Terminal approval states: APPROVED, REJECTED, VALIDATION_FAILED, NOT_FOUND, ALREADY_APPROVED | ✅ |
| **No execution controls** — approval records intent only | ✅ |
| 8 integration regression tests | ✅ |

---

## Architecture

```
LunaYield Mission Lab
├── backend/        # FastAPI, WebSockets, domain services, safety, telemetry, persistence
├── frontend/       # React, Vite, TypeScript, Tailwind, TanStack Query
├── docs/           # Architecture, demo instructions, Bob evidence log
├── datasets/       # Small processed demo assets only
└── preprocessing/  # Offline-only data prep (never in deployed backend)
```

### Backend Services
- **MissionService** — Authoritative mission state & transitions
- **PlanningService** — Deterministic 3-plan generation (Phase 1)
- **PersistenceService** — SQLite/SQLModel run lifecycle, snapshots, audit
- **ForecastingService** — Deterministic resource forecasting (Phase 3)
- **AnomalyService** — Deterministic anomaly detection on current/forecast state (Phase 3)
- **StrategyService** — Deterministic anomaly→strategy mapping (Phase 4)
- **ValidationService** — Strategy schema/structure validation (Phase 4)
- **ApprovalService** — Explicit operator approval with re-validation (Phase 4/5)
- **SafetyVerifier** — Pure Python safety module (`RETURN_BATTERY_MIN_20PCT`)
- **TelemetryService** — Deterministic tick-based samples
- **WSConnectionManager** — Broadcast to all connected clients
- **Routers**: `/api/mission`, `/api/plans`, `/api/forecast`, `/api/anomalies`, `/api/strategies`, `/api/strategies/validate`, `/api/strategies/{id}/approve`, `/api/history`, `/api/ws/mission`

### Frontend Components
- **MissionControls** — State-aware operator buttons
- **PlanComparison** — Candidate plans with safety visibility (Phase 1)
- **ForecastPanel** — Resource forecast with horizon selector (Phase 5)
- **AnomalyPanel** — Anomaly list with severity/type (Phase 5)
- **StrategyPanel** — Strategy cards with validation + approval (Phase 5)
- **TelemetryPanel** — Live WebSocket telemetry
- **RoutePanel** — Active route timeline
- **ResourcePanel** — Current resource levels
- **AuditPanel** — Newest-first immutable event log
- **useMissionSocket** — WS with reconnection/backoff
- **useMission hooks** — TanStack Query for all API calls

**Tech Stack**
- Backend: Python 3.12 · FastAPI · Pydantic · SQLModel/SQLite · FastAPI WebSockets
- Frontend: React 18 · TypeScript · Vite · Tailwind CSS · TanStack Query · Zustand
- AI/ML: **None in deployed backend** — all forecasting/anomaly/strategy are deterministic
- Testing: Pytest (backend: 318 tests) · Vitest (frontend: 182 tests) · Playwright (E2E)

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

### Run the Full Demo (Phases 1–5)
1. Start backend (Terminal 1)
2. Start frontend (Terminal 2)
3. Open `http://127.0.0.1:5173`
4. Follow [Full Demo Walkthrough](docs/full-demo-walkthrough.md)

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
- **LLM/AI never mutates state** — no LLM in deployed backend; all forecasting/anomaly/strategy are deterministic
- **SafetyVerifier** is a pure Python module, separate from any future model reasoning
- **Rejected plans/strategies** are displayed for auditability with violations, but:
  - Never recommended
  - Never have an active approval button
  - Never executable
- **Approval re-runs** deterministic validation independently
- **Single Phase 1 safety rule** enforced on candidate plans:
  - `RETURN_BATTERY_MIN_20PCT` — predicted return battery ≥ 20%
- **Phase 4 strategy validation** enforces schema/structure rules (required fields, priority bounds, action whitelist, resource consistency, approval requirement) — **NOT resource safety thresholds**

---

## Demo Scenario

**Mission**: Shackleton Rim Survey — Alpha (`luna-mission-001`)
- 5 waypoints: Base Camp → Crater A Rim → Ice Deposit Site → Ridge Observation Point → Base Camp (Return)
- Seed resources: 100% battery, 0% storage, -40°C, 2h comm window, 8h op time

**Phase 1 Candidate Plans (deterministic)**:
1. **Minimal Survey** — 34% return battery, 45 yield — VALID
2. **Extended Survey** — 42% return battery, 78 yield — VALID + **RECOMMENDED**
3. **Aggressive Survey** — 11% return battery, 92 yield — **REJECTED** (violates 20% minimum)

**Phases 3–4** extend this with:
- Deterministic forecasts showing resource evolution over selected horizon
- Deterministic anomaly detection on current and forecast state
- Deterministic strategy generation from anomalies (e.g., Battery CRITICAL → "Conserve Power")
- Strategy validation against schema/structure rules
- Operator approval of the highest-priority VALID strategy

---

## Development Phases (0–6)

| Phase | Focus |
|-------|-------|
| **0** | Project Foundation — architecture, safety rules, engineering constraints, agent guidance, development plan |
| **1** | Vertical MVP — deterministic mission lifecycle, telemetry, anomaly, 3-plan generation, safety, approval, UI |
| **2** | Persistence & Recovery — SQLite, run lifecycle, snapshots, audit, restoration, history APIs |
| **3** | Forecasting & Anomaly Detection — deterministic resource projection, anomaly detection, provenance |
| **4** | Strategy Generation, Validation & Approval — deterministic anomaly→strategy, schema validation, approval |
| **5** | Operator UX & Integration — Forecast/Anomaly/Strategy panels, shared horizon, fail-closed approval |
| **6** | Final Demo & Submission Polish — validation, documentation cleanup, truthfulness pass, demo readiness |

---

## IBM Bob Development Workflow

IBM Bob served as LunaYield's primary AI-assisted development environment and project-development tool. It was used to establish the repository architecture, engineering rules, safety constraints, development plan, phase structure, validation discipline, and submission workflow. Additional AI-assisted tooling was used during implementation and testing, while development remained guided by the architecture and safety constraints established through the Bob workflow.

[Bob Development Log](docs/bob-development-log.md) — High-level development provenance

---

## Documentation

- [Full Demo Walkthrough (Phases 1–5)](docs/full-demo-walkthrough.md) — Complete operator guide
- [Phase 1 Demo Walkthrough](docs/phase-1-demo.md) — Phase 1 only (legacy)
- [Bob Development Log](docs/bob-development-log.md) — Honest tool usage evidence
- [Submission Wording](docs/submission-wording.md) — Judge-facing submission
- [AGENTS.md](AGENTS.md) — Agent guidance and constraints

---

## License

IBM Space Exploration Hackathon project.
