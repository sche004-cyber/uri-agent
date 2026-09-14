"""M30.5: Deterministic Decision Gates - the verification layer between
a proposed Brain Decision Contract (decision_engine.py, M30.3) and any
future execution (M30.6+, not authorized yet).

Core principle, unchanged from every prior milestone in this sequence:
the model PROPOSES, this module ESTABLISHES RUNTIME TRUTH. Every gate
below reuses an already-existing, already-tested authority - none of
them are a second, competing implementation:

    - CapabilityDirectory (M30.2), itself already wrapping
      CapabilityFeasibility (legacy, connection-aware since M20) and
      MultiActionCapabilityRegistry (M27) - used for existence,
      availability, and schema truth.
    - capability_relevance.py (M30.5A) for the Unsupported Gate's "does
      anything even plausibly match" check - a directory-derived,
      generic-term-aware scorer (M30.5's own finding: M27's bare
      CapabilityDiscoveryEngine word-overlap check produced a false
      match from one shared generic word - see that module's docstring).
    - GmailCapability's own real, live `availability_check` (M27) -
      surfaced here at Level 2 for the first time (CapabilityDirectory.
      describe() previously dropped it - a real, in-scope gap this
      milestone closes, since the Connection/Availability gate cannot
      do its job without it).

Nothing in this module executes anything. `evaluate_gates()` returns a
GateResult describing what WOULD be safe to do - callers (tests, and
the M30.3 shadow hook, extended here to log gate results alongside
Brain proposals) decide what to do with that, and nothing today acts
on it in production.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from uri_core.core.capability_directory import CapabilityDirectory
from uri_core.core.capability_relevance import plausible_matches
from uri_core.core.decision_engine import DecisionOutcome


WORKFLOW_CONTINUATION_ENV_VAR = "URI_ENABLE_WORKFLOW_CONTINUATION_MODE"


def workflow_continuation_mode_enabled() -> bool:
    """True only for the explicitly enabled M30.7 continuation path."""
    import os
    return os.environ.get(WORKFLOW_CONTINUATION_ENV_VAR) == "1"


GATE_OUTCOMES = {
    "READY",
    "MISSING_PARAMETER",
    "DISCONNECTED",
    "UNAVAILABLE",
    "PERMISSION_DENIED",
    "APPROVAL_REQUIRED",
    "UNSUPPORTED",
    "INVALID_PROPOSAL",
    "DEGRADED",
}


@dataclass(frozen=True)
class GateResult:
    outcome: str
    capability_id: Optional[str]
    action_names: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    missing_field: Optional[str] = None
    expected_type: Optional[str] = None
    # Populated whenever the selected (or claimed-unsupported) identity
    # overlaps another registered capability - visible for review,
    # never silently resolved by picking one (per the accepted M30.5
    # scope: "do not solve overlap by deleting legacy capabilities yet").
    overlap_candidates: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "outcome": self.outcome,
            "capability_id": self.capability_id,
            "action_names": list(self.action_names),
            "reasons": list(self.reasons),
            "missing_field": self.missing_field,
            "expected_type": self.expected_type,
            "overlap_candidates": list(self.overlap_candidates),
        }


def _plausible_match_exists(directory: CapabilityDirectory, goal_text: str) -> List[str]:
    """M30.5A: tightened - requires at least one DISCRIMINATING shared
    term (uri_core.core.capability_relevance), not just any shared
    word. M30.5's own live finding was that a bare word-overlap check
    (M27's CapabilityDiscoveryEngine, used directly) treated a single
    generic shared word ("search") as a plausible Gmail match for an
    unrelated "job search" goal. Still fully generic and directory-
    derived - never a hardcoded phrase (see capability_relevance.py's
    own module docstring)."""
    try:
        candidates = plausible_matches(directory, goal_text or "", limit=5)
    except Exception:
        return []
    return [c["capability"] for c in candidates]


def _availability_outcome(
    entry: Dict[str, Any],
    capability_id: str,
    action_names: List[str],
    overlap_ids: List[str],
) -> Optional[GateResult]:
    """Gate 5's own classification, extracted verbatim so it can be
    reused from a second call site (the "no capability named" branch's
    plausible-match check, decision_gates.py's own scenario-2 repair)
    without duplicating it. Returns None when the capability is
    available (caller falls through to its own next step); a
    `GateResult` otherwise. Purely generic - reads only the same
    directory-derived `availability_known`/`available`/
    `availability_reason` fields every capability already exposes via
    `CapabilityDirectory.describe()`, never anything capability-
    specific."""
    availability_known = entry.get("availability_known")
    available = entry.get("available")
    availability_reason = entry.get("availability_reason")

    if availability_known and available is False:
        if availability_reason == "not_implemented":
            # CapabilityFeasibility's own two-reason distinction (M20),
            # reused directly: no adapter exists at all - this is a
            # real UNSUPPORTED, not a connection gap.
            return GateResult(
                outcome="UNSUPPORTED", capability_id=capability_id, action_names=action_names,
                reasons=["capability_not_implemented"], overlap_candidates=overlap_ids,
            )
        return GateResult(
            outcome="DISCONNECTED", capability_id=capability_id, action_names=action_names,
            reasons=[availability_reason or "unavailable"], overlap_candidates=overlap_ids,
        )

    if not availability_known:
        # Honest UNKNOWN, never inferred as connected (M27 gap, closed
        # partially this milestone via describe()'s real Level-2
        # check_availability() surfacing - see capability_directory.py.
        # Still reachable here if a capability declares no
        # availability_check at all.
        return GateResult(
            outcome="UNAVAILABLE", capability_id=capability_id, action_names=action_names,
            reasons=["availability_unknown_for_this_capability"], overlap_candidates=overlap_ids,
        )

    return None


def _overlap_candidates_for(directory: CapabilityDirectory, capability_id: str) -> List[str]:
    """Reuses CapabilityDirectory.overlaps() (M30.2) - never a second
    overlap-detection implementation."""
    try:
        overlaps = directory.overlaps()
    except Exception:
        return []
    ids: List[str] = []
    for record in overlaps:
        if record.get("legacy_id") == capability_id:
            ids.append(record.get("multi_action_id"))
        elif record.get("multi_action_id") == capability_id:
            ids.append(record.get("legacy_id"))
    return [i for i in ids if i]


def evaluate_gates(
    decision: DecisionOutcome,
    *,
    capability_directory: Optional[CapabilityDirectory],
    principal: Any = None,
    permission_checker: Optional[Callable[[str, Any], bool]] = None,
    turn_state_data: Optional[Dict[str, Any]] = None,
) -> GateResult:
    """The full deterministic pipeline (Stage 2/3 §6, accepted order).
    Never executes anything, never raises - degrades to DEGRADED/
    INVALID_PROPOSAL on any internal failure, matching this codebase's
    universal fail-safe-not-fail-open discipline for authority-adjacent
    code (unlike a pure context-assembly module, a gate's OWN failure
    must never silently read as READY)."""

    # 1. CONTRACT VALIDITY
    if decision.status != "ok" or decision.contract is None:
        return GateResult(
            outcome="INVALID_PROPOSAL",
            capability_id=None,
            reasons=[decision.invalid_reason or f"decision_status:{decision.status}"],
        )

    try:
        return _evaluate_gates_inner(
            decision, capability_directory=capability_directory,
            principal=principal, permission_checker=permission_checker,
            turn_state_data=turn_state_data,
        )
    except Exception as exc:
        return GateResult(
            outcome="DEGRADED", capability_id=decision.contract.get("capability"),
            reasons=[f"gate_evaluation_error:{exc}"],
        )


def _evaluate_gates_inner(
    decision: DecisionOutcome,
    *,
    capability_directory: Optional[CapabilityDirectory],
    principal: Any,
    permission_checker: Optional[Callable[[str, Any], bool]],
    turn_state_data: Optional[Dict[str, Any]],
) -> GateResult:
    contract = decision.contract
    mode = contract.get("mode")
    capability_id = contract.get("capability")
    actions = contract.get("actions") or []
    action_names = [a.get("name") for a in actions if isinstance(a, dict) and a.get("name")]
    goal_text = str(contract.get("goal") or "")

    # M30.7: a continuation is executable only when an enabled, durable
    # active pointer supplies (or confirms) the concrete paused action.
    # This enriches the untrusted contract before it enters the exact same
    # existence/availability/schema/permission/approval pipeline below.
    if mode == "workflow_continuation" and workflow_continuation_mode_enabled():
        active_pointer = (turn_state_data or {}).get("active_pointer") or {}
        if active_pointer.get("kind") == "none":
            return GateResult(
                outcome="INVALID_PROPOSAL", capability_id=None,
                reasons=["continuation_without_active_pointer"],
            )
        capability_id = capability_id or active_pointer.get("capability_id")
        if not capability_id:
            return GateResult(
                outcome="INVALID_PROPOSAL", capability_id=None,
                reasons=["continuation_no_durable_capability"],
            )
        known_inputs = active_pointer.get("known_inputs") or {}
        missing_field = active_pointer.get("missing_field")
        supplied_value = ((turn_state_data or {}).get("turn") or {}).get("user_text")
        if not action_names and active_pointer.get("action"):
            actions = [{"name": active_pointer["action"], "inputs": {}}]
        enriched_actions = []
        for action in actions:
            if not isinstance(action, dict) or not action.get("name"):
                continue
            enriched = dict(action)
            inputs = dict(known_inputs)
            inputs.update(action.get("inputs") or {})
            if missing_field and supplied_value and missing_field not in inputs:
                inputs[missing_field] = supplied_value
            enriched["inputs"] = inputs
            enriched_actions.append(enriched)
        actions = enriched_actions
        action_names = [a["name"] for a in actions]
        contract["capability"] = capability_id
        contract["actions"] = actions

    # ---- No capability named: only the Unsupported Gate has real work to do. ----
    if capability_id is None:
        matches: List[str] = []
        if capability_directory is not None:
            matches = _plausible_match_exists(capability_directory, goal_text)

        if mode == "unsupported":
            if matches:
                # Scenario 2 repair: before rejecting the model's own
                # "unsupported" claim as merely false, ask the SAME
                # generic connection gate below what the top matched
                # candidate's real runtime state actually is - never
                # let a text-overlap-only verdict stand in for the
                # real, deterministic connection truth. A capability
                # that is genuinely disconnected must surface as
                # DISCONNECTED (with its real capability_id, not null),
                # not as a generic INVALID_PROPOSAL - regardless of how
                # the model framed its own proposal.
                top_candidate = matches[0]
                candidate_entry = (
                    capability_directory.describe(top_candidate)
                    if capability_directory is not None
                    else None
                )
                if candidate_entry is not None:
                    candidate_outcome = _availability_outcome(
                        candidate_entry, top_candidate, action_names, matches,
                    )
                    if candidate_outcome is not None:
                        return candidate_outcome

                # 8. UNSUPPORTED GATE, model corrected: the model's own
                # unsupported claim is rejected - a real candidate
                # exists, and it is genuinely available (the check
                # above found nothing wrong with its connection state).
                # Mandatory M30.5 case 1's Gmail-unread equivalent for
                # the no-capability-named shape.
                return GateResult(
                    outcome="INVALID_PROPOSAL", capability_id=None, action_names=action_names,
                    reasons=["false_unsupported_claim_rejected_by_directory"],
                    overlap_candidates=matches,
                )
            return GateResult(
                outcome="UNSUPPORTED", capability_id=None, action_names=action_names,
                reasons=["no_plausible_capability_match"],
            )

        if mode == "clarification":
            if capability_directory is not None and not matches:
                # 8. UNSUPPORTED GATE, model corrected the other way:
                # nothing could ever satisfy this - a clarification loop
                # would never resolve it (mandatory M30.5 case 2's shape
                # for the "no capability named" case).
                return GateResult(
                    outcome="UNSUPPORTED", capability_id=None, action_names=action_names,
                    reasons=["clarification_proposed_but_nothing_could_ever_satisfy_this_goal"],
                )
            return GateResult(
                outcome="READY", capability_id=None, action_names=action_names,
                reasons=["clarification_pending_no_capability_named"],
            )

        if mode == "conversation":
            return GateResult(outcome="READY", capability_id=None, reasons=["no_capability_required"])

        if mode == "workflow_continuation":
            return GateResult(outcome="READY", capability_id=None, reasons=["continuation_no_capability_named"])

        return GateResult(
            outcome="INVALID_PROPOSAL", capability_id=None, action_names=action_names,
            reasons=[f"mode_{mode}_requires_a_capability_reference"],
        )

    # ---- A capability WAS named: run the full pipeline against it. ----
    if capability_directory is None:
        return GateResult(
            outcome="DEGRADED", capability_id=capability_id, action_names=action_names,
            reasons=["no_capability_directory_available_to_verify_against"],
        )

    # 2. CAPABILITY EXISTENCE
    entry = capability_directory.describe(capability_id)
    overlap_ids = _overlap_candidates_for(capability_directory, capability_id)
    if entry is None:
        return GateResult(
            outcome="INVALID_PROPOSAL", capability_id=capability_id, action_names=action_names,
            reasons=["unknown_capability"], overlap_candidates=overlap_ids,
        )

    # 3. ACTION EXISTENCE
    known_actions = set(entry.get("actions") or [])
    unknown = [a for a in action_names if known_actions and a not in known_actions]
    if unknown:
        return GateResult(
            outcome="INVALID_PROPOSAL", capability_id=capability_id, action_names=action_names,
            reasons=[f"unknown_action:{a}" for a in unknown], overlap_candidates=overlap_ids,
        )

    # 5. AVAILABILITY / CONNECTION (before completeness - an
    # unavailable capability's parameters are moot; distinct outcomes
    # per the accepted scope, never collapsed).
    availability_outcome = _availability_outcome(entry, capability_id, action_names, overlap_ids)
    if availability_outcome is not None:
        return availability_outcome

    # 4. COMPLETENESS / MISSING PARAMETER - schema-based, only where a
    # real per-action schema exists (multi-action capabilities today;
    # legacy capabilities have none yet, per the M30.2 completion
    # report's own honest gap - never fabricated here either).
    action_schemas = entry.get("action_schemas") or {}
    for action in actions:
        name = action.get("name") if isinstance(action, dict) else None
        inputs = action.get("inputs") or {} if isinstance(action, dict) else {}
        schema = action_schemas.get(name) if name else None
        if not schema:
            continue
        required = schema.get("required") or []
        missing = [field_name for field_name in required if field_name not in inputs]
        if missing:
            first_missing = missing[0]
            parameters = schema.get("parameters") or {}
            expected_type = (parameters.get(first_missing) or {}).get("type")
            return GateResult(
                outcome="MISSING_PARAMETER", capability_id=capability_id, action_names=action_names,
                reasons=[f"missing_required_input:{first_missing}"],
                missing_field=first_missing, expected_type=expected_type,
                overlap_candidates=overlap_ids,
            )

    # 6. PERMISSION
    if entry.get("permission_required"):
        allowed = True
        if permission_checker is not None:
            try:
                allowed = bool(permission_checker(capability_id, principal))
            except Exception:
                allowed = False
        if not allowed:
            return GateResult(
                outcome="PERMISSION_DENIED", capability_id=capability_id, action_names=action_names,
                reasons=["permission_not_granted"], overlap_candidates=overlap_ids,
            )

    # 7. APPROVAL - runtime metadata is authoritative regardless of the
    # model's own requires_approval claim (never read here at all).
    approval_required = entry.get("approval_required")
    if approval_required is None:
        approval_required = any(
            (action_schemas.get(name) or {}).get("approval_requirement") == "user_approval_required"
            for name in action_names
        )
    if approval_required:
        return GateResult(
            outcome="APPROVAL_REQUIRED", capability_id=capability_id, action_names=action_names,
            reasons=["capability_or_action_requires_approval"], overlap_candidates=overlap_ids,
        )

    # 9. EXECUTION READINESS - every gate passed; still never executed
    # here, per the accepted M30.5 scope.
    return GateResult(
        outcome="READY", capability_id=capability_id, action_names=action_names,
        reasons=["all_gates_passed"], overlap_candidates=overlap_ids,
    )
