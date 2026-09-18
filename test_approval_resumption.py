"""test_approval_resumption.py — M32.1.

Tests uri_core/core/approval_resumption.py (natural-language approval
resumption) and the M32.1 canonical_execution.py bridge that gives
Gmail/multi-action approval-required actions a real, durable
ApprovalStore action_id for the first time (previously: none, live-
confirmed during this milestone's own exploration).

Real collaborators throughout - real ApprovalStore (temp file), real
ApprovalGate, real MultiActionDispatch + real GmailCapability, only the
Gmail SERVICE backend is faked (FakeGmailService, this repo's own
established fixture) - mirrors test_m32_c2_c3_native_tool_loop.py's own
"model-free where possible, dispatch never mocked" convention.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from types import SimpleNamespace

from uri_core.capabilities import MultiActionCapabilityRegistry
from uri_core.capabilities.gmail import GmailCapability
from uri_core.core.approval_gate import ApprovalGate
from uri_core.core.approval_store import ApprovalStore
from uri_core.core.approval_resumption import (
    classify_confirmation,
    find_resumable_actions,
    resume_pending_approval,
)
from uri_core.core.canonical_execution import _execute_canonical
from uri_core.core.capability_registry import CapabilityRegistry
from uri_core.core.dispatcher import ToolDispatcher
from uri_core.core.multi_action_dispatch import MultiActionDispatch
from uri_core.core.state import SessionManager
from test_multi_action_capabilities import FakeGmailService


def _make_orchestrator(connected_gmail=True):
    tmp = tempfile.mkdtemp()
    cap_registry = CapabilityRegistry()
    dispatcher = ToolDispatcher()
    approval_store = ApprovalStore(storage_path=os.path.join(tmp, "approvals.json"))
    approval_gate = ApprovalGate(
        dispatcher=dispatcher, capability_registry=cap_registry, approval_store=approval_store,
    )
    gmail_service = FakeGmailService(connected=connected_gmail)
    gmail_registry = MultiActionCapabilityRegistry([GmailCapability(gmail_service)])
    mad = MultiActionDispatch(
        registry=gmail_registry, capability_registry=cap_registry,
        permission_checker=lambda *_: True,
    )
    session_manager = SessionManager(storage_path=os.path.join(tmp, "sessions"))
    orchestrator = SimpleNamespace(
        session_manager=session_manager, capability_registry=cap_registry,
        multi_action_dispatch=mad, approval_gate=approval_gate, conversation_history=None,
    )
    return orchestrator, gmail_service


_DRAFT_CONTRACT = {
    "mode": "single_action", "capability": "Gmail",
    "actions": [{"name": "create_draft", "inputs": {"to": "a@example.com", "subject": "hi", "body": "hello"}}],
}


def _propose_draft(orchestrator, session_id):
    return _execute_canonical(
        _DRAFT_CONTRACT, orchestrator=orchestrator, session_id=session_id,
        user_text="draft an email to a@example.com", principal=None,
    )


class ClassifyConfirmationTests(unittest.TestCase):
    def test_clear_affirmatives(self):
        for text in ["yes", "Yes", "YES!", "yep", "approve", "go ahead", "do it", "ok", "okay.", "sure"]:
            self.assertTrue(classify_confirmation(text), text)

    def test_clear_negatives(self):
        for text in ["no", "No.", "cancel", "never mind", "stop", "reject"]:
            self.assertFalse(classify_confirmation(text), text)

    def test_ambiguous_returns_none(self):
        for text in [
            "yes but also can you check my calendar",
            "maybe",
            "what does that mean",
            "yesterday I sent an email",
            "",
            "   ",
        ]:
            self.assertIsNone(classify_confirmation(text), text)

    def test_substring_inside_longer_sentence_never_matches(self):
        # "yes" appears inside a genuinely new, unrelated request - must
        # never be misread as a confirmation of something else.
        self.assertIsNone(classify_confirmation("yesterday's meeting notes please"))


class DurableGmailApprovalBridgeTests(unittest.TestCase):
    """The canonical_execution.py fix: an approval-required Gmail action
    now gets a real, durable action_id - previously it had none at all."""

    def test_approval_required_gmail_action_gets_real_action_id(self):
        orchestrator, _ = _make_orchestrator()
        envelope = _propose_draft(orchestrator, "s1")
        self.assertEqual(envelope["execution"]["status"], "awaiting_approval")
        action_id = envelope["execution"]["action_id"]
        self.assertTrue(action_id)
        pending = orchestrator.approval_gate.approval_store.list_pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].action_id, action_id)
        self.assertEqual(pending[0].capability_id, "Gmail")
        self.assertEqual(pending[0].action_name, "create_draft")

    def test_no_side_effect_before_approval(self):
        orchestrator, gmail_service = _make_orchestrator()
        _propose_draft(orchestrator, "s1")
        self.assertEqual(gmail_service.drafts, [], "proposing must never itself create the draft")


class ResumptionScenarioTests(unittest.TestCase):
    """The User's own explicit six-scenario list, each proven directly."""

    def test_scenario_1_approval_requested_turn_1(self):
        orchestrator, _ = _make_orchestrator()
        envelope = _propose_draft(orchestrator, "s1")
        self.assertEqual(envelope["status"], "success")
        self.assertEqual(envelope["execution"]["status"], "awaiting_approval")

    def test_scenario_2_natural_language_approval_resumes_correct_action(self):
        orchestrator, gmail_service = _make_orchestrator()
        _propose_draft(orchestrator, "s1")
        result = resume_pending_approval(orchestrator=orchestrator, session_id="s1", user_text="yes")
        self.assertIsNotNone(result)
        self.assertEqual(result["execution"]["status"], "success")
        self.assertEqual(gmail_service.drafts, [{"to": "a@example.com", "subject": "hi", "body": "hello"}])

    def test_scenario_3_duplicate_approval_does_not_execute_twice(self):
        orchestrator, gmail_service = _make_orchestrator()
        _propose_draft(orchestrator, "s1")
        first = resume_pending_approval(orchestrator=orchestrator, session_id="s1", user_text="yes")
        second = resume_pending_approval(orchestrator=orchestrator, session_id="s1", user_text="yes")
        self.assertIsNotNone(first)
        self.assertIsNone(second, "a second 'yes' with nothing pending must fall through, never re-dispatch")
        self.assertEqual(len(gmail_service.drafts), 1, "the draft must only ever be created once")

    def test_scenario_3b_duplicate_approval_via_explicit_stale_action_id_fails_honestly(self):
        """Same invariant, proven at the ApprovalStore layer directly -
        a second decide() for an already-decided action_id must fail
        closed, never silently succeed."""
        orchestrator, _ = _make_orchestrator()
        envelope = _propose_draft(orchestrator, "s1")
        action_id = envelope["execution"]["action_id"]
        store = orchestrator.approval_gate.approval_store
        store.decide(action_id, approved=True, session_id="s1")
        with self.assertRaises(Exception):
            store.decide(action_id, approved=True, session_id="s1")

    def test_scenario_4_wrong_session_cannot_resume(self):
        orchestrator, gmail_service = _make_orchestrator()
        _propose_draft(orchestrator, "s1")
        result = resume_pending_approval(orchestrator=orchestrator, session_id="s2-different", user_text="yes")
        self.assertIsNone(result, "a different session must never see another session's pending action")
        self.assertEqual(gmail_service.drafts, [])
        # The action must still be genuinely pending for its real session.
        pending = find_resumable_actions(orchestrator.approval_gate.approval_store, "s1")
        self.assertEqual(len(pending), 1)

    def test_scenario_5_stale_expired_approval_fails_safely(self):
        orchestrator, gmail_service = _make_orchestrator()
        envelope = _propose_draft(orchestrator, "s1")
        action_id = envelope["execution"]["action_id"]
        store = orchestrator.approval_gate.approval_store
        # Force expiry deterministically rather than sleeping 15 minutes.
        actions = store._load()
        for action in actions:
            if action.action_id == action_id:
                action.created_at = "2000-01-01T00:00:00+00:00"
        store._save(actions)
        result = resume_pending_approval(orchestrator=orchestrator, session_id="s1", user_text="yes")
        # list_pending() already excludes expired actions, so resumption
        # correctly finds nothing to resume (falls through) rather than
        # ever executing an expired approval.
        self.assertIsNone(result)
        self.assertEqual(gmail_service.drafts, [])

    def test_scenario_6_ambiguous_multiple_pending_requires_clarification(self):
        orchestrator, gmail_service = _make_orchestrator()
        _propose_draft(orchestrator, "s1")
        second_contract = {
            "mode": "single_action", "capability": "Gmail",
            "actions": [{"name": "create_draft", "inputs": {"to": "b@example.com", "subject": "hey", "body": "hi"}}],
        }
        _execute_canonical(second_contract, orchestrator=orchestrator, session_id="s1", user_text="draft another", principal=None)

        result = resume_pending_approval(orchestrator=orchestrator, session_id="s1", user_text="yes")
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "clarification_required")
        self.assertEqual(len(result["execution"]["pending_actions"]), 2)
        self.assertEqual(gmail_service.drafts, [], "an ambiguous confirmation must never guess and execute either one")

    def test_rejection_cancels_without_executing(self):
        orchestrator, gmail_service = _make_orchestrator()
        _propose_draft(orchestrator, "s1")
        result = resume_pending_approval(orchestrator=orchestrator, session_id="s1", user_text="no")
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(gmail_service.drafts, [])
        # The action is now REJECTED, not pending - a later "yes" must
        # not resurrect it.
        follow_up = resume_pending_approval(orchestrator=orchestrator, session_id="s1", user_text="yes")
        self.assertIsNone(follow_up)
        self.assertEqual(gmail_service.drafts, [])

    def test_non_confirmation_text_never_resumes(self):
        orchestrator, gmail_service = _make_orchestrator()
        _propose_draft(orchestrator, "s1")
        result = resume_pending_approval(
            orchestrator=orchestrator, session_id="s1", user_text="what's the weather like",
        )
        self.assertIsNone(result)
        self.assertEqual(gmail_service.drafts, [])

    def test_no_pending_action_never_resumes(self):
        orchestrator, gmail_service = _make_orchestrator()
        result = resume_pending_approval(orchestrator=orchestrator, session_id="s1", user_text="yes")
        self.assertIsNone(result)


class RestartRecoveryTests(unittest.TestCase):
    """ApprovalStore is file-backed - a fresh instance pointed at the
    same file must see the SAME pending action, proving durability
    survives process restart, not merely in-memory session lifetime."""

    def test_pending_action_survives_fresh_store_instance(self):
        orchestrator, gmail_service = _make_orchestrator()
        envelope = _propose_draft(orchestrator, "s1")
        action_id = envelope["execution"]["action_id"]
        storage_path = orchestrator.approval_gate.approval_store.storage_path

        # Simulate a restart: a brand new ApprovalStore instance, same file.
        fresh_store = ApprovalStore(storage_path=storage_path)
        fresh_orchestrator = SimpleNamespace(
            approval_gate=SimpleNamespace(approval_store=fresh_store, decide=orchestrator.approval_gate.decide),
            multi_action_dispatch=orchestrator.multi_action_dispatch,
        )
        pending = find_resumable_actions(fresh_store, "s1")
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].action_id, action_id)

        result = resume_pending_approval(orchestrator=fresh_orchestrator, session_id="s1", user_text="yes")
        self.assertIsNotNone(result)
        self.assertEqual(result["execution"]["status"], "success")
        self.assertEqual(gmail_service.drafts, [{"to": "a@example.com", "subject": "hi", "body": "hello"}])


if __name__ == "__main__":
    unittest.main()
