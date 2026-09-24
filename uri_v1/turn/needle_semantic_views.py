"""Needle Semantic View Schemas and Normalizers (Batch A2.3).

Defines tool schemas and deterministic normalizers for:
  - GoalView (select_goal)
  - OperationView (select_operations with candidate action IDs)
  - ReferenceView (select_references with candidate reference & target IDs)
  - OutputScopeView (select_output_scope)
  - Free-text variants for baseline comparison (select_operations_freetext, select_references_freetext)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from uri_v1.turn.contracts import (
    ConstraintScope,
    IntentFamily,
    OutputPreferences,
    ReferenceKind,
    SemanticOperation,
    SemanticReference,
    TemporalReference,
)
from uri_v1.turn.needle_wire import DecodeError, DecodeErrorReason, _dedupe

# ---------------------------------------------------------------------------
# Goal View Tool
# ---------------------------------------------------------------------------

SCHEMA_SELECT_GOAL: Dict[str, Any] = {
    "name": "select_goal",
    "description": "Always call this exactly once to record the primary goal and intent family.",
    "parameters": {
        "type": "object",
        "properties": {
            "goal": {"type": "string", "description": "Concise phrase describing the user's primary intended outcome."},
            "intent_family": {
                "type": "string",
                "enum": [f.value for f in IntentFamily],
                "description": "The general category of the user's intent.",
            },
        },
        "required": ["goal"],
        "additionalProperties": False,
    },
}

SYSTEM_SELECT_GOAL = (
    "You are a semantic goal selector. Identify the user's primary intended outcome concisely in 'goal', "
    "and select the best matching 'intent_family' from the allowed options. "
    "Use only the provided message and action cues. Never decline to call select_goal."
)

# ---------------------------------------------------------------------------
# Operation View Tool (Candidate-ID Selection)
# ---------------------------------------------------------------------------

SCHEMA_SELECT_OPERATIONS_ID: Dict[str, Any] = {
    "name": "select_operations",
    "description": "Always call this exactly once to classify candidate action IDs as requested or prohibited.",
    "parameters": {
        "type": "object",
        "properties": {
            "requested_action_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Action IDs (e.g. 'a1', 'a2') that the user wants performed.",
            },
            "prohibited_action_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Action IDs (e.g. 'a1', 'a2') that the user explicitly forbade or negated (e.g. 'don't send').",
            },
        },
        "required": ["requested_action_ids", "prohibited_action_ids"],
        "additionalProperties": False,
    },
}

SYSTEM_SELECT_OPERATIONS_ID = (
    "You are an action classifier. Given the user clauses, negation cues, and candidate action IDs (a1, a2, ...), "
    "select which action IDs are REQUESTED by the user, and which action IDs are PROHIBITED or negated. "
    "Emit ONLY IDs from the candidate list in requested_action_ids and prohibited_action_ids. "
    "If none apply, emit empty lists. Never decline to call select_operations."
)

# Free-text variant for comparison (§18)
SCHEMA_SELECT_OPERATIONS_FREETEXT: Dict[str, Any] = {
    "name": "select_operations_freetext",
    "description": "Extract requested and prohibited operation strings.",
    "parameters": {
        "type": "object",
        "properties": {
            "requested_operations": {"type": "array", "items": {"type": "string"}},
            "prohibited_operations": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["requested_operations", "prohibited_operations"],
        "additionalProperties": False,
    },
}

SYSTEM_SELECT_OPERATIONS_FREETEXT = (
    "Extract requested and prohibited operations from the text. "
    "Put negated actions into prohibited_operations."
)

# ---------------------------------------------------------------------------
# Reference View Tool (Candidate-ID Selection)
# ---------------------------------------------------------------------------

SCHEMA_SELECT_REFERENCES_ID: Dict[str, Any] = {
    "name": "select_references",
    "description": "Always call this exactly once to classify candidate IDs against active session targets.",
    "parameters": {
        "type": "object",
        "properties": {
            "resolved_candidate_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Candidate reference IDs and matching active target IDs (e.g. ['r1', 'x1']).",
            },
            "unresolved_candidate_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Candidate reference IDs that have no matching active session target.",
            },
        },
        "required": ["resolved_candidate_ids", "unresolved_candidate_ids"],
        "additionalProperties": False,
    },
}

SYSTEM_SELECT_REFERENCES_ID = (
    "You are a reference interpreter. Given candidate reference IDs (r1, r2, ...) and active target IDs (x1, e1, ...), "
    "identify which candidate IDs match an active target ID. Put matching candidate and target IDs in resolved_candidate_ids. "
    "Put unresolvable candidate reference IDs in unresolved_candidate_ids. Never decline to call select_references."
)

# Free-text variant for comparison (§18)
SCHEMA_SELECT_REFERENCES_FREETEXT: Dict[str, Any] = {
    "name": "select_references_freetext",
    "description": "Extract reference strings without IDs.",
    "parameters": {
        "type": "object",
        "properties": {
            "references": {"type": "array", "items": {"type": "string"}},
            "temporal_references": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["references", "temporal_references"],
        "additionalProperties": False,
    },
}

SYSTEM_SELECT_REFERENCES_FREETEXT = (
    "Extract unresolved reference expressions and temporal expressions."
)

# ---------------------------------------------------------------------------
# Output Scope View Tool
# ---------------------------------------------------------------------------

SCHEMA_SELECT_OUTPUT_SCOPE: Dict[str, Any] = {
    "name": "select_output_scope",
    "description": "Always call this exactly once to extract output preferences and constraints.",
    "parameters": {
        "type": "object",
        "properties": {
            "artifact_type": {"type": "string"},
            "tone": {"type": "string"},
            "audience": {"type": "string"},
            "language_variant": {"type": "string"},
            "structure": {"type": "string"},
            "included_scope": {"type": "array", "items": {"type": "string"}},
            "excluded_scope": {"type": "array", "items": {"type": "string"}},
            "length_limit": {"type": "string"},
            "temporal_scope": {"type": "array", "items": {"type": "string"}},
        },
        "additionalProperties": False,
    },
}

SYSTEM_SELECT_OUTPUT_SCOPE = (
    "Extract explicit output preferences (artifact_type, tone, audience, language_variant, structure) "
    "and constraints (included_scope, excluded_scope, length_limit, temporal_scope) directly mentioned in the cues. "
    "Leave unmentioned fields empty. Never decline to call select_output_scope."
)
