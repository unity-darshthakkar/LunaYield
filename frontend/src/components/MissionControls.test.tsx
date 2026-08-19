/** MissionControls component tests */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MissionControls } from '../components/MissionControls';
import type { MissionStatus } from '../types/mission';

const defaultProps = {
  missionStatus: 'IDLE' as MissionStatus,
  anomalyActive: false,
  candidatePlansCount: 0,
  onStart: vi.fn(),
  onPause: vi.fn(),
  onResume: vi.fn(),
  onInjectAnomaly: vi.fn(),
  onGeneratePlans: vi.fn(),
  onReset: vi.fn(),
};

describe('MissionControls', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Start Mission button enabled in IDLE', () => {
    render(<MissionControls {...defaultProps} missionStatus="IDLE" />);
    const startBtn = screen.getByRole('button', { name: /START MISSION/i });
    expect(startBtn).not.toBeDisabled();
  });

  it('renders Start Mission button disabled in RUNNING', () => {
    render(<MissionControls {...defaultProps} missionStatus="RUNNING" />);
    const startBtn = screen.getByRole('button', { name: /START MISSION/i });
    expect(startBtn).toBeDisabled();
  });

  it('renders Pause button enabled in RUNNING', () => {
    render(<MissionControls {...defaultProps} missionStatus="RUNNING" />);
    const pauseBtn = screen.getByRole('button', { name: /PAUSE/i });
    expect(pauseBtn).not.toBeDisabled();
  });

  it('renders Pause button disabled in IDLE', () => {
    render(<MissionControls {...defaultProps} missionStatus="IDLE" />);
    const pauseBtn = screen.getByRole('button', { name: /PAUSE/i });
    expect(pauseBtn).toBeDisabled();
  });

  it('renders Resume button enabled in PAUSED', () => {
    render(<MissionControls {...defaultProps} missionStatus="PAUSED" />);
    const resumeBtn = screen.getByRole('button', { name: /RESUME/i });
    expect(resumeBtn).not.toBeDisabled();
  });

  it('renders Resume button disabled in RUNNING', () => {
    render(<MissionControls {...defaultProps} missionStatus="RUNNING" />);
    const resumeBtn = screen.getByRole('button', { name: /RESUME/i });
    expect(resumeBtn).toBeDisabled();
  });

  it('renders Inject Anomaly button enabled in RUNNING', () => {
    render(<MissionControls {...defaultProps} missionStatus="RUNNING" />);
    const anomalyBtn = screen.getByRole('button', { name: /INJECT ANOMALY/i });
    expect(anomalyBtn).not.toBeDisabled();
  });

  it('renders Inject Anomaly button disabled in PAUSED', () => {
    render(<MissionControls {...defaultProps} missionStatus="PAUSED" />);
    const anomalyBtn = screen.getByRole('button', { name: /INJECT ANOMALY/i });
    expect(anomalyBtn).toBeDisabled();
  });

  it('renders Generate Plans button enabled in ANOMALY', () => {
    render(
      <MissionControls {...defaultProps} missionStatus="ANOMALY" anomalyActive={true} />
    );
    const generateBtn = screen.getByRole('button', { name: /GENERATE PLANS/i });
    expect(generateBtn).not.toBeDisabled();
  });

  it('renders Generate Plans button disabled in RUNNING', () => {
    render(<MissionControls {...defaultProps} missionStatus="RUNNING" />);
    const generateBtn = screen.getByRole('button', { name: /GENERATE PLANS/i });
    expect(generateBtn).toBeDisabled();
  });

  it('calls onStart when Start button clicked', () => {
    render(<MissionControls {...defaultProps} missionStatus="IDLE" />);
    const startBtn = screen.getByRole('button', { name: /START MISSION/i });
    fireEvent.click(startBtn);
    expect(defaultProps.onStart).toHaveBeenCalledTimes(1);
  });

  it('calls onPause when Pause button clicked', () => {
    render(<MissionControls {...defaultProps} missionStatus="RUNNING" />);
    const pauseBtn = screen.getByRole('button', { name: /PAUSE/i });
    fireEvent.click(pauseBtn);
    expect(defaultProps.onPause).toHaveBeenCalledTimes(1);
  });

  it('shows anomaly warning when anomalyActive is true in ANOMALY state', () => {
    render(
      <MissionControls {...defaultProps} missionStatus="ANOMALY" anomalyActive={true} />
    );
    expect(screen.getByText(/BATTERY ANOMALY ACTIVE/i)).toBeInTheDocument();
    expect(screen.getByText(/Generate recovery plans/i)).toBeInTheDocument();
  });

  it('shows candidate plans count when in AWAITING_APPROVAL with plans', () => {
    render(
      <MissionControls
        {...defaultProps}
        missionStatus="AWAITING_APPROVAL"
        candidatePlansCount={3}
      />
    );
    expect(screen.getByText(/3 CANDIDATE PLAN\(S\) AVAILABLE/i)).toBeInTheDocument();
    expect(screen.getByText(/Review and approve/i)).toBeInTheDocument();
  });

  it('AWAITING_APPROVAL disables all controls except reset', () => {
    render(
      <MissionControls
        {...defaultProps}
        missionStatus="AWAITING_APPROVAL"
        anomalyActive={true}
        candidatePlansCount={3}
        approvedPlanLabel="Extended Survey"
      />
    );

    expect(screen.getByRole('button', { name: /START MISSION/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /PAUSE/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /RESUME/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /INJECT ANOMALY/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /PLAN SELECTED: EXTENDED SURVEY/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /RESET MISSION/i })).not.toBeDisabled();
  });

  it('AWAITING_APPROVAL does not show Generate recovery plans banner', () => {
    render(
      <MissionControls
        {...defaultProps}
        missionStatus="AWAITING_APPROVAL"
        anomalyActive={true}
        candidatePlansCount={3}
      />
    );
    expect(screen.queryByText(/Generate recovery plans/i)).not.toBeInTheDocument();
  });

  it('EXECUTING with anomalyActive shows Recovery plan executing and hides stale banners', () => {
    render(
      <MissionControls
        {...defaultProps}
        missionStatus="EXECUTING"
        anomalyActive={true}
        candidatePlansCount={3}
      />
    );
    expect(screen.getByText(/Recovery plan executing/i)).toBeInTheDocument();
    expect(screen.queryByText(/Generate recovery plans/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Review and approve/i)).not.toBeInTheDocument();
  });

  it('EXECUTING without anomalyActive does not claim Battery Anomaly Active', () => {
    render(
      <MissionControls
        {...defaultProps}
        missionStatus="EXECUTING"
        anomalyActive={false}
      />
    );
    expect(screen.queryByText(/BATTERY ANOMALY ACTIVE/i)).not.toBeInTheDocument();
  });

  it('displays error message when provided', () => {
    render(
      <MissionControls
        {...defaultProps}
        missionStatus="RUNNING"
        startError="Cannot start from RUNNING status"
      />
    );
    expect(screen.getByText(/START: Cannot start from RUNNING status/i)).toBeInTheDocument();
  });

  it('Reset button is available in all states', () => {
    const statuses: MissionStatus[] = ['IDLE', 'RUNNING', 'PAUSED', 'ANOMALY', 'AWAITING_APPROVAL', 'EXECUTING'];
    statuses.forEach((status) => {
      const { unmount } = render(<MissionControls {...defaultProps} missionStatus={status} />);
      const resetBtn = screen.getByRole('button', { name: /RESET MISSION/i });
      expect(resetBtn).not.toBeDisabled();
      unmount();
    });
  });
});
