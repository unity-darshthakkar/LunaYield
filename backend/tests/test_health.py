"""Tests for GET /health."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_body(client: AsyncClient) -> None:
    response = await client.get("/health")
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_health_response_has_no_extra_noise(client: AsyncClient) -> None:
    response = await client.get("/health")
    body = response.json()
    assert set(body.keys()) == {"status", "version"}
