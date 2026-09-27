"""Focused S4 offline boundary qualification; frozen inputs are read-only."""

from __future__ import annotations

import json
from dataclasses import asdict

import pytest

from scripts.m33_3_s4_source_to_candidate import (
    SourceBoundaryError,
    build_snapshot,
    make_envelope,
    project,
)
from scripts.m33_3_s4_replay import CORPUS, classify, replay, verify_anchors


def _library() -> dict:
    return {
        "a": {"candidate_id": "a", "representation": "synthetic_minimal",
              "title": "Quarterly report", "object_type": "document", "created_at": "2026-09-01"},
        "b": {"candidate_id": "b", "representation": "synthetic_minimal",
              "title": "Travel ledger", "object_type": "spreadsheet", "created_at": "2026-09-02"},
    }


def test_snapshot_is_allowlisted_and_has_grounded_provenance() -> None:
    library = _library()
    forbidden_payload = {
        "ground_truth_references": [{"ref_key": "r1"}],
        "expected_outcome": "RESOLVED",
        "expected_by_reference": [{"intended_candidate_id": "a"}],
        "acceptable_alternatives": ["RESOLVED"],
        "intended_candidate_id": "a",
        "reason": "oracle",
        "category": "oracle",
        "secondary_signals": ["oracle"],
        "difficulty": "oracle",
    }
    library["a"].update(forbidden_payload)
    context = {"turn_attachments": [], **forbidden_payload}
    snap = build_snapshot("Open Quarterly report", context, ["a", "b"], library)
    envelope = make_envelope(snap)
    assert envelope.authorized_ids == ("a", "b")
    assert envelope.records[0].locator == "fixture://candidate_library/a"
    assert envelope.authorization_basis == "variant_available_candidates"
    wire = json.dumps(asdict(snap)) + json.dumps(asdict(envelope))
    for forbidden in ("ground_truth_references", "expected_outcome", "expected_by_reference",
                      "acceptable_alternatives", "intended_candidate_id", "reason",
                      "category", "secondary_signals", "difficulty"):
        assert forbidden not in wire


def test_unknown_duplicate_inconsistent_and_oversize_sources_fail_closed() -> None:
    library = _library()
    with pytest.raises(SourceBoundaryError):
        build_snapshot("x", {}, ["a", "a"], library)
    with pytest.raises(SourceBoundaryError):
        build_snapshot("x", {}, ["missing"], library)
    with pytest.raises(SourceBoundaryError):
        build_snapshot("x", {}, ["a"] * 17, library)
    broken = {"f": {"candidate_id": "f", "representation": "file_reference_shape",
                    "file_reference": {"file_id": "other", "filename": "f.pdf"},
                    "benchmark_added": {"object_type": "pdf"}}}
    with pytest.raises(SourceBoundaryError):
        build_snapshot("x", {}, ["f"], broken)
    library["a"]["title"] = "Z" * 17_000
    with pytest.raises(SourceBoundaryError):
        build_snapshot("x", {}, ["a"], library)


def test_anchors_require_unique_grounded_evidence() -> None:
    library = _library()
    snap = build_snapshot("Open Quarterly report", {}, ["a", "b"], library)
    query, origin = project(snap, make_envelope(snap), "Quarterly report")
    assert query.candidate_ids == ("a", "b")
    assert query.deterministic_anchor.unique_title_match == "a"
    assert origin == "unique_title"
    library["b"]["title"] = "Quarterly report"
    snap = build_snapshot("Open Quarterly report", {}, ["a", "b"], library)
    query, origin = project(snap, make_envelope(snap), "Quarterly report")
    assert query.deterministic_anchor is None
    assert origin == "conflict_or_nonunique"
    snap = build_snapshot("Open a", {}, ["a", "b"], _library())
    query, origin = project(snap, make_envelope(snap), "a")
    assert query.deterministic_anchor.exact_id == "a"
    assert origin == "exact_id"


def test_attachment_anchor_requires_authorized_single_current_attachment() -> None:
    library = {"f": {"candidate_id": "f", "representation": "file_reference_shape",
                     "file_reference": {"file_id": "f", "filename": "photo.pdf"},
                     "benchmark_added": {"object_type": "pdf", "created_at": "2026-09-01"}}}
    snap = build_snapshot("use the attached file", {"turn_attachments": ["f"]}, ["f"], library)
    query, origin = project(snap, make_envelope(snap), "the attached file")
    assert query.deterministic_anchor.current_attachment_id == "f"
    assert origin == "current_attachment"
    snap = build_snapshot("use the attached file", {"turn_attachments": ["other"]}, ["f"], library)
    query, origin = project(snap, make_envelope(snap), "the attached file")
    assert query.deterministic_anchor is None
    assert origin == "none"


def test_frozen_corpus_projection_and_replay_gate() -> None:
    assert verify_anchors()
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    for case in corpus["cases"]:
        for variant in case["variants"]:
            if variant["candidate_condition"] not in ("C1", "C2"):
                continue
            snap = build_snapshot(case["raw_user_text"], case["conversation_context"],
                                  variant["available_candidates"], corpus["candidate_library"])
            assert tuple(r.candidate_id for r in snap.records) == tuple(variant["available_candidates"])
    telemetry, aggregate = replay()
    assert aggregate["case_count"] == 79
    assert set(aggregate["groups"]) == {f"{a}:{c}:{p}" for a in ("D0", "D1R", "D1RQ")
                                         for c in ("C1", "C2", "C3") for p in ("control", "producer")}
    assert aggregate["promotion_eligible"] is False
    gates = aggregate["gates"]
    # Known frozen-mechanism residuals (A2.8I/A2.8J): present in control and producer alike.
    assert gates["annotated_wrong_binding_cases"] == ["NB-B-05:r1", "NB-H-06:r1"]
    assert gates["annotated_wrong_binding_rows"] == 8
    assert gates["producer_only_wrong_binding_rows"] == 0
    assert gates["false_certainty_authority_on_scored_rows"] == 0
    assert gates["certainty_authority_on_unattributed_rows"] == 8  # turn-scoped attachment anchor (User decision)
    assert gates["protected_hashes_unchanged"] is True
    assert gates["safety_gate_passed"] is False
    for row in telemetry["rows"]:
        assert row["candidate_id"] is None or row["candidate_id"] in row["source_ids"]
        assert all(p["candidate_id"] in row["source_ids"] for p in row["provenance"])
        assert "raw_user_text" not in row and "reason" not in row
        if row["anchor_origin"] in ("exact_id", "unique_title") or "exact_id+" in row["anchor_origin"]:
            assert row["rule_used"] in ("EXACT_ID", "EXACT_TITLE")
    by_case = {(r["case_id"], r["arm"], r["condition"]): r for r in telemetry["rows"]
               if r["path"] == "producer" and r["ref_key"] is None and r["case_id"] == "NB-L-01"
               and r["condition"] != "C3"}
    # "the Q2 one"/"the Q3 one" never inherit the Q2 filename's title anchor.
    assert by_case and all(r["anchor_origin"] == "turn_anchor_not_in_span" for r in by_case.values())


def test_scorer_never_calls_wrong_binding_a_success() -> None:
    assert classify("RESOLVED", ["a"], "RESOLVED", "b") == "INCORRECT_CONFIDENT_BINDING"
    assert classify("AMBIGUOUS", ["a", "b"], "RESOLVED", "a") == "INCORRECT_CONFIDENT_BINDING"
    assert classify("NO_REFERENCE", [], "RESOLVED", "a") == "FALSE_POSITIVE_BINDING"
    assert classify("UNATTRIBUTED_DETECTOR_FIND", [], "RESOLVED", "a") == "UNATTRIBUTED_DETECTOR_FIND"
    assert classify("NO_REFERENCE", [], "NO_DETECTION", None) == "CORRECT_NO_REFERENCE"
    assert classify("RESOLVED", ["a"], "UNKNOWN", None) == "MISSED_RESOLVABLE_CASE"


def test_lexical_anchor_is_scoped_to_the_reference_expression() -> None:
    library = _library()
    snap = build_snapshot("Open Quarterly report and send it, not the other one", {}, ["a", "b"], library)
    envelope = make_envelope(snap)
    query, origin = project(snap, envelope, "Quarterly report")
    assert query.deterministic_anchor.unique_title_match == "a" and origin == "unique_title"
    for span in ("it", "the other one"):
        query, origin = project(snap, envelope, span)
        assert query.deterministic_anchor is None
        assert origin == "turn_anchor_not_in_span"
    snap = build_snapshot("use a for this", {}, ["a", "b"], library)
    query, origin = project(snap, make_envelope(snap), "this")
    assert query.deterministic_anchor is None and origin == "turn_anchor_not_in_span"


def test_attachment_anchor_stays_turn_scoped_and_lexical_part_is_dropped() -> None:
    library = {"f": {"candidate_id": "f", "representation": "file_reference_shape",
                     "file_reference": {"file_id": "f", "filename": "photo.pdf"},
                     "benchmark_added": {"object_type": "pdf", "created_at": "2026-09-01"}}}
    snap = build_snapshot("log photo.pdf as this expense", {"turn_attachments": ["f"]}, ["f"], library)
    query, origin = project(snap, make_envelope(snap), "this expense")
    anchor = query.deterministic_anchor
    assert anchor.current_attachment_id == "f" and anchor.unique_title_match is None
    assert origin == "current_attachment"
