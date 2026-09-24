"""Diagnostic fixture tranche for Batch A2.5: Reference Anchor Resolution (RAR).

This module defines 24 model-neutral diagnostic fixtures across 8 key categories:
1. Simple candidate selection (2-3 candidates, single clear type/name match)
2. UNKNOWN (referent not present in candidate set, safe abstention required)
3. AMBIGUOUS (multiple equally plausible candidates, safe discrimination abstention required)
4. Relational references (previous, revised, same, earlier; order/recency signals)
5. Negation / contrast (skip X send Y, not that one the other one, don't email X notify Y)
6. Distractors (recent unrelated items of different/same types testing false-positive resistance)
7. Multi-reference turns (mixed independent references within single user turn)
8. Deterministic bypass (exact ID, foreground UI object, current attachment, exact alias)

All fixtures use model-neutral data structures (not prompt strings or raw JSON).
"""

from __future__ import annotations

from typing import List, Tuple

from uri_v1.turn.rar_contracts import (
    RARBasis,
    RARCandidate,
    RARDeterministicAnchor,
    RAREvidence,
    RARFixture,
    RAROutcome,
    RARQuery,
)


def get_rar_diagnostic_fixtures() -> Tuple[RARFixture, ...]:
    """Returns the complete tranche of 24 realistic URI diagnostic fixtures."""
    fixtures: List[RARFixture] = []

    # =========================================================================
    # Category 1: Simple Candidate Selection (3 fixtures)
    # =========================================================================
    fixtures.append(
        RARFixture(
            id="RAR-FIX-01",
            name="Simple draft selection between document and email",
            category="simple_selection",
            turn_text="Send that draft to the warden",
            query=RARQuery(
                reference_expression="that draft",
                candidates=(
                    RARCandidate(
                        id="doc_policy_draft",
                        title="Hostel_Policy_Draft_2026.docx",
                        candidate_type="document",
                        recency_rank=0,
                        domain_tags=("hostel", "draft", "policy"),
                    ),
                    RARCandidate(
                        id="email_wifi_notice",
                        title="Wi-Fi Maintenance Notice",
                        candidate_type="email",
                        recency_rank=1,
                        domain_tags=("network", "maintenance"),
                    ),
                ),
                local_evidence=RAREvidence(
                    clause_text="Send that draft to the warden",
                    candidate_verbs=("send",),
                    target_type_hint="document",
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="doc_policy_draft",
            expected_basis=RARBasis.MODEL_SELECTION,
            description="Clear type and domain alignment with 'draft' pointing to Hostel_Policy_Draft_2026.docx.",
        )
    )

    fixtures.append(
        RARFixture(
            id="RAR-FIX-02",
            name="Forward email when candidate pool contains email and PDF manual",
            category="simple_selection",
            turn_text="Forward the email to the registrar",
            query=RARQuery(
                reference_expression="the email",
                candidates=(
                    RARCandidate(
                        id="doc_lab_manual",
                        title="Spectrometer_Operation_Manual.pdf",
                        candidate_type="document",
                        recency_rank=0,
                        domain_tags=("lab", "equipment"),
                    ),
                    RARCandidate(
                        id="email_dean_schedule",
                        title="Fwd: Dean Review Meeting Schedule",
                        candidate_type="email",
                        recency_rank=1,
                        domain_tags=("administrative", "schedule"),
                    ),
                ),
                local_evidence=RAREvidence(
                    clause_text="Forward the email to the registrar",
                    candidate_verbs=("forward",),
                    target_type_hint="email",
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="email_dean_schedule",
            expected_basis=RARBasis.MODEL_SELECTION,
            description="Type tag discriminates email from PDF manual.",
        )
    )

    fixtures.append(
        RARFixture(
            id="RAR-FIX-03",
            name="Run onboarding workflow vs meeting notes document",
            category="simple_selection",
            turn_text="Trigger the onboarding workflow",
            query=RARQuery(
                reference_expression="the onboarding workflow",
                candidates=(
                    RARCandidate(
                        id="wf_student_onboard",
                        title="Student Onboarding & Verification Flow",
                        candidate_type="workflow",
                        recency_rank=0,
                        domain_tags=("student", "onboarding", "automation"),
                    ),
                    RARCandidate(
                        id="doc_minutes",
                        title="Admissions_Committee_Minutes.docx",
                        candidate_type="document",
                        recency_rank=1,
                        domain_tags=("admissions", "meeting"),
                    ),
                ),
                local_evidence=RAREvidence(
                    clause_text="Trigger the onboarding workflow",
                    candidate_verbs=("trigger",),
                    target_type_hint="workflow",
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="wf_student_onboard",
            expected_basis=RARBasis.MODEL_SELECTION,
            description="Explicit type match for workflow automation vs notes.",
        )
    )

    # =========================================================================
    # Category 2: UNKNOWN (Referent Not in Candidate Set) (3 fixtures)
    # =========================================================================
    fixtures.append(
        RARFixture(
            id="RAR-FIX-04",
            name="Quarterly financial report missing from cafeteria and IT ticket candidates",
            category="unknown",
            turn_text="Summarize the quarterly financial report",
            query=RARQuery(
                reference_expression="the quarterly financial report",
                candidates=(
                    RARCandidate(
                        id="email_cafeteria",
                        title="Cafeteria Menu Feedback",
                        candidate_type="email",
                        recency_rank=0,
                        domain_tags=("cafeteria", "feedback"),
                    ),
                    RARCandidate(
                        id="ticket_printer",
                        title="Ticket #402: Library Printer Jam",
                        candidate_type="workflow",
                        recency_rank=1,
                        domain_tags=("support", "hardware"),
                    ),
                ),
                local_evidence=RAREvidence(
                    clause_text="Summarize the quarterly financial report",
                    candidate_verbs=("summarize",),
                    target_type_hint="document",
                ),
            ),
            expected_outcome=RAROutcome.UNKNOWN,
            expected_candidate_id=None,
            expected_basis=RARBasis.MODEL_SELECTION,
            description="Referent does not exist in candidate pool; safe abstention as UNKNOWN required.",
        )
    )

    fixtures.append(
        RARFixture(
            id="RAR-FIX-05",
            name="Spreadsheet reference when only PDFs and emails are known",
            category="unknown",
            turn_text="Open that spreadsheet",
            query=RARQuery(
                reference_expression="that spreadsheet",
                candidates=(
                    RARCandidate(
                        id="doc_syllabus",
                        title="Course_Syllabus_Fall2026.pdf",
                        candidate_type="document",
                        recency_rank=0,
                    ),
                    RARCandidate(
                        id="email_reminder",
                        title="Grade Submission Deadline",
                        candidate_type="email",
                        recency_rank=1,
                    ),
                ),
                local_evidence=RAREvidence(
                    clause_text="Open that spreadsheet",
                    candidate_verbs=("open",),
                    target_type_hint="spreadsheet",
                ),
            ),
            expected_outcome=RAROutcome.UNKNOWN,
            expected_candidate_id=None,
            expected_basis=RARBasis.MODEL_SELECTION,
            description="Zero spreadsheet candidates exist; must abstain with UNKNOWN, not guess.",
        )
    )

    fixtures.append(
        RARFixture(
            id="RAR-FIX-06",
            name="Person reference to Dr. Verma when candidate pool has only student entities",
            category="unknown",
            turn_text="Send the notification to Dr. Verma",
            query=RARQuery(
                reference_expression="Dr. Verma",
                candidates=(
                    RARCandidate(
                        id="person_student_amit",
                        title="Amit Sharma (Student Roll 1024)",
                        candidate_type="person",
                        recency_rank=0,
                        domain_tags=("student", "hostel-1"),
                    ),
                    RARCandidate(
                        id="person_student_priya",
                        title="Priya Patel (Student Roll 1088)",
                        candidate_type="person",
                        recency_rank=1,
                        domain_tags=("student", "hostel-2"),
                    ),
                ),
                local_evidence=RAREvidence(
                    clause_text="Send the notification to Dr. Verma",
                    candidate_verbs=("send",),
                    target_type_hint="person",
                ),
            ),
            expected_outcome=RAROutcome.UNKNOWN,
            expected_candidate_id=None,
            expected_basis=RARBasis.MODEL_SELECTION,
            description="Target entity not in candidate pool; must abstain with UNKNOWN.",
        )
    )

    # =========================================================================
    # Category 3: AMBIGUOUS (Multiple Equally Plausible Candidates) (3 fixtures)
    # =========================================================================
    fixtures.append(
        RARFixture(
            id="RAR-FIX-07",
            name="Two quarterly budget spreadsheets with equal plausibility",
            category="ambiguous",
            turn_text="Open the budget spreadsheet",
            query=RARQuery(
                reference_expression="the budget spreadsheet",
                candidates=(
                    RARCandidate(
                        id="sheet_budget_q1",
                        title="Hostel_Budget_Q1_2026.xlsx",
                        candidate_type="spreadsheet",
                        recency_rank=1,
                        domain_tags=("budget", "hostel", "finance"),
                    ),
                    RARCandidate(
                        id="sheet_budget_q2",
                        title="Hostel_Budget_Q2_2026.xlsx",
                        candidate_type="spreadsheet",
                        recency_rank=1,
                        domain_tags=("budget", "hostel", "finance"),
                    ),
                ),
                local_evidence=RAREvidence(
                    clause_text="Open the budget spreadsheet",
                    candidate_verbs=("open",),
                    target_type_hint="spreadsheet",
                ),
            ),
            expected_outcome=RAROutcome.AMBIGUOUS,
            expected_ambiguous_candidate_ids=("sheet_budget_q1", "sheet_budget_q2"),
            expected_basis=RARBasis.MODEL_SELECTION,
            description="Two equally matching budget spreadsheets; must abstain as AMBIGUOUS.",
        )
    )

    fixtures.append(
        RARFixture(
            id="RAR-FIX-08",
            name="Two equipment invoices in same billing period",
            category="ambiguous",
            turn_text="Forward the invoice to accounts",
            query=RARQuery(
                reference_expression="the invoice",
                candidates=(
                    RARCandidate(
                        id="doc_inv_lab",
                        title="Invoice_LabEquipment_Oct26.pdf",
                        candidate_type="document",
                        recency_rank=0,
                        domain_tags=("invoice", "lab", "billing"),
                    ),
                    RARCandidate(
                        id="doc_inv_chem",
                        title="Invoice_ChemicalSupplies_Oct26.pdf",
                        candidate_type="document",
                        recency_rank=0,
                        domain_tags=("invoice", "chemistry", "billing"),
                    ),
                ),
                local_evidence=RAREvidence(
                    clause_text="Forward the invoice to accounts",
                    candidate_verbs=("forward",),
                    target_type_hint="document",
                ),
            ),
            expected_outcome=RAROutcome.AMBIGUOUS,
            expected_ambiguous_candidate_ids=("doc_inv_lab", "doc_inv_chem"),
            expected_basis=RARBasis.MODEL_SELECTION,
            description="Multiple matching invoices without distinguishing qualifier; AMBIGUOUS required.",
        )
    )

    fixtures.append(
        RARFixture(
            id="RAR-FIX-09",
            name="Two student grade dispute submissions",
            category="ambiguous",
            turn_text="Review the student's submission",
            query=RARQuery(
                reference_expression="the student's submission",
                candidates=(
                    RARCandidate(
                        id="doc_sub_rahul",
                        title="Grade_Review_Submission_Rahul.pdf",
                        candidate_type="document",
                        recency_rank=1,
                        domain_tags=("student", "submission", "grades"),
                    ),
                    RARCandidate(
                        id="doc_sub_sneha",
                        title="Grade_Review_Submission_Sneha.pdf",
                        candidate_type="document",
                        recency_rank=1,
                        domain_tags=("student", "submission", "grades"),
                    ),
                ),
                local_evidence=RAREvidence(
                    clause_text="Review the student's submission",
                    candidate_verbs=("review",),
                    target_type_hint="document",
                ),
            ),
            expected_outcome=RAROutcome.AMBIGUOUS,
            expected_ambiguous_candidate_ids=("doc_sub_rahul", "doc_sub_sneha"),
            expected_basis=RARBasis.MODEL_SELECTION,
            description="Two active student submissions with identical metadata cues; must preserve AMBIGUOUS.",
        )
    )

    # =========================================================================
    # Category 4: Relational References (Previous, Revised, Same, Earlier) (4 fixtures)
    # =========================================================================
    fixtures.append(
        RARFixture(
            id="RAR-FIX-10",
            name="Revised draft vs original draft version",
            category="relational",
            turn_text="Send the revised draft to the committee",
            query=RARQuery(
                reference_expression="the revised draft",
                candidates=(
                    RARCandidate(
                        id="doc_draft_v1",
                        title="Hostel_Allotment_Rules_v1.docx",
                        candidate_type="document",
                        recency_rank=2,
                        domain_tags=("draft", "original"),
                    ),
                    RARCandidate(
                        id="doc_draft_v2",
                        title="Hostel_Allotment_Rules_v2_revised.docx",
                        candidate_type="document",
                        recency_rank=0,
                        domain_tags=("draft", "revised"),
                    ),
                ),
                local_evidence=RAREvidence(
                    clause_text="Send the revised draft to the committee",
                    candidate_verbs=("send",),
                    recency_hint="revised",
                    target_type_hint="document",
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="doc_draft_v2",
            expected_basis=RARBasis.MODEL_SELECTION,
            description="'revised draft' binds to v2_revised based on tag and recency signal.",
        )
    )

    fixtures.append(
        RARFixture(
            id="RAR-FIX-11",
            name="The previous email in active thread",
            category="relational",
            turn_text="Reply to the previous email",
            query=RARQuery(
                reference_expression="the previous email",
                candidates=(
                    RARCandidate(
                        id="email_latest",
                        title="Re: Lab Allotment Final",
                        candidate_type="email",
                        recency_rank=0,
                    ),
                    RARCandidate(
                        id="email_prev",
                        title="Re: Lab Allotment Draft Inquiry",
                        candidate_type="email",
                        recency_rank=1,
                    ),
                    RARCandidate(
                        id="email_oldest",
                        title="Lab Allotment Initial Notice",
                        candidate_type="email",
                        recency_rank=2,
                    ),
                ),
                local_evidence=RAREvidence(
                    clause_text="Reply to the previous email",
                    candidate_verbs=("reply",),
                    recency_hint="previous",
                    target_type_hint="email",
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="email_prev",
            expected_basis=RARBasis.MODEL_SELECTION,
            description="'previous email' binds to recency_rank=1, skipping latest (recency_rank=0).",
        )
    )

    fixtures.append(
        RARFixture(
            id="RAR-FIX-12",
            name="The same document as discussed in prior turn",
            category="relational",
            turn_text="Share the same document with the dean",
            query=RARQuery(
                reference_expression="the same document",
                candidates=(
                    RARCandidate(
                        id="doc_prior_active",
                        title="Procurement_Report_2026.pdf",
                        candidate_type="document",
                        recency_rank=0,
                        domain_tags=("recently_discussed",),
                    ),
                    RARCandidate(
                        id="doc_dormant",
                        title="Cafeteria_Menu.pdf",
                        candidate_type="document",
                        recency_rank=4,
                        domain_tags=("unrelated",),
                    ),
                ),
                local_evidence=RAREvidence(
                    clause_text="Share the same document with the dean",
                    candidate_verbs=("share",),
                    recency_hint="same",
                    target_type_hint="document",
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="doc_prior_active",
            expected_basis=RARBasis.MODEL_SELECTION,
            description="'the same document' anchors to recently discussed document in active turn context.",
        )
    )

    fixtures.append(
        RARFixture(
            id="RAR-FIX-13",
            name="The earlier version of the proposal",
            category="relational",
            turn_text="Compare it against the earlier version",
            query=RARQuery(
                reference_expression="the earlier version",
                candidates=(
                    RARCandidate(
                        id="doc_prop_current",
                        title="Grant_Proposal_v3.pdf",
                        candidate_type="document",
                        recency_rank=0,
                    ),
                    RARCandidate(
                        id="doc_prop_earlier",
                        title="Grant_Proposal_v1.pdf",
                        candidate_type="document",
                        recency_rank=2,
                    ),
                ),
                local_evidence=RAREvidence(
                    clause_text="Compare it against the earlier version",
                    candidate_verbs=("compare",),
                    recency_hint="earlier",
                    target_type_hint="document",
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="doc_prop_earlier",
            expected_basis=RARBasis.MODEL_SELECTION,
            description="'the earlier version' targets older candidate in recency rank.",
        )
    )

    # =========================================================================
    # Category 5: Negation / Contrast (3 fixtures)
    # =========================================================================
    fixtures.append(
        RARFixture(
            id="RAR-FIX-14",
            name="Skip the invoice, send the proposal",
            category="negation_contrast",
            turn_text="Skip the invoice, send the proposal",
            query=RARQuery(
                reference_expression="the proposal",
                candidates=(
                    RARCandidate(
                        id="doc_inv_vendor",
                        title="Vendor_Invoice_402.pdf",
                        candidate_type="document",
                        recency_rank=0,
                        domain_tags=("invoice", "billing"),
                    ),
                    RARCandidate(
                        id="doc_proposal_rnd",
                        title="RnD_Research_Proposal_2026.docx",
                        candidate_type="document",
                        recency_rank=1,
                        domain_tags=("proposal", "research"),
                    ),
                ),
                local_evidence=RAREvidence(
                    clause_text="send the proposal",
                    negation_spans=("Skip the invoice",),
                    candidate_verbs=("send",),
                    target_type_hint="document",
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="doc_proposal_rnd",
            expected_basis=RARBasis.MODEL_SELECTION,
            description="Positive target 'the proposal' resolved while 'the invoice' is explicitly negated/skipped.",
        )
    )

    fixtures.append(
        RARFixture(
            id="RAR-FIX-15",
            name="Not that one, the other one (referring to unrejected candidate)",
            category="negation_contrast",
            turn_text="Not that one, the other one",
            query=RARQuery(
                reference_expression="the other one",
                candidates=(
                    RARCandidate(
                        id="doc_plan_rejected",
                        title="Campus_Expansion_Plan_Draft.docx",
                        candidate_type="document",
                        recency_rank=0,
                        domain_tags=("rejected_in_turn",),
                    ),
                    RARCandidate(
                        id="doc_plan_approved",
                        title="Campus_Expansion_Plan_Final.docx",
                        candidate_type="document",
                        recency_rank=1,
                        domain_tags=("alternative",),
                    ),
                ),
                local_evidence=RAREvidence(
                    clause_text="the other one",
                    negation_spans=("Not that one",),
                    recency_hint="other",
                    target_type_hint="document",
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="doc_plan_approved",
            expected_basis=RARBasis.MODEL_SELECTION,
            description="Contrastive pronoun 'the other one' resolves to non-negated alternative candidate.",
        )
    )

    fixtures.append(
        RARFixture(
            id="RAR-FIX-16",
            name="Don't email the director, notify the warden",
            category="negation_contrast",
            turn_text="Don't email the director, notify the warden",
            query=RARQuery(
                reference_expression="the warden",
                candidates=(
                    RARCandidate(
                        id="ent_director",
                        title="Office of the Director",
                        candidate_type="person",
                        recency_rank=0,
                        domain_tags=("director", "administration"),
                    ),
                    RARCandidate(
                        id="ent_warden",
                        title="Prof. K. Sen (Chief Warden)",
                        candidate_type="person",
                        recency_rank=1,
                        domain_tags=("warden", "hostel"),
                    ),
                ),
                local_evidence=RAREvidence(
                    clause_text="notify the warden",
                    negation_spans=("Don't email the director",),
                    candidate_verbs=("notify",),
                    target_type_hint="person",
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="ent_warden",
            expected_basis=RARBasis.MODEL_SELECTION,
            description="Entity contrast resolves to the positively targeted 'warden', rejecting the negated 'director'.",
        )
    )

    # =========================================================================
    # Category 6: Distractors (3 fixtures)
    # =========================================================================
    fixtures.append(
        RARFixture(
            id="RAR-FIX-17",
            name="Budget table target amidst flyer and lunch thread distractors",
            category="distractors",
            turn_text="Attach the budget table to the draft",
            query=RARQuery(
                reference_expression="the budget table",
                candidates=(
                    RARCandidate(
                        id="distractor_flyer",
                        title="Annual_Day_Flyer.pdf",
                        candidate_type="document",
                        recency_rank=0,
                        domain_tags=("event", "flyer"),
                    ),
                    RARCandidate(
                        id="distractor_thread",
                        title="Lunch Catering Options Thread",
                        candidate_type="email",
                        recency_rank=1,
                        domain_tags=("catering", "admin"),
                    ),
                    RARCandidate(
                        id="target_budget_sheet",
                        title="Department_Budget_Table_2026.xlsx",
                        candidate_type="spreadsheet",
                        recency_rank=2,
                        domain_tags=("budget", "finance", "table"),
                    ),
                ),
                local_evidence=RAREvidence(
                    clause_text="Attach the budget table to the draft",
                    candidate_verbs=("attach",),
                    target_type_hint="spreadsheet",
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="target_budget_sheet",
            expected_basis=RARBasis.MODEL_SELECTION,
            description="Recency-biased distractors must be resisted in favor of exact domain/type match.",
        )
    )

    fixtures.append(
        RARFixture(
            id="RAR-FIX-18",
            name="Contractor entity target amidst prominent faculty distractors",
            category="distractors",
            turn_text="Notify the contractor about the plumbing issue",
            query=RARQuery(
                reference_expression="the contractor",
                candidates=(
                    RARCandidate(
                        id="distractor_prof",
                        title="Prof. V. Sharma (Dean Academics)",
                        candidate_type="person",
                        recency_rank=0,
                        domain_tags=("dean", "faculty"),
                    ),
                    RARCandidate(
                        id="distractor_student",
                        title="Hostel Student Council Rep",
                        candidate_type="person",
                        recency_rank=1,
                        domain_tags=("student", "council"),
                    ),
                    RARCandidate(
                        id="target_contractor",
                        title="Apex Maintenance & Plumbing Contractor",
                        candidate_type="person",
                        recency_rank=2,
                        domain_tags=("contractor", "maintenance", "vendor"),
                    ),
                ),
                local_evidence=RAREvidence(
                    clause_text="Notify the contractor about the plumbing issue",
                    candidate_verbs=("notify",),
                    target_type_hint="person",
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="target_contractor",
            expected_basis=RARBasis.MODEL_SELECTION,
            description="Role/title tag correctly isolates contractor over more recent faculty members.",
        )
    )

    fixtures.append(
        RARFixture(
            id="RAR-FIX-19",
            name="Recording media target amidst minutes and email distractors",
            category="distractors",
            turn_text="Archive the meeting recording",
            query=RARQuery(
                reference_expression="the meeting recording",
                candidates=(
                    RARCandidate(
                        id="distractor_minutes",
                        title="Senate_Meeting_Minutes.docx",
                        candidate_type="document",
                        recency_rank=0,
                        domain_tags=("meeting", "minutes"),
                    ),
                    RARCandidate(
                        id="distractor_email",
                        title="Fwd: Meeting Agenda and Attendees",
                        candidate_type="email",
                        recency_rank=1,
                        domain_tags=("meeting", "agenda"),
                    ),
                    RARCandidate(
                        id="target_recording",
                        title="Senate_Meeting_Recording_21Sep.mp4",
                        candidate_type="media",
                        recency_rank=3,
                        domain_tags=("meeting", "recording", "video"),
                    ),
                ),
                local_evidence=RAREvidence(
                    clause_text="Archive the meeting recording",
                    candidate_verbs=("archive",),
                    target_type_hint="media",
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="target_recording",
            expected_basis=RARBasis.MODEL_SELECTION,
            description="Candidate type 'media' isolates recording from minutes document and agenda email.",
        )
    )

    # =========================================================================
    # Category 7: Multi-Reference Turns (1 turn, 2 independent queries)
    # =========================================================================
    candidates_c7 = (
        RARCandidate(
            id="doc_lab_audit",
            title="Annual_Lab_Safety_Audit.docx",
            candidate_type="document",
            recency_rank=0,
            domain_tags=("audit", "safety", "lab"),
        ),
        RARCandidate(
            id="person_lab_officer",
            title="Dr. B. Das (Lab Safety Officer)",
            candidate_type="person",
            recency_rank=1,
            domain_tags=("safety", "officer"),
        ),
    )

    fixtures.append(
        RARFixture(
            id="RAR-FIX-20A",
            name="Multi-ref mixed types: reference A (that file)",
            category="multi_reference",
            turn_text="Send that file to him",
            query=RARQuery(
                reference_expression="that file",
                candidates=candidates_c7,
                local_evidence=RAREvidence(
                    clause_text="Send that file to him",
                    candidate_verbs=("send",),
                    target_type_hint="document",
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="doc_lab_audit",
            expected_basis=RARBasis.MODEL_SELECTION,
            description="Mixed-type multi-ref: 'that file' binds to document candidate.",
        )
    )

    fixtures.append(
        RARFixture(
            id="RAR-FIX-20B",
            name="Multi-ref mixed types: reference B (him)",
            category="multi_reference",
            turn_text="Send that file to him",
            query=RARQuery(
                reference_expression="him",
                candidates=candidates_c7,
                local_evidence=RAREvidence(
                    clause_text="Send that file to him",
                    candidate_verbs=("send",),
                    target_type_hint="person",
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="person_lab_officer",
            expected_basis=RARBasis.MODEL_SELECTION,
            description="Mixed-type multi-ref: pronoun 'him' binds to person candidate.",
        )
    )

    # =========================================================================
    # Category 8: Deterministic Bypass (Zero Model Invocation) (3 fixtures)
    # =========================================================================
    fixtures.append(
        RARFixture(
            id="RAR-FIX-21",
            name="Explicit object ID pasted in turn text",
            category="deterministic_bypass",
            turn_text="Review doc_audit_984 right away",
            query=RARQuery(
                reference_expression="doc_audit_984",
                candidates=(
                    RARCandidate(
                        id="doc_audit_984",
                        title="Audit_Trail_Q4_Final.pdf",
                        candidate_type="document",
                        recency_rank=0,
                        exact_aliases=("doc_audit_984", "audit-984"),
                    ),
                    RARCandidate(
                        id="doc_notes",
                        title="Random_Scratch_Notes.txt",
                        candidate_type="document",
                        recency_rank=1,
                    ),
                ),
                deterministic_anchor=RARDeterministicAnchor(
                    exact_id="doc_audit_984",
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="doc_audit_984",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Pasted explicit candidate ID short-circuits deterministically without model invocation.",
        )
    )

    fixtures.append(
        RARFixture(
            id="RAR-FIX-22",
            name="Selected UI foreground object",
            category="deterministic_bypass",
            turn_text="Summarize this",
            query=RARQuery(
                reference_expression="this",
                candidates=(
                    RARCandidate(
                        id="doc_active_memo",
                        title="Disciplinary_Committee_Notice.pdf",
                        candidate_type="document",
                        recency_rank=0,
                    ),
                    RARCandidate(
                        id="doc_background",
                        title="Hostel_Fee_Receipt.pdf",
                        candidate_type="document",
                        recency_rank=3,
                    ),
                ),
                deterministic_anchor=RARDeterministicAnchor(
                    selected_ui_id="doc_active_memo",
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="doc_active_memo",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Active foreground UI object resolves directly via deterministic anchor.",
        )
    )

    fixtures.append(
        RARFixture(
            id="RAR-FIX-23",
            name="Current turn attachment reference",
            category="deterministic_bypass",
            turn_text="Convert this attachment to PDF",
            query=RARQuery(
                reference_expression="this attachment",
                candidates=(
                    RARCandidate(
                        id="att_meeting_draft",
                        title="Syndicate_Meeting_Minutes.docx",
                        candidate_type="document",
                        is_attachment=True,
                        recency_rank=0,
                    ),
                    RARCandidate(
                        id="doc_existing_repo",
                        title="Old_Regulations_2020.pdf",
                        candidate_type="document",
                        recency_rank=5,
                    ),
                ),
                deterministic_anchor=RARDeterministicAnchor(
                    current_attachment_id="att_meeting_draft",
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="att_meeting_draft",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Current turn foreground attachment resolves deterministically without model evaluation.",
        )
    )

    return tuple(fixtures)
