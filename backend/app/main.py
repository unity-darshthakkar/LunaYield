"""LunaYield Mission Lab — FastAPI application."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import (
    DatabaseConfig,
    create_engine_from_config,
    get_session_factory,
    init_db,
)
from app.routers import health, history, mission, planning, ws
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

    # Initialize the first mission run (creates run + initial snapshot + audit)
    # This runs once on startup, not on every request
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
