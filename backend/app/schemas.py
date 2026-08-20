"""
LunaYield Mission Lab — Pydantic domain schemas.

All public API boundaries use these models.  Every model that represents
a resource percentage enforces the 0–100 range via field validators.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class MissionStatus(StrEnum):
    """Lifecycle states of a mission."""

    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    ANOMALY = "ANOMALY"
    PLANNING = "PLANNING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    RESET = "RESET"


class PlanStatus(StrEnum):
    """Validity status of a candidate plan.

    APPROVED lives here (on CandidatePlan), not on MissionStatus.
    """

    VALID = "VALID"
    REJECTED = "REJECTED"
    APPROVED = "APPROVED"


class WaypointProgressStatus(StrEnum):
    """Backend-authoritative progress state for a route waypoint."""

    COMPLETED = "COMPLETED"
    CURRENT = "CURRENT"
    UPCOMING = "UPCOMING"
    SKIPPED = "SKIPPED"


# ---------------------------------------------------------------------------
# Resource models
# ---------------------------------------------------------------------------


class RoverResources(BaseModel):
    """Point-in-time snapshot of rover resource levels."""

    battery_pct: float = Field(..., description="Battery level 0–100 %")
    storage_pct: float = Field(..., description="Storage used 0–100 %")
    temperature_c: float = Field(..., description="Internal temperature in °C")
    comm_window_remaining_s: int = Field(
        ..., ge=0, description="Seconds remaining in current comms window"
    )
    op_time_remaining_s: int = Field(
        ..., ge=0, description="Seconds of operational time remaining"
    )

    @field_validator("battery_pct", "storage_pct")
    @classmethod
    def pct_range(cls, v: float) -> float:
        if not (0.0 <= v <= 100.0):
            raise ValueError(f"Percentage value {v!r} must be between 0 and 100")
        return v


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------


class TelemetrySample(BaseModel):
    """A single telemetry reading emitted by the rover simulation."""

    mission_id: str
    elapsed_s: int = Field(..., ge=0)
    resources: RoverResources
    timestamp: datetime


# ---------------------------------------------------------------------------
# Route models
# ---------------------------------------------------------------------------


class RouteWaypoint(BaseModel):
    """A single waypoint on a mission route."""

    id: str
    x: float = Field(..., ge=0.0, le=1.0, description="Normalised x position 0–1")
    y: float = Field(..., ge=0.0, le=1.0, description="Normalised y position 0–1")
    label: str
    is_science_target: bool = False
    progress_status: WaypointProgressStatus = WaypointProgressStatus.UPCOMING
    segment_elapsed_s: int = Field(
        default=0, ge=0, description="Elapsed segment time for this waypoint"
    )
    science_collected: bool = False


class MissionRoute(BaseModel):
    """An ordered sequence of waypoints forming a traversal path."""

    waypoints: list[RouteWaypoint]


# ---------------------------------------------------------------------------
# Safety / planning models
# ---------------------------------------------------------------------------


class ConstraintViolation(BaseModel):
    """A deterministic safety-rule violation attached to a rejected plan."""

    rule_id: str
    description: str
    measured_value: float
    threshold_value: float


class CandidatePlan(BaseModel):
    """One candidate mission plan produced by the planning service."""

    plan_id: str
    label: str
    description: str
    waypoints: list[RouteWaypoint]
    science_yield_score: float = Field(..., ge=0.0)
    predicted_return_battery_pct: float = Field(
        ..., description="Predicted battery % at mission return"
    )
    status: PlanStatus = PlanStatus.VALID
    violations: list[ConstraintViolation] = Field(default_factory=list)
    is_recommended: bool = False
    rank: int | None = None

    @field_validator("predicted_return_battery_pct")
    @classmethod
    def battery_range(cls, v: float) -> float:
        if not (0.0 <= v <= 100.0):
            raise ValueError(
                f"predicted_return_battery_pct {v!r} must be between 0 and 100"
            )
        return v


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


class AuditEvent(BaseModel):
    """An immutable record of a significant mission transition."""

    event_id: str
    event_type: str
    description: str
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Mission
# ---------------------------------------------------------------------------


class Mission(BaseModel):
    """Full mission state — the authoritative representation held by the backend."""

    mission_id: str
    label: str
    status: MissionStatus = MissionStatus.IDLE
    elapsed_s: int = Field(default=0, ge=0)
    resources: RoverResources
    original_route: MissionRoute
    active_route: MissionRoute
    candidate_plans: list[CandidatePlan] = Field(default_factory=list)
    anomaly_active: bool = False
    audit_trail: list[AuditEvent] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Plan approval result
# ---------------------------------------------------------------------------


class PlanApprovalResult(BaseModel):
    """Returned by the approval endpoint on success."""

    approved_plan_id: str
    updated_route: MissionRoute
    audit_event: AuditEvent
    mission_status: MissionStatus


# ---------------------------------------------------------------------------
# Forecasting schemas (Phase 3A)
# ---------------------------------------------------------------------------


class ResourceForecast(BaseModel):
    """Forecast of resource levels at a future point in time."""

    battery_pct: float = Field(
        ..., description="Forecasted battery level 0–100 %", ge=0.0, le=100.0
    )
    storage_pct: float = Field(
        ..., description="Forecasted storage used 0–100 %", ge=0.0, le=100.0
    )
    temperature_c: float = Field(
        ..., description="Forecasted internal temperature in °C"
    )
    comm_window_remaining_s: int = Field(
        ..., description="Forecasted seconds remaining in current comms window", ge=0
    )
    op_time_remaining_s: int = Field(
        ..., description="Forecasted seconds of operational time remaining", ge=0
    )


class ForecastPoint(BaseModel):
    """A single point in the forecast timeline."""

    forecast_seconds_ahead: int = Field(
        ..., description="Seconds ahead from current time for this forecast", ge=0
    )
    elapsed_s: int = Field(
        ..., description="Mission elapsed time at this forecast point", ge=0
    )
    resources: ResourceForecast


class MissionForecastResponse(BaseModel):
    """Response for mission resource forecast."""

    mission_id: str = Field(..., description="Mission identifier")
    current_elapsed_s: int = Field(
        ..., description="Current mission elapsed time in seconds", ge=0
    )
    current_resources: RoverResources = Field(
        ..., description="Current mission resource levels"
    )
    forecast_horizon_s: int = Field(
        ..., description="Forecast horizon in seconds", ge=0
    )
    forecast_tick_interval_s: int = Field(
        ..., description="Seconds per forecast tick", ge=1
    )
    forecast_points: list[ForecastPoint] = Field(
        ..., description="Array of forecast points from t+interval to t+horizon"
    )


# ---------------------------------------------------------------------------
# Anomaly Detection schemas (Phase 3B)
# ---------------------------------------------------------------------------


class AnomalySeverity(StrEnum):
    """Severity levels for anomaly findings."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AnomalyResource(StrEnum):
    """Resource types that can have anomalies."""

    BATTERY = "BATTERY"
    STORAGE = "STORAGE"
    TEMPERATURE = "TEMPERATURE"
    COMM_WINDOW = "COMM_WINDOW"
    OP_TIME = "OP_TIME"


class AnomalyFinding(BaseModel):
    """A single anomaly finding with resource, severity, observed/forecasted value,
    threshold, and reason."""

    resource: AnomalyResource = Field(
        ..., description="The resource type that has an anomaly"
    )
    severity: AnomalySeverity = Field(..., description="Severity level of the anomaly")
    observed_value: float | int = Field(
        ..., description="The observed or forecasted value that crossed the threshold"
    )
    threshold_value: float | int = Field(
        ..., description="The threshold that was crossed"
    )
    reason: str = Field(..., description="Human-readable reason for the anomaly")
    is_forecast: bool = Field(
        False, description="Whether this finding is from a forecast"
    )
    forecast_seconds_ahead: int | None = Field(
        None, description="Seconds ahead for forecast findings", ge=0
    )


class AnomalyDetectionResponse(BaseModel):
    """Response for anomaly detection endpoint."""

    mission_id: str = Field(..., description="Mission identifier")
    current_elapsed_s: int = Field(
        ..., description="Current mission elapsed time in seconds", ge=0
    )
    anomalies: list[AnomalyFinding] = Field(
        default_factory=list, description="List of detected anomalies"
    )
    anomaly_count: int = Field(
        ..., description="Total number of anomalies detected", ge=0
    )
    has_critical: bool = Field(
        ..., description="Whether any critical anomalies were detected"
    )
    has_warning: bool = Field(
        ..., description="Whether any warning anomalies were detected"
    )


# ---------------------------------------------------------------------------
# Strategy Generation schemas (Phase 4A)
# ---------------------------------------------------------------------------


class StrategyCandidate(BaseModel):
    """A single strategy candidate for operator review.

    Generated from current mission state, forecast, and anomaly findings.
    Read-only recommendation — does not mutate mission state.
    """

    strategy_id: str = Field(..., description="Unique strategy identifier")
    title: str = Field(..., description="Human-readable strategy title")
    rationale: str = Field(..., description="Why this strategy is proposed")
    priority: int = Field(..., ge=1, le=5, description="Priority 1=highest, 5=lowest")
    affected_resources: list[AnomalyResource] = Field(
        default_factory=list, description="Resources this strategy addresses"
    )
    recommended_actions: list[str] = Field(
        default_factory=list, description="Concrete actionable steps"
    )
    source_anomalies: list[str] = Field(
        default_factory=list,
        description="Anomaly identifiers that triggered this strategy",
    )
    requires_operator_approval: bool = Field(
        True,
        description="Whether operator approval is required (always true for Phase 4A)",
    )


class StrategyGenerationResponse(BaseModel):
    """Response for strategy generation endpoint."""

    mission_id: str = Field(..., description="Mission identifier")
    current_elapsed_s: int = Field(
        ..., description="Current mission elapsed time in seconds", ge=0
    )
    strategies: list[StrategyCandidate] = Field(
        default_factory=list, description="Generated strategy candidates"
    )
    strategy_count: int = Field(
        ..., description="Total number of strategies generated", ge=0
    )
    has_critical_priority: bool = Field(
        ..., description="Whether any priority-1 strategies were generated"
    )


# ---------------------------------------------------------------------------
# Strategy Validation schemas (Phase 4B)
# ---------------------------------------------------------------------------


class StrategyValidationResult(BaseModel):
    """Validation result for a single strategy candidate."""

    strategy_id: str = Field(..., description="Strategy identifier")
    is_valid: bool = Field(..., description="Whether the strategy passed validation")
    rejection_reasons: list[str] = Field(
        default_factory=list, description="Reasons for rejection (empty if valid)"
    )


class StrategyValidationResponse(BaseModel):
    """Response for strategy validation endpoint."""

    mission_id: str = Field(..., description="Mission identifier")
    current_elapsed_s: int = Field(
        ..., description="Current mission elapsed time in seconds", ge=0
    )
    validation_results: list[StrategyValidationResult] = Field(
        default_factory=list, description="Validation results per strategy"
    )
    validation_count: int = Field(
        ..., description="Total number of strategies validated", ge=0
    )
    all_valid: bool = Field(..., description="Whether all strategies passed validation")


# ---------------------------------------------------------------------------
# Strategy Approval schemas (Phase 4C)
# ---------------------------------------------------------------------------


class StrategyApprovalStatus(StrEnum):
    """Approval status for a strategy candidate."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    NOT_FOUND = "NOT_FOUND"
    ALREADY_APPROVED = "ALREADY_APPROVED"


class StrategyApprovalResult(BaseModel):
    """Result of a strategy approval request."""

    strategy_id: str = Field(..., description="Strategy identifier")
    approved: bool = Field(..., description="Whether the strategy was approved")
    approval_status: StrategyApprovalStatus = Field(
        ..., description="Detailed approval status"
    )
    rejection_reasons: list[str] = Field(
        default_factory=list, description="Reasons if rejected or validation failed"
    )


# ---------------------------------------------------------------------------
# History API response schemas (Phase 2B)
# ---------------------------------------------------------------------------


class MissionRunHistoryItem(BaseModel):
    """Minimal mission run representation for history API."""

    run_id: str
    mission_id: str
    label: str
    seed_mission_id: str
    started_at: datetime
    ended_at: datetime | None = None
    final_status: str | None = None


class MissionRunListResponse(BaseModel):
    """Response for listing mission runs."""

    mission_id: str
    runs: list[MissionRunHistoryItem]
    limit: int


class MissionRunDetailResponse(BaseModel):
    """Response for getting a single mission run."""

    run_id: str
    mission_id: str
    label: str
    seed_mission_id: str
    started_at: datetime
    ended_at: datetime | None = None
    final_status: str | None = None


class MissionSnapshotHistoryItem(BaseModel):
    """Minimal mission snapshot representation for history API."""

    snapshot_id: str
    sequence: int
    status: str
    elapsed_s: int
    created_at: datetime
    battery_pct: float | None = None
    temperature_c: float | None = None
    storage_pct: float | None = None
    anomaly_active: bool


class MissionSnapshotListResponse(BaseModel):
    """Response for listing mission snapshots."""

    run_id: str
    snapshots: list[MissionSnapshotHistoryItem]
    limit: int
    offset: int
    total_snapshots_available: int


class AuditEventHistoryItem(BaseModel):
    """Minimal audit event representation for history API."""

    audit_id: str
    event_type: str
    description: str
    timestamp: datetime
    sequence: int


class AuditEventListResponse(BaseModel):
    """Response for listing audit events."""

    run_id: str
    audit_events: list[AuditEventHistoryItem]
    limit: int
    offset: int
    total_audit_events_available: int
