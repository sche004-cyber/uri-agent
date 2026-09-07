"""Milestone 12 (Real Brain Loop): proves the Brain<->URI boundary can
recognize a real, registered capability the Brain names in a JSON
shape our strict contract does not expect - the exact failure mode
live testing against real Ollama repeatedly reproduced (the model
returning e.g. {"proposed_workflow": [{"capability_id": "..."}]} or
{"proposed_actions": [{"capability": "...", ...}]} instead of the
contracted {"action": {"capability": "..."}}) - WITHOUT adding a task
taxonomy, keyword scorer, or new reasoning subsystem: the recovery
looks only at a handful of generic, identifier-shaped keys
(_TOLERANT_CAPABILITY_KEYS) and only accepts a value already present
in the authoritative capability registry.

No network/Ollama involved anywhere in this file - every gateway here
is driven by a fake, in-process model_callable reproducing the exact
off-schema shapes observed live.
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
    def __init__(self):
        self.calls = []

    def execute_tool(self, tool_name, **kwargs):
        self.calls.append((tool_name, kwargs))
        return {"status": "success", "data": {"tool": tool_name}}


def _fake_model_callable(payload: dict):
    def _call(request_json):
        return json.dumps(payload)

    return _call


NOTE_SEMANTIC_RESULT = {
    "goal": "Handle a task",
    "task_type": "document drafting",
    "domain": "administrative",
    "requested_output": "office note",
    "entities": [],
}

PLANNING_REQUIRED_PLAN = {"status": "planning_required", "tool_name": None}


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
        orchestrator.capability_planner.plan = (
            lambda sr: dict(PLANNING_REQUIRED_PLAN)
        )
        return orchestrator


class OffSchemaSingleCapabilityRecoveryTests(_IsolatedOrchestratorCase):
    """Real, live-observed off-schema shapes naming exactly one
    registered capability are recognized and executed."""

    def test_capability_id_nested_under_proposed_workflow_list(self):
        # Verbatim shape of what a real model actually returned live.
        gateway = ModelReasoningGateway(
            model_callable=_fake_model_callable(
                {
                    "objective": "Retrieve a student's academic record.",
                    "proposed_workflow": [
                        {
                            "capability_id": "extract_student_records",
                            "parameters": {"roll_number": "required"},
                            "description": "Use this capability.",
                        }
                    ],
                    "required_user_input": {
                        "roll_number": "Please provide it."
                    },
                }
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="retrieve the record"
        )

        self.assertEqual(result["plan"]["source"], "model_reasoning")
        self.assertEqual(
            result["execution"]["tool"], "extract_student_records"
        )
        self.assertEqual(len(dispatcher.calls), 1)
        self.assertEqual(
            dispatcher.calls[0][0], "extract_student_records"
        )

    def test_capability_under_proposed_actions_list(self):
        # Another verbatim shape observed live.
        gateway = ModelReasoningGateway(
            model_callable=_fake_model_callable(
                {
                    "objective": "Draft a note.",
                    "proposed_actions": [
                        {
                            "capability": "draft_institutional_note",
                            "parameters": {"content": "..."},
                        }
                    ],
                }
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        self.assertEqual(result["plan"]["source"], "model_reasoning")
        self.assertEqual(
            result["execution"]["tool"], "draft_institutional_note"
        )
        self.assertEqual(len(dispatcher.calls), 1)

    def test_tool_name_key_variant_is_also_recognized(self):
        gateway = ModelReasoningGateway(
            model_callable=_fake_model_callable(
                {
                    "reasoning": "I will use this tool.",
                    "chosen": {"tool_name": "extract_student_records"},
                }
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="look it up"
        )

        self.assertEqual(
            result["execution"]["tool"], "extract_student_records"
        )


class CapabilityNamedAsListItemRecoveryTests(_IsolatedOrchestratorCase):
    """The shape a real model returns when given the FULL orchestrator
    context: the capability named as a list item under a plural,
    still identifier-shaped key, rather than as a single string under
    a singular one. Observed live with qwen3:14b for a Gmail-search
    request, where it was the difference between reaching the
    capability and reporting 'no implemented capability'."""

    def test_capabilities_required_list_is_recognized(self):
        # Verbatim shape observed live.
        gateway = ModelReasoningGateway(
            model_callable=_fake_model_callable(
                {
                    "proposal": {
                        "objective": "Search Gmail for the renewal email.",
                        "approach": "Use the gmail_search tool.",
                        "capabilities_required": ["gmail_search"],
                        "next_steps": [
                            {"action": "Execute the gmail_search tool."}
                        ],
                    },
                    "status": "proposal",
                }
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="search my gmail"
        )

        self.assertEqual(result["plan"]["source"], "model_reasoning")
        self.assertEqual(result["execution"]["tool"], "gmail_search")
        self.assertEqual(len(dispatcher.calls), 1)
        self.assertEqual(dispatcher.calls[0][0], "gmail_search")

    def test_singular_string_value_still_works_unchanged(self):
        # The pre-existing single-string path must be untouched.
        gateway = ModelReasoningGateway(
            model_callable=_fake_model_callable(
                {"proposed_actions": [{"capability": "gmail_search"}]}
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="search my gmail"
        )

        self.assertEqual(result["execution"]["tool"], "gmail_search")

    def test_unregistered_name_in_a_list_is_still_ignored(self):
        # The registry check still guards every list item individually.
        gateway = ModelReasoningGateway(
            model_callable=_fake_model_callable(
                {"capabilities_required": ["totally_made_up_capability_xyz"]}
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="do something"
        )

        self.assertNotEqual(
            result.get("plan", {}).get("source"), "model_reasoning"
        )
        self.assertEqual(dispatcher.calls, [])

    def test_prose_sentence_in_a_list_is_ignored(self):
        # A list item must be an EXACT registered id - a sentence that
        # merely mentions one is not a decision.
        gateway = ModelReasoningGateway(
            model_callable=_fake_model_callable(
                {
                    "capabilities_required": [
                        "I considered gmail_search but decided against it."
                    ]
                }
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="do something"
        )

        self.assertNotEqual(
            result.get("plan", {}).get("source"), "model_reasoning"
        )
        self.assertEqual(dispatcher.calls, [])


class OffSchemaMultiCapabilityImpliesWorkflowTests(_IsolatedOrchestratorCase):
    """Two or more distinct, real capabilities named off-schema are
    treated as an implied sequential workflow, dependency order
    matching the order they were written in."""

    def test_two_mentions_execute_in_written_order(self):
        gateway = ModelReasoningGateway(
            model_callable=_fake_model_callable(
                {
                    "proposed_workflow": [
                        {"capability_id": "extract_student_records"},
                        {"capability_id": "draft_institutional_note"},
                    ]
                }
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="handle the two-step task"
        )

        self.assertEqual(result["plan"]["source"], "model_reasoning")
        self.assertEqual(result["plan"]["status"], "planning_required")
        self.assertEqual(result["execution"]["status"], "success")
        self.assertEqual(len(dispatcher.calls), 2)
        self.assertEqual(
            dispatcher.calls[0][0], "extract_student_records"
        )
        self.assertEqual(
            dispatcher.calls[1][0], "draft_institutional_note"
        )


class RecoveryStaysBoundedTests(_IsolatedOrchestratorCase):
    """The recovery pass must not become a loophole: an unregistered
    capability, or a real capability mentioned under a non-identifier
    key, must not be recognized - falling back exactly as before."""

    def test_unregistered_capability_under_allowlisted_key_is_ignored(
        self,
    ):
        gateway = ModelReasoningGateway(
            model_callable=_fake_model_callable(
                {
                    "proposed_actions": [
                        {"capability": "totally_made_up_capability_xyz"}
                    ]
                }
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        self.assertNotEqual(
            result.get("plan", {}).get("source"), "model_reasoning"
        )
        self.assertEqual(dispatcher.calls, [])

    def test_mention_under_a_non_identifier_key_is_ignored(self):
        # A real capability name appears, but only as free text under
        # a key that says nothing about it being a decision - must not
        # be picked up (this is what keeps the recovery from becoming
        # a prose-scanning free-for-all).
        gateway = ModelReasoningGateway(
            model_callable=_fake_model_callable(
                {
                    "notes": (
                        "I considered extract_student_records but "
                        "decided against it."
                    ),
                    "action": None,
                }
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        self.assertNotEqual(
            result.get("plan", {}).get("source"), "model_reasoning"
        )
        self.assertEqual(dispatcher.calls, [])

    def test_prose_non_json_response_is_unaffected(self):
        # Recovery only ever operates on an already-parsed JSON
        # object - plain prose still fails exactly as before.
        gateway = ModelReasoningGateway(
            model_callable=lambda request_json: (
                "I need more information to proceed."
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        self.assertEqual(
            result["model_reasoning"]["status"], "reasoning_failed"
        )
        self.assertNotEqual(
            result.get("plan", {}).get("source"), "model_reasoning"
        )
        self.assertEqual(dispatcher.calls, [])


class RecoveredCapabilityStillGatesOnApprovalTests(_IsolatedOrchestratorCase):
    """A capability recovered via the tolerant path is executed
    through the exact same ApprovalGate boundary as a strictly-parsed
    one - the recovery never bypasses authorization."""

    def test_approval_required_capability_recovered_off_schema_still_pauses(
        self,
    ):
        from uri_core.core.approval_gate import ApprovalGate
        from uri_core.core.approval_store import ApprovalStore
        from uri_core.core.audit_trail import AuditTrail
        from uri_core.core.capability_registry import CapabilityRegistry

        registry_path = os.path.join(
            self.temp_dir.name, "capabilities_registry.json"
        )
        with open(registry_path, "w", encoding="utf-8") as file:
            json.dump(
                {
                    "active_tools": {
                        "needs_approval_capability": {
                            "file_path": "x.py",
                            "class_name": "X",
                            "method": "run",
                            "approval_requirement": "user_approval_required",
                        }
                    }
                },
                file,
            )
        registry = CapabilityRegistry(registry_path=registry_path)

        gateway = ModelReasoningGateway(
            registry_path=registry_path,
            model_callable=_fake_model_callable(
                {
                    "proposed_actions": [
                        {"capability": "needs_approval_capability"}
                    ]
                }
            ),
        )

        fake_dispatcher = _FakeDispatcher()
        approval_gate = ApprovalGate(
            dispatcher=fake_dispatcher,
            capability_registry=registry,
            approval_store=ApprovalStore(
                storage_path=os.path.join(
                    self.temp_dir.name, "approvals.json"
                )
            ),
            audit_trail=AuditTrail(),
        )

        orchestrator = self._orchestrator(
            model_reasoning_gateway=gateway, approval_gate=approval_gate
        )
        orchestrator.capability_registry = registry

        result = orchestrator.process_user_input(
            session_id="s1", user_text="do the risky thing"
        )

        self.assertEqual(result["plan"]["source"], "model_reasoning")
        self.assertEqual(
            result["execution"]["status"], "awaiting_approval"
        )
        self.assertEqual(fake_dispatcher.calls, [])


if __name__ == "__main__":
    unittest.main()
