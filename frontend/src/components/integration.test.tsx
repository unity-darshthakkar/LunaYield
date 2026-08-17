/** Phase 5D Integration Regression Tests */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';
import App from '../App';
import * as missionApi from '../api/mission';
import type { Mission, MissionForecastResponse, AnomalyDetectionResponse, StrategyGenerationResponse, StrategyValidationResponse, AnomalyResource } from '../types/mission';

// Mock the API
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

// Mock WebSocket hook to prevent connection attempts in tests
vi.mock('../hooks/useMissionSocket', () => ({
  useMissionSocket: () => ({ connectionStatus: 'connected' }),
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

// Shared mock data factories
const createMockMission = (overrides: Partial<Mission> = {}): Mission => ({
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
  audit_trail: [],
  ...overrides,
});

const createMockForecast = (horizon: number = 3600, overrides: Partial<MissionForecastResponse> = {}): MissionForecastResponse => ({
  mission_id: 'luna-mission-001',
  current_elapsed_s: 0,
  current_resources: createMockMission().resources,
  forecast_horizon_s: horizon,
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
    {
      forecast_seconds_ahead: 1800,
      elapsed_s: 1800,
      resources: {
        battery_pct: 90,
        storage_pct: 5,
        temperature_c: -30,
        comm_window_remaining_s: 5400,
        op_time_remaining_s: 27000,
      },
    },
    {
      forecast_seconds_ahead: 3600,
      elapsed_s: 3600,
      resources: {
        battery_pct: 85,
        storage_pct: 8,
        temperature_c: -25,
        comm_window_remaining_s: 3600,
        op_time_remaining_s: 25200,
      },
    },
  ],
  ...overrides,
});

const createMockAnomalies = (count: number = 0, overrides: Partial<AnomalyDetectionResponse> = {}): AnomalyDetectionResponse => {
  const anomalies: AnomalyDetectionResponse['anomalies'] = [];
  if (count > 0) {
    anomalies.push({
      resource: 'BATTERY',
      severity: 'WARNING',
      observed_value: 28,
      threshold_value: 30,
      reason: 'Battery level approaching critical threshold',
      is_forecast: false,
      forecast_seconds_ahead: null,
    });
  }
  if (count > 1) {
    anomalies.push({
      resource: 'TEMPERATURE',
      severity: 'CRITICAL',
      observed_value: 65,
      threshold_value: 60,
      reason: 'Temperature exceeds safe operating limit',
      is_forecast: true,
      forecast_seconds_ahead: 1800,
    });
  }
  return {
    mission_id: 'luna-mission-001',
    current_elapsed_s: 0,
    anomalies,
    anomaly_count: anomalies.length,
    has_critical: anomalies.some(a => a.severity === 'CRITICAL'),
    has_warning: anomalies.some(a => a.severity === 'WARNING'),
    ...overrides,
  };
};

const createMockStrategies = (count: number = 0, overrides: Partial<StrategyGenerationResponse> = {}): StrategyGenerationResponse => {
  const strategies: StrategyGenerationResponse['strategies'] = [];
  if (count > 0) {
    strategies.push({
      strategy_id: 'strat-BATTERY-CRITICAL',
      title: 'Conserve Power',
      rationale: 'Battery critically low at 12% (threshold: 15%). Immediate power conservation required.',
      priority: 1,
      affected_resources: ['BATTERY'] as AnomalyResource[],
      recommended_actions: ['Disable non-essential science instruments', 'Reduce communication frequency'],
      source_anomalies: ['BATTERY-CRITICAL'],
      requires_operator_approval: true,
    });
  }
  if (count > 1) {
    strategies.push({
      strategy_id: 'strat-TEMPERATURE-CRITICAL-f1800',
      title: 'Thermal Protection',
      rationale: 'Temperature critically high at 65°C (threshold: 60°C) (forecast). Thermal protection required.',
      priority: 1,
      affected_resources: ['TEMPERATURE'] as AnomalyResource[],
      recommended_actions: ['Enter thermal safe mode immediately', 'Orient rover for passive thermal control'],
      source_anomalies: ['TEMPERATURE-CRITICAL-f1800'],
      requires_operator_approval: true,
    });
  }
  return {
    mission_id: 'luna-mission-001',
    current_elapsed_s: 0,
    strategies,
    strategy_count: strategies.length,
    has_critical_priority: strategies.some(s => s.priority === 1),
    ...overrides,
  };
};

const createMockValidation = (allValid: boolean = true, overrides: Partial<StrategyValidationResponse> = {}): StrategyValidationResponse => ({
  mission_id: 'luna-mission-001',
  current_elapsed_s: 0,
  validation_results: [
    { strategy_id: 'strat-BATTERY-CRITICAL', is_valid: allValid, rejection_reasons: allValid ? [] : ['Validation failed'] },
    { strategy_id: 'strat-TEMPERATURE-CRITICAL-f1800', is_valid: allValid, rejection_reasons: allValid ? [] : ['Validation failed'] },
  ],
  validation_count: 2,
  all_valid: allValid,
  ...overrides,
});

function setupDefaultMocks(
  horizon: number = 3600,
  anomalyCount: number = 0,
  strategyCount: number = 0,
  validationAllValid: boolean = true
) {
  missionApi.getMissionState.mockResolvedValue(createMockMission());
  missionApi.getScenario.mockResolvedValue({
    mission_id: 'luna-mission-001',
    label: 'Shackleton Rim Survey — Alpha',
    waypoints: [],
  });
  missionApi.getForecast.mockResolvedValue(createMockForecast(horizon));
  missionApi.getAnomalies.mockResolvedValue(createMockAnomalies(anomalyCount));
  missionApi.getStrategies.mockResolvedValue(createMockStrategies(strategyCount));
  missionApi.validateStrategies.mockResolvedValue(createMockValidation(validationAllValid));
  missionApi.approveStrategy.mockResolvedValue({
    strategy_id: 'strat-BATTERY-CRITICAL',
    approved: true,
    approval_status: 'APPROVED',
    rejection_reasons: [],
  });
}

describe('Phase 5D Integration Regression Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('A. Shared forecast horizon propagates consistently', () => {
    it('uses the same horizon for forecast, anomalies, strategies, and validation requests after selector change', async () => {
      // Render with default horizon (3600 = 1 hour)
      setupDefaultMocks(3600, 2, 2, true);

      render(<App />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('RESOURCE FORECAST')).toBeInTheDocument();
      });

      // Clear mock call history to isolate the horizon-change requests
      missionApi.getForecast.mockClear();
      missionApi.getAnomalies.mockClear();
      missionApi.getStrategies.mockClear();
      missionApi.validateStrategies.mockClear();

      // Find the horizon selector (current value "1 hour") and change to 7200 (2 hours)
      const selector = screen.getByDisplayValue('1 hour');
      fireEvent.change(selector, { target: { value: '7200' } });

      // Wait for the new requests to be issued
      await waitFor(() => {
        expect(missionApi.getForecast).toHaveBeenCalledWith({ horizon: 7200, interval: 60 });
        expect(missionApi.getAnomalies).toHaveBeenCalledWith({ use_forecast: true, forecast_horizon: 7200 });
        expect(missionApi.getStrategies).toHaveBeenCalledWith({ use_forecast: true, forecast_horizon: 7200 });
        expect(missionApi.validateStrategies).toHaveBeenCalledWith({ use_forecast: true, forecast_horizon: 7200 });
      });
    });
  });

  describe('B. Panel independence - one panel failure does not crash others', () => {
    it('forecast failure does not break anomaly/strategy rendering', async () => {
      missionApi.getMissionState.mockResolvedValue(createMockMission());
      missionApi.getScenario.mockResolvedValue({
        mission_id: 'luna-mission-001',
        label: 'Test',
        waypoints: [],
      });
      missionApi.getForecast.mockRejectedValue(new Error('Forecast service down'));
      missionApi.getAnomalies.mockResolvedValue(createMockAnomalies(1));
      missionApi.getStrategies.mockResolvedValue(createMockStrategies(1));
      missionApi.validateStrategies.mockResolvedValue(createMockValidation(true));

      render(<App />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('FORECAST ERROR')).toBeInTheDocument();
      });

      // Other panels should still render
      await waitFor(() => {
        expect(screen.getByText('ANOMALY DETECTION')).toBeInTheDocument();
        expect(screen.getByText('STRATEGY RECOMMENDATIONS')).toBeInTheDocument();
      });

      // Verify anomaly and strategy data is displayed
      expect(screen.getByText('Battery level approaching critical threshold')).toBeInTheDocument();
      expect(screen.getByText('Conserve Power')).toBeInTheDocument();
    });

    it('strategy failure does not break forecast/anomaly rendering', async () => {
      missionApi.getMissionState.mockResolvedValue(createMockMission());
      missionApi.getScenario.mockResolvedValue({
        mission_id: 'luna-mission-001',
        label: 'Test',
        waypoints: [],
      });
      missionApi.getForecast.mockResolvedValue(createMockForecast());
      missionApi.getAnomalies.mockResolvedValue(createMockAnomalies(1));
      missionApi.getStrategies.mockRejectedValue(new Error('Strategy service down'));
      missionApi.validateStrategies.mockResolvedValue(createMockValidation(true));

      render(<App />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('STRATEGY ERROR')).toBeInTheDocument();
      });

      // Other panels should still render
      await waitFor(() => {
        expect(screen.getByText('RESOURCE FORECAST')).toBeInTheDocument();
        expect(screen.getByText('ANOMALY DETECTION')).toBeInTheDocument();
      });

      expect(screen.getByText('Battery level approaching critical threshold')).toBeInTheDocument();
    });

    it('validation failure leaves strategies visible but approval blocked', async () => {
      setupDefaultMocks(3600, 2, 2, true);
      missionApi.validateStrategies.mockRejectedValue(new Error('Validation service down'));

      render(<App />, { wrapper: createWrapper() });

      // Strategy recommendations should still render
      await waitFor(() => {
        expect(screen.getByText('Conserve Power')).toBeInTheDocument();
        expect(screen.getByText('Thermal Protection')).toBeInTheDocument();
      });

      // Error message with service down text is rendered
      expect(screen.getByText('VALIDATION UNAVAILABLE: Validation service down')).toBeInTheDocument();

      // At least one VALIDATION UNAVAILABLE badge exists (header or per-strategy)
      const unavailableBadges = screen.getAllByText('VALIDATION UNAVAILABLE');
      expect(unavailableBadges.length).toBeGreaterThanOrEqual(1);

      // Fail-closed: zero APPROVE STRATEGY buttons exist
      expect(screen.queryAllByText('APPROVE STRATEGY')).toHaveLength(0);
    });
  });

  describe('C. Empty/nominal flow renders cleanly', () => {
    it('no anomalies renders NOMINAL without implying application failure', async () => {
      setupDefaultMocks(3600, 0, 0, true);

      render(<App />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('ANOMALY DETECTION')).toBeInTheDocument();
      });

      // Verify anomaly-specific empty state text (primary assertion)
      expect(screen.getByText('No anomalies detected in current mission state')).toBeInTheDocument();

      // At least one NOMINAL badge exists (anomaly panel)
      const nominalBadges = screen.getAllByText('NOMINAL');
      expect(nominalBadges.length).toBeGreaterThanOrEqual(1);

      // Dashboard does not show an anomaly/application error
      expect(screen.queryByText(/FORECAST ERROR/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/ANOMALY ERROR/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/STRATEGY ERROR/i)).not.toBeInTheDocument();
    });

    it('no strategies renders NOMINAL without implying application failure', async () => {
      setupDefaultMocks(3600, 1, 0, true);

      render(<App />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('STRATEGY RECOMMENDATIONS')).toBeInTheDocument();
      });

      expect(screen.getByText('NOMINAL')).toBeInTheDocument();
      expect(screen.getByText('No strategy recommendations at this time')).toBeInTheDocument();
      expect(screen.queryByText(/error/i)).not.toBeInTheDocument();
    });
  });

  describe('D. No execution behavior - approval is not execution', () => {
    it('no EXECUTE / APPLY / RUN STRATEGY control appears in StrategyPanel', async () => {
      setupDefaultMocks(3600, 2, 2, true);

      render(<App />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('STRATEGY RECOMMENDATIONS')).toBeInTheDocument();
      });

      // No strategy execution controls anywhere in dashboard
      expect(screen.queryByText(/EXECUTE STRATEGY/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/RUN STRATEGY/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/APPLY STRATEGY/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/EXECUTE/i)).not.toBeInTheDocument();

      // APPROVE STRATEGY is the available operator strategy action
      const approveButtons = screen.getAllByText('APPROVE STRATEGY');
      expect(approveButtons.length).toBeGreaterThanOrEqual(1);
    });

    it('approval does not trigger mission resource mutation', async () => {
      setupDefaultMocks(3600, 2, 2, true);
      missionApi.approveStrategy.mockResolvedValue({
        strategy_id: 'strat-BATTERY-CRITICAL',
        approved: true,
        approval_status: 'APPROVED',
        rejection_reasons: [],
      });

      render(<App />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('STRATEGY RECOMMENDATIONS')).toBeInTheDocument();
      });

      // Click the first APPROVE STRATEGY button
      const approveButtons = screen.getAllByText('APPROVE STRATEGY');
      expect(approveButtons.length).toBeGreaterThanOrEqual(1);
      fireEvent.click(approveButtons[0]);

      // Wait for approveStrategy to be called
      await waitFor(() => {
        expect(missionApi.approveStrategy).toHaveBeenCalled();
      });

      // Verify strategy approval did NOT call any mission lifecycle/mutation APIs
      expect(missionApi.startMission).not.toHaveBeenCalled();
      expect(missionApi.pauseMission).not.toHaveBeenCalled();
      expect(missionApi.resumeMission).not.toHaveBeenCalled();
      expect(missionApi.resetMission).not.toHaveBeenCalled();
      expect(missionApi.injectAnomaly).not.toHaveBeenCalled();
      expect(missionApi.approvePlan).not.toHaveBeenCalled();
    });
  });
});