"""Milestone 13 Part 2: proves the canonical loop's two remaining
interaction hooks -

1. USER NOT SATISFIED / TRY AGAIN: a generic interaction_signal label
   (MISSING_INFORMATION or RESULT_NOT_ACCEPTED_OR_INCOMPLETE) reaches
   the Brain's next-turn reasoning request whenever the previous turn
   left something unresolved (a pending clarification or an
   unsatisfied result) - URI only detects and names the condition; the
   Brain decides what to do with it. The post-execution re-evaluation
   loop can also now pause on a targeted clarification instead of
   giving up when the Brain has no further action to propose.

2. USER ACCEPTS: once the Brain judges a result satisfied, URI asks it
   a single dedicated question - what is genuinely worth retaining for
   a future, different request - and controls validation/
   classification/persistence of whatever candidate comes back.

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
from uri_core.core.experience_store import ExperienceStore
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
        orchestrator.experience_store = ExperienceStore(
            storage_path=os.path.join(
                self.temp_dir.name, "experience.json"
            )
        )
        orchestrator.capability_planner.plan = (
            lambda sr: dict(PLANNING_REQUIRED_PLAN)
        )
        return orchestrator


class InteractionSignalTests(_IsolatedOrchestratorCase):

    def test_missing_information_signal_after_an_initial_clarification(
        self,
    ):
        captured = []
        gateway = ModelReasoningGateway(
            model_callable=_by_call_index(
                [
                    # Turn 1: the Brain needs more information.
                    {
                        "clarification": {"question": "Which roll number?"},
                        "action": None,
                    },
                    # Turn 2's initial call.
                    {"action": {"capability": "extract_student_records"}},
                    # Turn 2's pre-execution sanity check: confirm.
                    {"action": {"capability": "extract_student_records"}},
                    # Turn 2's post-execution evaluation: end cleanly.
                    {"objective": "not evaluation-shaped"},
                ],
                captured,
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        first = orchestrator.process_user_input(
            session_id="s1", user_text="look up the student record"
        )
        self.assertEqual(first["execution"]["status"], "waiting_for_input")
        self.assertEqual(dispatcher.calls, [])

        second = orchestrator.process_user_input(
            session_id="s1", user_text="22CS045"
        )

        turn2_initial_request = captured[1]
        self.assertEqual(
            turn2_initial_request.get("interaction_signal"),
            "MISSING_INFORMATION",
        )
        carried = turn2_initial_request.get("attempt_history")
        self.assertTrue(carried)
        self.assertEqual(
            carried[-1]["result"]["status"], "awaiting_user_response"
        )
        self.assertEqual(
            second["execution"]["tool"], "extract_student_records"
        )

    def test_result_not_accepted_signal_after_an_unsatisfied_turn(self):
        captured = []
        gateway = ModelReasoningGateway(
            model_callable=_by_call_index(
                [
                    # Turn 1: initial proposal.
                    {"action": {"capability": "extract_student_records"}},
                    # Turn 1: pre-execution sanity check, confirm.
                    {"action": {"capability": "extract_student_records"}},
                    # Turn 1: post-execution evaluation - not
                    # evaluation-shaped, ends turn 1 with a real
                    # (non-clarification) result carried forward.
                    {"objective": "not evaluation-shaped"},
                    # Turn 2's initial call.
                    {"action": {"capability": "draft_institutional_note"}},
                ],
                captured,
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        orchestrator.process_user_input(
            session_id="s1", user_text="look up the record"
        )
        orchestrator.process_user_input(
            session_id="s1", user_text="no, that's not what I wanted"
        )

        turn2_initial_request = captured[3]
        self.assertEqual(
            turn2_initial_request.get("interaction_signal"),
            "RESULT_NOT_ACCEPTED_OR_INCOMPLETE",
        )

    def test_no_signal_on_an_ordinary_fresh_turn(self):
        captured = []
        gateway = ModelReasoningGateway(
            model_callable=_by_call_index(
                [{"action": {"capability": "extract_student_records"}}],
                captured,
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        orchestrator.process_user_input(
            session_id="s1", user_text="look up the record"
        )

        self.assertIsNone(captured[0].get("interaction_signal"))


class PostExecutionClarificationTests(_IsolatedOrchestratorCase):

    def test_post_execution_evaluation_may_ask_instead_of_giving_up(self):
        gateway = ModelReasoningGateway(
            model_callable=_by_call_index(
                [
                    {"action": {"capability": "extract_student_records"}},
                    {"action": {"capability": "extract_student_records"}},
                    {
                        "evaluation": {
                            "satisfied": False,
                            "reason": "Ambiguous which record was meant.",
                        },
                        "clarification": {
                            "question": (
                                "There are two students with that "
                                "roll number pattern - which department?"
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
        self.assertIn("department", result["execution"]["message"])
        self.assertEqual(
            result["clarification"]["stage"], "post_execution_reevaluation"
        )
        self.assertNotIn("brain_evaluation", result)

        session = orchestrator.session_manager.get_session("s1")
        self.assertIsNotNone(session.last_goal_attempt_history)
        self.assertEqual(
            session.last_goal_attempt_history[-1]["result"]["status"],
            "awaiting_user_response",
        )
        # The real action taken earlier this turn is still part of the
        # carried record, not lost.
        self.assertEqual(
            session.last_goal_attempt_history[0]["proposal"]["capability"],
            "extract_student_records",
        )


class TolerantEvaluationRecoveryTests(_IsolatedOrchestratorCase):
    """Live testing found the real model sometimes names the same
    satisfaction judgment under a different, still self-evidently
    boolean key inside the SAME evaluation object (e.g.
    "result_satisfies_request") rather than the exact "satisfied" key
    - proves that recognized, without the loop mistaking a genuinely
    unevaluated response for one."""

    def test_alternate_satisfaction_key_is_recognized(self):
        gateway = ModelReasoningGateway(
            model_callable=_by_call_index(
                [
                    {"action": {"capability": "extract_student_records"}},
                    {"action": {"capability": "extract_student_records"}},
                    {
                        "evaluation": {
                            "result_satisfies_request": True,
                            "reason": "The record was found.",
                        }
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

        self.assertTrue(result["brain_evaluation"]["satisfied"])

    def test_no_evaluation_object_at_all_is_still_unavailable(self):
        # The harder case - the Brain skips evaluating entirely and
        # just proposes again in an unrelated shape - is NOT
        # tolerantly recovered; guessing intent from an unrelated
        # shape is out of bounds.
        gateway = ModelReasoningGateway(
            model_callable=_by_call_index(
                [
                    {"action": {"capability": "extract_student_records"}},
                    {"action": {"capability": "extract_student_records"}},
                    {"proposal": {"type": "capability", "capability": "x"}},
                ]
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="look up the record"
        )

        self.assertEqual(
            result["brain_evaluation"]["status"], "evaluation_unavailable"
        )


class AcceptanceRetentionTests(_IsolatedOrchestratorCase):

    def _satisfied_single_capability_gateway(self, retention_response):
        return ModelReasoningGateway(
            model_callable=_by_call_index(
                [
                    {"action": {"capability": "extract_student_records"}},
                    {"action": {"capability": "extract_student_records"}},
                    {
                        "evaluation": {
                            "satisfied": True,
                            "reason": "This answers the request.",
                        }
                    },
                    retention_response,
                ]
            )
        )

    def test_nothing_to_retain_is_the_normal_honest_outcome(self):
        gateway = self._satisfied_single_capability_gateway({})
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="look up the record"
        )

        self.assertTrue(result["brain_evaluation"]["satisfied"])
        self.assertEqual(
            result["retention"]["outcome"], "nothing_to_retain"
        )

    def test_single_capability_success_is_not_double_persisted(self):
        gateway = self._satisfied_single_capability_gateway(
            {
                "retention_candidate": {
                    "should_retain": True,
                    "category": "successful_approach",
                    "summary": "extract_student_records works for lookups.",
                }
            }
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="look up the record"
        )

        self.assertEqual(
            result["retention"]["outcome"], "candidate_received"
        )
        # Already recorded once by the existing, unconditional
        # dispatch-success auto-learn - persisted here must stay False
        # to avoid silently double-counting the exact same outcome.
        self.assertFalse(result["retention"]["persisted"])
        self.assertEqual(len(orchestrator.skill_memory.list_skills()), 1)

    def test_multi_step_workflow_success_is_persisted_via_skill_memory(
        self,
    ):
        gateway = ModelReasoningGateway(
            model_callable=_by_call_index(
                [
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
                    {
                        "evaluation": {
                            "satisfied": True,
                            "reason": "Both steps completed the request.",
                        }
                    },
                    {
                        "retention_candidate": {
                            "should_retain": True,
                            "category": "successful_approach",
                            "summary": (
                                "Look up then draft a note works for "
                                "this kind of request."
                            ),
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
        self.assertEqual(
            result["retention"]["outcome"], "candidate_received"
        )
        self.assertTrue(result["retention"]["persisted"])

        skills = orchestrator.skill_memory.list_skills()
        self.assertEqual(len(skills), 1)
        self.assertEqual(
            skills[0]["tool_name"],
            "extract_student_records+draft_institutional_note",
        )

    def test_non_successful_approach_category_is_not_persisted(self):
        gateway = self._satisfied_single_capability_gateway(
            {
                "retention_candidate": {
                    "should_retain": True,
                    "category": "user_preference",
                    "summary": "The user prefers concise institutional notes.",
                }
            }
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="look up the record"
        )

        self.assertEqual(result["retention"]["category"], "user_preference")
        self.assertFalse(result["retention"]["persisted"])
        # Only the existing unconditional single-capability auto-learn
        # entry exists - nothing new was added for this category.
        self.assertEqual(len(orchestrator.skill_memory.list_skills()), 1)

    def test_malformed_retention_response_never_breaks_brain_evaluation(
        self,
    ):
        gateway = self._satisfied_single_capability_gateway(
            "not even a JSON object"
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)
        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="look up the record"
        )

        self.assertTrue(result["brain_evaluation"]["satisfied"])
        self.assertIn(result["retention"]["outcome"], (
            "nothing_to_retain", "unavailable"
        ))


if __name__ == "__main__":
    unittest.main()
