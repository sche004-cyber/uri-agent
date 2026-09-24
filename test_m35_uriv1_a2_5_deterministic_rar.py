"""Unit tests for M35 URIv1 Batch A2.5 Stage 2: Legacy-Derived Deterministic RAR Stack.

Verifies:
1. All 24 diagnostic fixtures in uri_v1.turn.rar_fixtures pass with 100% precision.
2. Levels 0 through 6 rule mechanics under targeted unit fixtures.
3. Strict invariant enforcement (zero candidate invention, zero index-0 bias).
4. Adversarial edge cases (candidate reordering, duplicate titles, tied scores, negation collapse).
"""

from __future__ import annotations

import unittest

from uri_v1.turn.rar_contracts import (
    RARBasis,
    RARCandidate,
    RARContractViolationError,
    RARDeterministicAnchor,
    RAREvidence,
    RARFailureClass,
    RARDriverRule,
    RAROutcome,
    RARQuery,
    RARResolution,
    validate_rar_resolution,
)
from uri_v1.turn.rar_deterministic import (
    DeterministicRARTrace,
    clean_tokens,
    compute_term_document_frequency,
    resolve_rar_deterministic_extended,
    score_candidate_relevance,
    stem_title,
)
from uri_v1.turn.rar_fixtures import get_rar_diagnostic_fixtures


class RARDiagnosticFixturesRegressionTests(unittest.TestCase):
    """Executes the full 24-fixture diagnostic qualification tranche."""

    def test_all_24_diagnostic_fixtures_pass(self):
        fixtures = get_rar_diagnostic_fixtures()
        self.assertEqual(len(fixtures), 24)

        for fix in fixtures:
            with self.subTest(fixture_id=fix.id, name=fix.name):
                trace = resolve_rar_deterministic_extended(fix.query)
                res = trace.resolution

                # Outcome must match exactly
                self.assertEqual(
                    res.outcome,
                    fix.expected_outcome,
                    f"Fixture {fix.id} failed outcome match: expected {fix.expected_outcome}, got {res.outcome} (rule={trace.rule_used})",
                )

                # Candidate ID must match if expected
                if fix.expected_candidate_id is not None:
                    self.assertEqual(
                        res.candidate_id,
                        fix.expected_candidate_id,
                        f"Fixture {fix.id} failed candidate match: expected {fix.expected_candidate_id}, got {res.candidate_id}",
                    )

                # Ambiguous candidate IDs must match if expected
                if fix.expected_ambiguous_candidate_ids:
                    self.assertEqual(
                        set(res.ambiguous_candidate_ids),
                        set(fix.expected_ambiguous_candidate_ids),
                        f"Fixture {fix.id} failed ambiguous set match: expected {fix.expected_ambiguous_candidate_ids}, got {res.ambiguous_candidate_ids}",
                    )

                # Contract invariants must strictly hold
                validate_rar_resolution(res, fix.query.candidates)


class RARLevelRuleMechanicsTests(unittest.TestCase):
    """Tests each individual level of the deterministic RAR stack."""

    def test_level_0_exact_id_in_anchor(self):
        c1 = RARCandidate(id="doc_101", title="Memo.pdf", candidate_type="document")
        c2 = RARCandidate(id="doc_102", title="Notes.pdf", candidate_type="document")
        query = RARQuery(
            reference_expression="that document",
            candidates=(c1, c2),
            deterministic_anchor=RARDeterministicAnchor(exact_id="doc_101"),
        )
        trace = resolve_rar_deterministic_extended(query)
        self.assertEqual(trace.resolution.outcome, RAROutcome.RESOLVED)
        self.assertEqual(trace.resolution.candidate_id, "doc_101")
        self.assertEqual(trace.rule_used, RARDriverRule.EXACT_ID)

    def test_level_0_exact_alias_match(self):
        c1 = RARCandidate(
            id="doc_audit_984",
            title="Audit_Report.pdf",
            candidate_type="document",
            exact_aliases=("audit-984", "q4-audit"),
        )
        c2 = RARCandidate(id="doc_misc", title="Misc.pdf", candidate_type="document")
        query = RARQuery(
            reference_expression="audit-984",
            candidates=(c1, c2),
        )
        trace = resolve_rar_deterministic_extended(query)
        self.assertEqual(trace.resolution.outcome, RAROutcome.RESOLVED)
        self.assertEqual(trace.resolution.candidate_id, "doc_audit_984")
        self.assertEqual(trace.rule_used, RARDriverRule.EXACT_ALIAS)

    def test_level_1_active_attachment_anchor(self):
        c1 = RARCandidate(id="att_upload", title="File.pdf", candidate_type="document", is_attachment=True)
        c2 = RARCandidate(id="doc_repo", title="Existing.pdf", candidate_type="document")
        query = RARQuery(
            reference_expression="this attachment",
            candidates=(c1, c2),
            deterministic_anchor=RARDeterministicAnchor(current_attachment_id="att_upload"),
        )
        trace = resolve_rar_deterministic_extended(query)
        self.assertEqual(trace.resolution.outcome, RAROutcome.RESOLVED)
        self.assertEqual(trace.resolution.candidate_id, "att_upload")
        self.assertEqual(trace.rule_used, RARDriverRule.CURRENT_ATTACHMENT)

    def test_level_1_selected_ui_anchor(self):
        c1 = RARCandidate(id="ui_item_7", title="Selected Card", candidate_type="document")
        c2 = RARCandidate(id="bg_item_2", title="Background Card", candidate_type="document")
        query = RARQuery(
            reference_expression="this",
            candidates=(c1, c2),
            deterministic_anchor=RARDeterministicAnchor(selected_ui_id="ui_item_7"),
        )
        trace = resolve_rar_deterministic_extended(query)
        self.assertEqual(trace.resolution.outcome, RAROutcome.RESOLVED)
        self.assertEqual(trace.resolution.candidate_id, "ui_item_7")
        self.assertEqual(trace.rule_used, RARDriverRule.ACTIVE_UI)

    def test_level_2_verbatim_title_stem_match(self):
        c1 = RARCandidate(id="doc_hr", title="HR_Benefits_Guide_2026.docx", candidate_type="document")
        c2 = RARCandidate(id="doc_it", title="IT_Security_Protocol.pdf", candidate_type="document")
        query = RARQuery(
            reference_expression="hr benefits guide 2026",
            candidates=(c1, c2),
        )
        trace = resolve_rar_deterministic_extended(query)
        self.assertEqual(trace.resolution.outcome, RAROutcome.RESOLVED)
        self.assertEqual(trace.resolution.candidate_id, "doc_hr")
        self.assertEqual(trace.rule_used, RARDriverRule.EXACT_TITLE)

    def test_level_2_duplicate_title_tie_returns_ambiguous(self):
        """CRITICAL: Two candidates with duplicate titles MUST produce AMBIGUOUS, never guessing index 0."""
        c1 = RARCandidate(id="doc_version_a", title="Meeting_Minutes.docx", candidate_type="document")
        c2 = RARCandidate(id="doc_version_b", title="Meeting_Minutes.docx", candidate_type="document")
        query = RARQuery(
            reference_expression="Meeting_Minutes.docx",
            candidates=(c1, c2),
        )
        trace = resolve_rar_deterministic_extended(query)
        self.assertEqual(trace.resolution.outcome, RAROutcome.AMBIGUOUS)
        self.assertIsNone(trace.resolution.candidate_id)
        self.assertEqual(set(trace.resolution.ambiguous_candidate_ids), {"doc_version_a", "doc_version_b"})
        self.assertEqual(trace.failure_class, RARFailureClass.MULTIPLE_PLAUSIBLE)

    def test_level_3_active_pointer_same_document(self):
        c1 = RARCandidate(id="doc_active", title="Active_Doc.pdf", candidate_type="document", domain_tags=("recently_discussed",))
        c2 = RARCandidate(id="doc_dormant", title="Dormant.pdf", candidate_type="document", recency_rank=5)
        query = RARQuery(
            reference_expression="the same document",
            candidates=(c1, c2),
            local_evidence=RAREvidence(recency_hint="same", target_type_hint="document"),
        )
        trace = resolve_rar_deterministic_extended(query)
        self.assertEqual(trace.resolution.outcome, RAROutcome.RESOLVED)
        self.assertEqual(trace.resolution.candidate_id, "doc_active")
        self.assertEqual(trace.rule_used, RARDriverRule.ACTIVE_POINTER)

    def test_level_4_type_filtering_single_match(self):
        c1 = RARCandidate(id="flow_1", title="Export Workflow", candidate_type="workflow")
        c2 = RARCandidate(id="doc_1", title="Export Guide", candidate_type="document")
        query = RARQuery(
            reference_expression="the workflow",
            candidates=(c1, c2),
            local_evidence=RAREvidence(target_type_hint="workflow"),
        )
        trace = resolve_rar_deterministic_extended(query)
        self.assertEqual(trace.resolution.outcome, RAROutcome.RESOLVED)
        self.assertEqual(trace.resolution.candidate_id, "flow_1")
        self.assertEqual(trace.rule_used, RARDriverRule.TYPE_FILTER)

    def test_level_4_type_filtering_zero_matches_returns_unknown(self):
        c1 = RARCandidate(id="doc_1", title="Memo.pdf", candidate_type="document")
        c2 = RARCandidate(id="email_1", title="Notice", candidate_type="email")
        query = RARQuery(
            reference_expression="the spreadsheet",
            candidates=(c1, c2),
            local_evidence=RAREvidence(target_type_hint="spreadsheet"),
        )
        trace = resolve_rar_deterministic_extended(query)
        self.assertEqual(trace.resolution.outcome, RAROutcome.UNKNOWN)
        self.assertIsNone(trace.resolution.candidate_id)
        self.assertEqual(trace.failure_class, RARFailureClass.NO_CANDIDATE)

    def test_level_4_negation_eliminates_candidate(self):
        c1 = RARCandidate(id="doc_inv", title="Invoice_01.pdf", candidate_type="document", domain_tags=("invoice",))
        c2 = RARCandidate(id="doc_rep", title="Quarterly_Report.pdf", candidate_type="document", domain_tags=("report",))
        query = RARQuery(
            reference_expression="the report",
            candidates=(c1, c2),
            local_evidence=RAREvidence(
                negation_spans=("Skip the invoice",),
                target_type_hint="document",
            ),
        )
        trace = resolve_rar_deterministic_extended(query)
        self.assertEqual(trace.resolution.outcome, RAROutcome.RESOLVED)
        self.assertEqual(trace.resolution.candidate_id, "doc_rep")
        self.assertIn("doc_inv", trace.eliminated_candidate_ids)

    def test_level_5_temporal_previous_rank(self):
        c_latest = RARCandidate(id="msg_0", title="Thread 3", candidate_type="email", recency_rank=0)
        c_prev = RARCandidate(id="msg_1", title="Thread 2", candidate_type="email", recency_rank=1)
        c_old = RARCandidate(id="msg_2", title="Thread 1", candidate_type="email", recency_rank=2)
        query = RARQuery(
            reference_expression="the previous email",
            candidates=(c_latest, c_prev, c_old),
            local_evidence=RAREvidence(recency_hint="previous", target_type_hint="email"),
        )
        trace = resolve_rar_deterministic_extended(query)
        self.assertEqual(trace.resolution.outcome, RAROutcome.RESOLVED)
        self.assertEqual(trace.resolution.candidate_id, "msg_1")
        self.assertEqual(trace.rule_used, RARDriverRule.TEMPORAL_RELATION)

    def test_level_5_revision_relation(self):
        c_orig = RARCandidate(id="draft_v1", title="Rules_v1.docx", candidate_type="document", domain_tags=("original",))
        c_rev = RARCandidate(id="draft_v2", title="Rules_v2.docx", candidate_type="document", domain_tags=("revised",))
        query = RARQuery(
            reference_expression="the revised draft",
            candidates=(c_orig, c_rev),
            local_evidence=RAREvidence(recency_hint="revised", target_type_hint="document"),
        )
        trace = resolve_rar_deterministic_extended(query)
        self.assertEqual(trace.resolution.outcome, RAROutcome.RESOLVED)
        self.assertEqual(trace.resolution.candidate_id, "draft_v2")
        self.assertEqual(trace.rule_used, RARDriverRule.REVISION_RELATION)

    def test_level_6_tfidf_discriminating_term_isolation(self):
        c1 = RARCandidate(id="ent_prof", title="Prof. K. Sharma", candidate_type="person", domain_tags=("faculty", "dean"))
        c2 = RARCandidate(id="ent_contractor", title="Apex Plumbing Contractor", candidate_type="person", domain_tags=("contractor", "maintenance"))
        query = RARQuery(
            reference_expression="the contractor",
            candidates=(c1, c2),
            local_evidence=RAREvidence(target_type_hint="person"),
        )
        trace = resolve_rar_deterministic_extended(query)
        self.assertEqual(trace.resolution.outcome, RAROutcome.RESOLVED)
        self.assertEqual(trace.resolution.candidate_id, "ent_contractor")
        self.assertEqual(trace.rule_used, RARDriverRule.TERM_DISCRIMINATION)

    def test_level_6_tfidf_tied_scores_return_ambiguous(self):
        c1 = RARCandidate(id="sheet_q1", title="Budget_Q1.xlsx", candidate_type="spreadsheet", domain_tags=("budget", "finance"))
        c2 = RARCandidate(id="sheet_q2", title="Budget_Q2.xlsx", candidate_type="spreadsheet", domain_tags=("budget", "finance"))
        query = RARQuery(
            reference_expression="the budget spreadsheet",
            candidates=(c1, c2),
            local_evidence=RAREvidence(target_type_hint="spreadsheet"),
        )
        trace = resolve_rar_deterministic_extended(query)
        self.assertEqual(trace.resolution.outcome, RAROutcome.AMBIGUOUS)
        self.assertEqual(set(trace.resolution.ambiguous_candidate_ids), {"sheet_q1", "sheet_q2"})
        self.assertEqual(trace.failure_class, RARFailureClass.MULTIPLE_PLAUSIBLE)


class RARAdversarialEdgeCaseTests(unittest.TestCase):
    """Adversarial stress testing against candidate manipulation and edge cases."""

    def test_candidate_order_invariance(self):
        """Resolutions MUST be identical regardless of candidate array ordering."""
        c1 = RARCandidate(id="doc_policy", title="Hostel_Policy_Draft.docx", candidate_type="document", domain_tags=("policy", "draft"))
        c2 = RARCandidate(id="email_notice", title="Maintenance Notice", candidate_type="email")

        q_forward = RARQuery(
            reference_expression="that draft",
            candidates=(c1, c2),
            local_evidence=RAREvidence(target_type_hint="document"),
        )
        q_reverse = RARQuery(
            reference_expression="that draft",
            candidates=(c2, c1),
            local_evidence=RAREvidence(target_type_hint="document"),
        )

        trace_fwd = resolve_rar_deterministic_extended(q_forward)
        trace_rev = resolve_rar_deterministic_extended(q_reverse)

        self.assertEqual(trace_fwd.resolution.outcome, trace_rev.resolution.outcome)
        self.assertEqual(trace_fwd.resolution.candidate_id, trace_rev.resolution.candidate_id)
        self.assertEqual(trace_fwd.rule_used, trace_rev.rule_used)

    def test_empty_candidates_returns_safe_unknown(self):
        query = RARQuery(
            reference_expression="the proposal",
            candidates=(),
            local_evidence=RAREvidence(target_type_hint="document"),
        )
        trace = resolve_rar_deterministic_extended(query)
        self.assertEqual(trace.resolution.outcome, RAROutcome.UNKNOWN)
        self.assertIsNone(trace.resolution.candidate_id)
        self.assertEqual(trace.failure_class, RARFailureClass.NO_CANDIDATE)

    def test_all_candidates_negated_returns_safe_unknown(self):
        c1 = RARCandidate(id="doc_a", title="Plan_A.docx", candidate_type="document", domain_tags=("plan_a",))
        query = RARQuery(
            reference_expression="the plan",
            candidates=(c1,),
            local_evidence=RAREvidence(
                negation_spans=("Skip Plan A",),
                target_type_hint="document",
            ),
        )
        trace = resolve_rar_deterministic_extended(query)
        self.assertEqual(trace.resolution.outcome, RAROutcome.UNKNOWN)
        self.assertEqual(trace.failure_class, RARFailureClass.NO_CANDIDATE)
        self.assertIn("doc_a", trace.eliminated_candidate_ids)

    def test_unanchored_pronoun_with_multiple_candidates_returns_ambiguous(self):
        c1 = RARCandidate(id="cand_1", title="First Option.docx", candidate_type="document")
        c2 = RARCandidate(id="cand_2", title="Second Option.docx", candidate_type="document")
        query = RARQuery(
            reference_expression="that one",
            candidates=(c1, c2),
            local_evidence=RAREvidence(target_type_hint="document"),
        )
        trace = resolve_rar_deterministic_extended(query)
        self.assertEqual(trace.resolution.outcome, RAROutcome.AMBIGUOUS)
        self.assertEqual(trace.failure_class, RARFailureClass.PRONOUN_BINDING)
        self.assertEqual(set(trace.resolution.ambiguous_candidate_ids), {"cand_1", "cand_2"})


if __name__ == "__main__":
    unittest.main()
