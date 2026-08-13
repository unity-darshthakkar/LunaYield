"""Mission service — authoritative in-memory Mission state."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.schemas import (
    AuditEvent,
    Mission,
    MissionStatus,
    PlanStatus,
)
from app.seed import get_seed_mission
from app.services.exceptions import (
    MissionStateError,
    PlanningNotAllowedError,
    PlanNotFoundError,
    PlanUnsafeError,
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
        """Restore a Mission domain model from persisted snapshot and audit events.

        This is a pure reconstruction function — no side effects, no dependencies.
        Used at startup to rebuild Mission state from durable storage.

        Args:
            snapshot_data: Dictionary with snapshot fields (status, elapsed_s,
                resources_json, active_route_json, anomaly_active)
            audit_events: List of AuditEventRecords (already parsed to domain
                AuditEvent)
            seed_mission: The deterministic seed mission providing structural baseline
                (mission_id, label, original_route, etc.)

        Returns:
            Reconstructed Mission object ready for MissionService.
        """
        import json

        from app.schemas import MissionRoute, RoverResources

        # Parse persisted JSON fields
        resources_dict = json.loads(snapshot_data["resources_json"])
        active_route_dict = json.loads(snapshot_data["active_route_json"])

        resources = RoverResources(**resources_dict)
        active_route = MissionRoute(**active_route_dict)

        # Determine status from snapshot
        status = snapshot_data["status"]

        # State normalization: ensure restored state is internally consistent
        # If snapshot has AWAITING_APPROVAL but no candidate plans were persisted,
        # normalize to ANOMALY (since candidate plans are not persisted)
        normalized_status = status
        if status == "AWAITING_APPROVAL":
            # Cannot safely restore AWAITING_APPROVAL without candidate_plans
            # Normalize to ANOMALY — operator must regenerate plans
            normalized_status = "ANOMALY"

        # EXECUTING is safe to restore because active_route is persisted
        # RUNNING, PAUSED, IDLE, ANOMALY, COMPLETED, RESET are all safe

        # Construct restored mission
        restored = Mission(
            mission_id=seed_mission.mission_id,
            label=seed_mission.label,
            status=normalized_status,
            elapsed_s=snapshot_data["elapsed_s"],
            resources=resources,
            original_route=seed_mission.original_route,
            active_route=active_route,
            candidate_plans=[],  # Not persisted; cleared on restore
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
        """Restore mission state from a previously persisted Mission.

        Used at startup to load a Mission reconstructed from durable storage.
        This is the only way to set mission state externally; all other
        mutations go through explicit transition methods.

        Args:
            mission: A fully reconstructed Mission domain object.

        Returns:
            The restored mission.
        """
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

    def start(self) -> Mission:
        """Transition mission from IDLE to RUNNING."""
        mission = self.get_mission()
        if mission.status != MissionStatus.IDLE:
            raise MissionStateError(mission.status.value, "start")
        mission.status = MissionStatus.RUNNING
        event = self._create_audit_event(
            "mission.started", "Mission started by operator"
        )
        self._append_audit(event)
        return mission

    def pause(self) -> Mission:
        """Transition mission from RUNNING to PAUSED."""
        mission = self.get_mission()
        if mission.status != MissionStatus.RUNNING:
            raise MissionStateError(mission.status.value, "pause")
        mission.status = MissionStatus.PAUSED
        event = self._create_audit_event("mission.paused", "Mission paused by operator")
        self._append_audit(event)
        return mission

    def resume(self) -> Mission:
        """Transition mission from PAUSED to RUNNING."""
        mission = self.get_mission()
        if mission.status != MissionStatus.PAUSED:
            raise MissionStateError(mission.status.value, "resume")
        mission.status = MissionStatus.RUNNING
        event = self._create_audit_event(
            "mission.resumed", "Mission resumed by operator"
        )
        self._append_audit(event)
        return mission

    def inject_anomaly(self) -> Mission:
        """Transition mission from RUNNING to ANOMALY."""
        mission = self.get_mission()
        if mission.status != MissionStatus.RUNNING:
            raise MissionStateError(mission.status.value, "inject anomaly")
        mission.status = MissionStatus.ANOMALY
        mission.anomaly_active = True
        event = self._create_audit_event("anomaly.injected", "Battery anomaly injected")
        self._append_audit(event)
        return mission

    def reset(self) -> Mission:
        """Reset mission to deterministic seed state."""
        seed_mission = get_seed_mission()

        # New mission gets fresh audit trail; add reset event
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

        # Transition: ANOMALY -> PLANNING
        mission.status = MissionStatus.PLANNING
        planning_started_event = self._create_audit_event(
            "planning.started",
            "Candidate plan generation initiated",
        )
        self._append_audit(planning_started_event)

        if self._planning_service is None:
            raise RuntimeError("PlanningService not injected")

        # Generate candidate plans
        candidate_plans = self._planning_service.generate_candidate_plans(mission)

        # Assign to mission
        mission.candidate_plans = candidate_plans

        # Safety verification for each plan
        if self._safety_verifier is None:
            raise RuntimeError("SafetyVerifier not injected")

        for plan in mission.candidate_plans:
            violations = self._safety_verifier.verify(plan)
            plan.violations = violations
            if violations:
                plan.status = PlanStatus.REJECTED
            else:
                plan.status = PlanStatus.VALID

        # Determine recommendation (Extended Survey - VALID plan with highest yield)
        # Plan B (Extended Survey) is the recommended one
        for plan in mission.candidate_plans:
            if plan.label == "Extended Survey" and plan.status == PlanStatus.VALID:
                plan.is_recommended = True
                plan.rank = 1
            elif plan.status == PlanStatus.VALID:
                plan.is_recommended = False
                plan.rank = 2 if plan.is_recommended is False else 1

        # Transition: PLANNING -> AWAITING_APPROVAL
        mission.status = MissionStatus.AWAITING_APPROVAL
        plans_generated_event = self._create_audit_event(
            "plans.generated",
            f"Generated {len(candidate_plans)} candidate plans",
            {"plan_count": len(candidate_plans)},
        )
        self._append_audit(plans_generated_event)

        return mission

    def approve_plan(self, plan_id: str) -> Mission:
        """Approve a candidate plan and transition to EXECUTING."""
        mission = self.get_mission()
        if mission.status != MissionStatus.AWAITING_APPROVAL:
            raise MissionStateError(mission.status.value, "approve plan")

        # Find the plan
        plan = next((p for p in mission.candidate_plans if p.plan_id == plan_id), None)
        if plan is None:
            raise PlanNotFoundError(plan_id)

        # Re-run safety verification independently
        if self._safety_verifier is None:
            raise RuntimeError("SafetyVerifier not injected")

        violations = self._safety_verifier.verify(plan)
        if violations:
            raise PlanUnsafeError(plan_id, [v.description for v in violations])

        if plan.status == PlanStatus.REJECTED:
            raise PlanUnsafeError(
                plan_id, ["Plan was previously rejected by safety verification"]
            )

        # Approve the plan
        plan.status = PlanStatus.APPROVED
        mission.active_route = (
            plan.active_route if hasattr(plan, "active_route") else plan
        )
        # The plan contains waypoints; update active_route
        from app.schemas import MissionRoute

        mission.active_route = MissionRoute(waypoints=list(plan.waypoints))

        # Update mission status
        mission.status = MissionStatus.EXECUTING

        # Audit
        audit_event = self._create_audit_event(
            "plan.approved",
            f"Plan {plan.label} ({plan_id}) approved and activated",
            {"approved_plan_id": plan_id, "plan_label": plan.label},
        )
        self._append_audit(audit_event)

        return mission
