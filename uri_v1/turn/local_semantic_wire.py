"""Local Semantic Decoder Wire Schema and Normalizer for Qwen3-14B (Batch A2.4).

Defines the JSON schema, system prompts, and deterministic normalizer for the
14B control evaluation across Modes A, B, and C.
"""

from __future__ import annotations

from enum import Enum
import json
import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from uri_v1.turn.active_context import ActiveContext
from uri_v1.turn.turn_frame import TurnFrame
from uri_v1.turn.contracts import (
    AmbiguityKind,
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
    SemanticConfidence,
    SemanticOperation,
    SemanticReference,
    TemporalReference,
)
from uri_v1.turn.needle_wire import (
    DecodeError,
    DecodeErrorReason,
    _dedupe,
)

QWEN14B_WIRE_SCHEMA_NAME = "decoded_request"

QWEN14B_WIRE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "goal": {
            "type": "string",
            "description": "Concise phrase stating the user's primary intended outcome.",
        },
        "intent_family": {
            "type": "string",
            "enum": [f.value for f in IntentFamily],
            "description": "Broad category of the user's intent.",
        },
        "requested_operations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Actions or operations explicitly requested by the user (e.g. 'draft', 'convert', 'open', 'compare').",
        },
        "prohibited_operations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Actions or operations explicitly prohibited, forbidden, or negated by the user (e.g. 'do not send', 'don't open', 'do not reply', 'don't delete').",
        },
        "references": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Referring expression (e.g. 'it', 'this', 'that file', 'same thing', 'earlier one').",
                    },
                    "target_id": {
                        "type": "string",
                        "description": "Matching target ID (e.g. 'x1', 'e1') from active session context if clearly resolved, else empty string.",
                    },
                },
                "required": ["expression", "target_id"],
                "additionalProperties": False,
            },
            "description": "Referring expressions requiring context resolution.",
        },
        "temporal_references": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Temporal expressions mentioned (e.g. 'yesterday', 'tomorrow', '2025', 'next Tuesday').",
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
            "description": "Explicitly named persons, roles, or organizations (e.g. 'Prof. Rao', 'Chief Warden').",
        },
    },
    "required": ["goal", "intent_family", "requested_operations", "prohibited_operations", "references"],
    "additionalProperties": False,
}

SYSTEM_PROMPT_MODE_A = (
    "You are URI's Step-1 Semantic Decoder for the current user turn. "
    "Your job is to understand what the user means and output structured JSON matching the schema.\n"
    "CRITICAL RULES:\n"
    "1. Put explicitly requested actions into 'requested_operations' (e.g. 'draft', 'convert', 'compare').\n"
    "2. Put explicitly prohibited, forbidden, or negated actions into 'prohibited_operations' (e.g. 'send', 'open', 'delete'). NEVER put negated actions into requested_operations.\n"
    "3. Extract all pronouns ('this', 'that', 'it', 'them') and deictic noun phrases ('that file', 'earlier one', 'same thing') into 'references'. Set 'target_id' to empty string unless an explicit active context was provided.\n"
    "4. Do NOT invent outside context, files, people, or prior actions not mentioned in the message."
)

SYSTEM_PROMPT_MODE_B = (
    "You are URI's Step-1 Semantic Decoder for the current user turn. "
    "You are provided with the user message and deterministic pre-semantic surface observations (clauses, negation tokens, candidate verbs, candidate referring expressions).\n"
    "CRITICAL RULES:\n"
    "1. Classify candidate verbs into 'requested_operations' or 'prohibited_operations' based on negation cues and meaning. Prohibited/negated actions MUST go into 'prohibited_operations'.\n"
    "2. Record detected referring expressions ('it', 'that file', 'this', 'same thing') into 'references' with target_id=''.\n"
    "3. Do NOT invent entities or files."
)

SYSTEM_PROMPT_MODE_C = (
    "You are URI's Step-1 Semantic Decoder for conversational follow-ups. "
    "You are provided with the user message and active session working memory (active artifacts and entities).\n"
    "CRITICAL RULES:\n"
    "1. For each referring expression in 'references', if it clearly refers to an active session artifact or entity (e.g. 'that file' -> x1, 'them' -> e1), set 'target_id' to that ID. If it does not match, set target_id=''.\n"
    "2. Put requested actions into 'requested_operations', and prohibited/negated actions into 'prohibited_operations'.\n"
    "3. Do NOT invent new artifacts or entities outside the provided active context."
)

SYSTEM_PROMPT_MODE_D = (
    "You are URI's Step-1 Semantic Decoder for conversational follow-ups. "
    "You are provided with the user message, pre-semantic surface cues (clauses, verbs, candidate expressions), and active session working memory (active artifacts and entities).\n"
    "CRITICAL RULES:\n"
    "1. For each referring expression in 'references', if it clearly refers to an active session artifact or entity (e.g. 'that file' -> x1, 'them' -> e1), set 'target_id' to that ID. If it does not match, set target_id=''.\n"
    "2. Put requested actions into 'requested_operations', and prohibited/negated actions into 'prohibited_operations'.\n"
    "3. Do NOT invent new artifacts or entities outside the provided active context."
)


def format_mode_a_prompt(raw_text: str) -> str:
    """Mode A: Raw user turn only."""
    return raw_text


def format_mode_b_prompt(raw_text: str, turn_frame: TurnFrame) -> str:
    """Mode B: Raw user turn + TurnFrame pre-semantic surface cues."""
    lines = [f"User message: {raw_text}", "", "Pre-semantic surface cues:"]
    lines.append(f"- Clauses: {list(turn_frame.clauses)}")
    if turn_frame.negation_spans:
        lines.append(f"- Negation cues: {list(turn_frame.negation_spans)}")
    if turn_frame.candidate_actions:
        lines.append(f"- Candidate action verbs: {[a.verb for a in turn_frame.candidate_actions]}")
    if turn_frame.candidate_references:
        lines.append(f"- Candidate referring expressions: {[r.expression for r in turn_frame.candidate_references]}")
    if turn_frame.temporal_surface_spans:
        lines.append(f"- Temporal surface spans: {list(turn_frame.temporal_surface_spans)}")
    if turn_frame.explicit_formats:
        lines.append(f"- Format cues: {list(turn_frame.explicit_formats)}")
    if turn_frame.explicit_numbers:
        lines.append(f"- Number cues: {list(turn_frame.explicit_numbers)}")
    return "\n".join(lines)


def format_mode_c_prompt(raw_text: str, active_context: Optional[ActiveContext]) -> str:
    """Mode C: Raw user turn + ActiveContext working memory (no TurnFrame)."""
    lines = [f"User message: {raw_text}", "", "Active session working memory:"]
    if active_context is not None:
        if active_context.active_artifacts:
            lines.append(f"- Active artifacts: {[(a.id, a.name) for a in active_context.active_artifacts]}")
        if active_context.active_entities:
            lines.append(f"- Active entities: {[(e.id, e.name) for e in active_context.active_entities]}")
        if active_context.prior_semantic_operation:
            lines.append(f"- Prior operation: {active_context.prior_semantic_operation}")
        if active_context.active_topic:
            lines.append(f"- Active topic: {active_context.active_topic}")
    else:
        lines.append("- (No active session artifacts or entities)")
    return "\n".join(lines)


def format_mode_d_prompt(raw_text: str, turn_frame: TurnFrame, active_context: Optional[ActiveContext]) -> str:
    """Mode D: Raw user turn + TurnFrame surface cues + ActiveContext working memory."""
    lines = [f"User message: {raw_text}", "", "Pre-semantic surface cues:"]
    lines.append(f"- Clauses: {list(turn_frame.clauses)}")
    if turn_frame.candidate_actions:
        lines.append(f"- Candidate action verbs: {[a.verb for a in turn_frame.candidate_actions]}")
    if turn_frame.candidate_references:
        lines.append(f"- Candidate referring expressions: {[r.expression for r in turn_frame.candidate_references]}")
    lines.append("")
    lines.append("Active session working memory:")
    if active_context is not None:
        if active_context.active_artifacts:
            lines.append(f"- Active artifacts: {[(a.id, a.name) for a in active_context.active_artifacts]}")
        if active_context.active_entities:
            lines.append(f"- Active entities: {[(e.id, e.name) for e in active_context.active_entities]}")
        if active_context.prior_semantic_operation:
            lines.append(f"- Prior operation: {active_context.prior_semantic_operation}")
        if active_context.active_topic:
            lines.append(f"- Active topic: {active_context.active_topic}")
    else:
        lines.append("- (No active session artifacts or entities)")
    return "\n".join(lines)


def _classify_reference_kind(expr: str) -> ReferenceKind:
    lower = expr.lower().strip()
    if lower in ("this", "that", "it", "them", "him", "her", "they", "these", "those"):
        return ReferenceKind.PRONOUN
    if any(k in lower for k in ("file", "pdf", "document", "spreadsheet", "table", "letter", "order")):
        return ReferenceKind.DOCUMENT_OR_FILE
    if any(k in lower for k in ("previous", "earlier", "former", "prior", "last", "same thing", "same version")):
        return ReferenceKind.PREVIOUS_ACTION
    return ReferenceKind.OTHER


def _classify_entity_category(cat_str: Optional[str]) -> EntityCategory:
    if not cat_str:
        return EntityCategory.OTHER
    cat_lower = str(cat_str).lower().strip()
    for member in EntityCategory:
        if member.value == cat_lower:
            return member
    if any(w in cat_lower for w in ("person", "human", "individual")):
        return EntityCategory.PERSON
    if any(w in cat_lower for w in ("role", "title", "position")):
        return EntityCategory.ROLE
    if any(w in cat_lower for w in ("org", "department", "company", "group", "committee")):
        return EntityCategory.ORGANIZATION
    if any(w in cat_lower for w in ("file", "doc", "document")):
        return EntityCategory.FILE
    return EntityCategory.OTHER


def normalize_qwen14b_wire(
    wire: Dict[str, Any],
    input_data: Any,
    active_context: Optional[ActiveContext] = None,
    raw_confidence: Optional[float] = None,
) -> DecodedRequest:
    """Deterministically normalizes Qwen3-14B wire JSON into a frozen DecodedRequest."""
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
        raw_req = [raw_req]
    requested_names = _dedupe(tuple(str(x).strip() for x in raw_req if str(x).strip()))

    raw_proh = wire.get("prohibited_operations") or ()
    if not isinstance(raw_proh, (list, tuple)):
        raw_proh = [raw_proh]
    prohibited_names = _dedupe(tuple(str(x).strip() for x in raw_proh if str(x).strip()))

    overlap = set(requested_names) & set(prohibited_names)
    contradictions: List[SemanticAmbiguity] = []
    if overlap:
        for item in sorted(overlap):
            contradictions.append(
                SemanticAmbiguity(
                    kind=AmbiguityKind.MULTIPLE_INTERPRETATIONS,
                    description=f"Action '{item}' marked as both requested and prohibited",
                    candidates=(item,),
                )
            )

    operations: List[SemanticOperation] = []
    for name in requested_names:
        operations.append(SemanticOperation(name=name, status=OperationStatus.REQUESTED))
    for name in prohibited_names:
        operations.append(SemanticOperation(name=name, status=OperationStatus.PROHIBITED))

    # 3. References & Active Context Resolution
    artifact_map: Dict[str, str] = {}
    entity_map: Dict[str, str] = {}
    if active_context is not None:
        artifact_map = {art.id: art.name for art in active_context.active_artifacts}
        entity_map = {ent.id: ent.name for ent in active_context.active_entities}

    raw_refs = wire.get("references") or ()
    if not isinstance(raw_refs, (list, tuple)):
        raw_refs = [raw_refs]

    references: List[SemanticReference] = []
    dependencies: List[ContextDependency] = []

    for item in raw_refs:
        if isinstance(item, dict):
            expr = str(item.get("expression") or "").strip()
            target_id = str(item.get("target_id") or "").strip()
        elif isinstance(item, str):
            expr = item.strip()
            target_id = ""
        else:
            continue

        if not expr:
            continue

        is_resolved = False
        referent_hint: Optional[str] = None

        if target_id:
            if target_id in artifact_map:
                referent_hint = artifact_map[target_id]
                is_resolved = True
            elif target_id in entity_map:
                referent_hint = entity_map[target_id]
                is_resolved = True
            else:
                # Candidate-invention prevention: target_id not in active_context
                # must NEVER be marked resolved. It remains unresolved.
                referent_hint = None
                is_resolved = False

        references.append(
            SemanticReference(
                expression=expr,
                kind=_classify_reference_kind(expr),
                referent_hint=referent_hint,
                is_resolved=is_resolved,
            )
        )

        if not is_resolved:
            dependencies.append(
                ContextDependency(
                    description=f"unresolved reference: {expr}",
                    category=ContextDependencyCategory.PRIOR_CONTEXT_UNSPECIFIED,
                    unresolved_reference=expr,
                )
            )

    # 4. Temporal References
    raw_trefs = wire.get("temporal_references") or ()
    if not isinstance(raw_trefs, (list, tuple)):
        raw_trefs = [raw_trefs]
    temporal_references: List[TemporalReference] = []
    for t in raw_trefs:
        expr = str(t).strip() if isinstance(t, (str, int)) else (t.get("expression") if isinstance(t, dict) else "")
        if expr:
            temporal_references.append(TemporalReference(expression=expr))

    # 5. Constraints
    raw_constraints = wire.get("constraints") or {}
    if not isinstance(raw_constraints, dict):
        raw_constraints = {}
    inc_raw = raw_constraints.get("included_items") or ()
    exc_raw = raw_constraints.get("excluded_items") or ()
    included = _dedupe(tuple(str(x).strip() for x in inc_raw if str(x).strip()))
    excluded = _dedupe(tuple(str(x).strip() for x in exc_raw if str(x).strip()))

    constraints = ConstraintScope(
        included_items=included,
        excluded_items=excluded,
        length_limit=raw_constraints.get("length_limit"),
        language_constraints=raw_constraints.get("language_constraints"),
        prohibited_actions=prohibited_names,
    )

    # 6. Output Preferences
    raw_prefs = wire.get("output_preferences") or {}
    if not isinstance(raw_prefs, dict):
        raw_prefs = {}
    output_preferences = OutputPreferences(
        artifact_type=raw_prefs.get("artifact_type"),
        structure=raw_prefs.get("structure"),
        language=raw_prefs.get("language"),
        language_variant=raw_prefs.get("language_variant"),
        tone=raw_prefs.get("tone"),
        audience=raw_prefs.get("audience"),
    )

    # 7. Entities
    entities: List[MentionedEntity] = []
    for raw_ent in wire.get("entities") or ():
        if isinstance(raw_ent, dict):
            name = raw_ent.get("name")
            cat_str = raw_ent.get("category")
        elif isinstance(raw_ent, str):
            name = raw_ent
            cat_str = None
        else:
            continue
        if name and str(name).strip():
            entities.append(
                MentionedEntity(
                    name=str(name).strip(),
                    category=_classify_entity_category(cat_str),
                )
            )

    # 8. Ambiguities
    ambiguities = list(contradictions)
    for raw_amb in wire.get("ambiguities") or ():
        desc = str(raw_amb).strip() if isinstance(raw_amb, str) else (raw_amb.get("description") if isinstance(raw_amb, dict) else "")
        if desc:
            ambiguities.append(SemanticAmbiguity(kind=AmbiguityKind.OTHER, description=desc))

    # 9. Attachments
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
    overall_conf = ConfidenceLevel.HIGH if not contradictions else ConfidenceLevel.UNCERTAIN
    confidence = SemanticConfidence(
        goal=ConfidenceLevel.HIGH,
        operations=ConfidenceLevel.HIGH if not contradictions else ConfidenceLevel.UNCERTAIN,
        references=ConfidenceLevel.HIGH,
        constraints=ConfidenceLevel.HIGH,
        overall=overall_conf,
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
