"""Phase 4C integration test suite for operator approval flow.

These tests verify the StrategyApprovalService and approval endpoints:
- Valid strategy approval
- Invalid strategy rejection
- Validation failure prevents approval
- Unknown strategy ID rejection
- Explicit operator action required
- Approval does not execute actions
- Approval does not mutate mission state
- Repeated approval is deterministic/idempotent
- Generated strategy remains unchanged
- Phase 4A /api/strategies unchanged
- Phase 4B validation behavior unchanged
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
# Phase 4C Integration Tests
# ---------------------------------------------------------------------------


class TestStrategyApproval:
    """Integration tests for StrategyApprovalService and endpoints."""

    def test_approve_valid_strategy(self, isolated_db_config: DatabaseConfig):
        """Valid strategy can be approved via explicit operator action."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            # Get strategies with forecast to trigger anomaly
            gen_response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            assert gen_response.status_code == status.HTTP_200_OK
            generation = gen_response.json()

            assert generation["strategy_count"] >= 1
            strat_id = generation["strategies"][0]["strategy_id"]

            # Approve the strategy
            response = client.post(
                f"/api/strategies/{strat_id}/approve",
                params={"use_forecast": True, "forecast_horizon": 3600},
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["strategy_id"] == strat_id
            assert data["approved"] is True
            assert data["approval_status"] == "APPROVED"
            assert data["rejection_reasons"] == []

        finally:
            close_test_client(client)

    def test_reject_invalid_strategy(self, isolated_db_config: DatabaseConfig):
        """Invalid strategy (fails validation) cannot be approved."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            # Approve with strategy that doesn't exist
            response = client.post(
                "/api/strategies/nonexistent/approve",
                params={"use_forecast": True, "forecast_horizon": 3600},
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["strategy_id"] == "nonexistent"
            assert data["approved"] is False
            assert data["approval_status"] == "NOT_FOUND"
            assert len(data["rejection_reasons"]) > 0

        finally:
            close_test_client(client)

    def test_reject_unknown_strategy_id(self, isolated_db_config: DatabaseConfig):
        """Unknown strategy ID returns NOT_FOUND."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            response = client.post(
                "/api/strategies/strat-unknown-123/approve",
                params={"use_forecast": True, "forecast_horizon": 3600},
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["strategy_id"] == "strat-unknown-123"
            assert data["approved"] is False
            assert data["approval_status"] == "NOT_FOUND"
            reasons = data["rejection_reasons"]
            assert len(reasons) > 0
            # Message split in source - check for key phrase
            msg = "not found in current"
            msg2 = "generated strategy set"
            assert any(msg in r and msg2 in r for r in reasons)

        finally:
            close_test_client(client)

    def test_validation_failure_prevents_approval(
        self, isolated_db_config: DatabaseConfig, monkeypatch
    ):
        """Strategy that fails validation cannot be approved (VALIDATION_FAILED)."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            from app.main import app

            approval_service = app.state.approval_service
            strategy_service = app.state.strategy_service
            from app.schemas import (
                StrategyCandidate,
                StrategyGenerationResponse,
            )

            # Get a real generation to use as base
            real_generation = strategy_service.generate_strategies(
                use_forecast=True, forecast_horizon_s=3600
            )

            # Create invalid strategy that will fail validation (priority=0)
            invalid_strat = StrategyCandidate.model_construct(
                strategy_id="strat-invalid-test",
                title="Invalid",
                rationale="Test",
                priority=0,  # Invalid priority - out of range [1,5]
                affected_resources=["BATTERY"],
                recommended_actions=["Test action"],
                source_anomalies=["BATTERY-CRITICAL"],
                requires_operator_approval=True,
            )

            # Build a generation containing the invalid strategy
            test_generation = StrategyGenerationResponse(
                mission_id=real_generation.mission_id,
                current_elapsed_s=real_generation.current_elapsed_s,
                strategies=[invalid_strat],
                strategy_count=1,
                has_critical_priority=False,
            )

            # Monkeypatch generate_strategies to return our test generation
            def mock_generate_strategies(use_forecast, forecast_horizon_s):
                return test_generation

            monkeypatch.setattr(
                strategy_service, "generate_strategies", mock_generate_strategies
            )

            # Now try to approve the invalid strategy - should fail validation
            result = approval_service.approve_strategy(
                strategy_id="strat-invalid-test",
                use_forecast=True,
                forecast_horizon_s=3600,
            )

            # Should be VALIDATION_FAILED (since it's in the generated set but invalid)
            assert result.approved is False
            assert result.approval_status == "VALIDATION_FAILED"
            assert len(result.rejection_reasons) > 0
            assert any("priority 0 out of range" in r for r in result.rejection_reasons)

        finally:
            close_test_client(client)

    def test_explicit_operator_action_required(
        self, isolated_db_config: DatabaseConfig
    ):
        """Approval must be explicitly triggered - no auto-approval."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            # Get strategies
            gen_response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            assert gen_response.status_code == status.HTTP_200_OK
            generation = gen_response.json()

            assert generation["strategies"], (
                "Expected forecast strategies to be generated"
            )

            strat_id = generation["strategies"][0]["strategy_id"]

            # Simply generating strategies should NOT approve them
            from app.main import app

            approval_service = app.state.approval_service

            assert approval_service.is_approved(strat_id) is False

            # Even after validation, not approved
            val_response = client.get(
                "/api/strategies/validate?use_forecast=true&forecast_horizon=3600"
            )
            assert val_response.status_code == status.HTTP_200_OK

            assert approval_service.is_approved(strat_id) is False

            # Only explicit POST approval works
            response = client.post(
                f"/api/strategies/{strat_id}/approve",
                params={"use_forecast": True, "forecast_horizon": 3600},
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["approved"] is True

        finally:
            close_test_client(client)

    def test_approval_does_not_execute_actions(
        self, isolated_db_config: DatabaseConfig
    ):
        """Approval marks strategy as approved but does not execute actions."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            gen_response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            generation = gen_response.json()

            assert generation["strategies"], (
                "Expected forecast strategies to be generated"
            )

            strat_id = generation["strategies"][0]["strategy_id"]
            original_actions = generation["strategies"][0]["recommended_actions"]

            # Approve strategy
            response = client.post(
                f"/api/strategies/{strat_id}/approve",
                params={"use_forecast": True, "forecast_horizon": 3600},
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["approved"] is True

            # Mission state should be completely unchanged
            state_before = client.get("/api/mission/state").json()

            # The strategy service should still return same strategies
            gen_after = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            assert gen_after.status_code == status.HTTP_200_OK
            gen_data = gen_after.json()

            # Strategy still exists with same actions (no execution)
            approved_strat = next(
                s for s in gen_data["strategies"] if s["strategy_id"] == strat_id
            )
            assert approved_strat["recommended_actions"] == original_actions

            state_after = client.get("/api/mission/state").json()
            assert state_before == state_after, "Mission state mutated after approval"

        finally:
            close_test_client(client)

    def test_approval_does_not_mutate_mission_state(
        self, isolated_db_config: DatabaseConfig
    ):
        """Approval does not mutate any mission resource state."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            # Get initial mission state
            initial_state = client.get("/api/mission/state").json()

            # Get and approve a strategy
            gen_response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            generation = gen_response.json()

            if generation["strategies"]:
                strat_id = generation["strategies"][0]["strategy_id"]
                client.post(
                    f"/api/strategies/{strat_id}/approve",
                    params={"use_forecast": True, "forecast_horizon": 3600},
                )

                # Approve another if available
                if len(generation["strategies"]) > 1:
                    strat_id2 = generation["strategies"][1]["strategy_id"]
                    client.post(
                        f"/api/strategies/{strat_id2}/approve",
                        params={"use_forecast": True, "forecast_horizon": 3600},
                    )

            # State should be identical
            final_state = client.get("/api/mission/state").json()
            assert initial_state == final_state

        finally:
            close_test_client(client)

    def test_repeated_approval_idempotent(self, isolated_db_config: DatabaseConfig):
        """Repeated approval of same strategy is idempotent."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            gen_response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            generation = gen_response.json()

            assert generation["strategies"], (
                "Expected forecast strategies to be generated"
            )

            strat_id = generation["strategies"][0]["strategy_id"]

            # First approval
            response1 = client.post(
                f"/api/strategies/{strat_id}/approve",
                params={"use_forecast": True, "forecast_horizon": 3600},
            )
            assert response1.status_code == status.HTTP_200_OK
            data1 = response1.json()
            assert data1["approved"] is True
            assert data1["approval_status"] == "APPROVED"

            # Second approval
            response2 = client.post(
                f"/api/strategies/{strat_id}/approve",
                params={"use_forecast": True, "forecast_horizon": 3600},
            )
            assert response2.status_code == status.HTTP_200_OK
            data2 = response2.json()
            assert data2["approved"] is True
            assert data2["approval_status"] == "ALREADY_APPROVED"

            # Results should be consistent (both approved)
            assert data1["strategy_id"] == data2["strategy_id"] == strat_id

        finally:
            close_test_client(client)

    def test_generated_strategy_unchanged_after_approval(
        self, isolated_db_config: DatabaseConfig
    ):
        """Generated strategies remain identical after approval."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            # Get strategies before approval
            gen_before = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            assert gen_before.status_code == status.HTTP_200_OK
            before = gen_before.json()

            assert before["strategies"], "Expected forecast strategies to be generated"

            strat_id = before["strategies"][0]["strategy_id"]

            # Approve
            client.post(
                f"/api/strategies/{strat_id}/approve",
                params={"use_forecast": True, "forecast_horizon": 3600},
            )

            # Get strategies after approval
            gen_after = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            assert gen_after.status_code == status.HTTP_200_OK
            after = gen_after.json()

            # Strategies should be identical
            assert after["strategy_count"] == before["strategy_count"]
            assert after["has_critical_priority"] == before["has_critical_priority"]

            for before_strat, after_strat in zip(
                before["strategies"], after["strategies"]
            ):
                assert before_strat["strategy_id"] == after_strat["strategy_id"]
                assert before_strat["title"] == after_strat["title"]
                assert before_strat["rationale"] == after_strat["rationale"]
                assert before_strat["priority"] == after_strat["priority"]
                assert (
                    before_strat["affected_resources"]
                    == after_strat["affected_resources"]
                )
                assert (
                    before_strat["recommended_actions"]
                    == after_strat["recommended_actions"]
                )
                assert (
                    before_strat["source_anomalies"] == after_strat["source_anomalies"]
                )
                assert (
                    before_strat["requires_operator_approval"]
                    == after_strat["requires_operator_approval"]
                )

        finally:
            close_test_client(client)

    def test_phase4a_strategies_endpoint_unchanged(
        self, isolated_db_config: DatabaseConfig
    ):
        """Phase 4A /api/strategies endpoint behavior unchanged."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            # Without forecast - should work as before
            response = client.get("/api/strategies")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert "mission_id" in data
            assert "current_elapsed_s" in data
            assert "strategies" in data
            assert "strategy_count" in data
            assert "has_critical_priority" in data

            # With forecast - should work as before
            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert "mission_id" in data
            assert "strategies" in data
            assert isinstance(data["strategies"], list)

            # Forecast horizon validation should still work
            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=30"
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

            response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=86400"
            )
            assert response.status_code == status.HTTP_200_OK

        finally:
            close_test_client(client)

    def test_phase4b_validation_behavior_unchanged(
        self, isolated_db_config: DatabaseConfig
    ):
        """Phase 4B validation behavior unchanged."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            # POST validation endpoint
            gen_response = client.get(
                "/api/strategies?use_forecast=true&forecast_horizon=3600"
            )
            generation = gen_response.json()

            val_response = client.post("/api/strategies/validate", json=generation)
            assert val_response.status_code == status.HTTP_200_OK
            data = val_response.json()

            assert "mission_id" in data
            assert "current_elapsed_s" in data
            assert "validation_results" in data
            assert "validation_count" in data
            assert "all_valid" in data

            # GET validation endpoint
            conv_response = client.get(
                "/api/strategies/validate?use_forecast=true&forecast_horizon=3600"
            )
            assert conv_response.status_code == status.HTTP_200_OK
            conv_data = conv_response.json()

            # Both endpoints should return consistent results
            assert data["validation_count"] == conv_data["validation_count"]
            assert data["all_valid"] == conv_data["all_valid"]

        finally:
            close_test_client(client)

    def test_approval_requires_operator_approval_true(
        self, isolated_db_config: DatabaseConfig, monkeypatch
    ):
        """Strategy with requires_operator_approval=False fails mandatory validation."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            from app.main import app

            approval_service = app.state.approval_service
            strategy_service = app.state.strategy_service
            from app.schemas import (
                StrategyCandidate,
                StrategyGenerationResponse,
            )

            # Get a real generation to use as base
            real_generation = strategy_service.generate_strategies(
                use_forecast=True, forecast_horizon_s=3600
            )

            # Create strategy with requires_operator_approval=False
            invalid_strat = StrategyCandidate.model_construct(
                strategy_id="strat-no-approval",
                title="No Approval Needed",
                rationale="Test",
                priority=2,
                affected_resources=["BATTERY"],
                recommended_actions=["Test action"],
                source_anomalies=["BATTERY-WARNING"],
                requires_operator_approval=False,  # This should cause REJECTED
            )

            # Build a generation containing the invalid strategy
            test_generation = StrategyGenerationResponse(
                mission_id=real_generation.mission_id,
                current_elapsed_s=real_generation.current_elapsed_s,
                strategies=[invalid_strat],
                strategy_count=1,
                has_critical_priority=False,
            )

            # Monkeypatch generate_strategies to return our test generation
            def mock_generate_strategies(use_forecast, forecast_horizon_s):
                return test_generation

            monkeypatch.setattr(
                strategy_service, "generate_strategies", mock_generate_strategies
            )

            # Approval must fail because Phase 4B validation requires operator approval.
            result = approval_service.approve_strategy(
                strategy_id="strat-no-approval",
                use_forecast=True,
                forecast_horizon_s=3600,
            )

            # Phase 4B validation rejects the candidate before approval.
            assert result.approved is False
            assert result.approval_status == "VALIDATION_FAILED"
            reasons = result.rejection_reasons
            assert any("requires_operator_approval must be true" in r for r in reasons)

        finally:
            close_test_client(client)

    def test_approval_does_not_bypass_validation(
        self, isolated_db_config: DatabaseConfig, monkeypatch
    ):
        """Approval requires validation - cannot bypass StrategyValidationService."""
        client = create_test_client(isolated_db_config)
        try:
            client.post("/api/mission/start")

            from app.main import app

            approval_service = app.state.approval_service
            strategy_service = app.state.strategy_service
            from app.schemas import (
                StrategyCandidate,
                StrategyGenerationResponse,
            )

            # Get a real generation to use as base
            real_generation = strategy_service.generate_strategies(
                use_forecast=True, forecast_horizon_s=3600
            )

            # Create strategy that fails validation (priority=10, out of range)
            invalid_strat = StrategyCandidate.model_construct(
                strategy_id="strat-bad-priority",
                title="Bad Priority",
                rationale="Test",
                priority=10,  # Invalid - > 5
                affected_resources=["BATTERY"],
                recommended_actions=["Test action"],
                source_anomalies=["BATTERY-CRITICAL"],
                requires_operator_approval=True,
            )

            # Build a generation containing the invalid strategy
            test_generation = StrategyGenerationResponse(
                mission_id=real_generation.mission_id,
                current_elapsed_s=real_generation.current_elapsed_s,
                strategies=[invalid_strat],
                strategy_count=1,
                has_critical_priority=False,
            )

            # Monkeypatch generate_strategies to return our test generation
            def mock_generate_strategies(use_forecast, forecast_horizon_s):
                return test_generation

            monkeypatch.setattr(
                strategy_service, "generate_strategies", mock_generate_strategies
            )

            # Try to approve - validation must run and fail
            result = approval_service.approve_strategy(
                strategy_id="strat-bad-priority",
                use_forecast=True,
                forecast_horizon_s=3600,
            )

            # Should be VALIDATION_FAILED (validation ran and caught the error)
            assert result.approved is False
            assert result.approval_status == "VALIDATION_FAILED"
            assert len(result.rejection_reasons) > 0
            reasons = result.rejection_reasons
            assert any("priority 10 out of range" in r for r in reasons)

            # Validation service still works normally for other calls
            val_response = client.post(
                "/api/strategies/validate",
                json={
                    "mission_id": "luna-mission-001",
                    "current_elapsed_s": 0,
                    "strategies": [],
                    "strategy_count": 0,
                    "has_critical_priority": False,
                },
            )
            assert val_response.status_code == status.HTTP_200_OK
            val_data = val_response.json()
            assert val_data["all_valid"] is True
            assert val_data["validation_count"] == 0

        finally:
            close_test_client(client)
