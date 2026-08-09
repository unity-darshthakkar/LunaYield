/** Audit panel displaying mission audit trail */

import type { AuditEvent } from '../types/mission';
import { clsx } from 'clsx';

interface AuditPanelProps {
  events: AuditEvent[] | undefined;
  className?: string;
}

const eventTypeColors: Record<string, string> = {
  'mission.initialized': 'text-blue-400',
  'mission.started': 'text-green-400',
  'mission.paused': 'text-yellow-400',
  'mission.resumed': 'text-blue-400',
  'anomaly.injected': 'text-orange-400',
  'planning.started': 'text-purple-400',
  'plans.generated': 'text-purple-400',
  'plan.approved': 'text-emerald-400',
  'mission.reset': 'text-gray-400',
};

function formatTimestamp(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return timestamp;
  }
}

export function AuditPanel({ events, className = '' }: AuditPanelProps) {
  const auditEvents = events ?? [];

  if (!auditEvents.length) {
    return (
      <div className={clsx('p-4 bg-gray-900/50 rounded-lg border border-gray-700', className)}>
        <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-gray-600" />
          AUDIT TRAIL
        </h3>
        <p className="text-gray-500 text-sm text-center py-4">No audit events yet</p>
      </div>
    );
  }

  // Show newest first
  const sortedEvents = [...auditEvents].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  return (
    <div className={clsx('p-4 bg-gray-900/50 rounded-lg border border-gray-700', className)}>
      <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-gray-400" />
        AUDIT TRAIL
        <span className="text-xs text-gray-500 font-mono">({auditEvents.length} events)</span>
      </h3>
      <div className="max-h-64 overflow-y-auto space-y-2">
        {sortedEvents.map((event, index) => {
          const color = eventTypeColors[event.event_type] || 'text-gray-400';
          return (
            <div
              key={`${event.event_id}-${index}`}
              className="flex items-start gap-3 text-xs font-mono"
            >
              <div className="flex-shrink-0 w-20 text-gray-500">
                {formatTimestamp(event.timestamp)}
              </div>
              <div className={`flex-shrink-0 w-28 ${color}`}>
                {event.event_type}
              </div>
              <div className="flex-1 min-w-0 text-white truncate">
                {event.description}
              </div>
              {event.metadata && Object.keys(event.metadata).length > 0 && (
                <div className="flex-shrink-0 text-[10px] text-gray-500 max-w-[150px] truncate">
                  {JSON.stringify(event.metadata)}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}