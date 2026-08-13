"""Forecasting API endpoints for mission resource predictions."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from app.schemas import MissionForecastResponse
from app.services.forecasting import ForecastingService

router = APIRouter(prefix="/api", tags=["forecasting"])


def _get_forecasting_service(request: Request) -> ForecastingService:
    """Get ForecastingService from app state."""
    return request.app.state.forecasting_service


@router.get("/forecast", response_model=MissionForecastResponse)
async def get_resource_forecast(
    request: Request,
    horizon: int = Query(
        3600, description="Forecast horizon in seconds", ge=60, le=86400
    ),
    interval: int = Query(
        60, description="Forecast interval in seconds", ge=10, le=3600
    ),
) -> MissionForecastResponse:
    """Get deterministic forecast of mission resource levels.

    Returns forecast points showing how battery, storage, temperature,
    and time resources are expected to change over the forecast horizon.

    Uses deterministic calculations based on current mission state and
    historical consumption patterns. Does not mutate mission state.
    """
    forecasting_service = _get_forecasting_service(request)
    try:
        return forecasting_service.generate_forecast(
            forecast_horizon_s=horizon, forecast_tick_interval_s=interval
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
