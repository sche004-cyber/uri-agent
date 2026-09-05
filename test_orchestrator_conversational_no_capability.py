"""Orchestrator-level integration tests for the deterministic "no
capability required" path (see conversational_classifier.py).

Mirrors test_orchestrator_workflow.py's own setUp discipline exactly:
only semantic_interpreter/skill_memory/capability_planner are mocked -
workflow_planner, workflow executor construction, approval_gate, and
dispatcher are all real. This matters for the negative tests: if the
classifier ever misfired and let a genuine capability gap through, the
real generic workflow would actually run and correctly produce a
"failed" execution status, so a wrong classifier fails these tests
loudly rather than being silently masked by a mock.
"""

import unittest
from unittest.mock import MagicMock

from uri_core.core.conversational_classifier import (
    NO_CAPABILITY_REQUIRED_MESSAGE,
)
from uri_core.core.orchestrator import UriOrchestrator


class ConversationalNoCapabilityRequiredTests(unittest.TestCase):

    def setUp(self):
        self.orchestrator = UriOrchestrator()
        self.orchestrator.semantic_interpreter = MagicMock()
        self.orchestrator.skill_memory = MagicMock()
        self.orchestrator.skill_memory.find_matching_skill.return_value = None
        self.orchestrator.capability_planner = MagicMock()

    def _set_planning_required(self, semantic_result, known_gaps=None):
        self.orchestrator.semantic_interpreter.interpret.return_value = (
            semantic_result
        )
        self.orchestrator.capability_planner.plan.return_value = {
            "status": "planning_required",
            "tool_name": None,
            "known_gaps": known_gaps or [],
        }

    def test_greeting_succeeds_without_a_capability_gap_message(self):
        self._set_planning_required(
            {
                "goal": "Greet URI",
                "task_type": "greeting",
                "domain": "",
                "entities": [],
                "requested_output": "",
                "requires_evidence": False,
                "requires_clarification": False,
            }
        )

        result = self.orchestrator.process_user_input(
            session_id="test-session", user_text="hello URI"
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["execution"]["status"], "success")
        self.assertEqual(
            result["response"]["message"], NO_CAPABILITY_REQUIRED_MESSAGE
        )
        # Never built - proves workflow_planner/workflow_executor were
        # never reached for this request.
        self.assertIsNone(result["workflow"])

    def test_thanks_succeeds(self):
        self._set_planning_required(
            {
                "goal": "Acknowledge URI's help",
                "task_type": "acknowledgement",
                "domain": "",
                "entities": [],
                "requested_output": "",
                "requires_evidence": False,
                "requires_clarification": False,
            }
        )

        result = self.orchestrator.process_user_input(
            session_id="test-session", user_text="thanks!"
        )

        self.assertEqual(result["execution"]["status"], "success")
        self.assertIsNone(result["workflow"])

    def test_self_referential_capability_question_succeeds(self):
        # The real semantic_result shape observed for "what can you
        # do?" against a live model (see the LAN/manual verification
        # log) - requested_output is non-empty and must not be
        # required to be empty.
        self._set_planning_required(
            {
                "goal": "Understand the user's intent and capabilities of the system.",
                "task_type": "Information gathering",
                "domain": "General inquiry",
                "entities": [],
                "requested_output": "Explanation of the system's capabilities and limitations.",
                "requires_evidence": False,
                "requires_clarification": False,
                "suggested_next_step": "Provide a clear overview of the system's functions and constraints.",
            }
        )

        result = self.orchestrator.process_user_input(
            session_id="test-session", user_text="what can you do?"
        )

        self.assertEqual(result["execution"]["status"], "success")
        self.assertIsNone(result["workflow"])

    def test_genuine_capability_gap_still_fails_honestly(self):
        # "optimize my pc" - real capability-gap fixture, verbatim from
        # test_capability_planner.py's own regression tests. The
        # classifier must not intercept this: it falls through to the
        # REAL generic workflow (nothing is mocked here) and must still
        # produce the same honest capability-gap failure as before this
        # change.
        self._set_planning_required(
            {
                "task_type": "something unrelated",
                "domain": "",
                "goal": "optimize my pc",
                "requested_output": "",
                "entities": [],
            },
            known_gaps=[
                {
                    "id": "pc_system_optimization",
                    "description": "Not implemented.",
                    "status": "planned",
                    "limitations": "No adapter exists.",
                    "reason": "not_implemented",
                }
            ],
        )

        result = self.orchestrator.process_user_input(
            session_id="test-session", user_text="optimize my pc"
        )

        self.assertIsNotNone(result["workflow"])
        self.assertEqual(result["execution"]["status"], "failed")
        self.assertIn(
            "does not have an implemented capability",
            result["execution"]["error"],
        )

    def test_concrete_task_with_entities_still_fails_honestly(self):
        self._set_planning_required(
            {
                "task_type": "system optimization",
                "domain": "pc performance",
                "goal": "optimize my pc, clean up disk and check temperature",
                "requested_output": "pc optimization",
                "entities": ["cpu", "gpu", "ram", "temperature"],
                "requires_evidence": False,
                "requires_clarification": False,
            }
        )

        result = self.orchestrator.process_user_input(
            session_id="test-session",
            user_text="optimize my pc, clean up disk and check temperature",
        )

        self.assertIsNotNone(result["workflow"])
        self.assertEqual(result["execution"]["status"], "failed")

    def test_greeting_prefix_before_a_real_request_still_fails_honestly(self):
        # "hi, can you also optimize my pc" - the whole-message greeting
        # pattern must not fire on a prefix, so this must still be
        # treated as a genuine (if unsupported) task.
        self._set_planning_required(
            {
                "task_type": "system optimization",
                "domain": "pc performance",
                "goal": "optimize my pc",
                "requested_output": "",
                "entities": ["pc"],
                "requires_evidence": False,
                "requires_clarification": False,
            }
        )

        result = self.orchestrator.process_user_input(
            session_id="test-session",
            user_text="hi, can you also optimize my pc",
        )

        self.assertIsNotNone(result["workflow"])
        self.assertEqual(result["execution"]["status"], "failed")

    def test_known_supported_capability_is_still_selected_normally(self):
        # capability_selected is a completely separate branch from the
        # one this change touches - proves the new check cannot
        # possibly intercept a real, registered-capability request.
        self.orchestrator.semantic_interpreter.interpret.return_value = {
            "goal": "Draft an office note",
            "task_type": "document drafting",
            "domain": "administrative",
            "requested_output": "office note",
            "entities": [],
            "requires_evidence": False,
            "requires_clarification": False,
        }
        self.orchestrator.capability_planner.plan.return_value = {
            "status": "capability_selected",
            "tool_name": "draft_institutional_note",
        }
        self.orchestrator.dispatcher.execute_tool = MagicMock(
            return_value={
                "status": "success",
                "data": {"draft": "Office note generated."},
            }
        )
        self.orchestrator.skill_memory.learn_skill = MagicMock()

        result = self.orchestrator.process_user_input(
            session_id="test-session", user_text="Draft an office note."
        )

        self.assertEqual(result["execution"]["tool"], "draft_institutional_note")
        self.assertEqual(result["response"]["draft"], "Office note generated.")

    def test_conversational_path_never_calls_approval_gate_execute_tool(self):
        # No capability, no dispatch, no approval - a greeting must
        # never reach the one execution boundary in this codebase.
        self.orchestrator.approval_gate.execute_tool = MagicMock(
            side_effect=AssertionError(
                "approval_gate.execute_tool must never be called for a "
                "conversational, no-capability-required request"
            )
        )

        self._set_planning_required(
            {
                "goal": "Greet URI",
                "task_type": "greeting",
                "domain": "",
                "entities": [],
                "requested_output": "",
                "requires_evidence": False,
                "requires_clarification": False,
            }
        )

        result = self.orchestrator.process_user_input(
            session_id="test-session", user_text="hello URI"
        )

        self.assertEqual(result["execution"]["status"], "success")
        self.orchestrator.approval_gate.execute_tool.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
