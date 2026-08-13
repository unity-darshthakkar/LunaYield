"""Phase 2D test suite for restoration hardening.

These tests verify the enhanced validation and safety mechanisms
implemented in Phase 2D for mission run restoration, including:
- Validation of restored snapshots before applying them
- Safe handling of malformed or incomplete persisted audit history
- Deterministic startup recovery when multiple unfinished runs exist
- Ensuring failed restoration never leaves partial in-memory state

All tests use the existing Phase 2A/2B/2C test infrastructure with temporary
file-based SQLite databases via pytest tmp_path fixture.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db import DatabaseConfig
from app.db.models import AuditEventRecord, MissionRunRecord, MissionSnapshotRecord
from app.db.repository import (
    AuditEventRepository,
    MissionRunRepository,
)
from app.schemas import (
    MissionStatus,
)
from app.services.mission import MissionService
from app.services.persistence import MissionPersistenceService

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


def get_persistence_service(client: TestClient) -> MissionPersistenceService:
    """Get persistence service from a TestClient's app state."""
    return client.app.state.persistence_service


def get_mission_service(client: TestClient) -> MissionService:
    """Get mission service from a TestClient's app state."""
    return client.app.state.mission_service


def get_session_factory(client: TestClient):
    """Get session factory from app state."""
    return client.app.state.db_session_factory


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_db_config(tmp_path: Path) -> DatabaseConfig:
    """Provide isolated test database configuration using temp file."""
    return DatabaseConfig.test_temporary(tmp_path)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def runs_list_mission_id(session: Session, run_id: str) -> str:
    """Helper to get mission_id from a run."""
    run = session.exec(
        select(MissionRunRecord).where(MissionRunRecord.run_id == run_id)
    ).first()
    return run.mission_id


def create_valid_snapshot(
    session: Session,
    run_id: str,
    sequence: int,
    status: str,
    elapsed_s: int = 0,
    anomaly_active: bool = False,
) -> MissionSnapshotRecord:
    """Create a valid snapshot with proper JSON structure."""
    # Use same structure as seed mission
    snap_json_resources = json.dumps(
        {
            "battery_pct": 100.0,
            "storage_pct": 0.0,
            "temperature_c": -40.0,
            "comm_window_remaining_s": 7200,
            "op_time_remaining_s": 28800,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    snap_json_route = json.dumps(
        {
            "waypoints": [
                {
                    "id": "wp-base",
                    "x": 0.1,
                    "y": 0.1,
                    "label": "Base Camp",
                    "is_science_target": False,
                },
                {
                    "id": "wp-crater-a",
                    "x": 0.3,
                    "y": 0.4,
                    "label": "Crater A Rim",
                    "is_science_target": True,
                },
                {
                    "id": "wp-ice-deposit",
                    "x": 0.5,
                    "y": 0.6,
                    "label": "Ice Deposit Site",
                    "is_science_target": True,
                },
                {
                    "id": "wp-ridge",
                    "x": 0.7,
                    "y": 0.5,
                    "label": "Ridge Observation Point",
                    "is_science_target": True,
                },
                {
                    "id": "wp-return",
                    "x": 0.1,
                    "y": 0.1,
                    "label": "Base Camp (Return)",
                    "is_science_target": False,
                },
            ]
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    snapshot = MissionSnapshotRecord(
        run_id=run_id,
        sequence=sequence,
        status=status,
        elapsed_s=elapsed_s,
        resources_json=snap_json_resources,
        active_route_json=snap_json_route,
        anomaly_active=anomaly_active,
    )
    session.add(snapshot)
    return snapshot


def create_valid_audit_event(
    session: Session,
    run_id: str,
    sequence: int,
    event_type: str,
    description: str,
    timestamp: datetime,
    metadata: dict | None = None,
) -> AuditEventRecord:
    """Create a valid audit event record."""
    audit = AuditEventRecord(
        run_id=run_id,
        sequence=sequence,
        event_type=event_type,
        description=description,
        timestamp=timestamp,
        metadata_json=json.dumps(
            {"mission_id": "test-mission", **(metadata or {})},
            separators=(",", ":"),
            sort_keys=True,
        ),
    )
    session.add(audit)
    return audit


# ---------------------------------------------------------------------------
# Phase 2D Restoration Hardening Tests
# ---------------------------------------------------------------------------


def test_restored_mission_validation_negative_elapsed_s(
    isolated_db_config: DatabaseConfig,
):
    """Test that restored mission with negative elapsed_s fails safe."""
    # First startup creates run + snapshot
    client1 = create_test_client(isolated_db_config)
    ps1 = get_persistence_service(client1)
    run_id = ps1.current_run_id
    close_test_client(client1)

    # Manually corrupt the snapshot with negative elapsed_s
    with get_session_factory(client1)() as session:
        stmt = select(MissionSnapshotRecord).where(
            MissionSnapshotRecord.run_id == run_id
        )
        latest = session.exec(
            stmt.order_by(MissionSnapshotRecord.sequence.desc())
        ).first()
        latest.elapsed_s = -1  # Invalid negative value
        session.add(latest)
        session.commit()

    # Second startup should handle gracefully
    client2 = create_test_client(isolated_db_config)
    try:
        ps2 = get_persistence_service(client2)

        # Should be a DIFFERENT run (fresh run created)
        assert ps2.current_run_id != run_id

        # Old run marked as ended with RESTORATION_FAILED
        with get_session_factory(client2)() as session:
            run_repo = MissionRunRepository(session)
            old_run = run_repo.get(run_id)
            assert old_run.ended_at is not None
            assert old_run.final_status == "RESTORATION_FAILED"

        # Fresh mission is IDLE
        ms2 = get_mission_service(client2)
        mission = ms2.get_mission()
        assert mission.status == MissionStatus.IDLE
        assert mission.elapsed_s == 0
    finally:
        close_test_client(client2)


def test_restored_mission_validation_out_of_bounds_battery(
    isolated_db_config: DatabaseConfig,
):
    """Test that restored mission with out-of-bounds battery_pct fails safe."""
    # First startup creates run + snapshot
    client1 = create_test_client(isolated_db_config)
    ps1 = get_persistence_service(client1)
    run_id = ps1.current_run_id
    close_test_client(client1)

    # Manually corrupt the snapshot with invalid battery_pct (>100)
    with get_session_factory(client1)() as session:
        stmt = select(MissionSnapshotRecord).where(
            MissionSnapshotRecord.run_id == run_id
        )
        latest = session.exec(
            stmt.order_by(MissionSnapshotRecord.sequence.desc())
        ).first()
        # Corrupt resources_json to have battery_pct = 150.0
        resources_dict = {
            "battery_pct": 150.0,
            "storage_pct": 0.0,
            "temperature_c": -40.0,
            "comm_window_remaining_s": 7200,
            "op_time_remaining_s": 28800,
        }
        latest.resources_json = json.dumps(
            resources_dict, separators=(",", ":"), sort_keys=True
        )
        session.add(latest)
        session.commit()

    # Second startup should handle gracefully
    client2 = create_test_client(isolated_db_config)
    try:
        ps2 = get_persistence_service(client2)

        # Should be a DIFFERENT run (fresh run created)
        assert ps2.current_run_id != run_id

        # Old run marked as ended with RESTORATION_FAILED
        with get_session_factory(client2)() as session:
            run_repo = MissionRunRepository(session)
            old_run = run_repo.get(run_id)
            assert old_run.ended_at is not None
            assert old_run.final_status == "RESTORATION_FAILED"

        # Fresh mission is IDLE
        ms2 = get_mission_service(client2)
        mission = ms2.get_mission()
        assert mission.status == MissionStatus.IDLE
        assert mission.resources.battery_pct == 100.0  # Seed value
    finally:
        close_test_client(client2)


def test_restored_mission_invalid_waypoint_coordinates(
    isolated_db_config: DatabaseConfig,
):
    """Test that restored mission with invalid waypoint coordinates fails safe."""
    # First startup creates run + snapshot
    client1 = create_test_client(isolated_db_config)
    ps1 = get_persistence_service(client1)
    run_id = ps1.current_run_id
    close_test_client(client1)

    # Manually corrupt the snapshot with invalid waypoint x coordinate (>1.0)
    with get_session_factory(client1)() as session:
        stmt = select(MissionSnapshotRecord).where(
            MissionSnapshotRecord.run_id == run_id
        )
        latest = session.exec(
            stmt.order_by(MissionSnapshotRecord.sequence.desc())
        ).first()
        # Corrupt active_route_json to have x = 1.5
        route_dict = {
            "waypoints": [
                {
                    "id": "wp-base",
                    "x": 1.5,  # Invalid: > 1.0
                    "y": 0.1,
                    "label": "Base Camp",
                    "is_science_target": False,
                }
            ]
        }
        latest.active_route_json = json.dumps(
            route_dict, separators=(",", ":"), sort_keys=True
        )
        session.add(latest)
        session.commit()

    # Second startup should handle gracefully
    client2 = create_test_client(isolated_db_config)
    try:
        ps2 = get_persistence_service(client2)

        # Should be a DIFFERENT run (fresh run created)
        assert ps2.current_run_id != run_id

        # Old run marked as ended with RESTORATION_FAILED
        with get_session_factory(client2)() as session:
            run_repo = MissionRunRepository(session)
            old_run = run_repo.get(run_id)
            assert old_run.ended_at is not None
            assert old_run.final_status == "RESTORATION_FAILED"

        # Fresh mission is IDLE
        ms2 = get_mission_service(client2)
        mission = ms2.get_mission()
        assert mission.status == MissionStatus.IDLE
        # Active route should be reset to original (seed) route
        assert len(mission.active_route.waypoints) > 0
    finally:
        close_test_client(client2)


def test_restored_mission_invalid_status(
    isolated_db_config: DatabaseConfig,
):
    """Test that restored mission with invalid status fails safe."""
    # First startup creates run + snapshot
    client1 = create_test_client(isolated_db_config)
    ps1 = get_persistence_service(client1)
    run_id = ps1.current_run_id
    close_test_client(client1)

    # Manually corrupt the snapshot with invalid status
    with get_session_factory(client1)() as session:
        stmt = select(MissionSnapshotRecord).where(
            MissionSnapshotRecord.run_id == run_id
        )
        latest = session.exec(
            stmt.order_by(MissionSnapshotRecord.sequence.desc())
        ).first()
        latest.status = "INVALID_STATUS"  # Not a valid MissionStatus
        session.add(latest)
        session.commit()

    # Second startup should handle gracefully
    client2 = create_test_client(isolated_db_config)
    try:
        ps2 = get_persistence_service(client2)

        # Should be a DIFFERENT run (fresh run created)
        assert ps2.current_run_id != run_id

        # Old run marked as ended with RESTORATION_FAILED
        with get_session_factory(client2)() as session:
            run_repo = MissionRunRepository(session)
            old_run = run_repo.get(run_id)
            assert old_run.ended_at is not None
            assert old_run.final_status == "RESTORATION_FAILED"

        # Fresh mission is IDLE
        ms2 = get_mission_service(client2)
        mission = ms2.get_mission()
        assert mission.status == MissionStatus.IDLE
    finally:
        close_test_client(client2)


def test_malformed_audit_event_fails_safe(
    isolated_db_config: DatabaseConfig,
):
    """Test that malformed audit event JSON fails safe during reconstruction."""
    # First startup creates run + snapshot + audit
    client1 = create_test_client(isolated_db_config)
    client1.post("/api/mission/start")
    ps1 = get_persistence_service(client1)
    run_id = ps1.current_run_id
    close_test_client(client1)

    # Manually corrupt the audit event JSON (make it invalid)
    with get_session_factory(client1)() as session:
        stmt = select(AuditEventRecord).where(AuditEventRecord.run_id == run_id)
        audit = session.exec(stmt.order_by(AuditEventRecord.sequence.desc())).first()
        # Make metadata_json invalid JSON
        audit.metadata_json = "{ not valid json }"
        session.add(audit)
        session.commit()

    # Second startup should handle gracefully
    client2 = create_test_client(isolated_db_config)
    try:
        ps2 = get_persistence_service(client2)

        # Should be a DIFFERENT run (fresh run created)
        assert ps2.current_run_id != run_id

        # Old run marked as ended with RESTORATION_FAILED
        with get_session_factory(client2)() as session:
            run_repo = MissionRunRepository(session)
            old_run = run_repo.get(run_id)
            assert old_run.ended_at is not None
            assert old_run.final_status == "RESTORATION_FAILED"

        # Fresh mission is IDLE
        ms2 = get_mission_service(client2)
        mission = ms2.get_mission()
        assert mission.status == MissionStatus.IDLE
    finally:
        close_test_client(client2)


def test_deterministic_recovery_multiple_unfinished_same_started_at(
    isolated_db_config: DatabaseConfig,
):
    """When multiple unfinished runs have same started_at, higher id wins."""
    # First startup
    client1 = create_test_client(isolated_db_config)
    ps1 = get_persistence_service(client1)
    run1_id = ps1.current_run_id
    # Get the mission_id from run1
    session_factory = get_session_factory(client1)
    with session_factory() as session:
        run1 = session.exec(
            select(MissionRunRecord).where(MissionRunRecord.run_id == run1_id)
        ).first()
        mission_id = run1.mission_id
    close_test_client(client1)

    # Manually create a SECOND unfinished run with SAME started_at but higher id
    # We'll simulate this by setting the same started_at but letting id auto-increment
    with session_factory() as session:
        run_repo = MissionRunRepository(session)
        run2 = run_repo.create(
            mission_id=mission_id,
            label="Shackleton Rim Survey — Beta",
            seed_mission_id=mission_id,
        )
        # Manually set the same started_at as run1 to test tie-breaking
        run2.started_at = run1.started_at
        session.add(run2)
        session.commit()
        run2_id = run2.run_id

        # Create a valid snapshot for run2
        create_valid_snapshot(session, run2_id, 1, MissionStatus.IDLE.value)

        # Create initial audit event for run2
        create_valid_audit_event(
            session,
            run2_id,
            1,
            "mission.initialized",
            "Mission scenario loaded from seed data.",
            datetime.now(UTC),
        )
        session.commit()

    # Third startup - should select the run with HIGHER id (run2)
    # when started_at is tied
    client3 = create_test_client(isolated_db_config)
    try:
        ps3 = get_persistence_service(client3)
        assert ps3.current_run_id == run2_id, (
            "When started_at is tied, should select run with higher id"
        )
    finally:
        close_test_client(client3)


def test_failed_restoration_no_partial_state(
    isolated_db_config: DatabaseConfig,
):
    """Test that failed restoration leaves MissionService in clean state
    (fresh seed).
    """
    # First startup creates run + snapshot
    client1 = create_test_client(isolated_db_config)
    ps1 = get_persistence_service(client1)
    run_id = ps1.current_run_id
    close_test_client(client1)

    # Corrupt snapshot with invalid data that will fail validation
    with get_session_factory(client1)() as session:
        stmt = select(MissionSnapshotRecord).where(
            MissionSnapshotRecord.run_id == run_id
        )
        latest = session.exec(
            stmt.order_by(MissionSnapshotRecord.sequence.desc())
        ).first()
        # Invalid temperature (below absolute zero)
        resources_dict = {
            "battery_pct": 100.0,
            "storage_pct": 0.0,
            "temperature_c": -300.0,  # Below absolute zero
            "comm_window_remaining_s": 7200,
            "op_time_remaining_s": 28800,
        }
        latest.resources_json = json.dumps(
            resources_dict, separators=(",", ":"), sort_keys=True
        )
        session.add(latest)
        session.commit()

    # Second startup - should fail restoration and create fresh run
    client2 = create_test_client(isolated_db_config)
    try:
        ps2 = get_persistence_service(client2)
        ms2 = get_mission_service(client2)

        # Should have a different run ID (fresh run)
        assert ps2.current_run_id != run_id

        # MissionService should contain a FRESH seed mission
        # (not partial restored state)
        mission = ms2.get_mission()
        assert mission.status == MissionStatus.IDLE
        assert mission.elapsed_s == 0
        assert mission.anomaly_active is False
        assert mission.candidate_plans == []
        assert len(mission.audit_trail) == 1  # Only mission.initialized
        assert mission.audit_trail[0].event_type == "mission.initialized"

        # Resources should be seed values
        assert mission.resources.battery_pct == 100.0
        assert mission.resources.storage_pct == 0.0
        assert mission.resources.temperature_c == -40.0
    finally:
        close_test_client(client2)


def test_empty_audit_events_handled_gracefully(
    isolated_db_config: DatabaseConfig,
):
    """Test that empty audit events list is handled correctly."""
    # First startup creates run + snapshot
    client1 = create_test_client(isolated_db_config)
    ps1 = get_persistence_service(client1)
    run_id = ps1.current_run_id
    close_test_client(client1)

    # Manually DELETE all audit events for that run (simulating corruption)
    with get_session_factory(client1)() as session:
        stmt = select(AuditEventRecord).where(AuditEventRecord.run_id == run_id)
        audit_events = session.exec(stmt).all()
        for audit in audit_events:
            session.delete(audit)
        session.commit()
        # Verify none left
        assert session.exec(stmt).first() is None

    # Second startup - should handle empty audit events gracefully
    client2 = create_test_client(isolated_db_config)
    try:
        ps2 = get_persistence_service(client2)

        # Should restore the same run (snapshot exists, no audit events is OK)
        assert ps2.current_run_id == run_id

        # Mission should be restored correctly
        ms2 = get_mission_service(client2)
        mission = ms2.get_mission()
        assert mission.status == MissionStatus.IDLE  # From snapshot
        assert mission.elapsed_s == 0
        assert mission.audit_trail == []  # Empty audit trail

        # Persistence service should have correct state
        with get_session_factory(client2)() as session:
            audit_repo = AuditEventRepository(session)
            audits = audit_repo.list_for_run(run_id)
            assert len(audits) == 0  # Confirmed empty in DB
    finally:
        close_test_client(client2)


def test_restoration_validation_does_not_affect_normal_operation(
    isolated_db_config: DatabaseConfig,
):
    """Test that the enhanced validation doesn't break normal restoration."""
    # Normal workflow: start -> transition -> restart
    client1 = create_test_client(isolated_db_config)
    client1.post("/api/mission/start")
    client1.post("/api/mission/inject-anomaly")
    close_test_client(client1)

    # Second startup should restore normally
    client2 = create_test_client(isolated_db_config)
    try:
        ms2 = get_mission_service(client2)
        mission = ms2.get_mission()

        # Should restore to ANOMALY state
        assert mission.status == MissionStatus.ANOMALY
        assert mission.anomaly_active is True
        assert mission.elapsed_s >= 0  # Should have some elapsed time

    finally:
        close_test_client(client2)
