"""Strategy Service — deterministic mission strategy generation.

Generates structured, reviewable strategy candidates from mission state,
forecast, and anomaly findings. Does not mutate mission state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.schemas import (
    AnomalyResource,
    AnomalySeverity,
    StrategyCandidate,
    StrategyGenerationResponse,
)

if TYPE_CHECKING:
    from app.services.anomaly import AnomalyDetectionService
    from app.services.forecasting import ForecastingService
    from app.services.mission import MissionService


class StrategyService:
    """Generates deterministic mission strategy candidates.

    Consumes authoritative MissionService state, ForecastingService output,
    and AnomalyDetectionService findings to produce structured strategy
    recommendations. All strategies are read-only and require operator approval.
    """

    def __init__(
        self,
        mission_service: MissionService,
        forecasting_service: ForecastingService,
        anomaly_service: AnomalyDetectionService,
    ) -> None:
        """Initialize with required service dependencies.

        Args:
            mission_service: Provides authoritative current mission state.
            forecasting_service: Provides deterministic future projections.
            anomaly_service: Provides current and forecast anomaly findings.
        """
        self._mission_service = mission_service
        self._forecasting_service = forecasting_service
        self._anomaly_service = anomaly_service

    def generate_strategies(
        self, use_forecast: bool = False, forecast_horizon_s: int = 3600
    ) -> StrategyGenerationResponse:
        """Generate strategy candidates for current mission state.

        Args:
            use_forecast: If True, include forecast-based anomalies
                in analysis.
            forecast_horizon_s: How far into the future to check
                (when use_forecast=True).

        Returns:
            StrategyGenerationResponse with prioritized strategy candidates.
        """
        mission = self._mission_service.get_mission()

        # Get anomalies (current + optional forecast)
        anomalies_response = self._anomaly_service.detect_anomalies(
            use_forecast=use_forecast, forecast_horizon_s=forecast_horizon_s
        )

        # Generate one strategy per unique anomaly resource+severity
        # (AnomalyDetectionService dedups by resource, keeping most severe)
        strategies: list[StrategyCandidate] = []

        for anomaly in anomalies_response.anomalies:
            candidate = self._create_strategy_for_anomaly(anomaly)
            if candidate:
                # Validate through Pydantic (catches any generation bugs)
                try:
                    validated = StrategyCandidate.model_validate(candidate.model_dump())
                    strategies.append(validated)
                except Exception:
                    # Invalid candidate rejected - never becomes recommended strategy
                    # In production, this would be logged
                    pass

        # Deduplicate: keep highest priority for same affected resource set
        strategies = self._deduplicate_strategies(strategies)

        # Sort by priority (1=highest first), then by title for determinism
        strategies.sort(key=lambda s: (s.priority, s.title))

        has_critical = any(s.priority == 1 for s in strategies)

        return StrategyGenerationResponse(
            mission_id=mission.mission_id,
            current_elapsed_s=mission.elapsed_s,
            strategies=strategies,
            strategy_count=len(strategies),
            has_critical_priority=has_critical,
        )

    def _create_strategy_for_anomaly(self, anomaly) -> StrategyCandidate | None:
        """Create a deterministic strategy candidate for a single anomaly.

        Args:
            anomaly: An AnomalyFinding from AnomalyDetectionService.

        Returns:
            StrategyCandidate or None if no strategy maps to this anomaly.
        """
        resource = anomaly.resource
        severity = anomaly.severity
        forecast_suffix = " (forecast)" if anomaly.is_forecast else ""

        # Map anomaly to strategy template
        strategy_map = {
            (AnomalyResource.BATTERY, AnomalySeverity.CRITICAL): {
                "title": "Conserve Power",
                "rationale": (
                    f"Battery critically low at {anomaly.observed_value}% (threshold: "
                    f"{anomaly.threshold_value}%){forecast_suffix}. Immediate power "
                    f"conservation required to maintain critical systems."
                ),
                "priority": 1,
                "actions": [
                    "Disable non-essential science instruments",
                    "Reduce communication frequency",
                    "Orient solar panels for maximum charging",
                    "Enter low-power safe mode if below 5%",
                ],
            },
            (AnomalyResource.BATTERY, AnomalySeverity.WARNING): {
                "title": "Monitor Power",
                "rationale": (
                    f"Battery low at {anomaly.observed_value}% (threshold: "
                    f"{anomaly.threshold_value}%){forecast_suffix}. Proactive power "
                    f"management recommended to avoid critical depletion."
                ),
                "priority": 2,
                "actions": [
                    "Reduce science duty cycle by 50%",
                    "Schedule high-power activities during peak sun",
                    "Plan recharge stop at next sunlit waypoint",
                    "Monitor battery trend every 30 minutes",
                ],
            },
            (AnomalyResource.STORAGE, AnomalySeverity.CRITICAL): {
                "title": "Offload Data",
                "rationale": (
                    f"Storage critically full at {anomaly.observed_value}% (threshold: "
                    f"{anomaly.threshold_value}%){forecast_suffix}. Immediate data "
                    f"offload required to prevent data loss."
                ),
                "priority": 1,
                "actions": [
                    "Prioritize downlink during next comms window",
                    "Compress and queue all science data for transmission",
                    "Delete non-essential cached thumbnails",
                    "Suspend new data collection until offload complete",
                ],
            },
            (AnomalyResource.STORAGE, AnomalySeverity.WARNING): {
                "title": "Schedule Downlink",
                "rationale": (
                    f"Storage high at {anomaly.observed_value}% (threshold: "
                    f"{anomaly.threshold_value}%){forecast_suffix}. Plan data "
                    f"offload before storage becomes critical."
                ),
                "priority": 2,
                "actions": [
                    "Schedule downlink at next available comms window",
                    "Enable data compression for new collections",
                    "Archive completed science targets",
                    "Monitor storage growth rate",
                ],
            },
            (AnomalyResource.TEMPERATURE, AnomalySeverity.CRITICAL): {
                "title": "Thermal Protection",
                "rationale": (
                    f"Temperature critically "
                    f"{'low' if anomaly.observed_value < 0 else 'high'} "
                    f"at {anomaly.observed_value}°C "
                    f"(threshold: {anomaly.threshold_value}°C)"
                    f"{forecast_suffix}. Thermal protection "
                    f"required to prevent hardware damage."
                ),
                "priority": 1,
                "actions": [
                    "Enter thermal safe mode immediately",
                    "Orient rover for passive thermal control",
                    "Disable heat-generating instruments",
                    "Monitor temperature every 5 minutes",
                ],
            },
            (AnomalyResource.TEMPERATURE, AnomalySeverity.WARNING): {
                "title": "Monitor Thermal",
                "rationale": (
                    f"Temperature "
                    f"{'low' if anomaly.observed_value < 0 else 'high'} "
                    f"at {anomaly.observed_value}°C "
                    f"(threshold: {anomaly.threshold_value}°C)"
                    f"{forecast_suffix}. Reduce thermal load to "
                    f"avoid critical threshold."
                ),
                "priority": 2,
                "actions": [
                    "Reduce instrument duty cycle by 30%",
                    "Adjust rover orientation for thermal management",
                    "Enable active thermal control if available",
                    "Monitor temperature trend every 15 minutes",
                ],
            },
            (AnomalyResource.COMM_WINDOW, AnomalySeverity.CRITICAL): {
                "title": "Prioritize Comms",
                "rationale": (
                    f"Comms window critically short at {anomaly.observed_value}s "
                    f"(threshold: {anomaly.threshold_value}s){forecast_suffix}. "
                    f"Critical data must be transmitted immediately."
                ),
                "priority": 1,
                "actions": [
                    "Transmit highest-priority science data first",
                    "Send health and safety telemetry immediately",
                    "Defer non-critical data to next window",
                    "Confirm receipt before window closes",
                ],
            },
            (AnomalyResource.COMM_WINDOW, AnomalySeverity.WARNING): {
                "title": "Plan Comms",
                "rationale": (
                    f"Comms window short at {anomaly.observed_value}s "
                    f"(threshold: {anomaly.threshold_value}s){forecast_suffix}. "
                    f"Plan data transmission to maximize window utilization."
                ),
                "priority": 2,
                "actions": [
                    "Queue data by priority for next comms window",
                    "Compress data to maximize throughput",
                    "Verify ground station availability",
                    "Monitor window duration trend",
                ],
            },
            (AnomalyResource.OP_TIME, AnomalySeverity.CRITICAL): {
                "title": "Expedite Return",
                "rationale": (
                    f"Operational time critically low at {anomaly.observed_value}s "
                    f"(threshold: {anomaly.threshold_value}s){forecast_suffix}. "
                    f"Must begin return to base immediately."
                ),
                "priority": 1,
                "actions": [
                    "Abort current science activity",
                    "Plot direct return route to base",
                    "Disable all non-essential systems",
                    "Transmit final position and status",
                ],
            },
            (AnomalyResource.OP_TIME, AnomalySeverity.WARNING): {
                "title": "Optimize Timeline",
                "rationale": (
                    f"Operational time low at {anomaly.observed_value}s "
                    f"(threshold: {anomaly.threshold_value}s){forecast_suffix}. "
                    f"Reorder activities to complete science before deadline."
                ),
                "priority": 2,
                "actions": [
                    "Reorder waypoints for efficient path",
                    "Reduce dwell time at remaining targets",
                    "Skip lowest-priority science targets",
                    "Verify return trajectory has margin",
                ],
            },
        }

        template = strategy_map.get((resource, severity))
        if not template:
            return None

        # Generate deterministic strategy ID
        source_id = f"{resource.value}-{severity.value}"
        if anomaly.is_forecast:
            source_id += f"-f{anomaly.forecast_seconds_ahead}"

        candidate = StrategyCandidate(
            strategy_id=f"strat-{source_id}",
            title=template["title"],
            rationale=template["rationale"],
            priority=template["priority"],
            affected_resources=[resource],
            recommended_actions=template["actions"],
            source_anomalies=[source_id],
            requires_operator_approval=True,
        )

        return candidate

    def _deduplicate_strategies(
        self, strategies: list[StrategyCandidate]
    ) -> list[StrategyCandidate]:
        """Deduplicate strategies by affected resources, keeping highest priority.

        Args:
            strategies: List of candidate strategies.

        Returns:
            Deduplicated list, highest priority per resource set.
        """
        # Group by tuple of affected resources
        by_resources: dict[tuple[AnomalyResource, ...], list[StrategyCandidate]] = {}
        for strat in strategies:
            key = tuple(sorted(strat.affected_resources))
            if key not in by_resources:
                by_resources[key] = []
            by_resources[key].append(strat)

        # Keep highest priority (lowest number) for each resource set
        result = []
        for resource_strategies in by_resources.values():
            resource_strategies.sort(key=lambda s: (s.priority, s.title))
            result.append(resource_strategies[0])

        return result
