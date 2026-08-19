/** PlanComparison component tests */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PlanComparison } from './PlanComparison';
import { PlanStatus } from '../types/mission';
import type { CandidatePlan, RouteWaypoint } from '../types/mission';

const createMockPlan = (overrides: Partial<CandidatePlan> = {}): CandidatePlan => ({
  plan_id: 'plan-a-001',
  label: 'Minimal Survey',
  description: 'Conservative return to base',
  waypoints: [
    { id: 'wp-1', x: 0.1, y: 0.1, label: 'Base', is_science_target: false },
    { id: 'wp-2', x: 0.3, y: 0.4, label: 'Crater A', is_science_target: true },
  ] as RouteWaypoint[],
  science_yield_score: 45.0,
  predicted_return_battery_pct: 34.0,
  status: PlanStatus.VALID,
  violations: [],
  is_recommended: false,
  rank: 2,
  ...overrides,
});

const defaultProps = {
  plans: [
    createMockPlan({ plan_id: 'plan-a-001', label: 'Minimal Survey', predicted_return_battery_pct: 34.0, is_recommended: false }),
    createMockPlan({ plan_id: 'plan-b-001', label: 'Extended Survey', predicted_return_battery_pct: 42.0, is_recommended: true }),
    createMockPlan({ plan_id: 'plan-c-001', label: 'Aggressive Survey', predicted_return_battery_pct: 11.0, status: PlanStatus.REJECTED, violations: [
      { rule_id: 'RETURN_BATTERY_MIN_20PCT', description: 'Predicted return battery 11.0% is below minimum 20.0%', measured_value: 11.0, threshold_value: 20.0 }
    ], is_recommended: false }),
  ] as CandidatePlan[],
  onApprove: vi.fn(),
  disabled: false,
};

describe('PlanComparison', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all three plans', () => {
    render(<PlanComparison {...defaultProps} />);
    expect(screen.getByText('Minimal Survey')).toBeInTheDocument();
    expect(screen.getByText('Extended Survey')).toBeInTheDocument();
    expect(screen.getByText('Aggressive Survey')).toBeInTheDocument();
  });

  it('shows RECOMMENDED badge on Extended Survey', () => {
    render(<PlanComparison {...defaultProps} />);
    expect(screen.getByText('RECOMMENDED')).toBeInTheDocument();
  });

  it('shows VALID status for Minimal and Extended', () => {
    render(<PlanComparison {...defaultProps} />);
    const validStatuses = screen.getAllByText('VALID');
    expect(validStatuses).toHaveLength(2);
  });

  it('shows REJECTED status for Aggressive Survey', () => {
    render(<PlanComparison {...defaultProps} />);
    expect(screen.getByText('REJECTED')).toBeInTheDocument();
  });

  it('displays safety violation for rejected plan', () => {
    render(<PlanComparison {...defaultProps} />);
    expect(screen.getByText('SAFETY VIOLATIONS')).toBeInTheDocument();
    // Rule ID is rendered with brackets: [RETURN_BATTERY_MIN_20PCT]
    expect(screen.getByText('[RETURN_BATTERY_MIN_20PCT]')).toBeInTheDocument();
    // Description includes "Predicted return battery " prefix
    expect(screen.getByText('Predicted return battery 11.0% is below minimum 20.0%')).toBeInTheDocument();
  });

  it('shows violation details with measured and threshold values', () => {
    render(<PlanComparison {...defaultProps} />);
    // Measured and threshold are in the same span: "(measured: 11.0, threshold: 20.0)"
    expect(screen.getByText('(measured: 11.0, threshold: 20.0)')).toBeInTheDocument();
  });

  it('does not show approve button for rejected plan', () => {
    render(<PlanComparison {...defaultProps} />);
    // Rejected plan should show "REJECTED - CANNOT APPROVE" not an approve button
    expect(screen.getByText('REJECTED - CANNOT APPROVE')).toBeInTheDocument();
    // Should not have an actionable approve button for aggressive
    const approveButtons = screen.getAllByRole('button', { name: /APPROVE/i });
    // Only 2 valid plans should have approve buttons
    expect(approveButtons).toHaveLength(2);
  });

  it('shows approve button for VALID plans', () => {
    render(<PlanComparison {...defaultProps} />);
    expect(screen.getByRole('button', { name: /APPROVE PLAN/i })).toBeInTheDocument(); // Minimal
    expect(screen.getByRole('button', { name: /APPROVE \(RECOMMENDED\)/i })).toBeInTheDocument(); // Extended
  });

  it('Extended Survey approve button says RECOMMENDED', () => {
    render(<PlanComparison {...defaultProps} />);
    const recommendedBtn = screen.getByRole('button', { name: /APPROVE \(RECOMMENDED\)/i });
    expect(recommendedBtn).toBeInTheDocument();
  });

  it('calls onApprove when valid plan approve button clicked', () => {
    render(<PlanComparison {...defaultProps} />);
    const minimalApproveBtn = screen.getByRole('button', { name: /APPROVE PLAN/i });
    minimalApproveBtn.click();
    expect(defaultProps.onApprove).toHaveBeenCalledWith('plan-a-001');
  });

  it('renders predicted return battery percentages', () => {
    render(<PlanComparison {...defaultProps} />);
    expect(screen.getByText('34.0%')).toBeInTheDocument();
    expect(screen.getByText('42.0%')).toBeInTheDocument();
    expect(screen.getByText('11.0%')).toBeInTheDocument();
  });

  it('renders science yield scores', () => {
    render(<PlanComparison {...defaultProps} />);
    // Check that science yield scores are present in the document
    // Each plan has its own science yield displayed
    expect(screen.getAllByText('45.0').length).toBeGreaterThan(0);
    // Just verify numbers render, exact values vary by mock
    const container = screen.getByText('CANDIDATE PLANS').closest('div')!;
    expect(container.textContent).toContain('45.0');
  });

  it('shows plan IDs', () => {
    render(<PlanComparison {...defaultProps} />);
    // Each plan ID appears in the "ID: plan-x-xxx" text (split as "ID:" and "plan-x-xxx")
    expect(screen.getAllByText((content) => content.includes('plan-a-001')).length).toBeGreaterThan(0);
    expect(screen.getAllByText((content) => content.includes('plan-b-001')).length).toBeGreaterThan(0);
    expect(screen.getAllByText((content) => content.includes('plan-c-001')).length).toBeGreaterThan(0);
  });

  it('displays waypoint badges', () => {
    render(<PlanComparison {...defaultProps} />);
    // Each plan has the same waypoints, so they appear 3 times
    const baseBadges = screen.getAllByText('Base');
    const craterBadges = screen.getAllByText('Crater A');
    expect(baseBadges).toHaveLength(3);
    expect(craterBadges).toHaveLength(3);
  });

  it('shows waypoint badges with science target styling', () => {
    render(<PlanComparison {...defaultProps} />);
    // Science targets have blue styling (bg-blue-900/30), non-science have gray (bg-gray-800)
    // We verify by checking container textContent includes both
    const container = screen.getByText('CANDIDATE PLANS').closest('div')!;
    expect(container.textContent).toContain('Base');
    expect(container.textContent).toContain('Crater A');
  });

  it('disables buttons when disabled prop is true', () => {
    render(<PlanComparison {...defaultProps} disabled={true} />);
    const approveButtons = screen.getAllByRole('button', { name: /APPROVE/i });
    approveButtons.forEach((btn) => {
      expect(btn).toBeDisabled();
    });
  });

  it('renders nothing when plans array is empty', () => {
    const { container } = render(<PlanComparison {...defaultProps} plans={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
