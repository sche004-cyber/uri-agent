"""Milestone 11 Phase 2: proves an already-validated, multi-step Brain
workflow proposal is now the real execution source for the
planning_required path - via the existing, unmodified WorkflowExecutor
and ApprovalGate - without bypassing approval, without touching
ToolDispatcher directly, and with the deterministic WorkflowPlanner/
WorkflowCapabilityRouter pipeline preserved as the unchanged fallback.

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
            lambda semantic_result: dict(PLANNING_REQUIRED_PLAN)
        )

        return orchestrator


class MultiStepWorkflowExecutesTests(_IsolatedOrchestratorCase):
    """9a/9b/9g: a valid, dependency-ordered multi-step Brain workflow
    executes end to end, every step reaching ApprovalGate (never
    ToolDispatcher directly), in dependency order."""

    def test_two_step_workflow_executes_in_dependency_order(self):
        gateway = ModelReasoningGateway(
            model_callable=_fake_model_callable(
                {
                    "workflow": {
                        "goal": "Handle a multi-step administrative request",
                        "steps": [
                            {
                                "step_id": "step_1",
                                "capability": "draft_institutional_note",
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
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="handle this multi-step request"
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["execution"]["status"], "success")
        self.assertEqual(result["plan"]["source"], "model_reasoning")

        self.assertEqual(len(dispatcher.calls), 2)
        self.assertEqual(dispatcher.calls[0][0], "draft_institutional_note")
        self.assertEqual(dispatcher.calls[1][0], "extract_student_records")

    def test_dependency_violation_blocks_rather_than_reorders(self):
        # step_2 depends on a step_id that does not exist in this
        # workflow - WorkflowExecutor's own (unmodified) dependency
        # engine must block, never silently skip the dependency check.
        gateway = ModelReasoningGateway(
            model_callable=_fake_model_callable(
                {
                    "workflow": {
                        "goal": "Handle a request",
                        "steps": [
                            {
                                "step_id": "step_2",
                                "capability": "extract_student_records",
                                "depends_on": ["step_missing"],
                            },
                        ],
                    }
                }
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="handle this request"
        )

        self.assertEqual(result["execution"]["status"], "blocked")
        self.assertEqual(dispatcher.calls, [])


class ApprovalRequiredStepPausesTests(_IsolatedOrchestratorCase):
    """9c: an approval-required capability inside a Brain-composed
    workflow pauses for approval exactly as the direct single-
    capability path and the deterministic workflow path already do -
    the dispatcher is never actually called."""

    def test_approval_required_step_pauses_and_never_dispatches(self):
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
                {
                    "workflow": {
                        "goal": "Do the risky thing",
                        "steps": [
                            {
                                "step_id": "step_1",
                                "capability": "needs_approval_capability",
                                "depends_on": [],
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
        # The authoritative re-confirmation in _model_proposed_workflow
        # must see the SAME registry ApprovalGate itself uses.
        orchestrator.capability_registry = registry

        result = orchestrator.process_user_input(
            session_id="s1", user_text="do the risky thing"
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["plan"]["source"], "model_reasoning")
        # WorkflowExecutor represents every pause reason (missing
        # information or a pending approval) with the same generic
        # "waiting_for_input" workflow-level status - exactly how the
        # existing WorkflowCapabilityRouter-backed workflow path
        # already would, if any of its own capabilities required
        # approval today (none currently do). The approval-specific
        # data (action_id/risk/description/message) survives via
        # WorkflowExecutor's generic extra-field passthrough - see
        # workflow_executor.py's _pause_for_input.
        self.assertEqual(
            result["execution"]["status"], "waiting_for_input"
        )
        self.assertIn("action_id", result["execution"])
        self.assertIn(
            "approval", result["execution"]["message"].lower()
        )
        self.assertEqual(fake_dispatcher.calls, [])


class InvalidWorkflowFallsBackTests(_IsolatedOrchestratorCase):
    """9d: an unregistered-capability workflow proposal falls back
    safely to the existing WorkflowPlanner/WorkflowCapabilityRouter
    pipeline, unchanged."""

    def test_unregistered_capability_in_workflow_falls_back(self):
        gateway = ModelReasoningGateway(
            model_callable=_fake_model_callable(
                {
                    "workflow": {
                        "goal": "Do something",
                        "steps": [
                            {
                                "step_id": "step_1",
                                "capability": "totally_made_up_capability_xyz",
                                "depends_on": [],
                            },
                        ],
                    }
                }
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        created_workflows = []
        real_create_workflow = orchestrator.workflow_planner.create_workflow

        def _spy_create_workflow(**kwargs):
            created_workflows.append(kwargs)
            return real_create_workflow(**kwargs)

        orchestrator.workflow_planner.create_workflow = _spy_create_workflow

        result = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        # ModelReasoningGateway.validate_proposal() already rejected
        # the unregistered name - the deterministic WorkflowPlanner
        # path ran instead, unmodified.
        self.assertEqual(
            result["model_reasoning"]["result"]["status"],
            "model_proposal_rejected",
        )
        self.assertEqual(len(created_workflows), 1)
        self.assertNotEqual(
            result.get("plan", {}).get("source"), "model_reasoning"
        )


class ModelUnavailableFallsBackToWorkflowPlannerTests(
    _IsolatedOrchestratorCase
):
    """9e: model unavailable/disabled preserves the existing
    WorkflowPlanner behaviour exactly."""

    def test_model_not_configured_uses_workflow_planner(self):
        orchestrator = self._orchestrator(
            model_reasoning_gateway=ModelReasoningGateway()
        )

        created_workflows = []
        real_create_workflow = orchestrator.workflow_planner.create_workflow

        def _spy_create_workflow(**kwargs):
            created_workflows.append(kwargs)
            return real_create_workflow(**kwargs)

        orchestrator.workflow_planner.create_workflow = _spy_create_workflow

        result = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        self.assertEqual(len(created_workflows), 1)
        self.assertNotEqual(
            result.get("plan", {}).get("source"), "model_reasoning"
        )

    def test_model_reasoning_disabled_uses_workflow_planner(self):
        gateway = ModelReasoningGateway(
            model_callable=_fake_model_callable(
                {
                    "workflow": {
                        "goal": "Do something",
                        "steps": [
                            {
                                "step_id": "step_1",
                                "capability": "draft_institutional_note",
                                "depends_on": [],
                            },
                        ],
                    }
                }
            )
        )
        orchestrator = self._orchestrator(
            model_reasoning_gateway=gateway,
        )
        orchestrator.enable_model_reasoning_shadow = False

        created_workflows = []
        real_create_workflow = orchestrator.workflow_planner.create_workflow

        def _spy_create_workflow(**kwargs):
            created_workflows.append(kwargs)
            return real_create_workflow(**kwargs)

        orchestrator.workflow_planner.create_workflow = _spy_create_workflow

        result = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        self.assertEqual(result["model_reasoning"]["status"], "reasoning_disabled")
        self.assertEqual(len(created_workflows), 1)
        self.assertNotEqual(
            result.get("plan", {}).get("source"), "model_reasoning"
        )


class RequiresUserInputPausesAndResumesTests(_IsolatedOrchestratorCase):
    """9h: a requires_user_input step pauses before running its
    handler, and a subsequent turn correctly resumes and actually
    executes it - proving _create_workflow_executor's resume-time
    branch rebuilds the SAME (generic, capability-keyed) executor a
    Brain-composed workflow needs, not the abstract-stage
    WorkflowCapabilityRouter one."""

    def test_pause_then_resume_executes_the_step(self):
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
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        first = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        self.assertEqual(first["execution"]["status"], "waiting_for_input")
        self.assertEqual(dispatcher.calls, [])

        second = orchestrator.process_user_input(
            session_id="s1", user_text="yes, go ahead"
        )

        self.assertEqual(second["status"], "success")
        self.assertEqual(second["execution"]["status"], "success")
        self.assertEqual(len(dispatcher.calls), 1)
        self.assertEqual(dispatcher.calls[0][0], "draft_institutional_note")


class ModelWorkflowHandlerBoundaryTests(_IsolatedOrchestratorCase):
    """9b/9i unit-level proof: the generic handler this milestone adds
    calls only ApprovalGate.execute_tool, never ToolDispatcher
    directly - proven in isolation, independent of process_user_input."""

    def test_handler_calls_approval_gate_not_dispatcher(self):
        from unittest.mock import MagicMock

        orchestrator = self._orchestrator()
        orchestrator.approval_gate = MagicMock()
        orchestrator.approval_gate.execute_tool.return_value = {
            "status": "success",
            "data": {"ok": True},
        }
        orchestrator.dispatcher.execute_tool = MagicMock(
            side_effect=AssertionError(
                "ToolDispatcher must never be called directly"
            )
        )

        workflow = orchestrator._build_model_workflow(
            {
                "goal": "test goal",
                "steps": [
                    {
                        "step_id": "step_1",
                        "capability": "draft_institutional_note",
                        "depends_on": [],
                        "requires_user_input": False,
                    }
                ],
            }
        )

        executor = orchestrator._build_model_workflow_executor(
            workflow=workflow, session_id="s1"
        )

        result = executor.execute(workflow)

        self.assertEqual(result["status"], "success")
        orchestrator.approval_gate.execute_tool.assert_called_once_with(
            "draft_institutional_note",
            session_id="s1",
            request_text="test goal",
        )
        orchestrator.dispatcher.execute_tool.assert_not_called()


class ModelWorkflowAuditTests(_IsolatedOrchestratorCase):
    """9: honest audit metadata - workflow proposal present, used as
    plan, and fallback reason when applicable."""

    def _events(self, orchestrator, session_id):
        return [
            event
            for event in orchestrator.audit_trail.for_session(session_id)
            if event.event_type == "model_workflow_evaluation"
        ]

    def test_used_workflow_is_recorded_honestly(self):
        gateway = ModelReasoningGateway(
            model_callable=_fake_model_callable(
                {
                    "workflow": {
                        "goal": "Do something",
                        "steps": [
                            {
                                "step_id": "step_1",
                                "capability": "draft_institutional_note",
                                "depends_on": [],
                            },
                        ],
                    }
                }
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        orchestrator.dispatcher.execute_tool = _FakeDispatcher().execute_tool

        orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        events = self._events(orchestrator, "s1")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].status, "used")
        self.assertTrue(events[0].metadata["workflow_proposed"])
        self.assertTrue(events[0].metadata["workflow_valid"])
        self.assertTrue(events[0].metadata["used_as_plan"])
        self.assertIsNone(events[0].metadata["fallback_reason"])

    def test_invalid_workflow_records_fallback_reason(self):
        gateway = ModelReasoningGateway(
            model_callable=_fake_model_callable(
                {
                    "workflow": {
                        "goal": "Do something",
                        "steps": [
                            {
                                "step_id": "step_1",
                                "capability": "totally_made_up_capability_xyz",
                                "depends_on": [],
                            },
                        ],
                    }
                }
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        events = self._events(orchestrator, "s1")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].status, "fallback")
        self.assertFalse(events[0].metadata["used_as_plan"])
        self.assertIsNotNone(events[0].metadata["fallback_reason"])

    def test_no_workflow_proposed_records_fallback_reason(self):
        orchestrator = self._orchestrator(
            model_reasoning_gateway=ModelReasoningGateway()
        )

        orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        events = self._events(orchestrator, "s1")
        self.assertEqual(len(events), 1)
        self.assertFalse(events[0].metadata["workflow_proposed"])
        self.assertEqual(
            events[0].metadata["fallback_reason"], "no_workflow_proposed"
        )


if __name__ == "__main__":
    unittest.main()
