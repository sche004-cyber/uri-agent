"""M35 URIv1 -- A2.8K: Frozen S-D Diagnostic Minimal-Pair Battery.

Authored and hash-recorded BEFORE any hypothesis code exists (plan §7 step
order). Expected outcomes are fixed from the User's §8 Q1-Q4 freeze (see
`docs/plans/M35_URIV1_A2_8K_L5_EVIDENCE_SUFFICIENCY_PLAN.md` §11 history
entry), not from observing hypothesis behaviour. Changing any fixture here
after this freeze reopens the plan (plan §5).

Each item is an `RARFixture` (`uri_v1.turn.rar_contracts`), reused unmodified
for its invariant validation (`RARFixture.__post_init__` calls
`validate_rar_resolution`). Two fields specific to this battery are carried
outside the fixture, in `L5_DIAGNOSTIC_METADATA`, keyed by fixture id, because
`RARFixture`/`RARQuery`/`RARCandidate` are frozen contracts this batch must
not modify (plan §6, §18):

- `dx1_tie_ids`: the DX-1 turn-attachment tie oracle's input for this row
  (frozenset of candidate ids that share one rank/attach-event). Empty for
  every row except the Q2 Case-B (untrustworthy clock) twins, where it
  encodes the ground truth that both candidates were actually attached this
  turn despite carrying different `recency_rank` values.
- `measure_only`: True for DX-2 relative-anchor rows (§8 Q3). These are
  frozen to a safe-abstention expectation but are reported as MEASURE_ONLY,
  never scored as a target-class miss, per the User's freeze.

Semantic categories represented (plan §5 / directive §8):
- A. Attachment identity: generic "the attachment" at 1/2/3 compatible
  candidates (Q1); explicit "the latest/first attachment" under a
  trustworthy vs. untrustworthy ordering clock (Q2 Case A / Case B); a
  lexically distinguished attachment ("the attached invoice").
- B. Absent entity: "the earlier X" with X present vs. absent.
- C. Ordering domain: "the latest board minutes" matched vs. domain-violating
  pool composition (H3 target), plus the St/Street known-limitation pair.
- D. Relative anchor: "the one before that/it" (DX-2 measure-only).
- N. Negative controls: correct Level-5 bindings every hypothesis must
  preserve.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List, NamedTuple

from uri_v1.turn.rar_contracts import (
    RARBasis,
    RARCandidate,
    RAREvidence,
    RARFixture,
    RAROutcome,
    RARQuery,
)


class L5DiagnosticMeta(NamedTuple):
    dx1_tie_ids: FrozenSet[str]
    measure_only: bool


def _fixture(
    fid: str,
    category: str,
    ref: str,
    candidates,
    expected_outcome: RAROutcome,
    expected_candidate_id=None,
    expected_ambiguous_candidate_ids=(),
    recency_hint=None,
    target_type_hint=None,
    description: str = "",
) -> RARFixture:
    query = RARQuery(
        reference_expression=ref,
        candidates=tuple(candidates),
        local_evidence=RAREvidence(recency_hint=recency_hint, target_type_hint=target_type_hint),
    )
    return RARFixture(
        id=fid,
        name=fid,
        category=category,
        turn_text=ref,
        query=query,
        expected_outcome=expected_outcome,
        expected_candidate_id=expected_candidate_id,
        expected_ambiguous_candidate_ids=tuple(expected_ambiguous_candidate_ids),
        expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
        description=description,
    )


def _c(cid: str, title: str, *, rank: int = 0, is_attachment: bool = False, tags=()) -> RARCandidate:
    return RARCandidate(
        id=cid, title=title, candidate_type="document",
        recency_rank=rank, domain_tags=tuple(tags), is_attachment=is_attachment,
    )


# ---------------------------------------------------------------------------
# Class A -- Attachment identity / ordering
# ---------------------------------------------------------------------------

_a1_att = _c("sd-a1-att1", "Scanned_Form.pdf", is_attachment=True)
SD_A1 = _fixture(
    "SD-A-01", "attachment_identity_single", "the attachment", [_a1_att],
    RAROutcome.RESOLVED, expected_candidate_id=_a1_att.id,
    description="Generic attachment reference, exactly one compatible attachment -> RESOLVED.",
)

_a2_att1 = _c("sd-a2-att1", "Photo_1.jpg", is_attachment=True)
_a2_att2 = _c("sd-a2-att2", "Photo_2.jpg", is_attachment=True)
SD_A2 = _fixture(
    "SD-A-02", "attachment_identity_ambiguous", "the attachment", [_a2_att1, _a2_att2],
    RAROutcome.AMBIGUOUS, expected_ambiguous_candidate_ids=(_a2_att1.id, _a2_att2.id),
    description="Q1: generic attachment reference, 2 indistinguishable compatible attachments -> AMBIGUOUS.",
)

_a3_att1 = _c("sd-a3-att1", "Scan_A.pdf", rank=0, is_attachment=True)
_a3_att2 = _c("sd-a3-att2", "Scan_B.pdf", rank=1, is_attachment=True)
_a3_att3 = _c("sd-a3-att3", "Scan_C.pdf", rank=2, is_attachment=True)
SD_A3 = _fixture(
    "SD-A-03", "attachment_identity_ambiguous", "the attachment",
    [_a3_att1, _a3_att2, _a3_att3], RAROutcome.AMBIGUOUS,
    expected_ambiguous_candidate_ids=(_a3_att1.id, _a3_att2.id, _a3_att3.id),
    description="Q1: generic attachment reference, 3 indistinguishable compatible attachments -> AMBIGUOUS.",
)

_a4_new = _c("sd-a4-new", "Vacation_Photo_New.jpg", rank=0, is_attachment=True)
_a4_old = _c("sd-a4-old", "Vacation_Photo_Old.jpg", rank=1, is_attachment=True)
SD_A4 = _fixture(
    "SD-A-04", "attachment_ordering_trustworthy", "the latest attachment",
    [_a4_new, _a4_old], RAROutcome.RESOLVED, expected_candidate_id=_a4_new.id,
    recency_hint="latest",
    description="Q2 Case A: explicit 'latest attachment', ordering evidence is authoritative -> RESOLVED.",
)

_a5_x = _c("sd-a5-x", "Vacation_Photo_X.jpg", rank=0, is_attachment=True)
_a5_y = _c("sd-a5-y", "Vacation_Photo_Y.jpg", rank=1, is_attachment=True)
SD_A5 = _fixture(
    "SD-A-05", "attachment_ordering_untrustworthy_clock", "the latest attachment",
    [_a5_x, _a5_y], RAROutcome.AMBIGUOUS,
    expected_ambiguous_candidate_ids=(_a5_x.id, _a5_y.id), recency_hint="latest",
    description=(
        "Q2 Case B: explicit 'latest attachment', but recency_rank reflects historical "
        "created_at rather than current-turn attachment order (both were attached "
        "together this turn per DX-1 tie evidence) -> AMBIGUOUS, not a rank-driven bind."
    ),
)

_a6_early = _c("sd-a6-early", "Draft_Early.pdf", rank=1, is_attachment=True)
_a6_late = _c("sd-a6-late", "Draft_Late.pdf", rank=0, is_attachment=True)
SD_A6 = _fixture(
    "SD-A-06", "attachment_ordering_trustworthy", "the first attachment",
    [_a6_early, _a6_late], RAROutcome.RESOLVED, expected_candidate_id=_a6_early.id,
    recency_hint="earlier",
    description="Q2 Case A: explicit 'first attachment', ordering evidence authoritative -> RESOLVED.",
)

_a7_early = _c("sd-a7-early", "Draft_Early2.pdf", rank=1, is_attachment=True)
_a7_late = _c("sd-a7-late", "Draft_Late2.pdf", rank=0, is_attachment=True)
SD_A7 = _fixture(
    "SD-A-07", "attachment_ordering_untrustworthy_clock", "the first attachment",
    [_a7_early, _a7_late], RAROutcome.AMBIGUOUS,
    expected_ambiguous_candidate_ids=(_a7_early.id, _a7_late.id), recency_hint="earlier",
    description="Q2 Case B twin of SD-A-06: wrong clock (DX-1 tie) -> AMBIGUOUS.",
)

_a8_invoice = _c("sd-a8-invoice", "Invoice_04.pdf", rank=0, is_attachment=True, tags=("invoice",))
_a8_photo = _c("sd-a8-photo", "Photo_Trip.jpg", rank=1, is_attachment=True)
SD_A8 = _fixture(
    "SD-A-08", "attachment_lexically_distinguished", "the attached invoice",
    [_a8_invoice, _a8_photo], RAROutcome.RESOLVED, expected_candidate_id=_a8_invoice.id,
    description=(
        "Lexically distinguished attachment: only one of two attachments is compatible "
        "with 'invoice' -> RESOLVED. Distinct from SD-A-02/03 generic ambiguity."
    ),
)

# ---------------------------------------------------------------------------
# Class B -- Absent entity
# ---------------------------------------------------------------------------

_b1_new = _c("sd-b1-new", "Contract_2026.pdf", rank=0)
_b1_old = _c("sd-b1-old", "Contract_2025.pdf", rank=1)
SD_B1 = _fixture(
    "SD-B-01", "absent_entity_negative_control", "the earlier contract",
    [_b1_new, _b1_old], RAROutcome.RESOLVED, expected_candidate_id=_b1_old.id,
    recency_hint="earlier",
    description="Twin of SD-B-02: 'contract' present in the pool -> RESOLVED.",
)

_b2_memo = _c("sd-b2-memo", "Memo.pdf", rank=0)
_b2_notice = _c("sd-b2-notice", "Notice.pdf", rank=1)
SD_B2 = _fixture(
    "SD-B-02", "absent_entity", "the earlier contract",
    [_b2_memo, _b2_notice], RAROutcome.UNKNOWN, recency_hint="earlier",
    description="Absent entity: 'contract' is not in the pool -> UNKNOWN, not a rank-driven bind.",
)

# ---------------------------------------------------------------------------
# Class C -- Ordering domain
# ---------------------------------------------------------------------------

_c1_new = _c("sd-c1-new", "Board_Minutes_Oct.pdf", rank=0, tags=("minutes",))
_c1_old = _c("sd-c1-old", "Board_Minutes_Sep.pdf", rank=1, tags=("minutes",))
SD_C1 = _fixture(
    "SD-C-01", "ordering_domain_negative_control", "the latest board minutes",
    [_c1_new, _c1_old], RAROutcome.RESOLVED, expected_candidate_id=_c1_new.id,
    recency_hint="latest",
    description="Twin of SD-C-02: newest pool item IS board minutes -> RESOLVED.",
)

_c2_agenda = _c("sd-c2-agenda", "October_Agenda.pdf", rank=0)
_c2_minutes = _c("sd-c2-minutes", "Board_Minutes_Sep.pdf", rank=1, tags=("minutes",))
SD_C2 = _fixture(
    "SD-C-02", "ordering_domain", "the latest board minutes",
    [_c2_agenda, _c2_minutes], RAROutcome.RESOLVED, expected_candidate_id=_c2_minutes.id,
    recency_hint="latest",
    description=(
        "H3 target: the newest pool item (October_Agenda) is not board minutes; the "
        "newest compatible board-minutes candidate is the older item -> RESOLVED to it, "
        "not to the pool-wide newest item."
    ),
)

_c3_street = _c("sd-c3-street", "Main Street Annual Report.pdf", rank=0)
_c3_other = _c("sd-c3-other", "Oak Avenue Report.pdf", rank=1)
SD_C3 = _fixture(
    "SD-C-03", "known_limitation_street_abbreviation", "the latest report on Main St",
    [_c3_street, _c3_other], RAROutcome.RESOLVED, expected_candidate_id=_c3_street.id,
    recency_hint="latest",
    description=(
        "Known limitation: 'St' vs 'Street' abbreviation mismatch. Correct answer is "
        "Main_Street; H3's lexical compatibility check is expected to fail this pair "
        "(brittleness measured, not repaired -- no stemming/alias normalisation added)."
    ),
)

# ---------------------------------------------------------------------------
# Class D -- Relative anchor (DX-2 measure-only, Q3)
# ---------------------------------------------------------------------------

_d1_a = _c("sd-d1-a", "Report_A.pdf", rank=0)
_d1_b = _c("sd-d1-b", "Report_B.pdf", rank=1)
_d1_c = _c("sd-d1-c", "Report_C.pdf", rank=2)
SD_D1 = _fixture(
    "SD-D-01", "relative_anchor_measure_only", "the one before that",
    [_d1_a, _d1_b, _d1_c], RAROutcome.UNKNOWN,
    description="DX-2 measure-only: antecedent-relative reference with an intervening candidate.",
)

_d2_x = _c("sd-d2-x", "File_X.pdf", rank=0)
_d2_y = _c("sd-d2-y", "File_Y.pdf", rank=1)
_d2_z = _c("sd-d2-z", "File_Z.pdf", rank=2)
SD_D2 = _fixture(
    "SD-D-02", "relative_anchor_measure_only", "the one before it",
    [_d2_x, _d2_y, _d2_z], RAROutcome.UNKNOWN,
    description="DX-2 measure-only: antecedent-relative reference with an intervening candidate.",
)

# ---------------------------------------------------------------------------
# Class N -- Negative controls
# ---------------------------------------------------------------------------

_n1_new = _c("sd-n1-new", "Invoice_04.pdf", rank=0, tags=("invoice",))
_n1_old = _c("sd-n1-old", "Invoice_03.pdf", rank=1, tags=("invoice",))
SD_N1 = _fixture(
    "SD-N-01", "negative_control", "the latest invoice",
    [_n1_new, _n1_old], RAROutcome.RESOLVED, expected_candidate_id=_n1_new.id,
    recency_hint="latest",
    description="Negative control: legitimate deterministic 'latest' resolution among invoices.",
)

_n2_revised = _c("sd-n2-revised", "Policy_Draft_Revised.pdf", rank=0, tags=("revised",))
_n2_original = _c("sd-n2-original", "Policy_Draft.pdf", rank=1)
SD_N2 = _fixture(
    "SD-N-02", "negative_control", "the revised draft",
    [_n2_revised, _n2_original], RAROutcome.RESOLVED, expected_candidate_id=_n2_revised.id,
    recency_hint="revised",
    description="Negative control: legitimate 'revised' binding with one revised candidate.",
)

_n3_current = _c("sd-n3-current", "Budget_v3.xlsx", rank=0)
_n3_old = _c("sd-n3-old", "Budget_v2.xlsx", rank=1)
SD_N3 = _fixture(
    "SD-N-03", "negative_control", "the current version",
    [_n3_current, _n3_old], RAROutcome.RESOLVED, expected_candidate_id=_n3_current.id,
    recency_hint="current",
    description="Negative control: legitimate 'current' binding with valid rank-0 metadata.",
)


L5_DIAGNOSTIC_FIXTURES: List[RARFixture] = [
    SD_A1, SD_A2, SD_A3, SD_A4, SD_A5, SD_A6, SD_A7, SD_A8,
    SD_B1, SD_B2,
    SD_C1, SD_C2, SD_C3,
    SD_D1, SD_D2,
    SD_N1, SD_N2, SD_N3,
]

# DX-1 tie ids and DX-2 measure-only flags, keyed by fixture id. Not part of
# RARFixture/RARQuery/RARCandidate (frozen contracts) -- see module docstring.
L5_DIAGNOSTIC_METADATA: Dict[str, L5DiagnosticMeta] = {
    "SD-A-01": L5DiagnosticMeta(frozenset(), False),
    "SD-A-02": L5DiagnosticMeta(frozenset(), False),
    "SD-A-03": L5DiagnosticMeta(frozenset(), False),
    "SD-A-04": L5DiagnosticMeta(frozenset(), False),
    "SD-A-05": L5DiagnosticMeta(frozenset({_a5_x.id, _a5_y.id}), False),
    "SD-A-06": L5DiagnosticMeta(frozenset(), False),
    "SD-A-07": L5DiagnosticMeta(frozenset({_a7_early.id, _a7_late.id}), False),
    "SD-A-08": L5DiagnosticMeta(frozenset(), False),
    "SD-B-01": L5DiagnosticMeta(frozenset(), False),
    "SD-B-02": L5DiagnosticMeta(frozenset(), False),
    "SD-C-01": L5DiagnosticMeta(frozenset(), False),
    "SD-C-02": L5DiagnosticMeta(frozenset(), False),
    "SD-C-03": L5DiagnosticMeta(frozenset(), False),
    "SD-D-01": L5DiagnosticMeta(frozenset(), True),
    "SD-D-02": L5DiagnosticMeta(frozenset(), True),
    "SD-N-01": L5DiagnosticMeta(frozenset(), False),
    "SD-N-02": L5DiagnosticMeta(frozenset(), False),
    "SD-N-03": L5DiagnosticMeta(frozenset(), False),
}


def get_l5_diagnostic_fixtures() -> List[RARFixture]:
    return list(L5_DIAGNOSTIC_FIXTURES)
