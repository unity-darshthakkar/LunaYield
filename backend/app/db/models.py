"""SQLModel persistence entities for LunaYield.

These models are separate from API/domain Pydantic models and represent
the database schema for mission persistence.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlmodel import Field, SQLModel


def _generate_uuid() -> str:
    return uuid4().hex


class MissionRunRecord(SQLModel, table=True):
    """Persistence record for a mission run.

    A run represents a complete mission lifecycle. Future phases may
    associate multiple runs with the same mission_id, but Phase 2A
    only establishes the entity capability.
    """

    __tablename__ = "mission_run"

    # Auto-incrementing integer key guarantees deterministic insertion order
    # as secondary sort when started_at values are equal (same clock resolution).
    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(default_factory=_generate_uuid, index=True, unique=True)
    mission_id: str = Field(index=True)
    label: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ended_at: datetime | None = Field(default=None)
    final_status: str | None = Field(default=None)
    seed_mission_id: str


class MissionSnapshotRecord(SQLModel, table=True):
    """Point-in-time snapshot of mission state for future restore capability."""

    __tablename__ = "mission_snapshot"

    snapshot_id: str = Field(default_factory=_generate_uuid, primary_key=True)
    run_id: str = Field(foreign_key="mission_run.run_id", index=True)
    sequence: int = Field(index=True)  # ordering within a run
    status: str
    elapsed_s: int
    resources_json: str = Field(sa_column_kwargs={"nullable": False})
    active_route_json: str = Field(sa_column_kwargs={"nullable": False})
    anomaly_active: bool
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_resources_dict(self) -> dict[str, Any]:
        """Parse resources_json back to dict."""
        return json.loads(self.resources_json)

    def to_active_route_dict(self) -> dict[str, Any]:
        """Parse active_route_json back to dict."""
        return json.loads(self.active_route_json)


class AuditEventRecord(SQLModel, table=True):
    """Immutable audit event record, mirrors domain AuditEvent."""

    __tablename__ = "audit_event"

    event_id: str = Field(default_factory=_generate_uuid, primary_key=True)
    run_id: str = Field(foreign_key="mission_run.run_id", index=True)
    sequence: int = Field(index=True)  # ordering within a run
    event_type: str
    description: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata_json: str = Field(default="{}", sa_column_kwargs={"nullable": False})

    def to_metadata_dict(self) -> dict[str, Any]:
        """Parse metadata_json back to dict."""
        return json.loads(self.metadata_json)

    @classmethod
    def from_domain(
        cls, run_id: str, sequence: int, event: AuditEvent
    ) -> AuditEventRecord:
        """Create record from domain AuditEvent.

        Args:
            run_id: Associated mission run ID.
            sequence: Order within the run.
            event: Domain AuditEvent to persist.

        Returns:
            AuditEventRecord ready for database insertion.
        """

        return cls(
            run_id=run_id,
            sequence=sequence,
            event_type=event.event_type,
            description=event.description,
            timestamp=event.timestamp,
            metadata_json=json.dumps(
                event.metadata, separators=(",", ":"), sort_keys=True
            ),
        )


# Forward reference resolution for from_domain
from app.schemas import AuditEvent  # noqa: E402
