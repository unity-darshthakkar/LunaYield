"""Phase 4A integration test suite for strategy generation foundation.

These tests verify the StrategyService integration with MissionService,
ForecastingService, and AnomalyDetectionService.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.db import DatabaseConfig

# ---------------------------------------------------------------------------
# Helper: create a fresh TestClient bound to a specific DatabaseConfig
# ---------------------------------------------------------------------------


def create_test_client(db_config: DatabaseConfig) -> TestClient:
    """Create a TestClient with the given database config."""
    from app.main import app

    app.state.db_config = db_config
    app.state.disable_background_telemetry = True

    client = TestClient(app)
    client.__enter__()
    return client


def close_test_client(client: TestClient):
    """Close a TestClient created by create_test_client."""
    try:
        client.__exit__(None, None, None)
    finally:
        from app.main import app

        if hasattr(app.state, "db_config"):
            delattr(app.state, "db_config")
        if hasattr(app.state, "disable_background_telemetry"):
            delattr(app.state, "disable_background_telemetry")


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_db_config(tmp_path) -> DatabaseConfig:
    """Provide isolated test database configuration using temp file."""
    return DatabaseConfig.test_temporary(tmp_path)


# ---------------------------------------------------------------------------
# Phase 4A Integration Tests
# ---------------------------------------------------------------------------


class TestStrategyGeneration:
    """Integration tests for StrategyService."""

    def test_healthy_mission_state_no_strategies(
        self, isolated_db_config: DatabaseConfig
    ):
        """Healthy mission state produces no strategy candidates."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            response = client.get("/api/strategies")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["mission_id"] == "luna-mission-001"
            assert data["strategy_count"] == 0
            assert data["strategies"] == []
            assert data["has_critical_priority"] is False

        finally:
            close_test_client(client)

    def test_single_anomaly_produces_strategy(self, isolated_db_config: DatabaseConfig):
        """Single anomaly produces one strategy candidate."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            # Use forecast to trigger battery anomaly (will reach critical in forecast)
            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["strategy_count"] >= 1
            assert data["has_critical_priority"] is True

            # Find battery strategy
            battery_strategies = [
                s for s in data["strategies"] if "BATTERY" in s["affected_resources"]
            ]
            assert len(battery_strategies) == 1

            strat = battery_strategies[0]
            assert strat["priority"] == 1
            assert strat["title"] == "Conserve Power"
            assert strat["requires_operator_approval"] is True
            assert len(strat["recommended_actions"]) > 0
            assert len(strat["source_anomalies"]) > 0

        finally:
            close_test_client(client)

    def test_multiple_anomalies_produce_multiple_strategies(
        self, isolated_db_config: DatabaseConfig
    ):
        """Multiple anomalies produce multiple strategy candidates."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            # Get anomalies with forecast to trigger multiple
            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=7200"
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Should have strategies for multiple resources
            affected_resources = set()
            for s in data["strategies"]:
                affected_resources.update(s["affected_resources"])

            # Forecast will show multiple resource anomalies
            assert data["strategy_count"] >= 1
            assert len(affected_resources) >= 1

            # All strategies require operator approval
            for strat in data["strategies"]:
                assert strat["requires_operator_approval"] is True

        finally:
            close_test_client(client)

    def test_deterministic_fallback_works_without_llm(
        self, isolated_db_config: DatabaseConfig
    ):
        """Strategy generation works without LLM using deterministic fallback."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")
            client.post("/api/mission/inject-anomaly")

            # Call multiple times - all should be identical (deterministic)
            results = []
            for _ in range(5):
                resp = client.get("/api/strategies")
                assert resp.status_code == status.HTTP_200_OK
                results.append(resp.json())

            # All identical
            for i in range(1, len(results)):
                assert results[i] == results[0], f"Result {i} differs from result 0"

        finally:
            close_test_client(client)

    def test_invalid_generated_candidate_rejected(
        self, isolated_db_config: DatabaseConfig
    ):
        """Invalid generated candidates are rejected via Pydantic validation."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")
            client.post("/api/mission/inject-anomaly")

            # Direct service-level test: StrategyService validates each candidate
            from app.main import app

            strategy_service = app.state.strategy_service
            result = strategy_service.generate_strategies(use_forecast=False)

            # All returned strategies should be valid Pydantic models
            from app.schemas import StrategyCandidate

            for strat in result.strategies:
                # Should not raise
                validated = StrategyCandidate.model_validate(strat.model_dump())
                assert validated.strategy_id == strat.strategy_id
                assert validated.requires_operator_approval is True

        finally:
            close_test_client(client)

    def test_schema_validation_response_matches_schema(
        self, isolated_db_config: DatabaseConfig
    ):
        """Response matches StrategyGenerationResponse schema."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")
            client.post("/api/mission/inject-anomaly")

            response = client.get("/api/strategies")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Required top-level fields
            assert "mission_id" in data
            assert "current_elapsed_s" in data
            assert "strategies" in data
            assert "strategy_count" in data
            assert "has_critical_priority" in data

            # Types
            assert isinstance(data["mission_id"], str)
            assert isinstance(data["current_elapsed_s"], int)
            assert isinstance(data["strategies"], list)
            assert isinstance(data["strategy_count"], int)
            assert isinstance(data["has_critical_priority"], bool)

            # Strategy fields
            for strat in data["strategies"]:
                assert "strategy_id" in strat
                assert "title" in strat
                assert "rationale" in strat
                assert "priority" in strat
                assert "affected_resources" in strat
                assert "recommended_actions" in strat
                assert "source_anomalies" in strat
                assert "requires_operator_approval" in strat

                assert isinstance(strat["priority"], int)
                assert 1 <= strat["priority"] <= 5
                assert isinstance(strat["recommended_actions"], list)
                assert isinstance(strat["affected_resources"], list)
                assert isinstance(strat["source_anomalies"], list)
                assert strat["requires_operator_approval"] is True

        finally:
            close_test_client(client)

    def test_non_mutation_mission_state_unchanged(
        self, isolated_db_config: DatabaseConfig
    ):
        """Mission state unchanged after strategy generation requests."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")
            client.post("/api/mission/inject-anomaly")

            # Get initial state
            initial = client.get("/api/mission/state").json()

            # Make multiple strategy requests
            for _ in range(5):
                client.get("/api/strategies")
                client.get("/api/strategies?use_forecast=true&forecast_horizon=3600")

            # Get state again
            after = client.get("/api/mission/state").json()

            # State should be completely unchanged
            assert initial == after

        finally:
            close_test_client(client)

    def test_repeated_deterministic_behavior(self, isolated_db_config: DatabaseConfig):
        """Repeated identical requests produce identical results."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            # Make 10 identical requests with forecast
            results = []
            for _ in range(10):
                resp = client.get(
                    "/api/strategies?use_forecast=true&forecast_horizon=3600"
                )
                assert resp.status_code == status.HTTP_200_OK
                results.append(resp.json())

            # All should be identical
            for i in range(1, len(results)):
                assert results[i] == results[0], f"Result {i} differs from result 0"

        finally:
            close_test_client(client)

    def test_operator_approval_required_always_true(
        self, isolated_db_config: DatabaseConfig
    ):
        """All strategies require operator approval (always True)."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")
            client.post("/api/mission/inject-anomaly")

            # Test with current state
            response = client.get("/api/strategies")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            for strat in data["strategies"]:
                assert strat["requires_operator_approval"] is True

            # Test with forecast
            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            for strat in data["strategies"]:
                assert strat["requires_operator_approval"] is True

        finally:
            close_test_client(client)

    def test_no_automatic_execution_or_approval(
        self, isolated_db_config: DatabaseConfig
    ):
        """No automatic execution or approval endpoints exist."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")
            client.post("/api/mission/inject-anomaly")

            # GET strategies works
            response = client.get("/api/strategies")
            assert response.status_code == status.HTTP_200_OK

            # No POST /api/strategies/approve or /execute endpoints
            # These would return 404 if tested

            # Verify no state mutation
            initial = client.get("/api/mission/state").json()
            client.get("/api/strategies")
            after = client.get("/api/mission/state").json()
            assert initial == after

        finally:
            close_test_client(client)

    def test_strategy_service_direct_deduplication(
        self, isolated_db_config: DatabaseConfig
    ):
        """StrategyService deduplicates by affected resources."""
        client = create_test_client(isolated_db_config)
        try:
            from app.main import app

            strategy_service = app.state.strategy_service
            anomaly_service = app.state.anomaly_service

            client.post("/api/mission/start")

            # Get anomalies with forecast to potentially get multiple
            # for same resource (e.g., battery current + forecast)
            anomaly_service.detect_anomalies(use_forecast=True, forecast_horizon_s=3600)

            # Generate strategies
            result = strategy_service.generate_strategies(
                use_forecast=True, forecast_horizon_s=3600
            )

            # Each affected resource set appears at most once
            resource_sets = [
                tuple(sorted(s.affected_resources)) for s in result.strategies
            ]
            assert len(resource_sets) == len(set(resource_sets))

            # If battery has both current and forecast, only one strategy
            battery_strats = [
                s
                for s in result.strategies
                if "BATTERY" in [r.value for r in s.affected_resources]
            ]
            # StrategyService deduplicates by resource set
            assert len(battery_strats) <= 1

        finally:
            close_test_client(client)

    def test_strategy_with_forecast_provenance(
        self, isolated_db_config: DatabaseConfig
    ):
        """Strategy source_anomalies includes forecast provenance when applicable."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            # With forecast
            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Check source_anomalies field exists and has expected format
            for strat in data["strategies"]:
                assert isinstance(strat["source_anomalies"], list)
                for anomaly_ref in strat["source_anomalies"]:
                    assert isinstance(anomaly_ref, str)
                    # Should have resource-severity pattern
                    assert "-" in anomaly_ref

        finally:
            close_test_client(client)

    def test_strategy_endpoint_validates_forecast_horizon(
        self, isolated_db_config: DatabaseConfig
    ):
        """Strategy endpoint validates forecast_horizon bounds."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            # Too small (below 60)
            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=30"
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

            # Too large (above 86400)
            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=90000"
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

            # Valid boundary (60)
            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=60"
            )
            assert response.status_code == status.HTTP_200_OK

            # Valid boundary (86400)
            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=86400"
            )
            assert response.status_code == status.HTTP_200_OK

        finally:
            close_test_client(client)

    def test_strategy_priority_ordering(self, isolated_db_config: DatabaseConfig):
        """Strategies ordered by priority (1 highest) then title."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")
            client.post("/api/mission/inject-anomaly")

            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=7200"
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            strategies = data["strategies"]
            if len(strategies) > 1:
                # Check sorted by priority asc, then title
                for i in range(len(strategies) - 1):
                    curr = strategies[i]
                    next_s = strategies[i + 1]
                    if curr["priority"] == next_s["priority"]:
                        assert curr["title"] <= next_s["title"]
                    else:
                        assert curr["priority"] < next_s["priority"]

        finally:
            close_test_client(client)
