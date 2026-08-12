"""Database engine and session factory for LunaYield.

Provides minimal helpers for engine creation, table initialization,
and session management without unnecessary abstraction layers.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlmodel import Session, SQLModel, create_engine

from app.db.config import DatabaseConfig


def create_engine_from_config(config: DatabaseConfig):
    """Create SQLAlchemy engine from configuration.

    Args:
        config: DatabaseConfig with URL and echo settings.

    Returns:
        SQLAlchemy Engine configured for SQLite.
    """
    # SQLite-specific connect args for multi-threaded access (FastAPI)
    connect_args = {"check_same_thread": False}
    return create_engine(
        config.url,
        echo=config.echo,
        connect_args=connect_args,
    )


def init_db(engine) -> None:
    """Initialize database tables.

    Creates all tables defined in SQLModel metadata.
    Idempotent - safe to call multiple times.

    Args:
        engine: SQLAlchemy engine to initialize.
    """
    SQLModel.metadata.create_all(engine)


def get_session_factory(engine):
    """Create a session factory bound to the given engine.

    Returns a callable that produces new Session instances.
    Usage: session_factory() -> Session

    Args:
        engine: SQLAlchemy engine.

    Returns:
        Callable[[], Session] that creates new sessions.
    """
    return lambda: Session(engine, expire_on_commit=False)


@contextmanager
def session_scope(session_factory) -> Iterator[Session]:
    """Context manager for database session with automatic commit/rollback.

    Args:
        session_factory: Callable that returns a new Session.

    Yields:
        Session for database operations.
    """
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
