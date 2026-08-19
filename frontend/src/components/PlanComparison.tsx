/** Plan comparison panel showing all candidate plans */

import type { CandidatePlan } from '../types/mission';
import { clsx } from 'clsx';
import { PlanCard } from './PlanCard';

interface PlanComparisonProps {
  plans: CandidatePlan[];
  onApprove: (planId: string) => void;
  selectedPlanId?: string | null;
  disabled?: boolean;
  className?: string;
}

export function PlanComparison({
  plans,
  onApprove,
  selectedPlanId,
  disabled = false,
  className = '',
}: PlanComparisonProps) {
  if (!plans.length) {
    return null;
  }

  return (
    <div className={clsx('space-y-4', className)}>
      <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-purple-500" />
        CANDIDATE PLANS
        <span className="text-xs text-gray-500 font-mono">({plans.length} plans)</span>
      </h3>
      <div className="space-y-4">
        {plans.map((plan) => (
          <PlanCard
            key={plan.plan_id}
            plan={plan}
            onApprove={onApprove}
            isSelected={selectedPlanId === plan.plan_id}
            disabled={disabled}
          />
        ))}
      </div>
    </div>
  );
}