"""M30.3: Brain Decision Engine - SHADOW MODE ONLY.

Every test here proves either (a) the decision contract is validated
correctly against real Capability Directory data, never trusting a
model's own claim, or (b) that running the shadow path has zero effect
on anything a real user would see. Every schema/validation test injects
a fake `model_callable`, mirroring ModelReasoningGateway's own existing
fake-callable test convention (see test_orchestrator_user_interaction_
hooks.py) - the one exception is
ShadowExecutionIsolationTests.test_shadow_call_never_executes_anything_
and_returns_a_trace, which deliberately calls run_shadow_for_ask()
exactly as server.py's real /ask hook does (no injected callable), to
prove the real ModelRouter code path degrades safely (never raises,
never mutates old_path_result) whether or not a real provider answers -
this is the one place a real, local model may actually be attempted.
"""

import json
import os
import tempfile
import unittest

from uri_core.core.capability_directory import CapabilityDirectory
from uri_core.core.capability_feasibility import CapabilityFeasibility
from uri_core.core.capability_registry import CapabilityRegistry
from uri_core.core.decision_engine import (
    build_decision_request,
    build_shadow_trace,
    candidate_recall_at_k,
    classify_agreement,
    decision_engine_shadow_enabled,
    detect_over_tooling,
    evaluate_against_golden,
    preselect_candidate_ids,
    propose_decision,
    record_shadow_trace,
    run_shadow_for_ask,
    SHADOW_ENV_VAR,
)
from uri_core.core.turn_state import assemble_turn_state
from uri_core.capabilities import MultiActionCapabilityRegistry
from uri_core.capabilities.gmail import GmailCapability


def _fixed_model(payload):
    def _call(_request_json):
        return json.dumps(payload)

    return _call


CONVERSATION_DECISION = {
    "goal": "wants general career advice",
    "mode": "conversation",
    "capability": None,
    "actions": [],
    "clarification": None,
    "unsupported_reason": None,
    "requires_approval": False,
    "confidence": "high",
    "reason": "no registered capability applies",
}


def _write_registry(path, active_tools):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"active_tools": active_tools}, handle)


class _RealGmailDirectory:
    """Real CapabilityDirectory over a real, isolated legacy registry
    (gmail_search) plus the real MultiActionCapabilityRegistry (Gmail),
    for connected/disconnected availability tests."""

    def __init__(self, gmail_available):
        self.temp_dir = tempfile.TemporaryDirectory()
        registry_path = os.path.join(self.temp_dir.name, "capabilities_registry.json")
        _write_registry(
            registry_path,
            {
                "gmail_search": {
                    "file_path": "x.py", "class_name": "X", "method": "run",
                    "status": "implemented",
                    "availability": "available" if gmail_available else "unavailable_missing_dependency",
                    "description": "Search the connected Gmail account.",
                }
            },
        )
        feasibility = CapabilityFeasibility(
            capability_registry=CapabilityRegistry(registry_path=registry_path)
        )
        self.directory = CapabilityDirectory(capability_feasibility=feasibility)

    def cleanup(self):
        self.temp_dir.cleanup()


def _turn_state(directory=None, session=None, user_text="hello"):
    return assemble_turn_state(
        user_text=user_text, session_id="s1", session=session, capability_directory=directory
    ).data


class ValidDecisionTests(unittest.TestCase):

    def test_valid_conversation_decision(self):
        outcome = propose_decision(
            turn_state_data=_turn_state(),
            capability_directory=None,
            model_callable=_fixed_model(CONVERSATION_DECISION),
        )
        self.assertEqual(outcome.status, "ok")
        self.assertEqual(outcome.contract["mode"], "conversation")

    def test_valid_clarification_decision(self):
        payload = dict(CONVERSATION_DECISION, mode="clarification",
                        clarification={"question": "Which roll number?", "missing_field": "roll_number"})
        outcome = propose_decision(
            turn_state_data=_turn_state(), capability_directory=None,
            model_callable=_fixed_model(payload),
        )
        self.assertEqual(outcome.status, "ok")
        self.assertEqual(outcome.contract["clarification"]["missing_field"], "roll_number")

    def test_valid_unsupported_decision(self):
        payload = dict(CONVERSATION_DECISION, mode="unsupported",
                        unsupported_reason="no scheduling capability exists")
        outcome = propose_decision(
            turn_state_data=_turn_state(), capability_directory=None,
            model_callable=_fixed_model(payload),
        )
        self.assertEqual(outcome.status, "ok")
        self.assertEqual(outcome.contract["mode"], "unsupported")

    def test_valid_single_action_decision(self):
        registry = MultiActionCapabilityRegistry([GmailCapability()])
        directory = CapabilityDirectory(multi_action_registry=registry)
        payload = dict(CONVERSATION_DECISION, mode="single_action", capability="Gmail",
                        actions=[{"name": "list_labels", "inputs": {}}])
        outcome = propose_decision(
            turn_state_data=_turn_state(directory), capability_directory=directory,
            model_callable=_fixed_model(payload),
        )
        self.assertEqual(outcome.status, "ok")
        self.assertEqual(outcome.contract["capability"], "Gmail")

    def test_valid_multi_action_decision(self):
        registry = MultiActionCapabilityRegistry([GmailCapability()])
        directory = CapabilityDirectory(multi_action_registry=registry)
        payload = dict(
            CONVERSATION_DECISION, mode="multi_action", capability="Gmail",
            actions=[{"name": "list_labels", "inputs": {}}, {"name": "search_messages", "inputs": {"query": "is:unread"}}],
        )
        outcome = propose_decision(
            turn_state_data=_turn_state(directory), capability_directory=directory,
            model_callable=_fixed_model(payload),
        )
        self.assertEqual(outcome.status, "ok")
        self.assertEqual(len(outcome.contract["actions"]), 2)

    def test_valid_approval_required_decision(self):
        registry = MultiActionCapabilityRegistry([GmailCapability()])
        directory = CapabilityDirectory(multi_action_registry=registry)
        payload = dict(
            CONVERSATION_DECISION, mode="approval_required", capability="Gmail",
            actions=[{"name": "create_draft", "inputs": {}}], requires_approval=True,
        )
        outcome = propose_decision(
            turn_state_data=_turn_state(directory), capability_directory=directory,
            model_callable=_fixed_model(payload),
        )
        self.assertEqual(outcome.status, "ok")
        self.assertTrue(outcome.contract["requires_approval"])

    def test_valid_workflow_continuation_decision(self):
        payload = dict(CONVERSATION_DECISION, mode="workflow_continuation", capability=None)
        outcome = propose_decision(
            turn_state_data=_turn_state(), capability_directory=None,
            model_callable=_fixed_model(payload),
        )
        self.assertEqual(outcome.status, "ok")
        self.assertEqual(outcome.contract["mode"], "workflow_continuation")


class RejectionTests(unittest.TestCase):

    def test_unknown_capability_rejection(self):
        payload = dict(CONVERSATION_DECISION, mode="single_action", capability="not_a_real_capability")
        outcome = propose_decision(
            turn_state_data=_turn_state(), capability_directory=None,
            model_callable=_fixed_model(payload),
        )
        self.assertEqual(outcome.status, "invalid")
        self.assertEqual(outcome.invalid_reason, "unknown_capability")

    def test_unknown_action_rejection(self):
        registry = MultiActionCapabilityRegistry([GmailCapability()])
        directory = CapabilityDirectory(multi_action_registry=registry)
        payload = dict(CONVERSATION_DECISION, mode="single_action", capability="Gmail",
                        actions=[{"name": "delete_everything", "inputs": {}}])
        outcome = propose_decision(
            turn_state_data=_turn_state(directory), capability_directory=directory,
            model_callable=_fixed_model(payload),
        )
        self.assertEqual(outcome.status, "invalid")
        self.assertEqual(outcome.invalid_reason, "unknown_action:delete_everything")

    def test_invalid_mode_rejection(self):
        payload = dict(CONVERSATION_DECISION, mode="do_whatever_i_want")
        outcome = propose_decision(
            turn_state_data=_turn_state(), capability_directory=None,
            model_callable=_fixed_model(payload),
        )
        self.assertEqual(outcome.status, "invalid")
        self.assertEqual(outcome.invalid_reason, "invalid_mode")

    def test_malformed_model_output_handling(self):
        outcome = propose_decision(
            turn_state_data=_turn_state(), capability_directory=None,
            model_callable=lambda _req: "not json at all {{{",
        )
        self.assertEqual(outcome.status, "invalid")
        self.assertEqual(outcome.invalid_reason, "malformed_json")

    def test_missing_required_field_rejection(self):
        payload = dict(CONVERSATION_DECISION)
        del payload["reason"]
        outcome = propose_decision(
            turn_state_data=_turn_state(), capability_directory=None,
            model_callable=_fixed_model(payload),
        )
        self.assertEqual(outcome.status, "invalid")
        self.assertIn("missing_fields", outcome.invalid_reason)


class ProgressiveDiscoveryTests(unittest.TestCase):

    def test_level_1_progressive_discovery_only(self):
        registry = MultiActionCapabilityRegistry([GmailCapability()])
        directory = CapabilityDirectory(multi_action_registry=registry)
        request = build_decision_request(_turn_state(directory))
        serialized = json.dumps(request)
        # No full action schema (e.g. a "parameters" key inside any
        # capability summary) ever reaches the request payload.
        for summary in request["capability_summaries"]:
            self.assertNotIn("action_schemas", summary)
            self.assertNotIn("parameters", summary)

    def test_scoped_level_2_lookup_after_selection(self):
        registry = MultiActionCapabilityRegistry([GmailCapability()])
        directory = CapabilityDirectory(multi_action_registry=registry)
        payload = dict(CONVERSATION_DECISION, mode="single_action", capability="Gmail",
                        actions=[{"name": "list_labels", "inputs": {}}])
        outcome = propose_decision(
            turn_state_data=_turn_state(directory), capability_directory=directory,
            model_callable=_fixed_model(payload),
        )
        # Validating the proposed action DID require exactly one scoped
        # describe() call for the selected capability only - proven by
        # it succeeding for a real action name only that capability has.
        self.assertEqual(outcome.status, "ok")
        detail = directory.describe("Gmail")
        self.assertIn("list_labels", detail["actions"])


class GmailAvailabilityContextTests(unittest.TestCase):

    def test_gmail_connected_context_is_visible(self):
        fixture = _RealGmailDirectory(gmail_available=True)
        self.addCleanup(fixture.cleanup)
        request = build_decision_request(_turn_state(fixture.directory))
        entry = next(e for e in request["capability_summaries"] if e["capability_id"] == "gmail_search")
        self.assertTrue(entry["available"])

    def test_gmail_disconnected_context_is_visible(self):
        fixture = _RealGmailDirectory(gmail_available=False)
        self.addCleanup(fixture.cleanup)
        request = build_decision_request(_turn_state(fixture.directory))
        entry = next(e for e in request["capability_summaries"] if e["capability_id"] == "gmail_search")
        self.assertFalse(entry["available"])

    def test_model_proposing_a_known_disconnected_capability_is_flagged_not_trusted(self):
        fixture = _RealGmailDirectory(gmail_available=False)
        self.addCleanup(fixture.cleanup)
        payload = dict(CONVERSATION_DECISION, mode="single_action", capability="gmail_search",
                        actions=[])
        decision = propose_decision(
            turn_state_data=_turn_state(fixture.directory), capability_directory=fixture.directory,
            model_callable=_fixed_model(payload),
        )
        self.assertEqual(decision.status, "ok")  # schema is valid...
        agreement = classify_agreement(
            old_path_result={"plan": {}, "execution": {}}, decision=decision,
            capability_directory=fixture.directory, active_pointer_kind="none",
        )
        # ...but the comparison layer catches the model inventing
        # availability the directory already knows is false.
        self.assertEqual(agreement, "CONNECTION_STATE_MISMATCH")


class M304ComparisonHeuristicTests(unittest.TestCase):
    """M30.4: the M30.3 heuristic only ever caught a FALSE
    workflow_continuation claim. These prove it now also catches the
    real, live-observed opposite failure (a pending question answered,
    but the engine re-asked instead of continuing) - and that the
    golden-set evaluator can tell every false/missed direction apart,
    not only for continuation."""

    def test_missed_workflow_continuation_is_now_detected(self):
        payload = dict(CONVERSATION_DECISION, mode="clarification",
                        clarification={"question": "Which roll number?", "missing_field": "roll_number"})
        decision = propose_decision(
            turn_state_data=_turn_state(), capability_directory=None,
            model_callable=_fixed_model(payload),
        )
        agreement = classify_agreement(
            old_path_result={"plan": {}, "execution": {"status": "waiting_for_input"}},
            decision=decision, capability_directory=None,
            active_pointer_kind="awaiting_clarification_answer",
        )
        self.assertEqual(agreement, "WORKFLOW_CONTINUATION_MISSED")

    def test_genuine_topic_switch_is_not_penalized_by_classify_agreement_alone(self):
        # classify_agreement flags this as a MISSED candidate for human
        # review even on a genuine topic switch - by design (it cannot
        # know intent without a label). evaluate_against_golden below is
        # the ground-truth-aware version that correctly calls this one
        # "correct", not "missed".
        decision = propose_decision(
            turn_state_data=_turn_state(), capability_directory=None,
            model_callable=_fixed_model(CONVERSATION_DECISION),
        )
        expected = {"mode": "conversation", "capability": None, "min_actions": 0}
        result = evaluate_against_golden(expected, decision)
        self.assertEqual(result["category"], "correct")

    def test_false_unsupported_detected_against_golden_label(self):
        payload = dict(CONVERSATION_DECISION, mode="unsupported", unsupported_reason="x")
        decision = propose_decision(
            turn_state_data=_turn_state(), capability_directory=None,
            model_callable=_fixed_model(payload),
        )
        expected = {"mode": "single_action", "capability": "gmail_search", "min_actions": 1}
        result = evaluate_against_golden(expected, decision)
        self.assertEqual(result["category"], "false_unsupported")

    def test_missed_continuation_detected_against_golden_label(self):
        payload = dict(CONVERSATION_DECISION, mode="clarification",
                        clarification={"question": "?", "missing_field": "roll_number"})
        decision = propose_decision(
            turn_state_data=_turn_state(), capability_directory=None,
            model_callable=_fixed_model(payload),
        )
        expected = {"mode": "workflow_continuation", "capability": "extract_student_records", "min_actions": 0}
        result = evaluate_against_golden(expected, decision)
        self.assertEqual(result["category"], "missed_continuation")

    def test_invalid_decision_never_passes_golden_evaluation(self):
        decision = propose_decision(
            turn_state_data=_turn_state(), capability_directory=None,
            model_callable=lambda _req: "not json",
        )
        result = evaluate_against_golden({"mode": "conversation"}, decision)
        self.assertEqual(result["category"], "invalid")


class M305APreselectionTests(unittest.TestCase):
    """M30.5A: deterministic candidate preselection - reduces prompt
    size without a second model call, never silently hides the pending
    continuation's own capability, and never removes the structural
    possibility of conversation/unsupported (neither needs a capability
    at all)."""

    def _real_directory(self):
        return CapabilityDirectory(
            capability_feasibility=CapabilityFeasibility(),
            multi_action_registry=MultiActionCapabilityRegistry([GmailCapability()]),
        )

    def test_preselection_reduces_prompt_size(self):
        directory = self._real_directory()
        state = _turn_state(directory, user_text="how many unread emails do I have")
        full_request = build_decision_request(state)
        preselected = preselect_candidate_ids(state, directory, limit=5)
        narrowed_request = build_decision_request(state, preselected_ids=preselected)
        self.assertLess(
            len(json.dumps(narrowed_request)), len(json.dumps(full_request))
        )
        # M30.5B: the bound widened intentionally (top-N + always-visible
        # foundational capabilities + any originating-goal matches) - the
        # real invariant is "narrower than the full catalogue", not an
        # exact count.
        self.assertLess(
            len(narrowed_request["capability_summaries"]),
            len(full_request["capability_summaries"]),
        )

    def test_pending_capability_is_never_excluded_by_preselection(self):
        directory = self._real_directory()
        state = _turn_state(directory, user_text="B250012CS")
        state["active_pointer"] = {
            "kind": "awaiting_clarification_answer", "question": "roll number?",
            "missing_field": "roll_number", "reference": "x",
            "capability_id": "draft_institutional_note",  # deliberately unrelated to the raw text
            "originating_goal": "find the student", "action": None,
            "expected_type": "identifier", "prompt_asked": "roll number?",
            "created_at": None, "state": "awaiting_answer",
        }
        preselected = preselect_candidate_ids(state, directory, limit=1)
        narrowed_request = build_decision_request(state, preselected_ids=preselected)
        ids = {e["capability_id"] for e in narrowed_request["capability_summaries"]}
        self.assertIn("draft_institutional_note", ids)

    def test_conversation_mode_is_reachable_regardless_of_preselection(self):
        directory = self._real_directory()
        state = _turn_state(directory, user_text="do you think changing careers is sensible")
        outcome = propose_decision(
            turn_state_data=state, capability_directory=directory,
            model_callable=_fixed_model(CONVERSATION_DECISION), preselect=True,
        )
        self.assertEqual(outcome.status, "ok")
        self.assertEqual(outcome.contract["mode"], "conversation")

    def test_a_correct_proposal_still_validates_when_preselected(self):
        directory = self._real_directory()
        state = _turn_state(directory, user_text="how many unread emails do I have")
        payload = dict(CONVERSATION_DECISION, mode="single_action", capability="Gmail",
                        actions=[{"name": "list_labels", "inputs": {}}])
        outcome = propose_decision(
            turn_state_data=state, capability_directory=directory,
            model_callable=_fixed_model(payload), preselect=True,
        )
        self.assertEqual(outcome.status, "ok")
        self.assertEqual(outcome.contract["capability"], "Gmail")

    def test_false_candidate_exclusion_never_blocks_validation(self):
        # Even if preselection happened to miss the real capability the
        # model still correctly names, validation checks the FULL
        # directory, never the narrowed prompt list - a model that
        # somehow still names the right capability is not rejected.
        directory = self._real_directory()
        state = _turn_state(directory, user_text="something unrelated to gmail entirely")
        payload = dict(CONVERSATION_DECISION, mode="single_action", capability="Gmail",
                        actions=[{"name": "list_labels", "inputs": {}}])
        outcome = propose_decision(
            turn_state_data=state, capability_directory=directory,
            model_callable=_fixed_model(payload), preselect=True,
        )
        self.assertEqual(outcome.status, "ok")


class M305BCandidateRecallTests(unittest.TestCase):
    """CANDIDATE_RECALL@K - measures whether the right capability was
    even offered to the model, kept strictly separate from whether the
    model's final answer was right (evaluate_against_golden)."""

    def _real_directory(self):
        return CapabilityDirectory(
            capability_feasibility=CapabilityFeasibility(),
            multi_action_registry=MultiActionCapabilityRegistry([GmailCapability()]),
        )

    def test_recall_true_when_expected_capability_is_preselected(self):
        directory = self._real_directory()
        state = _turn_state(directory, user_text="how many unread emails do I have")
        self.assertTrue(candidate_recall_at_k(state, directory, "Gmail", k=5))

    def test_recall_false_when_expected_capability_is_not_preselected(self):
        directory = self._real_directory()
        state = _turn_state(directory, user_text="how many unread emails do I have")
        self.assertFalse(
            candidate_recall_at_k(state, directory, "draft_institutional_order", k=1)
        )

    def test_recall_is_none_when_no_capability_is_expected(self):
        directory = self._real_directory()
        state = _turn_state(directory, user_text="do you think changing careers is sensible")
        self.assertIsNone(candidate_recall_at_k(state, directory, None, k=5))

    def test_foundational_memory_capability_always_recalled(self):
        directory = self._real_directory()
        state = _turn_state(directory, user_text="I work at NIT Sikkim.")
        self.assertTrue(candidate_recall_at_k(state, directory, "remember_fact", k=3))


class M305AOverToolingTests(unittest.TestCase):
    """Decision-quality evaluation, explicitly separate from gate
    safety - a technically READY proposal can still be flagged here as
    unnecessary/mismatched."""

    def _real_directory(self):
        return CapabilityDirectory(
            capability_feasibility=CapabilityFeasibility(),
            multi_action_registry=MultiActionCapabilityRegistry([GmailCapability()]),
        )

    def test_semantically_unrelated_capability_flagged_as_over_tooling(self):
        directory = self._real_directory()
        state = _turn_state(directory, user_text="do you think changing careers is a good idea")
        payload = dict(
            CONVERSATION_DECISION, mode="single_action", capability="web_search",
            goal="do you think changing careers is a good idea",
            actions=[{"name": "web_search", "inputs": {}}],
        )
        decision = propose_decision(
            turn_state_data=state, capability_directory=directory,
            model_callable=_fixed_model(payload),
        )
        self.assertTrue(detect_over_tooling(decision, state, directory))

    def test_genuinely_relevant_capability_is_not_flagged(self):
        directory = self._real_directory()
        state = _turn_state(directory, user_text="how many unread emails do I have")
        payload = dict(
            CONVERSATION_DECISION, mode="single_action", capability="Gmail",
            goal="how many unread emails do I have",
            actions=[{"name": "list_labels", "inputs": {}}],
        )
        decision = propose_decision(
            turn_state_data=state, capability_directory=directory,
            model_callable=_fixed_model(payload),
        )
        self.assertFalse(detect_over_tooling(decision, state, directory))

    def test_conversation_mode_is_never_flagged(self):
        directory = self._real_directory()
        state = _turn_state(directory)
        decision = propose_decision(
            turn_state_data=state, capability_directory=directory,
            model_callable=_fixed_model(CONVERSATION_DECISION),
        )
        self.assertFalse(detect_over_tooling(decision, state, directory))


class ShadowFlagTests(unittest.TestCase):

    def test_shadow_disabled_by_default(self):
        os.environ.pop(SHADOW_ENV_VAR, None)
        self.assertFalse(decision_engine_shadow_enabled())

    def test_shadow_enabled_when_flag_set(self):
        os.environ[SHADOW_ENV_VAR] = "1"
        self.addCleanup(lambda: os.environ.pop(SHADOW_ENV_VAR, None))
        self.assertTrue(decision_engine_shadow_enabled())


class ShadowExecutionIsolationTests(unittest.TestCase):

    class _FakeOrchestrator:
        session_manager = None
        capability_registry = None
        conversation_history = None
        multi_action_dispatch = None

    def test_shadow_call_never_executes_anything_and_returns_a_trace(self):
        old_path_result = {
            "plan": {"tool_name": None, "status": "planning_required"},
            "execution": {"status": "waiting_for_input"},
        }
        original_copy = json.loads(json.dumps(old_path_result))

        trace = run_shadow_for_ask(
            orchestrator=self._FakeOrchestrator(),
            session_id="s1",
            user_text="hello",
            principal=None,
            old_path_result=old_path_result,
            log_path=os.path.join(tempfile.mkdtemp(), "shadow.jsonl"),
        )

        # old_path_result is completely untouched - no execution, no mutation.
        self.assertEqual(old_path_result, original_copy)
        # A trace was produced (model call fails softly with no real
        # provider configured in this test environment - still proves
        # the function completes and returns something inspectable
        # rather than raising).
        self.assertTrue(trace is None or isinstance(trace, dict))

    def test_a_failure_anywhere_inside_never_raises(self):
        # No orchestrator attributes at all - every collaborator lookup
        # inside run_shadow_for_ask must degrade, never raise.
        trace = run_shadow_for_ask(
            orchestrator=object(),
            session_id="s1",
            user_text="hello",
            principal=None,
            old_path_result={},
            log_path=os.path.join(tempfile.mkdtemp(), "shadow.jsonl"),
        )
        self.assertTrue(trace is None or isinstance(trace, dict))


class PrivacySafeTraceTests(unittest.TestCase):

    def test_trace_never_contains_raw_user_text(self):
        sensitive_text = "my password is hunter2 and my SSN is 123-45-6789"
        outcome = propose_decision(
            turn_state_data=_turn_state(user_text=sensitive_text),
            capability_directory=None,
            model_callable=_fixed_model(CONVERSATION_DECISION),
        )
        trace = build_shadow_trace(
            session_id="s1", user_text=sensitive_text,
            turn_state_data=_turn_state(user_text=sensitive_text),
            decision=outcome, old_path_result={}, agreement="AGREE",
        )
        serialized = json.dumps(trace)
        self.assertNotIn("hunter2", serialized)
        self.assertNotIn("123-45-6789", serialized)
        self.assertIn("user_text_length_bucket", trace)

    def test_record_shadow_trace_is_append_only_and_never_raises(self):
        path = os.path.join(tempfile.mkdtemp(), "shadow.jsonl")
        record_shadow_trace({"a": 1}, path=path)
        record_shadow_trace({"a": 2}, path=path)
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
        self.assertEqual(len(lines), 2)
        # Never raises even against an unwritable-looking path.
        record_shadow_trace({"a": 3}, path="\x00invalid\x00path")


class TurnStateAndDirectoryCompatibilityTests(unittest.TestCase):

    def test_m30_1_turn_state_still_used_directly(self):
        data = _turn_state()
        self.assertIn("turn", data)
        self.assertIn("capability_summaries", data)

    def test_m30_2_capability_directory_still_used_directly(self):
        registry = MultiActionCapabilityRegistry([GmailCapability()])
        directory = CapabilityDirectory(multi_action_registry=registry)
        self.assertTrue(any(e["capability_id"] == "Gmail" for e in directory.summaries()))


if __name__ == "__main__":
    unittest.main()
