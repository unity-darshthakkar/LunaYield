"""Phase 2F test suite for persistence integration regression hardening.

These tests verify integration between persistence layer, startup restoration,
and history APIs to ensure no regressions in durable mission run handling.

All tests use the existing Phase 2A-2E test infrastructure with temporary
file-based SQLite databases via pytest tmp_path fixture.
"""

from pathlib import Path

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import select

from app.db import DatabaseConfig, create_engine_from_config, get_session_factory
from app.db.models import MissionRunRecord

# ---------------------------------------------------------------------------
# Helper: create a fresh TestClient bound to a specific DatabaseConfig
# ---------------------------------------------------------------------------


def create_test_client(db_config: DatabaseConfig) -> TestClient:
    """Create a TestClient with the given database config.

    Triggers the full FastAPI lifespan (startup -> yield -> shutdown).
    Returns the client within the lifespan context.
    The caller is responsible for closing the client (exits context).
    """
    from app.main import app

    app.state.db_config = db_config

    client = TestClient(app)
    # The lifespan runs on __enter__; trigger it by entering the context
    client.__enter__()

    # Do NOT reset mission service - we want to inspect the state
    # produced by startup restoration.
    return client


def close_test_client(client: TestClient):
    """Close a TestClient created by create_test_client."""
    try:
        client.__exit__(None, None, None)
    finally:
        from app.main import app

        if hasattr(app.state, "db_config"):
            delattr(app.state, "db_config")


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_db_config(tmp_path: Path) -> DatabaseConfig:
    """Provide isolated test database configuration using temp file."""
    return DatabaseConfig.test_temporary(tmp_path)


# ---------------------------------------------------------------------------
# Phase 2F Persistence Integration Regression Hardening Tests
# ---------------------------------------------------------------------------


def test_persisted_run_survives_restart_and_is_visible_in_history(
    isolated_db_config: DatabaseConfig,
):
    """Verify a persisted mission run survives restart
    and remains visible in history.
    """
    # First client: start a mission and let it run briefly
    client1 = create_test_client(isolated_db_config)
    client1.post("/api/mission/start")
    # Inject some activity to create snapshots/audit
    client1.post("/api/mission/inject-anomaly")
    client1.post("/api/mission/restart")  # Clear anomaly
    run_id = client1.app.state.persistence_service.current_run_id
    # Get mission ID from the run object
    from app.main import app

    persistence = app.state.persistence_service
    with persistence._session_factory() as session:
        from app.db.repository import MissionRunRepository

        run_repo = MissionRunRepository(session)
        run = run_repo.get(run_id)
        mission_id = run.mission_id
    close_test_client(client1)

    # Second client: simulate full restart (new TestClient triggers new lifespan)
    client2 = create_test_client(isolated_db_config)
    try:
        # Verify the same run ID is restored
        assert client2.app.state.persistence_service.current_run_id == run_id

        # Verify the run appears in history endpoint
        response = client2.get(f"/api/missions/{mission_id}/runs")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["runs"]) >= 1
        # Most recent run should be first (due to ordering)
        assert data["runs"][0]["run_id"] == run_id

        # Verify snapshots and audit endpoints work for this run
        snap_resp = client2.get(f"/api/runs/{run_id}/snapshots")
        assert snap_resp.status_code == status.HTTP_200_OK
        snap_data = snap_resp.json()
        assert len(snap_data["snapshots"]) >= 1

        audit_resp = client2.get(f"/api/runs/{run_id}/audit")
        assert audit_resp.status_code == status.HTTP_200_OK
        audit_data = audit_resp.json()
        assert len(audit_data["audit_events"]) >= 1
    finally:
        close_test_client(client2)


def test_failed_restoration_marked_and_visible_in_history(
    isolated_db_config: DatabaseConfig,
):
    """Verify failed restoration produces a durable
    RESTORATION_FAILED run in history.
    """
    # First client: start a mission and create snapshot/audit
    client1 = create_test_client(isolated_db_config)
    client1.post("/api/mission/start")
    run_id = client1.app.state.persistence_service.current_run_id
    # Get mission ID from the run object
    from app.main import app

    persistence = app.state.persistence_service
    with persistence._session_factory() as session:
        from app.db.repository import MissionRunRepository

        run_repo = MissionRunRepository(session)
        run = run_repo.get(run_id)
        mission_id = run.mission_id
    close_test_client(client1)

    # Corrupt the snapshot to cause restoration failure
    engine = create_engine_from_config(isolated_db_config)
    session_factory = get_session_factory(engine)
    with session_factory() as session:
        stmt = select(MissionRunRecord).where(MissionRunRecord.run_id == run_id)
        run = session.exec(stmt).first()
        assert run is not None
        # We'll corrupt by setting an invalid status in the snapshot
        from app.db.repository import MissionSnapshotRepository

        snap_repo = MissionSnapshotRepository(session)
        snapshot = snap_repo.get_latest_for_run(run_id)
        assert snapshot is not None
        snapshot.status = "CORRUPTED_STATUS"
        session.add(snapshot)
        session.commit()

    # Second client: restart should fail restoration and create fresh run
    client2 = create_test_client(isolated_db_config)
    try:
        # Should have a new run ID (fresh run)
        new_run_id = client2.app.state.persistence_service.current_run_id
        assert new_run_id != run_id

        # Original run should be marked as RESTORATION_FAILED
        engine = create_engine_from_config(isolated_db_config)
        session_factory = get_session_factory(engine)
        with session_factory() as session:
            run_repo = MissionRunRepository(session)
            old_run = run_repo.get(run_id)
            assert old_run is not None
            assert old_run.ended_at is not None
            assert old_run.final_status == "RESTORATION_FAILED"

        # Both runs should appear in history, with new run first (more recent)
        response = client2.get(f"/api/missions/{mission_id}/runs")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["runs"]) == 2
        # New run should be first due to later started_at
        assert data["runs"][0]["run_id"] == new_run_id
        assert data["runs"][1]["run_id"] == run_id
        assert data["runs"][1]["final_status"] == "RESTORATION_FAILED"

        # Verify we can still access snapshots/audit for the failed run
        snap_resp = client2.get(f"/api/runs/{run_id}/snapshots")
        assert snap_resp.status_code == status.HTTP_200_OK
        snap_data = snap_resp.json()
        # Should have snapshots (they existed before corruption)
        assert len(snap_data["snapshots"]) >= 1

        audit_resp = client2.get(f"/api/runs/{run_id}/audit")
        assert audit_resp.status_code == status.HTTP_200_OK
        audit_data = audit_resp.json()
        # Should have audit events
        assert len(audit_data["audit_events"]) >= 1
    finally:
        close_test_client(client2)


def test_fresh_run_after_failed_restoration_is_queryable_and_ordered(
    isolated_db_config: DatabaseConfig,
):
    """Verify new runs after failed restoration remain
    queryable and correctly ordered.
    """
    # First client: start mission, corrupt snapshot to force failure on restart
    client1 = create_test_client(isolated_db_config)
    client1.post("/api/mission/start")
    run_id = client1.app.state.persistence_service.current_run_id
    # Get mission ID from the run object
    from app.main import app

    persistence = app.state.persistence_service
    with persistence._session_factory() as session:
        from app.db.repository import MissionRunRepository

        run_repo = MissionRunRepository(session)
        run = run_repo.get(run_id)
        mission_id = run.mission_id
    close_test_client(client1)

    # Corrupt snapshot
    engine = create_engine_from_config(isolated_db_config)
    session_factory = get_session_factory(engine)
    with session_factory() as session:
        from app.db.repository import MissionSnapshotRepository

        snap_repo = MissionSnapshotRepository(session)
        snapshot = snap_repo.get_latest_for_run(run_id)
        snapshot.status = "BAD_STATUS"
        session.add(snapshot)
        session.commit()

    # Second client: restart -> failed restoration -> fresh run
    client2 = create_test_client(isolated_db_config)
    try:
        failed_run_id = run_id
        fresh_run_id = client2.app.state.persistence_service.current_run_id
        assert fresh_run_id != failed_run_id

        # Third client: another restart should see both runs, fresh one first
        client3 = create_test_client(isolated_db_config)
        try:
            response = client3.get(f"/api/missions/{mission_id}/runs")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data["runs"]) == 2
            # Fresh run (most recent) should be first
            assert data["runs"][0]["run_id"] == fresh_run_id
            assert data["runs"][1]["run_id"] == failed_run_id
            assert data["runs"][1]["final_status"] == "RESTORATION_FAILED"

            # Verify we can start yet another run and it appears at the front
            client3.post("/api/mission/reset")
            client3.post("/api/mission/start")
            newer_run_id = client3.app.state.persistence_service.current_run_id
            assert newer_run_id != fresh_run_id
            assert newer_run_id != failed_run_id

            response = client3.get(f"/api/missions/{mission_id}/runs")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data["runs"]) == 3
            # Newest run should be first
            assert data["runs"][0]["run_id"] == newer_run_id
            assert data["runs"][1]["run_id"] == fresh_run_id
            assert data["runs"][2]["run_id"] == failed_run_id
        finally:
            close_test_client(client3)
    finally:
        close_test_client(client2)
