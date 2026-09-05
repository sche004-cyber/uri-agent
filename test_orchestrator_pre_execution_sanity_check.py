"""Milestone 13 Part 1: proves the canonical loop's pre-execution
step - after the Brain formulates an initial plan, URI gives it one
explicit opportunity to reconsider that plan against the same fuller
context, before anything executes. The Brain may confirm it, modify
or replace it, or decide more information is needed instead; URI
never judges which of these happened, it only relays whatever the
Brain now says into the exact same validated execution path.

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
    def __init__(self, results_by_capability=None):
        self.calls = []
        self._results = results_by_capability or {}

    def execute_tool(self, tool_name, **kwargs):
        self.calls.append((tool_name, kwargs))
        if tool_name in self._results:
            return self._results[tool_name]
        return {"status": "success", "data": {"tool": tool_name}}


def _by_call_index(responses, captured_requests=None):
    """responses is a list; call N (1-indexed) returns responses[N-1],
    the last entry repeating for any further call."""

    def _call(request_json):
        if captured_requests is not None:
            captured_requests.append(json.loads(request_json))
        index = min(_call.count, len(responses) - 1)
        _call.count += 1
        return json.dumps(responses[index])

    _call.count = 0
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


class BrainConfirmsPlanTests(_IsolatedOrchestratorCase):

    def test_confirmed_capability_executes_unchanged(self):
        captured = []
        gateway = ModelReasoningGateway(
            model_callable=_by_call_index(
                [
                    {"action": {"capability": "extract_student_records"}},
                    {"action": {"capability": "extract_student_records"}},
                ],
                captured,
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="look up the record"
        )

        self.assertEqual(result["plan"]["source"], "model_reasoning")
        self.assertEqual(
            result["execution"]["tool"], "extract_student_records"
        )
        self.assertEqual(len(dispatcher.calls), 1)
        # Initial proposal + pre-execution sanity check = 2 calls
        # before execution (the post-execution loop then adds one
        # more, evaluation-shaped-or-not, which this fixture's
        # repeated last entry harmlessly answers again).
        self.assertGreaterEqual(len(captured), 2)
        self.assertIsNone(captured[1].get("attempt_history") or None)
        self.assertEqual(
            captured[1]["pending_proposal"],
            {"action": {"capability": "extract_student_records"}},
        )


class BrainReplacesPlanTests(_IsolatedOrchestratorCase):

    def test_brain_replaces_its_own_capability_after_reconsidering(self):
        gateway = ModelReasoningGateway(
            model_callable=_by_call_index(
                [
                    {"action": {"capability": "extract_student_records"}},
                    {"action": {"capability": "draft_institutional_note"}},
                    {"objective": "not evaluation-shaped"},
                ]
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="handle this"
        )

        # The Brain's RECONSIDERED choice is what actually executes -
        # never the original, discarded first pass.
        self.assertEqual(
            result["execution"]["tool"], "draft_institutional_note"
        )
        self.assertEqual(result["plan"]["tool_name"], "draft_institutional_note")
        self.assertEqual(len(dispatcher.calls), 1)
        self.assertEqual(dispatcher.calls[0][0], "draft_institutional_note")

    def test_brain_replaces_a_single_capability_with_a_workflow(self):
        gateway = ModelReasoningGateway(
            model_callable=_by_call_index(
                [
                    {"action": {"capability": "extract_student_records"}},
                    {
                        "workflow": {
                            "steps": [
                                {
                                    "step_id": "s1",
                                    "capability": "extract_student_records",
                                    "depends_on": [],
                                },
                                {
                                    "step_id": "s2",
                                    "capability": "draft_institutional_note",
                                    "depends_on": ["s1"],
                                },
                            ]
                        }
                    },
                    {"objective": "not evaluation-shaped"},
                ]
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="handle this"
        )

        self.assertEqual(result["plan"]["status"], "planning_required")
        self.assertEqual(result["plan"]["source"], "model_reasoning")
        self.assertEqual(len(dispatcher.calls), 2)
        self.assertEqual(dispatcher.calls[0][0], "extract_student_records")
        self.assertEqual(dispatcher.calls[1][0], "draft_institutional_note")


class BrainRequestsMoreInformationTests(_IsolatedOrchestratorCase):

    def test_clarification_pauses_and_never_executes(self):
        gateway = ModelReasoningGateway(
            model_callable=_by_call_index(
                [
                    {"action": {"capability": "extract_student_records"}},
                    {
                        "clarification": {
                            "question": (
                                "Which roll number should I use - the "
                                "one from this year or last year?"
                            )
                        },
                        "action": None,
                    },
                ]
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="look up the record"
        )

        self.assertEqual(result["execution"]["status"], "waiting_for_input")
        self.assertIn("roll number", result["execution"]["message"])
        self.assertEqual(result["plan"]["status"], "clarification_needed")
        self.assertEqual(result["plan"]["source"], "model_reasoning")
        self.assertEqual(
            result["pre_execution_check"]["outcome"], "clarification_needed"
        )
        self.assertEqual(
            result["clarification"]["stage"], "pre_execution_check"
        )
        self.assertEqual(dispatcher.calls, [])
        self.assertNotIn("brain_evaluation", result)


class SanityCheckUnavailableFallsBackSafelyTests(_IsolatedOrchestratorCase):

    def test_malformed_sanity_check_response_keeps_original_proposal(self):
        gateway = ModelReasoningGateway(
            model_callable=_by_call_index(
                [
                    {"action": {"capability": "extract_student_records"}},
                    {"objective": "neither action, workflow, nor clarification"},
                    {"objective": "not evaluation-shaped"},
                ]
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="look up the record"
        )

        # The sanity check itself produced nothing usable - the
        # ORIGINAL, already-valid Brain proposal must still execute,
        # never discarded because the second call degraded.
        self.assertEqual(
            result["execution"]["tool"], "extract_student_records"
        )
        self.assertEqual(len(dispatcher.calls), 1)

    def test_model_unavailable_on_sanity_check_call_keeps_original(self):
        # Reasoning disabled entirely mid-flight is unrealistic, but a
        # gateway with no model configured for the SAME orchestrator
        # instance is a clean way to simulate "the sanity check call
        # itself cannot run" deterministically.
        calls = {"n": 0}

        class _FlakyGateway(ModelReasoningGateway):
            def reason(self, *args, **kwargs):
                calls["n"] += 1
                if calls["n"] == 1:
                    return super().reason(*args, **kwargs)
                return {"status": "model_not_configured", "request": {}, "proposal": None}

        gateway = _FlakyGateway(
            model_callable=_by_call_index(
                [{"action": {"capability": "extract_student_records"}}]
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="look up the record"
        )

        self.assertEqual(
            result["execution"]["tool"], "extract_student_records"
        )
        self.assertEqual(len(dispatcher.calls), 1)


class ApprovalBoundaryStillEnforcedAfterSanityCheckTests(_IsolatedOrchestratorCase):

    def test_approval_required_capability_still_pauses_after_confirmation(self):
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
            model_callable=_by_call_index(
                [
                    {"action": {"capability": "needs_approval_capability"}},
                    {"action": {"capability": "needs_approval_capability"}},
                ]
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
        self.assertNotIn("brain_evaluation", result)


class PostExecutionLoopStillWorksAfterSanityCheckTests(_IsolatedOrchestratorCase):
    """Preserves the M12 post-execution re-evaluation loop end to end,
    now that a pre-execution sanity check always runs first."""

    def test_first_result_insufficient_then_second_action_satisfies(self):
        gateway = ModelReasoningGateway(
            model_callable=_by_call_index(
                [
                    # Initial proposal.
                    {"action": {"capability": "extract_student_records"}},
                    # Pre-execution sanity check: confirmed.
                    {"action": {"capability": "extract_student_records"}},
                    # Post-execution evaluation: not satisfied, propose
                    # a different action.
                    {
                        "evaluation": {
                            "satisfied": False,
                            "reason": "The record alone doesn't answer the request.",
                        },
                        "action": {"capability": "draft_institutional_note"},
                    },
                    # Post-execution evaluation of the SECOND action:
                    # satisfied.
                    {
                        "evaluation": {
                            "satisfied": True,
                            "reason": "This now answers the request.",
                        }
                    },
                ]
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="handle this"
        )

        self.assertTrue(result["brain_evaluation"]["satisfied"])
        self.assertEqual(len(dispatcher.calls), 2)
        self.assertEqual(dispatcher.calls[0][0], "extract_student_records")
        self.assertEqual(dispatcher.calls[1][0], "draft_institutional_note")


class NoInitialProposalSkipsSanityCheckTests(_IsolatedOrchestratorCase):
    """When the Brain proposes nothing at all on its first call, the
    sanity check must not run, and the existing deterministic fallback
    behaviour is completely unaffected."""

    def test_no_proposal_falls_back_without_a_sanity_check_call(self):
        captured = []
        gateway = ModelReasoningGateway(
            model_callable=_by_call_index(
                [{"action": None, "workflow": None}], captured
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="do something vague"
        )

        self.assertNotEqual(
            result.get("plan", {}).get("source"), "model_reasoning"
        )
        self.assertEqual(len(captured), 1)


class InitialClarificationIsHonoredTests(_IsolatedOrchestratorCase):
    """Live testing surfaced this exact gap: when the Brain's very
    FIRST call already decides it needs more information (action and
    workflow both null, a clarification given instead), that decision
    must be honored - not silently discarded in favor of the
    deterministic CapabilityPlanner confidently guessing a capability
    the Brain explicitly said it did not have enough information to
    use responsibly yet."""

    def test_initial_clarification_pauses_instead_of_falling_back(self):
        gateway = ModelReasoningGateway(
            model_callable=_by_call_index(
                [
                    {
                        "clarification": {
                            "question": (
                                "Please provide the student's roll "
                                "number so I can retrieve their record."
                            )
                        },
                        "action": None,
                        "workflow": None,
                    }
                ]
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="Please look up the student record."
        )

        self.assertEqual(result["execution"]["status"], "waiting_for_input")
        self.assertIn("roll number", result["execution"]["message"])
        self.assertEqual(result["plan"]["source"], "model_reasoning")
        self.assertEqual(result["clarification"]["stage"], "initial_reasoning")
        self.assertEqual(dispatcher.calls, [])


if __name__ == "__main__":
    unittest.main()
