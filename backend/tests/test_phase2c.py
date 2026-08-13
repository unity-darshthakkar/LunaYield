"""Phase 2C test suite for mission run restoration and persistence.

These tests verify the restoration semantics, audit history handling,
reset after restoration, and deterministic AWAITING_APPROVAL normalization
implemented in Phase 2C.

All tests use the existing Phase 2A/2B test infrastructure with temporary
file-based SQLite databases via pytest tmp_path fixture.

Tests never touch backend/data/lunayield.db.
"""

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db import DatabaseConfig
from app.db.models import AuditEventRecord, MissionRunRecord, MissionSnapshotRecord
from app.db.repository import (
    AuditEventRepository,
    MissionRunRepository,
    MissionSnapshotRepository,
)
from app.schemas import MissionStatus
from app.services.mission import MissionService
from app.services.persistence import MissionPersistenceService

# ---------------------------------------------------------------------------
# Helper: create a fresh TestClient bound to a specific DatabaseConfig
# This simulates a full FastAPI application startup (lifespan).
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


# ---------------------------------------------------------------------------
# Core restoration tests - these require TWO startups against SAME DB file
# ---------------------------------------------------------------------------


def test_empty_db_first_startup_creates_one_unfinished_run(
    isolated_db_config: DatabaseConfig,
):
    """First startup against empty DB creates exactly one unfinished run
    with initial snapshot and audit.
    """
    client = create_test_client(isolated_db_config)
    try:
        ps = get_persistence_service(client)
        run_id = ps.current_run_id

        assert run_id is not None

        # Verify run in DB
        session_factory = get_session_factory(client)
        with session_factory() as session:
            run_repo = MissionRunRepository(session)
            run = run_repo.get(run_id)
            assert run is not None
            assert run.run_id == run_id
            assert run.ended_at is None  # unfinished
            assert run.final_status is None

        # Verify initial snapshot (sequence=1, IDLE)
        with session_factory() as session:
            snap_repo = MissionSnapshotRepository(session)
            snaps = snap_repo.list_for_run(run_id)
            assert len(snaps) == 1
            assert snaps[0].sequence == 1
            assert snaps[0].status == MissionStatus.IDLE.value

        # Verify initial audit event (mission.initialized from seed)
        with session_factory() as session:
            audit_repo = AuditEventRepository(session)
            audits = audit_repo.list_for_run(run_id)
            assert len(audits) == 1
            assert audits[0].event_type == "mission.initialized"
            assert audits[0].sequence == 1
    finally:
        close_test_client(client)


def test_second_startup_restores_same_unfinished_run(
    isolated_db_config: DatabaseConfig,
):
    """Second startup against SAME DB restores the same unfinished run
    (no new run created).
    """
    # First startup
    client1 = create_test_client(isolated_db_config)
    ps1 = get_persistence_service(client1)
    first_run_id = ps1.current_run_id
    assert first_run_id is not None
    close_test_client(client1)

    # Second startup - NEW client, SAME db_config (same file)
    client2 = create_test_client(isolated_db_config)
    try:
        ps2 = get_persistence_service(client2)
        second_run_id = ps2.current_run_id

        # Must be the SAME run_id
        assert second_run_id == first_run_id, (
            "Second startup must restore existing unfinished run"
        )

        # Verify no NEW run was created
        session_factory = get_session_factory(client2)
        with session_factory() as session:
            run_repo = MissionRunRepository(session)
            runs = run_repo.list_for_mission(
                runs_list_mission_id(session, first_run_id), limit=10
            )
            # Exactly one run total
            assert len(runs) == 1
            assert runs[0].run_id == first_run_id
    finally:
        close_test_client(client2)


def test_latest_unfinished_run_selected_when_multiple_exist(
    isolated_db_config: DatabaseConfig,
):
    """When multiple unfinished runs exist, latest (by started_at, then id)
    is selected on startup.
    """
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

    # Manually create a SECOND valid unfinished run with proper snapshot
    # (simulating a complete run that was in progress)
    with session_factory() as session:
        run_repo = MissionRunRepository(session)
        run2 = run_repo.create(
            mission_id=mission_id,
            label="Shackleton Rim Survey — Alpha",
            seed_mission_id=mission_id,
        )
        session.commit()
        run2_id = run2.run_id

        # Create a valid snapshot for run2
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
        snap = MissionSnapshotRecord(
            run_id=run2_id,
            sequence=1,
            status=MissionStatus.IDLE.value,
            elapsed_s=0,
            resources_json=snap_json_resources,
            active_route_json=snap_json_route,
            anomaly_active=False,
        )
        session.add(snap)

        # Create initial audit event for run2
        from datetime import UTC, datetime

        audit = AuditEventRecord(
            run_id=run2_id,
            sequence=1,
            event_type="mission.initialized",
            description="Mission scenario loaded from seed data.",
            timestamp=datetime.now(UTC),
            metadata_json=json.dumps(
                {"mission_id": mission_id}, separators=(",", ":"), sort_keys=True
            ),
        )
        session.add(audit)
        session.commit()

    # Third startup - should select the LATEST unfinished (run2)
    client3 = create_test_client(isolated_db_config)
    try:
        ps3 = get_persistence_service(client3)
        assert ps3.current_run_id == run2_id, "Must select latest unfinished run"
    finally:
        close_test_client(client3)


def test_ended_run_ignored_on_startup(isolated_db_config: DatabaseConfig):
    """Ended runs are ignored; startup picks latest unfinished or creates new."""
    # First startup
    client1 = create_test_client(isolated_db_config)
    ps1 = get_persistence_service(client1)
    run1_id = ps1.current_run_id
    with get_session_factory(client1)() as session:
        run = session.exec(
            select(MissionRunRecord).where(MissionRunRecord.run_id == run1_id)
        ).first()
        # mission_id = run.mission_id  # not used
    close_test_client(client1)

    # Manually END the first run
    with get_session_factory(client1)() as session:
        run_repo = MissionRunRepository(session)
        run_repo.mark_ended(run1_id, "RUNNING")
        session.commit()

    # Second startup - no unfinished runs exist, so NEW run created
    client2 = create_test_client(isolated_db_config)
    try:
        ps2 = get_persistence_service(client2)

        # Must be a DIFFERENT run_id
        assert ps2.current_run_id != run1_id

        # Old run is ended
        with get_session_factory(client2)() as session:
            run = session.exec(
                select(MissionRunRecord).where(MissionRunRecord.run_id == run1_id)
            ).first()
            assert run.ended_at is not None
            assert run.final_status == "RUNNING"

        # New run is unfinished
        with get_session_factory(client2)() as session:
            run = session.exec(
                select(MissionRunRecord).where(
                    MissionRunRecord.run_id == ps2.current_run_id
                )
            ).first()
            assert run.ended_at is None
    finally:
        close_test_client(client2)


# ---------------------------------------------------------------------------
# Restoration detail tests - verify actual restored state matches snapshot
# ---------------------------------------------------------------------------


def test_restored_mission_state_matches_latest_snapshot(
    isolated_db_config: DatabaseConfig,
):
    """Restored mission status/resources/elapsed/active_route/anomaly
    must match latest snapshot.
    """
    # First startup + make some transitions to create distinct snapshot
    client1 = create_test_client(isolated_db_config)
    client1.post("/api/mission/start")
    client1.post("/api/mission/inject-anomaly")

    ps1 = get_persistence_service(client1)
    run_id = ps1.current_run_id

    # Capture exact snapshot values
    with get_session_factory(client1)() as session:
        snap_repo = MissionSnapshotRepository(session)
        latest = snap_repo.get_latest_for_run(run_id)
        expected_status = latest.status
        expected_elapsed = latest.elapsed_s
        expected_resources = json.loads(latest.resources_json)
        expected_route = json.loads(latest.active_route_json)
        expected_anomaly = latest.anomaly_active

    close_test_client(client1)

    # Second startup - restores from that snapshot
    client2 = create_test_client(isolated_db_config)
    try:
        ms2 = get_mission_service(client2)
        mission = ms2.get_mission()

        assert mission.status.value == expected_status
        assert mission.elapsed_s == expected_elapsed
        assert mission.anomaly_active == expected_anomaly

        # Resources
        assert mission.resources.battery_pct == expected_resources["battery_pct"]
        assert mission.resources.storage_pct == expected_resources["storage_pct"]
        assert mission.resources.temperature_c == expected_resources["temperature_c"]
        assert (
            mission.resources.comm_window_remaining_s
            == expected_resources["comm_window_remaining_s"]
        )
        assert (
            mission.resources.op_time_remaining_s
            == expected_resources["op_time_remaining_s"]
        )

        # Active route
        assert len(mission.active_route.waypoints) == len(expected_route["waypoints"])
        for wp, exp_wp in zip(
            mission.active_route.waypoints, expected_route["waypoints"]
        ):
            assert wp.id == exp_wp["id"]
            assert wp.x == exp_wp["x"]
            assert wp.y == exp_wp["y"]
            assert wp.label == exp_wp["label"]
    finally:
        close_test_client(client2)


def test_audit_history_restored_without_duplication(isolated_db_config: DatabaseConfig):
    """Audit history reconstructed in sequence order, no duplication after restart."""
    # First startup + transitions
    client1 = create_test_client(isolated_db_config)
    client1.post("/api/mission/start")
    client1.post("/api/mission/pause")
    client1.post("/api/mission/resume")

    ps1 = get_persistence_service(client1)
    run_id = ps1.current_run_id

    # Capture audit events before restart
    with get_session_factory(client1)() as session:
        audit_repo = AuditEventRepository(session)
        audits_before = audit_repo.list_for_run(run_id)
        event_ids_before = [e.event_id for e in audits_before]
        sequences_before = [e.sequence for e in audits_before]

    close_test_client(client1)

    # Second startup
    client2 = create_test_client(isolated_db_config)
    try:
        with get_session_factory(client2)() as session:
            audit_repo = AuditEventRepository(session)
            audits_after = audit_repo.list_for_run(run_id)
            event_ids_after = [e.event_id for e in audits_after]
            sequences_after = [e.sequence for e in audits_after]

        # Same events, same order
        assert event_ids_after == event_ids_before
        assert sequences_after == sequences_before

        # All unique
        assert len(event_ids_after) == len(set(event_ids_after))

        # Monotonic sequences 1..N
        assert sequences_after == list(range(1, len(sequences_after) + 1))
    finally:
        close_test_client(client2)


def test_persistence_current_run_id_matches_restored_run(
    isolated_db_config: DatabaseConfig,
):
    """Persistence service current_run_id matches the restored run
    after second startup.
    """
    client1 = create_test_client(isolated_db_config)
    ps1 = get_persistence_service(client1)
    run_id = ps1.current_run_id
    close_test_client(client1)

    client2 = create_test_client(isolated_db_config)
    try:
        ps2 = get_persistence_service(client2)
        assert ps2.current_run_id == run_id
    finally:
        close_test_client(client2)


# ---------------------------------------------------------------------------
# Post-restore transition tests
# ---------------------------------------------------------------------------


def test_first_transition_after_restore_appends_to_same_run(
    isolated_db_config: DatabaseConfig,
):
    """First transition after restore appends to SAME run,
    continues snapshot/audit sequences.
    """
    # First startup + transitions to ANOMALY
    client1 = create_test_client(isolated_db_config)
    client1.post("/api/mission/start")
    client1.post("/api/mission/inject-anomaly")

    ps1 = get_persistence_service(client1)
    run_id = ps1.current_run_id

    # Count before restart
    with get_session_factory(client1)() as session:
        snap_repo = MissionSnapshotRepository(session)
        snaps_before = snap_repo.list_for_run(run_id)
        audit_repo = AuditEventRepository(session)
        audits_before = audit_repo.list_for_run(run_id)
        snap_count_before = len(snaps_before)
        audit_count_before = len(audits_before)
        max_snap_seq = max(s.sequence for s in snaps_before)
        max_audit_seq = max(e.sequence for e in audits_before)

    close_test_client(client1)

    # Second startup + ONE valid transition from ANOMALY
    client2 = create_test_client(isolated_db_config)
    try:
        # From ANOMALY, the valid transition is POST /api/plans/generate
        response = client2.post("/api/plans/generate")
        assert response.status_code == 200, f"plans/generate failed: {response.text}"

        with get_session_factory(client2)() as session:
            snap_repo = MissionSnapshotRepository(session)
            snaps_after = snap_repo.list_for_run(run_id)
            audit_repo = AuditEventRepository(session)
            audits_after = audit_repo.list_for_run(run_id)

        # Exactly one more snapshot
        assert len(snaps_after) == snap_count_before + 1

        # Exactly TWO new audit events (planning.started + plans.generated)
        assert len(audits_after) == audit_count_before + 2

        # New snapshot has sequence = max_seq + 1
        new_snap = [s for s in snaps_after if s.sequence > max_snap_seq][0]
        assert new_snap.sequence == max_snap_seq + 1
        # plans/generate transitions ANOMALY -> PLANNING -> AWAITING_APPROVAL
        assert new_snap.status == MissionStatus.AWAITING_APPROVAL.value

        # New audit events have sequences max_seq + 1 and max_seq + 2
        new_audits = [e for e in audits_after if e.sequence > max_audit_seq]
        assert len(new_audits) == 2
        new_audits_sorted = sorted(new_audits, key=lambda e: e.sequence)
        assert new_audits_sorted[0].sequence == max_audit_seq + 1
        assert new_audits_sorted[0].event_type == "planning.started"
        assert new_audits_sorted[1].sequence == max_audit_seq + 2
        assert new_audits_sorted[1].event_type == "plans.generated"

        # Still same run_id
        ps2 = get_persistence_service(client2)
        assert ps2.current_run_id == run_id

        # No new MissionRunRecord created
        with get_session_factory(client2)() as session:
            run_repo = MissionRunRepository(session)
            runs = run_repo.list_for_mission(
                runs_list_mission_id(session, run_id), limit=20
            )
            # Should still be exactly 1 run total
            assert len(runs) == 1
            assert runs[0].run_id == run_id
    finally:
        close_test_client(client2)


def test_snapshot_sequence_continues_monotonically_after_restore(
    isolated_db_config: DatabaseConfig,
):
    """Snapshot sequences are strictly increasing without gaps across restarts."""
    client1 = create_test_client(isolated_db_config)
    client1.post("/api/mission/start")
    client1.post("/api/mission/pause")
    client1.post("/api/mission/resume")
    ps1 = get_persistence_service(client1)
    run_id = ps1.current_run_id
    close_test_client(client1)

    client2 = create_test_client(isolated_db_config)
    try:
        client2.post("/api/mission/inject-anomaly")
        client2.post("/api/mission/pause")

        with get_session_factory(client2)() as session:
            snap_repo = MissionSnapshotRepository(session)
            snaps = snap_repo.list_for_run(run_id)
            sequences = [s.sequence for s in snaps]

        # Should be 1, 2, 3, 4, 5... with no gaps
        assert sequences == list(range(1, len(sequences) + 1))
    finally:
        close_test_client(client2)


def test_audit_sequence_continues_monotonically_after_restore(
    isolated_db_config: DatabaseConfig,
):
    """Audit sequences are strictly increasing without gaps across restarts."""
    client1 = create_test_client(isolated_db_config)
    client1.post("/api/mission/start")
    client1.post("/api/mission/pause")
    ps1 = get_persistence_service(client1)
    run_id = ps1.current_run_id
    close_test_client(client1)

    client2 = create_test_client(isolated_db_config)
    try:
        client2.post("/api/mission/resume")
        client2.post("/api/mission/inject-anomaly")

        with get_session_factory(client2)() as session:
            audit_repo = AuditEventRepository(session)
            audits = audit_repo.list_for_run(run_id)
            sequences = [e.sequence for e in audits]

        assert sequences == list(range(1, len(sequences) + 1))
    finally:
        close_test_client(client2)


# ---------------------------------------------------------------------------
# AWAITING_APPROVAL normalization test - must actually persist and restore
# ---------------------------------------------------------------------------


def test_awaiting_approval_normalizes_to_anomaly_on_restore(
    isolated_db_config: DatabaseConfig,
):
    """Persisted snapshot with AWAITING_APPROVAL status must restore as ANOMALY
    (candidate_plans not persisted).
    """
    # First startup
    client1 = create_test_client(isolated_db_config)
    client1.post("/api/mission/start")
    client1.post("/api/mission/inject-anomaly")
    client1.post("/api/plans/generate")  # Reaches AWAITING_APPROVAL

    ps1 = get_persistence_service(client1)
    run_id = ps1.current_run_id

    # Manually OVERWRITE the latest snapshot status to AWAITING_APPROVAL
    # (simulating a persisted snapshot that was AWAITING_APPROVAL before crash)
    with get_session_factory(client1)() as session:
        snap_repo = MissionSnapshotRepository(session)
        latest = snap_repo.get_latest_for_run(run_id)
        # Update status in DB directly
        latest.status = "AWAITING_APPROVAL"
        session.add(latest)
        session.commit()

    # Capture the mission state at this point (AWAITING_APPROVAL with candidate_plans)
    ms1 = get_mission_service(client1)
    assert ms1.get_mission().status == MissionStatus.AWAITING_APPROVAL
    assert len(ms1.get_mission().candidate_plans) > 0

    close_test_client(client1)

    # Second startup - should NORMALIZE AWAITING_APPROVAL -> ANOMALY
    client2 = create_test_client(isolated_db_config)
    try:
        ms2 = get_mission_service(client2)
        restored_mission = ms2.get_mission()

        # Status must be ANOMALY, not AWAITING_APPROVAL
        assert restored_mission.status == MissionStatus.ANOMALY

        # Candidate plans must be empty (not persisted)
        assert restored_mission.candidate_plans == []

        # anomaly_active should be True (from the anomaly injection snapshot)
        assert restored_mission.anomaly_active is True

        # Run ID preserved
        ps2 = get_persistence_service(client2)
        assert ps2.current_run_id == run_id
    finally:
        close_test_client(client2)


# ---------------------------------------------------------------------------
# Reset after restoration tests
# ---------------------------------------------------------------------------


def test_reset_after_restore_ends_restored_run_creates_new(
    isolated_db_config: DatabaseConfig,
):
    """Reset after restore ends the restored run and creates a new run."""
    # First startup + restore
    client1 = create_test_client(isolated_db_config)
    client1.post("/api/mission/start")
    close_test_client(client1)

    client2 = create_test_client(isolated_db_config)
    try:
        ps2 = get_persistence_service(client2)
        restored_run_id = ps2.current_run_id

        # Reset via API
        client2.post("/api/mission/reset")

        # New run created
        new_run_id = ps2.current_run_id
        assert new_run_id != restored_run_id

        # Old run ended
        with get_session_factory(client2)() as session:
            run_repo = MissionRunRepository(session)
            old_run = run_repo.get(restored_run_id)
            assert old_run.ended_at is not None
            assert old_run.final_status is not None

        # New run unfinished
        with get_session_factory(client2)() as session:
            run_repo = MissionRunRepository(session)
            new_run = run_repo.get(new_run_id)
            assert new_run.ended_at is None
            assert new_run.final_status is None
    finally:
        close_test_client(client2)


def test_restart_after_reset_restores_new_unfinished_run(
    isolated_db_config: DatabaseConfig,
):
    """Restart after reset restores the NEW unfinished run (not the old ended one)."""
    # Startup -> start -> reset
    client1 = create_test_client(isolated_db_config)
    client1.post("/api/mission/start")
    client1.post("/api/mission/reset")

    ps1 = get_persistence_service(client1)
    reset_run_id = ps1.current_run_id
    close_test_client(client1)

    # THIRD startup - should restore the run created by reset
    client3 = create_test_client(isolated_db_config)
    try:
        ps3 = get_persistence_service(client3)
        assert ps3.current_run_id == reset_run_id

        # Verify it's the correct run
        with get_session_factory(client3)() as session:
            run_repo = MissionRunRepository(session)
            run = run_repo.get(reset_run_id)
            assert run.ended_at is None  # unfinished
    finally:
        close_test_client(client3)


# ---------------------------------------------------------------------------
# Edge case: unfinished run with NO snapshot
# ---------------------------------------------------------------------------


def test_unfinished_run_with_no_snapshot_ends_bad_run_creates_fresh(
    isolated_db_config: DatabaseConfig,
):
    """Unfinished run with no snapshot -> ends bad run with RESTORATION_FAILED,
    creates fresh run.
    """
    # First startup creates run + snapshot
    client1 = create_test_client(isolated_db_config)
    ps1 = get_persistence_service(client1)
    run_id = ps1.current_run_id
    close_test_client(client1)

    # Manually DELETE the snapshot for that run (simulating corruption)
    with get_session_factory(client1)() as session:
        stmt = select(MissionSnapshotRecord).where(
            MissionSnapshotRecord.run_id == run_id
        )
        snapshots = session.exec(stmt).all()
        for snap in snapshots:
            session.delete(snap)
        session.commit()
        # Verify none left
        assert session.exec(stmt).first() is None

    # Second startup - no snapshot for unfinished run
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

        # New run has initial snapshot
        with get_session_factory(client2)() as session:
            snap_repo = MissionSnapshotRepository(session)
            snaps = snap_repo.list_for_run(ps2.current_run_id)
            assert len(snaps) == 1
            assert snaps[0].sequence == 1
            assert snaps[0].status == MissionStatus.IDLE.value
    finally:
        close_test_client(client2)


# ---------------------------------------------------------------------------
# Edge case: invalid persisted snapshot (corrupt JSON)
# ---------------------------------------------------------------------------


def test_invalid_persisted_snapshot_fails_safely_creates_fresh_run(
    isolated_db_config: DatabaseConfig,
):
    """Invalid/corrupt snapshot JSON -> falls back safely, creates fresh run."""
    client1 = create_test_client(isolated_db_config)
    client1.post("/api/mission/start")
    ps1 = get_persistence_service(client1)
    run_id = ps1.current_run_id
    close_test_client(client1)

    # Corrupt the snapshot JSON
    with get_session_factory(client1)() as session:
        stmt = select(MissionSnapshotRecord).where(
            MissionSnapshotRecord.run_id == run_id
        )
        latest = session.exec(
            stmt.order_by(MissionSnapshotRecord.sequence.desc())
        ).first()
        # Make resources_json invalid JSON
        latest.resources_json = "{ not valid json }"
        session.add(latest)
        session.commit()

    # Second startup - should handle gracefully
    client2 = create_test_client(isolated_db_config)
    try:
        ps2 = get_persistence_service(client2)

        # New current_run_id must be different from bad run
        new_run_id = ps2.current_run_id
        assert new_run_id != run_id

        # Bad run ended with RESTORATION_FAILED
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
        assert mission.anomaly_active is False
        assert mission.candidate_plans == []

        # Fresh run has initial snapshot sequence 1
        with get_session_factory(client2)() as session:
            snap_repo = MissionSnapshotRepository(session)
            snaps = snap_repo.list_for_run(new_run_id)
            assert len(snaps) == 1
            assert snaps[0].sequence == 1
            assert snaps[0].status == MissionStatus.IDLE.value
    finally:
        close_test_client(client2)


# ---------------------------------------------------------------------------
# Cross-session persistence (separate TestClient instances, same DB file)
# ---------------------------------------------------------------------------


def test_persistence_survives_separate_testclient_sessions(
    isolated_db_config: DatabaseConfig,
):
    """Data persisted via one TestClient is visible to another TestClient
    against same DB file.
    """
    # Session 1
    client1 = create_test_client(isolated_db_config)
    client1.post("/api/mission/start")
    ps1 = get_persistence_service(client1)
    run_id = ps1.current_run_id
    close_test_client(client1)

    # Session 2 - NEW TestClient, SAME db_config
    client2 = create_test_client(isolated_db_config)
    try:
        # Should restore the same run
        ps2 = get_persistence_service(client2)
        assert ps2.current_run_id == run_id

        # Verify snapshot visible
        with get_session_factory(client2)() as session:
            snap_repo = MissionSnapshotRepository(session)
            snaps = snap_repo.list_for_run(run_id)
            # initial + start = 2
            assert len(snaps) >= 2

        # Can continue transitions
        client2.post("/api/mission/pause")

        with get_session_factory(client2)() as session:
            snap_repo = MissionSnapshotRepository(session)
            snaps = snap_repo.list_for_run(run_id)
            assert len(snaps) >= 3
            paused = [s for s in snaps if s.status == MissionStatus.PAUSED.value]
            assert len(paused) == 1
    finally:
        close_test_client(client2)


# ---------------------------------------------------------------------------
# Dev database isolation
# ---------------------------------------------------------------------------


def test_tests_never_touch_dev_database(isolated_db_config: DatabaseConfig):
    """Verify test suite does not create or modify backend/data/lunayield.db."""
    dev_config = DatabaseConfig.development()
    dev_db_path = dev_config.url.replace("sqlite:///", "")

    dev_exists_before = os.path.exists(dev_db_path)
    dev_mtime_before = os.path.getmtime(dev_db_path) if dev_exists_before else None

    client = create_test_client(isolated_db_config)
    try:
        client.post("/api/mission/start")
    finally:
        close_test_client(client)

    dev_exists_after = os.path.exists(dev_db_path)
    dev_mtime_after = os.path.getmtime(dev_db_path) if dev_exists_after else None

    if dev_exists_before:
        assert dev_exists_after == dev_exists_before
        assert dev_mtime_after == dev_mtime_before
    else:
        assert not dev_exists_after
