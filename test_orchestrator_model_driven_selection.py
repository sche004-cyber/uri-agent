"""Milestone 11 Phase 1: proves the already-existing, already-validated
Brain proposal (ModelReasoningGateway.reason()) is now the real
decision source for the direct single-capability path, without
bypassing ApprovalGate/ToolDispatcher and without changing approval
behaviour, CapabilityPlanner, or the ModelProvider abstraction.

No network/Ollama involved anywhere in this file - every gateway here
is driven by a fake, in-process model_callable.
"""

import json
import os
import tempfile
import unittest

from uri_core.core.approval_gate import ApprovalGate
from uri_core.core.approval_store import ApprovalStore
from uri_core.core.audit_trail import AuditTrail
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
    """Records every call it actually receives - what matters here is
    whether the model's proposal ever reaches this without going
    through ApprovalGate, not real execution mechanics. Mirrors
    test_approval_gate.py's identical fixture."""

    def __init__(self):
        self.calls = []

    def execute_tool(self, tool_name, **kwargs):
        self.calls.append((tool_name, kwargs))
        return {"status": "success", "data": {"tool": tool_name}}


def _registry(temp_dir, entries: dict) -> CapabilityRegistry:
    path = os.path.join(temp_dir, "capabilities_registry.json")
    with open(path, "w", encoding="utf-8") as file:
        json.dump({"active_tools": entries}, file)
    return CapabilityRegistry(registry_path=path)


def _fake_model_callable(payload: dict, captured_requests=None):
    """A Callable[[str], str] matching model_callable's contract. When
    captured_requests is given, appends every raw request JSON string
    it receives so a test can inspect what the gateway actually sent."""

    def _call(request_json):
        if captured_requests is not None:
            captured_requests.append(request_json)
        return json.dumps(payload)

    return _call


NOTE_SEMANTIC_RESULT = {
    "goal": "Draft an office note",
    "task_type": "document drafting",
    "domain": "administrative",
    "requested_output": "office note",
    "entities": [],
}


class _IsolatedOrchestratorCase(unittest.TestCase):
    """Shared, fully-isolated construction: a fresh temp dir for
    session/skill-memory storage per test, no reliance on ambient
    uri_workspace/ state, and no narrative drafting (irrelevant to
    selection - kept off to avoid needing a drafting provider)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

    def _orchestrator(
        self,
        model_reasoning_gateway=None,
        approval_gate=None,
    ):
        orchestrator = UriOrchestrator(
            semantic_interpreter=_FixedSemanticInterpreter(
                NOTE_SEMANTIC_RESULT
            ),
            model_reasoning_gateway=model_reasoning_gateway,
            approval_gate=approval_gate,
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

        return orchestrator


class RegistryValidProposalExecutesTests(_IsolatedOrchestratorCase):
    """10a: a registry-valid Brain-proposed capability is actually
    executed through ApprovalGate, even when it disagrees with what
    CapabilityPlanner's keyword scoring would have picked."""

    def test_model_proposal_is_executed_even_when_planner_disagrees(self):
        gateway = ModelReasoningGateway(
            model_callable=_fake_model_callable(
                {"action": {"capability": "extract_student_records"}}
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        # CapabilityPlanner's keyword scoring would pick a different,
        # also-real tool for this semantic result - proving the
        # model's choice wins, not the planner's, when both exist.
        orchestrator.capability_planner.plan = (
            lambda semantic_result: {
                "status": "capability_selected",
                "tool_name": "draft_institutional_note",
            }
        )

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(
            result["execution"]["tool"], "extract_student_records"
        )
        self.assertEqual(result["plan"]["source"], "model_reasoning")
        self.assertEqual(len(dispatcher.calls), 1)
        self.assertEqual(dispatcher.calls[0][0], "extract_student_records")


class ApprovalRequiredStillPausesTests(_IsolatedOrchestratorCase):
    """10b: an approval-required Brain proposal still pauses for
    approval exactly as a CapabilityPlanner-selected one always has -
    the model's proposal never skips ApprovalGate's approval gate."""

    def test_model_proposed_approval_required_capability_pauses(self):
        registry = _registry(
            self.temp_dir.name,
            {
                "needs_approval_capability": {
                    "file_path": "x.py",
                    "class_name": "X",
                    "method": "run",
                    "approval_requirement": "user_approval_required",
                    "risk": "high",
                }
            },
        )

        gateway = ModelReasoningGateway(
            registry_path=os.path.join(
                self.temp_dir.name, "capabilities_registry.json"
            ),
            model_callable=_fake_model_callable(
                {"action": {"capability": "needs_approval_capability"}}
            ),
        )

        fake_dispatcher = _FakeDispatcher()
        approval_store = ApprovalStore(
            storage_path=os.path.join(self.temp_dir.name, "approvals.json")
        )
        approval_gate = ApprovalGate(
            dispatcher=fake_dispatcher,
            capability_registry=registry,
            approval_store=approval_store,
            audit_trail=AuditTrail(),
        )

        orchestrator = self._orchestrator(
            model_reasoning_gateway=gateway,
            approval_gate=approval_gate,
        )

        result = orchestrator.process_user_input(
            session_id="s1", user_text="do the risky thing"
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["plan"]["source"], "model_reasoning")
        self.assertEqual(
            result["execution"]["status"], "awaiting_approval"
        )
        self.assertIn("action_id", result["response"])
        # The capability was never actually executed - only proposed
        # and gated, exactly like a CapabilityPlanner-selected
        # approval-required capability always has been.
        self.assertEqual(fake_dispatcher.calls, [])


class InvalidProposalFallsBackTests(_IsolatedOrchestratorCase):
    """10c: an unregistered/invalid Brain proposal cannot execute and
    falls back safely to CapabilityPlanner."""

    def test_unregistered_capability_proposal_falls_back_to_planner(self):
        gateway = ModelReasoningGateway(
            model_callable=_fake_model_callable(
                {"action": {"capability": "totally_made_up_capability_xyz"}}
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        orchestrator.capability_planner.plan = (
            lambda semantic_result: {
                "status": "capability_selected",
                "tool_name": "draft_institutional_note",
            }
        )

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        # ModelReasoningGateway.validate_proposal() already rejected
        # the unregistered name - unmodified by this milestone - so
        # there was never anything usable to promote to a plan.
        self.assertEqual(
            result["model_reasoning"]["result"]["status"],
            "model_proposal_rejected",
        )
        self.assertEqual(
            result["execution"]["tool"], "draft_institutional_note"
        )
        self.assertNotEqual(result["plan"].get("source"), "model_reasoning")
        self.assertEqual(len(dispatcher.calls), 1)
        self.assertEqual(dispatcher.calls[0][0], "draft_institutional_note")
        # The bogus name never reached the dispatcher at all.
        self.assertNotIn(
            "totally_made_up_capability_xyz",
            [call[0] for call in dispatcher.calls],
        )

    def test_workflow_proposal_is_not_used_for_this_phase(self):
        # Phase 1 only promotes single-action proposals - a workflow
        # proposal (multi-step) must not be used as the direct-
        # capability plan, even though ModelReasoningGateway itself
        # already validates it.
        gateway = ModelReasoningGateway(
            model_callable=_fake_model_callable(
                {
                    "workflow": {
                        "steps": [
                            {
                                "step_id": "step_1",
                                "capability": "draft_institutional_note",
                                "depends_on": [],
                            }
                        ]
                    }
                }
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        orchestrator.capability_planner.plan = (
            lambda semantic_result: {
                "status": "capability_selected",
                "tool_name": "draft_institutional_note",
            }
        )

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        self.assertNotEqual(result["plan"].get("source"), "model_reasoning")
        self.assertEqual(
            result["execution"]["tool"], "draft_institutional_note"
        )


class ModelUnavailableFallsBackTests(_IsolatedOrchestratorCase):
    """10d: model unavailable/disabled preserves deterministic
    fallback behaviour exactly as before this milestone."""

    def test_model_not_configured_falls_back_to_planner(self):
        # Default ModelReasoningGateway() - model_callable=None.
        orchestrator = self._orchestrator(
            model_reasoning_gateway=ModelReasoningGateway()
        )

        orchestrator.capability_planner.plan = (
            lambda semantic_result: {
                "status": "capability_selected",
                "tool_name": "draft_institutional_note",
            }
        )

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        self.assertEqual(
            result["model_reasoning"]["result"]["status"],
            "model_not_configured",
        )
        self.assertEqual(
            result["execution"]["tool"], "draft_institutional_note"
        )
        self.assertNotEqual(result["plan"].get("source"), "model_reasoning")

    def test_model_reasoning_disabled_falls_back_to_planner(self):
        gateway = ModelReasoningGateway(
            model_callable=_fake_model_callable(
                {"action": {"capability": "draft_institutional_note"}}
            )
        )
        orchestrator = UriOrchestrator(
            semantic_interpreter=_FixedSemanticInterpreter(
                NOTE_SEMANTIC_RESULT
            ),
            model_reasoning_gateway=gateway,
            enable_model_reasoning_shadow=False,
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
        orchestrator.capability_planner.plan = (
            lambda semantic_result: {
                "status": "capability_selected",
                "tool_name": "draft_institutional_note",
            }
        )

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        self.assertEqual(result["model_reasoning"]["status"], "reasoning_disabled")
        self.assertEqual(
            result["execution"]["tool"], "draft_institutional_note"
        )


class ModelOutputCannotBypassBoundaryTests(_IsolatedOrchestratorCase):
    """Only a plain, already-validated capability-name string ever
    crosses from the Brain's proposal into execution - never the
    model's own proposed arguments/reason text."""

    def test_model_proposed_arguments_are_ignored(self):
        gateway = ModelReasoningGateway(
            model_callable=_fake_model_callable(
                {
                    "action": {
                        "capability": "draft_institutional_note",
                        # A model could propose anything here - it must
                        # never reach the dispatcher call's kwargs.
                        "arguments": {
                            "request_text": "INJECTED-BY-MODEL"
                        },
                    }
                }
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        orchestrator.process_user_input(
            session_id="s1", user_text="the real user request text"
        )

        self.assertEqual(len(dispatcher.calls), 1)
        _, kwargs = dispatcher.calls[0]
        self.assertEqual(
            kwargs.get("request_text"), "the real user request text"
        )
        self.assertNotEqual(
            kwargs.get("request_text"), "INJECTED-BY-MODEL"
        )


class QueryContextReachesReasoningRequestTests(_IsolatedOrchestratorCase):
    """10g: M10A's query context (identity/personalization/session/
    verified_facts/capabilities) reaches the Brain reasoning request,
    not only the response-drafting request."""

    def test_query_context_key_present_with_expected_sections(self):
        captured_requests = []

        gateway = ModelReasoningGateway(
            model_callable=_fake_model_callable(
                {"action": None},
                captured_requests=captured_requests,
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        orchestrator.process_user_input(
            session_id="s1",
            user_text="draft a note",
            personalization_context={
                "communication_style": "formal",
                "autonomy_level": "askEveryTime",
                "focus_areas": ["insurance"],
                "memory": [],
            },
        )

        self.assertEqual(len(captured_requests), 1)
        request = json.loads(captured_requests[0])

        self.assertIn("query_context", request)
        query_context = request["query_context"]

        self.assertIn("identity", query_context)
        self.assertIn("personalization", query_context)
        self.assertIn("session", query_context)
        self.assertIn("verified_facts", query_context)
        self.assertIn("capabilities", query_context)

        self.assertEqual(
            query_context["personalization"]["communication_style"],
            "formal",
        )
        self.assertIn("insurance", query_context["personalization"]["focus_areas"])
        self.assertTrue(
            any(
                entry.get("id") == "draft_institutional_note"
                for entry in query_context["capabilities"]
            )
        )


if __name__ == "__main__":
    unittest.main()
