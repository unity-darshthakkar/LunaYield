/** Strategy Panel - displays generated mission strategy recommendations */

import { StrategyGenerationResponse, StrategyCandidate, AnomalyResource } from '../types/mission';

interface StrategyPanelProps {
  strategies: StrategyGenerationResponse | undefined;
  isLoading: boolean;
  error: Error | null;
}

function getPriorityStyle(priority: number): {
  bg: string;
  border: string;
  text: string;
  label: string;
} {
  // Priority 1 = highest (CRITICAL), 5 = lowest
  switch (priority) {
    case 1:
      return {
        bg: 'bg-red-900/30',
        border: 'border-red-800',
        text: 'text-red-400',
        label: 'PRIORITY 1',
      };
    case 2:
      return {
        bg: 'bg-yellow-900/30',
        border: 'border-yellow-800',
        text: 'text-yellow-400',
        label: 'PRIORITY 2',
      };
    case 3:
      return {
        bg: 'bg-blue-900/30',
        border: 'border-blue-800',
        text: 'text-blue-400',
        label: 'PRIORITY 3',
      };
    case 4:
      return {
        bg: 'bg-gray-900/30',
        border: 'border-gray-800',
        text: 'text-gray-400',
        label: 'PRIORITY 4',
      };
    case 5:
    default:
      return {
        bg: 'bg-gray-800/30',
        border: 'border-gray-700',
        text: 'text-gray-500',
        label: 'PRIORITY 5',
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

export function StrategyPanel({
  strategies,
  isLoading,
  error,
}: StrategyPanelProps) {
  if (isLoading) {
    return (
      <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-white font-bold text-sm tracking-wide">STRATEGY RECOMMENDATIONS</h3>
          <div
            role="status"
            aria-label="Loading strategies"
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
          <span className="font-bold">STRATEGY ERROR</span>
        </div>
        <p className="text-gray-400 text-sm font-mono">{error.message}</p>
      </div>
    );
  }

  if (!strategies) {
    return (
      <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-4">
        <h3 className="text-white font-bold text-sm tracking-wide mb-3">STRATEGY RECOMMENDATIONS</h3>
        <p className="text-gray-500 text-sm">No strategy data available</p>
      </div>
    );
  }

  const { strategy_count, has_critical_priority, strategies: candidates } = strategies;

  // Empty state
  if (strategy_count === 0) {
    return (
      <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <h3 className="text-white font-bold text-sm tracking-wide">STRATEGY RECOMMENDATIONS</h3>
          <span className="px-2 py-0.5 bg-green-900/30 border border-green-800 text-green-400 text-xs font-mono rounded">
            NOMINAL
          </span>
        </div>
        <p className="text-gray-500 text-sm mb-2">No strategy recommendations at this time</p>
        <p className="text-gray-600 text-xs font-mono">
          Strategies are generated in response to anomaly detections
        </p>
      </div>
    );
  }

  // Sort by priority (1=highest first), then by title for determinism
  const sortedStrategies = [...candidates].sort(
    (a, b) => a.priority - b.priority || a.title.localeCompare(b.title)
  );

  return (
    <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-white font-bold text-sm tracking-wide">STRATEGY RECOMMENDATIONS</h3>
        <div className="flex items-center gap-2">
          {has_critical_priority && (
            <span className="px-2 py-0.5 bg-red-900/30 border border-red-800 text-red-400 text-xs font-mono rounded">
              PRIORITY 1 ACTIVE
            </span>
          )}
          <span className="px-2 py-0.5 bg-gray-800 border border-gray-700 text-gray-400 text-xs font-mono rounded">
            {strategy_count}
          </span>
        </div>
      </div>

      <div className="space-y-2 max-h-80 overflow-y-auto">
        {sortedStrategies.map((strategy: StrategyCandidate, index: number) => {
          const style = getPriorityStyle(strategy.priority);
          const isForecast = strategy.source_anomalies.some(id => id.includes('-f'));

          return (
            <div
              key={`${strategy.strategy_id}-${index}`}
              className={`${style.bg} ${style.border} border rounded p-3`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-2">
                    <span className={`${style.text} font-mono text-xs font-bold px-1.5 py-0.5 bg-gray-800 rounded border border-gray-700`}>
                      {style.label}
                    </span>
                    <span className="font-bold text-white text-sm capitalize flex-shrink-0">
                      {strategy.title}
                    </span>
                    {strategy.affected_resources.length > 0 && (
                      <>
                        <span className="text-gray-500 text-xs">affects:</span>
                        {strategy.affected_resources.map((res, i) => (
                          <span
                            key={i}
                            className={`${style.text} font-mono text-xs font-bold px-1.5 py-0.5 bg-gray-800 rounded border border-gray-700`}
                          >
                            {getResourceDisplayName(res)}
                          </span>
                        ))}
                      </>
                    )}
                    {strategy.requires_operator_approval && (
                      <span className="text-yellow-400 font-mono text-xs px-1.5 py-0.5 bg-yellow-900/30 rounded border border-yellow-800">
                        APPROVAL REQUIRED
                      </span>
                    )}
                    {isForecast && (
                      <span className="text-purple-400 font-mono text-xs px-1.5 py-0.5 bg-purple-900/30 rounded border border-purple-800">
                        FORECAST-BASED
                      </span>
                    )}
                  </div>
                  <p className="text-gray-300 text-sm leading-relaxed">{strategy.rationale}</p>

                  {strategy.recommended_actions.length > 0 && (
                    <div className="mt-2">
                      <p className="text-yellow-400 text-xs font-mono font-bold mb-1">RECOMMENDED ACTIONS:</p>
                      <ul className="space-y-1 pl-4">
                        {strategy.recommended_actions.map((action, actionIndex) => (
                          <li key={actionIndex} className="text-gray-300 text-sm font-mono list-disc">
                            {action}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {strategy.source_anomalies.length > 0 && (
                    <div className="mt-2">
                      <p className="text-purple-400 text-xs font-mono font-bold mb-1">SOURCE ANOMALIES:</p>
                      <p className="text-gray-500 text-xs font-mono">
                        {strategy.source_anomalies.join(', ')}
                      </p>
                    </div>
                  )}
                </div>
                <div className="flex flex-col items-end gap-1 text-right flex-shrink-0">
                  <div className={`${style.text} font-mono text-sm font-bold`}>
                    {strategy.strategy_id}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {candidates.length > 5 && (
        <p className="mt-2 text-gray-500 text-xs text-center">
          Showing {candidates.length} strategies
        </p>
      )}
    </div>
  );
}