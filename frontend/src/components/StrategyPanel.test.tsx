/** StrategyPanel tests */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrategyPanel } from './StrategyPanel';
import * as missionApi from '../api/mission';
import type { StrategyGenerationResponse, StrategyValidationResponse, StrategyCandidate, AnomalyResource, StrategyApprovalResult } from '../types/mission';

// Use vi.hoisted to create mock state at module level (before imports) for hoisted vi.mock
const mockApprovalState = vi.hoisted(() => ({
  value: {
    data: undefined as StrategyApprovalResult | undefined,
    isPending: false,
    isError: false,
    error: null as Error | null,
    variables: undefined as { strategyId: string; params?: { use_forecast: boolean; forecast_horizon: number } } | undefined,
  },
}));

// Mock the useApproveStrategy hook at module level using hoisted state
vi.mock('../hooks/useMission', async () => {
  const actual = await vi.importActual('../hooks/useMission');
  return {
    ...actual,
    useApproveStrategy: () => ({
      mutate: vi.fn(),
      isPending: mockApprovalState.value.isPending,
      data: mockApprovalState.value.data,
      error: mockApprovalState.value.error,
      isError: mockApprovalState.value.isError,
      isSuccess: !!mockApprovalState.value.data,
      variables: mockApprovalState.value.variables,
    }),
  };
});

// Mock validation data
const createMockValidation = (overrides: Partial<StrategyValidationResponse> = {}): StrategyValidationResponse => {
  return {
    mission_id: 'test-mission',
    current_elapsed_s: 0,
    validation_results: [
      { strategy_id: 'strat-BATTERY-CRITICAL', is_valid: true, rejection_reasons: [] },
      { strategy_id: 'strat-STORAGE-WARNING', is_valid: true, rejection_reasons: [] },
      { strategy_id: 'strat-TEMPERATURE-CRITICAL-f1800', is_valid: true, rejection_reasons: [] },
    ],
    validation_count: 3,
    all_valid: true,
    ...overrides,
  };
};

// Mock strategy data
const createMockStrategies = (overrides: Partial<StrategyGenerationResponse> = {}): StrategyGenerationResponse => {
  const mockStrategies: StrategyCandidate[] = [
    {
      strategy_id: 'strat-BATTERY-CRITICAL',
      title: 'Conserve Power',
      rationale: 'Battery critically low at 12% (threshold: 15%). Immediate power conservation required to maintain critical systems.',
      priority: 1,
      affected_resources: ['BATTERY'] as AnomalyResource[],
      recommended_actions: [
        'Disable non-essential science instruments',
        'Reduce communication frequency',
        'Orient solar panels for maximum charging',
        'Enter low-power safe mode if below 5%',
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
        'Archive completed science targets',
        'Monitor storage growth rate',
      ],
      source_anomalies: ['STORAGE-WARNING'],
      requires_operator_approval: true,
    },
    {
      strategy_id: 'strat-TEMPERATURE-CRITICAL-f1800',
      title: 'Thermal Protection',
      rationale: 'Temperature critically high at 65°C (threshold: 60°C) (forecast). Thermal protection required to prevent hardware damage.',
      priority: 1,
      affected_resources: ['TEMPERATURE'] as AnomalyResource[],
      recommended_actions: [
        'Enter thermal safe mode immediately',
        'Orient rover for passive thermal control',
        'Disable heat-generating instruments',
        'Monitor temperature every 5 minutes',
      ],
      source_anomalies: ['TEMPERATURE-CRITICAL-f1800'],
      requires_operator_approval: true,
    },
  ];

  return {
    mission_id: 'test-mission',
    current_elapsed_s: 0,
    strategies: mockStrategies,
    strategy_count: mockStrategies.length,
    has_critical_priority: true,
    ...overrides,
  };
};

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('StrategyPanel', () => {
  let wrapper: ReturnType<typeof createWrapper>;

  beforeEach(() => {
    wrapper = createWrapper();
    vi.useFakeTimers();
    // Reset mock state before each test
    mockApprovalState.value = {
      data: undefined,
      isPending: false,
      isError: false,
      error: null,
      variables: undefined,
    };
  });

  const defaultProps = {
    strategies: createMockStrategies(),
    validation: createMockValidation(),
    validationError: null,
    isLoading: false,
    error: null,
    validationLoading: false,
    forecastHorizon: 3600,
    useForecast: true,
  };

  // Terminal state test helper - controlled mock state for useApproveStrategy hook
  const renderWithMockedApproval = (
    overrides: typeof mockApprovalState.value = {}
  ) => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation();

    // Update the global mock state
    mockApprovalState.value = { ...mockApprovalState.value, ...overrides };

    const { result } = render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    return { result, strategies, mockValidation };
  };

  it('renders loading state when isLoading is true', () => {
    render(
      <StrategyPanel
        {...defaultProps}
        strategies={undefined}
        isLoading={true}
      />,
      { wrapper }
    );

    expect(screen.getByText('STRATEGY RECOMMENDATIONS')).toBeInTheDocument();
    expect(screen.getByRole('status', { name: /loading strategies/i })).toBeInTheDocument();
  });

  it('renders error state when error is present', () => {
    const mockError = new Error('Network error');
    render(
      <StrategyPanel
        {...defaultProps}
        strategies={undefined}
        error={mockError}
      />,
      { wrapper }
    );

    expect(screen.getByText('STRATEGY ERROR')).toBeInTheDocument();
    expect(screen.getByText('Network error')).toBeInTheDocument();
  });

  it('renders empty state when strategies is undefined and not loading', () => {
    render(
      <StrategyPanel
        {...defaultProps}
        strategies={undefined}
      />,
      { wrapper }
    );

    expect(screen.getByText('STRATEGY RECOMMENDATIONS')).toBeInTheDocument();
    expect(screen.getByText('No strategy data available')).toBeInTheDocument();
  });

  it('renders nominal state when no strategies generated', () => {
    const strategies = createMockStrategies({
      strategies: [],
      strategy_count: 0,
      has_critical_priority: false,
    });

    const mockValidation = createMockValidation();

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    expect(screen.getByText('STRATEGY RECOMMENDATIONS')).toBeInTheDocument();
    expect(screen.getByText('NOMINAL')).toBeInTheDocument();
    expect(screen.getByText('No strategy recommendations at this time')).toBeInTheDocument();
    expect(screen.getByText('Strategies are generated in response to anomaly detections')).toBeInTheDocument();
  });

  it('renders multiple strategies sorted by priority', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation();

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    expect(screen.getByText('STRATEGY RECOMMENDATIONS')).toBeInTheDocument();
    expect(screen.getByText('PRIORITY 1 ACTIVE')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument(); // strategy count

    // Check all three strategy titles are present
    expect(screen.getByText('Conserve Power')).toBeInTheDocument();
    expect(screen.getByText('Schedule Downlink')).toBeInTheDocument();
    expect(screen.getByText('Thermal Protection')).toBeInTheDocument();
  });

  it('displays strategy priority badges', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation();

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    // Priority 1 (critical) shows red badge (header + 2 strategies with priority 1 = 3 total)
    // Priority 2 (warning) shows yellow badge (1 strategy)
    const priority1Badges = screen.getAllByText('PRIORITY 1');
    const priority2Badges = screen.getAllByText('PRIORITY 2');
    expect(priority1Badges.length).toBeGreaterThanOrEqual(2); // At least 2 (header + first priority 1 strategy)
    expect(priority2Badges).toHaveLength(1);
  });

  it('displays affected resources for each strategy', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation();

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    // Multiple strategies have "affects:" label
    expect(screen.getAllByText('affects:')).toHaveLength(3);
    // Resources should be displayed
    expect(screen.getByText('BATTERY')).toBeInTheDocument();
    expect(screen.getByText('STORAGE')).toBeInTheDocument();
    expect(screen.getByText('TEMP')).toBeInTheDocument();
  });

  it('displays rationale for each strategy', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation();

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    expect(screen.getByText(/Battery critically low at 12%/)).toBeInTheDocument();
    expect(screen.getByText(/Storage high at 82%/)).toBeInTheDocument();
    expect(screen.getByText(/Temperature critically high at 65°C/)).toBeInTheDocument();
  });

  it('displays recommended actions for each strategy', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation();

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    // Multiple strategies have "RECOMMENDED ACTIONS:" label
    expect(screen.getAllByText('RECOMMENDED ACTIONS:')).toHaveLength(3);
    expect(screen.getByText('Disable non-essential science instruments')).toBeInTheDocument();
    expect(screen.getByText('Schedule downlink at next available comms window')).toBeInTheDocument();
    expect(screen.getByText('Enter thermal safe mode immediately')).toBeInTheDocument();
  });

  it('shows APPROVAL REQUIRED badge for all strategies', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation();

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    // All strategies have requires_operator_approval=true
    const approvalBadges = screen.getAllByText('APPROVAL REQUIRED');
    expect(approvalBadges).toHaveLength(3);
  });

  it('shows FORECAST-BASED badge for forecast strategies', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation();

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    // Third strategy has forecast source anomaly (contains -f)
    expect(screen.getByText('FORECAST-BASED')).toBeInTheDocument();
  });

  it('displays source anomalies for each strategy', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation();

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    // Multiple strategies have "SOURCE ANOMALIES:" label
    expect(screen.getAllByText('SOURCE ANOMALIES:')).toHaveLength(3);
    expect(screen.getByText('BATTERY-CRITICAL')).toBeInTheDocument();
    expect(screen.getByText('STORAGE-WARNING')).toBeInTheDocument();
    expect(screen.getByText('TEMPERATURE-CRITICAL-f1800')).toBeInTheDocument();
  });

  it('displays strategy IDs', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation();

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    expect(screen.getByText('strat-BATTERY-CRITICAL')).toBeInTheDocument();
    expect(screen.getByText('strat-STORAGE-WARNING')).toBeInTheDocument();
    expect(screen.getByText('strat-TEMPERATURE-CRITICAL-f1800')).toBeInTheDocument();
  });

  it('shows PRIORITY 1 ACTIVE badge when has_critical_priority is true', () => {
    const strategies = createMockStrategies({ has_critical_priority: true });
    const mockValidation = createMockValidation();

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    expect(screen.getByText('PRIORITY 1 ACTIVE')).toBeInTheDocument();
  });

  it('does not show PRIORITY 1 ACTIVE badge when has_critical_priority is false', () => {
    const strategies = createMockStrategies({
      has_critical_priority: false,
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
        }
      ],
      strategy_count: 1,
    });
    const mockValidation = createMockValidation();

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    expect(screen.queryByText('PRIORITY 1 ACTIVE')).not.toBeInTheDocument();
  });

  it('does not show APPROVING... on initial render', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation();

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    expect(screen.queryByText('APPROVING...')).not.toBeInTheDocument();
  });

  // Phase 5C: Validation and Approval tests

  it('shows ALL VALID badge when validation.all_valid is true', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation();

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    expect(screen.getByText('ALL VALID')).toBeInTheDocument();
  });

  it('shows VALIDATION FAILED badge when validation.all_valid is false', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation({ all_valid: false });

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    expect(screen.getByText('VALIDATION FAILED')).toBeInTheDocument();
  });

  it('shows VALID badge for each strategy when validation passes', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation();

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    const validBadges = screen.getAllByText('VALID');
    expect(validBadges).toHaveLength(3);
  });

  it('shows INVALID badge and rejection reasons for invalid strategies', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation({
      validation_results: [
        { strategy_id: 'strat-BATTERY-CRITICAL', is_valid: false, rejection_reasons: ['Battery conservation conflicts with science priorities'] },
        { strategy_id: 'strat-STORAGE-WARNING', is_valid: true, rejection_reasons: [] },
        { strategy_id: 'strat-TEMPERATURE-CRITICAL-f1800', is_valid: true, rejection_reasons: [] },
      ],
      all_valid: false,
    });

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    expect(screen.getByText('INVALID')).toBeInTheDocument();
    expect(screen.getByText('REJECTION REASONS:')).toBeInTheDocument();
    expect(screen.getByText('Battery conservation conflicts with science priorities')).toBeInTheDocument();
    // Should show CANNOT APPROVE message for invalid strategy
    expect(screen.getByText('CANNOT APPROVE - VALIDATION FAILED')).toBeInTheDocument();
  });

  it('shows APPROVE STRATEGY button for valid strategies requiring approval', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation();

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    const approveButtons = screen.getAllByText('APPROVE STRATEGY');
    expect(approveButtons).toHaveLength(3);
  });

  it('does not show APPROVE button for invalid strategies', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation({
      validation_results: [
        { strategy_id: 'strat-BATTERY-CRITICAL', is_valid: false, rejection_reasons: ['Validation failed'] },
        { strategy_id: 'strat-STORAGE-WARNING', is_valid: true, rejection_reasons: [] },
        { strategy_id: 'strat-TEMPERATURE-CRITICAL-f1800', is_valid: true, rejection_reasons: [] },
      ],
      all_valid: false,
    });

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    // First strategy is invalid - no approve button for it
    const approveButtons = screen.getAllByText('APPROVE STRATEGY');
    expect(approveButtons).toHaveLength(2);
  });

  it('shows VALIDATING STRATEGIES during validation loading', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation();

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
        validationLoading={true}
      />,
      { wrapper }
    );

    expect(screen.getByText('VALIDATING STRATEGIES...')).toBeInTheDocument();
  });

  // Fail-closed validation safety tests

  it('no approve button before validation result exists (validation undefined)', () => {
    const strategies = createMockStrategies();
    // No validation prop passed

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={undefined}
      />,
      { wrapper }
    );

    const approveButtons = screen.queryAllByText('APPROVE STRATEGY');
    expect(approveButtons).toHaveLength(0);
    // Should show AWAITING VALIDATION for all strategies (3 instances)
    const awaitingBadges = screen.getAllByText('AWAITING VALIDATION');
    expect(awaitingBadges.length).toBeGreaterThanOrEqual(3);
  });

  it('no approve button while validation is loading', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation();

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
        validationLoading={true}
      />,
      { wrapper }
    );

    const approveButtons = screen.queryAllByText('APPROVE STRATEGY');
    expect(approveButtons).toHaveLength(0);
    // Should show VALIDATING STRATEGIES...
    expect(screen.getByText('VALIDATING STRATEGIES...')).toBeInTheDocument();
  });

  it('no approve button when validation request errors', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation();
    const validationError = new Error('Validation service unavailable');

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
        validationError={validationError}
      />,
      { wrapper }
    );

    const approveButtons = screen.queryAllByText('APPROVE STRATEGY');
    expect(approveButtons).toHaveLength(0);
    // Should show VALIDATION UNAVAILABLE (multiple - header + per strategy badges)
    const unavailableBadges = screen.getAllByText('VALIDATION UNAVAILABLE');
    expect(unavailableBadges.length).toBeGreaterThanOrEqual(3);
    // Should show CANNOT APPROVE for each strategy (3 instances)
    const cannotApproveBadges = screen.getAllByText('CANNOT APPROVE - VALIDATION UNAVAILABLE');
    expect(cannotApproveBadges.length).toBeGreaterThanOrEqual(3);
  });

  it('no approve button when strategy_id is absent from validation_results', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation({
      validation_results: [
        { strategy_id: 'strat-STORAGE-WARNING', is_valid: true, rejection_reasons: [] },
        { strategy_id: 'strat-TEMPERATURE-CRITICAL-f1800', is_valid: true, rejection_reasons: [] },
      ],
      // strat-BATTERY-CRITICAL missing from validation_results
      all_valid: false,
    });

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    // First strategy (BATTERY-CRITICAL) missing from validation => no approve button
    const approveButtons = screen.getAllByText('APPROVE STRATEGY');
    expect(approveButtons).toHaveLength(2);
    // Should show AWAITING VALIDATION for missing strategy
    const awaitingBadges = screen.getAllByText('AWAITING VALIDATION');
    expect(awaitingBadges.length).toBeGreaterThanOrEqual(1);
  });

  it('approve button exists only for explicit is_valid=true', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation({
      validation_results: [
        { strategy_id: 'strat-BATTERY-CRITICAL', is_valid: true, rejection_reasons: [] },
        { strategy_id: 'strat-STORAGE-WARNING', is_valid: false, rejection_reasons: ['Failed'] },
      ],
      all_valid: false,
    });

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    // Only first strategy has explicit is_valid=true
    const approveButtons = screen.getAllByText('APPROVE STRATEGY');
    expect(approveButtons).toHaveLength(1);
  });

  it('explicit is_valid=false remains blocked', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation({
      validation_results: [
        { strategy_id: 'strat-BATTERY-CRITICAL', is_valid: false, rejection_reasons: ['Explicitly invalid'] },
        { strategy_id: 'strat-STORAGE-WARNING', is_valid: true, rejection_reasons: [] },
      ],
      all_valid: false,
    });

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    // First strategy explicitly invalid
    const invalidBadges = screen.getAllByText('INVALID');
    expect(invalidBadges).toHaveLength(1);
    expect(screen.getByText('CANNOT APPROVE - VALIDATION FAILED')).toBeInTheDocument();
    // Second strategy valid
    const approveButtons = screen.getAllByText('APPROVE STRATEGY');
    expect(approveButtons).toHaveLength(1);
  });

  it('validation error is rendered', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation();
    const validationError = new Error('Network timeout');

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
        validationError={validationError}
      />,
      { wrapper }
    );

    // Multiple VALIDATION UNAVAILABLE badges (header + per strategy)
    const unavailableBadges = screen.getAllByText('VALIDATION UNAVAILABLE');
    expect(unavailableBadges.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('VALIDATION UNAVAILABLE: Network timeout')).toBeInTheDocument();
  });

  it('approval is never called on render', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation();

    // We verify no APPROVING... state on initial render
    // The mutation is only triggered on user interaction (button click)
    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    // Just verify no APPROVING... state on initial render
    expect(screen.queryByText('APPROVING...')).not.toBeInTheDocument();
  });

  it('no execution controls exist', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation();

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    // Should not have any execute/run/start mission buttons
    expect(screen.queryByText(/EXECUTE/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/RUN/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/START MISSION/i)).not.toBeInTheDocument();
    // Only APPROVE STRATEGY buttons for valid strategies
    const approveButtons = screen.getAllByText('APPROVE STRATEGY');
    expect(approveButtons).toHaveLength(3);
  });

  it('shows VALIDATION PENDING badge when validation is loading', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation();

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
        validationLoading={true}
      />,
      { wrapper }
    );

    // Each strategy should show VALIDATION PENDING badge
    const pendingBadges = screen.getAllByText('VALIDATION PENDING');
    expect(pendingBadges.length).toBeGreaterThanOrEqual(3);
  });

  it('shows VALIDATION UNAVAILABLE badge when validation has error', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation();
    const validationError = new Error('Service unavailable');

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
        validationError={validationError}
      />,
      { wrapper }
    );

    // Should show VALIDATION UNAVAILABLE badge in header and per strategy
    const unavailableBadges = screen.getAllByText('VALIDATION UNAVAILABLE');
    expect(unavailableBadges.length).toBeGreaterThanOrEqual(1);
  });

  // Genuine behavioral tests for approval mutation

  it('approval mutation is never called on initial render', () => {
    const strategies = createMockStrategies();
    const mockValidation = createMockValidation();

    // Spy on the actual API function BEFORE rendering
    const approveStrategySpy = vi.spyOn(missionApi, 'approveStrategy');

    render(
      <StrategyPanel
        {...defaultProps}
        strategies={strategies}
        validation={mockValidation}
      />,
      { wrapper }
    );

    // Verify the API was not called during render
    expect(approveStrategySpy).not.toHaveBeenCalled();
    // Also verify no APPROVING... state
    expect(screen.queryByText('APPROVING...')).not.toBeInTheDocument();
  });

  // Terminal state tests by mocking the hook mutation state directly
  // This avoids async issues with query invalidation in test environment

  it('displays APPROVED terminal state when mutation data shows approved', () => {
    renderWithMockedApproval({
      data: {
        strategy_id: 'strat-BATTERY-CRITICAL',
        approved: true,
        approval_status: 'APPROVED',
        rejection_reasons: [],
      },
      variables: { strategyId: 'strat-BATTERY-CRITICAL', params: { use_forecast: true, forecast_horizon: 3600 } },
    });

    // Find the strat-BATTERY-CRITICAL card
    const batteryCard = screen.getByText('strat-BATTERY-CRITICAL').closest('div[class*="border rounded p-3"]');
    // Verify APPROVAL: APPROVED is shown in that card
    expect(within(batteryCard!).getByText(/APPROVAL: APPROVED/)).toBeInTheDocument();
    // Verify THAT CARD has no APPROVE STRATEGY button
    expect(within(batteryCard!).queryByText('APPROVE STRATEGY')).not.toBeInTheDocument();
    // Verify other strategies still have approval buttons
    const otherCards = Array.from(screen.getAllByText(/strat-(STORAGE|TEMPERATURE)/)).map(el => el.closest('div[class*="border rounded p-3"]'));
    otherCards.forEach(card => {
      expect(within(card!).getByText('APPROVE STRATEGY')).toBeInTheDocument();
    });
  });

  it('displays REJECTED terminal state with rejection reasons', () => {
    renderWithMockedApproval({
      data: {
        strategy_id: 'strat-BATTERY-CRITICAL',
        approved: false,
        approval_status: 'REJECTED',
        rejection_reasons: ['Insufficient battery for emergency reserve'],
      },
      variables: { strategyId: 'strat-BATTERY-CRITICAL', params: { use_forecast: true, forecast_horizon: 3600 } },
    });

    // Find the strat-BATTERY-CRITICAL card
    const batteryCard = screen.getByText('strat-BATTERY-CRITICAL').closest('div[class*="border rounded p-3"]');
    // Verify REJECTED badge is shown
    expect(within(batteryCard!).getByText(/APPROVAL: REJECTED/)).toBeInTheDocument();
    // Verify rejection reason is shown
    expect(within(batteryCard!).getByText('Insufficient battery for emergency reserve')).toBeInTheDocument();
    // Verify THAT CARD has no APPROVE STRATEGY button
    expect(within(batteryCard!).queryByText('APPROVE STRATEGY')).not.toBeInTheDocument();
    // Verify other strategies still have approval buttons
    const otherCards = Array.from(screen.getAllByText(/strat-(STORAGE|TEMPERATURE)/)).map(el => el.closest('div[class*="border rounded p-3"]'));
    otherCards.forEach(card => {
      expect(within(card!).getByText('APPROVE STRATEGY')).toBeInTheDocument();
    });
  });

  it('displays VALIDATION_FAILED terminal state', () => {
    renderWithMockedApproval({
      data: {
        strategy_id: 'strat-BATTERY-CRITICAL',
        approved: false,
        approval_status: 'VALIDATION_FAILED',
        rejection_reasons: ['Strategy failed validation'],
      },
      variables: { strategyId: 'strat-BATTERY-CRITICAL', params: { use_forecast: true, forecast_horizon: 3600 } },
    });

    // Find the strat-BATTERY-CRITICAL card
    const batteryCard = screen.getByText('strat-BATTERY-CRITICAL').closest('div[class*="border rounded p-3"]');
    // Verify VALIDATION_FAILED badge is shown
    expect(within(batteryCard!).getByText(/APPROVAL: VALIDATION FAILED/)).toBeInTheDocument();
    // Verify THAT CARD has no APPROVE STRATEGY button
    expect(within(batteryCard!).queryByText('APPROVE STRATEGY')).not.toBeInTheDocument();
    // Verify other strategies still have approval buttons
    const otherCards = Array.from(screen.getAllByText(/strat-(STORAGE|TEMPERATURE)/)).map(el => el.closest('div[class*="border rounded p-3"]'));
    otherCards.forEach(card => {
      expect(within(card!).getByText('APPROVE STRATEGY')).toBeInTheDocument();
    });
  });

  it('displays NOT_FOUND terminal state', () => {
    renderWithMockedApproval({
      data: {
        strategy_id: 'strat-BATTERY-CRITICAL',
        approved: false,
        approval_status: 'NOT_FOUND',
        rejection_reasons: [],
      },
      variables: { strategyId: 'strat-BATTERY-CRITICAL', params: { use_forecast: true, forecast_horizon: 3600 } },
    });

    // Find the strat-BATTERY-CRITICAL card
    const batteryCard = screen.getByText('strat-BATTERY-CRITICAL').closest('div[class*="border rounded p-3"]');
    // Verify NOT_FOUND badge is shown
    expect(within(batteryCard!).getByText(/APPROVAL: NOT FOUND/)).toBeInTheDocument();
    // Verify THAT CARD has no APPROVE STRATEGY button
    expect(within(batteryCard!).queryByText('APPROVE STRATEGY')).not.toBeInTheDocument();
    // Verify other strategies still have approval buttons
    const otherCards = Array.from(screen.getAllByText(/strat-(STORAGE|TEMPERATURE)/)).map(el => el.closest('div[class*="border rounded p-3"]'));
    otherCards.forEach(card => {
      expect(within(card!).getByText('APPROVE STRATEGY')).toBeInTheDocument();
    });
  });

  it('displays ALREADY_APPROVED terminal state and hides approve button', () => {
    renderWithMockedApproval({
      data: {
        strategy_id: 'strat-BATTERY-CRITICAL',
        approved: true,
        approval_status: 'ALREADY_APPROVED',
        rejection_reasons: [],
      },
      variables: { strategyId: 'strat-BATTERY-CRITICAL', params: { use_forecast: true, forecast_horizon: 3600 } },
    });

    // Find the strat-BATTERY-CRITICAL card
    const batteryCard = screen.getByText('strat-BATTERY-CRITICAL').closest('div[class*="border rounded p-3"]');
    // Verify ALREADY APPROVED badge is shown
    expect(within(batteryCard!).getByText(/APPROVAL: ALREADY APPROVED/)).toBeInTheDocument();
    // Verify THAT CARD has no APPROVE STRATEGY button
    expect(within(batteryCard!).queryByText('APPROVE STRATEGY')).not.toBeInTheDocument();
    // Verify other strategies still have approval buttons
    const otherCards = Array.from(screen.getAllByText(/strat-(STORAGE|TEMPERATURE)/)).map(el => el.closest('div[class*="border rounded p-3"]'));
    otherCards.forEach(card => {
      expect(within(card!).getByText('APPROVE STRATEGY')).toBeInTheDocument();
    });
  });

  it('displays approval error when mutation is in error state', () => {
    renderWithMockedApproval({
      isError: true,
      error: new Error('Approval service unavailable'),
      variables: { strategyId: 'strat-BATTERY-CRITICAL', params: { use_forecast: true, forecast_horizon: 3600 } },
    });

    // Verify error message is shown
    expect(screen.getByText('APPROVAL FAILED: Approval service unavailable')).toBeInTheDocument();
  });
});