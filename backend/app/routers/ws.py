"""WebSocket router for real-time mission events."""

from __future__ import annotations

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from app.ws_manager import WSConnectionManager

router = APIRouter(prefix="/api/ws", tags=["websocket"])


def _get_ws_manager(request: Request) -> WSConnectionManager:
    return request.app.state.ws_manager


@router.websocket("/mission")
async def mission_websocket(websocket: WebSocket, request: Request) -> None:
    """WebSocket endpoint for real-time mission events.

    Broadcasts structured JSON events:
    - telemetry.updated
    - mission.started
    - mission.paused
    - mission.resumed
    - anomaly.injected
    - plans.generated
    - plan.approved
    - mission.reset
    """
    ws_manager = _get_ws_manager(request)
    await ws_manager.connect(websocket)

    try:
        # Keep connection alive; listen for client messages
        # (ping/pong or future commands)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await ws_manager.disconnect(websocket)
