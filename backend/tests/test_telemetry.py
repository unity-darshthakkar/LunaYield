"""Tests for deterministic telemetry generation."""

from app.schemas import TelemetrySample
from app.services.mission import MissionService
from app.services.telemetry import TelemetryService


class TestTelemetryService:
    """Test deterministic telemetry behavior."""

    def test_generate_sample_returns_none_when_idle(
        self, clean_mission: MissionService
    ) -> None:
        """Telemetry should return None when mission is IDLE."""
        telemetry = TelemetryService(clean_mission)
        sample = telemetry.generate_sample()
        assert sample is None

    def test_generate_sample_returns_none_when_paused(
        self, clean_mission: MissionService
    ) -> None:
        """Telemetry should return None when mission is PAUSED."""
        clean_mission.start()
        clean_mission.pause()
        telemetry = TelemetryService(clean_mission)
        sample = telemetry.generate_sample()
        assert sample is None

    def test_generate_sample_returns_none_when_anomaly(
        self, clean_mission: MissionService
    ) -> None:
        """Telemetry should return None when mission is ANOMALY."""
        clean_mission.start()
        clean_mission.inject_anomaly()
        telemetry = TelemetryService(clean_mission)
        sample = telemetry.generate_sample()
        assert sample is None

    def test_generate_sample_returns_none_when_awaiting_approval(
        self, clean_mission: MissionService
    ) -> None:
        """Telemetry should return None when mission is AWAITING_APPROVAL."""
        from app.services.planning import PlanningService
        from app.services.safety import SafetyVerifier

        clean_mission.start()
        clean_mission.inject_anomaly()
        clean_mission.set_dependencies(SafetyVerifier(), PlanningService())
        clean_mission.generate_plans()

        telemetry = TelemetryService(clean_mission)
        sample = telemetry.generate_sample()
        assert sample is None

    def test_generate_conforms_to_telemetry_sample(
        self, clean_mission: MissionService
    ) -> None:
        """Generated sample must conform to TelemetrySample schema."""
        clean_mission.start()
        telemetry = TelemetryService(clean_mission)
        sample = telemetry.generate_sample()

        assert sample is not None
        assert isinstance(sample, TelemetrySample)
        assert sample.mission_id == clean_mission.get_mission().mission_id
        assert sample.elapsed_s == 2  # First tick adds 2 seconds
        assert sample.resources.battery_pct <= 100.0
        assert sample.resources.battery_pct >= 0.0
        assert sample.resources.storage_pct >= 0.0
        assert sample.resources.storage_pct <= 100.0
        assert sample.timestamp is not None

    def test_telemetry_is_deterministic(self, clean_mission: MissionService) -> None:
        """Same mission state should produce same telemetry."""
        clean_mission.start()
        telemetry1 = TelemetryService(clean_mission)
        telemetry2 = TelemetryService(clean_mission)

        sample1 = telemetry1.generate_sample()
        sample2 = telemetry2.generate_sample()

        assert sample1 is not None
        assert sample2 is not None
        assert sample1.elapsed_s == sample2.elapsed_s
        assert sample1.resources.battery_pct == sample2.resources.battery_pct
        assert sample1.resources.storage_pct == sample2.resources.storage_pct

    def test_resource_values_remain_valid(self, clean_mission: MissionService) -> None:
        """Resource values should stay within valid ranges."""
        clean_mission.start()
        telemetry = TelemetryService(clean_mission)

        # Generate multiple samples
        for _ in range(10):
            sample = telemetry.generate_sample()
            assert sample is not None
            assert 0.0 <= sample.resources.battery_pct <= 100.0
            assert 0.0 <= sample.resources.storage_pct <= 100.0
            assert sample.resources.comm_window_remaining_s >= 0
            assert sample.resources.op_time_remaining_s >= 0

    def test_emission_only_during_running_and_executing(
        self, clean_mission: MissionService
    ) -> None:
        """Telemetry should only emit during RUNNING and EXECUTING."""
        telemetry = TelemetryService(clean_mission)

        # IDLE
        assert telemetry.generate_sample() is None

        # RUNNING
        clean_mission.start()
        assert telemetry.generate_sample() is not None

        # PAUSED
        clean_mission.pause()
        assert telemetry.generate_sample() is None

        # RESUME -> RUNNING
        clean_mission.resume()
        assert telemetry.generate_sample() is not None

        # ANOMALY
        clean_mission.inject_anomaly()
        assert telemetry.generate_sample() is None

    def test_elapsed_time_increments(self, clean_mission: MissionService) -> None:
        """Elapsed time should increment with each telemetry tick."""
        clean_mission.start()
        telemetry = TelemetryService(clean_mission)

        sample1 = telemetry.generate_sample()
        assert sample1 is not None
        assert sample1.elapsed_s == 2

        sample2 = telemetry.generate_sample()
        assert sample2 is not None
        assert sample2.elapsed_s == 4

    def test_reset_tick_count(self, clean_mission: MissionService) -> None:
        """Reset tick count should reset internal counter."""
        clean_mission.start()
        telemetry = TelemetryService(clean_mission)

        telemetry.generate_sample()
        telemetry.generate_sample()
        telemetry.reset_tick_count()
        # This just tests the method runs without error
        assert telemetry._tick_count == 0
