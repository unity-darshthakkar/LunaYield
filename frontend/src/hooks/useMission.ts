/** React Query hooks for mission state and mutations */

import {
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryOptions,
  UseMutationOptions,
} from '@tanstack/react-query';
import type { Mission, CandidatePlan, RoverResources, MissionForecastResponse, AnomalyDetectionResponse } from '../types/mission';
import {
  getMissionState,
  getScenario,
  startMission,
  pauseMission,
  resumeMission,
  resetMission,
  injectAnomaly,
  generatePlans,
  approvePlan,
  getForecast,
  getAnomalies,
  type ScenarioResponse,
  type ForecastParams,
  type AnomalyParams,
} from '../api/mission';

// Query keys
export const missionKeys = {
  all: ['mission'] as const,
  state: () => [...missionKeys.all, 'state'] as const,
  scenario: () => ['scenario'] as const,
  forecast: (params?: ForecastParams) =>
    [...missionKeys.all, 'forecast', params] as const,
  anomalies: (params?: AnomalyParams) =>
    [...missionKeys.all, 'anomalies', params] as const,
};

// Query hooks

export function useMissionState(
  options?: UseQueryOptions<Mission, Error, Mission, typeof missionKeys.state>
) {
  return useQuery({
    queryKey: missionKeys.state(),
    queryFn: getMissionState,
    staleTime: 1000, // Short stale time for near-live feel
    refetchOnWindowFocus: false,
    ...options,
  });
}

export function useScenario(
  options?: UseQueryOptions<ScenarioResponse, Error, ScenarioResponse, typeof missionKeys.scenario>
) {
  return useQuery({
    queryKey: missionKeys.scenario(),
    queryFn: getScenario,
    staleTime: Infinity, // Scenario never changes
    ...options,
  });
}

export function useForecast(
  params?: ForecastParams,
  options?: UseQueryOptions<MissionForecastResponse, Error, MissionForecastResponse, ReturnType<typeof missionKeys.forecast>>
) {
  return useQuery({
    queryKey: missionKeys.forecast(params),
    queryFn: () => getForecast(params),
    staleTime: 2000, // Forecast updates periodically
    refetchOnWindowFocus: false,
    ...options,
  });
}

export function useAnomalies(
  params?: AnomalyParams,
  options?: UseQueryOptions<AnomalyDetectionResponse, Error, AnomalyDetectionResponse, ReturnType<typeof missionKeys.anomalies>>
) {
  return useQuery({
    queryKey: missionKeys.anomalies(params),
    queryFn: () => getAnomalies(params),
    staleTime: 2000, // Anomalies update periodically
    refetchOnWindowFocus: false,
    ...options,
  });
}

// Mutation hooks

export function useStartMission(
  options?: UseMutationOptions<Mission, Error, void, unknown>
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: startMission,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: missionKeys.state() });
    },
    ...options,
  });
}

export function usePauseMission(
  options?: UseMutationOptions<Mission, Error, void, unknown>
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: pauseMission,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: missionKeys.state() });
    },
    ...options,
  });
}

export function useResumeMission(
  options?: UseMutationOptions<Mission, Error, void, unknown>
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: resumeMission,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: missionKeys.state() });
    },
    ...options,
  });
}

export function useResetMission(
  options?: UseMutationOptions<Mission, Error, void, unknown>
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: resetMission,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: missionKeys.state() });
      queryClient.invalidateQueries({ queryKey: missionKeys.scenario() });
    },
    ...options,
  });
}

export function useInjectAnomaly(
  options?: UseMutationOptions<Mission, Error, void, unknown>
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: injectAnomaly,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: missionKeys.state() });
    },
    ...options,
  });
}

export function useGeneratePlans(
  options?: UseMutationOptions<CandidatePlan[], Error, void, unknown>
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: generatePlans,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: missionKeys.state() });
    },
    ...options,
  });
}

export function useApprovePlan(
  options?: UseMutationOptions<CandidatePlan, Error, string, unknown>
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: approvePlan,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: missionKeys.state() });
    },
    ...options,
  });
}

// Helper hook for typed error extraction
export function useMissionError(
  mutation: ReturnType<typeof useStartMission | typeof usePauseMission | typeof useResumeMission | typeof useResetMission | typeof useInjectAnomaly | typeof useGeneratePlans | typeof useApprovePlan>
): string | null {
  if (mutation.isError && mutation.error) {
    // The axios interceptor adds userMessage to the error
    const axiosError = mutation.error as Error & { userMessage?: string };
    return axiosError.userMessage ?? mutation.error.message;
  }
  return null;
}

// Derived state helpers
export function useMissionResources(): RoverResources | undefined {
  const { data: mission } = useMissionState();
  return mission?.resources;
}

export function useMissionStatus(): Mission['status'] | undefined {
  const { data: mission } = useMissionState();
  return mission?.status;
}

export function useCandidatePlans(): CandidatePlan[] | undefined {
  const { data: mission } = useMissionState();
  return mission?.candidate_plans;
}

export function useAuditTrail(): Mission['audit_trail'] | undefined {
  const { data: mission } = useMissionState();
  return mission?.audit_trail;
}

export function useActiveRoute(): Mission['active_route'] | undefined {
  const { data: mission } = useMissionState();
  return mission?.active_route;
}

export function useOriginalRoute(): Mission['original_route'] | undefined {
  const { data: mission } = useMissionState();
  return mission?.original_route;
}

export function useAnomalyActive(): boolean | undefined {
  const { data: mission } = useMissionState();
  return mission?.anomaly_active;
}

export function useElapsedTime(): number | undefined {
  const { data: mission } = useMissionState();
  return mission?.elapsed_s;
}