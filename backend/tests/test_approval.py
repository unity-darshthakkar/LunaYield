"""Tests for plan approval logic."""

import pytest
from fastapi.testclient import TestClient

from app.schemas import MissionStatus, PlanStatus, WaypointProgressStatus
from app.services.exceptions import PlanNotFoundError, PlanUnsafeError
from app.services.mission import MissionService
from app.services.planning import PlanningService
from app.services.safety import SafetyVerifier
from app.services.telemetry import TelemetryService


class TestPlanApprovalService:
    """Test plan approval via MissionService."""

    def _advance_ticks(self, telemetry: TelemetryService, ticks: int) -> None:
        for _ in range(ticks):
            telemetry.generate_sample()

    def setup_plan_generation(self, clean_mission: MissionService) -> MissionService:
        """Helper to set up mission with generated plans."""
        planning = PlanningService()
        clean_mission.set_dependencies(SafetyVerifier(), planning)
        clean_mission.start()
        clean_mission.inject_anomaly()
        clean_mission.generate_plans()
        return clean_mission

    def test_approve_valid_plan_succeeds(self, clean_mission: MissionService) -> None:
        mission = self.setup_plan_generation(clean_mission)
        extended_plan = next(
            p
            for p in mission.get_mission().candidate_plans
            if p.label == "Extended Survey"
        )

        result = mission.approve_plan(extended_plan.plan_id)

        assert result.status == MissionStatus.EXECUTING
        assert result.anomaly_active is False
        assert extended_plan.status == PlanStatus.APPROVED
        assert any(e.event_type == "plan.approved" for e in result.audit_trail)

    def test_approve_unknown_plan_returns_404(
        self, clean_mission: MissionService
    ) -> None:
        mission = self.setup_plan_generation(clean_mission)

        with pytest.raises(PlanNotFoundError):
            mission.approve_plan("non-existent-plan")

    def test_approve_rejected_plan_returns_422(
        self, clean_mission: MissionService
    ) -> None:
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
        mission = self.setup_plan_generation(clean_mission)
        minimal_plan = next(
            p
            for p in mission.get_mission().candidate_plans
            if p.label == "Minimal Survey"
        )

        result = mission.approve_plan(minimal_plan.plan_id)
        assert result.status == MissionStatus.EXECUTING

    def test_active_route_changes_on_approval(
        self, clean_mission: MissionService
    ) -> None:
        mission = clean_mission
        mission.set_dependencies(SafetyVerifier(), PlanningService())
        mission.start()
        telemetry = TelemetryService(mission)
        for _ in range(64):
            telemetry.generate_sample()
        mission.inject_anomaly()
        mission.generate_plans()

        minimal_plan = next(
            p
            for p in mission.get_mission().candidate_plans
            if p.label == "Minimal Survey"
        )

        mission.approve_plan(minimal_plan.plan_id)

        active_route = mission.get_mission().active_route.waypoints
        route_statuses = {wp.id: wp.progress_status for wp in active_route}
        assert route_statuses["wp-crater-a"] == WaypointProgressStatus.COMPLETED
        assert route_statuses["wp-ice-deposit"] == WaypointProgressStatus.COMPLETED
        assert route_statuses["wp-ridge"] == WaypointProgressStatus.CURRENT
        assert route_statuses["wp-return"] == WaypointProgressStatus.UPCOMING

    def test_minimal_recovery_completes_near_predicted_battery(
        self, clean_mission: MissionService
    ) -> None:
        clean_mission.set_dependencies(SafetyVerifier(), PlanningService())
        clean_mission.start()
        telemetry = TelemetryService(clean_mission)
        self._advance_ticks(telemetry, 30)

        mission = clean_mission.get_mission()
        assert mission.resources.battery_pct == 85.0

        clean_mission.inject_anomaly()
        assert mission.resources.battery_pct == 80.0

        clean_mission.generate_plans()
        minimal_plan = next(
            p for p in mission.candidate_plans if p.label == "Minimal Survey"
        )
        assert minimal_plan.predicted_return_battery_pct == 30.0

        clean_mission.approve_plan(minimal_plan.plan_id)
        while clean_mission.get_mission().status != MissionStatus.COMPLETED:
            assert telemetry.generate_sample() is not None

        final_mission = clean_mission.get_mission()
        assert final_mission.resources.battery_pct == 30.0
        assert final_mission.resources.storage_pct == 66.0
        assert (
            final_mission.resources.battery_pct
            == minimal_plan.predicted_return_battery_pct
        )
        route_statuses = {
            wp.id: wp.progress_status for wp in final_mission.active_route.waypoints
        }
        assert route_statuses["wp-ridge"] == WaypointProgressStatus.SKIPPED

    def test_extended_recovery_completes_near_predicted_battery(
        self, clean_mission: MissionService
    ) -> None:
        clean_mission.set_dependencies(SafetyVerifier(), PlanningService())
        clean_mission.start()
        telemetry = TelemetryService(clean_mission)
        self._advance_ticks(telemetry, 30)

        mission = clean_mission.get_mission()
        clean_mission.inject_anomaly()
        assert mission.resources.battery_pct == 80.0

        clean_mission.generate_plans()
        extended_plan = next(
            p for p in mission.candidate_plans if p.label == "Extended Survey"
        )
        assert extended_plan.predicted_return_battery_pct == 21.0

        clean_mission.approve_plan(extended_plan.plan_id)
        while clean_mission.get_mission().status != MissionStatus.COMPLETED:
            assert telemetry.generate_sample() is not None

        final_mission = clean_mission.get_mission()
        assert final_mission.resources.battery_pct == 21.0
        assert final_mission.resources.storage_pct == 100.0
        assert (
            final_mission.resources.battery_pct
            == extended_plan.predicted_return_battery_pct
        )
        assert all(
            waypoint.progress_status == WaypointProgressStatus.COMPLETED
            for waypoint in final_mission.active_route.waypoints
            if waypoint.progress_status != WaypointProgressStatus.SKIPPED
        )

    def test_approved_plan_receives_approved_status(
        self, clean_mission: MissionService
    ) -> None:
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
        mission = self.setup_plan_generation(clean_mission)
        aggressive_plan = next(
            p
            for p in mission.get_mission().candidate_plans
            if p.label == "Aggressive Survey"
        )

        assert aggressive_plan.status == PlanStatus.REJECTED

        with pytest.raises(PlanUnsafeError):
            mission.approve_plan(aggressive_plan.plan_id)

        assert aggressive_plan.status == PlanStatus.REJECTED
        assert mission.get_mission().status == MissionStatus.AWAITING_APPROVAL


class TestPlanApprovalAPI:
    """Test plan approval via HTTP API."""

    def _setup_awaiting_approval(self, client: TestClient):
        client.post("/api/mission/start")
        client.post("/api/mission/inject-anomaly")
        client.post("/api/plans/generate")

    def test_approve_valid_plan(self, client: TestClient) -> None:
        self._setup_awaiting_approval(client)

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

        mission_state = client.get("/api/mission/state")
        assert mission_state.json()["status"] == "EXECUTING"

    def test_approve_unknown_plan_returns_404(self, client: TestClient) -> None:
        self._setup_awaiting_approval(client)

        response = client.post("/api/plans/unknown-plan/approve")
        assert response.status_code == 404

    def test_approve_rejected_plan_returns_422(self, client: TestClient) -> None:
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
        client.get("/api/mission/state")
        response = client.post("/api/plans/some-plan/approve")
        assert response.status_code == 409
