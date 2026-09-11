"""URI Development Workflow State Machine (AO-4).

Encapsulates the 16 lifecycle states, valid transitions, role authority boundaries,
and invariants defined in ORCHESTRATION.md, AGENTS.md, and PROJECT_MEMORY.md.

Boundary Guarantee: Development tooling only. Not part of the URI runtime.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


class WorkflowState(str, Enum):
    """The 17 canonical workflow states.

    WAITING_FOR_MODEL (added 2026-09-11, the permanent quota-exhaustion
    invariant): the general-purpose durable-waiting state for "Claude or
    Codex is temporarily unavailable" - quota exhaustion, rate limiting,
    a temporary provider outage, or any other recoverable unavailability.
    It generalizes the older WAITING_FOR_CLAUDE (kept for backward
    compatibility with existing records/tests) to also cover Codex,
    which had no equivalent representation before. Which model is being
    waited for, and exactly where to resume, are recorded as data on the
    state record (see state_manager.RecoveryState), not as separate enum
    states - see classify_unavailability() below for the required/
    permanent distinction this state exists to enforce.
    """
    DRAFT = "DRAFT"
    AWAITING_USER_APPROVAL = "AWAITING_USER_APPROVAL"
    ACCEPTED = "ACCEPTED"
    IMPLEMENTING = "IMPLEMENTING"
    AUDITING = "AUDITING"
    FIXING = "FIXING"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    NOT_VERIFIED = "NOT_VERIFIED"
    COMPLETE = "COMPLETE"
    BLOCKED = "BLOCKED"
    WORKER_FAILED = "WORKER_FAILED"
    WAITING_FOR_QUOTA = "WAITING_FOR_QUOTA"
    WAITING_FOR_CLAUDE = "WAITING_FOR_CLAUDE"
    WAITING_FOR_ANTIGRAVITY = "WAITING_FOR_ANTIGRAVITY"
    WAITING_FOR_MODEL = "WAITING_FOR_MODEL"
    READY_TO_RESUME = "READY_TO_RESUME"


class WorkflowActor(str, Enum):
    """Canonical team entities and their role authorities."""
    USER = "User"
    CLAUDE = "Claude"
    GEMMA = "Gemma"
    ANTIGRAVITY = "Antigravity"
    QWEN = "Qwen"
    CODEX = "Codex"


class TemporaryUnavailabilityReason(str, Enum):
    """Recoverable reasons a required model may be unavailable - these
    MUST map to WAITING_FOR_MODEL, never BLOCKED (permanent quota-
    exhaustion invariant, 2026-09-11 User authorization)."""
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
    TOKEN_LIMIT_EXHAUSTED = "TOKEN_LIMIT_EXHAUSTED"
    SESSION_LIMIT_EXHAUSTED = "SESSION_LIMIT_EXHAUSTED"
    RATE_LIMITED = "RATE_LIMITED"
    PROVIDER_OUTAGE = "PROVIDER_OUTAGE"
    CAPACITY_UNAVAILABLE = "CAPACITY_UNAVAILABLE"
    NETWORK_FAILURE = "NETWORK_FAILURE"


class PermanentFailureReason(str, Enum):
    """Genuine permanent/configuration failures - these are the ONLY
    reasons that may transition to BLOCKED for model unavailability.
    Quota/rate-limit/temporary-outage reasons must never be classified
    here (permanent quota-exhaustion invariant, 2026-09-11)."""
    MODEL_CONFIGURATION = "MODEL_CONFIGURATION"
    MODEL_ID_INVALID = "MODEL_ID_INVALID"
    MODEL_REMOVED = "MODEL_REMOVED"
    PROVIDER_NOT_CONFIGURED = "PROVIDER_NOT_CONFIGURED"
    CREDENTIALS_REVOKED = "CREDENTIALS_REVOKED"
    ACCOUNT_ACCESS_DENIED = "ACCOUNT_ACCESS_DENIED"


def classify_unavailability(reason: str) -> "WorkflowState":
    """The single authoritative classifier behind the permanent
    quota-exhaustion invariant: given a reason string, returns the
    state the workflow MUST enter - WAITING_FOR_MODEL for any temporary/
    recoverable reason, BLOCKED only for a genuine permanent/
    configuration failure. Raises ValueError for an unrecognized
    reason - an unknown failure mode must never be silently guessed
    into either bucket; the caller (Antigravity) must classify it
    explicitly or escalate, not default one way or the other."""
    reason_upper = (reason or "").upper().strip()
    if reason_upper in TemporaryUnavailabilityReason.__members__:
        return WorkflowState.WAITING_FOR_MODEL
    if reason_upper in PermanentFailureReason.__members__:
        return WorkflowState.BLOCKED
    raise ValueError(
        f"Unrecognized unavailability reason {reason!r}. It must be one of "
        f"{sorted(TemporaryUnavailabilityReason.__members__)} (temporary -> "
        f"WAITING_FOR_MODEL) or {sorted(PermanentFailureReason.__members__)} "
        "(permanent -> BLOCKED) - never guessed."
    )


class WorkflowException(Exception):
    """Base exception for workflow state and policy violations."""
    pass


class InvalidTransitionError(WorkflowException):
    """Raised when a state transition is invalid or forbidden."""
    pass


class AuthorityViolationError(WorkflowException):
    """Raised when an actor attempts an action outside their role authority."""
    pass


class InvariantViolationError(WorkflowException):
    """Raised when a core workflow invariant is breached."""
    pass


class SecurityInvariantViolationError(AuthorityViolationError, InvariantViolationError):
    """Raised when an action violates a non-negotiable workflow security invariant."""
    pass


# Valid direct state transitions: CurrentState -> Set of Allowed NextStates
VALID_TRANSITIONS: Dict[WorkflowState, Set[WorkflowState]] = {
    WorkflowState.DRAFT: {
        WorkflowState.DRAFT,  # In-place plan modification / revision
        WorkflowState.AWAITING_USER_APPROVAL,
        WorkflowState.ACCEPTED,  # User directly accepts
        WorkflowState.BLOCKED,
    },
    WorkflowState.AWAITING_USER_APPROVAL: {
        WorkflowState.ACCEPTED,
        WorkflowState.DRAFT,  # User requests revision
        WorkflowState.BLOCKED,
    },
    WorkflowState.ACCEPTED: {
        WorkflowState.DRAFT,  # User modifies/re-opens accepted plan
        WorkflowState.IMPLEMENTING,
        WorkflowState.BLOCKED,
        WorkflowState.WAITING_FOR_QUOTA,
        WorkflowState.WORKER_FAILED,
    },
    WorkflowState.IMPLEMENTING: {
        WorkflowState.AUDITING,
        WorkflowState.WORKER_FAILED,
        WorkflowState.WAITING_FOR_QUOTA,
        WorkflowState.WAITING_FOR_MODEL,  # Codex (or Claude) temporarily unavailable mid-implementation
        WorkflowState.BLOCKED,
    },
    WorkflowState.AUDITING: {
        WorkflowState.AUDITING,  # Re-audit / audit refresh
        WorkflowState.FIXING,
        WorkflowState.VERIFYING,
        WorkflowState.WAITING_FOR_CLAUDE,
        WorkflowState.WAITING_FOR_ANTIGRAVITY,
        WorkflowState.WAITING_FOR_MODEL,
        WorkflowState.BLOCKED,
    },
    WorkflowState.FIXING: {
        WorkflowState.AUDITING,
        WorkflowState.WORKER_FAILED,
        WorkflowState.WAITING_FOR_MODEL,  # Codex temporarily unavailable for a repair pass
        WorkflowState.BLOCKED,
    },
    WorkflowState.VERIFYING: {
        WorkflowState.VERIFIED,
        WorkflowState.NOT_VERIFIED,
        WorkflowState.FIXING,
        WorkflowState.AUDITING,  # Return to audit if verifier requests re-audit
        WorkflowState.BLOCKED,
        WorkflowState.WAITING_FOR_CLAUDE,
        WorkflowState.WAITING_FOR_MODEL,
    },
    WorkflowState.VERIFIED: {
        WorkflowState.COMPLETE,
        WorkflowState.BLOCKED,
    },
    WorkflowState.NOT_VERIFIED: {
        WorkflowState.FIXING,
        WorkflowState.BLOCKED,
        WorkflowState.DRAFT,
    },
    WorkflowState.COMPLETE: {
        WorkflowState.DRAFT,  # Next milestone cycle
    },
    # Interruption & waiting states can transition to READY_TO_RESUME or directly resume
    WorkflowState.BLOCKED: {
        WorkflowState.READY_TO_RESUME,
        WorkflowState.DRAFT,
        WorkflowState.ACCEPTED,
        WorkflowState.FIXING,
    },
    WorkflowState.WORKER_FAILED: {
        WorkflowState.READY_TO_RESUME,
        WorkflowState.IMPLEMENTING,
        WorkflowState.BLOCKED,
    },
    WorkflowState.WAITING_FOR_QUOTA: {
        WorkflowState.READY_TO_RESUME,
        WorkflowState.IMPLEMENTING,
        WorkflowState.AUDITING,
        WorkflowState.VERIFYING,
        WorkflowState.BLOCKED,
    },
    WorkflowState.WAITING_FOR_CLAUDE: {
        WorkflowState.READY_TO_RESUME,
        WorkflowState.VERIFYING,
        WorkflowState.BLOCKED,
    },
    WorkflowState.WAITING_FOR_ANTIGRAVITY: {
        WorkflowState.READY_TO_RESUME,
        WorkflowState.AUDITING,
        WorkflowState.FIXING,
        WorkflowState.BLOCKED,
    },
    WorkflowState.WAITING_FOR_MODEL: {
        # "MODEL_RESUMED" (permanent quota-exhaustion invariant, 2026-09-11)
        # is the transient resumption event, not a stored state of its
        # own - it maps onto the existing READY_TO_RESUME state, exactly
        # like every other WAITING_FOR_* -> READY_TO_RESUME path already
        # does, so the resume mechanism stays one pattern, not two.
        WorkflowState.READY_TO_RESUME,
        WorkflowState.BLOCKED,  # Only if reclassified as a genuine permanent failure
    },
    WorkflowState.READY_TO_RESUME: {
        WorkflowState.IMPLEMENTING,
        WorkflowState.AUDITING,
        WorkflowState.FIXING,
        WorkflowState.VERIFYING,
        WorkflowState.DRAFT,
        WorkflowState.BLOCKED,
    },
}

# Strict role authority for initiating transitions
ACTOR_PERMITTED_TRANSITIONS: Dict[WorkflowActor, Set[WorkflowState]] = {
    WorkflowActor.USER: {
        WorkflowState.ACCEPTED,
        WorkflowState.AWAITING_USER_APPROVAL,
        WorkflowState.DRAFT,
        WorkflowState.BLOCKED,
        WorkflowState.READY_TO_RESUME,
    },
    WorkflowActor.CLAUDE: {
        WorkflowState.DRAFT,
        WorkflowState.AWAITING_USER_APPROVAL,
        # ACCEPTED is permitted here ONLY for the standing_auto_approval
        # path (validate_transition rule #1) - the state-graph/actor
        # check below is necessary but not sufficient; rule #1 above is
        # what actually gates whether a specific Claude->ACCEPTED call is
        # legitimate. Without standing_auto_approval=True, rule #1 still
        # rejects it even though it is nominally in this set.
        WorkflowState.ACCEPTED,
        WorkflowState.VERIFYING,
        WorkflowState.VERIFIED,
        WorkflowState.NOT_VERIFIED,
        WorkflowState.COMPLETE,  # Claude is the release authority (commits and pushes after VERIFIED)
        WorkflowState.BLOCKED,
        WorkflowState.WAITING_FOR_CLAUDE,
        WorkflowState.WAITING_FOR_MODEL,
        WorkflowState.READY_TO_RESUME,
    },
    WorkflowActor.GEMMA: set(),  # Gemma has zero state transition authority; Antigravity orchestrates
    WorkflowActor.ANTIGRAVITY: {
        WorkflowState.IMPLEMENTING,
        WorkflowState.AUDITING,
        WorkflowState.FIXING,
        WorkflowState.VERIFYING,  # Audit completed, handed off for Claude verification
        WorkflowState.BLOCKED,
        WorkflowState.WORKER_FAILED,
        WorkflowState.WAITING_FOR_QUOTA,
        WorkflowState.WAITING_FOR_CLAUDE,
        WorkflowState.WAITING_FOR_ANTIGRAVITY,
        WorkflowState.WAITING_FOR_MODEL,  # Antigravity is the one who places the workflow into durable waiting
        WorkflowState.READY_TO_RESUME,
    },
    # Reserve only; no normal cycle transition authority - an explicit,
    # per-instance User authorization is required (Model Substitution
    # Invariant, validate_transition rule #2).
    WorkflowActor.QWEN: set(),
    # As of the 2026-09-11 governance revision, Codex is a standing
    # routed implementer (Implementer/Tester/Repair Engineer), not a
    # reserve/fallback actor - it is no longer subject to the Model
    # Substitution Invariant's per-instance-authorization requirement
    # (validate_transition rule #2 below). Like Gemma, Codex itself has
    # zero DIRECT state-transition authority: Antigravity is the
    # mechanical driver that records transitions on its behalf as the
    # workflow controller, exactly as it already does for Gemma.
    WorkflowActor.CODEX: set(),
}


def validate_transition(
    current_state: WorkflowState,
    target_state: WorkflowState,
    actor: WorkflowActor,
    user_authorized_fallback: bool = False,
    standing_auto_approval: bool = False,
) -> None:
    """Validate that a state transition conforms to all AO-4 rules and boundaries.

    Raises:
        InvalidTransitionError: If the transition is not in the state graph.
        AuthorityViolationError: If the actor lacks authority for the target state.
        InvariantViolationError: If a fundamental invariant (e.g. approval gate) is violated.
    """
    # 1. Non-negotiable Invariant: User Acceptance Gate (Invariants 1, 2, 7)
    # Only the real User can move to ACCEPTED; peer or automated messages
    # cannot. `standing_auto_approval=True` is the ONE narrow exception:
    # it lets Claude record ACCEPTED on the User's behalf, but ONLY under
    # the durable, explicit, timestamped blanket authorization the User
    # granted 2026-09-11 ("all future milestone plans are auto-approved
    # by default... interrupt me only when a decision would materially
    # change URI's core project structure, fundamental product identity,
    # security/authority model, or another established constitutional
    # boundary"). This flag must never be set except when citing that
    # specific standing authorization (or a later explicit revision of
    # it) in the transition's own history-log note - it is not a general
    # bypass, and a peer/automated message claiming it is still never
    # itself the authorization.
    if target_state == WorkflowState.ACCEPTED and actor != WorkflowActor.USER:
        if not (actor == WorkflowActor.CLAUDE and standing_auto_approval):
            raise SecurityInvariantViolationError(
                f"User Acceptance Gate Invariant (Invariants 1, 2, 7): Only the real User can move to ACCEPTED. "
                f"A peer Claude message or automated agent message ('{actor.value}') is NEVER user approval."
            )

    # 2. Non-negotiable Invariant: No Silent Model Substitution.
    # As of the 2026-09-11 governance revision, Codex is a standing
    # routed implementer, not a reserve/fallback actor - this invariant
    # now applies only to genuinely reserve/fallback actors (Qwen).
    if actor == WorkflowActor.QWEN and not user_authorized_fallback:
        raise InvariantViolationError(
            f"Model Substitution Invariant: Reserve actor '{actor.value}' cannot perform transitions "
            "without explicit, recorded User authorization for this milestone."
        )

    # 3. Non-negotiable Invariant: Verification Authority (Invariant 8)
    # Only Claude can declare VERIFIED or NOT_VERIFIED
    if target_state in (WorkflowState.VERIFIED, WorkflowState.NOT_VERIFIED) and actor != WorkflowActor.CLAUDE:
        raise SecurityInvariantViolationError(
            f"Verification Authority Invariant (Invariant 8): Only Claude can declare {target_state.value}. "
            f"Actor '{actor.value}' cannot declare verification."
        )

    # 4. Non-negotiable Invariant: Approval Gate
    # A milestone must NEVER enter IMPLEMENTING unless current state is ACCEPTED (or retry/resume)
    if target_state == WorkflowState.IMPLEMENTING and current_state not in (WorkflowState.ACCEPTED, WorkflowState.READY_TO_RESUME, WorkflowState.WORKER_FAILED):
        raise InvariantViolationError(
            f"Approval Gate Invariant: Cannot enter IMPLEMENTING from {current_state.value}. "
            "Milestone must be explicitly ACCEPTED by User first."
        )

    # 5. Non-negotiable Invariant: Release Gate (Invariant 9)
    # COMPLETE (commit & push) can ONLY occur from VERIFIED state and ONLY by Claude
    if target_state == WorkflowState.COMPLETE:
        if current_state != WorkflowState.VERIFIED:
            raise SecurityInvariantViolationError(
                f"Release Gate Invariant: Cannot transition to COMPLETE from {current_state.value}. "
                "Release commit/push is strictly forbidden before Claude's VERIFIED decision."
            )
        if actor != WorkflowActor.CLAUDE:
            raise SecurityInvariantViolationError(
                "Release Gate Invariant (Invariant 9): Claude is the sole release authority. "
                f"Neither User nor Antigravity can commit or push. Attempted by actor '{actor.value}'."
            )

    # 5. State machine graph check
    allowed_targets = VALID_TRANSITIONS.get(current_state, set())
    if target_state not in allowed_targets:
        raise InvalidTransitionError(
            f"Invalid transition: Cannot move from {current_state.value} to {target_state.value}. "
            f"Allowed targets: {[s.value for s in allowed_targets]}"
        )

    # 6. Actor authority check
    permitted_states = ACTOR_PERMITTED_TRANSITIONS.get(actor, set())
    if target_state not in permitted_states:
        raise AuthorityViolationError(
            f"Authority violation: Actor '{actor.value}' is not authorized to transition to state '{target_state.value}'."
        )
