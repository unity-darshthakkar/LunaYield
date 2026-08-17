# LunaYield Mission Lab — Hackathon Submission Wording

---

## Project Title

**LunaYield Mission Lab: Deterministic Lunar Rover Operations with Backend-Authoritative Safety**

---

## One-Sentence Pitch

A lunar rover mission-planning platform that combines deterministic resource forecasting, anomaly detection, and strategy generation with **backend-authoritative deterministic safety** — so operators get decision support while the backend prevents rejected plans and invalid strategies from being approved, while strategy approval remains separate from execution.

---

## Problem Statement

Lunar rover missions face a fundamental tension: **science yield vs. survival risk**. A rover has limited battery, storage, communication windows, and thermal margins. Operators must:
1. Forecast resource evolution over hours
2. Detect anomalies before they become critical
3. Generate alternative mission strategies
4. Verify every strategy against safety rules
5. Get human approval — **without ever letting automation mutate state directly**

Current tools are either fully manual (spreadsheets) or fully autonomous (black-box automation). Neither provides the **auditable, fail-closed safety** required for billion-dollar missions.

---

## Solution: LunaYield Mission Lab

LunaYield delivers a **complete vertical slice** of mission operations across 5 phases — **all deterministic, no LLM/ML in deployed backend**:

| Phase | Capability | Innovation |
|-------|------------|------------|
| **1** | Deterministic mission lifecycle, telemetry, 3-plan safety, human approval | Foundation with pure Python determinism |
| **2** | SQLite persistence, run snapshots, audit trail, graceful shutdown/resume | Durable history without compromising live authority |
| **3** | Deterministic forecasting + deterministic anomaly detection | Resource projection & threshold detection with provenance |
| **4** | Deterministic strategy generation from anomalies + schema validation + approval | Anomaly→strategy mapping with fail-closed operator approval |
| **5** | Operator UI: forecast → anomaly → strategy → validation → approval | Shared horizon, fail-closed approval, zero execution behavior |

**Core Safety Guarantee**: The backend **re-verifies every plan/strategy on approval**. Rejected plans/strategies are visible for auditability but **cannot** be approved or executed. The frontend **never** calculates safety.

---

## Key Technical Innovations

### 1. Fail-Closed Safety Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    SAFETY BOUNDARY                          │
├─────────────────────────────────────────────────────────────┤
│  Deterministic Generation → Schema Validation → Safety      │
│  Verifier (Pure Python) → Approval Service (Re-verification)│
│  → Audit Log                                                │
└─────────────────────────────────────────────────────────────┘
```
- **Zero LLM/ML in deployed backend** — all forecasting/anomaly/strategy are deterministic calculations
- **Single Phase 1 safety rule** enforced deterministically on candidate plans:
  - `RETURN_BATTERY_MIN_20PCT` — return battery ≥ 20%
- **Phase 4 strategy validation** enforces schema/structure rules (required fields, priority bounds, action whitelist, resource consistency, approval requirement) — **NOT resource safety thresholds**
- **Five anomaly detection thresholds** exist (battery, thermal, comm, storage, op time) for detection only, not plan safety

### 2. Deterministic Forecasting with Provenance
- Resource forecasting over 10 min – 8 hr horizons using deterministic consumption rates
- Battery drain, storage increase, temperature drift, comm/op time drain per tick
- Configurable horizon and interval with validation
- Anomaly detection on both current state and forecast projections
- **Provenance tracking**: Every anomaly tagged `is_forecast` + `forecast_seconds_ahead`

### 3. Deterministic Strategy Generation from Anomalies
- 10 anomaly resource×severity combinations → 10 strategy templates (Conserve/Monitor/Offload/Schedule/Thermal/Comms/Expedite/Optimize)
- Structured output: IDs, titles, rationales, priorities (1–5), affected resources, recommended actions, source anomalies
- Deterministic prioritization and deduplication (highest priority per resource set)
- All strategies require `requires_operator_approval=true`
- **No Granite, no LLM** — pure deterministic rule-based mapping

### 4. Shared Horizon Architecture (Phase 5)
Single forecast horizon selector propagates to:
- ForecastPanel (resource timeline)
- AnomalyPanel (detection window)
- StrategyPanel (generation context)
- Validation (re-verification context)
- Approval (forecast context forwarded)

**Result**: Operator changes horizon once → entire decision pipeline updates consistently.

### 5. Phase 2 Persistence Without Compromise
- Live mission state **always** in-memory (`MissionService` authoritative)
- Database = durable history only (runs, snapshots, audit)
- Startup restoration from latest snapshot with validation
- **Zero telemetry persistence** — keeps DB small, fast, deterministic
- SQLModel `metadata.create_all` for table init — **no Alembic migrations**

### 6. Approval ≠ Execution (Critical UX Distinction)
- Approve button records **operator intent only**
- Endpoint: `POST /api/strategies/{strategy_id}/approve`
- No "Execute", "Apply", "Run Strategy" controls exist anywhere
- Post-approval: strategy marked APPROVED, audit logged
- Safety/validation re-verification runs **again** at approval time

---

## Demo Scenario: Shackleton Rim Survey — Alpha

**Mission**: `luna-mission-001`
**Waypoints**: Base Camp → Crater A Rim → Ice Deposit → Ridge Observation → Base Camp
**Seed**: 100% battery, 0% storage, -40°C, 2h comm, 8h op time

### Phase 1 Plans (Deterministic)
| Plan | Return Battery | Yield | Status |
|------|----------------|-------|--------|
| Minimal Survey | 34% | 45 | VALID |
| **Extended Survey** | **42%** | **78** | **VALID + RECOMMENDED** |
| Aggressive Survey | 11% | 92 | **REJECTED** (violates 20% battery) |

### Phases 3–5 Flow
1. **Forecast** (1 hr horizon, deterministic): Battery trends to 38%, temp -35°C, comm 7200s
2. **Anomalies** (deterministic threshold checks): NOMINAL or detected anomalies with provenance
3. **Strategies** (deterministic anomaly→strategy): e.g., Battery CRITICAL → "Conserve Power" (Priority 1)
4. **Validation** (schema/structure): Checks ID format, required fields, priority 1–5, action whitelist, resource enums, approval requirement
5. **Approval**: Operator approves highest-priority VALID strategy → audit logged

---

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         LUNAYIELD MISSION LAB                               │
├────────────────────────────────────────────────────────────────────────────┤
│  FRONTEND (React 18 + TypeScript + Vite + Tailwind + TanStack Query)       │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────┐ ┌────────────────────┐  │
│  │MissionControls│ │TelemetryPanel│ │ResourcePanel│ │     AuditPanel     │  │
│  └─────────────┘ └──────────────┘ └─────────────┘ └────────────────────┘  │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────────┐ │
│  │  ForecastPanel  │ │  AnomalyPanel   │ │        StrategyPanel        │ │
│  │  (Phase 5)      │ │  (Phase 5)      │ │  (Phase 5)                  │ │
│  │  • Horizon sel. │ │  • Severity     │ │  • Priority badges (1-5)    │ │
│  │  • Color-coded  │ │  • Provenance   │ │  • Rationale + actions      │ │
│  │  • 4 sample pts │ │  • NOMINAL state│ │  • Validate → Approve       │ │
│  └─────────────────┘ └─────────────────┘ └─────────────────────────────┘ │
│  └─────────────────────── useMissionSocket (WS + reconnection) ──────────┘ │
├────────────────────────────────────────────────────────────────────────────┤
│  BACKEND (FastAPI + Python 3.12 + SQLModel/SQLite)                         │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│  │MissionSvc  │ │PlanningSvc │ │Persistence │ │Forecasting │ │ Anomaly  │ │
│  │(authority) │ │(3 plans P1)│ │(runs/snap) │ │(determinist)│ │ (thresh) │ │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └──────────┘ │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│  │ StrategySvc│ │Validation  │ │ Approval   │ │  Safety    │ │Telemetry│ │
│  │(anomaly→   │ │Service     │ │Service     │ │ Verifier   │ │ Service │ │
│  │ strategy)  │ │(schema chck)│ │(re-verify) │ │(20% bat)   │ │         │ │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └──────────┘ │
│  Routers: /mission /plans /forecast /anomalies /strategies                │
│           /strategies/validate /strategies/{id}/approve /history /ws      │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Test Results — Submission Ready

| Layer | Tests | Pass Rate | Notes |
|-------|-------|-----------|-------|
| **Backend (pytest)** | **318** | **100%** | 10 Starlette/httpx deprecation warnings (non-blocking) |
| **Frontend (vitest)** | **182** | **100%** | 1 toBeEmpty deprecation (non-blocking) |
| **Frontend build** | — | ✅ | 285 kB JS, 20 kB CSS |
| **Frontend lint** | — | ✅ | ESLint clean |
| **Backend lint/format** | — | ✅ | Ruff clean |
| **git diff --check** | — | ✅ Clean | LF/CRLF warnings only (Windows) |

**Total Phase 6 tests: 500 (318 backend + 182 frontend)**

> **Note**: Playwright E2E (5 tests) was run historically in Phase 1D. Not re-run in Phase 6.

---

## Judge Walkthrough (3 Minutes)

### Minute 0:30 — Mission Start & Anomaly (Phase 1)
1. Load `http://localhost:5173` → **IDLE** state
2. Click **START MISSION** → **RUNNING**, live telemetry streaming
3. Click **INJECT ANOMALY** → **ANOMALY** state, orange badge
4. Click **GENERATE PLANS** → **AWAITING_APPROVAL**, 3 plans appear

### Minute 1:30 — Safety Verification (Phase 1)
5. Point out **Minimal Survey** (34% battery, VALID)
6. Point out **Extended Survey** (42% battery, **RECOMMENDED**, yellow badge)
7. Point out **Aggressive Survey** (11% battery, **REJECTED**, red badge, violation listed)
8. **Critical**: Show Aggressive has **no approve button** — "REJECTED - CANNOT APPROVE"

### Minute 2:00 — Deterministic Forecasting & Anomalies (Phase 3)
9. Show **ForecastPanel** → change horizon to 1 hour → forecast refreshes
10. Show **AnomalyPanel** → shares same horizon, shows NOMINAL or anomalies with provenance

### Minute 2:30 — Deterministic Strategy Generation (Phase 4)
11. Show **StrategyPanel** → strategies generated from anomalies
12. Show **Priority 1** (red) for critical, **Priority 2** (yellow) for warning
13. Expand → shows rationale, recommended actions list, source anomaly IDs

### Minute 3:00 — Validation & Approval (Phase 5)
14. Click **VALIDATE** (or observe auto-validation) → shows **ALL VALID** or **VALIDATION FAILED**
15. On VALID strategy: Click **APPROVE STRATEGY** → **APPROVED** green badge, audit logs it
16. **Final point**: "No Execute button exists — `POST /api/strategies/{id}/approve` records intent, backend re-verified validation"

---

## Submission Checklist

- [x] **README.md** — Accurately describes all Phases 1–5 as implemented (no "planned" claims)
- [x] **docs/full-demo-walkthrough.md** — Complete 30-step operator guide (truthful capabilities)
- [x] **docs/phase-1-demo.md** — Phase 1 legacy walkthrough preserved
- [x] **docs/bob-development-log.md** — Cleaned, honest tool attribution (contemporaneous records preserved)
- [x] **docs/submission-wording.md** — This document
- [x] **All tests passing** (318 backend + 182 frontend)
- [x] **Lint/format clean** (Ruff, ESLint)
- [x] **No TODO/FIXME/placeholder** in test suites
- [x] **Safety invariants verified** in integration tests (Phase 5)

---

## Repository Links

- **GitHub**: `https://github.com/unity-darshthakkar/LunaYield` (or local path)
- **Branch**: `phase-6-final-demo-submission-polish` (current)
- **Main**: `master`

---

## Team & Credits

**Primary Development Tool**: IBM Bob (architecture, safety model, phased implementation, validation workflow, submission preparation)
**Implementation Support**: FCC Claude with NVIDIA Nemotron models for Phases 1–5 implementation and testing
**Attribution**: Documented in `docs/bob-development-log.md`

---

## License

IBM Space Exploration Hackathon project. All rights reserved per hackathon terms.
