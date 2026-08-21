import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { MissionControlApp } from './MissionControlApp';
import { PlanStatus, type CandidatePlan, type Mission, WaypointProgressStatus } from '../types/mission';

type MockMutation = {
  mutate: ReturnType<typeof vi.fn>;
  reset: ReturnType<typeof vi.fn>;
  isSuccess: boolean;
  isError: boolean;
  isPending: boolean;
  error: { message: string; userMessage: string } | null;
};

let missionState: Mission;
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
      mutation.isPending = false;
    }),
    isSuccess: false,
    isError: Boolean(errorMessage),
    isPending: false,
    error: errorMessage ? { message: errorMessage, userMessage: errorMessage } : null,
  };
  return mutation;
}

function createPlan(overrides: Partial<CandidatePlan> = {}): CandidatePlan {
  return {
    plan_id: 'plan-a-001',
    label: 'Minimal Survey',
    description: 'Conservative return to base with minimal science stops',
    waypoints: [
      {
        id: 'wp-crater-a',
        x: 0.3,
        y: 0.4,
        label: 'Crater A Rim',
        is_science_target: true,
        progress_status: WaypointProgressStatus.COMPLETED,
        segment_elapsed_s: 0,
        science_collected: true,
      },
    ],
    science_yield_score: 45,
    predicted_return_battery_pct: 30,
    status: PlanStatus.VALID,
    violations: [],
    is_recommended: false,
    rank: 2,
    ...overrides,
  };
}

function createMission(overrides: Partial<Mission> = {}): Mission {
  return {
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
    ...overrides,
  } as Mission;
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

describe('MissionControlApp plan popup lifecycle', () => {
  beforeEach(() => {
    missionState = createMission();
    startMutation = createMutation();
    pauseMutation = createMutation();
    resumeMutation = createMutation();
    resetMutation = createMutation();
    injectMutation = createMutation();
    generateMutation = createMutation();
    approvePlanMutation = createMutation();
  });

  it('opens after generation, can be closed, and reopens via VIEW PLANS without regenerating', () => {
    const view = render(<MissionControlApp />);

    missionState = createMission({ status: 'ANOMALY', anomaly_active: true });
    view.rerender(<MissionControlApp />);

    fireEvent.click(screen.getByRole('button', { name: /GENERATE PLANS/i }));
    expect(generateMutation.mutate).toHaveBeenCalledTimes(1);

    missionState = createMission({
      status: 'AWAITING_APPROVAL',
      anomaly_active: true,
      candidate_plans: [
        createPlan(),
        createPlan({
          plan_id: 'plan-b-001',
          label: 'Extended Survey',
          predicted_return_battery_pct: 21,
          is_recommended: true,
          rank: 1,
        }),
        createPlan({
          plan_id: 'plan-c-001',
          label: 'Aggressive Survey',
          predicted_return_battery_pct: 10.5,
          status: PlanStatus.REJECTED,
          violations: [
            {
              rule_id: 'RETURN_BATTERY_MIN_20PCT',
              description: 'Predicted return battery 10.5% is below minimum 20.0%',
              measured_value: 10.5,
              threshold_value: 20,
            },
          ],
          rank: 3,
        }),
      ],
    });
    view.rerender(<MissionControlApp />);

    expect(screen.getByText('Generated mission plans')).toBeInTheDocument();
    expect(screen.getByText('Aggressive Survey')).toBeInTheDocument();
    expect(screen.getByText('REJECTED - CANNOT APPROVE')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /APPROVE/i })).toHaveLength(2);

    fireEvent.click(screen.getByRole('button', { name: /close plans popup/i }));
    expect(screen.queryByText('Generated mission plans')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /VIEW PLANS/i })).not.toBeDisabled();

    fireEvent.click(screen.getByRole('button', { name: /VIEW PLANS/i }));
    expect(screen.getByText('Generated mission plans')).toBeInTheDocument();
    expect(generateMutation.mutate).toHaveBeenCalledTimes(1);
  });

  it('approves a valid plan after reopening and preserves PLAN SELECTED display', () => {
    missionState = createMission({
      status: 'AWAITING_APPROVAL',
      anomaly_active: true,
      candidate_plans: [
        createPlan(),
        createPlan({
          plan_id: 'plan-b-001',
          label: 'Extended Survey',
          predicted_return_battery_pct: 21,
          is_recommended: true,
          rank: 1,
        }),
      ],
    });

    const view = render(<MissionControlApp />);

    fireEvent.click(screen.getByRole('button', { name: /close plans popup/i }));
    fireEvent.click(screen.getByRole('button', { name: /VIEW PLANS/i }));
    fireEvent.click(screen.getByRole('button', { name: /APPROVE PLAN/i }));

    expect(approvePlanMutation.mutate).toHaveBeenCalledWith('plan-a-001');

    missionState = createMission({
      status: 'EXECUTING',
      anomaly_active: false,
      candidate_plans: [
        createPlan({ status: PlanStatus.APPROVED }),
        createPlan({
          plan_id: 'plan-b-001',
          label: 'Extended Survey',
          predicted_return_battery_pct: 21,
          is_recommended: true,
          rank: 1,
        }),
      ],
    });
    view.rerender(<MissionControlApp />);

    expect(screen.queryByText('Generated mission plans')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /PLAN SELECTED: MINIMAL SURVEY/i })).toBeDisabled();
  });

  it('reset clears plans state and removes the popup', () => {
    missionState = createMission({
      status: 'AWAITING_APPROVAL',
      anomaly_active: true,
      candidate_plans: [createPlan()],
    });

    const view = render(<MissionControlApp />);
    expect(screen.getByText('Generated mission plans')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /RESET MISSION/i }));
    expect(resetMutation.mutate).toHaveBeenCalledTimes(1);

    resetMutation.isSuccess = true;
    missionState = createMission({ status: 'IDLE', candidate_plans: [], anomaly_active: false });
    view.rerender(<MissionControlApp />);

    expect(screen.queryByText('Generated mission plans')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /GENERATE PLANS/i })).toBeDisabled();
    expect(screen.queryByRole('button', { name: /VIEW PLANS/i })).not.toBeInTheDocument();
  });
});
