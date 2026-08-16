"""Phase 4B integration test suite for strategy validation and safety hardening.

These tests verify the StrategyValidationService validation logic
and API endpoints.
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


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_db_config(tmp_path) -> DatabaseConfig:
    """Provide isolated test database configuration using temp file."""
    return DatabaseConfig.test_temporary(tmp_path)


# ---------------------------------------------------------------------------
# Phase 4B Integration Tests
# ---------------------------------------------------------------------------


class TestStrategyValidationService:
    """Integration tests for StrategyValidationService."""

    def test_validate_healthy_mission_state(self, isolated_db_config: DatabaseConfig):
        """Validate strategies for healthy mission (should be valid if well-formed)."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            # Use GET endpoint to generate and validate
            response = client.get("/api/strategies")
            assert response.status_code == status.HTTP_200_OK
            generation = response.json()

            # Validate the generated strategies
            response = client.post("/api/strategies/validate", json=generation)
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["mission_id"] == "luna-mission-001"
            assert data["validation_count"] == generation["strategy_count"]
            # Healthy mission has no strategies (empty list)
            assert data["all_valid"] is True

        finally:
            close_test_client(client)

    def test_validate_single_strategy(self, isolated_db_config: DatabaseConfig):
        """Validate a single strategy candidate."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            # Get strategies with forecast to trigger anomalies
            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            assert response.status_code == status.HTTP_200_OK
            generation = response.json()

            assert generation["strategy_count"] >= 1

            # Validate them
            response = client.post("/api/strategies/validate", json=generation)
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["validation_count"] == generation["strategy_count"]
            assert len(data["validation_results"]) == generation["strategy_count"]

            for result in data["validation_results"]:
                assert "strategy_id" in result
                assert "is_valid" in result
                assert "rejection_reasons" in result
                # Generated strategies should be valid
                assert result["is_valid"] is True
                assert result["rejection_reasons"] == []

        finally:
            close_test_client(client)

    def test_validate_multiple_strategies(self, isolated_db_config: DatabaseConfig):
        """Validate multiple strategy candidates."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            # Get strategies with larger forecast horizon for multiple anomalies
            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=7200"
            )
            assert response.status_code == status.HTTP_200_OK
            generation = response.json()

            assert generation["strategy_count"] >= 1

            # Validate them
            response = client.post("/api/strategies/validate", json=generation)
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["validation_count"] == generation["strategy_count"]
            assert len(data["validation_results"]) == generation["strategy_count"]
            assert data["all_valid"] is True

        finally:
            close_test_client(client)

    def test_validate_empty_strategy_list(self, isolated_db_config: DatabaseConfig):
        """Validate empty strategy list returns all_valid=True."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            # No forecast = no anomalies = no strategies
            response = client.get("/api/strategies")
            assert response.status_code == status.HTTP_200_OK
            generation = response.json()

            assert generation["strategy_count"] == 0

            # Validate empty list
            response = client.post("/api/strategies/validate", json=generation)
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["validation_count"] == 0
            assert data["validation_results"] == []
            assert data["all_valid"] is True

        finally:
            close_test_client(client)

    def test_reject_invalid_strategy_id_format(
        self, isolated_db_config: DatabaseConfig
    ):
        """Reject strategy with invalid strategy_id format."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            assert response.status_code == status.HTTP_200_OK
            generation = response.json()

            # Modify first strategy to have invalid ID
            if generation["strategies"]:
                generation["strategies"][0]["strategy_id"] = "invalid-id-123"

                # Test validation service directly (bypasses API Pydantic validation)
                from app.main import app

                validation_service = app.state.validation_service
                from app.schemas import StrategyGenerationResponse

                gen_obj = StrategyGenerationResponse.model_validate(generation)
                data = validation_service.validate_strategies(
                    strategies=gen_obj.strategies,
                    mission_id=gen_obj.mission_id,
                    current_elapsed_s=gen_obj.current_elapsed_s,
                )

                assert data.all_valid is False
                assert data.validation_count >= 1

                invalid_result = data.validation_results[0]
                assert invalid_result.is_valid is False
                expected = "strategy_id must start with 'strat-'"
                assert any(expected in r for r in invalid_result.rejection_reasons)

        finally:
            close_test_client(client)

    def test_reject_empty_required_fields(self, isolated_db_config: DatabaseConfig):
        """Reject strategy with empty required fields (title, rationale)."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            assert response.status_code == status.HTTP_200_OK
            generation = response.json()

            if generation["strategies"]:
                # Empty title - test validation service directly
                generation["strategies"][0]["title"] = ""

                from app.main import app

                validation_service = app.state.validation_service
                from app.schemas import StrategyGenerationResponse

                gen_obj = StrategyGenerationResponse.model_validate(generation)
                data = validation_service.validate_strategies(
                    strategies=gen_obj.strategies,
                    mission_id=gen_obj.mission_id,
                    current_elapsed_s=gen_obj.current_elapsed_s,
                )

                assert data.all_valid is False
                invalid_result = data.validation_results[0]
                assert invalid_result.is_valid is False
                expected = "title is empty"
                assert any(expected in r for r in invalid_result.rejection_reasons)

        finally:
            close_test_client(client)

    def test_reject_invalid_priority_out_of_range_direct_service(
        self, isolated_db_config: DatabaseConfig
    ):
        """Reject strategy with priority outside 1-5 range (direct service test)."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            assert response.status_code == status.HTTP_200_OK
            generation = response.json()

            if generation["strategies"]:
                # Create invalid StrategyCandidate using model_construct
                # to bypass Pydantic validation
                from app.schemas import StrategyCandidate

                s = generation["strategies"][0]
                invalid_strategy = StrategyCandidate.model_construct(
                    strategy_id=s["strategy_id"],
                    title=s["title"],
                    rationale=s["rationale"],
                    priority=0,  # Invalid - below minimum
                    affected_resources=s["affected_resources"],
                    recommended_actions=s["recommended_actions"],
                    source_anomalies=s["source_anomalies"],
                    requires_operator_approval=s["requires_operator_approval"],
                )

                from app.main import app

                validation_service = app.state.validation_service

                data = validation_service.validate_strategies(
                    strategies=[invalid_strategy],
                    mission_id=generation["mission_id"],
                    current_elapsed_s=generation["current_elapsed_s"],
                )

                assert data.all_valid is False
                invalid_result = data.validation_results[0]
                assert invalid_result.is_valid is False
                expected = "priority 0 out of range"
                assert any(expected in r for r in invalid_result.rejection_reasons)

        finally:
            close_test_client(client)

    def test_reject_requires_operator_approval_false(
        self, isolated_db_config: DatabaseConfig
    ):
        """Reject strategy with requires_operator_approval=False."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            assert response.status_code == status.HTTP_200_OK
            generation = response.json()

            if generation["strategies"]:
                generation["strategies"][0]["requires_operator_approval"] = False

                from app.main import app

                validation_service = app.state.validation_service
                from app.schemas import StrategyGenerationResponse

                gen_obj = StrategyGenerationResponse.model_validate(generation)
                data = validation_service.validate_strategies(
                    strategies=gen_obj.strategies,
                    mission_id=gen_obj.mission_id,
                    current_elapsed_s=gen_obj.current_elapsed_s,
                )

                assert data.all_valid is False
                invalid_result = data.validation_results[0]
                assert invalid_result.is_valid is False
                assert any(
                    "requires_operator_approval must be true" in r
                    for r in invalid_result.rejection_reasons
                )

        finally:
            close_test_client(client)

    def test_reject_empty_affected_resources(self, isolated_db_config: DatabaseConfig):
        """Reject strategy with empty affected_resources."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            assert response.status_code == status.HTTP_200_OK
            generation = response.json()

            if generation["strategies"]:
                generation["strategies"][0]["affected_resources"] = []

                from app.main import app

                validation_service = app.state.validation_service
                from app.schemas import StrategyGenerationResponse

                gen_obj = StrategyGenerationResponse.model_validate(generation)
                data = validation_service.validate_strategies(
                    strategies=gen_obj.strategies,
                    mission_id=gen_obj.mission_id,
                    current_elapsed_s=gen_obj.current_elapsed_s,
                )

                assert data.all_valid is False
                invalid_result = data.validation_results[0]
                assert invalid_result.is_valid is False
                assert any(
                    "affected_resources must not be empty" in r
                    for r in invalid_result.rejection_reasons
                )

        finally:
            close_test_client(client)

    def test_reject_unknown_resource_reference(
        self, isolated_db_config: DatabaseConfig
    ):
        """Reject strategy with unknown AnomalyResource in affected_resources."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            assert response.status_code == status.HTTP_200_OK
            generation = response.json()

            if generation["strategies"]:
                # Create invalid StrategyCandidate using model_construct
                # to bypass Pydantic validation
                from app.schemas import StrategyCandidate

                s = generation["strategies"][0]
                invalid_strategy = StrategyCandidate.model_construct(
                    strategy_id=s["strategy_id"],
                    title=s["title"],
                    rationale=s["rationale"],
                    priority=s["priority"],
                    affected_resources=["UNKNOWN_RESOURCE"],  # Invalid resource
                    recommended_actions=s["recommended_actions"],
                    source_anomalies=s["source_anomalies"],
                    requires_operator_approval=s["requires_operator_approval"],
                )

                from app.main import app

                validation_service = app.state.validation_service

                data = validation_service.validate_strategies(
                    strategies=[invalid_strategy],
                    mission_id=generation["mission_id"],
                    current_elapsed_s=generation["current_elapsed_s"],
                )

                assert data.all_valid is False
                invalid_result = data.validation_results[0]
                assert invalid_result.is_valid is False
                expected = "unknown resource reference: UNKNOWN_RESOURCE"
                assert any(expected in r for r in invalid_result.rejection_reasons)

        finally:
            close_test_client(client)

    def test_reject_empty_recommended_actions(self, isolated_db_config: DatabaseConfig):
        """Reject strategy with empty recommended_actions."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            assert response.status_code == status.HTTP_200_OK
            generation = response.json()

            if generation["strategies"]:
                generation["strategies"][0]["recommended_actions"] = []

                from app.main import app

                validation_service = app.state.validation_service
                from app.schemas import StrategyGenerationResponse

                gen_obj = StrategyGenerationResponse.model_validate(generation)
                data = validation_service.validate_strategies(
                    strategies=gen_obj.strategies,
                    mission_id=gen_obj.mission_id,
                    current_elapsed_s=gen_obj.current_elapsed_s,
                )

                assert data.all_valid is False
                invalid_result = data.validation_results[0]
                assert invalid_result.is_valid is False
                assert any(
                    "recommended_actions must not be empty" in r
                    for r in invalid_result.rejection_reasons
                )

        finally:
            close_test_client(client)

    def test_reject_unsupported_action(self, isolated_db_config: DatabaseConfig):
        """Reject strategy with unsupported action not in SUPPORTED_ACTIONS."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            assert response.status_code == status.HTTP_200_OK
            generation = response.json()

            if generation["strategies"]:
                # Add action not in SUPPORTED_ACTIONS - test validation service directly
                generation["strategies"][0]["recommended_actions"] = [
                    "Launch into orbit immediately"
                ]

                from app.main import app

                validation_service = app.state.validation_service
                from app.schemas import StrategyGenerationResponse

                gen_obj = StrategyGenerationResponse.model_validate(generation)
                data = validation_service.validate_strategies(
                    strategies=gen_obj.strategies,
                    mission_id=gen_obj.mission_id,
                    current_elapsed_s=gen_obj.current_elapsed_s,
                )

                assert data.all_valid is False
                invalid_result = data.validation_results[0]
                assert invalid_result.is_valid is False
                expected = "unsupported action: Launch into orbit immediately"
                assert any(expected in r for r in invalid_result.rejection_reasons)

        finally:
            close_test_client(client)

    def test_reject_malformed_source_anomalies(
        self, isolated_db_config: DatabaseConfig
    ):
        """Reject strategy with malformed source_anomalies (missing '-')."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            assert response.status_code == status.HTTP_200_OK
            generation = response.json()

            if generation["strategies"]:
                generation["strategies"][0]["source_anomalies"] = ["malformed"]

                from app.main import app

                validation_service = app.state.validation_service
                from app.schemas import StrategyGenerationResponse

                gen_obj = StrategyGenerationResponse.model_validate(generation)
                data = validation_service.validate_strategies(
                    strategies=gen_obj.strategies,
                    mission_id=gen_obj.mission_id,
                    current_elapsed_s=gen_obj.current_elapsed_s,
                )

                assert data.all_valid is False
                invalid_result = data.validation_results[0]
                assert invalid_result.is_valid is False
                assert any(
                    "malformed source anomaly reference: malformed" in r
                    for r in invalid_result.rejection_reasons
                )

        finally:
            close_test_client(client)

    def test_validate_supported_actions_whitelist(
        self, isolated_db_config: DatabaseConfig
    ):
        """All supported actions in SUPPORTED_ACTIONS pass validation."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            assert response.status_code == status.HTTP_200_OK
            generation = response.json()

            if generation["strategies"]:
                from app.main import app

                validation_service = app.state.validation_service
                from app.schemas import StrategyGenerationResponse

                gen_obj = StrategyGenerationResponse.model_validate(generation)
                data = validation_service.validate_strategies(
                    strategies=gen_obj.strategies,
                    mission_id=gen_obj.mission_id,
                    current_elapsed_s=gen_obj.current_elapsed_s,
                )

                assert data.all_valid is True
                for result in data.validation_results:
                    assert result.is_valid is True
                    assert result.rejection_reasons == []

        finally:
            close_test_client(client)

    def test_validate_valid_anomaly_resources(self, isolated_db_config: DatabaseConfig):
        """All valid AnomalyResource values pass validation."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            assert response.status_code == status.HTTP_200_OK
            generation = response.json()

            if generation["strategies"]:
                from app.main import app

                validation_service = app.state.validation_service
                from app.schemas import StrategyGenerationResponse

                gen_obj = StrategyGenerationResponse.model_validate(generation)
                data = validation_service.validate_strategies(
                    strategies=gen_obj.strategies,
                    mission_id=gen_obj.mission_id,
                    current_elapsed_s=gen_obj.current_elapsed_s,
                )

                # All generated strategies should have valid AnomalyResource values
                assert data.all_valid is True

        finally:
            close_test_client(client)

    def test_validate_strategies_endpoint_with_forecast(
        self, isolated_db_config: DatabaseConfig
    ):
        """GET /api/strategies/validate convenience endpoint works."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            # Use convenience endpoint with forecast
            response = client.get(
                "/api/strategies/validate?use_forecast=true&forecast_horizon=3600"
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert "mission_id" in data
            assert "current_elapsed_s" in data
            assert "validation_results" in data
            assert "validation_count" in data
            assert "all_valid" in data

            assert isinstance(data["validation_results"], list)
            assert isinstance(data["validation_count"], int)
            assert isinstance(data["all_valid"], bool)

        finally:
            close_test_client(client)

    def test_validate_strategies_endpoint_without_forecast(
        self, isolated_db_config: DatabaseConfig
    ):
        """GET /api/strategies/validate works without forecast."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            response = client.get("/api/strategies/validate")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["mission_id"] == "luna-mission-001"
            assert data["validation_count"] == len(data["validation_results"])
            assert data["all_valid"] is True

        finally:
            close_test_client(client)

    def test_cross_endpoint_consistency(self, isolated_db_config: DatabaseConfig):
        """Validation endpoints produce consistent results."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            # Direct: GET /api/strategies then validate via service
            gen_response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            assert gen_response.status_code == status.HTTP_200_OK
            generation = gen_response.json()

            from app.main import app

            validation_service = app.state.validation_service
            from app.schemas import StrategyGenerationResponse

            gen_obj = StrategyGenerationResponse.model_validate(generation)
            direct = validation_service.validate_strategies(
                strategies=gen_obj.strategies,
                mission_id=gen_obj.mission_id,
                current_elapsed_s=gen_obj.current_elapsed_s,
            )
            direct_result = direct.model_dump(mode="json")

            # Convenience: GET /api/strategies/validate with same params
            conv_response = client.get(
                "/api/strategies/validate?use_forecast=true&forecast_horizon=3600"
            )
            assert conv_response.status_code == status.HTTP_200_OK
            conv_result = conv_response.json()

            # Both should have same validation outcome
            assert direct_result["validation_count"] == conv_result["validation_count"]
            assert direct_result["all_valid"] == conv_result["all_valid"]

            # Compare each strategy validation result
            vr_direct = direct_result["validation_results"]
            vr_conv = conv_result["validation_results"]
            assert len(vr_direct) == len(vr_conv)
            for direct, conv in zip(
                direct_result["validation_results"], conv_result["validation_results"]
            ):
                assert direct["strategy_id"] == conv["strategy_id"]
                assert direct["is_valid"] == conv["is_valid"]
                assert direct["rejection_reasons"] == conv["rejection_reasons"]

        finally:
            close_test_client(client)

    def test_no_state_mutation_during_validation(
        self, isolated_db_config: DatabaseConfig
    ):
        """Validation does not mutate mission state."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            initial = client.get("/api/mission/state").json()

            from app.main import app

            validation_service = app.state.validation_service
            from app.schemas import StrategyGenerationResponse

            # Valid empty generation for service test
            empty_generation = StrategyGenerationResponse(
                mission_id="luna-mission-001",
                current_elapsed_s=0,
                strategies=[],
                strategy_count=0,
                has_critical_priority=False,
            )

            # Run validation multiple times via service
            for _ in range(5):
                client.get(
                    "/api/strategies/validate?use_forecast=true&forecast_horizon=3600"
                )
                validation_service.validate_strategies(
                    strategies=empty_generation.strategies,
                    mission_id=empty_generation.mission_id,
                    current_elapsed_s=empty_generation.current_elapsed_s,
                )

            after = client.get("/api/mission/state").json()
            assert initial == after

        finally:
            close_test_client(client)

    def test_validation_response_schema(self, isolated_db_config: DatabaseConfig):
        """Validation response matches StrategyValidationResponse schema."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            response = client.get(
                "/api/strategies/validate?use_forecast=true&forecast_horizon=3600"
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Required top-level fields
            assert "mission_id" in data
            assert "current_elapsed_s" in data
            assert "validation_results" in data
            assert "validation_count" in data
            assert "all_valid" in data

            # Types
            assert isinstance(data["mission_id"], str)
            assert isinstance(data["current_elapsed_s"], int)
            assert isinstance(data["validation_results"], list)
            assert isinstance(data["validation_count"], int)
            assert isinstance(data["all_valid"], bool)

            # ValidationResult fields
            for result in data["validation_results"]:
                assert "strategy_id" in result
                assert "is_valid" in result
                assert "rejection_reasons" in result
                assert isinstance(result["strategy_id"], str)
                assert isinstance(result["is_valid"], bool)
                assert isinstance(result["rejection_reasons"], list)

        finally:
            close_test_client(client)

    def test_deterministic_validation_repeatable(
        self, isolated_db_config: DatabaseConfig
    ):
        """Identical strategy inputs produce identical validation results."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            # Get a generation
            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            assert response.status_code == status.HTTP_200_OK
            generation = response.json()

            # Validate multiple times via service
            from app.main import app

            validation_service = app.state.validation_service
            from app.schemas import StrategyGenerationResponse

            gen_obj = StrategyGenerationResponse.model_validate(generation)

            results = []
            for _ in range(5):
                data = validation_service.validate_strategies(
                    strategies=gen_obj.strategies,
                    mission_id=gen_obj.mission_id,
                    current_elapsed_s=gen_obj.current_elapsed_s,
                )
                results.append(data.model_dump(mode="json"))

            # All should be identical
            for i in range(1, len(results)):
                expected = f"Validation result {i} differs from result 0"
                assert results[i] == results[0], expected

        finally:
            close_test_client(client)

    def test_mixed_valid_invalid_strategies(self, isolated_db_config: DatabaseConfig):
        """all_valid is False when mix of valid and invalid strategies."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            assert response.status_code == status.HTTP_200_OK
            generation = response.json()

            if generation["strategies"]:
                # Create two custom strategies: one valid, one invalid
                from app.schemas import StrategyCandidate

                valid_strategy = StrategyCandidate(
                    strategy_id="strat-valid-1",
                    title="Valid Strategy",
                    rationale="Test valid strategy",
                    priority=1,
                    affected_resources=["BATTERY"],
                    recommended_actions=["Disable non-essential science instruments"],
                    source_anomalies=["BATTERY-CRITICAL"],
                    requires_operator_approval=True,
                )

                invalid_strategy = StrategyCandidate(
                    strategy_id="invalid-id",  # Invalid - doesn't start with 'strat-'
                    title="Invalid Strategy",
                    rationale="Test invalid strategy",
                    priority=2,
                    affected_resources=["STORAGE"],
                    recommended_actions=[
                        "Schedule downlink at next available comms window"
                    ],
                    source_anomalies=["STORAGE-WARNING"],
                    requires_operator_approval=True,
                )

                from app.main import app

                validation_service = app.state.validation_service

                data = validation_service.validate_strategies(
                    strategies=[valid_strategy, invalid_strategy],
                    mission_id=generation["mission_id"],
                    current_elapsed_s=generation["current_elapsed_s"],
                )

                assert data.all_valid is False
                # First valid, second invalid
                valid_count = sum(1 for r in data.validation_results if r.is_valid)
                invalid_count = sum(
                    1 for r in data.validation_results if not r.is_valid
                )
                assert valid_count == 1
                assert invalid_count == 1

        finally:
            close_test_client(client)
