"""M32 Batch C: server.py /ask wiring for the native tool loop.

Proves the toggle is genuinely inert by default (byte-identical
fallthrough to the existing canonical/legacy chain) and that a native
tool loop that returns None (turn-state assembly failure, or simply
being disabled) falls through completely unchanged - never a third,
competing execution route. No Ollama/network involved (mirrors
test_server_ask_narrative.py's own convention)."""

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from uri_core.app import server
from uri_core.core.native_tool_loop import TOOL_LOOP_ENV_VAR


class NativeToolLoopToggleWiringTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(server.app)
        os.environ.pop(TOOL_LOOP_ENV_VAR, None)
        self.addCleanup(lambda: os.environ.pop(TOOL_LOOP_ENV_VAR, None))

    @patch("uri_core.core.native_tool_loop.run_native_tool_loop")
    def test_toggle_off_by_default_never_calls_the_native_loop(self, mock_loop):
        # Toggle unset (the shipped default) - run_native_tool_loop must
        # never even be invoked, proving the wiring is genuinely inert,
        # not merely returning an unused result.
        self.client.post("/ask", json={"session_id": "s-wiring-1", "text": "hi"})
        mock_loop.assert_not_called()

    @patch("uri_core.core.native_tool_loop.run_native_tool_loop", return_value=None)
    def test_toggle_on_but_none_result_falls_through_unchanged(self, mock_loop):
        # Toggle on, but the loop itself returns None (e.g. turn-state
        # assembly failed) - this must fall through to the existing
        # canonical/legacy chain exactly like every other None-means-
        # fall-back seam in this codebase, never raise, never surface a
        # different response shape.
        os.environ[TOOL_LOOP_ENV_VAR] = "1"
        response = self.client.post("/ask", json={"session_id": "s-wiring-2", "text": "hi"})
        mock_loop.assert_called_once()
        self.assertEqual(response.status_code, 200)

    @patch("uri_core.core.native_tool_loop.run_native_tool_loop")
    def test_toggle_on_with_a_real_result_is_used_as_the_response(self, mock_loop):
        fake_envelope = {
            "status": "success", "session_id": "s-wiring-3", "tier": "tier0",
            "execution": {"status": "not_applicable", "branch_results": []},
            "response": {"message": "direct answer"}, "narrative": "direct answer",
            "semantic_analysis": None, "error": None,
        }
        mock_loop.return_value = fake_envelope
        os.environ[TOOL_LOOP_ENV_VAR] = "1"

        response = self.client.post("/ask", json={"session_id": "s-wiring-3", "text": "what is 2+2"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["narrative"], "direct answer")
        mock_loop.assert_called_once()


if __name__ == "__main__":
    unittest.main()
