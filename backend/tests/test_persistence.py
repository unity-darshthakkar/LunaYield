"""Phase 2A Persistence Foundation Tests.

Tests for database initialization, persistence entities, repositories,
and session isolation. No Phase 1 runtime behavior changes tested here.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlmodel import Session, select

from app.db import (
    AuditEventRecord,
    AuditEventRepository,
    DatabaseConfig,
    MissionRunRecord,
    MissionRunRepository,
    MissionSnapshotRecord,
    MissionSnapshotRepository,
    create_engine_from_config,
    init_db,
)
from app.schemas import (
    AuditEvent,
    MissionRoute,
    MissionStatus,
    RouteWaypoint,
    RoverResources,
)


class TestDatabaseInitialization:
    """Tests for database table initialization."""

    def test_init_db_creates_all_tables(self, db_config: DatabaseConfig) -> None:
        """init_db() creates all three tables."""
        engine = create_engine_from_config(db_config)
        init_db(engine)

        # Verify tables exist by querying sqlite_master
        with Session(engine) as session:
            result = session.exec(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name IN ('mission_run', 'mission_snapshot', 'audit_event')"
                )
            ).all()
            table_names = {row[0] for row in result}
            assert table_names == {"mission_run", "mission_snapshot", "audit_event"}

    def test_init_db_idempotent(self, db_config: DatabaseConfig) -> None:
        """init_db() can be called multiple times without error."""
        engine = create_engine_from_config(db_config)
        init_db(engine)
        init_db(engine)  # Should not raise
        init_db(engine)  # Should not raise


class TestMissionRunRepository:
    """Tests for MissionRunRepository CRUD operations."""

    def test_create_run(self, db_config: DatabaseConfig) -> None:
        """Create a mission run record."""
        engine = create_engine_from_config(db_config)
        init_db(engine)

        with Session(engine) as session:
            repo = MissionRunRepository(session)
            run = repo.create(
                mission_id="luna-mission-001",
                label="Shackleton Rim Survey — Alpha",
                seed_mission_id="luna-mission-001",
            )
            session.commit()

            assert run.run_id is not None
            assert run.mission_id == "luna-mission-001"
            assert run.label == "Shackleton Rim Survey — Alpha"
            assert run.seed_mission_id == "luna-mission-001"
            assert run.started_at is not None
            assert run.ended_at is None
            assert run.final_status is None

    def test_get_run(self, db_config: DatabaseConfig) -> None:
        """Get a mission run by ID."""
        engine = create_engine_from_config(db_config)
        init_db(engine)

        with Session(engine) as session:
            repo = MissionRunRepository(session)
            created = repo.create("mission-1", "Label", "seed-1")
            session.commit()
            run_id = created.run_id

        # New session
        with Session(engine) as session:
            repo = MissionRunRepository(session)
            run = repo.get(run_id)

            assert run is not None
            assert run.run_id == run_id
            assert run.mission_id == "mission-1"

    def test_get_missing_run_returns_none(self, db_config: DatabaseConfig) -> None:
        """Getting a non-existent run returns None deterministically."""
        engine = create_engine_from_config(db_config)
        init_db(engine)

        with Session(engine) as session:
            repo = MissionRunRepository(session)
            run = repo.get("non-existent-id")
            assert run is None

    def test_get_latest_for_mission(self, db_config: DatabaseConfig) -> None:
        """Get latest run for a mission returns most recent by started_at."""
        engine = create_engine_from_config(db_config)
        init_db(engine)

        with Session(engine) as session:
            repo = MissionRunRepository(session)
            repo.create("mission-1", "Run 1", "seed-1")
            session.commit()
            run2 = repo.create("mission-1", "Run 2", "seed-1")
            session.commit()
            run2_id = run2.run_id

        with Session(engine) as session:
            repo = MissionRunRepository(session)
            latest = repo.get_latest("mission-1")

            assert latest is not None
            assert latest.run_id == run2_id

    def test_list_for_mission(self, db_config: DatabaseConfig) -> None:
        """List runs for a mission returns in descending started_at order."""
        engine = create_engine_from_config(db_config)
        init_db(engine)

        with Session(engine) as session:
            repo = MissionRunRepository(session)
            repo.create("mission-1", "Run 1", "seed-1")
            repo.create("mission-1", "Run 2", "seed-1")
            repo.create("mission-2", "Run A", "seed-2")
            session.commit()

        with Session(engine) as session:
            repo = MissionRunRepository(session)
            runs = repo.list_for_mission("mission-1")

            assert len(runs) == 2
            assert runs[0].label == "Run 2"
            assert runs[1].label == "Run 1"

    def test_mark_ended(self, db_config: DatabaseConfig) -> None:
        """Mark a run as ended with final status."""
        engine = create_engine_from_config(db_config)
        init_db(engine)

        with Session(engine) as session:
            repo = MissionRunRepository(session)
            run = repo.create("mission-1", "Label", "seed-1")
            session.commit()
            run_id = run.run_id

        with Session(engine) as session:
            repo = MissionRunRepository(session)
            ended = repo.mark_ended(run_id, "COMPLETED")

            assert ended is not None
            assert ended.ended_at is not None
            assert ended.final_status == "COMPLETED"

    def test_mark_ended_missing_returns_none(self, db_config: DatabaseConfig) -> None:
        """Marking non-existent run returns None."""
        engine = create_engine_from_config(db_config)
        init_db(engine)

        with Session(engine) as session:
            repo = MissionRunRepository(session)
            result = repo.mark_ended("non-existent", "COMPLETED")
            assert result is None


class TestMissionSnapshotRepository:
    """Tests for MissionSnapshotRepository CRUD and JSON round-trip."""

    def _make_resources(self) -> RoverResources:
        return RoverResources(
            battery_pct=75.5,
            storage_pct=23.0,
            temperature_c=-12.5,
            comm_window_remaining_s=3600,
            op_time_remaining_s=14400,
        )

    def _make_active_route(self) -> MissionRoute:
        return MissionRoute(
            waypoints=[
                RouteWaypoint(
                    id="wp-1", x=0.1, y=0.1, label="Base", is_science_target=False
                ),
                RouteWaypoint(
                    id="wp-2", x=0.5, y=0.5, label="Target", is_science_target=True
                ),
            ]
        )

    def test_create_snapshot(self, db_config: DatabaseConfig) -> None:
        """Create a mission snapshot with JSON fields."""
        engine = create_engine_from_config(db_config)
        init_db(engine)

        with Session(engine) as session:
            run_repo = MissionRunRepository(session)
            run = run_repo.create("mission-1", "Label", "seed-1")
            session.commit()
            run_id = run.run_id

        with Session(engine) as session:
            snapshot_repo = MissionSnapshotRepository(session)
            snapshot = snapshot_repo.create(
                run_id=run_id,
                sequence=1,
                status=MissionStatus.RUNNING.value,
                elapsed_s=120,
                resources=self._make_resources(),
                active_route=self._make_active_route(),
                anomaly_active=False,
            )
            session.commit()

            assert snapshot.snapshot_id is not None
            assert snapshot.run_id == run_id
            assert snapshot.sequence == 1
            assert snapshot.status == MissionStatus.RUNNING.value
            assert snapshot.elapsed_s == 120
            assert snapshot.anomaly_active is False

    def test_snapshot_json_roundtrip(self, db_config: DatabaseConfig) -> None:
        """Resources and active_route JSON fields round-trip correctly."""
        engine = create_engine_from_config(db_config)
        init_db(engine)

        resources = self._make_resources()
        active_route = self._make_active_route()

        with Session(engine) as session:
            run_repo = MissionRunRepository(session)
            run = run_repo.create("mission-1", "Label", "seed-1")
            session.commit()
            run_id = run.run_id

        with Session(engine) as session:
            snapshot_repo = MissionSnapshotRepository(session)
            snapshot = snapshot_repo.create(
                run_id=run_id,
                sequence=1,
                status=MissionStatus.RUNNING.value,
                elapsed_s=120,
                resources=resources,
                active_route=active_route,
                anomaly_active=False,
            )
            session.commit()
            snapshot_id = snapshot.snapshot_id

        # New session - verify round-trip
        with Session(engine) as session:
            snapshot = session.get(MissionSnapshotRecord, snapshot_id)
            assert snapshot is not None

            # Parse JSON back to dicts
            resources_dict = snapshot.to_resources_dict()
            route_dict = snapshot.to_active_route_dict()

            # Verify resources
            assert resources_dict["battery_pct"] == 75.5
            assert resources_dict["storage_pct"] == 23.0
            assert resources_dict["temperature_c"] == -12.5
            assert resources_dict["comm_window_remaining_s"] == 3600
            assert resources_dict["op_time_remaining_s"] == 14400

            # Verify active_route waypoints
            assert len(route_dict["waypoints"]) == 2
            assert route_dict["waypoints"][0]["id"] == "wp-1"
            assert route_dict["waypoints"][0]["x"] == 0.1
            assert route_dict["waypoints"][0]["y"] == 0.1
            assert route_dict["waypoints"][0]["label"] == "Base"
            assert route_dict["waypoints"][0]["is_science_target"] is False

            assert route_dict["waypoints"][1]["id"] == "wp-2"
            assert route_dict["waypoints"][1]["is_science_target"] is True

    def test_create_from_mission(self, db_config: DatabaseConfig) -> None:
        """Create snapshot from domain Mission object."""
        engine = create_engine_from_config(db_config)
        init_db(engine)

        # Build a Mission object
        from app.schemas import Mission

        mission = Mission(
            mission_id="luna-mission-001",
            label="Test Mission",
            status=MissionStatus.RUNNING,
            elapsed_s=300,
            resources=self._make_resources(),
            original_route=self._make_active_route(),
            active_route=self._make_active_route(),
            candidate_plans=[],
            anomaly_active=False,
            audit_trail=[],
        )

        with Session(engine) as session:
            run_repo = MissionRunRepository(session)
            run = run_repo.create(mission.mission_id, mission.label, mission.mission_id)
            session.commit()
            run_id = run.run_id

        with Session(engine) as session:
            snapshot_repo = MissionSnapshotRepository(session)
            snapshot = snapshot_repo.create_from_mission(run_id, 1, mission)
            session.commit()

            assert snapshot.status == MissionStatus.RUNNING.value
            assert snapshot.elapsed_s == 300

        # Verify JSON round-trip
        with Session(engine) as session:
            saved = session.get(MissionSnapshotRecord, snapshot.snapshot_id)
            resources_dict = saved.to_resources_dict()
            assert resources_dict["battery_pct"] == 75.5

    def test_get_latest_for_run(self, db_config: DatabaseConfig) -> None:
        """Get latest snapshot for a run by sequence."""
        engine = create_engine_from_config(db_config)
        init_db(engine)

        with Session(engine) as session:
            run_repo = MissionRunRepository(session)
            run = run_repo.create("mission-1", "Label", "seed-1")
            session.commit()
            run_id = run.run_id

        with Session(engine) as session:
            snapshot_repo = MissionSnapshotRepository(session)
            snapshot_repo.create(
                run_id,
                1,
                "IDLE",
                0,
                self._make_resources(),
                self._make_active_route(),
                False,
            )
            snapshot_repo.create(
                run_id,
                2,
                "RUNNING",
                120,
                self._make_resources(),
                self._make_active_route(),
                False,
            )
            snapshot_repo.create(
                run_id,
                3,
                "PAUSED",
                240,
                self._make_resources(),
                self._make_active_route(),
                False,
            )
            session.commit()

        with Session(engine) as session:
            snapshot_repo = MissionSnapshotRepository(session)
            latest = snapshot_repo.get_latest_for_run(run_id)

            assert latest is not None
            assert latest.sequence == 3
            assert latest.status == "PAUSED"

    def test_list_for_run(self, db_config: DatabaseConfig) -> None:
        """List snapshots for a run in sequence order."""
        engine = create_engine_from_config(db_config)
        init_db(engine)

        with Session(engine) as session:
            run_repo = MissionRunRepository(session)
            run = run_repo.create("mission-1", "Label", "seed-1")
            session.commit()
            run_id = run.run_id

        with Session(engine) as session:
            snapshot_repo = MissionSnapshotRepository(session)
            snapshot_repo.create(
                run_id,
                3,
                "PAUSED",
                240,
                self._make_resources(),
                self._make_active_route(),
                False,
            )
            snapshot_repo.create(
                run_id,
                1,
                "IDLE",
                0,
                self._make_resources(),
                self._make_active_route(),
                False,
            )
            snapshot_repo.create(
                run_id,
                2,
                "RUNNING",
                120,
                self._make_resources(),
                self._make_active_route(),
                False,
            )
            session.commit()

        with Session(engine) as session:
            snapshot_repo = MissionSnapshotRepository(session)
            snapshots = snapshot_repo.list_for_run(run_id)

            assert len(snapshots) == 3
            assert snapshots[0].sequence == 1
            assert snapshots[1].sequence == 2
            assert snapshots[2].sequence == 3


class TestAuditEventRepository:
    """Tests for AuditEventRepository append and list."""

    def test_append_event(self, db_config: DatabaseConfig) -> None:
        """Append an audit event with metadata."""
        engine = create_engine_from_config(db_config)
        init_db(engine)

        with Session(engine) as session:
            run_repo = MissionRunRepository(session)
            run = run_repo.create("mission-1", "Label", "seed-1")
            session.commit()
            run_id = run.run_id

        with Session(engine) as session:
            audit_repo = AuditEventRepository(session)
            event = audit_repo.append(
                run_id=run_id,
                sequence=1,
                event_type="mission.started",
                description="Mission started",
                timestamp=datetime.now(UTC),
                metadata={"mission_id": "mission-1", "operator": "test"},
            )
            session.commit()

            assert event.event_id is not None
            assert event.run_id == run_id
            assert event.sequence == 1
            assert event.event_type == "mission.started"
            assert event.description == "Mission started"

    def test_append_from_domain(self, db_config: DatabaseConfig) -> None:
        """Append audit event from domain AuditEvent."""
        engine = create_engine_from_config(db_config)
        init_db(engine)

        with Session(engine) as session:
            run_repo = MissionRunRepository(session)
            run = run_repo.create("mission-1", "Label", "seed-1")
            session.commit()
            run_id = run.run_id

        domain_event = AuditEvent(
            event_id="audit-test-001",
            event_type="mission.started",
            description="Mission started by operator",
            timestamp=datetime(2026, 8, 6, 12, 0, 0, tzinfo=UTC),
            metadata={"mission_id": "mission-1", "custom_key": "custom_value"},
        )

        with Session(engine) as session:
            audit_repo = AuditEventRepository(session)
            event = audit_repo.append_from_domain(run_id, 1, domain_event)
            session.commit()

            assert event.event_type == "mission.started"
            assert event.description == "Mission started by operator"
            # SQLite stores naive datetime; compare with timezone stripped
            expected = domain_event.timestamp.replace(tzinfo=None)
            actual = event.timestamp.replace(tzinfo=None)
            assert actual == expected

        # Verify metadata round-trip
        with Session(engine) as session:
            saved = session.get(AuditEventRecord, event.event_id)
            metadata = saved.to_metadata_dict()
            assert metadata["mission_id"] == "mission-1"
            assert metadata["custom_key"] == "custom_value"

    def test_list_for_run(self, db_config: DatabaseConfig) -> None:
        """List audit events for a run in sequence order."""
        engine = create_engine_from_config(db_config)
        init_db(engine)

        with Session(engine) as session:
            run_repo = MissionRunRepository(session)
            run = run_repo.create("mission-1", "Label", "seed-1")
            session.commit()
            run_id = run.run_id

        with Session(engine) as session:
            audit_repo = AuditEventRepository(session)
            for i in range(1, 4):
                audit_repo.append(
                    run_id=run_id,
                    sequence=i,
                    event_type=f"event.{i}",
                    description=f"Event {i}",
                    timestamp=datetime.now(UTC),
                    metadata={},
                )
            session.commit()

        with Session(engine) as session:
            audit_repo = AuditEventRepository(session)
            events = audit_repo.list_for_run(run_id)

            assert len(events) == 3
            assert events[0].sequence == 1
            assert events[1].sequence == 2
            assert events[2].sequence == 3


class TestSessionIsolation:
    """Tests that records survive across separate SQLModel sessions."""

    def test_records_survive_across_sessions(self, db_config: DatabaseConfig) -> None:
        """Write in one session, read in another session."""
        engine = create_engine_from_config(db_config)
        init_db(engine)

        # Session 1: Create run and snapshot
        with Session(engine) as session:
            run_repo = MissionRunRepository(session)
            run = run_repo.create("mission-survive", "Survive Test", "seed-1")
            session.commit()
            run_id = run.run_id

            snapshot_repo = MissionSnapshotRepository(session)
            snapshot_repo.create(
                run_id=run_id,
                sequence=1,
                status="RUNNING",
                elapsed_s=100,
                resources=RoverResources(
                    battery_pct=90.0,
                    storage_pct=10.0,
                    temperature_c=-20.0,
                    comm_window_remaining_s=5000,
                    op_time_remaining_s=20000,
                ),
                active_route=MissionRoute(
                    waypoints=[
                        RouteWaypoint(
                            id="wp-1",
                            x=0.0,
                            y=0.0,
                            label="Start",
                            is_science_target=False,
                        )
                    ]
                ),
                anomaly_active=False,
            )
            session.commit()

        # Session 2: Read back
        with Session(engine) as session:
            run = session.exec(
                select(MissionRunRecord).where(MissionRunRecord.run_id == run_id)
            ).first()
            assert run is not None
            assert run.mission_id == "mission-survive"

            snapshots = list(
                session.exec(
                    select(MissionSnapshotRecord).where(
                        MissionSnapshotRecord.run_id == run_id
                    )
                ).all()
            )
            assert len(snapshots) == 1
            assert snapshots[0].sequence == 1
            resources = snapshots[0].to_resources_dict()
            assert resources["battery_pct"] == 90.0

    def test_audit_events_survive_across_sessions(
        self, db_config: DatabaseConfig
    ) -> None:
        """Audit events survive across sessions."""
        engine = create_engine_from_config(db_config)
        init_db(engine)

        with Session(engine) as session:
            run_repo = MissionRunRepository(session)
            run = run_repo.create("mission-audit", "Audit Test", "seed-1")
            session.commit()
            run_id = run.run_id

            audit_repo = AuditEventRepository(session)
            audit_repo.append(
                run_id=run_id,
                sequence=1,
                event_type="test.event",
                description="Test event",
                timestamp=datetime.now(UTC),
                metadata={"key": "value"},
            )
            session.commit()

        with Session(engine) as session:
            events = list(
                session.exec(
                    select(AuditEventRecord).where(AuditEventRecord.run_id == run_id)
                ).all()
            )
            assert len(events) == 1
            assert events[0].to_metadata_dict()["key"] == "value"


class TestTemporaryDatabaseIsolation:
    """Tests that temporary databases are isolated between tests."""

    def test_independent_databases_dont_share_data(
        self,
        tmp_path: pytest.fixture,
    ) -> None:
        """Two different temporary databases have independent data."""
        # This test uses the fixture's tmp_path implicitly
        # but we create two separate configs manually

        db1_path = tmp_path / "db1.db"
        db2_path = tmp_path / "db2.db"

        config1 = DatabaseConfig(url=f"sqlite:///{db1_path}", echo=False)
        config2 = DatabaseConfig(url=f"sqlite:///{db2_path}", echo=False)

        engine1 = create_engine_from_config(config1)
        init_db(engine1)
        engine2 = create_engine_from_config(config2)
        init_db(engine2)

        # Write to db1
        with Session(engine1) as session:
            run_repo = MissionRunRepository(session)
            run_repo.create("mission-1", "DB1", "seed-1")
            session.commit()

        # db2 should be empty
        with Session(engine2) as session:
            runs = list(session.exec(select(MissionRunRecord)).all())
            assert len(runs) == 0
