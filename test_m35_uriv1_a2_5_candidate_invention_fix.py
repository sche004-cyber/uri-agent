"""Regression tests for Batch A2.5: Candidate-Invention Defect Correction.

Verifies that:
1. Valid target_ids matching ActiveContext artifacts or entities resolve properly.
2. Invented / hallucinated target_ids not present in ActiveContext are NEVER marked resolved.
3. When active_context is None, any returned target_id is treated as unresolved.
4. Unresolved references generate ContextDependency objects; resolved ones do not.
5. Mixed turns with both valid and invented target_ids correctly discriminate between them.
"""

from __future__ import annotations

import unittest

from uri_v1.turn.active_context import ActiveContext, ArtifactDescriptor, EntityDescriptor
from uri_v1.turn.contracts import (
    ContextDependencyCategory,
    DecodedRequest,
)
from uri_v1.turn.decoder import DecodeInput
from uri_v1.turn.local_semantic_wire import normalize_qwen14b_wire


class CandidateInventionFixTests(unittest.TestCase):
    """Verifies that normalize_qwen14b_wire rejects invented target_ids."""

    def setUp(self):
        self.art = ArtifactDescriptor(
            id="art_valid_1",
            name="Quarterly_Report_Q3.pdf",
            artifact_type="document",
        )
        self.ent = EntityDescriptor(
            id="ent_valid_1",
            name="Registrar Office",
            category="organization",
        )
        self.active_context = ActiveContext(
            active_artifacts=(self.art,),
            active_entities=(self.ent,),
        )

    def test_valid_artifact_id_resolves(self):
        wire = {
            "goal": "Review the quarterly report",
            "intent_family": "analyze",
            "requested_operations": ["review"],
            "references": [{"expression": "the report", "target_id": "art_valid_1"}],
        }
        inp = DecodeInput.from_text("Review the report")
        decoded = normalize_qwen14b_wire(wire, inp, active_context=self.active_context)

        self.assertEqual(len(decoded.references), 1)
        ref = decoded.references[0]
        self.assertEqual(ref.expression, "the report")
        self.assertTrue(ref.is_resolved)
        self.assertEqual(ref.referent_hint, "Quarterly_Report_Q3.pdf")
        self.assertEqual(len(decoded.dependencies), 0)

    def test_valid_entity_id_resolves(self):
        wire = {
            "goal": "Notify the registrar",
            "intent_family": "communicate",
            "requested_operations": ["notify"],
            "references": [{"expression": "them", "target_id": "ent_valid_1"}],
        }
        inp = DecodeInput.from_text("Notify them")
        decoded = normalize_qwen14b_wire(wire, inp, active_context=self.active_context)

        self.assertEqual(len(decoded.references), 1)
        ref = decoded.references[0]
        self.assertEqual(ref.expression, "them")
        self.assertTrue(ref.is_resolved)
        self.assertEqual(ref.referent_hint, "Registrar Office")
        self.assertEqual(len(decoded.dependencies), 0)

    def test_invented_target_id_is_never_marked_resolved(self):
        """CRITICAL: An invented ID like 'doc_9999_hallucinated' must NOT be marked resolved."""
        wire = {
            "goal": "Open the secret memo",
            "intent_family": "retrieve",
            "requested_operations": ["open"],
            "references": [{"expression": "secret memo", "target_id": "doc_9999_hallucinated"}],
        }
        inp = DecodeInput.from_text("Open secret memo")
        decoded = normalize_qwen14b_wire(wire, inp, active_context=self.active_context)

        self.assertEqual(len(decoded.references), 1)
        ref = decoded.references[0]
        self.assertEqual(ref.expression, "secret memo")
        self.assertFalse(ref.is_resolved, "Invented target_id must NOT be marked resolved")
        self.assertIsNone(ref.referent_hint, "Invented target_id must have None referent_hint")

        # Must record unresolved dependency
        self.assertEqual(len(decoded.dependencies), 1)
        dep = decoded.dependencies[0]
        self.assertEqual(dep.category, ContextDependencyCategory.PRIOR_CONTEXT_UNSPECIFIED)
        self.assertEqual(dep.unresolved_reference, "secret memo")

    def test_target_id_with_no_active_context_remains_unresolved(self):
        """When active_context is None, any returned target_id must remain unresolved."""
        wire = {
            "goal": "Send document",
            "intent_family": "communicate",
            "requested_operations": ["send"],
            "references": [{"expression": "it", "target_id": "any_id"}],
        }
        inp = DecodeInput.from_text("Send it")
        decoded = normalize_qwen14b_wire(wire, inp, active_context=None)

        self.assertEqual(len(decoded.references), 1)
        ref = decoded.references[0]
        self.assertFalse(ref.is_resolved)
        self.assertIsNone(ref.referent_hint)
        self.assertEqual(len(decoded.dependencies), 1)

    def test_mixed_valid_and_invented_references(self):
        """Mixed turn: 1 valid artifact, 1 invented artifact, 1 empty target_id."""
        wire = {
            "goal": "Compare the report with the memo and that other thing",
            "intent_family": "analyze",
            "requested_operations": ["compare"],
            "references": [
                {"expression": "the report", "target_id": "art_valid_1"},
                {"expression": "the memo", "target_id": "invented_memo_007"},
                {"expression": "that other thing", "target_id": ""},
            ],
        }
        inp = DecodeInput.from_text("Compare the report with the memo and that other thing")
        decoded = normalize_qwen14b_wire(wire, inp, active_context=self.active_context)

        self.assertEqual(len(decoded.references), 3)

        # 1. Valid artifact
        self.assertEqual(decoded.references[0].expression, "the report")
        self.assertTrue(decoded.references[0].is_resolved)
        self.assertEqual(decoded.references[0].referent_hint, "Quarterly_Report_Q3.pdf")

        # 2. Invented artifact
        self.assertEqual(decoded.references[1].expression, "the memo")
        self.assertFalse(decoded.references[1].is_resolved)
        self.assertIsNone(decoded.references[1].referent_hint)

        # 3. Empty target_id
        self.assertEqual(decoded.references[2].expression, "that other thing")
        self.assertFalse(decoded.references[2].is_resolved)
        self.assertIsNone(decoded.references[2].referent_hint)

        # Dependencies: exactly 2 (for memo and that other thing)
        self.assertEqual(len(decoded.dependencies), 2)
        dep_refs = [d.unresolved_reference for d in decoded.dependencies]
        self.assertIn("the memo", dep_refs)
        self.assertIn("that other thing", dep_refs)


if __name__ == "__main__":
    unittest.main()
