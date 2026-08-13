"""LunaYield Mission Lab — FastAPI application."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import (
    DatabaseConfig,
    create_engine_from_config,
    get_session_factory,
    init_db,
)
from app.db.repository import (
    AuditEventRepository,
    MissionRunRepository,
    MissionSnapshotRepository,
)
from app.routers import health, history, mission, planning, ws
from app.schemas import AuditEvent
from app.seed import get_seed_mission
from app.services.mission import MissionService
from app.services.persistence import MissionPersistenceService
from app.services.planning import PlanningService
from app.services.safety import SafetyVerifier
from app.services.telemetry import TelemetryService
from app.ws_manager import WSConnectionManager


async def telemetry_loop(
    telemetry_service: TelemetryService,
    ws_manager: WSConnectionManager,
) -> None:
    """Background telemetry emission loop.

    Runs approximately every 2 seconds while mission is RUNNING or EXECUTING.
    """
    try:
        while True:
            sample = telemetry_service.generate_sample()
            if sample is not None:
                # Use Pydantic v2 JSON mode for proper datetime serialization
                payload = sample.model_dump(mode="json")
                await ws_manager.broadcast("telemetry.updated", payload)
            await asyncio.sleep(2.0)
    except asyncio.CancelledError:
        # Clean shutdown
        pass


def _create_db_config() -> DatabaseConfig:
    """Create database configuration.

    Can be overridden by setting app.state.db_config before lifespan runs
    (e.g., in tests).
    """
    return DatabaseConfig.development()


def _reconstruct_audit_events(audit_records: list) -> list[AuditEvent]:
    """Reconstruct domain AuditEvent objects from persisted records.

    Args:
        audit_records: List of AuditEventRecord from database.

    Returns:
        List of domain AuditEvent objects in sequence order.
    """
    events = []
    for record in audit_records:
        metadata = record.to_metadata_dict()
        event = AuditEvent(
            event_id=record.event_id,
            event_type=record.event_type,
            description=record.description,
            timestamp=record.timestamp,
            metadata=metadata,
        )
        events.append(event)
    return events


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    # Startup: create shared service instances
    # Database initialization (can be overridden by tests via app.state.db_config)
    db_config = getattr(app.state, "db_config", None) or _create_db_config()
    engine = create_engine_from_config(db_config)
    init_db(engine)
    session_factory = get_session_factory(engine)

    mission_service = MissionService()
    planning_service = PlanningService()
    safety_verifier = SafetyVerifier()
    telemetry_service = TelemetryService(mission_service)
    ws_manager = WSConnectionManager()
    persistence_service = MissionPersistenceService(session_factory)

    # Set up dependencies
    mission_service.set_dependencies(safety_verifier, planning_service)

    # Store in app state for router access
    app.state.mission_service = mission_service
    app.state.planning_service = planning_service
    app.state.safety_verifier = safety_verifier
    app.state.telemetry_service = telemetry_service
    app.state.ws_manager = ws_manager
    app.state.db_engine = engine
    app.state.db_session_factory = session_factory
    app.state.persistence_service = persistence_service

    # STARTUP RESTORATION FLOW
    # 1. Get seed mission (deterministic structural baseline)
    seed_mission = get_seed_mission()

    # 2. Query latest unfinished run for the seed mission
    with session_factory() as session:
        run_repo = MissionRunRepository(session)
        unfinished_run = run_repo.get_latest_unfinished(seed_mission.mission_id)

    if unfinished_run is not None:
        # 3a. Unfinished run exists — restore from it
        run_id = unfinished_run.run_id

        # 3b. Get latest snapshot for this run
        with session_factory() as session:
            snapshot_repo = MissionSnapshotRepository(session)
            latest_snapshot = snapshot_repo.get_latest_for_run(run_id)

        # 3c. Get persisted audit events for this run
        with session_factory() as session:
            audit_repo = AuditEventRepository(session)
            audit_records = audit_repo.list_for_run(run_id)

        # 3d. Reconstruct audit events
        audit_events = _reconstruct_audit_events(audit_records)

        # 3e. Reconstruct Mission from snapshot + audit + seed
        restoration_failed = False
        restored_mission = None
        if latest_snapshot is not None:
            snapshot_data = {
                "status": latest_snapshot.status,
                "elapsed_s": latest_snapshot.elapsed_s,
                "resources_json": latest_snapshot.resources_json,
                "active_route_json": latest_snapshot.active_route_json,
                "anomaly_active": latest_snapshot.anomaly_active,
            }
            try:
                restored_mission = MissionService.restore_from_snapshot(
                    snapshot_data, audit_events, seed_mission
                )
            except (json.JSONDecodeError, ValueError, KeyError, TypeError):
                # Snapshot reconstruction failed (malformed JSON,
                # invalid Pydantic values, etc.)
                restoration_failed = True
        else:
            # 3f. No snapshot for unfinished run — corrupt/invalid
            restoration_failed = True

        if restoration_failed:
            # End the unusable run to avoid repeated restoration attempts
            with session_factory() as session:
                run_repo = MissionRunRepository(session)
                run_repo.mark_ended(run_id, "RESTORATION_FAILED")
                session.commit()
            # Proceed to create fresh run below
            unfinished_run = None

        if unfinished_run is not None:
            # 3g. Load restored mission into MissionService via public API
            mission_service.restore(restored_mission)

            # 3h. Attach persistence service to existing run
            persistence_service.restore_current_run(
                run_id, restored_mission, latest_snapshot, audit_records
            )
        else:
            # Fall through to create new run
            initial_mission = mission_service.get_mission()
            persistence_service.create_initial_run(initial_mission)
    else:
        # 4. No unfinished run — retain Phase 2B behavior
        # Create new run with initial snapshot and audit
        initial_mission = mission_service.get_mission()
        persistence_service.create_initial_run(initial_mission)

    # Start telemetry background task
    telemetry_task = asyncio.create_task(telemetry_loop(telemetry_service, ws_manager))
    app.state.telemetry_task = telemetry_task

    yield

    # Shutdown: cancel telemetry task
    if telemetry_task is not None:
        telemetry_task.cancel()
        try:
            await telemetry_task
        except asyncio.CancelledError:
            pass

    # Dispose engine
    engine.dispose()


def create_app() -> FastAPI:
    application = FastAPI(
        title="LunaYield Mission Lab",
        version="1.0.0",
        description="Lunar rover operations and mission-planning platform.",
        lifespan=lifespan,
    )
    application.include_router(health.router)
    application.include_router(mission.mission_router)
    application.include_router(mission.scenario_router)
    application.include_router(planning.router)
    application.include_router(ws.router)
    application.include_router(history.router)
    return application


app = create_app()
