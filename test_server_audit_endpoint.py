"""Tests for GET /audit/shadow-comparison. No Ollama or network
involved - the endpoint only summarizes whatever is already sitting in
the orchestrator's in-memory audit trail, so these seed events
directly rather than driving real requests through /ask."""

import unittest

from fastapi.testclient import TestClient

from uri_core.app import server
from uri_core.core.audit_trail import AuditTrail


class ShadowComparisonEndpointTests(unittest.TestCase):

    def setUp(self):
        # Isolate each test from whatever the module-level orchestrator
        # has already accumulated (including from other test files that
        # import uri_core.app.server in the same process).
        self._original_audit_trail = server._orchestrator.audit_trail
        server._orchestrator.audit_trail = AuditTrail()
        self.client = TestClient(server.app)

    def tearDown(self):
        server._orchestrator.audit_trail = self._original_audit_trail

    def test_empty_trail_returns_zeroed_report(self):
        response = self.client.get("/audit/shadow-comparison")

        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertEqual(body["skill_router"]["total"], 0)
        self.assertEqual(body["model_reasoning"]["total"], 0)
        self.assertIsNone(body["skill_router"]["agreement_rate"])

    def test_reflects_recorded_events(self):
        server._orchestrator.audit_trail.record(
            event_type="skill_router_shadow_evaluation",
            status="shadow_completed",
            session_id="s1",
            capability="draft_institutional_note",
            metadata={
                "planner_tool_name": "draft_institutional_note",
                "agrees_with_planner": True,
            },
        )

        server._orchestrator.audit_trail.record(
            event_type="model_reasoning_shadow_evaluation",
            status="proposal_ready",
            session_id="s1",
            capability="extract_student_records",
            metadata={
                "planner_tool_name": "draft_institutional_note",
                "agrees_with_planner": False,
            },
        )

        response = self.client.get("/audit/shadow-comparison")
        body = response.json()

        self.assertEqual(body["skill_router"]["total"], 1)
        self.assertEqual(body["skill_router"]["agreements"], 1)
        self.assertEqual(body["skill_router"]["agreement_rate"], 1.0)

        self.assertEqual(body["model_reasoning"]["total"], 1)
        self.assertEqual(body["model_reasoning"]["disagreements"], 1)
        self.assertEqual(body["model_reasoning"]["agreement_rate"], 0.0)

    def test_response_never_leaks_capability_registry_or_prompts(self):
        # AuditEvent metadata is already validated at write time (see
        # audit_trail.py) to reject anything credential-shaped and to
        # cap value length - this asserts the HTTP response stays a
        # small, fixed set of summary fields on top of that, not a
        # dump of everything the audit trail happens to hold.
        server._orchestrator.audit_trail.record(
            event_type="skill_router_shadow_evaluation",
            status="shadow_completed",
            session_id="s1",
            capability="draft_institutional_note",
            metadata={
                "planner_tool_name": "draft_institutional_note",
                "agrees_with_planner": True,
                "router_destination": "uri_runtime",
            },
        )

        response = self.client.get("/audit/shadow-comparison")
        body = response.json()

        recent_entry = body["skill_router"]["recent"][0]
        self.assertEqual(
            set(recent_entry.keys()),
            {
                "timestamp",
                "session_id",
                "status",
                "shadow_capability",
                "planner_tool_name",
                "agrees_with_planner",
            },
        )


if __name__ == "__main__":
    unittest.main()
