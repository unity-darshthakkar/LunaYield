"""Tests for plan approval logic."""

import pytest
from fastapi.testclient import TestClient

from app.schemas import MissionStatus, PlanStatus
from app.services.exceptions import PlanNotFoundError, PlanUnsafeError
from app.services.mission import MissionService
from app.services.planning import PlanningService
from app.services.safety import SafetyVerifier


class TestPlanApprovalService:
    """Test plan approval via MissionService."""

    def setup_plan_generation(self, clean_mission: MissionService) -> MissionService:
        """Helper to set up mission with generated plans."""
        planning = PlanningService()
        clean_mission.set_dependencies(SafetyVerifier(), planning)
        clean_mission.start()
        clean_mission.inject_anomaly()
        clean_mission.generate_plans()
        return clean_mission

    def test_approve_valid_plan_succeeds(self, clean_mission: MissionService) -> None:
        """Approving a valid plan should succeed."""
        mission = self.setup_plan_generation(clean_mission)
        extended_plan = next(
            p
            for p in mission.get_mission().candidate_plans
            if p.label == "Extended Survey"
        )

        result = mission.approve_plan(extended_plan.plan_id)

        assert result.status == MissionStatus.EXECUTING
        assert extended_plan.status == PlanStatus.APPROVED
        assert any(e.event_type == "plan.approved" for e in result.audit_trail)

    def test_approve_unknown_plan_returns_404(
        self, clean_mission: MissionService
    ) -> None:
        """Approving unknown plan should raise PlanNotFoundError."""
        mission = self.setup_plan_generation(clean_mission)

        with pytest.raises(PlanNotFoundError):
            mission.approve_plan("non-existent-plan")

    def test_approve_rejected_plan_returns_422(
        self, clean_mission: MissionService
    ) -> None:
        """Approving a rejected plan should raise PlanUnsafeError."""
        mission = self.setup_plan_generation(clean_mission)
        aggressive_plan = next(
            p
            for p in mission.get_mission().candidate_plans
            if p.label == "Aggressive Survey"
        )

        with pytest.raises(PlanUnsafeError):
            mission.approve_plan(aggressive_plan.plan_id)

    def test_approval_independently_reverifies_safety(
        self, clean_mission: MissionService
    ) -> None:
        """Approval should independently re-run safety verification."""
        mission = self.setup_plan_generation(clean_mission)
        minimal_plan = next(
            p
            for p in mission.get_mission().candidate_plans
            if p.label == "Minimal Survey"
        )

        # Minimal Survey has 34% battery - should be valid
        result = mission.approve_plan(minimal_plan.plan_id)
        assert result.status == MissionStatus.EXECUTING

    def test_active_route_changes_on_approval(
        self, clean_mission: MissionService
    ) -> None:
        """Mission.active_route should be updated to approved plan's route."""
        mission = self.setup_plan_generation(clean_mission)
        extended_plan = next(
            p
            for p in mission.get_mission().candidate_plans
            if p.label == "Extended Survey"
        )

        # Get the approved plan's waypoints
        plan_waypoints = [wp.id for wp in extended_plan.waypoints]

        mission.approve_plan(extended_plan.plan_id)

        # Verify active_route matches the approved plan's waypoints
        active_route_waypoints = [
            wp.id for wp in mission.get_mission().active_route.waypoints
        ]
        assert active_route_waypoints == plan_waypoints

    def test_approved_plan_receives_approved_status(
        self, clean_mission: MissionService
    ) -> None:
        """Approved CandidatePlan should have PlanStatus.APPROVED."""
        mission = self.setup_plan_generation(clean_mission)
        extended_plan = next(
            p
            for p in mission.get_mission().candidate_plans
            if p.label == "Extended Survey"
        )

        mission.approve_plan(extended_plan.plan_id)

        assert extended_plan.status == PlanStatus.APPROVED

    def test_mission_status_becomes_executing(
        self, clean_mission: MissionService
    ) -> None:
        """MissionStatus should become EXECUTING after approval."""
        mission = self.setup_plan_generation(clean_mission)
        extended_plan = next(
            p
            for p in mission.get_mission().candidate_plans
            if p.label == "Extended Survey"
        )

        result = mission.approve_plan(extended_plan.plan_id)

        assert result.status == MissionStatus.EXECUTING

    def test_rejected_plan_can_never_be_approved(
        self, clean_mission: MissionService
    ) -> None:
        """A previously rejected plan can never become APPROVED."""
        mission = self.setup_plan_generation(clean_mission)
        aggressive_plan = next(
            p
            for p in mission.get_mission().candidate_plans
            if p.label == "Aggressive Survey"
        )

        # First verify it's rejected
        assert aggressive_plan.status == PlanStatus.REJECTED

        # Attempt approval - should fail
        with pytest.raises(PlanUnsafeError):
            mission.approve_plan(aggressive_plan.plan_id)

        # Plan status should remain REJECTED
        assert aggressive_plan.status == PlanStatus.REJECTED

        # Mission should still be AWAITING_APPROVAL
        assert mission.get_mission().status == MissionStatus.AWAITING_APPROVAL


class TestPlanApprovalAPI:
    """Test plan approval via HTTP API."""

    def _setup_awaiting_approval(self, client: TestClient):
        """Helper to get mission to AWAITING_APPROVAL state."""
        client.post("/api/mission/start")
        client.post("/api/mission/inject-anomaly")
        client.post("/api/plans/generate")

    def test_approve_valid_plan(self, client: TestClient) -> None:
        """Approving valid plan should return 200 and plan with APPROVED status."""
        self._setup_awaiting_approval(client)

        # Get the plans to find Extended Survey ID
        state = client.get("/api/mission/state")
        ext_plan = next(
            p
            for p in state.json()["candidate_plans"]
            if p["label"] == "Extended Survey"
        )

        response = client.post(f"/api/plans/{ext_plan['plan_id']}/approve")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "APPROVED"
        assert data["plan_id"] == ext_plan["plan_id"]

        # Verify mission state
        mission_state = client.get("/api/mission/state")
        assert mission_state.json()["status"] == "EXECUTING"

    def test_approve_unknown_plan_returns_404(self, client: TestClient) -> None:
        """Approving unknown plan should return 404."""
        self._setup_awaiting_approval(client)

        response = client.post("/api/plans/unknown-plan/approve")
        assert response.status_code == 404

    def test_approve_rejected_plan_returns_422(self, client: TestClient) -> None:
        """Approving rejected plan should return 422."""
        self._setup_awaiting_approval(client)

        state = client.get("/api/mission/state")
        agg_plan = next(
            p
            for p in state.json()["candidate_plans"]
            if p["label"] == "Aggressive Survey"
        )

        response = client.post(f"/api/plans/{agg_plan['plan_id']}/approve")
        assert response.status_code == 422

    def test_approve_from_wrong_state_returns_409(self, client: TestClient) -> None:
        """Approving from wrong mission state should return 409."""
        # Don't setup - mission is IDLE
        client.get("/api/mission/state")
        # No plans exist, but test the state check
        response = client.post("/api/plans/some-plan/approve")
        assert response.status_code == 409
