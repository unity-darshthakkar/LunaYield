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
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        """Unregister a WebSocket connection."""
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, event_type: str, payload: dict[str, Any]) -> None:
        """Broadcast an event to all connected clients."""
        message = {
            "event": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": payload,
        }
        data = json.dumps(message)

        async with self._lock:
            disconnected = set()
            for ws in self._connections:
                try:
                    await ws.send_text(data)
                except Exception:
                    disconnected.add(ws)

            # Clean up disconnected clients
            for ws in disconnected:
                self._connections.discard(ws)

    @property
    def connection_count(self) -> int:
        """Return the number of active connections."""
        return len(self._connections)
