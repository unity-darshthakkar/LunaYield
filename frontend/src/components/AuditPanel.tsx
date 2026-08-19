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
    return date.toLocaleTimeString([], {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return timestamp;
  }
}

export function AuditPanel({ events, className = '' }: AuditPanelProps) {
  const auditEvents = events ?? [];

  if (!auditEvents.length) {
    return (
      <div className={clsx('rounded-2xl border border-gray-700 bg-gray-900/50 p-5', className)}>
        <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-300">
          <span className="h-2 w-2 rounded-full bg-gray-600" />
          AUDIT TRAIL
        </h3>
        <p className="py-5 text-center text-sm text-gray-500">No audit events yet</p>
      </div>
    );
  }

  const sortedEvents = [...auditEvents].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  return (
    <div className={clsx('rounded-2xl border border-gray-700 bg-gray-900/50 p-5', className)}>
      <h3 className="mb-4 flex flex-wrap items-center gap-2 text-sm font-semibold text-gray-300">
        <span className="h-2 w-2 rounded-full bg-gray-400" />
        AUDIT TRAIL
        <span className="text-xs font-mono text-gray-500">({auditEvents.length} events)</span>
      </h3>
      <div className="max-h-80 space-y-3 overflow-y-auto pr-1">
        {sortedEvents.map((event, index) => {
          const color = eventTypeColors[event.event_type] || 'text-gray-400';

          return (
            <div
              key={`${event.event_id}-${index}`}
              className="rounded-xl border border-gray-800 bg-gray-950/35 p-3 text-xs font-mono"
            >
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <div className="text-gray-500">{formatTimestamp(event.timestamp)}</div>
                <div className={color}>{event.event_type}</div>
              </div>
              <div className="min-w-0 break-words leading-relaxed text-white">{event.description}</div>
              {event.metadata && Object.keys(event.metadata).length > 0 && (
                <div className="mt-2 break-words text-[10px] leading-relaxed text-gray-500">
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
