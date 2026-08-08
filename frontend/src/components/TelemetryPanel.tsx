/** Telemetry panel showing live telemetry from WebSocket */

import type { TelemetrySample } from '../types/mission';
import { clsx } from 'clsx';

interface TelemetryPanelProps {
  telemetry: TelemetrySample | null;
  className?: string;
}

export function TelemetryPanel({ telemetry, className = '' }: TelemetryPanelProps) {
  if (!telemetry) {
    return (
      <div className={clsx('p-4 bg-gray-900/50 rounded-lg border border-gray-700', className)}>
        <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-gray-600" />
          LIVE TELEMETRY
        </h3>
        <p className="text-gray-500 text-sm text-center py-4">
          Awaiting telemetry stream...<br />
          <span className="text-xs">Mission must be RUNNING or EXECUTING</span>
        </p>
      </div>
    );
  }

  const { elapsed_s, resources, timestamp } = telemetry;
  const elapsedMinutes = Math.floor(elapsed_s / 60);
  const elapsedSeconds = elapsed_s % 60;

  return (
    <div className={clsx('p-4 bg-gray-900/50 rounded-lg border border-gray-700', className)}>
      <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
        LIVE TELEMETRY
      </h3>
      <div className="grid grid-cols-2 gap-3 text-xs font-mono">
        <div>
          <span className="text-gray-400">ELAPSED</span>
          <div className="text-white">{elapsedMinutes}m {elapsedSeconds.toString().padStart(2, '0')}s</div>
        </div>
        <div>
          <span className="text-gray-400">BATTERY</span>
          <div className="text-white">{resources.battery_pct.toFixed(1)}%</div>
        </div>
        <div>
          <span className="text-gray-400">STORAGE</span>
          <div className="text-white">{resources.storage_pct.toFixed(1)}%</div>
        </div>
        <div>
          <span className="text-gray-400">TEMP</span>
          <div className="text-white">{resources.temperature_c.toFixed(1)}°C</div>
        </div>
        <div>
          <span className="text-gray-400">COMM WINDOW</span>
          <div className="text-white">
            {Math.floor(resources.comm_window_remaining_s / 60)}m
          </div>
        </div>
        <div>
          <span className="text-gray-400">OP TIME</span>
          <div className="text-white">
            {Math.floor(resources.op_time_remaining_s / 3600)}h
          </div>
        </div>
        <div className="col-span-2">
          <span className="text-gray-400">RECEIVED</span>
          <div className="text-white">
            {new Date(timestamp).toLocaleTimeString()}
          </div>
        </div>
      </div>
    </div>
  );
}