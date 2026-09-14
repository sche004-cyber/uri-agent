"""2026-09-12 (User-reported live defect): the Brain's very first,
unconstrained reasoning call could decide to ask a clarifying question
even when the deterministic layer had ALREADY fully resolved the
request - the semantic interpreter's own structured contract said
requires_clarification=False, and CapabilityPlanner confidently
selected a real, executable capability. That Brain clarification used
to win unconditionally, silently discarding a correct, ready-to-run
plan (live-verified: "I work at NIT Sikkim" and "how many unread
emails do I have" both got a redundant clarifying question instead of
ever executing anything).

This does NOT touch the original protection this same code path
exists for (test_orchestrator_user_interaction_hooks.py's
"a missing roll number correctly flagged by the Brain" regression) -
that fixture forces CapabilityPlanner to "planning_required", so the
guard added here never applies to it; a genuinely incomplete request
(the interpreter itself reporting requires_clarification=True) still
lets the Brain's clarification through unchanged.

No network/Ollama - a fake in-process model_callable throughout.
"""

import os
import tempfile
import unittest

from uri_core.core.model_reasoning_gateway import ModelReasoningGateway
from uri_core.core.orchestrator import UriOrchestrator
from uri_core.core.skill_memory import SkillMemory
from uri_core.core.experience_store import ExperienceStore
from uri_core.core.state import SessionManager


class _FixedSemanticInterpreter:
    def __init__(self, result: dict):
        self._result = result

    def interpret(self, user_text: str) -> dict:
        return self._result


class _FakeDispatcher:
    def __init__(self, results_by_capability=None):
        self.calls = []
        self._results = results_by_capability or {}

    def execute_tool(self, tool_name, **kwargs):
        self.calls.append((tool_name, kwargs))
        if tool_name in self._results:
            return self._results[tool_name]
        return {"status": "success", "data": {"tool": tool_name}}


def _fixed_response(payload):
    import json

    def _call(request_json):
        return json.dumps(payload)

    return _call


RESOLVED_SEMANTIC_RESULT = {
    "goal": "the user is sharing a fact about themselves: I work at NIT Sikkim",
    "task_type": "personal information disclosure",
    "domain": "personal",
    "entities": [],
    "requested_output": "save this fact about the user to memory",
    "requires_evidence": False,
    "requires_clarification": False,
    "suggested_next_step": "acknowledge the disclosure and proceed",
}

INCOMPLETE_SEMANTIC_RESULT = {
    "goal": "look up a student record",
    "task_type": "data retrieval",
    "domain": "academic records",
    "entities": [],
    "requested_output": "cgpa",
    "requires_evidence": True,
    "requires_clarification": True,
    "suggested_next_step": "ask for the roll number",
}

CONFIDENT_PLAN = {
    "status": "capability_selected",
    "tool_name": "remember_fact",
    "reason": "test fixture",
}

PLANNING_REQUIRED_PLAN = {"status": "planning_required", "tool_name": None}


class _IsolatedOrchestratorCase(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

    def _orchestrator(self, semantic_result, model_reasoning_gateway, plan):
        orchestrator = UriOrchestrator(
            semantic_interpreter=_FixedSemanticInterpreter(semantic_result),
            model_reasoning_gateway=model_reasoning_gateway,
            enable_model_reasoning_shadow=True,
            enable_skill_router_shadow=False,
            enable_response_narrative=False,
            session_manager=SessionManager(
                storage_path=os.path.join(self.temp_dir.name, "sessions")
            ),
        )
        orchestrator.skill_memory = SkillMemory(
            storage_path=os.path.join(self.temp_dir.name, "skill_memory.json")
        )
        orchestrator.skill_memory.find_matching_skill = (
            lambda semantic_result: None
        )
        orchestrator.experience_store = ExperienceStore(
            storage_path=os.path.join(self.temp_dir.name, "experience.json")
        )
        orchestrator.capability_planner.plan = lambda sr: dict(plan)
        return orchestrator


class DeterministicMatchOutranksRedundantClarificationTests(
    _IsolatedOrchestratorCase
):

    def test_confident_complete_match_ignores_the_brains_own_clarification(
        self,
    ):
        # The Brain's first, unconstrained call decides to ask a
        # question even though nothing is actually missing - this must
        # be ignored because the deterministic layer already fully
        # resolved the request.
        gateway = ModelReasoningGateway(
            model_callable=_fixed_response(
                {
                    "clarification": {
                        "question": "Which account is this about?"
                    },
                    "action": None,
                }
            )
        )
        orchestrator = self._orchestrator(
            RESOLVED_SEMANTIC_RESULT, gateway, CONFIDENT_PLAN
        )
        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool
        orchestrator.approval_gate.dispatcher.execute_tool = (
            dispatcher.execute_tool
        )

        result = orchestrator.process_user_input(
            session_id="s1", user_text="I work at NIT Sikkim"
        )

        self.assertNotEqual(result["execution"].get("status"), "waiting_for_input")
        self.assertEqual(dispatcher.calls[0][0], "remember_fact")

    def test_genuinely_incomplete_request_still_lets_the_clarification_through(
        self,
    ):
        # Original regression protection, unchanged: CapabilityPlanner
        # has NOT confidently matched anything (still
        # "planning_required"), so the Brain's clarification must still
        # win, exactly as before this fix.
        gateway = ModelReasoningGateway(
            model_callable=_fixed_response(
                {
                    "clarification": {"question": "Which roll number?"},
                    "action": None,
                }
            )
        )
        orchestrator = self._orchestrator(
            INCOMPLETE_SEMANTIC_RESULT, gateway, PLANNING_REQUIRED_PLAN
        )
        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="look up the student record"
        )

        self.assertEqual(result["execution"]["status"], "waiting_for_input")
        self.assertEqual(dispatcher.calls, [])


if __name__ == "__main__":
    unittest.main()
