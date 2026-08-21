"""Lightweight per-session mission context management for demo isolation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from threading import RLock

from fastapi import HTTPException, Request, WebSocket

from app.services.anomaly import AnomalyDetectionService
from app.services.approval import StrategyApprovalService
from app.services.forecasting import ForecastingService
from app.services.mission import MissionService
from app.services.persistence import MissionPersistenceService
from app.services.planning import PlanningService
from app.services.safety import SafetyVerifier
from app.services.strategy import StrategyService
from app.services.telemetry import TelemetryService
from app.services.validation import StrategyValidationService

DEMO_SESSION_HEADER = "X-Demo-Session-Id"
DEMO_SESSION_QUERY_PARAM = "session_id"
DEFAULT_SESSION_ID = "__default__"
DEFAULT_SESSION_TTL_MINUTES = 60


@dataclass
class SessionContext:
    """Per-demo-session service bundle."""

    session_id: str
    mission_service: MissionService
    telemetry_service: TelemetryService
    forecasting_service: ForecastingService
    anomaly_service: AnomalyDetectionService
    strategy_service: StrategyService
    validation_service: StrategyValidationService
    approval_service: StrategyApprovalService
    persistence_service: MissionPersistenceService
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_accessed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def touch(self) -> None:
        """Mark the session as recently used."""
        self.last_accessed_at = datetime.now(UTC)


class SessionManager:
    """Creates, stores, and expires per-session mission contexts."""

    def __init__(
        self,
        *,
        session_factory,
        safety_verifier: SafetyVerifier,
        planning_service: PlanningService,
        session_ttl: timedelta | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._safety_verifier = safety_verifier
        self._planning_service = planning_service
        self._session_ttl = session_ttl or timedelta(
            minutes=DEFAULT_SESSION_TTL_MINUTES
        )
        self._contexts: dict[str, SessionContext] = {}
        self._lock = RLock()

    def _build_context(
        self,
        session_id: str,
        *,
        restored_mission=None,
        restored_run_id: str | None = None,
        restored_snapshot=None,
        restored_audit_records: list | None = None,
    ) -> SessionContext:
        mission_service = MissionService()
        mission_service.set_dependencies(self._safety_verifier, self._planning_service)

        if restored_mission is not None:
            mission_service.restore(restored_mission)
        mission = mission_service.get_mission()

        persistence_service = MissionPersistenceService(self._session_factory)
        if restored_run_id is not None:
            persistence_service.restore_current_run(
                restored_run_id,
                mission,
                restored_snapshot,
                restored_audit_records or [],
            )
        else:
            persistence_service.create_initial_run(mission)

        telemetry_service = TelemetryService(mission_service)
        forecasting_service = ForecastingService(mission_service)
        anomaly_service = AnomalyDetectionService(mission_service, forecasting_service)
        strategy_service = StrategyService(
            mission_service, forecasting_service, anomaly_service
        )
        validation_service = StrategyValidationService(mission_service)
        approval_service = StrategyApprovalService(
            strategy_service,
            validation_service,
            mission_service,
            forecasting_service,
            anomaly_service,
        )

        return SessionContext(
            session_id=session_id,
            mission_service=mission_service,
            telemetry_service=telemetry_service,
            forecasting_service=forecasting_service,
            anomaly_service=anomaly_service,
            strategy_service=strategy_service,
            validation_service=validation_service,
            approval_service=approval_service,
            persistence_service=persistence_service,
        )

    def create_context(
        self,
        session_id: str,
        *,
        restored_mission=None,
        restored_run_id: str | None = None,
        restored_snapshot=None,
        restored_audit_records: list | None = None,
    ) -> SessionContext:
        """Create and register a new session context."""
        context = self._build_context(
            session_id,
            restored_mission=restored_mission,
            restored_run_id=restored_run_id,
            restored_snapshot=restored_snapshot,
            restored_audit_records=restored_audit_records,
        )
        with self._lock:
            self._contexts[session_id] = context
        return context

    def get_or_create(self, session_id: str) -> SessionContext:
        """Return an existing session context or create a fresh one."""
        with self._lock:
            context = self._contexts.get(session_id)
            if context is None:
                context = self._build_context(session_id)
                self._contexts[session_id] = context
            context.touch()
            return context

    def get(self, session_id: str) -> SessionContext | None:
        """Return a session context if present."""
        with self._lock:
            context = self._contexts.get(session_id)
            if context is not None:
                context.touch()
            return context

    def touch(self, session_id: str) -> None:
        """Update a session's last-access timestamp if it exists."""
        with self._lock:
            context = self._contexts.get(session_id)
            if context is not None:
                context.touch()

    def list_contexts(self) -> list[SessionContext]:
        """Return a snapshot list of active session contexts."""
        with self._lock:
            return list(self._contexts.values())

    def cleanup_expired_sessions(self, ws_manager) -> list[str]:
        """Remove inactive sessions with no active socket connections."""
        now = datetime.now(UTC)
        removed: list[str] = []

        with self._lock:
            expired_session_ids = [
                session_id
                for session_id, context in self._contexts.items()
                if session_id != DEFAULT_SESSION_ID
                and now - context.last_accessed_at > self._session_ttl
                and ws_manager.connection_count_for_session(session_id) == 0
            ]

            for session_id in expired_session_ids:
                context = self._contexts.pop(session_id)
                try:
                    mission = context.mission_service.get_mission()
                    context.persistence_service.mark_current_run_ended(
                        mission.status.value
                    )
                except Exception:
                    pass
                removed.append(session_id)

        for session_id in removed:
            ws_manager.close_session(session_id)

        return removed


def _normalize_session_id(raw_session_id: str | None) -> str:
    if raw_session_id is None:
        return DEFAULT_SESSION_ID

    session_id = raw_session_id.strip()
    if not session_id:
        raise HTTPException(
            status_code=400,
            detail=f"{DEMO_SESSION_HEADER} must not be empty",
        )
    return session_id


def get_session_id_from_request(request: Request) -> str:
    """Resolve a demo session ID from HTTP request headers."""
    return _normalize_session_id(request.headers.get(DEMO_SESSION_HEADER))


def get_session_context_from_request(request: Request) -> SessionContext:
    """Resolve the per-session mission context for an HTTP request."""
    session_id = get_session_id_from_request(request)
    session_manager: SessionManager = request.app.state.session_manager
    return session_manager.get_or_create(session_id)


def get_session_id_from_websocket(websocket: WebSocket) -> str:
    """Resolve a demo session ID from WebSocket query params or headers."""
    raw_session_id = websocket.query_params.get(DEMO_SESSION_QUERY_PARAM)
    if raw_session_id is None:
        raw_session_id = websocket.headers.get(DEMO_SESSION_HEADER)
    return _normalize_session_id(raw_session_id)
