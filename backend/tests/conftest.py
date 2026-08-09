"""
Pytest fixtures shared across Phase 1A and Phase 1B tests.

Phase 1A: HTTP client bound to the FastAPI app.
Phase 1B: MissionService fixture for direct service testing,
clean_mission for reset between tests.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.seed import get_seed_mission
from app.services.mission import MissionService
from app.services.planning import PlanningService
from app.services.safety import SafetyVerifier
from app.services.telemetry import TelemetryService


@pytest.fixture
def client() -> TestClient:
    """TestClient as context manager to trigger lifespan.

    Resets the shared MissionService before each test for isolation.
    """
    with TestClient(app) as c:
        mission_service: MissionService = app.state.mission_service
        mission_service.reset()
        yield c
        mission_service.reset()


@pytest.fixture
def clean_mission() -> MissionService:
    """Provide a fresh MissionService with seed mission for each test."""
    service = MissionService()
    # Initialize the seed
    service.get_mission()
    return service


@pytest.fixture
def safety_verifier() -> SafetyVerifier:
    return SafetyVerifier()


@pytest.fixture
def planning_service() -> PlanningService:
    return PlanningService()


@pytest.fixture
def telemetry_service(clean_mission: MissionService) -> TelemetryService:
    return TelemetryService(clean_mission)


@pytest.fixture
def seed_mission():
    """Return the deterministic seed mission directly."""
    return get_seed_mission()
