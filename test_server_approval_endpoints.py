"""Tests for POST /approve and POST /cancel (Milestone 7). No Ollama
or network involved."""

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from uri_core.app import server
from uri_core.core.approval_gate import ApprovalGate
from uri_core.core.approval_store import ApprovalStore


class _FakeDispatcher:
    def __init__(self):
        self.calls = []

    def execute_tool(self, tool_name, **kwargs):
        self.calls.append((tool_name, kwargs))
        return {"status": "success", "data": {"tool": tool_name}}


class ApprovalEndpointsTests(unittest.TestCase):

    def setUp(self):
        self._original_approval_gate = server._orchestrator.approval_gate

        self.dispatcher = _FakeDispatcher()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.approval_store = ApprovalStore(
            storage_path=os.path.join(
                self.temp_dir.name, "approvals.json"
            )
        )

        server._orchestrator.approval_gate = ApprovalGate(
            dispatcher=self.dispatcher,
            approval_store=self.approval_store,
        )

        self.client = TestClient(server.app)

    def tearDown(self):
        server._orchestrator.approval_gate = self._original_approval_gate
        self.temp_dir.cleanup()

    def test_approve_unknown_action_id_returns_error_not_500(self):
        response = self.client.post(
            "/approve", json={"action_id": "nope", "session_id": "s1"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")
        self.assertEqual(self.dispatcher.calls, [])

    def test_cancel_unknown_action_id_returns_error_not_500(self):
        response = self.client.post(
            "/cancel", json={"action_id": "nope", "session_id": "s1"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")

    def test_approve_a_real_pending_action_executes_it(self):
        proposed = self.approval_store.propose(
            capability_id="pc_system_optimization",
            arguments={"request_text": "clean up"},
            session_id="s1",
        )

        response = self.client.post(
            "/approve",
            json={"action_id": proposed.action_id, "session_id": "s1"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(len(self.dispatcher.calls), 1)

    def test_cancel_a_real_pending_action_never_executes_it(self):
        proposed = self.approval_store.propose(
            capability_id="pc_system_optimization",
            arguments={},
            session_id="s1",
        )

        response = self.client.post(
            "/cancel",
            json={"action_id": proposed.action_id, "session_id": "s1"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "cancelled")
        self.assertEqual(self.dispatcher.calls, [])

    def test_approving_twice_only_executes_once(self):
        proposed = self.approval_store.propose(
            capability_id="pc_system_optimization",
            arguments={},
            session_id="s1",
        )

        payload = {"action_id": proposed.action_id, "session_id": "s1"}
        first = self.client.post("/approve", json=payload)
        second = self.client.post("/approve", json=payload)

        self.assertEqual(first.json()["status"], "success")
        self.assertEqual(second.json()["status"], "error")
        self.assertEqual(len(self.dispatcher.calls), 1)


if __name__ == "__main__":
    unittest.main()
