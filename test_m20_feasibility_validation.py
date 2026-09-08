"""M20 (W1): proves the Brain<->URI capability-selection boundary now
rejects a currently-UNUSABLE capability before it becomes the real
plan - not just an unregistered one.

Before this milestone, _model_proposed_capability's strict
action.capability path returned ANY string ModelReasoningGateway.
validate_proposal() had accepted as a REGISTERED name - which only
means CapabilityRegistry status == "implemented", not "usable right
now" (see capability_registry.py's own availability field). A Brain
proposal naming an "implemented" but currently-unavailable capability
(e.g. gmail_search with no stored Gmail token, or
fetch_drive_spreadsheet with no service account) was promoted to the
real plan and only failed once actually dispatched. This file proves
that gap is closed for both the single-action and workflow-step paths,
using an isolated, deterministic registry - never the real
uri_workspace/capabilities_registry.json, whose "availability" values
depend on real, machine-specific credential state.

No network/Ollama involved - every gateway here is driven by a fake,
in-process model_callable.
"""

import json
import os
import tempfile
import unittest

from uri_core.core.capability_registry import CapabilityRegistry
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
    def __init__(self):
        self.calls = []

    def execute_tool(self, tool_name, **kwargs):
        self.calls.append((tool_name, kwargs))
        return {"status": "success", "data": {"tool": tool_name}}


NOTE_SEMANTIC_RESULT = {
    "goal": "Search Gmail for a message",
    "task_type": "information retrieval",
    "domain": "email",
    "requested_output": "email search results",
    "entities": [],
}


def _write_registry(path, active_tools):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"active_tools": active_tools}, f)


class _IsolatedOrchestratorCase(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

    def _orchestrator(self, model_reasoning_gateway, capability_registry):
        orchestrator = UriOrchestrator(
            semantic_interpreter=_FixedSemanticInterpreter(
                NOTE_SEMANTIC_RESULT
            ),
            model_reasoning_gateway=model_reasoning_gateway,
            capability_registry=capability_registry,
            enable_model_reasoning_shadow=True,
            enable_skill_router_shadow=False,
            enable_response_narrative=False,
            session_manager=SessionManager(
                storage_path=os.path.join(self.temp_dir.name, "sessions")
            ),
        )
        orchestrator.skill_memory = SkillMemory(
            storage_path=os.path.join(
                self.temp_dir.name, "skill_memory.json"
            )
        )
        orchestrator.skill_memory.find_matching_skill = (
            lambda semantic_result: None
        )
        # An unavailable-capability proposal should genuinely be
        # rejected pre-execution here, not merely deferred to a later
        # Brain re-evaluation round - force Gate B on so the sanity
        # check (which independently re-derives the proposal) doesn't
        # confuse the picture in these tests either way.
        orchestrator._should_run_pre_execution_sanity_check = (
            lambda **kwargs: False
        )
        return orchestrator


class UnavailableCapabilityIsNotPromotedTests(_IsolatedOrchestratorCase):

    def test_strict_single_action_proposal_for_unavailable_capability_falls_back(
        self,
    ):
        registry_path = os.path.join(
            self.temp_dir.name, "capabilities_registry.json"
        )
        _write_registry(
            registry_path,
            {
                "gmail_search": {
                    "file_path": "x.py",
                    "class_name": "X",
                    "method": "run",
                    "status": "implemented",
                    "availability": "unavailable_missing_dependency",
                }
            },
        )
        registry = CapabilityRegistry(registry_path=registry_path)

        gateway = ModelReasoningGateway(
            registry_path=registry_path,
            model_callable=lambda request_json: json.dumps(
                {"action": {"capability": "gmail_search"}}
            ),
        )
        orchestrator = self._orchestrator(gateway, registry)

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="search my gmail"
        )

        # The unavailable capability was never dispatched - the
        # deterministic CapabilityPlanner fallback ran instead (and
        # found nothing confident either, since this registry only
        # declares gmail_search).
        self.assertEqual(dispatcher.calls, [])
        self.assertNotEqual(result.get("plan", {}).get("source"), "model_reasoning")

    def test_available_capability_is_still_promoted_normally(self):
        """Regression guard: the feasibility check must not become
        MORE restrictive than is_executable for a genuinely usable
        capability."""

        registry_path = os.path.join(
            self.temp_dir.name, "capabilities_registry.json"
        )
        _write_registry(
            registry_path,
            {
                "gmail_search": {
                    "file_path": "x.py",
                    "class_name": "X",
                    "method": "run",
                    "status": "implemented",
                    "availability": "available",
                }
            },
        )
        registry = CapabilityRegistry(registry_path=registry_path)

        gateway = ModelReasoningGateway(
            registry_path=registry_path,
            model_callable=lambda request_json: json.dumps(
                {"action": {"capability": "gmail_search"}}
            ),
        )
        orchestrator = self._orchestrator(gateway, registry)

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="search my gmail"
        )

        self.assertEqual(result["plan"]["source"], "model_reasoning")
        self.assertEqual(dispatcher.calls[0][0], "gmail_search")


class UnavailableWorkflowStepIsRejectedTests(_IsolatedOrchestratorCase):

    def test_workflow_step_naming_an_unavailable_capability_falls_back(self):
        registry_path = os.path.join(
            self.temp_dir.name, "capabilities_registry.json"
        )
        _write_registry(
            registry_path,
            {
                "extract_student_records": {
                    "file_path": "x.py",
                    "class_name": "X",
                    "method": "run",
                    "status": "implemented",
                    "availability": "available",
                },
                "gmail_search": {
                    "file_path": "y.py",
                    "class_name": "Y",
                    "method": "run",
                    "status": "implemented",
                    "availability": "unavailable_missing_dependency",
                },
            },
        )
        registry = CapabilityRegistry(registry_path=registry_path)

        gateway = ModelReasoningGateway(
            registry_path=registry_path,
            model_callable=lambda request_json: json.dumps(
                {
                    "workflow": {
                        "goal": "look up a record and email it",
                        "steps": [
                            {
                                "step_id": "s1",
                                "capability": "extract_student_records",
                                "depends_on": [],
                            },
                            {
                                "step_id": "s2",
                                "capability": "gmail_search",
                                "depends_on": ["s1"],
                            },
                        ],
                    }
                }
            ),
        )
        orchestrator = self._orchestrator(gateway, registry)
        orchestrator.workflow_planner.create_workflow = lambda **kwargs: {
            "workflow": {
                "workflow_id": "fallback",
                "steps": [],
                "task": "generic",
            }
        }

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="look up the record and email it"
        )

        # The Brain-composed workflow (with its unavailable step) was
        # never used - the plan fell through to the deterministic
        # WorkflowPlanner path instead. Nothing was ever dispatched
        # with the unavailable capability.
        dispatched_tools = [call[0] for call in dispatcher.calls]
        self.assertNotIn("gmail_search", dispatched_tools)


if __name__ == "__main__":
    unittest.main()
