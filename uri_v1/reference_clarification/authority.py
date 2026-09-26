"""D5 classification and deterministic R2.9 eligibility, outside frozen RAR."""

from __future__ import annotations

from enum import Enum

from uri_v1.turn.rar_contracts import RARBasis, RARDriverRule, RAROutcome, RARQuery, RARResolution
from uri_v1.turn.rar_clarification_contract import WrongBindingImpact


class AuthorityClass(str, Enum):
    CERTAINTY = "CERTAINTY"
    HEURISTIC = "HEURISTIC"


def impact_value(value: WrongBindingImpact | str | None) -> WrongBindingImpact:
    try:
        return WrongBindingImpact(value)
    except (ValueError, TypeError):
        return WrongBindingImpact.CONSEQUENTIAL


def classify_authority(resolution: RARResolution, query: RARQuery) -> AuthorityClass:
    if resolution.outcome != RAROutcome.RESOLVED or resolution.basis == RARBasis.MODEL_SELECTION:
        return AuthorityClass.HEURISTIC
    rule = resolution.rule_used
    candidate_id = resolution.candidate_id
    anchor = query.deterministic_anchor
    if rule in (RARDriverRule.EXACT_ID, RARDriverRule.EXACT_ALIAS):
        return AuthorityClass.CERTAINTY
    if rule == RARDriverRule.ACTIVE_UI and anchor and anchor.selected_ui_id == candidate_id:
        return AuthorityClass.CERTAINTY
    if rule == RARDriverRule.CURRENT_ATTACHMENT and anchor and anchor.current_attachment_id == candidate_id:
        return AuthorityClass.CERTAINTY
    if rule == RARDriverRule.EXACT_TITLE:
        if anchor and anchor.unique_title_match == candidate_id:
            return AuthorityClass.CERTAINTY
        candidate = query.get_candidate(candidate_id or "")
        if candidate and query.reference_expression.strip().casefold() == candidate.title.strip().casefold():
            matches = [c for c in query.candidates if c.title.strip().casefold() == query.reference_expression.strip().casefold()]
            if len(matches) == 1:
                return AuthorityClass.CERTAINTY
    return AuthorityClass.HEURISTIC


def tentative_eligible(
    resolution: RARResolution,
    remaining_candidate_ids: tuple[str, ...],
    impact: WrongBindingImpact | str | None,
    *,
    model_preference_only: bool = False,
    grounded_evidence: bool = True,
) -> bool:
    """R2.9: separation, grounded evidence, session-local evidence, and impact."""
    if impact_value(impact) not in (WrongBindingImpact.NONE, WrongBindingImpact.RECOVERABLE):
        return False
    if model_preference_only or not grounded_evidence or resolution.basis == RARBasis.MODEL_SELECTION:
        return False
    return (resolution.outcome == RAROutcome.RESOLVED and resolution.candidate_id in remaining_candidate_ids
            or resolution.outcome != RAROutcome.UNKNOWN and len(remaining_candidate_ids) == 1)
