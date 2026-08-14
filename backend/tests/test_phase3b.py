"""Phase 3B test suite for anomaly detection foundation.

These tests verify the deterministic backend anomaly detection module,
including anomaly detection, schema validation, and API endpoint behavior.

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
# Phase 3B Anomaly Detection Foundation Tests
# ---------------------------------------------------------------------------


def test_anomaly_service_detects_no_anomalies_at_start(
    isolated_db_config: DatabaseConfig,
):
    """Verify AnomalyDetectionService returns no anomalies for fresh mission state."""
    client = create_test_client(isolated_db_config)
    try:
        # Start a mission
        client.post("/api/mission/start")

        # Get the anomaly service directly from app state
        from app.main import app

        anomaly_service = app.state.anomaly_service

        # Detect anomalies (current state only)
        result = anomaly_service.detect_anomalies(use_forecast=False)

        # Validate response structure
        assert result.mission_id == "luna-mission-001"
        assert result.current_elapsed_s >= 0
        assert result.anomaly_count == 0
        assert result.anomalies == []
        assert result.has_critical is False
        assert result.has_warning is False

    finally:
        close_test_client(client)


def test_anomaly_api_endpoint_returns_correct_schema(
    isolated_db_config: DatabaseConfig,
):
    """Test that the anomaly detection API endpoint returns the correct
    response schema."""
    client = create_test_client(isolated_db_config)
    try:
        # Start a mission
        client.post("/api/mission/start")

        # Call the anomaly detection endpoint
        response = client.get("/api/anomalies")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()

        # Validate top-level fields
        assert "mission_id" in data
        assert "current_elapsed_s" in data
        assert "anomalies" in data
        assert "anomaly_count" in data
        assert "has_critical" in data
        assert "has_warning" in data

        # Validate types
        assert isinstance(data["mission_id"], str)
        assert isinstance(data["current_elapsed_s"], int)
        assert isinstance(data["anomalies"], list)
        assert isinstance(data["anomaly_count"], int)
        assert isinstance(data["has_critical"], bool)
        assert isinstance(data["has_warning"], bool)

        # Validate anomalies structure if any
        for anomaly in data["anomalies"]:
            assert "resource" in anomaly
            assert "severity" in anomaly
            assert "observed_value" in anomaly
            assert "threshold_value" in anomaly
            assert "reason" in anomaly
            assert "is_forecast" in anomaly
            assert "forecast_seconds_ahead" in anomaly

    finally:
        close_test_client(client)


def test_anomaly_api_with_forecast_query_params(isolated_db_config: DatabaseConfig):
    """Test anomaly API with use_forecast and forecast_horizon parameters."""
    client = create_test_client(isolated_db_config)
    try:
        # Start a mission
        client.post("/api/mission/start")

        # Call with forecast enabled
        response = client.get("/api/anomalies?use_forecast=true&forecast_horizon=3600")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["mission_id"] == "luna-mission-001"

    finally:
        close_test_client(client)


def test_anomaly_api_validates_forecast_horizon(isolated_db_config: DatabaseConfig):
    """Test that anomaly API validates forecast_horizon parameter bounds."""
    client = create_test_client(isolated_db_config)
    try:
        client.post("/api/mission/start")

        # Test invalid horizon (too small)
        response = client.get("/api/anomalies?use_forecast=true&forecast_horizon=30")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test invalid horizon (too large)
        response = client.get("/api/anomalies?use_forecast=true&forecast_horizon=86401")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test valid boundary values
        response = client.get("/api/anomalies?use_forecast=true&forecast_horizon=60")
        assert response.status_code == status.HTTP_200_OK

        response = client.get("/api/anomalies?use_forecast=true&forecast_horizon=86400")
        assert response.status_code == status.HTTP_200_OK

    finally:
        close_test_client(client)


def test_anomaly_detection_is_deterministic(isolated_db_config: DatabaseConfig):
    """Test that anomaly detection produces deterministic results given
    the same state."""
    client = create_test_client(isolated_db_config)
    try:
        # Start a mission
        client.post("/api/mission/start")

        # Get anomalies twice
        response1 = client.get("/api/anomalies")
        response2 = client.get("/api/anomalies")

        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK

        data1 = response1.json()
        data2 = response2.json()

        # Should be identical
        assert data1 == data2

    finally:
        close_test_client(client)


def test_anomaly_detection_with_forecast_is_deterministic(
    isolated_db_config: DatabaseConfig,
):
    """Test that anomaly detection with forecast produces deterministic results."""
    client = create_test_client(isolated_db_config)
    try:
        # Start a mission
        client.post("/api/mission/start")

        # Get anomalies with forecast twice
        response1 = client.get("/api/anomalies?use_forecast=true&forecast_horizon=3600")
        response2 = client.get("/api/anomalies?use_forecast=true&forecast_horizon=3600")

        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK

        data1 = response1.json()
        data2 = response2.json()

        # Should be identical
        assert data1 == data2

    finally:
        close_test_client(client)


def test_anomaly_detection_does_not_mutate_mission_state(
    isolated_db_config: DatabaseConfig,
):
    """Test that anomaly detection does not mutate the mission state."""
    client = create_test_client(isolated_db_config)
    try:
        # Start a mission
        client.post("/api/mission/start")

        # Get initial mission state
        initial_response = client.get("/api/mission/state")
        assert initial_response.status_code == status.HTTP_200_OK
        initial_state = initial_response.json()

        # Call anomaly detection (should not change state)
        anomaly_response = client.get("/api/anomalies")
        assert anomaly_response.status_code == status.HTTP_200_OK

        # Get mission state again
        after_response = client.get("/api/mission/state")
        assert after_response.status_code == status.HTTP_200_OK
        after_state = after_response.json()

        # Mission state should be unchanged
        assert initial_state == after_state

    finally:
        close_test_client(client)


def test_anomaly_resource_enum_values(isolated_db_config: DatabaseConfig):
    """Verify AnomalyResource enum has all expected values."""
    from app.schemas import AnomalyResource

    expected = {
        "BATTERY",
        "STORAGE",
        "TEMPERATURE",
        "COMM_WINDOW",
        "OP_TIME",
    }
    actual = {a.value for a in AnomalyResource}
    assert actual == expected


def test_anomaly_severity_enum_values(isolated_db_config: DatabaseConfig):
    """Verify AnomalySeverity enum has all expected values."""
    from app.schemas import AnomalySeverity

    expected = {"INFO", "WARNING", "CRITICAL"}
    actual = {a.value for a in AnomalySeverity}
    assert actual == expected


def test_anomaly_finding_provenance_fields(isolated_db_config: DatabaseConfig):
    """Test that AnomalyFinding includes is_forecast and forecast_seconds_ahead."""
    from app.schemas import AnomalyFinding, AnomalyResource, AnomalySeverity

    # Current-state finding
    current = AnomalyFinding(
        resource=AnomalyResource.BATTERY,
        severity=AnomalySeverity.CRITICAL,
        observed_value=5.0,
        threshold_value=10.0,
        reason="Battery critically low",
        is_forecast=False,
        forecast_seconds_ahead=None,
    )
    assert current.is_forecast is False
    assert current.forecast_seconds_ahead is None

    # Forecast finding
    forecast = AnomalyFinding(
        resource=AnomalyResource.BATTERY,
        severity=AnomalySeverity.WARNING,
        observed_value=20.0,
        threshold_value=25.0,
        reason="Battery low (forecast)",
        is_forecast=True,
        forecast_seconds_ahead=1800,
    )
    assert forecast.is_forecast is True
    assert forecast.forecast_seconds_ahead == 1800


def test_anomaly_service_current_findings_have_false_provenance(
    isolated_db_config: DatabaseConfig,
):
    """Current-state anomalies must have is_forecast=False and
    forecast_seconds_ahead=None."""
    client = create_test_client(isolated_db_config)
    try:
        client.post("/api/mission/start")
        from app.main import app

        anomaly_service = app.state.anomaly_service
        result = anomaly_service.detect_anomalies(use_forecast=False)

        # Even with no anomalies, the service runs
        # Verify structure can be validated
        assert result.anomaly_count == 0

        # Inject an anomaly period to have actual findings
        client.post("/api/mission/inject-anomaly")
        result = anomaly_service.detect_anomalies(use_forecast=False)

        # All findings should be current-state
        for anomaly in result.anomalies:
            assert anomaly.is_forecast is False
            assert anomaly.forecast_seconds_ahead is None

    finally:
        close_test_client(client)


def test_anomaly_service_forecast_findings_have_true_provenance(
    isolated_db_config: DatabaseConfig,
):
    """Forecast anomalies must have is_forecast=True and forecast_seconds_ahead set."""
    client = create_test_client(isolated_db_config)
    try:
        client.post("/api/mission/start")
        from app.main import app

        anomaly_service = app.state.anomaly_service
        result = anomaly_service.detect_anomalies(
            use_forecast=True, forecast_horizon_s=36000
        )

        # Should have forecast anomalies
        forecast_anomalies = [a for a in result.anomalies if a.is_forecast]
        assert len(forecast_anomalies) > 0

        for anomaly in forecast_anomalies:
            assert anomaly.is_forecast is True
            assert anomaly.forecast_seconds_ahead is not None
            assert anomaly.forecast_seconds_ahead > 0

    finally:
        close_test_client(client)


def test_deduplication_higher_severity_wins(isolated_db_config: DatabaseConfig):
    """Higher severity (CRITICAL > WARNING > INFO) wins deduplication."""
    from app.main import app
    from app.schemas import AnomalyFinding, AnomalyResource, AnomalySeverity

    client = create_test_client(isolated_db_config)
    try:
        anomaly_service = app.state.anomaly_service

        # Create test anomalies manually using the internal method
        # We test the deduplication logic directly
        anomalies = [
            AnomalyFinding(
                resource=AnomalyResource.BATTERY,
                severity=AnomalySeverity.WARNING,
                observed_value=20.0,
                threshold_value=25.0,
                reason="Battery low",
                is_forecast=False,
                forecast_seconds_ahead=None,
            ),
            AnomalyFinding(
                resource=AnomalyResource.BATTERY,
                severity=AnomalySeverity.CRITICAL,
                observed_value=5.0,
                threshold_value=10.0,
                reason="Battery critically low",
                is_forecast=True,
                forecast_seconds_ahead=1800,
            ),
        ]

        result = anomaly_service._deduplicate_anomalies(anomalies)
        assert len(result) == 1
        assert result[0].severity == AnomalySeverity.CRITICAL
        assert result[0].resource == AnomalyResource.BATTERY

    finally:
        close_test_client(client)


def test_deduplication_current_wins_tie_over_forecast(
    isolated_db_config: DatabaseConfig,
):
    """For equal severity, current-state finding wins over forecast finding."""
    from app.main import app
    from app.schemas import AnomalyFinding, AnomalyResource, AnomalySeverity

    client = create_test_client(isolated_db_config)
    try:
        anomaly_service = app.state.anomaly_service

        # Create two WARNING anomalies for same resource
        anomalies = [
            AnomalyFinding(
                resource=AnomalyResource.STORAGE,
                severity=AnomalySeverity.WARNING,
                observed_value=90.0,
                threshold_value=85.0,
                reason="Storage high (forecast)",
                is_forecast=True,
                forecast_seconds_ahead=1800,
            ),
            AnomalyFinding(
                resource=AnomalyResource.STORAGE,
                severity=AnomalySeverity.WARNING,
                observed_value=88.0,
                threshold_value=85.0,
                reason="Storage high",
                is_forecast=False,
                forecast_seconds_ahead=None,
            ),
        ]

        result = anomaly_service._deduplicate_anomalies(anomalies)
        assert len(result) == 1
        assert result[0].severity == AnomalySeverity.WARNING
        assert result[0].is_forecast is False  # Current wins tie
        assert result[0].resource == AnomalyResource.STORAGE

    finally:
        close_test_client(client)


def test_deduplication_earliest_forecast_wins_tie(
    isolated_db_config: DatabaseConfig,
):
    """For equal severity forecast findings, earliest threshold crossing wins."""
    from app.main import app
    from app.schemas import AnomalyFinding, AnomalyResource, AnomalySeverity

    client = create_test_client(isolated_db_config)
    try:
        anomaly_service = app.state.anomaly_service

        # Create two WARNING forecast anomalies for same resource
        anomalies = [
            AnomalyFinding(
                resource=AnomalyResource.COMM_WINDOW,
                severity=AnomalySeverity.WARNING,
                observed_value=600,
                threshold_value=900,
                reason="Comms window short (forecast at 7200s)",
                is_forecast=True,
                forecast_seconds_ahead=7200,
            ),
            AnomalyFinding(
                resource=AnomalyResource.COMM_WINDOW,
                severity=AnomalySeverity.WARNING,
                observed_value=800,
                threshold_value=900,
                reason="Comms window short (forecast at 3600s)",
                is_forecast=True,
                forecast_seconds_ahead=3600,
            ),
        ]

        result = anomaly_service._deduplicate_anomalies(anomalies)
        assert len(result) == 1
        assert result[0].severity == AnomalySeverity.WARNING
        # Earlier crossing (smaller forecast_seconds_ahead) should win
        assert result[0].forecast_seconds_ahead == 3600
        assert result[0].resource == AnomalyResource.COMM_WINDOW

    finally:
        close_test_client(client)


def test_deduplication_preserves_reason_text(isolated_db_config: DatabaseConfig):
    """Deduplication should keep the reason text from the winning anomaly."""
    from app.main import app
    from app.schemas import AnomalyFinding, AnomalyResource, AnomalySeverity

    client = create_test_client(isolated_db_config)
    try:
        anomaly_service = app.state.anomaly_service

        anomalies = [
            AnomalyFinding(
                resource=AnomalyResource.OP_TIME,
                severity=AnomalySeverity.WARNING,
                observed_value=1500,
                threshold_value=1800,
                reason="Op time low at 1500s (forecast at 3600s)",
                is_forecast=True,
                forecast_seconds_ahead=3600,
            ),
            AnomalyFinding(
                resource=AnomalyResource.OP_TIME,
                severity=AnomalySeverity.CRITICAL,
                observed_value=400,
                threshold_value=600,
                reason="Op time critically low at 400s",
                is_forecast=False,
                forecast_seconds_ahead=None,
            ),
        ]

        result = anomaly_service._deduplicate_anomalies(anomalies)
        assert len(result) == 1
        # CRITICAL wins, so we should get the CRITICAL reason
        assert result[0].severity == AnomalySeverity.CRITICAL
        assert "critically low" in result[0].reason

    finally:
        close_test_client(client)


def test_anomaly_detection_with_storage_threshold(isolated_db_config: DatabaseConfig):
    """Test anomaly detection for storage thresholds with meaningful assertions."""
    from app.schemas import AnomalySeverity

    client = create_test_client(isolated_db_config)
    try:
        client.post("/api/mission/start")
        from app.main import app

        anomaly_service = app.state.anomaly_service

        # With long forecast, storage increases and should hit warning/critical
        result = anomaly_service.detect_anomalies(
            use_forecast=True, forecast_horizon_s=72000
        )

        storage_anomalies = [
            a for a in result.anomalies if a.resource.value == "STORAGE"
        ]
        assert len(storage_anomalies) <= 1  # Deduplicated
        if storage_anomalies:
            anomaly = storage_anomalies[0]
            assert anomaly.severity in (
                AnomalySeverity.WARNING,
                AnomalySeverity.CRITICAL,
            )
            assert anomaly.threshold_value in (85.0, 95.0)
            # Validate provenance
            assert anomaly.is_forecast is True
            assert anomaly.forecast_seconds_ahead is not None

    finally:
        close_test_client(client)


def test_anomaly_detection_with_temperature_thresholds(
    isolated_db_config: DatabaseConfig,
):
    """Test anomaly detection for temperature thresholds."""
    from app.schemas import AnomalySeverity

    client = create_test_client(isolated_db_config)
    try:
        client.post("/api/mission/start")
        from app.main import app

        anomaly_service = app.state.anomaly_service

        # With long forecast, temperature increases and hits hot thresholds
        result = anomaly_service.detect_anomalies(
            use_forecast=True, forecast_horizon_s=180000
        )

        temp_anomalies = [
            a for a in result.anomalies if a.resource.value == "TEMPERATURE"
        ]
        assert len(temp_anomalies) <= 1  # Deduplicated
        if temp_anomalies:
            anomaly = temp_anomalies[0]
            assert anomaly.severity in (
                AnomalySeverity.WARNING,
                AnomalySeverity.CRITICAL,
            )
            assert anomaly.threshold_value in (40.0, 50.0)
            # Should be forecast since seed temp is -40°C (good)
            assert anomaly.is_forecast is True
            assert anomaly.forecast_seconds_ahead is not None

    finally:
        close_test_client(client)


def test_anomaly_detection_with_comm_window_thresholds(
    isolated_db_config: DatabaseConfig,
):
    """Test anomaly detection for comm window thresholds."""
    from app.schemas import AnomalySeverity

    client = create_test_client(isolated_db_config)
    try:
        client.post("/api/mission/start")
        from app.main import app

        anomaly_service = app.state.anomaly_service

        # Comm window drains 2s per tick from 7200s
        result = anomaly_service.detect_anomalies(
            use_forecast=True, forecast_horizon_s=15000
        )

        comm_anomalies = [
            a for a in result.anomalies if a.resource.value == "COMM_WINDOW"
        ]
        assert len(comm_anomalies) <= 1  # Deduplicated
        if comm_anomalies:
            anomaly = comm_anomalies[0]
            assert anomaly.severity in (
                AnomalySeverity.WARNING,
                AnomalySeverity.CRITICAL,
            )
            assert anomaly.threshold_value in (900, 300)
            assert anomaly.is_forecast is True
            assert anomaly.forecast_seconds_ahead is not None

    finally:
        close_test_client(client)


def test_anomaly_detection_with_op_time_thresholds(isolated_db_config: DatabaseConfig):
    """Test anomaly detection for operational time thresholds."""
    from app.schemas import AnomalySeverity

    client = create_test_client(isolated_db_config)
    try:
        client.post("/api/mission/start")
        from app.main import app

        anomaly_service = app.state.anomaly_service

        # Op time drains 2s per tick from 28800s
        result = anomaly_service.detect_anomalies(
            use_forecast=True, forecast_horizon_s=30000
        )

        op_time_anomalies = [
            a for a in result.anomalies if a.resource.value == "OP_TIME"
        ]
        assert len(op_time_anomalies) <= 1  # Deduplicated
        if op_time_anomalies:
            anomaly = op_time_anomalies[0]
            assert anomaly.severity in (
                AnomalySeverity.WARNING,
                AnomalySeverity.CRITICAL,
            )
            assert anomaly.threshold_value in (1800, 600)
            assert anomaly.is_forecast is True
            assert anomaly.forecast_seconds_ahead is not None

    finally:
        close_test_client(client)


def test_anomaly_detection_current_state_only(isolated_db_config: DatabaseConfig):
    """Test anomaly detection with use_forecast=False (default)."""
    client = create_test_client(isolated_db_config)
    try:
        # Start a mission
        client.post("/api/mission/start")

        # Call without forecast
        response = client.get("/api/anomalies")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        # Seed mission starts at good levels, so no anomalies expected
        assert data["anomaly_count"] == 0
        assert data["has_critical"] is False
        assert data["has_warning"] is False

    finally:
        close_test_client(client)


def test_anomaly_detection_multiple_resource_anomalies(
    isolated_db_config: DatabaseConfig,
):
    """Test that multiple different resource anomalies can be
    detected simultaneously."""
    client = create_test_client(isolated_db_config)
    try:
        client.post("/api/mission/start")
        from app.main import app

        anomaly_service = app.state.anomaly_service

        # Use very long forecast to hit multiple thresholds
        result = anomaly_service.detect_anomalies(
            use_forecast=True, forecast_horizon_s=360000
        )

        # Verify we can detect anomalies across multiple resources
        resources = {a.resource.value for a in result.anomalies}
        # Should potentially have multiple different resources
        assert len(resources) >= 2

        # Each resource should appear at most once (deduplication)
        assert len(resources) == len(result.anomalies)

    finally:
        close_test_client(client)
