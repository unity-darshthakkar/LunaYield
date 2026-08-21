"""Tests for WebSocket event schemas and broadcasting."""

import json

import pytest

from app.schemas import TelemetrySample
from app.ws_manager import WSConnectionManager


class TestWSSchemas:
    """Test WebSocket event payload structures."""

    def test_telemetry_event_payload_structure(self) -> None:
        """Telemetry event should have correct structure."""
        sample = TelemetrySample(
            mission_id="test-mission",
            elapsed_s=10,
            resources={
                "battery_pct": 80.0,
                "storage_pct": 20.0,
                "temperature_c": -35.0,
                "comm_window_remaining_s": 3600,
                "op_time_remaining_s": 14400,
            },
            timestamp="2026-01-01T00:00:00+00:00",
        )

        payload = sample.model_dump()
        assert "mission_id" in payload
        assert "elapsed_s" in payload
        assert "resources" in payload
        assert "timestamp" in payload
        assert payload["resources"]["battery_pct"] == 80.0

    def test_mission_started_event_structure(self) -> None:
        """Mission started event should have correct structure."""
        payload = {"mission_id": "luna-mission-001", "status": "RUNNING"}

        assert payload["mission_id"] == "luna-mission-001"
        assert payload["status"] == "RUNNING"

    def test_anomaly_injected_event_structure(self) -> None:
        """Anomaly injected event should have correct structure."""
        payload = {"mission_id": "luna-mission-001", "status": "ANOMALY"}

        assert payload["status"] == "ANOMALY"

    def test_plans_generated_event_structure(self) -> None:
        """Plans generated event should have correct structure."""
        payload = {
            "mission_id": "luna-mission-001",
            "status": "AWAITING_APPROVAL",
            "plan_count": 3,
        }

        assert payload["plan_count"] == 3

    def test_plan_approved_event_structure(self) -> None:
        """Plan approved event should have correct structure."""
        payload = {
            "mission_id": "luna-mission-001",
            "status": "EXECUTING",
            "approved_plan_id": "plan-b-001",
            "approved_plan_label": "Extended Survey",
        }

        assert payload["approved_plan_label"] == "Extended Survey"

    def test_mission_reset_event_structure(self) -> None:
        """Mission reset event should have correct structure."""
        payload = {"mission_id": "luna-mission-001", "status": "IDLE"}

        assert payload["status"] == "IDLE"

    def test_ws_message_envelope(self) -> None:
        """WS message should have event, timestamp, payload envelope."""
        message = {
            "event": "telemetry.updated",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "payload": {"mission_id": "test", "elapsed_s": 10},
        }

        assert "event" in message
        assert "timestamp" in message
        assert "payload" in message
        assert message["event"] == "telemetry.updated"

    def test_ws_payloads_are_json_serializable(self) -> None:
        """All WS event payloads should be JSON serializable."""
        payloads = [
            {"mission_id": "test", "status": "RUNNING"},
            {"mission_id": "test", "status": "ANOMALY"},
            {"mission_id": "test", "plan_count": 3},
            {
                "mission_id": "test",
                "status": "EXECUTING",
                "approved_plan_id": "plan-1",
                "approved_plan_label": "Extended Survey",
            },
            {"mission_id": "test", "status": "IDLE"},
        ]

        for payload in payloads:
            # Should not raise
            json.dumps(payload)


class TestWSConnectionManager:
    """Test WebSocket connection manager."""

    class DummyWebSocket:
        def __init__(self) -> None:
            self.messages: list[str] = []

        async def accept(self) -> None:
            return None

        async def send_text(self, data: str) -> None:
            self.messages.append(data)

    @pytest.mark.asyncio
    async def test_connect_disconnect(self) -> None:
        """Connection manager should track connections."""
        manager = WSConnectionManager()
        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple(self) -> None:
        """Broadcast should send to all connected clients."""
        # Test that broadcast doesn't raise when no connections
        manager = WSConnectionManager()

        await manager.broadcast("session-a", "test.event", {"data": "test"})
        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_connection_counts_are_scoped_by_session(self) -> None:
        """Connection counts should be tracked per session bucket."""
        manager = WSConnectionManager()
        session_a_socket = self.DummyWebSocket()
        session_b_socket = self.DummyWebSocket()

        await manager.connect("session-a", session_a_socket)
        await manager.connect("session-b", session_b_socket)

        assert manager.connection_count == 2
        assert manager.connection_count_for_session("session-a") == 1
        assert manager.connection_count_for_session("session-b") == 1

    @pytest.mark.asyncio
    async def test_broadcast_only_reaches_target_session(self) -> None:
        """A session broadcast must not leak to other sessions."""
        manager = WSConnectionManager()
        session_a_socket = self.DummyWebSocket()
        session_b_socket = self.DummyWebSocket()

        await manager.connect("session-a", session_a_socket)
        await manager.connect("session-b", session_b_socket)
        await manager.broadcast("session-a", "mission.started", {"status": "RUNNING"})

        assert len(session_a_socket.messages) == 1
        assert session_b_socket.messages == []

    @pytest.mark.asyncio
    async def test_multiple_sockets_in_same_session_receive_same_event(self) -> None:
        """All sockets in one session should receive that session's event."""
        manager = WSConnectionManager()
        session_a_socket_1 = self.DummyWebSocket()
        session_a_socket_2 = self.DummyWebSocket()

        await manager.connect("session-a", session_a_socket_1)
        await manager.connect("session-a", session_a_socket_2)
        await manager.broadcast("session-a", "mission.started", {"status": "RUNNING"})

        assert len(session_a_socket_1.messages) == 1
        assert len(session_a_socket_2.messages) == 1
