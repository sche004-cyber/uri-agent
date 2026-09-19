"""M30.6: Controlled canonical execution - the FIRST milestone in this
sequence where the Brain Decision Contract + deterministic gate
pipeline (M30.3-M30.5D) is allowed to control real execution, for a
small, explicitly allowlisted set of capabilities only.

Governing constraints, enforced structurally by this module (not by
convention):

    - Default OFF (`URI_ENABLE_DECISION_ENGINE_LIVE` unset). When off,
      `run_canonical_for_ask()` is never reached from server.py at all
      (mirrors `URI_ENABLE_DECISION_ENGINE_SHADOW`'s own gating).
    - Allowlist-only: `CANONICAL_EXECUTION_ALLOWLIST` names the exact
      two capabilities the accepted migration plan's Phase C names
      (`URI_CANONICAL_AGENT_LOOP_MIGRATION_PLAN.md` §4) - Gmail
      (multi-action) and `remember_fact` (legacy). Nothing else can
      ever reach real execution through this module, regardless of
      what the model proposes.
    - Execution is allowed ONLY when the deterministic gate (M30.5's
      `decision_gates.evaluate_gates()`, reused unchanged) returns
      READY. Every other outcome (MISSING_PARAMETER, DISCONNECTED,
      UNAVAILABLE, PERMISSION_DENIED, APPROVAL_REQUIRED, UNSUPPORTED,
      INVALID_PROPOSAL, DEGRADED) falls back to the existing legacy
      `/ask` result untouched - this module never executes on any of
      them, and never invents a deterministic handling path of its own
      for a protected action; approval-required cases flow through the
      existing ApprovalGate/ApprovalStore pending-decision mechanism.
      (M32.1 correction: prior to M32.1 this was true only for the
      legacy `remember_fact` path - a Gmail APPROVAL_REQUIRED outcome
      had no durable ApprovalStore record at all, so it could never be
      resumed on a later turn. M32.1's `_propose_durable_gmail_approval()`
      bridges the Gmail single-action branch to a real, durable
      `ApprovalStore.propose()` call, making this claim true for both
      paths. The multi-step Gmail chain branch is still out of scope -
      see `approval_resumption.py`'s module docstring.)
    - No new invocation mechanics: Gmail actions execute through
      `MultiActionDispatch.dispatch_explicit()`/`dispatch_chain_explicit()`
      (M30.6, `multi_action_dispatch.py`) - thin wrappers around the
      SAME `MultiActionExecutor.execute()`/`execute_chain()` the legacy
      `dispatch()` path already used, with the Brain Decision
      Contract's explicit `capability`/`actions` fields replacing
      `dispatch()`'s own undocumented model-proposal-shape trigger
      (exactly the migration the accepted plan's §1 MultiActionDispatch
      row describes). `remember_fact` executes through the existing,
      unchanged `ApprovalGate.execute_tool()` boundary - the same one
      every legacy capability already uses.
    - Body -> Brain feedback: real execution evidence is packaged into
      the same `{"plan", "execution", "response"}` envelope shape
      `orchestrator.py`'s own legacy branches already build, then
      handed to the orchestrator's own existing, unchanged
      `_draft_narrative_safely()` - which only ever drafts from
      already-decided `execution`/`response` fields and independently
      validates claim-consistency (see that method's own docstring) -
      so a narrative can never claim more than the real evidence
      supports, without a second, new drafting/validation mechanism.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Sequence

from uri_core.core.decision_engine import (
    DEFAULT_SHADOW_LOG_PATH,
    build_turn_state_and_directory,
    propose_decision,
    record_shadow_trace,
)

LIVE_ENV_VAR = "URI_ENABLE_DECISION_ENGINE_LIVE"
WORKFLOW_CONTINUATION_ENV_VAR = "URI_ENABLE_WORKFLOW_CONTINUATION_MODE"
ALLOWLIST_ENV_VAR = "URI_CANONICAL_EXECUTION_ALLOWLIST"

DEFAULT_TELEMETRY_LOG_PATH = os.path.join(
    os.path.dirname(DEFAULT_SHADOW_LOG_PATH) or ".", "canonical_execution_log.jsonl"
)

# M30.8: canonical is the normal authority for every capability exposed by
# the Directory.  ``None`` deliberately means "no restriction".  Operators
# can replace this value with a (possibly empty) frozenset as an emergency
# rollback lever; server.py then uses legacy-first dispatch for that process.
# Keeping the value mutable is intentional: it is an operational kill switch,
# not a second capability registry.
CANONICAL_EXECUTION_ALLOWLIST: Optional[frozenset[str]] = None

# A mode with no real action to execute (conversation, clarification,
# unsupported, workflow_continuation-with-no-capability,
# approval_required - the last already excluded by gate READY) never
# reaches this module's execution branch at all.
EXECUTABLE_MODES = frozenset({"single_action", "multi_action", "workflow_continuation"})


def decision_engine_live_enabled() -> bool:
    """M32 B1.1: canonical is the committed production default - the
    absence of this env var no longer means "off". Set it to "0"
    (any other value than unset/"1" is treated as off) as the
    operational rollback lever when legacy-first handling is needed
    without a redeploy."""
    value = os.environ.get(LIVE_ENV_VAR)
    if value is None:
        return True
    return value == "1"


def workflow_continuation_mode_enabled() -> bool:
    """M32 B1.5: the second cutover flag, decided the same way as B1.1 -
    canonical handles resumed/continuation turns by default. Set to "0"
    to force resumed turns back to legacy without touching the primary
    LIVE_ENV_VAR."""
    value = os.environ.get(WORKFLOW_CONTINUATION_ENV_VAR)
    if value is None:
        return True
    return value == "1"


def _current_allowlist() -> Optional[frozenset[str]]:
    """M32 B1.2: the emergency rollback lever, made runtime-settable.

    ``URI_CANONICAL_EXECUTION_ALLOWLIST``, when set, takes precedence
    over the module-level ``CANONICAL_EXECUTION_ALLOWLIST`` constant -
    a comma-separated list of capability ids narrows canonical
    authority to exactly those, and an explicitly empty string narrows
    it to nothing (full legacy-first fallback), both without a
    redeploy. Unset means "defer to the module constant", preserving
    the pre-B1.2 code-level default of unrestricted (``None``).
    """
    raw = os.environ.get(ALLOWLIST_ENV_VAR)
    if raw is None:
        return CANONICAL_EXECUTION_ALLOWLIST
    raw = raw.strip()
    if not raw:
        return frozenset()
    return frozenset(item.strip() for item in raw.split(",") if item.strip())


def is_allowlisted(capability_id: Optional[str]) -> bool:
    if not capability_id:
        return False
    allowlist = _current_allowlist()
    return allowlist is None or capability_id in allowlist


def canonical_killswitch_enabled() -> bool:
    """Whether an operator narrowed canonical authority for rollback.

    The default ``None`` (module constant, or ``ALLOWLIST_ENV_VAR``
    unset) is unrestricted.  Any concrete set, including an empty one -
    from either the module constant or the runtime env var - is an
    explicit request for legacy-first route handling.
    """
    return _current_allowlist() is not None


def _propose_durable_gmail_approval(
    *, orchestrator: Any, session_id: Optional[str], capability: str,
    action_name: str, bound_inputs: Dict[str, Any],
) -> Optional[str]:
    """M32.1: MultiActionExecutor.execute()'s approval_required outcome
    (executor.py:54-57) is a stateless, per-call boolean check with no
    persistence of its own - unlike the legacy ApprovalGate.execute_tool()
    path, it never wrote anything to ApprovalStore, so an
    "awaiting_approval" Gmail/Drive envelope previously carried no
    action_id at all and could never actually be approved by anything,
    UI button or natural language alike (live-confirmed during M32.1's
    own investigation). Bridges it to the SAME ApprovalStore instance
    ApprovalGate already owns - never a second store instance pointed
    at a different file - so a real, durable, resumable action_id
    exists. Returns None (never raises) on any failure - a proposal
    write failing must degrade to "approval required, but not yet
    resumable" honestly, never break the turn that already succeeded
    in reaching a real, honest APPROVAL_REQUIRED decision."""
    approval_gate = getattr(orchestrator, "approval_gate", None)
    approval_store = getattr(approval_gate, "approval_store", None)
    if approval_store is None:
        return None
    try:
        proposed = approval_store.propose(
            capability_id=capability, arguments=bound_inputs,
            session_id=session_id, action_name=action_name,
        )
        return proposed.action_id
    except Exception:
        return None


def _execute_multi_action(
    contract: Dict[str, Any],
    *,
    capability_id: str,
    orchestrator: Any,
    session_id: Optional[str],
    user_text: str,
    principal: Any,
) -> Optional[Dict[str, Any]]:
    """M33 Batch B: the generalized form of the old `_execute_gmail` -
    any capability registered in `orchestrator.multi_action_dispatch.
    registry` (Gmail by default construction, plus whatever `server.py`'s
    user-context composition has published from Batch A's enabled
    external capabilities) executes through this ONE path. Gmail keeps
    its exact prior behavior because it is still exactly the same
    registered capability id going through the exact same `dispatch_
    explicit`/`dispatch_chain_explicit` calls - through registration,
    not through a `capability_id == "Gmail"` branch."""
    dispatch = getattr(orchestrator, "multi_action_dispatch", None)
    if dispatch is None:
        return None
    actions: List[Dict[str, Any]] = [
        a for a in (contract.get("actions") or []) if isinstance(a, dict) and a.get("name")
    ]
    if not actions:
        return None
    if len(actions) == 1:
        action_name = actions[0]["name"]
        envelope = dispatch.dispatch_explicit(
            capability_id, action_name, actions[0].get("inputs") or {},
            session_id=session_id, user_text=user_text, principal=principal,
        )
        # M32.1: a single-action awaiting_approval result is the ONLY
        # shape this milestone bridges to a durable, resumable action_id
        # - a multi-step chain (the `else` branch below) halting on a
        # mid-chain approval is a materially different problem (which
        # step, preserving already-completed steps) and is explicitly
        # out of this bounded milestone's scope; disclosed, not silently
        # handled. `_propose_durable_gmail_approval` already takes
        # `capability` as a parameter (never hardcodes "Gmail" itself),
        # so this bridge applies identically to any registered capability
        # - only its name is historical.
        if (
            isinstance(envelope, dict)
            and envelope.get("execution", {}).get("status") == "awaiting_approval"
        ):
            bound_inputs = envelope.get("plan", {}).get("inputs") or {}
            action_id = _propose_durable_gmail_approval(
                orchestrator=orchestrator, session_id=session_id, capability=capability_id,
                action_name=action_name, bound_inputs=bound_inputs,
            )
            if action_id is not None:
                envelope = dict(envelope)
                envelope["execution"] = dict(envelope["execution"])
                envelope["execution"]["action_id"] = action_id
                response = envelope.get("response")
                envelope["response"] = (
                    {**response, "action_id": action_id}
                    if isinstance(response, dict) else {"action_id": action_id, "detail": response}
                )
    else:
        # M34 C3.3: an action's own "capability" (already validated
        # against the real directory by `_validate_contract()`, and
        # already independently re-authorized per its OWN capability by
        # `evaluate_gates()`'s per-group pipeline before this function
        # is ever reached) takes precedence; an action with none keeps
        # inheriting the contract's top-level `capability_id` exactly as
        # before this milestone - so a single-capability chain builds
        # the identical `steps` list it always did.
        steps = [
            {
                "capability": (a.get("capability") if isinstance(a.get("capability"), str) and a.get("capability") else capability_id),
                "action": a["name"],
                "inputs": a.get("inputs") or {},
            }
            for a in actions
        ]
        envelope = dispatch.dispatch_chain_explicit(
            steps, session_id=session_id, principal=principal,
        )
    if envelope is None:
        return None
    envelope = dict(envelope)
    envelope.pop("handled", None)
    return envelope


def _execute_remember_fact(
    *,
    orchestrator: Any,
    session_id: Optional[str],
    user_text: str,
    principal: Any,
) -> Optional[Dict[str, Any]]:
    approval_gate = getattr(orchestrator, "approval_gate", None)
    if approval_gate is None:
        return None
    from uri_core.core.dispatcher import real_tool_status

    dispatch_result = approval_gate.execute_tool(
        "remember_fact", session_id=session_id, request_text=user_text, principal=principal,
    )
    outer_status = dispatch_result.get("status")
    if outer_status == "awaiting_approval":
        # Structurally unreachable today (remember_fact's registry
        # entry declares approval_requirement="none", and the gate
        # would have already returned APPROVAL_REQUIRED, never READY,
        # for a capability that did require it) - handled honestly
        # anyway rather than assumed impossible.
        return {
            "status": "success",
            "plan": {"status": "capability_selected", "capability": "remember_fact", "action": "remember_fact", "source": "legacy"},
            "execution": {"status": "awaiting_approval", "capability": "remember_fact", "action": "remember_fact"},
            "response": dispatch_result,
        }
    tool_status = real_tool_status(dispatch_result)
    envelope_status = "success" if tool_status in {"success", "ok"} else "unavailable"
    return {
        "status": envelope_status,
        "plan": {"status": "capability_selected", "capability": "remember_fact", "action": "remember_fact", "source": "legacy"},
        "execution": {"status": tool_status, "capability": "remember_fact", "action": "remember_fact", "raw_status": outer_status},
        "response": dispatch_result.get("data", dispatch_result),
    }


def _execute_legacy_capability(
    contract: Dict[str, Any],
    *,
    orchestrator: Any,
    session_id: Optional[str],
    user_text: str,
    principal: Any,
) -> Optional[Dict[str, Any]]:
    """Canonical entry to the existing legacy ToolDispatcher boundary.

    This does not recreate planning or approval logic.  It only lets a
    Directory-validated, explicit single-action contract reach the same
    ApprovalGate that owns legacy tool execution today.
    """
    capability_id = contract.get("capability")
    actions = contract.get("actions") or []
    if (
        not isinstance(capability_id, str)
        or len(actions) != 1
        or not isinstance(actions[0], dict)
        or actions[0].get("name") != capability_id
    ):
        return None
    approval_gate = getattr(orchestrator, "approval_gate", None)
    if approval_gate is None:
        return None
    result = approval_gate.execute_tool(
        capability_id, session_id=session_id, request_text=user_text, principal=principal,
    )
    status = result.get("status")
    if status == "awaiting_approval":
        execution_status = "awaiting_approval"
    else:
        from uri_core.core.dispatcher import real_tool_status
        execution_status = real_tool_status(result)
    return {
        "status": "success" if execution_status in {"success", "ok", "awaiting_approval"} else "unavailable",
        "plan": {"status": "capability_selected", "capability": capability_id, "action": capability_id, "source": "canonical"},
        "execution": {"status": execution_status, "capability": capability_id, "action": capability_id},
        "response": result.get("data", result),
    }


def decide_fallback_reason(
    *,
    gate_outcome: str,
    capability_id: Optional[str],
    mode: Optional[str],
    reasons: Sequence[str] = (),
    capability_ids: Optional[Sequence[str]] = None,
) -> Optional[str]:
    """Pure, deterministic, model-free: the exact eligibility check
    `run_canonical_for_ask()` applies once a Decision Contract and its
    real GateResult already exist. Returns None (proceed to execute)
    only when the gate is READY, the capability is explicitly
    allowlisted, and the mode is one that has a real action to run -
    otherwise names the specific reason execution never happens, for
    both correctness and telemetry. Extracted as its own function so
    every non-READY outcome's fallback behavior is unit-testable
    without any model or orchestrator involved.

    `reasons` is the GateResult's own `reasons` list, inspected only for
    one specific, already-uniquely-named string:
    "false_unsupported_claim_rejected_by_directory" - decision_gates.py's
    own real, decided verdict that the model's "unsupported" claim is
    false because a plausibly-matching, available capability exists. That
    verdict is a completed canonical decision, not an engine/proposal
    defect - it happens to reuse the INVALID_PROPOSAL outcome value, but
    dispatching it as an engine failure would fall back to legacy for a
    turn canonical already decided correctly. Every other INVALID_PROPOSAL
    cause (malformed contract, unknown capability/action, a continuation
    with no active pointer, a mode requiring a capability that named none)
    is unaffected and still falls back exactly as before.

    `capability_ids` (M34 C3.3, optional, additive): for a heterogeneous
    `multi_action` proposal, EVERY distinct effective capability the
    proposal can dispatch must be supplied by the caller's canonical
    contract calculation and be allowlisted. Omitted (every caller before
    this milestone, and every single-capability proposal after it) falls
    back to checking exactly `capability_id` alone. This closes the
    per-action-override authority gap: `URI_CANONICAL_EXECUTION_ALLOWLIST`
    narrows canonical authority for EVERY capability a proposal can reach,
    not only the contract's top-level one."""
    if gate_outcome == "INVALID_PROPOSAL" and "false_unsupported_claim_rejected_by_directory" in reasons:
        return None
    if gate_outcome in {"INVALID_PROPOSAL", "DEGRADED"}:
        return f"engine_failure:{gate_outcome}"
    # M32.1: APPROVAL_REQUIRED now also reaches _execute_canonical() (see
    # run_canonical_for_ask's own dispatch condition below), so it must
    # pass through the SAME executable-mode/workflow-continuation/
    # allowlist checks READY already does - this function previously
    # returned None for APPROVAL_REQUIRED before ever reaching those
    # checks, which was safe only because APPROVAL_REQUIRED never
    # dispatched at all. Widening the outcome set here without this
    # would have silently skipped the allowlist/killswitch check for
    # every approval-required capability.
    if gate_outcome not in {"READY", "APPROVAL_REQUIRED"}:
        return None
    if mode not in EXECUTABLE_MODES:
        return None
    if mode == "workflow_continuation" and not workflow_continuation_mode_enabled():
        return "mode_not_executable:workflow_continuation"
    ids_to_check = list(capability_ids) if capability_ids is not None else [capability_id]
    if not all(is_allowlisted(one_id) for one_id in ids_to_check):
        return "canonical_killswitch_not_allowlisted"
    return None


def effective_capability_ids(contract: Dict[str, Any]) -> List[Optional[str]]:
    """Return every capability an execution contract can actually reach.

    Derived at the execution boundary rather than from GateResult rollups:
    gates report evaluation detail, while the allowlist must cover every
    action dispatch can address. Actions without an override retain the
    historical top-level identity. A no-action contract retains its
    pre-C3.3 top-level-only behavior.
    """
    top_level = contract.get("capability")
    actions = [action for action in (contract.get("actions") or []) if isinstance(action, dict)]
    raw_ids = [
        action.get("capability")
        if isinstance(action.get("capability"), str) and action.get("capability")
        else top_level
        for action in actions
    ] or [top_level]
    return list(dict.fromkeys(raw_ids))


def _is_heterogeneous_contract(contract: Dict[str, Any]) -> bool:
    return len(set(effective_capability_ids(contract))) > 1


def _canonical_nonexecution_envelope(
    contract: Dict[str, Any], gate_result: Any,
) -> Dict[str, Any]:
    """Return a truthful terminal response for a valid non-execution turn.

    These outcomes are decisions, not failures.  In particular they must not
    be re-routed through the legacy planner simply because they are less
    convenient than an execution result.
    """
    outcome = getattr(gate_result, "outcome", "READY")
    missing = getattr(gate_result, "missing_field", None)
    clarification = contract.get("clarification")
    if outcome == "MISSING_PARAMETER" or contract.get("mode") == "clarification":
        message = clarification or (
            f"Please provide {missing}." if missing else "Please provide the missing information."
        )
        status, execution_status = "awaiting_user_response", "not_executed"
    elif outcome == "APPROVAL_REQUIRED" or contract.get("mode") == "approval_required":
        message = "This action requires your approval before it can run."
        status, execution_status = "approval_required", "not_executed"
    elif outcome == "DISCONNECTED":
        message = "That capability is not connected right now."
        status, execution_status = "unavailable", "not_executed"
    elif outcome in {"UNSUPPORTED", "UNAVAILABLE", "PERMISSION_DENIED"} or contract.get("mode") == "unsupported":
        message = contract.get("unsupported_reason") or "URI cannot perform that request with an available capability."
        status, execution_status = "unavailable", "not_executed"
    else:
        message = contract.get("reason") or "I can help with that."
        status, execution_status = "success", "not_applicable"
    plan: Dict[str, Any] = {
        "status": "canonical_non_execution",
        "mode": contract.get("mode"),
        "capability": contract.get("capability"),
        "gate_outcome": outcome,
    }
    # M34 C3.3: for a heterogeneous proposal, report exactly which
    # capability/action(s) blocked the chain (the real per-group
    # GateResults, never re-derived) rather than only the aggregate
    # outcome - so a denial or approval requirement on one action in a
    # multi-capability chain is never reported as an undifferentiated,
    # unexplained failure of the whole turn.
    sub_results = getattr(gate_result, "sub_results", None) or []
    if sub_results:
        plan["per_capability"] = [
            {"capability_id": sub.capability_id, "outcome": sub.outcome, "action_names": list(sub.action_names)}
            for sub in sub_results
        ]
    return {
        "status": status,
        "canonical_outcome": outcome,
        "plan": plan,
        "execution": {"status": execution_status, "capability": contract.get("capability")},
        "response": {"message": message},
    }


def _execute_canonical(
    contract: Dict[str, Any],
    *,
    orchestrator: Any,
    session_id: Optional[str],
    user_text: str,
    principal: Any,
) -> Optional[Dict[str, Any]]:
    capability_id = contract.get("capability")
    # M33 Batch B: registry lookup, not a `capability_id == "Gmail"`
    # branch - Gmail is simply always present in `dispatch.registry` by
    # its own default construction (`MultiActionCapabilityRegistry([Gmail
    # Capability()])`, unchanged); any external capability `server.py`'s
    # user-context composition has published lives in the exact same
    # registry and is reached by the exact same generalized call below.
    dispatch = getattr(orchestrator, "multi_action_dispatch", None)
    registry = getattr(dispatch, "registry", None)
    if (
        isinstance(capability_id, str)
        and registry is not None
        and registry.get_capability(capability_id) is not None
    ):
        # M34 C3.3: a heterogeneous proposal's per-action "capability"
        # overrides only ever reach `dispatch_chain_explicit()` - the
        # ONE existing mechanism that already authorizes and executes a
        # real per-step capability. If any referenced capability (top-
        # level or per-action) is NOT also registered in this same
        # `dispatch.registry`, no existing execution boundary can run
        # this specific mix safely (a legacy single-tool capability like
        # `remember_fact` has no chain concept at all) - decline here
        # (fall back to legacy for the whole turn, exactly like any
        # other `execution_dispatch_returned_none` case) rather than
        # inventing a new mixed-boundary execution path or silently
        # dropping/misrouting an action the model explicitly named.
        referenced_ids = {capability_id}
        for action in contract.get("actions") or []:
            if isinstance(action, dict):
                named = action.get("capability")
                if isinstance(named, str) and named:
                    referenced_ids.add(named)
        if len(referenced_ids) > 1 and not all(
            registry.get_capability(one_id) is not None for one_id in referenced_ids
        ):
            return None
        return _execute_multi_action(
            contract, capability_id=capability_id, orchestrator=orchestrator,
            session_id=session_id, user_text=user_text, principal=principal,
        )
    if capability_id == "remember_fact":
        return _execute_remember_fact(
            orchestrator=orchestrator, session_id=session_id,
            user_text=user_text, principal=principal,
        )
    return _execute_legacy_capability(
        contract, orchestrator=orchestrator, session_id=session_id,
        user_text=user_text, principal=principal,
    )


def build_canonical_telemetry(
    *,
    session_id: Optional[str],
    user_text: str,
    contract: Dict[str, Any],
    gate_result: Any,
    recall_at_5: Optional[bool],
    canonical_attempted: bool,
    envelope: Optional[Dict[str, Any]],
    fallback_used: bool,
    fallback_reason: Optional[str],
) -> Dict[str, Any]:
    """Privacy-safe by construction, mirroring `build_shadow_trace`'s
    own discipline: no raw user text, no raw tool output content - only
    status/id/enum fields already treated as non-sensitive elsewhere in
    this codebase."""
    execution_evidence_returned = bool(
        canonical_attempted and envelope is not None and envelope.get("execution") is not None
    )
    grounded_final_response = bool(
        canonical_attempted and envelope is not None and envelope.get("response") is not None
    )
    return {
        "timestamp": time.time(),
        "session_id": session_id,
        "user_text_length_bucket": len(user_text) // 20 * 20 if user_text else 0,
        "canonical_mode": contract.get("mode"),
        "selected_capability": contract.get("capability"),
        "selected_actions": [
            a.get("name") for a in (contract.get("actions") or []) if isinstance(a, dict)
        ],
        # M34 C3.3: per-action capability identity, additive - {action:
        # capability} for every action, falling back to the contract's
        # top-level `capability` for an action with no override of its
        # own (every contract before this milestone, and every single-
        # capability one after it, so `selected_capability` above
        # already told the whole story for those - this field's real
        # audit value appears only once a heterogeneous proposal exists).
        "action_capabilities": [
            {
                "action": a.get("name"),
                "capability": (
                    a.get("capability")
                    if isinstance(a.get("capability"), str) and a.get("capability")
                    else contract.get("capability")
                ),
            }
            for a in (contract.get("actions") or []) if isinstance(a, dict)
        ],
        "candidate_recall_at_5": recall_at_5,
        "gate_outcome": getattr(gate_result, "outcome", None),
        "canonical_execution_attempted": canonical_attempted,
        "canonical_execution_result": (envelope or {}).get("status") if envelope else None,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "execution_evidence_returned": execution_evidence_returned,
        "grounded_final_response": grounded_final_response,
    }


def record_canonical_telemetry(
    telemetry: Dict[str, Any], path: str = DEFAULT_TELEMETRY_LOG_PATH
) -> None:
    # Reuses `record_shadow_trace`'s exact append-only, best-effort
    # semantics - never raises, never affects the real response.
    record_shadow_trace(telemetry, path=path)


def run_canonical_for_ask(
    *,
    orchestrator: Any,
    session_id: Optional[str],
    user_text: str,
    principal: Any,
    personalization_context: Any = None,
    log_path: str = DEFAULT_TELEMETRY_LOG_PATH,
    decision_observer: Any = None,
) -> Optional[Dict[str, Any]]:
    """The single M30.6 entry point for a live `/ask` call site
    (`server.py`). Returns a full `{"status", "session_id", "execution",
    "response", ...}` envelope - the SAME shape `/ask` already relays to
    the client - only when canonical execution actually ran for an
    allowlisted, gate-READY proposal; returns None in every other case
    (invalid contract, non-READY gate, non-allowlisted capability,
    non-executable mode, or any internal failure), so the caller's
    existing legacy `result` is used completely unchanged. Never
    raises."""
    from uri_core.core.decision_gates import evaluate_gates
    from uri_core.core.decision_engine import candidate_recall_at_k

    contract: Dict[str, Any] = {}
    gate_result = None
    recall_at_5 = None
    envelope: Optional[Dict[str, Any]] = None
    fallback_reason: Optional[str] = None
    canonical_attempted = False

    try:
        turn_state_result, directory = build_turn_state_and_directory(
            orchestrator=orchestrator, session_id=session_id,
            user_text=user_text, principal=principal,
        )

        decision = propose_decision(
            turn_state_data=turn_state_result.data,
            capability_directory=directory,
            principal=principal,
            preselect=True,
        )

        if decision.status != "ok" or decision.contract is None:
            detail = str(decision.invalid_reason or decision.status)
            terminal = "provider" in detail.lower() and "unavailable" in detail.lower()
            fallback_reason = (
                "MODEL_TERMINALLY_UNAVAILABLE" if terminal
                else f"engine_failure:INVALID_PROPOSAL:{detail}"
            )
        else:
            contract = decision.contract
            gate_result = evaluate_gates(
                decision, capability_directory=directory, principal=principal,
                turn_state_data=turn_state_result.data,
            )
            if decision_observer is not None:
                try:
                    decision_observer(contract, gate_result)
                except Exception:
                    pass
            recall_at_5 = candidate_recall_at_k(
                turn_state_result.data, directory, contract.get("capability"), k=5
            )

            capability_id = contract.get("capability")
            mode = contract.get("mode")

            # M34 C3.3: check every capability dispatch could actually
            # reach, including an override shape that happens to form only
            # one gate group. GateResult sub-results are evidence, not the
            # allowlist authority source.
            capability_ids = effective_capability_ids(contract)

            fallback_reason = decide_fallback_reason(
                gate_outcome=gate_result.outcome, capability_id=capability_id, mode=mode,
                reasons=getattr(gate_result, "reasons", ()),
                capability_ids=capability_ids,
            )
            # M32.1: APPROVAL_REQUIRED now also reaches _execute_canonical()
            # - previously only READY did, which meant an approval-required
            # capability never reached ApprovalGate/ApprovalStore (or the
            # Gmail bridge above) at all and could never be durably
            # proposed. decide_fallback_reason() above already applies the
            # same executable-mode/allowlist gate to this outcome now, so
            # this widening cannot reach an un-allowlisted capability.
            if (
                fallback_reason is None
                and gate_result.outcome in ("READY", "APPROVAL_REQUIRED")
                and not (
                    gate_result.outcome == "APPROVAL_REQUIRED"
                    and _is_heterogeneous_contract(contract)
                )
                and mode in EXECUTABLE_MODES
            ):
                canonical_attempted = True
                envelope = _execute_canonical(
                    contract, orchestrator=orchestrator, session_id=session_id,
                    user_text=user_text, principal=principal,
                )
                if envelope is None:
                    fallback_reason = "execution_dispatch_returned_none"
            elif fallback_reason is None:
                envelope = _canonical_nonexecution_envelope(contract, gate_result)
    except Exception as exc:
        fallback_reason = f"canonical_execution_error:{exc}"
        envelope = None

    fallback_required = fallback_reason is not None
    telemetry = build_canonical_telemetry(
        session_id=session_id, user_text=user_text, contract=contract,
        gate_result=gate_result, recall_at_5=recall_at_5,
        canonical_attempted=canonical_attempted, envelope=envelope,
        fallback_used=fallback_required, fallback_reason=fallback_reason,
    )
    record_canonical_telemetry(telemetry, path=log_path)

    if fallback_required:
        return {
            "_canonical_fallback": True,
            "fallback_reason": fallback_reason,
            "gate_outcome": getattr(gate_result, "outcome", "INVALID_PROPOSAL"),
        }

    envelope = dict(envelope)
    envelope["session_id"] = session_id
    envelope.setdefault("semantic_analysis", None)
    envelope.setdefault("error", None)

    # M32 B1.6: `_draft_narrative_safely` already guarantees (by its own
    # docstring and internal except clauses) that it never raises - any
    # drafting/validation failure calls `mark_narrative_unavailable` on
    # `envelope` itself before returning. Execution has already happened
    # by this point, so falling back to legacy here would risk a second,
    # duplicate dispatch of an already-completed side effect - not a
    # safe or correct fix. The residual gap this closes is narrower:
    # if `_draft_narrative_safely` were ever to raise anyway (a defect
    # in that guarantee, not something to assume away), the previous
    # bare `except: pass` left `envelope` with no narrative and no
    # honest reason at all. This is defense in depth, not a new
    # fallback path.
    try:
        orchestrator._draft_narrative_safely(
            user_text=user_text, response=envelope,
            personalization_context=personalization_context, session_id=session_id,
        )
    except Exception as exc:
        try:
            from uri_core.core.response_drafting import mark_narrative_unavailable

            mark_narrative_unavailable(envelope, exc, principal)
        except Exception:
            pass

    try:
        orchestrator._persist_session(session_id)
    except Exception:
        pass

    return envelope
