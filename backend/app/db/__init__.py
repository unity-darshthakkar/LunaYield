"""LunaYield database module.

Exports database configuration, engine helpers, models, and repositories.
"""

from __future__ import annotations

from app.db.config import DatabaseConfig
from app.db.engine import (
    create_engine_from_config,
    get_session_factory,
    init_db,
    session_scope,
)
from app.db.models import (
    AuditEventRecord,
    MissionRunRecord,
    MissionSnapshotRecord,
)
from app.db.repository import (
    AuditEventRepository,
    MissionRunRepository,
    MissionSnapshotRepository,
)

__all__ = [
    # Config
    "DatabaseConfig",
    # Engine/session
    "create_engine_from_config",
    "init_db",
    "get_session_factory",
    "session_scope",
    # Models
    "MissionRunRecord",
    "MissionSnapshotRecord",
    "AuditEventRecord",
    # Repositories
    "MissionRunRepository",
    "MissionSnapshotRepository",
    "AuditEventRepository",
]
