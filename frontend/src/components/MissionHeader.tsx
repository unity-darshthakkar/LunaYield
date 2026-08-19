/** Mission header with title, status badge, and connection indicator */

import type { MissionStatus } from '../types/mission';
import { clsx } from 'clsx';
import { StatusBadge } from './StatusBadge';

interface MissionHeaderProps {
  missionStatus: MissionStatus | undefined;
  wsStatus: 'connecting' | 'connected' | 'disconnected' | 'reconnecting';
  className?: string;
}

const wsStatusConfig = {
  connecting: { color: 'text-yellow-400', label: 'CONNECTING', dot: 'bg-yellow-400 animate-pulse' },
  connected: { color: 'text-green-400', label: 'CONNECTED', dot: 'bg-green-400 animate-pulse' },
  disconnected: { color: 'text-red-400', label: 'DISCONNECTED', dot: 'bg-red-400' },
  reconnecting: { color: 'text-yellow-400', label: 'RECONNECTING', dot: 'bg-yellow-400 animate-pulse' },
};

export function MissionHeader({
  missionStatus,
  wsStatus,
  className = '',
}: MissionHeaderProps) {
  const wsConfig = wsStatusConfig[wsStatus];

  return (
    <header
      className={clsx(
        'sticky top-0 z-20 border-b border-gray-800 bg-gray-950/95 px-4 py-4 backdrop-blur-md md:px-6 md:py-5',
        className
      )}
    >
      <div className="mx-auto flex max-w-full flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex items-center gap-3 md:gap-4">
          <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-yellow-500 to-orange-600 shadow-[0_0_25px_rgba(245,158,11,0.18)] md:h-12 md:w-12">
            <svg className="h-6 w-6 text-black" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
            </svg>
          </div>
          <div className="min-w-0">
            <h1 className="text-lg font-bold tracking-tight text-white sm:text-xl md:text-2xl">
              LunaYield Mission Lab
            </h1>
            <p className="mt-1 text-xs leading-relaxed text-gray-500 sm:text-sm">
              Shackleton Rim Survey - Alpha
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:flex xl:flex-row xl:items-center xl:justify-end xl:gap-4">
          <div className="flex items-center justify-between gap-3 rounded-xl border border-gray-800 bg-gray-900/50 px-3 py-2.5">
            <span className="text-xs font-mono uppercase text-gray-500">STATUS</span>
            {missionStatus && <StatusBadge status={missionStatus} />}
          </div>

          <div className="flex items-center justify-between gap-3 rounded-xl border border-gray-800 bg-gray-900/50 px-3 py-2.5">
            <span className="text-xs font-mono uppercase text-gray-500">WS</span>
            <div className={`flex items-center gap-1.5 ${wsConfig.color}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${wsConfig.dot}`} />
              <span className="text-xs font-mono">{wsConfig.label}</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
