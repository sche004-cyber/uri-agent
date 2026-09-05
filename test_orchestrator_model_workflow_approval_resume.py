"""Milestone 11 Phase 2.1: proves a paused Brain-composed workflow's
remaining steps resume correctly after a real POST /approve (or
/cancel) decision - without bypassing ApprovalGate, without executing
the approved capability more than once, and without disturbing
existing single-capability approval behaviour - plus a focused
crash/restart recovery proof for a paused Brain-composed workflow.

No network/Ollama involved anywhere in this file - every gateway here
is driven by a fake, in-process model_callable.
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
    "goal": "Handle a multi-step administrative request",
    "task_type": "document drafting",
    "domain": "administrative",
    "requested_output": "office note",
    "entities": [],
}

PLANNING_REQUIRED_PLAN = {"status": "planning_required", "tool_name": None}

TWO_STEP_APPROVAL_WORKFLOW = {
    "workflow": {
        "goal": "Handle a multi-step administrative request",
        "steps": [
            {
                "step_id": "step_1",
                "capability": "draft_institutional_note",
                "depends_on": [],
                "requires_user_input": False,
            },
            {
                "step_id": "step_2",
                "capability": "extract_student_records",
                "depends_on": ["step_1"],
                "requires_user_input": False,
            },
        ],
    }
}


class _IsolatedOrchestratorCase(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

    def _session_manager(self):
        return SessionManager(
            storage_path=os.path.join(self.temp_dir.name, "sessions")
        )

    def _orchestrator(self, model_reasoning_gateway=None, **kwargs):
        orchestrator = UriOrchestrator(
            semantic_interpreter=_FixedSemanticInterpreter(
                NOTE_SEMANTIC_RESULT
            ),
            model_reasoning_gateway=model_reasoning_gateway,
            enable_model_reasoning_shadow=True,
            enable_skill_router_shadow=False,
            enable_response_narrative=False,
            session_manager=self._session_manager(),
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
            lambda semantic_result: dict(PLANNING_REQUIRED_PLAN)
        )

        return orchestrator

    def _registry_with_approval_required(
        self, capability_id, extra_capabilities=None
    ):
        active_tools = {
            capability_id: {
                "file_path": "x.py",
                "class_name": "X",
                "method": "run",
                "approval_requirement": "user_approval_required",
                "risk": "high",
            }
        }

        for extra_id in extra_capabilities or []:
            active_tools[extra_id] = {
                "file_path": "y.py",
                "class_name": "Y",
                "method": "run",
                "approval_requirement": "none",
            }

        path = os.path.join(self.temp_dir.name, "capabilities_registry.json")
        with open(path, "w", encoding="utf-8") as file:
            json.dump(
                {
                    "active_tools": active_tools
                },
                file,
            )
        return path


class ApprovalRequiredWorkflowResumesTests(_IsolatedOrchestratorCase):
    """A. The core Phase 2.1 proof: approving one step of a paused
    Brain-composed workflow lets its remaining dependent step run,
    without re-executing the approved capability."""

    def _build(self):
        from uri_core.core.approval_gate import ApprovalGate
        from uri_core.core.approval_store import ApprovalStore
        from uri_core.core.audit_trail import AuditTrail
        from uri_core.core.capability_registry import CapabilityRegistry

        registry_path = self._registry_with_approval_required(
            "needs_approval_capability",
            extra_capabilities=["extract_student_records"],
        )
        registry = CapabilityRegistry(registry_path=registry_path)

        gateway = ModelReasoningGateway(
            registry_path=registry_path,
            model_callable=_fake_model_callable(
                {
                    "workflow": {
                        "goal": "Do a two-step approval-gated task",
                        "steps": [
                            {
                                "step_id": "step_1",
                                "capability": "needs_approval_capability",
                                "depends_on": [],
                            },
                            {
                                "step_id": "step_2",
                                "capability": "extract_student_records",
                                "depends_on": ["step_1"],
                            },
                        ],
                    }
                }
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
        orchestrator.capability_registry = registry

        return orchestrator, fake_dispatcher

    def test_approval_resumes_and_executes_remaining_step_once(self):
        orchestrator, fake_dispatcher = self._build()

        first = orchestrator.process_user_input(
            session_id="s1", user_text="do the two-step task"
        )

        self.assertEqual(first["execution"]["status"], "waiting_for_input")
        action_id = first["execution"]["action_id"]
        self.assertEqual(fake_dispatcher.calls, [])

        result = orchestrator.decide_action(
            action_id=action_id, approved=True, session_id="s1"
        )

        self.assertEqual(result["status"], "success")
        self.assertIn("workflow_continuation", result)
        self.assertEqual(
            result["workflow_continuation"]["status"], "success"
        )

        # The approved capability executed exactly once, and its
        # dependent step ran exactly once afterwards, in order.
        self.assertEqual(len(fake_dispatcher.calls), 2)
        self.assertEqual(
            fake_dispatcher.calls[0][0], "needs_approval_capability"
        )
        self.assertEqual(
            fake_dispatcher.calls[1][0], "extract_student_records"
        )

        # The workflow is no longer active/paused.
        session = orchestrator.session_manager.get_session("s1")
        self.assertIsNone(session.active_workflow)

    def test_double_decide_never_executes_twice(self):
        orchestrator, fake_dispatcher = self._build()

        first = orchestrator.process_user_input(
            session_id="s1", user_text="do the two-step task"
        )
        action_id = first["execution"]["action_id"]

        orchestrator.decide_action(
            action_id=action_id, approved=True, session_id="s1"
        )
        self.assertEqual(len(fake_dispatcher.calls), 2)

        # A second decision on the same, already-consumed action_id
        # must fail closed (ApprovalStore's own STATUS_PENDING check,
        # unmodified) and must not re-run anything.
        second = orchestrator.decide_action(
            action_id=action_id, approved=True, session_id="s1"
        )

        self.assertEqual(second["status"], "error")
        self.assertNotIn("workflow_continuation", second)
        self.assertEqual(len(fake_dispatcher.calls), 2)

    def test_rejection_fails_the_workflow_closed(self):
        orchestrator, fake_dispatcher = self._build()

        first = orchestrator.process_user_input(
            session_id="s1", user_text="do the two-step task"
        )
        action_id = first["execution"]["action_id"]

        result = orchestrator.decide_action(
            action_id=action_id, approved=False, session_id="s1"
        )

        self.assertEqual(result["status"], "cancelled")
        self.assertIn("workflow_continuation", result)
        self.assertEqual(
            result["workflow_continuation"]["status"], "failed"
        )
        # Rejection means the underlying capability itself was never
        # dispatched, and its dependent step never ran either.
        self.assertEqual(fake_dispatcher.calls, [])

        session = orchestrator.session_manager.get_session("s1")
        self.assertIsNone(session.active_workflow)


class ExistingApprovalBehaviourUnchangedTests(_IsolatedOrchestratorCase):
    """Requirement: existing single-capability approval behaviour is
    unaffected - decide_action with no active Brain-composed workflow
    never adds workflow_continuation."""

    def test_plain_single_capability_decision_has_no_workflow_continuation(
        self,
    ):
        from uri_core.core.approval_gate import ApprovalGate
        from uri_core.core.approval_store import ApprovalStore
        from uri_core.core.audit_trail import AuditTrail
        from uri_core.core.capability_registry import CapabilityRegistry

        registry_path = self._registry_with_approval_required(
            "needs_approval_capability"
        )
        registry = CapabilityRegistry(registry_path=registry_path)

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

        # No workflow at all - just a plain proposal, as Milestone 7
        # already fully covers.
        proposed = approval_store.propose(
            capability_id="needs_approval_capability",
            arguments={"request_text": "hello"},
            session_id="s1",
        )

        orchestrator = self._orchestrator(approval_gate=approval_gate)

        result = orchestrator.decide_action(
            action_id=proposed.action_id, approved=True, session_id="s1"
        )

        self.assertEqual(result["status"], "success")
        self.assertNotIn("workflow_continuation", result)


class BrainWorkflowRecoveryTests(_IsolatedOrchestratorCase):
    """B. A paused Brain-composed workflow, persisted to disk, is
    correctly recovered and resumed by a completely fresh
    UriOrchestrator/SessionManager instance (the closest available
    proxy for a process restart) - proving _create_workflow_executor's
    "source"-tag branch survives the full session-reload path, not
    just an in-process resume within the same orchestrator instance."""

    def test_paused_workflow_survives_a_simulated_restart(self):
        session_storage = os.path.join(self.temp_dir.name, "sessions")

        gateway = ModelReasoningGateway(
            model_callable=_fake_model_callable(
                {
                    "workflow": {
                        "goal": "Draft a note that needs confirmation",
                        "steps": [
                            {
                                "step_id": "step_1",
                                "capability": "draft_institutional_note",
                                "depends_on": [],
                                "requires_user_input": True,
                            },
                        ],
                    }
                }
            )
        )

        first_orchestrator = UriOrchestrator(
            semantic_interpreter=_FixedSemanticInterpreter(
                NOTE_SEMANTIC_RESULT
            ),
            model_reasoning_gateway=gateway,
            enable_model_reasoning_shadow=True,
            enable_skill_router_shadow=False,
            enable_response_narrative=False,
            session_manager=SessionManager(storage_path=session_storage),
        )
        first_orchestrator.skill_memory = SkillMemory(
            storage_path=os.path.join(
                self.temp_dir.name, "skill_memory.json"
            )
        )
        first_orchestrator.skill_memory.find_matching_skill = (
            lambda semantic_result: None
        )
        first_orchestrator.capability_planner.plan = (
            lambda semantic_result: dict(PLANNING_REQUIRED_PLAN)
        )

        first_dispatcher = _FakeDispatcher()
        first_orchestrator.dispatcher.execute_tool = (
            first_dispatcher.execute_tool
        )

        paused = first_orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        self.assertEqual(paused["execution"]["status"], "waiting_for_input")
        self.assertEqual(first_dispatcher.calls, [])

        # A completely fresh orchestrator - fresh SkillMemory, fresh
        # SessionManager pointed at the SAME on-disk storage, and no
        # model configured at all - simulating a new process that
        # must recover this session purely from persisted state.
        second_orchestrator = UriOrchestrator(
            semantic_interpreter=_FixedSemanticInterpreter(
                NOTE_SEMANTIC_RESULT
            ),
            model_reasoning_gateway=ModelReasoningGateway(),
            enable_model_reasoning_shadow=True,
            enable_skill_router_shadow=False,
            enable_response_narrative=False,
            session_manager=SessionManager(storage_path=session_storage),
        )
        second_orchestrator.skill_memory = SkillMemory(
            storage_path=os.path.join(
                self.temp_dir.name, "skill_memory_2.json"
            )
        )
        second_orchestrator.skill_memory.find_matching_skill = (
            lambda semantic_result: None
        )

        second_dispatcher = _FakeDispatcher()
        second_orchestrator.dispatcher.execute_tool = (
            second_dispatcher.execute_tool
        )

        session_before = second_orchestrator.session_manager.get_session(
            "s1"
        )
        self.assertTrue(session_before.active_workflow_recovered)
        self.assertEqual(
            session_before.active_workflow.get("source"), "model_reasoning"
        )

        resumed = second_orchestrator.process_user_input(
            session_id="s1", user_text="yes, go ahead"
        )

        self.assertEqual(resumed["status"], "success")
        self.assertEqual(resumed["execution"]["status"], "success")
        self.assertEqual(len(second_dispatcher.calls), 1)
        self.assertEqual(
            second_dispatcher.calls[0][0], "draft_institutional_note"
        )


if __name__ == "__main__":
    unittest.main()
