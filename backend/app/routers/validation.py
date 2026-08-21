"""Strategy Validation API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.schemas import StrategyGenerationResponse, StrategyValidationResponse
from app.session_manager import get_session_context_from_request

router = APIRouter(prefix="/api", tags=["strategy-validation"])


@router.post("/strategies/validate", response_model=StrategyValidationResponse)
async def validate_strategies(
    request: Request,
    strategies_response: StrategyGenerationResponse,
) -> StrategyValidationResponse:
    """Validate a list of strategy candidates.

    Accepts a StrategyGenerationResponse and returns validation results
    for each strategy. Does not mutate mission state.
    """
    session_context = get_session_context_from_request(request)
    try:
        return session_context.validation_service.validate_strategies(
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
    session_context = get_session_context_from_request(request)

    try:
        # Generate strategies
        generation = session_context.strategy_service.generate_strategies(
            use_forecast=use_forecast, forecast_horizon_s=forecast_horizon
        )

        # Validate them
        return session_context.validation_service.validate_strategies(
            strategies=generation.strategies,
            mission_id=generation.mission_id,
            current_elapsed_s=generation.current_elapsed_s,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
