/** App component integration tests */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';
import App from './App';
import * as missionApi from './api/mission';
import type { Mission, MissionForecastResponse, AnomalyDetectionResponse } from './types/mission';

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
  getForecast: vi.fn(),
  getAnomalies: vi.fn(),
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

// Shared mock data
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

const mockForecast: MissionForecastResponse = {
  mission_id: 'luna-mission-001',
  current_elapsed_s: 0,
  current_resources: mockMission.resources,
  forecast_horizon_s: 3600,
  forecast_tick_interval_s: 60,
  forecast_points: [],
};

const mockAnomalies: AnomalyDetectionResponse = {
  mission_id: 'luna-mission-001',
  current_elapsed_s: 0,
  anomalies: [],
  anomaly_count: 0,
  has_critical: false,
  has_warning: false,
};

function setupMocks() {
  missionApi.getMissionState.mockResolvedValue(mockMission);
  missionApi.getScenario.mockResolvedValue({
    mission_id: 'luna-mission-001',
    label: 'Shackleton Rim Survey — Alpha',
    waypoints: [],
  });
  missionApi.getForecast.mockResolvedValue(mockForecast);
  missionApi.getAnomalies.mockResolvedValue(mockAnomalies);
}

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the LunaYield Mission Lab heading when mission loads', async () => {
    setupMocks();

    render(<App />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('LunaYield Mission Lab')).toBeInTheDocument();
    });
  });

  it('footer displays Phase 1 Demo', async () => {
    setupMocks();

    render(<App />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/LunaYield Mission Lab - Phase 1 Demo/i)).toBeInTheDocument();
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
    missionApi.getForecast.mockResolvedValue(mockForecast);
    missionApi.getAnomalies.mockResolvedValue(mockAnomalies);

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
    missionApi.getForecast.mockResolvedValue(mockForecast);
    missionApi.getAnomalies.mockResolvedValue(mockAnomalies);

    render(<App />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('CONNECTION FAILED')).toBeInTheDocument();
    });
  });

  it('displays forecast panel with horizon selector', async () => {
    setupMocks();

    render(<App />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('RESOURCE FORECAST')).toBeInTheDocument();
      expect(screen.getByDisplayValue('1 hour')).toBeInTheDocument();
    });
  });

  it('displays anomaly panel showing nominal state', async () => {
    setupMocks();

    render(<App />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('ANOMALY DETECTION')).toBeInTheDocument();
      expect(screen.getByText('NOMINAL')).toBeInTheDocument();
    });
  });

  it('does not mutate mission when viewing forecast or anomalies', async () => {
    setupMocks();

    render(<App />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('RESOURCE FORECAST')).toBeInTheDocument();
      expect(screen.getByText('ANOMALY DETECTION')).toBeInTheDocument();
    });

    // Verify no mutation APIs were called
    expect(missionApi.startMission).not.toHaveBeenCalled();
    expect(missionApi.pauseMission).not.toHaveBeenCalled();
    expect(missionApi.resumeMission).not.toHaveBeenCalled();
    expect(missionApi.resetMission).not.toHaveBeenCalled();
    expect(missionApi.injectAnomaly).not.toHaveBeenCalled();
    expect(missionApi.generatePlans).not.toHaveBeenCalled();
    expect(missionApi.approvePlan).not.toHaveBeenCalled();
  });
});