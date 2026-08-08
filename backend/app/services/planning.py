"""Planning service — deterministic candidate plan generation."""

from __future__ import annotations

from app.schemas import CandidatePlan, Mission, MissionRoute, PlanStatus, RouteWaypoint


class PlanningService:
    """Generates deterministic candidate plans for Phase 1B."""

    def __init__(self) -> None:
        # No counter - IDs are deterministic based on plan label
        pass

    def _plan_id_from_label(self, label: str) -> str:
        """Generate deterministic plan ID from label."""
        # Create consistent IDs: plan-a-001, plan-b-001, plan-c-001
        label_lower = label.lower().replace(" ", "-")
        if "minimal" in label_lower:
            return "plan-a-001"
        elif "extended" in label_lower:
            return "plan-b-001"
        elif "aggressive" in label_lower:
            return "plan-c-001"
        return f"plan-{label_lower}-001"

    def _base_waypoints(self) -> list[RouteWaypoint]:
        """Return the base waypoint sequence for all plans."""
        return [
            RouteWaypoint(
                id="wp-base",
                x=0.1,
                y=0.1,
                label="Base Camp",
                is_science_target=False,
            ),
            RouteWaypoint(
                id="wp-crater-a",
                x=0.3,
                y=0.4,
                label="Crater A Rim",
                is_science_target=True,
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

    def generate_candidate_plans(self, mission: Mission) -> list[CandidatePlan]:
        """Generate exactly three deterministic candidate plans.

        Plan A: Minimal Survey - 34% return battery, VALID, not recommended
        Plan B: Extended Survey - 42% return battery, VALID, recommended
        Plan C: Aggressive Survey - 11% return battery, REJECTED, not recommended
        """
        base_route = MissionRoute(waypoints=self._base_waypoints())

        # Plan A: Minimal Survey
        plan_a = CandidatePlan(
            plan_id=self._plan_id_from_label("Minimal Survey"),
            label="Minimal Survey",
            description="Conservative return to base with minimal science stops",
            waypoints=list(base_route.waypoints),
            science_yield_score=45.0,
            predicted_return_battery_pct=34.0,
            status=PlanStatus.VALID,
            violations=[],
            is_recommended=False,
            rank=2,
        )

        # Plan B: Extended Survey (RECOMMENDED)
        plan_b = CandidatePlan(
            plan_id=self._plan_id_from_label("Extended Survey"),
            label="Extended Survey",
            description="Full science survey with optimal resource management",
            waypoints=list(base_route.waypoints),
            science_yield_score=78.0,
            predicted_return_battery_pct=42.0,
            status=PlanStatus.VALID,
            violations=[],
            is_recommended=True,
            rank=1,
        )

        # Plan C: Aggressive Survey (REJECTED)
        plan_c = CandidatePlan(
            plan_id=self._plan_id_from_label("Aggressive Survey"),
            label="Aggressive Survey",
            description="Extended science targets with aggressive resource usage",
            waypoints=[
                *list(base_route.waypoints),
                RouteWaypoint(
                    id="wp-extra-crater",
                    x=0.8,
                    y=0.3,
                    label="Extra Crater Survey",
                    is_science_target=True,
                ),
                RouteWaypoint(
                    id="wp-return-2",
                    x=0.1,
                    y=0.1,
                    label="Base Camp (Return)",
                    is_science_target=False,
                ),
            ],
            science_yield_score=92.0,
            predicted_return_battery_pct=11.0,
            status=PlanStatus.REJECTED,
            violations=[],  # Will be populated by safety verifier
            is_recommended=False,
            rank=3,
        )

        return [plan_a, plan_b, plan_c]
