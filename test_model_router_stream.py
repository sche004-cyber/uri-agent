"""test_model_router_stream.py — M32 D5.

Verifies ModelRouter.attempt_stream() mirrors attempt()'s own ordered-
candidate/health-tracking/budget-gating structure (§13.8: "no change to
carry streaming"), with one deliberate addition: once any content has
been yielded to the caller for a candidate, that candidate is
committed — a later, mid-stream failure from that SAME candidate can no
longer silently fall back to a different provider (the caller has
already been shown some of its own words), so it is re-raised instead.
A failure BEFORE any content has been yielded may still advance to the
next candidate, exactly like attempt().
"""
import unittest
from unittest.mock import patch

from uri_core.core.model_router import (
    AllProvidersUnreachableError,
    ModelRouter,
    ProviderHealthTracker,
)
from uri_core.core.model_providers.base import (
    ModelNotFoundError,
    ModelResponse,
    ProviderAuthenticationError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    StreamChunk,
    ToolCall,
)


class FakeStreamingProvider:
    """A provider whose complete_stream() yields a pre-scripted sequence
    of StreamChunk, then raises `raises` (if given) once that sequence
    is exhausted - so `chunks=[]` raises immediately (before any
    content), and `chunks=[<content chunk>]` raises after one real
    content chunk was already yielded."""

    def __init__(self, chunks=None, raises=None):
        self._chunks = chunks or []
        self._raises = raises
        self.call_count = 0

    def complete_stream(self, **kwargs):
        self.call_count += 1
        for chunk in self._chunks:
            yield chunk
        if self._raises is not None:
            raise self._raises


def _final_chunk(content="answer", model="m"):
    return StreamChunk(
        content=content, done=True,
        final_response=ModelResponse(content=content, model=model, provider="p"),
    )


class TestAttemptStreamHappyPath(unittest.TestCase):
    def test_yields_all_chunks_and_returns_via_final_chunk(self):
        router = ModelRouter(health_tracker=ProviderHealthTracker())
        provider = FakeStreamingProvider(chunks=[
            StreamChunk(content="Hel", done=False),
            StreamChunk(content="lo", done=False),
            _final_chunk(content="Hello"),
        ])
        with patch("uri_core.core.model_router.build_provider", return_value=provider):
            chunks = list(router.attempt_stream("reasoning", None, system="s", user="u"))

        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[-1].final_response.content, "Hello")
        self.assertTrue(chunks[-1].done)

    def test_tool_call_chunk_carries_no_content_but_is_flagged(self):
        router = ModelRouter(health_tracker=ProviderHealthTracker())
        tc = ToolCall(id="c1", name="search", arguments={})
        provider = FakeStreamingProvider(chunks=[
            StreamChunk(content="", is_tool_call=True, done=False),
            StreamChunk(
                content="", is_tool_call=True, done=True,
                final_response=ModelResponse(content="", model="m", provider="p", tool_calls=(tc,)),
            ),
        ])
        with patch("uri_core.core.model_router.build_provider", return_value=provider):
            chunks = list(router.attempt_stream("reasoning", None, system="s", user="u"))

        self.assertTrue(all(c.is_tool_call for c in chunks))
        self.assertTrue(all(not c.content for c in chunks))
        self.assertEqual(chunks[-1].final_response.tool_calls[0].name, "search")


class TestAttemptStreamFallback(unittest.TestCase):
    def test_failure_before_any_content_advances_to_next_candidate(self):
        """Mirrors attempt()'s own fallback behaviour: a failure before
        any content is yielded may still try the next candidate."""
        router = ModelRouter(health_tracker=ProviderHealthTracker())
        failing = FakeStreamingProvider(raises=ProviderUnavailableError("down"))
        succeeding = FakeStreamingProvider(chunks=[_final_chunk(content="fallback answer")])

        call_log = []

        def fake_build(role, principal=None, provider_id_override=None):
            call_log.append(provider_id_override)
            return failing if len(call_log) == 1 else succeeding

        with patch("uri_core.core.model_router.load_model_roles") as mock_roles, \
             patch("uri_core.core.model_router.build_provider", side_effect=fake_build):
            mock_roles.return_value = {"reasoning": {"provider": "primary_p", "model": "primary_m"}}
            chunks = list(router.attempt_stream("reasoning", None, system="s", user="u"))

        self.assertEqual(chunks[-1].final_response.content, "fallback answer")
        self.assertEqual(len(call_log), 2)

    def test_mid_stream_failure_after_content_is_committed_never_falls_back(self):
        """The central new safety property: once content has been shown,
        a mid-stream failure must be re-raised, never silently retried
        against a different provider."""
        router = ModelRouter(health_tracker=ProviderHealthTracker())
        committed_then_fails = FakeStreamingProvider(
            chunks=[StreamChunk(content="Some real words already shown", done=False)],
            raises=ProviderUnavailableError("dropped mid-stream"),
        )
        never_reached = FakeStreamingProvider(chunks=[_final_chunk(content="should never be used")])

        call_log = []

        def fake_build(role, principal=None, provider_id_override=None):
            call_log.append(provider_id_override)
            return committed_then_fails if len(call_log) == 1 else never_reached

        with patch("uri_core.core.model_router.build_provider", side_effect=fake_build):
            gen = router.attempt_stream("reasoning", None, system="s", user="u")
            first = next(gen)
            self.assertEqual(first.content, "Some real words already shown")
            with self.assertRaises(ProviderUnavailableError):
                next(gen)

        # Only the one, already-committed candidate was ever tried.
        self.assertEqual(len(call_log), 1)

    def test_all_candidates_exhausted_raises_all_providers_unreachable(self):
        router = ModelRouter(health_tracker=ProviderHealthTracker())
        failing = FakeStreamingProvider(raises=ProviderUnavailableError("down"))
        with patch("uri_core.core.model_router.build_provider", return_value=failing):
            with self.assertRaises(AllProvidersUnreachableError):
                list(router.attempt_stream("reasoning", None, system="s", user="u"))

    def test_auth_error_before_content_propagates_immediately_never_caught(self):
        router = ModelRouter(health_tracker=ProviderHealthTracker())
        provider = FakeStreamingProvider(raises=ProviderAuthenticationError("bad key"))
        with patch("uri_core.core.model_router.build_provider", return_value=provider):
            with self.assertRaises(ProviderAuthenticationError):
                list(router.attempt_stream("reasoning", None, system="s", user="u"))

    def test_auth_error_after_content_also_propagates_immediately(self):
        router = ModelRouter(health_tracker=ProviderHealthTracker())
        provider = FakeStreamingProvider(
            chunks=[StreamChunk(content="partial", done=False)],
            raises=ProviderAuthenticationError("revoked mid-stream"),
        )
        with patch("uri_core.core.model_router.build_provider", return_value=provider):
            gen = router.attempt_stream("reasoning", None, system="s", user="u")
            next(gen)
            with self.assertRaises(ProviderAuthenticationError):
                next(gen)

    def test_model_not_found_before_content_marks_unhealthy_and_falls_back(self):
        router = ModelRouter(health_tracker=ProviderHealthTracker())
        failing = FakeStreamingProvider(raises=ModelNotFoundError("no model"))
        succeeding = FakeStreamingProvider(chunks=[_final_chunk(content="ok")])
        call_log = []

        def fake_build(role, principal=None, provider_id_override=None):
            call_log.append(provider_id_override)
            return failing if len(call_log) == 1 else succeeding

        with patch("uri_core.core.model_router.load_model_roles") as mock_roles, \
             patch("uri_core.core.model_router.build_provider", side_effect=fake_build):
            mock_roles.return_value = {"reasoning": {"provider": "primary_p", "model": "primary_m"}}
            chunks = list(router.attempt_stream("reasoning", None, system="s", user="u"))

        self.assertEqual(chunks[-1].final_response.content, "ok")
        self.assertFalse(router._health.is_healthy("primary_p", "primary_m"))


class TestAttemptStreamProviderAgnosticFallback(unittest.TestCase):
    """A provider with no real streaming implementation (the default
    ModelProvider.complete_stream() fallback) must still work correctly
    through attempt_stream() - proves provider-agnostic behaviour end to
    end, not just at the base-class-unit-test level."""

    def test_non_streaming_provider_still_works_via_default_fallback(self):
        from uri_core.core.model_providers.base import ModelProvider

        class NonStreamingProvider(ModelProvider):
            def complete(self, **kwargs):
                return ModelResponse(content="single-shot answer", model="m", provider="p")

            def describe(self):
                raise NotImplementedError

        router = ModelRouter(health_tracker=ProviderHealthTracker())
        with patch("uri_core.core.model_router.build_provider", return_value=NonStreamingProvider()):
            chunks = list(router.attempt_stream("reasoning", None, system="s", user="u"))

        self.assertEqual(len(chunks), 1)
        self.assertTrue(chunks[0].done)
        self.assertEqual(chunks[0].final_response.content, "single-shot answer")
        # TTFT for a non-streaming fallback must equal total duration -
        # never a fabricated improvement (§13.7/§13.8).
        self.assertEqual(chunks[0].ttft_seconds, chunks[0].final_response.duration_seconds)


if __name__ == "__main__":
    unittest.main()
