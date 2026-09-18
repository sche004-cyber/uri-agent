"""test_m32_1_ask_resumption_endpoint.py — M32.1.

Proves the /ask server-level wiring (toggle, ordering relative to
workflow_continuation, early-exit behavior) is correct - mirrors
test_m32_c_server_wiring.py's own convention of mocking the exact seam
this layer calls (resume_pending_approval) rather than re-exercising
its full logic (already covered with real collaborators in
test_approval_resumption.py)."""

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from uri_core.app import server
from uri_core.core.approval_resumption import APPROVAL_RESUMPTION_ENV_VAR


class ApprovalResumptionToggleWiringTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(server.app)
        os.environ.pop(APPROVAL_RESUMPTION_ENV_VAR, None)
        self.addCleanup(lambda: os.environ.pop(APPROVAL_RESUMPTION_ENV_VAR, None))

    @patch("uri_core.core.approval_resumption.resume_pending_approval")
    def test_toggle_off_by_default_never_calls_resumption(self, mock_resume):
        self.client.post("/ask", json={"session_id": "s-wiring-1", "text": "yes"})
        mock_resume.assert_not_called()

    @patch("uri_core.core.approval_resumption.resume_pending_approval", return_value=None)
    def test_toggle_on_but_none_result_falls_through_unchanged(self, mock_resume):
        os.environ[APPROVAL_RESUMPTION_ENV_VAR] = "1"
        response = self.client.post("/ask", json={"session_id": "s-wiring-2", "text": "yes"})
        mock_resume.assert_called_once()
        self.assertEqual(response.status_code, 200)

    @patch("uri_core.core.approval_resumption.resume_pending_approval")
    def test_toggle_on_with_a_real_result_is_used_as_the_response_and_short_circuits(self, mock_resume):
        fake_envelope = {
            "status": "success", "session_id": "s-wiring-3", "error": None,
            "semantic_analysis": None,
            "execution": {"status": "success", "action_id": "fake-action-id"},
            "response": {"message": "Done - the draft was created."},
            "narrative": None,
        }
        mock_resume.return_value = fake_envelope
        os.environ[APPROVAL_RESUMPTION_ENV_VAR] = "1"

        with patch("uri_core.core.native_tool_loop.run_native_tool_loop") as mock_native, \
             patch("uri_core.core.canonical_execution.run_canonical_for_ask") as mock_canonical:
            response = self.client.post("/ask", json={"session_id": "s-wiring-3", "text": "yes"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["response"], {"message": "Done - the draft was created."})
        # Short-circuit: nothing downstream should have even been reached.
        mock_native.assert_not_called()
        mock_canonical.assert_not_called()

    @patch("uri_core.core.approval_resumption.resume_pending_approval", side_effect=RuntimeError("boom"))
    def test_toggle_on_but_resumption_raises_falls_through_safely(self, mock_resume):
        """An internal failure in the resumption check must never break
        the turn - it must fall through exactly as if the block were
        absent, never surface a 500."""
        os.environ[APPROVAL_RESUMPTION_ENV_VAR] = "1"
        response = self.client.post("/ask", json={"session_id": "s-wiring-4", "text": "yes"})
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
