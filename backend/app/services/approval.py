"""Strategy Approval Service — explicit operator approval for validated strategies.

Handles deterministic approval state transitions for StrategyCandidate objects
produced by StrategyService and validated by StrategyValidationService.
Does not execute actions or mutate mission resource state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.schemas import (
    StrategyApprovalResult,
    StrategyApprovalStatus,
    StrategyCandidate,
    StrategyGenerationResponse,
)

if TYPE_CHECKING:
    from app.services.anomaly import AnomalyDetectionService
    from app.services.forecasting import ForecastingService
    from app.services.mission import MissionService
    from app.services.strategy import StrategyService
    from app.services.validation import StrategyValidationService


class StrategyApprovalService:
    """Manages explicit operator approval for validated strategy candidates.

    Approval is a discrete operator-triggered action that:
    - Only accepts strategies from the current generated strategy set
    - Requires strategy to pass StrategyValidationService
    - Requires requires_operator_approval=True
    - Does NOT execute recommended actions
    - Does NOT mutate mission resource state
    - Does NOT bypass StrategyValidationService
    - Stores approval state in memory (backend application memory)
    """

    def __init__(
        self,
        strategy_service: StrategyService,
        validation_service: StrategyValidationService,
        mission_service: MissionService,
        forecasting_service: ForecastingService,
        anomaly_service: AnomalyDetectionService,
    ) -> None:
        """Initialize with required service dependencies.

        Args:
            strategy_service: Provides current generated strategy set.
            validation_service: Validates strategies before approval.
            mission_service: Provides mission context (for response metadata).
            forecasting_service: Used for re-generating strategies if needed.
            anomaly_service: Used for re-generating strategies if needed.
        """
        self._strategy_service = strategy_service
        self._validation_service = validation_service
        self._mission_service = mission_service
        self._forecasting_service = forecasting_service
        self._anomaly_service = anomaly_service

        # In-memory approval state - maps strategy_id to approval status
        # Only exists in backend application memory for Phase 4C
        self._approval_state: dict[str, StrategyApprovalStatus] = {}

    def _generate_current_strategies(
        self, use_forecast: bool = False, forecast_horizon_s: int = 3600
    ) -> StrategyGenerationResponse:
        """Get the current generated strategy set.

        Args:
            use_forecast: Whether to include forecast-based strategies.
            forecast_horizon_s: Forecast horizon for generation.

        Returns:
            Current StrategyGenerationResponse.
        """
        return self._strategy_service.generate_strategies(
            use_forecast=use_forecast, forecast_horizon_s=forecast_horizon_s
        )

    def _find_strategy_in_current_set(
        self,
        strategy_id: str,
        use_forecast: bool = False,
        forecast_horizon_s: int = 3600,
    ) -> StrategyCandidate | None:
        """Find a strategy by ID in the current generated set.

        Args:
            strategy_id: The strategy identifier to find.
            use_forecast: Whether to include forecast-based strategies.
            forecast_horizon_s: Forecast horizon for generation.

        Returns:
            StrategyCandidate if found in current set, None otherwise.
        """
        generation = self._generate_current_strategies(
            use_forecast=use_forecast, forecast_horizon_s=forecast_horizon_s
        )
        for strategy in generation.strategies:
            if strategy.strategy_id == strategy_id:
                return strategy
        return None

    def approve_strategy(
        self,
        strategy_id: str,
        use_forecast: bool = False,
        forecast_horizon_s: int = 3600,
    ) -> StrategyApprovalResult:
        """Explicit operator approval for a validated strategy candidate.

        This is an explicit operator-triggered action. Approval:
        - Requires strategy to exist in current generated set
        - Requires strategy to pass validation
        - Requires requires_operator_approval=True
        - Does NOT execute recommended actions
        - Does NOT mutate mission resource state
        - Does NOT bypass StrategyValidationService

        Args:
            strategy_id: The strategy identifier to approve.
            use_forecast: Whether to include forecast-based strategies
                in the current generated set.
            forecast_horizon_s: Forecast horizon for generation.

        Returns:
            StrategyApprovalResult with approval outcome.
        """
        # 1. Find strategy in current generated set
        strategy = self._find_strategy_in_current_set(
            strategy_id, use_forecast, forecast_horizon_s
        )

        if strategy is None:
            return StrategyApprovalResult(
                strategy_id=strategy_id,
                approved=False,
                approval_status=StrategyApprovalStatus.NOT_FOUND,
                rejection_reasons=[
                    f"Strategy '{strategy_id}' not found in current "
                    f"generated strategy set"
                ],
            )

        # 2. Validate the strategy via StrategyValidationService
        mission = self._mission_service.get_mission()
        validation_response = self._validation_service.validate_strategies(
            strategies=[strategy],
            mission_id=mission.mission_id,
            current_elapsed_s=mission.elapsed_s,
        )

        validation_result = validation_response.validation_results[0]
        if not validation_result.is_valid:
            return StrategyApprovalResult(
                strategy_id=strategy_id,
                approved=False,
                approval_status=StrategyApprovalStatus.VALIDATION_FAILED,
                rejection_reasons=validation_result.rejection_reasons,
            )

        # 3. Check requires_operator_approval is True
        if strategy.requires_operator_approval is not True:
            return StrategyApprovalResult(
                strategy_id=strategy_id,
                approved=False,
                approval_status=StrategyApprovalStatus.REJECTED,
                rejection_reasons=["requires_operator_approval must be true"],
            )

        # 4. Check if already approved (idempotent behavior)
        existing_status = self._approval_state.get(strategy_id)
        if existing_status == StrategyApprovalStatus.APPROVED:
            return StrategyApprovalResult(
                strategy_id=strategy_id,
                approved=True,
                approval_status=StrategyApprovalStatus.ALREADY_APPROVED,
                rejection_reasons=[],
            )

        # 5. Approve - store approval state in memory
        self._approval_state[strategy_id] = StrategyApprovalStatus.APPROVED

        return StrategyApprovalResult(
            strategy_id=strategy_id,
            approved=True,
            approval_status=StrategyApprovalStatus.APPROVED,
            rejection_reasons=[],
        )

    def get_approval_status(self, strategy_id: str) -> StrategyApprovalStatus:
        """Get the current approval status for a strategy.

        Args:
            strategy_id: The strategy identifier.

        Returns:
            Current approval status, or REJECTED if never approved.
        """
        return self._approval_state.get(strategy_id, StrategyApprovalStatus.REJECTED)

    def clear_approval_state(self) -> None:
        """Clear all approval state (for testing or reset)."""
        self._approval_state.clear()

    def is_approved(self, strategy_id: str) -> bool:
        """Check if a strategy is currently approved.

        Args:
            strategy_id: The strategy identifier.

        Returns:
            True if strategy is approved, False otherwise.
        """
        return self._approval_state.get(strategy_id) == StrategyApprovalStatus.APPROVED
