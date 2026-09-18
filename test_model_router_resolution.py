"""test_model_router_resolution.py — M22.6 acceptance criterion #1.

Verifies that ModelRouter.resolve() follows the exact pipeline order
specified in URI_M22_ARCHITECTURE.md §7.1:
  primary → health check → budget seam (always-pass) → install default → degrade
"""
import os
import time
import unittest
from unittest.mock import patch

from uri_core.core.model_router import (
    AllProvidersUnreachableError,
    ModelRouter,
    ProviderHealthTracker,
    ProviderPlan,
    get_router,
)
from uri_core.core.model_providers.base import (
    DEFAULT_OLLAMA_MODEL,
    ModelNotFoundError,
    ModelResponse,
    ProviderAuthenticationError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

# ModelRouter._model_for_role() now resolves an unconfigured "ollama"
# candidate to this same default (OLLAMA_MODEL env override, else the
# packaged DEFAULT_OLLAMA_MODEL) instead of "" - see model_router.py's
# own default-model-selection fix (M32 D3). Health-tracker keys used by
# these tests must match the real key the router now computes.
_DEFAULT_OLLAMA_KEY_MODEL = os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)


class FakeProvider:
    def __init__(self, response_text="ok", raises=None):
        self._response = response_text
        self._raises = raises
        self.call_count = 0

    def complete(self, **kwargs):
        self.call_count += 1
        if self._raises:
            raise self._raises
        return ModelResponse(
            content=self._response,
            model="fake-model",
            provider="fake",
        )


class TestResolveReturnsHealthyPrimary(unittest.TestCase):
    def test_primary_returned_when_healthy(self):
        tracker = ProviderHealthTracker()
        router = ModelRouter(health_tracker=tracker)
        plan = router.resolve("reasoning")
        # Primary for the default all-ollama config is 'ollama'
        self.assertEqual(plan.provider_id, "ollama")
        self.assertIsInstance(plan.fallback_chain, list)
        self.assertGreater(len(plan.fallback_chain), 0)

    def test_unhealthy_primary_skipped(self):
        tracker = ProviderHealthTracker()
        # Mark ollama unhealthy
        tracker.mark_unhealthy("ollama", _DEFAULT_OLLAMA_KEY_MODEL)
        router = ModelRouter(health_tracker=tracker)
        plan = router.resolve("reasoning")
        # With ollama unhealthy and no other candidates, degrades
        self.assertIsNone(plan.provider_id)
        self.assertTrue(any("unhealthy" in c for c in plan.fallback_chain))

    def test_fallback_chain_populated(self):
        tracker = ProviderHealthTracker()
        router = ModelRouter(health_tracker=tracker)
        plan = router.resolve("semantic_interpretation")
        self.assertIsInstance(plan.fallback_chain, list)
        # At minimum, the primary candidate should appear
        self.assertGreater(len(plan.fallback_chain), 0)

    def test_budget_seam_always_passes(self):
        """_budget_ok() must return True in M22.6 (named no-op)."""
        router = ModelRouter()
        self.assertTrue(router._budget_ok("ollama", "reasoning", None))
        self.assertTrue(router._budget_ok("openai_compatible", "drafting", None))
        self.assertTrue(router._budget_ok("any_provider", "any_role", object()))

    def test_degrade_path_provider_id_is_none(self):
        tracker = ProviderHealthTracker()
        router = ModelRouter(health_tracker=tracker)
        # Mark all candidates unhealthy
        tracker.mark_unhealthy("ollama", _DEFAULT_OLLAMA_KEY_MODEL)
        tracker.mark_unhealthy("openai_compatible", "")
        plan = router.resolve("reasoning")
        self.assertIsNone(plan.provider_id)

    def test_resolve_does_not_raise(self):
        """resolve() returns a ProviderPlan even on full degrade — never raises."""
        tracker = ProviderHealthTracker()
        # Force every possible candidate to be unhealthy
        tracker.mark_unhealthy("ollama", _DEFAULT_OLLAMA_KEY_MODEL)
        tracker.mark_unhealthy("openai_compatible", "")
        router = ModelRouter(health_tracker=tracker)
        plan = router.resolve("reasoning")
        self.assertIsInstance(plan, ProviderPlan)

    def test_get_router_returns_singleton(self):
        r1 = get_router()
        r2 = get_router()
        self.assertIs(r1, r2)


class TestHealthTrackerCooldown(unittest.TestCase):
    def test_healthy_initially(self):
        tracker = ProviderHealthTracker()
        self.assertTrue(tracker.is_healthy("ollama", "qwen3:14b"))

    def test_mark_unhealthy_takes_effect(self):
        tracker = ProviderHealthTracker()
        tracker.mark_unhealthy("ollama", "qwen3:14b")
        self.assertFalse(tracker.is_healthy("ollama", "qwen3:14b"))

    def test_reset_clears_unhealthy(self):
        tracker = ProviderHealthTracker()
        tracker.mark_unhealthy("ollama", "model1")
        self.assertFalse(tracker.is_healthy("ollama", "model1"))
        tracker.reset("ollama", "model1")
        self.assertTrue(tracker.is_healthy("ollama", "model1"))

    def test_different_keys_independent(self):
        tracker = ProviderHealthTracker()
        tracker.mark_unhealthy("ollama", "model-a")
        self.assertFalse(tracker.is_healthy("ollama", "model-a"))
        self.assertTrue(tracker.is_healthy("ollama", "model-b"))
        self.assertTrue(tracker.is_healthy("other", "model-a"))


if __name__ == "__main__":
    unittest.main()
