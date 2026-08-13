"""Phase 2E test suite for history API hardening.

These tests verify the enhanced validation, error handling, and robustness
of the mission-run history API endpoints implemented in Phase 2E.

All tests use the existing Phase 2A-2D test infrastructure with temporary
file-based SQLite databases via pytest tmp_path fixture.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.db import DatabaseConfig

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
def isolated_db_config(tmp_path) -> DatabaseConfig:
    """Provide isolated test database configuration using temp file."""
    return DatabaseConfig.test_temporary(tmp_path)


# ---------------------------------------------------------------------------
# Phase 2E History API Hardening Tests
# ---------------------------------------------------------------------------


def test_list_mission_runs_invalid_limit_values(isolated_db_config: DatabaseConfig):
    """Test that invalid limit values return appropriate error responses."""
    client = create_test_client(isolated_db_config)
    try:
        # Test limit = 0 (should be 422 Unprocessable Entity)
        response = client.get("/api/missions/test-mission/runs?limit=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test limit = -1 (should be 422 Unprocessable Entity)
        response = client.get("/api/missions/test-mission/runs?limit=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test limit = 201 (above max of 200) (should be 422 Unprocessable Entity)
        response = client.get("/api/missions/test-mission/runs?limit=201")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test non-integer limit (should be 422 Unprocessable Entity)
        response = client.get("/api/missions/test-mission/runs?limit=invalid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    finally:
        close_test_client(client)


def test_list_mission_runs_invalid_offset_values(isolated_db_config: DatabaseConfig):
    """Test that invalid offset values return appropriate error responses."""
    client = create_test_client(isolated_db_config)
    try:
        # Test offset = -1 (should be 422 Unprocessable Entity)
        response = client.get("/api/missions/test-mission/runs?offset=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test non-integer offset (should be 422 Unprocessable Entity)
        response = client.get("/api/missions/test-mission/runs?offset=invalid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    finally:
        close_test_client(client)


def test_get_mission_run_invalid_run_id_format(isolated_db_config: DatabaseConfig):
    """Test that invalid run ID formats are handled gracefully."""
    client = create_test_client(isolated_db_config)
    try:
        # Test empty run ID
        response = client.get("/api/runs/")
        # This should be 404 (not found) or 405 (method not allowed) depending
        # on routing. Actually, FastAPI will return 404 for missing path parameter.
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        ]

        # Test very long run ID (should still return 404, not error)
        long_run_id = "x" * 1000
        response = client.get(f"/api/runs/{long_run_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    finally:
        close_test_client(client)


def test_list_run_snapshots_invalid_pagination(isolated_db_config: DatabaseConfig):
    """Test that invalid pagination parameters for snapshots
    return appropriate errors.
    """
    client = create_test_client(isolated_db_config)
    try:
        # First create a run to test against
        client.post("/api/mission/start")

        # Get the actual run ID from persistence service
        from app.main import app

        persistence = app.state.persistence_service
        with persistence._session_factory() as session:
            from app.db.repository import MissionRunRepository

            run_repo = MissionRunRepository(session)
            run = run_repo.get(persistence.current_run_id)
            run_id = run.run_id

        # Test invalid limit values
        response = client.get(f"/api/runs/{run_id}/snapshots?limit=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        response = client.get(f"/api/runs/{run_id}/snapshots?limit=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        response = client.get(
            f"/api/runs/{run_id}/snapshots?limit=501"  # Above max of 500
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test invalid offset values
        response = client.get(f"/api/runs/{run_id}/snapshots?offset=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    finally:
        close_test_client(client)


def test_list_run_audit_invalid_pagination(isolated_db_config: DatabaseConfig):
    """Test that invalid pagination parameters for audit events
    return appropriate errors.
    """
    client = create_test_client(isolated_db_config)
    try:
        # First create a run to test against
        client.post("/api/mission/start")

        # Get the actual run ID from persistence service
        from app.main import app

        persistence = app.state.persistence_service
        with persistence._session_factory() as session:
            from app.db.repository import MissionRunRepository

            run_repo = MissionRunRepository(session)
            run = run_repo.get(persistence.current_run_id)
            run_id = run.run_id

        # Test invalid limit values
        response = client.get(f"/api/runs/{run_id}/audit?limit=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        response = client.get(f"/api/runs/{run_id}/audit?limit=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        response = client.get(
            f"/api/runs/{run_id}/audit?limit=1001"  # Above max of 1000
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test invalid offset values
        response = client.get(f"/api/runs/{run_id}/audit?offset=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    finally:
        close_test_client(client)


def test_history_endpoints_handle_large_limit_gracefully(
    isolated_db_config: DatabaseConfig,
):
    """Test that extremely large (but valid) limit values
    are handled gracefully.
    """
    client = create_test_client(isolated_db_config)
    try:
        # Create a run
        client.post("/api/mission/start")

        # Get the actual run ID
        from app.main import app

        persistence = app.state.persistence_service
        with persistence._session_factory() as session:
            from app.db.repository import MissionRunRepository

            run_repo = MissionRunRepository(session)
            run = run_repo.get(persistence.current_run_id)
            run_id = run.run_id
            mission_id = run.mission_id

        # Test limit at maximum allowed value
        response = client.get(f"/api/missions/{mission_id}/runs?limit=200")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["limit"] == 200

        response = client.get(f"/api/runs/{run_id}/snapshots?limit=500")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["limit"] == 500

        response = client.get(f"/api/runs/{run_id}/audit?limit=1000")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["limit"] == 1000

    finally:
        close_test_client(client)


def test_history_endpoints_preserve_deterministic_ordering(
    isolated_db_config: DatabaseConfig,
):
    """Test that history endpoints preserve deterministic ordering
    even with pagination.
    """
    client = create_test_client(isolated_db_config)
    try:
        # Create multiple runs with known ordering
        client.post("/api/mission/start")  # Run 1
        client.post("/api/mission/reset")
        client.post("/api/mission/start")  # Run 2
        client.post("/api/mission/reset")
        client.post("/api/mission/start")  # Run 3

        # Get the actual mission ID and run IDs
        from app.main import app

        persistence = app.state.persistence_service
        with persistence._session_factory() as session:
            from app.db.repository import MissionRunRepository

            run_repo = MissionRunRepository(session)
            # Get mission ID from most recent run
            latest_run = run_repo.get(persistence.current_run_id)
            mission_id = latest_run.mission_id
            # Get all runs for this mission to verify ordering
            all_runs = run_repo.list_for_mission(mission_id, limit=50)
            run_ids = [r.run_id for r in all_runs]

        # Test list runs endpoint preserves ordering
        response = client.get(f"/api/missions/{mission_id}/runs?limit=10")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        returned_run_ids = [r["run_id"] for r in data["runs"]]
        # Should match the first N runs from our list (most recent first)
        assert returned_run_ids == run_ids[: len(returned_run_ids)]

        # Test with offset to get middle runs
        if len(run_ids) > 2:
            response = client.get(f"/api/missions/{mission_id}/runs?limit=1&offset=1")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            if data["runs"]:  # Should have exactly one run
                assert data["runs"][0]["run_id"] == run_ids[1]

    finally:
        close_test_client(client)


def test_history_endpoints_return_clean_404_for_missing_resources(
    isolated_db_config: DatabaseConfig,
):
    """Test that history endpoints return clean 404 responses for missing resources."""
    client = create_test_client(isolated_db_config)
    try:
        # Test GET /api/runs/{nonexistent_id}
        response = client.get("/api/runs/nonexistent-run-id-12345")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

        # Test GET /api/runs/{nonexistent_id}/snapshots
        response = client.get("/api/runs/nonexistent-run-id-12345/snapshots")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

        # Test GET /api/runs/{nonexistent_id}/audit
        response = client.get("/api/runs/nonexistent-run-id-12345/audit")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    finally:
        close_test_client(client)


def test_history_endpoints_return_valid_response_schemas(
    isolated_db_config: DatabaseConfig,
):
    """Test that history endpoints return responses that conform to their schemas."""
    client = create_test_client(isolated_db_config)
    try:
        # Create a run with some activity
        client.post("/api/mission/start")
        client.post("/api/mission/inject-anomaly")

        # Get the actual IDs
        from app.main import app

        persistence = app.state.persistence_service
        with persistence._session_factory() as session:
            from app.db.repository import MissionRunRepository

            run_repo = MissionRunRepository(session)
            run = run_repo.get(persistence.current_run_id)
            run_id = run.run_id
            mission_id = run.mission_id

        # Test mission runs list response schema
        response = client.get(f"/api/missions/{mission_id}/runs")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Check required top-level fields
        assert "mission_id" in data
        assert "runs" in data
        assert "limit" in data
        assert isinstance(data["mission_id"], str)
        assert isinstance(data["runs"], list)
        assert isinstance(data["limit"], int)
        # Check run items if any exist
        if data["runs"]:
            run = data["runs"][0]
            assert "run_id" in run
            assert "mission_id" in run
            assert "label" in run
            assert "seed_mission_id" in run
            assert "started_at" in run
            assert "ended_at" in run
            assert "final_status" in run

        # Test mission run detail response schema
        response = client.get(f"/api/runs/{run_id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "run_id" in data
        assert "mission_id" in data
        assert "label" in data
        assert "seed_mission_id" in data
        assert "started_at" in data
        assert "ended_at" in data
        assert "final_status" in data

        # Test snapshots list response schema
        response = client.get(f"/api/runs/{run_id}/snapshots")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "run_id" in data
        assert "snapshots" in data
        assert "limit" in data
        assert "offset" in data
        assert "total_snapshots_available" in data
        if data["snapshots"]:
            snapshot = data["snapshots"][0]
            assert "snapshot_id" in snapshot
            assert "sequence" in snapshot
            assert "status" in snapshot
            assert "elapsed_s" in snapshot
            assert "created_at" in snapshot
            assert "battery_pct" in snapshot or snapshot["battery_pct"] is None
            assert "temperature_c" in snapshot or snapshot["temperature_c"] is None
            assert "storage_pct" in snapshot or snapshot["storage_pct"] is None
            assert "anomaly_active" in snapshot

        # Test audit events list response schema
        response = client.get(f"/api/runs/{run_id}/audit")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "run_id" in data
        assert "audit_events" in data
        assert "limit" in data
        assert "offset" in data
        assert "total_audit_events_available" in data
        if data["audit_events"]:
            event = data["audit_events"][0]
            assert "audit_id" in event
            assert "event_type" in event
            assert "description" in event
            assert "timestamp" in event
            assert "sequence" in event

    finally:
        close_test_client(client)


def test_history_endpoints_handle_empty_collections_gracefully(
    isolated_db_config: DatabaseConfig,
):
    """Test that history endpoints handle empty collections correctly."""
    client = create_test_client(isolated_db_config)
    try:
        # Test with a mission that has no runs
        response = client.get("/api/missions/nonexistent-mission/runs")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["mission_id"] == "nonexistent-mission"
        assert data["runs"] == []
        assert data["limit"] == 50  # default limit

        # Create a run, then test snapshots/audit for a run that exists but has none
        client.post("/api/mission/start")

        from app.main import app

        persistence = app.state.persistence_service
        with persistence._session_factory() as session:
            from app.db.repository import MissionRunRepository

            run_repo = MissionRunRepository(session)
            run = run_repo.get(persistence.current_run_id)
            run_id = run.run_id

        # Test snapshots for fresh run (should have initial snapshot)
        response = client.get(f"/api/runs/{run_id}/snapshots")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["run_id"] == run_id
        assert isinstance(data["snapshots"], list)
        assert data["limit"] == 100
        assert data["offset"] == 0
        assert data["total_snapshots_available"] >= 1  # Should have at least initial

        # Test audit for fresh run (should have initial audit)
        response = client.get(f"/api/runs/{run_id}/audit")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["run_id"] == run_id
        assert isinstance(data["audit_events"], list)
        assert data["limit"] == 200
        assert data["offset"] == 0
        assert data["total_audit_events_available"] >= 1  # Should have at least initial

    finally:
        close_test_client(client)
