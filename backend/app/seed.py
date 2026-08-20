"""
LunaYield Mission Lab — deterministic scenario seed.

get_seed_mission() always returns the same Mission value.  It is the
single source of truth for the Phase 1 demo scenario and the reset target.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.schemas import (
    AuditEvent,
    Mission,
    MissionStatus,
    RouteWaypoint,
    RoverResources,
)
from app.services.route_progress import build_initialized_route

# ---------------------------------------------------------------------------
# Fixed identifiers
# ---------------------------------------------------------------------------

MISSION_ID = "luna-mission-001"
MISSION_LABEL = "Shackleton Rim Survey — Alpha"

# ---------------------------------------------------------------------------
# Seed waypoints
# ---------------------------------------------------------------------------

_ORIGINAL_WAYPOINTS: list[RouteWaypoint] = [
    RouteWaypoint(
        id="wp-base", x=0.1, y=0.1, label="Base Camp", is_science_target=False
    ),
    RouteWaypoint(
        id="wp-crater-a", x=0.3, y=0.4, label="Crater A Rim", is_science_target=True
    ),
    RouteWaypoint(
        id="wp-ice-deposit",
        x=0.5,
        y=0.6,
        label="Ice Deposit Site",
        is_science_target=True,
    ),
    RouteWaypoint(
        id="wp-ridge",
        x=0.7,
        y=0.5,
        label="Ridge Observation Point",
        is_science_target=True,
    ),
    RouteWaypoint(
        id="wp-return",
        x=0.1,
        y=0.1,
        label="Base Camp (Return)",
        is_science_target=False,
    ),
]

# ---------------------------------------------------------------------------
# Seed resources
# ---------------------------------------------------------------------------

_SEED_RESOURCES = RoverResources(
    battery_pct=100.0,
    storage_pct=0.0,
    temperature_c=-40.0,
    comm_window_remaining_s=7200,
    op_time_remaining_s=28800,
)

# ---------------------------------------------------------------------------
# Seed audit entry
# ---------------------------------------------------------------------------

_SEED_AUDIT_EVENT = AuditEvent(
    event_id="audit-seed-001",
    event_type="mission.initialized",
    description="Mission scenario loaded from seed data.",
    timestamp=datetime(2026, 8, 6, 0, 0, 0, tzinfo=UTC),
    metadata={"mission_id": MISSION_ID},
)


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def get_seed_mission() -> Mission:
    """Return a fresh, deterministic Mission in IDLE state.

    Calling this function multiple times always produces structurally
    identical objects (same IDs, values, and timestamps).
    """
    route = build_initialized_route(_ORIGINAL_WAYPOINTS)
    # Create a fresh audit trail list each time
    seed_audit = AuditEvent(
        event_id="audit-seed-001",
        event_type="mission.initialized",
        description="Mission scenario loaded from seed data.",
        timestamp=datetime(2026, 8, 6, 0, 0, 0, tzinfo=UTC),
        metadata={"mission_id": MISSION_ID},
    )
    return Mission(
        mission_id=MISSION_ID,
        label=MISSION_LABEL,
        status=MissionStatus.IDLE,
        elapsed_s=0,
        resources=_SEED_RESOURCES.model_copy(),
        original_route=route.model_copy(deep=True),
        active_route=route.model_copy(deep=True),
        candidate_plans=[],
        anomaly_active=False,
        audit_trail=[seed_audit],
    )
