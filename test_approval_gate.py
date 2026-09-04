import json
import os
import tempfile
import unittest

from uri_core.core.approval_gate import ApprovalGate
from uri_core.core.approval_store import ApprovalStore, STATUS_APPROVED
from uri_core.core.audit_trail import AuditTrail
from uri_core.core.capability_registry import CapabilityRegistry


class _FakeDispatcher:
    """Records every call it actually receives - the thing under test
    is whether ApprovalGate ever calls this without a valid approval,
    not the real ToolDispatcher's execution mechanics."""

    def __init__(self):
        self.calls = []

    def execute_tool(self, tool_name, **kwargs):
        self.calls.append((tool_name, kwargs))
        return {"status": "success", "data": {"tool": tool_name}}


def _registry(temp_dir, entries: dict) -> CapabilityRegistry:
    path = os.path.join(temp_dir, "capabilities_registry.json")
    with open(path, "w", encoding="utf-8") as file:
        json.dump({"active_tools": entries}, file)
    return CapabilityRegistry(registry_path=path)


class ApprovalGateNoApprovalRequiredTests(unittest.TestCase):
    """Regression: a capability with approval_requirement == "none"
    (every one of the 4 real tools today) must execute exactly as
    ToolDispatcher.execute_tool() always did - no detour, no proposal,
    no change in behaviour."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dispatcher = _FakeDispatcher()
        self.registry = _registry(
            self.temp_dir.name,
            {
                "draft_note": {
                    "file_path": "x.py",
                    "class_name": "X",
                    "method": "run",
                    "approval_requirement": "none",
                }
            },
        )
        self.approval_store = ApprovalStore(
            storage_path=os.path.join(
                self.temp_dir.name, "approvals.json"
            )
        )
        self.gate = ApprovalGate(
            dispatcher=self.dispatcher,
            capability_registry=self.registry,
            approval_store=self.approval_store,
            audit_trail=AuditTrail(),
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_executes_immediately_with_no_approval_step(self):
        result = self.gate.execute_tool(
            "draft_note", session_id="s1", request_text="hello"
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(self.dispatcher.calls), 1)
        self.assertEqual(self.dispatcher.calls[0][0], "draft_note")

    def test_creates_no_approval_record(self):
        self.gate.execute_tool(
            "draft_note", session_id="s1", request_text="hello"
        )

        self.assertEqual(self.approval_store._load(), [])

    def test_unregistered_capability_still_passes_through_unchanged(
        self,
    ):
        # Mirrors ToolDispatcher's own "tool not in registry" handling
        # - the gate must not intercept or change that behaviour.
        result = self.gate.execute_tool(
            "totally_unknown_tool", session_id="s1"
        )

        self.assertEqual(len(self.dispatcher.calls), 1)
        self.assertEqual(result["status"], "success")


class ApprovalGateApprovalRequiredTests(unittest.TestCase):
    """The core Milestone 7 requirements: no approval -> blocked,
    wrong approval -> blocked, valid approval -> allowed, model output
    alone cannot approve."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dispatcher = _FakeDispatcher()
        self.registry = _registry(
            self.temp_dir.name,
            {
                "pc_system_optimization": {
                    "file_path": "x.py",
                    "class_name": "X",
                    "method": "run",
                    "approval_requirement": "user_approval_required",
                    "risk": "high",
                }
            },
        )
        self.approval_store = ApprovalStore(
            storage_path=os.path.join(
                self.temp_dir.name, "approvals.json"
            )
        )
        self.audit = AuditTrail()
        self.gate = ApprovalGate(
            dispatcher=self.dispatcher,
            capability_registry=self.registry,
            approval_store=self.approval_store,
            audit_trail=self.audit,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_execute_tool_never_calls_the_dispatcher_directly(self):
        result = self.gate.execute_tool(
            "pc_system_optimization",
            session_id="s1",
            request_text="optimize my pc",
        )

        self.assertEqual(result["status"], "awaiting_approval")
        self.assertIn("action_id", result)
        self.assertEqual(self.dispatcher.calls, [])

    def test_awaiting_approval_response_includes_registry_description(
        self,
    ):
        # Issue 4: a client needs something better than the raw
        # tool_name to show the user - the registry's own
        # human-readable description.
        registry = _registry(
            self.temp_dir.name,
            {
                "pc_system_optimization": {
                    "file_path": "x.py",
                    "class_name": "X",
                    "method": "run",
                    "approval_requirement": "user_approval_required",
                    "risk": "high",
                    "description": "Optimize this device's performance.",
                }
            },
        )
        gate = ApprovalGate(
            dispatcher=self.dispatcher,
            capability_registry=registry,
            approval_store=self.approval_store,
            audit_trail=self.audit,
        )

        result = gate.execute_tool(
            "pc_system_optimization", session_id="s1", request_text="x"
        )

        self.assertEqual(
            result["description"], "Optimize this device's performance."
        )

    def test_awaiting_approval_description_defaults_safely_when_unavailable(
        self,
    ):
        # The existing setUp's registry entry has no "description"
        # field - must degrade to CapabilityDescriptor's own existing
        # unknown-safe default ("") rather than raise or guess a
        # value, consistent with capability_registry.py's discipline.
        result = self.gate.execute_tool(
            "pc_system_optimization", session_id="s1", request_text="x"
        )

        self.assertEqual(result["description"], "")

    def test_no_decision_ever_recorded_means_execution_stays_blocked(
        self,
    ):
        self.gate.execute_tool(
            "pc_system_optimization", session_id="s1", request_text="x"
        )
        # No decide() call at all - dispatcher must never be reached.
        self.assertEqual(self.dispatcher.calls, [])

    def test_rejecting_the_action_never_executes_it(self):
        proposal = self.gate.execute_tool(
            "pc_system_optimization", session_id="s1", request_text="x"
        )

        result = self.gate.decide(
            proposal["action_id"], approved=False, session_id="s1"
        )

        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(self.dispatcher.calls, [])

    def test_valid_approval_executes_exactly_once(self):
        proposal = self.gate.execute_tool(
            "pc_system_optimization", session_id="s1", request_text="x"
        )

        result = self.gate.decide(
            proposal["action_id"], approved=True, session_id="s1"
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(self.dispatcher.calls), 1)
        self.assertEqual(
            self.dispatcher.calls[0][1].get("request_text"), "x"
        )

    def test_replaying_the_same_approval_does_not_execute_twice(self):
        proposal = self.gate.execute_tool(
            "pc_system_optimization", session_id="s1", request_text="x"
        )
        self.gate.decide(
            proposal["action_id"], approved=True, session_id="s1"
        )

        second = self.gate.decide(
            proposal["action_id"], approved=True, session_id="s1"
        )

        self.assertEqual(second["status"], "error")
        self.assertEqual(len(self.dispatcher.calls), 1)

    def test_wrong_action_id_is_blocked(self):
        result = self.gate.decide(
            "fabricated-action-id", approved=True, session_id="s1"
        )

        self.assertEqual(result["status"], "error")
        self.assertEqual(self.dispatcher.calls, [])

    def test_wrong_session_cannot_decide_or_execute_another_sessions_action(
        self,
    ):
        proposal = self.gate.execute_tool(
            "pc_system_optimization",
            session_id="session-a",
            request_text="x",
        )

        # A different session attempting to approve session-a's
        # proposal must be blocked, and must not execute anything.
        wrong_session_attempt = self.gate.decide(
            proposal["action_id"],
            approved=True,
            session_id="session-b",
        )
        self.assertEqual(wrong_session_attempt["status"], "error")
        self.assertEqual(self.dispatcher.calls, [])

        # The mismatch must not have consumed or poisoned the action -
        # the real proposing session can still approve it correctly.
        correct_session_attempt = self.gate.decide(
            proposal["action_id"],
            approved=True,
            session_id="session-a",
        )
        self.assertEqual(correct_session_attempt["status"], "success")
        self.assertEqual(len(self.dispatcher.calls), 1)

    def test_model_output_alone_cannot_approve_an_action(self):
        # There is no code path from execute_tool()'s return value
        # (what a model/planner would see) back into decide() without
        # a separate, explicit caller. Simulate a model/planner
        # "reading" the proposal and attempting to immediately act on
        # it as if understanding it were the same as approving it -
        # nothing here can execute without a genuinely separate
        # decide() call the model has no way to trigger itself.
        proposal = self.gate.execute_tool(
            "pc_system_optimization", session_id="s1", request_text="x"
        )

        self.assertNotIn("approved", proposal)
        self.assertEqual(proposal["status"], "awaiting_approval")
        self.assertEqual(self.dispatcher.calls, [])

    def test_audit_trail_records_the_full_lifecycle(self):
        proposal = self.gate.execute_tool(
            "pc_system_optimization", session_id="s1", request_text="x"
        )
        self.gate.decide(
            proposal["action_id"], approved=True, session_id="s1"
        )

        events = self.audit.for_session("s1")
        statuses = {event.status for event in events}

        self.assertIn("proposed_awaiting_approval", statuses)
        self.assertIn("approved", statuses)
        self.assertIn("executed_after_approval", statuses)

    def test_audit_trail_records_rejection(self):
        proposal = self.gate.execute_tool(
            "pc_system_optimization", session_id="s1", request_text="x"
        )
        self.gate.decide(
            proposal["action_id"], approved=False, session_id="s1"
        )

        statuses = {
            event.status for event in self.audit.for_session("s1")
        }
        self.assertIn("rejected", statuses)

    def test_audit_trail_records_invalid_decision_attempts(self):
        self.gate.decide(
            "fabricated-id", approved=True, session_id="s1"
        )

        statuses = {
            event.status for event in self.audit.for_session("s1")
        }
        self.assertIn("approval_decision_rejected", statuses)

    def test_malformed_approval_store_fails_closed_not_open(self):
        with open(
            self.approval_store.storage_path, "w", encoding="utf-8"
        ) as file:
            file.write("{ not valid json")

        result = self.gate.decide(
            "anything", approved=True, session_id="s1"
        )

        self.assertEqual(result["status"], "error")
        self.assertEqual(self.dispatcher.calls, [])


if __name__ == "__main__":
    unittest.main()
