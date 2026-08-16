/** Forecast Panel - displays mission resource forecast */

import { ForecastPoint, MissionForecastResponse } from '../types/mission';

interface ForecastPanelProps {
  forecast: MissionForecastResponse | undefined;
  isLoading: boolean;
  error: Error | null;
  horizon: number;
  onHorizonChange: (horizon: number) => void;
}

const HORIZON_OPTIONS = [
  { value: 600, label: '10 min' },
  { value: 1800, label: '30 min' },
  { value: 3600, label: '1 hour' },
  { value: 7200, label: '2 hours' },
  { value: 14400, label: '4 hours' },
  { value: 28800, label: '8 hours' },
];

function formatSeconds(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
}

function getResourceColorPercent(value: number, warning: number, critical: number): string {
  if (value <= critical) return 'text-red-400';
  if (value <= warning) return 'text-yellow-400';
  return 'text-green-400';
}

function renderResourceValue(
  point: ForecastPoint,
  resource: keyof typeof point.resources,
  warnThreshold: number,
  critThreshold: number
) {
  const value = point.resources[resource];
  const color = getResourceColorPercent(value as number, warnThreshold, critThreshold);
  return <span className={`font-mono ${color}`}>{(value as number).toFixed(1)}</span>;
}

export function ForecastPanel({
  forecast,
  isLoading,
  error,
  horizon,
  onHorizonChange,
}: ForecastPanelProps) {
  if (isLoading) {
    return (
      <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-white font-bold text-sm tracking-wide">RESOURCE FORECAST</h3>
          <div
            role="status"
            aria-label="Loading forecast"
            className="w-6 h-6 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin"
          />
        </div>
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-4 bg-gray-800 rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-4">
        <div className="flex items-center gap-2 text-red-400 mb-2">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
          </svg>
          <span className="font-bold">FORECAST ERROR</span>
        </div>
        <p className="text-gray-400 text-sm font-mono">{error.message}</p>
        <button
          onClick={() => onHorizonChange(horizon)}
          className="mt-3 px-3 py-1 text-xs bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded hover:bg-blue-500/30 transition-colors"
        >
          RETRY
        </button>
      </div>
    );
  }

  if (!forecast) {
    return (
      <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-4">
        <h3 className="text-white font-bold text-sm tracking-wide mb-3">RESOURCE FORECAST</h3>
        <p className="text-gray-500 text-sm">No forecast data available</p>
      </div>
    );
  }

  const points = forecast.forecast_points;
  const horizonLabel = HORIZON_OPTIONS.find(o => o.value === horizon)?.label ?? formatSeconds(horizon);

  // Show key forecast points: 25%, 50%, 75%, 100% of horizon
  const sampleIndices = points.length > 0
    ? [
        Math.floor(points.length * 0.25) - 1,
        Math.floor(points.length * 0.50) - 1,
        Math.floor(points.length * 0.75) - 1,
        points.length - 1,
      ].filter((i) => i >= 0 && i < points.length)
    : [];

  return (
    <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-white font-bold text-sm tracking-wide">RESOURCE FORECAST</h3>
        <select
          value={horizon}
          onChange={(e) => onHorizonChange(Number(e.target.value))}
          className="bg-gray-800 border border-gray-700 text-white text-xs px-2 py-1 rounded font-mono focus:outline-none focus:ring-1 focus:ring-yellow-500"
        >
          {HORIZON_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div data-testid="forecast-meta" className="text-gray-500 text-xs font-mono mb-3">
        Horizon: <span className="text-white">{horizonLabel}</span> | Interval: {forecast.forecast_tick_interval_s}s | Points: {points.length}
      </div>

      {points.length === 0 ? (
        <div className="text-center py-6 text-gray-500 text-sm">
          No forecast points generated
        </div>
      ) : (
        <div className="space-y-2">
          {sampleIndices.map((idx) => {
            const point = points[idx];
            const hoursAhead = (point.forecast_seconds_ahead / 3600).toFixed(1);
            return (
              <div
                key={point.forecast_seconds_ahead}
                className="grid grid-cols-6 gap-2 p-2 bg-gray-800/50 rounded border border-gray-700"
              >
                <div className="col-span-1 text-right text-gray-400 text-xs font-mono">
                  T+{hoursAhead}h
                </div>
                <div className="col-span-1 text-center">
                  {renderResourceValue(point, 'battery_pct', 30, 15)}
                </div>
                <div className="col-span-1 text-center">
                  {renderResourceValue(point, 'storage_pct', 80, 95)}
                </div>
                <div className="col-span-1 text-center">
                  {renderResourceValue(point, 'temperature_c', 40, 60)}
                </div>
                <div className="col-span-1 text-center">
                  {renderResourceValue(point, 'comm_window_remaining_s', 600, 60)}
                </div>
                <div className="col-span-1 text-center">
                  {renderResourceValue(point, 'op_time_remaining_s', 3600, 600)}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Legend */}
      <div className="mt-4 pt-3 border-t border-gray-800">
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="px-2 py-0.5 bg-gray-800 rounded border border-gray-700">
            <span className="text-green-400">■</span> Nominal
          </span>
          <span className="px-2 py-0.5 bg-gray-800 rounded border border-gray-700">
            <span className="text-yellow-400">■</span> Warning
          </span>
          <span className="px-2 py-0.5 bg-gray-800 rounded border border-gray-700">
            <span className="text-red-400">■</span> Critical
          </span>
        </div>
        <div className="flex flex-wrap gap-4 mt-2 text-xs text-gray-400 font-mono">
          <span>BATT</span>
          <span>STOR</span>
          <span>TEMP</span>
          <span>COMM</span>
          <span>OPS</span>
        </div>
      </div>
    </div>
  );
}