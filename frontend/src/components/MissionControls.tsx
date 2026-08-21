/** Mission controls with state-aware buttons */

import type { MissionStatus } from '../types/mission';
import { clsx } from 'clsx';

interface MissionControlsProps {
  missionStatus: MissionStatus | undefined;
  anomalyActive: boolean | undefined;
  candidatePlansCount: number;
  approvedPlanLabel?: string;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onInjectAnomaly: () => void;
  onGeneratePlans: () => void;
  onReset: () => void;
  startError?: string | null;
  pauseError?: string | null;
  resumeError?: string | null;
  injectAnomalyError?: string | null;
  generatePlansError?: string | null;
  resetError?: string | null;
  className?: string;
}

function ControlButton({
  children,
  onClick,
  disabled = false,
  variant = 'primary',
  className = '',
}: {
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  variant?: 'primary' | 'secondary' | 'danger' | 'warning';
  className?: string;
}) {
  const variants = {
    primary:
      'bg-blue-500/20 text-blue-400 border border-blue-500/30 hover:bg-blue-500/30 disabled:opacity-50 disabled:cursor-not-allowed',
    secondary:
      'bg-gray-700 text-gray-300 border border-gray-600 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed',
    danger:
      'bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 disabled:opacity-50 disabled:cursor-not-allowed',
    warning:
      'bg-orange-500/20 text-orange-400 border border-orange-500/30 hover:bg-orange-500/30 disabled:opacity-50 disabled:cursor-not-allowed',
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        'w-full rounded-xl px-4 py-3 font-mono text-sm font-medium transition-colors',
        variants[variant],
        className
      )}
    >
      {children}
    </button>
  );
}

export function MissionControls({
  missionStatus,
  anomalyActive,
  candidatePlansCount,
  approvedPlanLabel,
  onStart,
  onPause,
  onResume,
  onInjectAnomaly,
  onGeneratePlans,
  onReset,
  startError,
  pauseError,
  resumeError,
  injectAnomalyError,
  generatePlansError,
  resetError,
  className = '',
}: MissionControlsProps) {
  const isIdle = missionStatus === 'IDLE';
  const isRunning = missionStatus === 'RUNNING';
  const isPaused = missionStatus === 'PAUSED';
  const isAnomaly = missionStatus === 'ANOMALY';
  const isAwaitingApproval = missionStatus === 'AWAITING_APPROVAL';
  const isExecuting = missionStatus === 'EXECUTING';
  const isCompleted = missionStatus === 'COMPLETED';
  const canPause = isRunning;
  const canResume = isPaused;
  const hasPendingPlans = candidatePlansCount > 0 && !approvedPlanLabel;
  const canManagePlans = isAnomaly || hasPendingPlans;
  const planButtonLabel = approvedPlanLabel
    ? `PLAN SELECTED: ${approvedPlanLabel.toUpperCase()}`
    : candidatePlansCount > 0
      ? 'VIEW PLANS'
      : 'GENERATE PLANS';
  const currentStateClassName = isExecuting
    ? 'text-emerald-300'
    : isAwaitingApproval
      ? 'text-purple-300'
      : isAnomaly
        ? 'text-orange-300'
        : isPaused
          ? 'text-yellow-300'
          : isCompleted
            ? 'text-cyan-300'
            : isRunning
              ? 'text-green-300'
              : 'text-white';

  const hasError =
    startError ||
    pauseError ||
    resumeError ||
    injectAnomalyError ||
    generatePlansError ||
    resetError;

  return (
    <div className={clsx('space-y-4', className)}>
      <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-gray-300">
        <span className="h-2 w-2 rounded-full bg-gray-400" />
        MISSION CONTROLS
      </h3>

      {hasError && (
        <div className="space-y-1 rounded-2xl border border-red-800 bg-red-900/30 p-4 text-sm font-mono text-red-300">
          {startError && <div>START: {startError}</div>}
          {pauseError && <div>PAUSE: {pauseError}</div>}
          {resumeError && <div>RESUME: {resumeError}</div>}
          {injectAnomalyError && <div>ANOMALY: {injectAnomalyError}</div>}
          {generatePlansError && <div>GENERATE: {generatePlansError}</div>}
          {resetError && <div>RESET: {resetError}</div>}
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <ControlButton onClick={onStart} disabled={!isIdle} variant="primary">
          START MISSION
        </ControlButton>

        <ControlButton onClick={onPause} disabled={!canPause} variant="warning">
          PAUSE
        </ControlButton>

        <ControlButton onClick={onResume} disabled={!canResume} variant="primary">
          RESUME
        </ControlButton>

        <ControlButton onClick={onInjectAnomaly} disabled={!isRunning} variant="danger">
          INJECT ANOMALY
        </ControlButton>

        <ControlButton onClick={onGeneratePlans} disabled={!canManagePlans} variant="secondary">
          {planButtonLabel}
        </ControlButton>

        <ControlButton onClick={onReset} disabled={false} variant="secondary">
          RESET MISSION
        </ControlButton>
      </div>

      <div className="rounded-2xl border border-gray-700 bg-gray-900/50 p-4 text-xs">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <span className="font-mono text-gray-500">CURRENT STATE:</span>
          <span
            data-testid="current-mission-state"
            className={clsx('font-mono', currentStateClassName)}
          >
            {missionStatus ?? 'UNKNOWN'}
          </span>
        </div>

        <div className="grid grid-cols-1 gap-2 text-[10px] sm:grid-cols-2 lg:grid-cols-3">
          <div className={`flex items-center gap-1 ${isRunning ? 'text-green-400' : 'text-gray-500'}`}>
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            RUNNING
          </div>
          <div className={`flex items-center gap-1 ${isExecuting ? 'text-emerald-400' : 'text-gray-500'}`}>
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            EXECUTING
          </div>
          <div className={`flex items-center gap-1 ${isPaused ? 'text-yellow-400' : 'text-gray-500'}`}>
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            PAUSED
          </div>
          <div className={`flex items-center gap-1 ${isCompleted ? 'text-cyan-400' : 'text-gray-500'}`}>
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            COMPLETED
          </div>
          <div className={`flex items-center gap-1 ${isAnomaly ? 'text-orange-400' : 'text-gray-500'}`}>
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            ANOMALY
          </div>
          <div className={`flex items-center gap-1 ${isAwaitingApproval ? 'text-purple-400' : 'text-gray-500'}`}>
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            AWAITING APPROVAL
          </div>
        </div>

        {anomalyActive && isAnomaly && (
          <div className="mt-3 rounded-xl border border-orange-800 bg-orange-900/30 p-3 text-[10px] font-mono leading-relaxed text-orange-300">
            BATTERY ANOMALY ACTIVE - Generate recovery plans
          </div>
        )}
        {isAwaitingApproval && candidatePlansCount > 0 && (
          <div className="mt-3 rounded-xl border border-purple-800 bg-purple-900/30 p-3 text-[10px] font-mono leading-relaxed text-purple-300">
            {candidatePlansCount} CANDIDATE PLAN(S) AVAILABLE - Review and approve. Mission is in AWAITING APPROVAL after plan generation.
          </div>
        )}
        {isExecuting && anomalyActive && (
          <div className="mt-3 rounded-xl border border-emerald-800 bg-emerald-900/30 p-3 text-[10px] font-mono leading-relaxed text-emerald-300">
            BATTERY ANOMALY ACTIVE - Recovery plan executing
          </div>
        )}
      </div>
    </div>
  );
}
