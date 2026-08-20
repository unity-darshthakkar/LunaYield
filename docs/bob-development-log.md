# IBM Bob Development Log — LunaYield

## Role of IBM Bob

IBM Bob served as LunaYield's primary AI-assisted development environment and project-development tool. It was used to establish the repository architecture, engineering rules, safety constraints, development plan, phase structure, validation discipline, and submission workflow. Additional AI-assisted tooling was used during implementation and testing, while development remained guided by the architecture and safety constraints established through the Bob workflow.

---

## Phase 0 — Project Foundation

**Branch**: `phase-0-project-foundation`
**Bob Workflow**: `/init` and Plan mode

### Bob Contributions
- Inspected repository structure and Git state
- Created root `AGENTS.md` with:
  - Repository boundaries and responsibilities
  - Confirmed frontend/backend/testing/AI/optimization/safety architecture
  - Required MVP flow definition
  - Deterministic safety and LLM-boundary rules
  - Phase discipline, deferred features, explicit exclusions, commit hygiene
  - Corrected rejected-plan policy (invalid candidates visible for auditability, never recommended/approved/executed)
- Created Bob rules for Plan, Agent, and Ask modes (`.bob/rules-*/AGENTS.md`)

### Architectural Decisions Established
1. **Backend is authoritative** for mission state, validity, and approval
2. **Raw LLM output never mutates mission state** — must pass Pydantic validation
3. **Safety verification separate** from LLM reasoning (`SafetyVerifier` pure Python module)
4. **Large data preparation outside** deployed backend (`preprocessing/`)
5. **Invalid plans displayed as rejected** with violations for auditability — never actionable

### Validation
- Only agent-guidance files modified
- No application code generated
- No dependencies introduced
- UTF-8 encoding preserved

---

## Phase 1 — Vertical MVP

**Branch**: `phase-1-demo-skeleton`

### Summary
Built the complete vertical slice: deterministic mission engine with 3-plan generation, safety verification, telemetry streaming via WebSocket, and the Mission Control frontend with WebSocket reconnection.

### Key Deliverables
- **MissionService** state machine with audit trail
- **PlanningService**: 3 deterministic plans (Minimal/Extended/Aggressive Survey)
- **SafetyVerifier**: single Phase 1 rule `RETURN_BATTERY_MIN_20PCT`
- **TelemetryService**: deterministic tick samples
- **WSConnectionManager**: WebSocket broadcast
- **HTTP routers**: `/api/mission`, `/api/plans`, `/api/ws/mission`
- **Frontend**: React components (MissionControls, PlanComparison, PlanCard, TelemetryPanel, RoutePanel, ResourcePanel, AuditPanel, MissionHeader)
- **Hooks**: `useMission` (TanStack Query), `useMissionSocket` (WS reconnection)
- **Typed API client** with error handling

### Validation
| Suite | Tests | Status |
|-------|-------|--------|
| Backend (pytest) | 105 | ✅ Pass |
| Frontend (vitest) | 67 | ✅ Pass |
| E2E (Playwright) | 5 | ✅ Pass (historical Phase 1D) |
| Ruff check/format | — | ✅ Pass |
| git diff --check | — | ✅ Clean |

---

## Phase 2 — Persistence & Recovery

**Branches**: Persistence through integration regression

### Summary
Added durable SQLite persistence with SQLModel while keeping live mission state authoritative in memory. Implemented mission runs, snapshots at transitions, audit persistence, startup restoration, and read-only history APIs.

### Key Deliverables
- **SQLModel + SQLite**: `MissionRunRecord`, `MissionSnapshotRecord`, `AuditEventRecord`
- Repository layer with session injection
- Database init via `init_db(engine)` using `metadata.create_all` (no Alembic)
- New `MissionRunRecord` on startup, snapshots at transitions
- Reset = run boundary (end old, start new)
- `MissionPersistenceService` coordinates without owning state
- Read-only history API: runs, snapshots, audit with pagination
- Startup restoration from latest unfinished run (`ended_at is NULL`)
- Reconstruct audit history, reattach to same `MissionRunRecord`
- Conservatively normalize `AWAITING_APPROVAL` → `ANOMALY`
- Deterministic recovery for corrupt/invalid snapshots (`RESTORATION_FAILED`)
- Stricter snapshot validation (elapsed, resources, waypoints, status)
- Hardened audit reconstruction
- Tie-breaking by DB ID when `started_at` matches
- Failed restoration never partially mutates `MissionService`
- Validated offset pagination for run listings

### Validation (Final)
| Suite | Tests | Status |
|-------|-------|--------|
| Backend (pytest) | 195 | ✅ Pass |
| Ruff check/format | — | ✅ Pass |
| git diff --check | — | ✅ Clean |
| No Alembic | — | Confirmed absent |

---

## Phase 3 — Forecasting & Anomaly Detection

**Branches**: Forecasting foundation through integration hardening

### Summary
Implemented deterministic resource forecasting and deterministic anomaly detection — no LLM/ML models. Added configurable horizons, provenance tracking, and integrated anomaly detection on both current and forecast resources.

### Key Deliverables
- **ForecastingService**: deterministic resource forecasting (battery, storage, temperature, comm, op time)
- Configurable horizon (10 min – 8 hours) with interval validation
- Reads `MissionService`, no mutation
- **No LLM calls, no TTM, no Granite** — pure deterministic calculation
- **AnomalyService**: deterministic anomaly detection on current/forecast resources
- Types: `resource_depletion`, `thermal`, `comm`, `performance`
- Severities: `info`, `warning`, `critical`
- Provenance: current-state vs forecast-derived with `forecast_seconds_ahead`
- Precedence: higher severity wins; current-state beats equal-severity forecast
- `/api/forecast` and `/api/anomalies` endpoints with optional forecast integration
- **No LLM calls** — deterministic threshold checks
- Integration: healthy state, future warning/critical detection, precedence, exact threshold crossing, multi-resource forecast anomalies, deterministic ordering, idempotency

### Validation (Final)
| Suite | Tests | Status |
|-------|-------|--------|
| Backend (pytest) | 247 | ✅ Pass |
| Ruff check/format | — | ✅ Pass |
| git diff --check | — | ✅ Clean |

---

## Phase 4 — Strategy Generation, Validation & Approval

**Branches**: Strategy generation through pipeline integration

### Summary
Built deterministic anomaly-to-strategy generation, schema/structure validation, and explicit operator approval — all without LLM integration. Approval re-verifies validation and never executes or mutates resources.

### Key Deliverables
- **StrategyService**: deterministic anomaly→strategy mapping (10 anomaly types × 2 severities)
- Deterministic fallback (no LLM dependency)
- Structured IDs, titles, rationales, priorities (1–5), affected resources, actions, source anomalies
- Deterministic prioritization and deduplication
- All strategies require `requires_operator_approval=true`
- **No Granite, no LLM** — pure deterministic rule-based generation
- **ValidationService**: deterministic schema/structure validation
- Validates IDs, text fields, priority bounds, resources, actions, anomaly refs, approval requirement
- Action whitelist enforcement (`SUPPORTED_ACTIONS` set), structured rejection reasons
- **Validates strategy structure, NOT resource safety thresholds**
- **ApprovalService**: explicit operator-triggered approval
- Only strategies in current generated set considered
- Mandatory validation before approval (`ValidationService`)
- Invalid strategies cannot be approved
- In-memory approval state: first = `APPROVED`, repeat = `ALREADY_APPROVED`
- `POST /api/strategies/{strategy_id}/approve`
- Approval does NOT execute, mutate resources, or bypass validation
- Integration across generation → validation → approval
- Invalid strategies cannot reach approved state
- Approval requires membership in current strategy set
- **No execution endpoint exists**

### Validation (Final)
| Suite | Tests | Status |
|-------|-------|--------|
| Backend (pytest) | 318 | ✅ Pass |
| Ruff check/format | — | ✅ Pass |
| git diff --check | — | ✅ Clean |
| Quality scan | — | No skip/TODO/FIXME/placeholder |

---

## Phase 5 — Operator UX & Integration

**Branches**: Forecast/anomaly UI through integration hardening

### Summary
Built the complete operator UI: ForecastPanel, AnomalyPanel, StrategyPanel with shared forecast horizon, validation display, and fail-closed approval. Added integration regression tests verifying panel isolation, nominal states, and zero execution behavior.

### Key Deliverables
- **ForecastPanel**: horizon selector (10 min – 8 hrs), resource timeline, color coding, metadata, loading/error/empty states
- **AnomalyPanel**: severity, resource, value, threshold, reason, provenance, forecast time-ahead, NOMINAL state
- **StrategyPanel**: title, ID, priority, rationale, affected resources, recommended actions, source anomalies, validation states, approve button
- Shared horizon between forecast and anomaly queries
- **Validation**: frontend `useStrategyValidation` hook, approval mutation via `POST /api/strategies/{id}/approve`
- Per-strategy states: VALID, INVALID, VALIDATION PENDING, AWAITING VALIDATION, VALIDATION UNAVAILABLE
- Rejection reasons visible for invalid strategies
- **Fail-closed approval**: approval only on explicit backend `is_valid=true`
- Missing/loading/unavailable/incomplete validation → no approval controls
- Terminal states: APPROVED, REJECTED, VALIDATION_FAILED, NOT_FOUND, ALREADY_APPROVED
- Approval forwards active forecast context
- Successful approval invalidates strategy/validation queries
- **No execution behavior**, approval ≠ execution
- **Integration regression tests (8)**:
  - Shared horizon propagation
  - Panel failure isolation
  - Nominal/empty states
  - Zero execution behavior
- Fixed duplicate React keys in forecast rows

### Validation (Final)
| Suite | Tests | Status |
|-------|-------|--------|
| Frontend (vitest) | 182 | ✅ Pass |
| Test files | 12 | ✅ Pass |
| Phase 5 integration | 8 | ✅ Pass |
| Lint | — | ✅ Pass |
| Production build | — | ✅ Pass |
| git diff --check | — | ✅ Clean |
| toBeEmpty deprecation | 1 | Non-blocking (PlanComparison) |

---

## Phase 6 — Final Demo & Submission Polish

**Branch**: `phase-6-final-demo-submission-polish`

### Summary
Final validation pass, documentation truthfulness correction, and submission preparation. No product functionality added.

### Deliverables
- Full backend validation: 318 tests passed
- Full frontend validation: 182 tests passed
- Build/lint verification: all clean
- Documentation truthfulness pass: removed unsupported claims (Granite, TTM, OR-Tools, NetworkX, five safety rules, execution endpoint, etc.)
- README cleanup to 7-phase structure
- Judge walkthrough creation
- Submission wording preparation
- Bob development evidence cleanup
- Final demo readiness

### Validation Results (Phase 6)
| Layer | Tests | Pass | Warnings |
|-------|-------|------|----------|
| Backend (pytest) | 318 | 318 ✅ | 10 Starlette/httpx/HTTP_422 (non-blocking) |
| Frontend (vitest) | 182 | 182 ✅ | 1 toBeEmpty deprecation (non-blocking) |
| Frontend build | — | ✅ | — |
| Frontend lint | — | ✅ | — |
| Ruff check/format | — | ✅ | — |
| git diff --check | — | ✅ Clean | LF/CRLF warnings only (Windows) |

**Total tests (Phase 6)**: 500 (318 backend + 182 frontend)

> **Note**: Playwright E2E (5 tests) was run historically in Phase 1D, not during Phase 6 validation.

---

## Phase 6A — Presentation Site UI Polish

**Branch**: `presentation-site-ui-redesign`

### Summary
Applied a constrained frontend-only presentation polish pass to the public site and Mission Control shell. The work strengthened the space-themed atmosphere, depth, and hierarchy without changing backend behavior, route structure, safety logic, or truthfulness.

### Bob Contributions
- Reviewed the full repository structure before implementation, including backend truth constraints and frontend route/layout boundaries
- Interpreted the UI-polish prompt against actual implementation limits
- Added reusable presentation-shell styling primitives for cosmic backgrounds, glow layers, glass surfaces, and brand-consistent gradients
- Refined the Home, Problem & Solution, Tech & Demo, header, footer, and Mission Control wrapper presentation
- Preserved truthful claims around deterministic forecasting/anomaly detection/strategy generation, backend-authoritative validation, and approval ≠ execution

### Implementation Notes
- Added reusable frontend presentation components:
  - `BrandMark`
  - `PresentationBackdrop`
- Expanded `frontend/src/index.css` with reusable atmosphere/surface utilities and reduced-motion-safe animations
- Upgraded public layout shell to use shared background treatment
- Enhanced public navigation/footer styling and replaced placeholder footer links with real internal routes
- Strengthened page hero sections, card depth, visual separation, and tab polish across:
  - Home
  - Problem & Solution
  - Tech & Demo
- Applied only light shell framing around Mission Control; dashboard logic and controls remain untouched

### Validation
- Planned validation after implementation:
  - `npm run lint`
  - `npm run build`
  - `npm run test`

### Follow-up Refinements
- Standardized the top hero/text-box width across presentation pages so Home, Problem & Solution, and Tech share the same visual frame
- Integrated the cleaned LunaYield logo into the presentation shell for stronger brand authenticity
- Added a fixed navigation experience across the presentation site
- Improved Mission Control readability with roomier card spacing, broader panel layout, and more responsive wrapping for forecast/anomaly/strategy content

### Commit Hash
- Working tree state at log update: uncommitted local changes

---

## Safety Architecture — Constraints Established in Phase 0

| Constraint | Enforcement |
|------------|-------------|
| Backend authoritative for all safety | All phases verify backend re-verification |
| Frontend never calculates safety | Phase 5: fail-closed, `is_valid=true` required |
| LLM/AI never mutates state | **No LLM in deployed backend** — all deterministic |
| SafetyVerifier separate from LLM | Pure Python module, single rule: `RETURN_BATTERY_MIN_20PCT` |
| Rejected plans/strategies: visible, not actionable | Phase 1: no approve button; Phase 5: fail-closed |
| Approval re-runs deterministic validation | Phase 4/5: mandatory validation before approval |

---

## Development Principles Established Through Bob

- **Backend authoritative** — Frontend is display/control layer only
- **Deterministic safety** — No LLM/ML in deployed backend
- **Invalid plans remain visible but non-actionable** — Rejected for auditability only
- **Approval requires validation** — Mandatory re-verification at approval time
- **Approval ≠ Execution** — No execution endpoint or execution controls
- **Persistence does not replace live authority** — Database = history only
- **Fail-closed UI** — Missing/incomplete validation blocks approval
- **Test before merging phases** — Validation required at each phase boundary

---

## Supporting AI-Assisted Tools

Additional AI-assisted tooling, including FCC Claude with NVIDIA Nemotron models (Nemotron 3 Ultra 550B-A55B, Nemotron 3 Super 120B-A12B, Fable 5), supported implementation, testing, review, and documentation across Phases 1–5. All implementation work was guided by the architecture, safety constraints, and validation requirements established through the IBM Bob workflow.

---

## Commit History (Key Milestones)

```
771707d - Phase 0/1: Project foundation, AGENTS.md, backend scaffold
f978351 - Phase 1: Mission engine, planning, safety, telemetry, 105 tests
01bf6ab - Phase 1: Frontend integration, 67 tests
[Phase 1D] - E2E tests, bug fixes, phase-1-demo.md, README.md
[Phase 2] - Persistence, restoration, history API, 195 backend tests
[Phase 3] - Forecasting, anomaly detection, 247 backend tests
[Phase 4] - Strategy generation, validation, approval, 318 backend tests
[Phase 5] - Operator UI, 182 frontend tests, 8 integration tests
[Phase 6] - Documentation cleanup, truthfulness pass, submission prep
```

## Phase 6B - Mission Simulation Coherence Repairs

**Branch**: current final-demo/submission working tree

### Summary
Made the seeded rover simulation coherent for judges without redesigning the UI or moving mission logic into the frontend. The backend now owns route progression, science-linked storage accumulation, nominal completion, defensive battery anomaly transitions, approved recovery-route updates, and richer mission audit events.

### Key Deliverables
- Added backend-authoritative waypoint progress states: `COMPLETED`, `CURRENT`, `UPCOMING`, `SKIPPED`
- Seed route now initializes with progress metadata and launches from Base Camp into the first science leg
- Telemetry now mutates authoritative mission state every tick instead of emitting read-only derived samples
- Storage no longer grows continuously during travel; deterministic one-time science gains occur only at science waypoints
- Nominal route timing now completes in 296 seconds with final battery 26.0% and final storage 84.0%
- Critical battery depletion now transitions through the existing anomaly architecture before battery reaches 0%
- Mission now transitions into `COMPLETED`, stops progression, and preserves final route/resource state
- Approved recovery plans now update `active_route` with progress-aware plan waypoints and clear `anomaly_active`
- Added meaningful audit events for waypoint arrival, science collection, route updates, automatic anomalies, and mission completion
- Mission snapshots are now persisted during live telemetry progression so restoration preserves route progress
- RoutePanel now renders backend-owned waypoint status badges without redesigning the existing presentation
- WebSocket telemetry events now invalidate mission-state queries so the frontend refetches authoritative route/status changes

### Files Updated
- `backend/app/main.py`
- `backend/app/schemas.py`
- `backend/app/seed.py`
- `backend/app/services/mission.py`
- `backend/app/services/planning.py`
- `backend/app/services/telemetry.py`
- `backend/app/services/route_progress.py` (new)
- `backend/tests/test_approval.py`
- `backend/tests/test_mission_lifecycle.py`
- `backend/tests/test_persistence.py`
- `backend/tests/test_phase4d.py`
- `backend/tests/test_telemetry.py`
- `frontend/src/components/RoutePanel.tsx`
- `frontend/src/components/RoutePanel.test.tsx`
- `frontend/src/hooks/useMissionSocket.ts`
- `frontend/src/types/mission.ts`

### Validation
- Backend targeted regression batches: 321 tests passed across all backend test files
- Frontend Vitest: 184 tests passed
- Frontend lint: passed
- Frontend build: passed
- No backend safety-verification rules were weakened
- No frontend execution behavior was introduced

## Phase 6C - Mission Sync, Completion Semantics, and Judge-Facing Nominal Finish

**Branch**: current final-demo/submission working tree

### Summary
Tightened the final demo path without redesigning the UI. The frontend now refetches authoritative mission state on live telemetry updates, audit history stays current during mission progression, stale control errors are cleared when a new action cycle starts, the nominal science run ends at 100% planned collection without being mislabeled as an unsafe storage anomaly, and completed-state controls/readouts stay visually coherent.

### Key Deliverables
- Mission WebSocket telemetry updates now invalidate the authoritative mission-state query so route, resources, current state, and audit data stay synchronized
- Mission Control now derives route, audit, anomaly, resource, and approved-plan display from a single mission-state source instead of redundant hook reads
- Reset/start/successful actions clear stale control error banners without weakening real failure handling
- Nominal science storage gains now total exactly 100% across the three seeded science targets
- Storage anomaly semantics now suppress the false "storage full" anomaly only for the completed seeded nominal science target case; real unsafe storage behavior remains intact
- Resource and Mission Controls panels now render completed-state feedback more clearly without changing the frozen visual design
- Added focused frontend tests for socket-driven refetch, audit refresh visibility, stale error clearing, and completed-state control gating
- Added backend/frontend determinism safeguards for tests that need a frozen mission state while preserving the production telemetry loop

### Files Updated
- `backend/app/main.py`
- `backend/app/services/anomaly.py`
- `backend/app/services/route_progress.py`
- `backend/tests/test_phase3b.py`
- `backend/tests/test_phase3c.py`
- `backend/tests/test_phase4a.py`
- `backend/tests/test_telemetry.py`
- `frontend/src/components/AuditPanel.tsx`
- `frontend/src/components/AuditPanel.test.tsx`
- `frontend/src/components/MissionControlApp.tsx`
- `frontend/src/components/MissionControlApp.errors.test.tsx` (new)
- `frontend/src/components/MissionControlApp.sync.test.tsx` (new)
- `frontend/src/components/MissionControls.tsx`
- `frontend/src/components/MissionControls.test.tsx`
- `frontend/src/components/ResourcePanel.tsx`
- `frontend/src/hooks/useMissionSocket.ts`
- `frontend/src/hooks/useMissionSocket.test.tsx` (new)

### Validation
- Focused backend regressions:
  - `backend/tests/test_telemetry.py` + `backend/tests/test_phase3b.py`: 36 passed
  - `backend/tests/test_phase3c.py::TestForecastingAnomalyIntegration::test_repeated_identical_requests_produce_identical_results`: passed
  - `backend/tests/test_phase4a.py::TestStrategyGeneration::test_repeated_deterministic_behavior`: passed
- Full backend suite: 322 passed
- Full frontend Vitest: 190 passed
- Frontend lint: passed
- Frontend build: passed
- Playwright not rerun in this environment

## Phase 6D - Physical Battery Degradation for Recovery-Plan Tradeoffs

**Branch**: current final-demo/submission working tree

### Summary
Implemented the final mission-logic change for the judge-facing anomaly story. The manual anomaly is no longer cosmetic: it now applies a deterministic one-time battery degradation to backend-authoritative mission state, recovery-plan predicted return batteries are derived from the same route/timing model used by execution, and the approved Minimal / Extended plans now finish near their shown predictions while preserving the unchanged nominal mission path.

### Key Deliverables
- `inject_anomaly()` now applies a deterministic 5% immediate battery loss and records both `anomaly.injected` and `battery.degraded`
- Recovery-plan battery predictions now come from authoritative current battery plus remaining route duration, instead of hardcoded plan card values
- Route-duration logic now accounts for the Minimal direct-return path after skipping Ridge and the shorter Aggressive detour legs
- Runtime execution still uses the same authoritative telemetry loop; no frontend battery logic was added
- Minimal / Extended / Aggressive now tell a coherent tradeoff story around the seeded ~1 minute anomaly point:
  - Minimal: 30.0% predicted / 30.0% actual
  - Extended: 21.0% predicted / 21.0% actual
  - Aggressive: 10.5% predicted and rejected by `RETURN_BATTERY_MIN_20PCT`
- Added persistence and audit regression coverage for degraded anomaly state restoration

### Files Updated
- `backend/app/services/mission.py`
- `backend/app/services/planning.py`
- `backend/app/services/route_progress.py`
- `backend/app/services/telemetry.py`
- `backend/tests/test_approval.py`
- `backend/tests/test_audit.py`
- `backend/tests/test_mission_lifecycle.py`
- `backend/tests/test_phase2f.py`
- `backend/tests/test_planning.py`

### Validation
- Focused anomaly/runtime backend tests: 73 passed
- Full backend suite: 326 passed
- Frontend not rerun in this pass because no frontend code or API schema changed
- Playwright not run in this environment
