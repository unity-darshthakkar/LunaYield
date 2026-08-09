"""Tests for GET /health."""

from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200


def test_health_response_body(client: TestClient) -> None:
    response = client.get("/health")
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "1.0.0"


def test_health_response_has_no_extra_noise(client: TestClient) -> None:
    response = client.get("/health")
    body = response.json()
    assert set(body.keys()) == {"status", "version"}
