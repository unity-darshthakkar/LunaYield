/** App component integration tests */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';
import App from './App';
import * as missionApi from './api/mission';
import type { Mission } from './types/mission';

// Mock the API
vi.mock('./api/mission', () => ({
  getMissionState: vi.fn(),
  getScenario: vi.fn(),
  startMission: vi.fn(),
  pauseMission: vi.fn(),
  resumeMission: vi.fn(),
  resetMission: vi.fn(),
  injectAnomaly: vi.fn(),
  generatePlans: vi.fn(),
  approvePlan: vi.fn(),
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: Infinity },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the LunaYield Mission Lab heading when mission loads', async () => {
    const mockMission: Mission = {
      mission_id: 'luna-mission-001',
      label: 'Shackleton Rim Survey — Alpha',
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
      audit_trail: [
        {
          event_id: 'audit-001',
          event_type: 'mission.initialized',
          description: 'Mission scenario loaded from seed data.',
          timestamp: '2026-08-06T00:00:00.000Z',
          metadata: { mission_id: 'luna-mission-001' },
        },
      ],
    };
    missionApi.getMissionState.mockResolvedValue(mockMission);
    missionApi.getScenario.mockResolvedValue({
      mission_id: 'luna-mission-001',
      label: 'Shackleton Rim Survey — Alpha',
      waypoints: [],
    });

    render(<App />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('LunaYield Mission Lab')).toBeInTheDocument();
    });
  });

  it('shows loading state initially', () => {
    const missionPromise = new Promise<Mission>((_resolve) => {
      // _resolve is used internally by the test
    });
    missionApi.getMissionState.mockReturnValue(missionPromise);
    missionApi.getScenario.mockResolvedValue({
      mission_id: 'luna-mission-001',
      label: 'Test',
      waypoints: [],
    });

    render(<App />, { wrapper: createWrapper() });

    expect(screen.getByText('INITIALIZING MISSION CONTROL...')).toBeInTheDocument();
  });

  it('shows error state when mission state fetch fails', async () => {
    missionApi.getMissionState.mockRejectedValue(new Error('Network error'));
    missionApi.getScenario.mockResolvedValue({
      mission_id: 'luna-mission-001',
      label: 'Test',
      waypoints: [],
    });

    render(<App />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('CONNECTION FAILED')).toBeInTheDocument();
    });
  });
});