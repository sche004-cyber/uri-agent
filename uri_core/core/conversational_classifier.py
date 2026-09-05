"""Deterministic "no capability required" classification.

Some requests genuinely need no registered capability at all - a
greeting, a thank-you, a bare question about what URI can do. Before
this module, every one of these fell through CapabilityPlanner's
"planning_required" branch into WorkflowPlanner's generic fallback
workflow (retrieve_evidence -> identify_missing_information ->
prepare_output -> review_result), whose prepare_output step
unconditionally reports a missing-capability failure (see
workflow_capability_router.py's prepare_output docstring) - correct for
a genuine capability gap, dishonest and confusing for "hello".

This module decides ONLY the narrow question "is this one of those
clearly conversational cases" - it is not a chat engine, and it never
generates any reply text itself (see orchestrator.py's caller, which
still uses a single fixed deterministic string, optionally paraphrased
by the exact same narrative-drafting/validation pipeline every other
outcome already goes through - no new model-authority surface is
created here).

Authority split, unchanged from ADR-018/URI_MODEL_RUNTIME_CONTRACT: the
semantic interpreter (a model) may only ever describe a request via the
fixed 8-key contract (goal/task_type/domain/entities/requested_output/
requires_evidence/requires_clarification/suggested_next_step) - it
never decides whether a capability is required. That decision is made
entirely here, deterministically, by:

    1. Matching the user's OWN raw text (never anything the model
       wrote) against a small, explicit set of regexes for a greeting,
       a farewell, gratitude, or a bare question about what URI is/can
       do. This is the primary signal precisely because it is not
       model-authored.
    2. A safety gate on the semantic result: entities must be empty
       (nothing concrete is being referred to) AND requires_evidence
       must be exactly False AND requires_clarification must be
       exactly False (missing/None fails closed - never treated as
       False). Any concrete target, or any hint that evidence or
       clarification is needed, means this is NOT pure conversation,
       regardless of how the raw text reads.

Both conditions must hold. This is deliberately conservative: a
request that doesn't clearly match is left completely alone and falls
through to the existing planning_required -> workflow path exactly as
it always has - a false negative here is the pre-existing, unchanged
behaviour, never a regression. A false positive (calling a genuine
capability gap "conversational") would be a real regression against
Milestone 6/7/8A's honesty guarantees, so the patterns below are kept
narrow and are matched against the whole message where that materially
reduces risk (see _WHOLE_MESSAGE_PATTERNS vs _SUBSTRING_PATTERNS).
"""

import re
from typing import Any, Dict, Optional

# Matched against the ENTIRE trimmed message (trailing punctuation
# ignored) - these phrases are conversational only when they ARE the
# message, not merely a prefix. "hi, also optimize my pc" must never
# match: requiring a full-message match is what keeps that safe without
# relying on the semantic safety gate alone.
#: An optional address to URI by name, tolerated on either side of the
#: core phrase ("hello URI", "URI, hello", "thanks URI") - naming who
#: you're greeting/thanking is still just a greeting/thanks, not a
#: second, concrete entity (the semantic safety gate below still
#: applies independently: if the interpreter reports any other entity,
#: classification is still blocked).
_URI_ADDRESS = r"(?:uri[,]?\s+|\s*,?\s*uri)?"

_WHOLE_MESSAGE_PATTERNS = (
    re.compile(
        rf"^{_URI_ADDRESS}"
        r"(hi|hello|hey|greetings|good\s+(morning|afternoon|evening|night))"
        rf"{_URI_ADDRESS}$",
        re.IGNORECASE,
    ),
    re.compile(
        rf"^{_URI_ADDRESS}"
        r"(thanks|thank\s+you|thx|ty|cheers|ok(ay)?|got\s+it|noted|"
        r"sounds\s+good|great|awesome|perfect)"
        rf"{_URI_ADDRESS}$",
        re.IGNORECASE,
    ),
    re.compile(
        rf"^{_URI_ADDRESS}(bye|goodbye|see\s+you|take\s+care){_URI_ADDRESS}$",
        re.IGNORECASE,
    ),
)

# Matched anywhere in the message - a bare, self-referential question
# about URI itself. Still gated by the same entities/requires_evidence/
# requires_clarification safety check below, so "what can you do to
# optimize my pc" is only misclassified if the semantic interpreter
# ALSO reports no entities and no evidence/clarification need for it,
# which real capability-gap fixtures do not (see
# test_conversational_classifier.py's negative cases).
_SUBSTRING_PATTERNS = (
    re.compile(r"\bwhat\s+can\s+you\s+do\b", re.IGNORECASE),
    re.compile(r"\bwho\s+are\s+you\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+are\s+you\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+do\s+you\s+do\b", re.IGNORECASE),
)

_TRAILING_PUNCTUATION = re.compile(r"[!?.\s]+$")


def _matches_conversational_text(user_text: str) -> bool:
    text = (user_text or "").strip()

    if not text:
        return False

    whole_message = _TRAILING_PUNCTUATION.sub("", text).strip()

    if any(
        pattern.match(whole_message) for pattern in _WHOLE_MESSAGE_PATTERNS
    ):
        return True

    return any(pattern.search(text) for pattern in _SUBSTRING_PATTERNS)


def _passes_semantic_safety_gate(semantic_result: Dict[str, Any]) -> bool:
    """Fails closed: a missing/None/non-boolean value is never treated
    as satisfying the gate. Only an explicit False from the semantic
    interpreter's own 8-key contract counts."""

    entities = semantic_result.get("entities")

    if not isinstance(entities, list):
        return False

    if len(entities) > 0:
        return False

    if semantic_result.get("requires_evidence") is not False:
        return False

    if semantic_result.get("requires_clarification") is not False:
        return False

    return True


def is_conversational_no_capability_required(
    user_text: str, semantic_result: Optional[Dict[str, Any]]
) -> bool:
    """True only when BOTH the raw user text clearly reads as a
    greeting/farewell/thanks/bare self-referential question AND the
    semantic interpreter's own structured result contains no concrete
    entity and no evidence/clarification need. See module docstring for
    why both conditions exist and why this stays conservative."""

    if not isinstance(semantic_result, dict):
        return False

    if not _passes_semantic_safety_gate(semantic_result):
        return False

    return _matches_conversational_text(user_text)


# The single, fixed, honest reply used whenever the above returns True.
# This is a static template, not a generated/free-form chat response -
# see orchestrator.py, where narrative drafting may optionally
# paraphrase it (through the exact same drafting/validation pipeline
# every other outcome already goes through), but the deterministic
# fallback a client sees if drafting is off/fails is always this exact
# text. Deliberately names only the real, registered capabilities
# (matches capabilities_registry.json's active_tools) rather than
# claiming anything broader.
NO_CAPABILITY_REQUIRED_MESSAGE = (
    "Hello — I'm URI. Right now I can help with drafting institutional "
    "notes and orders, looking up student records, and reading "
    "spreadsheets. Let me know what you'd like help with."
)
