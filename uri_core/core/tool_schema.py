"""M32 Batch C, C3.2: Brain-facing native tool schemas, generated from the
existing capability registry rather than hand-maintained as a second list.

What "the existing capability registry" actually contains, verified by
direct inspection before writing this module: every one of the 15
non-Gmail legacy tools' real callable signature is ``method(**kwargs)`` -
there is no structured parameter schema anywhere in
``uri_workspace/capabilities_registry.json`` (every entry's ``interface``
is ``null``) or in the Python signatures themselves. The real, ground-
truth parameter surface for each tool is what it actually reads out of
``kwargs`` in its own source (verified by inspection, listed in
``LEGACY_TOOL_PARAMETERS`` below), MINUS the fields URI itself injects at
dispatch time (``principal``, ``session_id``, ``decision_context``,
``file_store``, ``user_id``) - those are runtime context, never something
the model proposes, exactly like every other capability boundary in this
codebase (see dispatcher.py, approval_gate.py, canonical_execution.py's
own docstrings on this same invariant).

Gmail's actions already have real, structured ``Action``/``ActionSchema``
definitions (``capabilities/gmail/capability.py``) - those are read
directly, not re-declared here.

Capability overlap resolution (M30.5A) is reused unchanged: when Gmail's
multi-action capability covers the same real-world action a legacy tool
also names (``gmail_search``, ``gmail_find_draft``, ``drive_search``,
``gmail_create_draft`` today), the legacy tool is excluded from this
catalogue exactly as it already is from ``CapabilityDirectory.summaries()``
- the Brain must never see two different tools that claim to do the same
thing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from uri_core.capabilities import MultiActionCapabilityRegistry
from uri_core.core.capability_directory import CapabilityDirectory
from uri_core.core.capability_feasibility import CapabilityFeasibility
from uri_core.core.capability_registry import CapabilityRegistry

GMAIL_TOOL_PREFIX = "gmail_"

# Runtime-injected fields no tool ever receives from the model - see
# dispatcher.py's own file_store/user_id popping and approval_gate.py's
# principal/session_id threading. Never included in a Brain-facing schema.
_RUNTIME_INJECTED_FIELDS = frozenset({"principal", "session_id", "decision_context", "file_store", "user_id"})

# Ground truth, verified 2026-09-18 by grepping each tool's own source for
# `kwargs.get("...")` / `kwargs["..."]` - this IS the real parameter
# surface each legacy tool reads, since inspect.signature() on every one
# of them yields only `(**kwargs)` and tells nothing about which keys are
# actually consumed. `required` follows each tool's own honest-failure
# behavior (an omitted required field triggers the tool's own
# "input_required"/similar response, verified case by case, not guessed).
LEGACY_TOOL_PARAMETERS: Dict[str, Dict[str, Any]] = {
    "extract_student_records": {
        "properties": {
            "roll_number": {"type": "string", "description": "The student's roll number, exactly as stated in the request."},
            "request_text": {"type": "string", "description": "The user's original request, verbatim."},
        },
        "required": ["request_text"],
    },
    "fetch_drive_spreadsheet": {
        "properties": {
            "spreadsheet_id": {"type": "string", "description": "The Google Sheets spreadsheet ID."},
            "range_name": {"type": "string", "description": "The A1-notation range to read, e.g. 'Sheet1!A1:D10'."},
        },
        "required": ["spreadsheet_id"],
    },
    "draft_institutional_note": {
        "properties": {
            "request_text": {"type": "string", "description": "The user's original request, verbatim."},
            "requested_output": {"type": "string", "description": "What the note should conclude or recommend."},
        },
        "required": ["request_text"],
    },
    "draft_institutional_order": {
        "properties": {
            "request_text": {"type": "string", "description": "The user's original request, verbatim."},
            "requested_output": {"type": "string", "description": "What the order should conclude or recommend."},
        },
        "required": ["request_text"],
    },
    "generate_document": {
        "properties": {
            "request_text": {"type": "string", "description": "The user's original request, verbatim."},
            "requested_output": {"type": "string", "description": "What the generated document should contain."},
        },
        "required": ["request_text"],
    },
    "system_performance": {"properties": {}, "required": []},
    "remember_fact": {
        "properties": {
            "request_text": {"type": "string", "description": "The fact to remember, in the user's own words."},
        },
        "required": ["request_text"],
    },
    "recall_memory": {"properties": {}, "required": []},
    "convert_document": {
        "properties": {
            "request_text": {"type": "string", "description": "The user's original request, verbatim."},
            "requested_output": {"type": "string", "description": "The desired output format."},
        },
        "required": ["request_text"],
    },
    "read_attached_file": {"properties": {}, "required": []},
    "web_search": {
        "properties": {
            "request_text": {"type": "string", "description": "What to search the web for."},
        },
        "required": ["request_text"],
    },
    "gmail_search": {
        "properties": {"request_text": {"type": "string", "description": "What to search for in Gmail."}},
        "required": ["request_text"],
    },
    "gmail_find_draft": {
        "properties": {"request_text": {"type": "string", "description": "Which draft to find."}},
        "required": ["request_text"],
    },
    "drive_search": {
        "properties": {"request_text": {"type": "string", "description": "What to search for in Drive."}},
        "required": ["request_text"],
    },
    "gmail_create_draft": {
        "properties": {"request_text": {"type": "string", "description": "What the draft should say."}},
        "required": ["request_text"],
    },
    "drive_upload": {"properties": {}, "required": []},
    "fetch_url": {
        "properties": {"request_text": {"type": "string", "description": "The request naming the URL to fetch."}},
        "required": ["request_text"],
    },
}


def _legacy_tool_definition(capability_id: str, description: str) -> Dict[str, Any]:
    spec = LEGACY_TOOL_PARAMETERS.get(capability_id, {"properties": {}, "required": []})
    return {
        "type": "function",
        "function": {
            "name": capability_id,
            "description": description or f"Execute {capability_id}.",
            "parameters": {
                "type": "object",
                "properties": dict(spec["properties"]),
                "required": list(spec["required"]),
            },
        },
    }


def _gmail_action_definition(action_name: str, action_schema: Dict[str, Any]) -> Dict[str, Any]:
    properties: Dict[str, Any] = {}
    for name, param_spec in (action_schema.get("parameters") or {}).items():
        if name in _RUNTIME_INJECTED_FIELDS:
            continue
        prop = {"type": param_spec.get("type", "string")}
        if param_spec.get("description"):
            prop["description"] = param_spec["description"]
        properties[name] = prop
    required = [name for name in (action_schema.get("required") or []) if name not in _RUNTIME_INJECTED_FIELDS]
    return {
        "type": "function",
        "function": {
            "name": f"{GMAIL_TOOL_PREFIX}{action_name}",
            "description": action_schema.get("description") or f"Gmail: {action_name}.",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


def build_tool_schemas(
    *,
    capability_registry: Optional[CapabilityRegistry] = None,
    multi_action_registry: Optional[MultiActionCapabilityRegistry] = None,
) -> List[Dict[str, Any]]:
    """The Brain-facing native tool list, one entry per dispatchable
    capability/action, built from the same CapabilityDirectory overlap
    resolution the rest of the canonical/decision-gate pipeline already
    uses - never a second, independently-curated tool list.

    `capability_registry`/`multi_action_registry` are injectable purely
    for tests; production call sites omit both and get the real,
    installation-wide registry/GmailCapability the rest of the system
    already uses.
    """
    feasibility = CapabilityFeasibility(capability_registry=capability_registry or CapabilityRegistry())
    directory = CapabilityDirectory(
        capability_feasibility=feasibility,
        multi_action_registry=multi_action_registry,
        include_procedures=False,
    )

    tools: List[Dict[str, Any]] = []
    for summary in directory.summaries(resolve_overlaps=True):
        capability_id = summary["capability_id"]
        if summary["source"] == "legacy":
            tools.append(_legacy_tool_definition(capability_id, summary.get("summary", "")))
        elif summary["source"] == "multi_action":
            detail = directory.describe(capability_id) or {}
            action_schemas = detail.get("action_schemas", {})
            for action_name, action_schema in action_schemas.items():
                tools.append(_gmail_action_definition(action_name, action_schema))
        # "procedure" source (workflow templates) is excluded by
        # include_procedures=False above - Tier 2 escalation territory,
        # never something the native tool loop calls directly.
    return tools


def tool_name_to_contract_target(tool_name: str) -> Optional[Dict[str, str]]:
    """Reverses the naming convention above: a Brain-proposed tool name
    back to {"capability", "action"} - the shape tool_call_translator.py
    needs to build a Decision Contract. Returns None for a name that
    matches neither convention (an unknown tool - the caller must treat
    this as an error to the Brain, never a dispatch)."""
    if tool_name.startswith(GMAIL_TOOL_PREFIX):
        action_name = tool_name[len(GMAIL_TOOL_PREFIX):]
        if action_name:
            return {"capability": "Gmail", "action": action_name}
        return None
    if tool_name in LEGACY_TOOL_PARAMETERS:
        return {"capability": tool_name, "action": tool_name}
    return None
