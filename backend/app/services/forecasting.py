"""Forecasting service — deterministic resource forecasting.

Provides deterministic forecasts of mission resource levels based on current state
and historical consumption patterns. Does not mutate mission state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.schemas import (
    ForecastPoint,
    MissionForecastResponse,
    ResourceForecast,
)

if TYPE_CHECKING:
    from app.services.mission import MissionService


class ForecastingService:
    """Generates deterministic resource forecasts based on mission state.

    Uses the same deterministic patterns as TelemetryService to forecast
    future resource levels without mutating mission state.
    """

    # Resource consumption rates per ~2 second interval (matching TelemetryService)
    BATTERY_DRAIN_PER_TICK = 0.5  # % per tick
    STORAGE_INCREASE_PER_TICK = 0.3  # % per tick
    TEMP_DRIFT_PER_TICK = 0.1  # °C per tick (small drift)
    COMM_WINDOW_DRAIN_PER_TICK = 2  # seconds per tick
    OP_TIME_DRAIN_PER_TICK = 2  # seconds per tick

    # Tick duration in seconds
    TICK_DURATION_S = 2

    def __init__(self, mission_service: MissionService) -> None:
        """Initialize with mission service dependency.

        Args:
            mission_service: The mission service providing access to current state.
        """
        self._mission_service = mission_service

    def generate_forecast(
        self, forecast_horizon_s: int = 3600, forecast_tick_interval_s: int = 60
    ) -> MissionForecastResponse:
        """Generate a deterministic forecast of mission resources.

        Args:
            forecast_horizon_s: How far into the future to forecast (seconds).
            forecast_tick_interval_s: Interval between forecast points (seconds).

        Returns:
            MissionForecastResponse containing current state and forecast points.
        """
        mission = self._mission_service.get_mission()
        current_elapsed_s = mission.elapsed_s
        current_resources = mission.resources

        # Validate inputs
        if forecast_horizon_s <= 0:
            raise ValueError("forecast_horizon_s must be positive")
        if forecast_tick_interval_s <= 0:
            raise ValueError("forecast_tick_interval_s must be positive")
        if forecast_tick_interval_s > forecast_horizon_s:
            raise ValueError(
                "forecast_tick_interval_s cannot exceed forecast_horizon_s"
            )

        # Generate forecast points at each interval
        forecast_points = []
        for future_tick in range(
            forecast_tick_interval_s,  # Start from the first interval
            forecast_horizon_s + 1,  # Go to horizon (inclusive)
            forecast_tick_interval_s,
        ):
            # Calculate future ticks from now
            future_ticks = future_tick // self.TICK_DURATION_S
            forecast_elapsed_s = current_elapsed_s + future_tick

            # Calculate forecasted resources based on current state + future changes
            forecast_battery = max(
                0.0,
                min(
                    100.0,
                    current_resources.battery_pct
                    - self.BATTERY_DRAIN_PER_TICK * future_ticks,
                ),
            )
            forecast_storage = max(
                0.0,
                min(
                    100.0,
                    current_resources.storage_pct
                    + self.STORAGE_INCREASE_PER_TICK * future_ticks,
                ),
            )
            forecast_temperature = current_resources.temperature_c + (
                self.TEMP_DRIFT_PER_TICK * future_ticks
            )
            forecast_comm_window = max(
                0,
                current_resources.comm_window_remaining_s
                - self.COMM_WINDOW_DRAIN_PER_TICK * future_ticks,
            )
            forecast_op_time = max(
                0,
                current_resources.op_time_remaining_s
                - self.OP_TIME_DRAIN_PER_TICK * future_ticks,
            )

            forecast_resources = ResourceForecast(
                battery_pct=round(forecast_battery, 1),
                storage_pct=round(forecast_storage, 1),
                temperature_c=round(forecast_temperature, 1),
                comm_window_remaining_s=forecast_comm_window,
                op_time_remaining_s=forecast_op_time,
            )

            forecast_point = ForecastPoint(
                forecast_seconds_ahead=future_tick,
                elapsed_s=forecast_elapsed_s,
                resources=forecast_resources,
            )
            forecast_points.append(forecast_point)

        return MissionForecastResponse(
            mission_id=mission.mission_id,
            current_elapsed_s=current_elapsed_s,
            current_resources=current_resources,
            forecast_horizon_s=forecast_horizon_s,
            forecast_tick_interval_s=forecast_tick_interval_s,
            forecast_points=forecast_points,
        )
