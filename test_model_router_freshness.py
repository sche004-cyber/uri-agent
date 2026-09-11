"""test_model_router_freshness.py — M22.6 acceptance criterion #7 / §0.1.

Verifies that long-lived instances of ProviderSemanticInterpreter,
OllamaReasoningAdapter, and DocumentComposer re-resolve via the ModelRouter
on EACH call — they do NOT cache a provider at construction time.

The test changes the health state of the router between two calls on the
SAME long-lived instance. If the instance had cached the provider at
construction time, the second call would not pick up the health change.
With per-call resolution, the second call skips the unhealthy provider.

This is M22.6 §0.1 (per-call resolution), explicitly accepted by the User.
"""
import json
import unittest
from unittest.mock import patch, MagicMock

from uri_core.core.model_router import ModelRouter, ProviderHealthTracker, AllProvidersUnreachableError
from uri_core.core.model_providers.base import (
    ModelResponse,
    ProviderAuthenticationError,
    ProviderUnavailableError,
)
from uri_core.core.provider_semantic_interpreter import ProviderSemanticInterpreter
from uri_core.core.model_reasoning_adapter import OllamaReasoningAdapter
from uri_core.services.document_composer import DocumentComposer


MINIMAL_INTERPRET_RESULT = json.dumps({
    "goal": "test",
    "task_type": "test",
    "domain": "test",
    "entities": [],
    "requested_output": "test",
    "requires_evidence": False,
    "requires_clarification": False,
    "suggested_next_step": "none",
})


class FakeModelResponse:
    def __init__(self, content):
        self.content = content


class FakeProvider:
    def __init__(self, content, call_log=None, tag=""):
        self._content = content
        self._call_log = call_log
        self._tag = tag

    def complete(self, **kwargs):
        if self._call_log is not None:
            self._call_log.append(self._tag)
        return FakeModelResponse(self._content)


class TestSemanticInterpreterFreshness(unittest.TestCase):
    """ProviderSemanticInterpreter must resolve via router on each interpret() call."""

    def test_per_call_resolution(self):
        """Changing health state between calls is reflected in the second call."""
        tracker = ProviderHealthTracker()
        router = ModelRouter(health_tracker=tracker)

        call_log = []

        # Build ONE long-lived instance (no explicit provider — router path)
        interp = ProviderSemanticInterpreter()

        # Patch get_router to return our controlled router
        with patch("uri_core.core.provider_semantic_interpreter.get_router", return_value=router):
            # Patch router.attempt to track calls
            call_count = [0]

            original_attempt = router.attempt

            def counting_attempt(role, principal=None, **kwargs):
                call_count[0] += 1
                return FakeModelResponse(MINIMAL_INTERPRET_RESULT)

            router.attempt = counting_attempt

            # First call
            interp.interpret("hello")
            self.assertEqual(call_count[0], 1)

            # Second call on the SAME instance — must call router again
            interp.interpret("world")
            self.assertEqual(call_count[0], 2,
                "OllamaReasoningAdapter must call router on every interpret() — "
                "not cache the provider at construction time")

            router.attempt = original_attempt

    def test_explicit_provider_bypasses_router(self):
        """When explicit provider is given, router is NOT called."""
        fake = FakeProvider(MINIMAL_INTERPRET_RESULT)
        interp = ProviderSemanticInterpreter(provider=fake)

        with patch("uri_core.core.provider_semantic_interpreter.get_router") as mock_router:
            interp.interpret("hello")
            mock_router.assert_not_called()


class TestOllamaReasoningAdapterFreshness(unittest.TestCase):
    """OllamaReasoningAdapter must resolve via router on each __call__."""

    def test_per_call_resolution(self):
        adapter = OllamaReasoningAdapter()

        call_count = [0]

        def counting_attempt(role, principal=None, **kwargs):
            call_count[0] += 1
            return FakeModelResponse('{"proposal": "test"}')

        mock_router = MagicMock()
        mock_router.attempt.side_effect = counting_attempt

        with patch("uri_core.core.model_reasoning_adapter.get_router", return_value=mock_router):
            adapter('{"request": "test1"}')
            self.assertEqual(call_count[0], 1)

            adapter('{"request": "test2"}')
            self.assertEqual(call_count[0], 2,
                "OllamaReasoningAdapter must call router on every __call__ — "
                "not cache the provider at construction time")

    def test_explicit_provider_bypasses_router(self):
        fake = FakeProvider('{"result": "ok"}')
        adapter = OllamaReasoningAdapter(provider=fake)

        with patch("uri_core.core.model_reasoning_adapter.get_router") as mock_router:
            adapter('{"request": "test"}')
            mock_router.assert_not_called()


class TestDocumentComposerFreshness(unittest.TestCase):
    """DocumentComposer must resolve via router on each compose() call."""

    MINIMAL_BRIEF = {
        "document_type": "noting",
        "subject": "Test Subject",
        "parties": [],
        "conventions": {},
    }

    def test_per_call_resolution(self):
        composer = DocumentComposer()

        call_count = [0]

        def counting_attempt(role, principal=None, **kwargs):
            call_count[0] += 1
            return FakeModelResponse("Test document body for test subject.")

        mock_router = MagicMock()
        mock_router.attempt.side_effect = counting_attempt

        with patch("uri_core.services.document_composer.get_router", return_value=mock_router):
            composer.compose(
                brief=self.MINIMAL_BRIEF,
                request_text="Draft a noting about test subject",
            )
            self.assertEqual(call_count[0], 1)

            composer.compose(
                brief=self.MINIMAL_BRIEF,
                request_text="Draft another noting",
            )
            self.assertEqual(call_count[0], 2,
                "DocumentComposer must call router on every compose() — "
                "not cache the provider at construction time")

    def test_explicit_provider_bypasses_router(self):
        fake = FakeProvider("Test document body for test subject.")
        composer = DocumentComposer(provider=fake)

        with patch("uri_core.services.document_composer.get_router") as mock_router:
            composer.compose(
                brief=self.MINIMAL_BRIEF,
                request_text="Draft a noting",
            )
            mock_router.assert_not_called()


if __name__ == "__main__":
    unittest.main()
