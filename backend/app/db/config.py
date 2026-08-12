"""Database configuration for LunaYield.

Provides a simple, immutable configuration object for database connection.
Derives backend root from __file__ to ensure deterministic path resolution
regardless of process working directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    """Immutable database configuration.

    Attributes:
        url: SQLAlchemy database URL (e.g., "sqlite:///path/to/db.sqlite")
        echo: Enable SQLAlchemy echo mode for debugging.
    """

    url: str
    echo: bool = False

    @classmethod
    def development(cls) -> DatabaseConfig:
        """Create configuration for development database.

        Resolves backend/data/lunayield.db from the package location,
        not the current working directory.
        """
        # backend/app/db/config.py -> backend/ -> backend/data/lunayield.db
        backend_root = Path(__file__).resolve().parents[2]  # backend/
        data_dir = backend_root / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        db_path = data_dir / "lunayield.db"
        return cls(url=f"sqlite:///{db_path}", echo=False)

    @classmethod
    def test_temporary(cls, tmp_path: Path) -> DatabaseConfig:
        """Create configuration for isolated test database using temporary file.

        Args:
            tmp_path: pytest tmp_path fixture providing isolated temporary directory.

        Returns:
            DatabaseConfig pointing to a unique SQLite file in the temp directory.
        """
        db_path = tmp_path / "test_lunayield.db"
        return cls(url=f"sqlite:///{db_path}", echo=False)
