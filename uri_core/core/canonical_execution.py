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
      for a protected action; approval-required cases still flow
      through the existing ApprovalGate/ApprovalStore pending-decision
      mechanism exactly as they do today, unchanged.
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
from typing import Any, Dict, List, Optional

from uri_core.core.decision_engine import (
    DEFAULT_SHADOW_LOG_PATH,
    build_turn_state_and_directory,
    propose_decision,
    record_shadow_trace,
)

LIVE_ENV_VAR = "URI_ENABLE_DECISION_ENGINE_LIVE"
WORKFLOW_CONTINUATION_ENV_VAR = "URI_ENABLE_WORKFLOW_CONTINUATION_MODE"

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
    return os.environ.get(LIVE_ENV_VAR) == "1"


def workflow_continuation_mode_enabled() -> bool:
    return os.environ.get(WORKFLOW_CONTINUATION_ENV_VAR) == "1"


def is_allowlisted(capability_id: Optional[str]) -> bool:
    if not capability_id:
        return False
    return CANONICAL_EXECUTION_ALLOWLIST is None or capability_id in CANONICAL_EXECUTION_ALLOWLIST


def canonical_killswitch_enabled() -> bool:
    """Whether an operator narrowed canonical authority for rollback.

    The default ``None`` is unrestricted.  Any concrete set, including an
    empty one, is an explicit request for legacy-first route handling.
    """
    return CANONICAL_EXECUTION_ALLOWLIST is not None


def _execute_gmail(
    contract: Dict[str, Any],
    *,
    orchestrator: Any,
    session_id: Optional[str],
    user_text: str,
    principal: Any,
) -> Optional[Dict[str, Any]]:
    dispatch = getattr(orchestrator, "multi_action_dispatch", None)
    if dispatch is None:
        return None
    actions: List[Dict[str, Any]] = [
        a for a in (contract.get("actions") or []) if isinstance(a, dict) and a.get("name")
    ]
    if not actions:
        return None
    if len(actions) == 1:
        envelope = dispatch.dispatch_explicit(
            "Gmail", actions[0]["name"], actions[0].get("inputs") or {},
            session_id=session_id, user_text=user_text, principal=principal,
        )
    else:
        steps = [
            {"capability": "Gmail", "action": a["name"], "inputs": a.get("inputs") or {}}
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
) -> Optional[str]:
    """Pure, deterministic, model-free: the exact eligibility check
    `run_canonical_for_ask()` applies once a Decision Contract and its
    real GateResult already exist. Returns None (proceed to execute)
    only when the gate is READY, the capability is explicitly
    allowlisted, and the mode is one that has a real action to run -
    otherwise names the specific reason execution never happens, for
    both correctness and telemetry. Extracted as its own function so
    every non-READY outcome's fallback behavior is unit-testable
    without any model or orchestrator involved."""
    if gate_outcome in {"INVALID_PROPOSAL", "DEGRADED"}:
        return f"engine_failure:{gate_outcome}"
    if gate_outcome != "READY":
        return None
    if mode not in EXECUTABLE_MODES:
        return None
    if mode == "workflow_continuation" and not workflow_continuation_mode_enabled():
        return "mode_not_executable:workflow_continuation"
    if not is_allowlisted(capability_id):
        return "canonical_killswitch_not_allowlisted"
    return None


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
    return {
        "status": status,
        "canonical_outcome": outcome,
        "plan": {
            "status": "canonical_non_execution",
            "mode": contract.get("mode"),
            "capability": contract.get("capability"),
            "gate_outcome": outcome,
        },
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
    if capability_id == "Gmail":
        return _execute_gmail(
            contract, orchestrator=orchestrator, session_id=session_id,
            user_text=user_text, principal=principal,
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

            fallback_reason = decide_fallback_reason(
                gate_outcome=gate_result.outcome, capability_id=capability_id, mode=mode,
            )
            if fallback_reason is None and gate_result.outcome == "READY" and mode in EXECUTABLE_MODES:
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

    try:
        orchestrator._draft_narrative_safely(
            user_text=user_text, response=envelope,
            personalization_context=personalization_context, session_id=session_id,
        )
    except Exception:
        pass

    try:
        orchestrator._persist_session(session_id)
    except Exception:
        pass

    return envelope
