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
    <header className={clsx('px-6 py-4 bg-gray-950 border-b border-gray-800', className)}>
      <div className="max-w-full mx-auto flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        {/* Title */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-yellow-500 to-orange-600 flex items-center justify-center">
            <svg className="w-6 h-6 text-black" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">LunaYield Mission Lab</h1>
            <p className="text-xs text-gray-500">Shackleton Rim Survey — Alpha</p>
          </div>
        </div>

        {/* Status and Connection */}
        <div className="flex flex-col sm:flex-row items-center gap-4">
          {/* Mission Status */}
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-500 font-mono uppercase">STATUS</span>
            {missionStatus && <StatusBadge status={missionStatus} />}
          </div>

          {/* WebSocket Connection */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500 font-mono uppercase">WS</span>
            <div className={`flex items-center gap-1.5 ${wsConfig.color}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${wsConfig.dot}`} />
              <span className="text-xs font-mono">{wsConfig.label}</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}