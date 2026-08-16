"""Strategy Validation API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.schemas import StrategyGenerationResponse, StrategyValidationResponse
from app.services.strategy import StrategyService
from app.services.validation import StrategyValidationService

router = APIRouter(prefix="/api", tags=["strategy-validation"])


def _get_strategy_service(request: Request) -> StrategyService:
    """Get StrategyService from app state."""
    return request.app.state.strategy_service


def _get_validation_service(request: Request) -> StrategyValidationService:
    """Get StrategyValidationService from app state."""
    return request.app.state.validation_service


@router.post("/strategies/validate", response_model=StrategyValidationResponse)
async def validate_strategies(
    request: Request,
    strategies_response: StrategyGenerationResponse,
) -> StrategyValidationResponse:
    """Validate a list of strategy candidates.

    Accepts a StrategyGenerationResponse and returns validation results
    for each strategy. Does not mutate mission state.
    """
    validation_service = _get_validation_service(request)
    try:
        return validation_service.validate_strategies(
            strategies=strategies_response.strategies,
            mission_id=strategies_response.mission_id,
            current_elapsed_s=strategies_response.current_elapsed_s,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.get("/strategies/validate", response_model=StrategyValidationResponse)
async def validate_current_strategies(
    request: Request,
    use_forecast: bool = False,
    forecast_horizon: int = 3600,
) -> StrategyValidationResponse:
    """Generate and validate strategies for current mission state.

    Convenience endpoint that generates strategies via StrategyService
    then validates them via StrategyValidationService.
    """
    strategy_service = _get_strategy_service(request)
    validation_service = _get_validation_service(request)

    try:
        # Generate strategies
        generation = strategy_service.generate_strategies(
            use_forecast=use_forecast, forecast_horizon_s=forecast_horizon
        )

        # Validate them
        return validation_service.validate_strategies(
            strategies=generation.strategies,
            mission_id=generation.mission_id,
            current_elapsed_s=generation.current_elapsed_s,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
