import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from uri_core.core.approval_store import (
    ApprovalNotFoundError,
    ApprovalStateError,
    ApprovalStore,
    ApprovalValidationError,
    ProposedAction,
    STATUS_APPROVED,
    STATUS_CONSUMED,
    STATUS_EXPIRED,
    STATUS_PENDING,
    STATUS_REJECTED,
)


class ApprovalStoreProposeTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = os.path.join(
            self.temp_dir.name, "approvals.json"
        )
        self.store = ApprovalStore(storage_path=self.storage_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_propose_creates_a_pending_action(self):
        action = self.store.propose(
            capability_id="pc_system_optimization",
            arguments={"request_text": "clean up my disk"},
            session_id="session-1",
        )

        self.assertIsInstance(action, ProposedAction)
        self.assertEqual(action.status, STATUS_PENDING)
        self.assertTrue(action.action_id)
        self.assertEqual(action.capability_id, "pc_system_optimization")
        self.assertEqual(action.session_id, "session-1")

    def test_propose_persists_across_separate_store_instances(self):
        action = self.store.propose(
            capability_id="pc_system_optimization",
            arguments={"x": "y"},
        )

        reloaded = ApprovalStore(
            storage_path=self.storage_path
        ).get(action.action_id)

        self.assertIsNotNone(reloaded)
        self.assertEqual(reloaded.action_id, action.action_id)
        self.assertEqual(reloaded.status, STATUS_PENDING)

    def test_propose_rejects_credential_shaped_argument_value(self):
        with self.assertRaises(ApprovalValidationError):
            self.store.propose(
                capability_id="pc_system_optimization",
                arguments={"note": "sk-obviouslysecretvalue"},
            )

    def test_propose_rejects_credential_shaped_argument_key(self):
        with self.assertRaises(ApprovalValidationError):
            self.store.propose(
                capability_id="pc_system_optimization",
                arguments={"api_key": "x"},
            )

    def test_two_proposals_get_distinct_action_ids(self):
        first = self.store.propose(
            capability_id="pc_system_optimization", arguments={}
        )
        second = self.store.propose(
            capability_id="pc_system_optimization", arguments={}
        )

        self.assertNotEqual(first.action_id, second.action_id)


class ApprovalStoreDecideTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = os.path.join(
            self.temp_dir.name, "approvals.json"
        )
        self.store = ApprovalStore(storage_path=self.storage_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_decide_approved_transitions_to_approved(self):
        action = self.store.propose(
            capability_id="cap", arguments={}, session_id="s1"
        )

        decided = self.store.decide(
            action.action_id, approved=True, session_id="s1"
        )

        self.assertEqual(decided.status, STATUS_APPROVED)
        self.assertIsNotNone(decided.decided_at)

    def test_decide_rejected_transitions_to_rejected(self):
        action = self.store.propose(capability_id="cap", arguments={})

        decided = self.store.decide(action.action_id, approved=False)

        self.assertEqual(decided.status, STATUS_REJECTED)

    def test_decide_unknown_action_id_fails_closed(self):
        with self.assertRaises(ApprovalNotFoundError):
            self.store.decide("does-not-exist", approved=True)

    def test_decide_twice_on_the_same_action_fails_closed(self):
        action = self.store.propose(capability_id="cap", arguments={})
        self.store.decide(action.action_id, approved=True)

        with self.assertRaises(ApprovalStateError):
            self.store.decide(action.action_id, approved=True)

    def test_decide_from_a_different_session_fails_closed_without_mutating_state(
        self,
    ):
        action = self.store.propose(
            capability_id="cap", arguments={}, session_id="session-a"
        )

        with self.assertRaises(ApprovalStateError):
            self.store.decide(
                action.action_id, approved=True, session_id="session-b"
            )

        # The mismatch must not have poisoned the action - it stays
        # pending, so the real proposing session can still decide it
        # correctly.
        still_pending = self.store.get(action.action_id)
        self.assertEqual(still_pending.status, STATUS_PENDING)

        correctly_decided = self.store.decide(
            action.action_id, approved=True, session_id="session-a"
        )
        self.assertEqual(correctly_decided.status, STATUS_APPROVED)

    def test_decide_an_expired_pending_action_fails_closed(self):
        action = self.store.propose(capability_id="cap", arguments={})
        self._backdate(action.action_id, minutes=20)

        with self.assertRaises(ApprovalStateError):
            self.store.decide(action.action_id, approved=True)

    def _backdate(self, action_id: str, minutes: int) -> None:
        with open(self.storage_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        stale = (
            datetime.now(timezone.utc) - timedelta(minutes=minutes)
        ).isoformat()

        for raw in data["actions"]:
            if raw["action_id"] == action_id:
                raw["created_at"] = stale

        with open(self.storage_path, "w", encoding="utf-8") as file:
            json.dump(data, file)


class ApprovalStoreConsumeTests(unittest.TestCase):
    """The requirements this milestone must prove: no approval ->
    blocked, wrong approval -> blocked, approval for action A cannot
    authorize action B, valid approval -> allowed, replay is blocked,
    stale/expired fails closed."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = os.path.join(
            self.temp_dir.name, "approvals.json"
        )
        self.store = ApprovalStore(storage_path=self.storage_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _propose_and_approve(self, **kwargs):
        action = self.store.propose(**kwargs)
        return self.store.decide(
            action.action_id,
            approved=True,
            session_id=kwargs.get("session_id"),
        )

    def test_no_approval_at_all_is_blocked(self):
        with self.assertRaises(ApprovalNotFoundError):
            self.store.consume(
                "never-proposed",
                capability_id="cap",
                arguments={},
            )

    def test_pending_but_not_yet_decided_is_blocked(self):
        action = self.store.propose(capability_id="cap", arguments={})

        with self.assertRaises(ApprovalStateError):
            self.store.consume(
                action.action_id, capability_id="cap", arguments={}
            )

    def test_rejected_action_is_blocked(self):
        action = self.store.propose(capability_id="cap", arguments={})
        self.store.decide(action.action_id, approved=False)

        with self.assertRaises(ApprovalStateError):
            self.store.consume(
                action.action_id, capability_id="cap", arguments={}
            )

    def test_valid_approval_is_allowed_exactly_once(self):
        approved = self._propose_and_approve(
            capability_id="cap", arguments={"x": "y"}, session_id="s1"
        )

        consumed = self.store.consume(
            approved.action_id,
            capability_id="cap",
            arguments={"x": "y"},
            session_id="s1",
        )

        self.assertEqual(consumed.status, STATUS_CONSUMED)

    def test_replaying_a_consumed_approval_is_blocked(self):
        approved = self._propose_and_approve(
            capability_id="cap", arguments={}, session_id="s1"
        )

        self.store.consume(
            approved.action_id,
            capability_id="cap",
            arguments={},
            session_id="s1",
        )

        with self.assertRaises(ApprovalStateError):
            self.store.consume(
                approved.action_id,
                capability_id="cap",
                arguments={},
                session_id="s1",
            )

    def test_approval_cannot_authorize_a_different_capability(self):
        # Action A was approved for "draft_note" - trying to use that
        # same approval to run "delete_everything" must fail.
        approved = self._propose_and_approve(
            capability_id="draft_note",
            arguments={"text": "hello"},
            session_id="s1",
        )

        with self.assertRaises(ApprovalStateError):
            self.store.consume(
                approved.action_id,
                capability_id="delete_everything",
                arguments={"text": "hello"},
                session_id="s1",
            )

    def test_approval_cannot_authorize_different_arguments(self):
        # Same capability, different arguments than what was approved.
        approved = self._propose_and_approve(
            capability_id="cap",
            arguments={"amount": "10"},
            session_id="s1",
        )

        with self.assertRaises(ApprovalStateError):
            self.store.consume(
                approved.action_id,
                capability_id="cap",
                arguments={"amount": "999999"},
                session_id="s1",
            )

    def test_approval_cannot_be_consumed_from_a_different_session(self):
        approved = self._propose_and_approve(
            capability_id="cap", arguments={}, session_id="session-a"
        )

        with self.assertRaises(ApprovalStateError):
            self.store.consume(
                approved.action_id,
                capability_id="cap",
                arguments={},
                session_id="session-b",
            )

    def test_expired_approved_action_is_blocked(self):
        approved = self._propose_and_approve(
            capability_id="cap", arguments={}, session_id="s1"
        )
        self._backdate(approved.action_id, minutes=20)

        with self.assertRaises(ApprovalStateError):
            self.store.consume(
                approved.action_id,
                capability_id="cap",
                arguments={},
                session_id="s1",
            )

    def _backdate(self, action_id: str, minutes: int) -> None:
        with open(self.storage_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        stale = (
            datetime.now(timezone.utc) - timedelta(minutes=minutes)
        ).isoformat()

        for raw in data["actions"]:
            if raw["action_id"] == action_id:
                raw["created_at"] = stale

        with open(self.storage_path, "w", encoding="utf-8") as file:
            json.dump(data, file)


class ApprovalStoreFailClosedOnCorruptionTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = os.path.join(
            self.temp_dir.name, "approvals.json"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_corrupted_file_degrades_to_no_approvals(self):
        with open(self.storage_path, "w", encoding="utf-8") as file:
            file.write("{ not valid json")

        store = ApprovalStore(storage_path=self.storage_path)

        self.assertEqual(store._load(), [])

        with self.assertRaises(ApprovalNotFoundError):
            store.consume("anything", capability_id="cap", arguments={})

    def test_missing_file_degrades_to_no_approvals(self):
        store = ApprovalStore(storage_path=self.storage_path)

        with self.assertRaises(ApprovalNotFoundError):
            store.decide("anything", approved=True)


if __name__ == "__main__":
    unittest.main()
