"""Mission lifecycle routers."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.schemas import Mission
from app.services.exceptions import MissionStateError

# Mission router - lifecycle endpoints under /api/mission
mission_router = APIRouter(prefix="/api/mission", tags=["mission"])

# Scenario router - standalone endpoint at /api/scenario
scenario_router = APIRouter(prefix="/api", tags=["scenario"])


def _get_mission_service(request: Request):
    """Get MissionService from app state."""
    return request.app.state.mission_service


def _get_ws_manager(request: Request):
    """Get WebSocket manager from app state."""
    return request.app.state.ws_manager


@mission_router.get("/state", response_model=Mission)
async def get_mission_state(request: Request) -> Mission:
    """Get current mission state."""
    mission_service = _get_mission_service(request)
    return mission_service.get_mission()


@scenario_router.get("/scenario")
async def get_scenario(request: Request) -> dict:
    """Get mission scenario information (seed data)."""
    mission_service = _get_mission_service(request)
    mission = mission_service.get_mission()
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
    mission_service = _get_mission_service(request)
    ws_manager = _get_ws_manager(request)

    try:
        mission = mission_service.start()
    except MissionStateError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

    await ws_manager.broadcast(
        "mission.started",
        {"mission_id": mission.mission_id, "status": mission.status.value},
    )
    return mission


@mission_router.post("/pause", response_model=Mission)
async def pause_mission(request: Request) -> Mission:
    """Pause mission from RUNNING to PAUSED."""
    mission_service = _get_mission_service(request)
    ws_manager = _get_ws_manager(request)

    try:
        mission = mission_service.pause()
    except MissionStateError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

    await ws_manager.broadcast(
        "mission.paused",
        {"mission_id": mission.mission_id, "status": mission.status.value},
    )
    return mission


@mission_router.post("/resume", response_model=Mission)
async def resume_mission(request: Request) -> Mission:
    """Resume mission from PAUSED to RUNNING."""
    mission_service = _get_mission_service(request)
    ws_manager = _get_ws_manager(request)

    try:
        mission = mission_service.resume()
    except MissionStateError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

    await ws_manager.broadcast(
        "mission.resumed",
        {"mission_id": mission.mission_id, "status": mission.status.value},
    )
    return mission


@mission_router.post("/reset", response_model=Mission)
async def reset_mission(request: Request) -> Mission:
    """Reset mission to deterministic seed state."""
    mission_service = _get_mission_service(request)
    ws_manager = _get_ws_manager(request)
    telemetry_service = request.app.state.telemetry_service

    mission = mission_service.reset()
    telemetry_service.reset_tick_count()

    await ws_manager.broadcast(
        "mission.reset",
        {"mission_id": mission.mission_id, "status": mission.status.value},
    )
    return mission


@mission_router.post("/inject-anomaly", response_model=Mission)
async def inject_anomaly(request: Request) -> Mission:
    """Inject anomaly from RUNNING to ANOMALY."""
    mission_service = _get_mission_service(request)
    ws_manager = _get_ws_manager(request)

    try:
        mission = mission_service.inject_anomaly()
    except MissionStateError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

    await ws_manager.broadcast(
        "anomaly.injected",
        {"mission_id": mission.mission_id, "status": mission.status.value},
    )
    return mission
