"""RAR-SAFE Experimental Variant (Batch A2.8J).

Evidence-safety hardening qualification. This module is a SEPARATE,
isolated experimental fork of `uri_v1/turn/rar_deterministic.py`
(`resolve_rar_deterministic_extended`) -- it does not modify, import-patch,
or replace that module. Existing `rar_deterministic.py` remains the
production path and is imported here only for its already-approved,
unmodified helper functions and vocabulary (byte-identical reuse, not
duplication): `clean_tokens`, `stem_title`, `STOPWORDS`,
`GENERIC_TYPE_WORDS`, `PRONOUNS`, `compute_term_document_frequency`,
`score_candidate_relevance`, `classify_unresolved_failure`,
`DeterministicRARTrace`.

Candidate evidence-sufficiency invariant under test (A2.8J plan, mission
brief; unifies Known A/latent, Known B/active, New G/active, New F/latent
from A2.8I into one rule):

    No level may commit a binding that the resolver's own Level-6
    lexical/absent-entity evidence contradicts, and no binding may be
    committed on zero substantive evidence.

Exactly three bounded changes are made relative to the existing cascade,
all scoped by the accepted plan/task (S1/S2/S3 below). Cascade order
(Levels 0-7) and the query/candidate/evidence contracts are otherwise
byte-identical to the existing resolver -- this file is a drop-in
substitute for `resolve_rar_deterministic_extended` in a harness, nothing
more.

S1 (Level 4b, zero-substantive-evidence binding): a singleton type match no
    longer binds when the query supplies zero substantive tokens (after
    excluding stopwords/generic-type-words/pronouns/the type word itself).
    Previously a bare type mention (e.g. "that in an email" with
    target_type_hint="email") would bind the sole type match on no other
    evidence at all (New G, active/unsafe at C2 -- `NB-B-05:r1`). RAR-SAFE
    instead narrows the pool to the type-matched subset and lets the
    cascade continue (same behaviour as the existing multi-match branch),
    rather than inventing a new failure mode.

S2 (Level 5, commit against contradictory lexical evidence): before Level 5
    returns RESOLVED for any single-candidate temporal match (revised /
    previous / earlier / latest-current), it now consults a reusable
    pre-commit gate, `level6_would_contradict_binding`, built by extracting
    Level 6's own existing absent-entity / lexical-overlap mechanism (not a
    new scoring system). If the query's own substantive tokens are either
    absent from the whole candidate pool, or present on some OTHER
    candidate but not on the one Level 5 is about to bind, Level 5 does NOT
    commit -- execution falls through to the next cascade stage exactly as
    if this temporal hint had not matched (Known A, latent once recency is
    real; this is the reusable hook the plan requires, callable from any
    future commit point, without moving Level 6 earlier and without
    special-casing recency).

S3 (Level 4a, contrast/exclusion must demonstrate actual exclusion): the
    "the other"/"another" contrast shortcut previously fired whenever the
    post-elimination pool had exactly one candidate, even if the negation
    elimination step removed nothing (Known B, active/unsafe -- `NB-H-06`).
    RAR-SAFE requires the elimination step to have actually removed at
    least one candidate (`len(eliminated_ids) >= 1`) before the shortcut is
    permitted to fire. No string-literal special-casing of "the other" is
    added or removed; only the existing pool-size-only gate is tightened.

Frozen scope (A2.8J plan/task, restated here so this file's own diff stays
self-documenting): does NOT wire recency into production, does NOT
implement T2 bare-name detection, does NOT add session state, aliases,
morphology/stemming, or semantic knowledge, does NOT repair Known C/D
(partial-credit, plural/stemming, abbreviation normalization), and is NOT
integrated into any production call site. Benchmark/experimental use only.
"""

from __future__ import annotations

import time
from typing import List, Optional, Sequence, Set, Tuple

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

# Recency/temporal/revision/attachment vocabulary already recognised
# elsewhere in the resolver. Excluded from the S2 pre-commit gate's
# "substantive token" computation because these words express WHEN or
# WHICH-VERSION/WHICH-ROLE, not WHICH ENTITY, is meant -- Level 6 itself
# never sees most of them in any existing production case (Level 5 always
# intercepts first), so treating them as entity-discriminating tokens
# would make the gate fire on ordinary temporal/revision/attachment
# phrasing regardless of correctness.
#
# R3(a) repair (A2.8J independent final audit, finding D3): the original
# closed set below (RC-1's recency_hint literals + "other") did NOT
# include several words RAR's own baseline cascade already recognises as
# non-entity-discriminating temporal/revision/attachment vocabulary. This
# caused S2 to misclassify correct bindings such as "the earlier version"
# or "the revised draft" as lexically contradicted, because "version" and
# "draft" were treated as absent-entity substantive tokens. Per the audit
# and the accepted repair directive, the vocabulary is now DERIVED
# directly from the three existing baseline-RAR word sets below, not
# independently re-invented -- `rar_deterministic.py` itself is not
# modified (its two vocabularies are local to a function body and cannot
# be imported without editing that frozen file), so the values are
# reproduced verbatim from their source lines and cited here for
# traceability:
#
#   1. RC-1 recency_hint literals: RAREvidence.recency_hint values already
#      consumed by the baseline Level-5 cascade ("previous", "revised",
#      "original", "latest", "current", "earlier") plus the Level 3/4a
#      "same"/"other" pointer-and-contrast hint literals.
#   2. `classify_unresolved_failure`'s `revision_words`
#      (rar_deterministic.py:196): {"revised", "revision", "draft",
#      "original", "version", "v1", "v2"}.
#   3. `classify_unresolved_failure`'s `temporal_words`
#      (rar_deterministic.py:201): {"previous", "earlier", "latest",
#      "first", "last", "prior"}.
#   4. The cascade's own Level 5.5 `_ATTACHMENT_TRIGGER_TOKENS`
#      (rar_deterministic.py:711): {"attached", "attachment", "attaches"}
#      -- "attachment" itself is already excluded from "substantive" by
#      GENERIC_TYPE_WORDS; "attached"/"attaches" were not previously
#      excluded anywhere and are added here.
#
# "earliest" (plural/superlative of "earlier", already in the original
# S2 set) and "same" (Level 3 pointer hint) are retained unchanged; no
# word is removed from the original set, only added to. No case ID or
# benchmark-specific term is included.
_RECENCY_VOCABULARY: Set[str] = {
    # RC-1 recency_hint literals + Level 3/4a pointer/contrast hints
    "previous", "revised", "original", "latest", "current",
    "earlier", "earliest", "same", "other",
    # classify_unresolved_failure revision_words (rar_deterministic.py:196)
    "revision", "draft", "version", "v1", "v2",
    # classify_unresolved_failure temporal_words (rar_deterministic.py:201)
    "first", "last", "prior",
    # Level 5.5 _ATTACHMENT_TRIGGER_TOKENS (rar_deterministic.py:711)
    "attached", "attaches",
}


def _candidate_tokens(candidate: RARCandidate) -> Set[str]:
    toks = set(clean_tokens(candidate.title))
    toks.update(clean_tokens(" ".join(candidate.domain_tags)))
    for alias in candidate.exact_aliases:
        toks.update(clean_tokens(alias))
    return toks


def level6_would_contradict_binding(
    ref_tokens: Sequence[str],
    target_type: Optional[str],
    winner: RARCandidate,
    pool: Sequence[RARCandidate],
) -> bool:
    """Reusable pre-commit gate (S2): True if Level 6's own lexical /
    absent-entity evidence contradicts binding `winner` from the current
    `pool`.

    Two ways evidence can contradict a proposed binding, both extracted
    directly from Level 6's existing mechanism (`clean_tokens` +
    STOPWORDS/GENERIC_TYPE_WORDS/PRONOUNS filtering, and the existing
    absent-entity all-or-nothing check) rather than any new scoring:

    1. Absent entity: the query names a substantive token that appears in
       NONE of the candidates in `pool` (Level 6's existing rule).
    2. Misdirected entity: the query names a substantive token that is
       present in `pool` but not on `winner` specifically, while some OTHER
       candidate in `pool` does carry it -- i.e. the resolver's own lexical
       evidence points elsewhere.

    Returns False (no contradiction) when the query carries no substantive
    tokens at all -- that is a "zero evidence" case, not a "contradicting
    evidence" case, and is governed by S1, not S2.
    """
    substantive = [
        t for t in ref_tokens
        if t not in STOPWORDS
        and t not in GENERIC_TYPE_WORDS
        and t not in PRONOUNS
        and t not in _RECENCY_VOCABULARY
        and (not target_type or t != target_type.lower())
    ]
    if not substantive:
        return False

    all_pool_tokens: Set[str] = set()
    for c in pool:
        all_pool_tokens.update(_candidate_tokens(c))

    if any(t not in all_pool_tokens for t in substantive):
        return True

    winner_tokens = _candidate_tokens(winner)
    for t in substantive:
        if t in winner_tokens:
            continue
        if any(t in _candidate_tokens(c) for c in pool if c.id != winner.id):
            return True

    return False


def resolve_rar_safe_experimental(query: RARQuery) -> DeterministicRARTrace:
    """RAR-SAFE: the existing 7-level cascade with the three bounded S1/S2/S3
    safety gates applied. Levels 0-3, 4a's elimination step, 4b's zero/
    multi-match branches, 5.5, 6 and 7 are behaviourally identical to
    `resolve_rar_deterministic_extended` -- only the three named commit
    points are gated differently. See module docstring for the exact
    invariant and diff boundaries.
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
    # LEVEL 0: Verbatim ID / Exact Alias Anchor (unchanged)
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
    # LEVEL 1: Active Turn Context Anchors (unchanged)
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
    # LEVEL 2: Strict Verbatim Title Match (unchanged)
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
    # LEVEL 3: Active Pointer / Continuation Binding (unchanged)
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

            cand_tokens = _candidate_tokens(cand)
            substantive = [
                t for t in ref_tokens
                if t not in STOPWORDS and t not in GENERIC_TYPE_WORDS and t not in PRONOUNS and t != "same"
            ]
            tokens_conflict = bool(substantive and not any(t in cand_tokens for t in substantive))

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
    # LEVEL 4a: Negation / Contrast Elimination
    # S3: the contrast shortcut now requires elimination to have actually
    # removed >= 1 candidate -- pool size alone is no longer sufficient.
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

        # S3 gate: require actual elimination (>= 1 candidate removed), not
        # merely a post-filter pool size of 1. Previously a pool that
        # started at size 1 (nothing to eliminate) would still trigger the
        # shortcut and bind the sole -- excluded -- candidate (Known B,
        # active/unsafe, `NB-H-06`).
        if (query.local_evidence.recency_hint == "other" or "other" in ref_tokens) and eliminated_ids:
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

    # =========================================================================
    # LEVEL 4b: Type-Constraint Filtering
    # S1: singleton type match no longer binds on zero substantive evidence.
    # =========================================================================
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
            cand_tokens = _candidate_tokens(cand)

            if substantive_query_tokens:
                if not any(t in cand_tokens for t in substantive_query_tokens):
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

            # S1: zero substantive query evidence -- a type hint alone is
            # not sufficient to commit a binding. Narrow to the type-matched
            # subset and let the cascade continue, exactly as the existing
            # multi-match branch below already does.
            candidates_list = type_matches

        else:
            candidates_list = type_matches

    # =========================================================================
    # LEVEL 5: Temporal / Version Ordinal Offset Selection
    # S2: each single-candidate commit is gated by level6_would_contradict_binding
    # before returning RESOLVED. On contradiction, execution falls through
    # to the next stage exactly as if this hint had not matched.
    # =========================================================================
    recency_hint = query.local_evidence.recency_hint
    if recency_hint == "revised" or "revised" in ref_tokens:
        revised_cands = [
            c for c in candidates_list
            if "revised" in c.domain_tags or "revised" in clean_tokens(c.title)
        ]
        if len(revised_cands) == 1:
            if not level6_would_contradict_binding(ref_tokens, target_type, revised_cands[0], candidates_list):
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
        prev_cands = [c for c in candidates_list if c.recency_rank == 1]
        if len(prev_cands) == 1:
            if not level6_would_contradict_binding(ref_tokens, target_type, prev_cands[0], candidates_list):
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
        older_cands = [c for c in candidates_list if c.recency_rank > 0]
        if len(older_cands) == 1:
            if not level6_would_contradict_binding(ref_tokens, target_type, older_cands[0], candidates_list):
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
        has_ordering = any(c.recency_rank > 0 for c in candidates_list)
        if has_ordering:
            latest_cands = [c for c in candidates_list if c.recency_rank == 0]
            if len(latest_cands) == 1:
                if not level6_would_contradict_binding(ref_tokens, target_type, latest_cands[0], candidates_list):
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
            if len(candidates_list) >= 2:
                res = RARResolution(
                    reference_expression=query.reference_expression,
                    outcome=RAROutcome.AMBIGUOUS,
                    ambiguous_candidate_ids=tuple(c.id for c in candidates_list[:2]),
                    basis=RARBasis.DETERMINISTIC_ANCHOR,
                    failure_class=RARFailureClass.INSUFFICIENT_METADATA,
                    rule_used=RARDriverRule.TEMPORAL_RELATION,
                )
                return make_trace(res, RARDriverRule.TEMPORAL_RELATION, RARFailureClass.INSUFFICIENT_METADATA)

    # =========================================================================
    # LEVEL 5.5: Explicit Attachment Binding (unchanged)
    # =========================================================================
    _ATTACHMENT_TRIGGER_TOKENS = {"attached", "attachment", "attaches"}
    _attachment_semantics_explicit = bool(
        set(ref_tokens) & _ATTACHMENT_TRIGGER_TOKENS
        or (recency_hint and recency_hint in ("attachment", "attached"))
    )
    if _attachment_semantics_explicit:
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

    # =========================================================================
    # LEVEL 6: Discriminating Term Overlap Ranking (unchanged)
    # =========================================================================
    substantive = [t for t in ref_tokens if t not in STOPWORDS and t not in GENERIC_TYPE_WORDS and t not in PRONOUNS]

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

    unmatched_substantive = [t for t in substantive if t not in all_pool_tokens]
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
        if substantive:
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
        winner_tokens = _candidate_tokens(winner)

        all_substantive_matched = all(t in winner_tokens for t in substantive)
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
    # LEVEL 7: Residual Failure Classification & Safe Abstention (unchanged)
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
