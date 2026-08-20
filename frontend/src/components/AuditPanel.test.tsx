/** AuditPanel component tests */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AuditPanel } from './AuditPanel';
import type { AuditEvent } from '../types/mission';

const mockEvents: AuditEvent[] = [
  {
    event_id: 'audit-001',
    event_type: 'mission.initialized',
    description: 'Mission scenario loaded from seed data.',
    timestamp: '2026-08-06T00:00:00.000Z',
    metadata: { mission_id: 'luna-mission-001' },
  },
  {
    event_id: 'audit-002',
    event_type: 'mission.started',
    description: 'Mission started by operator',
    timestamp: '2026-08-06T12:00:00.000Z',
    metadata: { mission_id: 'luna-mission-001' },
  },
  {
    event_id: 'audit-003',
    event_type: 'anomaly.injected',
    description: 'Battery anomaly injected',
    timestamp: '2026-08-06T12:05:00.000Z',
    metadata: { mission_id: 'luna-mission-001' },
  },
  {
    event_id: 'audit-004',
    event_type: 'plans.generated',
    description: 'Generated 3 candidate plans',
    timestamp: '2026-08-06T12:06:00.000Z',
    metadata: { mission_id: 'luna-mission-001', plan_count: 3 },
  },
  {
    event_id: 'audit-005',
    event_type: 'plan.approved',
    description: 'Plan Extended Survey (plan-b-001) approved and activated',
    timestamp: '2026-08-06T12:10:00.000Z',
    metadata: { mission_id: 'luna-mission-001', approved_plan_id: 'plan-b-001', plan_label: 'Extended Survey' },
  },
];

describe('AuditPanel', () => {
  it('renders all audit events', () => {
    render(<AuditPanel events={mockEvents} />);
    expect(screen.getByText('mission.initialized')).toBeInTheDocument();
    expect(screen.getByText('mission.started')).toBeInTheDocument();
    expect(screen.getByText('anomaly.injected')).toBeInTheDocument();
    expect(screen.getByText('plans.generated')).toBeInTheDocument();
    expect(screen.getByText('plan.approved')).toBeInTheDocument();
  });

  it('renders event descriptions', () => {
    render(<AuditPanel events={mockEvents} />);
    expect(screen.getByText('Mission scenario loaded from seed data.')).toBeInTheDocument();
    expect(screen.getByText('Mission started by operator')).toBeInTheDocument();
    expect(screen.getByText('Battery anomaly injected')).toBeInTheDocument();
    expect(screen.getByText('Generated 3 candidate plans')).toBeInTheDocument();
    expect(screen.getByText('Plan Extended Survey (plan-b-001) approved and activated')).toBeInTheDocument();
  });

  it('renders timestamps in time format', () => {
    render(<AuditPanel events={mockEvents} />);
    // Timestamps should be formatted as time strings (HH:MM:SS format)
    const timeElements = screen.getAllByText(/\d{2}:\d{2}:\d{2}/);
    expect(timeElements.length).toBeGreaterThanOrEqual(5);
  });

  it('shows events in newest-first order', () => {
    render(<AuditPanel events={mockEvents} />);
    const container = screen.getByText('AUDIT TRAIL').closest('div')!;
    const text = container.textContent || '';
    const planApprovedIndex = text.indexOf('plan.approved');
    const missionInitializedIndex = text.indexOf('mission.initialized');
    expect(planApprovedIndex).toBeLessThan(missionInitializedIndex);
  });

  it('shows event count in header', () => {
    render(<AuditPanel events={mockEvents} />);
    expect(screen.getByText('(5 events)')).toBeInTheDocument();
  });

  it('renders metadata when present (as JSON string)', () => {
    render(<AuditPanel events={mockEvents} />);
    // Metadata is rendered as a JSON string in a truncate element
    // Use a more flexible matcher
    const container = screen.getByText('AUDIT TRAIL').closest('div')!;
    const text = container.textContent || '';
    expect(text).toContain('mission_id');
    expect(text).toContain('plan_count');
    expect(text).toContain('approved_plan_id');
  });

  it('shows empty state when no events', () => {
    render(<AuditPanel events={[]} />);
    expect(screen.getByText('No audit events yet')).toBeInTheDocument();
  });

  it('shows empty state when events is undefined', () => {
    render(<AuditPanel events={undefined} />);
    expect(screen.getByText('No audit events yet')).toBeInTheDocument();
  });

  it('renders AUDIT TRAIL header', () => {
    render(<AuditPanel events={mockEvents} />);
    expect(screen.getByText('AUDIT TRAIL')).toBeInTheDocument();
  });

  it('displays mission.paused and mission.resumed events', () => {
    const eventsWithPause: AuditEvent[] = [
      ...mockEvents,
      {
        event_id: 'audit-006',
        event_type: 'mission.paused',
        description: 'Mission paused by operator',
        timestamp: '2026-08-06T12:03:00.000Z',
        metadata: { mission_id: 'luna-mission-001' },
      },
      {
        event_id: 'audit-007',
        event_type: 'mission.resumed',
        description: 'Mission resumed by operator',
        timestamp: '2026-08-06T12:04:00.000Z',
        metadata: { mission_id: 'luna-mission-001' },
      },
    ];
    render(<AuditPanel events={eventsWithPause} />);
    expect(screen.getByText('mission.paused')).toBeInTheDocument();
    expect(screen.getByText('mission.resumed')).toBeInTheDocument();
  });

  it('displays planning.started event', () => {
    const eventsWithPlanning: AuditEvent[] = [
      ...mockEvents,
      {
        event_id: 'audit-008',
        event_type: 'planning.started',
        description: 'Candidate plan generation initiated',
        timestamp: '2026-08-06T12:05:30.000Z',
        metadata: { mission_id: 'luna-mission-001' },
      },
    ];
    render(<AuditPanel events={eventsWithPlanning} />);
    expect(screen.getByText('planning.started')).toBeInTheDocument();
    expect(screen.getByText('Candidate plan generation initiated')).toBeInTheDocument();
  });

  it('displays mission.reset event', () => {
    const eventsWithReset: AuditEvent[] = [
      ...mockEvents,
      {
        event_id: 'audit-009',
        event_type: 'mission.reset',
        description: 'Mission reset to seed state',
        timestamp: '2026-08-06T13:00:00.000Z',
        metadata: { mission_id: 'luna-mission-001' },
      },
    ];
    render(<AuditPanel events={eventsWithReset} />);
    expect(screen.getByText('mission.reset')).toBeInTheDocument();
    expect(screen.getByText('Mission reset to seed state')).toBeInTheDocument();
  });

  it('displays new route, science, and completion events', () => {
    const completedEvents: AuditEvent[] = [
      ...mockEvents,
      {
        event_id: 'audit-010',
        event_type: 'waypoint.reached',
        description: 'Reached Ridge Observation Point',
        timestamp: '2026-08-06T12:20:00.000Z',
        metadata: { mission_id: 'luna-mission-001', waypoint_id: 'wp-ridge' },
      },
      {
        event_id: 'audit-011',
        event_type: 'science.collected',
        description: 'Science collection completed at Ridge Observation Point',
        timestamp: '2026-08-06T12:21:00.000Z',
        metadata: { mission_id: 'luna-mission-001', storage_pct: 100 },
      },
      {
        event_id: 'audit-012',
        event_type: 'mission.completed',
        description: 'Mission completed and rover returned to Base Camp',
        timestamp: '2026-08-06T12:30:00.000Z',
        metadata: { mission_id: 'luna-mission-001', elapsed_s: 296 },
      },
    ];

    render(<AuditPanel events={completedEvents} />);
    expect(screen.getByText('waypoint.reached')).toBeInTheDocument();
    expect(screen.getByText('science.collected')).toBeInTheDocument();
    expect(screen.getByText('mission.completed')).toBeInTheDocument();
  });
});
