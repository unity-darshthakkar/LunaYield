"""
Pytest fixtures shared across Phase 1A tests.

Phase 1A only needs an HTTP client bound to the FastAPI app.
The mission-state reset fixture (clean_mission) will be added in Phase 1B
once MissionService exists.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
