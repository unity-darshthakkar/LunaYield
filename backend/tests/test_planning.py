"""Tests for deterministic planning and plan generation."""

from fastapi.testclient import TestClient

from app.schemas import PlanStatus
from app.services.mission import MissionService
from app.services.planning import PlanningService
from app.services.safety import SafetyVerifier


class TestPlanningService:
    """Test PlanningService deterministic plan generation."""

    def test_generate_exactly_three_plans(self, clean_mission: MissionService) -> None:
        """Should generate exactly 3 candidate plans."""
        planning = PlanningService()
        clean_mission.set_dependencies(SafetyVerifier(), planning)
        clean_mission.start()
        clean_mission.inject_anomaly()

        plans = planning.generate_candidate_plans(clean_mission.get_mission())

        assert len(plans) == 3

    def test_minimal_survey_plan_properties(
        self, clean_mission: MissionService
    ) -> None:
        """Plan A (Minimal Survey) should have correct properties."""
        planning = PlanningService()
        clean_mission.set_dependencies(SafetyVerifier(), planning)
        clean_mission.start()
        clean_mission.inject_anomaly()

        plans = planning.generate_candidate_plans(clean_mission.get_mission())
        plan_a = next(p for p in plans if p.label == "Minimal Survey")

        assert plan_a.predicted_return_battery_pct == 34.0
        assert plan_a.status == PlanStatus.VALID
        assert plan_a.is_recommended is False
        assert plan_a.rank == 2
        assert plan_a.science_yield_score == 45.0

    def test_extended_survey_plan_properties(
        self, clean_mission: MissionService
    ) -> None:
        """Plan B (Extended Survey) should have correct properties."""
        planning = PlanningService()
        clean_mission.set_dependencies(SafetyVerifier(), planning)
        clean_mission.start()
        clean_mission.inject_anomaly()

        plans = planning.generate_candidate_plans(clean_mission.get_mission())
        plan_b = next(p for p in plans if p.label == "Extended Survey")

        assert plan_b.predicted_return_battery_pct == 42.0
        assert plan_b.status == PlanStatus.VALID
        assert plan_b.is_recommended is True
        assert plan_b.rank == 1
        assert plan_b.science_yield_score == 78.0

    def test_aggressive_survey_plan_properties(
        self, clean_mission: MissionService
    ) -> None:
        """Plan C (Aggressive Survey) should have correct properties."""
        planning = PlanningService()
        clean_mission.set_dependencies(SafetyVerifier(), planning)
        clean_mission.start()
        clean_mission.inject_anomaly()

        plans = planning.generate_candidate_plans(clean_mission.get_mission())
        plan_c = next(p for p in plans if p.label == "Aggressive Survey")

        assert plan_c.predicted_return_battery_pct == 11.0
        assert plan_c.is_recommended is False
        assert plan_c.rank == 3
        assert plan_c.science_yield_score == 92.0
        # Has extra waypoint
        assert len(plan_c.waypoints) == 7  # 5 base + 2 extra

    def test_exactly_one_recommended_plan(self, clean_mission: MissionService) -> None:
        """Exactly one plan should be recommended."""
        planning = PlanningService()
        clean_mission.set_dependencies(SafetyVerifier(), planning)
        clean_mission.start()
        clean_mission.inject_anomaly()

        plans = planning.generate_candidate_plans(clean_mission.get_mission())
        recommended = [p for p in plans if p.is_recommended]

        assert len(recommended) == 1
        assert recommended[0].label == "Extended Survey"

    def test_recommended_plan_is_valid(self, clean_mission: MissionService) -> None:
        """The recommended plan must be VALID."""
        planning = PlanningService()
        clean_mission.set_dependencies(SafetyVerifier(), planning)
        clean_mission.start()
        clean_mission.inject_anomaly()

        plans = planning.generate_candidate_plans(clean_mission.get_mission())
        recommended = [p for p in plans if p.is_recommended]

        assert recommended[0].status == PlanStatus.VALID

    def test_rejected_plan_contains_violations(
        self, clean_mission: MissionService
    ) -> None:
        """Rejected plan should have violations after safety verification."""
        planning = PlanningService()
        clean_mission.set_dependencies(SafetyVerifier(), planning)
        clean_mission.start()
        clean_mission.inject_anomaly()

        # The generate_plans on MissionService runs safety verification
        mission = clean_mission.generate_plans()
        plan_c = next(
            p for p in mission.candidate_plans if p.label == "Aggressive Survey"
        )

        # Aggressive Survey has 11% battery, which is < 20% - should be REJECTED
        assert plan_c.status == PlanStatus.REJECTED
        assert len(plan_c.violations) >= 1
        assert any(v.rule_id == "RETURN_BATTERY_MIN_20PCT" for v in plan_c.violations)

    def test_rejected_plan_never_recommended(
        self, clean_mission: MissionService
    ) -> None:
        """Rejected plan must never be recommended."""
        planning = PlanningService()
        clean_mission.set_dependencies(SafetyVerifier(), planning)
        clean_mission.start()
        clean_mission.inject_anomaly()

        mission = clean_mission.generate_plans()
        rejected = [
            p for p in mission.candidate_plans if p.status == PlanStatus.REJECTED
        ]

        for plan in rejected:
            assert plan.is_recommended is False

    def test_plans_have_deterministic_ids(self, clean_mission: MissionService) -> None:
        """Plan IDs should be deterministic across runs."""
        planning = PlanningService()
        clean_mission.set_dependencies(SafetyVerifier(), planning)
        clean_mission.start()
        clean_mission.inject_anomaly()

        plans1 = planning.generate_candidate_plans(clean_mission.get_mission())
        plans2 = planning.generate_candidate_plans(clean_mission.get_mission())

        for p1, p2 in zip(plans1, plans2):
            assert p1.plan_id == p2.plan_id
            assert p1.label == p2.label
            assert p1.predicted_return_battery_pct == p2.predicted_return_battery_pct


class TestPlanningAPI:
    """Test plan generation via HTTP API."""

    def test_generate_plans_requires_anomaly_state(self, client: TestClient) -> None:
        """Plan generation should fail if not in ANOMALY state."""
        response = client.post("/api/plans/generate")
        assert response.status_code == 409

    def test_generate_plans_from_anomaly(self, client: TestClient) -> None:
        """Plan generation should succeed from ANOMALY state."""
        client.post("/api/mission/start")
        client.post("/api/mission/inject-anomaly")

        response = client.post("/api/plans/generate")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

        # Check plan labels
        labels = [p["label"] for p in data]
        assert "Minimal Survey" in labels
        assert "Extended Survey" in labels
        assert "Aggressive Survey" in labels

        # Check battery values
        min_plan = next(p for p in data if p["label"] == "Minimal Survey")
        ext_plan = next(p for p in data if p["label"] == "Extended Survey")
        agg_plan = next(p for p in data if p["label"] == "Aggressive Survey")

        assert min_plan["predicted_return_battery_pct"] == 34.0
        assert ext_plan["predicted_return_battery_pct"] == 42.0
        assert agg_plan["predicted_return_battery_pct"] == 11.0

        # Check recommended
        recommended = [p for p in data if p["is_recommended"]]
        assert len(recommended) == 1
        assert recommended[0]["label"] == "Extended Survey"

        # Check Aggressive is rejected
        assert agg_plan["status"] == "REJECTED"
        assert len(agg_plan["violations"]) >= 1

    def test_mission_status_transitions_correctly(self, client: TestClient) -> None:
        """Mission should go ANOMALY -> PLANNING -> AWAITING_APPROVAL."""
        client.post("/api/mission/start")
        client.post("/api/mission/inject-anomaly")

        # Check state before generation
        state_before = client.get("/api/mission/state")
        assert state_before.json()["status"] == "ANOMALY"

        # Generate plans
        client.post("/api/plans/generate")

        # Check state after
        state_after = client.get("/api/mission/state")
        assert state_after.json()["status"] == "AWAITING_APPROVAL"
        assert len(state_after.json()["candidate_plans"]) == 3
