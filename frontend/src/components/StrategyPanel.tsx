/** Strategy Panel - displays generated mission strategy recommendations with validation and approval */

import { useApproveStrategy } from '../hooks/useMission';
import { StrategyGenerationResponse, StrategyValidationResponse, StrategyCandidate, AnomalyResource, StrategyApprovalStatus } from '../types/mission';

interface StrategyPanelProps {
  strategies: StrategyGenerationResponse | undefined;
  validation: StrategyValidationResponse | undefined;
  validationError: Error | null;
  isLoading: boolean;
  error: Error | null;
  validationLoading?: boolean;
  forecastHorizon: number;
  useForecast: boolean;
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

function getValidationStatus(validation: StrategyValidationResponse | undefined, strategyId: string): {
  isValid: boolean | null;
  rejectionReasons: string[];
} | null {
  if (!validation?.validation_results) return null;
  const result = validation.validation_results.find(v => v.strategy_id === strategyId);
  if (!result) return null;
  return { isValid: result.is_valid, rejectionReasons: result.rejection_reasons };
}

function getApprovalStatusStyle(status: StrategyApprovalStatus): {
  bg: string;
  border: string;
  text: string;
  label: string;
} {
  switch (status) {
    case 'APPROVED':
      return {
        bg: 'bg-green-900/30',
        border: 'border-green-800',
        text: 'text-green-400',
        label: 'APPROVED',
      };
    case 'REJECTED':
      return {
        bg: 'bg-red-900/30',
        border: 'border-red-800',
        text: 'text-red-400',
        label: 'REJECTED',
      };
    case 'VALIDATION_FAILED':
      return {
        bg: 'bg-orange-900/30',
        border: 'border-orange-800',
        text: 'text-orange-400',
        label: 'VALIDATION FAILED',
      };
    case 'NOT_FOUND':
      return {
        bg: 'bg-gray-900/30',
        border: 'border-gray-800',
        text: 'text-gray-400',
        label: 'NOT FOUND',
      };
    case 'ALREADY_APPROVED':
      return {
        bg: 'bg-blue-900/30',
        border: 'border-blue-800',
        text: 'text-blue-400',
        label: 'ALREADY APPROVED',
      };
    default:
      return {
        bg: 'bg-gray-800/30',
        border: 'border-gray-700',
        text: 'text-gray-500',
        label: 'UNKNOWN',
      };
  }
}

function getValidationStateStyle(kind: ValidationState['kind']): {
  bg: string;
  border: string;
  text: string;
  label: string;
} {
  switch (kind) {
    case 'valid':
      return {
        bg: 'bg-green-900/30',
        border: 'border-green-800',
        text: 'text-green-400',
        label: 'VALID',
      };
    case 'invalid':
      return {
        bg: 'bg-red-900/30',
        border: 'border-red-800',
        text: 'text-red-400',
        label: 'INVALID',
      };
    case 'pending':
      return {
        bg: 'bg-yellow-900/30',
        border: 'border-yellow-800',
        text: 'text-yellow-400',
        label: 'VALIDATION PENDING',
      };
    case 'missing-for-strategy':
      return {
        bg: 'bg-yellow-900/30',
        border: 'border-yellow-800',
        text: 'text-yellow-400',
        label: 'AWAITING VALIDATION',
      };
    case 'unavailable':
      return {
        bg: 'bg-red-900/30',
        border: 'border-red-800',
        text: 'text-red-400',
        label: 'VALIDATION UNAVAILABLE',
      };
  }
}

type ValidationState =
  | { kind: 'unavailable'; message: string }
  | { kind: 'pending' }
  | { kind: 'missing-for-strategy' }
  | { kind: 'valid' }
  | { kind: 'invalid'; reasons: string[] };

function getValidationState(
  validation: StrategyValidationResponse | undefined,
  validationError: Error | null,
  validationLoading: boolean | undefined,
  strategyId: string
): ValidationState {
  // validationError present => unavailable (cannot approve)
  if (validationError) {
    return { kind: 'unavailable', message: validationError.message };
  }
  // validationLoading true => pending (cannot approve)
  if (validationLoading) {
    return { kind: 'pending' };
  }
  // validation response absent => awaiting validation (cannot approve)
  if (!validation) {
    return { kind: 'pending' };
  }
  // validation exists but strategy_id not in results => awaiting validation for this strategy
  const validationResult = getValidationStatus(validation, strategyId);
  if (validationResult === null) {
    return { kind: 'missing-for-strategy' };
  }
  // explicit validation result
  if (validationResult.isValid === true) {
    return { kind: 'valid' };
  }
  // explicit validation result with is_valid === false
  return { kind: 'invalid', reasons: validationResult.rejectionReasons };
}

export function StrategyPanel({
  strategies,
  validation,
  validationError,
  isLoading,
  error,
  validationLoading,
  forecastHorizon,
  useForecast,
}: StrategyPanelProps) {
  const approveStrategyMutation = useApproveStrategy();

  if (isLoading) {
    return (
      <div className="glass-panel rounded-2xl border border-gray-800 p-5">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
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
      <div className="glass-panel rounded-2xl border border-gray-800 p-5">
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
      <div className="glass-panel rounded-2xl border border-gray-800 p-5">
        <h3 className="text-white font-bold text-sm tracking-wide mb-3">STRATEGY RECOMMENDATIONS</h3>
        <p className="text-gray-500 text-sm">No strategy data available</p>
      </div>
    );
  }

  const { strategy_count, has_critical_priority, strategies: candidates } = strategies;

  // Empty state
  if (strategy_count === 0) {
    return (
      <div className="glass-panel rounded-2xl border border-gray-800 p-5">
        <div className="mb-3 flex flex-wrap items-center gap-2">
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

  // Compute overall validation state for header badge
  const getOverallValidationKind = (): 'all_valid' | 'validation_failed' | 'validation_pending' | 'validation_unavailable' => {
    if (validationError) return 'validation_unavailable';
    if (validationLoading) return 'validation_pending';
    if (!validation) return 'validation_pending';
    if (validation.all_valid) return 'all_valid';
    return 'validation_failed';
  };
  const overallValidationKind = getOverallValidationKind();

  function getOverallValidationStyle(kind: ReturnType<typeof getOverallValidationKind>): {
    bg: string;
    border: string;
    text: string;
    label: string;
  } {
    switch (kind) {
      case 'all_valid':
        return {
          bg: 'bg-green-900/30',
          border: 'border-green-800',
          text: 'text-green-400',
          label: 'ALL VALID',
        };
      case 'validation_failed':
        return {
          bg: 'bg-red-900/30',
          border: 'border-red-800',
          text: 'text-red-400',
          label: 'VALIDATION FAILED',
        };
      case 'validation_pending':
        return {
          bg: 'bg-yellow-900/30',
          border: 'border-yellow-800',
          text: 'text-yellow-400',
          label: 'VALIDATION PENDING',
        };
      case 'validation_unavailable':
        return {
          bg: 'bg-red-900/30',
          border: 'border-red-800',
          text: 'text-red-400',
          label: 'VALIDATION UNAVAILABLE',
        };
    }
  }

  const overallValidationStyle = getOverallValidationStyle(overallValidationKind);

  return (
    <div className="glass-panel rounded-2xl border border-gray-800 p-5">
      <div className="mb-4 flex flex-col gap-3 2xl:flex-row 2xl:items-center 2xl:justify-between">
        <h3 className="text-white font-bold text-sm tracking-wide">STRATEGY RECOMMENDATIONS</h3>
        <div className="flex flex-wrap items-center gap-2">
          {has_critical_priority && (
            <span className="px-2 py-0.5 bg-red-900/30 border border-red-800 text-red-400 text-xs font-mono rounded">
              PRIORITY 1 ACTIVE
            </span>
          )}
          <span className={`${overallValidationStyle.bg} ${overallValidationStyle.border} ${overallValidationStyle.text} px-2 py-0.5 text-xs font-mono rounded border`}>
            {overallValidationStyle.label}
          </span>
          <span className="px-2 py-0.5 bg-gray-800 border border-gray-700 text-gray-400 text-xs font-mono rounded">
            {strategy_count}
          </span>
        </div>
      </div>

      {(validationLoading || approveStrategyMutation.isPending) && !validationError && (
        <div className="mb-4 rounded-xl border border-yellow-800 bg-yellow-900/20 p-3 text-xs font-mono text-yellow-400">
          {validationLoading ? 'VALIDATING STRATEGIES...' : 'PROCESSING APPROVAL...'}
        </div>
      )}

      {/* Validation error display */}
      {validationError && (
        <div className="mb-4 rounded-xl border border-red-800 bg-red-900/30 p-3 text-xs font-mono text-red-300">
          VALIDATION UNAVAILABLE: {validationError.message}
        </div>
      )}

      <div className="space-y-4 max-h-[42rem] overflow-y-auto pr-1">
        {sortedStrategies.map((strategy: StrategyCandidate, index: number) => {
          const style = getPriorityStyle(strategy.priority);
          const isForecast = useForecast && strategy.source_anomalies.some(id => id.includes('-f'));
          const isApproving = approveStrategyMutation.isPending &&
            approveStrategyMutation.variables?.strategyId === strategy.strategy_id;

          // Compute validation state for this strategy
          const validationState = getValidationState(validation, validationError, validationLoading, strategy.strategy_id);
          const validationStateStyle = getValidationStateStyle(validationState.kind);
          const isExplicitlyValid = validationState.kind === 'valid';
          const isExplicitlyInvalid = validationState.kind === 'invalid';

          // Approval terminal states
          const approvalStatus = approveStrategyMutation.data?.strategy_id === strategy.strategy_id
            ? approveStrategyMutation.data.approval_status
            : null;

          // Can approve only when explicitly valid, not currently approving, and no terminal approval status
          const canApprove = strategy.requires_operator_approval &&
            isExplicitlyValid &&
            !isApproving &&
            approvalStatus === null;

          return (
            <div
              key={`${strategy.strategy_id}-${index}`}
              data-testid={`strategy-card-${strategy.strategy_id}`}
              className={`${style.bg} ${style.border} rounded-xl border p-4`}
            >
              <div className="flex flex-col gap-4 2xl:flex-row 2xl:items-start 2xl:justify-between">
                <div className="flex-1 min-w-0">
                  <div className="mb-3 flex flex-wrap items-center gap-2">
                    <span className={`${style.text} font-mono text-xs font-bold px-1.5 py-0.5 bg-gray-800 rounded border border-gray-700`}>
                      {style.label}
                    </span>
                    <span className="text-sm font-bold capitalize text-white">
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
                    {/* Validation status badge - uses consistent styling */}
                    <span className={`${validationStateStyle.bg} ${validationStateStyle.border} ${validationStateStyle.text} px-1.5 py-0.5 font-mono text-xs rounded border`}>
                      {validationStateStyle.label}
                    </span>
                  </div>
                  <p className="text-sm leading-relaxed text-gray-300">{strategy.rationale}</p>

                  {strategy.recommended_actions.length > 0 && (
                    <div className="mt-4 rounded-xl border border-white/10 bg-slate-950/35 p-3">
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
                    <div className="mt-3 rounded-xl border border-white/10 bg-slate-950/30 p-3">
                      <p className="text-purple-400 text-xs font-mono font-bold mb-1">SOURCE ANOMALIES:</p>
                      <p className="text-gray-500 text-xs font-mono">
                        {strategy.source_anomalies.join(', ')}
                      </p>
                    </div>
                  )}

                  {/* Validation rejection reasons - only when explicitly invalid */}
                  {isExplicitlyInvalid && validationState.reasons.length > 0 && (
                    <div className="mt-3 rounded-xl border border-red-800 bg-red-900/20 p-3">
                      <p className="text-red-400 text-xs font-mono font-bold mb-1">REJECTION REASONS:</p>
                      <ul className="space-y-1 pl-4">
                        {validationState.reasons.map((reason, reasonIndex) => (
                          <li key={reasonIndex} className="text-red-300 text-xs font-mono list-disc">
                            {reason}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Approval result display - terminal states */}
                  {approvalStatus && (
                    <div className="mt-4 rounded-xl border border-white/10 bg-slate-950/35 p-3">
                      {(() => {
                        const statusStyle = getApprovalStatusStyle(approvalStatus);
                        return (
                          <div className={`${statusStyle.bg} ${statusStyle.border} ${statusStyle.text} rounded border px-2 py-1 font-mono text-xs`}>
                            APPROVAL: {statusStyle.label}
                          </div>
                        );
                      })()}
                      {approveStrategyMutation.data?.rejection_reasons.length > 0 && (
                        <ul className="mt-1 pl-4 space-y-1">
                          {approveStrategyMutation.data.rejection_reasons.map((reason, reasonIndex) => (
                            <li key={reasonIndex} className="text-gray-300 text-xs font-mono list-disc">
                              {reason}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}

                  {/* Approval button - only for explicitly valid, non-terminal strategies */}
                  {canApprove && (
                    <div className="mt-4">
                      <button
                        onClick={() => {
                          approveStrategyMutation.mutate({
                            strategyId: strategy.strategy_id,
                            params: { use_forecast: useForecast, forecast_horizon: forecastHorizon },
                          });
                        }}
                        disabled={approveStrategyMutation.isPending}
                        className="w-full rounded-lg border border-blue-500/30 bg-blue-500/20 px-3 py-2 text-xs font-mono text-blue-400 transition-colors hover:bg-blue-500/30 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {isApproving ? 'APPROVING...' : 'APPROVE STRATEGY'}
                      </button>
                    </div>
                  )}

                  {/* Terminal/blocked states - no button, show status */}
                  {strategy.requires_operator_approval && !canApprove && !isApproving && !approvalStatus && (
                    <div className="mt-4">
                      {(() => {
                        if (isExplicitlyInvalid) {
                          return (
                            <span className="inline-flex rounded-lg border border-red-500/30 bg-red-500/20 px-3 py-2 text-xs font-mono text-red-400">
                              CANNOT APPROVE - VALIDATION FAILED
                            </span>
                          );
                        }
                        if (validationState.kind === 'unavailable') {
                          return (
                            <span className="inline-flex rounded-lg border border-red-500/30 bg-red-500/20 px-3 py-2 text-xs font-mono text-red-400">
                              CANNOT APPROVE - VALIDATION UNAVAILABLE
                            </span>
                          );
                        }
                        if (validationState.kind === 'pending' || validationState.kind === 'missing-for-strategy') {
                          return (
                            <span className="inline-flex rounded-lg border border-yellow-500/30 bg-yellow-500/20 px-3 py-2 text-xs font-mono text-yellow-400">
                              AWAITING VALIDATION
                            </span>
                          );
                        }
                        return null;
                      })()}
                    </div>
                  )}

                  {/* Approval error */}
                  {approveStrategyMutation.isError && approveStrategyMutation.variables?.strategyId === strategy.strategy_id && (
                    <div className="mt-4 rounded-xl border border-red-800 bg-red-900/30 p-3 text-xs font-mono text-red-300">
                      APPROVAL FAILED: {approveStrategyMutation.error?.message || 'Unknown error'}
                    </div>
                  )}
                </div>
                <div className="rounded-xl border border-white/10 bg-slate-950/40 px-3 py-2 text-left 2xl:min-w-[11rem] 2xl:text-right">
                  <p className="mb-1 text-[11px] uppercase tracking-[0.22em] text-gray-500">Strategy ID</p>
                  <div className={`${style.text} break-all font-mono text-sm font-bold`}>
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
