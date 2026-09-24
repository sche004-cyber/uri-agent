"""Scaffolded Needle Semantic Decoder (Batch A2.3).

Implements the adaptive, scaffolded architecture:
  1. Deterministic TurnFrame extraction (lexical observations only).
  2. Compact ActiveContext injection (current session memory only).
  3. Narrow Semantic Views with candidate-ID selection.
  4. Adaptive invocation (only calling views warranted by TurnFrame/ActiveContext).
  5. Per-turn transport reset to prevent cross-prompt dialogue bleed.
  6. Deterministic normalizers and merger assembling DecodedRequest.
  7. Strict truthfulness: zero heuristic semantic repair, contradictions preserved.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from uri_v1.turn.active_context import ActiveContext
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
from uri_v1.turn.decoder import DecodeInput, SemanticDecoder
from uri_v1.turn.needle_decoder import (
    NeedleBridgeTransport,
    NeedleTransportError,
    default_venv_python,
)
from uri_v1.turn.needle_semantic_views import (
    SCHEMA_SELECT_GOAL,
    SCHEMA_SELECT_OPERATIONS_ID,
    SCHEMA_SELECT_OUTPUT_SCOPE,
    SCHEMA_SELECT_REFERENCES_ID,
    SYSTEM_SELECT_GOAL,
    SYSTEM_SELECT_OPERATIONS_ID,
    SYSTEM_SELECT_OUTPUT_SCOPE,
    SYSTEM_SELECT_REFERENCES_ID,
)
from uri_v1.turn.needle_wire import DecodeError, DecodeErrorReason, _dedupe
from uri_v1.turn.semantic_envelope import SemanticInputEnvelope
from uri_v1.turn.turn_frame import CandidateAction, CandidateReference, TurnFrame
from uri_v1.turn.turn_frame_builder import build_turn_frame


@dataclass
class ScaffoldedNeedleResult:
    """Detailed result container for scaffolded Needle decoding."""

    decoded_request: Optional[DecodedRequest] = None
    error: Optional[DecodeError] = None
    turn_frame: Optional[TurnFrame] = None
    active_context: Optional[ActiveContext] = None
    called_views: Tuple[str, ...] = ()
    skipped_views: Tuple[str, ...] = ()
    view_latencies_ms: Dict[str, float] = field(default_factory=dict)
    total_latency_ms: float = 0.0
    contradictions: Tuple[str, ...] = ()
    unknown_ids: Tuple[str, ...] = ()
    raw_responses: Dict[str, Any] = field(default_factory=dict)


def _normalize_goal(
    raw_args: Dict[str, Any],
    raw_text: str,
) -> Tuple[IntendedOutcome, ConfidenceLevel]:
    """Normalizes select_goal wire arguments."""
    goal_desc = str(raw_args.get("goal") or "").strip()
    if not goal_desc:
        goal_desc = raw_text.strip()
        goal_conf = ConfidenceLevel.LOW
    else:
        goal_conf = ConfidenceLevel.HIGH

    raw_family = raw_args.get("intent_family")
    family = IntentFamily.UNSPECIFIED
    if isinstance(raw_family, str):
        try:
            family = IntentFamily(raw_family)
        except ValueError:
            family = IntentFamily.UNSPECIFIED
            goal_conf = ConfidenceLevel.MEDIUM

    return IntendedOutcome(description=goal_desc, intent_family=family), goal_conf


def _normalize_operations(
    raw_args: Dict[str, Any],
    turn_frame: TurnFrame,
) -> Tuple[
    Tuple[SemanticOperation, ...],
    Tuple[str, ...],  # prohibited action names
    Tuple[str, ...],  # contradictions
    Tuple[str, ...],  # unknown IDs
    Tuple[SemanticAmbiguity, ...],
    ConfidenceLevel,
]:
    """Maps candidate action IDs back to SemanticOperation instances."""
    candidate_map: Dict[str, CandidateAction] = {
        act.id: act for act in turn_frame.candidate_actions
    }

    raw_req = raw_args.get("requested_action_ids") or raw_args.get("requested_ids") or []
    raw_proh = raw_args.get("prohibited_action_ids") or raw_args.get("prohibited_ids") or []

    req_ids: List[str] = [str(x).strip() for x in raw_req if isinstance(x, (str, int))]
    proh_ids: List[str] = [str(x).strip() for x in raw_proh if isinstance(x, (str, int))]

    contradictions: List[str] = []
    unknown_ids: List[str] = []
    ambiguities: List[SemanticAmbiguity] = []
    operations: List[SemanticOperation] = []
    prohibited_names: List[str] = []

    # Check for contradictions (same ID in both sets)
    common_ids = set(req_ids).intersection(set(proh_ids))
    for cid in sorted(common_ids):
        act = candidate_map.get(cid)
        name = act.verb if act else cid
        contradictions.append(
            f"Action '{name}' (id '{cid}') was selected as both REQUESTED and PROHIBITED"
        )
        ambiguities.append(
            SemanticAmbiguity(
                kind=AmbiguityKind.MULTIPLE_INTERPRETATIONS,
                description=f"Contradictory action status: {name} marked both requested and prohibited",
                candidates=(name,),
            )
        )

    # Process requested
    for aid in req_ids:
        act = candidate_map.get(aid)
        if act is None:
            unknown_ids.append(f"Unknown requested action ID: '{aid}'")
        else:
            operations.append(
                SemanticOperation(name=act.verb, status=OperationStatus.REQUESTED)
            )

    # Process prohibited
    for aid in proh_ids:
        act = candidate_map.get(aid)
        if act is None:
            unknown_ids.append(f"Unknown prohibited action ID: '{aid}'")
        else:
            operations.append(
                SemanticOperation(name=act.verb, status=OperationStatus.PROHIBITED)
            )
            prohibited_names.append(act.verb)

    # Deduplicate operations preserving order
    seen_ops = set()
    deduped_ops: List[SemanticOperation] = []
    for op in operations:
        key = (op.name, op.status)
        if key not in seen_ops:
            seen_ops.add(key)
            deduped_ops.append(op)

    # Confidence evaluation
    if contradictions:
        conf = ConfidenceLevel.UNCERTAIN
    elif unknown_ids:
        conf = ConfidenceLevel.LOW
    else:
        conf = ConfidenceLevel.HIGH

    return (
        tuple(deduped_ops),
        _dedupe(prohibited_names),
        tuple(contradictions),
        tuple(unknown_ids),
        tuple(ambiguities),
        conf,
    )


def _normalize_references(
    raw_args: Dict[str, Any],
    turn_frame: TurnFrame,
    active_context: Optional[ActiveContext],
) -> Tuple[
    Tuple[SemanticReference, ...],
    Tuple[ContextDependency, ...],
    Tuple[SemanticAmbiguity, ...],
    Tuple[str, ...],  # unknown IDs
    ConfidenceLevel,
]:
    """Maps candidate reference IDs and target IDs to SemanticReference contracts."""
    candidate_map: Dict[str, CandidateReference] = {
        ref.id: ref for ref in turn_frame.candidate_references
    }
    artifact_map: Dict[str, str] = {}
    entity_map: Dict[str, str] = {}
    if active_context is not None:
        artifact_map = {art.id: art.name for art in active_context.active_artifacts}
        entity_map = {ent.id: ent.name for ent in active_context.active_entities}

    raw_resolutions = raw_args.get("reference_resolutions") or []
    raw_resolved_ids = raw_args.get("resolved_candidate_ids") or []
    raw_unresolved_ids = raw_args.get("unresolved_candidate_ids") or []

    references: List[SemanticReference] = []
    dependencies: List[ContextDependency] = []
    ambiguities: List[SemanticAmbiguity] = []
    unknown_ids: List[str] = []
    resolved_ref_ids = set()

    if isinstance(raw_resolutions, list) and raw_resolutions:
        for item in raw_resolutions:
            if not isinstance(item, dict):
                continue
            ref_id = str(item.get("reference_id") or "").strip()
            status = str(item.get("status") or "").strip().lower()
            target_id = str(item.get("candidate_target_id") or "").strip()

            cand = candidate_map.get(ref_id)
            if cand is None:
                if ref_id:
                    unknown_ids.append(f"Unknown reference ID: '{ref_id}'")
                continue

            resolved_ref_ids.add(ref_id)
            referent_hint: Optional[str] = None
            is_resolved = False

            if status == "resolved_candidate":
                if target_id in artifact_map:
                    referent_hint = artifact_map[target_id]
                    is_resolved = True
                elif target_id in entity_map:
                    referent_hint = entity_map[target_id]
                    is_resolved = True
                else:
                    unknown_ids.append(
                        f"Reference '{ref_id}' resolved to unknown target ID '{target_id}'"
                    )
                    is_resolved = False
            elif status == "ambiguous":
                ambiguities.append(
                    SemanticAmbiguity(
                        kind=AmbiguityKind.UNRESOLVED_REFERENT,
                        description=f"Ambiguous reference: {cand.expression}",
                        candidates=tuple(sorted(list(artifact_map.values()) + list(entity_map.values()))),
                    )
                )

            references.append(
                SemanticReference(
                    expression=cand.expression,
                    kind=ReferenceKind.OTHER,
                    referent_hint=referent_hint,
                    is_resolved=is_resolved,
                )
            )
            if not is_resolved:
                dependencies.append(
                    ContextDependency(
                        description=f"Unresolved reference: {cand.expression}",
                        category=ContextDependencyCategory.CONTEXT_REQUIRED,
                        unresolved_reference=cand.expression,
                    )
                )
    elif raw_resolved_ids or raw_unresolved_ids:
        resolved_items = [str(x).strip() for x in raw_resolved_ids if x]
        unresolved_items = [str(x).strip() for x in raw_unresolved_ids if x]

        # Extract target IDs from resolved items
        active_target_ids = [x for x in resolved_items if x in artifact_map or x in entity_map]
        target_name = None
        if active_target_ids:
            tid = active_target_ids[0]
            target_name = artifact_map.get(tid) or entity_map.get(tid)

        for ref_id, cand in candidate_map.items():
            if ref_id in resolved_items:
                resolved_ref_ids.add(ref_id)
                if target_name:
                    references.append(
                        SemanticReference(
                            expression=cand.expression,
                            kind=ReferenceKind.OTHER,
                            referent_hint=target_name,
                            is_resolved=True,
                        )
                    )
                else:
                    references.append(
                        SemanticReference(
                            expression=cand.expression,
                            kind=ReferenceKind.OTHER,
                            referent_hint=None,
                            is_resolved=False,
                        )
                    )
                    dependencies.append(
                        ContextDependency(
                            description=f"Unresolved reference: {cand.expression}",
                            category=ContextDependencyCategory.CONTEXT_REQUIRED,
                            unresolved_reference=cand.expression,
                        )
                    )
            elif ref_id in unresolved_items:
                resolved_ref_ids.add(ref_id)
                references.append(
                    SemanticReference(
                        expression=cand.expression,
                        kind=ReferenceKind.OTHER,
                        referent_hint=None,
                        is_resolved=False,
                    )
                )
                dependencies.append(
                    ContextDependency(
                        description=f"Unresolved reference: {cand.expression}",
                        category=ContextDependencyCategory.CONTEXT_REQUIRED,
                        unresolved_reference=cand.expression,
                    )
                )

    # Any candidate references from turn_frame that Needle omitted entirely
    # remain unresolved by default.
    for ref_id, cand in candidate_map.items():
        if ref_id not in resolved_ref_ids:
            references.append(
                SemanticReference(
                    expression=cand.expression,
                    kind=ReferenceKind.OTHER,
                    referent_hint=None,
                    is_resolved=False,
                )
            )
            dependencies.append(
                ContextDependency(
                    description=f"Unresolved reference: {cand.expression}",
                    category=ContextDependencyCategory.CONTEXT_REQUIRED,
                    unresolved_reference=cand.expression,
                )
            )

    conf = ConfidenceLevel.LOW if unknown_ids else ConfidenceLevel.HIGH
    return (
        tuple(references),
        tuple(dependencies),
        tuple(ambiguities),
        tuple(unknown_ids),
        conf,
    )


def _normalize_output_scope(
    raw_args: Dict[str, Any],
    prohibited_actions: Sequence[str],
) -> Tuple[OutputPreferences, ConstraintScope, Tuple[TemporalReference, ...], ConfidenceLevel]:
    """Normalizes select_output_scope wire arguments."""
    artifact_type = raw_args.get("artifact_type")
    tone = raw_args.get("tone")
    audience = raw_args.get("audience")
    language_variant = raw_args.get("language_variant")
    structure = raw_args.get("structure")

    prefs = OutputPreferences(
        artifact_type=str(artifact_type).strip() if artifact_type else None,
        tone=str(tone).strip() if tone else None,
        audience=str(audience).strip() if audience else None,
        language_variant=str(language_variant).strip() if language_variant else None,
        structure=str(structure).strip() if structure else None,
    )

    inc = [str(x).strip() for x in (raw_args.get("included_scope") or []) if x]
    exc = [str(x).strip() for x in (raw_args.get("excluded_scope") or []) if x]
    length_limit = raw_args.get("length_limit")

    temporal_scope = [
        str(x).strip() for x in (raw_args.get("temporal_scope") or []) if x
    ]
    time_range = ", ".join(temporal_scope) if temporal_scope else None

    constraints = ConstraintScope(
        time_range=time_range,
        included_items=_dedupe(inc),
        excluded_items=_dedupe(exc),
        length_limit=str(length_limit).strip() if length_limit else None,
        prohibited_actions=_dedupe(list(prohibited_actions)),
    )

    temporal_refs = tuple(
        TemporalReference(expression=t, is_relative=True) for t in _dedupe(temporal_scope)
    )

    return prefs, constraints, temporal_refs, ConfidenceLevel.HIGH


def _build_entities(turn_frame: TurnFrame) -> Tuple[MentionedEntity, ...]:
    """Builds MentionedEntity instances from TurnFrame surface detections."""
    entities: List[MentionedEntity] = []
    for mention in turn_frame.entity_surface_mentions:
        entities.append(MentionedEntity(name=mention, category=EntityCategory.OTHER))
    return tuple(entities)


def _build_temporal_references(
    turn_frame: TurnFrame,
    extra_temporal: Sequence[TemporalReference] = (),
) -> Tuple[TemporalReference, ...]:
    """Builds TemporalReference instances from TurnFrame and output scope."""
    seen = set()
    result: List[TemporalReference] = []
    for s in turn_frame.temporal_surface_spans:
        if s not in seen:
            seen.add(s)
            result.append(TemporalReference(expression=s, is_relative=True))
    for t in extra_temporal:
        if t.expression not in seen:
            seen.add(t.expression)
            result.append(t)
    return tuple(result)


def _calculate_overall_confidence(
    levels: Sequence[ConfidenceLevel],
) -> ConfidenceLevel:
    """Calculates overall confidence from aspect-level confidences."""
    if ConfidenceLevel.UNCERTAIN in levels:
        return ConfidenceLevel.UNCERTAIN
    if ConfidenceLevel.LOW in levels:
        return ConfidenceLevel.LOW
    if ConfidenceLevel.MEDIUM in levels:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.HIGH


class ScaffoldedNeedleDecoder(SemanticDecoder):
    """Adaptive Semantic Decoder using TurnFrame preprocessor and Needle 3 views."""

    def __init__(
        self,
        transport: Optional[NeedleBridgeTransport] = None,
        max_new_tokens_per_view: int = 150,
        reset_between_turns: bool = True,
    ) -> None:
        if transport is None:
            venv = default_venv_python()
            script = Path(__file__).parent / "needle_bridge_runtime.py"
            transport = NeedleBridgeTransport(venv, script)
        self._transport = transport
        self._max_new_tokens_per_view = max_new_tokens_per_view
        self._reset_between_turns = reset_between_turns

    def decode(self, input_data: DecodeInput) -> DecodedRequest:
        result = self.decode_with_result(input_data)
        if result.error is not None:
            raise result.error
        assert result.decoded_request is not None
        return result.decoded_request

    def decode_with_result(
        self,
        input_data: Union[DecodeInput, str],
        active_context: Optional[ActiveContext] = None,
        reset_state: Optional[bool] = None,
    ) -> ScaffoldedNeedleResult:
        if isinstance(input_data, str):
            input_data = DecodeInput.from_text(input_data)

        raw_text = input_data.raw_text
        turn_frame = build_turn_frame(raw_text, attachments=input_data.attachments)
        envelope = SemanticInputEnvelope(
            current_message=raw_text,
            turn_frame=turn_frame,
            active_context=active_context,
        )

        should_reset = self._reset_between_turns if reset_state is None else reset_state
        if should_reset:
            try:
                self._transport.reset()
            except NeedleTransportError as exc:
                return ScaffoldedNeedleResult(
                    error=DecodeError(
                        DecodeErrorReason.MALFORMED_OUTPUT,
                        f"Failed to reset Needle transport state: {exc}",
                    ),
                    turn_frame=turn_frame,
                    active_context=active_context,
                )

        # Adaptive view selection logic:
        # 1. GoalView: always called
        # 2. OperationView: called if candidate actions exist or negation cues exist
        # 3. ReferenceView: called if candidate references exist or active context has items
        # 4. OutputScopeView: called if output/format cues exist
        call_operations = turn_frame.has_candidate_actions or turn_frame.has_negation
        call_references = turn_frame.has_candidate_references or (
            active_context is not None
            and (active_context.has_active_artifacts or active_context.has_active_entities)
        )
        call_output_scope = turn_frame.has_output_cues

        called_views: List[str] = ["goal"]
        skipped_views: List[str] = []

        if call_operations:
            called_views.append("operations")
        else:
            skipped_views.append("operations")

        if call_references:
            called_views.append("references")
        else:
            skipped_views.append("references")

        if call_output_scope:
            called_views.append("output_scope")
        else:
            skipped_views.append("output_scope")

        view_latencies: Dict[str, float] = {}
        raw_responses: Dict[str, Any] = {}
        turn_started = time.perf_counter()

        # -----------------------------------------------------------------------
        # View 1: Goal
        # -----------------------------------------------------------------------
        goal_prompt = envelope.goal_view.format_prompt()
        v_start = time.perf_counter()
        try:
            resp_goal = self._transport.decode(
                goal_prompt,
                system=SYSTEM_SELECT_GOAL,
                schema=SCHEMA_SELECT_GOAL,
                max_new_tokens=self._max_new_tokens_per_view,
            )
        except NeedleTransportError as exc:
            return ScaffoldedNeedleResult(
                error=DecodeError(DecodeErrorReason.MALFORMED_OUTPUT, f"Goal view transport failure: {exc}"),
                turn_frame=turn_frame,
                active_context=active_context,
                called_views=tuple(called_views),
                skipped_views=tuple(skipped_views),
                total_latency_ms=(time.perf_counter() - turn_started) * 1000.0,
            )
        view_latencies["goal"] = (time.perf_counter() - v_start) * 1000.0
        raw_responses["goal"] = resp_goal

        calls_goal = resp_goal.get("function_calls") or []
        if not calls_goal or calls_goal[0].get("name") != "select_goal":
            return ScaffoldedNeedleResult(
                error=DecodeError(
                    DecodeErrorReason.MISSING_REQUIRED_STRUCTURE,
                    "Needle emitted no select_goal call",
                ),
                turn_frame=turn_frame,
                active_context=active_context,
                called_views=tuple(called_views),
                skipped_views=tuple(skipped_views),
                view_latencies_ms=view_latencies,
                total_latency_ms=(time.perf_counter() - turn_started) * 1000.0,
                raw_responses=raw_responses,
            )
        args_goal = calls_goal[0].get("arguments") or {}
        goal_outcome, conf_goal = _normalize_goal(args_goal, raw_text)

        # -----------------------------------------------------------------------
        # View 2: Operations (Adaptive)
        # -----------------------------------------------------------------------
        all_contradictions: List[str] = []
        all_unknown_ids: List[str] = []
        all_ambiguities: List[SemanticAmbiguity] = []
        prohibited_actions: Tuple[str, ...] = ()
        operations: Tuple[SemanticOperation, ...] = ()
        conf_ops = ConfidenceLevel.HIGH

        if call_operations:
            op_prompt = envelope.operation_view.format_prompt()
            v_start = time.perf_counter()
            try:
                resp_ops = self._transport.decode(
                    op_prompt,
                    system=SYSTEM_SELECT_OPERATIONS_ID,
                    schema=SCHEMA_SELECT_OPERATIONS_ID,
                    max_new_tokens=self._max_new_tokens_per_view,
                )
            except NeedleTransportError as exc:
                return ScaffoldedNeedleResult(
                    error=DecodeError(DecodeErrorReason.MALFORMED_OUTPUT, f"Operations view transport failure: {exc}"),
                    turn_frame=turn_frame,
                    active_context=active_context,
                    called_views=tuple(called_views),
                    skipped_views=tuple(skipped_views),
                    view_latencies_ms=view_latencies,
                    total_latency_ms=(time.perf_counter() - turn_started) * 1000.0,
                )
            view_latencies["operations"] = (time.perf_counter() - v_start) * 1000.0
            raw_responses["operations"] = resp_ops

            calls_ops = resp_ops.get("function_calls") or []
            if calls_ops and calls_ops[0].get("name") == "select_operations":
                args_ops = calls_ops[0].get("arguments") or {}
                (
                    operations,
                    prohibited_actions,
                    contradictions_ops,
                    unknown_ops,
                    ambiguities_ops,
                    conf_ops,
                ) = _normalize_operations(args_ops, turn_frame)
                all_contradictions.extend(contradictions_ops)
                all_unknown_ids.extend(unknown_ops)
                all_ambiguities.extend(ambiguities_ops)
            else:
                all_unknown_ids.append("select_operations call missing or malformed")
                conf_ops = ConfidenceLevel.LOW

        # -----------------------------------------------------------------------
        # View 3: References (Adaptive)
        # -----------------------------------------------------------------------
        references: Tuple[SemanticReference, ...] = ()
        dependencies: Tuple[ContextDependency, ...] = ()
        conf_refs = ConfidenceLevel.HIGH

        if call_references:
            ref_prompt = envelope.reference_view.format_prompt()
            v_start = time.perf_counter()
            try:
                resp_refs = self._transport.decode(
                    ref_prompt,
                    system=SYSTEM_SELECT_REFERENCES_ID,
                    schema=SCHEMA_SELECT_REFERENCES_ID,
                    max_new_tokens=self._max_new_tokens_per_view,
                )
            except NeedleTransportError as exc:
                return ScaffoldedNeedleResult(
                    error=DecodeError(DecodeErrorReason.MALFORMED_OUTPUT, f"Reference view transport failure: {exc}"),
                    turn_frame=turn_frame,
                    active_context=active_context,
                    called_views=tuple(called_views),
                    skipped_views=tuple(skipped_views),
                    view_latencies_ms=view_latencies,
                    total_latency_ms=(time.perf_counter() - turn_started) * 1000.0,
                )
            view_latencies["references"] = (time.perf_counter() - v_start) * 1000.0
            raw_responses["references"] = resp_refs

            calls_refs = resp_refs.get("function_calls") or []
            if calls_refs and calls_refs[0].get("name") == "select_references":
                args_refs = calls_refs[0].get("arguments") or {}
                (
                    references,
                    dependencies,
                    ambiguities_refs,
                    unknown_refs,
                    conf_refs,
                ) = _normalize_references(args_refs, turn_frame, active_context)
                all_unknown_ids.extend(unknown_refs)
                all_ambiguities.extend(ambiguities_refs)
            else:
                all_unknown_ids.append("select_references call missing or malformed")
                conf_refs = ConfidenceLevel.LOW

        # -----------------------------------------------------------------------
        # View 4: Output Scope (Adaptive)
        # -----------------------------------------------------------------------
        output_preferences = OutputPreferences()
        constraints = ConstraintScope(prohibited_actions=prohibited_actions)
        scope_temporal: Tuple[TemporalReference, ...] = ()
        conf_scope = ConfidenceLevel.HIGH

        if call_output_scope:
            scope_prompt = envelope.output_scope_view.format_prompt()
            v_start = time.perf_counter()
            try:
                resp_scope = self._transport.decode(
                    scope_prompt,
                    system=SYSTEM_SELECT_OUTPUT_SCOPE,
                    schema=SCHEMA_SELECT_OUTPUT_SCOPE,
                    max_new_tokens=self._max_new_tokens_per_view,
                )
            except NeedleTransportError as exc:
                return ScaffoldedNeedleResult(
                    error=DecodeError(DecodeErrorReason.MALFORMED_OUTPUT, f"Output scope view transport failure: {exc}"),
                    turn_frame=turn_frame,
                    active_context=active_context,
                    called_views=tuple(called_views),
                    skipped_views=tuple(skipped_views),
                    view_latencies_ms=view_latencies,
                    total_latency_ms=(time.perf_counter() - turn_started) * 1000.0,
                )
            view_latencies["output_scope"] = (time.perf_counter() - v_start) * 1000.0
            raw_responses["output_scope"] = resp_scope

            calls_scope = resp_scope.get("function_calls") or []
            if calls_scope and calls_scope[0].get("name") == "select_output_scope":
                args_scope = calls_scope[0].get("arguments") or {}
                (
                    output_preferences,
                    constraints,
                    scope_temporal,
                    conf_scope,
                ) = _normalize_output_scope(args_scope, prohibited_actions)
            else:
                all_unknown_ids.append("select_output_scope call missing or malformed")
                conf_scope = ConfidenceLevel.LOW

        # -----------------------------------------------------------------------
        # Deterministic Merger
        # -----------------------------------------------------------------------
        entities = _build_entities(turn_frame)
        temporal_references = _build_temporal_references(turn_frame, scope_temporal)
        attachments = tuple(input_data.attachments) + tuple(turn_frame.attachments)
        prompt_supplied_context = tuple(turn_frame.clauses)

        overall_conf = _calculate_overall_confidence(
            [conf_goal, conf_ops, conf_refs, conf_scope]
        )
        confidence = SemanticConfidence(
            goal=conf_goal,
            operations=conf_ops,
            references=conf_refs,
            constraints=conf_scope,
            overall=overall_conf,
        )

        decoded_request = DecodedRequest(
            raw_text=raw_text,
            goal=goal_outcome,
            operations=operations,
            prompt_supplied_context=prompt_supplied_context,
            constraints=constraints,
            output_preferences=output_preferences,
            entities=entities,
            references=references,
            temporal_references=temporal_references,
            attachments=attachments,
            dependencies=dependencies,
            ambiguities=tuple(all_ambiguities),
            confidence=confidence,
        )

        total_latency = (time.perf_counter() - turn_started) * 1000.0

        return ScaffoldedNeedleResult(
            decoded_request=decoded_request,
            turn_frame=turn_frame,
            active_context=active_context,
            called_views=tuple(called_views),
            skipped_views=tuple(skipped_views),
            view_latencies_ms=view_latencies,
            total_latency_ms=total_latency,
            contradictions=tuple(all_contradictions),
            unknown_ids=tuple(all_unknown_ids),
            raw_responses=raw_responses,
        )

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> "ScaffoldedNeedleDecoder":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()
