/** LunaYield Problem & Solution Page - Judge-facing narrative */

import { NavLink } from 'react-router-dom';
import { useState } from 'react';

const resources = [
  { name: 'Battery', unit: '%', icon: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757a13.062 13.062 0 011.871-5.183z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12c0 4.512-4.03 8.178-9 8.178a10.95 10.95 0 01-1.672-.387" />
    </svg>
  )},
  { name: 'Storage', unit: '%', icon: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
    </svg>
  )},
  { name: 'Temperature', unit: '°C', icon: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
    </svg>
  )},
  { name: 'Comm Window', unit: 's', icon: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
    </svg>
  )},
  { name: 'Op Time', unit: 's', icon: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  )},
];

const problemHardCards = [
  {
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
      </svg>
    ),
    title: 'Resources interact',
    description: 'A scientifically valuable route can consume scarce battery, fill limited storage, or exceed communication capacity. Optimizing for one resource often degrades another. Operators must evaluate cross-resource tradeoffs in real time, not in isolation.',
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
      </svg>
    ),
    title: 'Conditions evolve',
    description: 'Current resource levels alone are insufficient for safe decisions. A rover at 45% battery may be safe now but critical in two hours. Future projections across all five resources — with configurable horizons and provenance — are required for meaningful risk awareness.',
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.734-.988-2.386l-.548-.547z" />
      </svg>
    ),
    title: 'Operators need explainable decisions',
    description: 'Recommendations must be visible, auditable, and explicitly approved. Black-box automation is unacceptable for high-value missions. Every strategy must show its rationale, source anomalies, and validation status — with the human retaining final authority.',
  },
];

const solutionSteps = [
  { number: '01', label: 'Forecast Resources', desc: 'Deterministic projection of all five resources over 10 min – 8 hr horizons with configurable intervals. No ML/TTM — pure physics-based consumption rates.' },
  { number: '02', label: 'Detect Anomalies', desc: 'Threshold-based detection on current and forecast state. Four types (resource_depletion, thermal, comm, performance), three severities. Full provenance: current-state vs forecast-derived with time-ahead.' },
  { number: '03', label: 'Generate Strategies', desc: 'Deterministic anomaly→strategy mapping (10 templates). Conserve/Monitor/Offload/Schedule/Thermal/Comms/Expedite/Optimize. Priorities 1–5. Deduplicated by resource set.' },
  { number: '04', label: 'Validate Structure', desc: 'Schema/structure validation: required fields, priority bounds, action whitelist, resource enums, approval requirement. Invalid strategies rejected with structured reasons.' },
  { number: '05', label: 'Require Approval', desc: 'Explicit operator-triggered via POST /api/strategies/{id}/approve. Re-runs validation. Invalid strategies cannot be approved. In-memory approval state. Idempotent.' },
  { number: '06', label: 'Persist History', desc: 'SQLite runs, snapshots at transitions, immutable audit trail. Graceful shutdown. Startup restoration with validation. Paginated history API. No Alembic — metadata.create_all only.' },
];

const beforeAfter = {
  before: [
    'Reactive resource awareness — decisions made after thresholds breached',
    'Difficult cross-resource tradeoffs evaluated mentally or via spreadsheets',
    'Disconnected decision context — no shared horizon between forecast, anomalies, strategies',
    'Harder-to-review operational history — limited audit trail, no run persistence',
    'Unclear safety boundaries — no deterministic validation visible to operator',
  ],
  after: [
    'Forecast-driven awareness — projected state visible before anomalies manifest',
    'Structured anomaly context — typed, severitied, provenanced detections on current + future',
    'Prioritized recommendations — deterministic strategies from anomalies, sorted by urgency',
    'Deterministic validation — schema/structure checks with explicit rejection reasons',
    'Explicit operator approval — fail-closed: approve button only on backend-verified VALID',
    'Durable mission history — runs, snapshots, audit trail with pagination and restoration',
  ],
};

export function ProblemSolutionPage() {
  const [activeStep, setActiveStep] = useState<number | null>(null);

  return (
    <div className="min-h-screen">
      <section className="page-section relative flex min-h-[80vh] items-center justify-center overflow-hidden px-4 py-8 md:px-6 lg:px-8">
        <div className="presentation-hero-frame relative">
          <div className="presentation-hero-body">
            <div className="section-kicker mb-8 border-amber-500/20 bg-amber-500/10 text-amber-300 animate-fade-in-up">
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" aria-hidden="true" />
            The Problem
            </div>

            <h1 className="presentation-hero-title mb-6 animate-fade-in-up" style={{ animationDelay: '100ms' }}>
            Lunar rovers operate under{' '}
              <span className="text-gradient-violet">unforgiving resource constraints</span>
            </h1>

            <p className="presentation-hero-copy mb-10 animate-fade-in-up md:mb-12" style={{ animationDelay: '200ms' }}>
            Five critical resources. No recharge stations. No second chances.
            </p>

            <div className="mb-8 flex flex-wrap items-center justify-center gap-3 animate-fade-in-up" style={{ animationDelay: '260ms' }}>
              <span className="orbital-chip">Battery</span>
              <span className="orbital-chip">Storage</span>
              <span className="orbital-chip">Temperature</span>
              <span className="orbital-chip">Comm Window</span>
              <span className="orbital-chip">Op Time</span>
            </div>

            <div className="grid grid-cols-1 gap-4 animate-fade-in-up sm:grid-cols-2 lg:grid-cols-5" style={{ animationDelay: '300ms' }} role="list" aria-label="Monitored mission resources">
            {resources.map((res) => (
              <article key={res.name} className="glass-panel surface-hover group rounded-xl p-5">
                <div className="w-12 h-12 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-400 mb-3 group-hover:bg-amber-500/20 group-hover:scale-105 transition-all duration-300" aria-hidden="true">
                  {res.icon}
                </div>
                <h3 className="font-semibold text-white mb-1">{res.name}</h3>
                <p className="text-xs text-gray-500 uppercase tracking-wider">{res.unit}</p>
              </article>
            ))}
            </div>
          </div>
        </div>
      </section>

      <section className="page-section py-20 md:py-28">
        <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-white mb-4">Why the Problem Is Hard</h2>
            <p className="text-gray-400 text-lg max-w-2xl mx-auto">Three fundamental challenges that make lunar rover operations difficult to manage safely.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {problemHardCards.map((card, i) => (
              <article key={i} className="glass-panel surface-hover group rounded-2xl p-8">
                <div className="w-14 h-14 rounded-xl bg-amber-500/10 flex items-center justify-center text-amber-400 mb-6 group-hover:bg-amber-500/20 group-hover:scale-105 transition-all duration-300" aria-hidden="true">
                  {card.icon}
                </div>
                <h3 className="text-xl font-semibold text-white mb-3">{card.title}</h3>
                <p className="text-gray-400 leading-relaxed">{card.description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="page-section py-20 md:py-28">
        <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-white mb-4">LunaYield Solution</h2>
            <p className="text-gray-400 text-lg max-w-2xl mx-auto">Six integrated capabilities forming a complete decision-support pipeline.</p>
          </div>

          <div className="max-w-4xl mx-auto space-y-4">
            {solutionSteps.map((step, i) => (
              <div
                key={step.number}
                className={`glass-panel surface-hover group rounded-xl p-6 transition-all duration-300 ${
                  activeStep === i
                    ? 'border-cyan-500/50 bg-cyan-500/5 shadow-xl shadow-cyan-500/10'
                    : 'border-white/10 hover:border-cyan-500/30 hover:bg-cyan-500/5'
                }`}
                onMouseEnter={() => setActiveStep(i)}
                onMouseLeave={() => setActiveStep(null)}
                onFocus={() => setActiveStep(i)}
                onBlur={() => setActiveStep(null)}
                role="button"
                tabIndex={0}
                aria-pressed={activeStep === i}
              >
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
                  <div className="flex-shrink-0 w-14 h-14 rounded-xl bg-cyan-500/10 flex items-center justify-center text-cyan-400 font-bold text-xl font-mono group-hover:bg-cyan-500/20 transition-colors">
                    {step.number}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-semibold text-white mb-1">{step.label}</h3>
                    <p className={`text-gray-400 leading-relaxed transition-all duration-300 ${
                      activeStep === i ? 'text-white' : ''
                    }`}>
                      {step.desc}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Flow visual */}
          <div className="mt-12 hidden lg:block">
            <div className="flex items-center justify-center gap-2 text-gray-500 font-mono text-sm">
              {solutionSteps.map((step, i) => (
                <span key={step.number} className="flex items-center gap-2">
                  <span className="px-2 py-1 bg-gray-800 rounded text-cyan-400">{step.number}</span>
                  {i < solutionSteps.length - 1 && <span className="mx-2">→</span>}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="page-section py-20 md:py-28">
        <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-white mb-4">Before / With LunaYield</h2>
            <p className="text-gray-400 text-lg max-w-2xl mx-auto">The operator experience contrast. This is a demonstration system, not a replacement for professional flight software.</p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-5xl mx-auto">
            {/* Without */}
            <div className="glass-panel rounded-2xl border border-red-500/20 bg-red-500/5 p-8">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-lg bg-red-500/20 flex items-center justify-center text-red-400" aria-hidden="true">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-white sm:text-xl">Without LunaYield-Style Support</h3>
              </div>
              <ul className="space-y-4" role="list">
                {beforeAfter.before.map((item, i) => (
                  <li key={i} className="flex items-start gap-3 text-gray-400 leading-relaxed">
                    <span className="flex-shrink-0 w-5 h-5 rounded-full border border-red-500/30 flex items-center justify-center mt-0.5 flex-shrink-0" aria-hidden="true">
                      <svg className="w-3 h-3 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                      </svg>
                    </span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>

            {/* With */}
            <div className="glass-panel rounded-2xl border border-green-500/20 bg-green-500/5 p-8">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center text-green-400" aria-hidden="true">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-white sm:text-xl">With LunaYield</h3>
              </div>
              <ul className="space-y-4" role="list">
                {beforeAfter.after.map((item, i) => (
                  <li key={i} className="flex items-start gap-3 text-gray-400 leading-relaxed">
                    <span className="flex-shrink-0 w-5 h-5 rounded-full border border-green-500/30 flex items-center justify-center mt-0.5 flex-shrink-0" aria-hidden="true">
                      <svg className="w-3 h-3 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    </span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="glass-panel mt-10 rounded-xl p-4">
            <p className="text-sm text-gray-500 text-center">
              <strong className="text-gray-400">Note:</strong> LunaYield is a demonstration system for the IBM Space Exploration Hackathon.
              It does not replace professional flight software, certified mission operations tools, or formal verification processes.
            </p>
          </div>
        </div>
      </section>

      <section className="page-section py-20 md:py-28 text-center">
        <div className="max-w-2xl mx-auto px-4 md:px-6 lg:px-8">
          <div className="hero-panel px-5 py-10 sm:px-6 md:px-10 md:py-12">
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-white mb-6">See It Working Live</h2>
          <p className="mb-10 text-lg leading-relaxed text-gray-400 sm:text-xl">
            Run the complete operator workflow — anomaly injection, plan generation, safety verification, and explicit approval.
          </p>
          <NavLink
            to="/mission-control"
            className="inline-flex w-full items-center justify-center gap-3 rounded-lg bg-cyan-500 px-6 py-4 text-base font-bold text-gray-950 transition-all duration-200 hover:bg-cyan-400 hover:shadow-xl hover:shadow-cyan-500/30 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/50 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-950 sm:w-auto sm:px-10 sm:py-5 sm:text-lg"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Open Mission Control
          </NavLink>
          </div>
        </div>
      </section>
    </div>
  );
}
