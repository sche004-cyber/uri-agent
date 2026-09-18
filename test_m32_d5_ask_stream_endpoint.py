"""test_m32_d5_ask_stream_endpoint.py — M32 D5.

Integration tests for POST /ask/stream at the HTTP boundary. No real
Ollama/network involved - mirrors test_m32_c_server_wiring.py's own
mocking convention (patch the exact seam the endpoint calls, assert on
the resulting SSE body). Real end-to-end evidence against a live Ollama
server is reported separately (docs/plans/M32_POST_BATCH_C_LATENCY_
ARCHITECTURE_PLAN.md §14), not duplicated here as an offline test.
"""
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from uri_core.app import server
from uri_core.core.native_tool_loop import TOOL_LOOP_ENV_VAR
from uri_core.core.stream_tool_loop import StreamCapacityExceededError, TurnStreamEvent


def _parse_sse(body: str):
    """Splits a raw SSE response body into (event, data_json_str) pairs."""
    events = []
    for block in body.strip().split("\n\n"):
        if not block.strip():
            continue
        event_line, data_line = None, None
        for line in block.splitlines():
            if line.startswith("event:"):
                event_line = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data_line = line[len("data:"):].strip()
        events.append((event_line, data_line))
    return events


class AskStreamFallbackTests(unittest.TestCase):
    """native_tool_loop disabled (the shipped default) - /ask/stream must
    delegate to the existing, unmodified ask() rather than attempt
    streaming at all."""

    def setUp(self):
        self.client = TestClient(server.app)
        os.environ.pop(TOOL_LOOP_ENV_VAR, None)
        self.addCleanup(lambda: os.environ.pop(TOOL_LOOP_ENV_VAR, None))

    def test_toggle_off_delegates_to_ask_as_one_message_event(self):
        response = self.client.post(
            "/ask/stream", json={"session_id": "s-stream-fallback-1", "text": "hi"},
        )
        self.assertEqual(response.status_code, 200)
        events = _parse_sse(response.text)
        kinds = [e for e, _ in events]
        self.assertEqual(kinds, ["message", "done"])

    def test_fallback_message_event_matches_a_direct_ask_call(self):
        direct = self.client.post(
            "/ask", json={"session_id": "s-stream-fallback-2", "text": "hi"},
        )
        streamed = self.client.post(
            "/ask/stream", json={"session_id": "s-stream-fallback-2b", "text": "hi"},
        )
        events = _parse_sse(streamed.text)
        import json as _json
        message_data = _json.loads(events[0][1])
        direct_data = direct.json()
        # Same shape/keys - the fallback wraps ask()'s own result verbatim.
        self.assertEqual(set(message_data.keys()), set(direct_data.keys()))


class AskStreamEligibleTests(unittest.TestCase):
    """native_tool_loop enabled - /ask/stream must attempt the real
    streaming fast path (stream_first_turn), not silently fall back."""

    def setUp(self):
        self.client = TestClient(server.app)
        os.environ[TOOL_LOOP_ENV_VAR] = "1"
        self.addCleanup(lambda: os.environ.pop(TOOL_LOOP_ENV_VAR, None))

    def test_content_events_and_done_are_emitted(self):
        fake_envelope = {
            "status": "success", "session_id": "s-stream-eligible-1", "tier": "tier0",
            "execution": {"status": "not_applicable", "branch_results": []},
            "response": {"message": "Hello there"}, "narrative": "Hello there",
            "semantic_analysis": None, "error": None,
        }

        def fake_stream_first_turn(**kwargs):
            yield TurnStreamEvent(kind="content", content="Hello")
            yield TurnStreamEvent(kind="content", content=" there")
            yield TurnStreamEvent(
                kind="done", envelope=fake_envelope, ttft_seconds=0.05,
                narrative_interrupted=False,
            )

        with patch(
            "uri_core.core.stream_tool_loop.stream_first_turn", side_effect=fake_stream_first_turn,
        ):
            response = self.client.post(
                "/ask/stream", json={"session_id": "s-stream-eligible-1", "text": "hi"},
            )

        self.assertEqual(response.status_code, 200)
        events = _parse_sse(response.text)
        kinds = [e for e, _ in events]
        self.assertEqual(kinds, ["content", "content", "done"])

        import json as _json
        done_data = _json.loads(events[-1][1])
        self.assertEqual(done_data["ttft_seconds"], 0.05)
        self.assertFalse(done_data["narrative_interrupted"])
        self.assertEqual(done_data["response"]["narrative"], "Hello there")

    def test_tool_call_detected_event_is_forwarded(self):
        fake_envelope = {
            "status": "success", "session_id": "s-stream-eligible-2", "tier": "tier1",
            "execution": {"status": "success", "branch_results": []},
            "response": {"message": "done"}, "narrative": "done",
            "semantic_analysis": None, "error": None,
        }

        def fake_stream_first_turn(**kwargs):
            yield TurnStreamEvent(kind="content", content="checking...")
            yield TurnStreamEvent(kind="tool_call_detected")
            yield TurnStreamEvent(kind="done", envelope=fake_envelope, narrative_interrupted=True)

        with patch(
            "uri_core.core.stream_tool_loop.stream_first_turn", side_effect=fake_stream_first_turn,
        ):
            response = self.client.post(
                "/ask/stream", json={"session_id": "s-stream-eligible-2", "text": "check my email"},
            )

        events = _parse_sse(response.text)
        kinds = [e for e, _ in events]
        self.assertEqual(kinds, ["content", "tool_call_detected", "done"])

        import json as _json
        done_data = _json.loads(events[-1][1])
        self.assertTrue(done_data["narrative_interrupted"])

    def test_none_envelope_falls_back_to_ask(self):
        """The SAME "None means fall back" convention /ask's own
        native_tool_loop branch already follows (turn-state assembly
        failure)."""

        def fake_stream_first_turn(**kwargs):
            yield TurnStreamEvent(kind="done", envelope=None)

        with patch(
            "uri_core.core.stream_tool_loop.stream_first_turn", side_effect=fake_stream_first_turn,
        ):
            response = self.client.post(
                "/ask/stream", json={"session_id": "s-stream-eligible-3", "text": "hi"},
            )

        events = _parse_sse(response.text)
        kinds = [e for e, _ in events]
        self.assertEqual(kinds, ["message", "done"])

    def test_capacity_exceeded_falls_back_to_ask(self):
        def fake_stream_first_turn(**kwargs):
            raise StreamCapacityExceededError("at capacity")
            yield  # pragma: no cover - makes this a generator function

        with patch(
            "uri_core.core.stream_tool_loop.stream_first_turn", side_effect=fake_stream_first_turn,
        ):
            response = self.client.post(
                "/ask/stream", json={"session_id": "s-stream-eligible-4", "text": "hi"},
            )

        self.assertEqual(response.status_code, 200)
        events = _parse_sse(response.text)
        kinds = [e for e, _ in events]
        self.assertEqual(kinds, ["message", "done"])


if __name__ == "__main__":
    unittest.main()
