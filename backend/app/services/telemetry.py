"""Telemetry service — deterministic telemetry generation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.schemas import (
    MissionStatus,
    RoverResources,
    TelemetrySample,
    WaypointProgressStatus,
)
from app.services.anomaly import AnomalyDetectionService
from app.services.route_progress import (
    first_current_index,
    next_upcoming_index,
    science_storage_gain_pct,
    segment_duration_s,
)

if TYPE_CHECKING:
    from app.services.mission import MissionService


class TelemetryService:
    """Generates deterministic telemetry samples based on mission state."""

    TICK_SECONDS = 2
    BATTERY_DRAIN_PER_TICK = 0.5
    TEMP_DRIFT_PER_TICK = 0.1
    COMM_WINDOW_DRAIN_PER_TICK = 2
    OP_TIME_DRAIN_PER_TICK = 2

    def __init__(self, mission_service: MissionService) -> None:
        self._mission_service = mission_service

    def _build_sample(self) -> TelemetrySample:
        mission = self._mission_service.get_mission()
        return TelemetrySample(
            mission_id=mission.mission_id,
            elapsed_s=mission.elapsed_s,
            resources=mission.resources.model_copy(),
            timestamp=datetime.now(UTC),
        )

    def generate_sample(self) -> TelemetrySample | None:
        """Generate a telemetry sample if mission is active."""
        mission = self._mission_service.get_mission()

        if mission.status not in (MissionStatus.RUNNING, MissionStatus.EXECUTING):
            return None

        current_index = first_current_index(mission.active_route)
        if current_index is None:
            self._mission_service.complete_mission()
            return self._build_sample()

        mission.elapsed_s += self.TICK_SECONDS
        current_waypoint = mission.active_route.waypoints[current_index]
        current_waypoint.segment_elapsed_s += self.TICK_SECONDS

        mission.resources = RoverResources(
            battery_pct=max(
                0.0,
                round(
                    mission.resources.battery_pct - self.BATTERY_DRAIN_PER_TICK,
                    1,
                ),
            ),
            storage_pct=mission.resources.storage_pct,
            temperature_c=round(
                mission.resources.temperature_c + self.TEMP_DRIFT_PER_TICK,
                1,
            ),
            comm_window_remaining_s=max(
                0,
                mission.resources.comm_window_remaining_s
                - self.COMM_WINDOW_DRAIN_PER_TICK,
            ),
            op_time_remaining_s=max(
                0,
                mission.resources.op_time_remaining_s - self.OP_TIME_DRAIN_PER_TICK,
            ),
        )

        if (
            mission.resources.battery_pct
            <= AnomalyDetectionService.BATTERY_CRITICAL_PCT
        ):
            self._mission_service.trigger_resource_anomaly(
                resource="BATTERY",
                description=(
                    "Battery critically low during mission execution; "
                    "transitioned to anomaly handling"
                ),
                observed_value=mission.resources.battery_pct,
                threshold_value=AnomalyDetectionService.BATTERY_CRITICAL_PCT,
            )
            return self._build_sample()

        if current_waypoint.segment_elapsed_s >= segment_duration_s(
            mission.active_route, current_index
        ):
            current_waypoint.progress_status = WaypointProgressStatus.COMPLETED
            self._mission_service.record_event(
                "waypoint.reached",
                f"Reached {current_waypoint.label}",
                {"waypoint_id": current_waypoint.id, "elapsed_s": mission.elapsed_s},
            )

            if (
                current_waypoint.is_science_target
                and not current_waypoint.science_collected
            ):
                storage_gain = science_storage_gain_pct(current_waypoint)
                mission.resources.storage_pct = min(
                    100.0,
                    round(mission.resources.storage_pct + storage_gain, 1),
                )
                current_waypoint.science_collected = True
                self._mission_service.record_event(
                    "science.collected",
                    f"Science collection completed at {current_waypoint.label}",
                    {
                        "waypoint_id": current_waypoint.id,
                        "storage_pct": mission.resources.storage_pct,
                        "storage_gain_pct": storage_gain,
                    },
                )

            next_index = next_upcoming_index(
                mission.active_route,
                after_index=current_index,
            )
            if next_index is not None:
                mission.active_route.waypoints[
                    next_index
                ].progress_status = WaypointProgressStatus.CURRENT
            else:
                self._mission_service.complete_mission()

        return self._build_sample()

    def reset_tick_count(self) -> None:
        """Preserved for compatibility with existing reset wiring."""
        return None
