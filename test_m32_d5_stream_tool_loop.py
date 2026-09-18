"""test_m32_d5_stream_tool_loop.py — M32 D5.

Tests uri_core/core/stream_tool_loop.py: the streaming wrapper around
run_native_tool_loop()'s Tier 0 fast path. run_native_tool_loop() itself
is never modified or mocked-around here — these tests use the SAME real
`_Fixture` (real SessionManager, real CapabilityRegistry, real
ApprovalGate/ToolDispatcher, real MultiActionDispatch wired to a fake
Gmail service) test_m32_c2_c3_native_tool_loop.py already established,
so gate/approval/audit behaviour is exercised for real, not assumed.

Only the model layer is faked (a FakeStreamRouter substituted for the
real ModelRouter via `uri_core.core.stream_tool_loop.get_router`) -
mirrors this repo's own "model-free where possible" convention.
"""
from __future__ import annotations

import os
import threading
import time
import unittest
from unittest.mock import patch

from uri_core.core.model_providers.base import (
    ModelResponse,
    ProviderUnavailableError,
    StreamChunk,
    ToolCall,
)
from uri_core.core.native_tool_loop import run_native_tool_loop
from uri_core.core.stream_tool_loop import (
    DEFAULT_MAX_CONCURRENT_STREAMS,
    MAX_CONCURRENT_STREAMS_ENV_VAR,
    StreamCapacityExceededError,
    max_concurrent_streams,
    stream_first_turn,
)
from test_m32_c2_c3_native_tool_loop import _Fixture


class FakeStreamRouter:
    """Substituted for the real ModelRouter singleton. `attempt_stream`
    drives iteration 1 (the only iteration eligible for live streaming);
    `attempt` drives every later iteration - exactly mirroring the real
    router's own two entry points."""

    def __init__(self, stream_chunks=None, continuation_response=None, stream_error=None, gate=None, delay=0.0):
        self._stream_chunks = stream_chunks or []
        self._continuation_response = continuation_response
        self._stream_error = stream_error
        self._gate = gate  # optional threading.Event the test can use to pause mid-stream
        self._delay = delay  # optional real per-chunk delay, so a test has a window to cancel
        self.attempt_calls = []
        self.attempt_stream_calls = 0
        self.chunks_yielded = 0
        self.closed = False

    def attempt_stream(self, role, principal, **kwargs):
        self.attempt_stream_calls += 1
        try:
            for chunk in self._stream_chunks:
                if self._gate is not None:
                    self._gate.wait(timeout=5.0)
                if self._delay:
                    time.sleep(self._delay)
                yield chunk
                self.chunks_yielded += 1
            if self._stream_error is not None:
                raise self._stream_error
        except GeneratorExit:
            self.closed = True
            raise

    def attempt(self, role, principal, **kwargs):
        self.attempt_calls.append(kwargs)
        return self._continuation_response


def _content_chunk(text, done=False):
    return StreamChunk(content=text, is_tool_call=False, done=done)


def _final_content_chunk(full_text, ttft=0.05):
    return StreamChunk(
        content="", is_tool_call=False, done=True,
        final_response=ModelResponse(content=full_text, model="fake", provider="fake"),
        ttft_seconds=ttft,
    )


class ContentOnlyStreamingTests(unittest.TestCase):
    """Tier 0: a plain-content turn, no tool call anywhere in the stream."""

    def test_content_events_then_done_with_matching_envelope(self):
        fixture = _Fixture()
        router = FakeStreamRouter(stream_chunks=[
            _content_chunk("Hello"),
            _content_chunk(", world"),
            _final_content_chunk("Hello, world"),
        ])
        with patch("uri_core.core.stream_tool_loop.get_router", return_value=router):
            events = list(stream_first_turn(
                orchestrator=fixture.orchestrator(), session_id="s1",
                user_text="hi", principal=None,
            ))

        content_events = [e for e in events if e.kind == "content"]
        self.assertEqual([e.content for e in content_events], ["Hello", ", world"])
        self.assertEqual(events[-1].kind, "done")
        self.assertFalse(events[-1].narrative_interrupted)
        self.assertEqual(events[-1].envelope["narrative"], "Hello, world")
        self.assertEqual(events[-1].ttft_seconds, 0.05)
        self.assertEqual(router.attempt_stream_calls, 1)
        self.assertEqual(router.attempt_calls, [])  # iteration 2 never happened

    def test_envelope_matches_the_unmodified_non_streaming_run_native_tool_loop(self):
        """Persistence integrity: streaming must not change WHAT the turn
        computes, only how it is delivered. The exact same final
        ModelResponse fed through run_native_tool_loop() directly (no
        streaming wrapper at all) must produce an identical envelope to
        the one stream_first_turn() reports on "done"."""
        fixture = _Fixture()

        def direct_model_callable(*, system, user, tools=None):
            return ModelResponse(content="Hello, world", model="fake", provider="fake")

        direct_envelope = run_native_tool_loop(
            orchestrator=fixture.orchestrator(), session_id="s-direct", user_text="hi",
            principal=None, model_callable=direct_model_callable,
        )

        router = FakeStreamRouter(stream_chunks=[
            _content_chunk("Hello"),
            _content_chunk(", world"),
            _final_content_chunk("Hello, world"),
        ])
        with patch("uri_core.core.stream_tool_loop.get_router", return_value=router):
            events = list(stream_first_turn(
                orchestrator=fixture.orchestrator(), session_id="s-direct", user_text="hi",
                principal=None,
            ))

        streamed_envelope = events[-1].envelope
        for key in ("status", "tier", "response", "narrative", "execution"):
            self.assertEqual(streamed_envelope[key], direct_envelope[key], key)


class LateToolCallTests(unittest.TestCase):
    """The User's explicit clarification: a first content chunk never
    proves a turn is terminal. A tool call arriving AFTER some content
    chunks were already streamed must still be honoured correctly -
    every prior content event is provisional, the turn continues
    through the real, unmodified gate/execute path, and the terminal
    envelope reflects the REAL tool execution, never the provisional
    prose."""

    def test_content_then_tool_call_marks_narrative_interrupted_and_executes_for_real(self):
        from uri_core.core.tool_schema import GMAIL_TOOL_PREFIX

        fixture = _Fixture(connected_gmail=True)
        tool_call = ToolCall(id="c1", name=f"{GMAIL_TOOL_PREFIX}search_messages", arguments={"query": "insurance"})
        iteration1_chunks = [
            _content_chunk("Let me check "),
            _content_chunk("your inbox..."),
            StreamChunk(
                content="", is_tool_call=True, done=True,
                final_response=ModelResponse(
                    content="", model="fake", provider="fake", tool_calls=(tool_call,),
                ),
            ),
        ]
        continuation_response = ModelResponse(content="I found it.", model="fake", provider="fake")
        router = FakeStreamRouter(
            stream_chunks=iteration1_chunks, continuation_response=continuation_response,
        )

        with patch("uri_core.core.stream_tool_loop.get_router", return_value=router):
            events = list(stream_first_turn(
                orchestrator=fixture.orchestrator(), session_id="s2",
                user_text="check my email for insurance", principal=None,
            ))

        content_events = [e for e in events if e.kind == "content"]
        self.assertEqual([e.content for e in content_events], ["Let me check ", "your inbox..."])

        tool_call_events = [e for e in events if e.kind == "tool_call_detected"]
        self.assertEqual(len(tool_call_events), 1, "must fire exactly once, the instant the tool call appears")

        done = events[-1]
        self.assertEqual(done.kind, "done")
        self.assertTrue(done.narrative_interrupted)
        # The real Gmail search actually executed - not a fabricated
        # success, and never the provisional "Let me check your inbox..."
        # text repurposed as if it were the real narrative.
        self.assertEqual(done.envelope["narrative"], "I found it.")
        branch_results = done.envelope["execution"]["branch_results"]
        self.assertEqual(len(branch_results), 1)
        self.assertEqual(branch_results[0]["capability"], "Gmail")
        self.assertEqual(branch_results[0]["status"], "success")
        # Iteration 2 (the continuation, after real tool execution) used
        # the existing non-streaming router path, not the stream.
        self.assertEqual(router.attempt_stream_calls, 1)
        self.assertEqual(len(router.attempt_calls), 1)

    def test_tool_call_in_first_chunk_also_works_with_zero_content_events(self):
        """Control: the more common real case (empirically observed
        against real Ollama - tool_calls in the FIRST streamed chunk, no
        prose first) must work identically - zero content events."""
        from uri_core.core.tool_schema import GMAIL_TOOL_PREFIX

        fixture = _Fixture(connected_gmail=True)
        tool_call = ToolCall(id="c1", name=f"{GMAIL_TOOL_PREFIX}search_messages", arguments={"query": "x"})
        router = FakeStreamRouter(
            stream_chunks=[
                StreamChunk(
                    content="", is_tool_call=True, done=True,
                    final_response=ModelResponse(content="", model="fake", provider="fake", tool_calls=(tool_call,)),
                ),
            ],
            continuation_response=ModelResponse(content="done.", model="fake", provider="fake"),
        )

        with patch("uri_core.core.stream_tool_loop.get_router", return_value=router):
            events = list(stream_first_turn(
                orchestrator=fixture.orchestrator(), session_id="s3",
                user_text="check my email", principal=None,
            ))

        self.assertEqual([e for e in events if e.kind == "content"], [])
        self.assertEqual(len([e for e in events if e.kind == "tool_call_detected"]), 1)
        self.assertTrue(events[-1].narrative_interrupted)
        self.assertEqual(events[-1].envelope["narrative"], "done.")


class CancellationTests(unittest.TestCase):
    """Client-disconnect-style cancellation (§13.4)."""

    def test_setting_cancel_event_stops_the_stream_early_and_closes_upstream(self):
        """A stream that gets cancelled part-way through is caught by
        run_native_tool_loop()'s own existing "model_callable raised" ->
        `{"status": "unavailable", ...}` degrade path - the SAME honest,
        already-audited outcome a real provider failure already produces
        today, non-streamed. StreamCancelled is never a new, special-
        cased failure surface."""
        many_chunks = [_content_chunk(f"word{i} ") for i in range(50)]
        # A small real delay per chunk gives the main thread a real
        # window to cancel before all 50 chunks race through.
        router = FakeStreamRouter(stream_chunks=many_chunks, delay=0.01)
        fixture = _Fixture()
        cancel_event = threading.Event()

        with patch("uri_core.core.stream_tool_loop.get_router", return_value=router):
            gen = stream_first_turn(
                orchestrator=fixture.orchestrator(), session_id="s-cancel", user_text="hi",
                principal=None, cancel_event=cancel_event,
            )
            first = next(gen)
            self.assertEqual(first.kind, "content")

            cancel_event.set()  # simulate a detected client disconnect
            events = [first] + list(gen)  # drain the rest

        content_events = [e for e in events if e.kind == "content"]
        self.assertLess(
            len(content_events), 50,
            "cancellation did not stop the stream early - all 50 chunks were produced",
        )
        self.assertEqual(events[-1].kind, "done")
        self.assertEqual(events[-1].envelope["status"], "unavailable")
        self.assertTrue(router.closed, "upstream provider stream generator was never closed on cancellation")

    def test_consumer_stopping_early_also_cancels_and_joins_cleanly(self):
        """Even if the caller never sets cancel_event itself (e.g. it
        simply stops iterating), the generator's own finally must signal
        cancellation and join the background thread - no orphaned
        thread/connection."""
        many_chunks = [_content_chunk(f"word{i} ") for i in range(50)]
        router = FakeStreamRouter(stream_chunks=many_chunks, delay=0.01)
        fixture = _Fixture()

        with patch("uri_core.core.stream_tool_loop.get_router", return_value=router):
            gen = stream_first_turn(
                orchestrator=fixture.orchestrator(), session_id="s-early-stop", user_text="hi",
                principal=None,
            )
            next(gen)  # consume exactly one event, then abandon the generator
            gen.close()

        self.assertTrue(router.closed)


class ProviderErrorTests(unittest.TestCase):
    """Mid-generation provider failure (§13.4). A provider that fails
    after already streaming some content is caught by run_native_tool_
    loop()'s own existing exception handling - the streamed path
    produces the identical honest "unavailable" degrade a non-streamed
    provider failure already would, never a new failure shape."""

    def test_error_after_some_content_degrades_honestly_never_persists_partial_as_success(self):
        fixture = _Fixture()
        router = FakeStreamRouter(
            stream_chunks=[_content_chunk("Partial")],
            stream_error=ProviderUnavailableError("connection dropped"),
        )

        with patch("uri_core.core.stream_tool_loop.get_router", return_value=router):
            events = list(stream_first_turn(
                orchestrator=fixture.orchestrator(), session_id="s-err", user_text="hi",
                principal=None,
            ))

        self.assertEqual(events[0].kind, "content")
        self.assertEqual(events[0].content, "Partial")
        self.assertEqual(events[-1].kind, "done")
        self.assertEqual(events[-1].envelope["status"], "unavailable")
        # The provisional "Partial" text must never appear as the
        # authoritative narrative/response of a turn reported unavailable.
        self.assertNotIn("Partial", str(events[-1].envelope.get("narrative")))
        self.assertNotIn("Partial", str(events[-1].envelope.get("response")))


class ConnectionCapTests(unittest.TestCase):
    """R-D5-6: a bounded, deployment-configurable cap on concurrent
    streams."""

    def setUp(self):
        os.environ.pop(MAX_CONCURRENT_STREAMS_ENV_VAR, None)
        self.addCleanup(lambda: os.environ.pop(MAX_CONCURRENT_STREAMS_ENV_VAR, None))

    def test_default_cap_is_a_small_positive_number(self):
        self.assertEqual(max_concurrent_streams(), DEFAULT_MAX_CONCURRENT_STREAMS)
        self.assertGreaterEqual(DEFAULT_MAX_CONCURRENT_STREAMS, 1)
        self.assertLessEqual(DEFAULT_MAX_CONCURRENT_STREAMS, 32)

    def test_configurable_via_env_var(self):
        os.environ[MAX_CONCURRENT_STREAMS_ENV_VAR] = "3"
        self.assertEqual(max_concurrent_streams(), 3)

    def test_falls_back_to_default_on_invalid_value(self):
        os.environ[MAX_CONCURRENT_STREAMS_ENV_VAR] = "not-a-number"
        self.assertEqual(max_concurrent_streams(), DEFAULT_MAX_CONCURRENT_STREAMS)
        os.environ[MAX_CONCURRENT_STREAMS_ENV_VAR] = "0"
        self.assertEqual(max_concurrent_streams(), DEFAULT_MAX_CONCURRENT_STREAMS)

    def test_exceeding_the_cap_raises_immediately_without_starting_a_thread(self):
        os.environ[MAX_CONCURRENT_STREAMS_ENV_VAR] = "1"
        fixture = _Fixture()

        gate = threading.Event()
        blocked_router = FakeStreamRouter(
            stream_chunks=[_content_chunk("A"), _final_content_chunk("A")], gate=gate,
        )

        with patch("uri_core.core.stream_tool_loop.get_router", return_value=blocked_router):
            first = stream_first_turn(
                orchestrator=fixture.orchestrator(), session_id="s-cap-1", user_text="hi",
                principal=None,
            )
            next(first)  # start the first stream, holding its capacity slot

            second_router = FakeStreamRouter(stream_chunks=[_final_content_chunk("B")])
            with patch("uri_core.core.stream_tool_loop.get_router", return_value=second_router):
                second = stream_first_turn(
                    orchestrator=fixture.orchestrator(), session_id="s-cap-2", user_text="hi",
                    principal=None,
                )
                with self.assertRaises(StreamCapacityExceededError):
                    next(second)

            self.assertEqual(second_router.attempt_stream_calls, 0, "a rejected stream must never even start")

            gate.set()
            first.close()


class OnlyFirstIterationStreamsTests(unittest.TestCase):
    """Scope decision (§13.2/§13.12): only iteration 1 is eligible for
    live streaming; a genuine multi-tool-call turn's LATER iterations
    always use the existing non-streaming router path."""

    def test_second_tool_call_iteration_never_streams(self):
        from uri_core.core.tool_schema import GMAIL_TOOL_PREFIX

        fixture = _Fixture(connected_gmail=True)
        # Iteration 1: a tool call immediately (no content).
        tc1 = ToolCall(id="c1", name=f"{GMAIL_TOOL_PREFIX}search_messages", arguments={"query": "a"})
        iteration1 = StreamChunk(
            content="", is_tool_call=True, done=True,
            final_response=ModelResponse(content="", model="fake", provider="fake", tool_calls=(tc1,)),
        )
        # Iteration 2 (via the non-streaming `attempt()`): another tool
        # call, then iteration 3 (still non-streaming) finally answers.
        tc2 = ToolCall(id="c2", name=f"{GMAIL_TOOL_PREFIX}search_messages", arguments={"query": "b"})
        call_sequence = [
            ModelResponse(content="", model="fake", provider="fake", tool_calls=(tc2,)),
            ModelResponse(content="final answer", model="fake", provider="fake"),
        ]

        class MultiIterationRouter(FakeStreamRouter):
            def attempt(self, role, principal, **kwargs):
                self.attempt_calls.append(kwargs)
                return call_sequence[len(self.attempt_calls) - 1]

        router = MultiIterationRouter(stream_chunks=[iteration1])

        with patch("uri_core.core.stream_tool_loop.get_router", return_value=router):
            events = list(stream_first_turn(
                orchestrator=fixture.orchestrator(), session_id="s-multi", user_text="hi",
                principal=None, max_iterations=3,
            ))

        self.assertEqual(router.attempt_stream_calls, 1)
        self.assertEqual(len(router.attempt_calls), 2)
        self.assertEqual(events[-1].envelope["narrative"], "final answer")


if __name__ == "__main__":
    unittest.main()
