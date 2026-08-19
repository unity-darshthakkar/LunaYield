/** LunaYield Header - Public site navigation */

import { NavLink } from 'react-router-dom';
import { useState } from 'react';
import { BrandMark } from '../components/presentation';

const navLinks = [
  { path: '/', label: 'Home' },
  { path: '/problem-solution', label: 'Problem & Solution' },
  { path: '/mission-control', label: 'Mission Control' },
  { path: '/tech', label: 'Tech & Demo' },
];

export function Header({ isMissionControl = false }: { isMissionControl?: boolean }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-40 backdrop-blur-md transition-all duration-300 ${
        isMissionControl
          ? 'border-b border-cyan-500/10 bg-slate-950/80 shadow-[0_12px_40px_rgba(2,6,23,0.4)]'
          : 'border-b border-white/10 bg-slate-950/70 shadow-[0_12px_40px_rgba(2,6,23,0.35)]'
      }`}
    >
      <nav className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8" aria-label="Main navigation">
        <div className="flex items-center justify-between h-16 md:h-20">
          <NavLink
            to="/"
            className="flex min-w-0 items-center gap-2 rounded-lg px-2 py-1 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/50 sm:gap-3"
            aria-label="LunaYield - Home"
          >
            <div className="rounded-2xl border border-white/10 bg-white/5 p-1 shadow-[0_0_30px_rgba(139,92,246,0.12)]">
              <BrandMark className="h-8 w-8" compact />
            </div>

            <div className="min-w-0">
              <span className="block truncate text-base font-bold tracking-tight text-white sm:text-xl md:text-2xl">
                LunaYield
              </span>
            </div>
          </NavLink>

          <div className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => (
              <NavLink
                key={link.path}
                to={link.path}
                className={({ isActive }) =>
                  `px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? 'border border-cyan-400/20 bg-white/10 text-cyan-200 shadow-[0_0_25px_rgba(34,211,238,0.08)]'
                      : 'text-gray-400 hover:bg-white/5 hover:text-white'
                  }`
                }
              >
                {link.label}
              </NavLink>
            ))}
          </div>

          <div className="hidden md:flex items-center gap-3">
            <NavLink
              to={isMissionControl ? '/tech' : '/mission-control'}
              className={`rounded-lg px-5 py-2.5 text-sm font-semibold transition-all duration-200 ${
                isMissionControl
                  ? 'border border-amber-400/30 bg-amber-500/15 text-amber-200 hover:bg-amber-500/25'
                  : 'bg-gradient-to-r from-cyan-400 to-violet-500 text-slate-950 shadow-lg shadow-cyan-500/20 hover:from-cyan-300 hover:to-violet-400'
              }`}
            >
              {isMissionControl ? 'View Demo Guide' : 'Launch Mission Control'}
            </NavLink>
          </div>

          <button
            type="button"
            className="rounded-lg p-2 text-gray-400 hover:bg-white/10 hover:text-white md:hidden"
            onClick={() => setMobileMenuOpen((open) => !open)}
            aria-expanded={mobileMenuOpen}
            aria-controls="mobile-menu"
            aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
          >
            {mobileMenuOpen ? (
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 6l12 12M18 6L6 18" />
              </svg>
            ) : (
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7h16M4 12h16M4 17h16" />
              </svg>
            )}
          </button>
        </div>

        {mobileMenuOpen && (
          <div id="mobile-menu" className="border-t border-white/10 py-4 md:hidden">
            <div className="flex flex-col gap-2">
              {navLinks.map((link) => (
                <NavLink
                  key={link.path}
                  to={link.path}
                  className={({ isActive }) =>
                    `rounded-lg px-4 py-3 text-base font-medium transition-colors ${
                      isActive
                        ? 'bg-white/10 text-cyan-200'
                        : 'text-gray-400 hover:bg-white/5 hover:text-white'
                    }`
                  }
                  onClick={() => setMobileMenuOpen(false)}
                >
                  {link.label}
                </NavLink>
              ))}
              <NavLink
                to={isMissionControl ? '/tech' : '/mission-control'}
                className={`mt-2 rounded-lg px-4 py-3 text-base font-semibold transition-all duration-200 ${
                  isMissionControl
                    ? 'border border-amber-400/30 bg-amber-500/15 text-amber-200'
                    : 'bg-gradient-to-r from-cyan-400 to-violet-500 text-slate-950'
                }`}
                onClick={() => setMobileMenuOpen(false)}
              >
                {isMissionControl ? 'View Demo Guide' : 'Launch Mission Control'}
              </NavLink>
            </div>
          </div>
        )}
      </nav>
    </header>
  );
}
