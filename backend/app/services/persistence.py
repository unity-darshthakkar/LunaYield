"""Mission persistence orchestration service.

Coordinates durable mission run history persistence without owning mission state.
MissionService remains the authoritative in-memory mission state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.db import (
    AuditEventRecord,
    MissionRunRecord,
    MissionSnapshotRecord,
    create_engine_from_config,
    get_session_factory,
    init_db,
)
from app.db.repository import (
    AuditEventRepository,
    MissionRunRepository,
    MissionSnapshotRepository,
)
from app.schemas import Mission

if TYPE_CHECKING:
    from sqlmodel import Session

    from app.db.config import DatabaseConfig


class MissionPersistenceService:
    """Orchestrates persistence of mission runs, snapshots, and audit events.

    This service does not own mission state; it persists state transitions
    initiated by MissionService.
    """

    def __init__(self, session_factory) -> None:
        """Initialize with a session factory.

        Args:
            session_factory: Callable that returns a new SQLModel Session.
        """
        self._session_factory = session_factory
        self._current_run_id: str | None = None
        self._persisted_audit_count: int = 0
        self._next_snapshot_sequence: int = 1

    @property
    def current_run_id(self) -> str | None:
        """Get the current mission run ID."""
        return self._current_run_id

    def create_initial_run(self, mission: Mission) -> MissionRunRecord:
        """Create the initial mission run on application startup.

        Args:
            mission: The current in-memory mission (seed mission).

        Returns:
            The created MissionRunRecord.
        """
        with self._session_factory() as session:
            run_repo = MissionRunRepository(session)
            run = run_repo.create(
                mission_id=mission.mission_id,
                label=mission.label,
                seed_mission_id=mission.mission_id,
            )
            session.commit()
            run_id = run.run_id

        # Set as current run
        self._current_run_id = run_id
        self._persisted_audit_count = 0
        self._next_snapshot_sequence = 1

        # Persist initial snapshot
        self.persist_snapshot(mission)

        # Persist initial audit events (seed mission's audit trail)
        self.persist_new_audit_events(mission)

        return run

    def _get_next_snapshot_sequence(self, session: Session) -> int:
        """Get the next snapshot sequence number for the current run."""
        if self._current_run_id is None:
            return 1
        snapshot_repo = MissionSnapshotRepository(session)
        latest = snapshot_repo.get_latest_for_run(self._current_run_id)
        if latest is None:
            return 1
        return latest.sequence + 1

    def _get_next_audit_sequence(self, session: Session) -> int:
        """Get the next audit event sequence number for the current run."""
        if self._current_run_id is None:
            return 1
        audit_repo = AuditEventRepository(session)
        events = audit_repo.list_for_run(self._current_run_id)
        if not events:
            return 1
        return max(e.sequence for e in events) + 1

    def persist_snapshot(self, mission: Mission) -> MissionSnapshotRecord | None:
        """Persist a mission snapshot for the current run.

        Args:
            mission: The current mission state to snapshot.

        Returns:
            The created MissionSnapshotRecord, or None if no current run.
        """
        if self._current_run_id is None:
            return None

        with self._session_factory() as session:
            snapshot_repo = MissionSnapshotRepository(session)
            sequence = self._get_next_snapshot_sequence(session)
            snapshot = snapshot_repo.create_from_mission(
                run_id=self._current_run_id,
                sequence=sequence,
                mission=mission,
            )
            session.commit()
            return snapshot

    def persist_new_audit_events(self, mission: Mission) -> list[AuditEventRecord]:
        """Persist newly added audit events for the current run.

        Only persists events that haven't been persisted yet, based on
        the audit trail length comparison.

        Args:
            mission: The current mission with its audit trail.

        Returns:
            List of newly persisted AuditEventRecords.
        """
        if self._current_run_id is None:
            return []

        new_events = mission.audit_trail[self._persisted_audit_count :]
        if not new_events:
            return []

        created_records = []
        with self._session_factory() as session:
            audit_repo = AuditEventRepository(session)
            for i, event in enumerate(new_events):
                sequence = self._get_next_audit_sequence(session)
                record = audit_repo.append_from_domain(
                    run_id=self._current_run_id,
                    sequence=sequence,
                    event=event,
                )
                created_records.append(record)
            session.commit()

        # Update persisted count
        self._persisted_audit_count = len(mission.audit_trail)

        return created_records

    def mark_current_run_ended(
        self, final_status: str | None = None
    ) -> MissionRunRecord | None:
        """Mark the current mission run as ended.

        Args:
            final_status: The final mission status (optional).

        Returns:
            The ended MissionRunRecord, or None if no current run.
        """
        if self._current_run_id is None:
            return None

        with self._session_factory() as session:
            run_repo = MissionRunRepository(session)
            run = run_repo.mark_ended(self._current_run_id, final_status or "")
            session.commit()
            return run

    def reset_and_create_new_run(self, mission: Mission) -> MissionRunRecord:
        """Handle mission reset: create new run after old run has been ended.

        The old run should already be ended via mark_current_run_ended() called
        by the router with the pre-reset status.

        Args:
            mission: The new mission state after reset.

        Returns:
            The new MissionRunRecord.
        """
        # Create new run for the post-reset mission
        self._persisted_audit_count = 0
        self._next_snapshot_sequence = 1

        with self._session_factory() as session:
            run_repo = MissionRunRepository(session)
            run = run_repo.create(
                mission_id=mission.mission_id,
                label=mission.label,
                seed_mission_id=mission.mission_id,
            )
            session.commit()
            self._current_run_id = run.run_id

        # Persist initial snapshot of new run
        self.persist_snapshot(mission)

        # Persist audit events of new mission (includes reset event)
        self.persist_new_audit_events(mission)

        return run


def create_persistence_service_from_config(
    config: DatabaseConfig,
) -> MissionPersistenceService:
    """Create a MissionPersistenceService from database configuration.

    Args:
        config: DatabaseConfig instance.

    Returns:
        MissionPersistenceService with engine/session from config.
    """
    engine = create_engine_from_config(config)
    init_db(engine)
    session_factory = get_session_factory(engine)
    return MissionPersistenceService(session_factory)
