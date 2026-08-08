/** ResourcePanel component tests */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ResourcePanel } from './ResourcePanel';
import type { RoverResources } from '../types/mission';

const mockResources: RoverResources = {
  battery_pct: 75.5,
  storage_pct: 23.1,
  temperature_c: -38.2,
  comm_window_remaining_s: 3600,
  op_time_remaining_s: 14400,
};

describe('ResourcePanel', () => {
  it('renders resource values correctly', () => {
    render(<ResourcePanel resources={mockResources} />);
    expect(screen.getByText('75.5%')).toBeInTheDocument();
    expect(screen.getByText('23.1%')).toBeInTheDocument();
    expect(screen.getByText('-38.2°C')).toBeInTheDocument();
  });

  it('renders battery progress bar container', () => {
    render(<ResourcePanel resources={mockResources} />);
    expect(screen.getByText('BATTERY')).toBeInTheDocument();
  });

  it('renders storage progress bar', () => {
    render(<ResourcePanel resources={mockResources} />);
    expect(screen.getByText('STORAGE')).toBeInTheDocument();
  });

  it('formats comm window as time', () => {
    render(<ResourcePanel resources={mockResources} />);
    expect(screen.getByText('COMM WINDOW')).toBeInTheDocument();
    // 3600 seconds = 1h 0m 0s - check for time parts (text may be split across elements)
    const container = screen.getByText('COMM WINDOW').closest('div');
    expect(container?.textContent).toContain('1h');
    expect(container?.textContent).toContain('0m');
  });

  it('formats op time as time', () => {
    render(<ResourcePanel resources={mockResources} />);
    expect(screen.getByText('OP TIME')).toBeInTheDocument();
    // 14400 seconds = 4h
    const container = screen.getByText('OP TIME').closest('div');
    expect(container?.textContent).toContain('4h');
  });

  it('shows awaiting message when resources is undefined', () => {
    render(<ResourcePanel resources={undefined} />);
    expect(screen.getByText('Awaiting mission data...')).toBeInTheDocument();
  });

  it('renders battery when low', () => {
    const lowBatteryResources = { ...mockResources, battery_pct: 25 };
    render(<ResourcePanel resources={lowBatteryResources} />);
    expect(screen.getByText('BATTERY')).toBeInTheDocument();
    expect(screen.getByText('25.0%')).toBeInTheDocument();
  });

  it('renders battery when critical', () => {
    const criticalBatteryResources = { ...mockResources, battery_pct: 15 };
    render(<ResourcePanel resources={criticalBatteryResources} />);
    expect(screen.getByText('BATTERY')).toBeInTheDocument();
    expect(screen.getByText('15.0%')).toBeInTheDocument();
  });

  it('displays temperature with °C unit', () => {
    render(<ResourcePanel resources={mockResources} />);
    expect(screen.getByText('-38.2°C')).toBeInTheDocument();
  });

  it('renders ROVER RESOURCES header', () => {
    render(<ResourcePanel resources={mockResources} />);
    expect(screen.getByText('ROVER RESOURCES')).toBeInTheDocument();
  });
});