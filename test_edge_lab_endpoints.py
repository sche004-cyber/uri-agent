"""Unit tests for Edge Lab overview, live probe, and ARN integration."""

import unittest
import uuid
from fastapi.testclient import TestClient

from uri_core.app.server import app
from uri_core.core.auth_session import AuthSessionStore


class TestEdgeLabEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.session_store = AuthSessionStore()
        # Create an authenticated session with a valid UUID user_id
        self.user_id = str(uuid.uuid4())
        self.session_token = self.session_store.create(self.user_id)
        self.auth_headers = {"Authorization": f"Bearer {self.session_token}"}

    def test_unauthenticated_lab_overview_rejected(self):
        response = self.client.get("/intelligence/lab/overview")
        self.assertEqual(response.status_code, 401)

    def test_authenticated_lab_overview_structure(self):
        response = self.client.get("/intelligence/lab/overview", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "active")
        self.assertEqual(data["runtime_lifecycle"]["state"], "RESIDENT")
        self.assertEqual(data["runtime_lifecycle"]["active_runtime_id"], "needle-3")

        # Verify candidate qualification statuses
        candidates = {c["id"]: c for c in data["candidates"]}
        self.assertIn("needle-3", candidates)
        self.assertEqual(candidates["needle-3"]["status"], "RESIDENT")
        self.assertTrue(candidates["needle-3"]["qualified"])
        self.assertEqual(candidates["needle-3"]["reflex_accuracy_pct"], 100)
        self.assertFalse(candidates["needle-3"]["argument_trusted"])

        self.assertIn("smollm2-135m-instruct", candidates)
        self.assertEqual(candidates["smollm2-135m-instruct"]["status"], "BYPASSED")

        self.assertIn("qwen2.5-0.5b-instruct", candidates)
        self.assertEqual(candidates["qwen2.5-0.5b-instruct"]["status"], "BYPASSED")

        self.assertIn("faster-whisper", candidates)
        self.assertEqual(candidates["faster-whisper"]["status"], "UNAVAILABLE")

        self.assertIn("tesseract-ocr", candidates)
        self.assertEqual(candidates["tesseract-ocr"]["status"], "UNAVAILABLE")

        self.assertIn("vlm-edge", candidates)
        self.assertEqual(candidates["vlm-edge"]["status"], "UNAVAILABLE")

    def test_edge_lab_probe_reflex_and_escalate(self):
        # Reflex query (greeting)
        resp_greeting = self.client.post(
            "/intelligence/lab/probe",
            json={"query": "hello"},
            headers=self.auth_headers,
        )
        self.assertEqual(resp_greeting.status_code, 200)
        result = resp_greeting.json()["probe_result"]
        self.assertEqual(result["decision"], "EDGE_REPLY")
        self.assertEqual(result["candidate"], "needle-3")

        # Complex query (should escalate to Main Brain)
        resp_complex = self.client.post(
            "/intelligence/lab/probe",
            json={"query": "Find the invoices for project alpha from March"},
            headers=self.auth_headers,
        )
        self.assertEqual(resp_complex.status_code, 200)
        result_complex = resp_complex.json()["probe_result"]
        self.assertEqual(result_complex["decision"], "ESCALATE")
        self.assertIn("COMPLEX_INTENT_DETECTED", result_complex["reason_codes"])


if __name__ == "__main__":
    unittest.main()
