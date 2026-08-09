"""Tests for Pydantic domain schemas and the deterministic seed."""

import pytest
from pydantic import ValidationError

from app.schemas import (
    CandidatePlan,
    MissionStatus,
    PlanStatus,
    RouteWaypoint,
    RoverResources,
)
from app.seed import get_seed_mission

# ---------------------------------------------------------------------------
# RoverResources — percentage range validation
# ---------------------------------------------------------------------------


class TestRoverResourcesValidation:
    def test_battery_pct_below_zero_raises(self) -> None:
        with pytest.raises(ValidationError):
            RoverResources(
                battery_pct=-1.0,
                storage_pct=50.0,
                temperature_c=-40.0,
                comm_window_remaining_s=3600,
                op_time_remaining_s=7200,
            )

    def test_battery_pct_above_100_raises(self) -> None:
        with pytest.raises(ValidationError):
            RoverResources(
                battery_pct=100.1,
                storage_pct=50.0,
                temperature_c=-40.0,
                comm_window_remaining_s=3600,
                op_time_remaining_s=7200,
            )

    def test_storage_pct_below_zero_raises(self) -> None:
        with pytest.raises(ValidationError):
            RoverResources(
                battery_pct=80.0,
                storage_pct=-0.1,
                temperature_c=-40.0,
                comm_window_remaining_s=3600,
                op_time_remaining_s=7200,
            )

    def test_storage_pct_above_100_raises(self) -> None:
        with pytest.raises(ValidationError):
            RoverResources(
                battery_pct=80.0,
                storage_pct=101.0,
                temperature_c=-40.0,
                comm_window_remaining_s=3600,
                op_time_remaining_s=7200,
            )

    def test_valid_boundary_values_accepted(self) -> None:
        r = RoverResources(
            battery_pct=0.0,
            storage_pct=100.0,
            temperature_c=20.0,
            comm_window_remaining_s=0,
            op_time_remaining_s=0,
        )
        assert r.battery_pct == 0.0
        assert r.storage_pct == 100.0


# ---------------------------------------------------------------------------
# CandidatePlan — predicted_return_battery_pct range
# ---------------------------------------------------------------------------


class TestCandidatePlanValidation:
    def _base_waypoint(self) -> RouteWaypoint:
        return RouteWaypoint(id="wp-1", x=0.5, y=0.5, label="WP1")

    def test_negative_return_battery_raises(self) -> None:
        with pytest.raises(ValidationError):
            CandidatePlan(
                plan_id="p1",
                label="Test",
                description="Test plan",
                waypoints=[self._base_waypoint()],
                science_yield_score=10.0,
                predicted_return_battery_pct=-1.0,
            )

    def test_return_battery_above_100_raises(self) -> None:
        with pytest.raises(ValidationError):
            CandidatePlan(
                plan_id="p1",
                label="Test",
                description="Test plan",
                waypoints=[self._base_waypoint()],
                science_yield_score=10.0,
                predicted_return_battery_pct=100.1,
            )

    def test_zero_return_battery_accepted(self) -> None:
        plan = CandidatePlan(
            plan_id="p1",
            label="Test",
            description="Test plan",
            waypoints=[self._base_waypoint()],
            science_yield_score=10.0,
            predicted_return_battery_pct=0.0,
        )
        assert plan.predicted_return_battery_pct == 0.0


# ---------------------------------------------------------------------------
# MissionStatus and PlanStatus — enum membership
# ---------------------------------------------------------------------------


class TestEnumMembers:
    def test_mission_status_contains_required_states(self) -> None:
        required = {
            "IDLE",
            "RUNNING",
            "PAUSED",
            "ANOMALY",
            "PLANNING",
            "AWAITING_APPROVAL",
            "EXECUTING",
            "COMPLETED",
            "RESET",
        }
        actual = {s.value for s in MissionStatus}
        assert required == actual

    def test_mission_status_has_no_approved_state(self) -> None:
        # APPROVED belongs to PlanStatus only, not MissionStatus
        assert "APPROVED" not in {s.value for s in MissionStatus}

    def test_plan_status_contains_required_states(self) -> None:
        required = {"VALID", "REJECTED", "APPROVED"}
        actual = {s.value for s in PlanStatus}
        assert required == actual


# ---------------------------------------------------------------------------
# Seed — structural integrity
# ---------------------------------------------------------------------------


class TestSeedMission:
    def test_seed_returns_mission(self) -> None:
        from app.schemas import Mission

        mission = get_seed_mission()
        assert isinstance(mission, Mission)

    def test_seed_status_is_idle(self) -> None:
        mission = get_seed_mission()
        assert mission.status == MissionStatus.IDLE

    def test_seed_elapsed_is_zero(self) -> None:
        mission = get_seed_mission()
        assert mission.elapsed_s == 0

    def test_seed_has_mission_id(self) -> None:
        mission = get_seed_mission()
        assert mission.mission_id != ""

    def test_seed_resources_are_valid(self) -> None:
        mission = get_seed_mission()
        r = mission.resources
        assert 0.0 <= r.battery_pct <= 100.0
        assert 0.0 <= r.storage_pct <= 100.0

    def test_seed_original_route_has_waypoints(self) -> None:
        mission = get_seed_mission()
        assert len(mission.original_route.waypoints) > 0

    def test_seed_active_route_matches_original(self) -> None:
        mission = get_seed_mission()
        orig_ids = [w.id for w in mission.original_route.waypoints]
        active_ids = [w.id for w in mission.active_route.waypoints]
        assert orig_ids == active_ids

    def test_seed_no_candidate_plans(self) -> None:
        mission = get_seed_mission()
        assert mission.candidate_plans == []

    def test_seed_anomaly_inactive(self) -> None:
        mission = get_seed_mission()
        assert mission.anomaly_active is False

    def test_seed_has_initial_audit_event(self) -> None:
        mission = get_seed_mission()
        assert len(mission.audit_trail) >= 1

    def test_seed_is_deterministic(self) -> None:
        m1 = get_seed_mission()
        m2 = get_seed_mission()
        assert m1.mission_id == m2.mission_id
        assert m1.resources.battery_pct == m2.resources.battery_pct
        assert m1.status == m2.status
        orig_ids_1 = [w.id for w in m1.original_route.waypoints]
        orig_ids_2 = [w.id for w in m2.original_route.waypoints]
        assert orig_ids_1 == orig_ids_2
