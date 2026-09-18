"""M32 Batch C: Tier 0 (direct chat) and Tier 1 (native tool loop).

New module - per the standing PC4 rule, all new Batch C behaviour lands
here, never in orchestrator.py.

    - Tier 0 (C2): the Brain is offered tools=[...] and declines every
      one (an empty tool_calls tuple) - its own response content IS the
      reply, streamed tokens strengthening the Brain-authored-words rule
      by construction (no separate drafting call re-renders them). Tier 0
      is selected by the Brain's own choice, never by a URI-side
      classifier or keyword rule.
    - Tier 1 (C3): the Brain calls one or more tools. Each call is
      translated (tool_call_translator.py, C3.1) into the EXISTING
      Decision Contract shape and evaluated through the UNCHANGED
      evaluate_gates()/canonical_execution._execute_canonical() boundary -
      this module adds no new authorization logic.

Deliberate per-action (not per-contract) gate evaluation. Batching every
tool call from one Brain response into a single multi-action contract
would evaluate approval/permission in aggregate (decision_gates.py's own
`approval_required = any(...)` across all actions) and block a whole
batch merely because ONE action needs approval (finding SR-6/C3.8).
Evaluating each call as its OWN single-action contract instead - reusing
exactly the single-action path canonical_execution.py already runs in
production - gives branch preservation (C3.5) and mixed-approval handling
(C3.8) for free, without inventing new gate logic.
"""

from __future__ import annotations

import concurrent.futures
import os
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

from uri_core.core.canonical_execution import _execute_canonical
from uri_core.core.capability_registry import CapabilityRegistry
from uri_core.core.decision_engine import DecisionOutcome, build_turn_state_and_directory
from uri_core.core.decision_gates import evaluate_gates
from uri_core.core.model_providers.base import ToolCall
from uri_core.core.tool_call_translator import translate_tool_calls
from uri_core.core.tool_schema import build_tool_schemas

ROLE_NATIVE_TOOL_LOOP = "reasoning"  # same role gemma4:12b is configured under today


def default_model_callable(principal: Any) -> Callable[..., Any]:
    """Production `model_callable` seam: the real, process-wide
    ModelRouter, bound to the ROLE_NATIVE_TOOL_LOOP role and this
    request's authenticated principal - the same router every other
    Brain call site in this codebase already goes through, so tool
    calling inherits M22.6's existing per-call provider resolution,
    health tracking, and budget checks for free."""
    from uri_core.core.model_router import get_router

    router = get_router()

    def _call(*, system: str, user: str, tools: Optional[List[Dict[str, Any]]] = None) -> Any:
        return router.attempt(
            ROLE_NATIVE_TOOL_LOOP, principal, system=system, user=user, tools=tools, max_tokens=800,
        )

    return _call

DEFAULT_MAX_ITERATIONS = 3  # C3.7 - matches legacy's own max_brain_iterations (orchestrator.py)

TOOL_LOOP_ENV_VAR = "URI_ENABLE_NATIVE_TOOL_LOOP"

# M32 D4: a bounded, deployment-configurable cap on how many read-only +
# approval-free branches (see C3.4/_read_only_and_approval_free) may run
# concurrently in one ThreadPoolExecutor. Before this, worker count was
# `len(eligible)` - unbounded, growing with however many read-only tool
# calls the Brain happened to request in a single turn. Risk R-New-1
# (M32_POST_BATCH_C_LATENCY_ARCHITECTURE_PLAN.md): this machine was
# independently measured at 97% RAM utilization, so an unbounded pool on
# a turn with many parallel-eligible calls is a real, if not-yet-observed,
# resource-exhaustion risk. 4 is a conservative default for I/O-bound
# tool calls (network-bound Gmail/web_search work, not CPU-bound) -
# deliberately not "arbitrarily large" (Python's own ThreadPoolExecutor
# default, min(32, cpu_count+4), was rejected as too large given the
# measured memory pressure). Only bounds *how many run at once*; every
# eligible branch still executes exactly once, in whatever order
# ThreadPoolExecutor schedules it - WHICH branches are eligible for
# concurrency at all is unaffected (_read_only_and_approval_free, C3.4's
# safety classification, is untouched).
DEFAULT_MAX_PARALLEL_TOOL_WORKERS = 4
MAX_PARALLEL_TOOL_WORKERS_ENV_VAR = "URI_MAX_PARALLEL_TOOL_WORKERS"


def _max_parallel_tool_workers() -> int:
    """Runtime-configurable worker cap (env var, read per-call so a test
    or a live deployment can change it without a process restart - same
    discipline as native_tool_loop_enabled()). Falls back to the safe
    default on anything that isn't a positive integer - never 0, never
    negative, never a parse error left to propagate into
    ThreadPoolExecutor (which itself raises ValueError for max_workers
    <= 0)."""
    raw = os.environ.get(MAX_PARALLEL_TOOL_WORKERS_ENV_VAR)
    if raw is None:
        return DEFAULT_MAX_PARALLEL_TOOL_WORKERS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_MAX_PARALLEL_TOOL_WORKERS
    return value if value >= 1 else DEFAULT_MAX_PARALLEL_TOOL_WORKERS


def native_tool_loop_enabled() -> bool:
    """M32 C toggle (plan §10: "the toggle must be runtime-settable, not
    a module constant"). Deliberately OFF by default, unlike Batch B's
    canonical flags - this is materially newer, less-evidenced code
    (built and tested this same session, with only the live evidence
    gathered directly alongside it) and has not earned the same default-
    on bar canonical's 36+ pre-existing tests and multiple prior
    milestones' worth of live evidence had. Set to "1" to opt in."""
    return os.environ.get(TOOL_LOOP_ENV_VAR) == "1"


def _legacy_effect_map(capability_registry: CapabilityRegistry) -> Dict[str, Any]:
    """Loaded once per batch (not once per action - list_capabilities()
    re-reads/re-parses the registry JSON from disk on every call)."""
    return {descriptor.id: descriptor for descriptor in capability_registry.list_capabilities()}


def _read_only_and_approval_free(
    capability_id: str,
    action_name: str,
    *,
    legacy_descriptors: Dict[str, Any],
    directory_describe: Callable[[str], Optional[Dict[str, Any]]],
) -> bool:
    """C3.4's exact safety rule (R4/SR-1): only a call that is BOTH
    read-only AND approval-free may ever be scheduled concurrently with
    another. Ground truth is read per capability shape - Gmail's real,
    structured per-action Action.read_only/approval_requirement (via
    CapabilityDirectory.describe(), which already exposes them), or the
    legacy registry's own effect_type/approval_requirement (Batch A's
    EffectType classification) for everything else. Never guesses;
    returns False (serial) on any lookup failure - fail closed."""
    if capability_id == "Gmail":
        detail = directory_describe(capability_id) or {}
        schema = (detail.get("action_schemas") or {}).get(action_name)
        if not schema:
            return False
        return bool(schema.get("read_only")) and schema.get("approval_requirement") == "none"

    descriptor = legacy_descriptors.get(capability_id)
    if descriptor is None:
        return False
    return descriptor.effect_type == "read_only" and descriptor.approval_requirement == "none"


def _dedup_signature(capability_id: str, action_name: str, inputs: Dict[str, Any]) -> Tuple[Any, ...]:
    try:
        normalized = tuple(sorted((str(k), repr(v)) for k, v in inputs.items()))
    except Exception:
        normalized = (repr(inputs),)
    return (capability_id, action_name, normalized)


def _execute_one_branch(
    *,
    capability_id: str,
    action_name: str,
    inputs: Dict[str, Any],
    orchestrator: Any,
    session_id: Optional[str],
    user_text: str,
    principal: Any,
    directory: Any,
    turn_state_data: Dict[str, Any],
    tool_call_id: str,
    executed_signatures: Set[Tuple[Any, ...]],
    effect_type_is_read_only: bool,
) -> Dict[str, Any]:
    """Gate + execute exactly one translated action. Never raises - any
    internal failure degrades to an honest per-branch error result, never
    a fabricated success and never a crash of the sibling branches."""
    single_action_contract = {
        "mode": "single_action",
        "capability": capability_id,
        "actions": [{"name": action_name, "inputs": inputs}],
        "goal": "", "clarification": None, "unsupported_reason": None,
        "reason": "", "requires_approval": False, "confidence": "high",
    }

    try:
        gate_result = evaluate_gates(
            DecisionOutcome(status="ok", contract=single_action_contract),
            capability_directory=directory, principal=principal, turn_state_data=turn_state_data,
        )
    except Exception as exc:
        return {
            "tool_call_id": tool_call_id, "capability": capability_id, "action": action_name,
            "status": "unavailable", "gate_outcome": "DEGRADED", "detail": f"gate evaluation failed: {exc}",
        }

    if gate_result.outcome != "READY":
        return {
            "tool_call_id": tool_call_id, "capability": capability_id, "action": action_name,
            "status": "not_executed", "gate_outcome": gate_result.outcome,
            "detail": "; ".join(gate_result.reasons) if gate_result.reasons else gate_result.outcome,
        }

    # C3.9: in-turn idempotency. A non-read-only action already executed
    # once in THIS loop invocation is never dispatched a second time, even
    # if the Brain's own continuation reasoning proposes it again after a
    # partial-failure result. Bounded to one loop invocation - not a
    # cross-request/cross-session dedup store (see module docstring / the
    # completion report's residual-risk section for that explicit scope
    # limit).
    signature = _dedup_signature(capability_id, action_name, inputs)
    if not effect_type_is_read_only:
        if signature in executed_signatures:
            return {
                "tool_call_id": tool_call_id, "capability": capability_id, "action": action_name,
                "status": "skipped_duplicate", "gate_outcome": "READY",
                "detail": "This exact action already executed once this turn - refusing a duplicate dispatch.",
            }
        executed_signatures.add(signature)

    try:
        envelope = _execute_canonical(
            single_action_contract, orchestrator=orchestrator, session_id=session_id,
            user_text=user_text, principal=principal,
        )
    except Exception as exc:
        return {
            "tool_call_id": tool_call_id, "capability": capability_id, "action": action_name,
            "status": "unavailable", "gate_outcome": "READY", "detail": f"execution raised: {exc}",
        }

    if envelope is None:
        return {
            "tool_call_id": tool_call_id, "capability": capability_id, "action": action_name,
            "status": "unavailable", "gate_outcome": "READY", "detail": "execution dispatch returned no result",
        }

    return {
        "tool_call_id": tool_call_id, "capability": capability_id, "action": action_name,
        "status": envelope.get("status", "unavailable"),
        "gate_outcome": "READY",
        "execution": envelope.get("execution"),
        "response": envelope.get("response"),
    }


def execute_translated_batch(
    contract: Dict[str, Any],
    *,
    results_meta: Sequence[Dict[str, Any]],
    orchestrator: Any,
    session_id: Optional[str],
    user_text: str,
    principal: Any,
    directory: Any,
    turn_state_data: Dict[str, Any],
    capability_registry: CapabilityRegistry,
    executed_signatures: Set[Tuple[Any, ...]],
) -> List[Dict[str, Any]]:
    """C3.5 (branch preservation) + C3.4 (bounded parallel execution).

    Every action in `contract["actions"]` is gated and executed
    independently - a failure or approval-required outcome on one never
    stops the others. Calls that are BOTH read-only and approval-free
    (per capability-real ground truth, not the old provably-wrong
    `read_only = approval == "none"` derivation C3.4 was blocked on) run
    concurrently; anything else runs strictly serially, in order.
    """
    capability_id = contract["capability"]
    actions = contract["actions"]
    call_ids = [meta["tool_call_id"] for meta in results_meta]

    legacy_descriptors = _legacy_effect_map(capability_registry)
    eligible: List[int] = []
    serial: List[int] = []
    for index, action in enumerate(actions):
        is_ro = _read_only_and_approval_free(
            capability_id, action["name"],
            legacy_descriptors=legacy_descriptors,
            directory_describe=directory.describe,
        )
        (eligible if is_ro else serial).append(index)

    results: Dict[int, Dict[str, Any]] = {}

    def _run(index: int) -> None:
        action = actions[index]
        results[index] = _execute_one_branch(
            capability_id=capability_id, action_name=action["name"], inputs=action.get("inputs") or {},
            orchestrator=orchestrator, session_id=session_id, user_text=user_text, principal=principal,
            directory=directory, turn_state_data=turn_state_data, tool_call_id=call_ids[index],
            executed_signatures=executed_signatures, effect_type_is_read_only=(index in eligible),
        )

    if len(eligible) > 1:
        worker_count = min(len(eligible), _max_parallel_tool_workers())
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as pool:
            list(pool.map(_run, eligible))
    else:
        for index in eligible:
            _run(index)

    # Serial branches always run strictly in order, never interleaved
    # with (or before) the parallel read-only batch above - preserves
    # audit ordering (R4) for anything side-effecting or approval-gated.
    for index in serial:
        _run(index)

    return [results[i] for i in range(len(actions))]


def _terminal_envelope(
    *, content: str, tier: str, session_id: Optional[str], branch_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    return {
        "status": "success",
        "session_id": session_id,
        "tier": tier,
        "execution": {"status": "not_applicable" if tier == "tier0" else "success", "branch_results": branch_results},
        "response": {"message": content},
        # M32: the Brain's own generated content IS the reply - no
        # separate drafting call re-renders it (strengthens, never
        # weakens, the Brain-authored-words rule).
        "narrative": content,
        "semantic_analysis": None,
        "error": None,
    }


def run_native_tool_loop(
    *,
    orchestrator: Any,
    session_id: Optional[str],
    user_text: str,
    principal: Any,
    model_callable: Callable[..., Any],
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    capability_registry: Optional[CapabilityRegistry] = None,
) -> Optional[Dict[str, Any]]:
    """The single Tier-0/Tier-1 entry point. `model_callable` is an
    injectable `(*, system, user, tools) -> ModelResponse` seam (the
    router's own `attempt()` bound to a role/principal in production,
    a fake in tests) so this function never constructs its own provider.

    Returns a full envelope (Tier 0 or a completed/bounded Tier 1 turn),
    or None if tools/turn-state could not even be assembled (caller's
    existing fallback - e.g. canonical's own JSON-contract path, or
    legacy - is used unchanged, matching every other M30.6+ entry point's
    own None-means-fall-back convention)."""
    capability_registry = capability_registry or CapabilityRegistry()

    try:
        turn_state_result, directory = build_turn_state_and_directory(
            orchestrator=orchestrator, session_id=session_id, user_text=user_text, principal=principal,
        )
    except Exception:
        return None

    # M32 D2: reuse the SAME CapabilityDirectory just built above for
    # this turn's tool-schema generation, instead of build_tool_schemas
    # constructing a second, independent one. Both would describe the
    # exact same real-world capability/connection state; building two
    # only doubled the live Google OAuth refresh cost measured in
    # docs/plans/M32_POST_BATCH_C_LATENCY_ARCHITECTURE_PLAN.md §2.2.
    multi_action_registry = getattr(orchestrator.multi_action_dispatch, "registry", None)
    tools = build_tool_schemas(
        capability_registry=capability_registry, multi_action_registry=multi_action_registry,
        directory=directory,
    )
    offered_names = {t["function"]["name"] for t in tools}

    all_branch_results: List[Dict[str, Any]] = []
    executed_signatures: Set[Tuple[Any, ...]] = set()
    conversation_note = user_text

    for iteration in range(1, max_iterations + 1):
        try:
            response = model_callable(system=_SYSTEM_PROMPT, user=conversation_note, tools=tools)
        except Exception as exc:
            return {
                "status": "unavailable", "session_id": session_id, "tier": "tier1",
                "execution": {"status": "unavailable", "branch_results": all_branch_results},
                "response": {"message": "URI could not reach its model provider, so it did not complete this request."},
                "narrative": None, "semantic_analysis": None, "error": str(exc),
            }

        tool_calls = response.tool_calls or ()
        if not tool_calls:
            tier = "tier0" if iteration == 1 else "tier1_continuation"
            return _terminal_envelope(
                content=response.content, tier=tier, session_id=session_id, branch_results=all_branch_results,
            )

        translation = translate_tool_calls(tool_calls, offered_tool_names=offered_names, principal=principal)
        if not translation["ok"]:
            # C3.7-bounded: fed back as an honest per-call error so the
            # Brain can try something else next iteration, never dispatched.
            all_branch_results.extend(
                {
                    "tool_call_id": r.get("tool_call_id"), "capability": None, "action": r.get("tool_name"),
                    "status": "translation_error", "detail": r.get("error"),
                }
                for r in translation.get("results", [])
            )
            conversation_note = (
                f"{user_text}\n\n[Tool call error: {translation['error']}. "
                "Please answer directly or choose a different tool.]"
            )
            continue

        contract = translation["contract"]
        results_meta = translation["results"]
        branch_results = execute_translated_batch(
            contract, results_meta=results_meta, orchestrator=orchestrator, session_id=session_id,
            user_text=user_text, principal=principal, directory=directory,
            turn_state_data=turn_state_result.data, capability_registry=capability_registry,
            executed_signatures=executed_signatures,
        )
        all_branch_results.extend(branch_results)

        # C3.6: continuation - real evidence feeds back to the Brain for
        # its own re-evaluation (the USER->BRAIN->URI loop's own
        # re-evaluation step), never URI composing the next question.
        conversation_note = (
            f"{user_text}\n\n[Tool results so far: {branch_results}. "
            "If this fully answers the request, reply directly. "
            "Otherwise call another tool.]"
        )

    # C3.7: loop bound reached - reported honestly, never silently
    # truncated.
    return {
        "status": "success", "session_id": session_id, "tier": "tier1_bounded",
        "execution": {"status": "iteration_limit_reached", "branch_results": all_branch_results},
        "response": {"message": "URI reached its tool-call iteration limit for this turn."},
        "narrative": None, "semantic_analysis": None, "error": None,
    }


_SYSTEM_PROMPT = (
    "You are URI's Brain. Use the offered tools when the user's request "
    "needs one of them; otherwise reply directly in your own words. "
    "Never claim an action succeeded unless a tool result confirms it."
)
