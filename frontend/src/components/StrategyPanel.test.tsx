/** StrategyPanel tests */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrategyPanel } from './StrategyPanel';
import type { StrategyGenerationResponse, StrategyCandidate, AnomalyResource } from '../types/mission';

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
  });

  it('renders loading state when isLoading is true', () => {
    render(
      <StrategyPanel
        strategies={undefined}
        isLoading={true}
        error={null}
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
        strategies={undefined}
        isLoading={false}
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
        strategies={undefined}
        isLoading={false}
        error={null}
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

    render(
      <StrategyPanel
        strategies={strategies}
        isLoading={false}
        error={null}
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
    render(
      <StrategyPanel
        strategies={strategies}
        isLoading={false}
        error={null}
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
    render(
      <StrategyPanel
        strategies={strategies}
        isLoading={false}
        error={null}
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
    render(
      <StrategyPanel
        strategies={strategies}
        isLoading={false}
        error={null}
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
    render(
      <StrategyPanel
        strategies={strategies}
        isLoading={false}
        error={null}
      />,
      { wrapper }
    );

    expect(screen.getByText(/Battery critically low at 12%/)).toBeInTheDocument();
    expect(screen.getByText(/Storage high at 82%/)).toBeInTheDocument();
    expect(screen.getByText(/Temperature critically high at 65°C/)).toBeInTheDocument();
  });

  it('displays recommended actions for each strategy', () => {
    const strategies = createMockStrategies();
    render(
      <StrategyPanel
        strategies={strategies}
        isLoading={false}
        error={null}
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
    render(
      <StrategyPanel
        strategies={strategies}
        isLoading={false}
        error={null}
      />,
      { wrapper }
    );

    // All strategies have requires_operator_approval=true
    const approvalBadges = screen.getAllByText('APPROVAL REQUIRED');
    expect(approvalBadges).toHaveLength(3);
  });

  it('shows FORECAST-BASED badge for forecast strategies', () => {
    const strategies = createMockStrategies();
    render(
      <StrategyPanel
        strategies={strategies}
        isLoading={false}
        error={null}
      />,
      { wrapper }
    );

    // Third strategy has forecast source anomaly (contains -f)
    expect(screen.getByText('FORECAST-BASED')).toBeInTheDocument();
  });

  it('displays source anomalies for each strategy', () => {
    const strategies = createMockStrategies();
    render(
      <StrategyPanel
        strategies={strategies}
        isLoading={false}
        error={null}
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
    render(
      <StrategyPanel
        strategies={strategies}
        isLoading={false}
        error={null}
      />,
      { wrapper }
    );

    expect(screen.getByText('strat-BATTERY-CRITICAL')).toBeInTheDocument();
    expect(screen.getByText('strat-STORAGE-WARNING')).toBeInTheDocument();
    expect(screen.getByText('strat-TEMPERATURE-CRITICAL-f1800')).toBeInTheDocument();
  });

  it('shows PRIORITY 1 ACTIVE badge when has_critical_priority is true', () => {
    const strategies = createMockStrategies({ has_critical_priority: true });
    render(
      <StrategyPanel
        strategies={strategies}
        isLoading={false}
        error={null}
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
    render(
      <StrategyPanel
        strategies={strategies}
        isLoading={false}
        error={null}
      />,
      { wrapper }
    );

    expect(screen.queryByText('PRIORITY 1 ACTIVE')).not.toBeInTheDocument();
  });
});