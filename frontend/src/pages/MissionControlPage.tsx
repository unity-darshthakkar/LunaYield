/** LunaYield Mission Control Page - Thin wrapper around existing Mission Control App */

import { MissionControlApp } from '../components/MissionControlApp';

export function MissionControlPage() {
  return (
    <div className="min-h-screen px-3 pb-6 pt-3 md:px-5 md:pb-8 md:pt-5">
      <div className="overflow-visible rounded-[1.75rem] border border-cyan-400/12 bg-slate-950/78 shadow-[0_30px_80px_rgba(2,6,23,0.4)]">
        <div className="flex items-center justify-between border-b border-white/10 bg-white/[0.03] px-4 py-3 font-mono text-xs uppercase tracking-[0.28em] text-slate-400">
          <span>Presentation Shell</span>
          <span className="text-cyan-300">Mission Control</span>
        </div>
        <MissionControlApp />
      </div>
    </div>
  );
}
