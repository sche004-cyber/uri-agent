"""A2.8L frozen 13-template / 14-row factorial fixture set.

Every record transcribes `docs/plans/M35_URIV1_A2_8L_OVERLAY_MANIFEST.md`
verbatim. Reused fixtures (`SD-A-*`) reuse `rar_l5_diagnostic_fixtures.py`'s
own candidate/query construction byte-for-byte (same ids, titles, ranks,
recency_hint); natural rows (`NB-C-04`, `NB-C-05`, `NB-D-01`) reuse
`m35_rar_natural_boundary_harness.build_candidate_pool` against the frozen
natural corpus, unmodified.

Two of the 14 rows are disclosed structural exceptions found during
implementation (see `docs/plans/M35_URIV1_A2_8L_EXECUTION_REPORT.md`
"Interpretive notes and disclosed limitations"):

- `C-LEXICAL-ATTACHMENT` (`SD-A-08`): unreachable by any of the six frozen
  factors (Level 5.5's `is_attachment` counting is outside M/G/P/D/R/Q
  scope as literally frozen). Marked `reachable_by_factors=False`; excluded
  from the "passes every control" qualification gate per explicit User
  direction, but still run and reported in every cell.
- `B-DISTRACTOR` (`NB-C-05` C2): required extending D/M's membership
  restriction to Level 5.5's generic attachment-counting set (not just
  Level 5's ordinal branches) -- disclosed in
  `rar_attachment_order_experimental.py`'s module docstring as the same
  D/M mechanism applied at the sibling level, not a 7th factor.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from uri_v1.turn.rar_contracts import RARCandidate, RAREvidence, RAROutcome, RARQuery
from uri_v1.turn.rar_attachment_order_experimental import (
    AttachmentOrderOverlay,
    PROVENANCE_CURRENT_TURN_SEQUENCE,
    PROVENANCE_HISTORICAL_OBJECT_CREATED_AT,
    PROVENANCE_UNKNOWN,
)

import m35_rar_natural_boundary_harness as nbh  # noqa: E402


def _c(cid: str, title: str, *, rank: int = 0, is_attachment: bool = True, tags=()) -> RARCandidate:
    return RARCandidate(id=cid, title=title, candidate_type="document", recency_rank=rank,
                         domain_tags=tuple(tags), is_attachment=is_attachment)


@dataclass(frozen=True)
class FactorialCase:
    id: str
    manifest_id: str
    source: str
    is_causal_target: bool
    pool_condition: str
    query: RARQuery
    overlay: AttachmentOrderOverlay
    expected_outcome: RAROutcome
    expected_candidate_id: Optional[str] = None
    expected_ambiguous_candidate_ids: Tuple[str, ...] = ()
    reachable_by_factors: bool = True
    disclosure: str = ""


def _build_cases() -> List[FactorialCase]:
    cases: List[FactorialCase] = []

    # --- §5.1 causal targets -------------------------------------------------
    a4_new = _c("sd-a4-new", "Vacation_Photo_New.jpg", rank=0)
    a4_old = _c("sd-a4-old", "Vacation_Photo_Old.jpg", rank=1)
    cases.append(FactorialCase(
        "A-LATEST-2", "A2L-OV-03", "SD-A-04", True, "",
        RARQuery("the latest attachment", (a4_new, a4_old), RAREvidence(recency_hint="latest")),
        AttachmentOrderOverlay(
            turn_membership_ids=frozenset({"sd-a4-new", "sd-a4-old"}),
            event_group_by_id={"sd-a4-old": "event-0", "sd-a4-new": "event-1"},
            group_ordinal_by_event={"event-0": 0, "event-1": 1},
            provenance=PROVENANCE_CURRENT_TURN_SEQUENCE,
        ),
        RAROutcome.RESOLVED, expected_candidate_id="sd-a4-new",
    ))

    a6_early = _c("sd-a6-early", "Draft_Early.pdf", rank=1)
    a6_late = _c("sd-a6-late", "Draft_Late.pdf", rank=0)
    cases.append(FactorialCase(
        "A-FIRST-2", "A2L-OV-04", "SD-A-06", True, "",
        RARQuery("the first attachment", (a6_early, a6_late), RAREvidence(recency_hint="earlier")),
        AttachmentOrderOverlay(
            turn_membership_ids=frozenset({"sd-a6-early", "sd-a6-late"}),
            event_group_by_id={"sd-a6-early": "event-0", "sd-a6-late": "event-1"},
            group_ordinal_by_event={"event-0": 0, "event-1": 1},
            provenance=PROVENANCE_CURRENT_TURN_SEQUENCE,
        ),
        RAROutcome.RESOLVED, expected_candidate_id="sd-a6-early",
    ))

    ad_old = _c("a2l-ad-old", "Draft_Old.pdf", rank=2)
    ad_new = _c("a2l-ad-new", "Draft_New.pdf", rank=1)
    ad_distractor = _c("a2l-ad-distractor", "Unrelated_Newer.pdf", rank=0)
    cases.append(FactorialCase(
        "A-LATEST-DISTRACTOR", "A2L-OV-01", "authored", True, "",
        RARQuery("the latest attachment", (ad_old, ad_new, ad_distractor), RAREvidence(recency_hint="latest")),
        AttachmentOrderOverlay(
            turn_membership_ids=frozenset({"a2l-ad-old", "a2l-ad-new"}),
            event_group_by_id={"a2l-ad-old": "event-0", "a2l-ad-new": "event-1"},
            group_ordinal_by_event={"event-0": 0, "event-1": 1},
            provenance=PROVENANCE_CURRENT_TURN_SEQUENCE,
        ),
        RAROutcome.RESOLVED, expected_candidate_id="a2l-ad-new",
    ))

    a5_x = _c("sd-a5-x", "Vacation_Photo_X.jpg", rank=0)
    a5_y = _c("sd-a5-y", "Vacation_Photo_Y.jpg", rank=1)
    cases.append(FactorialCase(
        "B-LATEST-WRONG-CLOCK", "A2L-OV-05", "SD-A-05", True, "",
        RARQuery("the latest attachment", (a5_x, a5_y), RAREvidence(recency_hint="latest")),
        AttachmentOrderOverlay(
            turn_membership_ids=frozenset({"sd-a5-x", "sd-a5-y"}),
            event_group_by_id={"sd-a5-x": "event-0", "sd-a5-y": "event-0"},
            group_ordinal_by_event={"event-0": 0},
            provenance=PROVENANCE_HISTORICAL_OBJECT_CREATED_AT,
        ),
        RAROutcome.AMBIGUOUS, expected_ambiguous_candidate_ids=("sd-a5-x", "sd-a5-y"),
    ))

    a7_early = _c("sd-a7-early", "Draft_Early2.pdf", rank=1)
    a7_late = _c("sd-a7-late", "Draft_Late2.pdf", rank=0)
    cases.append(FactorialCase(
        "B-FIRST-WRONG-CLOCK", "A2L-OV-06", "SD-A-07", True, "",
        RARQuery("the first attachment", (a7_early, a7_late), RAREvidence(recency_hint="earlier")),
        AttachmentOrderOverlay(
            turn_membership_ids=frozenset({"sd-a7-early", "sd-a7-late"}),
            event_group_by_id={"sd-a7-early": "event-0", "sd-a7-late": "event-0"},
            group_ordinal_by_event={"event-0": 0},
            provenance=PROVENANCE_HISTORICAL_OBJECT_CREATED_AT,
        ),
        RAROutcome.AMBIGUOUS, expected_ambiguous_candidate_ids=("sd-a7-early", "sd-a7-late"),
    ))

    # B-LATEST-PROVENANCE-TWIN: byte-identical candidates/query to A-LATEST-2;
    # only provenance differs (UNKNOWN, not CURRENT_TURN_ATTACHMENT_SEQUENCE).
    t_new = _c("sd-a4-new", "Vacation_Photo_New.jpg", rank=0)
    t_old = _c("sd-a4-old", "Vacation_Photo_Old.jpg", rank=1)
    cases.append(FactorialCase(
        "B-LATEST-PROVENANCE-TWIN", "A2L-OV-02", "SD-A-04 (provenance twin)", True, "",
        RARQuery("the latest attachment", (t_new, t_old), RAREvidence(recency_hint="latest")),
        AttachmentOrderOverlay(
            turn_membership_ids=frozenset({"sd-a4-new", "sd-a4-old"}),
            event_group_by_id={"sd-a4-old": "event-0", "sd-a4-new": "event-1"},
            group_ordinal_by_event={"event-0": 0, "event-1": 1},
            provenance=PROVENANCE_UNKNOWN,
        ),
        RAROutcome.AMBIGUOUS, expected_ambiguous_candidate_ids=("sd-a4-new", "sd-a4-old"),
    ))

    # B-DISTRACTOR: natural NB-C-05 C2.
    _nb_data = nbh.load_fixture()
    _nb_lib = _nb_data["candidate_library"]
    _nb_case = next(c for c in _nb_data["cases"] if c["case_id"] == "NB-C-05")
    _nb_c2 = next(v for v in _nb_case["variants"] if v["candidate_condition"] == "C2")
    _nb_ids = _nb_c2["available_candidates"]
    _nb_candidates = nbh.build_candidate_pool(_nb_ids, _nb_lib, oracle_recency=False)
    _nb_gt = _nb_case["ground_truth_references"][0]
    _nb_turn_att = frozenset(_nb_case["conversation_context"]["turn_attachments"])
    cases.append(FactorialCase(
        "B-DISTRACTOR", "A2L-OV-07", "NB-C-05 C2 (natural)", True, "",
        RARQuery(_nb_gt["human_marked_span"], _nb_candidates, RAREvidence()),
        AttachmentOrderOverlay(
            turn_membership_ids=_nb_turn_att,
            event_group_by_id={cid: "event-0" for cid in _nb_turn_att},
            group_ordinal_by_event={"event-0": 0},
            provenance=PROVENANCE_HISTORICAL_OBJECT_CREATED_AT,
        ),
        RAROutcome.AMBIGUOUS, expected_ambiguous_candidate_ids=tuple(sorted(_nb_turn_att)),
    ))

    # --- §5.2 controls ---------------------------------------------------
    a2_1 = _c("sd-a2-att1", "Photo_1.jpg", rank=0)
    a2_2 = _c("sd-a2-att2", "Photo_2.jpg", rank=0)
    cases.append(FactorialCase(
        "C-GENERIC-2", "A2L-OV-08", "SD-A-02", False, "",
        RARQuery("the attachment", (a2_1, a2_2), RAREvidence()),
        AttachmentOrderOverlay(),
        RAROutcome.AMBIGUOUS, expected_ambiguous_candidate_ids=("sd-a2-att1", "sd-a2-att2"),
    ))

    _nbc4_case = next(c for c in _nb_data["cases"] if c["case_id"] == "NB-C-04")
    _nbc4_turn_att = frozenset(_nbc4_case["conversation_context"]["turn_attachments"])
    for pool_cond in ("C1", "C2"):
        _v = next(v for v in _nbc4_case["variants"] if v["candidate_condition"] == pool_cond)
        _ids = _v["available_candidates"]
        _cands = nbh.build_candidate_pool(_ids, _nb_lib, oracle_recency=False)
        _gt = _nbc4_case["ground_truth_references"][0]
        cases.append(FactorialCase(
            f"C-NATURAL-PHOTOS-{pool_cond}", "A2L-OV-09", f"NB-C-04 {pool_cond} (natural)", False, pool_cond,
            RARQuery(_gt["human_marked_span"], _cands, RAREvidence()),
            AttachmentOrderOverlay(
                turn_membership_ids=_nbc4_turn_att,
                event_group_by_id={cid: "event-0" for cid in _nbc4_turn_att},
                group_ordinal_by_event={"event-0": 0},
                provenance=PROVENANCE_HISTORICAL_OBJECT_CREATED_AT,
            ),
            RAROutcome.AMBIGUOUS, expected_ambiguous_candidate_ids=tuple(sorted(_nbc4_turn_att)),
        ))

    a8_invoice = _c("sd-a8-invoice", "Invoice_04.pdf", rank=0, tags=("invoice",))
    a8_photo = _c("sd-a8-photo", "Photo_Trip.jpg", rank=1)
    cases.append(FactorialCase(
        "C-LEXICAL-ATTACHMENT", "A2L-OV-10", "SD-A-08", False, "",
        RARQuery("the attached invoice", (a8_invoice, a8_photo), RAREvidence()),
        AttachmentOrderOverlay(),
        RAROutcome.RESOLVED, expected_candidate_id="sd-a8-invoice",
        reachable_by_factors=False,
        disclosure=(
            "Unreachable by any of the six frozen factors: Level 5.5's "
            "is_attachment counting has no lexical consumer in M/G/P/D/R/Q "
            "as literally scoped. Both raw baseline and the accepted H3 "
            "mechanism return AMBIGUOUS for this fixture in every "
            "configuration. Excluded from the qualification gate per "
            "explicit User direction (2026-09-24); still run and reported."
        ),
    ))

    c2_agenda = _c("sd-c2-agenda", "October_Agenda.pdf", rank=0, is_attachment=False)
    c2_minutes = _c("sd-c2-minutes", "Board_Minutes_Sep.pdf", rank=1, is_attachment=False, tags=("minutes",))
    cases.append(FactorialCase(
        "C-DOMAIN-RANK-SYNTH", "A2L-OV-11", "SD-C-02", False, "",
        RARQuery("the latest board minutes", (c2_agenda, c2_minutes), RAREvidence(recency_hint="latest")),
        AttachmentOrderOverlay(),
        RAROutcome.RESOLVED, expected_candidate_id="sd-c2-minutes",
    ))

    _nbd1_case = next(c for c in _nb_data["cases"] if c["case_id"] == "NB-D-01")
    _nbd1_c2 = next(v for v in _nbd1_case["variants"] if v["candidate_condition"] == "C2")
    _nbd1_ids = _nbd1_c2["available_candidates"]
    _nbd1_cands = nbh.build_candidate_pool(_nbd1_ids, _nb_lib, oracle_recency=True)
    _nbd1_gt = _nbd1_case["ground_truth_references"][0]
    cases.append(FactorialCase(
        "C-DOMAIN-RANK-NATURAL", "A2L-OV-12", "NB-D-01 C2 (natural, oracle ranks)", False, "C2",
        RARQuery(_nbd1_gt["human_marked_span"], _nbd1_cands, RAREvidence(recency_hint="latest")),
        AttachmentOrderOverlay(),
        RAROutcome.RESOLVED, expected_candidate_id="2f58b7c0-e6a3-4d91-a4c5-09d7e1f2d111",
    ))

    r1 = RARCandidate(id="doc_r1", title="Report 2025", candidate_type="document", recency_rank=1, is_attachment=False)
    r2 = RARCandidate(id="doc_r2", title="Report 2024", candidate_type="document", recency_rank=2, is_attachment=False)
    cases.append(FactorialCase(
        "C-NO-RANK0", "A2L-OV-13", "test_rc1_current_conflicting_no_rank0_abstains shape", False, "",
        RARQuery("the current report", (r1, r2), RAREvidence(recency_hint="current")),
        AttachmentOrderOverlay(),
        RAROutcome.UNKNOWN,  # "must not RESOLVE" -- UNKNOWN is the actual safe outcome; scorer checks outcome != RESOLVED
    ))

    return cases


FACTORIAL_CASES: List[FactorialCase] = _build_cases()

assert len(FACTORIAL_CASES) == 14, f"Expected 14 decision rows, got {len(FACTORIAL_CASES)}"
assert len({c.id for c in FACTORIAL_CASES}) == 14, "Duplicate case ids in A2.8L factorial fixtures"


def get_factorial_cases() -> List[FactorialCase]:
    return list(FACTORIAL_CASES)
