"""Phase 2B test suite for mission run persistence and history API.

These tests verify the durability semantics, audit event handling, reset
behavior, and history API contract implemented in Phase 2B.

All tests use the existing Phase 2A test infrastructure with temporary
file-based SQLite databases via pytest tmp_path fixture.

Tests never touch backend/data/lunayield.db.
"""

import pytest
from fastapi.testclient import TestClient

from app.db import DatabaseConfig

# ---------------------------------------------------------------------------
# Helper fixtures using existing Phase 2A infrastructure
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_db_config(tmp_path: str) -> DatabaseConfig:
    """Provide isolated test database configuration using temp file."""
    return DatabaseConfig.test_temporary(tmp_path)


@pytest.fixture
def client_with_db(isolated_db_config: DatabaseConfig) -> TestClient:
    """TestClient bound to isolated test database.

    Uses the same pattern as conftest.client but with explicit db_config.
    """
    from app.main import app

    app.state.db_config = isolated_db_config
    with TestClient(app) as c:
        # Reset mission service for clean state
        mission_service = app.state.mission_service
        mission_service.reset()
        yield c
        mission_service.reset()
    # Cleanup
    if hasattr(app.state, "db_config"):
        delattr(app.state, "db_config")


# ---------------------------------------------------------------------------
# Startup persistence tests
# ---------------------------------------------------------------------------


def test_startup_creates_exactly_one_persisted_run(client_with_db: TestClient):
    """Application startup must create exactly one MissionRunRecord."""
    from app.services.persistence import MissionPersistenceService

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )
    run_id = persistence.current_run_id

    assert run_id is not None

    # Verify run is in database
    with persistence._session_factory() as session:
        from app.db.repository import MissionRunRepository

        run_repo = MissionRunRepository(session)
        run = run_repo.get(run_id)
        assert run is not None
        assert run.run_id == run_id


def test_startup_persists_initial_snapshot(client_with_db: TestClient):
    """Startup must persist an initial snapshot for the current run."""
    from app.services.persistence import MissionPersistenceService

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )
    run_id = persistence.current_run_id

    with persistence._session_factory() as session:
        from app.db.repository import MissionSnapshotRepository

        snapshot_repo = MissionSnapshotRepository(session)
        snapshots = snapshot_repo.list_for_run(run_id)

    assert len(snapshots) == 1
    assert snapshots[0].sequence == 1
    assert snapshots[0].status == "IDLE"


def test_startup_persists_initial_audit_events(client_with_db: TestClient):
    """Startup must persist initial audit events from seed mission."""
    from app.services.persistence import MissionPersistenceService

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )
    run_id = persistence.current_run_id

    with persistence._session_factory() as session:
        from app.db.repository import AuditEventRepository

        audit_repo = AuditEventRepository(session)
        events = audit_repo.list_for_run(run_id)

    assert len(events) > 0
    # Seed mission should have at least one audit event (mission creation)
    assert all(e.run_id == run_id for e in events)


# ---------------------------------------------------------------------------
# Transition persistence tests (via HTTP endpoints)
# ---------------------------------------------------------------------------


def test_start_transition_persists_snapshot(client_with_db: TestClient):
    """POST /api/mission/start must persist a snapshot."""
    from app.services.persistence import MissionPersistenceService

    # Get initial snapshot count
    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )
    run_id = persistence.current_run_id

    with persistence._session_factory() as session:
        from app.db.repository import MissionSnapshotRepository

        snapshot_repo = MissionSnapshotRepository(session)
        initial_count = len(snapshot_repo.list_for_run(run_id))

    # Start mission via HTTP
    response = client_with_db.post("/api/mission/start")
    assert response.status_code == 200

    # Verify new snapshot added
    with persistence._session_factory() as session:
        from app.db.repository import MissionSnapshotRepository

        snapshot_repo = MissionSnapshotRepository(session)
        snapshots = snapshot_repo.list_for_run(run_id)

    assert len(snapshots) == initial_count + 1
    # New snapshot should have RUNNING status
    running_snapshots = [s for s in snapshots if s.status == "RUNNING"]
    assert len(running_snapshots) == 1


def test_pause_transition_persists_snapshot(client_with_db: TestClient):
    """POST /api/mission/pause must persist a snapshot."""
    from app.services.persistence import MissionPersistenceService

    # First start the mission
    client_with_db.post("/api/mission/start")

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )
    run_id = persistence.current_run_id

    with persistence._session_factory() as session:
        from app.db.repository import MissionSnapshotRepository

        snapshot_repo = MissionSnapshotRepository(session)
        initial_count = len(snapshot_repo.list_for_run(run_id))

    # Pause mission
    response = client_with_db.post("/api/mission/pause")
    assert response.status_code == 200

    # Verify new snapshot added
    with persistence._session_factory() as session:
        from app.db.repository import MissionSnapshotRepository

        snapshot_repo = MissionSnapshotRepository(session)
        snapshots = snapshot_repo.list_for_run(run_id)

    assert len(snapshots) == initial_count + 1
    paused_snapshots = [s for s in snapshots if s.status == "PAUSED"]
    assert len(paused_snapshots) == 1


def test_resume_transition_persists_snapshot(client_with_db: TestClient):
    """POST /api/mission/resume must persist a snapshot."""
    from app.services.persistence import MissionPersistenceService

    # Start and pause first
    client_with_db.post("/api/mission/start")
    client_with_db.post("/api/mission/pause")

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )
    run_id = persistence.current_run_id

    with persistence._session_factory() as session:
        from app.db.repository import MissionSnapshotRepository

        snapshot_repo = MissionSnapshotRepository(session)
        initial_count = len(snapshot_repo.list_for_run(run_id))

    # Resume mission
    response = client_with_db.post("/api/mission/resume")
    assert response.status_code == 200

    # Verify new snapshot added
    with persistence._session_factory() as session:
        from app.db.repository import MissionSnapshotRepository

        snapshot_repo = MissionSnapshotRepository(session)
        snapshots = snapshot_repo.list_for_run(run_id)

    assert len(snapshots) == initial_count + 1
    running_snapshots = [s for s in snapshots if s.status == "RUNNING"]
    assert len(running_snapshots) >= 1  # At least the resume snapshot


def test_anomaly_transition_persists_snapshot(client_with_db: TestClient):
    """POST /api/mission/inject-anomaly persists snapshot with anomaly_active=True."""
    from app.services.persistence import MissionPersistenceService

    # Start mission first
    client_with_db.post("/api/mission/start")

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )
    run_id = persistence.current_run_id

    with persistence._session_factory() as session:
        from app.db.repository import MissionSnapshotRepository

        snapshot_repo = MissionSnapshotRepository(session)
        initial_count = len(snapshot_repo.list_for_run(run_id))

    # Inject anomaly
    response = client_with_db.post("/api/mission/inject-anomaly")
    assert response.status_code == 200

    # Verify new snapshot added
    with persistence._session_factory() as session:
        from app.db.repository import MissionSnapshotRepository

        snapshot_repo = MissionSnapshotRepository(session)
        snapshots = snapshot_repo.list_for_run(run_id)

    assert len(snapshots) == initial_count + 1
    anomaly_snapshots = [s for s in snapshots if s.anomaly_active is True]
    assert len(anomaly_snapshots) == 1


def test_planning_transition_persists_resulting_state(client_with_db: TestClient):
    """POST /api/plans/generate must persist snapshot with PLANNING status."""
    from app.services.persistence import MissionPersistenceService

    # Start mission and inject anomaly to reach ANOMALY state
    client_with_db.post("/api/mission/start")
    client_with_db.post("/api/mission/inject-anomaly")

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )
    run_id = persistence.current_run_id

    with persistence._session_factory() as session:
        from app.db.repository import MissionSnapshotRepository

        snapshot_repo = MissionSnapshotRepository(session)
        initial_count = len(snapshot_repo.list_for_run(run_id))

    # Generate plans
    response = client_with_db.post("/api/plans/generate")
    assert response.status_code == 200

    # Verify new snapshot added
    with persistence._session_factory() as session:
        from app.db.repository import MissionSnapshotRepository

        snapshot_repo = MissionSnapshotRepository(session)
        snapshots = snapshot_repo.list_for_run(run_id)

    assert len(snapshots) == initial_count + 1
    planning_snapshots = [
        s for s in snapshots if s.status in ("PLANNING", "AWAITING_APPROVAL")
    ]
    assert len(planning_snapshots) >= 1


def test_approval_executing_transition_persists_resulting_state(
    client_with_db: TestClient,
):
    """POST /api/plans/{plan_id}/approve must persist snapshot with EXECUTING status."""
    from app.services.persistence import MissionPersistenceService

    # Setup: start -> anomaly -> generate plans
    client_with_db.post("/api/mission/start")
    client_with_db.post("/api/mission/inject-anomaly")
    gen_response = client_with_db.post("/api/plans/generate")
    assert gen_response.status_code == 200

    plans = gen_response.json()
    assert len(plans) > 0
    plan_id = plans[0]["plan_id"]

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )
    run_id = persistence.current_run_id

    with persistence._session_factory() as session:
        from app.db.repository import MissionSnapshotRepository

        snapshot_repo = MissionSnapshotRepository(session)
        initial_count = len(snapshot_repo.list_for_run(run_id))

    # Approve plan
    approve_response = client_with_db.post(f"/api/plans/{plan_id}/approve")
    assert approve_response.status_code == 200

    # Verify new snapshot added
    with persistence._session_factory() as session:
        from app.db.repository import MissionSnapshotRepository

        snapshot_repo = MissionSnapshotRepository(session)
        snapshots = snapshot_repo.list_for_run(run_id)

    assert len(snapshots) == initial_count + 1
    executing_snapshots = [s for s in snapshots if s.status == "EXECUTING"]
    assert len(executing_snapshots) == 1


def test_failed_transition_adds_no_snapshot(client_with_db: TestClient):
    """Failed transitions (e.g., pause from IDLE) must not persist snapshots."""
    from app.services.persistence import MissionPersistenceService

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )
    run_id = persistence.current_run_id

    with persistence._session_factory() as session:
        from app.db.repository import MissionSnapshotRepository

        snapshot_repo = MissionSnapshotRepository(session)
        initial_count = len(snapshot_repo.list_for_run(run_id))

    # Attempt pause from IDLE (should fail 409)
    response = client_with_db.post("/api/mission/pause")
    assert response.status_code == 409

    # Verify no new snapshot added
    with persistence._session_factory() as session:
        from app.db.repository import MissionSnapshotRepository

        snapshot_repo = MissionSnapshotRepository(session)
        snapshots = snapshot_repo.list_for_run(run_id)

    assert len(snapshots) == initial_count


# ---------------------------------------------------------------------------
# Audit persistence tests
# ---------------------------------------------------------------------------


def test_new_audit_events_persist_exactly_once(client_with_db: TestClient):
    """Each domain audit event must be persisted exactly once."""
    from app.services.persistence import MissionPersistenceService

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )
    run_id = persistence.current_run_id

    # Get initial audit count (from startup)
    with persistence._session_factory() as session:
        from app.db.repository import AuditEventRepository

        audit_repo = AuditEventRepository(session)
        initial_audits = audit_repo.list_for_run(run_id)
        initial_count = len(initial_audits)

    # Start mission (adds one audit event to in-memory mission)
    # Note: fixture's pre-test reset() adds an extra audit event to in-memory mission
    # that hasn't been persisted yet. So first transition persists 2 events.
    client_with_db.post("/api/mission/start")

    with persistence._session_factory() as session:
        from app.db.repository import AuditEventRepository

        audit_repo = AuditEventRepository(session)
        audits = audit_repo.list_for_run(run_id)

    # Initial persist: 1 event (mission.initialized)
    # Fixture reset adds 1 event to in-memory mission (mission.reset)
    # Start transition adds 1 event (mission.started)
    # First persist_new_audit_events call persists 2 new events (reset + started)
    assert len(audits) == initial_count + 2


def test_multiple_transitions_no_audit_duplication(client_with_db: TestClient):
    """Repeated transitions must not duplicate earlier audit events."""
    from app.services.persistence import MissionPersistenceService

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )
    run_id = persistence.current_run_id

    # Start - first transition (persists 2: fixture reset + start)
    client_with_db.post("/api/mission/start")

    with persistence._session_factory() as session:
        from app.db.repository import AuditEventRepository

        audit_repo = AuditEventRepository(session)
        after_start = audit_repo.list_for_run(run_id)

    # Pause - second transition (persists 1: pause)
    client_with_db.post("/api/mission/pause")

    with persistence._session_factory() as session:
        from app.db.repository import AuditEventRepository

        audit_repo = AuditEventRepository(session)
        after_pause = audit_repo.list_for_run(run_id)

    # Resume - third transition (persists 1: resume)
    client_with_db.post("/api/mission/resume")

    with persistence._session_factory() as session:
        from app.db.repository import AuditEventRepository

        audit_repo = AuditEventRepository(session)
        after_resume = audit_repo.list_for_run(run_id)

    # Each transition adds exactly one new audit event
    # Startup: 1 (initialized) + Start: 2 (reset + started) = 3
    # Pause: +1 = 4, Resume: +1 = 5
    assert len(after_start) == 3
    assert len(after_pause) == 4
    assert len(after_resume) == 5

    # Verify no duplicates by checking event_ids are unique
    all_ids = [e.event_id for e in after_resume]
    assert len(all_ids) == len(set(all_ids))


# ---------------------------------------------------------------------------
# Sequencing tests
# ---------------------------------------------------------------------------


def test_snapshot_sequence_monotonic(client_with_db: TestClient):
    """Snapshot sequence must be strictly increasing within a run."""
    from app.services.persistence import MissionPersistenceService

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )
    run_id = persistence.current_run_id

    # Trigger several transitions
    client_with_db.post("/api/mission/start")
    client_with_db.post("/api/mission/pause")
    client_with_db.post("/api/mission/resume")
    client_with_db.post("/api/mission/anomaly")

    with persistence._session_factory() as session:
        from app.db.repository import MissionSnapshotRepository

        snapshot_repo = MissionSnapshotRepository(session)
        snapshots = snapshot_repo.list_for_run(run_id)

    sequences = [s.sequence for s in snapshots]
    # Sequences should be 1, 2, 3, 4, 5
    assert sequences == list(range(1, len(sequences) + 1))


def test_audit_sequence_monotonic(client_with_db: TestClient):
    """Audit sequence must be strictly increasing within a run."""
    from app.services.persistence import MissionPersistenceService

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )
    run_id = persistence.current_run_id

    # Trigger several transitions
    client_with_db.post("/api/mission/start")
    client_with_db.post("/api/mission/pause")
    client_with_db.post("/api/mission/resume")

    with persistence._session_factory() as session:
        from app.db.repository import AuditEventRepository

        audit_repo = AuditEventRepository(session)
        events = audit_repo.list_for_run(run_id)

    sequences = [e.sequence for e in events]
    assert sequences == list(range(1, len(sequences) + 1))


# ---------------------------------------------------------------------------
# Reset semantics tests
# ---------------------------------------------------------------------------


def test_reset_ends_previous_run(client_with_db: TestClient):
    """POST /api/mission/reset must mark previous run as ended."""
    from app.services.persistence import MissionPersistenceService

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )

    # Start mission first (transition from IDLE to RUNNING)
    client_with_db.post("/api/mission/start")

    # Capture pre-reset run_id
    old_run_id = persistence.current_run_id
    assert old_run_id is not None

    # Reset
    response = client_with_db.post("/api/mission/reset")
    assert response.status_code == 200

    # Verify old run is ended
    with persistence._session_factory() as session:
        from app.db.repository import MissionRunRepository

        run_repo = MissionRunRepository(session)
        old_run = run_repo.get(old_run_id)

    assert old_run is not None
    assert old_run.ended_at is not None
    assert old_run.final_status == "RUNNING"  # Pre-reset status


def test_reset_final_status_uses_pre_reset_state(client_with_db: TestClient):
    """Old run's final_status must equal mission status BEFORE reset."""
    from app.services.persistence import MissionPersistenceService

    # Start, pause, then reset
    client_with_db.post("/api/mission/start")
    client_with_db.post("/api/mission/pause")

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )
    old_run_id = persistence.current_run_id

    client_with_db.post("/api/mission/reset")

    with persistence._session_factory() as session:
        from app.db.repository import MissionRunRepository

        run_repo = MissionRunRepository(session)
        old_run = run_repo.get(old_run_id)

    assert old_run.final_status == "PAUSED"


def test_reset_creates_exactly_one_new_run(client_with_db: TestClient):
    """Reset must create exactly one new MissionRunRecord."""
    from app.services.persistence import MissionPersistenceService

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )

    # Get mission_id from current run
    with persistence._session_factory() as session:
        from app.db.repository import MissionRunRepository

        run_repo = MissionRunRepository(session)
        current_run = run_repo.get(persistence.current_run_id)
        mission_id = current_run.mission_id

    # Start mission
    client_with_db.post("/api/mission/start")

    with persistence._session_factory() as session:
        from app.db.repository import MissionRunRepository

        run_repo = MissionRunRepository(session)
        runs_before = run_repo.list_for_mission(mission_id, limit=10)

    client_with_db.post("/api/mission/reset")

    with persistence._session_factory() as session:
        from app.db.repository import MissionRunRepository

        run_repo = MissionRunRepository(session)
        runs_after = run_repo.list_for_mission(mission_id, limit=10)

    # One more run total
    # Note: listing by mission_id may include earlier runs
    assert len(runs_after) == len(runs_before) + 1


def test_new_run_has_initial_snapshot(client_with_db: TestClient):
    """New run after reset must have an initial snapshot (sequence=1)."""
    from app.services.persistence import MissionPersistenceService

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )

    # Start and reset
    client_with_db.post("/api/mission/start")
    client_with_db.post("/api/mission/reset")

    new_run_id = persistence.current_run_id
    assert new_run_id is not None

    with persistence._session_factory() as session:
        from app.db.repository import MissionSnapshotRepository

        snapshot_repo = MissionSnapshotRepository(session)
        snapshots = snapshot_repo.list_for_run(new_run_id)

    assert len(snapshots) == 1
    assert snapshots[0].sequence == 1
    assert snapshots[0].status == "IDLE"  # Reset returns to IDLE


def test_reset_audit_ownership_deterministic(client_with_db: TestClient):
    """Reset audit event must appear only on new run, not duplicated on old."""
    from app.services.persistence import MissionPersistenceService

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )

    client_with_db.post("/api/mission/start")
    old_run_id = persistence.current_run_id

    with persistence._session_factory() as session:
        from app.db.repository import AuditEventRepository

        audit_repo = AuditEventRepository(session)
        old_run_audits_before = len(audit_repo.list_for_run(old_run_id))

    client_with_db.post("/api/mission/reset")

    # Old run audit count unchanged
    with persistence._session_factory() as session:
        from app.db.repository import AuditEventRepository

        audit_repo = AuditEventRepository(session)
        old_run_audits_after = len(audit_repo.list_for_run(old_run_id))

    assert old_run_audits_after == old_run_audits_before

    # New run has audit events from new seed mission (initialized + reset)
    new_run_id = persistence.current_run_id
    with persistence._session_factory() as session:
        from app.db.repository import AuditEventRepository

        audit_repo = AuditEventRepository(session)
        new_run_audits = audit_repo.list_for_run(new_run_id)

    # New run gets initialized from seed + reset event from MissionService.reset()
    assert len(new_run_audits) == 2
    event_types = [e.event_type for e in new_run_audits]
    assert "mission.initialized" in event_types
    assert "mission.reset" in event_types


def test_multiple_resets_create_distinct_runs(client_with_db: TestClient):
    """Multiple resets must create distinct runs with correct final_status."""
    from app.services.persistence import MissionPersistenceService

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )

    # Start and reset first time
    client_with_db.post("/api/mission/start")
    client_with_db.post("/api/mission/reset")
    run1_id = persistence.current_run_id  # This is the run CREATED by first reset

    # Start and reset second time
    client_with_db.post("/api/mission/start")
    client_with_db.post("/api/mission/pause")
    client_with_db.post("/api/mission/reset")
    run2_id = persistence.current_run_id  # This is the run CREATED by second reset

    # Start and reset third time
    client_with_db.post("/api/mission/start")
    client_with_db.post("/api/mission/reset")
    run3_id = persistence.current_run_id  # This is the run CREATED by third reset

    # All three run_ids distinct
    assert len({run1_id, run2_id, run3_id}) == 3

    # Verify final_status of each run
    # run1 (created after first reset) was ended by second reset with PAUSED status
    # run2 (created after second reset) was ended by third reset with RUNNING status
    # run3 (created after third reset) is still running, not ended yet
    with persistence._session_factory() as session:
        from app.db.repository import MissionRunRepository

        run_repo = MissionRunRepository(session)
        run1 = run_repo.get(run1_id)
        run2 = run_repo.get(run2_id)
        run3 = run_repo.get(run3_id)

    assert run1 is not None and run1.final_status == "PAUSED"
    assert run2 is not None and run2.final_status == "RUNNING"
    assert run3 is not None and run3.final_status is None


# ---------------------------------------------------------------------------
# Deterministic ordering tests
# ---------------------------------------------------------------------------


def test_run_ordering_deterministic(client_with_db: TestClient):
    """Mission runs must be ordered newest first by started_at then id."""
    from app.services.persistence import MissionPersistenceService

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )

    # Create multiple runs via multiple resets
    client_with_db.post("/api/mission/start")
    client_with_db.post("/api/mission/reset")
    run1_id = persistence.current_run_id

    client_with_db.post("/api/mission/start")
    client_with_db.post("/api/mission/reset")
    run2_id = persistence.current_run_id

    # Query runs via history endpoint using actual mission_id
    with persistence._session_factory() as session:
        from app.db.repository import MissionRunRepository

        run_repo = MissionRunRepository(session)
        run = run_repo.get(persistence.current_run_id)
        mission_id = run.mission_id

    response = client_with_db.get(f"/api/missions/{mission_id}/runs")
    assert response.status_code == 200

    data = response.json()
    runs = data["runs"]

    # Newest first -> run2 should be first
    assert runs[0]["run_id"] == run2_id
    assert runs[1]["run_id"] == run1_id


# ---------------------------------------------------------------------------
# History API tests
# ---------------------------------------------------------------------------


def test_history_list_runs_endpoint(client_with_db: TestClient):
    """GET /api/missions/{mission_id}/runs returns correct structure."""
    from app.services.persistence import MissionPersistenceService

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )

    # Create a couple of runs
    client_with_db.post("/api/mission/start")
    client_with_db.post("/api/mission/reset")

    # Get actual mission_id from the current run
    with persistence._session_factory() as session:
        from app.db.repository import MissionRunRepository

        run_repo = MissionRunRepository(session)
        run = run_repo.get(persistence.current_run_id)
        mission_id = run.mission_id

    response = client_with_db.get(f"/api/missions/{mission_id}/runs")
    assert response.status_code == 200

    data = response.json()
    assert data["mission_id"] == mission_id
    assert "runs" in data
    assert "limit" in data
    assert len(data["runs"]) >= 2

    run = data["runs"][0]
    assert "run_id" in run
    assert "mission_id" in run
    assert "label" in run
    assert "seed_mission_id" in run
    assert "started_at" in run
    assert "ended_at" in run
    assert "final_status" in run


def test_history_get_run_endpoint(client_with_db: TestClient):
    """GET /api/runs/{run_id} returns correct structure."""
    from app.services.persistence import MissionPersistenceService

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )
    run_id = persistence.current_run_id

    response = client_with_db.get(f"/api/runs/{run_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["run_id"] == run_id
    assert "mission_id" in data
    assert "label" in data
    assert "seed_mission_id" in data
    assert "started_at" in data
    assert "ended_at" in data
    assert "final_status" in data


def test_history_get_missing_run_returns_404(client_with_db: TestClient):
    """GET /api/runs/{nonexistent} must return 404."""
    response = client_with_db.get("/api/runs/nonexistent-run-id")
    assert response.status_code == 404


def test_history_snapshot_endpoint(client_with_db: TestClient):
    """GET /api/runs/{run_id}/snapshots returns correct structure."""
    from app.services.persistence import MissionPersistenceService

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )

    # Trigger transitions to generate snapshots
    client_with_db.post("/api/mission/start")
    client_with_db.post("/api/mission/pause")

    run_id = persistence.current_run_id

    response = client_with_db.get(f"/api/runs/{run_id}/snapshots")
    assert response.status_code == 200

    data = response.json()
    assert data["run_id"] == run_id
    assert "snapshots" in data
    assert "limit" in data
    assert "offset" in data
    assert "total_snapshots_available" in data

    snapshot = data["snapshots"][0]
    assert "snapshot_id" in snapshot
    assert "sequence" in snapshot
    assert "status" in snapshot
    assert "elapsed_s" in snapshot
    assert "created_at" in snapshot
    assert "battery_pct" in snapshot
    assert "temperature_c" in snapshot
    assert "storage_pct" in snapshot
    assert "anomaly_active" in snapshot


def test_history_snapshot_ordering(client_with_db: TestClient):
    """Snapshots must be ordered by sequence ascending."""
    from app.services.persistence import MissionPersistenceService

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )

    client_with_db.post("/api/mission/start")
    client_with_db.post("/api/mission/pause")
    client_with_db.post("/api/mission/resume")

    run_id = persistence.current_run_id
    response = client_with_db.get(f"/api/runs/{run_id}/snapshots")
    assert response.status_code == 200

    data = response.json()
    sequences = [s["sequence"] for s in data["snapshots"]]
    assert sequences == sorted(sequences)


def test_history_audit_endpoint(client_with_db: TestClient):
    """GET /api/runs/{run_id}/audit returns correct structure."""
    from app.services.persistence import MissionPersistenceService

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )

    client_with_db.post("/api/mission/start")
    client_with_db.post("/api/mission/pause")

    run_id = persistence.current_run_id
    response = client_with_db.get(f"/api/runs/{run_id}/audit")
    assert response.status_code == 200

    data = response.json()
    assert data["run_id"] == run_id
    assert "audit_events" in data
    assert "limit" in data
    assert "offset" in data
    assert "total_audit_events_available" in data

    event = data["audit_events"][0]
    assert "audit_id" in event
    assert "event_type" in event
    assert "description" in event
    assert "timestamp" in event
    assert "sequence" in event


def test_history_audit_ordering(client_with_db: TestClient):
    """Audit events must be ordered by sequence ascending."""
    from app.services.persistence import MissionPersistenceService

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )

    client_with_db.post("/api/mission/start")
    client_with_db.post("/api/mission/pause")
    client_with_db.post("/api/mission/resume")

    run_id = persistence.current_run_id
    response = client_with_db.get(f"/api/runs/{run_id}/audit")
    assert response.status_code == 200

    data = response.json()
    sequences = [e["sequence"] for e in data["audit_events"]]
    assert sequences == sorted(sequences)


def test_mission_with_no_runs_returns_empty_list(client_with_db: TestClient):
    """Mission with no runs should return empty runs list (not error)."""
    # Startup creates a run for the seed mission, so test with
    # a nonexistent mission_id to verify empty list returned.
    response = client_with_db.get("/api/missions/nonexistent-mission/runs")
    assert response.status_code == 200
    data = response.json()
    assert data["mission_id"] == "nonexistent-mission"
    assert data["runs"] == []


# ---------------------------------------------------------------------------
# Cross-session persistence tests
# ---------------------------------------------------------------------------


def test_persistence_survives_separate_sessions(client_with_db: TestClient):
    """Data persisted in one session must be visible in another session."""
    from app.services.persistence import MissionPersistenceService

    persistence: MissionPersistenceService = (
        client_with_db.app.state.persistence_service
    )
    run_id = persistence.current_run_id

    # Trigger a transition
    client_with_db.post("/api/mission/start")

    # Open a new session against the same database
    with persistence._session_factory() as session:
        from app.db.repository import MissionSnapshotRepository

        snapshot_repo = MissionSnapshotRepository(session)
        snapshots = snapshot_repo.list_for_run(run_id)

    # Should see the snapshot from the earlier transition
    assert len(snapshots) >= 2  # initial + start
    running_snapshots = [s for s in snapshots if s.status == "RUNNING"]
    assert len(running_snapshots) >= 1


# ---------------------------------------------------------------------------
# Dev DB isolation test
# ---------------------------------------------------------------------------


def test_tests_never_touch_dev_database(client_with_db: TestClient, tmp_path):
    """Verify test suite does not create or modify backend/data/lunayield.db."""
    import os

    from app.db.config import DatabaseConfig

    # Get dev DB path
    dev_config = DatabaseConfig.development()
    dev_db_path = dev_config.url.replace("sqlite:///", "")

    # Check if it exists and get mtime
    dev_exists_before = os.path.exists(dev_db_path)
    dev_mtime_before = os.path.getmtime(dev_db_path) if dev_exists_before else None

    # Run a transition
    client_with_db.post("/api/mission/start")

    # Check again
    dev_exists_after = os.path.exists(dev_db_path)
    dev_mtime_after = os.path.getmtime(dev_db_path) if dev_exists_after else None

    # Dev DB should not have been created/modified by tests
    if dev_exists_before:
        assert dev_exists_after == dev_exists_before
        # If it existed, mtime should not have changed
        assert dev_mtime_after == dev_mtime_before
    else:
        # If it didn't exist, tests should not have created it
        assert not dev_exists_after
