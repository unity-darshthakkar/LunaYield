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
from app.routers import (
    anomaly,
    approval,
    forecasting,
    health,
    history,
    mission,
    planning,
    strategy,
    validation,
    ws,
)
from app.schemas import (
    AuditEvent,
    Mission,
    MissionStatus,
)
from app.seed import get_seed_mission
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

    Raises:
        ValueError: If any audit event data is invalid or malformed.
    """
    events = []
    for i, record in enumerate(audit_records):
        try:
            metadata = record.to_metadata_dict()
            event = AuditEvent(
                event_id=record.event_id,
                event_type=record.event_type,
                description=record.description,
                timestamp=record.timestamp,
                metadata=metadata,
            )
            events.append(event)
        except Exception as e:
            # If we can't reconstruct an audit event, the audit history is compromised
            raise ValueError(f"Failed to reconstruct audit event at index {i}: {e}")
    return events


def _validate_restored_mission(mission: Mission) -> None:
    """Validate a restored mission for internal consistency and safety.

    Performs additional validation beyond Pydantic model validation to ensure
    the restored mission is safe to use as authoritative state.

    Args:
        mission: The restored mission to validate.

    Raises:
        ValueError: If the mission fails validation checks.
    """
    # Validate that elapsed_s is non-negative
    if mission.elapsed_s < 0:
        raise ValueError(f"elapsed_s cannot be negative: {mission.elapsed_s}")

    # Validate that resources are within bounds (Pydantic should catch this,
    # but double-check)
    if not (0.0 <= mission.resources.battery_pct <= 100.0):
        raise ValueError(f"battery_pct out of range: {mission.resources.battery_pct}")
    if not (0.0 <= mission.resources.storage_pct <= 100.0):
        raise ValueError(f"storage_pct out of range: {mission.resources.storage_pct}")
    if mission.resources.temperature_c < -273.15:  # Absolute zero
        raise ValueError(
            f"temperature_c below absolute zero: {mission.resources.temperature_c}"
        )
    if mission.resources.comm_window_remaining_s < 0:
        raise ValueError(
            f"comm_window_remaining_s cannot be negative: "
            f"{mission.resources.comm_window_remaining_s}"
        )
    if mission.resources.op_time_remaining_s < 0:
        raise ValueError(
            f"op_time_remaining_s cannot be negative: "
            f"{mission.resources.op_time_remaining_s}"
        )

    # Validate waypoints in both routes
    for i, waypoint in enumerate(mission.original_route.waypoints):
        if not (0.0 <= waypoint.x <= 1.0):
            raise ValueError(
                f"original_route waypoint {i} x out of range [0,1]: {waypoint.x}"
            )
        if not (0.0 <= waypoint.y <= 1.0):
            raise ValueError(
                f"original_route waypoint {i} y out of range [0,1]: {waypoint.y}"
            )

    for i, waypoint in enumerate(mission.active_route.waypoints):
        if not (0.0 <= waypoint.x <= 1.0):
            raise ValueError(
                f"active_route waypoint {i} x out of range [0,1]: {waypoint.x}"
            )
        if not (0.0 <= waypoint.y <= 1.0):
            raise ValueError(
                f"active_route waypoint {i} y out of range [0,1]: {waypoint.y}"
            )

    # Validate that status is a valid MissionStatus
    try:
        MissionStatus(mission.status)
    except ValueError:
        raise ValueError(f"Invalid mission status: {mission.status}")

    # Additional state consistency checks
    # If status is EXECUTING, anomaly_active should be False
    # (can't be executing during anomaly)
    if mission.status == MissionStatus.EXECUTING.value and mission.anomaly_active:
        raise ValueError("Cannot be in EXECUTING state with anomaly_active=True")

    # If status is AWAITING_APPROVAL, candidate_plans should normally be empty
    # (they're not persisted)
    # Note: We allow non-empty here as it might be valid in some edge cases,
    # but we warn in logs if needed


def _safe_restore_mission(
    snapshot_data: dict, audit_events: list, seed_mission: Mission
) -> Mission:
    """Safely restore a mission with comprehensive validation.

    Attempts to reconstruct and validate a mission from persisted data.
    If any step fails, raises an exception to trigger fallback to fresh run.

    Args:
        snapshot_data: Dictionary with snapshot fields
        audit_events: List of AuditEvent objects
        seed_mission: The deterministic seed mission

    Returns:
        Validated Mission object ready for use

    Raises:
        (json.JSONDecodeError, ValueError, KeyError, TypeError):
            If restoration fails at any step
    """
    # Reconstruct mission (may raise json.JSONDecodeError,
    # ValueError, KeyError, TypeError)
    restored_mission = MissionService.restore_from_snapshot(
        snapshot_data, audit_events, seed_mission
    )

    # Validate the reconstructed mission (may raise ValueError)
    _validate_restored_mission(restored_mission)

    return restored_mission


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
    ws_manager = WSConnectionManager()
    persistence_service = MissionPersistenceService(session_factory)

    # Set up dependencies
    mission_service.set_dependencies(safety_verifier, planning_service)

    # Store in app state for router access
    app.state.mission_service = mission_service
    app.state.planning_service = planning_service
    app.state.safety_verifier = safety_verifier
    app.state.telemetry_service = telemetry_service
    app.state.forecasting_service = forecasting_service
    app.state.anomaly_service = anomaly_service
    app.state.strategy_service = strategy_service
    app.state.validation_service = validation_service
    app.state.approval_service = approval_service
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
        restoration_failed = False
        audit_events = None
        try:
            audit_events = _reconstruct_audit_events(audit_records)
        except (json.JSONDecodeError, ValueError, KeyError, TypeError):
            # Audit event reconstruction failed (malformed JSON, etc.)
            restoration_failed = True

        # 3e. Reconstruct Mission from snapshot + audit + seed with validation
        restored_mission = None
        if not restoration_failed and latest_snapshot is not None:
            snapshot_data = {
                "status": latest_snapshot.status,
                "elapsed_s": latest_snapshot.elapsed_s,
                "resources_json": latest_snapshot.resources_json,
                "active_route_json": latest_snapshot.active_route_json,
                "anomaly_active": latest_snapshot.anomaly_active,
            }
            try:
                restored_mission = _safe_restore_mission(
                    snapshot_data, audit_events, seed_mission
                )
            except (json.JSONDecodeError, ValueError, KeyError, TypeError):
                # Snapshot reconstruction or validation failed (malformed JSON,
                # invalid Pydantic values, etc.)
                restoration_failed = True
        else:
            # Either audit reconstruction failed or no snapshot
            # for unfinished run — corrupt/invalid
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
            # At this point, restored_mission is guaranteed to be valid
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
    application.include_router(forecasting.router)
    application.include_router(anomaly.router)
    application.include_router(strategy.router)
    application.include_router(validation.router)
    application.include_router(approval.router)
    return application


app = create_app()
