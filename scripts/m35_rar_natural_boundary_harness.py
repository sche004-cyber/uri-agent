"""M35 URIv1 -- RAR Natural-Boundary Frozen-Corpus Execution Harness.

Benchmark-only. Imports the real, unmodified resolver and TurnFrame builder
and runs them against the frozen raw-turn corpus. No production file is
modified or hardcoded to any fixture case.

Adapter responsibilities (mechanical, documented, independent of expected
answers -- see docs/plans/M35_URIV1_RAR_NATURAL_BOUNDARY_EXECUTION_REPORT.md
Section 3 "Harness design" for the rationale behind each decision below):

1. candidate_library -> RARCandidate: maps the frozen candidate object shape
   (file_reference_shape / synthetic_minimal) onto the resolver's own
   RARCandidate dataclass fields. Pure field renaming; no scoring logic.
2. S1 query construction: byte-for-byte mirrors the one real production call
   site (uri_v1/turn/lfm_semantic_decoder.py:345-356) -- same recency_hint
   literal check, same turn-global negation_spans pass-through, same
   deterministic_anchor=None, same recency_rank=0 on every candidate (the
   real call site never computes recency_rank; confirmed by the governing
   audit's Claim B).
3. S2 query construction: uses the fixture's own oracle
   ground_truth_references fields (human_marked_span / implicit_antecedent,
   intended_type, temporal_meaning, user_exclusions) as the idealized
   upstream input the approved plan's S2 axis defines. recency_rank under S2
   is computed by sorting each variant's candidate pool on the candidate
   library's own created_at field (real per-object metadata, not a
   fixture-authored "expected" field) -- this is the mechanical oracle
   counterpart to S1's hardcoded recency_rank=0, and is documented as a
   harness construction decision, not left ambiguous (see report Section 3).
4. deterministic_anchor is never constructed in ANY condition (S1 or S2),
   per the approved plan's Section 13 restraint: no code path in the real
   system ever builds RARDeterministicAnchor, and inventing one here would
   fabricate a condition the real system cannot produce.

Ground truth is read only by the scorer, after the resolver has already
returned its answer -- never passed into RARQuery/RAREvidence/RARCandidate.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from uri_v1.turn.contracts import AttachmentReference  # noqa: E402
from uri_v1.turn.turn_frame_builder import build_turn_frame  # noqa: E402
from uri_v1.turn.rar_contracts import (  # noqa: E402
    RARCandidate,
    RAREvidence,
    RARQuery,
)
from uri_v1.turn.rar_deterministic import (  # noqa: E402
    resolve_rar_deterministic_extended,
    DeterministicRARTrace,
)

FIXTURE_PATH = REPO_ROOT / "uri_v1" / "turn" / "rar_natural_boundary_raw_turn_fixtures.json"
TELEMETRY_PATH = REPO_ROOT / "docs" / "plans" / "M35_URIV1_RAR_NATURAL_BOUNDARY_TELEMETRY.json"

SENSITIVITY_EXCLUDE_CASE_IDS = {"NB-C-06", "NB-C-07", "NB-I-06", "NB-I-07"}

# ---------------------------------------------------------------------------
# Oracle temporal_meaning -> RAREvidence.recency_hint mapping (S2 only).
# Documented explicitly; passthrough where the resolver has no bespoke
# handling, so any resulting gap is an observed finding, not hidden.
# ---------------------------------------------------------------------------
TEMPORAL_MEANING_TO_RECENCY_HINT = {
    "none": None,
    "most_recent": "latest",
    "one_before_most_recent": "previous",
    "earlier_not_latest": "earlier",
    "earliest": "earlier",  # resolver has no bespoke "earliest" hint; nearest existing concept
    "last_discussed": "same",
    "one_before_last_discussed": "previous",
}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_fixture() -> dict:
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# candidate_library entry -> RARCandidate (mechanical field mapping only)
# ---------------------------------------------------------------------------

def library_entry_title(entry: dict) -> str:
    if entry["representation"] == "file_reference_shape":
        return entry["file_reference"]["filename"]
    return entry["synthetic_minimal"]["title"] if "synthetic_minimal" in entry else entry["title"]


def library_entry_type(entry: dict) -> str:
    if entry["representation"] == "file_reference_shape":
        return entry["benchmark_added"].get("object_type") or ""
    obj = entry.get("synthetic_minimal", entry)
    return obj.get("object_type") or ""


def library_entry_created_at(entry: dict) -> Optional[str]:
    if entry["representation"] == "file_reference_shape":
        return entry["benchmark_added"].get("created_at")
    obj = entry.get("synthetic_minimal", entry)
    return obj.get("created_at")


def library_entry_domain_tags(entry: dict) -> Tuple[str, ...]:
    obj = entry.get("synthetic_minimal", entry) if entry["representation"] != "file_reference_shape" else {}
    tags: List[str] = []
    for field_name in ("origin", "status", "direction", "counterparty"):
        v = obj.get(field_name)
        if v:
            tags.append(str(v))
    return tuple(tags)


def build_candidate(
    candidate_id: str,
    library: Dict[str, dict],
    recency_rank: int = 0,
) -> RARCandidate:
    entry = library[candidate_id]
    is_attachment = entry["representation"] == "file_reference_shape"
    return RARCandidate(
        id=candidate_id,
        title=library_entry_title(entry),
        candidate_type=library_entry_type(entry),
        recency_rank=recency_rank,
        domain_tags=library_entry_domain_tags(entry),
        is_attachment=is_attachment,
    )


def build_candidate_pool(
    candidate_ids: Sequence[str],
    library: Dict[str, dict],
    oracle_recency: bool,
) -> Tuple[RARCandidate, ...]:
    """Builds the RARCandidate tuple for one variant's available_candidates.

    oracle_recency=False (S1): every candidate gets recency_rank=0, mirroring
    the one real production call site, which never computes recency_rank.
    oracle_recency=True (S2): candidates are ranked 0..N-1 by descending
    created_at (ties share a rank), the mechanical oracle counterpart.
    """
    if not oracle_recency:
        return tuple(build_candidate(cid, library, recency_rank=0) for cid in candidate_ids)

    dated: List[Tuple[str, Optional[str]]] = [(cid, library_entry_created_at(library[cid])) for cid in candidate_ids]
    with_ts = sorted((it for it in dated if it[1] is not None), key=lambda it: it[1], reverse=True)  # most recent first
    without_ts = [it for it in dated if it[1] is None]
    ordered = with_ts + without_ts  # missing timestamps ranked last, in original order

    # Assign rank 0..N-1 by position; identical timestamps share the same rank
    # (a genuine tie -- two candidates with the same real created_at value).
    rank_by_id: Dict[str, int] = {}
    current_rank = -1
    last_ts = object()
    for cid, ts in ordered:
        if ts != last_ts:
            current_rank += 1
        rank_by_id[cid] = current_rank
        last_ts = ts

    return tuple(build_candidate(cid, library, recency_rank=rank_by_id[cid]) for cid in candidate_ids)


# ---------------------------------------------------------------------------
# S1: real wired path (raw text -> build_turn_frame -> candidate_references)
# ---------------------------------------------------------------------------

@dataclass
class S1Extraction:
    turn_frame_negation_spans: Tuple[str, ...]
    found_reference_exprs: Tuple[str, ...]  # what TurnFrame actually found (candidate_references)


def run_s1_extraction(raw_text: str, turn_attachment_ids: Sequence[str]) -> S1Extraction:
    attachments = tuple(AttachmentReference(identifier=aid) for aid in turn_attachment_ids)
    turn_frame = build_turn_frame(raw_text, attachments=attachments)
    return S1Extraction(
        turn_frame_negation_spans=turn_frame.negation_spans,
        found_reference_exprs=tuple(cr.expression for cr in turn_frame.candidate_references),
    )


def s1_query_for_expression(
    ref_expr: str,
    candidates: Tuple[RARCandidate, ...],
    negation_spans: Tuple[str, ...],
) -> RARQuery:
    """Mirrors lfm_semantic_decoder.py:345-356 exactly."""
    evidence = RAREvidence(
        recency_hint="same" if ref_expr in ("same", "same thing") else None,
        negation_spans=negation_spans,
    )
    return RARQuery(
        reference_expression=ref_expr,
        candidates=candidates,
        local_evidence=evidence,
        deterministic_anchor=None,
    )


# ---------------------------------------------------------------------------
# S2: oracle path
# ---------------------------------------------------------------------------

def s2_query_for_reference(
    gt_ref: dict,
    candidates: Tuple[RARCandidate, ...],
) -> RARQuery:
    ref_expr = gt_ref.get("human_marked_span") or gt_ref.get("implicit_antecedent") or ""
    recency_hint = TEMPORAL_MEANING_TO_RECENCY_HINT.get(gt_ref.get("temporal_meaning") or "none")
    target_type_hint = gt_ref.get("intended_type")
    # Per-reference-scoped negation: the exclusion phrases attributed to this
    # reference only (oracle scoping -- the real path passes turn-global
    # negation_spans instead; this is exactly the S1 vs S2 contrast §10 of
    # the approved plan requires for UNSAFE_OVER_ELIMINATION attribution).
    negation_spans = tuple(gt_ref.get("user_exclusions") or ())
    evidence = RAREvidence(
        recency_hint=recency_hint,
        negation_spans=negation_spans,
        target_type_hint=target_type_hint,
    )
    return RARQuery(
        reference_expression=ref_expr,
        candidates=candidates,
        local_evidence=evidence,
        deterministic_anchor=None,
    )
