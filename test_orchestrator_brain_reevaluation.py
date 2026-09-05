"""Milestone 11 Part 2: proves the Brain re-evaluation loop -

user goal -> Brain proposes -> URI validates/executes -> real result
-> Brain re-evaluates -> satisfied (finish) or not satisfied (next
proposal) -> URI validates/executes -> ... -> goal achieved / no
viable path / safety cap reached.

URI never decides on its own that a technically-successful execution
means the goal was achieved, and URI never repeats an action on its
own initiative - every additional attempt must come from a fresh,
independently-validated Brain proposal.

No network/Ollama involved anywhere in this file - every gateway here
is driven by a fake, in-process model_callable that inspects
attempt_history to decide how to respond, exactly mirroring how a
real model would be asked to evaluate versus propose.
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
    """A model_callable that inspects the request's attempt_history
    length (0 = initial proposal, 1 = evaluating attempt 1, 2 =
    evaluating attempt 2, ...) and returns the JSON payload registered
    for that count. This is what lets these tests drive "the Brain
    evaluates, says no, proposes something else, evaluates again"
    deterministically without a real model."""

    def _call(request_json):
        request = json.loads(request_json)
        count = len(request.get("attempt_history", []))
        payload = responses_by_count.get(
            count, responses_by_count.get("default", {})
        )
        return json.dumps(payload)

    return _call


NOTE_SEMANTIC_RESULT = {
    "goal": "Handle a task requiring re-evaluation",
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
        return orchestrator


class CriticalReevaluationTests(_IsolatedOrchestratorCase):
    """Brain -> Action A -> technically succeeds but doesn't satisfy
    -> Brain says NO -> Action B -> satisfies -> YES."""

    def test_action_a_insufficient_then_action_b_satisfies(self):
        gateway = ModelReasoningGateway(
            model_callable=_by_attempt_count(
                {
                    0: {
                        "action": {
                            "capability": "extract_student_records"
                        }
                    },
                    1: {
                        "evaluation": {
                            "satisfied": False,
                            "reason": (
                                "The record lookup alone doesn't "
                                "produce the requested note."
                            ),
                        },
                        "action": {
                            "capability": "draft_institutional_note"
                        },
                    },
                    2: {
                        "evaluation": {
                            "satisfied": True,
                            "reason": "The note now covers the request.",
                        },
                    },
                }
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        orchestrator.capability_planner.plan = (
            lambda sr: dict(PLANNING_REQUIRED_PLAN)
        )

        dispatcher = _FakeDispatcher(
            {
                "extract_student_records": {
                    "status": "success",
                    "data": {"roll": "123", "cgpa": 8.1},
                },
                "draft_institutional_note": {
                    "status": "success",
                    "data": {"draft": "Note referencing CGPA 8.1."},
                },
            }
        )
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="handle the CGPA-based note task"
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(dispatcher.calls), 2)
        self.assertEqual(dispatcher.calls[0][0], "extract_student_records")
        self.assertEqual(dispatcher.calls[1][0], "draft_institutional_note")

        self.assertEqual(result["execution"]["tool"], "draft_institutional_note")
        self.assertEqual(result["plan"]["source"], "model_reasoning")

        self.assertIn("brain_evaluation", result)
        self.assertTrue(result["brain_evaluation"]["satisfied"])
        self.assertEqual(result["brain_evaluation"]["iterations"], 2)


class FirstResultSatisfiesTests(_IsolatedOrchestratorCase):
    """If the first result already satisfies the goal, there must be
    no second action - only one evaluation call, no repeat dispatch."""

    def test_no_second_action_when_first_result_satisfies(self):
        gateway = ModelReasoningGateway(
            model_callable=_by_attempt_count(
                {
                    0: {
                        "action": {
                            "capability": "draft_institutional_note"
                        }
                    },
                    1: {
                        "evaluation": {
                            "satisfied": True,
                            "reason": "This fully answers the request.",
                        },
                    },
                }
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        orchestrator.capability_planner.plan = (
            lambda sr: dict(PLANNING_REQUIRED_PLAN)
        )

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="draft the note"
        )

        self.assertEqual(len(dispatcher.calls), 1)
        self.assertTrue(result["brain_evaluation"]["satisfied"])
        self.assertEqual(result["brain_evaluation"]["iterations"], 1)


class ExecutionFailureReconsiderationTests(_IsolatedOrchestratorCase):
    """An execution failure (not a pending approval) must still reach
    the Brain for evaluation, and the Brain may propose something
    different in response."""

    def test_brain_reconsiders_after_a_failure(self):
        gateway = ModelReasoningGateway(
            model_callable=_by_attempt_count(
                {
                    0: {
                        "action": {
                            "capability": "extract_student_records"
                        }
                    },
                    1: {
                        "evaluation": {
                            "satisfied": False,
                            "reason": "That action failed outright.",
                        },
                        "action": {
                            "capability": "draft_institutional_note"
                        },
                    },
                    2: {
                        "evaluation": {"satisfied": True, "reason": "OK now."},
                    },
                }
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        orchestrator.capability_planner.plan = (
            lambda sr: dict(PLANNING_REQUIRED_PLAN)
        )

        dispatcher = _FakeDispatcher(
            {
                "extract_student_records": {
                    "status": "error",
                    "message": "Roll number not found.",
                },
                "draft_institutional_note": {
                    "status": "success",
                    "data": {"draft": "Fallback note."},
                },
            }
        )
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="look up the record"
        )

        self.assertEqual(len(dispatcher.calls), 2)
        self.assertEqual(result["execution"]["tool"], "draft_institutional_note")
        self.assertTrue(result["brain_evaluation"]["satisfied"])


class ApprovalRequiredProtectedTests(_IsolatedOrchestratorCase):
    """An approval-required action must never be sent to the Brain for
    evaluation - the loop must no-op immediately, with zero extra
    reason() calls, leaving the pending approval exactly as Phase 1
    already produces it."""

    def test_awaiting_approval_is_never_evaluated(self):
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
                            "risk": "high",
                        }
                    }
                },
                file,
            )
        registry = CapabilityRegistry(registry_path=registry_path)

        call_count = {"n": 0}

        def _call(request_json):
            call_count["n"] += 1
            return json.dumps(
                {"action": {"capability": "needs_approval_capability"}}
            )

        gateway = ModelReasoningGateway(
            registry_path=registry_path, model_callable=_call
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
        orchestrator.capability_planner.plan = (
            lambda sr: dict(PLANNING_REQUIRED_PLAN)
        )

        result = orchestrator.process_user_input(
            session_id="s1", user_text="do the risky thing"
        )

        self.assertEqual(result["execution"]["status"], "awaiting_approval")
        self.assertEqual(fake_dispatcher.calls, [])
        # Exactly one reasoning call (the initial proposal) - the loop
        # must not have attempted a second, evaluation call.
        self.assertEqual(call_count["n"], 1)
        self.assertNotIn("brain_evaluation", result)


class IterationLimitTests(_IsolatedOrchestratorCase):
    """The safety cap must stop the loop deterministically, without
    hanging, when the Brain keeps saying "not satisfied" indefinitely."""

    def test_iteration_limit_stops_safely(self):
        gateway = ModelReasoningGateway(
            model_callable=_by_attempt_count(
                {
                    "default": {
                        "evaluation": {
                            "satisfied": False,
                            "reason": "Still not right, try again.",
                        },
                        "action": {
                            "capability": "draft_institutional_note"
                        },
                    },
                    0: {
                        "action": {
                            "capability": "draft_institutional_note"
                        }
                    },
                }
            )
        )
        orchestrator = self._orchestrator(
            model_reasoning_gateway=gateway,
            max_brain_iterations=2,
        )
        orchestrator.capability_planner.plan = (
            lambda sr: dict(PLANNING_REQUIRED_PLAN)
        )

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="draft the note"
        )

        # max_brain_iterations=2 means at most 2 executions total.
        self.assertEqual(len(dispatcher.calls), 2)
        self.assertFalse(result["brain_evaluation"]["satisfied"])
        self.assertEqual(
            result["brain_evaluation"]["status"], "iteration_limit_reached"
        )
        self.assertEqual(result["brain_evaluation"]["iterations"], 2)


class NoViableProposalTests(_IsolatedOrchestratorCase):
    """When the Brain honestly has nothing further to propose, the
    loop must stop and say so rather than looping or fabricating an
    action."""

    def test_no_further_proposal_stops_honestly(self):
        gateway = ModelReasoningGateway(
            model_callable=_by_attempt_count(
                {
                    0: {
                        "action": {
                            "capability": "draft_institutional_note"
                        }
                    },
                    1: {
                        "evaluation": {
                            "satisfied": False,
                            "reason": (
                                "Nothing in the available capability "
                                "catalogue can achieve this goal."
                            ),
                        },
                        "action": None,
                        "workflow": None,
                    },
                }
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        orchestrator.capability_planner.plan = (
            lambda sr: dict(PLANNING_REQUIRED_PLAN)
        )

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="draft the note"
        )

        self.assertEqual(len(dispatcher.calls), 1)
        self.assertFalse(result["brain_evaluation"]["satisfied"])
        self.assertEqual(
            result["brain_evaluation"]["status"], "no_further_proposal"
        )
        self.assertIn(
            "capability catalogue", result["brain_evaluation"]["reason"]
        )


class CrossTypeProposalTests(_IsolatedOrchestratorCase):
    """The next proposal may be a different shape than the first
    (workflow after a single action, or vice versa) - proving the loop
    is generic, not locked to one proposal type per turn."""

    def test_workflow_first_attempt_then_single_capability_satisfies(self):
        gateway = ModelReasoningGateway(
            model_callable=_by_attempt_count(
                {
                    0: {
                        "workflow": {
                            "goal": "handle the task",
                            "steps": [
                                {
                                    "step_id": "step_1",
                                    "capability": "extract_student_records",
                                    "depends_on": [],
                                }
                            ],
                        }
                    },
                    1: {
                        "evaluation": {
                            "satisfied": False,
                            "reason": "The workflow result alone isn't enough.",
                        },
                        "action": {
                            "capability": "draft_institutional_note"
                        },
                    },
                    2: {
                        "evaluation": {"satisfied": True, "reason": "Done."},
                    },
                }
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        orchestrator.capability_planner.plan = (
            lambda sr: dict(PLANNING_REQUIRED_PLAN)
        )

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="handle the task"
        )

        self.assertEqual(len(dispatcher.calls), 2)
        self.assertEqual(dispatcher.calls[0][0], "extract_student_records")
        self.assertEqual(dispatcher.calls[1][0], "draft_institutional_note")
        # The final attempt was a single capability - "workflow" must
        # no longer be present in the final response.
        self.assertNotIn("workflow", result)
        self.assertEqual(result["execution"]["tool"], "draft_institutional_note")
        self.assertTrue(result["brain_evaluation"]["satisfied"])


class NonBrainPlansAreNeverEvaluatedTests(_IsolatedOrchestratorCase):
    """A learned skill or a CapabilityPlanner-selected capability must
    never enter the evaluation loop - preserving existing fallback
    behaviour exactly, with zero extra reasoning calls."""

    def test_capability_planner_plan_is_not_evaluated(self):
        call_count = {"n": 0}

        def _call(request_json):
            call_count["n"] += 1
            return json.dumps({"action": None})

        gateway = ModelReasoningGateway(model_callable=_call)
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        orchestrator.capability_planner.plan = lambda sr: {
            "status": "capability_selected",
            "tool_name": "draft_institutional_note",
        }

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="draft the note"
        )

        self.assertEqual(len(dispatcher.calls), 1)
        self.assertNotIn("brain_evaluation", result)
        # Exactly one reasoning call (the initial one that returned
        # nothing usable) - no evaluation round was attempted for a
        # non-Brain-sourced plan.
        self.assertEqual(call_count["n"], 1)


if __name__ == "__main__":
    unittest.main()
