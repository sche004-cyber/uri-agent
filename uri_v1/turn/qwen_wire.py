"""Qwen semantic wire schema and deterministic normalizer (Batch A2.2).

Extracts and normalizes Step-1 semantic representations from Qwen models:
  DecodeInput -> Qwen (local LLM) -> structured wire JSON -> normalize_qwen_wire -> DecodedRequest.

Validation and mapping only:
  - Zero semantic invention: missing fields remain neutral/empty.
  - Zero reference resolution: all references remain strictly is_resolved=False (Rule 3).
  - Context dependencies are derived deterministically from references and attachments (Rules 3 & 8).
  - Contradictions (e.g. operation both requested and prohibited) raise DecodeError.
  - Excludes all tool names, capability IDs, Graphify nodes, and routing metadata.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from uri_v1.turn.contracts import (
    AttachmentReference,
    ConfidenceLevel,
    ConstraintScope,
    ContextDependency,
    ContextDependencyCategory,
    DecodedRequest,
    EntityCategory,
    IntendedOutcome,
    IntentFamily,
    MentionedEntity,
    OperationStatus,
    OutputPreferences,
    ReferenceKind,
    SemanticAmbiguity,
    AmbiguityKind,
    SemanticConfidence,
    SemanticOperation,
    SemanticReference,
    TemporalReference,
)
from uri_v1.turn.needle_wire import (
    DecodeError,
    DecodeErrorReason,
    _confidence_bucket,
    _dedupe,
)

QWEN_WIRE_SCHEMA_NAME = "decoded_request"

QWEN_WIRE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "goal": {
            "type": "string",
            "description": "One concise phrase stating the primary intended outcome the user wants achieved.",
        },
        "intent_family": {
            "type": "string",
            "enum": [f.value for f in IntentFamily],
            "description": "The category of the user's intent.",
        },
        "requested_operations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Operations or actions requested by the user.",
        },
        "prohibited_operations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Operations or actions explicitly prohibited, forbidden, or negated by the user (e.g. 'do not send', 'don't summarize').",
        },
        "prompt_supplied_context": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Contextual facts or background explicitly stated within the prompt.",
        },
        "constraints": {
            "type": "object",
            "properties": {
                "included_items": {"type": "array", "items": {"type": "string"}},
                "excluded_items": {"type": "array", "items": {"type": "string"}},
                "length_limit": {"type": "string"},
                "language_constraints": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "output_preferences": {
            "type": "object",
            "properties": {
                "artifact_type": {"type": "string"},
                "tone": {"type": "string"},
                "audience": {"type": "string"},
                "language": {"type": "string"},
                "language_variant": {"type": "string"},
                "length": {"type": "string"},
                "structure": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "category": {"type": "string"},
                },
                "required": ["name"],
                "additionalProperties": False,
            },
        },
        "references": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Unresolved referring expressions such as pronouns ('this', 'that', 'it', 'them') or noun phrases ('that file', 'same thing', 'earlier one'). Do NOT resolve them.",
        },
        "temporal_references": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Temporal expressions mentioned in the text (e.g. 'yesterday', 'tomorrow', '2025', 'earlier').",
        },
        "dependencies": {
            "type": "array",
            "items": {"type": "string"},
            "description": "External or context items required to satisfy the request.",
        },
        "ambiguities": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Unresolved ambiguities or missing information in the request.",
        },
    },
    "required": ["goal", "intent_family"],
    "additionalProperties": False,
}

QWEN_SYSTEM_PROMPT = (
    "You are URI's Step-1 Semantic Decoder for the current user message only. "
    "Your sole job is to understand what the user means and extract their intended goal, "
    "operations, constraints, references, and output preferences into structured JSON. "
    "\n"
    "Governing Rules:\n"
    "1. Do NOT execute the task, do NOT draft the final answer, do NOT choose tools or capabilities.\n"
    "2. Record referring expressions (like 'this', 'that', 'it', 'them', 'that file', 'same thing', "
    "'the earlier one') in 'references' as UNRESOLVED expressions. Do NOT resolve them.\n"
    "3. Keep prohibited or negated actions (e.g. 'don't send', 'do not summarize', 'don't open') "
    "strictly in 'prohibited_operations', distinct from 'requested_operations'.\n"
    "4. Extract explicit constraints and output preferences directly stated by the user.\n"
    "5. If an aspect is not present, leave its list or object empty. Never invent facts not in the message.\n"
    "6. Output ONLY valid JSON adhering strictly to the schema."
)


def _strip_markdown_fence(raw: str) -> str:
    """Strips markdown code fences (e.g. ```json ... ```) if present."""
    text = raw.strip()
    if text.startswith("```"):
        # Remove opening fence and optional language tag
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        if text.endswith("```"):
            text = text[:-3].rstrip()
    return text.strip()


def parse_wire_json(raw: str) -> Dict[str, Any]:
    """Parses raw model output into a dictionary, handling fences or leading/trailing noise."""
    cleaned = _strip_markdown_fence(raw)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # Fallback: search for first '{' and matching '}'
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    raise DecodeError(
        DecodeErrorReason.MALFORMED_OUTPUT,
        f"Model output is not valid JSON object: {raw[:200]!r}",
    )


def _classify_reference_kind(expr: str) -> ReferenceKind:
    """Classifies reference kind based on surface shape only; is_resolved is ALWAYS False."""
    lower = expr.strip().lower()
    if lower in {"this", "that", "it", "them", "these", "those", "him", "her", "they"}:
        return ReferenceKind.PRONOUN
    if any(k in lower for k in ("file", "document", "pdf", "sheet", "spreadsheet", "letter", "report", "attachment")):
        return ReferenceKind.DOCUMENT_OR_FILE
    if any(k in lower for k in ("previous", "earlier", "former", "prior", "last", "next", "same thing")):
        return ReferenceKind.PREVIOUS_ACTION
    return ReferenceKind.OTHER


def normalize_qwen_wire(
    wire: Dict[str, Any],
    input_data: Any,
    *,
    raw_confidence: Optional[float] = None,
) -> DecodedRequest:
    """Deterministically normalizes Qwen wire dictionary into DecodedRequest.

    Validation and mapping only -- no semantic reasoning.
    """
    if not isinstance(wire, dict):
        raise DecodeError(DecodeErrorReason.MALFORMED_OUTPUT, "Wire payload is not a dictionary")

    # 1. Goal / Intent
    goal_text = wire.get("goal")
    if not isinstance(goal_text, str) or not goal_text.strip():
        raise DecodeError(
            DecodeErrorReason.MISSING_REQUIRED_STRUCTURE,
            "Wire payload has no non-empty 'goal' field",
        )

    raw_intent = wire.get("intent_family")
    try:
        intent_family = IntentFamily(raw_intent) if raw_intent else IntentFamily.UNSPECIFIED
    except ValueError:
        intent_family = IntentFamily.UNSPECIFIED

    goal = IntendedOutcome(description=goal_text.strip(), intent_family=intent_family)

    # 2. Operations (Requested vs. Prohibited)
    raw_req = wire.get("requested_operations") or ()
    if not isinstance(raw_req, (list, tuple)):
        raise DecodeError(DecodeErrorReason.OPERATION_ERROR, "'requested_operations' must be an array")
    requested_names = _dedupe(tuple(str(x).strip() for x in raw_req if str(x).strip()))

    raw_proh = wire.get("prohibited_operations") or ()
    if not isinstance(raw_proh, (list, tuple)):
        raise DecodeError(DecodeErrorReason.OPERATION_ERROR, "'prohibited_operations' must be an array")
    prohibited_names = _dedupe(tuple(str(x).strip() for x in raw_proh if str(x).strip()))

    overlap = set(requested_names) & set(prohibited_names)
    if overlap:
        raise DecodeError(
            DecodeErrorReason.OPERATION_ERROR,
            f"operation(s) marked both requested and prohibited: {sorted(overlap)}",
        )

    operations: List[SemanticOperation] = []
    for name in requested_names:
        operations.append(SemanticOperation(name=name, status=OperationStatus.REQUESTED))
    for name in prohibited_names:
        operations.append(SemanticOperation(name=name, status=OperationStatus.PROHIBITED))

    # 3. References (strictly unresolved)
    raw_refs = wire.get("references") or ()
    if not isinstance(raw_refs, (list, tuple)):
        raise DecodeError(DecodeErrorReason.REFERENCE_ERROR, "'references' must be an array")
    references: List[SemanticReference] = []
    for r in raw_refs:
        expr = str(r).strip() if isinstance(r, (str, int)) else (r.get("expression") if isinstance(r, dict) else "")
        if expr:
            references.append(
                SemanticReference(
                    expression=expr,
                    kind=_classify_reference_kind(expr),
                    is_resolved=False,  # strictly unresolved in Step 1
                )
            )

    # 4. Temporal References
    raw_trefs = wire.get("temporal_references") or ()
    if not isinstance(raw_trefs, (list, tuple)):
        raise DecodeError(DecodeErrorReason.TEMPORAL_ERROR, "'temporal_references' must be an array")
    temporal_references: List[TemporalReference] = []
    for t in raw_trefs:
        expr = str(t).strip() if isinstance(t, (str, int)) else (t.get("expression") if isinstance(t, dict) else "")
        if expr:
            temporal_references.append(TemporalReference(expression=expr))

    # 5. Constraints
    raw_constraints = wire.get("constraints") or {}
    if not isinstance(raw_constraints, dict):
        raise DecodeError(DecodeErrorReason.CONSTRAINT_ERROR, "'constraints' must be an object")
    inc_raw = raw_constraints.get("included_items") or ()
    exc_raw = raw_constraints.get("excluded_items") or ()
    included = _dedupe(tuple(str(x).strip() for x in inc_raw if str(x).strip()))
    excluded = _dedupe(tuple(str(x).strip() for x in exc_raw if str(x).strip()))
    inc_exc_overlap = set(included) & set(excluded)
    if inc_exc_overlap:
        raise DecodeError(
            DecodeErrorReason.CONSTRAINT_ERROR,
            f"item(s) both included and excluded: {sorted(inc_exc_overlap)}",
        )
    constraints = ConstraintScope(
        included_items=included,
        excluded_items=excluded,
        length_limit=raw_constraints.get("length_limit"),
        language_constraints=raw_constraints.get("language_constraints"),
    )

    # 6. Output Preferences
    raw_prefs = wire.get("output_preferences") or {}
    if not isinstance(raw_prefs, dict):
        raise DecodeError(DecodeErrorReason.OUTPUT_PREFERENCE_ERROR, "'output_preferences' must be an object")
    output_preferences = OutputPreferences(
        artifact_type=raw_prefs.get("artifact_type"),
        structure=raw_prefs.get("structure"),
        language=raw_prefs.get("language"),
        language_variant=raw_prefs.get("language_variant"),
        tone=raw_prefs.get("tone"),
        audience=raw_prefs.get("audience"),
        length=raw_prefs.get("length"),
    )

    # 7. Entities
    entities: List[MentionedEntity] = []
    for raw_ent in wire.get("entities") or ():
        if isinstance(raw_ent, dict):
            name = raw_ent.get("name")
            cat_str = raw_ent.get("category", EntityCategory.OTHER.value)
        elif isinstance(raw_ent, str):
            name = raw_ent
            cat_str = EntityCategory.OTHER.value
        else:
            continue
        if name and str(name).strip():
            try:
                cat = EntityCategory(cat_str)
            except ValueError:
                cat = EntityCategory.OTHER
            entities.append(MentionedEntity(name=str(name).strip(), category=cat))

    # 8. Ambiguities
    ambiguities: List[SemanticAmbiguity] = []
    for raw_amb in wire.get("ambiguities") or ():
        desc = str(raw_amb).strip() if isinstance(raw_amb, str) else (raw_amb.get("description") if isinstance(raw_amb, dict) else "")
        if desc:
            ambiguities.append(SemanticAmbiguity(kind=AmbiguityKind.OTHER, description=desc))

    # 9. Context Dependencies (Rules 3 & 8)
    dependencies: List[ContextDependency] = []
    for ref in references:
        dependencies.append(
            ContextDependency(
                description=f"unresolved reference: {ref.expression}",
                category=ContextDependencyCategory.PRIOR_CONTEXT_UNSPECIFIED,
                unresolved_reference=ref.expression,
            )
        )

    attachments: Tuple[AttachmentReference, ...] = ()
    if input_data is not None and getattr(input_data, "attachments", None):
        attachments = tuple(input_data.attachments)
        for att in attachments:
            dependencies.append(
                ContextDependency(
                    description=f"current attachment: {att.name or att.identifier or 'unnamed'}",
                    category=ContextDependencyCategory.CURRENT_ATTACHMENT,
                )
            )

    # 10. Confidence
    confidence = SemanticConfidence(
        goal=ConfidenceLevel.UNCERTAIN,
        operations=ConfidenceLevel.UNCERTAIN,
        references=ConfidenceLevel.UNCERTAIN,
        constraints=ConfidenceLevel.UNCERTAIN,
        overall=_confidence_bucket(raw_confidence),
    )

    raw_text = getattr(input_data, "raw_text", "") if input_data is not None else ""

    return DecodedRequest(
        raw_text=raw_text,
        goal=goal,
        operations=tuple(operations),
        constraints=constraints,
        output_preferences=output_preferences,
        entities=tuple(entities),
        references=tuple(references),
        temporal_references=tuple(temporal_references),
        attachments=attachments,
        dependencies=tuple(dependencies),
        ambiguities=tuple(ambiguities),
        confidence=confidence,
    )
