"""Mission service — authoritative in-memory Mission state."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.schemas import (
    AuditEvent,
    Mission,
    MissionRoute,
    MissionStatus,
    PlanStatus,
    WaypointProgressStatus,
)
from app.seed import get_seed_mission
from app.services.exceptions import (
    MissionStateError,
    PlanningNotAllowedError,
    PlanNotFoundError,
    PlanUnsafeError,
)
from app.services.route_progress import (
    ANOMALY_IMMEDIATE_BATTERY_LOSS_PCT,
    clone_waypoints,
    next_upcoming_index,
)

if TYPE_CHECKING:
    from app.services.planning import PlanningService
    from app.services.safety import SafetyVerifier


class MissionService:
    """Owns the authoritative Mission state and valid state transitions."""

    def __init__(self) -> None:
        self._mission: Mission | None = None
        self._safety_verifier: SafetyVerifier | None = None
        self._planning_service: PlanningService | None = None

    @classmethod
    def restore_from_snapshot(
        cls, snapshot_data: dict, audit_events: list, seed_mission: Mission
    ) -> Mission:
        """Restore a Mission domain model from persisted snapshot and audit events."""
        import json

        from app.schemas import RoverResources

        resources_dict = json.loads(snapshot_data["resources_json"])
        active_route_dict = json.loads(snapshot_data["active_route_json"])

        resources = RoverResources(**resources_dict)
        active_route = MissionRoute(**active_route_dict)

        status = snapshot_data["status"]
        normalized_status = status
        if status == MissionStatus.AWAITING_APPROVAL.value:
            normalized_status = MissionStatus.ANOMALY.value

        restored = Mission(
            mission_id=seed_mission.mission_id,
            label=seed_mission.label,
            status=normalized_status,
            elapsed_s=snapshot_data["elapsed_s"],
            resources=resources,
            original_route=seed_mission.original_route,
            active_route=active_route,
            candidate_plans=[],
            anomaly_active=snapshot_data["anomaly_active"],
            audit_trail=audit_events,
        )

        return restored

    def set_dependencies(
        self,
        safety_verifier: SafetyVerifier,
        planning_service: PlanningService,
    ) -> None:
        """Inject dependencies after construction to avoid circular imports."""
        self._safety_verifier = safety_verifier
        self._planning_service = planning_service

    def get_mission(self) -> Mission:
        """Return the current mission, initializing from seed if needed."""
        if self._mission is None:
            self._mission = get_seed_mission()
        return self._mission

    def restore(self, mission: Mission) -> Mission:
        """Restore mission state from a previously persisted Mission."""
        self._mission = mission
        return self._mission

    def _create_audit_event(
        self,
        event_type: str,
        description: str,
        metadata: dict | None = None,
    ) -> AuditEvent:
        """Create a deterministic audit event."""
        mission = self.get_mission()
        return AuditEvent(
            event_id=f"audit-{uuid.uuid4().hex[:8]}",
            event_type=event_type,
            description=description,
            timestamp=datetime.now(UTC),
            metadata={"mission_id": mission.mission_id, **(metadata or {})},
        )

    def _append_audit(self, event: AuditEvent) -> None:
        """Append audit event to mission."""
        mission = self.get_mission()
        mission.audit_trail.append(event)

    def record_event(
        self,
        event_type: str,
        description: str,
        metadata: dict | None = None,
    ) -> AuditEvent:
        """Public helper for appending a significant mission audit event."""
        event = self._create_audit_event(event_type, description, metadata)
        self._append_audit(event)
        return event

    def _prime_route_for_launch(self, mission: Mission) -> None:
        """Mark the launch point complete and the next waypoint active."""
        if not mission.active_route.waypoints:
            return

        first_waypoint = mission.active_route.waypoints[0]
        if (
            first_waypoint.id == "wp-base"
            and first_waypoint.progress_status == WaypointProgressStatus.CURRENT
        ):
            first_waypoint.progress_status = WaypointProgressStatus.COMPLETED
            next_index = next_upcoming_index(mission.active_route, after_index=0)
            if next_index is not None:
                mission.active_route.waypoints[
                    next_index
                ].progress_status = WaypointProgressStatus.CURRENT

    def complete_mission(self) -> Mission:
        """Transition the mission to its terminal completed state."""
        mission = self.get_mission()
        mission.status = MissionStatus.COMPLETED
        mission.anomaly_active = False
        self.record_event(
            "mission.completed",
            "Mission completed and rover returned to Base Camp",
            {"elapsed_s": mission.elapsed_s},
        )
        return mission

    def trigger_resource_anomaly(
        self,
        *,
        resource: str,
        description: str,
        observed_value: float,
        threshold_value: float,
    ) -> Mission:
        """Use the existing anomaly state for unexpected critical resource issues."""
        mission = self.get_mission()
        if mission.status not in (MissionStatus.RUNNING, MissionStatus.EXECUTING):
            return mission

        mission.status = MissionStatus.ANOMALY
        mission.anomaly_active = True
        self.record_event(
            "anomaly.detected",
            description,
            {
                "resource": resource,
                "observed_value": round(observed_value, 1),
                "threshold_value": threshold_value,
            },
        )
        return mission

    def start(self) -> Mission:
        """Transition mission from IDLE to RUNNING."""
        mission = self.get_mission()
        if mission.status != MissionStatus.IDLE:
            raise MissionStateError(mission.status.value, "start")
        mission.status = MissionStatus.RUNNING
        self._prime_route_for_launch(mission)
        self.record_event("mission.started", "Mission started by operator")
        return mission

    def pause(self) -> Mission:
        """Transition mission from RUNNING to PAUSED."""
        mission = self.get_mission()
        if mission.status != MissionStatus.RUNNING:
            raise MissionStateError(mission.status.value, "pause")
        mission.status = MissionStatus.PAUSED
        self.record_event("mission.paused", "Mission paused by operator")
        return mission

    def resume(self) -> Mission:
        """Transition mission from PAUSED to RUNNING."""
        mission = self.get_mission()
        if mission.status != MissionStatus.PAUSED:
            raise MissionStateError(mission.status.value, "resume")
        mission.status = MissionStatus.RUNNING
        self.record_event("mission.resumed", "Mission resumed by operator")
        return mission

    def inject_anomaly(self) -> Mission:
        """Transition mission from RUNNING to ANOMALY."""
        mission = self.get_mission()
        if mission.status != MissionStatus.RUNNING:
            raise MissionStateError(mission.status.value, "inject anomaly")

        battery_before = mission.resources.battery_pct
        battery_after = max(
            0.0,
            round(
                battery_before - ANOMALY_IMMEDIATE_BATTERY_LOSS_PCT,
                1,
            ),
        )
        mission.resources.battery_pct = battery_after
        mission.status = MissionStatus.ANOMALY
        mission.anomaly_active = True
        self.record_event(
            "anomaly.injected",
            "Battery anomaly injected",
            {
                "battery_before_pct": battery_before,
                "battery_after_pct": battery_after,
            },
        )
        self.record_event(
            "battery.degraded",
            "Battery system degraded after anomaly injection",
            {
                "battery_before_pct": battery_before,
                "battery_after_pct": battery_after,
                "battery_loss_pct": ANOMALY_IMMEDIATE_BATTERY_LOSS_PCT,
            },
        )
        return mission

    def reset(self) -> Mission:
        """Reset mission to deterministic seed state."""
        seed_mission = get_seed_mission()

        reset_event = self._create_audit_event(
            "mission.reset", "Mission reset to seed state"
        )

        self._mission = seed_mission
        self._mission.audit_trail.append(reset_event)
        return self._mission

    def generate_plans(self) -> Mission:
        """Generate candidate plans from ANOMALY state."""
        mission = self.get_mission()
        if mission.status != MissionStatus.ANOMALY:
            raise PlanningNotAllowedError(mission.status.value)

        mission.status = MissionStatus.PLANNING
        self.record_event(
            "planning.started",
            "Candidate plan generation initiated",
        )

        if self._planning_service is None:
            raise RuntimeError("PlanningService not injected")

        candidate_plans = self._planning_service.generate_candidate_plans(mission)
        mission.candidate_plans = candidate_plans

        if self._safety_verifier is None:
            raise RuntimeError("SafetyVerifier not injected")

        for plan in mission.candidate_plans:
            violations = self._safety_verifier.verify(plan)
            plan.violations = violations
            plan.status = PlanStatus.REJECTED if violations else PlanStatus.VALID

        for plan in mission.candidate_plans:
            if plan.label == "Extended Survey" and plan.status == PlanStatus.VALID:
                plan.is_recommended = True
                plan.rank = 1
            elif plan.status == PlanStatus.VALID:
                plan.is_recommended = False
                plan.rank = 2

        mission.status = MissionStatus.AWAITING_APPROVAL
        self.record_event(
            "plans.generated",
            f"Generated {len(candidate_plans)} candidate plans",
            {"plan_count": len(candidate_plans)},
        )

        return mission

    def approve_plan(self, plan_id: str) -> Mission:
        """Approve a candidate plan and transition to EXECUTING."""
        mission = self.get_mission()
        if mission.status != MissionStatus.AWAITING_APPROVAL:
            raise MissionStateError(mission.status.value, "approve plan")

        plan = next((p for p in mission.candidate_plans if p.plan_id == plan_id), None)
        if plan is None:
            raise PlanNotFoundError(plan_id)

        if self._safety_verifier is None:
            raise RuntimeError("SafetyVerifier not injected")

        violations = self._safety_verifier.verify(plan)
        if violations:
            raise PlanUnsafeError(plan_id, [v.description for v in violations])

        if plan.status == PlanStatus.REJECTED:
            raise PlanUnsafeError(
                plan_id, ["Plan was previously rejected by safety verification"]
            )

        plan.status = PlanStatus.APPROVED
        mission.active_route = MissionRoute(waypoints=clone_waypoints(plan.waypoints))
        mission.status = MissionStatus.EXECUTING
        mission.anomaly_active = False

        self.record_event(
            "plan.approved",
            f"Plan {plan.label} ({plan_id}) approved and activated",
            {"approved_plan_id": plan_id, "plan_label": plan.label},
        )
        self.record_event(
            "route.updated",
            f"Active route updated to {plan.label}",
            {
                "approved_plan_id": plan_id,
                "waypoint_count": len(mission.active_route.waypoints),
            },
        )

        return mission
