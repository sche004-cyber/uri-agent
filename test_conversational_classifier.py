"""Design/test pass: deterministic "no capability required"
classification for genuinely conversational requests.

Positive fixtures prove clear conversational cases are recognized.
Negative fixtures prove genuine capability gaps - including ones that
happen to share a semantic-safety-gate signal (empty entities, no
evidence/clarification needed) with the positive cases - are never
misclassified. The negative "optimize my pc" fixtures are taken
verbatim from test_capability_planner.py's own regression fixtures, so
this file is directly checked against the exact shapes that module
already treats as genuine capability gaps.
"""

import unittest

from uri_core.core.conversational_classifier import (
    NO_CAPABILITY_REQUIRED_MESSAGE,
    is_conversational_no_capability_required,
)


class PositiveConversationalCasesTests(unittest.TestCase):
    """Clearly conversational requests - no concrete target, no
    evidence/clarification need, and the raw text reads as a greeting,
    farewell, thanks, or a bare question about URI itself."""

    def _semantic(self, **overrides):
        base = {
            "entities": [],
            "requires_evidence": False,
            "requires_clarification": False,
        }
        base.update(overrides)
        return base

    def test_hello_uri(self):
        self.assertTrue(
            is_conversational_no_capability_required(
                "hello URI", self._semantic()
            )
        )

    def test_bare_hi(self):
        self.assertTrue(
            is_conversational_no_capability_required("hi", self._semantic())
        )

    def test_good_morning(self):
        self.assertTrue(
            is_conversational_no_capability_required(
                "good morning", self._semantic()
            )
        )

    def test_thanks(self):
        self.assertTrue(
            is_conversational_no_capability_required(
                "thanks!", self._semantic()
            )
        )

    def test_thank_you_with_punctuation(self):
        self.assertTrue(
            is_conversational_no_capability_required(
                "Thank you.", self._semantic()
            )
        )

    def test_what_can_you_do(self):
        self.assertTrue(
            is_conversational_no_capability_required(
                "what can you do?", self._semantic()
            )
        )

    def test_who_are_you(self):
        self.assertTrue(
            is_conversational_no_capability_required(
                "Who are you?", self._semantic()
            )
        )

    def test_real_model_style_capability_inquiry_fixture(self):
        # The actual semantic_result shape observed from a real model
        # run for "what can you do?" (see the LAN/manual verification
        # log for Prototype 2) - requested_output is non-empty
        # ("Explanation of the system's capabilities and limitations.")
        # and must not be required to be empty for this to classify
        # correctly.
        semantic_result = {
            "goal": "Understand the user's intent and capabilities of the system.",
            "task_type": "Information gathering",
            "domain": "General inquiry",
            "entities": [],
            "requested_output": "Explanation of the system's capabilities and limitations.",
            "requires_evidence": False,
            "requires_clarification": False,
            "suggested_next_step": "Provide a clear overview of the system's functions and constraints.",
        }
        self.assertTrue(
            is_conversational_no_capability_required(
                "what can you do?", semantic_result
            )
        )

    def test_goodbye(self):
        self.assertTrue(
            is_conversational_no_capability_required(
                "bye", self._semantic()
            )
        )

    def test_message_is_never_generated_it_is_a_fixed_constant(self):
        # No new model-authority surface: the reply text is a fixed
        # string, not something this module (or a model) generates.
        self.assertIsInstance(NO_CAPABILITY_REQUIRED_MESSAGE, str)
        self.assertGreater(len(NO_CAPABILITY_REQUIRED_MESSAGE), 0)


class NegativeGenuineCapabilityGapTests(unittest.TestCase):
    """Genuine capability gaps must never be reclassified as
    conversational, including the tricky edge cases where
    requested_output/entities happen to be empty too."""

    def test_optimize_my_pc_with_empty_requested_output_and_entities(self):
        # Verbatim shape from
        # test_capability_planner.py::test_no_confident_match_includes_known_gaps
        # - requires_evidence/requires_clarification are ABSENT
        # entirely (not False), which must fail closed.
        semantic_result = {
            "task_type": "something unrelated",
            "domain": "",
            "goal": "optimize my pc",
            "requested_output": "",
            "entities": [],
        }
        self.assertFalse(
            is_conversational_no_capability_required(
                "optimize my pc", semantic_result
            )
        )

    def test_optimize_my_pc_with_concrete_entities(self):
        # Verbatim shape from
        # test_capability_planner.py::test_pc_optimization_request_is_never_selected
        semantic_result = {
            "task_type": "system optimization",
            "domain": "pc performance",
            "goal": "optimize my pc, clean up disk and check temperature",
            "requested_output": "pc optimization",
            "entities": ["cpu", "gpu", "ram", "temperature"],
        }
        self.assertFalse(
            is_conversational_no_capability_required(
                "optimize my pc, clean up disk and check temperature",
                semantic_result,
            )
        )

    def test_optimize_my_pc_even_if_the_gate_fields_were_satisfied(self):
        # Belt-and-suspenders: even granting the semantic safety gate
        # (which real fixtures above never actually satisfy), the raw
        # text itself does not match any conversational pattern, so
        # this must still be False.
        semantic_result = {
            "task_type": "system optimization",
            "domain": "pc performance",
            "goal": "optimize my pc",
            "requested_output": "",
            "entities": [],
            "requires_evidence": False,
            "requires_clarification": False,
        }
        self.assertFalse(
            is_conversational_no_capability_required(
                "optimize my pc", semantic_result
            )
        )

    def test_analyze_unsupported_task(self):
        semantic_result = {
            "task_type": "analysis",
            "domain": "",
            "goal": "analyze this unsupported task",
            "requested_output": "",
            "entities": [],
            "requires_evidence": False,
            "requires_clarification": False,
        }
        self.assertFalse(
            is_conversational_no_capability_required(
                "analyze this unsupported task", semantic_result
            )
        )

    def test_concrete_task_with_no_registered_capability(self):
        semantic_result = {
            "task_type": "unknown",
            "domain": "",
            "goal": "perform a concrete task for which no registered capability exists",
            "requested_output": "",
            "entities": [],
            "requires_evidence": False,
            "requires_clarification": False,
        }
        self.assertFalse(
            is_conversational_no_capability_required(
                "perform a concrete task for which no registered "
                "capability exists",
                semantic_result,
            )
        )

    def test_greeting_prefix_followed_by_a_real_request_is_not_conversational(
        self,
    ):
        # "hi" alone is conversational, but this is not just "hi" - the
        # whole-message match must not fire on a prefix.
        semantic_result = {
            "task_type": "system optimization",
            "domain": "pc performance",
            "goal": "optimize my pc",
            "requested_output": "",
            "entities": ["pc"],
            "requires_evidence": False,
            "requires_clarification": False,
        }
        self.assertFalse(
            is_conversational_no_capability_required(
                "hi, can you also optimize my pc", semantic_result
            )
        )

    def test_self_referential_question_about_a_concrete_task_stays_a_gap(
        self,
    ):
        # "what can you do" appears, but this names a concrete target
        # (entities non-empty) - the safety gate must block it.
        semantic_result = {
            "task_type": "system optimization",
            "domain": "pc performance",
            "goal": "optimize my pc",
            "requested_output": "",
            "entities": ["pc"],
            "requires_evidence": False,
            "requires_clarification": False,
        }
        self.assertFalse(
            is_conversational_no_capability_required(
                "what can you do to optimize my pc", semantic_result
            )
        )

    def test_requires_evidence_true_blocks_classification_even_with_greeting_text(
        self,
    ):
        semantic_result = {
            "entities": [],
            "requires_evidence": True,
            "requires_clarification": False,
        }
        self.assertFalse(
            is_conversational_no_capability_required("hello", semantic_result)
        )

    def test_requires_clarification_true_blocks_classification(self):
        semantic_result = {
            "entities": [],
            "requires_evidence": False,
            "requires_clarification": True,
        }
        self.assertFalse(
            is_conversational_no_capability_required("hello", semantic_result)
        )

    def test_missing_requires_evidence_key_fails_closed(self):
        # Absent key -> None -> must not satisfy "is False".
        semantic_result = {
            "entities": [],
            "requires_clarification": False,
        }
        self.assertFalse(
            is_conversational_no_capability_required("hello", semantic_result)
        )

    def test_non_empty_entities_blocks_classification_even_with_greeting_text(
        self,
    ):
        semantic_result = {
            "entities": ["something"],
            "requires_evidence": False,
            "requires_clarification": False,
        }
        self.assertFalse(
            is_conversational_no_capability_required("hello", semantic_result)
        )

    def test_none_semantic_result_is_safe(self):
        self.assertFalse(
            is_conversational_no_capability_required("hello", None)
        )

    def test_empty_user_text_is_never_conversational(self):
        semantic_result = {
            "entities": [],
            "requires_evidence": False,
            "requires_clarification": False,
        }
        self.assertFalse(
            is_conversational_no_capability_required("", semantic_result)
        )

    def test_known_supported_capability_request_is_unaffected(self):
        # A real, registered-capability-shaped request must not match
        # the conversational patterns at all.
        semantic_result = {
            "task_type": "document drafting",
            "domain": "administrative",
            "goal": "prepare a note",
            "requested_output": "office note",
            "entities": ["office note"],
            "requires_evidence": False,
            "requires_clarification": False,
        }
        self.assertFalse(
            is_conversational_no_capability_required(
                "please draft an office note about the meeting",
                semantic_result,
            )
        )


if __name__ == "__main__":
    unittest.main()
