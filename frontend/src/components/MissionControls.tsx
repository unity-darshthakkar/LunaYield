/** Mission controls with state-aware buttons */

import type { MissionStatus } from '../types/mission';
import { clsx } from 'clsx';

interface MissionControlsProps {
  missionStatus: MissionStatus | undefined;
  anomalyActive: boolean | undefined;
  candidatePlansCount: number;
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
    primary: 'bg-blue-500/20 text-blue-400 border border-blue-500/30 hover:bg-blue-500/30 disabled:opacity-50 disabled:cursor-not-allowed',
    secondary: 'bg-gray-700 text-gray-300 border border-gray-600 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed',
    danger: 'bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 disabled:opacity-50 disabled:cursor-not-allowed',
    warning: 'bg-orange-500/20 text-orange-400 border border-orange-500/30 hover:bg-orange-500/30 disabled:opacity-50 disabled:cursor-not-allowed',
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        'px-4 py-2 rounded font-mono text-sm font-medium transition-colors w-full sm:w-auto',
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

  // Any error state for display
  const hasError = startError || pauseError || resumeError || injectAnomalyError || generatePlansError || resetError;

  return (
    <div className={clsx('space-y-4', className)}>
      <h3 className="text-sm font-semibold text-gray-300 mb-2 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-gray-400" />
        MISSION CONTROLS
      </h3>

      {/* Error Display */}
      {hasError && (
        <div className="p-3 bg-red-900/30 border border-red-800 rounded text-red-300 text-sm font-mono space-y-1">
          {startError && <div>START: {startError}</div>}
          {pauseError && <div>PAUSE: {pauseError}</div>}
          {resumeError && <div>RESUME: {resumeError}</div>}
          {injectAnomalyError && <div>ANOMALY: {injectAnomalyError}</div>}
          {generatePlansError && <div>GENERATE: {generatePlansError}</div>}
          {resetError && <div>RESET: {resetError}</div>}
        </div>
      )}

      {/* Primary Action Buttons */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <ControlButton
          onClick={onStart}
          disabled={!isIdle}
          variant="primary"
        >
          START MISSION
        </ControlButton>

        <ControlButton
          onClick={onPause}
          disabled={!isRunning}
          variant="warning"
        >
          PAUSE
        </ControlButton>

        <ControlButton
          onClick={onResume}
          disabled={!isPaused}
          variant="primary"
        >
          RESUME
        </ControlButton>

        <ControlButton
          onClick={onInjectAnomaly}
          disabled={!isRunning}
          variant="danger"
        >
          INJECT ANOMALY
        </ControlButton>

        <ControlButton
          onClick={onGeneratePlans}
          disabled={!isAnomaly}
          variant="secondary"
        >
          GENERATE PLANS
        </ControlButton>

        <ControlButton
          onClick={onReset}
          disabled={hasError} // Reset always available unless error
          variant="secondary"
        >
          RESET MISSION
        </ControlButton>
      </div>

      {/* Status Context */}
      <div className="p-3 bg-gray-900/50 rounded border border-gray-700 text-xs">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-gray-500 font-mono">CURRENT STATE:</span>
          <span className="text-white font-mono">{missionStatus ?? 'UNKNOWN'}</span>
        </div>
        <div className="grid grid-cols-2 gap-2 text-[10px]">
          <div className={`flex items-center gap-1 ${isRunning ? 'text-green-400' : 'text-gray-500'}`}>
            <span className="w-1.5 h-1.5 rounded-full bg-current" />
            RUNNING
          </div>
          <div className={`flex items-center gap-1 ${isPaused ? 'text-yellow-400' : 'text-gray-500'}`}>
            <span className="w-1.5 h-1.5 rounded-full bg-current" />
            PAUSED
          </div>
          <div className={`flex items-center gap-1 ${isAnomaly ? 'text-orange-400' : 'text-gray-500'}`}>
            <span className="w-1.5 h-1.5 rounded-full bg-current" />
            ANOMALY
          </div>
          <div className={`flex items-center gap-1 ${isAwaitingApproval ? 'text-purple-400' : 'text-gray-500'}`}>
            <span className="w-1.5 h-1.5 rounded-full bg-current" />
            AWAITING APPROVAL
          </div>
        </div>
        {anomalyActive && (
          <div className="mt-2 p-2 bg-orange-900/30 border border-orange-800 rounded text-orange-300 font-mono text-[10px]">
            ⚠ BATTERY ANOMALY ACTIVE — Generate recovery plans
          </div>
        )}
        {candidatePlansCount > 0 && (
          <div className="mt-2 p-2 bg-purple-900/30 border border-purple-800 rounded text-purple-300 font-mono text-[10px]">
            {candidatePlansCount} CANDIDATE PLAN(S) AVAILABLE — Review and approve
          </div>
        )}
      </div>
    </div>
  );
}