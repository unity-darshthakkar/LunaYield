"""Tests for audit trail events."""

from app.services.mission import MissionService
from app.services.planning import PlanningService
from app.services.safety import SafetyVerifier


class TestAuditTrail:
    """Test audit events are created correctly."""

    def setup_full_mission(self, clean_mission: MissionService) -> MissionService:
        """Set up mission through full lifecycle."""
        planning = PlanningService()
        clean_mission.set_dependencies(SafetyVerifier(), planning)
        clean_mission.start()
        clean_mission.pause()
        clean_mission.resume()
        clean_mission.inject_anomaly()
        clean_mission.generate_plans()
        # Approve a plan
        extended_plan = next(
            p
            for p in clean_mission.get_mission().candidate_plans
            if p.label == "Extended Survey"
        )
        clean_mission.approve_plan(extended_plan.plan_id)
        return clean_mission

    def test_audit_events_recorded_for_all_transitions(
        self, clean_mission: MissionService
    ) -> None:
        """Each meaningful transition should create an audit event."""
        mission = self.setup_full_mission(clean_mission)

        audit_types = [e.event_type for e in mission.get_mission().audit_trail]

        # Required events
        assert "mission.initialized" in audit_types  # seed
        assert "mission.started" in audit_types
        assert "mission.paused" in audit_types
        assert "mission.resumed" in audit_types
        assert "anomaly.injected" in audit_types
        assert "battery.degraded" in audit_types
        assert "planning.started" in audit_types
        assert "plans.generated" in audit_types
        assert "plan.approved" in audit_types

    def test_no_duplicate_audit_events(self, clean_mission: MissionService) -> None:
        """Audit events should not be duplicated."""
        mission = self.setup_full_mission(clean_mission)

        audit_types = [e.event_type for e in mission.get_mission().audit_trail]

        # Each transition event should appear exactly once (except mission.initialized)
        for event_type in [
            "mission.started",
            "mission.paused",
            "mission.resumed",
            "anomaly.injected",
            "battery.degraded",
            "planning.started",
            "plans.generated",
            "plan.approved",
        ]:
            count = audit_types.count(event_type)
            assert count == 1, f"{event_type} appears {count} times, expected 1"

    def test_reset_creates_single_reset_audit(
        self, clean_mission: MissionService
    ) -> None:
        """Reset should create exactly one mission.reset audit event."""
        clean_mission.start()
        clean_mission.inject_anomaly()

        # Reset once
        clean_mission.reset()

        audit_types = [e.event_type for e in clean_mission.get_mission().audit_trail]
        reset_count = audit_types.count("mission.reset")
        assert reset_count == 1

    def test_repeated_reset_behavior(self, clean_mission: MissionService) -> None:
        """Repeated resets should each append a reset audit."""
        clean_mission.start()
        clean_mission.inject_anomaly()

        clean_mission.reset()
        mission1 = clean_mission.get_mission()
        reset_events_1 = [
            e for e in mission1.audit_trail if e.event_type == "mission.reset"
        ]
        assert len(reset_events_1) == 1

        clean_mission.start()
        clean_mission.inject_anomaly()
        clean_mission.reset()

        mission2 = clean_mission.get_mission()
        reset_events_2 = [
            e for e in mission2.audit_trail if e.event_type == "mission.reset"
        ]
        assert (
            len(reset_events_2) == 1
        )  # Each reset creates fresh mission with one reset event

    def test_audit_events_have_required_fields(
        self, clean_mission: MissionService
    ) -> None:
        """Each audit event should have all required fields."""
        clean_mission.start()

        event = next(
            e
            for e in clean_mission.get_mission().audit_trail
            if e.event_type == "mission.started"
        )

        assert event.event_id is not None
        assert event.event_type == "mission.started"
        assert event.description is not None
        assert event.timestamp is not None
        assert event.metadata is not None
        assert "mission_id" in event.metadata

    def test_audit_timestamp_ordering(self, clean_mission: MissionService) -> None:
        """Audit events should be in chronological order."""
        mission = self.setup_full_mission(clean_mission)

        timestamps = [e.timestamp for e in mission.get_mission().audit_trail]
        assert timestamps == sorted(timestamps)

    def test_mission_initialized_audit_exists(
        self, clean_mission: MissionService
    ) -> None:
        """Seed mission should have initial audit event."""
        mission = clean_mission.get_mission()

        initialized_events = [
            e for e in mission.audit_trail if e.event_type == "mission.initialized"
        ]
        assert len(initialized_events) == 1
        assert "Mission scenario loaded" in initialized_events[0].description
