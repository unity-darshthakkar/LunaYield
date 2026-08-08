/** Individual plan card for plan comparison */

import type { CandidatePlan, ConstraintViolation } from '../types/mission';
import { PlanStatus } from '../types/mission';
import { clsx } from 'clsx';

interface PlanCardProps {
  plan: CandidatePlan;
  onApprove?: (planId: string) => void;
  disabled?: boolean;
  className?: string;
}

const statusColors: Record<PlanStatus, string> = {
  VALID: 'bg-green-900/30 text-green-300 border-green-700',
  REJECTED: 'bg-red-900/30 text-red-300 border-red-700',
  APPROVED: 'bg-emerald-900/30 text-emerald-300 border-emerald-700',
};

const statusLabels: Record<PlanStatus, string> = {
  VALID: 'VALID',
  REJECTED: 'REJECTED',
  APPROVED: 'APPROVED',
};

export function PlanCard({
  plan,
  onApprove,
  disabled = false,
  className = '',
}: PlanCardProps) {
  const isRejected = plan.status === PlanStatus.REJECTED;
  const isApproved = plan.status === PlanStatus.APPROVED;
  const isRecommended = plan.is_recommended;

  return (
    <div
      className={clsx(
        'p-4 rounded-lg border-2 transition-all',
        isRecommended
          ? 'border-yellow-500/50 bg-yellow-900/10 ring-1 ring-yellow-500/20'
          : 'border-gray-700 bg-gray-900/30',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h4 className="text-lg font-semibold text-white">{plan.label}</h4>
            {isRecommended && (
              <span className="px-2 py-0.5 text-[10px] font-mono font-semibold bg-yellow-500/20 text-yellow-400 rounded border border-yellow-500/30">
                RECOMMENDED
              </span>
            )}
          </div>
          <p className="text-sm text-gray-400">{plan.description}</p>
        </div>
        <div className="text-right">
          <div className={`inline-flex items-center px-2 py-1 rounded text-xs font-mono font-semibold ${statusColors[plan.status]}`}>
            {statusLabels[plan.status]}
          </div>
          <div className="text-xs text-gray-500 font-mono mt-1">
            ID: {plan.plan_id}
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-4 mb-3 p-3 bg-gray-900/50 rounded">
        <div>
          <div className="text-[10px] text-gray-500 font-mono uppercase tracking-wide">
            Science Yield
          </div>
          <div className="text-xl font-mono font-bold text-white">
            {plan.science_yield_score.toFixed(1)}
          </div>
        </div>
        <div>
          <div className="text-[10px] text-gray-500 font-mono uppercase tracking-wide">
            Return Battery
          </div>
          <div className="text-xl font-mono font-bold text-white">
            {plan.predicted_return_battery_pct.toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Violations */}
      {plan.violations.length > 0 && (
        <div className="mb-3 p-3 bg-red-900/20 border border-red-800 rounded">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-mono text-red-400">SAFETY VIOLATIONS</span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 bg-red-900/50 text-red-300 rounded border border-red-800">
              {plan.violations.length}
            </span>
          </div>
          <ul className="space-y-1">
            {plan.violations.map((violation: ConstraintViolation, index: number) => (
              <li key={index} className="text-xs text-red-300 font-mono">
                <span className="text-red-500">[{violation.rule_id}]</span>{' '}
                {violation.description}
                <span className="text-red-500 ml-1">
                  (measured: {violation.measured_value.toFixed(1)}, threshold: {violation.threshold_value.toFixed(1)})
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Waypoints Summary */}
      <div className="mb-3">
        <div className="text-[10px] text-gray-500 font-mono uppercase tracking-wide mb-1">
          Waypoints ({plan.waypoints.length})
        </div>
        <div className="flex flex-wrap gap-1">
          {plan.waypoints.slice(0, 5).map((wp) => (
            <span
              key={wp.id}
              className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                wp.is_science_target
                  ? 'bg-blue-900/30 text-blue-300 border border-blue-800'
                  : 'bg-gray-800 text-gray-300 border border-gray-700'
              }`}
            >
              {wp.label}
            </span>
          ))}
          {plan.waypoints.length > 5 && (
            <span className="text-[10px] text-gray-500 px-1.5 py-0.5">
              +{plan.waypoints.length - 5} more
            </span>
          )}
        </div>
      </div>

      {/* Approve Button - only for VALID plans, not REJECTED or APPROVED */}
      {plan.status === PlanStatus.VALID && !isApproved && (
        <button
          onClick={() => onApprove?.(plan.plan_id)}
          disabled={disabled}
          className={`w-full py-2 rounded font-mono text-sm font-medium transition-colors ${
            isRecommended
              ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 hover:bg-yellow-500/30 disabled:opacity-50 disabled:cursor-not-allowed'
              : 'bg-green-500/20 text-green-400 border border-green-500/30 hover:bg-green-500/30 disabled:opacity-50 disabled:cursor-not-allowed'
          }`}
        >
          {isRecommended ? 'APPROVE (RECOMMENDED)' : 'APPROVE PLAN'}
        </button>
      )}

      {plan.status === PlanStatus.APPROVED && (
        <div className="w-full py-2 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-center font-mono text-sm">
          PLAN APPROVED
        </div>
      )}

      {isRejected && (
        <div className="w-full py-2 rounded bg-red-500/10 text-red-500 border border-red-800/50 text-center font-mono text-xs">
          REJECTED - CANNOT APPROVE
        </div>
      )}
    </div>
  );
}