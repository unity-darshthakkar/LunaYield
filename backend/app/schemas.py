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
