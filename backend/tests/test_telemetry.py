"""Tests for deterministic telemetry generation."""

from app.schemas import MissionStatus, TelemetrySample, WaypointProgressStatus
from app.services.mission import MissionService
from app.services.telemetry import TelemetryService


class TestTelemetryService:
    """Test deterministic telemetry behavior."""

    def _advance_ticks(
        self, telemetry: TelemetryService, count: int
    ) -> list[TelemetrySample]:
        samples: list[TelemetrySample] = []
        for _ in range(count):
            sample = telemetry.generate_sample()
            assert sample is not None
            samples.append(sample)
        return samples

    def test_generate_sample_returns_none_when_idle(
        self, clean_mission: MissionService
    ) -> None:
        telemetry = TelemetryService(clean_mission)
        assert telemetry.generate_sample() is None

    def test_generate_sample_returns_none_when_paused(
        self, clean_mission: MissionService
    ) -> None:
        clean_mission.start()
        clean_mission.pause()
        telemetry = TelemetryService(clean_mission)
        assert telemetry.generate_sample() is None

    def test_generate_sample_returns_none_when_anomaly(
        self, clean_mission: MissionService
    ) -> None:
        clean_mission.start()
        clean_mission.inject_anomaly()
        telemetry = TelemetryService(clean_mission)
        assert telemetry.generate_sample() is None

    def test_generate_sample_returns_none_when_awaiting_approval(
        self, clean_mission: MissionService
    ) -> None:
        from app.services.planning import PlanningService
        from app.services.safety import SafetyVerifier

        clean_mission.start()
        clean_mission.inject_anomaly()
        clean_mission.set_dependencies(SafetyVerifier(), PlanningService())
        clean_mission.generate_plans()

        telemetry = TelemetryService(clean_mission)
        assert telemetry.generate_sample() is None

    def test_generate_conforms_to_telemetry_sample(
        self, clean_mission: MissionService
    ) -> None:
        clean_mission.start()
        telemetry = TelemetryService(clean_mission)
        sample = telemetry.generate_sample()

        assert sample is not None
        assert isinstance(sample, TelemetrySample)
        assert sample.mission_id == clean_mission.get_mission().mission_id
        assert sample.elapsed_s == 2
        assert sample.resources.battery_pct == 99.5
        assert sample.resources.storage_pct == 0.0
        assert sample.timestamp is not None

    def test_route_progression_is_deterministic(
        self, clean_mission: MissionService
    ) -> None:
        other_mission = MissionService()
        clean_mission.start()
        other_mission.start()

        telemetry1 = TelemetryService(clean_mission)
        telemetry2 = TelemetryService(other_mission)

        samples1 = self._advance_ticks(telemetry1, 40)
        samples2 = self._advance_ticks(telemetry2, 40)

        mission1 = clean_mission.get_mission()
        mission2 = other_mission.get_mission()

        assert [sample.elapsed_s for sample in samples1] == [
            sample.elapsed_s for sample in samples2
        ]
        assert mission1.resources == mission2.resources
        assert mission1.status == mission2.status
        assert [wp.progress_status for wp in mission1.active_route.waypoints] == [
            wp.progress_status for wp in mission2.active_route.waypoints
        ]

    def test_storage_does_not_grow_during_travel(
        self, clean_mission: MissionService
    ) -> None:
        clean_mission.start()
        telemetry = TelemetryService(clean_mission)

        samples = self._advance_ticks(telemetry, 27)

        assert all(sample.resources.storage_pct == 0.0 for sample in samples)
        assert clean_mission.get_mission().resources.storage_pct == 0.0

    def test_storage_increases_at_science_waypoints_only(
        self, clean_mission: MissionService
    ) -> None:
        clean_mission.start()
        telemetry = TelemetryService(clean_mission)

        first_site_sample = self._advance_ticks(telemetry, 28)[-1]
        assert first_site_sample.resources.storage_pct == 33.0

        second_site_sample = self._advance_ticks(telemetry, 36)[-1]
        assert second_site_sample.resources.storage_pct == 66.0

        third_site_sample = self._advance_ticks(telemetry, 44)[-1]
        assert third_site_sample.resources.storage_pct == 100.0

    def test_base_camp_and_return_do_not_generate_science_storage(
        self, clean_mission: MissionService
    ) -> None:
        clean_mission.start()
        telemetry = TelemetryService(clean_mission)
        self._advance_ticks(telemetry, 148)

        mission = clean_mission.get_mission()
        base_waypoint = mission.active_route.waypoints[0]
        return_waypoint = mission.active_route.waypoints[-1]

        assert base_waypoint.is_science_target is False
        assert return_waypoint.is_science_target is False
        assert mission.resources.storage_pct == 100.0

    def test_nominal_mission_completes_with_final_state_preserved(
        self, clean_mission: MissionService
    ) -> None:
        clean_mission.start()
        telemetry = TelemetryService(clean_mission)
        final_sample = self._advance_ticks(telemetry, 148)[-1]

        mission = clean_mission.get_mission()

        assert mission.status == MissionStatus.COMPLETED
        assert final_sample.elapsed_s == 296
        assert mission.resources.battery_pct == 26.0
        assert mission.resources.storage_pct == 100.0
        assert all(
            waypoint.progress_status == WaypointProgressStatus.COMPLETED
            for waypoint in mission.active_route.waypoints
        )
        assert telemetry.generate_sample() is None

    def test_emission_only_during_running_and_executing(
        self, clean_mission: MissionService
    ) -> None:
        telemetry = TelemetryService(clean_mission)

        assert telemetry.generate_sample() is None

        clean_mission.start()
        assert telemetry.generate_sample() is not None

        clean_mission.pause()
        assert telemetry.generate_sample() is None

        clean_mission.resume()
        assert telemetry.generate_sample() is not None

        clean_mission.inject_anomaly()
        assert telemetry.generate_sample() is None

    def test_critical_battery_transitions_to_anomaly(
        self, clean_mission: MissionService
    ) -> None:
        clean_mission.start()
        mission = clean_mission.get_mission()
        mission.resources.battery_pct = 10.5

        telemetry = TelemetryService(clean_mission)
        sample = telemetry.generate_sample()

        assert sample is not None
        assert clean_mission.get_mission().status == MissionStatus.ANOMALY
        assert clean_mission.get_mission().anomaly_active is True
        assert clean_mission.get_mission().resources.battery_pct == 10.0
        assert any(
            event.event_type == "anomaly.detected"
            for event in clean_mission.get_mission().audit_trail
        )
        assert telemetry.generate_sample() is None

    def test_reset_tick_count(self, clean_mission: MissionService) -> None:
        telemetry = TelemetryService(clean_mission)
        telemetry.reset_tick_count()
        assert telemetry.generate_sample() is None
