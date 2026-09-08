"""M20 (W9): a semantic interpreter failure (malformed JSON, missing
key, unreachable provider) must degrade the turn honestly, not take
it down entirely.

Before this change, orchestrator.py's process_user_input called
self.semantic_interpreter.interpret(user_text) unguarded - any
exception was caught only by _process_user_input_core's own broad
except at the very bottom, which returns {"status": "failed"} with no
Brain call and no narrative. Every OTHER model call in this pipeline
already degrades safely instead of failing the whole turn; this was
the one that didn't.
"""

import os
import tempfile
import unittest

from uri_core.core.model_reasoning_gateway import ModelReasoningGateway
from uri_core.core.orchestrator import UriOrchestrator
from uri_core.core.skill_memory import SkillMemory
from uri_core.core.state import SessionManager


class _RaisingSemanticInterpreter:
    def interpret(self, user_text: str) -> dict:
        raise ValueError("Semantic interpreter returned incomplete result.")


class _IsolatedOrchestratorCase(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

    def _orchestrator(self, **kwargs):
        orchestrator = UriOrchestrator(
            semantic_interpreter=_RaisingSemanticInterpreter(),
            enable_model_reasoning_shadow=True,
            enable_skill_router_shadow=False,
            enable_response_narrative=False,
            session_manager=SessionManager(
                storage_path=os.path.join(self.temp_dir.name, "sessions")
            ),
            **kwargs,
        )
        orchestrator.skill_memory = SkillMemory(
            storage_path=os.path.join(
                self.temp_dir.name, "skill_memory.json"
            )
        )
        orchestrator.skill_memory.find_matching_skill = (
            lambda semantic_result: None
        )
        return orchestrator


class SemanticInterpreterFailureDegradesHonestlyTests(_IsolatedOrchestratorCase):

    def test_raising_interpreter_does_not_fail_the_whole_turn(self):
        orchestrator = self._orchestrator(model_reasoning_gateway=None)

        result = orchestrator.process_user_input(
            session_id="s1", user_text="look up the record for roll 123"
        )

        self.assertEqual(result["status"], "success")
        self.assertIn("semantic_analysis", result)
        self.assertEqual(
            result["semantic_analysis"]["goal"],
            "look up the record for roll 123",
        )
        self.assertTrue(result["semantic_analysis"]["requires_clarification"])

    def test_brain_still_reasons_with_the_real_user_text(self):
        captured = []

        def _model_callable(request_json):
            captured.append(request_json)
            return '{"action": null}'

        gateway = ModelReasoningGateway(model_callable=_model_callable)
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        orchestrator.process_user_input(
            session_id="s1", user_text="extract the record for roll 123"
        )

        self.assertEqual(len(captured), 1)
        self.assertIn("extract the record for roll 123", captured[0])

    def test_capability_planner_gets_the_degraded_result_without_raising(self):
        orchestrator = self._orchestrator(model_reasoning_gateway=None)

        result = orchestrator.process_user_input(
            session_id="s1", user_text="do something"
        )

        # The deterministic fallback correctly finds nothing confident
        # to select - an honest "planning_required", not a crash.
        self.assertEqual(result["status"], "success")
        self.assertIn(result["plan"]["status"], ("planning_required",))


if __name__ == "__main__":
    unittest.main()
