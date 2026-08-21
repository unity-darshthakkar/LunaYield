"""Anomaly Detection API endpoints for mission resource anomalies."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from app.schemas import AnomalyDetectionResponse
from app.session_manager import get_session_context_from_request

router = APIRouter(prefix="/api", tags=["anomaly"])


@router.get("/anomalies", response_model=AnomalyDetectionResponse)
async def detect_anomalies(
    request: Request,
    use_forecast: bool = Query(
        False, description="Whether to also check forecasted resource levels"
    ),
    forecast_horizon: int = Query(
        3600,
        description="Forecast horizon in seconds for forecast-based detection",
        ge=60,
        le=86400,
    ),
) -> AnomalyDetectionResponse:
    """Detect resource anomalies in current mission state.

    Returns structured anomaly findings with resource, severity, observed value,
    threshold, and reason. Does not mutate mission state.

    Supports checking both current state and optionally forecasted future state.
    """
    session_context = get_session_context_from_request(request)
    try:
        return session_context.anomaly_service.detect_anomalies(
            use_forecast=use_forecast, forecast_horizon_s=forecast_horizon
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
