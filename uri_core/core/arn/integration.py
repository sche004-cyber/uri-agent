"""Authority-neutral seams between ARN bookkeeping and execution results."""

from __future__ import annotations

from typing import Any, Dict, Optional

from uri_core.core.arn.engine import ARNEngine, _is_empty_result
from uri_core.core.arn.models import ARNState, CostCeiling


def is_not_found_result(result: Any) -> bool:
    """Recognize empty/NOT_FOUND without importing a tool or Graphify."""
    if isinstance(result, dict):
        execution = result.get("execution")
        if isinstance(execution, dict) and execution.get("status") == "not_found":
            return True
        if result.get("status") in {"not_found", "NOT_FOUND"}:
            return True
        if "data" in result:
            return is_not_found_result(result["data"])
        if "response" in result:
            return is_not_found_result(result["response"])
    return _is_empty_result(result)


def trigger_not_found_recovery(
    *,
    goal: str,
    source: str,
    query: str,
    result: Any,
    state: Optional[ARNState] = None,
    cost_ceiling: Optional[CostCeiling] = None,
) -> Optional[ARNState]:
    """Return task-local recovery state for a real empty result, else None."""
    if not is_not_found_result(result):
        return None
    engine = ARNEngine(state=state, cost_ceiling=cost_ceiling)
    if state is None:
        state = ARNState(task_goal=goal)
        engine.state = state
    if not engine.is_search_repeated(source, query):
        engine.record_source_checked(source, query, result)
    return state


def attach_not_found_recovery(
    envelope: Dict[str, Any],
    *,
    goal: str,
    source: str,
    query: str,
    state: Optional[ARNState] = None,
    cost_ceiling: Optional[CostCeiling] = None,
) -> Dict[str, Any]:
    """Turn terminal-looking NOT_FOUND into structured recovery evidence.

    The original execution status remains untouched under ``execution``;
    only the envelope outcome changes so the first miss cannot masquerade as
    a final answer.  The returned state remains plain task-local data.
    """
    recovery = trigger_not_found_recovery(
        goal=goal,
        source=source,
        query=query,
        result=envelope,
        state=state,
        cost_ceiling=cost_ceiling,
    )
    if recovery is None:
        return envelope
    updated = dict(envelope)
    updated["status"] = "recovery_required"
    updated["arn_state"] = ARNEngine(
        state=recovery, cost_ceiling=cost_ceiling
    ).get_case_summary()
    return updated
