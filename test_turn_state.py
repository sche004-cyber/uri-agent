"""M30.1: Turn State is a read-only projection over existing live
state - these tests prove it assembles a coherent view from real
collaborator shapes (fakes matching their real interfaces, not mocks
of turn_state.py's own internals) without fabricating anything it
wasn't given, and that nothing sensitive leaks into the projection.

Nothing here touches uri_core.core.orchestrator - this module is not
wired into the production /ask path in this milestone (see turn_state.py's
own module docstring). Production-unchanged is proven separately, by the
existing full regression suite and by re-running M30.0's six live
/ask traces (see the M30.1 completion report, not this file).
"""

import unittest

from uri_core.core.turn_state import assemble_turn_state


class _FakePrincipal:
    """Carries a sensitive-looking attribute alongside user_id, to
    prove only user_id ever reaches the projection (test 11)."""

    def __init__(self, user_id, api_key="sk-should-never-appear"):
        self.user_id = user_id
        self.api_key = api_key


class _FakeSession:
    def __init__(
        self,
        active_workflow=None,
        active_workflow_status=None,
        active_workflow_required_field=None,
        active_workflow_question=None,
        last_goal_attempt_history=None,
        fact_history=None,
    ):
        self.active_workflow = active_workflow
        self.active_workflow_status = active_workflow_status
        self.active_workflow_required_field = active_workflow_required_field
        self.active_workflow_question = active_workflow_question
        self.last_goal_attempt_history = last_goal_attempt_history
        self.fact_history = fact_history or {}


class _FakeFact:
    def __init__(self, value, status):
        self.value = value
        self.status = status


class _FakeConversationHistoryStore:
    def __init__(self, turns):
        self._turns = turns

    def get_session(self, session_id):
        return self._turns


class _FakeCapabilityFeasibility:
    def __init__(self, snapshot):
        self._snapshot = snapshot

    def snapshot(self):
        return self._snapshot


class _FakeMultiActionRegistry:
    def __init__(self, summaries):
        self._summaries = summaries

    def capability_summaries(self):
        return self._summaries


class _FakeHealthTracker:
    def __init__(self, healthy_pairs):
        self._healthy = set(healthy_pairs)

    def is_healthy(self, provider_id, model):
        return (provider_id, model) in self._healthy


class BasicAssemblyTests(unittest.TestCase):

    def test_assembles_successfully_for_a_normal_conversation(self):
        result = assemble_turn_state(user_text="hello", session_id="s1")
        self.assertIn("turn", result.data)
        self.assertIn("recent_conversation", result.data)
        self.assertIn("capability_summaries", result.data)

    def test_latest_user_turn_is_correctly_represented(self):
        result = assemble_turn_state(user_text="how many unread emails", session_id="s1")
        self.assertEqual(result.data["turn"]["user_text"], "how many unread emails")
        self.assertEqual(result.data["turn"]["session_id"], "s1")


class RecentConversationTests(unittest.TestCase):

    def test_recent_conversation_appears_in_correct_order(self):
        turns = [
            {"user_text": "first message", "response_text": "first reply"},
            {"user_text": "second message", "response_text": "second reply"},
            {"user_text": "third message", "response_text": "third reply"},
        ]
        store = _FakeConversationHistoryStore(turns)

        result = assemble_turn_state(
            user_text="fourth message",
            session_id="s1",
            conversation_history_store=store,
        )

        projected = result.data["recent_conversation"]
        self.assertEqual(len(projected), 3)
        self.assertEqual(projected[0]["user"], "first message")
        self.assertEqual(projected[-1]["user"], "third message")

    def test_bounded_to_the_recent_limit(self):
        turns = [{"user_text": f"m{i}", "response_text": f"r{i}"} for i in range(20)]
        store = _FakeConversationHistoryStore(turns)

        result = assemble_turn_state(
            user_text="latest",
            session_id="s1",
            conversation_history_store=store,
            recent_conversation_limit=3,
        )

        self.assertEqual(len(result.data["recent_conversation"]), 3)
        self.assertEqual(result.data["recent_conversation"][-1]["user"], "m19")


class GroundedResultAndFactsTests(unittest.TestCase):

    def test_existing_grounded_action_result_can_be_projected(self):
        session = _FakeSession(
            last_goal_attempt_history=[
                {
                    "goal": "look up the record",
                    "proposal": {"capability": "extract_student_records"},
                    "result": {"status": "success", "data": {"roll_number": "B250012CS"}},
                }
            ]
        )

        result = assemble_turn_state(user_text="anything", session_id="s1", session=session)

        self.assertEqual(len(result.data["attempt_history"]), 1)
        self.assertEqual(
            result.data["attempt_history"][0]["result"]["data"]["roll_number"], "B250012CS"
        )

    def test_existing_session_facts_can_be_represented(self):
        session = _FakeSession(
            fact_history={"workplace": [_FakeFact(value="NIT Sikkim", status="CONFIRMED")]}
        )

        result = assemble_turn_state(user_text="anything", session_id="s1", session=session)

        self.assertEqual(
            result.data["session_facts"],
            [{"name": "workplace", "value": "NIT Sikkim", "status": "CONFIRMED"}],
        )


class CapabilityAvailabilityTests(unittest.TestCase):

    def test_gmail_connected_state_is_represented_correctly(self):
        feasibility = _FakeCapabilityFeasibility(
            {"gmail_search": {"description": "Search Gmail", "usable": True, "gap_reason": None,
                               "requires_approval": False, "risk": "low"}}
        )

        result = assemble_turn_state(
            user_text="anything", session_id="s1", capability_feasibility=feasibility
        )

        entry = result.data["capability_summaries"][0]
        self.assertEqual(entry["id"], "gmail_search")
        self.assertTrue(entry["usable"])
        self.assertIsNone(entry["gap_reason"])
        self.assertTrue(entry["availability_known"])

    def test_gmail_disconnected_state_is_represented_correctly(self):
        feasibility = _FakeCapabilityFeasibility(
            {"gmail_search": {"description": "Search Gmail", "usable": False,
                               "gap_reason": "not_connected", "requires_approval": False,
                               "risk": "low"}}
        )

        result = assemble_turn_state(
            user_text="anything", session_id="s1", capability_feasibility=feasibility
        )

        entry = result.data["capability_summaries"][0]
        self.assertFalse(entry["usable"])
        self.assertEqual(entry["gap_reason"], "not_connected")

    def test_multi_action_summaries_honestly_report_availability_unknown(self):
        # Stage 1 §11.6's own finding, made structurally visible: M27's
        # summary stage has no connection signal yet - never fabricated
        # as usable=True here.
        registry = _FakeMultiActionRegistry(
            [{"name": "gmail", "description": "Gmail multi-action capability"}]
        )

        result = assemble_turn_state(
            user_text="anything", session_id="s1", multi_action_registry=registry
        )

        entry = result.data["capability_summaries"][0]
        self.assertEqual(entry["source"], "multi_action")
        self.assertIsNone(entry["usable"])
        self.assertFalse(entry["availability_known"])


class MissingInformationHonestyTests(unittest.TestCase):

    def test_missing_runtime_information_is_absent_never_fabricated(self):
        result = assemble_turn_state(user_text="anything", session_id=None)

        self.assertEqual(result.data["recent_conversation"], [])
        self.assertEqual(result.data["capability_summaries"], [])
        self.assertIsNone(result.data["runtime_health"]["healthy"])
        self.assertEqual(result.data["durable_memory_relevant"], [])
        self.assertEqual(result.data["graph_context"], {})
        self.assertIn("recent_conversation", result.unavailable_fields)
        self.assertIn("capability_summaries", result.unavailable_fields)
        self.assertIn("runtime_health", result.unavailable_fields)
        self.assertIn("durable_memory_relevant", result.unavailable_fields)
        self.assertIn("graph_context", result.unavailable_fields)
        self.assertIn("grounded_entities", result.unavailable_fields)

    def test_runtime_health_reports_unknown_not_false_without_a_tracker(self):
        result = assemble_turn_state(
            user_text="anything",
            session_id="s1",
            active_provider_id="ollama",
            active_model="qwen3:14b",
        )
        # A provider/model IS known here, but no health tracker was given -
        # must stay None ("unknown"), never silently become False.
        self.assertIsNone(result.data["runtime_health"]["healthy"])


class DurableContextPassthroughTests(unittest.TestCase):

    def test_durable_memory_and_graph_context_are_pass_through_only(self):
        memory = [{"content": "prefers short official notes", "category": "preference"}]
        graph = {"entities": [{"id": "n1", "type": "User"}], "relationships": []}

        result = assemble_turn_state(
            user_text="anything",
            session_id="s1",
            durable_memory_relevant=memory,
            graph_context=graph,
        )

        self.assertEqual(result.data["durable_memory_relevant"], memory)
        self.assertEqual(result.data["graph_context"], graph)
        self.assertNotIn("durable_memory_relevant", result.unavailable_fields)
        self.assertNotIn("graph_context", result.unavailable_fields)

    def test_capability_index_hint_is_additive_only(self):
        # Graphify Foundation (docs/plans/M30_GRAPHIFY_FOUNDATION_PLAN.md
        # §A.4): the same additive-key discipline as graph_context above,
        # applied to the new capability_index_hint field.
        without_hint = assemble_turn_state(user_text="anything", session_id="s1")
        hint = [{"id": "capability:Gmail", "kind": "capability"}]
        with_hint = assemble_turn_state(
            user_text="anything", session_id="s1", capability_index_hint=hint,
        )

        for key in without_hint.data:
            if key == "capability_index_hint":
                continue
            self.assertEqual(
                without_hint.data[key], with_hint.data[key],
                f"supplying capability_index_hint must not change the '{key}' section",
            )

        self.assertEqual(with_hint.data["capability_index_hint"], hint)
        self.assertEqual(without_hint.data["capability_index_hint"], [])
        self.assertIn("capability_index_hint", without_hint.unavailable_fields)
        self.assertNotIn("capability_index_hint", with_hint.unavailable_fields)


class PendingInteractionStateTests(unittest.TestCase):

    def test_pending_clarification_state_can_be_represented(self):
        session = _FakeSession(
            active_workflow_status="waiting_for_input",
            active_workflow_question="What is the student's roll number?",
        )

        result = assemble_turn_state(user_text="B250012CS", session_id="s1", session=session)

        pointer = result.data["active_pointer"]
        self.assertEqual(pointer["kind"], "awaiting_clarification_answer")
        self.assertEqual(pointer["question"], "What is the student's roll number?")

    def test_no_pending_state_reports_kind_none(self):
        session = _FakeSession()
        result = assemble_turn_state(user_text="hello", session_id="s1", session=session)
        self.assertEqual(result.data["active_pointer"]["kind"], "none")

    def test_real_ordinary_clarification_pause_shape_is_now_detected(self):
        # M30.5A bugfix: this is the EXACT shape a real, on-disk session
        # file has after "Find the student." -> pending roll number
        # (inspected directly this milestone) - active_workflow_question
        # stays null; the real signal is last_goal_attempt_history. This
        # used to silently report kind="none" here, which is why
        # workflow_continuation was never reachable for this - the most
        # common - continuation scenario in any prior milestone's tests.
        session = _FakeSession(
            last_goal_attempt_history=[
                {
                    "goal": "Find the student.",
                    "proposal": {
                        "type": "clarification",
                        "question": "What is the student's roll number?",
                    },
                    "result": {"status": "awaiting_user_response", "data": None},
                }
            ]
        )

        result = assemble_turn_state(user_text="B250012CS", session_id="s1", session=session)

        pointer = result.data["active_pointer"]
        self.assertEqual(pointer["kind"], "awaiting_clarification_answer")
        self.assertEqual(pointer["question"], "What is the student's roll number?")
        self.assertEqual(pointer["originating_goal"], "Find the student.")

    def test_expected_type_is_inferred_generically_from_field_name(self):
        session = _FakeSession(
            active_workflow_status="waiting_for_input",
            active_workflow_question="What is the roll number?",
            active_workflow_required_field="roll_number",
        )
        result = assemble_turn_state(user_text="B250012CS", session_id="s1", session=session)
        self.assertEqual(result.data["active_pointer"]["expected_type"], "identifier")

    def test_ordinary_clarification_pause_honestly_leaves_missing_field_unknown(self):
        # This mechanism's real shape carries no separately-named
        # field - must stay None, never guessed from free text.
        session = _FakeSession(
            last_goal_attempt_history=[
                {
                    "goal": "Find the student.",
                    "proposal": {"type": "clarification", "question": "Which one?"},
                    "result": {"status": "awaiting_user_response", "data": None},
                }
            ]
        )
        result = assemble_turn_state(user_text="B250012CS", session_id="s1", session=session)
        self.assertIsNone(result.data["active_pointer"]["missing_field"])
        self.assertIsNone(result.data["active_pointer"]["expected_type"])


class SensitiveDataExclusionTests(unittest.TestCase):

    def test_principal_object_never_appears_only_its_user_id_does(self):
        principal = _FakePrincipal(user_id="user-42")

        result = assemble_turn_state(
            user_text="anything", session_id="s1", principal=principal
        )

        self.assertEqual(result.data["turn"]["principal_id"], "user-42")
        import json

        serialized = json.dumps(result.data)
        self.assertNotIn("sk-should-never-appear", serialized)
        self.assertNotIn("api_key", serialized)


if __name__ == "__main__":
    unittest.main()
