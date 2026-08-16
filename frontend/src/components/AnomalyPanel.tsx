/** Anomaly Panel - displays detected resource anomalies */

import { AnomalyDetectionResponse, AnomalyFinding, AnomalySeverity, AnomalyResource } from '../types/mission';

interface AnomalyPanelProps {
  anomalies: AnomalyDetectionResponse | undefined;
  isLoading: boolean;
  error: Error | null;
}

function getSeverityStyle(severity: AnomalySeverity): {
  bg: string;
  border: string;
  text: string;
  icon: string;
} {
  switch (severity) {
    case 'CRITICAL':
      return {
        bg: 'bg-red-900/30',
        border: 'border-red-800',
        text: 'text-red-400',
        icon: '●',
      };
    case 'WARNING':
      return {
        bg: 'bg-yellow-900/30',
        border: 'border-yellow-800',
        text: 'text-yellow-400',
        icon: '▲',
      };
    case 'INFO':
    default:
      return {
        bg: 'bg-blue-900/30',
        border: 'border-blue-800',
        text: 'text-blue-400',
        icon: '◆',
      };
  }
}

function getResourceDisplayName(resource: AnomalyResource): string {
  switch (resource) {
    case 'BATTERY':
      return 'BATTERY';
    case 'STORAGE':
      return 'STORAGE';
    case 'TEMPERATURE':
      return 'TEMP';
    case 'COMM_WINDOW':
      return 'COMMS';
    case 'OP_TIME':
      return 'OPS_TIME';
  }
}

function formatValue(value: number | int, resource: AnomalyResource): string {
  if (resource === 'TEMPERATURE') return `${value}°C`;
  if (resource === 'COMM_WINDOW' || resource === 'OP_TIME') return `${value}s`;
  return `${value}%`;
}

function formatForecastAhead(seconds: number | null): string {
  if (seconds === null || seconds === undefined) return '';
  const mins = Math.floor(seconds / 60);
  if (mins < 60) return `${mins}m ahead`;
  const hours = Math.floor(mins / 60);
  const remMins = mins % 60;
  return remMins > 0 ? `${hours}h ${remMins}m ahead` : `${hours}h ahead`;
}

export function AnomalyPanel({
  anomalies,
  isLoading,
  error,
}: AnomalyPanelProps) {
  if (isLoading) {
    return (
      <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-white font-bold text-sm tracking-wide">ANOMALY DETECTION</h3>
          <div
            role="status"
            aria-label="Loading anomalies"
            className="w-6 h-6 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin"
          />
        </div>
        <div className="space-y-2">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-6 bg-gray-800 rounded animate-pulse" />
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
          <span className="font-bold">ANOMALY ERROR</span>
        </div>
        <p className="text-gray-400 text-sm font-mono">{error.message}</p>
      </div>
    );
  }

  if (!anomalies) {
    return (
      <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-4">
        <h3 className="text-white font-bold text-sm tracking-wide mb-3">ANOMALY DETECTION</h3>
        <p className="text-gray-500 text-sm">No anomaly data available</p>
      </div>
    );
  }

  const { anomaly_count, has_critical, has_warning, anomalies: findings } = anomalies;

  // Healthy state
  if (anomaly_count === 0) {
    return (
      <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <h3 className="text-white font-bold text-sm tracking-wide">ANOMALY DETECTION</h3>
          <span className="px-2 py-0.5 bg-green-900/30 border border-green-800 text-green-400 text-xs font-mono rounded">
            NOMINAL
          </span>
        </div>
        <p className="text-gray-500 text-sm mb-2">No anomalies detected in current mission state</p>
        <p className="text-gray-600 text-xs font-mono">
          Forecast-based detection available via horizon control in Forecast panel
        </p>
      </div>
    );
  }

  // Group findings by severity for display order: CRITICAL > WARNING > INFO
  const severityOrder: Record<AnomalySeverity, number> = { CRITICAL: 0, WARNING: 1, INFO: 2 };
  const sortedFindings = [...findings].sort(
    (a, b) => severityOrder[a.severity] - severityOrder[b.severity]
  );

  return (
    <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-white font-bold text-sm tracking-wide">ANOMALY DETECTION</h3>
        <div className="flex items-center gap-2">
          {has_critical && (
            <span className="px-2 py-0.5 bg-red-900/30 border border-red-800 text-red-400 text-xs font-mono rounded">
              CRITICAL
            </span>
          )}
          {has_warning && !has_critical && (
            <span className="px-2 py-0.5 bg-yellow-900/30 border border-yellow-800 text-yellow-400 text-xs font-mono rounded">
              WARNING
            </span>
          )}
          {!has_critical && !has_warning && anomaly_count > 0 && (
            <span className="px-2 py-0.5 bg-blue-900/30 border border-blue-800 text-blue-400 text-xs font-mono rounded">
              INFO
            </span>
          )}
          <span className="px-2 py-0.5 bg-gray-800 border border-gray-700 text-gray-400 text-xs font-mono rounded">
            {anomaly_count}
          </span>
        </div>
      </div>

      <div className="space-y-2 max-h-60 overflow-y-auto">
        {sortedFindings.map((finding: AnomalyFinding, index: number) => {
          const style = getSeverityStyle(finding.severity);
          const isForecast = finding.is_forecast;
          const forecastAhead = formatForecastAhead(finding.forecast_seconds_ahead);

          return (
            <div
              key={`${finding.resource}-${finding.severity}-${index}`}
              className={`${style.bg} ${style.border} border rounded p-3`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <span className={`${style.text} text-lg font-mono flex-shrink-0`}>
                    {style.icon}
                  </span>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-white capitalize flex-shrink-0">
                        {finding.severity.toLowerCase()}
                      </span>
                      <span className={`${style.text} font-mono text-xs font-bold px-1.5 py-0.5 bg-gray-800 rounded border border-gray-700`}>
                        {getResourceDisplayName(finding.resource)}
                      </span>
                      {isForecast && (
                        <span className="text-purple-400 font-mono text-xs px-1.5 py-0.5 bg-purple-900/30 rounded border border-purple-800">
                          FORECAST
                        </span>
                      )}
                    </div>
                    <p className="text-gray-300 text-sm mt-1 leading-relaxed">{finding.reason}</p>
                    {forecastAhead && (
                      <p className="text-purple-400 text-xs font-mono mt-1">{forecastAhead}</p>
                    )}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1 text-right flex-shrink-0">
                  <div className={`${style.text} font-mono text-sm font-bold`}>
                    {formatValue(finding.observed_value, finding.resource)}
                  </div>
                  <div className="text-gray-500 text-xs font-mono">
                    threshold: {formatValue(finding.threshold_value, finding.resource)}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {findings.length > 5 && (
        <p className="mt-2 text-gray-500 text-xs text-center">
          Showing {findings.length} anomalies
        </p>
      )}
    </div>
  );
}