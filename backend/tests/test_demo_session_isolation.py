"""Regression coverage for per-demo-session mission isolation."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import DatabaseConfig

SESSION_A_ID = "session-a"
SESSION_B_ID = "session-b"
SESSION_C_ID = "session-c"
SESSION_A_HEADERS = {"X-Demo-Session-Id": SESSION_A_ID}
SESSION_B_HEADERS = {"X-Demo-Session-Id": SESSION_B_ID}
SESSION_C_HEADERS = {"X-Demo-Session-Id": SESSION_C_ID}


def create_test_client(db_config: DatabaseConfig) -> TestClient:
    """Create a TestClient with background telemetry disabled."""
    from app.main import app

    app.state.db_config = db_config
    app.state.disable_background_telemetry = True

    client = TestClient(app)
    client.__enter__()
    return client


def close_test_client(client: TestClient) -> None:
    """Close a TestClient created by create_test_client."""
    try:
        client.__exit__(None, None, None)
    finally:
        from app.main import app

        if hasattr(app.state, "db_config"):
            delattr(app.state, "db_config")
        if hasattr(app.state, "disable_background_telemetry"):
            delattr(app.state, "disable_background_telemetry")


@pytest.fixture
def isolated_db_config(tmp_path: Path) -> DatabaseConfig:
    """Provide isolated test database configuration using a temp file."""
    return DatabaseConfig.test_temporary(tmp_path)


class TestDemoSessionIsolation:
    """Verify browser-tab demo sessions are isolated from one another."""

    def test_independent_sessions_begin_idle_and_reuse_same_context(
        self, isolated_db_config: DatabaseConfig
    ) -> None:
        client = create_test_client(isolated_db_config)
        try:
            session_manager = client.app.state.session_manager

            response_a = client.get("/api/mission/state", headers=SESSION_A_HEADERS)
            response_b = client.get("/api/mission/state", headers=SESSION_B_HEADERS)
            response_a_repeat = client.get(
                "/api/mission/state", headers=SESSION_A_HEADERS
            )

            assert response_a.status_code == 200
            assert response_b.status_code == 200
            assert response_a.json()["status"] == "IDLE"
            assert response_b.json()["status"] == "IDLE"
            assert session_manager.get(SESSION_A_ID) is session_manager.get(
                SESSION_A_ID
            )
            assert session_manager.get(SESSION_A_ID) is not session_manager.get(
                SESSION_B_ID
            )
            assert response_a_repeat.json()["status"] == "IDLE"
        finally:
            close_test_client(client)

    def test_start_reset_and_anomaly_are_session_specific(
        self, isolated_db_config: DatabaseConfig
    ) -> None:
        client = create_test_client(isolated_db_config)
        try:
            start_a = client.post("/api/mission/start", headers=SESSION_A_HEADERS)
            state_b_before = client.get("/api/mission/state", headers=SESSION_B_HEADERS)
            reset_b = client.post("/api/mission/reset", headers=SESSION_B_HEADERS)
            state_a_after_reset_b = client.get(
                "/api/mission/state", headers=SESSION_A_HEADERS
            )

            assert start_a.status_code == 200
            assert state_b_before.json()["status"] == "IDLE"
            assert reset_b.status_code == 200
            assert state_a_after_reset_b.json()["status"] == "RUNNING"

            anomaly_a = client.post(
                "/api/mission/inject-anomaly", headers=SESSION_A_HEADERS
            )
            state_b_after_anomaly = client.get(
                "/api/mission/state", headers=SESSION_B_HEADERS
            )

            assert anomaly_a.status_code == 200
            assert anomaly_a.json()["status"] == "ANOMALY"
            assert anomaly_a.json()["resources"]["battery_pct"] == 95.0
            assert state_b_after_anomaly.json()["status"] == "IDLE"
            assert state_b_after_anomaly.json()["resources"]["battery_pct"] == 100.0
        finally:
            close_test_client(client)

    def test_plan_generation_and_approval_do_not_cross_sessions(
        self, isolated_db_config: DatabaseConfig
    ) -> None:
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start", headers=SESSION_A_HEADERS)
            client.post("/api/mission/inject-anomaly", headers=SESSION_A_HEADERS)

            generate_a = client.post("/api/plans/generate", headers=SESSION_A_HEADERS)
            state_b = client.get("/api/mission/state", headers=SESSION_B_HEADERS)

            assert generate_a.status_code == 200
            assert len(generate_a.json()) == 3
            assert state_b.json()["candidate_plans"] == []
            assert state_b.json()["status"] == "IDLE"

            extended_plan_id = next(
                plan["plan_id"]
                for plan in generate_a.json()
                if plan["label"] == "Extended Survey"
            )
            approve_a = client.post(
                f"/api/plans/{extended_plan_id}/approve", headers=SESSION_A_HEADERS
            )
            state_a = client.get("/api/mission/state", headers=SESSION_A_HEADERS)
            state_b_after = client.get("/api/mission/state", headers=SESSION_B_HEADERS)

            assert approve_a.status_code == 200
            assert state_a.json()["status"] == "EXECUTING"
            assert state_b_after.json()["status"] == "IDLE"
            assert state_b_after.json()["candidate_plans"] == []
        finally:
            close_test_client(client)

    def test_telemetry_progression_is_independent_per_session(
        self, isolated_db_config: DatabaseConfig
    ) -> None:
        client = create_test_client(isolated_db_config)
        try:
            session_manager = client.app.state.session_manager

            client.post("/api/mission/start", headers=SESSION_A_HEADERS)

            context_a = session_manager.get(SESSION_A_ID)
            context_b = session_manager.get_or_create(SESSION_B_ID)

            sample_a = context_a.telemetry_service.generate_sample()
            mission_a = context_a.mission_service.get_mission()
            mission_b = context_b.mission_service.get_mission()

            assert sample_a is not None
            assert mission_a.elapsed_s == 2
            assert mission_a.resources.battery_pct == 99.5
            assert mission_b.elapsed_s == 0
            assert mission_b.resources.battery_pct == 100.0

            client.post("/api/mission/start", headers=SESSION_B_HEADERS)
            sample_b = context_b.telemetry_service.generate_sample()
            mission_b_after = context_b.mission_service.get_mission()

            assert sample_b is not None
            assert mission_b_after.elapsed_s == 2
            assert mission_b_after.resources.battery_pct == 99.5
            assert mission_a.elapsed_s == 2
        finally:
            close_test_client(client)

    def test_persistence_tracking_is_per_session(
        self, isolated_db_config: DatabaseConfig
    ) -> None:
        client = create_test_client(isolated_db_config)
        try:
            session_manager = client.app.state.session_manager
            client.get("/api/mission/state", headers=SESSION_A_HEADERS)
            client.get("/api/mission/state", headers=SESSION_B_HEADERS)

            context_a = session_manager.get(SESSION_A_ID)
            context_b = session_manager.get(SESSION_B_ID)

            run_id_a_before = context_a.persistence_service.current_run_id
            run_id_b_before = context_b.persistence_service.current_run_id

            client.post("/api/mission/reset", headers=SESSION_A_HEADERS)

            run_id_a_after = context_a.persistence_service.current_run_id
            run_id_b_after = context_b.persistence_service.current_run_id

            assert run_id_a_before is not None
            assert run_id_b_before is not None
            assert run_id_a_before != run_id_b_before
            assert run_id_a_after != run_id_a_before
            assert run_id_b_after == run_id_b_before
        finally:
            close_test_client(client)

    def test_new_session_id_creates_fresh_mission(
        self, isolated_db_config: DatabaseConfig
    ) -> None:
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start", headers=SESSION_A_HEADERS)
            state_c = client.get("/api/mission/state", headers=SESSION_C_HEADERS)

            assert state_c.status_code == 200
            assert state_c.json()["status"] == "IDLE"
            assert state_c.json()["resources"]["battery_pct"] == 100.0
        finally:
            close_test_client(client)
