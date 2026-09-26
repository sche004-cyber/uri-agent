"""Build S1 clarification rounds from frozen deterministic RAR outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from uri_v1.turn.rar_contracts import RAROutcome, RARQuery, RARResolution, validate_rar_resolution
from uri_v1.turn.rar_clarification_contract import (
    AttributeOption, BindingState, ClarificationCandidate, ClarificationContract,
    ClarificationKind, CandidateFact, MAX_OPTIONS, WrongBindingImpact, validate_contract,
)
from .attribute_narrowing import recommend_axis
from .authority import AuthorityClass, classify_authority, tentative_eligible
from .facts import project_facts
from .fingerprints import candidate_fingerprint, candidate_set_fingerprint


@dataclass(frozen=True)
class BuildResult:
    state: BindingState
    candidate_id: str | None = None
    contract: ClarificationContract | None = None
    binding_id: str | None = None
    session_id: str | None = None


def build_clarification(
    query: RARQuery, resolution: RARResolution, *, session_id: str, turn_id: str,
    wrong_binding_impact: WrongBindingImpact | str | None, reference_required: bool = True,
    round_index: int = 1, expires_after_seconds: int = 900,
    excluded_ids: tuple[str, ...] = (), answered_axes: tuple[str, ...] = (),
    attribute_narrowed: bool = False, change_of: str | None = None,
    current_binding_id: str | None = None, now: datetime | None = None,
    fact_sources: dict[str, dict[str, str]] | None = None,
    extra_facts: dict[str, tuple[CandidateFact, ...]] | None = None,
    provenance_required: bool = False, parent_locator: str | None = None,
    candidate_locators: dict[str, str] | None = None,
) -> BuildResult:
    validate_rar_resolution(resolution, query.candidates)
    if not session_id or not turn_id or expires_after_seconds <= 0:
        raise ValueError("invalid builder context")
    if resolution.outcome == RAROutcome.RESOLVED:
        candidate_id = resolution.candidate_id
        if not attribute_narrowed and not change_of and classify_authority(resolution, query) == AuthorityClass.CERTAINTY:
            return BuildResult(BindingState.CONFIRMED, candidate_id,
                               binding_id=str(uuid4()), session_id=session_id)
        if not change_of and tentative_eligible(resolution, (candidate_id,), wrong_binding_impact):
            return BuildResult(BindingState.TENTATIVE, candidate_id,
                               binding_id=str(uuid4()), session_id=session_id)
        kind = ClarificationKind.CONFIRM_ONE
        scope = (candidate_id,)
    elif resolution.outcome == RAROutcome.AMBIGUOUS:
        scope = resolution.ambiguous_candidate_ids
        kind = ClarificationKind.CHOOSE_ONE
    elif resolution.outcome == RAROutcome.UNKNOWN:
        if attribute_narrowed and len(query.candidates) == 1:
            scope = (query.candidates[0].id,)
            kind = ClarificationKind.CONFIRM_ONE
        elif not reference_required:
            return BuildResult(BindingState.PENDING)
        else:
            scope = ()
            kind = ClarificationKind.FREE_INPUT_ONLY
    else:
        raise ValueError("unknown RAR outcome")
    if len(scope) == 1 and kind == ClarificationKind.CHOOSE_ONE:
        kind = ClarificationKind.CONFIRM_ONE
    scope_candidates = tuple(query.get_candidate(cid) for cid in scope)
    if any(c is None for c in scope_candidates):
        raise ValueError("RAR scope contains missing candidate")
    axis_result = None
    if kind == ClarificationKind.CHOOSE_ONE:
        # ARN.1 grouping is useful for a flat set, particularly when display cap would hide choices.
        flat = len({c.title.strip().casefold() for c in scope_candidates}) == 1
        axis_result = recommend_axis(scope_candidates, answered_axes) if (flat or len(scope) > MAX_OPTIONS) else None
        if axis_result is not None:
            kind = ClarificationKind.CHOOSE_ATTRIBUTE
    attribute_axis = axis_result[0] if axis_result else None
    attribute_options = tuple(
        AttributeOption(f"a{i}", attribute_axis, value, members)
        for i, (value, members) in enumerate(axis_result[1].items(), 1)
    ) if axis_result else ()
    displayed = scope_candidates[:MAX_OPTIONS] if kind != ClarificationKind.CHOOSE_ATTRIBUTE else ()
    extra_facts = extra_facts or {}
    for cid, facts in extra_facts.items():
        if cid not in query.candidate_ids or any(not f.source or f.key not in (
                "modified", "version", "sender", "thread_subject", "locator") for f in facts):
            raise ValueError("ungrounded extra display fact")
    facts_by_id = {c.id: project_facts(c, (fact_sources or {}).get(c.id)) + extra_facts.get(c.id, ())
                   for c in displayed}
    if kind == ClarificationKind.CHOOSE_ONE:
        signatures = [tuple((fact.key, fact.value) for fact in facts_by_id[c.id]) for c in displayed]
        if len(signatures) != len(set(signatures)):
            raise ValueError("indistinguishable candidates lack grounded display facts")
    keys = tuple(k for k in ("title", "type", "owner", "recency", "modified", "version", "locator", "sender", "thread_subject")
                 if len({next((f.value for f in facts_by_id[c.id] if f.key == k), "") for c in displayed}) > 1)
    candidates = tuple(ClarificationCandidate(
        c.id, c.candidate_type, i, facts_by_id[c.id], keys,
        resolution.rule_used.value if resolution.rule_used else
        (resolution.failure_class.value if resolution.failure_class else "NONE"),
        candidate_fingerprint(c), f"s{i}") for i, c in enumerate(displayed, 1))
    scope_fingerprints = tuple((c.id, candidate_fingerprint(c)) for c in scope_candidates)
    timestamp = now or datetime.now(timezone.utc)
    contract = ClarificationContract(
        ambiguity_id=str(uuid4()), session_id=session_id, turn_id=turn_id,
        round_index=round_index, kind=kind,
        ambiguity_type=resolution.failure_class.value if resolution.failure_class else "NONE",
        original_reference=resolution.reference_expression,
        contrast_exclusions=excluded_ids, candidates=candidates,
        overflow_count=max(0, len(scope) - len(displayed)) if kind == ClarificationKind.CHOOSE_ONE else 0,
        max_options=MAX_OPTIONS, free_input_allowed=True,
        binding_target="RARDeterministicAnchor.selected_ui_id",
        candidate_set_fingerprint=candidate_set_fingerprint(scope_fingerprints, attribute_options),
        created_at=timestamp.isoformat(), expires_at=(timestamp + timedelta(seconds=expires_after_seconds)).isoformat(),
        resolution_basis=resolution.basis.value, attribute_axis=attribute_axis,
        attribute_options=attribute_options, scope_candidate_ids=scope,
        scope_fingerprints=scope_fingerprints, change_of=change_of,
        current_binding_id=current_binding_id, answered_axes=answered_axes,
        provenance_required=provenance_required, parent_locator=parent_locator,
        candidate_locators=tuple((cid, (candidate_locators or {}).get(cid, "")) for cid in scope),
        excluded_fact_values=tuple(f.value for cid in excluded_ids
            if (excluded := query.get_candidate(cid)) is not None for f in project_facts(excluded)
            if f.key in ("title", "owner") and f.value not in {
                own.value for candidate in scope_candidates for own in project_facts(candidate)}),
    )
    validate_contract(contract, query)
    return BuildResult(BindingState.PENDING if not change_of else BindingState.CHANGE_PENDING, contract=contract)
