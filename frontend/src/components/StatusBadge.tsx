/** Status badge component with color coding for mission status */

import type { MissionStatus } from '../types/mission';

interface StatusBadgeProps {
  status: MissionStatus;
  className?: string;
}

const statusColors: Record<MissionStatus, string> = {
  IDLE: 'bg-gray-600 text-gray-100',
  RUNNING: 'bg-green-600 text-green-50',
  PAUSED: 'bg-yellow-600 text-yellow-50',
  ANOMALY: 'bg-orange-600 text-orange-50',
  PLANNING: 'bg-blue-600 text-blue-50',
  AWAITING_APPROVAL: 'bg-purple-600 text-purple-50',
  EXECUTING: 'bg-emerald-600 text-emerald-50',
  COMPLETED: 'bg-slate-600 text-slate-50',
  RESET: 'bg-gray-500 text-gray-100',
};

const statusLabels: Record<MissionStatus, string> = {
  IDLE: 'IDLE',
  RUNNING: 'RUNNING',
  PAUSED: 'PAUSED',
  ANOMALY: 'ANOMALY',
  PLANNING: 'PLANNING',
  AWAITING_APPROVAL: 'AWAITING APPROVAL',
  EXECUTING: 'EXECUTING',
  COMPLETED: 'COMPLETED',
  RESET: 'RESET',
};

export function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-mono font-semibold ${statusColors[status]} ${className}`}
    >
      {statusLabels[status]}
    </span>
  );
}