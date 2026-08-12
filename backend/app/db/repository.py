"""Repository layer for LunaYield persistence.

Provides data access methods for mission runs, snapshots, and audit events.
Repositories receive a SQLModel Session via dependency injection.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session, select

from app.db.models import (
    AuditEventRecord,
    MissionRunRecord,
    MissionSnapshotRecord,
)
from app.schemas import AuditEvent, Mission, MissionRoute, RoverResources


class MissionRunRepository:
    """Repository for mission run persistence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        mission_id: str,
        label: str,
        seed_mission_id: str,
    ) -> MissionRunRecord:
        """Create a new mission run record."""
        run = MissionRunRecord(
            mission_id=mission_id,
            label=label,
            seed_mission_id=seed_mission_id,
        )
        self._session.add(run)
        self._session.flush()
        return run

    def mark_ended(self, run_id: str, final_status: str) -> MissionRunRecord | None:
        """Mark a mission run as ended with final status."""
        stmt = select(MissionRunRecord).where(MissionRunRecord.run_id == run_id)
        run = self._session.exec(stmt).first()
        if run is None:
            return None
        run.ended_at = datetime.now(UTC)
        run.final_status = final_status
        self._session.flush()
        return run

    def get(self, run_id: str) -> MissionRunRecord | None:
        """Get a mission run by ID."""
        stmt = select(MissionRunRecord).where(MissionRunRecord.run_id == run_id)
        return self._session.exec(stmt).first()

    def get_latest(self, mission_id: str) -> MissionRunRecord | None:
        """Get the most recent mission run for a mission.

        Uses deterministic ordering: started_at DESC, then id DESC (auto-increment).
        This guarantees stable ordering even when started_at timestamps are equal.
        """
        stmt = (
            select(MissionRunRecord)
            .where(MissionRunRecord.mission_id == mission_id)
            .order_by(MissionRunRecord.started_at.desc(), MissionRunRecord.id.desc())
            .limit(1)
        )
        return self._session.exec(stmt).first()

    def list_for_mission(
        self, mission_id: str, limit: int = 50
    ) -> list[MissionRunRecord]:
        """List mission runs for a mission, newest first.

        Uses deterministic ordering: started_at DESC, then id DESC (auto-increment).
        This guarantees stable ordering even when started_at timestamps are equal.
        """
        stmt = (
            select(MissionRunRecord)
            .where(MissionRunRecord.mission_id == mission_id)
            .order_by(MissionRunRecord.started_at.desc(), MissionRunRecord.id.desc())
            .limit(limit)
        )
        return list(self._session.exec(stmt).all())


class MissionSnapshotRepository:
    """Repository for mission snapshot persistence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        run_id: str,
        sequence: int,
        status: str,
        elapsed_s: int,
        resources: RoverResources,
        active_route: MissionRoute,
        anomaly_active: bool,
    ) -> MissionSnapshotRecord:
        """Create a new mission snapshot record."""
        snapshot = MissionSnapshotRecord(
            run_id=run_id,
            sequence=sequence,
            status=status,
            elapsed_s=elapsed_s,
            resources_json=json.dumps(
                resources.model_dump(mode="json"),
                separators=(",", ":"),
                sort_keys=True,
            ),
            active_route_json=json.dumps(
                active_route.model_dump(mode="json"),
                separators=(",", ":"),
                sort_keys=True,
            ),
            anomaly_active=anomaly_active,
        )
        self._session.add(snapshot)
        self._session.flush()
        return snapshot

    def create_from_mission(
        self, run_id: str, sequence: int, mission: Mission
    ) -> MissionSnapshotRecord:
        """Create snapshot from domain Mission object."""
        return self.create(
            run_id=run_id,
            sequence=sequence,
            status=mission.status.value,
            elapsed_s=mission.elapsed_s,
            resources=mission.resources,
            active_route=mission.active_route,
            anomaly_active=mission.anomaly_active,
        )

    def get_latest_for_run(self, run_id: str) -> MissionSnapshotRecord | None:
        """Get the most recent snapshot for a run."""
        stmt = (
            select(MissionSnapshotRecord)
            .where(MissionSnapshotRecord.run_id == run_id)
            .order_by(MissionSnapshotRecord.sequence.desc())
            .limit(1)
        )
        return self._session.exec(stmt).first()

    def get_latest(self, run_id: str) -> MissionSnapshotRecord | None:
        """Alias for get_latest_for_run."""
        return self.get_latest_for_run(run_id)

    def list_for_run(self, run_id: str) -> list[MissionSnapshotRecord]:
        """List all snapshots for a run in sequence order."""
        stmt = (
            select(MissionSnapshotRecord)
            .where(MissionSnapshotRecord.run_id == run_id)
            .order_by(MissionSnapshotRecord.sequence)
        )
        return list(self._session.exec(stmt).all())


class AuditEventRepository:
    """Repository for audit event persistence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def append(
        self,
        run_id: str,
        sequence: int,
        event_type: str,
        description: str,
        timestamp: datetime,
        metadata: dict[str, Any],
    ) -> AuditEventRecord:
        """Append an audit event record."""
        record = AuditEventRecord(
            run_id=run_id,
            sequence=sequence,
            event_type=event_type,
            description=description,
            timestamp=timestamp,
            metadata_json=json.dumps(
                metadata,
                separators=(",", ":"),
                sort_keys=True,
            ),
        )
        self._session.add(record)
        self._session.flush()
        return record

    def append_from_domain(
        self, run_id: str, sequence: int, event: AuditEvent
    ) -> AuditEventRecord:
        """Append audit event from domain AuditEvent."""
        return self.append(
            run_id=run_id,
            sequence=sequence,
            event_type=event.event_type,
            description=event.description,
            timestamp=event.timestamp,
            metadata=event.metadata,
        )

    def list_for_run(self, run_id: str) -> list[AuditEventRecord]:
        """List all audit events for a run in sequence order."""
        stmt = (
            select(AuditEventRecord)
            .where(AuditEventRecord.run_id == run_id)
            .order_by(AuditEventRecord.sequence)
        )
        return list(self._session.exec(stmt).all())
