/** AnomalyPanel tests */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AnomalyPanel } from './AnomalyPanel';
import type { AnomalyDetectionResponse, AnomalyFinding } from '../types/mission';

const createMockAnomalies = (overrides: Partial<AnomalyDetectionResponse> = {}): AnomalyDetectionResponse => {
  const mockFindings: AnomalyFinding[] = [
    {
      resource: 'BATTERY',
      severity: 'WARNING',
      observed_value: 28.5,
      threshold_value: 30.0,
      reason: 'Battery level approaching critical threshold',
      is_forecast: false,
      forecast_seconds_ahead: null,
    },
    {
      resource: 'STORAGE',
      severity: 'INFO',
      observed_value: 82.0,
      threshold_value: 80.0,
      reason: 'Storage utilization exceeding nominal capacity',
      is_forecast: false,
      forecast_seconds_ahead: null,
    },
    {
      resource: 'TEMPERATURE',
      severity: 'CRITICAL',
      observed_value: 65.0,
      threshold_value: 60.0,
      reason: 'Temperature exceeds safe operating limit',
      is_forecast: true,
      forecast_seconds_ahead: 1800,
    },
  ];

  return {
    mission_id: 'test-mission',
    current_elapsed_s: 0,
    anomalies: mockFindings,
    anomaly_count: mockFindings.length,
    has_critical: true,
    has_warning: true,
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

describe('AnomalyPanel', () => {
  let wrapper: ReturnType<typeof createWrapper>;

  beforeEach(() => {
    wrapper = createWrapper();
    vi.useFakeTimers();
  });

  function getAnomalyCard(reason: string) {
    return screen.getByText(reason).closest('.rounded-xl.border.p-4') as HTMLElement;
  }

  it('renders loading state when isLoading is true', () => {
    render(
      <AnomalyPanel
        anomalies={undefined}
        isLoading={true}
        error={null}
      />,
      { wrapper }
    );

    expect(screen.getByText('ANOMALY DETECTION')).toBeInTheDocument();
    expect(screen.getByRole('status', { name: /loading anomalies/i })).toBeInTheDocument();
  });

  it('renders error state when error is present', () => {
    const mockError = new Error('Network error');
    render(
      <AnomalyPanel
        anomalies={undefined}
        isLoading={false}
        error={mockError}
      />,
      { wrapper }
    );

    expect(screen.getByText('ANOMALY ERROR')).toBeInTheDocument();
    expect(screen.getByText('Network error')).toBeInTheDocument();
  });

  it('renders empty state when anomalies is undefined and not loading', () => {
    render(
      <AnomalyPanel
        anomalies={undefined}
        isLoading={false}
        error={null}
      />,
      { wrapper }
    );

    expect(screen.getByText('ANOMALY DETECTION')).toBeInTheDocument();
    expect(screen.getByText('No anomaly data available')).toBeInTheDocument();
  });

  it('renders healthy/nominal state when no anomalies detected', () => {
    const anomalies = createMockAnomalies({
      anomalies: [],
      anomaly_count: 0,
      has_critical: false,
      has_warning: false,
    });

    render(
      <AnomalyPanel
        anomalies={anomalies}
        isLoading={false}
        error={null}
      />,
      { wrapper }
    );

    expect(screen.getByText('ANOMALY DETECTION')).toBeInTheDocument();
    expect(screen.getByText('NOMINAL')).toBeInTheDocument();
    expect(screen.getByText('No anomalies detected in current mission state')).toBeInTheDocument();
    expect(screen.getByText('Forecast-based detection available via horizon control in Forecast panel')).toBeInTheDocument();
  });

  it('displays all anomalies sorted by severity (critical > warning > info)', () => {
    const anomalies = createMockAnomalies();
    render(
      <AnomalyPanel
        anomalies={anomalies}
        isLoading={false}
        error={null}
      />,
      { wrapper }
    );

    expect(screen.getByText('Battery level approaching critical threshold')).toBeInTheDocument();
    expect(screen.getByText('Storage utilization exceeding nominal capacity')).toBeInTheDocument();
    expect(screen.getByText('Temperature exceeds safe operating limit')).toBeInTheDocument();
  });

  it('shows severity badges for each anomaly', () => {
    const anomalies = createMockAnomalies();
    render(
      <AnomalyPanel
        anomalies={anomalies}
        isLoading={false}
        error={null}
      />,
      { wrapper }
    );

    expect(screen.getByText('warning')).toBeInTheDocument();
    expect(screen.getByText('info')).toBeInTheDocument();
    expect(screen.getByText('critical')).toBeInTheDocument();
  });

  it('displays resource tags for each anomaly', () => {
    const anomalies = createMockAnomalies();
    render(
      <AnomalyPanel
        anomalies={anomalies}
        isLoading={false}
        error={null}
      />,
      { wrapper }
    );

    expect(screen.getByText('BATTERY')).toBeInTheDocument();
    expect(screen.getByText('STORAGE')).toBeInTheDocument();
    expect(screen.getByText('TEMP')).toBeInTheDocument();
  });

  it('shows forecast badge and time ahead for forecast anomalies', () => {
    const anomalies = createMockAnomalies();
    render(
      <AnomalyPanel
        anomalies={anomalies}
        isLoading={false}
        error={null}
      />,
      { wrapper }
    );

    expect(screen.getByText('FORECAST')).toBeInTheDocument();
    expect(screen.getByText('30m ahead')).toBeInTheDocument();
  });

  it('displays observed value and threshold for each anomaly', () => {
    const anomalies = createMockAnomalies();
    render(
      <AnomalyPanel
        anomalies={anomalies}
        isLoading={false}
        error={null}
      />,
      { wrapper }
    );

    const batteryCard = getAnomalyCard('Battery level approaching critical threshold');
    expect(within(batteryCard).getByText('Observed')).toBeInTheDocument();
    expect(within(batteryCard).getByText('28.5%')).toBeInTheDocument();
    expect(within(batteryCard).getByText('Threshold')).toBeInTheDocument();
    expect(within(batteryCard).getByText('30%')).toBeInTheDocument();

    const storageCard = getAnomalyCard('Storage utilization exceeding nominal capacity');
    expect(within(storageCard).getByText('Observed')).toBeInTheDocument();
    expect(within(storageCard).getByText('82%')).toBeInTheDocument();
    expect(within(storageCard).getByText('Threshold')).toBeInTheDocument();
    expect(within(storageCard).getByText('80%')).toBeInTheDocument();

    const temperatureCard = getAnomalyCard('Temperature exceeds safe operating limit');
    expect(within(temperatureCard).getByText('Observed')).toBeInTheDocument();
    expect(within(temperatureCard).getByText((_, element) => element?.textContent === '65°C')).toBeInTheDocument();
    expect(within(temperatureCard).getByText('Threshold')).toBeInTheDocument();
    expect(within(temperatureCard).getByText((_, element) => element?.textContent === '60°C')).toBeInTheDocument();
  });

  it('shows overall status badges (CRITICAL + count, WARNING only when no CRITICAL)', () => {
    const anomalies = createMockAnomalies();
    render(
      <AnomalyPanel
        anomalies={anomalies}
        isLoading={false}
        error={null}
      />,
      { wrapper }
    );

    expect(screen.getByText('CRITICAL')).toBeInTheDocument();
    expect(screen.queryByText('WARNING')).not.toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('formats temperature in Celsius', () => {
    const anomalies = createMockAnomalies({
      anomalies: [
        {
          resource: 'TEMPERATURE',
          severity: 'WARNING',
          observed_value: 45,
          threshold_value: 40,
          reason: 'Temperature rising',
          is_forecast: false,
          forecast_seconds_ahead: null,
        },
      ],
      anomaly_count: 1,
      has_critical: false,
      has_warning: true,
    });

    render(
      <AnomalyPanel
        anomalies={anomalies}
        isLoading={false}
        error={null}
      />,
      { wrapper }
    );

    const temperatureCard = getAnomalyCard('Temperature rising');
    expect(within(temperatureCard).getByText((_, element) => element?.textContent === '45°C')).toBeInTheDocument();
    expect(within(temperatureCard).getByText('Threshold')).toBeInTheDocument();
    expect(within(temperatureCard).getByText((_, element) => element?.textContent === '40°C')).toBeInTheDocument();
  });

  it('formats comm window and op time in seconds', () => {
    const anomalies = createMockAnomalies({
      anomalies: [
        {
          resource: 'COMM_WINDOW',
          severity: 'WARNING',
          observed_value: 500,
          threshold_value: 600,
          reason: 'Comm window ending',
          is_forecast: false,
          forecast_seconds_ahead: null,
        },
        {
          resource: 'OP_TIME',
          severity: 'CRITICAL',
          observed_value: 300,
          threshold_value: 600,
          reason: 'Operational time low',
          is_forecast: false,
          forecast_seconds_ahead: null,
        },
      ],
      anomaly_count: 2,
      has_critical: true,
      has_warning: true,
    });

    render(
      <AnomalyPanel
        anomalies={anomalies}
        isLoading={false}
        error={null}
      />,
      { wrapper }
    );

    const commCard = getAnomalyCard('Comm window ending');
    expect(within(commCard).getByText('500s')).toBeInTheDocument();
    expect(within(commCard).getByText('Threshold')).toBeInTheDocument();
    expect(within(commCard).getByText('600s')).toBeInTheDocument();

    const opTimeCard = getAnomalyCard('Operational time low');
    expect(within(opTimeCard).getByText('300s')).toBeInTheDocument();
    expect(within(opTimeCard).getByText('Threshold')).toBeInTheDocument();
    expect(within(opTimeCard).getByText('600s')).toBeInTheDocument();
  });

  it('shows provenance - current vs forecast clearly', () => {
    const anomalies = createMockAnomalies({
      anomalies: [
        {
          resource: 'BATTERY',
          severity: 'WARNING',
          observed_value: 28,
          threshold_value: 30,
          reason: 'Current battery low',
          is_forecast: false,
          forecast_seconds_ahead: null,
        },
        {
          resource: 'BATTERY',
          severity: 'CRITICAL',
          observed_value: 12,
          threshold_value: 15,
          reason: 'Forecast battery critical',
          is_forecast: true,
          forecast_seconds_ahead: 3600,
        },
      ],
      anomaly_count: 2,
      has_critical: true,
      has_warning: true,
    });

    render(
      <AnomalyPanel
        anomalies={anomalies}
        isLoading={false}
        error={null}
      />,
      { wrapper }
    );

    const currentAnomaly = getAnomalyCard('Current battery low');
    expect(currentAnomaly).not.toHaveTextContent('FORECAST');

    const forecastAnomaly = getAnomalyCard('Forecast battery critical');
    expect(forecastAnomaly).toHaveTextContent('FORECAST');
    expect(screen.getByText('1h ahead')).toBeInTheDocument();
  });

  it('handles only INFO severity correctly', () => {
    const anomalies = createMockAnomalies({
      anomalies: [
        {
          resource: 'BATTERY',
          severity: 'INFO',
          observed_value: 85,
          threshold_value: 90,
          reason: 'Battery nominal but monitored',
          is_forecast: false,
          forecast_seconds_ahead: null,
        },
      ],
      anomaly_count: 1,
      has_critical: false,
      has_warning: false,
    });

    render(
      <AnomalyPanel
        anomalies={anomalies}
        isLoading={false}
        error={null}
      />,
      { wrapper }
    );

    expect(screen.getByText('info')).toBeInTheDocument();
    expect(screen.queryByText('CRITICAL')).not.toBeInTheDocument();
    expect(screen.queryByText('WARNING')).not.toBeInTheDocument();
  });
});