"""Telemetry service — deterministic telemetry generation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.schemas import RoverResources, TelemetrySample

if TYPE_CHECKING:
    from app.services.mission import MissionService


class TelemetryService:
    """Generates deterministic telemetry samples based on mission state."""

    # Resource consumption rates per ~2 second interval
    BATTERY_DRAIN_PER_TICK = 0.5  # % per tick
    STORAGE_INCREASE_PER_TICK = 0.3  # % per tick
    TEMP_DRIFT_PER_TICK = 0.1  # °C per tick (small drift)
    COMM_WINDOW_DRAIN_PER_TICK = 2  # seconds per tick
    OP_TIME_DRAIN_PER_TICK = 2  # seconds per tick

    # Seed values from get_seed_mission()
    SEED_BATTERY_PCT = 100.0
    SEED_STORAGE_PCT = 0.0
    SEED_TEMP_C = -40.0
    SEED_COMM_WINDOW_S = 7200
    SEED_OP_TIME_S = 28800

    def __init__(self, mission_service: MissionService) -> None:
        self._mission_service = mission_service
        self._tick_count = 0

    def generate_sample(self) -> TelemetrySample | None:
        """Generate a telemetry sample if mission is active."""
        mission = self._mission_service.get_mission()

        # Only emit during RUNNING or EXECUTING
        if mission.status not in (mission.status.RUNNING, mission.status.EXECUTING):
            self._tick_count = 0
            return None

        # Compute deterministic values based on tick count
        # Do NOT mutate mission state
        self._tick_count += 1
        tick = self._tick_count

        elapsed_s = tick * 2
        new_battery = max(
            0.0, self.SEED_BATTERY_PCT - self.BATTERY_DRAIN_PER_TICK * tick
        )
        new_storage = min(
            100.0, self.SEED_STORAGE_PCT + self.STORAGE_INCREASE_PER_TICK * tick
        )
        new_temp = self.SEED_TEMP_C + self.TEMP_DRIFT_PER_TICK * tick
        new_comm = max(
            0, self.SEED_COMM_WINDOW_S - self.COMM_WINDOW_DRAIN_PER_TICK * tick
        )
        new_op_time = max(0, self.SEED_OP_TIME_S - self.OP_TIME_DRAIN_PER_TICK * tick)

        updated_resources = RoverResources(
            battery_pct=new_battery,
            storage_pct=new_storage,
            temperature_c=new_temp,
            comm_window_remaining_s=new_comm,
            op_time_remaining_s=new_op_time,
        )

        return TelemetrySample(
            mission_id=mission.mission_id,
            elapsed_s=elapsed_s,
            resources=updated_resources,
            timestamp=datetime.now(UTC),
        )

    def reset_tick_count(self) -> None:
        """Reset tick counter (called on mission reset)."""
        self._tick_count = 0
