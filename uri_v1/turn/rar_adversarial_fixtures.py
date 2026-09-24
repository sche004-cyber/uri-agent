"""Held-Out Adversarial RAR Safety Gate Fixtures (Batch A2.5 Phase 0).

Provides at least 20 held-out adversarial test cases challenging the deterministic
RAR engine with edge cases, distractors, misleading lexical overlap, contradictory
metadata, and ambiguous queries.

Invariants verified:
- WRONG BINDING RATE = 0.
- Safe abstention (UNKNOWN or AMBIGUOUS) over false certainty.
- Invariant under candidate list permutation (no index-0 bias).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

from uri_v1.turn.rar_contracts import (
    RARCandidate,
    RARDeterministicAnchor,
    RAREvidence,
    RARFailureClass,
    RAROutcome,
    RARQuery,
)


@dataclass(frozen=True)
class RARAdversarialFixture:
    """A held-out adversarial test fixture for deterministic RAR safety qualification."""

    id: str
    name: str
    category: str
    query: RARQuery
    expected_outcome: RAROutcome
    expected_candidate_id: Optional[str] = None
    acceptable_outcomes: Tuple[RAROutcome, ...] = ()


def _cand(
    cid: str,
    title: str,
    ctype: str = "document",
    tags: Sequence[str] = (),
    aliases: Sequence[str] = (),
    rank: int = 0,
    is_att: bool = False,
) -> RARCandidate:
    return RARCandidate(
        id=cid,
        title=title,
        candidate_type=ctype,
        domain_tags=tuple(tags),
        exact_aliases=tuple(aliases),
        recency_rank=rank,
        is_attachment=is_att,
    )


def get_rar_adversarial_fixtures() -> Tuple[RARAdversarialFixture, ...]:
    """Returns the held-out adversarial safety suite for Phase 0."""
    fixtures = [
        # 1. Duplicate titles (verbatim match across multiple identical titles -> AMBIGUOUS)
        RARAdversarialFixture(
            id="ADV-01",
            name="Duplicate titles with identical text",
            category="duplicate_titles",
            query=RARQuery(
                reference_expression="Project Proposal.pdf",
                candidates=(
                    _cand("c1", "Project Proposal.pdf"),
                    _cand("c2", "Project Proposal.pdf"),
                ),
            ),
            expected_outcome=RAROutcome.AMBIGUOUS,
            acceptable_outcomes=(RAROutcome.AMBIGUOUS,),
        ),

        # 2. Candidate order shuffling (reversed list must still produce AMBIGUOUS, no index-0 bias)
        RARAdversarialFixture(
            id="ADV-02",
            name="Candidate order shuffling on duplicate titles",
            category="candidate_order_shuffling",
            query=RARQuery(
                reference_expression="Project Proposal.pdf",
                candidates=(
                    _cand("c2", "Project Proposal.pdf"),
                    _cand("c1", "Project Proposal.pdf"),
                ),
            ),
            expected_outcome=RAROutcome.AMBIGUOUS,
            acceptable_outcomes=(RAROutcome.AMBIGUOUS,),
        ),

        # 3. Misleading lexical overlap: absent specific entity "sports"
        RARAdversarialFixture(
            id="ADV-03",
            name="Misleading lexical overlap with absent specific domain noun",
            category="misleading_lexical_overlap",
            query=RARQuery(
                reference_expression="the sports sanction letter",
                candidates=(
                    _cand("c1", "Hostel Sanction Letter", tags=("hostel", "sanction")),
                    _cand("c2", "Academic Fee Sanction Letter", tags=("academic", "fees")),
                ),
            ),
            expected_outcome=RAROutcome.UNKNOWN,
            acceptable_outcomes=(RAROutcome.UNKNOWN, RAROutcome.AMBIGUOUS),
        ),

        # 4. Stale active pointer: type mismatch with active candidate
        RARAdversarialFixture(
            id="ADV-04",
            name="Stale active pointer referencing absent audio type",
            category="stale_active_pointer",
            query=RARQuery(
                reference_expression="the audio recording",
                candidates=(
                    _cand("c1", "Committee Minutes.docx", ctype="document", tags=("recently_discussed",)),
                    _cand("c2", "Budget Overview.xlsx", ctype="spreadsheet"),
                ),
                local_evidence=RAREvidence(recency_hint="same", target_type_hint="audio"),
            ),
            expected_outcome=RAROutcome.UNKNOWN,
            acceptable_outcomes=(RAROutcome.UNKNOWN, RAROutcome.AMBIGUOUS),
        ),

        # 5. Two equally plausible 'previous' candidates (tied recency rank=1)
        RARAdversarialFixture(
            id="ADV-05",
            name="Two equally plausible previous candidates",
            category="tied_previous_candidates",
            query=RARQuery(
                reference_expression="the previous decision",
                candidates=(
                    _cand("c1", "Decision A", rank=1),
                    _cand("c2", "Decision B", rank=1),
                    _cand("c0", "Decision Current", rank=0),
                ),
                local_evidence=RAREvidence(recency_hint="previous"),
            ),
            expected_outcome=RAROutcome.AMBIGUOUS,
            acceptable_outcomes=(RAROutcome.AMBIGUOUS,),
        ),

        # 6. Missing timestamps: all rank defaults = 0 with 'latest'
        RARAdversarialFixture(
            id="ADV-06",
            name="Missing timestamps when querying latest",
            category="missing_timestamps",
            query=RARQuery(
                reference_expression="the latest audit report",
                candidates=(
                    _cand("c1", "Audit Draft A", rank=0),
                    _cand("c2", "Audit Draft B", rank=0),
                ),
                local_evidence=RAREvidence(recency_hint="latest"),
            ),
            expected_outcome=RAROutcome.AMBIGUOUS,
            acceptable_outcomes=(RAROutcome.AMBIGUOUS,),
        ),

        # 7. Contradictory recency metadata: 'earlier' when all ranks are 0
        RARAdversarialFixture(
            id="ADV-07",
            name="Contradictory recency metadata for earlier reference",
            category="contradictory_recency_metadata",
            query=RARQuery(
                reference_expression="the earlier order",
                candidates=(
                    _cand("c1", "Office Order Alpha", rank=0),
                    _cand("c2", "Office Order Beta", rank=0),
                ),
                local_evidence=RAREvidence(recency_hint="earlier"),
            ),
            expected_outcome=RAROutcome.UNKNOWN,
            acceptable_outcomes=(RAROutcome.UNKNOWN, RAROutcome.AMBIGUOUS),
        ),

        # 8. Irrelevant distractor candidates surrounding exact alias match
        RARAdversarialFixture(
            id="ADV-08",
            name="Exact alias amidst dense irrelevant distractors",
            category="irrelevant_distractors",
            query=RARQuery(
                reference_expression="ORD-994",
                candidates=(
                    _cand("d1", "Lab Policy Memo", tags=("lab",)),
                    _cand("d2", "Vendor Quotation", tags=("vendor",)),
                    _cand("d3", "Meeting Notes", tags=("notes",)),
                    _cand("d4", "Campus Map", tags=("estate",)),
                    _cand("target", "Office Order 994", aliases=("ORD-994",)),
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="target",
            acceptable_outcomes=(RAROutcome.RESOLVED,),
        ),

        # 9. Same title across different target types without type hint
        RARAdversarialFixture(
            id="ADV-09",
            name="Same title across different candidate types without type hint",
            category="same_title_diff_types",
            query=RARQuery(
                reference_expression="Annual Report",
                candidates=(
                    _cand("doc1", "Annual Report.pdf", ctype="document"),
                    _cand("aud1", "Annual Report.mp3", ctype="audio"),
                ),
            ),
            expected_outcome=RAROutcome.AMBIGUOUS,
            acceptable_outcomes=(RAROutcome.AMBIGUOUS,),
        ),

        # 10. Multiple pronouns in query
        RARAdversarialFixture(
            id="ADV-10",
            name="Multiple pronouns without anchor",
            category="multiple_pronouns",
            query=RARQuery(
                reference_expression="it and that one",
                candidates=(
                    _cand("c1", "Document Alpha"),
                    _cand("c2", "Document Beta"),
                ),
            ),
            expected_outcome=RAROutcome.AMBIGUOUS,
            acceptable_outcomes=(RAROutcome.AMBIGUOUS,),
        ),

        # 11. Multiple references of different types (cross reference)
        RARAdversarialFixture(
            id="ADV-11",
            name="Cross-reference mentioning two distinct object types",
            category="cross_reference",
            query=RARQuery(
                reference_expression="the spreadsheet and the email",
                candidates=(
                    _cand("s1", "Q3 Financial Sheet.xlsx", ctype="spreadsheet"),
                    _cand("e1", "Dean Notification Email.eml", ctype="email"),
                ),
            ),
            expected_outcome=RAROutcome.AMBIGUOUS,
            acceptable_outcomes=(RAROutcome.AMBIGUOUS,),
        ),

        # 12. Negated candidate via negation spans
        RARAdversarialFixture(
            id="ADV-12",
            name="Negated candidate eliminated leaving single survivor",
            category="negated_candidate",
            query=RARQuery(
                reference_expression="the proposal",
                candidates=(
                    _cand("p_draft", "Draft Proposal", tags=("draft",)),
                    _cand("p_final", "Final Proposal", tags=("final",)),
                ),
                local_evidence=RAREvidence(negation_spans=("draft proposal",)),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="p_final",
            acceptable_outcomes=(RAROutcome.RESOLVED,),
        ),

        # 13. 'not that one' rejection without selecting alternative
        RARAdversarialFixture(
            id="ADV-13",
            name="User says 'not that one' rejecting active candidate",
            category="not_that_one",
            query=RARQuery(
                reference_expression="not that one",
                candidates=(
                    _cand("c1", "Primary Memo", tags=("rejected_in_turn",)),
                    _cand("c2", "Secondary Memo"),
                ),
                local_evidence=RAREvidence(negation_spans=("that one",)),
            ),
            expected_outcome=RAROutcome.UNKNOWN,
            acceptable_outcomes=(RAROutcome.UNKNOWN, RAROutcome.AMBIGUOUS),
        ),

        # 14. 'the other one' contrast selection
        RARAdversarialFixture(
            id="ADV-14",
            name="'the other one' contrast selection after rejection",
            category="the_other_one",
            query=RARQuery(
                reference_expression="the other one",
                candidates=(
                    _cand("c1", "Option A", tags=("rejected_in_turn",)),
                    _cand("c2", "Option B"),
                ),
                local_evidence=RAREvidence(negation_spans=("Option A",), recency_hint="other"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="c2",
            acceptable_outcomes=(RAROutcome.RESOLVED,),
        ),

        # 15. Revised vs original version relationship
        RARAdversarialFixture(
            id="ADV-15",
            name="Original version ordinal selection",
            category="revised_vs_original",
            query=RARQuery(
                reference_expression="the original memo",
                candidates=(
                    _cand("v1", "Budget Memo", rank=1, tags=("original",)),
                    _cand("v2", "Budget Memo Revised", rank=0, tags=("revised",)),
                ),
                local_evidence=RAREvidence(recency_hint="original"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="v1",
            acceptable_outcomes=(RAROutcome.RESOLVED,),
        ),

        # 16. Strong TF-IDF overlap but wrong semantic identity (absent year 2024)
        RARAdversarialFixture(
            id="ADV-16",
            name="Strong lexical overlap with missing year qualifier",
            category="strong_overlap_wrong_identity",
            query=RARQuery(
                reference_expression="2024 campus carbon emission audit",
                candidates=(
                    _cand("c2023", "2023 campus carbon emission audit"),
                    _cand("c2022", "2022 campus energy audit"),
                ),
            ),
            expected_outcome=RAROutcome.UNKNOWN,
            acceptable_outcomes=(RAROutcome.UNKNOWN, RAROutcome.AMBIGUOUS),
        ),

        # 17. Insufficient metadata: empty candidate types with target_type_hint
        RARAdversarialFixture(
            id="ADV-17",
            name="Insufficient metadata with empty candidate types",
            category="insufficient_metadata",
            query=RARQuery(
                reference_expression="the report",
                candidates=(
                    _cand("c1", "Report Alpha", ctype=""),
                    _cand("c2", "Report Beta", ctype=""),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.UNKNOWN,
            acceptable_outcomes=(RAROutcome.UNKNOWN, RAROutcome.AMBIGUOUS),
        ),

        # 18. Zero candidates in pool
        RARAdversarialFixture(
            id="ADV-18",
            name="Zero candidates in pool",
            category="zero_candidates",
            query=RARQuery(
                reference_expression="the invoice",
                candidates=(),
            ),
            expected_outcome=RAROutcome.UNKNOWN,
            acceptable_outcomes=(RAROutcome.UNKNOWN,),
        ),

        # 19. One valid candidate among 8 distractors with exact ID
        RARAdversarialFixture(
            id="ADV-19",
            name="Single valid candidate with exact ID among many distractors",
            category="valid_among_distractors",
            query=RARQuery(
                reference_expression="INV-4001",
                candidates=(
                    _cand("d1", "Memo 1"),
                    _cand("d2", "Memo 2"),
                    _cand("d3", "Memo 3"),
                    _cand("d4", "Memo 4"),
                    _cand("d5", "Memo 5"),
                    _cand("d6", "Memo 6"),
                    _cand("INV-4001", "Vendor Invoice 4001"),
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="INV-4001",
            acceptable_outcomes=(RAROutcome.RESOLVED,),
        ),

        # 20. Ambiguous ownership: 'his proposal' with multiple male/neutral candidates
        RARAdversarialFixture(
            id="ADV-20",
            name="Ambiguous ownership pronoun with ungendered candidates",
            category="ambiguous_ownership",
            query=RARQuery(
                reference_expression="his proposal",
                candidates=(
                    _cand("c1", "Dean Academic Proposal", tags=("faculty",)),
                    _cand("c2", "Director Research Proposal", tags=("director",)),
                ),
            ),
            expected_outcome=RAROutcome.AMBIGUOUS,
            acceptable_outcomes=(RAROutcome.AMBIGUOUS,),
        ),

        # 21. Absent specific person name in query
        RARAdversarialFixture(
            id="ADV-21",
            name="Absent specific person name with generic word overlap",
            category="absent_entity_name",
            query=RARQuery(
                reference_expression="Dr. Sen's lab requisition",
                candidates=(
                    _cand("c1", "Dr. Verma's lab requisition"),
                    _cand("c2", "Hostel maintenance requisition"),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.UNKNOWN,
            acceptable_outcomes=(RAROutcome.UNKNOWN, RAROutcome.AMBIGUOUS),
        ),

        # 22. Tied lexical scores under candidate order permutation
        RARAdversarialFixture(
            id="ADV-22",
            name="Tied lexical scores under permutation",
            category="tied_lexical_permutation",
            query=RARQuery(
                reference_expression="quarterly financial analysis",
                candidates=(
                    _cand("c1", "Quarterly Analysis Summary"),
                    _cand("c2", "Financial Analysis Summary"),
                ),
            ),
            expected_outcome=RAROutcome.AMBIGUOUS,
            acceptable_outcomes=(RAROutcome.AMBIGUOUS,),
        ),

        # 23. Active UI selection amidst other candidates
        RARAdversarialFixture(
            id="ADV-23",
            name="Active UI selection mechanically anchor-bound",
            category="active_ui_selection",
            query=RARQuery(
                reference_expression="this document",
                candidates=(
                    _cand("c1", "Background Paper.pdf"),
                    _cand("ui_target", "Actionable Item.docx"),
                ),
                deterministic_anchor=RARDeterministicAnchor(selected_ui_id="ui_target"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="ui_target",
            acceptable_outcomes=(RAROutcome.RESOLVED,),
        ),

        # 24. Current attachment mechanically anchor-bound
        RARAdversarialFixture(
            id="ADV-24",
            name="Current attachment mechanically anchor-bound",
            category="current_attachment",
            query=RARQuery(
                reference_expression="the attachment",
                candidates=(
                    _cand("c1", "Parent Email.eml"),
                    _cand("att1", "Spreadsheet.xlsx", is_att=True),
                ),
                deterministic_anchor=RARDeterministicAnchor(current_attachment_id="att1"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="att1",
            acceptable_outcomes=(RAROutcome.RESOLVED,),
        ),
    ]
    return tuple(fixtures)
