"""Planning service — deterministic candidate plan generation."""

from __future__ import annotations

from app.schemas import (
    CandidatePlan,
    Mission,
    MissionRoute,
    PlanStatus,
    RouteWaypoint,
    WaypointProgressStatus,
)
from app.services.route_progress import clone_waypoints, predict_return_battery_pct


class PlanningService:
    """Generates deterministic candidate plans for Phase 1B."""

    def __init__(self) -> None:
        pass

    def _plan_id_from_label(self, label: str) -> str:
        """Generate deterministic plan ID from label."""
        label_lower = label.lower().replace(" ", "-")
        if "minimal" in label_lower:
            return "plan-a-001"
        if "extended" in label_lower:
            return "plan-b-001"
        if "aggressive" in label_lower:
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

    def _route_basis(self, mission: Mission) -> list[RouteWaypoint]:
        """Use current active route progress when generating recovery plans."""
        if mission.active_route.waypoints:
            return clone_waypoints(mission.active_route.waypoints)
        return clone_waypoints(self._base_waypoints())

    def _minimal_route(self, mission: Mission) -> list[RouteWaypoint]:
        """Keep completed/current work, skip future science, and return safely."""
        waypoints = self._route_basis(mission)
        current_index = next(
            (
                index
                for index, waypoint in enumerate(waypoints)
                if waypoint.progress_status == WaypointProgressStatus.CURRENT
            ),
            None,
        )

        for index, waypoint in enumerate(waypoints):
            if waypoint.progress_status in (
                WaypointProgressStatus.COMPLETED,
                WaypointProgressStatus.CURRENT,
                WaypointProgressStatus.SKIPPED,
            ):
                continue
            if waypoint.id == "wp-return":
                waypoint.progress_status = WaypointProgressStatus.UPCOMING
                continue
            if current_index is None or index > current_index:
                waypoint.progress_status = WaypointProgressStatus.SKIPPED
                waypoint.segment_elapsed_s = 0
                waypoint.science_collected = False

        return waypoints

    def _extended_route(self, mission: Mission) -> list[RouteWaypoint]:
        """Continue the current route with no additional skips."""
        return self._route_basis(mission)

    def _aggressive_route(self, mission: Mission) -> list[RouteWaypoint]:
        """Append an extra science target and second return leg."""
        waypoints = self._route_basis(mission)
        waypoints.extend(
            [
                RouteWaypoint(
                    id="wp-extra-crater",
                    x=0.8,
                    y=0.3,
                    label="Extra Crater Survey",
                    is_science_target=True,
                    progress_status=WaypointProgressStatus.UPCOMING,
                ),
                RouteWaypoint(
                    id="wp-return-2",
                    x=0.1,
                    y=0.1,
                    label="Base Camp (Return)",
                    is_science_target=False,
                    progress_status=WaypointProgressStatus.UPCOMING,
                ),
            ]
        )
        return waypoints

    def generate_candidate_plans(self, mission: Mission) -> list[CandidatePlan]:
        """Generate exactly three deterministic candidate plans."""
        minimal_route = self._minimal_route(mission)
        extended_route = self._extended_route(mission)
        aggressive_route = self._aggressive_route(mission)

        plan_a = CandidatePlan(
            plan_id=self._plan_id_from_label("Minimal Survey"),
            label="Minimal Survey",
            description="Conservative return to base with minimal science stops",
            waypoints=minimal_route,
            science_yield_score=45.0,
            predicted_return_battery_pct=predict_return_battery_pct(
                mission.resources.battery_pct,
                MissionRoute(waypoints=minimal_route),
            ),
            status=PlanStatus.VALID,
            violations=[],
            is_recommended=False,
            rank=2,
        )

        plan_b = CandidatePlan(
            plan_id=self._plan_id_from_label("Extended Survey"),
            label="Extended Survey",
            description="Full science survey with optimal resource management",
            waypoints=extended_route,
            science_yield_score=78.0,
            predicted_return_battery_pct=predict_return_battery_pct(
                mission.resources.battery_pct,
                MissionRoute(waypoints=extended_route),
            ),
            status=PlanStatus.VALID,
            violations=[],
            is_recommended=True,
            rank=1,
        )

        plan_c = CandidatePlan(
            plan_id=self._plan_id_from_label("Aggressive Survey"),
            label="Aggressive Survey",
            description="Extended science targets with aggressive resource usage",
            waypoints=aggressive_route,
            science_yield_score=92.0,
            predicted_return_battery_pct=predict_return_battery_pct(
                mission.resources.battery_pct,
                MissionRoute(waypoints=aggressive_route),
            ),
            status=PlanStatus.VALID,
            violations=[],
            is_recommended=False,
            rank=3,
        )

        return [plan_a, plan_b, plan_c]
