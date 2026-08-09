"""Tests for deterministic safety verification."""

from app.schemas import CandidatePlan, ConstraintViolation, PlanStatus, RouteWaypoint
from app.services.safety import SafetyVerifier


class TestSafetyVerifier:
    """Test safety verification logic."""

    def test_plan_with_sufficient_return_battery_passes(
        self, safety_verifier: SafetyVerifier
    ) -> None:
        """Plan with >= 20% return battery should pass."""
        plan = self._create_plan(predicted_return_battery_pct=20.0)
        violations = safety_verifier.verify(plan)
        assert violations == []
        assert safety_verifier.is_valid(plan) is True

    def test_plan_with_high_return_battery_passes(
        self, safety_verifier: SafetyVerifier
    ) -> None:
        """Plan with high return battery should pass."""
        plan = self._create_plan(predicted_return_battery_pct=42.0)
        violations = safety_verifier.verify(plan)
        assert violations == []
        assert safety_verifier.is_valid(plan) is True

    def test_plan_with_low_return_battery_fails(
        self, safety_verifier: SafetyVerifier
    ) -> None:
        """Plan with < 20% return battery should fail."""
        plan = self._create_plan(predicted_return_battery_pct=11.0)
        violations = safety_verifier.verify(plan)
        assert len(violations) == 1
        assert violations[0].rule_id == "RETURN_BATTERY_MIN_20PCT"
        assert violations[0].measured_value == 11.0
        assert violations[0].threshold_value == 20.0
        assert "below minimum" in violations[0].description
        assert safety_verifier.is_valid(plan) is False

    def test_plan_with_exactly_20_pct_passes(
        self, safety_verifier: SafetyVerifier
    ) -> None:
        """Plan with exactly 20% return battery should pass (boundary)."""
        plan = self._create_plan(predicted_return_battery_pct=20.0)
        violations = safety_verifier.verify(plan)
        assert violations == []

    def test_plan_with_19_9_pct_fails(self, safety_verifier: SafetyVerifier) -> None:
        """Plan with 19.9% return battery should fail (boundary)."""
        plan = self._create_plan(predicted_return_battery_pct=19.9)
        violations = safety_verifier.verify(plan)
        assert len(violations) == 1

    def test_verifier_is_pure_and_independent(
        self, safety_verifier: SafetyVerifier
    ) -> None:
        """SafetyVerifier should have no external dependencies and be stateless."""
        plan1 = self._create_plan(predicted_return_battery_pct=30.0)
        plan2 = self._create_plan(predicted_return_battery_pct=15.0)

        # Multiple calls should produce same results
        for _ in range(3):
            assert safety_verifier.verify(plan1) == []
            assert len(safety_verifier.verify(plan2)) == 1

        # No internal state should be modified
        assert not hasattr(safety_verifier, "_cache")

    def test_violation_contains_required_fields(
        self, safety_verifier: SafetyVerifier
    ) -> None:
        """ConstraintViolation should contain all required fields."""
        plan = self._create_plan(predicted_return_battery_pct=10.0)
        violations = safety_verifier.verify(plan)

        violation = violations[0]
        assert isinstance(violation, ConstraintViolation)
        assert violation.rule_id == "RETURN_BATTERY_MIN_20PCT"
        assert isinstance(violation.description, str)
        assert len(violation.description) > 0
        assert violation.measured_value == 10.0
        assert violation.threshold_value == 20.0

    def _create_plan(self, predicted_return_battery_pct: float) -> CandidatePlan:
        """Helper to create a test candidate plan."""
        return CandidatePlan(
            plan_id="test-plan",
            label="Test Plan",
            description="Test plan for safety verification",
            waypoints=[
                RouteWaypoint(id="wp-1", x=0.1, y=0.1, label="Start"),
                RouteWaypoint(
                    id="wp-2", x=0.5, y=0.5, label="Target", is_science_target=True
                ),
                RouteWaypoint(id="wp-3", x=0.1, y=0.1, label="Return"),
            ],
            science_yield_score=50.0,
            predicted_return_battery_pct=predicted_return_battery_pct,
            status=PlanStatus.VALID,
            violations=[],
            is_recommended=False,
            rank=1,
        )
