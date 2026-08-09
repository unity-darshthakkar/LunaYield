# LunaYield Phase 1 Demo — Operator Walkthrough

## What Phase 1 Implements

Phase 1 delivers a **complete vertical MVP** demonstrating deterministic mission operations for a lunar rover:

- **Mission lifecycle**: IDLE → RUNNING → ANOMALY → PLANNING → AWAITING_APPROVAL → EXECUTING → (RESET → IDLE)
- **Live telemetry**: Battery, storage, temperature, comm window, operational time — streamed via WebSocket
- **Anomaly injection**: Deterministic battery anomaly trigger
- **Candidate plan generation**: Exactly 3 deterministic plans with fixed properties
- **Safety verification**: `RETURN_BATTERY_MIN_20PCT` rule — rejected plans cannot be approved
- **Human-in-the-loop approval**: Operator approves exactly one VALID+RECOMMENDED plan
- **Route update**: Active route changes to approved plan after approval
- **Audit trail**: Immutable event log of all state transitions
- **WebSocket + HTTP hybrid**: Real-time updates + authoritative REST API
- **Full reset**: Deterministic return to seed state for repeatable demos

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                      LunaYield Mission Lab                       │
├─────────────────────────────────────────────────────────────────┤
│  Frontend (React + TypeScript + Vite + Tailwind)                │
│  ├── MissionControls – state-aware operator buttons              │
│  ├── PlanComparison – candidate plans with safety visibility     │
│  ├── TelemetryPanel – live WebSocket telemetry                   │
│  ├── RoutePanel – active route timeline                          │
│  ├── ResourcePanel – current resource levels                     │
│  ├── AuditPanel – newest-first event log                         │
│  └── useMissionSocket – WS with reconnection/backoff             │
├─────────────────────────────────────────────────────────────────┤
│  Backend (FastAPI + Python 3.12)                                 │
│  ├── MissionService – authoritative mission state & transitions  │
│  ├── PlanningService – deterministic 3-plan generation           │
│  ├── SafetyVerifier – RETURN_BATTERY_MIN_20PCT rule             │
│  ├── TelemetryService – deterministic tick-based samples         │
│  ├── WSConnectionManager – broadcast to all clients              │
│  └── Routers: /api/mission, /api/plans, /api/ws/mission         │
└─────────────────────────────────────────────────────────────────┘
```

**Safety Architecture**: Backend is **authoritative** for all safety decisions. The frontend **never** calculates safety. Rejected plans are displayed for auditability but **cannot** be recommended, approved, or executed.

---

## Quick Start

### Prerequisites
- Python 3.12+ with virtual environment
- Node.js 20+ / npm
- Playwright (installed via `npm ci` in frontend/)

### Backend
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Verify: `http://127.0.0.1:8000/api/health` → `{"status":"ok"}`

### Frontend
```powershell
cd frontend
npm run dev -- --host 127.0.0.1
```
App runs at `http://127.0.0.1:5173` (proxies `/api` → backend:8000, upgrades WS)

### Run E2E Tests
```powershell
# Terminal 1: Backend (must be running)
cd backend && .\.venv\Scripts\Activate.ps1 && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2: Frontend (optional - Playwright webServer starts it)
cd frontend && npm run dev -- --host 127.0.0.1

# Terminal 3: E2E
cd frontend && npx playwright test
```
> **Note**: If frontend is already running in Terminal 2, set `reuseExistingServer: true` in `playwright.config.ts` (default for non-CI).

---

## Demo Walkthrough (22 Steps)

| Step | Action | Expected State | Verification |
|------|--------|----------------|--------------|
| 1 | Load `http://127.0.0.1:5173` | **IDLE** | "CURRENT STATE: IDLE", Start enabled |
| 2 | Click **START MISSION** | **RUNNING** | Status RUNNING, telemetry appears |
| 3 | Wait ~2–4s | **RUNNING** | Battery < 100%, "LIVE TELEMETRY" pulsing |
| 4 | Click **INJECT ANOMALY** | **ANOMALY** | Orange anomaly badge, Generate Plans enabled |
| 5 | Click **GENERATE PLANS** | **AWAITING_APPROVAL** | 3 plan cards appear |
| 6 | Inspect **Minimal Survey** | VALID, not recommended | "34.0%" battery, "APPROVE PLAN" button |
| 7 | Inspect **Extended Survey** | VALID, **RECOMMENDED** | "42.0%" battery, yellow badge, "APPROVE (RECOMMENDED)" |
| 8 | Inspect **Aggressive Survey** | **REJECTED** | "11.0%" battery, red badge, violations listed |
| 9 | Verify Aggressive violation | Visible | `[RETURN_BATTERY_MIN_20PCT]` measured 11.0, threshold 20.0 |
| 10 | Verify Aggressive non-actionable | No approve button | "REJECTED - CANNOT APPROVE" |
| 11 | Click **Extended Survey** approve | **EXECUTING** | Status EXECUTING |
| 12 | Verify Extended = APPROVED | Green badge | "PLAN APPROVED" text |
| 13 | Verify active route updated | Matches Extended | Base → Crater A → Ice → Ridge → Base |
| 14 | Verify audit: `plan.approved` | Present | plan-b-001, Extended Survey |
| 15 | Click **RESET MISSION** | **IDLE** | Status IDLE |
| 16 | Verify plans cleared | No PlanComparison | "CANDIDATE PLANS" gone |
| 17 | Verify audit: `mission.reset` | Present | In audit trail |
| 18 | Verify telemetry idle | "Awaiting telemetry..." | No live data |
| 19 | **Repeat** → Same deterministic result | ✓ | 3× consecutive cycles |

---

## Expected States Table

| Mission Status | Enabled Buttons | Disabled Buttons | Telemetry |
|----------------|-----------------|------------------|-----------|
| IDLE | Start, Reset | Pause, Resume, Anomaly, Generate | Idle message |
| RUNNING | Pause, Anomaly, Reset | Start, Resume, Generate | Live |
| ANOMALY | Generate, Reset | Start, Pause, Resume, Anomaly | Live |
| PLANNING | Reset | All others | Live |
| AWAITING_APPROVAL | Reset | All others | Live |
| EXECUTING | Reset | All others | Live |

---

## Expected Candidate Plans

| Plan | Label | Battery at Return | Science Yield | Status | Recommended |
|------|-------|-------------------|---------------|--------|-------------|
| A | Minimal Survey | **34.0%** | 45.0 | VALID | No |
| B | Extended Survey | **42.0%** | 78.0 | VALID | **Yes** |
| C | Aggressive Survey | **11.0%** | 92.0 | REJECTED | No |

> **Deterministic**: These values are identical every run. Plan IDs: `plan-a-001`, `plan-b-001`, `plan-c-001`.

---

## Safety Rule Explanation

**Rule**: `RETURN_BATTERY_MIN_20PCT`
> *"Predicted return battery must be ≥ 20%"*

- **Minimal Survey**: 34.0% → ✅ PASS
- **Extended Survey**: 42.0% → ✅ PASS
- **Aggressive Survey**: 11.0% → ❌ FAIL (rejected)

**Enforcement**:
1. Plans generated → SafetyVerifier runs → violations attached
2. Rejected plans: `status=REJECTED`, `is_recommended=false`, violations visible
3. Approval endpoint **re-verifies independently** → rejects if unsafe
4. Rejected plans **never** get approve button in UI
5. Recommended flag set **only** on VALID plans by backend

---

## Reset Instructions

**Soft Reset (UI)**: Click **RESET MISSION** button — always enabled, clears all state.

**Hard Reset (API)**: `POST http://127.0.0.1:8000/api/mission/reset`

**Effects**:
- Mission → IDLE, elapsed=0, battery=100%, anomaly=false
- Candidate plans → []
- Active route → Original route
- Audit trail → Seed event + `mission.reset` event
- Telemetry tick counter → 0

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| "CONNECTION FAILED" on load | Backend not running | Start backend on port 8000 |
| WebSocket shows DISCONNECTED | Backend not reachable | Check backend running, no firewall |
| Telemetry never appears | Mission not RUNNING | Click START MISSION first |
| Generate Plans disabled | Not in ANOMALY state | Click INJECT ANOMALY from RUNNING |
| Aggressive Survey has approve button | Bug — should not happen | Report — safety invariant broken |
| Reset doesn't clear plans | Bug — should clear | Report — deterministic reset broken |
| Port 5173/8000 in use | Another process | `netstat -ano | findstr :5173` → kill PID |
| Playwright timeout | Servers not ready | Wait for "MISSION CONTROL" to render |

---

## Known Phase 1 Limitations

- **No persistence**: All state in-memory; restart loses history
- **No AI/ML**: Granite TTM, Granite reasoning, OR-Tools — all deferred
- **No 3D visualization**: Three.js/terrain — Phase 2+
- **Single rover**: No multi-rover coordination
- **Deterministic only**: No stochastic forecasting, no learned anomaly detection
- **No authentication**: Single-operator demo mode
- **No Docker/deployment**: Local dev only

---

## Running All Tests

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

# E2E (requires backend + frontend running)
cd frontend && npx playwright test
```

---

## Safety Architecture Note (for Judges)

> **Backend owns mission state.** The frontend is display-only for safety decisions.
> - LLM/AI output **never** mutates mission state (no LLM in Phase 1)
> - Every model response would pass Pydantic validation (Phase 2+)
> - Safety verification lives in `SafetyVerifier` — separate from any future LLM reasoning
> - Rejected plans are visible for **auditability**, not actionability
> - Approval **always** re-runs deterministic safety check