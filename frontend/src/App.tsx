/** LunaYield Mission Lab - Main Application */

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
} from './hooks/useMission';
import { useMissionSocket } from './hooks/useMissionSocket';
import {
  MissionHeader,
  ResourcePanel,
  TelemetryPanel,
  RoutePanel,
  PlanComparison,
  AuditPanel,
  MissionControls,
  ForecastPanel,
  AnomalyPanel,
  StrategyPanel,
} from './components';
import type { TelemetrySample } from './types/mission';
import { PlanStatus } from './types/mission';

function MissionControl() {
  // Mission state queries
  const { data: mission, isLoading, error: queryError } = useMissionState();
  const missionStatus = useMissionStatus();
  const resources = useMissionResources();
  const candidatePlans = useCandidatePlans() ?? [];
  const auditTrail = useAuditTrail();
  const activeRoute = useActiveRoute();
  const originalRoute = useOriginalRoute();
  const anomalyActive = useAnomalyActive();

  // Forecast, Anomaly, and Strategy queries
  const [forecastHorizon, setForecastHorizon] = useState<number>(3600);
  const {
    data: forecast,
    isLoading: forecastLoading,
    error: forecastError,
  } = useForecast({ horizon: forecastHorizon, interval: 60 });
  const {
    data: anomalies,
    isLoading: anomaliesLoading,
    error: anomaliesError,
  } = useAnomalies({ use_forecast: true, forecast_horizon: forecastHorizon });
  const {
    data: strategies,
    isLoading: strategiesLoading,
    error: strategiesError,
  } = useStrategies({ use_forecast: true, forecast_horizon: forecastHorizon });

  // Find approved plan label from backend-provided candidate plans
  const approvedPlanLabel = candidatePlans.find((p) => p.status === PlanStatus.APPROVED)?.label;

  // Live telemetry state (updated via WebSocket only)
  const [liveTelemetry, setLiveTelemetry] = useState<TelemetrySample | null>(null);
  const [lastMissionId, setLastMissionId] = useState<string | null>(null);

  // Mutations
  const startMission = useStartMission();
  const pauseMission = usePauseMission();
  const resumeMission = useResumeMission();
  const resetMission = useResetMission();
  const injectAnomaly = useInjectAnomaly();
  const generatePlans = useGeneratePlans();
  const approvePlan = useApprovePlan();

  // Error messages from mutations
  const startError = useMissionError(startMission);
  const pauseError = useMissionError(pauseMission);
  const resumeError = useMissionError(resumeMission);
  const resetError = useMissionError(resetMission);
  const injectAnomalyError = useMissionError(injectAnomaly);
  const generatePlansError = useMissionError(generatePlans);
  const approvePlanError = useMissionError(approvePlan);

  // WebSocket connection
  const { connectionStatus } = useMissionSocket({
    enabled: true,
    onTelemetryUpdate: setLiveTelemetry,
  });

  // Handle plan approval
  const handleApprovePlan = (planId: string) => {
    approvePlan.mutate(planId);
  };

  // Clear stale telemetry when mission ID changes or mission is reset
  useEffect(() => {
    if (mission?.mission_id && mission.mission_id !== lastMissionId) {
      setLiveTelemetry(null);
      setLastMissionId(mission.mission_id);
    }
  }, [mission?.mission_id, lastMissionId]);

  // Clear telemetry on reset mutation success
  useEffect(() => {
    if (resetMission.isSuccess) {
      setLiveTelemetry(null);
      setLastMissionId(null);
    }
  }, [resetMission.isSuccess]);

  // Show loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-yellow-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400 font-mono">INITIALIZING MISSION CONTROL...</p>
        </div>
      </div>
    );
  }

  // Show query error
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
            className="mt-6 px-6 py-2 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded font-mono hover:bg-blue-500/30 transition-colors"
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
        <div className="max-w-7xl mx-auto">
          {/* Main Grid Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 lg:gap-6">
            {/* Left Column - Resources, Telemetry, Route */}
            <div className="lg:col-span-2 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <ResourcePanel resources={liveTelemetry?.resources ?? resources} />
                <TelemetryPanel telemetry={liveTelemetry} />
              </div>
              <RoutePanel
                activeRoute={activeRoute}
                originalRoute={originalRoute}
                approvedPlanLabel={approvedPlanLabel}
              />
              {/* Forecast, Anomaly & Strategy Panels */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <ForecastPanel
                  forecast={forecast}
                  isLoading={forecastLoading}
                  error={forecastError}
                  horizon={forecastHorizon}
                  onHorizonChange={setForecastHorizon}
                />
                <AnomalyPanel
                  anomalies={anomalies}
                  isLoading={anomaliesLoading}
                  error={anomaliesError}
                />
                <StrategyPanel
                  strategies={strategies}
                  isLoading={strategiesLoading}
                  error={strategiesError}
                />
              </div>
            </div>

            {/* Right Column - Controls, Plans, Audit */}
            <div className="lg:col-span-1 space-y-4">
              <MissionControls
                missionStatus={missionStatus}
                anomalyActive={anomalyActive}
                candidatePlansCount={candidatePlans.length}
                onStart={() => startMission.mutate()}
                onPause={() => pauseMission.mutate()}
                onResume={() => resumeMission.mutate()}
                onInjectAnomaly={() => injectAnomaly.mutate()}
                onGeneratePlans={() => generatePlans.mutate()}
                onReset={() => resetMission.mutate()}
                startError={startError}
                pauseError={pauseError}
                resumeError={resumeError}
                injectAnomalyError={injectAnomalyError}
                generatePlansError={generatePlansError}
                resetError={resetError}
              />

              {candidatePlans.length > 0 && (
                <PlanComparison
                  plans={candidatePlans}
                  onApprove={handleApprovePlan}
                  disabled={approvePlan.isPending}
                />
              )}

              {/* Approve error display */}
              {approvePlanError && (
                <div className="p-3 bg-red-900/30 border border-red-800 rounded text-red-300 text-sm font-mono">
                  APPROVAL FAILED: {approvePlanError}
                </div>
              )}

              <AuditPanel events={auditTrail} />
            </div>
          </div>

          {/* Footer */}
          <div className="mt-6 pt-4 border-t border-gray-800 text-center">
            <p className="text-xs text-gray-500 font-mono">
              LunaYield Mission Lab - Phase 1 Demo
              {' | '}
              <span className="text-yellow-500">BACKEND AUTHORITATIVE</span>
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <div className="min-h-screen bg-gray-950">
      <MissionControl />
    </div>
  );
}