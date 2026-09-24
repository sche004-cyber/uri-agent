"""Deterministic merger from narrow extraction results to DecodedRequest (Batch A2.1).

Combines independent outputs of Schema A, B, C, and D into the deep-frozen
DecodedRequest contract:
  - Schema A -> IntendedOutcome (goal, intent_family)
  - Schema B -> SemanticOperation tuples (requested and prohibited)
  - Schema C -> SemanticReference (strictly is_resolved=False) & TemporalReference tuples
  - Schema D -> ConstraintScope & OutputPreferences
  - Attachments -> propagated strictly from DecodeInput
  - ContextDependencies -> generated deterministically for unresolved references and attachments

ZERO semantic reasoning, ZERO semantic invention. If an extractor failed or declined,
its output remains empty/neutral -- the merger never fabricates missing information.
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

from uri_v1.turn.contracts import (
    AttachmentReference,
    ConfidenceLevel,
    ConstraintScope,
    ContextDependency,
    ContextDependencyCategory,
    DecodedRequest,
    IntendedOutcome,
    IntentFamily,
    OperationStatus,
    OutputPreferences,
    ReferenceKind,
    SemanticConfidence,
    SemanticOperation,
    SemanticReference,
    TemporalReference,
)
from uri_v1.turn.decoder import DecodeInput
from uri_v1.turn.needle_narrow import (
    NarrowConstraintsResult,
    NarrowGoalResult,
    NarrowOperationsResult,
    NarrowReferencesResult,
)
from uri_v1.turn.needle_wire import (
    DecodeError,
    DecodeErrorReason,
    _confidence_bucket,
    _dedupe,
)


def _classify_reference_kind(expr: str) -> ReferenceKind:
    """Classifies reference kind based on surface shape only; is_resolved is ALWAYS False."""
    lower = expr.strip().lower()
    if lower in {"this", "that", "it", "them", "these", "those", "him", "her", "they"}:
        return ReferenceKind.PRONOUN
    if any(k in lower for k in ("file", "document", "pdf", "sheet", "spreadsheet", "letter", "report")):
        return ReferenceKind.DOCUMENT_OR_FILE
    if any(k in lower for k in ("previous", "earlier", "former", "prior", "last", "next", "same thing")):
        return ReferenceKind.PREVIOUS_ACTION
    return ReferenceKind.OTHER


def merge_narrow_results(
    goal_res: NarrowGoalResult,
    ops_res: NarrowOperationsResult,
    refs_res: NarrowReferencesResult,
    const_res: NarrowConstraintsResult,
    input_data: Optional[DecodeInput] = None,
    *,
    raise_on_contradiction: bool = True,
) -> DecodedRequest:
    """Deterministically merges 4 narrow extraction results into a DecodedRequest.

    Validation & mapping only -- no semantic inference.
    """
    raw_text = input_data.raw_text if input_data is not None else ""

    # 1. Goal / Intent
    goal_desc = goal_res.goal.strip() if goal_res.goal else ""
    intent_family = goal_res.intent_family if goal_res.intent_family else IntentFamily.UNSPECIFIED
    goal = IntendedOutcome(description=goal_desc, intent_family=intent_family)

    # 2. Operations
    req_ops = ops_res.requested_operations
    proh_ops = ops_res.prohibited_operations
    overlap = set(req_ops) & set(proh_ops)
    if overlap and raise_on_contradiction:
        raise DecodeError(
            DecodeErrorReason.OPERATION_ERROR,
            f"operation(s) marked both requested and prohibited: {sorted(overlap)}",
        )

    operations: List[SemanticOperation] = []
    for name in req_ops:
        if name:
            operations.append(SemanticOperation(name=name, status=OperationStatus.REQUESTED))
    for name in proh_ops:
        if name and name not in overlap:
            operations.append(SemanticOperation(name=name, status=OperationStatus.PROHIBITED))

    # 3. References & Temporal References
    references: List[SemanticReference] = []
    for expr in refs_res.references:
        if expr:
            references.append(
                SemanticReference(
                    expression=expr,
                    kind=_classify_reference_kind(expr),
                    is_resolved=False,  # strictly unresolved in Step 1
                )
            )

    temporal_references: List[TemporalReference] = []
    for expr in refs_res.temporal_references:
        if expr:
            temporal_references.append(TemporalReference(expression=expr))

    # 4. Constraints & Output Preferences
    constraints = const_res.constraints if const_res.constraints is not None else ConstraintScope()
    output_preferences = const_res.output_preferences if const_res.output_preferences is not None else OutputPreferences()

    # 5. Context Dependencies (governing rules 3 & 8)
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
    if input_data is not None and input_data.attachments:
        attachments = tuple(input_data.attachments)
        for att in attachments:
            dependencies.append(
                ContextDependency(
                    description=f"current attachment: {att.name or att.identifier or 'unnamed'}",
                    category=ContextDependencyCategory.CURRENT_ATTACHMENT,
                )
            )

    # 6. Confidence telemetry
    confidences = [
        c
        for c in (
            goal_res.raw_confidence,
            ops_res.raw_confidence,
            refs_res.raw_confidence,
            const_res.raw_confidence,
        )
        if c is not None
    ]
    avg_conf = (sum(confidences) / len(confidences)) if confidences else None
    confidence = SemanticConfidence(
        goal=ConfidenceLevel.UNCERTAIN,
        operations=ConfidenceLevel.UNCERTAIN,
        references=ConfidenceLevel.UNCERTAIN,
        constraints=ConfidenceLevel.UNCERTAIN,
        overall=_confidence_bucket(avg_conf),
    )

    return DecodedRequest(
        raw_text=raw_text,
        goal=goal,
        operations=tuple(operations),
        constraints=constraints,
        output_preferences=output_preferences,
        entities=(),
        references=tuple(references),
        temporal_references=tuple(temporal_references),
        attachments=attachments,
        dependencies=tuple(dependencies),
        ambiguities=(),
        confidence=confidence,
    )
