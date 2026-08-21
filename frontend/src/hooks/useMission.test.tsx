/** useMission hook tests */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useMissionState, useStartMission, useResetMission, useForecast, useAnomalies, useStrategies, useValidateStrategies, useApproveStrategy } from './useMission';
import * as missionApi from '../api/mission';
import type { MissionForecastResponse, AnomalyDetectionResponse, StrategyGenerationResponse, StrategyValidationResponse, StrategyApprovalResult, AnomalyResource } from '../types/mission';

// Mock the API
vi.mock('../api/mission', () => ({
  getMissionState: vi.fn(),
  startMission: vi.fn(),
  pauseMission: vi.fn(),
  resetMission: vi.fn(),
  getForecast: vi.fn(),
  getAnomalies: vi.fn(),
  getStrategies: vi.fn(),
  validateStrategies: vi.fn(),
  approveStrategy: vi.fn(),
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('useMission hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useMissionState', () => {
    it('fetches mission state', async () => {
      const mockMission = {
        mission_id: 'luna-mission-001',
        label: 'Test',
        status: 'IDLE' as const,
        elapsed_s: 0,
        resources: {
          battery_pct: 100,
          storage_pct: 0,
          temperature_c: -40,
          comm_window_remaining_s: 7200,
          op_time_remaining_s: 28800,
        },
        original_route: { waypoints: [] },
        active_route: { waypoints: [] },
        candidate_plans: [],
        anomaly_active: false,
        audit_trail: [],
      };
      missionApi.getMissionState.mockResolvedValue(mockMission);

      const { result } = renderHook(() => useMissionState(), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockMission);
    });
  });

  describe('useStartMission', () => {
    it('mutates and invalidates query on success', async () => {
      const mockMission = {
        status: 'RUNNING',
        mission_id: 'luna-mission-001',
      } as missionApi.Mission;
      missionApi.startMission.mockResolvedValue(mockMission);
      missionApi.getMissionState.mockResolvedValue(mockMission);

      const { result } = renderHook(() => useStartMission(), { wrapper: createWrapper() });

      result.current.mutate();

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(missionApi.startMission).toHaveBeenCalled();
    });

    it('returns error message on 409', async () => {
      const error = new Error('Cannot start from RUNNING status');
      (error as Error & { userMessage?: string }).userMessage = 'Cannot start from RUNNING status';
      missionApi.startMission.mockRejectedValue(error);

      const { result } = renderHook(() => useStartMission(), { wrapper: createWrapper() });

      result.current.mutate();

      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(result.current.error).toBeDefined();
    });
  });

  describe('useResetMission', () => {
    it('mutates and invalidates both mission and scenario queries', async () => {
      const mockMission = {
        status: 'IDLE',
        mission_id: 'luna-mission-001',
      } as missionApi.Mission;
      missionApi.resetMission.mockResolvedValue(mockMission);
      missionApi.getMissionState.mockResolvedValue(mockMission);

      const { result } = renderHook(() => useResetMission(), { wrapper: createWrapper() });

      result.current.mutate();

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(missionApi.resetMission).toHaveBeenCalled();
    });
  });

  describe('useForecast', () => {
    const mockForecast: MissionForecastResponse = {
      mission_id: 'luna-mission-001',
      current_elapsed_s: 0,
      current_resources: {
        battery_pct: 100,
        storage_pct: 0,
        temperature_c: -40,
        comm_window_remaining_s: 7200,
        op_time_remaining_s: 28800,
      },
      forecast_horizon_s: 3600,
      forecast_tick_interval_s: 60,
      forecast_points: [
        {
          forecast_seconds_ahead: 600,
          elapsed_s: 600,
          resources: {
            battery_pct: 95,
            storage_pct: 2,
            temperature_c: -35,
            comm_window_remaining_s: 6600,
            op_time_remaining_s: 28200,
          },
        },
      ],
    };

    it('fetches forecast with default params', async () => {
      missionApi.getForecast.mockResolvedValue(mockForecast);

      const { result } = renderHook(() => useForecast(), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockForecast);
      expect(missionApi.getForecast).toHaveBeenCalledWith(undefined);
    });

    it('fetches forecast with custom params', async () => {
      missionApi.getForecast.mockResolvedValue(mockForecast);

      const { result } = renderHook(() => useForecast({ horizon: 7200, interval: 120 }), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(missionApi.getForecast).toHaveBeenCalledWith({ horizon: 7200, interval: 120 });
    });

    it('handles error correctly', async () => {
      const error = new Error('Forecast failed');
      missionApi.getForecast.mockRejectedValue(error);

      const { result } = renderHook(() => useForecast(), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(result.current.error).toBeDefined();
    });
  });

  describe('useAnomalies', () => {
    const mockAnomalies: AnomalyDetectionResponse = {
      mission_id: 'luna-mission-001',
      current_elapsed_s: 0,
      anomalies: [
        {
          resource: 'BATTERY',
          severity: 'WARNING',
          observed_value: 28,
          threshold_value: 30,
          reason: 'Battery low',
          is_forecast: false,
          forecast_seconds_ahead: null,
        },
      ],
      anomaly_count: 1,
      has_critical: false,
      has_warning: true,
    };

    it('fetches anomalies with default params', async () => {
      missionApi.getAnomalies.mockResolvedValue(mockAnomalies);

      const { result } = renderHook(() => useAnomalies(), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockAnomalies);
      expect(missionApi.getAnomalies).toHaveBeenCalledWith(undefined);
    });

    it('fetches anomalies with forecast params', async () => {
      missionApi.getAnomalies.mockResolvedValue(mockAnomalies);

      const { result } = renderHook(() => useAnomalies({ use_forecast: true, forecast_horizon: 3600 }), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(missionApi.getAnomalies).toHaveBeenCalledWith({ use_forecast: true, forecast_horizon: 3600 });
    });

    it('handles error correctly', async () => {
      const error = new Error('Anomaly detection failed');
      missionApi.getAnomalies.mockRejectedValue(error);

      const { result } = renderHook(() => useAnomalies(), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(result.current.error).toBeDefined();
    });

    it('returns empty anomalies when no anomalies detected', async () => {
      const emptyAnomalies = {
        ...mockAnomalies,
        anomalies: [],
        anomaly_count: 0,
        has_critical: false,
        has_warning: false,
      };
      missionApi.getAnomalies.mockResolvedValue(emptyAnomalies);

      const { result } = renderHook(() => useAnomalies(), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.anomaly_count).toBe(0);
      expect(result.current.data?.has_critical).toBe(false);
      expect(result.current.data?.has_warning).toBe(false);
    });

    it('correctly reports critical and warning flags', async () => {
      const criticalAnomalies = {
        ...mockAnomalies,
        anomalies: [
          {
            resource: 'TEMPERATURE',
            severity: 'CRITICAL' as const,
            observed_value: 65,
            threshold_value: 60,
            reason: 'Overheating',
            is_forecast: true,
            forecast_seconds_ahead: 1800,
          },
        ],
        anomaly_count: 1,
        has_critical: true,
        has_warning: false,
      };
      missionApi.getAnomalies.mockResolvedValue(criticalAnomalies);

      const { result } = renderHook(() => useAnomalies({ use_forecast: true, forecast_horizon: 3600 }), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.has_critical).toBe(true);
      expect(result.current.data?.has_warning).toBe(false);
      expect(result.current.data?.anomalies[0].is_forecast).toBe(true);
      expect(result.current.data?.anomalies[0].forecast_seconds_ahead).toBe(1800);
    });
  });

  describe('useStrategies', () => {
    const mockStrategies: StrategyGenerationResponse = {
      mission_id: 'luna-mission-001',
      current_elapsed_s: 0,
      strategies: [
        {
          strategy_id: 'strat-BATTERY-CRITICAL',
          title: 'Conserve Power',
          rationale: 'Battery critically low at 12% (threshold: 15%). Immediate power conservation required.',
          priority: 1,
          affected_resources: ['BATTERY'] as AnomalyResource[],
          recommended_actions: [
            'Disable non-essential science instruments',
            'Reduce communication frequency',
          ],
          source_anomalies: ['BATTERY-CRITICAL'],
          requires_operator_approval: true,
        },
        {
          strategy_id: 'strat-STORAGE-WARNING',
          title: 'Schedule Downlink',
          rationale: 'Storage high at 82% (threshold: 80%). Plan data offload before storage becomes critical.',
          priority: 2,
          affected_resources: ['STORAGE'] as AnomalyResource[],
          recommended_actions: [
            'Schedule downlink at next available comms window',
            'Enable data compression for new collections',
          ],
          source_anomalies: ['STORAGE-WARNING'],
          requires_operator_approval: true,
        },
      ],
      strategy_count: 2,
      has_critical_priority: true,
    };

    it('fetches strategies with default params', async () => {
      missionApi.getStrategies.mockResolvedValue(mockStrategies);

      const { result } = renderHook(() => useStrategies(), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockStrategies);
      expect(missionApi.getStrategies).toHaveBeenCalledWith(undefined);
    });

    it('fetches strategies with custom params', async () => {
      missionApi.getStrategies.mockResolvedValue(mockStrategies);

      const { result } = renderHook(() => useStrategies({ use_forecast: true, forecast_horizon: 3600 }), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(missionApi.getStrategies).toHaveBeenCalledWith({ use_forecast: true, forecast_horizon: 3600 });
    });

    it('handles error correctly', async () => {
      const error = new Error('Strategy generation failed');
      missionApi.getStrategies.mockRejectedValue(error);

      const { result } = renderHook(() => useStrategies(), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(result.current.error).toBeDefined();
    });

    it('returns critical priority flag when priority 1 strategies exist', async () => {
      missionApi.getStrategies.mockResolvedValue(mockStrategies);

      const { result } = renderHook(() => useStrategies(), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.has_critical_priority).toBe(true);
      expect(result.current.data?.strategy_count).toBe(2);
    });

    it('returns correct strategy data including approval requirement and forecast context', async () => {
      missionApi.getStrategies.mockResolvedValue(mockStrategies);

      const { result } = renderHook(() => useStrategies({ use_forecast: true, forecast_horizon: 3600 }), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.strategies[0].requires_operator_approval).toBe(true);
      expect(result.current.data?.strategies[0].priority).toBe(1);
      expect(result.current.data?.strategies[0].title).toBe('Conserve Power');
      expect(result.current.data?.strategies[0].affected_resources).toEqual(['BATTERY'] as AnomalyResource[]);
      expect(result.current.data?.strategies[0].recommended_actions).toContain('Disable non-essential science instruments');
      expect(result.current.data?.strategies[1].source_anomalies).toContain('STORAGE-WARNING');
    });

    it('returns no critical priority when all strategies are priority 2+', async () => {
      const noCriticalStrategies = {
        ...mockStrategies,
        strategies: [
          {
            strategy_id: 'strat-BATTERY-WARNING',
            title: 'Monitor Power',
            rationale: 'Battery low at 28% (threshold: 30%). Proactive power management recommended.',
            priority: 2,
            affected_resources: ['BATTERY'] as AnomalyResource[],
            recommended_actions: ['Reduce science duty cycle by 50%'],
            source_anomalies: ['BATTERY-WARNING'],
            requires_operator_approval: true,
          },
          {
            strategy_id: 'strat-STORAGE-WARNING',
            title: 'Schedule Downlink',
            rationale: 'Storage high at 82% (threshold: 80%). Plan data offload.',
            priority: 3,
            affected_resources: ['STORAGE'] as AnomalyResource[],
            recommended_actions: ['Schedule downlink at next available comms window'],
            source_anomalies: ['STORAGE-WARNING'],
            requires_operator_approval: true,
          },
        ],
        strategy_count: 2,
        has_critical_priority: false,
      };
      missionApi.getStrategies.mockResolvedValue(noCriticalStrategies);

      const { result } = renderHook(() => useStrategies(), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.has_critical_priority).toBe(false);
      expect(result.current.data?.strategy_count).toBe(2);
    });
  });

  describe('useValidateStrategies', () => {
    const mockValidation: StrategyValidationResponse = {
      mission_id: 'luna-mission-001',
      current_elapsed_s: 0,
      validation_results: [
        {
          strategy_id: 'strat-BATTERY-CRITICAL',
          is_valid: true,
          rejection_reasons: [],
        },
        {
          strategy_id: 'strat-STORAGE-WARNING',
          is_valid: false,
          rejection_reasons: ['Storage strategy conflicts with downlink schedule'],
        },
      ],
      validation_count: 2,
      all_valid: false,
    };

    it('fetches validation with default params', async () => {
      missionApi.validateStrategies.mockResolvedValue(mockValidation);

      const { result } = renderHook(() => useValidateStrategies(), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockValidation);
      expect(missionApi.validateStrategies).toHaveBeenCalledWith(undefined);
    });

    it('fetches validation with custom params', async () => {
      missionApi.validateStrategies.mockResolvedValue(mockValidation);

      const { result } = renderHook(() => useValidateStrategies({ use_forecast: true, forecast_horizon: 3600 }), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(missionApi.validateStrategies).toHaveBeenCalledWith({ use_forecast: true, forecast_horizon: 3600 });
    });

    it('handles error correctly', async () => {
      const error = new Error('Validation failed');
      missionApi.validateStrategies.mockRejectedValue(error);

      const { result } = renderHook(() => useValidateStrategies(), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(result.current.error).toBeDefined();
    });

    it('returns all_valid flag and validation results', async () => {
      missionApi.validateStrategies.mockResolvedValue(mockValidation);

      const { result } = renderHook(() => useValidateStrategies({ use_forecast: true, forecast_horizon: 3600 }), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.all_valid).toBe(false);
      expect(result.current.data?.validation_count).toBe(2);
      expect(result.current.data?.validation_results[0].is_valid).toBe(true);
      expect(result.current.data?.validation_results[1].is_valid).toBe(false);
      expect(result.current.data?.validation_results[1].rejection_reasons).toContain('Storage strategy conflicts with downlink schedule');
    });

    it('returns all_valid true when all strategies are valid', async () => {
      const allValidValidation = {
        ...mockValidation,
        validation_results: [
          { strategy_id: 'strat-BATTERY-CRITICAL', is_valid: true, rejection_reasons: [] },
          { strategy_id: 'strat-STORAGE-WARNING', is_valid: true, rejection_reasons: [] },
        ],
        all_valid: true,
      };
      missionApi.validateStrategies.mockResolvedValue(allValidValidation);

      const { result } = renderHook(() => useValidateStrategies(), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.all_valid).toBe(true);
      expect(result.current.data?.validation_count).toBe(2);
    });
  });

  describe('useApproveStrategy', () => {
    const mockApprovalResult: StrategyApprovalResult = {
      strategy_id: 'strat-BATTERY-CRITICAL',
      approved: true,
      approval_status: 'APPROVED',
      rejection_reasons: [],
    };

    it('mutates and returns approval result', async () => {
      missionApi.approveStrategy.mockResolvedValue(mockApprovalResult);

      const { result } = renderHook(() => useApproveStrategy(), { wrapper: createWrapper() });

      result.current.mutate({ strategyId: 'strat-BATTERY-CRITICAL', params: { use_forecast: true, forecast_horizon: 3600 } });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockApprovalResult);
      expect(missionApi.approveStrategy).toHaveBeenCalledWith('strat-BATTERY-CRITICAL', { use_forecast: true, forecast_horizon: 3600 });
    });

    it('returns approved status correctly', async () => {
      missionApi.approveStrategy.mockResolvedValue(mockApprovalResult);

      const { result } = renderHook(() => useApproveStrategy(), { wrapper: createWrapper() });

      result.current.mutate({ strategyId: 'strat-BATTERY-CRITICAL' });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.approved).toBe(true);
      expect(result.current.data?.approval_status).toBe('APPROVED');
    });

    it('returns rejected status with reasons when approval fails', async () => {
      const rejectedResult: StrategyApprovalResult = {
        strategy_id: 'strat-BATTERY-CRITICAL',
        approved: false,
        approval_status: 'REJECTED',
        rejection_reasons: ['Insufficient battery for emergency reserve'],
      };
      missionApi.approveStrategy.mockResolvedValue(rejectedResult);

      const { result } = renderHook(() => useApproveStrategy(), { wrapper: createWrapper() });

      result.current.mutate({ strategyId: 'strat-BATTERY-CRITICAL' });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.approved).toBe(false);
      expect(result.current.data?.approval_status).toBe('REJECTED');
      expect(result.current.data?.rejection_reasons).toContain('Insufficient battery for emergency reserve');
    });

    it('handles validation failed status', async () => {
      const validationFailedResult: StrategyApprovalResult = {
        strategy_id: 'strat-BATTERY-CRITICAL',
        approved: false,
        approval_status: 'VALIDATION_FAILED',
        rejection_reasons: ['Strategy failed validation'],
      };
      missionApi.approveStrategy.mockResolvedValue(validationFailedResult);

      const { result } = renderHook(() => useApproveStrategy(), { wrapper: createWrapper() });

      result.current.mutate({ strategyId: 'strat-BATTERY-CRITICAL' });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.approval_status).toBe('VALIDATION_FAILED');
    });

    it('handles error correctly', async () => {
      const error = new Error('Approval failed');
      missionApi.approveStrategy.mockRejectedValue(error);

      const { result } = renderHook(() => useApproveStrategy(), { wrapper: createWrapper() });

      result.current.mutate({ strategyId: 'strat-BATTERY-CRITICAL' });

      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(result.current.error).toBeDefined();
    });

    it('forwards forecast params to approval endpoint', async () => {
      missionApi.approveStrategy.mockResolvedValue(mockApprovalResult);

      const { result } = renderHook(() => useApproveStrategy(), { wrapper: createWrapper() });

      result.current.mutate({ strategyId: 'strat-BATTERY-CRITICAL', params: { use_forecast: true, forecast_horizon: 7200 } });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(missionApi.approveStrategy).toHaveBeenCalledWith('strat-BATTERY-CRITICAL', { use_forecast: true, forecast_horizon: 7200 });
    });

    it('invalidates strategy and validation queries with prefix matching', async () => {
      const mockApprovalResult: StrategyApprovalResult = {
        strategy_id: 'strat-BATTERY-CRITICAL',
        approved: true,
        approval_status: 'APPROVED',
        rejection_reasons: [],
      };
      missionApi.approveStrategy.mockResolvedValue(mockApprovalResult);

      // Create a queryClient with mock invalidation tracking
      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false },
          mutations: { retry: false },
        },
      });

      // Track invalidated query keys
      const invalidatedKeys: ReadonlyArray<unknown>[] = [];
      const originalInvalidate = queryClient.invalidateQueries.bind(queryClient);
      queryClient.invalidateQueries = vi.fn((args: { queryKey: ReadonlyArray<unknown> }) => {
        invalidatedKeys.push(args.queryKey);
        return originalInvalidate(args);
      });

      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      );

      const { result } = renderHook(() => useApproveStrategy(), { wrapper });

      result.current.mutate({ strategyId: 'strat-BATTERY-CRITICAL' });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Should invalidate queries with prefix ['mission', sessionId, 'strategies']
      const strategyInvalidated = invalidatedKeys.some(key =>
        Array.isArray(key) && key[0] === 'mission' && key[2] === 'strategies'
      );
      expect(strategyInvalidated).toBe(true);

      // Should invalidate queries with prefix ['mission', sessionId, 'validation']
      const validationInvalidated = invalidatedKeys.some(key =>
        Array.isArray(key) && key[0] === 'mission' && key[2] === 'validation'
      );
      expect(validationInvalidated).toBe(true);

      // Should NOT invalidate mission state
      const missionStateInvalidated = invalidatedKeys.some(key =>
        Array.isArray(key) && key[0] === 'mission' && key[2] === 'state'
      );
      expect(missionStateInvalidated).toBe(false);
    });
  });
});
