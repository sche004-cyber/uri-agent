"""URI Correction Part 1: proves

1. A learned skill is advisory context (surfaced to the Brain as
   "learned_skill_reference"), never an automatic override of a fresh,
   valid Brain proposal - the Brain may use it, depart from it, or
   ignore it, and a learned skill remains a genuine fallback only when
   the Brain has nothing usable to offer.
2. The immediately preceding turn's Brain attempt history survives
   into the next turn's reasoning request when that turn did not end
   satisfied - real evidence for whatever the user's next message
   turns out to be (acceptance, rejection, or redirection) - and is
   cleared, not carried forward, once a turn does end satisfied.
3. None of the above ever bypasses ApprovalGate/security boundaries.

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
        self._results_by_capability = results_by_capability or {}

    def execute_tool(self, tool_name, **kwargs):
        self.calls.append((tool_name, kwargs))
        if tool_name in self._results_by_capability:
            return self._results_by_capability[tool_name]
        return {"status": "success", "data": {"tool": tool_name}}


class _FakeSkillMemory:
    """Always reports the same match - mirrors
    test_orchestrator_skill_memory_execution.py's own fixture."""

    def __init__(self, tool_name, success_count=2):
        self.matched = {
            "task_type": "document drafting",
            "domain": "administrative",
            "tool_name": tool_name,
            "workflow": ["interpret_request", f"execute_{tool_name}"],
            "success_count": success_count,
        }
        self.learn_skill_calls = []

    def find_matching_skill(self, semantic_result):
        return dict(self.matched)

    def learn_skill(self, semantic_result, workflow, tool_name=None):
        self.learn_skill_calls.append(tool_name)


def _capturing_callable(responses_by_count, captured_requests):
    """A model_callable that records every raw request it receives and
    responds according to the request's attempt_history length -
    exactly the technique test_orchestrator_brain_reevaluation.py
    already uses, extended to also expose the captured requests for
    direct inspection (e.g. checking learned_skill_reference or
    cross-turn attempt_history content)."""

    def _call(request_json):
        request = json.loads(request_json)
        captured_requests.append(request)
        count = len(request.get("attempt_history", []))
        payload = responses_by_count.get(
            count, responses_by_count.get("default", {})
        )
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

    def _session_manager(self):
        return SessionManager(
            storage_path=os.path.join(self.temp_dir.name, "sessions")
        )

    def _orchestrator(
        self,
        model_reasoning_gateway=None,
        skill_memory=None,
        enable_model_reasoning_shadow=True,
        **kwargs
    ):
        orchestrator = UriOrchestrator(
            semantic_interpreter=_FixedSemanticInterpreter(
                NOTE_SEMANTIC_RESULT
            ),
            model_reasoning_gateway=model_reasoning_gateway,
            enable_model_reasoning_shadow=enable_model_reasoning_shadow,
            enable_skill_router_shadow=False,
            enable_response_narrative=False,
            session_manager=self._session_manager(),
            **kwargs,
        )
        orchestrator.skill_memory = skill_memory or SkillMemory(
            storage_path=os.path.join(
                self.temp_dir.name, "skill_memory.json"
            )
        )
        return orchestrator


class LearnedSkillIsAdvisoryTests(_IsolatedOrchestratorCase):
    """A learned skill is reference context, never a binding override
    of a fresh, valid Brain proposal."""

    def test_brain_may_ignore_the_learned_skill_and_propose_differently(
        self,
    ):
        captured_requests = []
        gateway = ModelReasoningGateway(
            model_callable=_capturing_callable(
                {0: {"action": {"capability": "extract_student_records"}}},
                captured_requests,
            )
        )
        skill_memory = _FakeSkillMemory("draft_institutional_note")
        orchestrator = self._orchestrator(
            model_reasoning_gateway=gateway, skill_memory=skill_memory
        )

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="do something"
        )

        # The Brain's own, different choice won - not the learned one.
        self.assertEqual(result["plan"]["source"], "model_reasoning")
        self.assertEqual(
            result["execution"]["tool"], "extract_student_records"
        )
        self.assertEqual(len(dispatcher.calls), 1)
        self.assertEqual(dispatcher.calls[0][0], "extract_student_records")

        # The Brain's own execution succeeded, so the Part 2
        # re-evaluation loop makes one further (evaluation) call
        # before honestly stopping (this fixture's model returns
        # nothing evaluation-shaped on that second call).
        self.assertEqual(len(captured_requests), 2)
        self.assertFalse(result["brain_evaluation"]["satisfied"])

        # The learned skill was still genuinely offered to the Brain
        # as a reference on its first (proposing) call, not silently
        # withheld.
        reference = captured_requests[0]["session_context"].get(
            "learned_skill_reference"
        )
        self.assertIsNotNone(reference)
        self.assertEqual(
            reference["tool_name"], "draft_institutional_note"
        )

    def test_learned_skill_remains_a_fallback_when_brain_has_nothing_usable(
        self,
    ):
        # The Brain IS enabled and configured, but its response never
        # resolves to a usable action/workflow (e.g. off-schema, as
        # real models sometimes produce) - the learned skill still
        # rescues the turn instead of falling all the way to
        # CapabilityPlanner's keyword scoring.
        gateway = ModelReasoningGateway(
            model_callable=lambda request_json: json.dumps(
                {"objective": "something not in the expected shape"}
            )
        )
        skill_memory = _FakeSkillMemory("draft_institutional_note")
        orchestrator = self._orchestrator(
            model_reasoning_gateway=gateway, skill_memory=skill_memory
        )
        # If the learned skill were ignored, CapabilityPlanner's own
        # keyword scoring would also plausibly match this - assert
        # source to prove which path actually won.
        orchestrator.capability_planner.plan = (
            lambda sr: dict(PLANNING_REQUIRED_PLAN)
        )

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="do something"
        )

        self.assertEqual(result["plan"]["source"], "skill_memory")
        self.assertEqual(
            result["execution"]["tool"], "draft_institutional_note"
        )

    def test_learned_skill_still_gates_on_approval_when_used(self):
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

        # Brain disabled entirely - the learned skill is the only
        # source, exactly like test_orchestrator_skill_memory_execution.py.
        skill_memory = _FakeSkillMemory("needs_approval_capability")
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
            model_reasoning_gateway=None,
            skill_memory=skill_memory,
            enable_model_reasoning_shadow=False,
            approval_gate=approval_gate,
        )
        orchestrator.capability_registry = registry

        result = orchestrator.process_user_input(
            session_id="s1", user_text="do the risky thing"
        )

        self.assertEqual(result["plan"]["source"], "skill_memory")
        self.assertEqual(
            result["execution"]["status"], "awaiting_approval"
        )
        self.assertEqual(fake_dispatcher.calls, [])


class CrossTurnAttemptHistoryTests(_IsolatedOrchestratorCase):
    """The immediately preceding turn's Brain attempt history survives
    into the next turn's reasoning request - real evidence for the
    user's next message - and is cleared once a turn is satisfied."""

    def test_unsatisfied_turn_carries_into_the_next_turn(self):
        captured_requests = []

        gateway = ModelReasoningGateway(
            model_callable=_capturing_callable(
                {
                    0: {"action": {"capability": "draft_institutional_note"}},
                    # Turn 1's evaluation call - no "evaluation" key at
                    # all, so _model_evaluation returns None
                    # ("evaluation_unavailable") - a realistic case
                    # since real models sometimes drop the expected
                    # shape entirely.
                    1: {"objective": "not the expected evaluation shape"},
                },
                captured_requests,
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        orchestrator.capability_planner.plan = (
            lambda sr: dict(PLANNING_REQUIRED_PLAN)
        )
        orchestrator.skill_memory.find_matching_skill = (
            lambda sr: None
        )

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        first = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note about policy X"
        )

        self.assertFalse(first["brain_evaluation"]["satisfied"])
        self.assertEqual(
            first["brain_evaluation"]["status"], "evaluation_unavailable"
        )

        session = orchestrator.session_manager.get_session("s1")
        self.assertEqual(
            session.last_goal_text, "draft a note about policy X"
        )
        self.assertIsNotNone(session.last_goal_attempt_history)
        self.assertEqual(len(session.last_goal_attempt_history), 1)

        # A second, unrelated-looking message on the same session -
        # the carried history must reach the Brain's next request.
        second = orchestrator.process_user_input(
            session_id="s1", user_text="no, that's not what I meant"
        )

        self.assertEqual(len(captured_requests), 3)
        second_turn_request = captured_requests[2]
        carried = second_turn_request.get("attempt_history")
        self.assertTrue(carried)
        self.assertEqual(
            carried[0]["goal"], "draft a note about policy X"
        )

        # Read-once: consumed now, not left sitting in session state.
        session_after = orchestrator.session_manager.get_session("s1")
        self.assertIsNone(session_after.last_goal_attempt_history)

    def test_rejection_message_leads_the_brain_to_a_different_action(
        self,
    ):
        captured_requests = []
        call_count = {"n": 0}

        def _model(request_json):
            request = json.loads(request_json)
            captured_requests.append(request)
            call_count["n"] += 1

            if call_count["n"] == 1:
                # Turn 1, initial proposal.
                return json.dumps(
                    {"action": {"capability": "extract_student_records"}}
                )

            if call_count["n"] == 2:
                # Turn 1's own in-turn evaluation call - nothing
                # evaluation-shaped, so this turn stops cleanly after
                # its one execution (evaluation_unavailable) and
                # carries its history forward, rather than continuing
                # to a second action within the SAME turn.
                return json.dumps({"objective": "not evaluation-shaped"})

            if call_count["n"] == 3:
                # Turn 2's initial call: the carried attempt_history
                # from turn 1 (its goal + real result) plus the user's
                # new, rejecting message is real evidence - propose
                # something different instead of repeating the same
                # action.
                self.assertTrue(request.get("attempt_history"))
                return json.dumps(
                    {
                        "evaluation": {
                            "satisfied": False,
                            "reason": (
                                "The user rejected the previous record "
                                "lookup - try drafting a note instead."
                            ),
                        },
                        "action": {
                            "capability": "draft_institutional_note"
                        },
                    }
                )

            # Turn 2's own in-turn evaluation call, after
            # draft_institutional_note executed - satisfied this time,
            # so turn 2 stops cleanly after its one new action.
            return json.dumps(
                {
                    "evaluation": {
                        "satisfied": True,
                        "reason": "This now answers the request.",
                    }
                }
            )

        gateway = ModelReasoningGateway(model_callable=_model)
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        orchestrator.capability_planner.plan = (
            lambda sr: dict(PLANNING_REQUIRED_PLAN)
        )
        orchestrator.skill_memory.find_matching_skill = lambda sr: None

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        first = orchestrator.process_user_input(
            session_id="s1", user_text="look up the student record"
        )
        self.assertEqual(
            first["execution"]["tool"], "extract_student_records"
        )
        self.assertFalse(first["brain_evaluation"]["satisfied"])

        second = orchestrator.process_user_input(
            session_id="s1", user_text="no, that's not what I wanted"
        )

        self.assertEqual(
            second["execution"]["tool"], "draft_institutional_note"
        )
        self.assertEqual(second["plan"]["source"], "model_reasoning")
        self.assertEqual(len(dispatcher.calls), 2)
        self.assertEqual(dispatcher.calls[0][0], "extract_student_records")
        self.assertEqual(dispatcher.calls[1][0], "draft_institutional_note")

    def test_satisfied_turn_does_not_carry_forward(self):
        captured_requests = []
        gateway = ModelReasoningGateway(
            model_callable=_capturing_callable(
                {
                    0: {"action": {"capability": "draft_institutional_note"}},
                    1: {
                        "evaluation": {
                            "satisfied": True,
                            "reason": "This fully answers the request.",
                        }
                    },
                },
                captured_requests,
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        orchestrator.capability_planner.plan = (
            lambda sr: dict(PLANNING_REQUIRED_PLAN)
        )
        orchestrator.skill_memory.find_matching_skill = lambda sr: None

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        first = orchestrator.process_user_input(
            session_id="s1", user_text="draft the note"
        )
        self.assertTrue(first["brain_evaluation"]["satisfied"])

        session = orchestrator.session_manager.get_session("s1")
        self.assertIsNone(session.last_goal_text)
        self.assertIsNone(session.last_goal_attempt_history)

        orchestrator.process_user_input(
            session_id="s1", user_text="thanks, one more thing"
        )

        third_call_request = captured_requests[2]
        self.assertEqual(
            third_call_request.get("attempt_history"), []
        )


if __name__ == "__main__":
    unittest.main()
