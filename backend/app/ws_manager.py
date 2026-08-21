"""WebSocket connection manager for LunaYield."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket


class WSConnectionManager:
    """Manages WebSocket connections and broadcasts events."""

    def __init__(self) -> None:
        self._connections_by_session: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self._connections_by_session.setdefault(session_id, set()).add(websocket)

    async def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        """Unregister a WebSocket connection."""
        async with self._lock:
            session_connections = self._connections_by_session.get(session_id)
            if session_connections is None:
                return
            session_connections.discard(websocket)
            if not session_connections:
                self._connections_by_session.pop(session_id, None)

    async def broadcast(
        self, session_id: str, event_type: str, payload: dict[str, Any]
    ) -> None:
        """Broadcast an event to all connected clients in one session."""
        message = {
            "event": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": payload,
        }
        data = json.dumps(message)

        async with self._lock:
            session_connections = self._connections_by_session.get(session_id, set())
            disconnected = set()
            for ws in session_connections:
                try:
                    await ws.send_text(data)
                except Exception:
                    disconnected.add(ws)

            # Clean up disconnected clients
            for ws in disconnected:
                session_connections.discard(ws)

            if not session_connections:
                self._connections_by_session.pop(session_id, None)

    def close_session(self, session_id: str) -> None:
        """Drop tracked connections for a session bucket."""
        self._connections_by_session.pop(session_id, None)

    @property
    def connection_count(self) -> int:
        """Return the total number of active connections across all sessions."""
        return sum(
            len(connections) for connections in self._connections_by_session.values()
        )

    def connection_count_for_session(self, session_id: str) -> int:
        """Return the number of active connections for one session."""
        return len(self._connections_by_session.get(session_id, set()))
