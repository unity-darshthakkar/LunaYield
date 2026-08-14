"""Anomaly Detection Service — deterministic anomaly detection.

Provides deterministic detection of resource anomalies based on current mission state
and/or deterministic forecast output. Does not mutate mission state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.schemas import (
    AnomalyDetectionResponse,
    AnomalyFinding,
    AnomalyResource,
    AnomalySeverity,
)

if TYPE_CHECKING:
    from app.services.forecasting import ForecastingService
    from app.services.mission import MissionService


class AnomalyDetectionService:
    """Detects anomalies in mission resources using deterministic rules.

    Checks current resource levels and optionally forecasted levels against
    predefined thresholds. Does not mutate mission state.
    """

    # Thresholds for anomaly detection
    BATTERY_CRITICAL_PCT = 10.0
    BATTERY_WARNING_PCT = 25.0
    STORAGE_CRITICAL_PCT = 95.0
    STORAGE_WARNING_PCT = 85.0
    TEMPERATURE_CRITICAL_MIN_C = -50.0
    TEMPERATURE_WARNING_MIN_C = -45.0
    TEMPERATURE_CRITICAL_MAX_C = 50.0
    TEMPERATURE_WARNING_MAX_C = 40.0
    COMM_WINDOW_CRITICAL_S = 300  # 5 minutes
    COMM_WINDOW_WARNING_S = 900  # 15 minutes
    OP_TIME_CRITICAL_S = 600  # 10 minutes
    OP_TIME_WARNING_S = 1800  # 30 minutes

    def __init__(
        self,
        mission_service: MissionService,
        forecasting_service: ForecastingService | None = None,
    ) -> None:
        """Initialize with mission service and optional forecasting service.

        Args:
            mission_service: The mission service providing access
                to current state.
            forecasting_service: Optional forecasting service for
                forecast-based detection.
        """
        self._mission_service = mission_service
        self._forecasting_service = forecasting_service

    def detect_anomalies(
        self, use_forecast: bool = False, forecast_horizon_s: int = 3600
    ) -> AnomalyDetectionResponse:
        """Detect anomalies in current mission resources.

        Args:
            use_forecast: If True, also check forecasted resource levels
                for anomalies.
            forecast_horizon_s: How far into the future to check (when
                use_forecast is True).

        Returns:
            AnomalyDetectionResponse containing all detected anomalies.
        """
        mission = self._mission_service.get_mission()
        current_resources = mission.resources
        current_elapsed_s = mission.elapsed_s

        anomalies: list[AnomalyFinding] = []

        # Check current resource levels
        anomalies.extend(self._check_battery(current_resources.battery_pct))
        anomalies.extend(self._check_storage(current_resources.storage_pct))
        anomalies.extend(self._check_temperature(current_resources.temperature_c))
        anomalies.extend(
            self._check_comm_window(current_resources.comm_window_remaining_s)
        )
        anomalies.extend(self._check_op_time(current_resources.op_time_remaining_s))

        # Optionally check forecasted resources
        if use_forecast and self._forecasting_service is not None:
            forecast = self._forecasting_service.generate_forecast(
                forecast_horizon_s=forecast_horizon_s,
                forecast_tick_interval_s=60,
            )
            for point in forecast.forecast_points:
                ahead_s = point.forecast_seconds_ahead
                anomalies.extend(
                    self._check_battery(
                        point.resources.battery_pct,
                        forecast=True,
                        forecast_seconds_ahead=ahead_s,
                    )
                )
                anomalies.extend(
                    self._check_storage(
                        point.resources.storage_pct,
                        forecast=True,
                        forecast_seconds_ahead=ahead_s,
                    )
                )
                anomalies.extend(
                    self._check_temperature(
                        point.resources.temperature_c,
                        forecast=True,
                        forecast_seconds_ahead=ahead_s,
                    )
                )
                anomalies.extend(
                    self._check_comm_window(
                        point.resources.comm_window_remaining_s,
                        forecast=True,
                        forecast_seconds_ahead=ahead_s,
                    )
                )
                anomalies.extend(
                    self._check_op_time(
                        point.resources.op_time_remaining_s,
                        forecast=True,
                        forecast_seconds_ahead=ahead_s,
                    )
                )

        # Deduplicate: keep most severe for each resource
        anomalies = self._deduplicate_anomalies(anomalies)

        # Count severities
        has_critical = any(a.severity == AnomalySeverity.CRITICAL for a in anomalies)
        has_warning = any(a.severity == AnomalySeverity.WARNING for a in anomalies)

        return AnomalyDetectionResponse(
            mission_id=mission.mission_id,
            current_elapsed_s=current_elapsed_s,
            anomalies=anomalies,
            anomaly_count=len(anomalies),
            has_critical=has_critical,
            has_warning=has_warning,
        )

    def _check_battery(
        self,
        battery_pct: float,
        forecast: bool = False,
        forecast_seconds_ahead: int | None = None,
    ) -> list[AnomalyFinding]:
        """Check battery level against thresholds."""
        anomalies: list[AnomalyFinding] = []

        if battery_pct <= self.BATTERY_CRITICAL_PCT:
            anomalies.append(
                AnomalyFinding(
                    resource=AnomalyResource.BATTERY,
                    severity=AnomalySeverity.CRITICAL,
                    observed_value=round(battery_pct, 1),
                    threshold_value=self.BATTERY_CRITICAL_PCT,
                    reason=(
                        f"Battery critically low at {battery_pct:.1f}% "
                        f"(threshold: {self.BATTERY_CRITICAL_PCT}%)"
                        + (" (forecast)" if forecast else "")
                    ),
                    is_forecast=forecast,
                    forecast_seconds_ahead=forecast_seconds_ahead,
                )
            )
        elif battery_pct <= self.BATTERY_WARNING_PCT:
            anomalies.append(
                AnomalyFinding(
                    resource=AnomalyResource.BATTERY,
                    severity=AnomalySeverity.WARNING,
                    observed_value=round(battery_pct, 1),
                    threshold_value=self.BATTERY_WARNING_PCT,
                    reason=(
                        f"Battery low at {battery_pct:.1f}% "
                        f"(threshold: {self.BATTERY_WARNING_PCT}%)"
                        + (" (forecast)" if forecast else "")
                    ),
                    is_forecast=forecast,
                    forecast_seconds_ahead=forecast_seconds_ahead,
                )
            )

        return anomalies

    def _check_storage(
        self,
        storage_pct: float,
        forecast: bool = False,
        forecast_seconds_ahead: int | None = None,
    ) -> list[AnomalyFinding]:
        """Check storage usage against thresholds."""
        anomalies: list[AnomalyFinding] = []

        if storage_pct >= self.STORAGE_CRITICAL_PCT:
            anomalies.append(
                AnomalyFinding(
                    resource=AnomalyResource.STORAGE,
                    severity=AnomalySeverity.CRITICAL,
                    observed_value=round(storage_pct, 1),
                    threshold_value=self.STORAGE_CRITICAL_PCT,
                    reason=(
                        f"Storage critically full at {storage_pct:.1f}% "
                        f"(threshold: {self.STORAGE_CRITICAL_PCT}%)"
                        + (" (forecast)" if forecast else "")
                    ),
                    is_forecast=forecast,
                    forecast_seconds_ahead=forecast_seconds_ahead,
                )
            )
        elif storage_pct >= self.STORAGE_WARNING_PCT:
            anomalies.append(
                AnomalyFinding(
                    resource=AnomalyResource.STORAGE,
                    severity=AnomalySeverity.WARNING,
                    observed_value=round(storage_pct, 1),
                    threshold_value=self.STORAGE_WARNING_PCT,
                    reason=(
                        f"Storage high at {storage_pct:.1f}% "
                        f"(threshold: {self.STORAGE_WARNING_PCT}%)"
                        + (" (forecast)" if forecast else "")
                    ),
                    is_forecast=forecast,
                    forecast_seconds_ahead=forecast_seconds_ahead,
                )
            )

        return anomalies

    def _check_temperature(
        self,
        temperature_c: float,
        forecast: bool = False,
        forecast_seconds_ahead: int | None = None,
    ) -> list[AnomalyFinding]:
        """Check temperature against thresholds."""
        anomalies: list[AnomalyFinding] = []

        # Check cold thresholds
        if temperature_c <= self.TEMPERATURE_CRITICAL_MIN_C:
            anomalies.append(
                AnomalyFinding(
                    resource=AnomalyResource.TEMPERATURE,
                    severity=AnomalySeverity.CRITICAL,
                    observed_value=round(temperature_c, 1),
                    threshold_value=self.TEMPERATURE_CRITICAL_MIN_C,
                    reason=(
                        f"Temperature critically low at {temperature_c:.1f}°C "
                        f"(threshold: {self.TEMPERATURE_CRITICAL_MIN_C}°C)"
                        + (" (forecast)" if forecast else "")
                    ),
                    is_forecast=forecast,
                    forecast_seconds_ahead=forecast_seconds_ahead,
                )
            )
        elif temperature_c <= self.TEMPERATURE_WARNING_MIN_C:
            anomalies.append(
                AnomalyFinding(
                    resource=AnomalyResource.TEMPERATURE,
                    severity=AnomalySeverity.WARNING,
                    observed_value=round(temperature_c, 1),
                    threshold_value=self.TEMPERATURE_WARNING_MIN_C,
                    reason=(
                        f"Temperature low at {temperature_c:.1f}°C "
                        f"(threshold: {self.TEMPERATURE_WARNING_MIN_C}°C)"
                        + (" (forecast)" if forecast else "")
                    ),
                    is_forecast=forecast,
                    forecast_seconds_ahead=forecast_seconds_ahead,
                )
            )

        # Check hot thresholds
        if temperature_c >= self.TEMPERATURE_CRITICAL_MAX_C:
            anomalies.append(
                AnomalyFinding(
                    resource=AnomalyResource.TEMPERATURE,
                    severity=AnomalySeverity.CRITICAL,
                    observed_value=round(temperature_c, 1),
                    threshold_value=self.TEMPERATURE_CRITICAL_MAX_C,
                    reason=(
                        f"Temperature critically high at {temperature_c:.1f}°C "
                        f"(threshold: {self.TEMPERATURE_CRITICAL_MAX_C}°C)"
                        + (" (forecast)" if forecast else "")
                    ),
                    is_forecast=forecast,
                    forecast_seconds_ahead=forecast_seconds_ahead,
                )
            )
        elif temperature_c >= self.TEMPERATURE_WARNING_MAX_C:
            anomalies.append(
                AnomalyFinding(
                    resource=AnomalyResource.TEMPERATURE,
                    severity=AnomalySeverity.WARNING,
                    observed_value=round(temperature_c, 1),
                    threshold_value=self.TEMPERATURE_WARNING_MAX_C,
                    reason=(
                        f"Temperature high at {temperature_c:.1f}°C "
                        f"(threshold: {self.TEMPERATURE_WARNING_MAX_C}°C)"
                        + (" (forecast)" if forecast else "")
                    ),
                    is_forecast=forecast,
                    forecast_seconds_ahead=forecast_seconds_ahead,
                )
            )

        return anomalies

    def _check_comm_window(
        self,
        comm_window_s: int,
        forecast: bool = False,
        forecast_seconds_ahead: int | None = None,
    ) -> list[AnomalyFinding]:
        """Check communications window against thresholds."""
        anomalies: list[AnomalyFinding] = []

        if comm_window_s <= self.COMM_WINDOW_CRITICAL_S:
            anomalies.append(
                AnomalyFinding(
                    resource=AnomalyResource.COMM_WINDOW,
                    severity=AnomalySeverity.CRITICAL,
                    observed_value=comm_window_s,
                    threshold_value=self.COMM_WINDOW_CRITICAL_S,
                    reason=(
                        f"Comms window critically short at {comm_window_s}s "
                        f"(threshold: {self.COMM_WINDOW_CRITICAL_S}s)"
                        + (" (forecast)" if forecast else "")
                    ),
                    is_forecast=forecast,
                    forecast_seconds_ahead=forecast_seconds_ahead,
                )
            )
        elif comm_window_s <= self.COMM_WINDOW_WARNING_S:
            anomalies.append(
                AnomalyFinding(
                    resource=AnomalyResource.COMM_WINDOW,
                    severity=AnomalySeverity.WARNING,
                    observed_value=comm_window_s,
                    threshold_value=self.COMM_WINDOW_WARNING_S,
                    reason=(
                        f"Comms window short at {comm_window_s}s "
                        f"(threshold: {self.COMM_WINDOW_WARNING_S}s)"
                        + (" (forecast)" if forecast else "")
                    ),
                    is_forecast=forecast,
                    forecast_seconds_ahead=forecast_seconds_ahead,
                )
            )

        return anomalies

    def _check_op_time(
        self,
        op_time_s: int,
        forecast: bool = False,
        forecast_seconds_ahead: int | None = None,
    ) -> list[AnomalyFinding]:
        """Check operational time remaining against thresholds."""
        anomalies: list[AnomalyFinding] = []

        if op_time_s <= self.OP_TIME_CRITICAL_S:
            anomalies.append(
                AnomalyFinding(
                    resource=AnomalyResource.OP_TIME,
                    severity=AnomalySeverity.CRITICAL,
                    observed_value=op_time_s,
                    threshold_value=self.OP_TIME_CRITICAL_S,
                    reason=(
                        f"Operational time critically low at {op_time_s}s "
                        f"(threshold: {self.OP_TIME_CRITICAL_S}s)"
                        + (" (forecast)" if forecast else "")
                    ),
                    is_forecast=forecast,
                    forecast_seconds_ahead=forecast_seconds_ahead,
                )
            )
        elif op_time_s <= self.OP_TIME_WARNING_S:
            anomalies.append(
                AnomalyFinding(
                    resource=AnomalyResource.OP_TIME,
                    severity=AnomalySeverity.WARNING,
                    observed_value=op_time_s,
                    threshold_value=self.OP_TIME_WARNING_S,
                    reason=(
                        f"Operational time low at {op_time_s}s "
                        f"(threshold: {self.OP_TIME_WARNING_S}s)"
                        + (" (forecast)" if forecast else "")
                    ),
                    is_forecast=forecast,
                    forecast_seconds_ahead=forecast_seconds_ahead,
                )
            )

        return anomalies

    def _deduplicate_anomalies(
        self, anomalies: list[AnomalyFinding]
    ) -> list[AnomalyFinding]:
        """Deduplicate anomalies by resource, keeping the most severe.

        Tie-breaking rules:
        1. Higher severity wins (CRITICAL > WARNING > INFO)
        2. For equal severity: current-state (is_forecast=False) wins over forecast
        3. For equal severity forecast findings: earliest threshold crossing wins
        """
        severity_order = {
            AnomalySeverity.INFO: 0,
            AnomalySeverity.WARNING: 1,
            AnomalySeverity.CRITICAL: 2,
        }

        # Group by resource
        by_resource: dict[AnomalyResource, list[AnomalyFinding]] = {}
        for anomaly in anomalies:
            if anomaly.resource not in by_resource:
                by_resource[anomaly.resource] = []
            by_resource[anomaly.resource].append(anomaly)

        # Keep only the most severe for each resource with tie-breaking
        result = []
        for resource, resource_anomalies in by_resource.items():
            # Sort by: severity desc, is_forecast asc (False first),
            # forecast_seconds_ahead asc
            resource_anomalies.sort(
                key=lambda a: (
                    -severity_order.get(a.severity, 0),
                    a.is_forecast,
                    a.forecast_seconds_ahead
                    if a.forecast_seconds_ahead is not None
                    else 0,
                )
            )
            result.append(resource_anomalies[0])

        # Sort by resource for consistent output
        result.sort(key=lambda a: a.resource.value)

        return result
