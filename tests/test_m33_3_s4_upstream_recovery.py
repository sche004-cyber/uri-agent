"""M33.3 S4 upstream recovery: detector preposition boundary and RAR RC-5 contrast gate.

Each test targets a failure class, not a benchmark sentence. The benchmark
utterances (NB-B-05, NB-H-06) are covered by the S4 replay gate test.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from m35_a2_8f_detector_d1r import detect_references as d1r_detect  # noqa: E402
from m35_a2_8h_detector_d1rq import detect_references as d1rq_detect  # noqa: E402
from uri_v1.turn.rar_contracts import RARCandidate, RAREvidence, RAROutcome, RARQuery  # noqa: E402
from uri_v1.turn.rar_deterministic import resolve_rar_deterministic_extended  # noqa: E402

DETECTORS = pytest.mark.parametrize("detect", [d1r_detect, d1rq_detect], ids=["D1R", "D1RQ"])


def _spans(detect, text: str) -> dict[str, str | None]:
    return {r.span: r.coarse_type for r in detect(text)}


@DETECTORS
@pytest.mark.parametrize("text, destination, type_word", [
    ("Put that in an email to Sam", "email", "email"),
    ("Drop this in a spreadsheet for me", "spreadsheet", "spreadsheet"),
    ("Save those on a file share", "file", "document"),
    ("Upload it via an email link", "email", "email"),
])
def test_destination_type_word_never_becomes_reference_evidence(detect, text, destination, type_word) -> None:
    refs = detect(text)
    assert refs, text
    for ref in refs:
        # The destination is the verb's complement, not part of the referring phrase.
        assert destination not in ref.span.lower(), ref
        assert ref.coarse_type != type_word, ref


@DETECTORS
def test_noun_phrase_stops_at_preposition_and_keeps_its_own_type(detect) -> None:
    spans = _spans(detect, "Forward the pdf in the email to finance")
    assert spans.get("the pdf") == "pdf"
    assert "the pdf in the email" not in spans
    spans = _spans(detect, "Re-check the formulas in the same spreadsheet.")
    assert spans.get("the formulas") is None and "the formulas" in spans
    assert spans.get("the same spreadsheet") == "spreadsheet"


@DETECTORS
def test_ordinal_and_existing_boundaries_are_preserved(detect) -> None:
    # Temporal prepositions are not stops: "the one before" stays an ordinal reference.
    assert "the one before" in _spans(detect, "open the one before that")
    assert "the report" in _spans(detect, "open the report from last week")
    assert "the quarterly budget report" in _spans(detect, "send the quarterly budget report")


def _query(ref: str, candidates, negation=(), recency=None, type_hint=None) -> RARQuery:
    return RARQuery(reference_expression=ref, candidates=tuple(candidates),
                    local_evidence=RAREvidence(recency_hint=recency, negation_spans=tuple(negation),
                                               target_type_hint=type_hint))


@pytest.mark.parametrize("ref, negation, recency", [
    ("the other scan", ("no", "the other"), "earlier"),
    ("the other one", ("not that one",), None),
    ("another copy", ("no",), "other"),
])
def test_contrast_without_demonstrated_exclusion_never_binds_the_only_candidate(ref, negation, recency) -> None:
    pool = [RARCandidate(id="only", title="scan_0034.pdf", candidate_type="pdf")]
    trace = resolve_rar_deterministic_extended(_query(ref, pool, negation, recency))
    assert trace.resolution.outcome != RAROutcome.RESOLVED
    assert trace.resolution.candidate_id is None


def test_contrast_after_real_exclusion_still_binds_the_survivor() -> None:
    pool = [RARCandidate(id="dark", title="Dark theme mockup", candidate_type="image"),
            RARCandidate(id="light", title="Light theme mockup", candidate_type="image")]
    trace = resolve_rar_deterministic_extended(
        _query("the other mockup", pool, ("Not the dark theme mockup",)))
    assert trace.resolution.outcome == RAROutcome.RESOLVED
    assert trace.resolution.candidate_id == "light"
    assert trace.rule_used.value == "CONTRAST_FILTER"
    assert trace.eliminated_candidate_ids == ("dark",)


def test_structural_rejection_counts_as_demonstrated_exclusion() -> None:
    pool = [RARCandidate(id="old", title="Offer letter", candidate_type="document", domain_tags=("rejected_in_turn",)),
            RARCandidate(id="new", title="Contract", candidate_type="document")]
    trace = resolve_rar_deterministic_extended(_query("the other one", pool, ("no",)))
    assert trace.resolution.outcome == RAROutcome.RESOLVED
    assert trace.resolution.candidate_id == "new"
