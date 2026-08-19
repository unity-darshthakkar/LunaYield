/** Individual plan card for plan comparison */

import type { CandidatePlan, ConstraintViolation } from '../types/mission';
import { PlanStatus } from '../types/mission';
import { clsx } from 'clsx';

interface PlanCardProps {
  plan: CandidatePlan;
  onApprove?: (planId: string) => void;
  isSelected?: boolean;
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
  isSelected = false,
  disabled = false,
  className = '',
}: PlanCardProps) {
  const isRejected = plan.status === PlanStatus.REJECTED;
  const isApproved = plan.status === PlanStatus.APPROVED;
  const isRecommended = plan.is_recommended;

  return (
    <div
      data-testid="plan-card"
      className={clsx(
        'rounded-2xl border-2 p-5 transition-all',
        isSelected && 'ring-2 ring-cyan-400/35 shadow-[0_0_30px_rgba(34,211,238,0.12)]',
        isRecommended
          ? 'border-yellow-500/50 bg-yellow-900/10 ring-1 ring-yellow-500/20'
          : 'border-gray-700 bg-gray-900/30',
        className
      )}
    >
      <div className="mb-4 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <h4 className="text-lg font-semibold text-white">{plan.label}</h4>
            {isRecommended && (
              <span className="rounded border border-yellow-500/30 bg-yellow-500/20 px-2 py-0.5 text-[10px] font-mono font-semibold text-yellow-400">
                RECOMMENDED
              </span>
            )}
            {isSelected && (
              <span className="rounded border border-cyan-400/30 bg-cyan-400/15 px-2 py-0.5 text-[10px] font-mono font-semibold text-cyan-200">
                SELECTED
              </span>
            )}
          </div>
          <p className="text-sm leading-relaxed text-gray-400">{plan.description}</p>
        </div>
        <div className="text-left sm:text-right">
          <div
            data-testid="plan-status"
            className={`inline-flex items-center rounded px-2 py-1 text-xs font-mono font-semibold ${statusColors[plan.status]}`}
          >
            {statusLabels[plan.status]}
          </div>
          <div className="mt-1 break-all text-xs font-mono text-gray-500">ID: {plan.plan_id}</div>
        </div>
      </div>

      <div className="mb-4 grid grid-cols-1 gap-3 rounded-xl bg-gray-900/50 p-4 sm:grid-cols-2">
        <div className="rounded-lg border border-gray-800 bg-gray-950/30 p-3">
          <div className="text-[10px] font-mono uppercase tracking-wide text-gray-500">Science Yield</div>
          <div className="text-xl font-bold text-white">{plan.science_yield_score.toFixed(1)}</div>
        </div>
        <div className="rounded-lg border border-gray-800 bg-gray-950/30 p-3">
          <div className="text-[10px] font-mono uppercase tracking-wide text-gray-500">Return Battery</div>
          <div className="text-xl font-bold text-white">{plan.predicted_return_battery_pct.toFixed(1)}%</div>
        </div>
      </div>

      {plan.violations.length > 0 && (
        <div className="mb-4 rounded-xl border border-red-800 bg-red-900/20 p-4">
          <div className="mb-2 flex items-center gap-2">
            <span className="text-xs font-mono text-red-400">SAFETY VIOLATIONS</span>
            <span className="rounded border border-red-800 bg-red-900/50 px-1.5 py-0.5 text-[10px] font-mono text-red-300">
              {plan.violations.length}
            </span>
          </div>
          <ul className="space-y-2">
            {plan.violations.map((violation: ConstraintViolation, index: number) => (
              <li key={index} className="text-xs font-mono leading-relaxed text-red-300">
                <span className="text-red-500">[{violation.rule_id}]</span>{' '}
                {violation.description}
                <span className="ml-1 text-red-500">
                  (measured: {violation.measured_value.toFixed(1)}, threshold: {violation.threshold_value.toFixed(1)})
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mb-4">
        <div className="mb-2 text-[10px] font-mono uppercase tracking-wide text-gray-500">
          Waypoints ({plan.waypoints.length})
        </div>
        <div className="flex flex-wrap gap-2">
          {plan.waypoints.slice(0, 5).map((wp) => (
            <span
              key={wp.id}
              className={`rounded border px-1.5 py-0.5 text-[10px] font-mono ${
                wp.is_science_target
                  ? 'border-blue-800 bg-blue-900/30 text-blue-300'
                  : 'border-gray-700 bg-gray-800 text-gray-300'
              }`}
            >
              {wp.label}
            </span>
          ))}
          {plan.waypoints.length > 5 && (
            <span className="px-1.5 py-0.5 text-[10px] text-gray-500">+{plan.waypoints.length - 5} more</span>
          )}
        </div>
      </div>

      <div className="space-y-3">
        {plan.status === PlanStatus.VALID && !isApproved && (
          <button
            onClick={() => onApprove?.(plan.plan_id)}
            disabled={disabled}
            className={`w-full rounded-xl py-3 font-mono text-sm font-medium transition-colors ${
              isRecommended
                ? 'border border-yellow-500/30 bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30 disabled:cursor-not-allowed disabled:opacity-50'
                : 'border border-green-500/30 bg-green-500/20 text-green-400 hover:bg-green-500/30 disabled:cursor-not-allowed disabled:opacity-50'
            }`}
          >
            {isRecommended ? 'APPROVE (RECOMMENDED)' : 'APPROVE PLAN'}
          </button>
        )}
      </div>

      {plan.status === PlanStatus.APPROVED && (
        <div className="w-full rounded-xl border border-emerald-500/30 bg-emerald-500/20 py-3 text-center font-mono text-sm text-emerald-400">
          PLAN APPROVED
        </div>
      )}

      {isRejected && (
        <div className="w-full rounded-xl border border-red-800/50 bg-red-500/10 py-3 text-center font-mono text-xs text-red-500">
          REJECTED - CANNOT APPROVE
        </div>
      )}
    </div>
  );
}