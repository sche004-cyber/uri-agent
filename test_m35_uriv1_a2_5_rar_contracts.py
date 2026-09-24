"""Unit tests for Batch A2.5: Reference Anchor Resolution (RAR) Contracts and Fixtures.

Verifies:
1. RAR Enums and frozen dataclasses immutability.
2. Invariant enforcement in validate_rar_resolution (Anti-Candidate Invention).
3. Deterministic anchor short-circuiting (resolve_rar_deterministically).
4. Fixture suite integrity across all 24 diagnostic fixtures and 8 categories.
"""

from __future__ import annotations

import unittest

from uri_v1.turn.rar_contracts import (
    RARBasis,
    RARCandidate,
    RARContractViolationError,
    RARDeterministicAnchor,
    RAREvidence,
    RAROutcome,
    RARQuery,
    RARResolution,
    resolve_rar_deterministically,
    validate_rar_resolution,
)
from uri_v1.turn.rar_fixtures import get_rar_diagnostic_fixtures


class RARContractsAndInvariantsTests(unittest.TestCase):
    """Tests contract integrity and candidate-invention protection."""

    def setUp(self):
        self.c1 = RARCandidate(
            id="cand_1",
            title="Policy_Document_2026.docx",
            candidate_type="document",
            recency_rank=0,
            exact_aliases=("cand_1", "policy-2026"),
        )
        self.c2 = RARCandidate(
            id="cand_2",
            title="Procurement_Guidelines.pdf",
            candidate_type="document",
            recency_rank=1,
        )
        self.candidates = (self.c1, self.c2)

    def test_valid_resolved_passes_validation(self):
        res = RARResolution(
            reference_expression="the policy",
            outcome=RAROutcome.RESOLVED,
            candidate_id="cand_1",
            basis=RARBasis.MODEL_SELECTION,
        )
        # Should not raise
        validate_rar_resolution(res, self.candidates)

    def test_resolved_with_none_candidate_id_raises(self):
        res = RARResolution(
            reference_expression="the policy",
            outcome=RAROutcome.RESOLVED,
            candidate_id=None,
        )
        with self.assertRaises(RARContractViolationError) as ctx:
            validate_rar_resolution(res, self.candidates)
        self.assertIn("candidate_id is empty/None", str(ctx.exception))

    def test_resolved_with_invented_candidate_id_raises(self):
        """CRITICAL: Candidate invention must be strictly rejected."""
        res = RARResolution(
            reference_expression="the secret policy",
            outcome=RAROutcome.RESOLVED,
            candidate_id="invented_doc_999",
        )
        with self.assertRaises(RARContractViolationError) as ctx:
            validate_rar_resolution(res, self.candidates)
        self.assertIn("Candidate invention detected", str(ctx.exception))
        self.assertIn("invented_doc_999", str(ctx.exception))

    def test_resolved_with_ambiguous_ids_raises(self):
        res = RARResolution(
            reference_expression="the policy",
            outcome=RAROutcome.RESOLVED,
            candidate_id="cand_1",
            ambiguous_candidate_ids=("cand_1", "cand_2"),
        )
        with self.assertRaises(RARContractViolationError) as ctx:
            validate_rar_resolution(res, self.candidates)
        self.assertIn("ambiguous_candidate_ids is non-empty", str(ctx.exception))

    def test_valid_ambiguous_passes_validation(self):
        res = RARResolution(
            reference_expression="the document",
            outcome=RAROutcome.AMBIGUOUS,
            ambiguous_candidate_ids=("cand_1", "cand_2"),
        )
        validate_rar_resolution(res, self.candidates)

    def test_ambiguous_with_candidate_id_set_raises(self):
        res = RARResolution(
            reference_expression="the document",
            outcome=RAROutcome.AMBIGUOUS,
            candidate_id="cand_1",
            ambiguous_candidate_ids=("cand_1", "cand_2"),
        )
        with self.assertRaises(RARContractViolationError) as ctx:
            validate_rar_resolution(res, self.candidates)
        self.assertIn("candidate_id is set", str(ctx.exception))

    def test_ambiguous_with_fewer_than_two_candidates_raises(self):
        res = RARResolution(
            reference_expression="the document",
            outcome=RAROutcome.AMBIGUOUS,
            ambiguous_candidate_ids=("cand_1",),
        )
        with self.assertRaises(RARContractViolationError) as ctx:
            validate_rar_resolution(res, self.candidates)
        self.assertIn("fewer than 2 ambiguous_candidate_ids", str(ctx.exception))

    def test_ambiguous_with_invented_candidate_id_raises(self):
        res = RARResolution(
            reference_expression="the document",
            outcome=RAROutcome.AMBIGUOUS,
            ambiguous_candidate_ids=("cand_1", "invented_xyz"),
        )
        with self.assertRaises(RARContractViolationError) as ctx:
            validate_rar_resolution(res, self.candidates)
        self.assertIn("Candidate invention in ambiguity set", str(ctx.exception))
        self.assertIn("invented_xyz", str(ctx.exception))

    def test_valid_unknown_passes_validation(self):
        res = RARResolution(
            reference_expression="the invoice",
            outcome=RAROutcome.UNKNOWN,
        )
        validate_rar_resolution(res, self.candidates)

    def test_unknown_with_candidate_id_set_raises(self):
        res = RARResolution(
            reference_expression="the invoice",
            outcome=RAROutcome.UNKNOWN,
            candidate_id="cand_1",
        )
        with self.assertRaises(RARContractViolationError) as ctx:
            validate_rar_resolution(res, self.candidates)
        self.assertIn("candidate_id is set", str(ctx.exception))

    def test_unknown_with_ambiguous_ids_set_raises(self):
        res = RARResolution(
            reference_expression="the invoice",
            outcome=RAROutcome.UNKNOWN,
            ambiguous_candidate_ids=("cand_1", "cand_2"),
        )
        with self.assertRaises(RARContractViolationError) as ctx:
            validate_rar_resolution(res, self.candidates)
        self.assertIn("ambiguous_candidate_ids is non-empty", str(ctx.exception))


class RARDeterministicBypassTests(unittest.TestCase):
    """Verifies that deterministic anchors short-circuit without model intervention."""

    def setUp(self):
        self.c_ui = RARCandidate(
            id="doc_ui_active",
            title="Active_Tab.pdf",
            candidate_type="document",
        )
        self.c_att = RARCandidate(
            id="att_current",
            title="Attached_Spreadsheet.xlsx",
            candidate_type="spreadsheet",
            is_attachment=True,
        )
        self.c_exact = RARCandidate(
            id="doc_exact_42",
            title="Regulation_42.pdf",
            candidate_type="document",
            exact_aliases=("doc_exact_42", "reg-42"),
        )
        self.candidates = (self.c_ui, self.c_att, self.c_exact)

    def test_selected_ui_anchor_resolves_deterministically(self):
        query = RARQuery(
            reference_expression="this document",
            candidates=self.candidates,
            deterministic_anchor=RARDeterministicAnchor(selected_ui_id="doc_ui_active"),
        )
        res = resolve_rar_deterministically(query)
        self.assertIsNotNone(res)
        self.assertEqual(res.outcome, RAROutcome.RESOLVED)
        self.assertEqual(res.candidate_id, "doc_ui_active")
        self.assertEqual(res.basis, RARBasis.DETERMINISTIC_ANCHOR)

    def test_current_attachment_anchor_resolves_deterministically(self):
        query = RARQuery(
            reference_expression="this attachment",
            candidates=self.candidates,
            deterministic_anchor=RARDeterministicAnchor(current_attachment_id="att_current"),
        )
        res = resolve_rar_deterministically(query)
        self.assertIsNotNone(res)
        self.assertEqual(res.outcome, RAROutcome.RESOLVED)
        self.assertEqual(res.candidate_id, "att_current")
        self.assertEqual(res.basis, RARBasis.DETERMINISTIC_ANCHOR)

    def test_exact_id_anchor_resolves_deterministically(self):
        query = RARQuery(
            reference_expression="doc_exact_42",
            candidates=self.candidates,
            deterministic_anchor=RARDeterministicAnchor(exact_id="doc_exact_42"),
        )
        res = resolve_rar_deterministically(query)
        self.assertIsNotNone(res)
        self.assertEqual(res.outcome, RAROutcome.RESOLVED)
        self.assertEqual(res.candidate_id, "doc_exact_42")
        self.assertEqual(res.basis, RARBasis.DETERMINISTIC_ANCHOR)

    def test_verbatim_alias_match_resolves_deterministically(self):
        query = RARQuery(
            reference_expression="reg-42",
            candidates=self.candidates,
        )
        res = resolve_rar_deterministically(query)
        self.assertIsNotNone(res)
        self.assertEqual(res.outcome, RAROutcome.RESOLVED)
        self.assertEqual(res.candidate_id, "doc_exact_42")
        self.assertEqual(res.basis, RARBasis.DETERMINISTIC_ANCHOR)

    def test_unanchored_query_returns_none_for_model_delegation(self):
        query = RARQuery(
            reference_expression="that file",
            candidates=self.candidates,
        )
        res = resolve_rar_deterministically(query)
        self.assertIsNone(res, "Unanchored natural language query must return None (delegate to model)")


class RARDiagnosticFixturesTests(unittest.TestCase):
    """Verifies that all 24 diagnostic fixtures are structurally sound and complete."""

    def test_fixture_count_and_categories(self):
        fixtures = get_rar_diagnostic_fixtures()
        self.assertEqual(len(fixtures), 24, "Must contain exactly 24 diagnostic fixtures")

        expected_categories = {
            "simple_selection",
            "unknown",
            "ambiguous",
            "relational",
            "negation_contrast",
            "distractors",
            "multi_reference",
            "deterministic_bypass",
        }
        present_categories = {f.category for f in fixtures}
        self.assertEqual(present_categories, expected_categories)

    def test_category_counts(self):
        fixtures = get_rar_diagnostic_fixtures()
        from collections import Counter
        counts = Counter(f.category for f in fixtures)

        self.assertEqual(counts["simple_selection"], 3)
        self.assertEqual(counts["unknown"], 3)
        self.assertEqual(counts["ambiguous"], 3)
        self.assertEqual(counts["relational"], 4)
        self.assertEqual(counts["negation_contrast"], 3)
        self.assertEqual(counts["distractors"], 3)
        self.assertEqual(counts["multi_reference"], 2)
        self.assertEqual(counts["deterministic_bypass"], 3)

    def test_deterministic_fixtures_resolve_via_bypass(self):
        fixtures = get_rar_diagnostic_fixtures()
        det_fixtures = [f for f in fixtures if f.category == "deterministic_bypass"]

        self.assertEqual(len(det_fixtures), 3)
        for f in det_fixtures:
            res = resolve_rar_deterministically(f.query)
            self.assertIsNotNone(res, f"Fixture {f.id} should resolve deterministically")
            self.assertEqual(res.outcome, f.expected_outcome)
            self.assertEqual(res.candidate_id, f.expected_candidate_id)
            self.assertEqual(res.basis, RARBasis.DETERMINISTIC_ANCHOR)

    def test_model_fixtures_do_not_falsely_bypass(self):
        fixtures = get_rar_diagnostic_fixtures()
        model_fixtures = [f for f in fixtures if f.category != "deterministic_bypass"]

        for f in model_fixtures:
            res = resolve_rar_deterministically(f.query)
            self.assertIsNone(
                res,
                f"Fixture {f.id} ({f.category}) should not resolve deterministically; requires model path",
            )


if __name__ == "__main__":
    unittest.main()
