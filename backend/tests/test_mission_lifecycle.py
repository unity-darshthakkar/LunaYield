"""Tests for mission lifecycle state transitions."""

import pytest
from fastapi.testclient import TestClient

from app.schemas import MissionStatus
from app.services.exceptions import MissionStateError
from app.services.mission import MissionService


class TestMissionLifecycle:
    """Test mission state transitions via MissionService."""

    def test_start_from_idle(self, clean_mission: MissionService) -> None:
        mission = clean_mission.start()
        assert mission.status == MissionStatus.RUNNING
        assert len(mission.audit_trail) >= 2  # seed + started

    def test_start_from_non_idle_raises(self, clean_mission: MissionService) -> None:
        clean_mission.start()  # Now RUNNING
        with pytest.raises(MissionStateError):
            clean_mission.start()

    def test_pause_from_running(self, clean_mission: MissionService) -> None:
        clean_mission.start()
        mission = clean_mission.pause()
        assert mission.status == MissionStatus.PAUSED
        assert any(e.event_type == "mission.paused" for e in mission.audit_trail)

    def test_pause_from_non_running_raises(self, clean_mission: MissionService) -> None:
        with pytest.raises(MissionStateError):
            clean_mission.pause()

    def test_resume_from_paused(self, clean_mission: MissionService) -> None:
        clean_mission.start()
        clean_mission.pause()
        mission = clean_mission.resume()
        assert mission.status == MissionStatus.RUNNING
        assert any(e.event_type == "mission.resumed" for e in mission.audit_trail)

    def test_resume_from_non_paused_raises(self, clean_mission: MissionService) -> None:
        with pytest.raises(MissionStateError):
            clean_mission.resume()

    def test_inject_anomaly_from_running(self, clean_mission: MissionService) -> None:
        clean_mission.start()
        mission = clean_mission.inject_anomaly()
        assert mission.status == MissionStatus.ANOMALY
        assert mission.anomaly_active is True
        assert any(e.event_type == "anomaly.injected" for e in mission.audit_trail)

    def test_inject_anomaly_from_non_running_raises(
        self, clean_mission: MissionService
    ) -> None:
        with pytest.raises(MissionStateError):
            clean_mission.inject_anomaly()

    def test_reset_returns_to_idle(self, clean_mission: MissionService) -> None:
        clean_mission.start()
        clean_mission.inject_anomaly()
        mission = clean_mission.reset()
        assert mission.status == MissionStatus.IDLE
        assert mission.elapsed_s == 0
        assert mission.anomaly_active is False
        assert mission.candidate_plans == []
        assert any(e.event_type == "mission.reset" for e in mission.audit_trail)

    def test_reset_is_deterministic(self, clean_mission: MissionService) -> None:
        clean_mission.start()
        clean_mission.inject_anomaly()

        mission1 = clean_mission.reset()
        mission2 = clean_mission.reset()

        assert mission1.mission_id == mission2.mission_id
        assert mission1.resources.battery_pct == mission2.resources.battery_pct
        assert mission1.status == mission2.status
        assert len(mission1.audit_trail) == len(mission2.audit_trail)

    def test_anomaly_to_planning_transition(
        self, clean_mission: MissionService
    ) -> None:
        """Test ANOMALY -> PLANNING -> AWAITING_APPROVAL with proper audit events."""
        clean_mission.start()
        clean_mission.inject_anomaly()

        # Manually set up dependencies for planning
        from app.services.planning import PlanningService
        from app.services.safety import SafetyVerifier

        clean_mission.set_dependencies(SafetyVerifier(), PlanningService())

        mission = clean_mission.generate_plans()

        assert mission.status == MissionStatus.AWAITING_APPROVAL
        assert len(mission.candidate_plans) == 3

        # Check audit events: planning.started AND plans.generated
        audit_types = [e.event_type for e in mission.audit_trail]
        assert "planning.started" in audit_types
        assert "plans.generated" in audit_types


class TestMissionLifecycleAPI:
    """Test mission lifecycle via HTTP API."""

    def test_get_state(self, client: TestClient) -> None:
        response = client.get("/api/mission/state")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "IDLE"

    def test_get_scenario(self, client: TestClient) -> None:
        response = client.get("/api/scenario")
        assert response.status_code == 200
        data = response.json()
        assert "mission_id" in data
        assert "waypoints" in data
        assert len(data["waypoints"]) == 5

    def test_start_mission(self, client: TestClient) -> None:
        response = client.post("/api/mission/start")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "RUNNING"

    def test_start_from_running_returns_409(self, client: TestClient) -> None:
        client.post("/api/mission/start")
        response = client.post("/api/mission/start")
        assert response.status_code == 409

    def test_pause_mission(self, client: TestClient) -> None:
        client.post("/api/mission/start")
        response = client.post("/api/mission/pause")
        assert response.status_code == 200
        assert response.json()["status"] == "PAUSED"

    def test_pause_from_idle_returns_409(self, client: TestClient) -> None:
        response = client.post("/api/mission/pause")
        assert response.status_code == 409

    def test_resume_mission(self, client: TestClient) -> None:
        client.post("/api/mission/start")
        client.post("/api/mission/pause")
        response = client.post("/api/mission/resume")
        assert response.status_code == 200
        assert response.json()["status"] == "RUNNING"

    def test_resume_from_running_returns_409(self, client: TestClient) -> None:
        client.post("/api/mission/start")
        response = client.post("/api/mission/resume")
        assert response.status_code == 409

    def test_inject_anomaly(self, client: TestClient) -> None:
        client.post("/api/mission/start")
        response = client.post("/api/mission/inject-anomaly")
        assert response.status_code == 200
        assert response.json()["status"] == "ANOMALY"
        assert response.json()["anomaly_active"] is True

    def test_inject_anomaly_from_paused_returns_409(self, client: TestClient) -> None:
        client.post("/api/mission/start")
        client.post("/api/mission/pause")
        response = client.post("/api/mission/inject-anomaly")
        assert response.status_code == 409

    def test_reset_mission(self, client: TestClient) -> None:
        client.post("/api/mission/start")
        client.post("/api/mission/inject-anomaly")
        response = client.post("/api/mission/reset")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "IDLE"
        assert data["elapsed_s"] == 0
        assert data["anomaly_active"] is False
