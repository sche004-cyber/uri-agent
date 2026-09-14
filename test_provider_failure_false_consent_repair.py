"""M30-PFC regression tests for the provider-failure learned-skill gate.

These tests keep the production collaborators real where it matters (the
orchestrator and SkillMemory matching logic) and use narrow spies for the
otherwise-dangerous memory execution boundary.
"""

import json
import os
import tempfile
import unittest

from uri_core.core.model_router import AllProvidersUnreachableError
from uri_core.core.orchestrator import UriOrchestrator
from uri_core.core.skill_memory import SkillMemory
from uri_core.core.state import SessionManager


HEALTHY_DISCLOSURE = {
    "goal": "I work at NIT Sikkim.",
    "task_type": "personal information disclosure",
    "domain": "personal profile",
    "entities": ["NIT Sikkim"],
    "requested_output": "save this fact about the user",
    "requires_evidence": False,
    "requires_clarification": False,
    "suggested_next_step": "Save the stated fact.",
}


class _TerminallyUnavailableInterpreter:
    def interpret(self, user_text):
        try:
            raise AllProvidersUnreachableError("all providers exhausted")
        except AllProvidersUnreachableError as exc:
            raise ValueError("Semantic interpreter unavailable") from exc


class _MalformedInterpreter:
    def interpret(self, user_text):
        raise ValueError("Model response is not valid JSON")


class _FixedInterpreter:
    def __init__(self, result):
        self.result = result

    def interpret(self, user_text):
        return dict(self.result)


class _SkillMemoryMatch:
    def __init__(self, task_type="personal information disclosure", tool_name="remember_fact"):
        self.match = {
            "task_type": task_type,
            "domain": "personal profile",
            "tool_name": tool_name,
            "success_count": 8,
        }

    def find_matching_skill(self, semantic_result):
        return dict(self.match)

    def learn_skill(self, semantic_result, workflow, tool_name=None):
        pass


class _MemoryStoreSpy:
    def __init__(self):
        self.add_calls = []

    def add(self, **kwargs):
        self.add_calls.append(kwargs)


class _ApprovalGateSpy:
    def __init__(self, memory_store):
        self.calls = []
        self.memory_store = memory_store

    def execute_tool(self, tool_name, **kwargs):
        self.calls.append((tool_name, kwargs))
        if tool_name == "remember_fact":
            self.memory_store.add(
                category="explicit_statement",
                content=kwargs["request_text"],
            )
        return {"status": "success", "data": {"status": "success"}}


class ProviderFailureFalseConsentRepairTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.memory_store = _MemoryStoreSpy()
        self.approval_gate = _ApprovalGateSpy(self.memory_store)

    def _orchestrator(self, interpreter, skill_memory, *, reasoning=True):
        orchestrator = UriOrchestrator(
            semantic_interpreter=interpreter,
            enable_model_reasoning_shadow=reasoning,
            enable_skill_router_shadow=False,
            enable_response_narrative=False,
            session_manager=SessionManager(
                storage_path=os.path.join(self.temp_dir.name, "sessions")
            ),
        )
        orchestrator.skill_memory = skill_memory
        orchestrator.approval_gate = self.approval_gate
        return orchestrator

    def test_unreachable_provider_cannot_execute_remember_fact(self):
        result = self._orchestrator(
            _TerminallyUnavailableInterpreter(), _SkillMemoryMatch(),
            reasoning=False,
        ).process_user_input("s1", "What is the weather in Delhi today?")

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["execution"]["status"], "unavailable")
        self.assertEqual(result["plan"]["status"], "model_unavailable")
        self.assertEqual(self.approval_gate.calls, [])

    def test_terminal_failure_has_no_memory_side_effect(self):
        self._orchestrator(
            _TerminallyUnavailableInterpreter(), _SkillMemoryMatch(),
            reasoning=False,
        ).process_user_input("s1", "What is the weather in Delhi today?")

        self.assertEqual(self.memory_store.add_calls, [])

    def test_terminal_failure_creates_no_user_provided_provenance(self):
        self._orchestrator(
            _TerminallyUnavailableInterpreter(), _SkillMemoryMatch(),
            reasoning=False,
        ).process_user_input("s1", "What is the weather in Delhi today?")

        self.assertFalse(self.memory_store.add_calls)

    def test_empty_task_type_and_domain_never_match_a_skill(self):
        path = os.path.join(self.temp_dir.name, "skill_memory.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"skills": [{
                "task_type": "",
                "domain": "",
                "tool_name": "remember_fact",
                "success_count": 5,
                "failure_count": 0,
            }]}, handle)

        self.assertIsNone(SkillMemory(storage_path=path).find_matching_skill({
            "task_type": "", "domain": "",
        }))

    def test_confident_nonempty_match_cannot_bypass_terminal_failure(self):
        result = self._orchestrator(
            _TerminallyUnavailableInterpreter(),
            _SkillMemoryMatch(task_type="weather lookup"),
            reasoning=False,
        ).process_user_input("s1", "What is the weather in Delhi today?")

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(self.approval_gate.calls, [])

    def test_healthy_explicit_disclosure_still_executes_remember_fact(self):
        result = self._orchestrator(
            _FixedInterpreter(HEALTHY_DISCLOSURE), _SkillMemoryMatch(),
            reasoning=False,
        ).process_user_input("s1", "I work at NIT Sikkim.")

        self.assertEqual(result["execution"]["status"], "success")
        self.assertEqual(self.approval_gate.calls[0][0], "remember_fact")
        self.assertEqual(self.memory_store.add_calls[0]["content"], "I work at NIT Sikkim.")

    def test_reached_but_malformed_response_does_not_set_unavailable_marker(self):
        result = self._orchestrator(
            _MalformedInterpreter(), _SkillMemoryMatch(), reasoning=False,
        ).process_user_input("s1", "draft a note")

        self.assertNotIn("interpretation_unreachable", result["semantic_analysis"])
        self.assertEqual(result["execution"]["status"], "success")

    def test_reasoning_terminal_failure_also_gates_learned_execution(self):
        orchestrator = self._orchestrator(
            _FixedInterpreter(HEALTHY_DISCLOSURE), _SkillMemoryMatch(),
            reasoning=False,
        )
        orchestrator._run_model_reasoning = lambda **kwargs: {
            "status": "reasoning_failed",
            "error": "All providers exhausted for role 'reasoning'.",
        }

        result = orchestrator.process_user_input("s1", "I work at NIT Sikkim.")

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(self.approval_gate.calls, [])

    def test_terminal_failure_blocks_approval_and_side_effecting_capability_execution(self):
        # When MODEL_TERMINALLY_UNAVAILABLE is reached, prove that URI blocks not only
        # learned-skill/remember_fact execution, but also approval execution and any
        # other side-effecting capability execution. The deterministic model-unavailable
        # response should be returned instead.
        result = self._orchestrator(
            _TerminallyUnavailableInterpreter(),
            _SkillMemoryMatch(task_type="email management", tool_name="create_draft"),
            reasoning=False,
        ).process_user_input("s1", "Draft an email to professor about project meeting")

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["execution"]["status"], "unavailable")
        self.assertEqual(result["plan"]["status"], "model_unavailable")
        self.assertIsNone(result["execution"]["tool"])
        self.assertEqual(self.approval_gate.calls, [])
        self.assertIn("could not reach its model provider", result["response"]["message"])


if __name__ == "__main__":
    unittest.main()
