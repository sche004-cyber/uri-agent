"""Needle 3 wire schema and deterministic normalizer (Batch A2).

DecodeInput -> Needle 3 -> compact wire dict -> THIS deterministic
normalizer -> DecodedRequest.

The normalizer performs NO semantic reasoning. It validates, maps, and
defaults. It never infers a field Needle did not state. If the wire output
is malformed or contradictory, decoding fails truthfully (see DecodeError)
rather than fabricating a DecodedRequest.

The wire schema is intentionally small and flat compared to DecodedRequest:
it must be easy for a 3-generation, base-weight Needle model to emit, and
it deliberately excludes anything execution/routing shaped (no tool names,
capability IDs, Graphify nodes, workflow IDs, provider names, Edge
decisions, execution plans, or final answers -- see WIRE_SCHEMA).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
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

WIRE_TOOL_NAME = "decode_request"

SYSTEM_PROMPT = (
    "You are a semantic decoder for the current user message only. "
    "You must always call decode_request exactly once for every message, with no exceptions. "
    "Fill its fields using only the current message text. Do not use outside knowledge, "
    "prior turns, or invented identities. Leave a field empty/omitted if the message does not "
    "state it. Do not resolve pronouns like 'this', 'that', 'it', 'them' to specific things - "
    "record them as unresolved references instead. Never decline to call decode_request."
)

# JSON Schema for the single structured-extraction tool Needle is offered.
# Deliberately excludes: tool names, capability IDs, Graphify nodes, workflow
# IDs, provider names, Edge decisions, execution plans, final answers.
WIRE_SCHEMA: Dict[str, Any] = {
    "name": WIRE_TOOL_NAME,
    "description": "Always call this exactly once to record the semantic decoding of the current user message.",
    "parameters": {
        "type": "object",
        "properties": {
            "goal": {"type": "string", "description": "One short phrase: the user's intended outcome."},
            "intent_family": {
                "type": "string",
                "enum": [f.value for f in IntentFamily],
            },
            "operations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "status": {"type": "string", "enum": [s.value for s in OperationStatus]},
                    },
                    "required": ["name", "status"],
                },
            },
            "references": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string"},
                        "kind": {"type": "string", "enum": [k.value for k in ReferenceKind]},
                    },
                    "required": ["expression"],
                },
            },
            "temporal_references": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"expression": {"type": "string"}},
                    "required": ["expression"],
                },
            },
            "constraints": {
                "type": "object",
                "properties": {
                    "included_items": {"type": "array", "items": {"type": "string"}},
                    "excluded_items": {"type": "array", "items": {"type": "string"}},
                    "length_limit": {"type": "string"},
                    "language_constraints": {"type": "string"},
                },
            },
            "output_preferences": {
                "type": "object",
                "properties": {
                    "artifact_type": {"type": "string"},
                    "tone": {"type": "string"},
                    "audience": {"type": "string"},
                    "language": {"type": "string"},
                    "language_variant": {"type": "string"},
                },
            },
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}, "category": {"type": "string"}},
                    "required": ["name"],
                },
            },
            "ambiguities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"description": {"type": "string"}},
                    "required": ["description"],
                },
            },
        },
        "required": ["goal"],
        "additionalProperties": False,
    },
}


class DecodeErrorReason(str, Enum):
    """Failure taxonomy for Needle wire decoding (Batch A2 section 12)."""

    GOAL_ERROR = "GOAL_ERROR"
    OPERATION_ERROR = "OPERATION_ERROR"
    NEGATION_ERROR = "NEGATION_ERROR"
    REFERENCE_ERROR = "REFERENCE_ERROR"
    CONTEXT_INVENTION = "CONTEXT_INVENTION"
    CONSTRAINT_ERROR = "CONSTRAINT_ERROR"
    OUTPUT_PREFERENCE_ERROR = "OUTPUT_PREFERENCE_ERROR"
    ENTITY_ERROR = "ENTITY_ERROR"
    TEMPORAL_ERROR = "TEMPORAL_ERROR"
    AMBIGUITY_ERROR = "AMBIGUITY_ERROR"
    MALFORMED_OUTPUT = "MALFORMED_OUTPUT"
    UNKNOWN_FIELD = "UNKNOWN_FIELD"
    MISSING_REQUIRED_STRUCTURE = "MISSING_REQUIRED_STRUCTURE"
    OVERCONFIDENT_ERROR = "OVERCONFIDENT_ERROR"


class DecodeError(Exception):
    """Raised when Needle wire output cannot be truthfully normalized.

    The normalizer never fabricates a DecodedRequest from malformed or
    contradictory wire output; it raises this instead.
    """

    def __init__(self, reason: DecodeErrorReason, detail: str) -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason.value}: {detail}")


def _confidence_bucket(raw: Optional[float]) -> ConfidenceLevel:
    """Deterministically bucket Needle's single overall confidence float.

    Needle 3 (generation 3, base weights) exposes exactly one overall
    ``confidence`` float per response -- never per-field confidence (see
    research_notes/Edge runtime evaluation/needle.md and the A2 live
    qualification evidence). This bucketing is a URIv1 implementation
    decision, not something Needle reports; it is applied only to the
    ``overall`` confidence dimension. Aspect-level confidence dimensions
    (goal/operations/references/constraints) are never derived from it --
    see normalize_wire.
    """
    if raw is None:
        return ConfidenceLevel.UNCERTAIN
    if raw >= 0.75:
        return ConfidenceLevel.HIGH
    if raw >= 0.5:
        return ConfidenceLevel.MEDIUM
    if raw >= 0.25:
        return ConfidenceLevel.LOW
    return ConfidenceLevel.UNCERTAIN


def _dedupe(items: Tuple[str, ...]) -> Tuple[str, ...]:
    seen: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.append(item)
    return tuple(seen)


def normalize_wire(
    wire: Dict[str, Any],
    input_data: Any,
    *,
    raw_confidence: Optional[float] = None,
) -> DecodedRequest:
    """Deterministically map validated Needle wire output to a DecodedRequest.

    Performs validation and mapping only -- no semantic reasoning. Raises
    DecodeError for malformed, missing-required, or contradictory input.
    """
    if not isinstance(wire, dict):
        raise DecodeError(DecodeErrorReason.MALFORMED_OUTPUT, "wire output is not an object")

    goal_text = wire.get("goal")
    if not isinstance(goal_text, str) or not goal_text.strip():
        raise DecodeError(
            DecodeErrorReason.MISSING_REQUIRED_STRUCTURE,
            "wire output has no non-empty 'goal' field",
        )

    raw_intent_family = wire.get("intent_family")
    try:
        intent_family = IntentFamily(raw_intent_family) if raw_intent_family else IntentFamily.UNSPECIFIED
    except ValueError:
        intent_family = IntentFamily.UNSPECIFIED

    goal = IntendedOutcome(description=goal_text.strip(), intent_family=intent_family)

    operations: List[SemanticOperation] = []
    requested_names: List[str] = []
    prohibited_names: List[str] = []
    for raw_op in wire.get("operations") or ():
        if not isinstance(raw_op, dict):
            continue
        name = raw_op.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        try:
            status = OperationStatus(raw_op.get("status", OperationStatus.REQUESTED.value))
        except ValueError:
            status = OperationStatus.REQUESTED
        operations.append(SemanticOperation(name=name.strip(), status=status, target=raw_op.get("target")))
        (requested_names if status == OperationStatus.REQUESTED else prohibited_names).append(name.strip())

    overlap = set(requested_names) & set(prohibited_names)
    if overlap:
        raise DecodeError(
            DecodeErrorReason.OPERATION_ERROR,
            f"operation(s) marked both requested and prohibited: {sorted(overlap)}",
        )

    references: List[SemanticReference] = []
    for raw_ref in wire.get("references") or ():
        if not isinstance(raw_ref, dict):
            continue
        expression = raw_ref.get("expression")
        if not isinstance(expression, str) or not expression.strip():
            continue
        try:
            kind = ReferenceKind(raw_ref.get("kind", ReferenceKind.OTHER.value))
        except ValueError:
            kind = ReferenceKind.OTHER
        # is_resolved is never true from Needle wire output: Step 1 never
        # resolves references (governing rule 3). A malformed wire payload
        # claiming resolution would be context invention.
        if raw_ref.get("is_resolved"):
            raise DecodeError(
                DecodeErrorReason.CONTEXT_INVENTION,
                f"wire output claims resolved reference '{expression}', which Step 1 must never do",
            )
        references.append(SemanticReference(expression=expression.strip(), kind=kind, is_resolved=False))

    temporal_references: List[TemporalReference] = []
    for raw_tref in wire.get("temporal_references") or ():
        if not isinstance(raw_tref, dict):
            continue
        expression = raw_tref.get("expression")
        if isinstance(expression, str) and expression.strip():
            temporal_references.append(TemporalReference(expression=expression.strip()))

    raw_constraints = wire.get("constraints") or {}
    if not isinstance(raw_constraints, dict):
        raise DecodeError(DecodeErrorReason.CONSTRAINT_ERROR, "'constraints' is not an object")
    constraints = ConstraintScope(
        included_items=_dedupe(tuple(str(x) for x in raw_constraints.get("included_items") or () if x)),
        excluded_items=_dedupe(tuple(str(x) for x in raw_constraints.get("excluded_items") or () if x)),
        length_limit=raw_constraints.get("length_limit"),
        language_constraints=raw_constraints.get("language_constraints"),
    )
    included_excluded_overlap = set(constraints.included_items) & set(constraints.excluded_items)
    if included_excluded_overlap:
        raise DecodeError(
            DecodeErrorReason.CONSTRAINT_ERROR,
            f"item(s) both included and excluded: {sorted(included_excluded_overlap)}",
        )

    raw_output_prefs = wire.get("output_preferences") or {}
    if not isinstance(raw_output_prefs, dict):
        raise DecodeError(DecodeErrorReason.OUTPUT_PREFERENCE_ERROR, "'output_preferences' is not an object")
    output_preferences = OutputPreferences(
        artifact_type=raw_output_prefs.get("artifact_type"),
        tone=raw_output_prefs.get("tone"),
        audience=raw_output_prefs.get("audience"),
        language=raw_output_prefs.get("language"),
        language_variant=raw_output_prefs.get("language_variant"),
    )

    entities: List[MentionedEntity] = []
    for raw_ent in wire.get("entities") or ():
        if not isinstance(raw_ent, dict):
            continue
        name = raw_ent.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        try:
            category = EntityCategory(raw_ent.get("category", EntityCategory.OTHER.value))
        except ValueError:
            category = EntityCategory.OTHER
        entities.append(MentionedEntity(name=name.strip(), category=category))

    ambiguities: List[SemanticAmbiguity] = []
    for raw_amb in wire.get("ambiguities") or ():
        if not isinstance(raw_amb, dict):
            continue
        description = raw_amb.get("description")
        if isinstance(description, str) and description.strip():
            ambiguities.append(
                SemanticAmbiguity(kind=AmbiguityKind.OTHER, description=description.strip())
            )

    # Context dependencies are derived deterministically, not inferred
    # semantically: an unresolved reference or attachment MUST produce a
    # context dependency stating that context is required (governing rule
    # 8) -- this is a mapping rule, not reasoning about what the context is.
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
