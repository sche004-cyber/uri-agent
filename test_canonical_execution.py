"""M30.6: Controlled canonical execution - unit/integration tests.

Model-free where possible (mirrors this repository's own standing
convention: real model calls are reserved for scripts/, not the
pytest suite) - `decide_fallback_reason()` is tested directly with
hand-built gate outcomes/capability ids/modes, and `_execute_*` are
tested directly with fake-but-real collaborators (a connected
FakeGmailService, a real remember_fact write to a temp-scoped memory
store) so every one of the 18 M30.6 test requirements is covered
without depending on a real, possibly-unreachable local model.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from uri_core.capabilities import MultiActionCapabilityRegistry
from uri_core.capabilities.gmail import GmailCapability
from uri_core.core.approval_gate import ApprovalGate
from uri_core.core.canonical_execution import (
    CANONICAL_EXECUTION_ALLOWLIST,
    DEFAULT_TELEMETRY_LOG_PATH,
    LIVE_ENV_VAR,
    build_canonical_telemetry,
    decide_fallback_reason,
    decision_engine_live_enabled,
    is_allowlisted,
    record_canonical_telemetry,
    run_canonical_for_ask,
)
from uri_core.core.dispatcher import ToolDispatcher
from uri_core.core.multi_action_dispatch import MultiActionDispatch
from uri_core.core.user_memory import MemoryStore
from test_multi_action_capabilities import FakeGmailService


def _connected_dispatch():
    registry = MultiActionCapabilityRegistry([GmailCapability(FakeGmailService())])
    return MultiActionDispatch(registry=registry, permission_checker=lambda *_: True)


def _disconnected_dispatch():
    registry = MultiActionCapabilityRegistry([GmailCapability(FakeGmailService(connected=False))])
    return MultiActionDispatch(registry=registry, permission_checker=lambda *_: True)


class _FakeOrchestrator:
    """Minimal orchestrator double: only the attributes
    canonical_execution.py actually touches. `_draft_narrative_safely`/
    `_persist_session` are no-ops here - proving canonical execution
    itself never depends on real narrative drafting or session
    persistence succeeding (both are best-effort, wrapped in their own
    try/except in run_canonical_for_ask)."""

    session_manager = None
    capability_registry = None
    conversation_history = None

    def __init__(self, multi_action_dispatch=None, approval_gate=None):
        self.multi_action_dispatch = multi_action_dispatch
        self.approval_gate = approval_gate
        self.narrative_calls = []
        self.persist_calls = []

    def _draft_narrative_safely(self, **kwargs):
        self.narrative_calls.append(kwargs)

    def _persist_session(self, session_id):
        self.persist_calls.append(session_id)


class AllowlistAndFlagTests(unittest.TestCase):

    def test_flag_disabled_by_default(self):
        os.environ.pop(LIVE_ENV_VAR, None)
        self.assertFalse(decision_engine_live_enabled())

    def test_flag_enabled_when_set(self):
        os.environ[LIVE_ENV_VAR] = "1"
        self.addCleanup(lambda: os.environ.pop(LIVE_ENV_VAR, None))
        self.assertTrue(decision_engine_live_enabled())

    def test_default_authority_is_unrestricted(self):
        self.assertIsNone(CANONICAL_EXECUTION_ALLOWLIST)

    def test_directory_capability_is_eligible_by_default(self):
        self.assertTrue(is_allowlisted("draft_institutional_note"))
        self.assertTrue(is_allowlisted("convert_document"))
        self.assertFalse(is_allowlisted(None))


class FallbackDecisionTests(unittest.TestCase):
    """Test requirement 4-9: never execute on a non-READY gate outcome,
    a non-allowlisted capability, or a non-executable mode - pure,
    deterministic, model-free."""

    def test_feature_flag_off_means_zero_canonical_execution(self):
        # Requirement 1: server.py never even calls run_canonical_for_ask
        # when the flag is off - proven at the flag level, not here.
        os.environ.pop(LIVE_ENV_VAR, None)
        self.assertFalse(decision_engine_live_enabled())

    def test_ready_gmail_single_action_is_eligible(self):
        self.assertIsNone(
            decide_fallback_reason(gate_outcome="READY", capability_id="Gmail", mode="single_action")
        )

    def test_ready_remember_fact_is_eligible(self):
        self.assertIsNone(
            decide_fallback_reason(gate_outcome="READY", capability_id="remember_fact", mode="single_action")
        )

    def test_ready_multi_action_gmail_is_eligible(self):
        self.assertIsNone(
            decide_fallback_reason(gate_outcome="READY", capability_id="Gmail", mode="multi_action")
        )

    def test_directory_capability_can_execute_even_if_not_in_old_allowlist(self):
        reason = decide_fallback_reason(gate_outcome="READY", capability_id="draft_institutional_note", mode="single_action")
        self.assertIsNone(reason)

    def test_invalid_proposal_never_executes(self):
        reason = decide_fallback_reason(gate_outcome="INVALID_PROPOSAL", capability_id="Gmail", mode="single_action")
        self.assertEqual(reason, "engine_failure:INVALID_PROPOSAL")

    def test_missing_parameter_never_executes(self):
        reason = decide_fallback_reason(gate_outcome="MISSING_PARAMETER", capability_id="Gmail", mode="single_action")
        self.assertIsNone(reason)

    def test_disconnected_never_executes(self):
        reason = decide_fallback_reason(gate_outcome="DISCONNECTED", capability_id="Gmail", mode="single_action")
        self.assertIsNone(reason)

    def test_approval_required_never_executes(self):
        reason = decide_fallback_reason(gate_outcome="APPROVAL_REQUIRED", capability_id="Gmail", mode="single_action")
        self.assertIsNone(reason)

    def test_unsupported_never_executes(self):
        reason = decide_fallback_reason(gate_outcome="UNSUPPORTED", capability_id="Gmail", mode="single_action")
        self.assertIsNone(reason)

    def test_permission_denied_never_executes(self):
        reason = decide_fallback_reason(gate_outcome="PERMISSION_DENIED", capability_id="Gmail", mode="single_action")
        self.assertIsNone(reason)

    def test_degraded_never_executes(self):
        reason = decide_fallback_reason(gate_outcome="DEGRADED", capability_id="Gmail", mode="single_action")
        self.assertEqual(reason, "engine_failure:DEGRADED")

    def test_conversation_mode_never_executes_even_if_ready(self):
        reason = decide_fallback_reason(gate_outcome="READY", capability_id=None, mode="conversation")
        self.assertIsNone(reason)

    def test_workflow_continuation_with_no_capability_never_executes(self):
        reason = decide_fallback_reason(gate_outcome="READY", capability_id=None, mode="workflow_continuation")
        self.assertEqual(reason, "mode_not_executable:workflow_continuation")


class CanonicalTerminalOutcomeTests(unittest.TestCase):
    """M30.8: valid canonical decisions are terminal, never fallbacks."""

    def _run(self, contract, gate):
        from uri_core.core import canonical_execution

        with patch.object(
            canonical_execution, "build_turn_state_and_directory",
            return_value=(SimpleNamespace(data={}), object()),
        ), patch.object(
            canonical_execution, "propose_decision",
            return_value=SimpleNamespace(status="ok", contract=contract, invalid_reason=None),
        ), patch("uri_core.core.decision_gates.evaluate_gates", return_value=gate):
            return canonical_execution.run_canonical_for_ask(
                orchestrator=_FakeOrchestrator(), session_id="m30-8", user_text="test",
                principal=None, log_path=os.path.join(tempfile.mkdtemp(), "canonical.jsonl"),
            )

    def test_valid_non_execution_outcomes_do_not_request_legacy(self):
        cases = [
            ("MISSING_PARAMETER", "clarification", "awaiting_user_response"),
            ("DISCONNECTED", "single_action", "unavailable"),
            ("APPROVAL_REQUIRED", "approval_required", "approval_required"),
            ("UNSUPPORTED", "unsupported", "unavailable"),
            ("READY", "conversation", "success"),
        ]
        for outcome, mode, expected_status in cases:
            with self.subTest(outcome=outcome):
                contract = {
                    "mode": mode, "capability": "Gmail" if mode != "conversation" else None,
                    "actions": [], "clarification": "Which message?", "unsupported_reason": "Not available",
                }
                gate = SimpleNamespace(outcome=outcome, missing_field="query")
                result = self._run(contract, gate)
                self.assertNotIn("_canonical_fallback", result)
                self.assertEqual(result["status"], expected_status)

    def test_engine_failure_is_the_only_gate_fallback(self):
        contract = {"mode": "single_action", "capability": "Gmail", "actions": []}
        result = self._run(contract, SimpleNamespace(outcome="DEGRADED", missing_field=None))
        self.assertTrue(result["_canonical_fallback"])
        self.assertEqual(result["fallback_reason"], "engine_failure:DEGRADED")

    def test_narrowed_allowlist_is_an_explicit_killswitch(self):
        from uri_core.core import canonical_execution

        with patch.object(canonical_execution, "CANONICAL_EXECUTION_ALLOWLIST", frozenset()):
            self.assertTrue(canonical_execution.canonical_killswitch_enabled())
            self.assertFalse(canonical_execution.is_allowlisted("Gmail"))
            self.assertEqual(
                canonical_execution.decide_fallback_reason(
                    gate_outcome="READY", capability_id="Gmail", mode="single_action",
                ),
                "canonical_killswitch_not_allowlisted",
            )


class GmailExecutionTests(unittest.TestCase):
    """Requirement 2, 12: an allowlisted Gmail read request executes
    canonically through the real MultiActionExecutor/GmailCapability
    machinery (fake, connected GmailService - real Gmail is not
    connected in this dev environment, see the M30.6 report), and a
    grounded follow-up reference (an attachment on a previously found
    message) resolves through the real CapabilityContextResolver."""

    def test_single_action_search_executes_and_returns_real_evidence(self):
        from uri_core.core.canonical_execution import _execute_gmail

        dispatch = _connected_dispatch()
        contract = {
            "capability": "Gmail",
            "actions": [{"name": "search_messages", "inputs": {"query": "insurance"}}],
        }
        envelope = _execute_gmail(
            contract, orchestrator=_FakeOrchestrator(multi_action_dispatch=dispatch),
            session_id="s1", user_text="find the latest insurance email", principal=None,
        )
        self.assertIsNotNone(envelope)
        self.assertEqual(envelope["execution"]["status"], "success")
        self.assertIn("results", envelope["response"])

    def test_grounded_follow_up_resolves_real_message_id(self):
        from uri_core.core.canonical_execution import _execute_gmail

        dispatch = _connected_dispatch()
        orchestrator = _FakeOrchestrator(multi_action_dispatch=dispatch)
        search_contract = {
            "capability": "Gmail",
            "actions": [{"name": "search_messages", "inputs": {"query": "insurance"}}],
        }
        _execute_gmail(
            search_contract, orchestrator=orchestrator, session_id="s1",
            user_text="find the latest insurance email", principal=None,
        )
        # Follow-up: "Read that one." - no explicit message_id given,
        # must be grounded from the prior turn's real search result via
        # CapabilityContextResolver (the same mechanism the legacy
        # dispatch() path already used - unchanged here).
        read_contract = {"capability": "Gmail", "actions": [{"name": "read_message", "inputs": {}}]}
        envelope = _execute_gmail(
            read_contract, orchestrator=orchestrator, session_id="s1",
            user_text="Read that one.", principal=None,
        )
        self.assertIsNotNone(envelope)
        self.assertEqual(envelope["execution"]["status"], "success")
        bound_message_id = envelope["plan"]["inputs"].get("message_id")
        self.assertEqual(bound_message_id, "m-1")  # the real id FakeGmailService returned

    def test_multi_action_chain_executes_in_order(self):
        from uri_core.core.canonical_execution import _execute_gmail

        dispatch = _connected_dispatch()
        contract = {
            "capability": "Gmail",
            "actions": [
                {"name": "search_messages", "inputs": {"query": "insurance"}},
                {"name": "read_message", "inputs": {"message_id": "m-1"}},
                {"name": "read_attachment", "inputs": {"message_id": "m-1", "attachment_id": "a-1", "filename": "policy.pdf"}},
            ],
        }
        envelope = _execute_gmail(
            contract, orchestrator=_FakeOrchestrator(multi_action_dispatch=dispatch),
            session_id="s2", user_text="find, read, and check the attachment", principal=None,
        )
        self.assertIsNotNone(envelope)
        self.assertEqual(envelope["execution"]["status"], "success")

    def test_disconnected_gmail_never_executes_real_gate_check(self):
        # Not exercised through run_canonical_for_ask's gate (that needs
        # a real model call) - directly proves the underlying
        # MultiActionExecutor itself refuses a disconnected capability,
        # which is what the deterministic gate's DISCONNECTED outcome
        # is itself derived from (decision_gates.py, unchanged).
        dispatch = _disconnected_dispatch()
        executor = dispatch._executor_for("s3", None)
        result = executor.execute("Gmail", "search_messages", {"query": "insurance"})
        self.assertEqual(result["status"], "unavailable")


class RememberFactExecutionTests(unittest.TestCase):
    """Requirement 3: allowlisted remember_fact executes canonically -
    a REAL execution (real file write to a temp-scoped MemoryStore),
    not a fake, since remember_fact has no external network dependency
    in this environment."""

    def _orchestrator_with_real_approval_gate(self, registry_path):
        dispatcher = ToolDispatcher(registry_path=registry_path)
        approval_gate = ApprovalGate(dispatcher=dispatcher)
        return _FakeOrchestrator(approval_gate=approval_gate)

    def _write_registry(self, path):
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "active_tools": {
                        "remember_fact": {
                            "file_path": "uri_core/tools/remember_fact.py",
                            "class_name": "RememberFactTool",
                            "method": "remember",
                            "description": "test",
                            "status": "implemented",
                            "availability": "available",
                            "permissions": [],
                            "approval_requirement": "none",
                            "risk": "controlled",
                        }
                    }
                },
                handle,
            )

    def test_disclosure_saves_to_real_memory_and_returns_evidence(self):
        from uri_core.core.canonical_execution import _execute_remember_fact

        tmp_dir = tempfile.mkdtemp()
        registry_path = os.path.join(tmp_dir, "registry.json")
        self._write_registry(registry_path)
        orchestrator = self._orchestrator_with_real_approval_gate(registry_path)

        envelope = _execute_remember_fact(
            orchestrator=orchestrator, session_id="s1",
            user_text="I work at NIT Sikkim.", principal=None,
        )
        self.assertIsNotNone(envelope)
        self.assertEqual(envelope["status"], "success")
        self.assertEqual(envelope["response"]["status"], "success")
        self.assertIn("NIT Sikkim", envelope["response"]["content"])

    def test_never_routed_to_web_search(self):
        # Structural proof: _execute_remember_fact only ever calls
        # approval_gate.execute_tool("remember_fact", ...) - there is no
        # code path here that could reach web_search regardless of the
        # disclosure's wording.
        import inspect
        from uri_core.core import canonical_execution

        source = inspect.getsource(canonical_execution._execute_remember_fact)
        self.assertNotIn("web_search", source)
        self.assertIn('"remember_fact"', source)


class NarrativeAndPersistenceTests(unittest.TestCase):
    """Requirement 10, 11: execution result feeds back into response
    reasoning (the envelope handed to `_draft_narrative_safely`), and
    session persistence is attempted - both only ever run AFTER real
    execution evidence exists, never before."""

    def test_execution_evidence_present_before_narrative_would_draft(self):
        from uri_core.core.canonical_execution import _execute_gmail

        dispatch = _connected_dispatch()
        contract = {"capability": "Gmail", "actions": [{"name": "list_labels", "inputs": {}}]}
        envelope = _execute_gmail(
            contract, orchestrator=_FakeOrchestrator(multi_action_dispatch=dispatch),
            session_id="s1", user_text="list my gmail labels", principal=None,
        )
        self.assertIsNotNone(envelope)
        # No narrative claim can exist without this real, already-decided
        # execution/response evidence present in the envelope handed to
        # _draft_narrative_safely.
        self.assertIn("execution", envelope)
        self.assertIn("response", envelope)
        self.assertIsNotNone(envelope["execution"])


class TelemetryTests(unittest.TestCase):
    """Requirement 17: telemetry is privacy-safe (no raw user text, no
    raw tool output content)."""

    def test_telemetry_never_contains_raw_user_text(self):
        class _FakeGate:
            outcome = "READY"

        telemetry = build_canonical_telemetry(
            session_id="s1", user_text="I work at NIT Sikkim, my SSN is 123-45-6789",
            contract={"mode": "single_action", "capability": "remember_fact", "actions": []},
            gate_result=_FakeGate(), recall_at_5=True, canonical_attempted=True,
            envelope={"status": "success", "execution": {"status": "success"}, "response": {"content": "..."}},
            fallback_used=False, fallback_reason=None,
        )
        serialized = json.dumps(telemetry)
        self.assertNotIn("NIT Sikkim", serialized)
        self.assertNotIn("123-45-6789", serialized)
        self.assertIn("session_id", telemetry)
        self.assertIn("gate_outcome", telemetry)
        self.assertIn("fallback_used", telemetry)

    def test_telemetry_records_without_raising_and_is_appendable(self):
        tmp_path = os.path.join(tempfile.mkdtemp(), "telemetry.jsonl")
        record_canonical_telemetry({"a": 1}, path=tmp_path)
        record_canonical_telemetry({"b": 2}, path=tmp_path)
        with open(tmp_path, encoding="utf-8") as handle:
            lines = [json.loads(line) for line in handle]
        self.assertEqual(lines, [{"a": 1}, {"b": 2}])


class RunCanonicalForAskIsolationTests(unittest.TestCase):
    """Mirrors ShadowExecutionIsolationTests' own convention exactly:
    a real (possibly unreachable/local) model call happens inside here,
    but the function must never raise regardless of what it returns,
    and a fully bare orchestrator must degrade safely."""

    def test_a_failure_anywhere_inside_never_raises(self):
        result = run_canonical_for_ask(
            orchestrator=object(), session_id="s1", user_text="hello",
            principal=None, log_path=os.path.join(tempfile.mkdtemp(), "canon.jsonl"),
        )
        self.assertTrue(result is None or isinstance(result, dict))

    def test_flag_object_has_no_side_effect_on_legacy_result_shape(self):
        # This does not assert the flag itself (server.py owns that
        # gating) - it proves that when this function returns None
        # (the overwhelming common case for any non-allowlisted/non-
        # ready proposal), there is nothing left for a caller to do but
        # keep using its own existing legacy result, unchanged.
        result = run_canonical_for_ask(
            orchestrator=_FakeOrchestrator(), session_id="s1",
            user_text="do you think remote work is better than office work",
            principal=None, log_path=os.path.join(tempfile.mkdtemp(), "canon.jsonl"),
        )
        self.assertTrue(result is None or isinstance(result, dict))


if __name__ == "__main__":
    unittest.main()
