"""Live UX Repair (post-launch): regression coverage for a real, confirmed
routing/discovery defect found while live-verifying Groq/API-key
provider support.

Root cause: build_provider()'s `provider_id_override` dispatch compared
a real catalogue provider_id (e.g. "groq", passed by ModelRouter for any
non-static-deployment-config candidate) directly against the three
literal ADAPTER family names ("ollama" / "openai_compatible" /
"anthropic"). This only ever happened to work for "ollama" and
"anthropic", whose provider_id equals their own adapter name - every
other catalogue provider that shares the "openai_compatible" adapter
(groq, openai, openrouter, gemini) could never be reached through
ModelRouter.attempt() at all: build_provider() raised
UnknownModelProviderError immediately, ModelRouter marked the candidate
"failed" and moved on, and a real, valid, verified API key silently
never got used.

A second, related defect: ModelRouter._model_for_role() compared the
Active Brain override's ADAPTER name against the candidate pid too, so
even once a cloud provider became reachable, its real chosen model
string was discarded in favour of the static deployment default model
for every provider except ollama/anthropic.

A third, related defect: ModelRouter._ordered_candidates() never
considered the user's real Active Brain at all unless the User had
separately used the advanced Fallback Routing dialog - "URI Auto" for
an account that had only ever used "Set as Active Brain" always fell
straight through to the static deployment default + ollama.
"""

import os
import unittest
from unittest.mock import patch

from uri_core.config.model_roles import (
    build_provider,
    ROLE_REASONING,
    ROLE_SEMANTIC_INTERPRETATION,
)
from uri_core.core.model_providers import OpenAICompatibleProvider
from uri_core.core.model_router import ModelRouter, ProviderHealthTracker
from uri_core.core.principal_context import PrincipalContext


def _principal(user_id: str) -> PrincipalContext:
    return PrincipalContext(user_id=user_id, role="user", device_id="test-device")


class BuildProviderCloudOverrideTests(unittest.TestCase):
    """build_provider(..., provider_id_override=<real provider_id>) must
    resolve the SAME provider's own config/key, not "openai" defaults or
    an immediate UnknownModelProviderError."""

    def test_groq_override_resolves_groq_config_and_key_not_openai(self):
        with self._tmp_stores() as user_id:
            from uri_core.core.provider_keys import ProviderKeyStore

            ProviderKeyStore(user_id).set_key("groq", "gsk-test-not-a-real-key")

            provider = build_provider(
                ROLE_REASONING, _principal(user_id), provider_id_override="groq"
            )

            self.assertIsInstance(provider, OpenAICompatibleProvider)
            self.assertIn("groq.com", provider._config.base_url)
            self.assertEqual(provider._api_key, "gsk-test-not-a-real-key")

    def test_openrouter_override_also_resolves_correctly(self):
        """Not just Groq - every openai_compatible-adapter provider was
        equally broken by the adapter-vs-provider_id confusion."""
        with self._tmp_stores() as user_id:
            from uri_core.core.provider_keys import ProviderKeyStore

            ProviderKeyStore(user_id).set_key("openrouter", "or-test-not-real")

            provider = build_provider(
                ROLE_REASONING, _principal(user_id), provider_id_override="openrouter"
            )

            self.assertIsInstance(provider, OpenAICompatibleProvider)
            self.assertIn("openrouter.ai", provider._config.base_url)
            self.assertEqual(provider._api_key, "or-test-not-real")

    def test_router_mediated_call_uses_the_real_active_brain_model_not_the_hardcoded_default(self):
        """The second half of the same defect, found only once the first
        half (dispatch) was fixed and live-verified: build_provider()
        adopted the Active Brain's overridden role_config only when
        `overridden_role_config["provider"]` (the ADAPTER, e.g.
        "openai_compatible") equalled provider_id_override (a real
        provider_id, e.g. "groq") - which can never match for any
        provider except "anthropic". So even after dispatch correctly
        resolved to OpenAICompatibleProvider, this role_config was
        silently NOT adopted, and the provider was built with this
        role's hardcoded openai_compatible default model ("gpt-4o")
        instead of the user's real Active Brain model - which the real
        provider then genuinely rejects with ModelNotFoundError. Live-
        reproduced against the real Groq API before this fix."""
        with self._tmp_stores() as user_id:
            from uri_core.core.provider_keys import ProviderKeyStore
            from uri_core.core.provider_registry import ProviderConfigStore

            ProviderKeyStore(user_id).set_key("groq", "gsk-test-not-a-real-key")
            ProviderConfigStore(user_id).set_active_brain("groq", "llama-guard-4-12b")

            provider = build_provider(
                ROLE_SEMANTIC_INTERPRETATION,
                _principal(user_id),
                provider_id_override="groq",
            )

            self.assertEqual(provider._config.model, "llama-guard-4-12b")
            self.assertNotEqual(provider._config.model, "gpt-4o")

    def test_unknown_provider_id_override_still_raises(self):
        from uri_core.config.model_roles import UnknownModelProviderError

        with self.assertRaises(UnknownModelProviderError):
            build_provider(
                ROLE_REASONING, provider_id_override="not_a_real_provider_xyz"
            )

    def test_legacy_adapter_literal_override_unaffected(self):
        """The pre-existing static-deployment-config mechanism (a
        uri_workspace/model_roles.json role whose "provider" field is
        literally the adapter name "ollama") must keep working exactly
        as before - this repair only fixes the real-provider_id path."""
        provider = build_provider(
            ROLE_REASONING, provider_id_override="ollama"
        )
        from uri_core.core.model_providers.ollama_provider import OllamaProvider

        self.assertIsInstance(provider, OllamaProvider)

    from contextlib import contextmanager

    @contextmanager
    def _tmp_stores(self):
        import tempfile
        user_id = "11111111-2222-4333-8444-555555555555"
        with tempfile.TemporaryDirectory() as tmp:
            def _usp(_user, name):
                return os.path.join(tmp, name)

            with patch("uri_core.core.provider_keys.user_scoped_path", side_effect=_usp), \
                 patch("uri_core.core.provider_registry.user_scoped_path", side_effect=_usp), \
                 patch.dict(os.environ, {"URI_PROVIDER_KEY_SECRET": "test_secret_passphrase"}):
                yield user_id


class ModelRouterCloudActiveBrainTests(unittest.TestCase):
    """"URI Auto" (no explicit Fallback Routing) must try a cloud Active
    Brain first, with its own real model - not silently ignore it."""

    def test_ordered_candidates_uses_active_brain_as_implicit_primary(self):
        with self._tmp_stores() as user_id:
            from uri_core.core.provider_registry import ProviderConfigStore

            ProviderConfigStore(user_id).set_active_brain("groq", "llama-3.3-70b-versatile")

            router = ModelRouter(health_tracker=ProviderHealthTracker())
            candidates = router._ordered_candidates(ROLE_REASONING, _principal(user_id))

            self.assertEqual(candidates[0], "groq")
            self.assertIn("ollama", candidates)

    def test_model_for_role_returns_real_active_brain_model_for_cloud_provider(self):
        with self._tmp_stores() as user_id:
            from uri_core.core.provider_registry import ProviderConfigStore

            ProviderConfigStore(user_id).set_active_brain("groq", "llama-3.3-70b-versatile")

            router = ModelRouter(health_tracker=ProviderHealthTracker())
            model = router._model_for_role(ROLE_REASONING, _principal(user_id), pid="groq")

            self.assertEqual(model, "llama-3.3-70b-versatile")

    def test_explicit_fallback_routing_primary_still_wins_over_active_brain(self):
        with self._tmp_stores() as user_id:
            from uri_core.core.provider_registry import ProviderConfigStore
            from uri_core.core.fallback_routing_store import FallbackRoutingStore

            ProviderConfigStore(user_id).set_active_brain("groq", "llama-3.3-70b-versatile")
            FallbackRoutingStore(user_id).save({
                "primary": {"provider_id": "anthropic", "model": "claude-3-5-sonnet"},
                "fallback_1": None,
                "fallback_2": None,
            })

            router = ModelRouter(health_tracker=ProviderHealthTracker())
            candidates = router._ordered_candidates(ROLE_REASONING, _principal(user_id))

            self.assertEqual(candidates[0], "anthropic")

    from contextlib import contextmanager

    @contextmanager
    def _tmp_stores(self):
        import tempfile
        user_id = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
        with tempfile.TemporaryDirectory() as tmp:
            def _usp(_user, name):
                return os.path.join(tmp, name)

            with patch("uri_core.core.provider_registry.user_scoped_path", side_effect=_usp), \
                 patch("uri_core.core.fallback_routing_store.user_scoped_path", side_effect=_usp):
                yield user_id


if __name__ == "__main__":
    unittest.main()
