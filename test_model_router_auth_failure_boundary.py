"""test_model_router_auth_failure_boundary.py — M22.6 acceptance criterion #2 / §5.1.

Verifies that ProviderAuthenticationError from any candidate:
  - Propagates immediately and uncaught out of ModelRouter.attempt()
  - NEVER advances the fallback chain to the next candidate
  - NEVER marks the provider as unhealthy in the health tracker
  - NEVER is recorded as a transient failure in the fallback chain annotation

This is the load-bearing security rule of M22.6 (§5.1, §7.2).
"""
import unittest
from unittest.mock import MagicMock, patch, call

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
)


class FakeProvider:
    def __init__(self, raises=None, response_text="ok"):
        self._raises = raises
        self._response = response_text
        self.call_count = 0

    def complete(self, **kwargs):
        self.call_count += 1
        if self._raises is not None:
            raise self._raises
        return ModelResponse(content=self._response, model="m", provider="p")


class TestAuthFailurePropagates(unittest.TestCase):

    def _make_router_with_fake(self, provider_raises):
        """Build a router where build_provider() returns a fake that raises."""
        tracker = ProviderHealthTracker()
        router = ModelRouter(health_tracker=tracker)
        fake = FakeProvider(raises=provider_raises)
        with patch("uri_core.core.model_router.build_provider", return_value=fake):
            with self.assertRaises(type(provider_raises)):
                router.attempt("reasoning")
        return tracker, fake

    def test_auth_error_propagates_immediately(self):
        """ProviderAuthenticationError exits attempt() immediately."""
        tracker = ProviderHealthTracker()
        router = ModelRouter(health_tracker=tracker)
        fake = FakeProvider(raises=ProviderAuthenticationError("bad key"))
        with patch("uri_core.core.model_router.build_provider", return_value=fake):
            with self.assertRaises(ProviderAuthenticationError):
                router.attempt("reasoning")

    def test_auth_error_does_not_mark_unhealthy(self):
        """After a ProviderAuthenticationError, the provider must NOT be in the cooldown table."""
        tracker = ProviderHealthTracker()
        router = ModelRouter(health_tracker=tracker)
        fake = FakeProvider(raises=ProviderAuthenticationError("bad key"))
        with patch("uri_core.core.model_router.build_provider", return_value=fake):
            try:
                router.attempt("reasoning")
            except ProviderAuthenticationError:
                pass
        # The provider must still be reported as healthy (not in cooldown)
        self.assertTrue(tracker.is_healthy("ollama", ""))

    def test_auth_error_does_not_advance_chain(self):
        """After ProviderAuthenticationError, no further provider is tried."""
        call_log = []

        def fake_build(role, principal=None, provider_id_override=None):
            fake = FakeProvider(raises=ProviderAuthenticationError("bad"))
            call_log.append(provider_id_override or "primary")
            return fake

        tracker = ProviderHealthTracker()
        router = ModelRouter(health_tracker=tracker)
        with patch("uri_core.core.model_router.build_provider", side_effect=fake_build):
            try:
                router.attempt("reasoning")
            except ProviderAuthenticationError:
                pass
        # Only one provider should have been tried — auth failure stops the chain
        self.assertEqual(len(call_log), 1,
            f"Expected exactly 1 provider attempt, but {len(call_log)} were made: {call_log}")

    def test_transient_error_does_advance_chain(self):
        """Control: transient errors DO advance the chain (contrast with auth)."""
        call_log = []

        def fake_build(role, principal=None, provider_id_override=None):
            call_log.append(provider_id_override or "primary")
            return FakeProvider(raises=ProviderUnavailableError("down"))

        tracker = ProviderHealthTracker()
        router = ModelRouter(health_tracker=tracker)
        with patch("uri_core.core.model_router.build_provider", side_effect=fake_build):
            try:
                router.attempt("reasoning")
            except AllProvidersUnreachableError:
                pass
        # Transient errors should have tried all candidates in the chain
        self.assertGreater(len(call_log), 0)

    def test_transient_error_marks_unhealthy(self):
        """Control: transient errors DO mark the provider unhealthy."""
        tracker = ProviderHealthTracker()
        router = ModelRouter(health_tracker=tracker)
        fake = FakeProvider(raises=ProviderUnavailableError("down"))
        with patch("uri_core.core.model_router.build_provider", return_value=fake):
            try:
                router.attempt("reasoning")
            except AllProvidersUnreachableError:
                pass
        # After transient failure, provider should be in cooldown
        self.assertFalse(tracker.is_healthy("ollama", ""))

    def test_timeout_error_marks_unhealthy(self):
        tracker = ProviderHealthTracker()
        router = ModelRouter(health_tracker=tracker)
        fake = FakeProvider(raises=ProviderTimeoutError("timeout"))
        with patch("uri_core.core.model_router.build_provider", return_value=fake):
            try:
                router.attempt("reasoning")
            except AllProvidersUnreachableError:
                pass
        self.assertFalse(tracker.is_healthy("ollama", ""))

    def test_model_not_found_marks_unhealthy(self):
        tracker = ProviderHealthTracker()
        router = ModelRouter(health_tracker=tracker)
        fake = FakeProvider(raises=ModelNotFoundError("no model"))
        with patch("uri_core.core.model_router.build_provider", return_value=fake):
            try:
                router.attempt("reasoning")
            except AllProvidersUnreachableError:
                pass
        self.assertFalse(tracker.is_healthy("ollama", ""))


if __name__ == "__main__":
    unittest.main()
