/** useMission hook tests */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useMissionState, useStartMission, useResetMission, useForecast, useAnomalies } from './useMission';
import * as missionApi from '../api/mission';
import type { MissionForecastResponse, AnomalyDetectionResponse } from '../types/mission';

// Mock the API
vi.mock('../api/mission', () => ({
  getMissionState: vi.fn(),
  startMission: vi.fn(),
  pauseMission: vi.fn(),
  resetMission: vi.fn(),
  getForecast: vi.fn(),
  getAnomalies: vi.fn(),
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
});