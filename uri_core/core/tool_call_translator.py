"""M32 Batch C, C3.1: translates a native ModelResponse.ToolCall into the
existing Brain Decision Contract shape (``{"mode", "capability", "actions"}``)
BEFORE it ever reaches ``evaluate_gates()`` - the gates and
``_execute_canonical`` never learn that "native tool calling" exists (the
plan's own central C3 safety property).

Two binding constraints, carried over unchanged from the frozen plan's
review findings:

    - SR-5 (principal provenance): ``principal`` is a required, keyword-only
      parameter here, supplied by the caller from the authenticated request
      context - never parsed out of a tool call's own arguments. A tool
      call cannot smuggle a principal of its own choosing.
    - R12 / SR-4 (single-capability scope): C3.3 (cross-capability
      multi-tool routing) is explicitly BLOCKED in the frozen plan pending
      P1 (`multi_action_dispatch._action_permitted`, specified in
      `M33_EXTERNAL_CAPABILITY_BRIDGE_BLUEPRINT.md` and out of this
      milestone's scope). ``translate_tool_calls`` therefore only ever
      builds a contract when every call in the batch targets the SAME
      capability - a mixed-capability batch is refused honestly (an error
      result per call, never a partial or silent dispatch), not smuggled
      through as if it were the existing single-capability trust boundary.

Unknown tool name -> an error result returned to the Brain, never a
dispatch (verified against the SAME tool schema catalogue actually offered
for this call, not just the naming convention - a name the Brain was never
given cannot be dispatched even if it happens to parse).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from uri_core.core.model_providers.base import ToolCall
from uri_core.core.tool_schema import tool_name_to_contract_target


def translate_tool_call(
    tool_call: ToolCall,
    *,
    offered_tool_names: Sequence[str],
    principal: Any,
) -> Dict[str, Any]:
    """Translate exactly one tool call. Always returns a dict - either a
    valid single-action Decision Contract (`{"ok": True, "contract": ...}`)
    or an explicit error the Brain should be told about
    (`{"ok": False, "tool_call_id", "error"}`), never `None` and never a
    silent drop."""
    if tool_call.name not in offered_tool_names:
        return {
            "ok": False,
            "tool_call_id": tool_call.id,
            "tool_name": tool_call.name,
            "error": f"Unknown tool {tool_call.name!r} - it was not offered for this turn.",
        }

    target = tool_name_to_contract_target(tool_call.name)
    if target is None:
        return {
            "ok": False,
            "tool_call_id": tool_call.id,
            "tool_name": tool_call.name,
            "error": f"Tool {tool_call.name!r} could not be resolved to a real capability/action.",
        }

    contract = {
        "mode": "single_action",
        "capability": target["capability"],
        "actions": [{"name": target["action"], "inputs": dict(tool_call.arguments)}],
        # M32 C3: goal/clarification/reason/unsupported_reason are the
        # remaining Decision Contract fields decision_gates.py/
        # canonical_execution.py read; a native tool call never carries a
        # separate goal string of its own, so these are left unset
        # (falsy/None) exactly as an empty legacy contract field would be.
        "goal": "",
        "clarification": None,
        "unsupported_reason": None,
        "reason": "",
        "requires_approval": False,
        "confidence": "high",
    }
    return {"ok": True, "tool_call_id": tool_call.id, "tool_name": tool_call.name, "contract": contract, "principal": principal}


def translate_tool_calls(
    tool_calls: Sequence[ToolCall],
    *,
    offered_tool_names: Sequence[str],
    principal: Any,
) -> Dict[str, Any]:
    """Translate a whole batch from one Brain response.

    Single-capability batches (including multiple actions against the
    SAME capability, e.g. two Gmail actions in one response - the
    diagnostic report's own headline multi-tool case) build one
    `multi_action`-mode contract, reusing the existing, already-audited
    `MultiActionDispatch.dispatch_chain_explicit` trust boundary. A
    mixed-capability batch is refused per-call rather than partially
    executed - see this module's own docstring for why (C3.3/P1 blocked).
    """
    if not tool_calls:
        return {"ok": False, "results": [], "error": "No tool calls to translate."}

    translated = [
        translate_tool_call(call, offered_tool_names=offered_tool_names, principal=principal)
        for call in tool_calls
    ]

    if any(not entry["ok"] for entry in translated):
        # At least one call is unknown/unresolvable. Per-call error
        # results are returned so the Brain can see exactly which calls
        # failed translation and which (if any) would have been fine -
        # nothing here dispatches partially.
        return {"ok": False, "results": translated, "error": "One or more tool calls could not be translated."}

    capabilities = {entry["contract"]["capability"] for entry in translated}
    if len(capabilities) > 1:
        # R12/SR-4: cross-capability multi-tool has no execution path
        # today and is explicitly blocked pending P1. Refuse honestly
        # rather than smuggling a new, un-audited trust boundary through
        # under "the gates are unchanged."
        return {
            "ok": False,
            "results": [
                {
                    "ok": False,
                    "tool_call_id": entry["tool_call_id"],
                    "tool_name": entry["tool_name"],
                    "error": (
                        "Multiple tool calls in one turn must target the same "
                        "capability - cross-capability multi-tool calls are not "
                        "yet supported."
                    ),
                }
                for entry in translated
            ],
            "error": "Cross-capability multi-tool batch refused (C3.3 blocked pending P1).",
        }

    if len(translated) == 1:
        single = translated[0]
        return {"ok": True, "results": translated, "contract": single["contract"], "principal": principal}

    capability = capabilities.pop()
    actions = [entry["contract"]["actions"][0] for entry in translated]
    contract = {
        "mode": "multi_action",
        "capability": capability,
        "actions": actions,
        "goal": "",
        "clarification": None,
        "unsupported_reason": None,
        "reason": "",
        "requires_approval": False,
        "confidence": "high",
    }
    return {"ok": True, "results": translated, "contract": contract, "principal": principal}
