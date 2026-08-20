"""Pure helpers for authoritative route progression state."""

from __future__ import annotations

from collections.abc import Iterable

from app.schemas import MissionRoute, RouteWaypoint, WaypointProgressStatus

MISSION_TICK_SECONDS = 2
NOMINAL_BATTERY_DRAIN_PER_TICK = 0.5
ANOMALY_IMMEDIATE_BATTERY_LOSS_PCT = 5.0

NOMINAL_SEGMENT_DURATION_S: dict[str, int] = {
    "wp-crater-a": 56,
    "wp-ice-deposit": 72,
    "wp-ridge": 88,
    "wp-return": 80,
    "wp-extra-crater": 24,
    "wp-return-2": 18,
}

MINIMAL_DIRECT_RETURN_DURATION_S = 132

SCIENCE_STORAGE_GAIN_PCT: dict[str, float] = {
    "wp-crater-a": 33.0,
    "wp-ice-deposit": 33.0,
    "wp-ridge": 34.0,
    "wp-extra-crater": 16.0,
}


def clone_waypoints(waypoints: Iterable[RouteWaypoint]) -> list[RouteWaypoint]:
    """Return detached waypoint copies."""
    return [waypoint.model_copy(deep=True) for waypoint in waypoints]


def build_initialized_route(waypoints: Iterable[RouteWaypoint]) -> MissionRoute:
    """Return a route with the first waypoint current and the rest upcoming."""
    normalized = clone_waypoints(waypoints)
    for index, waypoint in enumerate(normalized):
        waypoint.progress_status = (
            WaypointProgressStatus.CURRENT
            if index == 0
            else WaypointProgressStatus.UPCOMING
        )
        waypoint.segment_elapsed_s = 0
        waypoint.science_collected = False
    return MissionRoute(waypoints=normalized)


def first_current_index(route: MissionRoute) -> int | None:
    """Return the current waypoint index, if any."""
    for index, waypoint in enumerate(route.waypoints):
        if waypoint.progress_status == WaypointProgressStatus.CURRENT:
            return index
    return None


def next_upcoming_index(route: MissionRoute, *, after_index: int) -> int | None:
    """Return the next upcoming waypoint after a given index."""
    for index in range(after_index + 1, len(route.waypoints)):
        if route.waypoints[index].progress_status == WaypointProgressStatus.UPCOMING:
            return index
    return None


def previous_non_skipped_index(route: MissionRoute, *, before_index: int) -> int | None:
    """Return the previous non-skipped waypoint index before a given index."""
    for index in range(before_index - 1, -1, -1):
        if route.waypoints[index].progress_status != WaypointProgressStatus.SKIPPED:
            return index
    return None


def segment_duration_s(route: MissionRoute, current_index: int) -> int:
    """Return the configured segment duration for a waypoint in route context."""
    waypoint = route.waypoints[current_index]
    if waypoint.id == "wp-return":
        previous_index = previous_non_skipped_index(route, before_index=current_index)
        if previous_index is not None:
            previous_waypoint = route.waypoints[previous_index]
            if previous_waypoint.id == "wp-ice-deposit":
                ridge_waypoint = next(
                    (
                        candidate
                        for candidate in route.waypoints
                        if candidate.id == "wp-ridge"
                    ),
                    None,
                )
                if (
                    ridge_waypoint is not None
                    and ridge_waypoint.progress_status == WaypointProgressStatus.SKIPPED
                ):
                    return MINIMAL_DIRECT_RETURN_DURATION_S
    return NOMINAL_SEGMENT_DURATION_S.get(waypoint.id, 48)


def science_storage_gain_pct(waypoint: RouteWaypoint) -> float:
    """Return the one-time deterministic storage gain for a science waypoint."""
    return SCIENCE_STORAGE_GAIN_PCT.get(waypoint.id, 0.0)


def all_science_targets_collected(route: MissionRoute) -> bool:
    """Return True when every science waypoint in the route is complete."""
    science_waypoints = [
        waypoint for waypoint in route.waypoints if waypoint.is_science_target
    ]
    if not science_waypoints:
        return False
    return all(waypoint.science_collected for waypoint in science_waypoints)


def remaining_route_ticks(route: MissionRoute) -> int:
    """Return deterministic remaining mission ticks for the active route."""
    ticks = 0
    for index, waypoint in enumerate(route.waypoints):
        if waypoint.progress_status in (
            WaypointProgressStatus.COMPLETED,
            WaypointProgressStatus.SKIPPED,
        ):
            continue

        duration_s = segment_duration_s(route, index)
        if waypoint.progress_status == WaypointProgressStatus.CURRENT:
            remaining_s = max(0, duration_s - waypoint.segment_elapsed_s)
        else:
            remaining_s = duration_s

        ticks += remaining_s // MISSION_TICK_SECONDS
    return ticks


def predict_return_battery_pct(
    current_battery_pct: float, route: MissionRoute
) -> float:
    """Predict return battery from deterministic route assumptions."""
    predicted = current_battery_pct - (
        remaining_route_ticks(route) * NOMINAL_BATTERY_DRAIN_PER_TICK
    )
    return round(max(0.0, predicted), 1)
