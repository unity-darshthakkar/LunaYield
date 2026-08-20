import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { MissionControlApp } from './MissionControlApp';
import * as missionApi from '../api/mission';
import {
  MissionStatus,
  type Mission,
  type TelemetrySample,
  WaypointProgressStatus,
} from '../types/mission';

vi.mock('../api/mission', () => ({
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
  getStrategies: vi.fn(),
  validateStrategies: vi.fn(),
  approveStrategy: vi.fn(),
}));

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  static OPEN = 1;

  readyState = MockWebSocket.OPEN;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(public url: string) {
    MockWebSocket.instances.push(this);
    queueMicrotask(() => this.onopen?.());
  }

  close() {
    this.onclose?.();
  }

  send() {}

  emitMessage(message: unknown) {
    this.onmessage?.({ data: JSON.stringify(message) });
  }
}

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0, gcTime: Infinity },
      mutations: { retry: false, gcTime: Infinity },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

const buildMission = (overrides: Partial<Mission>): Mission => ({
  mission_id: 'luna-mission-001',
  label: 'Shackleton Rim Survey - Alpha',
  status: MissionStatus.RUNNING,
  elapsed_s: 2,
  resources: {
    battery_pct: 99.5,
    storage_pct: 0,
    temperature_c: -39.9,
    comm_window_remaining_s: 7198,
    op_time_remaining_s: 28798,
  },
  original_route: {
    waypoints: [],
  },
  active_route: {
    waypoints: [
      {
        id: 'wp-base',
        label: 'Base Camp',
        x: 0.1,
        y: 0.1,
        is_science_target: false,
        progress_status: WaypointProgressStatus.COMPLETED,
        segment_elapsed_s: 0,
        science_collected: false,
      },
      {
        id: 'wp-crater-a',
        label: 'Crater A Rim',
        x: 0.3,
        y: 0.4,
        is_science_target: true,
        progress_status: WaypointProgressStatus.CURRENT,
        segment_elapsed_s: 2,
        science_collected: false,
      },
      {
        id: 'wp-ice-deposit',
        label: 'Ice Deposit Site',
        x: 0.5,
        y: 0.6,
        is_science_target: true,
        progress_status: WaypointProgressStatus.UPCOMING,
        segment_elapsed_s: 0,
        science_collected: false,
      },
    ],
  },
  candidate_plans: [],
  anomaly_active: false,
  audit_trail: [
    {
      event_id: 'audit-seed-001',
      event_type: 'mission.started',
      description: 'Mission started by operator',
      timestamp: '2026-08-20T12:00:00.000Z',
      metadata: { mission_id: 'luna-mission-001' },
    },
  ],
  ...overrides,
});

describe('MissionControlApp live synchronization', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MockWebSocket.instances = [];
    vi.stubGlobal('WebSocket', MockWebSocket);

    missionApi.getScenario.mockResolvedValue({
      mission_id: 'luna-mission-001',
      label: 'Shackleton Rim Survey - Alpha',
      waypoints: [],
    });
    missionApi.getForecast.mockResolvedValue({
      mission_id: 'luna-mission-001',
      current_elapsed_s: 0,
      current_resources: buildMission({}).resources,
      forecast_horizon_s: 3600,
      forecast_tick_interval_s: 60,
      forecast_points: [],
    });
    missionApi.getAnomalies.mockResolvedValue({
      mission_id: 'luna-mission-001',
      current_elapsed_s: 0,
      anomalies: [],
      anomaly_count: 0,
      has_critical: false,
      has_warning: false,
    });
    missionApi.getStrategies.mockResolvedValue({
      mission_id: 'luna-mission-001',
      current_elapsed_s: 0,
      strategies: [],
      strategy_count: 0,
      has_critical_priority: false,
    });
    missionApi.validateStrategies.mockResolvedValue({
      mission_id: 'luna-mission-001',
      current_elapsed_s: 0,
      validation_results: [],
      validation_count: 0,
      all_valid: true,
    });
    missionApi.approveStrategy.mockResolvedValue({
      strategy_id: 'noop',
      approved: false,
      approval_status: 'NOT_FOUND',
      rejection_reasons: [],
    });
  });

  it('refetches and renders completed mission state after telemetry update', async () => {
    const runningMission = buildMission({});
    const completedMission = buildMission({
      status: MissionStatus.COMPLETED,
      elapsed_s: 296,
      resources: {
        battery_pct: 26,
        storage_pct: 100,
        temperature_c: -25.2,
        comm_window_remaining_s: 6904,
        op_time_remaining_s: 28504,
      },
      active_route: {
        waypoints: runningMission.active_route.waypoints.map((waypoint) => ({
          ...waypoint,
          progress_status: WaypointProgressStatus.COMPLETED,
          science_collected: waypoint.is_science_target,
        })),
      },
      audit_trail: [
        ...runningMission.audit_trail,
        {
          event_id: 'audit-complete-001',
          event_type: 'mission.completed',
          description: 'Mission completed and rover returned to Base Camp',
          timestamp: '2026-08-20T12:04:56.000Z',
          metadata: { mission_id: 'luna-mission-001', elapsed_s: 296 },
        },
      ],
    });

    missionApi.getMissionState
      .mockResolvedValueOnce(runningMission)
      .mockResolvedValue(completedMission);

    render(<MissionControlApp />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('current-mission-state')).toHaveTextContent('RUNNING');
    });
    expect(screen.getByText(/^CURRENT$/)).toBeInTheDocument();

    const telemetrySample: TelemetrySample = {
      mission_id: 'luna-mission-001',
      elapsed_s: 296,
      resources: completedMission.resources,
      timestamp: '2026-08-20T12:04:56.000Z',
    };

    act(() => {
      MockWebSocket.instances[0].emitMessage({
        event: 'telemetry.updated',
        payload: telemetrySample,
      });
    });

    await waitFor(() => {
      expect(screen.getByTestId('current-mission-state')).toHaveTextContent('COMPLETED');
    });

    await waitFor(() => {
      expect(screen.queryByText(/^CURRENT$/)).not.toBeInTheDocument();
      expect(screen.getAllByText(/^COMPLETED$/).length).toBeGreaterThanOrEqual(3);
    });

    fireEvent.click(screen.getByRole('button', { name: /open audit trail/i }));
    await waitFor(() => {
      expect(screen.getByText('mission.completed')).toBeInTheDocument();
    });
  });
});
