"""M22.6 Degraded Mode & Unreachable Fallback Tests.

Validates acceptance criteria 1, 3, and Claude remediation finding 1 & 3:
- When all candidates in the fallback chain are exhausted, AllProvidersUnreachableError
  is raised with chain details.
- resolve() returns ProviderPlan(provider_id=None) in degraded mode.
- UnknownModelProviderError (e.g. unconfigured provider or missing principal)
  advances the fallback chain to the install default (ollama) without marking unhealthy.
- DocumentComposer.compose() produces a clean fallback document on unreachable/unknown provider.
- Deterministic capabilities remain fully operable when providers are unreachable.
"""

import unittest
from unittest.mock import MagicMock, patch

from uri_core.core.model_router import (
    AllProvidersUnreachableError,
    ModelRouter,
    ProviderHealthTracker,
    ProviderPlan,
)
from uri_core.core.model_providers.base import (
    ModelNotFoundError,
    ModelResponse,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from uri_core.config.model_roles import (
    ROLE_DOCUMENT_COMPOSITION,
    ROLE_REASONING,
    UnknownModelProviderError,
)
from uri_core.services.document_composer import DocumentComposer
from uri_core.core.model_reasoning_adapter import OllamaReasoningAdapter


class TestModelRouterDegradedMode(unittest.TestCase):
    def setUp(self):
        self.health = ProviderHealthTracker()
        self.router = ModelRouter(health_tracker=self.health)

    def test_all_unhealthy_candidates_resolve_to_degraded_plan(self):
        """When all candidates are marked unhealthy, resolve() returns provider_id=None."""
        # Force ollama and primary unhealthy
        self.health.mark_unhealthy("ollama", "")
        self.health.mark_unhealthy("openai", "")
        plan = self.router.resolve(ROLE_REASONING)
        self.assertIsNone(plan.provider_id)
        self.assertIn("ollama(unhealthy)", plan.fallback_chain)

    def test_exhausted_chain_raises_all_providers_unreachable_error(self):
        """When every provider in chain fails transiently, AllProvidersUnreachableError is raised."""
        with patch("uri_core.core.model_router.build_provider") as mock_bp:
            fake = MagicMock()
            fake.complete.side_effect = ProviderUnavailableError("service down")
            mock_bp.return_value = fake

            with self.assertRaises(AllProvidersUnreachableError) as ctx:
                self.router.attempt(ROLE_REASONING, None, system="sys", user="usr")

            self.assertIn("All providers exhausted", str(ctx.exception))
            self.assertIn("failed:ProviderUnavailableError", str(ctx.exception))

    def test_transient_error_advances_to_next_candidate(self):
        """A transient error on the first provider falls back to the next candidate in chain."""
        with patch("uri_core.core.model_router.load_model_roles") as mock_roles, \
             patch("uri_core.core.model_router.build_provider") as mock_bp:
            mock_roles.return_value = {
                ROLE_REASONING: {"provider": "primary_p", "model": "primary_m"}
            }
            failing = MagicMock()
            failing.complete.side_effect = ProviderTimeoutError("timed out")
            succeeding = MagicMock()
            succeeding.complete.return_value = ModelResponse(content="fallback answer", model="test_m", provider="test_p")

            mock_bp.side_effect = lambda role, principal, provider_id_override: (
                failing if provider_id_override == "primary_p" else succeeding
            )

            resp = self.router.attempt(ROLE_REASONING, None, system="s", user="u")
            self.assertEqual(resp.content, "fallback answer")
            # primary_p should be marked unhealthy
            self.assertFalse(self.health.is_healthy("primary_p", "primary_m"))

    @patch("uri_core.core.model_router.load_model_roles")
    @patch("uri_core.core.model_router.build_provider")
    def test_unknown_provider_error_falls_back_to_ollama(self, mock_bp, mock_roles):
        """UnknownModelProviderError (e.g. missing principal or config) advances chain to ollama
        without marking the provider globally unhealthy."""
        mock_roles.return_value = {
            ROLE_REASONING: {"provider": "openai_compatible", "model": "gpt-4o"}
        }
        mock_health = MagicMock()
        mock_health.is_healthy.return_value = True
        router = ModelRouter(health_tracker=mock_health)

        first_fail = UnknownModelProviderError("no principal supplied for openai_compatible")
        second_ok = MagicMock()
        second_ok.complete.return_value = ModelResponse(content="ollama answer", model="test_m", provider="test_p")

        def bp_side_effect(role, principal, provider_id_override):
            if provider_id_override == "openai_compatible":
                raise first_fail
            return second_ok

        mock_bp.side_effect = bp_side_effect

        resp = router.attempt(ROLE_REASONING, None, system="s", user="u")
        self.assertEqual(resp.content, "ollama answer")
        # Ensure UnknownModelProviderError did NOT mark unhealthy
        mock_health.mark_unhealthy.assert_not_called()

    def test_document_composer_handles_all_providers_unreachable(self):
        """DocumentComposer.compose() produces a fallback document when all providers are unreachable."""
        with patch.object(self.router, "attempt") as mock_attempt, \
             patch("uri_core.services.document_composer.get_router", return_value=self.router):
            mock_attempt.side_effect = AllProvidersUnreachableError("all down")

            composer = DocumentComposer()
            result = composer.compose(
                brief={"document_type": "noting", "purpose": "administrative"},
                request_text="Draft administrative approval",
            )
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["composed_by"], "fallback")
            self.assertIn("The reasoning model was unreachable", result["detail"])
            self.assertIn("DRAFT (NOTING)", result["body"])

    def test_document_composer_handles_unknown_model_provider_error(self):
        """DocumentComposer.compose() produces a fallback document on UnknownModelProviderError."""
        with patch.object(self.router, "attempt") as mock_attempt, \
             patch("uri_core.services.document_composer.get_router", return_value=self.router):
            mock_attempt.side_effect = UnknownModelProviderError("no principal for openai_compatible")

            composer = DocumentComposer()
            result = composer.compose(
                brief={"document_type": "order", "purpose": "policy"},
                request_text="Draft office order",
            )
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["composed_by"], "fallback")
            self.assertIn("The reasoning model was unreachable", result["detail"])

    def test_document_composer_per_call_principal_threading(self):
        """DocumentComposer.compose(principal=...) passes explicit per-call principal to router."""
        with patch.object(self.router, "attempt") as mock_attempt, \
             patch("uri_core.services.document_composer.get_router", return_value=self.router):
            mock_attempt.return_value = ModelResponse(content="Valid note sheet body with sufficient structure.", model="test_m", provider="test_p")

            mock_principal = MagicMock(user_id="user_123")
            composer = DocumentComposer()  # No principal at init
            result = composer.compose(
                brief={"document_type": "noting", "purpose": "test"},
                request_text="Draft note",
                principal=mock_principal,
            )
            # Verify attempt was called with the per-call principal
            mock_attempt.assert_called_once()
            args, kwargs = mock_attempt.call_args
            self.assertEqual(args[0], ROLE_DOCUMENT_COMPOSITION)
            self.assertEqual(args[1], mock_principal)

    def test_ollama_reasoning_adapter_threads_principal(self):
        """OllamaReasoningAdapter(principal=principal) threads that principal to ModelRouter.attempt."""
        with patch("uri_core.core.model_reasoning_adapter.get_router") as mock_get_router:
            mock_router = MagicMock()
            mock_router.attempt.return_value = ModelResponse(content='{"status": "ok"}', model="test_m", provider="test_p")
            mock_get_router.return_value = mock_router

            mock_principal = MagicMock(user_id="user_456")
            adapter = OllamaReasoningAdapter(principal=mock_principal)
            adapter('{"request": "test"}')

            mock_router.attempt.assert_called_once()
            args, kwargs = mock_router.attempt.call_args
            self.assertEqual(args[0], ROLE_REASONING)
            self.assertEqual(args[1], mock_principal)

    def test_deterministic_capabilities_unaffected_when_providers_unreachable(self):
        """Deterministic operations (e.g. ProviderPlan inspection, router resolve)
        do not fail or call a model when all providers are unreachable."""
        self.health.mark_unhealthy("ollama", "")
        plan = self.router.resolve(ROLE_REASONING)
        self.assertIsNone(plan.provider_id)
        self.assertEqual(len(plan.fallback_chain), 1)
        self.assertEqual(plan.fallback_chain[0], "ollama(unhealthy)")


if __name__ == "__main__":
    unittest.main()