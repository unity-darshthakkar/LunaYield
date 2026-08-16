/** ForecastPanel tests */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ForecastPanel } from './ForecastPanel';
import type { MissionForecastResponse, ForecastPoint, ResourceForecast } from '../types/mission';

// Mock forecast data
const createMockForecast = (overrides: Partial<MissionForecastResponse> = {}): MissionForecastResponse => {
  const mockResources: ResourceForecast = {
    battery_pct: 85.5,
    storage_pct: 12.3,
    temperature_c: 22.1,
    comm_window_remaining_s: 5400,
    op_time_remaining_s: 25200,
  };

  const mockPoints: ForecastPoint[] = [
    {
      forecast_seconds_ahead: 600,
      elapsed_s: 600,
      resources: { ...mockResources, battery_pct: 83.0, storage_pct: 14.1 },
    },
    {
      forecast_seconds_ahead: 1800,
      elapsed_s: 1800,
      resources: { ...mockResources, battery_pct: 78.5, storage_pct: 19.8 },
    },
    {
      forecast_seconds_ahead: 3600,
      elapsed_s: 3600,
      resources: { ...mockResources, battery_pct: 71.0, storage_pct: 28.4 },
    },
  ];

  return {
    mission_id: 'test-mission',
    current_elapsed_s: 0,
    current_resources: mockResources,
    forecast_horizon_s: 3600,
    forecast_tick_interval_s: 60,
    forecast_points: mockPoints,
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

describe('ForecastPanel', () => {
  let wrapper: ReturnType<typeof createWrapper>;

  beforeEach(() => {
    wrapper = createWrapper();
    vi.useFakeTimers();
  });

  it('renders loading state when isLoading is true', () => {
    render(
      <ForecastPanel
        forecast={undefined}
        isLoading={true}
        error={null}
        horizon={3600}
        onHorizonChange={vi.fn()}
      />,
      { wrapper }
    );

    expect(screen.getByText('RESOURCE FORECAST')).toBeInTheDocument();
    expect(screen.getByRole('status', { name: /loading forecast/i })).toBeInTheDocument();
  });

  it('renders error state when error is present', () => {
    const mockError = new Error('Network error');
    render(
      <ForecastPanel
        forecast={undefined}
        isLoading={false}
        error={mockError}
        horizon={3600}
        onHorizonChange={vi.fn()}
      />,
      { wrapper }
    );

    expect(screen.getByText('FORECAST ERROR')).toBeInTheDocument();
    expect(screen.getByText('Network error')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });

  it('renders empty state when forecast is undefined and not loading', () => {
    render(
      <ForecastPanel
        forecast={undefined}
        isLoading={false}
        error={null}
        horizon={3600}
        onHorizonChange={vi.fn()}
      />,
      { wrapper }
    );

    expect(screen.getByText('RESOURCE FORECAST')).toBeInTheDocument();
    expect(screen.getByText('No forecast data available')).toBeInTheDocument();
  });

  it('renders forecast data with horizon selector', () => {
    const forecast = createMockForecast();
    render(
      <ForecastPanel
        forecast={forecast}
        isLoading={false}
        error={null}
        horizon={3600}
        onHorizonChange={vi.fn()}
      />,
      { wrapper }
    );

    expect(screen.getByText('RESOURCE FORECAST')).toBeInTheDocument();
    expect(screen.getByDisplayValue('1 hour')).toBeInTheDocument();
    // Horizon metadata is split across text nodes and span - verify the container text
    const metaContainer = screen.getByTestId('forecast-meta');
    expect(metaContainer).toHaveTextContent('Horizon: 1 hour');
    expect(metaContainer).toHaveTextContent('Interval: 60s');
    expect(metaContainer).toHaveTextContent('Points: 3');
  });

  it('shows forecast points with resource values', () => {
    const forecast = createMockForecast();
    render(
      <ForecastPanel
        forecast={forecast}
        isLoading={false}
        error={null}
        horizon={3600}
        onHorizonChange={vi.fn()}
      />,
      { wrapper }
    );

    // Check key forecast points are shown
    expect(screen.getByText('T+0.2h')).toBeInTheDocument(); // 600s = 0.16h ≈ 0.2h
    expect(screen.getByText('T+0.5h')).toBeInTheDocument(); // 1800s = 0.5h
    expect(screen.getByText('T+1.0h')).toBeInTheDocument(); // 3600s = 1.0h
  });

  it('displays resource values with color coding', () => {
    const forecast = createMockForecast();
    render(
      <ForecastPanel
        forecast={forecast}
        isLoading={false}
        error={null}
        horizon={3600}
        onHorizonChange={vi.fn()}
      />,
      { wrapper }
    );

    // Battery values should be displayed
    expect(screen.getByText('83.0')).toBeInTheDocument();
    expect(screen.getByText('78.5')).toBeInTheDocument();
    expect(screen.getByText('71.0')).toBeInTheDocument();
  });

  it('shows legend with nominal/warning/critical indicators', () => {
    const forecast = createMockForecast();
    render(
      <ForecastPanel
        forecast={forecast}
        isLoading={false}
        error={null}
        horizon={3600}
        onHorizonChange={vi.fn()}
      />,
      { wrapper }
    );

    expect(screen.getByText('Nominal')).toBeInTheDocument();
    expect(screen.getByText('Warning')).toBeInTheDocument();
    expect(screen.getByText('Critical')).toBeInTheDocument();
  });

  it('calls onHorizonChange when horizon selector changes', () => {
    const forecast = createMockForecast();
    const handleChange = vi.fn();
    render(
      <ForecastPanel
        forecast={forecast}
        isLoading={false}
        error={null}
        horizon={3600}
        onHorizonChange={handleChange}
      />,
      { wrapper }
    );

    const selector = screen.getByDisplayValue('1 hour');
    fireEvent.change(selector, { target: { value: '7200' } });

    expect(handleChange).toHaveBeenCalledWith(7200);
  });

  it('shows empty message when no forecast points', () => {
    const forecast = createMockForecast({ forecast_points: [] });
    render(
      <ForecastPanel
        forecast={forecast}
        isLoading={false}
        error={null}
        horizon={3600}
        onHorizonChange={vi.fn()}
      />,
      { wrapper }
    );

    expect(screen.getByText('No forecast points generated')).toBeInTheDocument();
  });

  it('displays resource headers (BATT, STOR, TEMP, COMM, OPS)', () => {
    const forecast = createMockForecast();
    render(
      <ForecastPanel
        forecast={forecast}
        isLoading={false}
        error={null}
        horizon={3600}
        onHorizonChange={vi.fn()}
      />,
      { wrapper }
    );

    expect(screen.getByText('BATT')).toBeInTheDocument();
    expect(screen.getByText('STOR')).toBeInTheDocument();
    expect(screen.getByText('TEMP')).toBeInTheDocument();
    expect(screen.getByText('COMM')).toBeInTheDocument();
    expect(screen.getByText('OPS')).toBeInTheDocument();
  });
});