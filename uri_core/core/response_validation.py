"""Claim-consistency validation for a drafted response (Milestone 8A).

Do not assume model output is trustworthy just because it is natural
language. This is a narrow, structural check on the specific
dangerous claims a hallucination could make - never full fact-
checking, which is infeasible and out of scope. Its job is to catch
the drafted text disagreeing with the deterministic outcome it was
given, not to verify every sentence is true.

On any failure, the caller (see orchestrator.py's
_draft_narrative_safely) discards the draft and keeps the existing
deterministic template response - the fallback that already existed
before this milestone and is never removed. Fail closed: an
uncertain-but-plausible draft is rejected, not shown.

A non-success narrative must remain an explanation of the known
runtime outcome, never a solution-generation path: for a
not_implemented/unavailable capability gap, URI explains the
limitation and whatever known_gaps evidence the runtime actually has -
it must not invent troubleshooting steps, commands, alternatives, or
imply a capability it does not have. See
MAX_EXPANSION_RATIO/MIN_UNGROUNDED_DRAFT_LENGTH below for the
structural check backing this, and response_drafting.py's
_DRAFTING_INSTRUCTIONS for the primary (prompt-level) defense.
"""

import re
from typing import Any, Dict, Optional

from uri_core.core.security_guards import looks_like_credential_value

MAX_NARRATIVE_LENGTH = 2000

# Evidence-proportional grounding (see module docstring's "explanation,
# not solution-generation" invariant): for any non-"success" outcome,
# the draft may be at most MAX_EXPANSION_RATIO times the length of the
# actual evidence text the runtime gave it (outcome.response's
# message/error plus outcome.known_gaps' description/limitations).
# MIN_UNGROUNDED_DRAFT_LENGTH is a floor so a short, honest "I can't
# do this yet" is always allowed even when the runtime gave almost no
# evidence text at all. This is a heuristic backstop, not a guarantee
# - see _DRAFTING_INSTRUCTIONS in response_drafting.py for the primary
# defense (explicit instruction not to propose troubleshooting,
# commands, or alternatives beyond the given evidence). False
# positives (a grounded draft rejected) are the acceptable failure
# direction here; a false negative (invented advice slipping through
# under the length cap) is not, which is why the ratio is kept tight.
MAX_EXPANSION_RATIO = 3.0
MIN_UNGROUNDED_DRAFT_LENGTH = 300

# A hard ceiling on top of the ratio/floor above, independent of how
# much evidence text the runtime happened to provide. A genuinely
# concise explanation of a known outcome ("I can't do this yet -
# that's a known limitation") never needs more than a couple of short
# sentences; a well-documented capability's real limitations text can
# make evidence_length large enough that MAX_EXPANSION_RATIO alone
# would still permit a multi-section troubleshooting guide through -
# this was observed live (a ~1200-char invented guide passed the
# ratio check because one registry entry's own limitations text was
# long). This cap does not scale with evidence at all, closing that
# gap regardless of how verbose any single capability's documented
# limitations are.
MAX_NON_SUCCESS_NARRATIVE_LENGTH = 400

# Deliberately a modest, imprecise word list, not a parser - false
# positives (a safe draft rejected) are the acceptable failure
# direction here; a false negative (a false success claim shown to the
# user) is not. See module docstring.
_SUCCESS_CLAIM_PATTERN = re.compile(
    r"\b(done|completed|finished|succeeded|sent it|i('| ha)ve sent|"
    r"approved|executed)\b",
    re.IGNORECASE,
)

# For a "not_implemented" gap specifically (see
# CapabilityDescriptor.gap_reason / response_drafting.py's four-state
# distinction) - no execution adapter exists at all, so nothing the
# user provides changes that. A live-observed failure: even with the
# prompt instruction and the length caps above in place, a draft could
# still stay short and evidence-proportional while ending with
# something like "To move forward, I recommend providing more details
# ... This will help in tailoring the optimization steps to your
# needs" - true for an "unavailable_runtime" gap (a missing credential
# really would unblock it) but false for "not_implemented" (there is
# no adapter to unblock). Deliberately a modest, imprecise phrase list,
# not a parser - same false-positive-acceptable, false-negative-not
# posture as _SUCCESS_CLAIM_PATTERN above.
_IMPLIES_FUTURE_CAPABILITY_PATTERNS = (
    re.compile(r"\bthis will help\b", re.IGNORECASE),
    re.compile(r"\bto (proceed|move forward)\b", re.IGNORECASE),
    re.compile(
        r"\bonce you (provide|share|specify|give|authorize|approve)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\btailor(ed|ing)?\b", re.IGNORECASE),
    re.compile(
        r"\b(?:please|kindly)?\s*(?:provide|share|specify|give|"
        r"let me know|tell me)\b[^.]{0,80}\b(?:will|can|could|would|"
        r"help|allow|enable)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bif you (?:provide|share|specify|give|authorize|approve)\b"
        r"[^.]{0,80}\b(?:i (?:can|will|could|would)|"
        r"uri (?:can|will|could|would))\b",
        re.IGNORECASE,
    ),
)


class ResponseValidationError(ValueError):
    """Raised when a drafted response fails claim-consistency
    validation. Always means "discard this draft," never "retry
    automatically" - retrying is the caller's decision, not this
    function's."""


def validate_drafted_response(
    draft_text: str, outcome: Dict[str, Any]
) -> str:

    if not isinstance(draft_text, str) or not draft_text.strip():
        raise ResponseValidationError("draft is empty.")

    text = draft_text.strip()

    if len(text) > MAX_NARRATIVE_LENGTH:
        raise ResponseValidationError(
            f"draft exceeds {MAX_NARRATIVE_LENGTH} characters."
        )

    if looks_like_credential_value(text):
        raise ResponseValidationError(
            "draft looks credential-shaped."
        )

    execution = outcome.get("execution")
    execution_status = (
        execution.get("status") if isinstance(execution, dict) else None
    )

    if execution_status != "success" and _SUCCESS_CLAIM_PATTERN.search(
        text
    ):
        raise ResponseValidationError(
            "draft uses success-shaped language but the actual "
            f"execution status was {execution_status!r}, not "
            "'success'."
        )

    if execution_status != "success" and _has_not_implemented_gap(
        outcome
    ) and _implies_future_capability(text):
        raise ResponseValidationError(
            "draft implies that more detail, clarification, or "
            "authorization would make a not_implemented capability "
            "executable - no execution adapter exists at all for it, "
            "so nothing the user provides changes that."
        )

    if execution_status != "success":

        evidence_length = _outcome_evidence_length(outcome)
        allowed_length = min(
            MAX_NON_SUCCESS_NARRATIVE_LENGTH,
            max(
                MIN_UNGROUNDED_DRAFT_LENGTH,
                evidence_length * MAX_EXPANSION_RATIO,
            ),
        )

        if len(text) > allowed_length:
            raise ResponseValidationError(
                f"draft ({len(text)} chars) is too long relative to "
                f"the {evidence_length} chars of actual evidence in "
                f"outcome for a non-success status "
                f"({execution_status!r}); this is an explanation of "
                "a known outcome, not a solution-generation path, "
                "and likely contains invented content beyond what "
                "the runtime actually provided."
            )

    # The draft need not repeat an opaque action_id to the user - but
    # if it mentions a *different* action-id-shaped token than the one
    # actually in the outcome, that's a forged/hallucinated reference
    # and must be rejected.
    action_id = _find_action_id(outcome)

    for forged_id in _find_all_action_id_like_tokens(text):

        if forged_id != action_id:
            raise ResponseValidationError(
                "draft references an action id that does not match "
                "the actual proposed action."
            )

    return text


def _has_not_implemented_gap(outcome: Dict[str, Any]) -> bool:
    """True when outcome.known_gaps contains at least one entry whose
    gap reason is "not_implemented" (see
    CapabilityDescriptor.gap_reason) - i.e. no execution adapter
    exists at all for it. Falls back to the older status field
    (status in "planned"/"not_implemented") when "reason" is absent,
    so outcomes/tests built before this field existed are still
    treated correctly rather than silently exempted."""

    known_gaps = outcome.get("known_gaps")

    if not isinstance(known_gaps, list):
        return False

    for gap in known_gaps:

        if not isinstance(gap, dict):
            continue

        reason = gap.get("reason")

        if reason == "not_implemented":
            return True

        if reason is None and gap.get("status") in (
            "planned",
            "not_implemented",
        ):
            return True

    return False


def _implies_future_capability(text: str) -> bool:
    return any(
        pattern.search(text)
        for pattern in _IMPLIES_FUTURE_CAPABILITY_PATTERNS
    )


def _outcome_evidence_length(outcome: Dict[str, Any]) -> int:
    """Total length of the actual textual evidence the runtime gave
    the drafting model to work with: outcome.response's message/error
    text, plus every known_gaps entry's description/limitations. Used
    only to bound a non-"success" draft's length relative to real
    evidence - see MAX_EXPANSION_RATIO/MIN_UNGROUNDED_DRAFT_LENGTH."""

    parts = []

    response = outcome.get("response")

    if isinstance(response, dict):

        for key in ("message", "error"):
            value = response.get(key)

            if isinstance(value, str):
                parts.append(value)

    known_gaps = outcome.get("known_gaps")

    if isinstance(known_gaps, list):

        for gap in known_gaps:

            if not isinstance(gap, dict):
                continue

            for key in ("description", "limitations"):
                value = gap.get(key)

                if isinstance(value, str):
                    parts.append(value)

    return sum(len(part) for part in parts)


def _find_action_id(outcome: Dict[str, Any]) -> Optional[str]:

    response = outcome.get("response")

    if isinstance(response, dict):
        action_id = response.get("action_id")

        if isinstance(action_id, str):
            return action_id

    return None


_ACTION_ID_LIKE_PATTERN = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)


def _find_all_action_id_like_tokens(text: str):
    return _ACTION_ID_LIKE_PATTERN.findall(text)
