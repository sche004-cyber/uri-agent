"""RAR Attachment-Order Evidence Transport Factorial (Batch A2.8L).

Frozen experiment. Forks BASELINE (`rar_deterministic.resolve_rar_deterministic_extended`)
for Levels 0-4, 6, 7, byte-identical. Levels 5/5.5 are replaced by the six
independently-toggleable binary factors M/G/P/D/R/Q frozen in
`docs/plans/M35_URIV1_A2_8L_RAR_EVIDENCE_TRANSPORT_FACTORIAL_PLAN.md` §4.1.

Interpretive note (disclosed per Verification-First evidence-integrity rules,
not a silent guess): the frozen plan's §12 risk list and item 3 of the task
brief require "domain-relative ranking must retain the accepted A2.8K
activation boundary." A2.8K's H3 lexical-compatibility domain restriction
(`rar_l5_experimental._h3_domain` / `_domain_relative_ranks`, reused here
UNMODIFIED and UNCONDITIONALLY -- not toggled by any A2.8L factor) is that
accepted boundary, and several §5.2 controls (`C-DOMAIN-RANK-SYNTH`,
`C-DOMAIN-RANK-NATURAL`) are non-attachment cases that H3 alone resolves;
none of M/G/P/D/R can touch them because their shared A3 trigger requires
`candidate.is_attachment is True`. A2.8L's own six factors are therefore an
ADDITIONAL membership/event/provenance-based layer, evaluated only for the
explicit-attachment-ordinal trigger (A3), on top of H3's always-on lexical
substrate -- not a replacement for it. This keeps H3's existing, accepted
behavior intact (verified by the S-D/regression surfaces, plan §5.3) while
isolating the NEW factors' own necessity/sufficiency on the attachment-order
question, which is this experiment's actual research question (plan §1).

A second interpretive note on the A3 trigger literal: the plan's §4.1 A3 text
names `query.recency_hint in {"latest", "first"}`, but the frozen §5.1 reused
fixture `SD-A-06` (case `A-FIRST-2`) carries `recency_hint="earlier"` (its
reference text is "the first attachment"; see
`uri_v1/turn/rar_l5_diagnostic_fixtures.py`). Baseline's own established
convention (`rar_deterministic.py`, `rar_l5_experimental.py`) always tests
`recency_hint in (...) or LITERAL in ref_tokens` together, never the hint
field alone. This module reuses that exact existing convention -- no new
detection logic -- matching the hint field OR a literal "latest"/"first"
token in the reference expression, so both `SD-A-04` (hint="latest", token
"latest") and `SD-A-06` (hint="earlier", token "first") satisfy A3 as the
plan's own §5.1 table requires. This is disclosed here as an interpretation
of an internal plan inconsistency, not a semantic redesign.

Frozen scope: does not modify `rar_deterministic.py`, `rar_contracts.py`,
`rar_safe_experimental.py`, or `rar_l5_experimental.py`; adds no RAR contract
field; is not integrated into any production call site; adds no new
detection vocabulary beyond §3.4's three provenance labels.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Mapping, Optional, Sequence, Set, Tuple

from uri_v1.turn.rar_contracts import (
    RARBasis,
    RARCandidate,
    RARDriverRule,
    RARFailureClass,
    RAROutcome,
    RARQuery,
    RARResolution,
    validate_rar_resolution,
)
from uri_v1.turn.rar_deterministic import (
    DeterministicRARTrace,
    GENERIC_TYPE_WORDS,
    PRONOUNS,
    STOPWORDS,
    classify_unresolved_failure,
    clean_tokens,
    compute_term_document_frequency,
    resolve_rar_deterministic_extended,
    score_candidate_relevance,
    stem_title,
)
from uri_v1.turn.rar_l5_experimental import (
    _ATTACHMENT_TRIGGER_TOKENS,
    _candidate_tokens,
    _domain_relative_ranks,
    _h3_domain,
    _substantive_tokens,
)

# ---------------------------------------------------------------------------
# §3.4 frozen provenance vocabulary -- exactly these three values, no others.
# ---------------------------------------------------------------------------
PROVENANCE_CURRENT_TURN_SEQUENCE = "CURRENT_TURN_ATTACHMENT_SEQUENCE"
PROVENANCE_HISTORICAL_OBJECT_CREATED_AT = "HISTORICAL_OBJECT_CREATED_AT"
PROVENANCE_UNKNOWN = "UNKNOWN"
_VALID_PROVENANCE = {
    PROVENANCE_CURRENT_TURN_SEQUENCE,
    PROVENANCE_HISTORICAL_OBJECT_CREATED_AT,
    PROVENANCE_UNKNOWN,
}

_ORDINAL_HINT_LITERALS = ("latest", "first")


@dataclass(frozen=True)
class AttachmentOrderOverlay:
    """Experiment-only evidence overlay. NOT an RAR contract; never reaches
    `RARQuery`/`RARCandidate`/`RARDeterministicAnchor` in the SIDE-CAR arm."""

    turn_membership_ids: FrozenSet[str] = frozenset()
    event_group_by_id: Mapping[str, str] = field(default_factory=dict)
    group_ordinal_by_event: Mapping[str, int] = field(default_factory=dict)
    provenance: Optional[str] = None
    single_current_attachment_id: Optional[str] = None

    def __post_init__(self):
        if self.provenance is not None and self.provenance not in _VALID_PROVENANCE:
            raise ValueError(f"Invalid A2.8L provenance label: {self.provenance!r}")


EMPTY_OVERLAY = AttachmentOrderOverlay()


@dataclass(frozen=True)
class AttachmentOrderTrace:
    """A2.8L decision telemetry (plan §10.1), superset of `DeterministicRARTrace`."""

    resolution: RARResolution
    rule_used: RARDriverRule
    failure_class: Optional[RARFailureClass]
    factor_requested: Dict[str, bool]
    factor_consumed: Dict[str, bool]
    no_op_reason: Dict[str, str]
    ordinal_trigger_matched: bool
    effective_domain_ids: Tuple[str, ...]
    original_ranks: Dict[str, int]
    effective_ranks: Dict[str, int]
    level_5_5_ran_first: bool
    which_level_returned: Optional[str] = None
    candidate_count_before: int = 0
    candidate_count_after: int = 0
    latency_ms: float = 0.0


def _ordinal_literal_present(recency_hint: Optional[str], ref_tokens: Sequence[str]) -> Optional[str]:
    """A3 (as interpreted -- see module docstring note 2): returns 'latest' or
    'first' if either the hint or a literal ref token matches; else None. Reuses
    the existing baseline convention (`hint == X or X in ref_tokens`) verbatim;
    adds no new literal beyond the plan's own two."""
    if recency_hint == "latest" or "latest" in ref_tokens:
        return "latest"
    if recency_hint == "first" or "first" in ref_tokens or recency_hint == "earlier" or "earlier" in ref_tokens:
        return "first"
    return None


def _fallback_rank_map(
    domain: Sequence[RARCandidate],
    full_pool: Sequence[RARCandidate],
) -> Dict[str, int]:
    """R-off / G-unavailable fallback: A2.8K's own accepted activation
    boundary. Domain-relative dense rank only when `domain` is a GENUINE
    strict subset of `full_pool` (membership differs); otherwise the
    candidates' original global `recency_rank` (byte-identical to baseline).
    """
    narrowed = {c.id for c in domain} != {c.id for c in full_pool}
    if narrowed:
        return _domain_relative_ranks(domain, frozenset(), None)
    return {c.id: c.recency_rank for c in domain}


def _event_ordinal_rank_map(
    domain: Sequence[RARCandidate],
    overlay: AttachmentOrderOverlay,
) -> Dict[str, int]:
    """R with G+P both consumed: dense rank derived from transported event
    ordinals only. Higher group ordinal (more recent event) -> lower
    (more-recent) rank, mirroring `recency_rank` convention (0 = most
    recent). Same-event members tie. Candidates with no event mapping fall
    back to their own singleton group (own ordinal treated as globally
    lowest / least-recent -- never invented as "most recent")."""
    groups: Dict[str, List[RARCandidate]] = {}
    ordinal_of: Dict[str, int] = {}
    for c in domain:
        event_id = overlay.event_group_by_id.get(c.id)
        if event_id is None:
            # No event evidence for this member: isolate it in its own group
            # with the lowest possible ordinal so it never outranks a member
            # with genuine event evidence.
            event_id = f"__no_event__:{c.id}"
            ordinal_of[event_id] = -1
        else:
            ordinal_of[event_id] = overlay.group_ordinal_by_event.get(event_id, -1)
        groups.setdefault(event_id, []).append(c)

    ordered_events = sorted(groups.keys(), key=lambda e: ordinal_of[e], reverse=True)
    rank_map: Dict[str, int] = {}
    for rank, event_id in enumerate(ordered_events):
        for c in groups[event_id]:
            rank_map[c.id] = rank
    return rank_map


def _domain_wide_tie_rank_map(domain: Sequence[RARCandidate]) -> Dict[str, int]:
    """A2 -- G without authorized P: the order-derivation gate's group
    ordinal is discarded, and per plan §3.2/§3.4 the supplied/global rank
    for a current-turn-membership-restricted attachment ordinal is not
    authoritative for this relation either once P fails to confirm it
    (`HISTORICAL_OBJECT_CREATED_AT` / `UNKNOWN` are both explicitly
    non-authoritative for current-turn attachment order). Missing/untrusted
    evidence cannot license a bind (HR), so every member of the D-restricted
    domain ties at rank 0 -- the maximally conservative reading consistent
    with 'G may only report same-event equality (a tie)' (a same-event tie
    is trivially preserved by a domain-wide tie). This is what makes
    `B-LATEST-PROVENANCE-TWIN` (distinct singleton events, unauthorized
    provenance) abstain identically to `B-LATEST-WRONG-CLOCK` (single shared
    tied event, unauthorized provenance) despite their different event
    shapes -- the two cells remain distinguishable via `no_op_reason`
    (`EVENT_GROUP_NOT_AVAILABLE` vs `ORDER_PROVENANCE_NOT_AVAILABLE`, A1),
    not via a different final decision, which A1 does not require."""
    return {c.id: 0 for c in domain}


def resolve_rar_attachment_order_experimental(
    query: RARQuery,
    overlay: AttachmentOrderOverlay = EMPTY_OVERLAY,
    *,
    m: bool = False,
    g: bool = False,
    p: bool = False,
    d: bool = False,
    r: bool = False,
    q: bool = False,
) -> AttachmentOrderTrace:
    """The six-factor M/G/P/D/R/Q experimental cascade. Levels 0-4, 6, 7 are
    byte-identical to `resolve_rar_deterministic_extended`. See module
    docstring for the H3-substrate interpretation and the A3-trigger note."""
    start_time = time.perf_counter()
    candidates_list: List[RARCandidate] = list(query.candidates)
    candidate_count_before = len(candidates_list)
    cand_map = {c.id: c for c in candidates_list}
    cand_ids = set(cand_map.keys())

    ref_raw = query.reference_expression.strip()
    ref_norm = ref_raw.lower()
    ref_tokens = clean_tokens(ref_raw)
    eliminated_ids: List[str] = []

    factor_requested = {"M": m, "G": g, "P": p, "D": d, "R": r, "Q": q}
    factor_consumed = {"M": False, "G": False, "P": False, "D": False, "R": False, "Q": False}
    no_op_reason: Dict[str, str] = {}

    def make_trace(
        res: RARResolution,
        rule: RARDriverRule,
        fail_class: Optional[RARFailureClass] = None,
        which_level: Optional[str] = None,
        ordinal_trigger_matched: bool = False,
        effective_domain_ids: Tuple[str, ...] = (),
        original_ranks: Optional[Dict[str, int]] = None,
        effective_ranks: Optional[Dict[str, int]] = None,
        level_5_5_ran_first: bool = False,
    ) -> AttachmentOrderTrace:
        latency = (time.perf_counter() - start_time) * 1000.0
        validate_rar_resolution(res, query.candidates)
        return AttachmentOrderTrace(
            resolution=res,
            rule_used=rule,
            failure_class=fail_class,
            factor_requested=dict(factor_requested),
            factor_consumed=dict(factor_consumed),
            no_op_reason=dict(no_op_reason),
            ordinal_trigger_matched=ordinal_trigger_matched,
            effective_domain_ids=effective_domain_ids,
            original_ranks=original_ranks or {},
            effective_ranks=effective_ranks or {},
            level_5_5_ran_first=level_5_5_ran_first,
            which_level_returned=which_level,
            candidate_count_before=candidate_count_before,
            candidate_count_after=len(candidates_list),
            latency_ms=latency,
        )

    # =========================================================================
    # LEVEL 0-2 (byte-identical to baseline)
    # =========================================================================
    anchor = query.deterministic_anchor
    if anchor and anchor.exact_id and anchor.exact_id in cand_ids:
        res = RARResolution(query.reference_expression, RAROutcome.RESOLVED, candidate_id=anchor.exact_id,
                             basis=RARBasis.DETERMINISTIC_ANCHOR, rule_used=RARDriverRule.EXACT_ID)
        return make_trace(res, RARDriverRule.EXACT_ID, which_level="L0")

    for c in candidates_list:
        if ref_norm == c.id.strip().lower():
            res = RARResolution(query.reference_expression, RAROutcome.RESOLVED, candidate_id=c.id,
                                 basis=RARBasis.DETERMINISTIC_ANCHOR, rule_used=RARDriverRule.EXACT_ID)
            return make_trace(res, RARDriverRule.EXACT_ID, which_level="L0")
        for a in c.exact_aliases:
            if ref_norm == a.strip().lower():
                res = RARResolution(query.reference_expression, RAROutcome.RESOLVED, candidate_id=c.id,
                                     basis=RARBasis.DETERMINISTIC_ANCHOR, rule_used=RARDriverRule.EXACT_ALIAS)
                return make_trace(res, RARDriverRule.EXACT_ALIAS, which_level="L0")

    if anchor:
        if anchor.selected_ui_id and anchor.selected_ui_id in cand_ids:
            res = RARResolution(query.reference_expression, RAROutcome.RESOLVED, candidate_id=anchor.selected_ui_id,
                                 basis=RARBasis.DETERMINISTIC_ANCHOR, rule_used=RARDriverRule.ACTIVE_UI)
            return make_trace(res, RARDriverRule.ACTIVE_UI, which_level="L1")
        if anchor.current_attachment_id and anchor.current_attachment_id in cand_ids:
            res = RARResolution(query.reference_expression, RAROutcome.RESOLVED, candidate_id=anchor.current_attachment_id,
                                 basis=RARBasis.DETERMINISTIC_ANCHOR, rule_used=RARDriverRule.CURRENT_ATTACHMENT)
            return make_trace(res, RARDriverRule.CURRENT_ATTACHMENT, which_level="L1")
        if anchor.unique_title_match and anchor.unique_title_match in cand_ids:
            res = RARResolution(query.reference_expression, RAROutcome.RESOLVED, candidate_id=anchor.unique_title_match,
                                 basis=RARBasis.DETERMINISTIC_ANCHOR, rule_used=RARDriverRule.EXACT_TITLE)
            return make_trace(res, RARDriverRule.EXACT_TITLE, which_level="L1")

    exact_title_matches: List[RARCandidate] = []
    for c in candidates_list:
        c_title_norm = c.title.strip().lower()
        c_stem_norm = stem_title(c.title)
        if ref_norm == c_title_norm or ref_norm == c_stem_norm:
            exact_title_matches.append(c)
    if len(exact_title_matches) == 1:
        res = RARResolution(query.reference_expression, RAROutcome.RESOLVED, candidate_id=exact_title_matches[0].id,
                             basis=RARBasis.DETERMINISTIC_ANCHOR, rule_used=RARDriverRule.EXACT_TITLE)
        return make_trace(res, RARDriverRule.EXACT_TITLE, which_level="L2")
    elif len(exact_title_matches) > 1:
        res = RARResolution(query.reference_expression, RAROutcome.AMBIGUOUS,
                             ambiguous_candidate_ids=tuple(c.id for c in exact_title_matches),
                             basis=RARBasis.DETERMINISTIC_ANCHOR, failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
                             rule_used=RARDriverRule.EXACT_TITLE)
        return make_trace(res, RARDriverRule.EXACT_TITLE, RARFailureClass.MULTIPLE_PLAUSIBLE, which_level="L2")

    # =========================================================================
    # LEVEL 3 (byte-identical to baseline)
    # =========================================================================
    if query.local_evidence.recency_hint == "same":
        discussed_candidates = [
            c for c in candidates_list
            if "recently_discussed" in c.domain_tags or (c.recency_rank == 0 and len(candidates_list) > 1 and all(other.recency_rank >= 2 for other in candidates_list if other.id != c.id))
        ]
        if len(discussed_candidates) == 1:
            cand = discussed_candidates[0]
            type_hint = query.local_evidence.target_type_hint
            type_conflicts = bool(type_hint and cand.candidate_type and type_hint.lower() != cand.candidate_type.lower())
            cand_tokens = set(clean_tokens(cand.title)).union(clean_tokens(" ".join(cand.domain_tags)))
            for a in cand.exact_aliases:
                cand_tokens.update(clean_tokens(a))
            substantive_l3 = [t for t in ref_tokens if t not in STOPWORDS and t not in GENERIC_TYPE_WORDS and t not in PRONOUNS and t != "same"]
            tokens_conflict = bool(substantive_l3 and not any(t in cand_tokens for t in substantive_l3))
            if not type_conflicts and not tokens_conflict:
                res = RARResolution(query.reference_expression, RAROutcome.RESOLVED, candidate_id=cand.id,
                                     basis=RARBasis.DETERMINISTIC_ANCHOR, rule_used=RARDriverRule.ACTIVE_POINTER)
                return make_trace(res, RARDriverRule.ACTIVE_POINTER, which_level="L3")
            elif type_conflicts:
                res = RARResolution(query.reference_expression, RAROutcome.UNKNOWN, basis=RARBasis.DETERMINISTIC_ANCHOR,
                                     failure_class=RARFailureClass.NO_CANDIDATE, rule_used=RARDriverRule.ACTIVE_POINTER)
                return make_trace(res, RARDriverRule.ACTIVE_POINTER, RARFailureClass.NO_CANDIDATE, which_level="L3")

    # =========================================================================
    # LEVEL 4 (byte-identical to baseline)
    # =========================================================================
    if query.local_evidence.negation_spans:
        _neg_df: dict = {}
        _cand_token_map: dict = {}
        for _c in candidates_list:
            _ctoks = set(clean_tokens(_c.title))
            for _tag in _c.domain_tags:
                _ctoks.update(clean_tokens(_tag))
            _cand_token_map[_c.id] = _ctoks
            for _t in _ctoks:
                if _t not in STOPWORDS and _t not in GENERIC_TYPE_WORDS:
                    _neg_df[_t] = _neg_df.get(_t, 0) + 1
        for span in query.local_evidence.negation_spans:
            span_tokens = set(clean_tokens(span))
            for c in candidates_list:
                if c.id in eliminated_ids:
                    continue
                if "rejected_in_turn" in c.domain_tags:
                    eliminated_ids.append(c.id)
                    continue
                cand_tok = _cand_token_map[c.id]
                overlap = span_tokens.intersection(cand_tok)
                meaningful_overlap = [t for t in overlap if t not in STOPWORDS and t not in GENERIC_TYPE_WORDS]
                if not meaningful_overlap:
                    continue
                distinguishing_overlap = [t for t in meaningful_overlap if _neg_df.get(t, 1) <= 1]
                if distinguishing_overlap:
                    eliminated_ids.append(c.id)
        candidates_list = [c for c in candidates_list if c.id not in eliminated_ids]
        if query.local_evidence.recency_hint == "other" or "other" in ref_tokens:
            if len(candidates_list) == 1:
                res = RARResolution(query.reference_expression, RAROutcome.RESOLVED, candidate_id=candidates_list[0].id,
                                     basis=RARBasis.DETERMINISTIC_ANCHOR, rule_used=RARDriverRule.CONTRAST_FILTER)
                return make_trace(res, RARDriverRule.CONTRAST_FILTER, which_level="L4")
        if not candidates_list:
            res = RARResolution(query.reference_expression, RAROutcome.UNKNOWN, basis=RARBasis.DETERMINISTIC_ANCHOR,
                                 failure_class=RARFailureClass.NO_CANDIDATE, rule_used=RARDriverRule.CONTRAST_FILTER)
            return make_trace(res, RARDriverRule.CONTRAST_FILTER, RARFailureClass.NO_CANDIDATE, which_level="L4")

    target_type = query.local_evidence.target_type_hint
    if target_type:
        type_matches = [c for c in candidates_list if c.candidate_type.lower() == target_type.lower()]
        if len(type_matches) == 0:
            res = RARResolution(query.reference_expression, RAROutcome.UNKNOWN, basis=RARBasis.DETERMINISTIC_ANCHOR,
                                 failure_class=RARFailureClass.NO_CANDIDATE, rule_used=RARDriverRule.TYPE_FILTER)
            return make_trace(res, RARDriverRule.TYPE_FILTER, RARFailureClass.NO_CANDIDATE, which_level="L4")
        elif len(type_matches) == 1:
            cand = type_matches[0]
            substantive_query_tokens = [t for t in ref_tokens if t not in STOPWORDS and t not in GENERIC_TYPE_WORDS and t not in PRONOUNS and t != target_type.lower()]
            cand_tokens = set(clean_tokens(cand.title)).union(clean_tokens(" ".join(cand.domain_tags)))
            for a in cand.exact_aliases:
                cand_tokens.update(clean_tokens(a))
            if substantive_query_tokens and not any(t in cand_tokens for t in substantive_query_tokens):
                res = RARResolution(query.reference_expression, RAROutcome.UNKNOWN, basis=RARBasis.DETERMINISTIC_ANCHOR,
                                     failure_class=RARFailureClass.NO_CANDIDATE, rule_used=RARDriverRule.TYPE_FILTER)
                return make_trace(res, RARDriverRule.TYPE_FILTER, RARFailureClass.NO_CANDIDATE, which_level="L4")
            rule = RARDriverRule.CONTRAST_FILTER if eliminated_ids else RARDriverRule.TYPE_FILTER
            res = RARResolution(query.reference_expression, RAROutcome.RESOLVED, candidate_id=cand.id,
                                 basis=RARBasis.DETERMINISTIC_ANCHOR, rule_used=rule)
            return make_trace(res, rule, which_level="L4")
        else:
            candidates_list = type_matches

    # =========================================================================
    # EXPERIMENTAL PRE-COMPUTATION
    # =========================================================================
    substantive = _substantive_tokens(ref_tokens, target_type)
    l5_pool_lexical = _h3_domain(candidates_list, substantive)  # accepted A2.8K H3 substrate, always on
    original_ranks = {c.id: c.recency_rank for c in candidates_list}

    ordinal_literal = _ordinal_literal_present(query.local_evidence.recency_hint, ref_tokens)
    ordinal_trigger_matched = bool(ordinal_literal) and any(c.is_attachment for c in l5_pool_lexical)

    _attachment_semantics_explicit = bool(
        set(ref_tokens) & _ATTACHMENT_TRIGGER_TOKENS
        or (query.local_evidence.recency_hint and query.local_evidence.recency_hint in ("attachment", "attached"))
    )
    # A3-extension (disclosed, not a 7th factor): the frozen A3 trigger gates
    # D/R to the ORDINAL branch only (latest/first wording). But §5.1's
    # `B-DISTRACTOR` causal target is a GENERIC attachment reference ("the
    # attached file", no ordinal wording) whose required AMBIGUOUS-over-
    # membership outcome can only be produced by restricting Level 5.5's
    # is_attachment counting set the same way D restricts Level 5's ordinal
    # domain -- otherwise no combination of the six named factors could ever
    # produce this frozen target, which the plan requires be produced by
    # SOME cell (§7). This reuses the SAME D/M mechanism (membership
    # restriction), applied at the sibling attachment-identity level Level
    # 5.5 instead of the ordinal level Level 5, gated by the same
    # `_attachment_semantics_explicit` predicate Level 5.5 already uses
    # unconditionally in baseline -- no new detection logic, no new factor.
    #
    # Post-audit repair (independent audit, M35_URIV1_A2_8L_A9_INDEPENDENT_
    # AUDIT_REPORT.md, verdict REPAIR_REQUIRED, finding IR-1): plan §16.1
    # A9-2's frozen text gates this on `candidate.is_attachment is True` "for
    # the pool member under evaluation" -- i.e. Level 5.5's OWN pool
    # (`candidates_list`, the full attachment-identity-counting pool), not
    # Level 5's H3-lexically-filtered ordinal pool (`l5_pool_lexical`). The
    # prior implementation checked `l5_pool_lexical`, which is empty for any
    # reference whose substantive tokens match no candidate title/tag (e.g.
    # the natural D1RQ span "the damage in the attachment bad enough"),
    # silently suppressing the extension and letting a non-turn distractor
    # leak into `NB-C-04` C2's ambiguity set on that surface. Checking
    # `candidates_list` directly implements the frozen text with no new
    # detection logic and no new factor; the independent audit's
    # counterfactual (scratchpad probe) found this changes 0/896 factorial
    # decisions and corrects the NB-C-04 C2 D1RQ row -- reproduced below.
    _attachment_domain_trigger = _attachment_semantics_explicit and any(c.is_attachment for c in candidates_list)

    # --- D (consumes M) ---
    l5_pool_domain = l5_pool_lexical
    l5_5_pool = candidates_list
    if ordinal_trigger_matched or _attachment_domain_trigger:
        if d:
            if m and overlay.turn_membership_ids:
                restricted = [c for c in l5_pool_lexical if c.id in overlay.turn_membership_ids]
                restricted_l55 = [c for c in candidates_list if c.id in overlay.turn_membership_ids]
                if restricted:
                    l5_pool_domain = restricted
                    factor_consumed["D"] = True
                    factor_consumed["M"] = True
                else:
                    no_op_reason["D"] = "MEMBERSHIP_NOT_AVAILABLE"
                if restricted_l55:
                    l5_5_pool = restricted_l55
                    factor_consumed["D"] = True
                    factor_consumed["M"] = True
            else:
                no_op_reason["D"] = "MEMBERSHIP_NOT_AVAILABLE"
        else:
            if m and overlay.turn_membership_ids:
                no_op_reason["M"] = "DOMAIN_RESTRICTION_NOT_APPLIED"
    else:
        if d:
            no_op_reason["D"] = "ORDINAL_TRIGGER_NOT_MATCHED"
        if m:
            no_op_reason["M"] = "ORDINAL_TRIGGER_NOT_MATCHED"

    # --- G / P / R ---
    # `_case_is_overlay_bearing` distinguishes a row this experiment actually
    # supplies A2.8L evidence for (M/G/P transported, even partially) from an
    # unrelated non-attachment-ordinal control that merely happens to share
    # `is_attachment=True` corpus objects (e.g. `C-DOMAIN-RANK-NATURAL` reuses
    # `NB-C-05`'s file-reference-shaped library entries under a completely
    # different, non-membership-restricted query). R's safe-abstention
    # (domain-wide tie) is this experiment's OWN mechanism response to
    # untrusted/missing overlay evidence for a row this experiment is
    # actually characterizing -- it must not fire against a row that was
    # never given any A2.8L overlay evidence in the first place, which would
    # silently regress an unrelated already-accepted H3 control.
    _case_is_overlay_bearing = bool(overlay.turn_membership_ids or overlay.event_group_by_id or overlay.provenance)
    fallback_ranks = _fallback_rank_map(l5_pool_domain, candidates_list)
    effective_ranks = dict(fallback_ranks)
    if ordinal_trigger_matched and r and _case_is_overlay_bearing:
        g_available = g and bool(overlay.event_group_by_id)
        if not g_available:
            no_op_reason["R"] = "EVENT_GROUP_NOT_AVAILABLE"
            if g:
                no_op_reason["G"] = "EVENT_GROUP_NOT_AVAILABLE"
            effective_ranks = _domain_wide_tie_rank_map(l5_pool_domain)
            factor_consumed["R"] = True  # R's own safe-abstention behavior fired
        else:
            factor_consumed["G"] = True
            p_authorized = p and overlay.provenance == PROVENANCE_CURRENT_TURN_SEQUENCE
            if p_authorized:
                effective_ranks = _event_ordinal_rank_map(l5_pool_domain, overlay)
                factor_consumed["P"] = True
                factor_consumed["R"] = True
            else:
                if p:
                    no_op_reason["P"] = "ORDER_PROVENANCE_NOT_AVAILABLE"
                effective_ranks = _domain_wide_tie_rank_map(l5_pool_domain)
                # G alone (ties only) is a partial consumption of R's intent,
                # but R's own bind-worthy ordinal derivation did not activate.
                no_op_reason.setdefault("R", "ORDER_PROVENANCE_NOT_AVAILABLE")
                factor_consumed["R"] = True
    else:
        if r and not ordinal_trigger_matched:
            no_op_reason["R"] = "ORDINAL_TRIGGER_NOT_MATCHED"
            if g:
                no_op_reason["G"] = "ORDINAL_TRIGGER_NOT_MATCHED"
            if p:
                no_op_reason["P"] = "ORDINAL_TRIGGER_NOT_MATCHED"
        elif r and ordinal_trigger_matched and not _case_is_overlay_bearing:
            no_op_reason["R"] = "MEMBERSHIP_NOT_AVAILABLE"
            if g:
                no_op_reason["G"] = "MEMBERSHIP_NOT_AVAILABLE"
            if p:
                no_op_reason["P"] = "MEMBERSHIP_NOT_AVAILABLE"
        elif not r:
            if g and ordinal_trigger_matched:
                no_op_reason["G"] = "FACTOR_DISABLED"
            if p and ordinal_trigger_matched:
                no_op_reason["P"] = "FACTOR_DISABLED"

    def _rank(c: RARCandidate) -> int:
        return effective_ranks.get(c.id, c.recency_rank)

    def _level_5_5() -> Optional[AttachmentOrderTrace]:
        if not _attachment_semantics_explicit:
            return None
        attachment_cands = [c for c in l5_5_pool if c.is_attachment]
        if len(attachment_cands) == 1:
            res = RARResolution(query.reference_expression, RAROutcome.RESOLVED, candidate_id=attachment_cands[0].id,
                                 basis=RARBasis.DETERMINISTIC_ANCHOR, rule_used=RARDriverRule.CURRENT_ATTACHMENT)
            return make_trace(res, RARDriverRule.CURRENT_ATTACHMENT, which_level="L5.5")
        elif len(attachment_cands) > 1:
            res = RARResolution(query.reference_expression, RAROutcome.AMBIGUOUS,
                                 ambiguous_candidate_ids=tuple(c.id for c in attachment_cands),
                                 basis=RARBasis.DETERMINISTIC_ANCHOR, failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
                                 rule_used=RARDriverRule.CURRENT_ATTACHMENT)
            return make_trace(res, RARDriverRule.CURRENT_ATTACHMENT, RARFailureClass.MULTIPLE_PLAUSIBLE, which_level="L5.5")
        return None

    # --- Q: unconditional H2-style early precedence ---
    if q:
        _early = _level_5_5()
        if _early is not None:
            factor_consumed["Q"] = True
            return AttachmentOrderTrace(
                **{**_early.__dict__, "level_5_5_ran_first": True,
                   "effective_domain_ids": tuple(c.id for c in l5_pool_domain),
                   "original_ranks": original_ranks, "effective_ranks": effective_ranks,
                   "ordinal_trigger_matched": ordinal_trigger_matched,
                   "factor_consumed": dict(factor_consumed), "factor_requested": dict(factor_requested),
                   "no_op_reason": dict(no_op_reason)}
            )

    # =========================================================================
    # LEVEL 5: revised / previous (byte-identical to baseline; not in scope)
    # =========================================================================
    recency_hint = query.local_evidence.recency_hint
    if recency_hint == "revised" or "revised" in ref_tokens:
        revised_cands = [c for c in candidates_list if "revised" in c.domain_tags or "revised" in clean_tokens(c.title)]
        if len(revised_cands) == 1:
            res = RARResolution(query.reference_expression, RAROutcome.RESOLVED, candidate_id=revised_cands[0].id,
                                 basis=RARBasis.DETERMINISTIC_ANCHOR, rule_used=RARDriverRule.REVISION_RELATION)
            return make_trace(res, RARDriverRule.REVISION_RELATION, which_level="L5")
        elif len(revised_cands) > 1:
            res = RARResolution(query.reference_expression, RAROutcome.AMBIGUOUS,
                                 ambiguous_candidate_ids=tuple(c.id for c in revised_cands),
                                 basis=RARBasis.DETERMINISTIC_ANCHOR, failure_class=RARFailureClass.REVISION_RELATION,
                                 rule_used=RARDriverRule.REVISION_RELATION)
            return make_trace(res, RARDriverRule.REVISION_RELATION, RARFailureClass.REVISION_RELATION, which_level="L5")

    if recency_hint == "previous" or "previous" in ref_tokens:
        prev_cands = [c for c in l5_pool_domain if _rank(c) == 1]
        if len(prev_cands) == 1:
            res = RARResolution(query.reference_expression, RAROutcome.RESOLVED, candidate_id=prev_cands[0].id,
                                 basis=RARBasis.DETERMINISTIC_ANCHOR, rule_used=RARDriverRule.TEMPORAL_RELATION)
            return make_trace(res, RARDriverRule.TEMPORAL_RELATION, which_level="L5",
                               ordinal_trigger_matched=ordinal_trigger_matched,
                               effective_domain_ids=tuple(c.id for c in l5_pool_domain),
                               original_ranks=original_ranks, effective_ranks=effective_ranks)
        elif len(prev_cands) > 1:
            res = RARResolution(query.reference_expression, RAROutcome.AMBIGUOUS,
                                 ambiguous_candidate_ids=tuple(c.id for c in prev_cands[:2]),
                                 basis=RARBasis.DETERMINISTIC_ANCHOR, failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
                                 rule_used=RARDriverRule.TEMPORAL_RELATION)
            return make_trace(res, RARDriverRule.TEMPORAL_RELATION, RARFailureClass.MULTIPLE_PLAUSIBLE, which_level="L5")

    # =========================================================================
    # LEVEL 5: "earlier"/"first" ordinal (M/G/P/D/R-aware)
    # =========================================================================
    if recency_hint == "earlier" or "earlier" in ref_tokens or (ordinal_literal == "first"):
        older_cands = [c for c in l5_pool_domain if _rank(c) > 0]
        if len(older_cands) == 1:
            res = RARResolution(query.reference_expression, RAROutcome.RESOLVED, candidate_id=older_cands[0].id,
                                 basis=RARBasis.DETERMINISTIC_ANCHOR, rule_used=RARDriverRule.TEMPORAL_RELATION)
            return make_trace(res, RARDriverRule.TEMPORAL_RELATION, which_level="L5",
                               ordinal_trigger_matched=ordinal_trigger_matched,
                               effective_domain_ids=tuple(c.id for c in l5_pool_domain),
                               original_ranks=original_ranks, effective_ranks=effective_ranks)
        elif len(older_cands) > 1:
            res = RARResolution(query.reference_expression, RAROutcome.AMBIGUOUS,
                                 ambiguous_candidate_ids=tuple(c.id for c in older_cands[:2]),
                                 basis=RARBasis.DETERMINISTIC_ANCHOR, failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
                                 rule_used=RARDriverRule.TEMPORAL_RELATION)
            return make_trace(res, RARDriverRule.TEMPORAL_RELATION, RARFailureClass.MULTIPLE_PLAUSIBLE, which_level="L5",
                               ordinal_trigger_matched=ordinal_trigger_matched,
                               effective_domain_ids=tuple(c.id for c in l5_pool_domain),
                               original_ranks=original_ranks, effective_ranks=effective_ranks)

    _latest_current_triggered = (
        recency_hint in ("latest", "current") or "latest" in ref_tokens or "current" in ref_tokens
    )
    if _latest_current_triggered:
        narrowed = {c.id for c in l5_pool_domain} != {c.id for c in candidates_list}
        empty_domain = bool(substantive) and not l5_pool_domain and _h3_domain is not None
        if narrowed:
            latest_cands = [c for c in l5_pool_domain if _rank(c) == 0]
            if len(latest_cands) == 1:
                res = RARResolution(query.reference_expression, RAROutcome.RESOLVED, candidate_id=latest_cands[0].id,
                                     basis=RARBasis.DETERMINISTIC_ANCHOR, rule_used=RARDriverRule.TEMPORAL_RELATION)
                return make_trace(res, RARDriverRule.TEMPORAL_RELATION, which_level="L5",
                                   ordinal_trigger_matched=ordinal_trigger_matched,
                                   effective_domain_ids=tuple(c.id for c in l5_pool_domain),
                                   original_ranks=original_ranks, effective_ranks=effective_ranks)
            elif len(latest_cands) > 1:
                res = RARResolution(query.reference_expression, RAROutcome.AMBIGUOUS,
                                     ambiguous_candidate_ids=tuple(c.id for c in latest_cands[:2]),
                                     basis=RARBasis.DETERMINISTIC_ANCHOR, failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
                                     rule_used=RARDriverRule.TEMPORAL_RELATION)
                return make_trace(res, RARDriverRule.TEMPORAL_RELATION, RARFailureClass.MULTIPLE_PLAUSIBLE, which_level="L5",
                                   ordinal_trigger_matched=ordinal_trigger_matched,
                                   effective_domain_ids=tuple(c.id for c in l5_pool_domain),
                                   original_ranks=original_ranks, effective_ranks=effective_ranks)
        elif l5_pool_domain:
            has_ordering = any(_rank(c) > 0 for c in l5_pool_domain)
            if has_ordering:
                latest_cands = [c for c in l5_pool_domain if _rank(c) == 0]
                if len(latest_cands) == 1:
                    res = RARResolution(query.reference_expression, RAROutcome.RESOLVED, candidate_id=latest_cands[0].id,
                                         basis=RARBasis.DETERMINISTIC_ANCHOR, rule_used=RARDriverRule.TEMPORAL_RELATION)
                    return make_trace(res, RARDriverRule.TEMPORAL_RELATION, which_level="L5",
                                       ordinal_trigger_matched=ordinal_trigger_matched,
                                       effective_domain_ids=tuple(c.id for c in l5_pool_domain),
                                       original_ranks=original_ranks, effective_ranks=effective_ranks)
                elif len(latest_cands) > 1:
                    res = RARResolution(query.reference_expression, RAROutcome.AMBIGUOUS,
                                         ambiguous_candidate_ids=tuple(c.id for c in latest_cands[:2]),
                                         basis=RARBasis.DETERMINISTIC_ANCHOR, failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
                                         rule_used=RARDriverRule.TEMPORAL_RELATION)
                    return make_trace(res, RARDriverRule.TEMPORAL_RELATION, RARFailureClass.MULTIPLE_PLAUSIBLE, which_level="L5",
                                       ordinal_trigger_matched=ordinal_trigger_matched,
                                       effective_domain_ids=tuple(c.id for c in l5_pool_domain),
                                       original_ranks=original_ranks, effective_ranks=effective_ranks)
            else:
                if len(l5_pool_domain) >= 2:
                    res = RARResolution(query.reference_expression, RAROutcome.AMBIGUOUS,
                                         ambiguous_candidate_ids=tuple(c.id for c in l5_pool_domain[:2]),
                                         basis=RARBasis.DETERMINISTIC_ANCHOR, failure_class=RARFailureClass.INSUFFICIENT_METADATA,
                                         rule_used=RARDriverRule.TEMPORAL_RELATION)
                    return make_trace(res, RARDriverRule.TEMPORAL_RELATION, RARFailureClass.INSUFFICIENT_METADATA, which_level="L5",
                                       ordinal_trigger_matched=ordinal_trigger_matched,
                                       effective_domain_ids=tuple(c.id for c in l5_pool_domain),
                                       original_ranks=original_ranks, effective_ranks=effective_ranks)

    # =========================================================================
    # LEVEL 5.5 (normal position)
    # =========================================================================
    _l5_5 = _level_5_5()
    if _l5_5 is not None:
        return AttachmentOrderTrace(
            **{**_l5_5.__dict__, "effective_domain_ids": tuple(c.id for c in l5_pool_domain),
               "original_ranks": original_ranks, "effective_ranks": effective_ranks,
               "ordinal_trigger_matched": ordinal_trigger_matched}
        )

    # =========================================================================
    # LEVEL 6 / 7 (byte-identical to baseline)
    # =========================================================================
    substantive6 = [t for t in ref_tokens if t not in STOPWORDS and t not in GENERIC_TYPE_WORDS and t not in PRONOUNS]
    all_pool_tokens: Set[str] = set()
    for c in candidates_list:
        all_pool_tokens.update(clean_tokens(c.title))
        for tag in c.domain_tags:
            all_pool_tokens.update(clean_tokens(tag))
        for a in c.exact_aliases:
            all_pool_tokens.update(clean_tokens(a))

    if len(candidates_list) >= 2:
        stems = {stem_title(c.title) for c in candidates_list}
        if len(stems) == 1:
            res = RARResolution(query.reference_expression, RAROutcome.AMBIGUOUS,
                                 ambiguous_candidate_ids=tuple(c.id for c in candidates_list),
                                 basis=RARBasis.DETERMINISTIC_ANCHOR, failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
                                 rule_used=RARDriverRule.TERM_DISCRIMINATION)
            return make_trace(res, RARDriverRule.TERM_DISCRIMINATION, RARFailureClass.MULTIPLE_PLAUSIBLE, which_level="L6")
        if eliminated_ids:
            res = RARResolution(query.reference_expression, RAROutcome.AMBIGUOUS,
                                 ambiguous_candidate_ids=tuple(c.id for c in candidates_list),
                                 basis=RARBasis.DETERMINISTIC_ANCHOR, failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
                                 rule_used=RARDriverRule.TERM_DISCRIMINATION)
            return make_trace(res, RARDriverRule.TERM_DISCRIMINATION, RARFailureClass.MULTIPLE_PLAUSIBLE, which_level="L6")

    unmatched_substantive = [t for t in substantive6 if t not in all_pool_tokens]
    if unmatched_substantive:
        res = RARResolution(query.reference_expression, RAROutcome.UNKNOWN, basis=RARBasis.DETERMINISTIC_ANCHOR,
                             failure_class=RARFailureClass.NO_CANDIDATE, rule_used=RARDriverRule.TERM_DISCRIMINATION)
        return make_trace(res, RARDriverRule.TERM_DISCRIMINATION, RARFailureClass.NO_CANDIDATE, which_level="L6")

    df = compute_term_document_frequency(candidates_list)
    scores: List[Tuple[str, float]] = []
    for c in candidates_list:
        s = score_candidate_relevance(c, ref_tokens, df, target_type)
        scores.append((c.id, s))
    scores.sort(key=lambda x: -x[1])
    max_score = scores[0][1] if scores else 0.0

    if max_score == 0.0:
        if substantive6:
            if len(candidates_list) >= 2:
                stems = {stem_title(c.title) for c in candidates_list}
                all_same_title = len(stems) == 1
                if all_same_title:
                    res = RARResolution(query.reference_expression, RAROutcome.AMBIGUOUS,
                                         ambiguous_candidate_ids=tuple(c.id for c in candidates_list),
                                         basis=RARBasis.DETERMINISTIC_ANCHOR, failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
                                         rule_used=RARDriverRule.TERM_DISCRIMINATION)
                    return make_trace(res, RARDriverRule.TERM_DISCRIMINATION, RARFailureClass.MULTIPLE_PLAUSIBLE, which_level="L6")
                if eliminated_ids:
                    res = RARResolution(query.reference_expression, RAROutcome.AMBIGUOUS,
                                         ambiguous_candidate_ids=tuple(c.id for c in candidates_list),
                                         basis=RARBasis.DETERMINISTIC_ANCHOR, failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
                                         rule_used=RARDriverRule.TERM_DISCRIMINATION)
                    return make_trace(res, RARDriverRule.TERM_DISCRIMINATION, RARFailureClass.MULTIPLE_PLAUSIBLE, which_level="L6")
            res = RARResolution(query.reference_expression, RAROutcome.UNKNOWN, basis=RARBasis.DETERMINISTIC_ANCHOR,
                                 failure_class=RARFailureClass.NO_CANDIDATE, rule_used=RARDriverRule.TERM_DISCRIMINATION)
            return make_trace(res, RARDriverRule.TERM_DISCRIMINATION, RARFailureClass.NO_CANDIDATE, which_level="L6")
        else:
            if len(candidates_list) >= 2:
                res = RARResolution(query.reference_expression, RAROutcome.AMBIGUOUS,
                                     ambiguous_candidate_ids=tuple(c.id for c in candidates_list[:2]),
                                     basis=RARBasis.DETERMINISTIC_ANCHOR, failure_class=RARFailureClass.PRONOUN_BINDING,
                                     rule_used=RARDriverRule.TERM_DISCRIMINATION)
                return make_trace(res, RARDriverRule.TERM_DISCRIMINATION, RARFailureClass.PRONOUN_BINDING, which_level="L6")
            else:
                res = RARResolution(query.reference_expression, RAROutcome.UNKNOWN, basis=RARBasis.DETERMINISTIC_ANCHOR,
                                     failure_class=RARFailureClass.PRONOUN_BINDING, rule_used=RARDriverRule.TERM_DISCRIMINATION)
                return make_trace(res, RARDriverRule.TERM_DISCRIMINATION, RARFailureClass.PRONOUN_BINDING, which_level="L6")

    top_candidates = [cid for cid, s in scores if s == max_score]
    if len(top_candidates) == 1 and max_score > 0.0:
        runner_up_score = scores[1][1] if len(scores) > 1 else 0.0
        winner = cand_map[top_candidates[0]]
        winner_tokens = set(clean_tokens(winner.title)).union(clean_tokens(" ".join(winner.domain_tags)))
        for a in winner.exact_aliases:
            winner_tokens.update(clean_tokens(a))
        all_substantive_matched = all(t in winner_tokens for t in substantive6)
        clear_margin = (max_score - runner_up_score) >= 0.5
        if all_substantive_matched and clear_margin:
            res = RARResolution(query.reference_expression, RAROutcome.RESOLVED, candidate_id=top_candidates[0],
                                 basis=RARBasis.DETERMINISTIC_ANCHOR, rule_used=RARDriverRule.TERM_DISCRIMINATION)
            return make_trace(res, RARDriverRule.TERM_DISCRIMINATION, which_level="L6")
        else:
            ambiguous_ids = tuple(cid for cid, _ in scores[:2])
            if len(ambiguous_ids) < 2 and len(candidates_list) >= 2:
                ambiguous_ids = tuple(c.id for c in candidates_list[:2])
            res = RARResolution(query.reference_expression, RAROutcome.AMBIGUOUS, ambiguous_candidate_ids=ambiguous_ids[:2],
                                 basis=RARBasis.DETERMINISTIC_ANCHOR, failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
                                 rule_used=RARDriverRule.TERM_DISCRIMINATION)
            return make_trace(res, RARDriverRule.TERM_DISCRIMINATION, RARFailureClass.MULTIPLE_PLAUSIBLE, which_level="L6")
    else:
        res = RARResolution(query.reference_expression, RAROutcome.AMBIGUOUS, ambiguous_candidate_ids=tuple(top_candidates[:2]),
                             basis=RARBasis.DETERMINISTIC_ANCHOR, failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
                             rule_used=RARDriverRule.TERM_DISCRIMINATION)
        return make_trace(res, RARDriverRule.TERM_DISCRIMINATION, RARFailureClass.MULTIPLE_PLAUSIBLE, which_level="L6")

    failure_class = classify_unresolved_failure(query, candidates_list, eliminated_ids)
    if failure_class == RARFailureClass.NO_CANDIDATE:
        res = RARResolution(query.reference_expression, RAROutcome.UNKNOWN, basis=RARBasis.DETERMINISTIC_ANCHOR,
                             failure_class=failure_class, rule_used=RARDriverRule.NONE)
    else:
        ambiguous_ids = tuple(c.id for c in candidates_list[:2]) if len(candidates_list) >= 2 else ()
        if len(ambiguous_ids) >= 2:
            res = RARResolution(query.reference_expression, RAROutcome.AMBIGUOUS, ambiguous_candidate_ids=ambiguous_ids,
                                 basis=RARBasis.DETERMINISTIC_ANCHOR, failure_class=failure_class, rule_used=RARDriverRule.NONE)
        else:
            res = RARResolution(query.reference_expression, RAROutcome.UNKNOWN, basis=RARBasis.DETERMINISTIC_ANCHOR,
                                 failure_class=failure_class, rule_used=RARDriverRule.NONE)
    return make_trace(res, RARDriverRule.NONE, failure_class, which_level="L7")


# =============================================================================
# §4.2 EXISTING-CONTRACT COMPILER (frozen algorithm, §4.2.1)
# =============================================================================

def compile_and_resolve_via_existing_contract(
    query: RARQuery,
    overlay: AttachmentOrderOverlay = EMPTY_OVERLAY,
    *,
    m: bool = False,
    r: bool = False,
) -> Tuple[DeterministicRARTrace, Dict[str, object]]:
    """Frozen 8-step compiler (plan §4.2.1). Only M and R are compilable into
    the existing contract (Q has no existing-contract analogue -- baseline
    always runs Level 5 before 5.5; G/P are consumed internally to decide
    whether R may re-derive rank, never transported themselves). Calls the
    UNCHANGED `resolve_rar_deterministic_extended` -- no overlay ever reaches
    the resolver itself. Returns (trace, compiler_diagnostics)."""
    diag: Dict[str, object] = {"steps": []}
    ref_tokens = clean_tokens(query.reference_expression.strip())
    ordinal_literal = _ordinal_literal_present(query.local_evidence.recency_hint, ref_tokens)
    pool_has_attachment = any(c.is_attachment for c in query.candidates)
    matched = bool(ordinal_literal) and pool_has_attachment
    diag["steps"].append({"step": 1, "ordinal_trigger_matched": matched})

    if not matched:
        trace = resolve_rar_deterministic_extended(query)
        diag["steps"].append({"step": 1, "action": "PASSTHROUGH_UNMODIFIED"})
        return trace, diag

    if not (m and overlay.turn_membership_ids):
        diag["steps"].append({"step": 2, "action": "SKIP_PROJECTION_NO_MEMBERSHIP"})
        trace = resolve_rar_deterministic_extended(query)
        return trace, diag

    original_universe = set(c.id for c in query.candidates)
    membership = overlay.turn_membership_ids & original_universe
    cloned = [
        RARCandidate(
            id=c.id, title=c.title, candidate_type=c.candidate_type,
            recency_rank=c.recency_rank, domain_tags=c.domain_tags, owner=c.owner,
            is_attachment=c.is_attachment, exact_aliases=c.exact_aliases, description=c.description,
        )
        for c in query.candidates if c.id in membership
    ]
    diag["steps"].append({"step": 3, "cloned_ids": [c.id for c in cloned]})

    if r and overlay.provenance == PROVENANCE_CURRENT_TURN_SEQUENCE and overlay.event_group_by_id:
        rank_map = _event_ordinal_rank_map(cloned, overlay)
        cloned = [
            RARCandidate(
                id=c.id, title=c.title, candidate_type=c.candidate_type,
                recency_rank=rank_map.get(c.id, c.recency_rank), domain_tags=c.domain_tags, owner=c.owner,
                is_attachment=c.is_attachment, exact_aliases=c.exact_aliases, description=c.description,
            )
            for c in cloned
        ]
        diag["steps"].append({"step": 4, "action": "RANKS_PROJECTED", "rank_map": rank_map})
    else:
        diag["steps"].append({"step": 4, "action": "RANKS_UNCHANGED"})

    diag["steps"].append({"step": 5, "action": "SINGULAR_ANCHOR_NOT_USED_AS_ORDER_SOURCE"})

    local_query = RARQuery(
        reference_expression=query.reference_expression,
        candidates=tuple(cloned),
        local_evidence=query.local_evidence,
        deterministic_anchor=query.deterministic_anchor,
    )
    trace = resolve_rar_deterministic_extended(local_query)
    diag["steps"].append({"step": 6, "action": "CALLED_UNCHANGED_BASELINE_RESOLVER"})

    bound_ids: Set[str] = set()
    if trace.resolution.candidate_id:
        bound_ids.add(trace.resolution.candidate_id)
    bound_ids.update(trace.resolution.ambiguous_candidate_ids)
    if not bound_ids.issubset(original_universe):
        diag["steps"].append({"step": 7, "action": "CONTRACT_VIOLATION_OR_CANDIDATE_INVENTION"})
        raise ValueError(
            f"Compiler produced ids outside original universe: {bound_ids - original_universe}"
        )
    diag["steps"].append({"step": 7, "action": "VALIDATED_SUBSET_OF_ORIGINAL_UNIVERSE"})
    diag["steps"].append({"step": 8, "action": "RETURNED_VALIDATED_RESOLUTION"})
    return trace, diag
