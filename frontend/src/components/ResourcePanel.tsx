/** Resource panel displaying rover resources with progress bars */

import type { MissionStatus, RoverResources } from '../types/mission';
import { clsx } from 'clsx';

interface ResourcePanelProps {
  resources: RoverResources | undefined;
  missionStatus?: MissionStatus;
  scienceCollectionComplete?: boolean;
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
  nominalComplete = false,
}: {
  label: string;
  value: number;
  max?: number;
  unit?: string;
  warningThreshold?: number;
  criticalThreshold?: number;
  invert?: boolean;
  nominalComplete?: boolean;
}) {
  const percentage = Math.max(0, Math.min(100, (value / max) * 100));

  let barColor = nominalComplete ? 'bg-cyan-400' : 'bg-green-500';
  if (!nominalComplete) {
    if (invert) {
      if (value <= criticalThreshold!) barColor = 'bg-red-500';
      else if (value <= warningThreshold!) barColor = 'bg-yellow-500';
    } else {
      if (value >= criticalThreshold!) barColor = 'bg-red-500';
      else if (value >= warningThreshold!) barColor = 'bg-yellow-500';
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3 text-xs font-mono">
        <span className="text-gray-400">{label}</span>
        <span className="text-white">
          {value.toFixed(1)}
          {unit}
        </span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-gray-800">
        <div className={`${barColor} h-full transition-all duration-300`} style={{ width: `${percentage}%` }} />
      </div>
    </div>
  );
}

function TimeDisplay({ label, seconds }: { label: string; seconds: number }) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  return (
    <div className="flex justify-between gap-3 text-xs font-mono sm:flex-col sm:gap-1">
      <span className="text-gray-400">{label}</span>
      <span className="text-white">
        {hours > 0 ? `${hours}h ` : ''}
        {minutes}m {secs}s
      </span>
    </div>
  );
}

export function ResourcePanel({
  resources,
  missionStatus,
  scienceCollectionComplete = false,
  className = '',
}: ResourcePanelProps) {
  if (!resources) {
    return (
      <div className={clsx('rounded-2xl border border-gray-700 bg-gray-900/50 p-5', className)}>
        <h3 className="mb-4 text-sm font-semibold text-gray-300">ROVER RESOURCES</h3>
        <p className="text-sm text-gray-500">Awaiting mission data...</p>
      </div>
    );
  }

  return (
    <div className={clsx('rounded-2xl border border-gray-700 bg-gray-900/50 p-5', className)}>
      <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-300">
        <span className="h-2 w-2 rounded-full bg-green-500" />
        ROVER RESOURCES
      </h3>
      <div className="space-y-4">
        <ResourceBar label="BATTERY" value={resources.battery_pct} warningThreshold={30} criticalThreshold={20} />
        <ResourceBar
          label="STORAGE"
          value={resources.storage_pct}
          warningThreshold={80}
          criticalThreshold={95}
          invert={false}
          nominalComplete={scienceCollectionComplete && missionStatus === 'COMPLETED'}
        />
        <div className="grid grid-cols-1 gap-3 rounded-xl border border-gray-800 bg-gray-950/40 p-3 sm:grid-cols-3">
          <div className="flex justify-between gap-3 text-xs font-mono sm:flex-col sm:gap-1">
            <span className="text-gray-400">TEMP</span>
            <span className="text-white">{resources.temperature_c.toFixed(1)}°C</span>
          </div>
          <TimeDisplay label="COMM WINDOW" seconds={resources.comm_window_remaining_s} />
          <TimeDisplay label="OP TIME" seconds={resources.op_time_remaining_s} />
        </div>
      </div>
    </div>
  );
}
