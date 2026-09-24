"""Realistic Blind Challenge Dataset for Batch A2.5 Stage 3: Reference Anchor Resolution (RAR).

This module contains 100 realistic, unseen challenge scenarios across authentic URI domains:
- Documents, emails, attachments, office orders, notices, minutes, approvals, applications,
  quotations, reports, drafts, institutional correspondence, and workflows.

Distribution:
- ~70% Normal Realistic References (CHAL-001 to CHAL-070)
- ~20% Naturally Difficult References (CHAL-071 to CHAL-090)
- ~10% Legitimately Unresolvable / Ambiguous (CHAL-091 to CHAL-100)

Dataset Freezing Rule:
Once created and hashed with SHA-256, this dataset is STRICTLY FROZEN.
Neither the fixtures nor the Stage 2 deterministic resolver will be tuned to alter scores.
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


def get_rar_challenge_fixtures() -> Tuple[RARFixture, ...]:
    """Returns the complete frozen tranche of 100 realistic blind RAR qualification fixtures."""
    fixtures: List[RARFixture] = []

    # =========================================================================
    # PART 1: Normal Realistic References (CHAL-001 to CHAL-070)
    # =========================================================================

    # --- Group 1A: Explicit Identifiers & Exact Aliases (8 fixtures) ---
    fixtures.append(
        RARFixture(
            id="CHAL-001",
            name="Pasted office order identifier",
            category="explicit_identifier",
            turn_text="Execute order_2026_881 immediately",
            query=RARQuery(
                reference_expression="order_2026_881",
                candidates=(
                    RARCandidate(id="order_2026_881", title="Office_Order_881_Hostel_Fee.pdf", candidate_type="document"),
                    RARCandidate(id="order_2026_882", title="Office_Order_882_Mess_Tender.pdf", candidate_type="document"),
                ),
                deterministic_anchor=RARDeterministicAnchor(exact_id="order_2026_881"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="order_2026_881",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Direct pasted order ID resolves via exact anchor.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-002",
            name="Support ticket alias reference",
            category="explicit_identifier",
            turn_text="Update ticket-409 with the technician's notes",
            query=RARQuery(
                reference_expression="ticket-409",
                candidates=(
                    RARCandidate(id="tk_server_409", title="Ticket #409: DNS Outage", candidate_type="workflow", exact_aliases=("ticket-409", "tk-409")),
                    RARCandidate(id="tk_ac_410", title="Ticket #410: AC Repair", candidate_type="workflow", exact_aliases=("ticket-410",)),
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="tk_server_409",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Matches candidate exact_alias 'ticket-409'.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-003",
            name="Exact procurement requisition code",
            category="explicit_identifier",
            turn_text="Approve PR-8902 for laboratory chemicals",
            query=RARQuery(
                reference_expression="PR-8902",
                candidates=(
                    RARCandidate(id="pr_8902", title="Requisition #8902: Chemistry Reagents", candidate_type="document", exact_aliases=("PR-8902", "req-8902")),
                    RARCandidate(id="pr_8905", title="Requisition #8905: Glassware", candidate_type="document", exact_aliases=("PR-8905",)),
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="pr_8902",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Exact code match against candidate aliases.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-004",
            name="Pasted email message identifier in thread",
            category="explicit_identifier",
            turn_text="View msg_thread_772a",
            query=RARQuery(
                reference_expression="msg_thread_772a",
                candidates=(
                    RARCandidate(id="msg_thread_772a", title="Re: Syndicate Committee Date", candidate_type="email"),
                    RARCandidate(id="msg_thread_772b", title="Re: Convocation Robes", candidate_type="email"),
                ),
                deterministic_anchor=RARDeterministicAnchor(exact_id="msg_thread_772a"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="msg_thread_772a",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Anchor exact_id binds directly to message candidate.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-005",
            name="Workflow process instance key",
            category="explicit_identifier",
            turn_text="Resume proc_onboard_v2",
            query=RARQuery(
                reference_expression="proc_onboard_v2",
                candidates=(
                    RARCandidate(id="proc_onboard_v2", title="Faculty Onboarding Pipeline v2", candidate_type="workflow"),
                    RARCandidate(id="proc_clearance_v1", title="Student No-Dues Clearance", candidate_type="workflow"),
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="proc_onboard_v2",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Verbatim ID equality match on candidate ID.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-006",
            name="Equipment asset tag reference",
            category="explicit_identifier",
            turn_text="Check maintenance log for AST-8831",
            query=RARQuery(
                reference_expression="AST-8831",
                candidates=(
                    RARCandidate(id="asset_spectrometer", title="UV-Vis Spectrometer Model 40", candidate_type="document", exact_aliases=("AST-8831", "asset-8831")),
                    RARCandidate(id="asset_centrifuge", title="High Speed Centrifuge", candidate_type="document", exact_aliases=("AST-8832",)),
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="asset_spectrometer",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Asset tag resolves via candidate alias.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-007",
            name="Invoice voucher number match",
            category="explicit_identifier",
            turn_text="Forward VCH-2026-901 to accounts section",
            query=RARQuery(
                reference_expression="VCH-2026-901",
                candidates=(
                    RARCandidate(id="inv_vch_901", title="Payment Voucher #901: Library Books", candidate_type="document", exact_aliases=("VCH-2026-901", "vch-901")),
                    RARCandidate(id="inv_vch_902", title="Payment Voucher #902: Sports Kits", candidate_type="document", exact_aliases=("VCH-2026-902",)),
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="inv_vch_901",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Voucher code matches exact alias.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-008",
            name="Explicit student roll number alias",
            category="explicit_identifier",
            turn_text="Send the marks sheet to 2026CS104",
            query=RARQuery(
                reference_expression="2026CS104",
                candidates=(
                    RARCandidate(id="person_student_vikram", title="Vikramaditya Rao", candidate_type="person", exact_aliases=("2026CS104", "vikram-rao")),
                    RARCandidate(id="person_student_rohit", title="Rohit Mehra", candidate_type="person", exact_aliases=("2026CS105",)),
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="person_student_vikram",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Roll number matches candidate exact alias.",
        )
    )

    # --- Group 1B: Verbatim Titles & Filenames (10 fixtures) ---
    fixtures.append(
        RARFixture(
            id="CHAL-009",
            name="Verbatim PDF filename match with extension",
            category="verbatim_title",
            turn_text="Open Hostel_Allotment_List_Final.pdf",
            query=RARQuery(
                reference_expression="Hostel_Allotment_List_Final.pdf",
                candidates=(
                    RARCandidate(id="doc_hostel_allotment", title="Hostel_Allotment_List_Final.pdf", candidate_type="document"),
                    RARCandidate(id="doc_mess_rebate", title="Mess_Rebate_Notice.pdf", candidate_type="document"),
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="doc_hostel_allotment",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Exact verbatim title match.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-010",
            name="Title match with normalized whitespace and missing extension",
            category="verbatim_title",
            turn_text="View Annual Quality Assurance Report 2026",
            query=RARQuery(
                reference_expression="Annual Quality Assurance Report 2026",
                candidates=(
                    RARCandidate(id="doc_aqar_2026", title="Annual_Quality_Assurance_Report_2026.docx", candidate_type="document"),
                    RARCandidate(id="doc_naac_notes", title="NAAC_Review_Notes.docx", candidate_type="document"),
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="doc_aqar_2026",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Stem normalization resolves docx file without extension.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-011",
            name="Exact title stem for course syllabus",
            category="verbatim_title",
            turn_text="Print Advanced Machine Learning Syllabus",
            query=RARQuery(
                reference_expression="Advanced Machine Learning Syllabus",
                candidates=(
                    RARCandidate(id="syl_aml", title="Advanced_Machine_Learning_Syllabus.pdf", candidate_type="document"),
                    RARCandidate(id="syl_dbms", title="Database_Systems_Syllabus.pdf", candidate_type="document"),
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="syl_aml",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Exact stem match for course syllabus document.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-012",
            name="Verbatim tender notification document title",
            category="verbatim_title",
            turn_text="Download Tender_Notice_Catering_2026.pdf",
            query=RARQuery(
                reference_expression="Tender_Notice_Catering_2026.pdf",
                candidates=(
                    RARCandidate(id="doc_tender_cat", title="Tender_Notice_Catering_2026.pdf", candidate_type="document"),
                    RARCandidate(id="doc_tender_sec", title="Tender_Notice_Security_2026.pdf", candidate_type="document"),
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="doc_tender_cat",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Exact filename match distinguishes catering tender from security tender.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-013",
            name="Verbatim committee minutes title",
            category="verbatim_title",
            turn_text="Read Senate Minutes 48th Meeting",
            query=RARQuery(
                reference_expression="Senate Minutes 48th Meeting",
                candidates=(
                    RARCandidate(id="min_senate_48", title="Senate_Minutes_48th_Meeting.pdf", candidate_type="document"),
                    RARCandidate(id="min_senate_47", title="Senate_Minutes_47th_Meeting.pdf", candidate_type="document"),
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="min_senate_48",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Exact stem matching distinguishes meeting numbers.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-014",
            name="Exact research grant agreement title",
            category="verbatim_title",
            turn_text="Review DST_SERB_Grant_Sanction_Letter.pdf",
            query=RARQuery(
                reference_expression="DST_SERB_Grant_Sanction_Letter.pdf",
                candidates=(
                    RARCandidate(id="doc_serb_grant", title="DST_SERB_Grant_Sanction_Letter.pdf", candidate_type="document"),
                    RARCandidate(id="doc_mhrd_grant", title="MHRD_Grant_Sanction_Letter.pdf", candidate_type="document"),
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="doc_serb_grant",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Exact filename match for sponsored grant document.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-015",
            name="Verbatim conference schedule title without extension",
            category="verbatim_title",
            turn_text="Display International Conference Technical Schedule",
            query=RARQuery(
                reference_expression="International Conference Technical Schedule",
                candidates=(
                    RARCandidate(id="sched_conf", title="International_Conference_Technical_Schedule.xlsx", candidate_type="spreadsheet"),
                    RARCandidate(id="flyer_conf", title="Conference_Flyer_Poster.pdf", candidate_type="document"),
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="sched_conf",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Stem match on spreadsheet title.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-016",
            name="Verbatim medical reimbursement claim filename",
            category="verbatim_title",
            turn_text="Submit Medical_Claim_Form_Faculty.docx",
            query=RARQuery(
                reference_expression="Medical_Claim_Form_Faculty.docx",
                candidates=(
                    RARCandidate(id="claim_faculty", title="Medical_Claim_Form_Faculty.docx", candidate_type="document"),
                    RARCandidate(id="claim_staff", title="Medical_Claim_Form_Staff.docx", candidate_type="document"),
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="claim_faculty",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Verbatim filename isolates faculty medical claim.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-017",
            name="Verbatim leave application title",
            category="verbatim_title",
            turn_text="Open Casual Leave Application Form",
            query=RARQuery(
                reference_expression="Casual Leave Application Form",
                candidates=(
                    RARCandidate(id="form_cl", title="Casual_Leave_Application_Form.pdf", candidate_type="document"),
                    RARCandidate(id="form_el", title="Earned_Leave_Application_Form.pdf", candidate_type="document"),
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="form_cl",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Stem title match isolates casual leave from earned leave.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-018",
            name="Verbatim laboratory safety guideline filename",
            category="verbatim_title",
            turn_text="Share Chemistry_Lab_Safety_Rules.pdf with the batch",
            query=RARQuery(
                reference_expression="Chemistry_Lab_Safety_Rules.pdf",
                candidates=(
                    RARCandidate(id="doc_chem_safety", title="Chemistry_Lab_Safety_Rules.pdf", candidate_type="document"),
                    RARCandidate(id="doc_physics_safety", title="Physics_Lab_Safety_Rules.pdf", candidate_type="document"),
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="doc_chem_safety",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Verbatim filename resolves chemistry rules over physics rules.",
        )
    )

    # --- Group 1C: Active Turn Context & Attachments (10 fixtures) ---
    fixtures.append(
        RARFixture(
            id="CHAL-019",
            name="Active attachment in current turn with deictic expression",
            category="active_context",
            turn_text="Convert this attachment to text",
            query=RARQuery(
                reference_expression="this attachment",
                candidates=(
                    RARCandidate(id="att_uploaded_memo", title="Memo_Scanned.pdf", candidate_type="document", is_attachment=True),
                    RARCandidate(id="doc_history", title="Old_Circular.pdf", candidate_type="document"),
                ),
                deterministic_anchor=RARDeterministicAnchor(current_attachment_id="att_uploaded_memo"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="att_uploaded_memo",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Current turn foreground attachment resolves via deterministic anchor.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-020",
            name="Selected UI card in active view",
            category="active_context",
            turn_text="Summarize the selected item",
            query=RARQuery(
                reference_expression="the selected item",
                candidates=(
                    RARCandidate(id="ui_selected_invoice", title="Vendor_Invoice_984.pdf", candidate_type="document"),
                    RARCandidate(id="ui_unselected_draft", title="Draft_Reply.docx", candidate_type="document"),
                ),
                deterministic_anchor=RARDeterministicAnchor(selected_ui_id="ui_selected_invoice"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="ui_selected_invoice",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Selected UI anchor binds directly to foreground invoice.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-021",
            name="Single attached document in turn",
            category="active_context",
            turn_text="Extract the table from the attached file",
            query=RARQuery(
                reference_expression="the attached file",
                candidates=(
                    RARCandidate(id="att_fee_structure", title="Revised_Fee_Structure.xlsx", candidate_type="spreadsheet", is_attachment=True),
                    RARCandidate(id="doc_archived", title="Fee_Structure_2020.pdf", candidate_type="document"),
                ),
                deterministic_anchor=RARDeterministicAnchor(current_attachment_id="att_fee_structure"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="att_fee_structure",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Attachment reference anchors to current turn attachment handle.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-022",
            name="Bare deictic 'this' over active UI selection",
            category="active_context",
            turn_text="Send this to the registrar",
            query=RARQuery(
                reference_expression="this",
                candidates=(
                    RARCandidate(id="doc_noting_active", title="Noting_Sheet_PhD_Admission.docx", candidate_type="document"),
                    RARCandidate(id="doc_noting_old", title="Noting_Sheet_Old.docx", candidate_type="document"),
                ),
                deterministic_anchor=RARDeterministicAnchor(selected_ui_id="doc_noting_active"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="doc_noting_active",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Deictic pronoun 'this' resolves via selected UI anchor.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-023",
            name="Recently discussed document continuation",
            category="active_context",
            turn_text="Send the same document to the warden",
            query=RARQuery(
                reference_expression="the same document",
                candidates=(
                    RARCandidate(id="doc_hostel_rules", title="Hostel_Disciplinary_Rules.pdf", candidate_type="document", recency_rank=0, domain_tags=("recently_discussed",)),
                    RARCandidate(id="doc_library_rules", title="Library_Fine_Rules.pdf", candidate_type="document", recency_rank=4),
                ),
                local_evidence=RAREvidence(recency_hint="same", target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="doc_hostel_rules",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Continuation reference 'the same document' anchors to recently discussed candidate.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-024",
            name="Active email thread reply follow-up",
            category="active_context",
            turn_text="Prepare a reply to that email",
            query=RARQuery(
                reference_expression="that email",
                candidates=(
                    RARCandidate(id="email_dean_convocation", title="Fwd: Convocation Rehearsal Schedule", candidate_type="email", recency_rank=0),
                    RARCandidate(id="doc_notes", title="Rehearsal_Notes.txt", candidate_type="document", recency_rank=1),
                ),
                local_evidence=RAREvidence(recency_hint="latest", target_type_hint="email"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="email_dean_convocation",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Type filter and recency rank isolate active thread email.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-025",
            name="Current attachment referenced as 'this PDF'",
            category="active_context",
            turn_text="Please sign this PDF",
            query=RARQuery(
                reference_expression="this PDF",
                candidates=(
                    RARCandidate(id="att_reimbursement", title="TA_DA_Claim_Signed.pdf", candidate_type="document", is_attachment=True),
                    RARCandidate(id="doc_travel_rules", title="TA_DA_Rules_Govt.pdf", candidate_type="document"),
                ),
                deterministic_anchor=RARDeterministicAnchor(current_attachment_id="att_reimbursement"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="att_reimbursement",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Foreground attachment handle resolves directly.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-026",
            name="Active workflow waiting for approval",
            category="active_context",
            turn_text="Approve the active workflow",
            query=RARQuery(
                reference_expression="the active workflow",
                candidates=(
                    RARCandidate(id="wf_mtech_admission", title="MTech Admission Verification Flow", candidate_type="workflow", recency_rank=0),
                    RARCandidate(id="doc_handbook", title="Student_Handbook.pdf", candidate_type="document", recency_rank=3),
                ),
                local_evidence=RAREvidence(target_type_hint="workflow"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="wf_mtech_admission",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Type constraint filters single active workflow.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-027",
            name="Selected person entity in directory card",
            category="active_context",
            turn_text="Send an email to him",
            query=RARQuery(
                reference_expression="him",
                candidates=(
                    RARCandidate(id="person_prof_gupta", title="Prof. R. K. Gupta", candidate_type="person"),
                    RARCandidate(id="doc_memo", title="Leave_Memo.pdf", candidate_type="document"),
                ),
                deterministic_anchor=RARDeterministicAnchor(selected_ui_id="person_prof_gupta"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="person_prof_gupta",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Deictic pronoun 'him' over selected person UI anchor.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-028",
            name="Anchor unique title match for institutional order",
            category="active_context",
            turn_text="Circulate the order",
            query=RARQuery(
                reference_expression="the order",
                candidates=(
                    RARCandidate(id="order_holiday", title="Holiday_Notification_Diwali.pdf", candidate_type="document"),
                    RARCandidate(id="email_newsletter", title="Campus Weekly Newsletter", candidate_type="email"),
                ),
                deterministic_anchor=RARDeterministicAnchor(unique_title_match="order_holiday"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="order_holiday",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Deterministic anchor unique title match.",
        )
    )

    # --- Group 1D: Type-Constrained References (12 fixtures) ---
    fixtures.append(
        RARFixture(
            id="CHAL-029",
            name="Isolate email amidst PDF manuals and spreadsheets",
            category="type_constrained",
            turn_text="Forward the email to the head of department",
            query=RARQuery(
                reference_expression="the email",
                candidates=(
                    RARCandidate(id="doc_lab_guide", title="Lab_Safety_Guidelines.pdf", candidate_type="document"),
                    RARCandidate(id="sheet_attendance", title="Student_Attendance_Sep26.xlsx", candidate_type="spreadsheet"),
                    RARCandidate(id="email_hod_invite", title="Fwd: Board of Studies Meeting", candidate_type="email"),
                ),
                local_evidence=RAREvidence(target_type_hint="email"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="email_hod_invite",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Target type hint 'email' isolates email from document and spreadsheet.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-030",
            name="Isolate spreadsheet amidst documents and workflows",
            category="type_constrained",
            turn_text="Update the budget spreadsheet",
            query=RARQuery(
                reference_expression="the budget spreadsheet",
                candidates=(
                    RARCandidate(id="doc_policy", title="Hostel_Rules.docx", candidate_type="document"),
                    RARCandidate(id="sheet_budget", title="Annual_Department_Budget_2026.xlsx", candidate_type="spreadsheet", domain_tags=("budget", "finance")),
                    RARCandidate(id="wf_leave", title="Staff Leave Application Flow", candidate_type="workflow"),
                ),
                local_evidence=RAREvidence(target_type_hint="spreadsheet"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="sheet_budget",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Spreadsheet type hint isolates budget sheet.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-031",
            name="Isolate workflow amidst email and text notes",
            category="type_constrained",
            turn_text="Trigger the clearance workflow",
            query=RARQuery(
                reference_expression="the clearance workflow",
                candidates=(
                    RARCandidate(id="wf_clearance", title="Student No-Dues Clearance Workflow", candidate_type="workflow"),
                    RARCandidate(id="email_reminder", title="Reminder: Submit Dues", candidate_type="email"),
                    RARCandidate(id="doc_dues_list", title="Dues_Defaulters_List.txt", candidate_type="document"),
                ),
                local_evidence=RAREvidence(target_type_hint="workflow"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="wf_clearance",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Workflow type hint isolates workflow candidate.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-032",
            name="Isolate media video recording amidst agendas and minutes",
            category="type_constrained",
            turn_text="Download the meeting recording",
            query=RARQuery(
                reference_expression="the meeting recording",
                candidates=(
                    RARCandidate(id="min_bogs", title="Board_Of_Governors_Minutes.docx", candidate_type="document"),
                    RARCandidate(id="agenda_bogs", title="Fwd: BOG 34th Meeting Agenda", candidate_type="email"),
                    RARCandidate(id="rec_bogs", title="BOG_Meeting_34_Recording.mp4", candidate_type="media"),
                ),
                local_evidence=RAREvidence(target_type_hint="media"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="rec_bogs",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Media candidate type isolates video recording.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-033",
            name="Isolate person entity amidst committee files",
            category="type_constrained",
            turn_text="Notify the warden about the water outage",
            query=RARQuery(
                reference_expression="the warden",
                candidates=(
                    RARCandidate(id="person_warden_sen", title="Prof. S. Sen (Chief Warden)", candidate_type="person", domain_tags=("warden", "hostel")),
                    RARCandidate(id="doc_water_tender", title="Plumbing_Maintenance_Report.pdf", candidate_type="document"),
                    RARCandidate(id="email_hostel_notice", title="Water Supply Disruption Notice", candidate_type="email"),
                ),
                local_evidence=RAREvidence(target_type_hint="person"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="person_warden_sen",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Person type hint isolates warden entity.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-034",
            name="Isolate office order document amidst emails and spreadsheets",
            category="type_constrained",
            turn_text="Circulate the office order to all departments",
            query=RARQuery(
                reference_expression="the office order",
                candidates=(
                    RARCandidate(id="doc_office_order", title="Office_Order_Winter_Vacation_2026.pdf", candidate_type="document", domain_tags=("order", "vacation")),
                    RARCandidate(id="email_holiday_inquiry", title="Inquiry regarding winter break", candidate_type="email"),
                    RARCandidate(id="sheet_duty_roster", title="Winter_Break_Essential_Duty_Roster.xlsx", candidate_type="spreadsheet"),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="doc_office_order",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Document type hint and 'order' tag match office order.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-035",
            name="Isolate invoice document amidst correspondence",
            category="type_constrained",
            turn_text="Forward the invoice to internal audit",
            query=RARQuery(
                reference_expression="the invoice",
                candidates=(
                    RARCandidate(id="doc_invoice_printer", title="Invoice_HP_LaserJet_Printers.pdf", candidate_type="document", domain_tags=("invoice", "billing")),
                    RARCandidate(id="email_quote_vendor", title="Price Quotation for Printers", candidate_type="email"),
                    RARCandidate(id="wf_vendor_approval", title="Vendor Payment Approval Pipeline", candidate_type="workflow"),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="doc_invoice_printer",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Type filter and domain tag isolate invoice document.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-036",
            name="Isolate application document amidst notices",
            category="type_constrained",
            turn_text="Review the student's scholarship application",
            query=RARQuery(
                reference_expression="the scholarship application",
                candidates=(
                    RARCandidate(id="app_scholarship_ananya", title="Scholarship_Application_Ananya.pdf", candidate_type="document", domain_tags=("scholarship", "application")),
                    RARCandidate(id="notice_merit", title="Merit_Scholarship_Notice_2026.pdf", candidate_type="document", domain_tags=("scholarship", "notice")),
                    RARCandidate(id="email_donor", title="Endowment Fund Allocation", candidate_type="email"),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="app_scholarship_ananya",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Term discrimination on 'application' isolates candidate from notice.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-037",
            name="Isolate quotation document from supplier email",
            category="type_constrained",
            turn_text="Review the equipment quotation",
            query=RARQuery(
                reference_expression="the equipment quotation",
                candidates=(
                    RARCandidate(id="doc_quote_centrifuge", title="Quotation_Benchtop_Centrifuge_ColeParmer.pdf", candidate_type="document", domain_tags=("quotation", "equipment")),
                    RARCandidate(id="email_vendor_dispatch", title="Dispatch Status for Centrifuge", candidate_type="email"),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="doc_quote_centrifuge",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Type filter isolates quotation document from vendor email.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-038",
            name="Isolate fee receipt document amidst guidelines",
            category="type_constrained",
            turn_text="Attach the fee receipt to the form",
            query=RARQuery(
                reference_expression="the fee receipt",
                candidates=(
                    RARCandidate(id="doc_receipt_semester", title="Semester_Fee_Receipt_Autumn26.pdf", candidate_type="document", domain_tags=("fee", "receipt")),
                    RARCandidate(id="doc_fee_structure", title="Annual_Fee_Structure_Rules.pdf", candidate_type="document", domain_tags=("fee", "rules")),
                    RARCandidate(id="email_fee_portal", title="Payment Gateway Maintenance", candidate_type="email"),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="doc_receipt_semester",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Term discrimination on 'receipt' isolates receipt from fee structure rules.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-039",
            name="Isolate presentation slides amidst project report and emails",
            category="type_constrained",
            turn_text="Open the presentation slides",
            query=RARQuery(
                reference_expression="the presentation slides",
                candidates=(
                    RARCandidate(id="doc_thesis_report", title="Final_Year_Thesis_Report.pdf", candidate_type="document"),
                    RARCandidate(id="pres_thesis_slides", title="Thesis_Defense_Presentation.pdf", candidate_type="document", domain_tags=("presentation", "slides")),
                    RARCandidate(id="email_panel", title="External Examiner Schedule", candidate_type="email"),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="pres_thesis_slides",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Term discrimination on 'presentation' and 'slides' isolates defense slides.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-040",
            name="Isolate contract agreement document amidst correspondence",
            category="type_constrained",
            turn_text="Send the contract agreement to legal counsel",
            query=RARQuery(
                reference_expression="the contract agreement",
                candidates=(
                    RARCandidate(id="doc_canteen_contract", title="Campus_Canteen_License_Agreement.pdf", candidate_type="document", domain_tags=("contract", "agreement", "canteen")),
                    RARCandidate(id="email_canteen_review", title="Canteen Committee Review Meeting", candidate_type="email"),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="doc_canteen_contract",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Document type filter isolates contract from review email.",
        )
    )

    # --- Group 1E: Straightforward Temporal & Recency References (10 fixtures) ---
    fixtures.append(
        RARFixture(
            id="CHAL-041",
            name="Previous email in multi-message thread",
            category="temporal_reference",
            turn_text="Reply to the previous email",
            query=RARQuery(
                reference_expression="the previous email",
                candidates=(
                    RARCandidate(id="msg_latest", title="Re: Lab Equipment Delivery Confirmed", candidate_type="email", recency_rank=0),
                    RARCandidate(id="msg_previous", title="Re: Lab Equipment Delivery Inquiry", candidate_type="email", recency_rank=1),
                    RARCandidate(id="msg_original", title="Purchase Order Lab Equipment", candidate_type="email", recency_rank=2),
                ),
                local_evidence=RAREvidence(recency_hint="previous", target_type_hint="email"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="msg_previous",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'previous email' binds to recency_rank 1 candidate.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-042",
            name="Earlier draft of hostel allotment rules",
            category="temporal_reference",
            turn_text="Compare against the earlier draft",
            query=RARQuery(
                reference_expression="the earlier draft",
                candidates=(
                    RARCandidate(id="draft_current", title="Hostel_Allotment_Rules_v3.docx", candidate_type="document", recency_rank=0),
                    RARCandidate(id="draft_earlier", title="Hostel_Allotment_Rules_v1.docx", candidate_type="document", recency_rank=2),
                ),
                local_evidence=RAREvidence(recency_hint="earlier", target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="draft_earlier",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'earlier draft' resolves to recency_rank > 0 candidate.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-043",
            name="Latest committee circular",
            category="temporal_reference",
            turn_text="Display the latest circular",
            query=RARQuery(
                reference_expression="the latest circular",
                candidates=(
                    RARCandidate(id="circ_oct", title="Circular_Mess_Charges_Oct26.pdf", candidate_type="document", recency_rank=0, domain_tags=("circular",)),
                    RARCandidate(id="circ_sep", title="Circular_Mess_Charges_Sep26.pdf", candidate_type="document", recency_rank=1, domain_tags=("circular",)),
                ),
                local_evidence=RAREvidence(recency_hint="latest", target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="circ_oct",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'latest circular' anchors to recency_rank 0.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-044",
            name="Previous version of conference agenda",
            category="temporal_reference",
            turn_text="Restore the previous version",
            query=RARQuery(
                reference_expression="the previous version",
                candidates=(
                    RARCandidate(id="agenda_v2", title="Conference_Agenda_v2.docx", candidate_type="document", recency_rank=0),
                    RARCandidate(id="agenda_v1", title="Conference_Agenda_v1.docx", candidate_type="document", recency_rank=1),
                ),
                local_evidence=RAREvidence(recency_hint="previous", target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="agenda_v1",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'previous version' maps to recency_rank 1.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-045",
            name="Earlier message from accounts section",
            category="temporal_reference",
            turn_text="Check the earlier email from accounts",
            query=RARQuery(
                reference_expression="the earlier email",
                candidates=(
                    RARCandidate(id="mail_acc_now", title="Re: Salary Disbursal Oct", candidate_type="email", recency_rank=0),
                    RARCandidate(id="mail_acc_before", title="Salary Disbursal Schedule Notice", candidate_type="email", recency_rank=2),
                ),
                local_evidence=RAREvidence(recency_hint="earlier", target_type_hint="email"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="mail_acc_before",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'earlier email' selects older candidate in thread.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-046",
            name="Most recent audit report in archive",
            category="temporal_reference",
            turn_text="Summarize the latest audit report",
            query=RARQuery(
                reference_expression="the latest audit report",
                candidates=(
                    RARCandidate(id="audit_2026", title="Internal_Audit_Report_2026.pdf", candidate_type="document", recency_rank=0, domain_tags=("audit", "report")),
                    RARCandidate(id="audit_2025", title="Internal_Audit_Report_2025.pdf", candidate_type="document", recency_rank=3, domain_tags=("audit", "report")),
                ),
                local_evidence=RAREvidence(recency_hint="latest", target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="audit_2026",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'latest audit report' selects candidate with recency_rank 0.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-047",
            name="Previous meeting minutes in academic council thread",
            category="temporal_reference",
            turn_text="Forward the previous minutes to the registrar",
            query=RARQuery(
                reference_expression="the previous minutes",
                candidates=(
                    RARCandidate(id="min_ac_50", title="Academic_Council_Minutes_Meeting_50.pdf", candidate_type="document", recency_rank=0),
                    RARCandidate(id="min_ac_49", title="Academic_Council_Minutes_Meeting_49.pdf", candidate_type="document", recency_rank=1),
                ),
                local_evidence=RAREvidence(recency_hint="previous", target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="min_ac_49",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'previous minutes' targets recency_rank 1 candidate.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-048",
            name="Earlier draft of faculty recruitment advertisement",
            category="temporal_reference",
            turn_text="Restore the earlier draft of the advertisement",
            query=RARQuery(
                reference_expression="the earlier draft",
                candidates=(
                    RARCandidate(id="ad_faculty_v2", title="Faculty_Recruitment_Ad_v2.docx", candidate_type="document", recency_rank=0),
                    RARCandidate(id="ad_faculty_v1", title="Faculty_Recruitment_Ad_v1.docx", candidate_type="document", recency_rank=3),
                ),
                local_evidence=RAREvidence(recency_hint="earlier", target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="ad_faculty_v1",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'earlier draft' targets older candidate in recency order.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-049",
            name="The previous order issued by the director",
            category="temporal_reference",
            turn_text="Review the previous office order",
            query=RARQuery(
                reference_expression="the previous office order",
                candidates=(
                    RARCandidate(id="ord_dir_302", title="Director_Order_302.pdf", candidate_type="document", recency_rank=0),
                    RARCandidate(id="ord_dir_301", title="Director_Order_301.pdf", candidate_type="document", recency_rank=1),
                ),
                local_evidence=RAREvidence(recency_hint="previous", target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="ord_dir_301",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'previous office order' selects rank 1 order.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-050",
            name="Earlier quotation submitted by vendor",
            category="temporal_reference",
            turn_text="Compare this price with the earlier quotation",
            query=RARQuery(
                reference_expression="the earlier quotation",
                candidates=(
                    RARCandidate(id="quote_oct", title="Lab_Chemicals_Quotation_Oct.pdf", candidate_type="document", recency_rank=0),
                    RARCandidate(id="quote_jul", title="Lab_Chemicals_Quotation_Jul.pdf", candidate_type="document", recency_rank=2),
                ),
                local_evidence=RAREvidence(recency_hint="earlier", target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="quote_jul",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'earlier quotation' targets older quotation.",
        )
    )

    # --- Group 1F: Revision & Version Relations (10 fixtures) ---
    fixtures.append(
        RARFixture(
            id="CHAL-051",
            name="Revised office order vs original draft",
            category="revision_relation",
            turn_text="Send the revised office order to accounts",
            query=RARQuery(
                reference_expression="the revised office order",
                candidates=(
                    RARCandidate(id="order_orig", title="Office_Order_Mess_Rebate_Orig.pdf", candidate_type="document", domain_tags=("order", "original")),
                    RARCandidate(id="order_rev", title="Office_Order_Mess_Rebate_Revised.pdf", candidate_type="document", domain_tags=("order", "revised")),
                ),
                local_evidence=RAREvidence(recency_hint="revised", target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="order_rev",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'revised office order' selects candidate with 'revised' tag.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-052",
            name="Revised budget spreadsheet vs preliminary budget",
            category="revision_relation",
            turn_text="Open the revised budget",
            query=RARQuery(
                reference_expression="the revised budget",
                candidates=(
                    RARCandidate(id="sheet_prelim", title="Preliminary_Budget_2026.xlsx", candidate_type="spreadsheet", domain_tags=("budget", "draft")),
                    RARCandidate(id="sheet_revised", title="Revised_Budget_Estimate_2026.xlsx", candidate_type="spreadsheet", domain_tags=("budget", "revised")),
                ),
                local_evidence=RAREvidence(recency_hint="revised", target_type_hint="spreadsheet"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="sheet_revised",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'revised budget' binds to spreadsheet with 'revised' tag and stem.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-053",
            name="Revised curriculum syllabus document",
            category="revision_relation",
            turn_text="Upload the revised syllabus to the portal",
            query=RARQuery(
                reference_expression="the revised syllabus",
                candidates=(
                    RARCandidate(id="syl_v1", title="BTech_CSE_Curriculum_2026_v1.pdf", candidate_type="document", domain_tags=("curriculum", "original")),
                    RARCandidate(id="syl_v2", title="BTech_CSE_Curriculum_2026_revised.pdf", candidate_type="document", domain_tags=("curriculum", "revised")),
                ),
                local_evidence=RAREvidence(recency_hint="revised", target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="syl_v2",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'revised syllabus' selects candidate with 'revised' domain tag.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-054",
            name="Revised tender document vs draft tender",
            category="revision_relation",
            turn_text="Publish the revised tender notice",
            query=RARQuery(
                reference_expression="the revised tender notice",
                candidates=(
                    RARCandidate(id="tnd_draft", title="Catering_Tender_Draft.pdf", candidate_type="document", domain_tags=("tender", "draft")),
                    RARCandidate(id="tnd_revised", title="Catering_Tender_Notice_Revised.pdf", candidate_type="document", domain_tags=("tender", "revised")),
                ),
                local_evidence=RAREvidence(recency_hint="revised", target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="tnd_revised",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'revised tender' binds to candidate with 'revised' tag.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-055",
            name="Revised MoU agreement draft",
            category="revision_relation",
            turn_text="Forward the revised MoU to the industry partner",
            query=RARQuery(
                reference_expression="the revised MoU",
                candidates=(
                    RARCandidate(id="mou_v1", title="Industry_Collaboration_MoU_Initial.docx", candidate_type="document", domain_tags=("mou", "initial")),
                    RARCandidate(id="mou_v2", title="Industry_Collaboration_MoU_revised.docx", candidate_type="document", domain_tags=("mou", "revised")),
                ),
                local_evidence=RAREvidence(recency_hint="revised", target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="mou_v2",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'revised MoU' resolves to revised version candidate.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-056",
            name="Revised fee structure circular",
            category="revision_relation",
            turn_text="Display the revised fee circular",
            query=RARQuery(
                reference_expression="the revised fee circular",
                candidates=(
                    RARCandidate(id="circ_fee_old", title="Hostel_Fee_Structure_Original.pdf", candidate_type="document", domain_tags=("fee", "original")),
                    RARCandidate(id="circ_fee_new", title="Hostel_Fee_Structure_Revised.pdf", candidate_type="document", domain_tags=("fee", "revised")),
                ),
                local_evidence=RAREvidence(recency_hint="revised", target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="circ_fee_new",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'revised fee circular' selects revised candidate.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-057",
            name="Revised project proposal document",
            category="revision_relation",
            turn_text="Submit the revised proposal to DST",
            query=RARQuery(
                reference_expression="the revised proposal",
                candidates=(
                    RARCandidate(id="prop_draft", title="DST_AI_Healthcare_Proposal_Draft.docx", candidate_type="document", domain_tags=("proposal", "draft")),
                    RARCandidate(id="prop_revised", title="DST_AI_Healthcare_Proposal_revised.docx", candidate_type="document", domain_tags=("proposal", "revised")),
                ),
                local_evidence=RAREvidence(recency_hint="revised", target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="prop_revised",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'revised proposal' resolves to candidate with 'revised' tag.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-058",
            name="Revised exam timetable spreadsheet",
            category="revision_relation",
            turn_text="Print the revised timetable",
            query=RARQuery(
                reference_expression="the revised timetable",
                candidates=(
                    RARCandidate(id="time_draft", title="Midsem_Timetable_Draft.xlsx", candidate_type="spreadsheet", domain_tags=("timetable", "draft")),
                    RARCandidate(id="time_revised", title="Midsem_Timetable_Revised.xlsx", candidate_type="spreadsheet", domain_tags=("timetable", "revised")),
                ),
                local_evidence=RAREvidence(recency_hint="revised", target_type_hint="spreadsheet"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="time_revised",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'revised timetable' selects revised spreadsheet candidate.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-059",
            name="Revised hostel allotment list",
            category="revision_relation",
            turn_text="Notify students about the revised allotment list",
            query=RARQuery(
                reference_expression="the revised allotment list",
                candidates=(
                    RARCandidate(id="list_initial", title="Hostel_Allotment_Round1.pdf", candidate_type="document", domain_tags=("allotment", "initial")),
                    RARCandidate(id="list_revised", title="Hostel_Allotment_Round1_Revised.pdf", candidate_type="document", domain_tags=("allotment", "revised")),
                ),
                local_evidence=RAREvidence(recency_hint="revised", target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="list_revised",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'revised allotment list' selects revised version.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-060",
            name="Revised purchase requisition",
            category="revision_relation",
            turn_text="Send the revised requisition to procurement",
            query=RARQuery(
                reference_expression="the revised requisition",
                candidates=(
                    RARCandidate(id="req_orig", title="Spectrometer_Purchase_Requisition_v1.pdf", candidate_type="document", domain_tags=("requisition", "original")),
                    RARCandidate(id="req_rev", title="Spectrometer_Purchase_Requisition_revised.pdf", candidate_type="document", domain_tags=("requisition", "revised")),
                ),
                local_evidence=RAREvidence(recency_hint="revised", target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="req_rev",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'revised requisition' binds to revised candidate.",
        )
    )

    # --- Group 1G: Straightforward Institutional Terminology Discrimination (10 fixtures) ---
    fixtures.append(
        RARFixture(
            id="CHAL-061",
            name="Hostel policy document vs library rules",
            category="institutional_discrimination",
            turn_text="Send that hostel policy to the prefect",
            query=RARQuery(
                reference_expression="that hostel policy",
                candidates=(
                    RARCandidate(id="doc_hostel_pol", title="Hostel_Conduct_Policy_2026.docx", candidate_type="document", domain_tags=("hostel", "policy")),
                    RARCandidate(id="doc_lib_pol", title="Library_Borrowing_Rules.docx", candidate_type="document", domain_tags=("library", "rules")),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="doc_hostel_pol",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'hostel policy' matches title and tags uniquely.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-062",
            name="Sports tender vs catering tender",
            category="institutional_discrimination",
            turn_text="Review the sports equipment tender",
            query=RARQuery(
                reference_expression="the sports equipment tender",
                candidates=(
                    RARCandidate(id="tender_sports", title="Tender_Sports_Equipment_2026.pdf", candidate_type="document", domain_tags=("sports", "equipment", "tender")),
                    RARCandidate(id="tender_catering", title="Tender_Hostel_Catering_2026.pdf", candidate_type="document", domain_tags=("hostel", "catering", "tender")),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="tender_sports",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'sports equipment' uniquely discriminates sports tender.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-063",
            name="Convocation circular vs semester registration notice",
            category="institutional_discrimination",
            turn_text="Publish the convocation notice",
            query=RARQuery(
                reference_expression="the convocation notice",
                candidates=(
                    RARCandidate(id="not_convocation", title="18th_Convocation_Notice.pdf", candidate_type="document", domain_tags=("convocation", "notice")),
                    RARCandidate(id="not_registration", title="Autumn_Semester_Registration_Notice.pdf", candidate_type="document", domain_tags=("registration", "notice")),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="not_convocation",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'convocation' discriminates convocation notice.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-064",
            name="Mess rebate circular vs internet maintenance circular",
            category="institutional_discrimination",
            turn_text="Download the mess rebate notice",
            query=RARQuery(
                reference_expression="the mess rebate notice",
                candidates=(
                    RARCandidate(id="circ_mess", title="Mess_Rebate_Notification_Oct26.pdf", candidate_type="document", domain_tags=("mess", "rebate")),
                    RARCandidate(id="circ_net", title="Campus_Network_Maintenance_Notice.pdf", candidate_type="document", domain_tags=("network", "maintenance")),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="circ_mess",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'mess rebate' discriminates mess circular.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-065",
            name="Anti-ragging affidavit form vs health declaration",
            category="institutional_discrimination",
            turn_text="Print the anti-ragging affidavit",
            query=RARQuery(
                reference_expression="the anti-ragging affidavit",
                candidates=(
                    RARCandidate(id="form_antiragging", title="UGC_Anti_Ragging_Affidavit_Form.pdf", candidate_type="document", domain_tags=("antiragging", "affidavit", "ugc")),
                    RARCandidate(id="form_health", title="Student_Health_Declaration_Form.pdf", candidate_type="document", domain_tags=("health", "medical")),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="form_antiragging",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'anti-ragging affidavit' matches tags and title.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-066",
            name="Scholarship merit list vs fee defaulters list",
            category="institutional_discrimination",
            turn_text="Check the scholarship award list",
            query=RARQuery(
                reference_expression="the scholarship award list",
                candidates=(
                    RARCandidate(id="list_scholarship", title="Merit_Scholarship_Award_List_2026.xlsx", candidate_type="spreadsheet", domain_tags=("scholarship", "merit", "award")),
                    RARCandidate(id="list_defaulters", title="Outstanding_Dues_Student_List.xlsx", candidate_type="spreadsheet", domain_tags=("dues", "defaulters")),
                ),
                local_evidence=RAREvidence(target_type_hint="spreadsheet"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="list_scholarship",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'scholarship award' discriminates merit list.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-067",
            name="Plumbing maintenance contractor entity vs faculty member",
            category="institutional_discrimination",
            turn_text="Call the plumbing contractor",
            query=RARQuery(
                reference_expression="the plumbing contractor",
                candidates=(
                    RARCandidate(id="ent_plumber", title="Apex Pipeline & Plumbing Services", candidate_type="person", domain_tags=("plumbing", "contractor", "maintenance")),
                    RARCandidate(id="ent_faculty", title="Prof. Animesh Roy (Civil Engg)", candidate_type="person", domain_tags=("faculty", "civil")),
                ),
                local_evidence=RAREvidence(target_type_hint="person"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="ent_plumber",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'plumbing contractor' uniquely matches plumbing vendor.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-068",
            name="Library book order vs stationery order",
            category="institutional_discrimination",
            turn_text="Approve the library book order",
            query=RARQuery(
                reference_expression="the library book order",
                candidates=(
                    RARCandidate(id="ord_books", title="Purchase_Order_Central_Library_Books.pdf", candidate_type="document", domain_tags=("library", "books", "order")),
                    RARCandidate(id="ord_stationery", title="Purchase_Order_Office_Stationery.pdf", candidate_type="document", domain_tags=("stationery", "order")),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="ord_books",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'library book' uniquely discriminates library purchase order.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-069",
            name="Faculty recruitment roster vs student grade roster",
            category="institutional_discrimination",
            turn_text="Open the recruitment roster",
            query=RARQuery(
                reference_expression="the recruitment roster",
                candidates=(
                    RARCandidate(id="sheet_recruitment", title="Assistant_Professor_Recruitment_Roster.xlsx", candidate_type="spreadsheet", domain_tags=("recruitment", "roster", "faculty")),
                    RARCandidate(id="sheet_grades", title="Endsem_Grade_Roster_Autumn26.xlsx", candidate_type="spreadsheet", domain_tags=("grades", "student")),
                ),
                local_evidence=RAREvidence(target_type_hint="spreadsheet"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="sheet_recruitment",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'recruitment roster' matches recruitment spreadsheet.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-070",
            name="Wi-Fi downtime notice vs electricity outage notice",
            category="institutional_discrimination",
            turn_text="Forward the Wi-Fi notice to the hostel group",
            query=RARQuery(
                reference_expression="the Wi-Fi notice",
                candidates=(
                    RARCandidate(id="circ_wifi", title="Campus_WiFi_Maintenance_Downtime.pdf", candidate_type="document", domain_tags=("wifi", "network", "notice")),
                    RARCandidate(id="circ_power", title="Substation_Transformer_Power_Outage.pdf", candidate_type="document", domain_tags=("power", "electricity", "notice")),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="circ_wifi",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'Wi-Fi' uniquely discriminates network notice.",
        )
    )

    # =========================================================================
    # PART 2: Naturally Difficult References (CHAL-071 to CHAL-090)
    # =========================================================================

    # --- Group 2A: Similarly Titled Documents with Specific Sub-Topic (4 fixtures) ---
    fixtures.append(
        RARFixture(
            id="CHAL-071",
            name="Two committee minutes distinguished by committee name in query",
            category="similar_titles",
            turn_text="Review the library committee minutes",
            query=RARQuery(
                reference_expression="the library committee minutes",
                candidates=(
                    RARCandidate(id="min_lib", title="Committee_Meeting_Minutes_Oct26.docx", candidate_type="document", domain_tags=("library", "committee", "minutes")),
                    RARCandidate(id="min_hostel", title="Committee_Meeting_Minutes_Sep26.docx", candidate_type="document", domain_tags=("hostel", "committee", "minutes")),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="min_lib",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'library' discriminates the library committee minutes despite identical filename prefix.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-072",
            name="Two vendor quotations distinguished by supplier name",
            category="similar_titles",
            turn_text="Forward the Zenith quotation to procurement",
            query=RARQuery(
                reference_expression="the Zenith quotation",
                candidates=(
                    RARCandidate(id="quote_apex", title="Quotation_Spectrometer_402.pdf", candidate_type="document", domain_tags=("quotation", "apex", "vendor")),
                    RARCandidate(id="quote_zenith", title="Quotation_Spectrometer_901.pdf", candidate_type="document", domain_tags=("quotation", "zenith", "vendor")),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="quote_zenith",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'Zenith' discriminates between two spectrometer quotations.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-073",
            name="Two hostel notices distinguished by hostel wing",
            category="similar_titles",
            turn_text="Display the notice for Brahmaputra hostel",
            query=RARQuery(
                reference_expression="the notice for Brahmaputra hostel",
                candidates=(
                    RARCandidate(id="not_brahma", title="Hostel_Maintenance_Notice.pdf", candidate_type="document", domain_tags=("hostel", "brahmaputra", "notice")),
                    RARCandidate(id="not_ganga", title="Hostel_Maintenance_Notice_Ganga.pdf", candidate_type="document", domain_tags=("hostel", "ganga", "notice")),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="not_brahma",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'Brahmaputra' domain tag isolates specific hostel notice.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-074",
            name="Two student grade dispute submissions distinguished by student roll",
            category="similar_titles",
            turn_text="Review Sneha's grade submission",
            query=RARQuery(
                reference_expression="Sneha's grade submission",
                candidates=(
                    RARCandidate(id="sub_rahul", title="Grade_Appeal_Submission.pdf", candidate_type="document", domain_tags=("appeal", "rahul", "grades")),
                    RARCandidate(id="sub_sneha", title="Grade_Appeal_Submission_Sneha.pdf", candidate_type="document", domain_tags=("appeal", "sneha", "grades")),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="sub_sneha",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'Sneha' uniquely discriminates student grade appeal.",
        )
    )

    # --- Group 2B: Multiple Emails from Same Sender / Similar Thread (4 fixtures) ---
    fixtures.append(
        RARFixture(
            id="CHAL-075",
            name="Two emails from Dean distinguished by exam subject line",
            category="same_sender",
            turn_text="Reply to the Dean's email about the exam schedule",
            query=RARQuery(
                reference_expression="the Dean's email about the exam schedule",
                candidates=(
                    RARCandidate(id="mail_dean_budget", title="Dean Academics: Budget Allocations", candidate_type="email", domain_tags=("dean", "budget")),
                    RARCandidate(id="mail_dean_exam", title="Dean Academics: Endsem Exam Schedule", candidate_type="email", domain_tags=("dean", "exam", "schedule")),
                ),
                local_evidence=RAREvidence(target_type_hint="email"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="mail_dean_exam",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'exam schedule' discriminates between two emails from the Dean.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-076",
            name="Two messages from Registrar distinguished by convocation topic",
            category="same_sender",
            turn_text="Open the Registrar's email regarding convocation gowns",
            query=RARQuery(
                reference_expression="the Registrar's email regarding convocation gowns",
                candidates=(
                    RARCandidate(id="mail_reg_convoc", title="Office of Registrar: Convocation Gowns Measurement", candidate_type="email", domain_tags=("registrar", "convocation", "gowns")),
                    RARCandidate(id="mail_reg_senate", title="Office of Registrar: Senate Notification", candidate_type="email", domain_tags=("registrar", "senate")),
                ),
                local_evidence=RAREvidence(target_type_hint="email"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="mail_reg_convoc",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'convocation gowns' discriminates email topic.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-077",
            name="Two messages from Hostel Warden distinguished by mess menu",
            category="same_sender",
            turn_text="Reply to the warden's email about the mess menu",
            query=RARQuery(
                reference_expression="the warden's email about the mess menu",
                candidates=(
                    RARCandidate(id="mail_warden_discipline", title="Warden: Hostel Curfew Hours", candidate_type="email", domain_tags=("warden", "curfew")),
                    RARCandidate(id="mail_warden_menu", title="Warden: Special Dinner Menu Survey", candidate_type="email", domain_tags=("warden", "mess", "menu")),
                ),
                local_evidence=RAREvidence(target_type_hint="email"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="mail_warden_menu",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'mess menu' discriminates specific email thread from the warden.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-078",
            name="Two messages from Accounts Section distinguished by salary slip",
            category="same_sender",
            turn_text="View the accounts section email with the salary slip",
            query=RARQuery(
                reference_expression="the accounts section email with the salary slip",
                candidates=(
                    RARCandidate(id="mail_acc_tax", title="Accounts: Income Tax Proof Submission", candidate_type="email", domain_tags=("accounts", "tax")),
                    RARCandidate(id="mail_acc_slip", title="Accounts: Monthly Salary Slip Disbursed", candidate_type="email", domain_tags=("accounts", "salary", "slip")),
                ),
                local_evidence=RAREvidence(target_type_hint="email"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="mail_acc_slip",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'salary slip' discriminates email topic from accounts.",
        )
    )

    # --- Group 2C: Natural Negation & Correction (4 fixtures) ---
    fixtures.append(
        RARFixture(
            id="CHAL-079",
            name="Correction: Not the minutes, the order",
            category="negation_correction",
            turn_text="Not the minutes, the order",
            query=RARQuery(
                reference_expression="the order",
                candidates=(
                    RARCandidate(id="doc_minutes", title="Senate_Meeting_Minutes.pdf", candidate_type="document", domain_tags=("minutes", "senate")),
                    RARCandidate(id="doc_order", title="Director_Office_Order_401.pdf", candidate_type="document", domain_tags=("order", "director")),
                ),
                local_evidence=RAREvidence(
                    clause_text="the order",
                    negation_spans=("Not the minutes",),
                    target_type_hint="document",
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="doc_order",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Negation span eliminates minutes, leaving order.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-080",
            name="Correction: Skip the draft, forward the final notice",
            category="negation_correction",
            turn_text="Skip the draft, forward the final notice",
            query=RARQuery(
                reference_expression="the final notice",
                candidates=(
                    RARCandidate(id="not_draft", title="Convocation_Circular_Draft.docx", candidate_type="document", domain_tags=("circular", "draft")),
                    RARCandidate(id="not_final", title="Convocation_Circular_Final.pdf", candidate_type="document", domain_tags=("circular", "final", "notice")),
                ),
                local_evidence=RAREvidence(
                    clause_text="forward the final notice",
                    negation_spans=("Skip the draft",),
                    target_type_hint="document",
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="not_final",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Negation span eliminates draft, resolving final notice.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-081",
            name="Correction: Don't notify the registrar, message the warden",
            category="negation_correction",
            turn_text="Don't notify the registrar, message the warden",
            query=RARQuery(
                reference_expression="the warden",
                candidates=(
                    RARCandidate(id="ent_registrar", title="Dr. S. K. Roy (Registrar)", candidate_type="person", domain_tags=("registrar",)),
                    RARCandidate(id="ent_warden", title="Prof. Anupam Sen (Hostel Warden)", candidate_type="person", domain_tags=("warden",)),
                ),
                local_evidence=RAREvidence(
                    clause_text="message the warden",
                    negation_spans=("Don't notify the registrar",),
                    target_type_hint="person",
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="ent_warden",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Negation eliminates registrar, resolving warden.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-082",
            name="Contrast: Not that one, the other quotation",
            category="negation_correction",
            turn_text="Not that one, the other quotation",
            query=RARQuery(
                reference_expression="the other quotation",
                candidates=(
                    RARCandidate(id="quote_high", title="Quotation_VendorA_HighRate.pdf", candidate_type="document", domain_tags=("rejected_in_turn", "quotation")),
                    RARCandidate(id="quote_low", title="Quotation_VendorB_L1Rate.pdf", candidate_type="document", domain_tags=("alternative", "quotation")),
                ),
                local_evidence=RAREvidence(
                    clause_text="the other quotation",
                    negation_spans=("Not that one",),
                    recency_hint="other",
                    target_type_hint="document",
                ),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="quote_low",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Contrastive 'other' resolves to unrejected quotation.",
        )
    )

    # --- Group 2D: Multiple Attachments / Distractor Attachments (4 fixtures) ---
    fixtures.append(
        RARFixture(
            id="CHAL-083",
            name="Two attachments in thread distinguished by spreadsheet type hint",
            category="multi_attachment",
            turn_text="Import the spreadsheet attachment",
            query=RARQuery(
                reference_expression="the spreadsheet attachment",
                candidates=(
                    RARCandidate(id="att_pdf_cover", title="Covering_Letter.pdf", candidate_type="document", is_attachment=True),
                    RARCandidate(id="att_xls_data", title="Applicant_Rank_List.xlsx", candidate_type="spreadsheet", is_attachment=True),
                ),
                local_evidence=RAREvidence(target_type_hint="spreadsheet"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="att_xls_data",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Spreadsheet type hint discriminates XLSX attachment from PDF letter.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-084",
            name="Two attachments distinguished by voucher keyword",
            category="multi_attachment",
            turn_text="Print the payment voucher attachment",
            query=RARQuery(
                reference_expression="the payment voucher attachment",
                candidates=(
                    RARCandidate(id="att_voucher", title="Payment_Voucher_Oct.pdf", candidate_type="document", is_attachment=True, domain_tags=("voucher", "payment")),
                    RARCandidate(id="att_brochure", title="Equipment_Brochure.pdf", candidate_type="document", is_attachment=True, domain_tags=("brochure", "manual")),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="att_voucher",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'voucher' keyword isolates payment voucher attachment.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-085",
            name="Attachment target amidst repository document distractors",
            category="multi_attachment",
            turn_text="Attach the newly uploaded receipt to the noting",
            query=RARQuery(
                reference_expression="the newly uploaded receipt",
                candidates=(
                    RARCandidate(id="doc_archived_receipt", title="Fee_Receipt_Old.pdf", candidate_type="document", is_attachment=False, recency_rank=3),
                    RARCandidate(id="att_current_receipt", title="HDFC_Payment_Receipt.pdf", candidate_type="document", is_attachment=True, recency_rank=0),
                ),
                deterministic_anchor=RARDeterministicAnchor(current_attachment_id="att_current_receipt"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="att_current_receipt",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Current attachment anchor isolates newly uploaded receipt from archived receipt.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-086",
            name="Target attachment distinguished from email body",
            category="multi_attachment",
            turn_text="Extract the tables from the PDF attached to that email",
            query=RARQuery(
                reference_expression="the PDF attached to that email",
                candidates=(
                    RARCandidate(id="mail_body", title="Fwd: Financial Audit Review", candidate_type="email"),
                    RARCandidate(id="att_audit_sheet", title="Audit_Schedule_Annexure.pdf", candidate_type="document", is_attachment=True),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="att_audit_sheet",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Type filter 'document' isolates PDF attachment from parent email.",
        )
    )

    # --- Group 2E: Multi-Reference Turns (4 fixtures) ---
    c_mref_pair1 = (
        RARCandidate(id="doc_sanction_order", title="Sanction_Order_DST_Project.pdf", candidate_type="document", recency_rank=0),
        RARCandidate(id="ent_director_office", title="Office of the Director", candidate_type="person", recency_rank=1),
    )

    fixtures.append(
        RARFixture(
            id="CHAL-087",
            name="Multi-ref turn clause 1: document target",
            category="multi_reference",
            turn_text="Forward the sanction order to the director",
            query=RARQuery(
                reference_expression="the sanction order",
                candidates=c_mref_pair1,
                local_evidence=RAREvidence(clause_text="Forward the sanction order", target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="doc_sanction_order",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Clause 1 document target resolves to sanction order.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-088",
            name="Multi-ref turn clause 2: person target",
            category="multi_reference",
            turn_text="Forward the sanction order to the director",
            query=RARQuery(
                reference_expression="the director",
                candidates=c_mref_pair1,
                local_evidence=RAREvidence(clause_text="to the director", target_type_hint="person"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="ent_director_office",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Clause 2 person target resolves to director.",
        )
    )

    c_mref_pair2 = (
        RARCandidate(id="sheet_marks", title="Endsem_Consolidated_Marks.xlsx", candidate_type="spreadsheet"),
        RARCandidate(id="mail_dean_ac", title="Dean Academics Notification", candidate_type="email"),
    )

    fixtures.append(
        RARFixture(
            id="CHAL-089",
            name="Multi-ref turn clause A: spreadsheet target",
            category="multi_reference",
            turn_text="Attach the marks spreadsheet to that email",
            query=RARQuery(
                reference_expression="the marks spreadsheet",
                candidates=c_mref_pair2,
                local_evidence=RAREvidence(clause_text="Attach the marks spreadsheet", target_type_hint="spreadsheet"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="sheet_marks",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Clause A spreadsheet target resolves to marks sheet.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-090",
            name="Multi-ref turn clause B: email target",
            category="multi_reference",
            turn_text="Attach the marks spreadsheet to that email",
            query=RARQuery(
                reference_expression="that email",
                candidates=c_mref_pair2,
                local_evidence=RAREvidence(clause_text="to that email", target_type_hint="email"),
            ),
            expected_outcome=RAROutcome.RESOLVED,
            expected_candidate_id="mail_dean_ac",
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Clause B email target resolves to dean email.",
        )
    )

    # =========================================================================
    # PART 3: Legitimately Unresolvable / Ambiguous (CHAL-091 to CHAL-100)
    # =========================================================================

    # --- Group 3A: Truly Ambiguous (5 fixtures) ---
    fixtures.append(
        RARFixture(
            id="CHAL-091",
            name="Two equipment purchase orders with identical title and recency",
            category="legitimate_ambiguous",
            turn_text="Forward the purchase order to accounts",
            query=RARQuery(
                reference_expression="the purchase order",
                candidates=(
                    RARCandidate(id="po_spectrometer", title="Purchase_Order_Lab_Equipment.pdf", candidate_type="document", recency_rank=0, domain_tags=("purchase", "order", "lab")),
                    RARCandidate(id="po_chromatograph", title="Purchase_Order_Lab_Supplies.pdf", candidate_type="document", recency_rank=0, domain_tags=("purchase", "order", "lab")),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.AMBIGUOUS,
            expected_ambiguous_candidate_ids=("po_spectrometer", "po_chromatograph"),
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Two purchase orders with identical rank and generic words; safe abstention as AMBIGUOUS required.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-092",
            name="Two notices from Academic Section with equal plausibility",
            category="legitimate_ambiguous",
            turn_text="Display the notice",
            query=RARQuery(
                reference_expression="the notice",
                candidates=(
                    RARCandidate(id="not_exam", title="Academic_Notice_Examinations.pdf", candidate_type="document", recency_rank=1, domain_tags=("academic", "notice")),
                    RARCandidate(id="not_registration", title="Academic_Notice_Registration.pdf", candidate_type="document", recency_rank=1, domain_tags=("academic", "notice")),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.AMBIGUOUS,
            expected_ambiguous_candidate_ids=("not_exam", "not_registration"),
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Bare reference 'the notice' over two academic notices; must return AMBIGUOUS.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-093",
            name="Unanchored bare pronoun with two active documents",
            category="legitimate_ambiguous",
            turn_text="Send it to the registrar",
            query=RARQuery(
                reference_expression="it",
                candidates=(
                    RARCandidate(id="doc_memo_1", title="Proposal_Draft_A.pdf", candidate_type="document", recency_rank=1),
                    RARCandidate(id="doc_memo_2", title="Proposal_Draft_B.pdf", candidate_type="document", recency_rank=1),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.AMBIGUOUS,
            expected_ambiguous_candidate_ids=("doc_memo_1", "doc_memo_2"),
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Unanchored pronoun 'it' across two active documents; safe abstention as AMBIGUOUS required.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-094",
            name="Two fee receipts without distinguishing student qualifier",
            category="legitimate_ambiguous",
            turn_text="Check the fee receipt",
            query=RARQuery(
                reference_expression="the fee receipt",
                candidates=(
                    RARCandidate(id="rcpt_amit", title="Hostel_Fee_Receipt_Amit.pdf", candidate_type="document", recency_rank=0, domain_tags=("fee", "receipt")),
                    RARCandidate(id="rcpt_priya", title="Hostel_Fee_Receipt_Priya.pdf", candidate_type="document", recency_rank=0, domain_tags=("fee", "receipt")),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.AMBIGUOUS,
            expected_ambiguous_candidate_ids=("rcpt_amit", "rcpt_priya"),
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Generic reference to 'the fee receipt' when two receipts exist; must return AMBIGUOUS.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-095",
            name="Two revised guidelines in active context",
            category="legitimate_ambiguous",
            turn_text="Open the revised guidelines",
            query=RARQuery(
                reference_expression="the revised guidelines",
                candidates=(
                    RARCandidate(id="guide_hostel", title="Hostel_Discipline_Guidelines_revised.pdf", candidate_type="document", domain_tags=("guidelines", "revised")),
                    RARCandidate(id="guide_library", title="Library_Borrowing_Guidelines_revised.pdf", candidate_type="document", domain_tags=("guidelines", "revised")),
                ),
                local_evidence=RAREvidence(recency_hint="revised", target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.AMBIGUOUS,
            expected_ambiguous_candidate_ids=("guide_hostel", "guide_library"),
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Two revised guideline documents with equal revision cues; must return AMBIGUOUS.",
        )
    )

    # --- Group 3B: Legitimate Unknown / Absent Target (5 fixtures) ---
    fixtures.append(
        RARFixture(
            id="CHAL-096",
            name="Chemistry lab report missing from candidate pool",
            category="legitimate_unknown",
            turn_text="Summarize the chemistry lab report",
            query=RARQuery(
                reference_expression="the chemistry lab report",
                candidates=(
                    RARCandidate(id="doc_physics", title="Physics_Experiment_Report.pdf", candidate_type="document", domain_tags=("physics", "lab")),
                    RARCandidate(id="doc_math", title="Mathematics_Tutorial_Sheet.pdf", candidate_type="document", domain_tags=("math", "tutorial")),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.UNKNOWN,
            expected_candidate_id=None,
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="'chemistry' report is not in candidate set; safe abstention as UNKNOWN required.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-097",
            name="Named professor not present in candidate pool",
            category="legitimate_unknown",
            turn_text="Forward the email to Dr. Kulkarni",
            query=RARQuery(
                reference_expression="Dr. Kulkarni",
                candidates=(
                    RARCandidate(id="person_prof_das", title="Dr. B. Das", candidate_type="person", domain_tags=("faculty", "chemistry")),
                    RARCandidate(id="person_prof_sharma", title="Prof. V. Sharma", candidate_type="person", domain_tags=("faculty", "physics")),
                ),
                local_evidence=RAREvidence(target_type_hint="person"),
            ),
            expected_outcome=RAROutcome.UNKNOWN,
            expected_candidate_id=None,
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Target person Dr. Kulkarni absent from candidates; safe abstention as UNKNOWN required.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-098",
            name="Spreadsheet reference when only PDFs and emails exist",
            category="legitimate_unknown",
            turn_text="Open the budget spreadsheet",
            query=RARQuery(
                reference_expression="the budget spreadsheet",
                candidates=(
                    RARCandidate(id="doc_rules", title="Hostel_Allotment_Rules.pdf", candidate_type="document"),
                    RARCandidate(id="mail_notice", title="Hostel Fee Reminder", candidate_type="email"),
                ),
                local_evidence=RAREvidence(target_type_hint="spreadsheet"),
            ),
            expected_outcome=RAROutcome.UNKNOWN,
            expected_candidate_id=None,
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Zero spreadsheet candidates exist; must safely abstain as UNKNOWN.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-099",
            name="Warranty card requested when only invoices and receipts exist",
            category="legitimate_unknown",
            turn_text="Check the warranty card for the spectrometer",
            query=RARQuery(
                reference_expression="the warranty card",
                candidates=(
                    RARCandidate(id="doc_inv", title="Tax_Invoice_Spectrometer.pdf", candidate_type="document", domain_tags=("invoice", "tax")),
                    RARCandidate(id="doc_rcpt", title="Delivery_Challan_Receipt.pdf", candidate_type="document", domain_tags=("delivery", "challan")),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.UNKNOWN,
            expected_candidate_id=None,
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Warranty card is absent from candidate pool; must abstain as UNKNOWN.",
        )
    )

    fixtures.append(
        RARFixture(
            id="CHAL-100",
            name="Non-existent order number reference",
            category="legitimate_unknown",
            turn_text="Review Office Order #9921",
            query=RARQuery(
                reference_expression="Office Order #9921",
                candidates=(
                    RARCandidate(id="ord_401", title="Office_Order_401.pdf", candidate_type="document", exact_aliases=("order-401",)),
                    RARCandidate(id="ord_402", title="Office_Order_402.pdf", candidate_type="document", exact_aliases=("order-402",)),
                ),
                local_evidence=RAREvidence(target_type_hint="document"),
            ),
            expected_outcome=RAROutcome.UNKNOWN,
            expected_candidate_id=None,
            expected_basis=RARBasis.DETERMINISTIC_ANCHOR,
            description="Order #9921 does not exist in candidates; must return UNKNOWN.",
        )
    )

    return tuple(fixtures)
