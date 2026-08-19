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
      <div className="rounded-2xl border border-gray-800 bg-gray-900/50 p-5">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-bold tracking-wide text-white">RESOURCE FORECAST</h3>
          <div
            role="status"
            aria-label="Loading forecast"
            className="h-6 w-6 animate-spin rounded-full border-2 border-yellow-500 border-t-transparent"
          />
        </div>
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-4 animate-pulse rounded bg-gray-800" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-gray-800 bg-gray-900/50 p-5">
        <div className="mb-2 flex items-center gap-2 text-red-400">
          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
          </svg>
          <span className="font-bold">FORECAST ERROR</span>
        </div>
        <p className="text-sm font-mono text-gray-400">{error.message}</p>
        <button
          onClick={() => onHorizonChange(horizon)}
          className="mt-3 rounded border border-blue-500/30 bg-blue-500/20 px-3 py-1 text-xs text-blue-400 transition-colors hover:bg-blue-500/30"
        >
          RETRY
        </button>
      </div>
    );
  }

  if (!forecast) {
    return (
      <div className="rounded-2xl border border-gray-800 bg-gray-900/50 p-5">
        <h3 className="mb-4 text-sm font-bold tracking-wide text-white">RESOURCE FORECAST</h3>
        <p className="text-sm text-gray-500">No forecast data available</p>
      </div>
    );
  }

  const points = forecast.forecast_points;
  const horizonLabel = HORIZON_OPTIONS.find((o) => o.value === horizon)?.label ?? formatSeconds(horizon);

  const sampleIndices = points.length > 0
    ? [
        Math.floor(points.length * 0.25) - 1,
        Math.floor(points.length * 0.5) - 1,
        Math.floor(points.length * 0.75) - 1,
        points.length - 1,
      ].filter((i) => i >= 0 && i < points.length)
    : [];

  return (
    <div className="rounded-2xl border border-gray-800 bg-gray-900/50 p-5">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h3 className="text-sm font-bold tracking-wide text-white">RESOURCE FORECAST</h3>
        <select
          value={horizon}
          onChange={(e) => onHorizonChange(Number(e.target.value))}
          className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-xs font-mono text-white focus:outline-none focus:ring-1 focus:ring-yellow-500"
        >
          {HORIZON_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div data-testid="forecast-meta" className="mb-4 text-xs font-mono leading-relaxed text-gray-500">
        Horizon: <span className="text-white">{horizonLabel}</span> | Interval: {forecast.forecast_tick_interval_s}s | Points: {points.length}
      </div>

      {points.length === 0 ? (
        <div className="py-6 text-center text-sm text-gray-500">No forecast points generated</div>
      ) : (
        <div className="space-y-3">
          {sampleIndices.map((idx, sampleIdx) => {
            const point = points[idx];
            const hoursAhead = (point.forecast_seconds_ahead / 3600).toFixed(1);
            return (
              <div
                key={`${sampleIdx}-${point.forecast_seconds_ahead}`}
                className="rounded-xl border border-gray-700 bg-gray-800/50 p-3"
              >
                <div className="mb-3 text-xs font-mono text-gray-400">T+{hoursAhead}h</div>
                <div className="grid grid-cols-2 gap-3 text-center sm:grid-cols-3">
                  <div className="rounded-lg border border-gray-700 bg-gray-950/25 px-2 py-2">
                    <div className="mb-1 text-[10px] font-mono text-gray-500">BATT</div>
                    {renderResourceValue(point, 'battery_pct', 30, 15)}
                  </div>
                  <div className="rounded-lg border border-gray-700 bg-gray-950/25 px-2 py-2">
                    <div className="mb-1 text-[10px] font-mono text-gray-500">STOR</div>
                    {renderResourceValue(point, 'storage_pct', 80, 95)}
                  </div>
                  <div className="rounded-lg border border-gray-700 bg-gray-950/25 px-2 py-2">
                    <div className="mb-1 text-[10px] font-mono text-gray-500">TEMP</div>
                    {renderResourceValue(point, 'temperature_c', 40, 60)}
                  </div>
                  <div className="rounded-lg border border-gray-700 bg-gray-950/25 px-2 py-2">
                    <div className="mb-1 text-[10px] font-mono text-gray-500">COMM</div>
                    {renderResourceValue(point, 'comm_window_remaining_s', 600, 60)}
                  </div>
                  <div className="rounded-lg border border-gray-700 bg-gray-950/25 px-2 py-2">
                    <div className="mb-1 text-[10px] font-mono text-gray-500">OPS</div>
                    {renderResourceValue(point, 'op_time_remaining_s', 3600, 600)}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="mt-5 border-t border-gray-800 pt-4">
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="rounded border border-gray-700 bg-gray-800 px-2 py-0.5">
            <span className="text-green-400">■</span> Nominal
          </span>
          <span className="rounded border border-gray-700 bg-gray-800 px-2 py-0.5">
            <span className="text-yellow-400">■</span> Warning
          </span>
          <span className="rounded border border-gray-700 bg-gray-800 px-2 py-0.5">
            <span className="text-red-400">■</span> Critical
          </span>
        </div>
        <div className="mt-2 flex flex-wrap gap-4 text-xs font-mono text-gray-400">
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
