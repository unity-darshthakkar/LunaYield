import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { MissionControlApp } from './MissionControlApp';

type MockMutation = {
  mutate: ReturnType<typeof vi.fn>;
  reset: ReturnType<typeof vi.fn>;
  isSuccess: boolean;
  isError: boolean;
  error: { message: string; userMessage: string } | null;
};

let missionState: {
  mission_id: string;
  label: string;
  status: string;
  elapsed_s: number;
  resources: {
    battery_pct: number;
    storage_pct: number;
    temperature_c: number;
    comm_window_remaining_s: number;
    op_time_remaining_s: number;
  };
  original_route: { waypoints: never[] };
  active_route: { waypoints: never[] };
  candidate_plans: never[];
  anomaly_active: boolean;
  audit_trail: never[];
};

let startMutation: MockMutation;
let pauseMutation: MockMutation;
let resumeMutation: MockMutation;
let resetMutation: MockMutation;
let injectMutation: MockMutation;
let generateMutation: MockMutation;
let approvePlanMutation: MockMutation;

function createMutation(errorMessage: string | null = null): MockMutation {
  const mutation: MockMutation = {
    mutate: vi.fn(),
    reset: vi.fn(() => {
      mutation.isError = false;
      mutation.error = null;
      mutation.isSuccess = false;
    }),
    isSuccess: false,
    isError: Boolean(errorMessage),
    error: errorMessage
      ? { message: errorMessage, userMessage: errorMessage }
      : null,
  };
  return mutation;
}

vi.mock('../hooks/useMission', () => ({
  useMissionState: () => ({
    data: missionState,
    isLoading: false,
    error: null,
  }),
  useStartMission: () => startMutation,
  usePauseMission: () => pauseMutation,
  useResumeMission: () => resumeMutation,
  useResetMission: () => resetMutation,
  useInjectAnomaly: () => injectMutation,
  useGeneratePlans: () => generateMutation,
  useApprovePlan: () => approvePlanMutation,
  useMissionError: (mutation: MockMutation) =>
    mutation.isError && mutation.error
      ? mutation.error.userMessage ?? mutation.error.message
      : null,
  useForecast: () => ({ data: null, isLoading: false, error: null }),
  useAnomalies: () => ({ data: null, isLoading: false, error: null }),
  useStrategies: () => ({ data: null, isLoading: false, error: null }),
  useValidateStrategies: () => ({ data: null, isLoading: false, error: null }),
}));

vi.mock('../hooks/useMissionSocket', () => ({
  useMissionSocket: () => ({ connectionStatus: 'connected' }),
}));

describe('MissionControlApp action error clearing', () => {
  beforeEach(() => {
    missionState = {
      mission_id: 'luna-mission-001',
      label: 'Shackleton Rim Survey - Alpha',
      status: 'IDLE',
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
    startMutation = createMutation();
    pauseMutation = createMutation();
    resumeMutation = createMutation();
    resetMutation = createMutation();
    injectMutation = createMutation();
    generateMutation = createMutation();
    approvePlanMutation = createMutation();
  });

  it('RESET clears stale action errors before starting a fresh mission cycle', () => {
    missionState.status = 'RUNNING';
    pauseMutation = createMutation('Cannot pause from COMPLETED status');
    injectMutation = createMutation('Cannot inject anomaly from COMPLETED status');

    const view = render(<MissionControlApp />);
    expect(screen.getByText(/PAUSE: Cannot pause from COMPLETED status/i)).toBeInTheDocument();
    expect(screen.getByText(/ANOMALY: Cannot inject anomaly from COMPLETED status/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /RESET MISSION/i }));
    view.rerender(<MissionControlApp />);

    expect(resetMutation.mutate).toHaveBeenCalledTimes(1);
    expect(
      screen.queryByText(/PAUSE: Cannot pause from COMPLETED status/i)
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(/ANOMALY: Cannot inject anomaly from COMPLETED status/i)
    ).not.toBeInTheDocument();
  });

  it('START clears stale action errors before beginning a new run', () => {
    pauseMutation = createMutation('Cannot pause from COMPLETED status');
    injectMutation = createMutation('Cannot inject anomaly from COMPLETED status');

    const view = render(<MissionControlApp />);
    expect(screen.getByText(/PAUSE: Cannot pause from COMPLETED status/i)).toBeInTheDocument();
    expect(screen.getByText(/ANOMALY: Cannot inject anomaly from COMPLETED status/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /START MISSION/i }));
    view.rerender(<MissionControlApp />);

    expect(startMutation.mutate).toHaveBeenCalledTimes(1);
    expect(
      screen.queryByText(/PAUSE: Cannot pause from COMPLETED status/i)
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(/ANOMALY: Cannot inject anomaly from COMPLETED status/i)
    ).not.toBeInTheDocument();
  });
});
