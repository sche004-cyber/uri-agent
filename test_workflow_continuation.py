"""Focused M30.7 coverage for durable continuation state and its guarded path."""

import os
import json
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from uri_core.core.decision_engine import DecisionOutcome
from uri_core.core.decision_gates import evaluate_gates
from uri_core.core.model_reasoning_gateway import ModelReasoningGateway
from uri_core.core.state import SessionManager
from uri_core.core.turn_state import _project_active_pointer
from uri_core.core.orchestrator import UriOrchestrator


class _Directory:
    def describe(self, capability_id):
        if capability_id != "Gmail":
            return None
        return {
            "actions": ["search_messages"], "availability_known": True,
            "available": True, "availability_reason": None,
            "action_schemas": {"search_messages": {"required": ["query"],
                "parameters": {"query": {"type": "string"}}}},
            "permission_required": False, "approval_required": False,
        }

    def overlaps(self):
        return []


def _decision():
    return DecisionOutcome(status="ok", contract={
        "goal": "find mail", "mode": "workflow_continuation",
        "capability": None, "actions": [], "clarification": None,
        "unsupported_reason": None, "requires_approval": False,
        "confidence": "high", "reason": "answer supplies query",
    })


class DurableMetadataTests(unittest.TestCase):
    def test_pre_execution_check_threads_proposed_capability_into_pause(self):
        """A sanity-check clarification retains the original capability."""
        with tempfile.TemporaryDirectory() as temp_dir:
            responses = iter((
                {"action": {"capability": "remember_fact"}},
                {"clarification": {"question": "Which mailbox query?"}},
            ))
            gateway = ModelReasoningGateway(
                model_callable=lambda _request: json.dumps(next(responses))
            )
            orchestrator = UriOrchestrator(
                model_reasoning_gateway=gateway,
                enable_model_reasoning_shadow=True,
                enable_skill_router_shadow=False,
                enable_response_narrative=False,
                session_manager=SessionManager(
                    storage_path=os.path.join(temp_dir, "sessions")
                ),
            )
            orchestrator.skill_memory.find_matching_skill = lambda _result: None
            orchestrator.capability_planner.plan = (
                lambda _result: {"status": "planning_required", "tool_name": None}
            )
            orchestrator._should_run_pre_execution_sanity_check = (
                lambda **_kwargs: True
            )

            result = orchestrator.process_user_input(
                session_id="pre-execution-capability", user_text="Search my email."
            )

            self.assertEqual(result["execution"]["status"], "waiting_for_input")
            self.assertEqual(
                result["pre_execution_check"]["outcome"], "clarification_needed"
            )
            session = orchestrator.session_manager.get_session(
                "pre-execution-capability"
            )
            proposal = session.last_goal_attempt_history[-1]["proposal"]
            self.assertEqual(proposal["capability_id"], "remember_fact")

    def test_post_execution_reevaluation_threads_last_capability_into_pause(self):
        """The reevaluation pause retains the real preceding capability."""
        orchestrator = UriOrchestrator.__new__(UriOrchestrator)
        orchestrator.max_brain_iterations = 2
        orchestrator._run_model_reasoning = Mock(return_value={})
        orchestrator._model_evaluation = Mock(return_value={
            "satisfied": False, "reason": "need the query",
        })
        orchestrator._model_proposed_capability = Mock(return_value=None)
        orchestrator._model_proposed_workflow = Mock(return_value=None)
        orchestrator._model_clarification = Mock(return_value={
            "question": "What should I search for?",
        })
        orchestrator._record_brain_reevaluation_audit = Mock()
        orchestrator._apply_clarification_pause = Mock()

        orchestrator._continue_brain_evaluation_loop(
            user_text="Search my email.",
            session=SimpleNamespace(),
            session_id="test-session",
            personalization_context={},
            response={"execution": {"status": "success"}},
            first_proposal_description={
                "type": "capability", "capability": "Gmail",
            },
        )

        self.assertEqual(
            orchestrator._apply_clarification_pause.call_args.kwargs[
                "capability_id"
            ],
            "Gmail",
        )
        self.assertEqual(
            orchestrator._apply_clarification_pause.call_args.kwargs["stage"],
            "post_execution_reevaluation",
        )

    def test_active_workflow_projection_preserves_action_and_known_inputs(self):
        session = SimpleNamespace(
            active_workflow={
                "goal": "Find the student.",
                "capability": "StudentRecords",
                "action": "extract_student_records",
            },
            active_workflow_question="What is the roll number?",
            active_workflow_required_field="roll_number",
            active_workflow_status="waiting_for_input",
            current_facts={"department": "CS"},
        )
        pointer = _project_active_pointer(session)
        self.assertEqual(pointer["action"], "extract_student_records")
        self.assertEqual(pointer["known_inputs"], {"department": "CS"})

    def test_attempt_history_projection_preserves_paused_action_metadata(self):
        session = SimpleNamespace(active_workflow=None, active_workflow_question=None,
            active_workflow_required_field=None, active_workflow_status=None,
            last_goal_attempt_history=[{"goal": "Find mail", "proposal": {
                "type": "clarification", "question": "Which query?",
                "capability_id": "Gmail", "action": "search_messages",
                "known_inputs": {"label": "INBOX"}, "missing_field": "query"},
                "result": {"status": "awaiting_user_response"}}])
        pointer = _project_active_pointer(session)
        self.assertEqual(pointer["capability_id"], "Gmail")
        self.assertEqual(pointer["action"], "search_messages")
        self.assertEqual(pointer["known_inputs"], {"label": "INBOX"})
        self.assertEqual(pointer["missing_field"], "query")

    def test_enabled_gate_resolves_pointer_and_merges_answer(self):
        with patch.dict(os.environ, {"URI_ENABLE_WORKFLOW_CONTINUATION_MODE": "1"}, clear=False):
            result = evaluate_gates(_decision(), capability_directory=_Directory(), turn_state_data={
                "turn": {"user_text": "is:unread"}, "active_pointer": {
                    "kind": "awaiting_clarification_answer", "capability_id": "Gmail",
                    "action": "search_messages", "known_inputs": {}, "missing_field": "query"}})
        self.assertEqual(result.outcome, "READY")
        self.assertEqual(result.capability_id, "Gmail")
        self.assertEqual(result.action_names, ["search_messages"])

    def test_flag_explicit_off_retains_placeholder_continuation_result(self):
        # M32 B1.5: the continuation flag now defaults ON (see
        # test_flag_enabled_by_default_requires_durable_capability below) -
        # this proves the opt-out ("0") still restores the pre-B1.5
        # pass-through placeholder behaviour for a workflow_continuation
        # contract with no continuation-specific enrichment.
        with patch.dict(os.environ, {"URI_ENABLE_WORKFLOW_CONTINUATION_MODE": "0"}, clear=True):
            result = evaluate_gates(_decision(), capability_directory=_Directory(), turn_state_data={})
        self.assertEqual((result.outcome, result.capability_id), ("READY", None))

    def test_flag_enabled_by_default_requires_durable_capability(self):
        # M32 B1.5: with the flag unset (now the committed default), the
        # continuation-specific validation actually runs - a contract with
        # no capability and no active pointer is correctly rejected as an
        # invalid continuation, not silently passed through as READY.
        with patch.dict(os.environ, {}, clear=True):
            result = evaluate_gates(_decision(), capability_directory=_Directory(), turn_state_data={})
        self.assertEqual(result.outcome, "INVALID_PROPOSAL")
        self.assertIn("continuation_no_durable_capability", result.reasons)


class AskPrecedenceTests(unittest.TestCase):
    def _call_ask(self, observed_mode, observed_gate, canonical_result):
        from uri_core.app import server
        session = SimpleNamespace(active_workflow={"goal": "old"}, active_workflow_status="waiting_for_input")
        calls = []
        orchestrator = SimpleNamespace(
            session_manager=SimpleNamespace(get_session=lambda _sid: session),
            _clear_active_workflow=lambda value: setattr(value, "active_workflow", None),
            process_user_input=lambda **_: calls.append(True) or {"status": "success", "session_id": "s", "error": None,
                "semantic_analysis": None, "execution": None, "response": {"message": "fresh"}, "narrative": None},
        )
        context = SimpleNamespace(orchestrator=orchestrator, profile_store=SimpleNamespace(load_or_create=lambda: {}),
            memory_store=SimpleNamespace(list_all=lambda: []))
        def canonical(**kwargs):
            kwargs["decision_observer"]({"mode": observed_mode}, SimpleNamespace(outcome=observed_gate))
            return canonical_result
        with patch.dict(os.environ, {"URI_ENABLE_WORKFLOW_CONTINUATION_MODE": "1", "URI_ENABLE_DECISION_ENGINE_LIVE": "0"}, clear=False), \
             patch.object(server, "_resolve_context", return_value=context), \
             patch.object(server, "build_personalization_context", return_value={}), \
             patch("uri_core.core.canonical_execution.run_canonical_for_ask", side_effect=canonical), \
             patch("uri_core.core.canonical_execution.decision_engine_live_enabled", return_value=False):
            answer = server.ask(server.AskRequest(session_id="s", text="new goal"), user_id=None)
        return answer, session, calls

    def test_ready_continuation_returns_early_without_legacy_resume(self):
        canonical = {"status": "success", "session_id": "s", "error": None,
            "semantic_analysis": None, "execution": {"status": "success"},
            "response": {"message": "continued"}, "narrative": None}
        answer, _session, calls = self._call_ask("workflow_continuation", "READY", canonical)
        self.assertEqual(answer["response"]["message"], "continued")
        self.assertEqual(calls, [])

    def test_nonready_continuation_falls_through_without_clearing_pointer(self):
        _answer, session, calls = self._call_ask("workflow_continuation", "MISSING_PARAMETER", None)
        self.assertIsNotNone(session.active_workflow)
        self.assertEqual(calls, [True])

    def test_topic_change_clears_pending_workflow_then_uses_fresh_legacy_turn(self):
        from uri_core.app import server
        session = SimpleNamespace(active_workflow={"goal": "old"}, active_workflow_status="waiting_for_input")
        orchestrator = SimpleNamespace(
            session_manager=SimpleNamespace(get_session=lambda _sid: session),
            _clear_active_workflow=lambda value: setattr(value, "active_workflow", None),
            process_user_input=lambda **_: {"status": "success", "session_id": "s", "error": None,
                "semantic_analysis": None, "execution": None, "response": {"message": "fresh"}, "narrative": None},
        )
        context = SimpleNamespace(orchestrator=orchestrator, profile_store=SimpleNamespace(load_or_create=lambda: {}),
            memory_store=SimpleNamespace(list_all=lambda: []))
        with patch.dict(os.environ, {"URI_ENABLE_WORKFLOW_CONTINUATION_MODE": "1"}, clear=False), \
             patch.object(server, "_resolve_context", return_value=context), \
             patch.object(server, "build_personalization_context", return_value={}), \
             patch("uri_core.core.canonical_execution.run_canonical_for_ask", side_effect=lambda **kwargs: kwargs["decision_observer"]({"mode": "conversation"}, SimpleNamespace(outcome="READY"))):
            answer = server.ask(server.AskRequest(session_id="s", text="new goal"), user_id=None)
        self.assertIsNone(session.active_workflow)
        self.assertEqual(answer["response"]["message"], "fresh")
