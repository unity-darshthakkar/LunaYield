"""Mission lifecycle routers."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.schemas import Mission
from app.services.exceptions import MissionStateError
from app.session_manager import get_session_context_from_request

# Mission router - lifecycle endpoints under /api/mission
mission_router = APIRouter(prefix="/api/mission", tags=["mission"])

# Scenario router - standalone endpoint at /api/scenario
scenario_router = APIRouter(prefix="/api", tags=["scenario"])


def _get_ws_manager(request: Request):
    """Get WebSocket manager from app state."""
    return request.app.state.ws_manager


@mission_router.get("/state", response_model=Mission)
async def get_mission_state(request: Request) -> Mission:
    """Get current mission state."""
    session_context = get_session_context_from_request(request)
    return session_context.mission_service.get_mission()


@scenario_router.get("/scenario")
async def get_scenario(request: Request) -> dict:
    """Get mission scenario information (seed data)."""
    session_context = get_session_context_from_request(request)
    mission = session_context.mission_service.get_mission()
    return {
        "mission_id": mission.mission_id,
        "label": mission.label,
        "waypoints": [
            {
                "id": wp.id,
                "x": wp.x,
                "y": wp.y,
                "label": wp.label,
                "is_science_target": wp.is_science_target,
            }
            for wp in mission.original_route.waypoints
        ],
    }


@mission_router.post("/start", response_model=Mission)
async def start_mission(request: Request) -> Mission:
    """Start mission from IDLE to RUNNING."""
    session_context = get_session_context_from_request(request)
    ws_manager = _get_ws_manager(request)

    try:
        mission = session_context.mission_service.start()
    except MissionStateError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

    session_context.persistence_service.persist_snapshot(mission)
    session_context.persistence_service.persist_new_audit_events(mission)

    await ws_manager.broadcast(
        session_context.session_id,
        "mission.started",
        {"mission_id": mission.mission_id, "status": mission.status.value},
    )
    return mission


@mission_router.post("/pause", response_model=Mission)
async def pause_mission(request: Request) -> Mission:
    """Pause mission from RUNNING to PAUSED."""
    session_context = get_session_context_from_request(request)
    ws_manager = _get_ws_manager(request)

    try:
        mission = session_context.mission_service.pause()
    except MissionStateError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

    session_context.persistence_service.persist_snapshot(mission)
    session_context.persistence_service.persist_new_audit_events(mission)

    await ws_manager.broadcast(
        session_context.session_id,
        "mission.paused",
        {"mission_id": mission.mission_id, "status": mission.status.value},
    )
    return mission


@mission_router.post("/resume", response_model=Mission)
async def resume_mission(request: Request) -> Mission:
    """Resume mission from PAUSED to RUNNING."""
    session_context = get_session_context_from_request(request)
    ws_manager = _get_ws_manager(request)

    try:
        mission = session_context.mission_service.resume()
    except MissionStateError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

    session_context.persistence_service.persist_snapshot(mission)
    session_context.persistence_service.persist_new_audit_events(mission)

    await ws_manager.broadcast(
        session_context.session_id,
        "mission.resumed",
        {"mission_id": mission.mission_id, "status": mission.status.value},
    )
    return mission


@mission_router.post("/reset", response_model=Mission)
async def reset_mission(request: Request) -> Mission:
    """Reset mission to deterministic seed state.

    Ends current run and creates new run.
    """
    session_context = get_session_context_from_request(request)
    ws_manager = _get_ws_manager(request)

    # Capture pre-reset status for ending the current mission run
    pre_reset_mission = session_context.mission_service.get_mission()
    pre_reset_status = pre_reset_mission.status.value

    # Perform the reset
    mission = session_context.mission_service.reset()
    session_context.telemetry_service.reset_tick_count()

    # Persist: end old run, create new run, snapshot, audit events
    session_context.persistence_service.mark_current_run_ended(pre_reset_status)
    session_context.persistence_service.reset_and_create_new_run(mission)

    await ws_manager.broadcast(
        session_context.session_id,
        "mission.reset",
        {"mission_id": mission.mission_id, "status": mission.status.value},
    )
    return mission


@mission_router.post("/inject-anomaly", response_model=Mission)
async def inject_anomaly(request: Request) -> Mission:
    """Inject anomaly from RUNNING to ANOMALY."""
    session_context = get_session_context_from_request(request)
    ws_manager = _get_ws_manager(request)

    try:
        mission = session_context.mission_service.inject_anomaly()
    except MissionStateError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

    session_context.persistence_service.persist_snapshot(mission)
    session_context.persistence_service.persist_new_audit_events(mission)

    await ws_manager.broadcast(
        session_context.session_id,
        "anomaly.injected",
        {"mission_id": mission.mission_id, "status": mission.status.value},
    )
    return mission
