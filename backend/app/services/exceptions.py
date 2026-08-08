"""Domain exceptions for LunaYield backend."""

from __future__ import annotations


class MissionStateError(Exception):
    """Raised when a mission state transition is invalid."""

    def __init__(self, current_status: str, attempted_action: str) -> None:
        self.current_status = current_status
        self.attempted_action = attempted_action
        super().__init__(f"Cannot {attempted_action} from {current_status} status")


class PlanNotFoundError(Exception):
    """Raised when a candidate plan is not found."""

    def __init__(self, plan_id: str) -> None:
        self.plan_id = plan_id
        super().__init__(f"Candidate plan {plan_id!r} not found")


class PlanUnsafeError(Exception):
    """Raised when a plan fails safety verification."""

    def __init__(self, plan_id: str, violations: list[str]) -> None:
        self.plan_id = plan_id
        self.violations = violations
        super().__init__(f"Plan {plan_id!r} is unsafe: {', '.join(violations)}")


class PlanningNotAllowedError(Exception):
    """Raised when plan generation is requested in an invalid state."""

    def __init__(self, current_status: str) -> None:
        self.current_status = current_status
        super().__init__(f"Cannot generate plans from {current_status} status")
