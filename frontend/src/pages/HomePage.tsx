/** LunaYield Home Page - Public presentation */

import { NavLink } from 'react-router-dom';
import { useState } from 'react';
import { BrandMark } from '../components/presentation';

const workflowStages = [
  {
    id: 'mission-state',
    label: 'MISSION STATE',
    description: 'Deterministic lifecycle: IDLE → RUNNING → ANOMALY → PLANNING → AWAITING_APPROVAL → EXECUTING. Every transition audited.',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
      </svg>
    ),
  },
  {
    id: 'resource-forecast',
    label: 'RESOURCE FORECAST',
    description: 'Deterministic projection of battery, storage, temperature, comm window, and op time over 10 min – 8 hr horizons. Configurable interval.',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
      </svg>
    ),
  },
  {
    id: 'anomaly-detection',
    label: 'ANOMALY DETECTION',
    description: 'Threshold-based detection on current and forecast state. Types: resource_depletion, thermal, comm, performance. Severities: info/warning/critical. Provenance tracked.',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
  },
  {
    id: 'strategy-generation',
    label: 'STRATEGY GENERATION',
    description: 'Deterministic anomaly→strategy mapping (10 templates). Conserve/Monitor/Offload/Schedule/Thermal/Comms/Expedite/Optimize. Priorities 1–5. Deduplicated.',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
    ),
  },
  {
    id: 'validation',
    label: 'VALIDATION',
    description: 'Schema/structure validation: required fields, priority bounds (1–5), action whitelist, resource enums, approval requirement. Invalid strategies rejected with reasons.',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    id: 'approval',
    label: 'OPERATOR APPROVAL',
    description: 'Explicit operator-triggered via POST /api/strategies/{id}/approve. Re-runs validation. Invalid strategies cannot be approved. Approval ≠ execution. Audit logged.',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
    ),
  },
];

const whyCards = [
  {
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
      </svg>
    ),
    title: 'Predict resource risks before they become critical',
    description: 'Deterministic forecasting projects all five mission resources over configurable horizons. Anomaly detection runs on both current state and projected future, with full provenance tracking so operators know exactly what triggered each alert.',
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
    title: 'Preserve human decision authority',
    description: 'Every strategy requires explicit operator approval. The backend re-verifies validation at approval time. Rejected plans and invalid strategies are visible for auditability but have no actionable approval controls. No autonomous execution exists.',
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    title: 'Maintain auditable mission history',
    description: 'SQLite persistence captures every mission run, state snapshot at transitions, and immutable audit trail. Graceful shutdown preserves final state. Startup restores from last snapshot with validation. History API provides paginated access to runs, snapshots, and audit events.',
  },
];

export function HomePage() {
  const [activeStage, setActiveStage] = useState<string | null>(null);

  return (
    <div className="min-h-screen">
      {/* HERO */}
      <section className="page-section relative flex min-h-[90vh] items-center justify-center overflow-hidden px-4 py-8 md:px-6 lg:px-8">
        <div className="presentation-hero-frame relative">
          <div
            className="pointer-events-none absolute inset-y-0 right-0 hidden w-[42%] lg:block"
            aria-hidden="true"
          >
            <div className="absolute inset-y-10 right-10 rounded-[2rem] border border-white/10 bg-gradient-to-b from-violet-500/18 via-slate-950/15 to-cyan-400/12 shadow-[0_30px_70px_rgba(34,211,238,0.12)]" />
            <div className="absolute right-20 top-16 h-24 w-24 rounded-full border border-cyan-300/35 bg-cyan-300/10 shadow-[0_0_40px_rgba(34,211,238,0.22)]" />
            <div className="absolute right-28 top-24 h-12 w-12 rounded-full border border-white/30 bg-white/90" />
            <div className="absolute bottom-24 left-12 h-40 w-40 rounded-full border border-violet-400/20 bg-violet-500/10 blur-[1px]" />
            <div className="absolute bottom-14 left-0 right-10 h-px bg-gradient-to-r from-transparent via-cyan-400/40 to-transparent" />
            <div className="absolute bottom-12 left-6 right-14 h-[2px] rounded-full bg-gradient-to-r from-cyan-400/0 via-cyan-400/45 to-violet-400/0 shadow-[0_0_18px_rgba(34,211,238,0.26)]" />
            <div className="absolute bottom-10 left-16 h-16 w-16 rounded-full border border-cyan-400/35 bg-cyan-400/10" />
          </div>

          <div className="presentation-hero-body relative lg:text-left">
            <div className="mb-8 flex flex-col items-center gap-4 sm:gap-5 lg:flex-row lg:items-center lg:justify-start">
              <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-2 shadow-[0_0_40px_rgba(139,92,246,0.18)]">
                <BrandMark className="h-14 w-14 sm:h-16 sm:w-16 md:h-20 md:w-20" />
              </div>
              <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-3 lg:justify-start">
                <span className="orbital-chip">Mission Planning</span>
                <span className="orbital-chip">Deterministic Validation</span>
                <span className="orbital-chip">Operator Approval</span>
              </div>
            </div>

            <div className="section-kicker mb-8 border-cyan-400/20 bg-cyan-400/10 text-cyan-200 animate-fade-in-up">
              <span className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse" aria-hidden="true" />
              IBM Space Exploration Hackathon
            </div>

            <h1 className="presentation-hero-title mb-6 animate-fade-in-up lg:text-left" style={{ animationDelay: '100ms' }}>
              <span className="block text-white">AI-Assisted</span>
              <span className="block text-gradient-violet">Lunar Mission Planning</span>
            </h1>

            <p className="presentation-hero-copy mb-6 animate-fade-in-up lg:mx-0" style={{ animationDelay: '200ms' }}>
              Forecast. Verify. Optimize. Maximize science yield.
            </p>

            <p className="mb-10 max-w-4xl text-base leading-relaxed text-gray-400 animate-fade-in-up sm:text-lg md:mb-12 md:text-xl lg:mx-0" style={{ animationDelay: '300ms' }}>
              LunaYield forecasts mission resources, detects current and future anomalies, generates deterministic operational strategies, validates them through backend-authoritative rules, and keeps the human operator in control.
            </p>

            <div className="mb-10 grid max-w-5xl grid-cols-1 gap-4 text-left md:grid-cols-3 animate-fade-in-up" style={{ animationDelay: '350ms' }}>
              {[
                ['Backend Authoritative', 'Safety and approval decisions stay on the FastAPI backend.'],
                ['Deterministic Pipeline', 'Forecasting, anomaly detection, and strategy generation are rule-based today.'],
                ['Approval Not Execution', 'Operator approval records intent and re-runs validation only.'],
              ].map(([title, body]) => (
                <div key={title} className="glass-panel surface-hover rounded-2xl p-4">
                  <p className="mb-2 text-xs uppercase tracking-[0.22em] text-cyan-200">{title}</p>
                  <p className="text-sm leading-relaxed text-slate-300">{body}</p>
                </div>
              ))}
            </div>

            <div className="flex flex-col items-stretch justify-center gap-4 animate-fade-in-up sm:items-center md:flex-row lg:justify-start" style={{ animationDelay: '400ms' }}>
              <NavLink
                to="/mission-control"
                className="w-full rounded-lg bg-gradient-to-r from-cyan-400 to-violet-500 px-6 py-4 text-center text-base font-semibold text-slate-950 transition-all duration-200 hover:from-cyan-300 hover:to-violet-400 hover:shadow-lg hover:shadow-cyan-500/25 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/50 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-950 sm:text-lg md:w-auto"
              >
                Launch Mission Control
              </NavLink>
              <NavLink
                to="/problem-solution"
                className="w-full rounded-lg border border-white/10 bg-white/5 px-6 py-4 text-center text-base font-semibold text-white transition-all duration-200 hover:border-white/20 hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/50 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-950 sm:text-lg md:w-auto"
              >
                Explore the System
              </NavLink>
            </div>

            <div className="mt-16 animate-bounce-slow" aria-hidden="true">
              <svg className="w-6 h-6 text-gray-500 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
              </svg>
            </div>
          </div>
        </div>
      </section>

      {/* MISSION AT A GLANCE */}
      <section className="page-section py-20 md:py-28">
        <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-white mb-4">Mission at a Glance</h2>
            <p className="text-gray-400 text-lg max-w-2xl mx-auto">Five resources. Five waypoints. Deterministic validation. Operator-authorized decisions.</p>
          </div>

          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { icon: '🔋', label: '5 Monitored Resources', desc: 'Battery, Storage, Temperature, Comm Window, Op Time' },
              { icon: '📍', label: '5 Mission Waypoints', desc: 'Base Camp → Crater A → Ice Deposit → Ridge → Return' },
              { icon: '✅', label: 'Deterministic Validation', desc: 'Schema checks, safety rules, zero LLM/ML in backend' },
              { icon: '👨‍🚀', label: 'Operator-Authorized', desc: 'Explicit approval required, approval ≠ execution' },
            ].map((item, i) => (
              <div key={i} className="glass-panel surface-hover group rounded-2xl p-6">
                <div className="text-4xl mb-4" aria-hidden="true">{item.icon}</div>
                <h3 className="text-lg font-semibold text-white mb-2">{item.label}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* HOW LUNAYIELD WORKS */}
      <section className="page-section py-20 md:py-28">
        <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-white mb-4">How LunaYield Works</h2>
            <p className="text-gray-400 text-lg max-w-2xl mx-auto">Interactive workflow — hover or focus each stage to learn more.</p>
          </div>

          <div className="hidden max-w-5xl mx-auto lg:block">
            <div className="relative">
              {/* Connecting line */}
              <div className="hidden lg:block absolute left-10 top-0 bottom-0 w-0.5 bg-gradient-to-b from-cyan-500/30 via-cyan-500/10 to-gray-800" aria-hidden="true" />

              <div className="space-y-8 md:space-y-12">
                {workflowStages.map((stage, index) => (
                  <div
                    key={stage.id}
                  className={`relative flex gap-6 group ${index % 2 === 0 ? '' : 'lg:ml-20'}`}
                  >
                    <div
                      className={`relative flex-shrink-0 w-20 h-20 rounded-2xl flex items-center justify-center transition-all duration-300 ${
                        activeStage === stage.id
                          ? 'bg-cyan-500/20 border-2 border-cyan-500/50 scale-110 shadow-xl shadow-cyan-500/10'
                          : 'glass-panel border border-white/10 hover:border-cyan-500/30 hover:bg-cyan-500/10'
                      }`}
                      onMouseEnter={() => setActiveStage(stage.id)}
                      onMouseLeave={() => setActiveStage(null)}
                      onFocus={() => setActiveStage(stage.id)}
                      onBlur={() => setActiveStage(null)}
                      role="button"
                      tabIndex={0}
                      aria-pressed={activeStage === stage.id}
                    >
                      <span className="text-cyan-400" aria-hidden="true">{stage.icon}</span>
                      {/* Step number */}
                      <span className="absolute -top-3 -right-3 w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-400 text-xs font-mono flex items-center justify-center border border-cyan-500/30">
                        {index + 1}
                      </span>
                    </div>

                    <div className="flex-1 min-w-0">
                      <h3 className="text-xl font-semibold text-white mb-2 flex items-center gap-2">
                        <span className={`text-cyan-400 font-mono text-sm ${activeStage === stage.id ? 'opacity-100' : 'opacity-0 transition-opacity'}`}>
                          {index + 1}.
                        </span>
                        {stage.label}
                      </h3>
                      <p className={`text-gray-400 leading-relaxed transition-all duration-300 ${
                        activeStage === stage.id ? 'text-white max-h-32 opacity-100' : 'max-h-0 opacity-0 overflow-hidden'
                      }`}>
                        {stage.description}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Mobile horizontal scroll version */}
          <div className="lg:hidden mt-12">
            <div className="overflow-x-auto pb-4 -mx-4 px-4 snap-x flex gap-4">
              {workflowStages.map((stage) => (
                <div key={stage.id} className="glass-panel flex-shrink-0 w-[85vw] max-w-[20rem] snap-center rounded-xl p-4 sm:w-72">
                  <div className="flex items-center justify-center w-16 h-16 rounded-xl bg-gray-800/50 border border-gray-700 mx-auto mb-4 text-cyan-400">
                    {stage.icon}
                  </div>
                  <h3 className="text-sm font-semibold text-white mb-2 text-center">{stage.label}</h3>
                  <p className="text-xs text-gray-400 text-center">{stage.description}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Approval ≠ Execution callout */}
          <div className="glass-panel mt-16 rounded-2xl border border-amber-500/30 bg-amber-500/10 p-6">
            <div className="flex items-start gap-4">
              <svg className="w-6 h-6 text-amber-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <h4 className="text-amber-300 font-semibold text-lg mb-1">Critical Distinction: Approval ≠ Execution</h4>
                <p className="text-gray-400">
                  The <code className="bg-gray-800 px-1.5 py-0.5 rounded text-amber-300 font-mono text-sm">
  POST /api/strategies/{'{id}'}/approve
</code> endpoint records operator intent only.
                  No "Execute", "Apply", or "Run Strategy" controls exist. Safety/validation re-runs at approval time. The frontend never calculates safety.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* WHY LUNAYIELD */}
      <section className="page-section py-20 md:py-28">
        <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-white mb-4">Why LunaYield</h2>
            <p className="text-gray-400 text-lg max-w-2xl mx-auto">Three principles that define the system architecture and operator experience.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {whyCards.map((card, i) => (
              <article key={i} className="glass-panel surface-hover group rounded-2xl p-8">
                <div className="w-14 h-14 rounded-xl bg-cyan-500/10 flex items-center justify-center text-cyan-400 mb-6 group-hover:bg-cyan-500/20 group-hover:scale-105 transition-all duration-300" aria-hidden="true">
                  {card.icon}
                </div>
                <h3 className="text-xl font-semibold text-white mb-3">{card.title}</h3>
                <p className="text-gray-400 leading-relaxed">{card.description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* FINAL CTA */}
      <section className="page-section relative overflow-hidden py-20 md:py-28">
        <div className="absolute inset-0" aria-hidden="true">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-cyan-500/5 rounded-full blur-3xl" />
        </div>

        <div className="hero-panel relative mx-auto max-w-3xl px-5 py-10 text-center sm:px-6 md:px-10 md:py-12">
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight text-white mb-6">
            Ready to See It in Action?
          </h2>
          <p className="mb-10 max-w-2xl mx-auto text-lg leading-relaxed text-gray-400 sm:text-xl">
            Open the live Mission Control and run the complete operator workflow — from anomaly injection through strategy approval.
          </p>
          <NavLink
            to="/mission-control"
            className="inline-flex w-full items-center justify-center gap-3 rounded-lg bg-cyan-500 px-6 py-4 text-base font-bold text-gray-950 transition-all duration-200 hover:bg-cyan-400 hover:shadow-xl hover:shadow-cyan-500/30 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/50 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-950 sm:w-auto sm:px-10 sm:py-5 sm:text-lg"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Open Live Mission Control
          </NavLink>
        </div>
      </section>
    </div>
  );
}
