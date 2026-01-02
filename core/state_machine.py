"""Engagement lifecycle state machine."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EngagementState(str, Enum):
    """Engagement lifecycle states."""

    NEW = "new"  # Just created
    INGESTED = "ingested"  # Data has been ingested
    ANALYZED = "analyzed"  # Analysis complete
    REVIEWED = "reviewed"  # Human review complete
    FINALIZED = "finalized"  # Deliverables ready


class StateTransition(BaseModel):
    """Allowed state transitions."""

    from_state: EngagementState
    to_state: EngagementState
    required_artifacts: list[str] = Field(default_factory=list)


# Define valid transitions
VALID_TRANSITIONS = {
    EngagementState.NEW: [EngagementState.INGESTED],
    EngagementState.INGESTED: [EngagementState.ANALYZED],
    EngagementState.ANALYZED: [EngagementState.REVIEWED],
    EngagementState.REVIEWED: [EngagementState.FINALIZED],
    EngagementState.FINALIZED: [],  # Terminal state
}

# Required artifacts for each transition
TRANSITION_REQUIREMENTS = {
    (EngagementState.NEW, EngagementState.INGESTED): [
        "repo_inventory",
        "db_schema",
    ],
    (EngagementState.INGESTED, EngagementState.ANALYZED): [
        "topology",
        "cost_drivers",
        "risk_register",
    ],
    (EngagementState.ANALYZED, EngagementState.REVIEWED): [
        "review_approval",
    ],
    (EngagementState.REVIEWED, EngagementState.FINALIZED): [
        "executive_summary",
        "technical_appendix",
    ],
}


class StateViolationError(Exception):
    """Raised when attempting invalid state transition."""

    pass


def validate_transition(
    current: EngagementState,
    target: EngagementState,
    available_artifacts: Optional[list[str]] = None,
) -> bool:
    """Validate if transition is allowed.
    
    Args:
        current: Current engagement state
        target: Target state
        available_artifacts: List of available artifact types
        
    Returns:
        True if transition is valid
        
    Raises:
        StateViolationError: If transition is not allowed
    """
    # Check if transition is in allowed list
    if target not in VALID_TRANSITIONS.get(current, []):
        raise StateViolationError(
            f"Invalid transition: {current.value} → {target.value}. "
            f"Valid transitions from {current.value}: "
            f"{[s.value for s in VALID_TRANSITIONS.get(current, [])]}"
        )
    
    # Check artifact requirements
    required = TRANSITION_REQUIREMENTS.get((current, target), [])
    if required and available_artifacts is not None:
        missing = set(required) - set(available_artifacts)
        if missing:
            raise StateViolationError(
                f"Missing required artifacts for {current.value} → {target.value}: "
                f"{', '.join(missing)}"
            )
    
    return True


def get_next_allowed_states(current: EngagementState) -> list[EngagementState]:
    """Get list of states reachable from current state.
    
    Args:
        current: Current engagement state
        
    Returns:
        List of allowed target states
    """
    return VALID_TRANSITIONS.get(current, [])


def get_required_artifacts(
    current: EngagementState, target: EngagementState
) -> list[str]:
    """Get required artifacts for transition.
    
    Args:
        current: Current state
        target: Target state
        
    Returns:
        List of required artifact types
    """
    return TRANSITION_REQUIREMENTS.get((current, target), [])
