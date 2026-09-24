"""Legacy-Derived Deterministic Reference Anchor Resolution (RAR) Stack (Batch A2.5).

Stage 2: initial 7-level stack derived from legacy URI prototype.
Stage 4: four bounded deterministic refinements (Root Causes 1-4 from Stage 3 analysis):
  RC-1 — Explicit latest/current temporal semantics (Level 5 extension).
  RC-2 — Distinguishing-term-only negation elimination (Level 4a repair).
  RC-3 — UNKNOWN vs AMBIGUOUS semantic distinction on zero-score (Level 6 repair).
  RC-4 — Existing is_attachment metadata consulted for explicit attachment references
          (new Level 5.5 between Temporal and TF-IDF).

Deterministic Coverage Stack:
- Level 0: Verbatim ID / Exact Alias Anchor
- Level 1: Active Turn Context Anchors (Attachment handle, Selected UI item, Anchor title)
- Level 2: Strict Verbatim Title Match (with multi-match anti-bias guard)
- Level 3: Active Pointer / Continuation Binding ("same", "recently_discussed")
- Level 4: Schema & Type-Constraint Filtering + Negation/Contrast Filtering
- Level 5: Temporal / Version Ordinal Offset Selection
            (previous/earlier/revised/latest/current)
- Level 5.5: Explicit Attachment Binding (is_attachment metadata)
- Level 6: Discriminating Term Overlap Ranking (Adapted TF-IDF candidate discrimination)
- Residual: 10-class structured failure partitioning

Invariants:
- Absolute zero candidate invention.
- Absolute zero first-item bias on ambiguity (ties MUST return AMBIGUOUS).
- Safe abstention (UNKNOWN / AMBIGUOUS) is treated as correct behaviour when expected.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

from uri_v1.turn.rar_contracts import (
    RARBasis,
    RARCandidate,
    RARDeterministicAnchor,
    RAREvidence,
    RARFailureClass,
    RARDriverRule,
    RAROutcome,
    RARQuery,
    RARResolution,
    validate_rar_resolution,
)

# Standard linguistic stop words to exclude from semantic term discrimination
STOPWORDS: Set[str] = {
    "a", "an", "the", "that", "this", "these", "those",
    "it", "its", "it's", "to", "for", "in", "on", "of", "at", "by", "with",
    "from", "into", "onto", "and", "or", "but", "so", "as", "is", "was",
    "are", "were", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "not", "no", "one", "ones", "about", "against",
    "send", "forward", "trigger", "summarize", "open", "review",
    "reply", "share", "compare", "skip", "notify", "attach", "archive", "convert",
}

# Generic type words that do not serve as discriminating semantic nouns
GENERIC_TYPE_WORDS: Set[str] = {
    "document", "file", "email", "attachment", "workflow", "sheet",
    "spreadsheet", "pdf", "docx", "xlsx", "mp4", "txt", "person", "entity",
    "item", "object", "media", "recording", "message",
}

# Personal and deictic pronouns
PRONOUNS: Set[str] = {
    "it", "its", "that", "this", "these", "those",
    "he", "him", "his", "she", "her", "hers",
    "they", "them", "their", "theirs",
    "we", "us", "our", "ours", "you", "your", "yours",
    "me", "my", "mine", "one", "ones", "who", "whom",
}


@dataclass(frozen=True)
class DeterministicRARTrace:
    """Diagnostic trace recording deterministic execution and metrics."""

    resolution: RARResolution
    rule_used: RARDriverRule
    failure_class: Optional[RARFailureClass] = None
    candidate_count_before: int = 0
    candidate_count_after: int = 0
    latency_ms: float = 0.0
    eliminated_candidate_ids: Tuple[str, ...] = ()
    candidate_scores: Tuple[Tuple[str, float], ...] = ()


def clean_tokens(text: str) -> List[str]:
    """Extracts cleaned alphanumeric tokens from text, expanding camelCase/delimiters."""
    # Replace separators with spaces
    cleaned = re.sub(r"[_\.\-\/\:\#\(\)]", " ", text)
    # Split camelCase (e.g. LabEquipment -> Lab Equipment)
    cleaned = re.sub(r"([a-z])([A-Z])", r"\1 \2", cleaned)
    tokens = re.findall(r"[a-zA-Z0-9]+", cleaned.lower())
    return [t for t in tokens if len(t) >= 2]


def stem_title(title: str) -> str:
    """Strips file extensions and normalizes title text for stem comparison."""
    # Strip extension
    stem = re.sub(r"\.(pdf|docx|xlsx|csv|txt|mp4|mov|zip|json|mp3|wav|m4a|ogg|html|pptx)$", "", title, flags=re.IGNORECASE)
    # Replace delimiters with single space
    cleaned = re.sub(r"[_\.\-\/]", " ", stem)
    return " ".join(cleaned.lower().split())


def compute_term_document_frequency(candidates: Sequence[RARCandidate]) -> Dict[str, int]:
    """Computes document frequency for each word token across candidate descriptors.

    Adapted from legacy uri_core/core/capability_relevance.py.
    """
    df: Dict[str, int] = {}
    for c in candidates:
        descriptor_tokens: Set[str] = set()
        # Title tokens
        descriptor_tokens.update(clean_tokens(c.title))
        # Domain tags
        for tag in c.domain_tags:
            descriptor_tokens.update(clean_tokens(tag))
        # Candidate type
        descriptor_tokens.update(clean_tokens(c.candidate_type))
        # Aliases
        for alias in c.exact_aliases:
            descriptor_tokens.update(clean_tokens(alias))

        for t in descriptor_tokens:
            if t not in STOPWORDS:
                df[t] = df.get(t, 0) + 1
    return df


def score_candidate_relevance(
    candidate: RARCandidate,
    query_tokens: Sequence[str],
    df: Dict[str, int],
    target_type_hint: Optional[str] = None,
) -> float:
    """Calculates discriminating term overlap score for a candidate.

    Tokens appearing in <= 1 candidate are treated as discriminating (high weight).
    Tokens appearing in >= 2 candidates are treated as generic (low weight).
    """
    if not query_tokens:
        return 0.0

    cand_tokens = set(clean_tokens(candidate.title))
    cand_tags = set(clean_tokens(" ".join(candidate.domain_tags)))
    for a in candidate.exact_aliases:
        cand_tokens.update(clean_tokens(a))

    score = 0.0
    for t in query_tokens:
        if t in STOPWORDS or t in GENERIC_TYPE_WORDS:
            continue
        is_in_cand = (t in cand_tokens) or (t in cand_tags)
        if is_in_cand:
            freq = df.get(t, 1)
            if freq <= 1:
                # Discriminating term
                score += 3.0
            else:
                # Shared/generic term
                score += 1.0
            if t in cand_tags:
                score += 1.0

    # Type bonus (only added to reinforce actual lexical/semantic matches)
    if score > 0.0 and target_type_hint and candidate.candidate_type.lower() == target_type_hint.lower():
        score += 0.5

    return score


def classify_unresolved_failure(
    query: RARQuery,
    candidates: Sequence[RARCandidate],
    eliminated_ids: Sequence[str],
) -> RARFailureClass:
    """Classifies an unresolved reference into one of the 10 stable structured failure classes."""
    ref_lower = query.reference_expression.strip().lower()
    ref_tokens = clean_tokens(ref_lower)

    # 1. NO_CANDIDATE
    if not candidates:
        return RARFailureClass.NO_CANDIDATE

    # 2. CONTRAST_SELECTION
    if query.local_evidence.negation_spans or "not" in ref_tokens or "skip" in ref_tokens or "other" in ref_tokens:
        if len(candidates) > 1:
            return RARFailureClass.CONTRAST_SELECTION

    # 3. REVISION_RELATION
    revision_words = {"revised", "revision", "draft", "original", "version", "v1", "v2"}
    if query.local_evidence.recency_hint in ("revised", "original") or any(w in ref_tokens for w in revision_words):
        return RARFailureClass.REVISION_RELATION

    # 4. TEMPORAL_RELATION
    temporal_words = {"previous", "earlier", "latest", "first", "last", "prior"}
    if query.local_evidence.recency_hint in temporal_words or any(w in ref_tokens for w in temporal_words):
        return RARFailureClass.TEMPORAL_RELATION

    # 5. OWNERSHIP_RELATION
    if "'s" in ref_lower or any(p in ref_tokens for p in ("his", "her", "their", "my", "our")):
        return RARFailureClass.OWNERSHIP_RELATION

    # 6. PRONOUN_BINDING
    pronouns = {"it", "that", "this", "them", "he", "she", "him", "her", "that one", "this one"}
    if ref_lower in pronouns or (len(ref_tokens) == 1 and ref_tokens[0] in pronouns):
        return RARFailureClass.PRONOUN_BINDING

    # 7. INSUFFICIENT_METADATA
    if query.local_evidence.target_type_hint and any(c.candidate_type == "" for c in candidates):
        return RARFailureClass.INSUFFICIENT_METADATA

    # 8. MULTIPLE_PLAUSIBLE
    if len(candidates) >= 2:
        return RARFailureClass.MULTIPLE_PLAUSIBLE

    # 9. CROSS_REFERENCE
    if " and " in ref_lower or "," in ref_lower:
        return RARFailureClass.CROSS_REFERENCE

    # 10. Default: SEMANTIC_DISCRIMINATION
    return RARFailureClass.SEMANTIC_DISCRIMINATION


def resolve_rar_deterministic_extended(query: RARQuery) -> DeterministicRARTrace:
    """Executes the full 7-level legacy-derived deterministic RAR stack.

    Levels evaluated strictly in order:
    Level 0: Verbatim ID / Exact Alias Anchor
    Level 1: Active Turn Context Anchors (Attachment, UI, Anchor title)
    Level 2: Strict Verbatim Title Match (anti-bias tie check)
    Level 3: Active Pointer / Continuation Binding ("same", "recently_discussed")
    Level 4: Schema / Type Filtering & Contrast / Negation Filtering
    Level 5: Temporal / Version Ordinal Offset Selection
    Level 6: Discriminating Term Overlap Ranking (Adapted TF-IDF)
    Level 7: Structured Failure Partitioning & Safe Abstention

    Invariants strictly enforced:
    - Never invents an ID.
    - Never guesses index 0 on ambiguity.
    - Resolves or safely abstains with full diagnostic attribution.
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
        # Enforce contract validation
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
    # LEVEL 0: Verbatim ID / Exact Alias Anchor (100% Certainty)
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

    # Verbatim reference expression match against candidate ID or exact aliases
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
    # LEVEL 1: Active Turn Context Anchors (100% Certainty)
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
    # LEVEL 2: Strict Verbatim Title Match (Anti-Bias Tie Guard)
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
        # Multiple candidates share identical title/stem! Anti-first-item-bias!
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
    # LEVEL 3: Active Pointer / Continuation Binding
    # =========================================================================
    if query.local_evidence.recency_hint == "same":
        # Look for recently discussed candidate in turn context
        discussed_candidates = [
            c for c in candidates_list
            if "recently_discussed" in c.domain_tags or (c.recency_rank == 0 and len(candidates_list) > 1 and all(other.recency_rank >= 2 for other in candidates_list if other.id != c.id))
        ]
        if len(discussed_candidates) == 1:
            cand = discussed_candidates[0]
            # Authority Policy: non-conflicting requirement
            type_hint = query.local_evidence.target_type_hint
            type_conflicts = bool(
                type_hint
                and cand.candidate_type
                and type_hint.lower() != cand.candidate_type.lower()
            )

            cand_tokens = set(clean_tokens(cand.title)).union(clean_tokens(" ".join(cand.domain_tags)))
            for a in cand.exact_aliases:
                cand_tokens.update(clean_tokens(a))
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
    # LEVEL 4: Schema & Type-Constraint Filtering + Negation/Contrast Filtering
    # =========================================================================
    # 4a. Negation / Contrast Elimination (RC-2: distinguishing-term-only)
    #
    # Stage 4 repair: elimination must rely on candidate-distinguishing evidence,
    # not merely any token overlap.  A token is distinguishing only when the
    # document-frequency (df) across the current candidate set is 1 — i.e. it
    # appears in exactly one candidate.  Tokens shared by multiple candidates
    # (e.g. the head-noun "coordinator" that appears in both
    # "Coordinator Report" and "Assistant Coordinator Report") are generic
    # within this candidate set and MUST NOT be used to eliminate a candidate.
    #
    # Explicit "rejected_in_turn" domain tag is still honoured unconditionally
    # (it is a structural fact, not a lexical inference).
    if query.local_evidence.negation_spans:
        # Pre-compute per-candidate token sets and document-frequency for
        # the full current candidate set so we can test distinguishability.
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
                # Structural explicit rejection — always honour
                if "rejected_in_turn" in c.domain_tags:
                    eliminated_ids.append(c.id)
                    continue
                # Compute meaningful overlap between the negation span and
                # this candidate's tokens
                cand_tok = _cand_token_map[c.id]
                overlap = span_tokens.intersection(cand_tok)
                meaningful_overlap = [
                    t for t in overlap
                    if t not in STOPWORDS and t not in GENERIC_TYPE_WORDS
                ]
                if not meaningful_overlap:
                    continue
                # RC-2 gate: only eliminate if at least one overlapping token
                # is distinguishing (df==1 in the current set).  Shared
                # head-nouns (df>1) do not constitute sufficient evidence.
                distinguishing_overlap = [
                    t for t in meaningful_overlap if _neg_df.get(t, 1) <= 1
                ]
                if distinguishing_overlap:
                    eliminated_ids.append(c.id)

        candidates_list = [c for c in candidates_list if c.id not in eliminated_ids]

        # Contrast selection shortcut ("the other one", "the alternative")
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

    # 4b. Type-Constraint Filtering
    target_type = query.local_evidence.target_type_hint
    if target_type:
        type_matches = [
            c for c in candidates_list
            if c.candidate_type.lower() == target_type.lower()
        ]
        if len(type_matches) == 0:
            # Safe abstention: required type does not exist in candidate pool
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
            # Safety check: if reference expression contains specific discriminating terms
            # not present in candidate, do not falsely bind
            substantive_query_tokens = [
                t for t in ref_tokens
                if t not in STOPWORDS and t not in GENERIC_TYPE_WORDS and t not in PRONOUNS and t != target_type.lower()
            ]
            cand_tokens = set(clean_tokens(cand.title)).union(clean_tokens(" ".join(cand.domain_tags)))
            for a in cand.exact_aliases:
                cand_tokens.update(clean_tokens(a))

            # If query has substantive tokens, verify at least one matches candidate
            if substantive_query_tokens and not any(t in cand_tokens for t in substantive_query_tokens):
                # Target entity is absent despite type match
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
            # Narrow candidates to type-matched subset
            candidates_list = type_matches

    # =========================================================================
    # LEVEL 5: Temporal / Version Ordinal Offset Selection
    # =========================================================================
    recency_hint = query.local_evidence.recency_hint
    if recency_hint == "revised" or "revised" in ref_tokens:
        revised_cands = [
            c for c in candidates_list
            if "revised" in c.domain_tags or "revised" in clean_tokens(c.title)
        ]
        if len(revised_cands) == 1:
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
        # Older than active/current candidate
        older_cands = [c for c in candidates_list if c.recency_rank > 0]
        if len(older_cands) == 1:
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

    # RC-1 — Explicit latest / current temporal semantics.
    #
    # "latest" / "current" resolve to the candidate with recency_rank == 0
    # when exactly one such candidate exists and recency metadata is present
    # (i.e. at least one candidate has a non-zero recency_rank, confirming the
    # metadata is structurally populated rather than all defaults).
    #
    # Safety invariants:
    # - candidate[0] list position is NEVER used; only recency_rank == 0 value.
    # - Resolution requires recency metadata to be genuinely present (at least
    #   one candidate with rank > 0).
    # - Tie (two+ candidates both at rank 0) → safe abstention.
    # - Missing metadata (all ranks are 0, meaning no ordering is established)
    #   → safe abstention.
    # - "current" as an open-ended phrase (e.g. "this cycle") is explicitly NOT
    #   covered here — only the keywords "latest"/"current" with valid rank data.
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
    # LEVEL 5.5: Explicit Attachment Binding (RC-4)
    #
    # RARCandidate.is_attachment already exists in the contract but was never
    # consulted.  When the user's reference expression explicitly establishes
    # attachment semantics ("attached", "attachment") AND exactly one candidate
    # has is_attachment=True with no conflicting evidence, resolve via that
    # structural fact.
    #
    # Safety invariants:
    # - Attachment semantics must be explicit in the reference expression token
    #   set or in the recency_hint (not inferred from filename alone).
    # - Exactly one is_attachment=True candidate required; multiple → AMBIGUOUS
    #   (let further deterministic refinement or clarification handle it).
    # - is_attachment=True alone is not sufficient when the user did not reference
    #   an attachment (the trigger guard below prevents false firing).
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
            # Multiple plausible attachments → AMBIGUOUS (safe, let clarification
            # or further evidence distinguish them)
            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.AMBIGUOUS,
                ambiguous_candidate_ids=tuple(c.id for c in attachment_cands),
                basis=RARBasis.DETERMINISTIC_ANCHOR,
                failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
                rule_used=RARDriverRule.CURRENT_ATTACHMENT,
            )
            return make_trace(res, RARDriverRule.CURRENT_ATTACHMENT, RARFailureClass.MULTIPLE_PLAUSIBLE)
        # Zero attachment candidates → fall through to Level 6 (maybe there's
        # a lexical match, or safe abstention will occur)

    # =========================================================================
    # LEVEL 6: Discriminating Term Overlap Ranking (Adapted TF-IDF)
    # =========================================================================
    substantive = [t for t in ref_tokens if t not in STOPWORDS and t not in GENERIC_TYPE_WORDS and t not in PRONOUNS]

    # Pre-gather all known descriptor tokens across the current candidate pool
    all_pool_tokens: Set[str] = set()
    for c in candidates_list:
        all_pool_tokens.update(clean_tokens(c.title))
        for tag in c.domain_tags:
            all_pool_tokens.update(clean_tokens(tag))
        for a in c.exact_aliases:
            all_pool_tokens.update(clean_tokens(a))

    # Case B & C pre-check: If all candidates share identical titles or are negation survivors,
    # vague referring expressions (e.g. "the other version") indicate indistinguishable candidates,
    # not an absent entity.
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

    # Absent entity detection (Mechanism A from Stage 4B / Authority Policy):
    # If the user query contains substantive discriminating tokens that appear
    # in NONE of the candidates, the referent is absent from the pool.
    # Do NOT falsely bind an existing candidate on generic residual terms.
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

    # If all candidates scored 0:
    if max_score == 0.0:
        if substantive:
            # RC-3: Distinguish "no plausible candidate" (UNKNOWN) from "known
            # candidates exist but cannot be discriminated" (AMBIGUOUS).
            if len(candidates_list) >= 2:
                stems = {stem_title(c.title) for c in candidates_list}
                all_same_title = len(stems) == 1

                if all_same_title:
                    # Case B: identical titles — structurally indistinguishable.
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
                    # Case C: negation narrowed the pool; survivors are the known
                    # plausible set but remain undiscriminated.
                    res = RARResolution(
                        reference_expression=query.reference_expression,
                        outcome=RAROutcome.AMBIGUOUS,
                        ambiguous_candidate_ids=tuple(c.id for c in candidates_list),
                        basis=RARBasis.DETERMINISTIC_ANCHOR,
                        failure_class=RARFailureClass.MULTIPLE_PLAUSIBLE,
                        rule_used=RARDriverRule.TERM_DISCRIMINATION,
                    )
                    return make_trace(res, RARDriverRule.TERM_DISCRIMINATION, RARFailureClass.MULTIPLE_PLAUSIBLE, scores)

            # Case A — different titles, no negation narrowing, single candidate, or
            # referent absent: query explicitly named an entity not present in pool.
            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.UNKNOWN,
                basis=RARBasis.DETERMINISTIC_ANCHOR,
                failure_class=RARFailureClass.NO_CANDIDATE,
                rule_used=RARDriverRule.TERM_DISCRIMINATION,
            )
            return make_trace(res, RARDriverRule.TERM_DISCRIMINATION, RARFailureClass.NO_CANDIDATE, scores)

        else:
            # Pure pronoun or deictic reference without anchor
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

    # Check for ties or runner-up margin
    top_candidates = [cid for cid, s in scores if s == max_score]
    if len(top_candidates) == 1 and max_score > 0.0:
        runner_up_score = scores[1][1] if len(scores) > 1 else 0.0
        winner = cand_map[top_candidates[0]]
        winner_tokens = set(clean_tokens(winner.title)).union(clean_tokens(" ".join(winner.domain_tags)))
        for a in winner.exact_aliases:
            winner_tokens.update(clean_tokens(a))

        # RAR Authority Policy (Section 4):
        # Ranking Only: TF-IDF / discriminating-term overlap should normally narrow or rank candidates.
        # Do NOT silently bind solely because one candidate receives the highest lexical score
        # unless an already-defined deterministic uniqueness rule independently justifies it.
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
        # Multiple candidates tied for highest score -> AMBIGUOUS (anti-first-item-bias)
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
    # LEVEL 7: Residual Failure Classification & Safe Abstention
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
