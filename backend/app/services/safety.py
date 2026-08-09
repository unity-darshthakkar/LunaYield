"""Safety verifier — deterministic, pure safety verification."""

from __future__ import annotations

from app.schemas import CandidatePlan, ConstraintViolation


class SafetyVerifier:
    """Deterministic safety verification for candidate plans.

    Phase 1B implements the RETURN_BATTERY_MIN_20PCT rule.
    """

    MIN_RETURN_BATTERY_PCT = 20.0
    RULE_ID = "RETURN_BATTERY_MIN_20PCT"

    def verify(self, plan: CandidatePlan) -> list[ConstraintViolation]:
        """Verify a candidate plan against safety rules.

        Args:
            plan: The candidate plan to verify.

        Returns:
            List of ConstraintViolation objects (empty if plan is valid).
        """
        violations: list[ConstraintViolation] = []

        # Rule: predicted return battery must be >= 20%
        if plan.predicted_return_battery_pct < self.MIN_RETURN_BATTERY_PCT:
            pct = plan.predicted_return_battery_pct
            violations.append(
                ConstraintViolation(
                    rule_id=self.RULE_ID,
                    description=(
                        f"Predicted return battery {pct:.1f}% "
                        f"is below minimum {self.MIN_RETURN_BATTERY_PCT}%"
                    ),
                    measured_value=pct,
                    threshold_value=self.MIN_RETURN_BATTERY_PCT,
                )
            )

        return violations

    def is_valid(self, plan: CandidatePlan) -> bool:
        """Check if a plan passes all safety rules."""
        return len(self.verify(plan)) == 0
