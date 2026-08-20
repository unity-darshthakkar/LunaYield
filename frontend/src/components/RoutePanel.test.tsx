/** RoutePanel component tests */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RoutePanel } from '../components/RoutePanel';
import type { MissionRoute } from '../types/mission';
import { WaypointProgressStatus } from '../types/mission';

const mockRoute: MissionRoute = {
  waypoints: [
    {
      id: 'wp-1',
      label: 'Base Camp',
      x: 0.1,
      y: 0.1,
      is_science_target: false,
      progress_status: WaypointProgressStatus.COMPLETED,
    },
    {
      id: 'wp-2',
      label: 'Crater A Rim',
      x: 0.3,
      y: 0.4,
      is_science_target: true,
      progress_status: WaypointProgressStatus.CURRENT,
    },
    {
      id: 'wp-3',
      label: 'Ice Deposit Site',
      x: 0.5,
      y: 0.6,
      is_science_target: true,
      progress_status: WaypointProgressStatus.UPCOMING,
    },
  ],
};

describe('RoutePanel', () => {
  it('displays active route header with waypoint count', () => {
    render(<RoutePanel activeRoute={mockRoute} originalRoute={undefined} />);
    expect(screen.getByText('ACTIVE ROUTE')).toBeInTheDocument();
    expect(screen.getByText('(3 waypoints)')).toBeInTheDocument();
  });

  it('falls back to originalRoute when activeRoute is undefined', () => {
    render(<RoutePanel activeRoute={undefined} originalRoute={mockRoute} />);
    expect(screen.getByText('ACTIVE ROUTE')).toBeInTheDocument();
    expect(screen.getByText('(3 waypoints)')).toBeInTheDocument();
  });

  it('shows no route message when both routes are undefined', () => {
    render(<RoutePanel activeRoute={undefined} originalRoute={undefined} />);
    expect(screen.getByText('No route data available')).toBeInTheDocument();
  });

  it('displays approved plan label when provided', () => {
    render(
      <RoutePanel
        activeRoute={mockRoute}
        originalRoute={undefined}
        approvedPlanLabel="Extended Survey"
      />
    );
    expect(screen.getByText('Approved plan: Extended Survey')).toBeInTheDocument();
  });

  it('renders backend-authoritative waypoint progress states', () => {
    render(<RoutePanel activeRoute={mockRoute} originalRoute={undefined} />);

    expect(screen.getByText('COMPLETED')).toBeInTheDocument();
    expect(screen.getByText('CURRENT')).toBeInTheDocument();
    expect(screen.getByText('UPCOMING')).toBeInTheDocument();
  });

  it('does not display approved plan label when not provided', () => {
    render(<RoutePanel activeRoute={mockRoute} originalRoute={undefined} />);
    expect(screen.queryByText(/Approved plan:/i)).not.toBeInTheDocument();
  });

  it('does not display approved plan label when empty string', () => {
    render(
      <RoutePanel
        activeRoute={mockRoute}
        originalRoute={undefined}
        approvedPlanLabel=""
      />
    );
    expect(screen.queryByText(/Approved plan:/i)).not.toBeInTheDocument();
  });
});
