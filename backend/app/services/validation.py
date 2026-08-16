"""Strategy Validation Service — deterministic strategy candidate validation.

Validates StrategyCandidate objects produced by StrategyService.
Deterministic, backend-authoritative validation. Invalid strategies
are rejected and never become recommended, approved, or executable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.schemas import (
    AnomalyResource,
    StrategyCandidate,
    StrategyValidationResponse,
    StrategyValidationResult,
)

if TYPE_CHECKING:
    from app.services.mission import MissionService


# Supported actions defined by the deterministic fallback logic
SUPPORTED_ACTIONS = {
    "Disable non-essential science instruments",
    "Reduce communication frequency",
    "Orient solar panels for maximum charging",
    "Enter low-power safe mode if below 5%",
    "Reduce science duty cycle by 50%",
    "Schedule high-power activities during peak sun",
    "Plan recharge stop at next sunlit waypoint",
    "Monitor battery trend every 30 minutes",
    "Prioritize downlink during next comms window",
    "Compress and queue all science data for transmission",
    "Delete non-essential cached thumbnails",
    "Suspend new data collection until offload complete",
    "Schedule downlink at next available comms window",
    "Enable data compression for new collections",
    "Archive completed science targets",
    "Monitor storage growth rate",
    "Enter thermal safe mode immediately",
    "Orient rover for passive thermal control",
    "Disable heat-generating instruments",
    "Monitor temperature every 5 minutes",
    "Reduce instrument duty cycle by 30%",
    "Adjust rover orientation for thermal management",
    "Enable active thermal control if available",
    "Monitor temperature trend every 15 minutes",
    "Transmit highest-priority science data first",
    "Send health and safety telemetry immediately",
    "Defer non-critical data to next window",
    "Confirm receipt before window closes",
    "Queue data by priority for next comms window",
    "Compress data to maximize throughput",
    "Verify ground station availability",
    "Monitor window duration trend",
    "Abort current science activity",
    "Plot direct return route to base",
    "Disable all non-essential systems",
    "Transmit final position and status",
    "Reorder waypoints for efficient path",
    "Reduce dwell time at remaining targets",
    "Skip lowest-priority science targets",
    "Verify return trajectory has margin",
}


class StrategyValidationService:
    """Validates StrategyCandidate objects for safety and consistency.

    Deterministic validation that ensures only well-formed, safe strategies
    can proceed to any future approval/execution flow.
    """

    def __init__(self, mission_service: MissionService) -> None:
        """Initialize with mission service for resource reference validation.

        Args:
            mission_service: Provides access to current mission state
                for resource consistency checks.
        """
        self._mission_service = mission_service

    def validate_strategies(
        self,
        strategies: list[StrategyCandidate],
        mission_id: str,
        current_elapsed_s: int,
    ) -> StrategyValidationResponse:
        """Validate a list of strategy candidates.

        Args:
            strategies: List of StrategyCandidate objects to validate.
            mission_id: Mission identifier for the response.
            current_elapsed_s: Current mission elapsed time for the response.

        Returns:
            StrategyValidationResponse with per-strategy validation results.
        """
        results: list[StrategyValidationResult] = []

        for strategy in strategies:
            result = self._validate_strategy(strategy)
            results.append(result)

        all_valid = all(r.is_valid for r in results)

        return StrategyValidationResponse(
            mission_id=mission_id,
            current_elapsed_s=current_elapsed_s,
            validation_results=results,
            validation_count=len(results),
            all_valid=all_valid,
        )

    def _validate_strategy(
        self, strategy: StrategyCandidate
    ) -> StrategyValidationResult:
        """Validate a single strategy candidate.

        Args:
            strategy: The StrategyCandidate to validate.

        Returns:
            StrategyValidationResult with validation outcome.
        """
        reasons: list[str] = []

        # 1. Required fields - Pydantic already enforces presence,
        # but check for empty strings
        if not strategy.strategy_id or not strategy.strategy_id.strip():
            reasons.append("strategy_id is empty")
        if not strategy.title or not strategy.title.strip():
            reasons.append("title is empty")
        if not strategy.rationale or not strategy.rationale.strip():
            reasons.append("rationale is empty")

        # 2. Priority range (Pydantic enforces 1-5, but double-check)
        if not (1 <= strategy.priority <= 5):
            reasons.append(f"priority {strategy.priority} out of range [1,5]")

        # 3. requires_operator_approval must be True
        if strategy.requires_operator_approval is not True:
            reasons.append("requires_operator_approval must be true")

        # 4. affected_resources consistency - all must be valid AnomalyResource
        if not strategy.affected_resources:
            reasons.append("affected_resources must not be empty")
        else:
            for resource in strategy.affected_resources:
                if resource not in AnomalyResource:
                    reasons.append(f"unknown resource reference: {resource}")

        # 5. recommended_actions must not be empty and all must be supported
        if not strategy.recommended_actions:
            reasons.append("recommended_actions must not be empty")
        else:
            for action in strategy.recommended_actions:
                if not action or not action.strip():
                    reasons.append("recommended_actions contains empty string")
                elif action not in SUPPORTED_ACTIONS:
                    reasons.append(f"unsupported action: {action}")

        # 6. source_anomalies format check (if present)
        for anomaly_ref in strategy.source_anomalies:
            if not anomaly_ref or not anomaly_ref.strip():
                reasons.append("source_anomalies contains empty string")
            # Basic format check: should contain resource-severity pattern
            # We don't enforce exact format, but check it's not malformed
            if "-" not in anomaly_ref:
                reasons.append(f"malformed source anomaly reference: {anomaly_ref}")

        # 7. strategy_id format check (should start with "strat-")
        if strategy.strategy_id and not strategy.strategy_id.startswith("strat-"):
            reasons.append("strategy_id must start with 'strat-'")

        is_valid = len(reasons) == 0

        return StrategyValidationResult(
            strategy_id=strategy.strategy_id,
            is_valid=is_valid,
            rejection_reasons=reasons,
        )
