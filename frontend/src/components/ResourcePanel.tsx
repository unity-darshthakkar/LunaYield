/** Resource panel displaying rover resources with progress bars */

import type { RoverResources } from '../types/mission';
import { clsx } from 'clsx';

interface ResourcePanelProps {
  resources: RoverResources | undefined;
  className?: string;
}

function ResourceBar({
  label,
  value,
  max = 100,
  unit = '%',
  warningThreshold,
  criticalThreshold,
  invert = false,
}: {
  label: string;
  value: number;
  max?: number;
  unit?: string;
  warningThreshold?: number;
  criticalThreshold?: number;
  invert?: boolean;
}) {
  const percentage = Math.max(0, Math.min(100, (value / max) * 100));

  let barColor = 'bg-green-500';
  if (invert) {
    if (value <= criticalThreshold!) barColor = 'bg-red-500';
    else if (value <= warningThreshold!) barColor = 'bg-yellow-500';
  } else {
    if (value >= criticalThreshold!) barColor = 'bg-red-500';
    else if (value >= warningThreshold!) barColor = 'bg-yellow-500';
  }

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs font-mono">
        <span className="text-gray-400">{label}</span>
        <span className="text-white">{value.toFixed(1)}{unit}</span>
      </div>
      <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`${barColor} h-full transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

function TimeDisplay({ label, seconds }: { label: string; seconds: number }) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  return (
    <div className="flex justify-between text-xs font-mono">
      <span className="text-gray-400">{label}</span>
      <span className="text-white">
        {hours > 0 ? `${hours}h ` : ''}{minutes}m {secs}s
      </span>
    </div>
  );
}

export function ResourcePanel({ resources, className = '' }: ResourcePanelProps) {
  if (!resources) {
    return (
      <div className={clsx('p-4 bg-gray-900/50 rounded-lg border border-gray-700', className)}>
        <h3 className="text-sm font-semibold text-gray-300 mb-3">ROVER RESOURCES</h3>
        <p className="text-gray-500 text-sm">Awaiting mission data...</p>
      </div>
    );
  }

  return (
    <div className={clsx('p-4 bg-gray-900/50 rounded-lg border border-gray-700', className)}>
      <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-green-500" />
        ROVER RESOURCES
      </h3>
      <div className="space-y-4">
        <ResourceBar
          label="BATTERY"
          value={resources.battery_pct}
          warningThreshold={30}
          criticalThreshold={20}
        />
        <ResourceBar
          label="STORAGE"
          value={resources.storage_pct}
          warningThreshold={80}
          criticalThreshold={95}
          invert={false}
        />
        <div className="flex justify-between text-xs font-mono">
          <span className="text-gray-400">TEMP</span>
          <span className="text-white">{resources.temperature_c.toFixed(1)}°C</span>
        </div>
        <TimeDisplay label="COMM WINDOW" seconds={resources.comm_window_remaining_s} />
        <TimeDisplay label="OP TIME" seconds={resources.op_time_remaining_s} />
      </div>
    </div>
  );
}