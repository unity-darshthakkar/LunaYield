"""Phase 3A test suite for forecasting foundation.

These tests verify the deterministic backend resource forecasting module,
including forecast generation, schema validation, and API endpoint behavior.

All tests use the existing test infrastructure with temporary
file-based SQLite databases via pytest tmp_path fixture.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.db import DatabaseConfig

# ---------------------------------------------------------------------------
# Helper: create a fresh TestClient bound to a specific DatabaseConfig
# ---------------------------------------------------------------------------


def create_test_client(db_config: DatabaseConfig) -> TestClient:
    """Create a TestClient with the given database config.

    Triggers the full FastAPI lifespan (startup -> yield -> shutdown).
    Returns the client within the lifespan context.
    The caller is responsible for closing the client (exits context).
    """
    from app.main import app

    app.state.db_config = db_config

    client = TestClient(app)
    # The lifespan runs on __enter__; trigger it by entering the context
    client.__enter__()

    # Do NOT reset mission service - we want to inspect the state
    # produced by startup restoration.
    return client


def close_test_client(client: TestClient):
    """Close a TestClient created by create_test_client."""
    try:
        client.__exit__(None, None, None)
    finally:
        from app.main import app

        if hasattr(app.state, "db_config"):
            delattr(app.state, "db_config")


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_db_config(tmp_path) -> DatabaseConfig:
    """Provide isolated test database configuration using temp file."""
    return DatabaseConfig.test_temporary(tmp_path)


# ---------------------------------------------------------------------------
# Phase 3A Forecasting Foundation Tests
# ---------------------------------------------------------------------------


def test_forecasting_service_generates_valid_forecast(
    isolated_db_config: DatabaseConfig,
):
    """Verify ForecastingService generates a valid forecast
    with the expected structure.
    """
    client = create_test_client(isolated_db_config)
    try:
        # Start a mission to have some state
        client.post("/api/mission/start")

        # Get the forecasting service directly from app state
        from app.main import app

        forecasting_service = app.state.forecasting_service

        # Generate a forecast
        forecast = forecasting_service.generate_forecast(
            forecast_horizon_s=3600,  # 1 hour
            forecast_tick_interval_s=60,  # 1 minute intervals
        )

        # Validate response structure
        assert forecast.mission_id == "luna-mission-001"
        assert forecast.current_elapsed_s >= 0
        assert hasattr(
            forecast.current_resources, "battery_pct"
        )  # RoverResources object
        assert hasattr(forecast.current_resources, "storage_pct")
        assert hasattr(forecast.current_resources, "temperature_c")
        assert hasattr(forecast.current_resources, "comm_window_remaining_s")
        assert hasattr(forecast.current_resources, "op_time_remaining_s")
        assert forecast.forecast_horizon_s == 3600
        assert forecast.forecast_tick_interval_s == 60
        assert isinstance(forecast.forecast_points, list)
        assert len(forecast.forecast_points) > 0

        # Check first forecast point
        first_point = forecast.forecast_points[0]
        assert first_point.forecast_seconds_ahead == 60
        assert first_point.elapsed_s >= 60
        assert hasattr(first_point.resources, "battery_pct")  # ResourceForecast object
        assert hasattr(first_point.resources, "storage_pct")
        assert hasattr(first_point.resources, "temperature_c")
        assert hasattr(first_point.resources, "comm_window_remaining_s")
        assert hasattr(first_point.resources, "op_time_remaining_s")

        # Validate resource ranges
        for point in forecast.forecast_points:
            assert 0.0 <= point.resources.battery_pct <= 100.0
            assert 0.0 <= point.resources.storage_pct <= 100.0
            assert point.resources.comm_window_remaining_s >= 0
            assert point.resources.op_time_remaining_s >= 0

        # Verify forecast points are in order
        for i in range(1, len(forecast.forecast_points)):
            assert (
                forecast.forecast_points[i].forecast_seconds_ahead
                > forecast.forecast_points[i - 1].forecast_seconds_ahead
            )

    finally:
        close_test_client(client)


def test_forecasting_api_endpoint_returns_correct_schema(
    isolated_db_config: DatabaseConfig,
):
    """Test that the forecasting API endpoint returns the correct response schema."""
    client = create_test_client(isolated_db_config)
    try:
        # Start a mission
        client.post("/api/mission/start")

        # Call the forecasting endpoint
        response = client.get("/api/forecast?horizon=1800&interval=30")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()

        # Validate top-level fields
        assert "mission_id" in data
        assert "current_elapsed_s" in data
        assert "current_resources" in data
        assert "forecast_horizon_s" in data
        assert "forecast_tick_interval_s" in data
        assert "forecast_points" in data

        # Validate types
        assert isinstance(data["mission_id"], str)
        assert isinstance(data["current_elapsed_s"], int)
        assert isinstance(data["current_resources"], dict)  # API returns dict
        assert isinstance(data["forecast_horizon_s"], int)
        assert isinstance(data["forecast_tick_interval_s"], int)
        assert isinstance(data["forecast_points"], list)

        # Validate forecast horizon and interval
        assert data["forecast_horizon_s"] == 1800
        assert data["forecast_tick_interval_s"] == 30

        # Validate forecast points structure
        assert len(data["forecast_points"]) > 0
        for point in data["forecast_points"]:
            assert "forecast_seconds_ahead" in point
            assert "elapsed_s" in point
            assert "resources" in point
            assert isinstance(point["resources"], dict)
            assert "battery_pct" in point["resources"]
            assert "storage_pct" in point["resources"]
            assert "temperature_c" in point["resources"]
            assert "comm_window_remaining_s" in point["resources"]
            assert "op_time_remaining_s" in point["resources"]

    finally:
        close_test_client(client)


def test_forecasting_respects_resource_boundaries(isolated_db_config: DatabaseConfig):
    """Verify forecasting respects resource and time boundaries."""
    client = create_test_client(isolated_db_config)
    try:
        # Start a mission and let it run for a while to consume resources
        client.post("/api/mission/start")
        # Fast-forward by making several telemetry-generating calls
        for _ in range(100):  # Simulate ~200 seconds of runtime
            client.post("/api/mission/inject-anomaly")
            client.post("/api/mission/restart")

        # Generate a long forecast to test boundary conditions
        response = client.get(
            "/api/forecast?horizon=7200&interval=60"
        )  # 2 hour forecast
        assert response.status_code == status.HTTP_200_OK

        data = response.json()

        # Verify all resources stay within bounds
        for point in data["forecast_points"]:
            resources = point["resources"]
            assert 0.0 <= resources["battery_pct"] <= 100.0, (
                f"Battery out of bounds: {resources['battery_pct']}"
            )
            assert 0.0 <= resources["storage_pct"] <= 100.0, (
                f"Storage out of bounds: {resources['storage_pct']}"
            )
            assert resources["comm_window_remaining_s"] >= 0, (
                f"Comm window negative: {resources['comm_window_remaining_s']}"
            )
            assert resources["op_time_remaining_s"] >= 0, (
                f"Op time negative: {resources['op_time_remaining_s']}"
            )
            # Temperature can go below seed but should be reasonable
            assert resources["temperature_c"] >= -50.0, (
                f"Temperature unreasonably low: {resources['temperature_c']}"
            )

    finally:
        close_test_client(client)


def test_forecasting_handles_edge_cases(isolated_db_config: DatabaseConfig):
    """Test forecasting edge cases like zero horizon, invalid parameters."""
    client = create_test_client(isolated_db_config)
    try:
        # Start a mission
        client.post("/api/mission/start")

        # Test invalid horizon (too small)
        response = client.get(
            "/api/forecast?horizon=30&interval=60"
        )  # horizon < interval
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test invalid interval (too small)
        response = client.get(
            "/api/forecast?horizon=3600&interval=5"
        )  # interval < minimum
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test invalid horizon (too large)
        response = client.get("/api/forecast?horizon=86401&interval=60")  # > 24 hours
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test invalid interval (too large)
        response = client.get("/api/forecast?horizon=3600&interval=3601")  # > horizon
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test valid boundary values
        response = client.get("/api/forecast?horizon=60&interval=10")  # minimum valid
        assert response.status_code == status.HTTP_200_OK

        response = client.get(
            "/api/forecast?horizon=86400&interval=3600"
        )  # maximum valid
        assert response.status_code == status.HTTP_200_OK

    finally:
        close_test_client(client)


def test_forecasting_is_deterministic(isolated_db_config: DatabaseConfig):
    """Test that forecasting produces deterministic results given the same state."""
    client = create_test_client(isolated_db_config)
    try:
        # Start a mission and inject a known anomaly
        client.post("/api/mission/start")
        client.post("/api/mission/inject-anomaly")

        # Get forecast twice
        response1 = client.get("/api/forecast?horizon=300&interval=30")
        response2 = client.get("/api/forecast?horizon=300&interval=30")

        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK

        data1 = response1.json()
        data2 = response2.json()

        # Should be identical
        assert data1 == data2

    finally:
        close_test_client(client)


def test_forecasting_does_not_mutate_mission_state(isolated_db_config: DatabaseConfig):
    """Test that forecasting does not mutate the mission state."""
    client = create_test_client(isolated_db_config)
    try:
        # Start a mission
        client.post("/api/mission/start")

        # Get initial mission state
        initial_response = client.get("/api/mission/state")
        assert initial_response.status_code == status.HTTP_200_OK
        initial_state = initial_response.json()

        # Generate a forecast (should not change state)
        forecast_response = client.get("/api/forecast?horizon=3600&interval=60")
        assert forecast_response.status_code == status.HTTP_200_OK

        # Get mission state again
        after_response = client.get("/api/mission/state")
        assert after_response.status_code == status.HTTP_200_OK
        after_state = after_response.json()

        # Mission state should be unchanged
        assert initial_state == after_state

    finally:
        close_test_client(client)


def test_forecasting_uses_current_mission_state(isolated_db_config: DatabaseConfig):
    """Verify that forecasting uses current mission state, not hardcoded seed values."""
    client = create_test_client(isolated_db_config)
    try:
        # Start a mission and modify state by injecting anomaly and waiting
        client.post("/api/mission/start")
        client.post("/api/mission/inject-anomaly")  # Now in ANOMALY state

        # Fast-forward time by simulating several ticks
        # Each tick is ~2 seconds, so 10 ticks = ~20 seconds
        for _ in range(10):
            client.post(
                "/api/mission/inject-anomaly"
            )  # This will toggle anomaly but also advance telemetry tick
            client.post(
                "/api/mission/restart"
            )  # Back to normal state but advances time

        # Get current mission state to verify resources have changed
        state_response = client.get("/api/mission/state")
        assert state_response.status_code == status.HTTP_200_OK
        current_state = state_response.json()

        # Get forecast
        forecast_response = client.get("/api/forecast?horizon=60&interval=30")
        assert forecast_response.status_code == status.HTTP_200_OK
        forecast_data = forecast_response.json()

        # Verify forecast uses current state as baseline
        # Battery should be forecasted from current battery level, not 100%
        assert (
            forecast_data["current_resources"]["battery_pct"]
            == current_state["resources"]["battery_pct"]
        )
        assert (
            forecast_data["current_resources"]["storage_pct"]
            == current_state["resources"]["storage_pct"]
        )
        assert (
            forecast_data["current_resources"]["temperature_c"]
            == current_state["resources"]["temperature_c"]
        )
        assert (
            forecast_data["current_resources"]["comm_window_remaining_s"]
            == current_state["resources"]["comm_window_remaining_s"]
        )
        assert (
            forecast_data["current_resources"]["op_time_remaining_s"]
            == current_state["resources"]["op_time_remaining_s"]
        )

        # Verify first forecast point is based on current state plus changes
        first_forecast = forecast_data["forecast_points"][0]
        assert first_forecast["forecast_seconds_ahead"] == 30
        assert first_forecast["elapsed_s"] == current_state["elapsed_s"] + 30

        # Battery should decrease from current level (not from 100%)
        expected_battery = max(
            0, min(100, current_state["resources"]["battery_pct"] - 0.5 * (30 / 2))
        )
        assert abs(first_forecast["resources"]["battery_pct"] - expected_battery) < 0.1

        # Storage should increase from current level (not from 0%)
        expected_storage = max(
            0, min(100, current_state["resources"]["storage_pct"] + 0.3 * (30 / 2))
        )
        assert abs(first_forecast["resources"]["storage_pct"] - expected_storage) < 0.1

        # Temperature should drift from current level (not from -40)
        expected_temp = current_state["resources"]["temperature_c"] + 0.1 * (30 / 2)
        assert abs(first_forecast["resources"]["temperature_c"] - expected_temp) < 0.1

        # Comm window should decrease from current level (not from 7200)
        expected_comm = max(
            0, current_state["resources"]["comm_window_remaining_s"] - 2 * (30 / 2)
        )
        assert first_forecast["resources"]["comm_window_remaining_s"] == expected_comm

        # Op time should decrease from current level (not from 28800)
        expected_op = max(
            0, current_state["resources"]["op_time_remaining_s"] - 2 * (30 / 2)
        )
        assert first_forecast["resources"]["op_time_remaining_s"] == expected_op

    finally:
        close_test_client(client)
