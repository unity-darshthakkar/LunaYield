"""WebSocket router for real-time mission events."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.session_manager import get_session_id_from_websocket
from app.ws_manager import WSConnectionManager

router = APIRouter(prefix="/api/ws", tags=["websocket"])


@router.websocket("/mission")
async def mission_websocket(websocket: WebSocket) -> None:
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
    # Access ws_manager from the websocket's app state (via scope)
    ws_manager: WSConnectionManager = websocket.app.state.ws_manager
    session_id = get_session_id_from_websocket(websocket)
    websocket.app.state.session_manager.get_or_create(session_id)
    await ws_manager.connect(session_id, websocket)

    try:
        # Keep connection alive; listen for client messages
        # (ping/pong or future commands)
        while True:
            await websocket.receive_text()
            websocket.app.state.session_manager.touch(session_id)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await ws_manager.disconnect(session_id, websocket)
