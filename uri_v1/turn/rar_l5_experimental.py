"""RAR L5-Experimental Variant (Batch A2.8K).

Diagnostic qualification. This module is a SEPARATE, isolated experimental
fork of `uri_v1/turn/rar_deterministic.py`'s
`resolve_rar_deterministic_extended` -- it does not modify, import-patch, or
replace that module, `rar_contracts.py`, or `rar_safe_experimental.py`. It is
a fork of BASELINE (not of RAR-SAFE), so no S1/S2/S3 behaviour leaks in
(plan §3.1). Existing modules are imported here only for their already-
approved, unmodified helper functions and vocabulary: `clean_tokens`,
`stem_title`, `STOPWORDS`, `GENERIC_TYPE_WORDS`, `PRONOUNS`,
`compute_term_document_frequency`, `score_candidate_relevance`,
`classify_unresolved_failure`, `DeterministicRARTrace` (from
`rar_deterministic`), and the R3(a) recency/temporal/revision/attachment
vocabulary set (from `rar_safe_experimental`, reused byte-identical -- no new
words added, per the A2.8K directive).

Central question under test (plan §0): under exactly what evidence
conditions should Level 5 convert recency into a confident binding, and when
should Level 5.5 attachment-ambiguity handling take precedence?

Three independently toggleable hypotheses plus one diagnostic-only probe,
all scoped to Level 5 / Level 5.5 only. Cascade order and behaviour at every
other level (0-4, 6, 7) are byte-identical to baseline. With every flag off,
`resolve_rar_l5_experimental` is decision-identical to
`resolve_rar_deterministic_extended` on every surface (mandatory equivalence
test, plan §3.1, §9.2).

H1 -- Level-5 evidence floor. A Level-5 single-candidate binding (revised /
    previous / earlier / latest-current -- every commit point in baseline's
    Level 5) commits only if the reference expression carries at
    least one substantive token, where "substantive" excludes STOPWORDS,
    PRONOUNS, GENERIC_TYPE_WORDS, the target type word, and the R3(a)
    recency vocabulary (so ordinary recency/revision/attachment phrasing
    alone never counts as "evidence" for this gate -- it would make the gate
    fire on every recency-worded query regardless of correctness). On
    failure the branch does not return RESOLVED; it falls through to the
    next stage exactly as if the branch had not matched (never abstains in
    its own place -- Level 6 or Level 7 decide the final outcome).

H2 -- Attachment-ambiguity precedence. When the reference expression carries
    explicit attachment semantics (baseline's own unchanged Level 5.5
    trigger set: {"attached", "attachment", "attaches"}, or
    recency_hint in ("attachment", "attached")), Level 5.5's attachment-set
    evaluation runs BEFORE Level 5's ordinal branches, using the exact same
    Level 5.5 logic (single is_attachment=True candidate -> RESOLVED;
    multiple -> AMBIGUOUS; zero -> fall through to Level 5 as normal). No
    redefinition of `is_attachment`; the existing distinction between
    "file-reference object" and "attached in the current turn" (plan §1.1)
    remains exactly as visible in the evidence as it is in baseline.

H3 -- Evidence-compatible ordering domain. Level 5's ORDINAL branches
    (previous / earlier / latest-current only, same scope as H1) compute
    their rank-based relation only over the candidates in the current pool
    that are lexically compatible with the reference's substantive tokens
    (same substantive-token definition as H1): every substantive token must
    appear in the candidate's title, tags, or aliases (`clean_tokens`
    matching, byte-identical to Level 6's own tokenizer -- no stemming, no
    fuzzy matching, no aliases beyond baseline). An empty substantive-token
    set means no domain restriction (baseline full-pool behaviour -- this is
    not an evidence-floor gate, H1 already covers that). An empty compatible
    subset means Level 5 does not bind on this branch and falls through.
    This can incidentally resolve Class-B absent-entity rows (Level 6's own
    absent-entity check then applies), but H3 does not veto an
    already-proposed winner (that is S2's distinct, out-of-scope question,
    per plan §2 scope note) -- it only changes which candidate set the
    ordinal relation is computed over.

    Rank semantics (A2.8K-R1, activation boundary narrowed by A2.8K-R2):
    when the compatible domain is a GENUINE strict subset of the pool
    Level 5 would otherwise see (candidate membership differs, not merely
    list length), the ordinal branches use domain-relative rank (position
    within that subset), not the candidates' original global `recency_rank`
    -- so "the latest X" among a domain of one compatible X resolves to it,
    even if that X's global rank is not 0. When the lexical filter changes
    nothing (including the zero-substantive-tokens case, which by
    definition never narrows), baseline's original global-rank semantics
    and its `has_ordering` gate apply exactly as in
    `resolve_rar_deterministic_extended` -- domain-relative re-ranking must
    never fabricate a rank-0 winner in a domain baseline deliberately left
    without one (R2's regression target,
    `test_rc1_current_conflicting_no_rank0_abstains`).

H4 -- H1 + H2 + H3 combined, unmodified and untuned relative to their
    isolated definitions (plan §9: "do not tune the components based on
    their isolated results before running H4").

DX-1 -- Turn-attachment tie oracle (diagnostic only, never a production
    mechanism, never an adoption candidate). `dx1_tie_ids` is a frozenset of
    candidate ids that the calling harness asserts were attached in the same
    current-turn event and must therefore be treated as tied for Level 5's
    ordinal branches specifically (previous / earlier / latest-current),
    regardless of what their individual `recency_rank` values say. This
    isolates whether a Class-A failure is caused by the rank clock
    (created_at representing something other than current-turn attachment
    order) versus by cascade precedence: if DX-1 alone (h1=h2=h3=False)
    converts a wrong confident binding into a safe AMBIGUOUS, the cause is
    the rank clock / missing turn-attachment-membership evidence, not
    precedence -- a contract/architecture question to escalate, not to fix
    here (plan §2, DX-1 row). No RAR contract field is added; the tie
    assertion lives only in this function's own parameter, never in
    RARCandidate/RARQuery.

Frozen scope (A2.8K plan/directive, restated so this file's diff stays
self-documenting): does NOT modify `rar_deterministic.py`, `rar_contracts.py`,
or `rar_safe_experimental.py`; does NOT wire recency into production; does
NOT add session state, antecedent tracking, aliases, stemming, or
abbreviation normalisation; does NOT redesign S2 or repair the St/Street
known limitation; is NOT integrated into any production call site.
Benchmark/experimental use only.
"""

from __future__ import annotations

import time
from typing import FrozenSet, List, Optional, Sequence, Set, Tuple

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
    score_candidate_relevance,
    stem_title,
)
from uri_v1.turn.rar_safe_experimental import _RECENCY_VOCABULARY

_ATTACHMENT_TRIGGER_TOKENS = {"attached", "attachment", "attaches"}


def _candidate_tokens(candidate: RARCandidate) -> Set[str]:
    toks = set(clean_tokens(candidate.title))
    toks.update(clean_tokens(" ".join(candidate.domain_tags)))
    for alias in candidate.exact_aliases:
        toks.update(clean_tokens(alias))
    return toks


def _substantive_tokens(
    ref_tokens: Sequence[str], target_type: Optional[str]
) -> List[str]:
    """H1/H3-shared 'substantive token' definition. Excludes STOPWORDS,
    PRONOUNS, GENERIC_TYPE_WORDS, the target type word, and the R3(a)
    recency/temporal/revision/attachment vocabulary (byte-identical reuse
    from `rar_safe_experimental`, no new words) -- ordinary recency wording
    is never itself "evidence" of which entity is meant.
    """
    return [
        t for t in ref_tokens
        if t not in STOPWORDS
        and t not in GENERIC_TYPE_WORDS
        and t not in PRONOUNS
        and t not in _RECENCY_VOCABULARY
        and (not target_type or t != target_type.lower())
    ]


def _h3_domain(
    pool: Sequence[RARCandidate],
    substantive: Sequence[str],
) -> List[RARCandidate]:
    """H3: restrict `pool` to candidates lexically compatible with every
    substantive token (title/tags/aliases). No substantive tokens -> no
    restriction (baseline full-pool behaviour; H1 governs the zero-evidence
    case, not H3).
    """
    if not substantive:
        return list(pool)
    compatible = [c for c in pool if all(t in _candidate_tokens(c) for t in substantive)]
    return compatible


def _domain_relative_ranks(
    pool: Sequence[RARCandidate],
    dx1_tie_ids: FrozenSet[str],
    tie_rank: Optional[int],
) -> "dict[str, int]":
    """A2.8K-R1 (repair R1-A). Once H3 has filtered the candidate pool down
    to a compatible domain, the ordinal relation ("previous" / "earlier" /
    "latest"-"current") must be evaluated over POSITION WITHIN THAT DOMAIN,
    not the candidates' original absolute/global `recency_rank` values. A
    domain of {rank 1, rank 3} must be treated as {position 0, position 1},
    exactly as a domain of {rank 0, rank 1} would be -- otherwise "latest"
    can never match a compatible candidate whose global rank happens not to
    be 0, which is precisely the independent audit's `SD-C-02` /
    `NB-D-01` C2 finding (audit §10).

    Ordering source: the same value Level 5 has always used to establish
    order, `RARCandidate.recency_rank` (via `_effective_rank`, so a DX-1 tie
    override is honoured first -- H3 restricts WHICH candidates the ordinal
    relation runs over; it does not change what "tied" means once DX-1 has
    already asserted it). No new ordering key is invented: this reuses the
    exact tie-preserving dense-rank algorithm the natural-boundary harness
    itself already uses to turn `created_at` into `recency_rank`
    (`m35_rar_natural_boundary_harness.build_candidate_pool`) -- sort by the
    existing key, assign 0..N-1 by position, candidates whose (possibly
    DX-1-adjusted) value ties share one domain-relative rank.
    """
    ranked = sorted(pool, key=lambda c: _effective_rank(c, dx1_tie_ids, tie_rank))
    rank_by_id: "dict[str, int]" = {}
    current_rank = -1
    last_val = object()
    for c in ranked:
        val = _effective_rank(c, dx1_tie_ids, tie_rank)
        if val != last_val:
            current_rank += 1
        rank_by_id[c.id] = current_rank
        last_val = val
    return rank_by_id


def _effective_rank(c: RARCandidate, dx1_tie_ids: FrozenSet[str], tie_rank: Optional[int]) -> int:
    """DX-1: candidates in `dx1_tie_ids` share one rank (the minimum rank
    among the tie group actually present in the pool), overriding their
    individually supplied `recency_rank` for Level-5 ordinal comparisons
    only. `tie_rank` is precomputed once per call (see caller).
    """
    if dx1_tie_ids and c.id in dx1_tie_ids and tie_rank is not None:
        return tie_rank
    return c.recency_rank


def resolve_rar_l5_experimental(
    query: RARQuery,
    *,
    h1: bool = False,
    h2: bool = False,
    h3: bool = False,
    dx1_tie_ids: FrozenSet[str] = frozenset(),
) -> DeterministicRARTrace:
    """The existing 7-level cascade with the Level-5/5.5 experimental
    toggles applied. Levels 0-4, 6, and 7 are behaviourally identical to
    `resolve_rar_deterministic_extended`. See module docstring for H1/H2/H3/
    DX-1 semantics and the exact diff boundary.
    """
    start_time = time.perf_counter()
    candidates_list: List[RARCandidate] = list(query.candidates)
    candidate_count_before = len(candidates_list)
    cand_map = {c.id: c for c in candidates_list}
    cand_ids = set(cand_map.keys())

    ref_raw = query.reference_expression.strip()
    ref_norm = ref_raw.lower()
    ref_tokens = clean_tokens(ref_raw)
    eliminated_ids: List[str] = []

    def make_trace(
        res: RARResolution,
        rule: RARDriverRule,
        fail_class: Optional[RARFailureClass] = None,
        scores: Sequence[Tuple[str, float]] = (),
    ) -> DeterministicRARTrace:
        latency = (time.perf_counter() - start_time) * 1000.0
        validate_rar_resolution(res, query.candidates)
        return DeterministicRARTrace(
            resolution=res,
            rule_used=rule,
            failure_class=fail_class,
            candidate_count_before=candidate_count_before,
            candidate_count_after=len(candidates_list),
            latency_ms=latency,
            eliminated_candidate_ids=tuple(eliminated_ids),
            candidate_scores=tuple(scores),
        )

    # =========================================================================
    # LEVEL 0: Verbatim ID / Exact Alias Anchor (identical to baseline)
    # =========================================================================
    anchor = query.deterministic_anchor
    if anchor and anchor.exact_id and anchor.exact_id in cand_ids:
        res = RARResolution(
            reference_expression=query.reference_expression,
            outcome=RAROutcome.RESOLVED,
            candidate_id=anchor.exact_id,
            basis=RARBasis.DETERMINISTIC_ANCHOR,
            rule_used=RARDriverRule.EXACT_ID,
        )
        return make_trace(res, RARDriverRule.EXACT_ID)

    for c in candidates_list:
        if ref_norm == c.id.strip().lower():
            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.RESOLVED,
                candidate_id=c.id,
                basis=RARBasis.DETERMINISTIC_ANCHOR,
                rule_used=RARDriverRule.EXACT_ID,
            )
            return make_trace(res, RARDriverRule.EXACT_ID)
        for a in c.exact_aliases:
            if ref_norm == a.strip().lower():
                res = RARResolution(
                    reference_expression=query.reference_expression,
                    outcome=RAROutcome.RESOLVED,
                    candidate_id=c.id,
                    basis=RARBasis.DETERMINISTIC_ANCHOR,
                    rule_used=RARDriverRule.EXACT_ALIAS,
                )
                return make_trace(res, RARDriverRule.EXACT_ALIAS)

    # =========================================================================
    # LEVEL 1: Active Turn Context Anchors (identical to baseline)
    # =========================================================================
    if anchor:
        if anchor.selected_ui_id and anchor.selected_ui_id in cand_ids:
            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.RESOLVED,
                candidate_id=anchor.selected_ui_id,
                basis=RARBasis.DETERMINISTIC_ANCHOR,
                rule_used=RARDriverRule.ACTIVE_UI,
            )
            return make_trace(res, RARDriverRule.ACTIVE_UI)

        if anchor.current_attachment_id and anchor.current_attachment_id in cand_ids:
            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.RESOLVED,
                candidate_id=anchor.current_attachment_id,
                basis=RARBasis.DETERMINISTIC_ANCHOR,
                rule_used=RARDriverRule.CURRENT_ATTACHMENT,
            )
            return make_trace(res, RARDriverRule.CURRENT_ATTACHMENT)

        if anchor.unique_title_match and anchor.unique_title_match in cand_ids:
            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.RESOLVED,
                candidate_id=anchor.unique_title_match,
                basis=RARBasis.DETERMINISTIC_ANCHOR,
                rule_used=RARDriverRule.EXACT_TITLE,
            )
            return make_trace(res, RARDriverRule.EXACT_TITLE)

    # =========================================================================
    # LEVEL 2: Strict Verbatim Title Match (identical to baseline)
    # =========================================================================
    exact_title_matches: List[RARCandidate] = []
    for c in candidates_list:
        c_title_norm = c.title.strip().lower()
        c_stem_norm = stem_title(c.title)
        if ref_norm == c_title_norm or ref_norm == c_stem_norm:
            exact_title_matches.append(c)

    if len(exact_title_matches) == 1:
        res = RARResolution(
            reference_expression=query.reference_expression,
            outcome=RAROutcome.RESOLVED,
            candidate_id=exact_title_matches[0].id,
            basis=RARBasis.DETERMINISTIC_ANCHOR,
            rule_used=RARDriverRule.EXACT_TITLE,
        )
        return make_trace(res, RARDriverRule.EXACT_TITLE)
    elif len(exact_title_matches) > 1:
        res = RARResolution(
            reference_expression=query.reference_expression,
            outcome=RAROutcome.AMBIGUOUS,
            ambiguous_candidate_ids=tuple(c.id for c in exact_title_matches),
            basis=RARBasis.DETERMINISTIC_ANCHOR,
            failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
            rule_used=RARDriverRule.EXACT_TITLE,
        )
        return make_trace(res, RARDriverRule.EXACT_TITLE, RARFailureClass.MULTIPLE_PLAUSIBLE)

    # =========================================================================
    # LEVEL 3: Active Pointer / Continuation Binding (identical to baseline)
    # =========================================================================
    if query.local_evidence.recency_hint == "same":
        discussed_candidates = [
            c for c in candidates_list
            if "recently_discussed" in c.domain_tags or (c.recency_rank == 0 and len(candidates_list) > 1 and all(other.recency_rank >= 2 for other in candidates_list if other.id != c.id))
        ]
        if len(discussed_candidates) == 1:
            cand = discussed_candidates[0]
            type_hint = query.local_evidence.target_type_hint
            type_conflicts = bool(
                type_hint
                and cand.candidate_type
                and type_hint.lower() != cand.candidate_type.lower()
            )

            cand_tokens = set(clean_tokens(cand.title)).union(clean_tokens(" ".join(cand.domain_tags)))
            for a in cand.exact_aliases:
                cand_tokens.update(clean_tokens(a))
            substantive_l3 = [
                t for t in ref_tokens
                if t not in STOPWORDS and t not in GENERIC_TYPE_WORDS and t not in PRONOUNS and t != "same"
            ]
            tokens_conflict = bool(substantive_l3 and not any(t in cand_tokens for t in substantive_l3))

            if not type_conflicts and not tokens_conflict:
                res = RARResolution(
                    reference_expression=query.reference_expression,
                    outcome=RAROutcome.RESOLVED,
                    candidate_id=cand.id,
                    basis=RARBasis.DETERMINISTIC_ANCHOR,
                    rule_used=RARDriverRule.ACTIVE_POINTER,
                )
                return make_trace(res, RARDriverRule.ACTIVE_POINTER)
            elif type_conflicts:
                res = RARResolution(
                    reference_expression=query.reference_expression,
                    outcome=RAROutcome.UNKNOWN,
                    basis=RARBasis.DETERMINISTIC_ANCHOR,
                    failure_class=RARFailureClass.NO_CANDIDATE,
                    rule_used=RARDriverRule.ACTIVE_POINTER,
                )
                return make_trace(res, RARDriverRule.ACTIVE_POINTER, RARFailureClass.NO_CANDIDATE)

    # =========================================================================
    # LEVEL 4: Schema & Type-Constraint Filtering + Negation/Contrast Filtering
    # (identical to baseline)
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
                meaningful_overlap = [
                    t for t in overlap
                    if t not in STOPWORDS and t not in GENERIC_TYPE_WORDS
                ]
                if not meaningful_overlap:
                    continue
                distinguishing_overlap = [
                    t for t in meaningful_overlap if _neg_df.get(t, 1) <= 1
                ]
                if distinguishing_overlap:
                    eliminated_ids.append(c.id)

        candidates_list = [c for c in candidates_list if c.id not in eliminated_ids]

        if query.local_evidence.recency_hint == "other" or "other" in ref_tokens:
            if len(candidates_list) == 1:
                res = RARResolution(
                    reference_expression=query.reference_expression,
                    outcome=RAROutcome.RESOLVED,
                    candidate_id=candidates_list[0].id,
                    basis=RARBasis.DETERMINISTIC_ANCHOR,
                    rule_used=RARDriverRule.CONTRAST_FILTER,
                )
                return make_trace(res, RARDriverRule.CONTRAST_FILTER)

        if not candidates_list:
            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.UNKNOWN,
                basis=RARBasis.DETERMINISTIC_ANCHOR,
                failure_class=RARFailureClass.NO_CANDIDATE,
                rule_used=RARDriverRule.CONTRAST_FILTER,
            )
            return make_trace(res, RARDriverRule.CONTRAST_FILTER, RARFailureClass.NO_CANDIDATE)

    target_type = query.local_evidence.target_type_hint
    if target_type:
        type_matches = [
            c for c in candidates_list
            if c.candidate_type.lower() == target_type.lower()
        ]
        if len(type_matches) == 0:
            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.UNKNOWN,
                basis=RARBasis.DETERMINISTIC_ANCHOR,
                failure_class=RARFailureClass.NO_CANDIDATE,
                rule_used=RARDriverRule.TYPE_FILTER,
            )
            return make_trace(res, RARDriverRule.TYPE_FILTER, RARFailureClass.NO_CANDIDATE)

        elif len(type_matches) == 1:
            cand = type_matches[0]
            substantive_query_tokens = [
                t for t in ref_tokens
                if t not in STOPWORDS and t not in GENERIC_TYPE_WORDS and t not in PRONOUNS and t != target_type.lower()
            ]
            cand_tokens = set(clean_tokens(cand.title)).union(clean_tokens(" ".join(cand.domain_tags)))
            for a in cand.exact_aliases:
                cand_tokens.update(clean_tokens(a))

            if substantive_query_tokens and not any(t in cand_tokens for t in substantive_query_tokens):
                res = RARResolution(
                    reference_expression=query.reference_expression,
                    outcome=RAROutcome.UNKNOWN,
                    basis=RARBasis.DETERMINISTIC_ANCHOR,
                    failure_class=RARFailureClass.NO_CANDIDATE,
                    rule_used=RARDriverRule.TYPE_FILTER,
                )
                return make_trace(res, RARDriverRule.TYPE_FILTER, RARFailureClass.NO_CANDIDATE)

            rule = RARDriverRule.CONTRAST_FILTER if eliminated_ids else RARDriverRule.TYPE_FILTER
            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.RESOLVED,
                candidate_id=cand.id,
                basis=RARBasis.DETERMINISTIC_ANCHOR,
                rule_used=rule,
            )
            return make_trace(res, rule)

        else:
            candidates_list = type_matches

    # =========================================================================
    # EXPERIMENTAL PRE-COMPUTATION (H1/H3 shared substantive tokens; DX-1 tie
    # rank). None of this changes behaviour when h1=h3=False and
    # dx1_tie_ids is empty -- computed unconditionally only because it is
    # cheap and side-effect-free; only consumed inside the Level-5 branches
    # below.
    # =========================================================================
    substantive = _substantive_tokens(ref_tokens, target_type)

    tie_rank: Optional[int] = None
    if dx1_tie_ids:
        tie_members = [c for c in candidates_list if c.id in dx1_tie_ids]
        if tie_members:
            tie_rank = min(c.recency_rank for c in tie_members)

    def _l5_pool() -> List[RARCandidate]:
        """The pool Level-5's ordinal branches read from: H3-restricted when
        h3 is on and substantive tokens exist, else the full current pool.
        Never mutates `candidates_list` itself (H3 restricts the ordinal
        relation's domain only, per plan §2 scope note -- Level 5.5/6/7
        still see the full pool).
        """
        if h3:
            return _h3_domain(candidates_list, substantive)
        return list(candidates_list)

    # A2.8K-R1 repair R1-A: computed once per invocation (the pool and
    # substantive tokens do not change across the previous/earlier/
    # latest-current branches below). When h3 is off, `l5_pool` is always
    # `candidates_list` and `_domain_relative_ranks` reproduces the exact
    # same values as `_effective_rank` for every actual pool this codebase
    # constructs (both the natural-boundary harness and the S-D fixtures
    # always supply dense 0..N-1 ranks over the current queried pool, per
    # their own construction -- see docstring above) -- flag-off/H1/H2/DX-1
    # equivalence to baseline is therefore unaffected; this is verified by
    # the existing flag-off equivalence tests, not merely asserted here.
    _l5_pool_cached = _l5_pool()

    # A2.8K-R2 repair (activation-boundary): domain-relative re-ranking must
    # activate only when H3's lexical-compatibility filter GENUINELY
    # narrows the candidate domain -- i.e. the set of candidate ids Level 5
    # would otherwise see actually shrinks. Membership (id set), not list
    # length, decides this: a domain whose size happens to match the
    # original pool but whose MEMBERS differ would also count as narrowed
    # (this repository's `_h3_domain` can only ever remove members, never
    # substitute one for another, but the comparison is written against
    # identity/membership rather than length so it is correct regardless).
    # When nothing was actually filtered out -- including H3's own "no
    # substantive tokens -> domain is the current pool" case, which by
    # construction leaves the id set unchanged -- `_h3_domain` already
    # returns the same members, so this check naturally also covers that
    # case without a separate flag. Confirmed by the independent R1
    # re-audit: dense re-ranking must NOT apply to an unnarrowed domain,
    # because it can fabricate a rank-0 winner baseline deliberately
    # withheld (`test_rc1_current_conflicting_no_rank0_abstains`).
    _h3_narrowed = h3 and ({c.id for c in _l5_pool_cached} != {c.id for c in candidates_list})
    _domain_rank_map = _domain_relative_ranks(_l5_pool_cached, dx1_tie_ids, tie_rank) if _h3_narrowed else None

    def _rank(c: RARCandidate) -> int:
        if _domain_rank_map is not None:
            return _domain_rank_map[c.id]
        return _effective_rank(c, dx1_tie_ids, tie_rank)

    # =========================================================================
    # LEVEL 5.5 (H2 early precedence): when explicit attachment semantics are
    # present and h2 is on, evaluate the attachment set BEFORE any Level-5
    # ordinal branch. Identical logic to the normal-position Level 5.5 below;
    # calling it here first and returning early is the entire H2 diff.
    # =========================================================================
    _attachment_semantics_explicit = bool(
        set(ref_tokens) & _ATTACHMENT_TRIGGER_TOKENS
        or (query.local_evidence.recency_hint and query.local_evidence.recency_hint in ("attachment", "attached"))
    )

    def _level_5_5() -> Optional[DeterministicRARTrace]:
        if not _attachment_semantics_explicit:
            return None
        attachment_cands = [c for c in candidates_list if c.is_attachment]
        if len(attachment_cands) == 1:
            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.RESOLVED,
                candidate_id=attachment_cands[0].id,
                basis=RARBasis.DETERMINISTIC_ANCHOR,
                rule_used=RARDriverRule.CURRENT_ATTACHMENT,
            )
            return make_trace(res, RARDriverRule.CURRENT_ATTACHMENT)
        elif len(attachment_cands) > 1:
            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.AMBIGUOUS,
                ambiguous_candidate_ids=tuple(c.id for c in attachment_cands),
                basis=RARBasis.DETERMINISTIC_ANCHOR,
                failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
                rule_used=RARDriverRule.CURRENT_ATTACHMENT,
            )
            return make_trace(res, RARDriverRule.CURRENT_ATTACHMENT, RARFailureClass.MULTIPLE_PLAUSIBLE)
        return None

    if h2:
        _early = _level_5_5()
        if _early is not None:
            return _early

    # =========================================================================
    # LEVEL 5: Temporal / Version Ordinal Offset Selection
    # =========================================================================
    recency_hint = query.local_evidence.recency_hint

    # "revised" is a tag/title lookup, not a rank-based ordering relation --
    # out of scope for H3 (plan: H3 governs the "ordinal relation" only).
    # H1's evidence floor still applies: "revised"/"draft" etc. are excluded
    # from "substantive" by the R3(a) vocabulary, so a bare "the revised
    # draft" has zero substantive tokens and H1 blocks this branch's commit,
    # falling through to Level 6 (which uses its own, unfiltered substantive
    # set and can still resolve the same case lexically).
    if recency_hint == "revised" or "revised" in ref_tokens:
        revised_cands = [
            c for c in candidates_list
            if "revised" in c.domain_tags or "revised" in clean_tokens(c.title)
        ]
        if len(revised_cands) == 1:
            if not (h1 and not substantive):
                res = RARResolution(
                    reference_expression=query.reference_expression,
                    outcome=RAROutcome.RESOLVED,
                    candidate_id=revised_cands[0].id,
                    basis=RARBasis.DETERMINISTIC_ANCHOR,
                    rule_used=RARDriverRule.REVISION_RELATION,
                )
                return make_trace(res, RARDriverRule.REVISION_RELATION)
        elif len(revised_cands) > 1:
            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.AMBIGUOUS,
                ambiguous_candidate_ids=tuple(c.id for c in revised_cands),
                basis=RARBasis.DETERMINISTIC_ANCHOR,
                failure_class=RARFailureClass.REVISION_RELATION,
                rule_used=RARDriverRule.REVISION_RELATION,
            )
            return make_trace(res, RARDriverRule.REVISION_RELATION, RARFailureClass.REVISION_RELATION)

    if recency_hint == "previous" or "previous" in ref_tokens:
        l5_pool = _l5_pool_cached
        prev_cands = [c for c in l5_pool if _rank(c) == 1]
        if len(prev_cands) == 1:
            if not (h1 and not substantive):
                res = RARResolution(
                    reference_expression=query.reference_expression,
                    outcome=RAROutcome.RESOLVED,
                    candidate_id=prev_cands[0].id,
                    basis=RARBasis.DETERMINISTIC_ANCHOR,
                    rule_used=RARDriverRule.TEMPORAL_RELATION,
                )
                return make_trace(res, RARDriverRule.TEMPORAL_RELATION)
        elif len(prev_cands) > 1:
            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.AMBIGUOUS,
                ambiguous_candidate_ids=tuple(c.id for c in prev_cands[:2]),
                basis=RARBasis.DETERMINISTIC_ANCHOR,
                failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
                rule_used=RARDriverRule.TEMPORAL_RELATION,
            )
            return make_trace(res, RARDriverRule.TEMPORAL_RELATION, RARFailureClass.MULTIPLE_PLAUSIBLE)

    if recency_hint == "earlier" or "earlier" in ref_tokens:
        l5_pool = _l5_pool_cached
        older_cands = [c for c in l5_pool if _rank(c) > 0]
        if len(older_cands) == 1:
            if not (h1 and not substantive):
                res = RARResolution(
                    reference_expression=query.reference_expression,
                    outcome=RAROutcome.RESOLVED,
                    candidate_id=older_cands[0].id,
                    basis=RARBasis.DETERMINISTIC_ANCHOR,
                    rule_used=RARDriverRule.TEMPORAL_RELATION,
                )
                return make_trace(res, RARDriverRule.TEMPORAL_RELATION)
        elif len(older_cands) > 1:
            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.AMBIGUOUS,
                ambiguous_candidate_ids=tuple(c.id for c in older_cands[:2]),
                basis=RARBasis.DETERMINISTIC_ANCHOR,
                failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
                rule_used=RARDriverRule.TEMPORAL_RELATION,
            )
            return make_trace(res, RARDriverRule.TEMPORAL_RELATION, RARFailureClass.MULTIPLE_PLAUSIBLE)

    _latest_current_triggered = (
        recency_hint in ("latest", "current")
        or "latest" in ref_tokens
        or "current" in ref_tokens
    )
    if _latest_current_triggered:
        l5_pool = _l5_pool_cached
        # H3: an empty compatible domain means this branch does not bind at
        # all (plan §2: "An empty subset means Level 5 does not bind and
        # falls through") -- it must not fall into baseline's own
        # missing-metadata AMBIGUOUS fallback below using the full pool,
        # which would be answering a different question (whether ordering
        # metadata exists at all) than the one H3 actually failed (whether
        # any candidate is compatible with the reference's own wording).
        # No-op when h3 is off or the domain was not narrowed to empty,
        # since l5_pool == candidates_list in that case.
        _h3_empty_domain = h3 and bool(substantive) and not l5_pool
        if not _h3_empty_domain:
            # A2.8K-R1 repair R1-A, narrowed by A2.8K-R2: once h3 has
            # GENUINELY restricted `l5_pool` to a strict subset (`_h3_narrowed`
            # -- see its definition above; false when the lexical filter kept
            # every candidate, including the "no substantive tokens" case),
            # `_rank` returns DOMAIN-RELATIVE positions, so a value of 0
            # always exists for any non-empty domain by construction -- a
            # singleton domain member is trivially its own domain's latest
            # (the audit's own words: "the only -- and therefore latest --
            # member of the compatible domain"). Baseline's `has_ordering`
            # gate answered a different question ("does this POOL carry any
            # real recency metadata at all, as opposed to every candidate
            # silently defaulting to rank 0") that has no domain-relative
            # analogue: under dense re-ranking, "all domain members
            # genuinely tied" and "no domain metadata populated" already
            # collapse into the same safe outcome via the
            # len(latest_cands) > 1 branch below, so no separate gate is
            # needed once genuine narrowing is active. The gate is kept,
            # byte-identical to baseline, whenever the domain was NOT
            # genuinely narrowed -- this is the R2 fix: R1 used the bare
            # `h3` flag here, which incorrectly skipped the gate even when
            # H3's filter changed nothing (e.g. "the current document" with
            # no candidate excluded), fabricating a rank-0 winner baseline
            # deliberately withheld
            # (`test_rc1_current_conflicting_no_rank0_abstains`).
            if _h3_narrowed:
                latest_cands = [c for c in l5_pool if _rank(c) == 0]
                if len(latest_cands) == 1:
                    if not (h1 and not substantive):
                        res = RARResolution(
                            reference_expression=query.reference_expression,
                            outcome=RAROutcome.RESOLVED,
                            candidate_id=latest_cands[0].id,
                            basis=RARBasis.DETERMINISTIC_ANCHOR,
                            rule_used=RARDriverRule.TEMPORAL_RELATION,
                        )
                        return make_trace(res, RARDriverRule.TEMPORAL_RELATION)
                elif len(latest_cands) > 1:
                    res = RARResolution(
                        reference_expression=query.reference_expression,
                        outcome=RAROutcome.AMBIGUOUS,
                        ambiguous_candidate_ids=tuple(c.id for c in latest_cands[:2]),
                        basis=RARBasis.DETERMINISTIC_ANCHOR,
                        failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
                        rule_used=RARDriverRule.TEMPORAL_RELATION,
                    )
                    return make_trace(res, RARDriverRule.TEMPORAL_RELATION, RARFailureClass.MULTIPLE_PLAUSIBLE)
            else:
                has_ordering = any(_rank(c) > 0 for c in l5_pool)
                if has_ordering:
                    latest_cands = [c for c in l5_pool if _rank(c) == 0]
                    if len(latest_cands) == 1:
                        if not (h1 and not substantive):
                            res = RARResolution(
                                reference_expression=query.reference_expression,
                                outcome=RAROutcome.RESOLVED,
                                candidate_id=latest_cands[0].id,
                                basis=RARBasis.DETERMINISTIC_ANCHOR,
                                rule_used=RARDriverRule.TEMPORAL_RELATION,
                            )
                            return make_trace(res, RARDriverRule.TEMPORAL_RELATION)
                    elif len(latest_cands) > 1:
                        res = RARResolution(
                            reference_expression=query.reference_expression,
                            outcome=RAROutcome.AMBIGUOUS,
                            ambiguous_candidate_ids=tuple(c.id for c in latest_cands[:2]),
                            basis=RARBasis.DETERMINISTIC_ANCHOR,
                            failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
                            rule_used=RARDriverRule.TEMPORAL_RELATION,
                        )
                        return make_trace(res, RARDriverRule.TEMPORAL_RELATION, RARFailureClass.MULTIPLE_PLAUSIBLE)
                else:
                    if len(l5_pool) >= 2:
                        res = RARResolution(
                            reference_expression=query.reference_expression,
                            outcome=RAROutcome.AMBIGUOUS,
                            ambiguous_candidate_ids=tuple(c.id for c in l5_pool[:2]),
                            basis=RARBasis.DETERMINISTIC_ANCHOR,
                            failure_class=RARFailureClass.INSUFFICIENT_METADATA,
                            rule_used=RARDriverRule.TEMPORAL_RELATION,
                        )
                        return make_trace(res, RARDriverRule.TEMPORAL_RELATION, RARFailureClass.INSUFFICIENT_METADATA)

    # =========================================================================
    # LEVEL 5.5 (normal position -- baseline order when h2 is off, or the
    # idempotent re-check when h2 is on and the early call above found
    # nothing to resolve).
    # =========================================================================
    _l5_5 = _level_5_5()
    if _l5_5 is not None:
        return _l5_5

    # =========================================================================
    # LEVEL 6: Discriminating Term Overlap Ranking (identical to baseline)
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
            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.AMBIGUOUS,
                ambiguous_candidate_ids=tuple(c.id for c in candidates_list),
                basis=RARBasis.DETERMINISTIC_ANCHOR,
                failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
                rule_used=RARDriverRule.TERM_DISCRIMINATION,
            )
            return make_trace(res, RARDriverRule.TERM_DISCRIMINATION, RARFailureClass.MULTIPLE_PLAUSIBLE)
        if eliminated_ids:
            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.AMBIGUOUS,
                ambiguous_candidate_ids=tuple(c.id for c in candidates_list),
                basis=RARBasis.DETERMINISTIC_ANCHOR,
                failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
                rule_used=RARDriverRule.TERM_DISCRIMINATION,
            )
            return make_trace(res, RARDriverRule.TERM_DISCRIMINATION, RARFailureClass.MULTIPLE_PLAUSIBLE)

    unmatched_substantive = [t for t in substantive6 if t not in all_pool_tokens]
    if unmatched_substantive:
        res = RARResolution(
            reference_expression=query.reference_expression,
            outcome=RAROutcome.UNKNOWN,
            basis=RARBasis.DETERMINISTIC_ANCHOR,
            failure_class=RARFailureClass.NO_CANDIDATE,
            rule_used=RARDriverRule.TERM_DISCRIMINATION,
        )
        return make_trace(res, RARDriverRule.TERM_DISCRIMINATION, RARFailureClass.NO_CANDIDATE)

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
                    res = RARResolution(
                        reference_expression=query.reference_expression,
                        outcome=RAROutcome.AMBIGUOUS,
                        ambiguous_candidate_ids=tuple(c.id for c in candidates_list),
                        basis=RARBasis.DETERMINISTIC_ANCHOR,
                        failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
                        rule_used=RARDriverRule.TERM_DISCRIMINATION,
                    )
                    return make_trace(res, RARDriverRule.TERM_DISCRIMINATION, RARFailureClass.MULTIPLE_PLAUSIBLE, scores)

                if eliminated_ids:
                    res = RARResolution(
                        reference_expression=query.reference_expression,
                        outcome=RAROutcome.AMBIGUOUS,
                        ambiguous_candidate_ids=tuple(c.id for c in candidates_list),
                        basis=RARBasis.DETERMINISTIC_ANCHOR,
                        failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
                        rule_used=RARDriverRule.TERM_DISCRIMINATION,
                    )
                    return make_trace(res, RARDriverRule.TERM_DISCRIMINATION, RARFailureClass.MULTIPLE_PLAUSIBLE, scores)

            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.UNKNOWN,
                basis=RARBasis.DETERMINISTIC_ANCHOR,
                failure_class=RARFailureClass.NO_CANDIDATE,
                rule_used=RARDriverRule.TERM_DISCRIMINATION,
            )
            return make_trace(res, RARDriverRule.TERM_DISCRIMINATION, RARFailureClass.NO_CANDIDATE, scores)

        else:
            if len(candidates_list) >= 2:
                res = RARResolution(
                    reference_expression=query.reference_expression,
                    outcome=RAROutcome.AMBIGUOUS,
                    ambiguous_candidate_ids=tuple(c.id for c in candidates_list[:2]),
                    basis=RARBasis.DETERMINISTIC_ANCHOR,
                    failure_class=RARFailureClass.PRONOUN_BINDING,
                    rule_used=RARDriverRule.TERM_DISCRIMINATION,
                )
                return make_trace(res, RARDriverRule.TERM_DISCRIMINATION, RARFailureClass.PRONOUN_BINDING, scores)
            else:
                res = RARResolution(
                    reference_expression=query.reference_expression,
                    outcome=RAROutcome.UNKNOWN,
                    basis=RARBasis.DETERMINISTIC_ANCHOR,
                    failure_class=RARFailureClass.PRONOUN_BINDING,
                    rule_used=RARDriverRule.TERM_DISCRIMINATION,
                )
                return make_trace(res, RARDriverRule.TERM_DISCRIMINATION, RARFailureClass.PRONOUN_BINDING, scores)

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
            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.RESOLVED,
                candidate_id=top_candidates[0],
                basis=RARBasis.DETERMINISTIC_ANCHOR,
                rule_used=RARDriverRule.TERM_DISCRIMINATION,
            )
            return make_trace(res, RARDriverRule.TERM_DISCRIMINATION, scores=scores)
        else:
            ambiguous_ids = tuple(cid for cid, _ in scores[:2])
            if len(ambiguous_ids) < 2 and len(candidates_list) >= 2:
                ambiguous_ids = tuple(c.id for c in candidates_list[:2])
            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.AMBIGUOUS,
                ambiguous_candidate_ids=ambiguous_ids[:2],
                basis=RARBasis.DETERMINISTIC_ANCHOR,
                failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
                rule_used=RARDriverRule.TERM_DISCRIMINATION,
            )
            return make_trace(res, RARDriverRule.TERM_DISCRIMINATION, RARFailureClass.MULTIPLE_PLAUSIBLE, scores)
    else:
        res = RARResolution(
            reference_expression=query.reference_expression,
            outcome=RAROutcome.AMBIGUOUS,
            ambiguous_candidate_ids=tuple(top_candidates[:2]),
            basis=RARBasis.DETERMINISTIC_ANCHOR,
            failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
            rule_used=RARDriverRule.TERM_DISCRIMINATION,
        )
        return make_trace(res, RARDriverRule.TERM_DISCRIMINATION, RARFailureClass.MULTIPLE_PLAUSIBLE, scores)

    # =========================================================================
    # LEVEL 7: Residual Failure Classification & Safe Abstention (identical
    # to baseline)
    # =========================================================================
    failure_class = classify_unresolved_failure(query, candidates_list, eliminated_ids)
    if failure_class == RARFailureClass.NO_CANDIDATE:
        res = RARResolution(
            reference_expression=query.reference_expression,
            outcome=RAROutcome.UNKNOWN,
            basis=RARBasis.DETERMINISTIC_ANCHOR,
            failure_class=failure_class,
            rule_used=RARDriverRule.NONE,
        )
    else:
        ambiguous_ids = tuple(c.id for c in candidates_list[:2]) if len(candidates_list) >= 2 else ()
        if len(ambiguous_ids) >= 2:
            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.AMBIGUOUS,
                ambiguous_candidate_ids=ambiguous_ids,
                basis=RARBasis.DETERMINISTIC_ANCHOR,
                failure_class=failure_class,
                rule_used=RARDriverRule.NONE,
            )
        else:
            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.UNKNOWN,
                basis=RARBasis.DETERMINISTIC_ANCHOR,
                failure_class=failure_class,
                rule_used=RARDriverRule.NONE,
            )
    return make_trace(res, RARDriverRule.NONE, failure_class, scores)
