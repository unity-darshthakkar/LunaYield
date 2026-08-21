"""Strategy Generation API endpoints for mission strategy candidates."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from app.schemas import StrategyGenerationResponse
from app.session_manager import get_session_context_from_request

router = APIRouter(prefix="/api", tags=["strategy"])


@router.get("/strategies", response_model=StrategyGenerationResponse)
async def get_strategies(
    request: Request,
    use_forecast: bool = Query(
        False, description="Whether to also check forecasted resource levels"
    ),
    forecast_horizon: int = Query(
        3600,
        description="Forecast horizon in seconds for forecast-based generation",
        ge=60,
        le=86400,
    ),
) -> StrategyGenerationResponse:
    """Generate structured, reviewable strategy candidates for current mission.

    Returns strategy candidates based on current mission state, anomalies,
    and optionally forecasted future state. All strategies are read-only
    recommendations requiring operator approval.

    Does not mutate mission state. No automatic approval or execution.
    """
    session_context = get_session_context_from_request(request)
    try:
        return session_context.strategy_service.generate_strategies(
            use_forecast=use_forecast, forecast_horizon_s=forecast_horizon
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
