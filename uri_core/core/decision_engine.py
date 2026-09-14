"""M30.3: canonical Brain Decision Engine - SHADOW MODE ONLY.

docs/architecture/URI_CANONICAL_AGENT_LOOP_ARCHITECTURE.md §5 (frozen
schema) / docs/plans/URI_CANONICAL_AGENT_LOOP_MIGRATION_PLAN.md §4
Phase A.

This module proposes. It never executes, never alters routing, and
never changes what a user sees - every public function here either
returns a plain dict describing what WOULD happen, or writes one
privacy-safe line to a shadow-evidence log. Nothing in this module is
imported by, or can influence, the live decision/execution path unless
a caller explicitly reads its return value and acts on it - which
nothing does yet (that is M30.5/M30.6's separately-authorized scope).

One canonical schema, no second classifier: this is the ONLY place a
Brain Decision Contract is requested from a model in this codebase.
It reasons over Turn State (M30.1) + Capability Directory Level-1
summaries (M30.2) only - never a second discovery/classification
round-trip, per the frozen Stage 2 architecture's explicit rejection of
that pattern. If a capability is selected, Level 2 detail (full action
schema) is fetched deterministically, from the SAME CapabilityDirectory
instance, scoped to exactly that one capability - never flattened into
the decision prompt itself.

Naming note carried over from the accepted migration plan: the frozen
mode name is `single_action` (Stage 2 §5), not `action`.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from uri_core.config.model_roles import ROLE_REASONING, build_provider
from uri_core.core.model_router import get_router
from uri_core.core.capability_directory import CapabilityDirectory
from uri_core.core.capability_feasibility import CapabilityFeasibility
from uri_core.core.capability_relevance import plausible_matches
from uri_core.core.turn_state import assemble_turn_state

try:
    from uri_core.capabilities import MultiActionCapabilityRegistry
except ImportError:  # pragma: no cover
    MultiActionCapabilityRegistry = None  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------
# Feature flag - env-var gated, matching this repository's existing
# precedent for a runtime-behavior toggle that is not a per-user
# preference (see server.py's URI_ALLOW_INSECURE_BIND). Default OFF:
# reading this function costs nothing when unset, and nothing in this
# module runs unless a caller checks it first.
# ---------------------------------------------------------------------

SHADOW_ENV_VAR = "URI_ENABLE_DECISION_ENGINE_SHADOW"


def decision_engine_shadow_enabled() -> bool:
    return os.environ.get(SHADOW_ENV_VAR) == "1"


# ---------------------------------------------------------------------
# Decision Contract - frozen Stage 2 §5 schema.
# ---------------------------------------------------------------------

VALID_MODES = {
    "conversation",
    "clarification",
    "unsupported",
    "single_action",
    "multi_action",
    "approval_required",
    "workflow_continuation",
}

REQUIRED_CONTRACT_KEYS = (
    "goal",
    "mode",
    "capability",
    "actions",
    "clarification",
    "unsupported_reason",
    "requires_approval",
    "confidence",
    "reason",
)

DECISION_CONTRACT_SYSTEM_PROMPT = """
This is URI's canonical Brain Decision Engine, in SHADOW MODE - your
output is recorded for comparison only and never executes anything.

You are given a compact "turn_state" JSON object: the latest user
message, recent conversation, any pending interaction (a prior question
still awaiting an answer), a list of capability summaries (name,
one-line description, real availability where already known, action
names), recent real results, and known session facts. When present,
"capability_action_affordances" gives a one-line description for each
real action of the small set of capabilities already shown to you (not
every capability that exists) - use it to judge whether one action or
several are needed, never to guess parameters in detail (full schemas
are still looked up only after you select a capability).

Decide FIRST what kind of situation this is, then only what to do about
it. Return ONLY a single valid JSON object with exactly these keys:
goal, mode, capability, actions, clarification, unsupported_reason,
requires_approval, confidence, reason - every key present, even when
its value is null. Answer the questions below, in this order, before
picking `mode`:

    1. LATEST USER INTENT WINS, unless this message plausibly satisfies
       a pending interaction. Apply the pending interaction as ACTIVE
       CANDIDATE CONTEXT, never as a mandatory next route. Work this
       step in order:

       1a. Interpret THIS message on its own first, as if
           active_pointer.kind were "none" and recent_conversation did
           not exist. On its own words alone: does it most plausibly
           name a real, different goal that one of the given capability
           summaries covers - a goal unrelated to whatever active_
           pointer.originating_goal was about? Form this independent
           judgment BEFORE looking at active_pointer at all; recent_
           conversation and active_pointer are background/candidate
           context for later steps, never the starting point for
           reading this message's own meaning.

       1b. If active_pointer.kind is exactly "none": there is nothing
           pending - use your 1a judgment as-is and continue to
           question 2. "workflow_continuation" is never valid here.
           Example: active_pointer.kind is "none" and the user says "I
           usually work from the library in the evenings." - mode is
           "single_action" with capability "remember_fact" (1a's own
           judgment - a fact worth saving), never "workflow_continuation".

       1c. If active_pointer.kind is NOT "none": does this message
           plausibly SATISFY the pending field itself - a real,
           specific, affirmative match, not just "does not look like
           something else"? Strong satisfaction evidence: it is short
           and concrete, and (when active_pointer.expected_type is
           given) shaped like that type (e.g. an identifier-looking
           string when expected_type is "identifier"), OR it names one
           of the choices the pending question itself offered. If it
           satisfies the pending field: "workflow_continuation" - set
           `capability` in this same step FROM active_pointer, not from
           your 1a judgment (1a only asked whether a DIFFERENT goal
           exists, it never restricts this): use active_pointer.
           capability_id directly when given; when it is null, name
           whichever given capability summary best fits active_pointer.
           originating_goal (what URI was originally trying to do) -
           this message's own short words will often carry no capability
           clue of their own, that is expected and not a reason to leave
           `capability` null. Stop here.
           Example: active_pointer.originating_goal is "Check my unread
           mailbox for something urgent." (question: "Which message did
           you mean?", expected_type "string"), user replies "The
           second one." - this satisfies the pending selection (mode
           "workflow_continuation"), and `capability` must still be set
           to whichever given summary best fits "check my mailbox" (the
           mailbox-handling capability) - never left null just because
           "The second one." itself names no capability.

       1d. If it does NOT satisfy the pending field (1c is false): the
           pending interaction loses priority - LATEST USER INTENT WINS.
           Use your 1a judgment: if 1a names a real different goal,
           treat active_pointer as no longer relevant and continue to
           question 2 with THAT goal, exactly as if nothing were
           pending. If 1a instead reads as ending/withdrawing the
           pending request itself (no new goal, no satisfying value -
           the user is stepping away from what URI asked, however that
           is phrased), the answer is "conversation" - stop here.

       This is a judgment about the message's own content, never a
       fixed list of accept/cancel words - satisfaction is decided by
       shape/choice-matching (1c), not by the mere existence of a
       pending question.
       Example: active_pointer.originating_goal is "Find the student."
       (question: "What is the student's roll number?", expected_type
       "identifier") and the user replies "Actually, draft an office
       order instead." - 1a independently reads this as the goal
       "draft an office order," which does not satisfy an
       identifier-shaped roll number (1c is false), so LATEST USER
       INTENT WINS: mode is "single_action" with capability
       "draft_institutional_order", NEVER "workflow_continuation",
       even though active_pointer.kind is not "none".
    2. Otherwise, does the user simply want discussion, an opinion, or
       reasoning, with no concrete outcome any capability produces? The
       answer is "conversation" - stop here.
    3. Otherwise, does at least one capability summary plausibly cover
       this goal? Pick your single best real candidate (never invented)
       and continue to question 4.
       - If NO capability plausibly covers it, at all: the answer is
         "unsupported" - stop here. This must be a genuine absence of
         fit, not mere uncertainty about which one applies (see the
         "clarification" rule below for that case).
    4. Given your best candidate from question 3, is a concrete,
       specific required input actually missing (e.g. an identifier, a
       search term the user never gave) - not merely "I'm not fully
       sure this is the right capability"? If a real input is missing:
       "clarification" (name the capability anyway if you have one).
       If nothing concrete is missing, does answering the user's WHOLE
       request take exactly one action, or does it genuinely take more
       than one? A single request can contain more than one real
       sub-ask (e.g. "how many X are there, AND is anything among them
       notable" asks for a count AND a content check - two different
       actions, even from the same one capability). If exactly one
       action fully answers it: "single_action". If it genuinely takes
       more than one action to fully answer what was asked (whether
       from one capability or several): "multi_action" - list every
       action needed, in order, in `actions`.
    5. Would the specific action you'd take be inherently sensitive
       (e.g. sending, deleting, publishing something) even before
       considering the runtime's own real approval rules? If so:
       "approval_required" - the runtime still decides the real
       requirement from the capability's own metadata, this is your
       best-effort flag only.

CRITICAL: "clarification" is not a safe default for general
uncertainty. Being unsure WHICH capability fits, when at least one
plausibly does, is answered by picking your best candidate
("single_action"/"multi_action"), not by asking a clarifying question.
Reserve "clarification" for a genuinely missing, concrete, required
piece of information for an otherwise-identified capability.

A capability summary describes that capability's OWN normal use - you
must still judge whether THIS message performs that role, not only
whether it uses the same words the summary does. A first-person
statement of a fact about the user (their name, workplace, a stated
preference, a contact detail, or similar) IS itself an implicit request
to remember it, even when it never says "remember" or "save" - treat it
as satisfying a memory-saving capability's role directly, never as
merely "conversation" because no save-shaped phrase was used.

goal: the user's actual objective, plain text.

mode: exactly one of "conversation", "clarification", "unsupported",
    "single_action", "multi_action", "approval_required",
    "workflow_continuation" - chosen via the checklist above.
    - "conversation": no capability is needed at all.
    - "clarification": a real capability likely applies, but one
      specific, concrete piece of information is genuinely missing -
      never used merely because you are uncertain which capability
      applies.
    - "unsupported": nothing in the given capability summaries could
      plausibly do what the user is asking, regardless of what they
      might clarify. Never choose this only because a capability LOOKS
      unavailable right now (that is "single_action"/"multi_action"
      with capability named - a disconnected/unavailable capability is
      not the same as "no such capability exists").
    - "single_action": one action fully completes the user's goal.
    - "multi_action": completing the user's WHOLE goal genuinely takes
      more than one action - never chosen merely because more than one
      capability happens to exist or could theoretically help; only
      when the request itself has more than one real part to answer.
      Never use "clarification" instead just because the request needs
      multiple actions - naming several real actions is itself a
      complete, valid answer, not something to ask permission for.
    - "approval_required": propose this only when you believe the
      action is inherently sensitive (e.g. sending/deleting something)
      - the real approval requirement is always decided by the runtime
      from the capability's own declared metadata, never by you alone.
    - "workflow_continuation": chosen only at step 1c above - this
      message affirmatively satisfies the pending field. Never guess
      this when active_pointer.kind is "none" (1b), and never when the
      message does not satisfy the pending field even if
      active_pointer.kind is not "none" (1d - latest intent wins
      instead). Always set `capability` in the same step, per 1c.

capability: the exact capability_id from the given capability_summaries
    list, or null. Never invent a name that is not in that list, and
    never use an action name (from `actions` or from
    `capability_action_affordances`'s inner keys) as a capability -
    those are two different vocabularies; a capability_id never
    matches one of its own action names.

actions: a list of {"name": "...", "inputs": {...}} objects using only
    action names you were told this capability has (if none were given,
    leave actions empty - detailed schemas are looked up separately,
    after you select a capability, never guessed here).

clarification: {"question": "...", "missing_field": "..."} or null -
    only when mode is "clarification".

unsupported_reason: a short explanation, or null - only when mode is
    "unsupported".

requires_approval: true or false - your own best guess only; the real
    answer is decided deterministically elsewhere.

confidence: "high", "medium", or "low" - be honest; "low" is a normal,
    useful answer, not a failure.

reason: one short sentence justifying this decision.

Never claim a capability is available, connected, or permitted - you do
not have that authority and are not given it here. Never claim an
action already happened. Return nothing but the JSON object.
"""


@dataclass(frozen=True)
class DecisionOutcome:
    status: str  # "ok" | "invalid" | "unavailable"
    contract: Optional[Dict[str, Any]] = None
    invalid_reason: Optional[str] = None
    error: Optional[str] = None
    raw_text: Optional[str] = None


def _foundational_ids(capability_directory: CapabilityDirectory) -> List[str]:
    try:
        return [
            e["capability_id"] for e in capability_directory.summaries() if e.get("foundational")
        ]
    except Exception:
        return []


def preselect_candidate_ids(
    turn_state_data: Dict[str, Any],
    capability_directory: Optional[CapabilityDirectory],
    limit: int = 5,
) -> Optional[List[str]]:
    """M30.5A/M30.5B: deterministic, non-LLM candidate preselection -
    reuses capability_relevance.py's own directory-derived scoring (the
    same function the tightened Unsupported Gate uses), never a second
    model round-trip. Generous by design (a low min score): under-
    inclusion here silently hides a valid capability from the Decision
    Engine, which is worse than a slightly larger prompt - conservative
    in the OPPOSITE direction from the Unsupported Gate's own
    tightening.

    M30.5B fix (a real, live-verified regression M30.5A introduced):
    lexical top-N alone silently excluded remember_fact/recall_memory
    for personal disclosures ("I work at NIT Sikkim") that share almost
    no vocabulary with either capability's own description - these two
    are now ALWAYS included (capability_directory.py's `foundational`
    flag, a property of the capability, never of the user's specific
    wording) regardless of lexical score. M30.5B also unions in
    candidates discovered against `active_pointer.originating_goal`
    (when a pending interaction exists) - the same deterministic
    scoring, just also run against what URI was originally trying to
    do, so a continuation's own capability can be recovered even when
    the session itself never recorded one (see turn_state.py's own
    documented gap).

    Returns None (never an empty list treated as "nothing plausible")
    when preselection cannot run at all, so the caller falls back to
    showing every capability rather than silently showing none."""
    if capability_directory is None:
        return None
    goal_text = str(turn_state_data.get("turn", {}).get("user_text") or "")
    try:
        candidates = plausible_matches(
            capability_directory, goal_text, limit=limit, min_discriminating_score=0.0
        )
        ids = [c["capability"] for c in candidates]
    except Exception:
        ids = []

    originating_goal = (turn_state_data.get("active_pointer") or {}).get("originating_goal")
    if originating_goal:
        try:
            originating_candidates = plausible_matches(
                capability_directory, str(originating_goal), limit=limit, min_discriminating_score=0.0
            )
            for c in originating_candidates:
                if c["capability"] not in ids:
                    ids.append(c["capability"])
        except Exception:
            pass

    for foundational_id in _foundational_ids(capability_directory):
        if foundational_id not in ids:
            ids.append(foundational_id)

    return ids or None


def candidate_recall_at_k(
    turn_state_data: Dict[str, Any],
    capability_directory: Optional[CapabilityDirectory],
    expected_capability_id: Optional[str],
    k: int,
) -> Optional[bool]:
    """M30.5B: CANDIDATE_RECALL@K - a preselection-quality metric, kept
    strictly separate from mode/capability accuracy (evaluate_against_
    golden measures whether the MODEL's final answer was right; this
    measures whether the right capability was even offered to it).

    Returns True/False when `expected_capability_id` is given (whether
    that id is present in preselect_candidate_ids(..., limit=k)), or
    None when there is no expected capability for this case (recall is
    not a meaningful concept for e.g. a pure-conversation golden case -
    callers should exclude None results from the recall denominator,
    never count them as a miss)."""
    if not expected_capability_id:
        return None
    ids = preselect_candidate_ids(turn_state_data, capability_directory, limit=k) or []
    return expected_capability_id in ids


def build_decision_request(
    turn_state_data: Dict[str, Any],
    preselected_ids: Optional[List[str]] = None,
    capability_directory: Optional[CapabilityDirectory] = None,
) -> Dict[str, Any]:
    """Level-1-only prompt payload - no full action schemas, no full
    memory/graph dumps, matching the frozen "progressive discovery,
    never flattened" principle. `preselected_ids`, when given, narrows
    `capability_summaries` to that deterministic candidate set - always
    including whatever active_pointer.capability_id already names (a
    pending continuation's own capability must never silently vanish
    from view because preselection missed it for this turn's raw text).

    M30.5B: when both `preselected_ids` and `capability_directory` are
    given, also attaches a compact `capability_action_affordances` map
    - {capability_id: {action_name: one-line description}} - for
    exactly the small (already-narrowed) candidate set only. This is
    NOT a full schema dump (no parameters/returns/risk) and never
    applies to the un-preselected full catalogue - it exists so the
    model can actually reason about WHICH combination of a preselected
    capability's real actions its one goal needs (the M30.5 finding:
    multi_action needs this, not more capability-level prose)."""
    summaries = turn_state_data["capability_summaries"]
    if preselected_ids is not None:
        keep = set(preselected_ids)
        pending_capability = (turn_state_data.get("active_pointer") or {}).get("capability_id")
        if pending_capability:
            keep.add(pending_capability)
        summaries = [s for s in summaries if s.get("capability_id") in keep]

    request = {
        "user_text": turn_state_data["turn"]["user_text"],
        "recent_conversation": turn_state_data["recent_conversation"],
        "active_pointer": turn_state_data["active_pointer"],
        "capability_summaries": summaries,
        "session_facts": turn_state_data["session_facts"],
        "attempt_history": turn_state_data["attempt_history"],
    }

    if preselected_ids is not None and capability_directory is not None:
        affordances: Dict[str, Any] = {}
        for summary in summaries:
            capability_id = summary.get("capability_id")
            if summary.get("source") != "multi_action" or not capability_id:
                continue
            try:
                detail = capability_directory.describe(capability_id)
            except Exception:
                detail = None
            schemas = (detail or {}).get("action_schemas") or {}
            if schemas:
                affordances[capability_id] = {
                    name: (info or {}).get("description")
                    for name, info in schemas.items()
                }
        if affordances:
            request["capability_action_affordances"] = affordances

    return request


def _validate_contract(
    parsed: Any, known_capability_ids: set, directory: Optional[CapabilityDirectory]
) -> DecisionOutcome:
    if not isinstance(parsed, dict):
        return DecisionOutcome(status="invalid", invalid_reason="not_an_object")

    missing = [key for key in REQUIRED_CONTRACT_KEYS if key not in parsed]
    if missing:
        return DecisionOutcome(
            status="invalid", invalid_reason=f"missing_fields:{','.join(missing)}"
        )

    mode = parsed.get("mode")
    if mode not in VALID_MODES:
        return DecisionOutcome(status="invalid", invalid_reason="invalid_mode")

    capability = parsed.get("capability")
    if capability is not None:
        if not isinstance(capability, str) or capability not in known_capability_ids:
            return DecisionOutcome(status="invalid", invalid_reason="unknown_capability")

    actions = parsed.get("actions") or []
    if not isinstance(actions, list):
        return DecisionOutcome(status="invalid", invalid_reason="actions_not_a_list")

    if capability is not None and actions and directory is not None:
        detail = directory.describe(capability)
        known_actions = set(detail["actions"]) if detail else set()
        for action in actions:
            name = action.get("name") if isinstance(action, dict) else None
            if known_actions and name not in known_actions:
                return DecisionOutcome(
                    status="invalid", invalid_reason=f"unknown_action:{name}"
                )

    return DecisionOutcome(status="ok", contract=parsed)


def propose_decision(
    *,
    turn_state_data: Dict[str, Any],
    capability_directory: Optional[CapabilityDirectory],
    model_callable: Optional[Callable[[str], str]] = None,
    principal: Any = None,
    preselect: bool = False,
    preselect_limit: int = 5,
) -> DecisionOutcome:
    """Never raises. `model_callable`, when given (tests), receives the
    request JSON string and returns raw model text - the exact shape
    ModelReasoningGateway's own model_callable already uses, so a test
    fake here is identical in spirit to test_orchestrator_*'s existing
    fakes. Without one, the real ModelRouter (M22.6, unchanged) is used
    - the same transport model_reasoning_adapter.py already relies on,
    reused rather than duplicated.

    `preselect=True` (M30.5A, default False - additive, never changes
    existing callers' behavior) narrows the prompt's capability_
    summaries to a deterministic candidate set (preselect_candidate_ids)
    before the one model call - never a second model round-trip.
    Validation (_validate_contract) always checks the model's proposal
    against the FULL directory regardless of this flag, so preselection
    can only narrow what the model SEES, never what a correct proposal
    is allowed to name."""

    preselected_ids = (
        preselect_candidate_ids(turn_state_data, capability_directory, limit=preselect_limit)
        if preselect
        else None
    )
    request_json = json.dumps(
        build_decision_request(
            turn_state_data,
            preselected_ids=preselected_ids,
            capability_directory=capability_directory if preselect else None,
        ),
        ensure_ascii=False,
    )

    try:
        if model_callable is not None:
            raw_text = model_callable(request_json)
        else:
            response = get_router().attempt(
                ROLE_REASONING,
                principal,
                system=DECISION_CONTRACT_SYSTEM_PROMPT,
                user=request_json,
                temperature=0,
                max_tokens=500,
            )
            raw_text = response.content
    except Exception as exc:
        return DecisionOutcome(status="unavailable", error=str(exc))

    text = (raw_text or "").strip()
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(text)
    except (TypeError, ValueError):
        return DecisionOutcome(status="invalid", invalid_reason="malformed_json", raw_text=text[:500])

    known_ids = set()
    if capability_directory is not None:
        try:
            known_ids = {e["capability_id"] for e in capability_directory.summaries()}
        except Exception:
            known_ids = set()

    outcome = _validate_contract(parsed, known_ids, capability_directory)
    if outcome.status == "invalid":
        return DecisionOutcome(
            status=outcome.status, invalid_reason=outcome.invalid_reason, raw_text=text[:500]
        )
    return outcome


# ---------------------------------------------------------------------
# Old-path vs. new-decision comparison (evidence for M30.4).
# ---------------------------------------------------------------------

AGREEMENT_CATEGORIES = (
    "AGREE",
    "MODE_MISMATCH",
    "CAPABILITY_MISMATCH",
    "CLARIFICATION_MISMATCH",
    "UNSUPPORTED_MISMATCH",
    "CONNECTION_STATE_MISMATCH",
    "WORKFLOW_CONTINUATION_MISMATCH",
    # M30.4: the M30.3 heuristic only ever caught a FALSE continuation
    # claim (proposing workflow_continuation with nothing pending) - it
    # had no way to notice the opposite, real failure M30.3's own shadow
    # run surfaced live (a roll-number answer to a pending question
    # re-classified as a fresh "clarification" instead of continuing).
    # Both directions are now distinct categories, never merged.
    "WORKFLOW_CONTINUATION_MISSED",
    "ACTION_SET_MISMATCH",
    "INVALID_DECISION",
)


def _old_path_summary(old_path_result: Dict[str, Any]) -> Dict[str, Any]:
    plan = old_path_result.get("plan") or {}
    execution = old_path_result.get("execution") or {}
    return {
        "plan_status": plan.get("status"),
        "tool_name": plan.get("tool_name") or execution.get("capability") or execution.get("tool"),
        "execution_status": execution.get("status"),
    }


def classify_agreement(
    old_path_result: Dict[str, Any],
    decision: DecisionOutcome,
    capability_directory: Optional[CapabilityDirectory],
    active_pointer_kind: str,
) -> str:
    """Approximate, documented heuristic - evidence for the human-
    reviewed M30.4 comparison, never itself a decision. Never raises."""

    if decision.status != "ok" or decision.contract is None:
        return "INVALID_DECISION"

    contract = decision.contract
    old = _old_path_summary(old_path_result)
    mode = contract.get("mode")
    new_capability = contract.get("capability")

    old_had_no_tool = not old["tool_name"]
    old_was_waiting = old["execution_status"] == "waiting_for_input"
    old_was_success = old["execution_status"] == "success"

    if mode == "workflow_continuation" and active_pointer_kind == "none":
        return "WORKFLOW_CONTINUATION_MISMATCH"

    # M30.4: a real pending question/workflow existed BEFORE this turn
    # (active_pointer reflects state carried in from the prior turn),
    # and the engine did not propose continuing it. This is also the
    # correct, expected shape for a genuine topic switch (mandatory
    # scenario 12) - this category flags the CANDIDATE for review, it
    # does not itself judge right or wrong; see evaluate_against_golden()
    # for the ground-truth-aware version used against the golden set,
    # where a real topic-switch case is labeled correct, not missed.
    if active_pointer_kind != "none" and mode != "workflow_continuation":
        return "WORKFLOW_CONTINUATION_MISSED"

    if mode == "conversation":
        return "AGREE" if old_had_no_tool else "MODE_MISMATCH"

    if mode == "unsupported":
        # The old path executing something real while the new decision
        # claims nothing could ever work is a genuine mismatch worth a
        # human look, not silently accepted.
        return "UNSUPPORTED_MISMATCH" if old_was_success else "AGREE"

    if mode == "clarification":
        return "AGREE" if old_was_waiting else "CLARIFICATION_MISMATCH"

    if mode in ("single_action", "multi_action"):
        if new_capability and capability_directory is not None:
            entry = capability_directory.describe(new_capability)
            if entry is not None and entry.get("availability_known") and entry.get("available") is False:
                # The model proposed executing a capability the
                # directory already knows is unavailable right now -
                # exactly the "never let the model invent availability"
                # case (mandatory scenario 3).
                return "CONNECTION_STATE_MISMATCH"

        if old["tool_name"] and new_capability and old["tool_name"] != new_capability:
            return "CAPABILITY_MISMATCH"

        if old["tool_name"] and new_capability == old["tool_name"]:
            old_action_count = 1 if old["tool_name"] else 0
            new_action_count = len(contract.get("actions") or []) or (1 if new_capability else 0)
            if mode == "multi_action" and new_action_count <= 1:
                return "ACTION_SET_MISMATCH"
            return "AGREE"

        if old_had_no_tool and new_capability:
            return "CAPABILITY_MISMATCH"

        return "MODE_MISMATCH"

    if mode == "approval_required":
        return "AGREE" if old["execution_status"] in ("waiting_for_input", "success") else "MODE_MISMATCH"

    return "MODE_MISMATCH"


# ---------------------------------------------------------------------
# M30.4: golden-set (ground-truth) evaluation - distinct from
# classify_agreement() above, which compares against the OLD PATH's
# outcome (useful when there is no human label). This compares against
# an explicit expected shape a human wrote for a golden test case, and
# can therefore distinguish a FALSE positive from a MISSED one in both
# directions for every mode, not only workflow_continuation.
# ---------------------------------------------------------------------

GOLDEN_CATEGORIES = (
    "correct",
    "false_unsupported",
    "missed_unsupported",
    "false_clarification",
    "missed_clarification",
    "false_continuation",
    "missed_continuation",
    "false_capability",
    "missed_capability",
    "over_tooling",
    "under_tooling",
    "invalid",
)


def evaluate_against_golden(
    expected: Dict[str, Any], decision: DecisionOutcome
) -> Dict[str, Any]:
    """`expected` is a golden-set case's ground truth: at minimum
    {"mode": ..., "capability": ... or None, "min_actions": int}. Never
    raises. Returns a dict with per-aspect booleans plus one overall
    `category` from GOLDEN_CATEGORIES, so a runner can compute both a
    simple accuracy number and precision/recall per mode."""

    if decision.status != "ok" or decision.contract is None:
        return {
            "mode_correct": False,
            "capability_correct": False,
            "action_set_correct": False,
            "category": "invalid",
        }

    contract = decision.contract
    expected_mode = expected.get("mode")
    actual_mode = contract.get("mode")
    mode_correct = expected_mode == actual_mode

    expected_capability = expected.get("capability")
    actual_capability = contract.get("capability")
    capability_correct = (
        expected_capability is None or expected_capability == actual_capability
    )

    expected_min_actions = expected.get("min_actions", 0)
    actual_action_count = len(contract.get("actions") or [])
    action_set_correct = actual_action_count >= expected_min_actions

    # Priority order matters here: unsupported and workflow_continuation
    # are checked before the generic clarification pair, so e.g. an
    # expected workflow_continuation that came back as clarification is
    # reported as "missed_continuation" (the load-bearing distinction),
    # never masked as a generic "false_clarification".
    category = "correct"
    if not mode_correct:
        if expected_mode == "unsupported" and actual_mode != "unsupported":
            category = "missed_unsupported"
        elif actual_mode == "unsupported" and expected_mode != "unsupported":
            category = "false_unsupported"
        elif expected_mode == "workflow_continuation" and actual_mode != "workflow_continuation":
            category = "missed_continuation"
        elif actual_mode == "workflow_continuation" and expected_mode != "workflow_continuation":
            category = "false_continuation"
        elif expected_mode == "clarification" and actual_mode != "clarification":
            category = "missed_clarification"
        elif actual_mode == "clarification" and expected_mode != "clarification":
            category = "false_clarification"
        else:
            category = "false_capability" if actual_capability else "missed_capability"
    elif not capability_correct:
        category = "missed_capability" if actual_capability is None else "false_capability"
    elif not action_set_correct:
        category = "under_tooling" if actual_action_count < expected_min_actions else "over_tooling"

    return {
        "mode_correct": mode_correct,
        "capability_correct": capability_correct,
        "action_set_correct": action_set_correct,
        "category": category,
    }


# ---------------------------------------------------------------------
# M30.5A: over-tooling detection - DECISION-QUALITY evaluation, kept
# explicitly separate from decision_gates.py's safety verification (per
# the accepted scope: "keep safety validity separate from decision
# quality"). A capability can be entirely real, available, permitted,
# and require no approval - genuinely READY by every gate - while still
# being the wrong thing to reach for. Gates will never flag that; this
# does, offline, for evaluation only.
# ---------------------------------------------------------------------


def detect_over_tooling(
    decision: DecisionOutcome,
    turn_state_data: Dict[str, Any],
    capability_directory: Optional[CapabilityDirectory],
    min_discriminating_score: float = 0.02,
) -> bool:
    """True when an action-taking mode was proposed but the proposed
    capability's own discriminating-term overlap with the goal (see
    capability_relevance.py) is at or below the same conservative
    threshold the Unsupported Gate itself uses - i.e. nothing about
    this specific capability's real affordances actually justifies it
    for this goal, even though it may pass every safety gate cleanly.
    Never raises; False (not flagged) on any missing input, since this
    is an offline quality signal, not a safety gate - silence here is
    never treated as a safety guarantee."""
    if decision.status != "ok" or decision.contract is None or capability_directory is None:
        return False

    mode = decision.contract.get("mode")
    capability_id = decision.contract.get("capability")
    if mode not in ("single_action", "multi_action") or not capability_id:
        return False

    entry = capability_directory.describe(capability_id)
    if entry is None:
        return False

    goal_text = str(decision.contract.get("goal") or turn_state_data.get("turn", {}).get("user_text") or "")
    capability_text = f"{capability_id} {entry.get('summary') or ''}"

    try:
        from uri_core.core.capability_relevance import (
            compute_term_document_frequency,
            discriminating_overlap,
        )

        doc_freq = compute_term_document_frequency(capability_directory)
        overlap = discriminating_overlap(goal_text, capability_text, doc_freq)
    except Exception:
        return False

    return overlap["discriminating_score"] <= min_discriminating_score


# ---------------------------------------------------------------------
# Privacy-safe shadow trace.
# ---------------------------------------------------------------------

DEFAULT_SHADOW_LOG_PATH = "uri_workspace/decision_engine_shadow_log.jsonl"


def _bucket_length(text: str) -> str:
    length = len(text or "")
    if length == 0:
        return "0"
    if length <= 20:
        return "1-20"
    if length <= 80:
        return "21-80"
    if length <= 200:
        return "81-200"
    return "200+"


def build_shadow_trace(
    *,
    session_id: Optional[str],
    user_text: str,
    turn_state_data: Dict[str, Any],
    decision: DecisionOutcome,
    old_path_result: Dict[str, Any],
    agreement: str,
    gate_result: Any = None,
) -> Dict[str, Any]:
    """Every field here is either a length bucket, a status/id string
    already treated as non-sensitive elsewhere in this codebase (e.g.
    capability ids, mode names), or a small boolean/enum - never raw
    user text, raw memory/graph content, or any credential-shaped
    value."""

    contract = decision.contract or {}
    capability_id = contract.get("capability")
    availability_known = None
    connection_state = None
    if capability_id:
        for entry in turn_state_data.get("capability_summaries", []):
            if entry.get("capability_id") == capability_id:
                availability_known = entry.get("availability_known")
                connection_state = entry.get("connection_state")
                break

    return {
        "timestamp": time.time(),
        "session_id": session_id,
        "user_text_length_bucket": _bucket_length(user_text),
        "decision_status": decision.status,
        "invalid_reason": decision.invalid_reason,
        "mode": contract.get("mode"),
        "capability_id": capability_id,
        "action_names": [
            a.get("name") for a in (contract.get("actions") or []) if isinstance(a, dict)
        ],
        "needs_clarification": contract.get("mode") == "clarification",
        "missing_field": (contract.get("clarification") or {}).get("missing_field"),
        "unsupported_proposed": contract.get("mode") == "unsupported",
        "workflow_continuation_proposed": contract.get("mode") == "workflow_continuation",
        "approval_proposed": contract.get("requires_approval"),
        "confidence": contract.get("confidence"),
        "capability_availability_known": availability_known,
        "connection_state": connection_state,
        "old_path": _old_path_summary(old_path_result),
        "agreement": agreement,
        # M30.5: the deterministic gate's authoritative outcome for this
        # SAME proposal - logged for comparison only, never acted on.
        # None when gates were not evaluated (e.g. gate module
        # unavailable) - never fabricated as READY.
        "gate_outcome": gate_result.outcome if gate_result is not None else None,
        "gate_reasons": list(gate_result.reasons) if gate_result is not None else None,
    }


def record_shadow_trace(
    trace: Dict[str, Any], path: str = DEFAULT_SHADOW_LOG_PATH
) -> None:
    """Append-only, best-effort. Never raises - a logging failure must
    never affect the real (already-decided, already-returned) response
    this trace is merely describing after the fact."""
    try:
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(trace, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------
# Single entry point for a live /ask call site (server.py). Builds Turn
# State from the orchestrator's own existing collaborators - never a
# second store, never a change to what the orchestrator itself holds.
# ---------------------------------------------------------------------


def build_turn_state_and_directory(
    *,
    orchestrator: Any,
    session_id: Optional[str],
    user_text: str,
    principal: Any,
) -> Any:
    """Shared setup, extracted from `run_shadow_for_ask` (M30.3) so
    M30.6's canonical execution path reuses the exact same Turn
    State/Directory construction rather than a second copy of it.
    Returns a (TurnStateResult, CapabilityDirectory) tuple. Raises on
    failure - callers are each responsible for their own try/except,
    matching this module's existing per-caller isolation discipline."""
    session = None
    if getattr(orchestrator, "session_manager", None) is not None and session_id:
        session = orchestrator.session_manager.get_session(session_id)

    capability_feasibility = CapabilityFeasibility(
        capability_registry=getattr(orchestrator, "capability_registry", None)
    )
    multi_action_registry = None
    dispatch = getattr(orchestrator, "multi_action_dispatch", None)
    if dispatch is not None:
        multi_action_registry = getattr(dispatch, "registry", None)

    directory = CapabilityDirectory(
        capability_feasibility=capability_feasibility,
        multi_action_registry=multi_action_registry,
    )

    turn_state_result = assemble_turn_state(
        user_text=user_text,
        session_id=session_id,
        principal=principal,
        session=session,
        conversation_history_store=getattr(orchestrator, "conversation_history", None),
        capability_directory=directory,
    )
    return turn_state_result, directory


def run_shadow_for_ask(
    *,
    orchestrator: Any,
    session_id: Optional[str],
    user_text: str,
    principal: Any,
    old_path_result: Dict[str, Any],
    log_path: str = DEFAULT_SHADOW_LOG_PATH,
) -> Optional[Dict[str, Any]]:
    """Top-level, fully isolated: any failure anywhere in this function
    is swallowed here, never propagated - this function's only possible
    effects are (a) appending one line to the shadow log, (b) returning
    a dict for a caller (tests) that wants to inspect it. It never
    touches `old_path_result` or anything the real /ask response reads.
    Returns None on any failure (never raises)."""

    try:
        turn_state_result, directory = build_turn_state_and_directory(
            orchestrator=orchestrator, session_id=session_id,
            user_text=user_text, principal=principal,
        )

        decision = propose_decision(
            turn_state_data=turn_state_result.data,
            capability_directory=directory,
            principal=principal,
            # M30.6 bugfix: this call never passed preselect=True since
            # M30.5A introduced it - shadow-mode logging (and every
            # metric recorded against it) was running the UNPRESELECTED
            # pipeline the whole time, never the one actually validated
            # across M30.5A-D's golden-set evaluations. Canonical
            # execution (below) needs the validated pipeline to be a
            # real precondition for acting on a decision at all, so this
            # is fixed here rather than left to silently diverge further.
            preselect=True,
        )

        active_pointer_kind = turn_state_result.data["active_pointer"]["kind"]
        agreement = classify_agreement(
            old_path_result, decision, directory, active_pointer_kind
        )

        # M30.5: lazy import - decision_gates.py itself imports
        # DecisionOutcome from this module, so importing it back at
        # module load time here would be circular. Deferred to call
        # time instead, exactly like this function's own top-level
        # try/except already treats every collaborator as optional.
        gate_result = None
        try:
            from uri_core.core.decision_gates import evaluate_gates

            gate_result = evaluate_gates(
                decision, capability_directory=directory, principal=principal
            )
        except Exception:
            gate_result = None

        trace = build_shadow_trace(
            session_id=session_id,
            user_text=user_text,
            turn_state_data=turn_state_result.data,
            decision=decision,
            old_path_result=old_path_result,
            agreement=agreement,
            gate_result=gate_result,
        )
        record_shadow_trace(trace, path=log_path)
        return trace
    except Exception:
        return None
