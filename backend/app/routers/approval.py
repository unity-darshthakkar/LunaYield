"""Strategy Approval API endpoints.

Provides explicit operator approval for validated strategy candidates.
Approval is an explicit operator-triggered action that does NOT execute
recommended actions or mutate mission state.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from app.schemas import StrategyApprovalResult
from app.services.approval import StrategyApprovalService

router = APIRouter(prefix="/api", tags=["strategy-approval"])


def _get_approval_service(request: Request) -> StrategyApprovalService:
    """Get StrategyApprovalService from app state."""
    return request.app.state.approval_service


@router.post("/strategies/{strategy_id}/approve", response_model=StrategyApprovalResult)
async def approve_strategy(
    request: Request,
    strategy_id: str,
    use_forecast: bool = Query(
        False, description="Whether to include forecast in strategy generation"
    ),
    forecast_horizon: int = Query(
        3600,
        description="Forecast horizon in seconds for strategy generation",
        ge=60,
        le=86400,
    ),
) -> StrategyApprovalResult:
    """Approve a strategy candidate by ID.

    Explicit operator approval required - no automatic execution.
    Strategy must exist in current generated set and pass validation.
    Does NOT execute recommended actions or mutate mission state.
    """
    approval_service = _get_approval_service(request)
    try:
        return approval_service.approve_strategy(
            strategy_id=strategy_id,
            use_forecast=use_forecast,
            forecast_horizon_s=forecast_horizon,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
