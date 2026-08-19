/** LunaYield Footer - Public site footer */

import { NavLink } from 'react-router-dom';
import { BrandMark } from '../components/presentation';

export function Footer({ variant = 'public' }: { variant?: 'public' | 'mission-control' }) {
  const currentYear = new Date().getFullYear();

  if (variant === 'mission-control') {
    return (
      <footer className="relative z-10 border-t border-cyan-500/10 bg-slate-950/55 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 py-4">
          <p className="text-center font-mono text-xs text-gray-500">
            LunaYield Mission Lab - IBM Space Exploration Hackathon
            {' | '}
            <span className="text-cyan-500">BACKEND AUTHORITATIVE</span>
            {' | '}
            <span className="text-amber-500">APPROVAL != EXECUTION</span>
            {' | '}
            {currentYear}
          </p>
        </div>
      </footer>
    );
  }

  return (
    <footer className="relative z-10 border-t border-white/10 bg-slate-950/65 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 py-12 md:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-8 md:grid-cols-4">
          <div className="md:col-span-2">
            <div className="mb-4 flex items-center gap-3">
              <div className="rounded-3xl border border-white/10 bg-white/5 p-1.5 shadow-[0_0_34px_rgba(139,92,246,0.14)]">
                <BrandMark className="h-9 w-9" compact />
              </div>
              <div>
                <span className="text-xl font-bold tracking-tight text-white">LunaYield</span>
                <div className="text-xs uppercase tracking-[0.35em] text-cyan-300">Mission Lab</div>
              </div>
            </div>
            <p className="max-w-sm text-sm leading-relaxed text-gray-400">
              Deterministic mission decision support for resource-constrained lunar rover operations.
              Built for the IBM Space Exploration Hackathon.
            </p>
          </div>

          <nav aria-label="Quick links">
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-white">Navigate</h3>
            <ul className="space-y-2">
              {[
                { path: '/', label: 'Home' },
                { path: '/problem-solution', label: 'Problem & Solution' },
                { path: '/mission-control', label: 'Mission Control' },
                { path: '/tech', label: 'Tech & Demo' },
              ].map((link) => (
                <li key={link.path}>
                  <NavLink
                    to={link.path}
                    className="text-sm text-gray-400 transition-colors hover:text-cyan-300"
                  >
                    {link.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>

          <nav aria-label="Resources">
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-white">Resources</h3>
            <ul className="space-y-2">
              <li>
                <a
                  href="https://github.com/unity-darshthakkar/LunaYield"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-sm text-gray-400 transition-colors hover:text-cyan-300"
                >
                  <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z" />
                  </svg>
                  GitHub Repository
                </a>
              </li>
              <li>
                <a href="/tech" className="text-sm text-gray-400 transition-colors hover:text-cyan-300">
                  Demo Walkthrough
                </a>
              </li>
              <li>
                <a href="/problem-solution" className="text-sm text-gray-400 transition-colors hover:text-cyan-300">
                  Submission Document
                </a>
              </li>
            </ul>
          </nav>
        </div>

        <div className="mt-10 border-t border-gray-800 pt-8">
          <div className="flex flex-col items-center justify-between gap-4 md:flex-row">
            <p className="text-center text-xs text-gray-500 md:text-left">
              {currentYear} LunaYield Mission Lab - IBM Space Exploration Hackathon
            </p>
            <div className="flex flex-wrap items-center justify-center gap-4 text-xs text-gray-500 md:justify-end md:gap-6">
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-cyan-500 animate-pulse" aria-hidden="true" />
                Deterministic
              </span>
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-amber-500" aria-hidden="true" />
                Operator-Authorized
              </span>
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-green-500" aria-hidden="true" />
                Auditable
              </span>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
