"""Tests for GET /tasks: cross-session pending approvals (UI prototype
phase 1). No Ollama/network involved."""

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from uri_core.app import server
from uri_core.core.approval_gate import ApprovalGate
from uri_core.core.approval_store import ApprovalStore


class TasksEndpointTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self._original_approval_gate = server._orchestrator.approval_gate

        self.approval_store = ApprovalStore(
            storage_path=os.path.join(
                self.temp_dir.name, "approvals.json"
            )
        )
        server._orchestrator.approval_gate = ApprovalGate(
            dispatcher=server._orchestrator.dispatcher,
            capability_registry=server._orchestrator.capability_registry,
            approval_store=self.approval_store,
            audit_trail=server._orchestrator.audit_trail,
        )

        self.client = TestClient(server.app)

    def tearDown(self):
        server._orchestrator.approval_gate = self._original_approval_gate
        self.temp_dir.cleanup()

    def test_no_pending_actions_returns_empty_list(self):
        response = self.client.get("/tasks")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["tasks"], [])

    def test_pending_action_appears_with_capability_metadata(self):
        self.approval_store.propose(
            capability_id="pc_system_optimization",
            arguments={"request_text": "optimize"},
            session_id="s1",
        )

        response = self.client.get("/tasks")
        tasks = response.json()["tasks"]

        self.assertEqual(len(tasks), 1)
        self.assertEqual(
            tasks[0]["capability_id"], "pc_system_optimization"
        )
        self.assertEqual(tasks[0]["session_id"], "s1")
        self.assertIn("action_id", tasks[0])
        # Joined from the real capability registry (Milestone 6).
        self.assertEqual(tasks[0]["risk"], "high")
        self.assertTrue(tasks[0]["description"])

    def test_approved_action_no_longer_appears(self):
        proposed = self.approval_store.propose(
            capability_id="pc_system_optimization",
            arguments={},
            session_id="s1",
        )

        self.client.post(
            "/approve",
            json={"action_id": proposed.action_id, "session_id": "s1"},
        )

        response = self.client.get("/tasks")
        self.assertEqual(response.json()["tasks"], [])

    def test_unknown_capability_id_degrades_safely(self):
        self.approval_store.propose(
            capability_id="not_a_real_capability",
            arguments={},
            session_id="s1",
        )

        response = self.client.get("/tasks")
        tasks = response.json()["tasks"]

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["risk"], "unknown")
        self.assertEqual(tasks[0]["description"], "")


if __name__ == "__main__":
    unittest.main()
