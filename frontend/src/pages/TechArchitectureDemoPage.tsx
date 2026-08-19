/** LunaYield Tech Stack + Architecture + Safety + Demo Page - /tech Route */
import { useState } from 'react';
/** Tech Stack Section */
/** TECH STACK DATA */
const techStack = {
  frontend: [
    { name: 'React', category: 'UI', verified: true },
    { name: 'TypeScript', category: 'Language', verified: true },
    { name: 'Vite', category: 'Build Tool', verified: true },
    { name: 'TanStack Query', category: 'Data Fetching', verified: true },
    { name: 'Zustand', category: 'State Management', verified: true },
    { name: 'Recharts', category: 'Visualization', verified: true },
    { name: 'Tailwind CSS', category: 'Styling', verified: true },
    { name: 'Vitest', category: 'Testing', verified: true },
    { name: 'Playwright', category: 'E2E Testing', verified: true },
  ],
  backend: [
    { name: 'Python', category: 'Runtime', verified: true },
    { name: 'FastAPI', category: 'API Framework', verified: true },
    { name: 'Pydantic', category: 'Data Validation', verified: true },
    { name: 'SQLModel', category: 'ORM', verified: true },
    { name: 'SQLite', category: 'Database', verified: true },
    { name: 'WebSockets', category: 'Real-time', verified: true },
    { name: 'Pytest', category: 'Testing', verified: true },
    { name: 'Ruff', category: 'Linting', verified: true },
  ],
  workflow: [
    { name: 'IBM Bob', category: 'AI-assisted Workflow', verified: true },
    { name: 'Git/GitHub', category: 'Version Control', verified: true },
  ],
};

/** ARCHITECTURE SECTION */
const architecturalFlow = [
  { label: 'Operator', description: 'Human operator initiates mission actions via UI' },
  { label: 'React Frontend', description: 'UI layer renders state, captures input, relays to backend via HTTP/WebSocket' },
  { label: 'HTTP/WebSocket', description: 'REST APIs for state mutations; WebSocket for live telemetry events' },
  { label: 'FastAPI Backend', description: 'Authoritative service managing mission state transitions, planning, forecasting, anomaly detection, strategy generation, validation, and approval' },
  { label: 'Mission Service', description: 'Mission lifecycle management (IDLE → RUNNING → ANOMALY → PLANNING → AWAITING_APPROVAL → EXECUTING)' },
  { label: 'Planning Service', description: 'Deterministic 3-candidate plan generation (Phase 1) using RETURN_BATTERY_MIN_20PCT safety rule' },
  { label: 'Forecasting Service', description: 'Deterministic resource projection over configurable horizons (Phase 3)' },
  { label: 'Anomaly Service', description: 'Threshold-based detection on current + forecast state (Phase 3)' },
  { label: 'Strategy Service', description: 'Deterministic anomaly→strategy mapping with 10 templates (Phase 4)' },
  { label: 'Validation Service', description: 'Schema/structure/constraint validation (Phase 4/5) — structural checks only, not resource safety' },
  { label: 'Approval Service', description: 'Operator-triggered re-verification; re-runs validation at approval time; invalid strategies cannot be approved' },
  { label: 'Persistence Service', description: 'SQLite run lifecycle, snapshots, immutable audit trail (Phase 2)' },
];

/** SAFETY SECTION */
const safetyPoints = [
  { title: 'Backend Authoritative', detail: 'The frontend never calculates safety, never makes validation decisions, and never executes strategies. All safety decisions originate from the backend.' },
  { title: 'Frontend Does Not Calculate Safety', detail: 'Resource forecasts, anomaly detections, and strategy evaluations are UI displays only. The frontend presents backend-provided results without interpretation.' },
  { title: 'Phase 1 Plan Safety (RETURN_BATTERY_MIN_20PCT)', detail: 'Phase 1 candidate plans are verified against the RETURN_BATTERY_MIN_20PCT rule. The Aggressive Survey plan was rejected (measured 11.0% battery, threshold 20.0%) and displays SAFETY VIOLATIONS with measured/threshold values. Rejected plans are visible for auditability but non-actionable — no approve button is rendered.' },
  { title: 'Phase 4 Strategy Validation = Schema/Structure', detail: 'Phase 4 validation checks structural requirements: required fields non-empty, priority bounds 1–5, requires_operator_approval flag, valid affected_resources enum, recommended_actions in SUPPORTED_ACTIONS whitelist, source_anomalies with hyphen format, strategy_id format. These are constraint checks, not resource safety thresholds.' },
  { title: 'Invalid Strategies Cannot Be Approved', detail: 'The approve button is only rendered when backend validation returns VALID. If validation fails, the approve button is hidden and "CANNOT APPROVE" text is shown instead.' },
  { title: 'Approval Re-runs Deterministic Validation', detail: 'When an operator clicks APPROVE, the backend re-executes the full validation pipeline. This is a mandatory invariant — approval does not short-circuit.' },
  { title: 'Approval ≠ Execution', detail: 'The POST /api/strategies/{id}/approve endpoint records operator intent only. No "EXECUTE", "APPLY", or "RUN STRATEGY" controls exist in the UI. Approval updates audit trail but does not trigger plan execution.' },
  { title: 'No Strategy Execution Endpoint', detail: 'The backend does not expose an execution endpoint. The UI has no control over plan execution. Operator approval is the final step; the system remains in AWAITING_APPROVAL state indefinitely until manual reset.' },
];

/** DEMO SECTION */
const demoChecklist = [
  { step: '01', label: 'Start Mission', action: 'Click "START MISSION" button', note: 'Mission transitions from IDLE to RUNNING. Header badge shows RUNNING. Telemetry stream begins pulsing. Start button disables. Pause, Inject Anomaly, and Reset become enabled.', expanded: false },
  { step: '02', label: 'Observe Telemetry', action: 'Watch TelemetryPanel and ResourcePanel', note: 'Live telemetry samples appear with current battery %, storage %, temperature, comm window, and op time. Values update in real via WebSocket. Awaiting telemetry message clears after mission start.' }, { step: '03', label: 'Inject Anomaly', action: 'Click "INJECT ANOMALY" button', note: 'Mission status transitions to ANOMALY. Orange anomaly badge appears. Inject button disables. Generate Plans becomes enabled. Anomaly type and severity are displayed with provenance tracking.' }, { step: '04', label: 'Generate Candidate Plans', action: 'Click "GENERATE PLANS" button', note: 'Mission status becomes AWAITING_APPROVAL. Three candidate plan cards appear in PlanComparison: Minimal Survey (VALID, not recommended), Extended Survey (VALID, RECOMMENDED), Aggressive Survey (REJECTED with safety violations). Plan IDs: plan-a-001, plan-b-001, plan-c-001.', expanded: false }, { step: '05', label: 'Inspect Rejected Plan', action: 'Select Aggressive Survey plan card', note: 'Plan shows REJECTED status badge, SAFETY VIOLATIONS tag, and detailed violation: "[RETURN_BATTERY_MIN_20PCT] Predicted return battery 11.0% is below minimum 20.0% (measured: 11.0, threshold: 20.0)". Approve button is NOT visible. Text reads "REJECTED - CANNOT APPROVE".', expanded: false }, { step: '06', label: 'View Resource Forecast', action: 'Use ForecastPanel horizon selector', note: 'Change horizon via the selector (10 min / 30 min / 1 hour / 2 hours / 4 hours / 8 hours). ForecastPoints update accordingly. Changing horizon in ForecastPanel automatically updates AnomalyPanel (shared horizon). Battery forecast color coding: green >30%, yellow 15-30%, red <15%.', expanded: false }, { step: '07', label: 'Inspect Detected Anomalies', action: 'View AnomalyPanel', note: 'Displays detected anomalies with severity badges (info/warning/critical). Anomalies tagged with is_forecast and forecast_seconds_ahead if derived from projection. "NOMINAL" displayed if no anomalies detected. Resource labels show which resource triggered each anomaly.', expanded: false }, { step: '08', label: 'Review Strategies', action: 'View StrategyPanel', note: 'Strategy cards appear with priority badges (PRIORITY 1-red through PRIORITY 5-blue/gray). Each strategy shows title, rationale, affected resources (badges), recommended actions list, and source anomaly IDs. Cards sorted by priority ascending (PRIORITY 1 at top). Strategy generation is deterministic from detected anomalies at current horizon.', expanded: false }, { step: '09', label: 'Validate Strategy', action: 'Inspect individual strategy validation badge', note: 'Each strategy shows a validation badge: VALID (green) or INVALID (red). INVALID strategies show structured rejection reasons below the badge. Validation checks: required fields, priority bounds, action whitelist, resource enums, source_anomaly format, strategy_id format. The frontend never makes these judgments — all validation is backend-authoritative.', expanded: false }, { step: '10', label: 'Approve Valid Strategy', action: 'Click APPROVE STRATEGY button on a VALID strategy', note: 'Status changes to "APPROVAL: APPROVED" with green badge. Strategy card updates to show APPROVED status. Audit trail records strategy.approved event. Approve button is removed and replaced with "PLAN APPROVED" text. This is approval only — no execution occurs.', expanded: false }, { step: '11', label: 'Confirm Approval ≠ Execution', action: 'Observe system state after approval', note: 'Mission remains in AWAITING_APPROVAL state (or transitions based on backend logic). No "EXECUTE" or "RUN STRATEGY" button exists. The approve button does not reappear. Audit trail shows the approval event. The operator retains full decision authority. To reset and restart, click RESET MISSION.', expanded: false },
];

export function TechArchitectureDemoPage() {
  const [activeSection, setActiveSection] = useState<'tech' | 'architecture' | 'safety' | 'demo'>('tech');

  return (
    <div className="min-h-screen text-white">
      <section className="page-section px-4 pb-6 pt-8 md:px-6 lg:px-8">
        <div className="presentation-hero-frame">
          <div className="presentation-hero-body flex flex-col items-center text-center">
            <div className="section-kicker mb-6 border-cyan-400/20 bg-cyan-400/10 text-cyan-200">
              Verified implementation notes
            </div>
            <h1 className="presentation-hero-title">
              Tech stack, architecture, safety, and demo flow
            </h1>
            <p className="presentation-hero-copy">
              This page stays aligned with the real repo: deterministic backend logic, backend-authoritative validation, and no implied execution controls.
            </p>
          </div>
        </div>
      </section>

      <div className="sticky top-16 z-20 border-b border-white/10 bg-slate-950/60 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8">
          <div className="tab-strip py-3">
            <button
              className={`
                shrink-0 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeSection === 'tech'
                    ? 'bg-white/10 text-cyan-200 border border-cyan-500/30 shadow-[0_0_25px_rgba(34,211,238,0.08)]'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              onClick={() => setActiveSection('tech')}
            >
              Tech Stack
            </button>
            <button
              className={`
                shrink-0 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeSection === 'architecture'
                    ? 'bg-white/10 text-cyan-200 border border-cyan-500/30 shadow-[0_0_25px_rgba(34,211,238,0.08)]'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              onClick={() => setActiveSection('architecture')}
            >
              Architecture
            </button>
            <button
              className={`
                shrink-0 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeSection === 'safety'
                    ? 'bg-white/10 text-cyan-200 border border-cyan-500/30 shadow-[0_0_25px_rgba(34,211,238,0.08)]'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              onClick={() => setActiveSection('safety')}
            >
              Safety
            </button>
            <button
              className={`
                shrink-0 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeSection === 'demo'
                    ? 'bg-white/10 text-cyan-200 border border-cyan-500/30 shadow-[0_0_25px_rgba(34,211,238,0.08)]'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              onClick={() => setActiveSection('demo')}
            >
              Demo
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-4 md:px-6 md:py-6 lg:px-8">
        {activeSection === 'tech' && <TechStackSection techStack={techStack} />}
        {activeSection === 'architecture' && <ArchitectureSection architectureFlow={architecturalFlow} />}
        {activeSection === 'safety' && <SafetySection safetyPoints={safetyPoints} />}
        {activeSection === 'demo' && <DemoSection demoChecklist={demoChecklist} />}
      </div>
    </div>
  );
}

/** Tech Stack Section */
function TechStackSection({ techStack }: { techStack: typeof techStack }) {
  return (
    <section className="page-section py-20 md:py-28">
      <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-white mb-4">
            Tech Stack
          </h2>

          <p className="text-gray-400 text-lg max-w-2xl mx-auto leading-relaxed">
            Verified technologies powering LunaYield Mission Lab.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
          {/* Frontend */}
          <div className="glass-panel surface-hover rounded-2xl p-6 text-center">

            <h3 className="text-xl font-semibold text-white mb-4">
              Frontend
            </h3>

            <div className="flex flex-wrap justify-center gap-2">
              {techStack.frontend.map((t) => (
                <span
                  key={t.name}
                  className="bg-gray-800 px-2 py-1 rounded text-cyan-300 text-xs font-mono"
                >
                  {t.name}
                </span>
              ))}
            </div>
          </div>

          {/* Backend */}
          <div className="glass-panel surface-hover rounded-2xl p-6 text-center hover:border-amber-500/30">
            <h3 className="text-xl font-semibold text-white mb-4">
              Backend
            </h3>

            <div className="flex flex-wrap justify-center gap-2">
              {techStack.backend.map((t) => (
                <span
                  key={t.name}
                  className="bg-gray-800 px-2 py-1 rounded text-amber-300 text-xs font-mono"
                >
                  {t.name}
                </span>
              ))}
            </div>
          </div>

          {/* Workflow */}
          <div className="glass-panel surface-hover rounded-2xl p-6 text-center">
            <h3 className="text-xl font-semibold text-white mb-4">
              Workflow
            </h3>

            <div className="flex flex-wrap justify-center gap-2">
              {techStack.workflow.map((t) => (
                <span
                  key={t.name}
                  className="bg-gray-800 px-2 py-1 rounded text-cyan-300 text-xs font-mono"
                >
                  {t.name}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/** Architecture Section */
function ArchitectureSection({ architectureFlow }: { architectureFlow: typeof architecturalFlow }) {
  return (
    <section className="page-section py-20 md:py-28">
      <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-white mb-4">
            Architecture
          </h2>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto leading-relaxed">
            LunaYield system architecture reflecting the real implementation.
          </p>
        </div>

        <div className="space-y-6">
          {architectureFlow.map((node, i) => (
            <div
              key={i}
              className="glass-panel surface-hover relative rounded-2xl p-4"
            >
              <div className={`flex flex-col gap-3 sm:flex-row sm:items-start ${
                i % 2 === 0 ? 'sm:justify-start' : 'sm:justify-end'
              }`}>
                <div className={`relative w-12 h-12 rounded-2xl flex items-center justify-center ${
                  i % 2 === 0 ? 'bg-gray-800/50 border border-gray-700' : 'bg-cyan-500/20 border border-cyan-500/50'
                } shrink-0`}>
                  <span className="text-cyan-400" aria-hidden="true">{i + 1}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-semibold text-white mb-1">{node.label}</h3>
                  <p className="text-gray-400 text-sm leading-relaxed">{node.description}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Connection arrows description */}
        <div className="glass-panel mt-8 rounded-xl p-4 text-sm">
          <p className="mb-3 text-gray-400">
            Flow: Operator → React Frontend → HTTP/WebSocket → FastAPI Backend
          </p>

          <div className="flex flex-wrap gap-2">
            {[
              'Mission Service',
              'Planning Service',
              'Forecasting Service',
              'Anomaly Service',
              'Strategy Service',
              'Validation Service',
              'Approval Service',
              'Persistence Service (SQLite)',
            ].map((service) => (
              <span
                key={service}
                className="rounded bg-gray-800 px-2 py-1 text-xs font-mono text-cyan-300"
              >
                {service}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

/** Safety Section */
function SafetySection({ safetyPoints }: { safetyPoints: typeof safetyPoints }) {
  return (
    <section className="page-section py-20 md:py-28">
      <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-white mb-4">
            Safety Architecture
          </h2>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto leading-relaxed">
            Backend authoritative. Frontend display only.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
          {safetyPoints.map((point, i) => (
            <div
              key={i}
              className="glass-panel surface-hover group rounded-2xl p-6"
            >
              <div className={`flex items-start gap-3 mb-4`}>
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  i % 2 === 0 ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-300'
                } text-sm font-medium`}>
                  {point.title.split(' ')[0]}
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-semibold text-white mb-1">{point.title}</h4>
                  <p className="text-gray-400 text-sm leading-relaxed">{point.detail}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/** Demo Section */
function DemoSection({ demoChecklist }: { demoChecklist: typeof demoChecklist }) {
  return (
    <section className="page-section py-20 md:py-28">
      <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-white mb-4">
            Operator Walkthrough
          </h2>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto leading-relaxed">
            Eleven-step complete flow from mission start through approval confirmation.
          </p>
        </div>

        <div className="space-y-4">
          {demoChecklist.map((item) => (
            <details
              key={item.step}
              className="glass-panel surface-hover group rounded-2xl p-6 transition-all duration-300 hover:border-cyan-500/30 hover:bg-cyan-500/5"
              open={item.expanded}
              style={{ cursor: 'pointer' }}
            >
              <summary className={`
                flex items-start gap-3 cursor-pointer text-white
                transition-all duration-200
                ${item.expanded ? 'text-cyan-300' : 'text-gray-400'}
              `}>
                <span className={`w-8 h-8 rounded bg-cyan-500/20 flex items-center justify-center text-cyan-400 font-mono flex-shrink-0 ${item.expanded ? 'scale-110' : ''}`}>
                  {item.step}
                </span>
                <div className="min-w-0">
                  <h4 className="font-medium">{item.label}</h4>
                  <p className="max-w-full text-xs text-gray-500 sm:max-w-xs sm:truncate">{item.action}</p>
                </div>
              </summary>
              <div className={`
                mt-4 text-gray-400 text-sm leading-relaxed
                ${item.expanded ? '' : 'hidden'}
              `}>
                <p className="font-medium">{item.note}</p>
              </div>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
