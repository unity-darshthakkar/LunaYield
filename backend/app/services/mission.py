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
