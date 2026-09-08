"""M20 (W5): a bounded, single-round research capability (web_search/
fetch_url) usable within the existing Brain re-evaluation loop when no
other registered capability can satisfy the request - and never more
than once per turn, enforced deterministically by the runtime, not
only by the prompt clause that asks the Brain for restraint.

No network/Ollama involved - every gateway here is driven by a fake,
in-process model_callable keyed by attempt_history length, mirroring
test_orchestrator_brain_reevaluation.py's own discipline. web_search/
fetch_url themselves are stubbed via a fake dispatcher - no real
Tavily/HTTP call happens in this file.
"""

import json
import os
import tempfile
import unittest

from uri_core.core.model_reasoning_gateway import ModelReasoningGateway
from uri_core.core.orchestrator import UriOrchestrator
from uri_core.core.skill_memory import SkillMemory
from uri_core.core.state import SessionManager


class _FixedSemanticInterpreter:
    def __init__(self, result: dict):
        self._result = result

    def interpret(self, user_text: str) -> dict:
        return self._result


class _FakeDispatcher:
    def __init__(self, results_by_capability=None):
        self.calls = []
        self._results_by_capability = results_by_capability or {}

    def execute_tool(self, tool_name, **kwargs):
        self.calls.append((tool_name, kwargs))
        if tool_name in self._results_by_capability:
            return self._results_by_capability[tool_name]
        return {"status": "success", "data": {"tool": tool_name}}


def _by_attempt_count(responses_by_count):
    def _call(request_json):
        request = json.loads(request_json)
        count = len(request.get("attempt_history", []))
        payload = responses_by_count.get(
            count, responses_by_count.get("default", {})
        )
        return json.dumps(payload)

    return _call


NOTE_SEMANTIC_RESULT = {
    "goal": "Find out about a public policy change",
    "task_type": "information retrieval",
    "domain": "general",
    "requested_output": "an answer",
    "entities": [],
}


class _IsolatedOrchestratorCase(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

    def _orchestrator(self, model_reasoning_gateway=None, **kwargs):
        orchestrator = UriOrchestrator(
            semantic_interpreter=_FixedSemanticInterpreter(
                NOTE_SEMANTIC_RESULT
            ),
            model_reasoning_gateway=model_reasoning_gateway,
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
        orchestrator.capability_planner.plan = lambda sr: {
            "status": "planning_required",
            "tool_name": None,
        }
        return orchestrator


class ResearchProposalExecutesTests(_IsolatedOrchestratorCase):
    """A capability gap -> the Brain proposes web_search during
    recovery -> results land in attempt_history -> the Brain
    reassesses and is satisfied."""

    def test_research_result_reaches_attempt_history_and_satisfies(self):
        gateway = ModelReasoningGateway(
            model_callable=_by_attempt_count(
                {
                    # Initial call: nothing registered can help
                    # directly; the Brain proposes web_search.
                    0: {"action": {"capability": "web_search"}},
                    # Recovery call: evaluates the real search result
                    # and is satisfied.
                    1: {
                        "evaluation": {
                            "satisfied": True,
                            "reason": "The search result answers the question.",
                        }
                    },
                }
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        dispatcher = _FakeDispatcher(
            {
                "web_search": {
                    "status": "success",
                    "data": {"results": [{"title": "Policy change explained"}]},
                }
            }
        )
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="what changed in the new policy?"
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["execution"]["tool"], "web_search")
        self.assertTrue(result["brain_evaluation"]["satisfied"])
        self.assertTrue(result["research_attempted"])
        self.assertEqual(dispatcher.calls[0][0], "web_search")

    def test_no_research_no_research_attempted_flag(self):
        """An ordinary satisfied turn with no research involved leaves
        research_attempted False - the field must not default to
        True or be absent."""

        gateway = ModelReasoningGateway(
            model_callable=_by_attempt_count(
                {
                    0: {"action": {"capability": "extract_student_records"}},
                    1: {
                        "evaluation": {
                            "satisfied": True,
                            "reason": "The record answers the request.",
                        }
                    },
                }
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="look up the record"
        )

        self.assertIn("research_attempted", result)
        self.assertFalse(result["research_attempted"])


class ResearchBudgetBoundedTests(_IsolatedOrchestratorCase):
    """Research is never proposed/executed more than once per turn,
    even if the Brain itself proposes it again - the runtime enforces
    this deterministically, not only via the prompt."""

    def test_second_research_proposal_is_not_executed(self):
        gateway = ModelReasoningGateway(
            model_callable=_by_attempt_count(
                {
                    0: {"action": {"capability": "web_search"}},
                    # Recovery call 1: not satisfied, proposes
                    # web_search AGAIN - the runtime must refuse this.
                    1: {
                        "evaluation": {
                            "satisfied": False,
                            "reason": "The first search wasn't enough.",
                        },
                        "action": {"capability": "web_search"},
                    },
                    # Would only be reached if the runtime incorrectly
                    # executed the second research proposal.
                    2: {
                        "evaluation": {
                            "satisfied": True,
                            "reason": "Should never be reached.",
                        }
                    },
                }
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        dispatcher = _FakeDispatcher(
            {
                "web_search": {
                    "status": "success",
                    "data": {"results": []},
                }
            }
        )
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="what changed in the new policy?"
        )

        # Only ONE dispatch ever happened - the second web_search
        # proposal was refused before execution.
        self.assertEqual(len(dispatcher.calls), 1)
        self.assertEqual(dispatcher.calls[0][0], "web_search")

        self.assertFalse(result["brain_evaluation"]["satisfied"])
        self.assertEqual(
            result["brain_evaluation"]["status"], "research_budget_exhausted"
        )
        self.assertTrue(result["research_attempted"])


class ResearchNeverInstallsOrExecutesSkillsTests(_IsolatedOrchestratorCase):
    """Research recovery only ever proposes already-registered
    capabilities (web_search/fetch_url) through the exact same
    ApprovalGate-gated path as any other proposal - it never touches
    SkillInstaller or writes to the capability registry."""

    def test_research_never_calls_skill_installer(self):
        import uri_core.skills.skill_installer as skill_installer_module

        install_calls = []
        original_install = skill_installer_module.SkillInstaller.install_from_path

        def _tracking_install(self, *args, **kwargs):
            install_calls.append((args, kwargs))
            return original_install(self, *args, **kwargs)

        skill_installer_module.SkillInstaller.install_from_path = _tracking_install
        self.addCleanup(
            setattr,
            skill_installer_module.SkillInstaller,
            "install_from_path",
            original_install,
        )

        gateway = ModelReasoningGateway(
            model_callable=_by_attempt_count(
                {
                    0: {"action": {"capability": "web_search"}},
                    1: {
                        "evaluation": {
                            "satisfied": True,
                            "reason": "Good enough.",
                        }
                    },
                }
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        dispatcher = _FakeDispatcher(
            {"web_search": {"status": "success", "data": {"results": []}}}
        )
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        orchestrator.process_user_input(
            session_id="s1", user_text="what changed in the new policy?"
        )

        self.assertEqual(install_calls, [])


if __name__ == "__main__":
    unittest.main()
