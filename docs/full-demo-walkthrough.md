# LunaYield Full Demo Walkthrough — Phases 1–5

## Overview

This walkthrough demonstrates the complete LunaYield mission operations flow from **Phase 1 (Vertical MVP)** through **Phase 5 (Operator UX & Integration)**. The system showcases:

- **Phase 1**: Deterministic mission lifecycle, telemetry, anomaly injection, 3-plan generation, safety verification, human approval
- **Phase 2**: SQLite persistence, run snapshots, audit trail, graceful shutdown/resume
- **Phase 3**: Deterministic resource forecasting + deterministic anomaly detection
- **Phase 4**: Deterministic strategy generation from anomalies + schema validation + operator approval
- **Phase 5**: Operator UI for forecast/anomaly/strategy/validation with full integration

**Key**: No LLM/ML models in deployed backend. All forecasting, anomaly detection, and strategy generation are deterministic calculations.

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LunaYield Mission Lab                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  Frontend (React + TypeScript + Vite + Tailwind + TanStack Query)           │
│  ├── MissionControls       – State-aware operator buttons                    │
│  ├── TelemetryPanel        – Live WebSocket telemetry                        │
│  ├── ResourcePanel         – Current resource levels                         │
│  ├── RoutePanel            – Active route timeline                           │
│  ├── AuditPanel            – Newest-first immutable event log               │
│  ├── ForecastPanel         – Resource forecast + horizon selector (Phase 5) │
│  ├── AnomalyPanel          – Anomaly list with severity/type (Phase 5)      │
│  ├── StrategyPanel         – Strategy cards + validation + approval (Phase 5)│
│  └── useMissionSocket      – WS with reconnection/backoff                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Backend (FastAPI + Python 3.12 + SQLModel/SQLite)                          │
│  ├── MissionService          – Authoritative mission state & transitions    │
│  ├── PlanningService         – Deterministic 3-plan generation (Phase 1)    │
│  ├── PersistenceService      – Run lifecycle, snapshots, audit (Phase 2)    │
│  ├── ForecastingService      – Deterministic resource forecasting (Phase 3) │
│  ├── AnomalyService          – Deterministic anomaly detection (Phase 3)    │
│  ├── StrategyService         – Deterministic anomaly→strategy mapping (Phase 4)│
│  ├── ValidationService       – Strategy schema/structure validation (Phase 4)│
│  ├── ApprovalService         – Re-verification + approval (Phase 4/5)       │
│  ├── SafetyVerifier          – Pure Python safety (`RETURN_BATTERY_MIN_20PCT`)│
│  ├── TelemetryService        – Deterministic tick samples                   │
│  ├── WSConnectionManager     – Broadcast to all clients                     │
│  └── Routers: /api/mission, /api/plans, /api/forecast, /api/anomalies,      │
│      /api/strategies, /api/strategies/validate, /api/strategies/{id}/approve,│
│      /api/history, /api/ws/mission                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Safety Architecture**: Backend is **authoritative** for all safety decisions. The frontend **never** calculates safety. Rejected plans/strategies are displayed for auditability but **cannot** be recommended, approved, or executed. Approval **always** re-runs deterministic validation.

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

---

## Full Demo Walkthrough (30 Steps)

### Phase 1: Mission Start & Anomaly (Steps 1–10)

| Step | Action | Expected State | Verification |
|------|--------|----------------|--------------|
| 1 | Load `http://127.0.0.1:5173` | **IDLE** | "CURRENT STATE: IDLE", Start enabled |
| 2 | Click **START MISSION** | **RUNNING** | Status RUNNING, telemetry appears |
| 3 | Wait ~2–4s | **RUNNING** | Battery < 100%, "LIVE TELEMETRY" pulsing |
| 4 | Click **INJECT ANOMALY** | **ANOMALY** | Orange anomaly badge, Generate Plans enabled |
| 5 | Click **GENERATE PLANS** | **AWAITING_APPROVAL** | 3 plan cards appear in PlanComparison |
| 6 | Inspect **Minimal Survey** | VALID, not recommended | "34.0%" battery, "APPROVE PLAN" button |
| 7 | Inspect **Extended Survey** | VALID, **RECOMMENDED** | "42.0%" battery, yellow badge, "APPROVE (RECOMMENDED)" |
| 8 | Inspect **Aggressive Survey** | **REJECTED** | "11.0%" battery, red badge, violations listed |
| 9 | Verify Aggressive violation | Visible | `[RETURN_BATTERY_MIN_20PCT]` measured 11.0, threshold 20.0 |
| 10 | Verify Aggressive non-actionable | No approve button | "REJECTED - CANNOT APPROVE" |

### Phase 3: Deterministic Forecasting & Anomaly Detection (Steps 11–16)

| Step | Action | Expected State | Verification |
|------|--------|----------------|--------------|
| 11 | Observe **ForecastPanel** (top right) | Loaded | "RESOURCE FORECAST" header, horizon selector |
| 12 | Change horizon to **1 hour** (3600s) | Forecast refreshes | Points update, "Horizon: 1 hour" in meta |
| 13 | Observe forecast points | 4 sample points shown | T+0.25h, T+0.5h, T+0.75h, T+1.0h with BATT/STOR/TEMP/COMM/OPS |
| 14 | Verify color coding | Green/Yellow/Red | Battery >30% green, 15-30% yellow, <15% red |
| 15 | Observe **AnomalyPanel** (below forecast) | Loaded | "ANOMALY DETECTION" header |
| 16 | Verify anomaly state | Shows anomalies or "NOMINAL" | If anomalies: severity badges (info/warning/critical), resource labels |

> **Note**: Forecast and anomaly panels share the **same horizon selector**. Changing horizon in ForecastPanel updates AnomalyPanel automatically (Phase 5 integration test A).

### Phase 4: Deterministic Strategy Generation (Steps 17–22)

| Step | Action | Expected State | Verification |
|------|--------|----------------|--------------|
| 17 | Observe **StrategyPanel** (bottom right) | Loaded | "STRATEGY RECOMMENDATIONS" header |
| 18 | Verify horizon sync | Shows "3600s" | Strategy horizon matches Forecast/Anomaly |
| 19 | Wait for auto-generation (or refresh page after anomaly) | Strategies appear | 1+ strategy cards with priority badges |
| 20 | Inspect strategy types | Priority labels | PRIORITY 1 (red), PRIORITY 2 (yellow), PRIORITY 3-5 (blue/gray) |
| 21 | Expand strategy details | Rationale, actions, source anomalies | Shows recommended actions list, affected resources, source anomaly IDs |
| 22 | Verify sort order | Priority ascending | Highest priority (1) at top |

> **Phase 5 Integration**: StrategyPanel uses the **shared horizon** from ForecastPanel. Strategies are generated from anomalies detected at that horizon.

### Phase 5: Validation & Operator Approval (Steps 23–28)

| Step | Action | Expected State | Verification |
|------|--------|----------------|--------------|
| 23 | Observe validation header | "ALL VALID" or "VALIDATION FAILED" | Green badge if all valid, red if any invalid |
| 24 | On a strategy card, check validation badge | VALID (green) or INVALID (red) | INVALID shows rejection reasons below |
| 25 | If VALID: Click **APPROVE STRATEGY** | Button enabled | Blue button appears for explicitly valid strategies |
| 26 | If INVALID: Verify button disabled | No approve button | "CANNOT APPROVE - VALIDATION FAILED" or similar |
| 27 | On VALID strategy, click **APPROVE STRATEGY** | **APPROVED** green badge | Status changes to "APPROVAL: APPROVED" |
| 28 | Verify audit trail updated | New `strategy.approved` event | AuditPanel shows approval with strategy ID |

> **Critical Safety Invariant (Phase 4/5)**:
> - **Approval ≠ Execution** — No "EXECUTE", "APPLY", or "RUN STRATEGY" button exists
> - Re-running strategy validation on approval is **mandatory**
> - Invalid strategies **never** get an approve button
> - Frontend **never** makes safety/validation decisions

### Phase 2: Persistence Verification (Steps 29–30)

| Step | Action | Expected State | Verification |
|------|--------|----------------|--------------|
| 29 | Check run persisted | Backend DB has run | `GET /api/missions/{mission_id}/runs` shows completed run |
| 30 | Restart backend, reload frontend | State recovered | Mission resumes from last snapshot, audit intact |

---

## Expected States Table (Phase 1 Core)

| Mission Status | Enabled Buttons | Disabled Buttons | Telemetry |
|----------------|-----------------|------------------|-----------|
| IDLE | Start, Reset | Pause, Resume, Anomaly, Generate | Idle message |
| RUNNING | Pause, Anomaly, Reset | Start, Resume, Generate | Live |
| ANOMALY | Generate, Reset | Start, Pause, Resume, Anomaly | Live |
| PLANNING | Reset | All others | Live |
| AWAITING_APPROVAL | Reset | All others | Live |
| EXECUTING | Reset | All others | Live |

---

## Phase 1 Expected Candidate Plans

| Plan | Label | Battery at Return | Science Yield | Status | Recommended |
|------|-------|-------------------|---------------|--------|-------------|
| A | Minimal Survey | **34.0%** | 45.0 | VALID | No |
| B | Extended Survey | **42.0%** | 78.0 | VALID | **Yes** |
| C | Aggressive Survey | **11.0%** | 92.0 | REJECTED | No |

> **Deterministic**: These values are identical every run. Plan IDs: `plan-a-001`, `plan-b-001`, `plan-c-001`.

---

## Phase 3: Forecasting Details

### Horizons Available
| Value | Label | Use Case |
|-------|-------|----------|
| 600 | 10 min | Short-term ops |
| 1800 | 30 min | Standard ops |
| 3600 | 1 hour | **Default demo** |
| 7200 | 2 hours | Extended survey |
| 14400 | 4 hours | Long traverse |
| 28800 | 8 hours | Maximum horizon |

### Forecast Resources (per point)
- **Battery** (%): Green >30, Yellow 15-30, Red <15
- **Storage** (%): Green <80, Yellow 80-95, Red >95
- **Temperature** (°C): Green >-45, Yellow -45 to -50, Red <-50 (cold); Green <40, Yellow 40-50, Red >50 (hot)
- **Comm Window** (s): Green >900, Yellow 300-900, Red <300
- **Op Time** (s): Green >1800, Yellow 600-1800, Red <600

### Anomaly Types & Severities
| Type | Severity Levels | Trigger |
|------|-----------------|---------|
| resource_depletion (battery/storage) | info/warning/critical | Forecast breach of threshold |
| thermal | info/warning/critical | Temperature breach |
| comm | info/warning/critical | Comm window breach |
| performance | info/warning/critical | Op time breach |

**Provenance**: Each anomaly tagged `is_forecast` (true/false) and `forecast_seconds_ahead` if forecast-derived.

---

## Phase 4: Strategy Types (Deterministic Mapping from Anomalies)

| Anomaly Resource | Severity | Strategy Title | Priority | Example Actions |
|------------------|----------|----------------|----------|-----------------|
| BATTERY | CRITICAL | Conserve Power | 1 | Disable instruments, reduce comms, orient panels, safe mode |
| BATTERY | WARNING | Monitor Power | 2 | Reduce duty cycle, schedule recharge, monitor trend |
| STORAGE | CRITICAL | Offload Data | 1 | Prioritize downlink, compress, delete thumbnails, suspend collection |
| STORAGE | WARNING | Schedule Downlink | 2 | Schedule downlink, enable compression, archive, monitor growth |
| TEMPERATURE | CRITICAL | Thermal Protection | 1 | Thermal safe mode, orient for passive, disable heat instruments |
| TEMPERATURE | WARNING | Monitor Thermal | 2 | Reduce duty cycle, adjust orientation, enable active thermal |
| COMM_WINDOW | CRITICAL | Prioritize Comms | 1 | Transmit priority data first, send health telemetry, defer rest |
| COMM_WINDOW | WARNING | Plan Comms | 2 | Queue by priority, compress, verify ground station, monitor |
| OP_TIME | CRITICAL | Expedite Return | 1 | Abort science, direct return, disable non-essential, transmit final |
| OP_TIME | WARNING | Optimize Timeline | 2 | Reorder waypoints, reduce dwell, skip low-priority, verify margin |

**Strategy Card Fields**:
- Priority badge (1–5, color-coded)
- Title, rationale
- Affected resources (badges)
- Recommended actions (list)
- Source anomaly IDs (with `-f{seconds}` suffix for forecast-based)
- Validation status badge
- Approve button (only when explicitly VALID)

---

## Phase 5: Strategy Validation Rules (Schema/Structure)

| Check | Description |
|-------|-------------|
| Required fields | strategy_id, title, rationale non-empty |
| Priority range | 1–5 |
| requires_operator_approval | Must be `true` |
| affected_resources | Non-empty, valid AnomalyResource enums |
| recommended_actions | Non-empty, all in SUPPORTED_ACTIONS whitelist |
| source_anomalies | Non-empty, contain hyphen |
| strategy_id format | Must start with "strat-" |

**Note**: These are **structure/schema validations**, not resource safety thresholds. Resource safety (battery/thermal/comm/storage/time) is only enforced on Phase 1 candidate plans via `RETURN_BATTERY_MIN_20PCT` in SafetyVerifier.

---

## Reset Instructions

**Soft Reset (UI)**: Click **RESET MISSION** button — always enabled, clears all state.

**Hard Reset (API)**: `POST http://127.0.0.1:8000/api/mission/reset`

**Effects**:
- Mission → IDLE, elapsed=0, battery=100%, anomaly=false
- Candidate plans (Phase 1) → []
- Strategies/Validations (Phase 4/5) → []
- Active route → Original route
- Audit trail → Seed event + `mission.reset` event
- Telemetry tick counter → 0
- **Database run** → New run started on next mission start

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| "CONNECTION FAILED" on load | Backend not running | Start backend on port 8000 |
| WebSocket shows DISCONNECTED | Backend not reachable | Check backend running, no firewall |
| Telemetry never appears | Mission not RUNNING | Click START MISSION first |
| Forecast shows error | Invalid horizon/interval | Check query params: horizon 60-86400, interval 10-3600 |
| Anomaly panel empty | No forecast yet | Select horizon, wait for forecast |
| Generate Strategies missing | Not in ANOMALY state | Click INJECT ANOMALY from RUNNING |
| Strategy validation fails | Schema violation | Check rejection reasons, verify strategy structure |
| Aggressive Survey has approve button | Bug — should not happen | Report — safety invariant broken |
| Reset doesn't clear plans | Bug — should clear | Report — deterministic reset broken |
| Port 5173/8000 in use | Another process | `netstat -ano | findstr :5173` → kill PID |

---

## Running All Tests

```powershell
# Backend (318 tests)
cd backend
.\.venv\Scripts\Activate.ps1
python -m ruff check app tests
python -m ruff format --check app tests
python -m pytest -v

# Frontend (182 tests)
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
> - **No LLM/ML in deployed backend** — all forecasting, anomaly detection, and strategy generation are deterministic
> - Safety verification lives in `SafetyVerifier` — pure Python, single rule: `RETURN_BATTERY_MIN_20PCT`
> - Strategy validation checks schema/structure, not resource limits
> - Rejected plans/strategies are visible for **auditability**, not actionability
> - Approval **always** re-runs deterministic validation
> - **Five anomaly thresholds** exist (battery, thermal, comm, storage, op time) but are for detection, not plan safety
> - **Zero execution behavior** in UI — approval records intent only

---

## Demo Script for Judges (3-Minute Version)

1. **"Mission Start"** (30s): Load app → Start Mission → Watch telemetry → Inject Anomaly
2. **"Phase 1 Plans"** (30s): Generate Plans → Show 3 plans → Point out REJECTED Aggressive
3. **"Phase 3 Forecast"** (30s): Show ForecastPanel → Change horizon → Show AnomalyPanel
4. **"Phase 4 Strategies"** (30s): Show StrategyPanel → Show anomaly→strategy mapping → Show actions
5. **"Phase 5 Validation"** (30s): Validate → Show VALID/INVALID → Approve VALID
6. **"Safety Guarantee"** (30s): Show rejected plan has no approve button → Audit trail → Reset

**Total**: ~3 minutes for complete Phases 1-5 flow