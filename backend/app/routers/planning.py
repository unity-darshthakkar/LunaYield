"""Planning and approval routers."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.schemas import CandidatePlan
from app.services.exceptions import (
    MissionStateError,
    PlanningNotAllowedError,
    PlanNotFoundError,
    PlanUnsafeError,
)
from app.session_manager import get_session_context_from_request

router = APIRouter(prefix="/api/plans", tags=["planning"])


def _get_ws_manager(request: Request):
    return request.app.state.ws_manager


@router.post("/generate", response_model=list[CandidatePlan])
async def generate_plans(request: Request) -> list[CandidatePlan]:
    """Generate candidate plans from ANOMALY state.

    Transition: ANOMALY -> PLANNING -> AWAITING_APPROVAL
    """
    session_context = get_session_context_from_request(request)
    ws_manager = _get_ws_manager(request)

    try:
        mission = session_context.mission_service.generate_plans()
    except PlanningNotAllowedError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except MissionStateError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

    session_context.persistence_service.persist_snapshot(mission)
    session_context.persistence_service.persist_new_audit_events(mission)

    await ws_manager.broadcast(
        session_context.session_id,
        "plans.generated",
        {
            "mission_id": mission.mission_id,
            "status": mission.status.value,
            "plan_count": len(mission.candidate_plans),
        },
    )

    return mission.candidate_plans


@router.post("/{plan_id}/approve", response_model=CandidatePlan)
async def approve_plan(plan_id: str, request: Request) -> CandidatePlan:
    """Approve a candidate plan.

    Requirements:
    - Mission must be in AWAITING_APPROVAL
    - Plan must exist
    - Plan must pass independent safety re-verification
    - Rejected plans can never be approved
    """
    session_context = get_session_context_from_request(request)
    ws_manager = _get_ws_manager(request)

    try:
        mission = session_context.mission_service.approve_plan(plan_id)
    except MissionStateError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except PlanNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except PlanUnsafeError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    session_context.persistence_service.persist_snapshot(mission)
    session_context.persistence_service.persist_new_audit_events(mission)

    approved_plan = next(p for p in mission.candidate_plans if p.plan_id == plan_id)

    await ws_manager.broadcast(
        session_context.session_id,
        "plan.approved",
        {
            "mission_id": mission.mission_id,
            "status": mission.status.value,
            "approved_plan_id": approved_plan.plan_id,
            "approved_plan_label": approved_plan.label,
        },
    )

    return approved_plan
