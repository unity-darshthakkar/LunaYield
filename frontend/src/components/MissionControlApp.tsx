/** LunaYield Mission Control App - Extracted core Mission Control composition */

import { useState, useEffect } from 'react';
import {
  useMissionState,
  useStartMission,
  usePauseMission,
  useResumeMission,
  useResetMission,
  useInjectAnomaly,
  useGeneratePlans,
  useApprovePlan,
  useMissionError,
  useCandidatePlans,
  useAuditTrail,
  useActiveRoute,
  useOriginalRoute,
  useAnomalyActive,
  useMissionStatus,
  useMissionResources,
  useForecast,
  useAnomalies,
  useStrategies,
  useValidateStrategies,
} from '../hooks/useMission';
import { useMissionSocket } from '../hooks/useMissionSocket';

import { MissionHeader } from './MissionHeader';
import { ResourcePanel } from './ResourcePanel';
import { TelemetryPanel } from './TelemetryPanel';
import { RoutePanel } from './RoutePanel';
import { PlanComparison } from './PlanComparison';
import { AuditPanel } from './AuditPanel';
import { MissionControls } from './MissionControls';
import { ForecastPanel } from './ForecastPanel';
import { AnomalyPanel } from './AnomalyPanel';
import { StrategyPanel } from './StrategyPanel';

import type { TelemetrySample } from '../types/mission';
import { PlanStatus } from '../types/mission';

export function MissionControlApp() {
  const { data: mission, isLoading, error: queryError } = useMissionState();
  const missionStatus = useMissionStatus();
  const resources = useMissionResources();
  const candidatePlans = useCandidatePlans() ?? [];
  const auditTrail = useAuditTrail();
  const activeRoute = useActiveRoute();
  const originalRoute = useOriginalRoute();
  const anomalyActive = useAnomalyActive();

  const [forecastHorizon, setForecastHorizon] = useState<number>(3600);
  const forecastParams = { horizon: forecastHorizon, interval: 60 };
  const anomalyStrategyParams = { use_forecast: true, forecast_horizon: forecastHorizon };

  const {
    data: forecast,
    isLoading: forecastLoading,
    error: forecastError,
  } = useForecast(forecastParams);
  const {
    data: anomalies,
    isLoading: anomaliesLoading,
    error: anomaliesError,
  } = useAnomalies(anomalyStrategyParams);
  const {
    data: strategies,
    isLoading: strategiesLoading,
    error: strategiesError,
  } = useStrategies(anomalyStrategyParams);
  const {
    data: validation,
    isLoading: validationLoading,
    error: validationError,
  } = useValidateStrategies(anomalyStrategyParams);

  const approvedPlan = candidatePlans.find((plan) => plan.status === PlanStatus.APPROVED) ?? null;
  const approvedPlanLabel = approvedPlan?.label;

  const [liveTelemetry, setLiveTelemetry] = useState<TelemetrySample | null>(null);
  const [lastMissionId, setLastMissionId] = useState<string | null>(null);
  const [auditOpen, setAuditOpen] = useState(false);
  const [showAnomalies, setShowAnomalies] = useState(false);
  const [showStrategies, setShowStrategies] = useState(false);
  const [plansOpen, setPlansOpen] = useState(false);

  const startMission = useStartMission();
  const pauseMission = usePauseMission();
  const resumeMission = useResumeMission();
  const resetMission = useResetMission();
  const injectAnomaly = useInjectAnomaly();
  const generatePlans = useGeneratePlans();
  const approvePlan = useApprovePlan();

  const startError = useMissionError(startMission);
  const pauseError = useMissionError(pauseMission);
  const resumeError = useMissionError(resumeMission);
  const resetError = useMissionError(resetMission);
  const injectAnomalyError = useMissionError(injectAnomaly);
  const generatePlansError = useMissionError(generatePlans);
  const approvePlanError = useMissionError(approvePlan);

  const { connectionStatus } = useMissionSocket({
    enabled: true,
    onTelemetryUpdate: setLiveTelemetry,
  });

  const handleApprovePlan = (planId: string) => {
    setPlansOpen(false);
    approvePlan.mutate(planId);
  };

  useEffect(() => {
    if (mission?.mission_id && mission.mission_id !== lastMissionId) {
      setLiveTelemetry(null);
      setLastMissionId(mission.mission_id);
      setPlansOpen(false);
    }
  }, [mission?.mission_id, lastMissionId]);

  useEffect(() => {
    if (resetMission.isSuccess) {
      setLiveTelemetry(null);
      setLastMissionId(null);
      setPlansOpen(false);
    }
  }, [resetMission.isSuccess]);

  useEffect(() => {
    if (candidatePlans.length > 0) {
      setPlansOpen(true);
    } else {
      setPlansOpen(false);
    }
  }, [candidatePlans.length]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400 font-mono">INITIALIZING MISSION CONTROL...</p>
        </div>
      </div>
    );
  }

  if (queryError) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 mx-auto mb-4 bg-red-900/30 rounded-full flex items-center justify-center">
            <svg className="w-8 h-8 text-red-400" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-white mb-2">CONNECTION FAILED</h2>
          <p className="text-gray-400 mb-4">
            Unable to connect to mission backend. Ensure the API server is running.
          </p>
          <p className="text-sm text-gray-500 font-mono">{queryError.message}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-6 px-6 py-2 bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 rounded font-mono hover:bg-cyan-500/30 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/50 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-950"
          >
            RETRY CONNECTION
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white font-mono">
      <MissionHeader
        missionStatus={missionStatus}
        wsStatus={connectionStatus}
      />

      <main className="p-4 md:p-6 lg:p-8">
        <div className="mx-auto max-w-[1500px]">
          <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
            <div className="space-y-5">
              <div className="grid grid-cols-1 gap-5">
                <ResourcePanel resources={liveTelemetry?.resources ?? resources} />
              </div>
              <RoutePanel
                activeRoute={activeRoute}
                originalRoute={originalRoute}
                approvedPlanLabel={approvedPlanLabel}
              />
            </div>

            <div className="space-y-5 xl:sticky xl:top-24 xl:self-start">
              <MissionControls
                missionStatus={missionStatus}
                anomalyActive={anomalyActive}
                candidatePlansCount={candidatePlans.length}
                approvedPlanLabel={approvedPlanLabel}
                onStart={() => startMission.mutate()}
                onPause={() => pauseMission.mutate()}
                onResume={() => resumeMission.mutate()}
                onInjectAnomaly={() => injectAnomaly.mutate()}
                onGeneratePlans={() => {
                  if (candidatePlans.length > 0) {
                    setPlansOpen(true);
                    return;
                  }
                  generatePlans.mutate();
                }}
                onReset={() => resetMission.mutate()}
                startError={startError}
                pauseError={pauseError}
                resumeError={resumeError}
                injectAnomalyError={injectAnomalyError}
                generatePlansError={generatePlansError}
                resetError={resetError}
              />
              <TelemetryPanel telemetry={liveTelemetry} />
            </div>
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => setShowAnomalies((current) => !current)}
              className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] transition-colors ${
                showAnomalies
                  ? 'border-amber-400/30 bg-amber-500/15 text-amber-200'
                  : 'border-white/10 bg-white/5 text-slate-300 hover:bg-white/10 hover:text-white'
              }`}
            >
              <span className={`h-2 w-2 rounded-full ${showAnomalies ? 'bg-amber-300' : 'bg-slate-500'}`} />
              {showAnomalies ? 'Hide Anomaly' : 'Show Anomaly'}
            </button>
            <button
              type="button"
              onClick={() => setShowStrategies((current) => !current)}
              className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] transition-colors ${
                showStrategies
                  ? 'border-cyan-400/30 bg-cyan-500/15 text-cyan-200'
                  : 'border-white/10 bg-white/5 text-slate-300 hover:bg-white/10 hover:text-white'
              }`}
            >
              <span className={`h-2 w-2 rounded-full ${showStrategies ? 'bg-cyan-300' : 'bg-slate-500'}`} />
              {showStrategies ? 'Hide Solution' : 'Show Solution'}
            </button>
          </div>

          <div className="mt-5 grid grid-cols-1 gap-5 xl:grid-cols-12">
            <div className={`${showAnomalies && showStrategies ? 'xl:col-span-4' : showAnomalies || showStrategies ? 'xl:col-span-6' : 'xl:col-span-12'}`}>
              <ForecastPanel
                forecast={forecast}
                isLoading={forecastLoading}
                error={forecastError}
                horizon={forecastHorizon}
                onHorizonChange={setForecastHorizon}
              />
            </div>
            {showAnomalies && (
              <div className={showStrategies ? 'xl:col-span-4' : 'xl:col-span-6'}>
                <AnomalyPanel
                  anomalies={anomalies}
                  isLoading={anomaliesLoading}
                  error={anomaliesError}
                />
              </div>
            )}
            {showStrategies && (
              <div className={showAnomalies ? 'xl:col-span-4' : 'xl:col-span-6'}>
                <StrategyPanel
                  strategies={strategies}
                  validation={validation}
                  validationError={validationError}
                  isLoading={strategiesLoading}
                  error={strategiesError}
                  validationLoading={validationLoading}
                  forecastHorizon={forecastHorizon}
                  useForecast={true}
                />
              </div>
            )}
          </div>

          <div className="mt-5 grid grid-cols-1 gap-5">
            <div className="space-y-5">
              {approvePlanError && (
                <div className="p-3 bg-red-900/30 border border-red-800 rounded text-red-300 text-sm font-mono">
                  APPROVAL FAILED: {approvePlanError}
                </div>
              )}
            </div>
          </div>

          <div className="mt-8 border-t border-gray-800 pt-5 text-center">
            <p className="text-xs text-gray-500 font-mono">
              LunaYield Mission Lab - IBM Space Exploration Hackathon
              {' | '}
              <span className="text-cyan-500">BACKEND AUTHORITATIVE</span>
              {' | '}
              <span className="text-amber-500">APPROVAL != EXECUTION</span>
            </p>
          </div>
        </div>
      </main>

      <div className="fixed bottom-5 right-5 z-50 flex max-w-[calc(100vw-2.5rem)] flex-col items-end gap-3 md:bottom-6 md:right-6">
        {auditOpen && (
          <div className="w-[min(30rem,calc(100vw-2.5rem))] rounded-[1.4rem] border border-white/10 bg-slate-950/95 p-4 shadow-[0_24px_80px_rgba(2,6,23,0.6)] backdrop-blur-xl">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-gray-300">
                <span className="h-2 w-2 rounded-full bg-cyan-400" />
                AUDIT TRAIL
              </div>
              <button
                type="button"
                onClick={() => setAuditOpen(false)}
                className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 text-gray-300 transition-colors hover:bg-white/10 hover:text-white"
                aria-label="Close audit trail"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 6l12 12M18 6L6 18" />
                </svg>
              </button>
            </div>
            <AuditPanel events={auditTrail} className="border-0 bg-transparent p-0" />
          </div>
        )}

        {!auditOpen && (
          <button
            type="button"
            onClick={() => setAuditOpen(true)}
            className="inline-flex h-14 items-center gap-3 rounded-full border border-cyan-400/20 bg-slate-950/90 px-5 py-3 text-sm font-semibold text-cyan-200 shadow-[0_18px_50px_rgba(2,6,23,0.5)] backdrop-blur-xl transition-colors hover:bg-slate-900 hover:text-white"
            aria-label="Open audit trail"
          >
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-cyan-500/15 text-cyan-200">
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h8M8 14h5M7 4h10a3 3 0 013 3v7a3 3 0 01-3 3h-4l-4 3v-3H7a3 3 0 01-3-3V7a3 3 0 013-3z" />
              </svg>
            </span>
            Audit Trail
          </button>
        )}
      </div>

      {plansOpen && candidatePlans.length > 0 && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-sm">
          <div className="relative w-full max-w-6xl rounded-[1.4rem] border border-white/10 bg-slate-950/95 p-4 shadow-[0_30px_100px_rgba(2,6,23,0.72)] backdrop-blur-xl md:p-5">
            <div className="mb-4 flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-purple-200">
                  Candidate Plans
                </p>
                <h3 className="mt-1 text-xl font-semibold text-white">Generated mission plans</h3>
                <p className="mt-1 text-sm text-slate-400">
                  Review the generated options and approve a valid plan directly from this popup.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setPlansOpen(false)}
                className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/5 text-gray-300 transition-colors hover:bg-white/10 hover:text-white"
                aria-label="Close plans popup"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 6l12 12M18 6L6 18" />
                </svg>
              </button>
            </div>

            <PlanComparison
              plans={candidatePlans}
              onApprove={handleApprovePlan}
              selectedPlanId={approvedPlan?.plan_id ?? null}
              disabled={approvePlan.isPending}
              className="max-h-[72vh] overflow-y-auto pr-1 [&>div:last-child]:grid [&>div:last-child]:grid-cols-1 [&>div:last-child]:gap-4 lg:[&>div:last-child]:grid-cols-3"
            />
          </div>
        </div>
      )}
    </div>
  );
}