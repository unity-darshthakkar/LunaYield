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
from app.services.persistence import MissionPersistenceService

router = APIRouter(prefix="/api/plans", tags=["planning"])


def _get_mission_service(request: Request):
    return request.app.state.mission_service


def _get_ws_manager(request: Request):
    return request.app.state.ws_manager


def _get_persistence_service(request: Request) -> MissionPersistenceService:
    """Get MissionPersistenceService from app state."""
    return request.app.state.persistence_service


async def _persist_after_transition(request: Request, mission) -> None:
    """Persist snapshot and new audit events after a successful state transition."""
    persistence_service = _get_persistence_service(request)
    persistence_service.persist_snapshot(mission)
    persistence_service.persist_new_audit_events(mission)


@router.post("/generate", response_model=list[CandidatePlan])
async def generate_plans(request: Request) -> list[CandidatePlan]:
    """Generate candidate plans from ANOMALY state.

    Transition: ANOMALY -> PLANNING -> AWAITING_APPROVAL
    """
    mission_service = _get_mission_service(request)
    ws_manager = _get_ws_manager(request)

    try:
        mission = mission_service.generate_plans()
    except PlanningNotAllowedError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except MissionStateError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

    await _persist_after_transition(request, mission)

    await ws_manager.broadcast(
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
    mission_service = _get_mission_service(request)
    ws_manager = _get_ws_manager(request)

    try:
        mission = mission_service.approve_plan(plan_id)
    except MissionStateError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except PlanNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except PlanUnsafeError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    await _persist_after_transition(request, mission)

    approved_plan = next(p for p in mission.candidate_plans if p.plan_id == plan_id)

    await ws_manager.broadcast(
        "plan.approved",
        {
            "mission_id": mission.mission_id,
            "status": mission.status.value,
            "approved_plan_id": approved_plan.plan_id,
            "approved_plan_label": approved_plan.label,
        },
    )

    return approved_plan
