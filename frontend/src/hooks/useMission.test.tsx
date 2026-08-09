/** useMission hook tests */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useMissionState, useStartMission, useResetMission } from './useMission';
import * as missionApi from '../api/mission';

// Mock the API
vi.mock('../api/mission', () => ({
  getMissionState: vi.fn(),
  startMission: vi.fn(),
  pauseMission: vi.fn(),
  resetMission: vi.fn(),
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
});