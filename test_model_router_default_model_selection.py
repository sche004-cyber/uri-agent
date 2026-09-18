"""test_model_router_default_model_selection.py — M32 D3.

Live-verified defect (reproduced directly against this repository's real
ModelRouter, on a machine whose Ollama install does not have the packaged
default model pulled): ModelRouter._model_for_role() returned "" (an
empty string) instead of the real default model whenever a role had no
explicit "model" configured and no Active Brain / explicit override
applied - the exact case every packaged-default deployment hits for
every role. build_provider() itself never had this bug (its own
"ollama" branch already fell back to ModelProviderConfig.from_env().model,
i.e. OLLAMA_MODEL if set, else DEFAULT_OLLAMA_MODEL) - only the router's
OWN internal bookkeeping (ProviderPlan.model, the health-tracker cooldown
key, and every "peek without calling" consumer of router.resolve(), i.e.
response_drafting._resolve_context_budget and
model_reasoning_adapter._resolve_router_context_budget) silently diverged
from what the provider was actually constructed with.

This suite covers the four cases the D3 remediation requires:
  1. missing default model (packaged defaults, nothing configured)
  2. a valid explicitly-configured model (role config / deployment override)
  3. explicit override precedence (per-request model_override, Active Brain)
  4. fail-clear behaviour: an unavailable model still produces a clear,
     honest AllProvidersUnreachableError naming the real model - never a
     silent substitution of some other, arbitrary installed model.
"""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from uri_core.core.model_router import (
    AllProvidersUnreachableError,
    ModelRouter,
    ProviderHealthTracker,
)
from uri_core.core.model_providers.base import (
    DEFAULT_OLLAMA_MODEL,
    ModelNotFoundError,
    ModelResponse,
)
from uri_core.config.model_roles import ROLE_REASONING

_ENV_DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)


class TestMissingDefaultModelResolution(unittest.TestCase):
    """Case 1: role config has no "model" key at all (every packaged-default
    role, on every deployment that has not set OLLAMA_MODEL or a per-role
    override) - resolve() must report the SAME model build_provider()
    would actually construct, never an empty placeholder."""

    def test_resolve_reports_the_real_default_model_not_empty_string(self):
        router = ModelRouter(health_tracker=ProviderHealthTracker())
        plan = router.resolve(ROLE_REASONING)
        self.assertEqual(plan.provider_id, "ollama")
        self.assertEqual(plan.model, _ENV_DEFAULT_MODEL)
        self.assertNotEqual(plan.model, "")

    def test_model_for_role_matches_resolve(self):
        """_model_for_role() (the health-tracker key / attempt() candidate
        model) must agree with resolve()'s own reported model - the two
        must never diverge for the same role/pid."""
        router = ModelRouter(health_tracker=ProviderHealthTracker())
        direct = router._model_for_role(ROLE_REASONING, None, pid="ollama")
        via_resolve = router.resolve(ROLE_REASONING).model
        self.assertEqual(direct, via_resolve)
        self.assertEqual(direct, _ENV_DEFAULT_MODEL)

    def test_env_override_wins_over_packaged_default(self):
        """OLLAMA_MODEL, when set, must be preferred over the packaged
        DEFAULT_OLLAMA_MODEL constant - the exact same precedence
        ModelProviderConfig.from_env() already applies for the provider
        that actually gets constructed."""
        router = ModelRouter(health_tracker=ProviderHealthTracker())
        with patch.dict(os.environ, {"OLLAMA_MODEL": "some-other-installed-model"}):
            plan = router.resolve(ROLE_REASONING)
        self.assertEqual(plan.model, "some-other-installed-model")


class TestValidConfiguredModelResolution(unittest.TestCase):
    """Case 2: a role explicitly configures its own model (deployment
    override / uri_workspace/model_roles.json) - that explicit value must
    always be used verbatim, never replaced by the packaged default."""

    def test_explicit_role_config_model_wins_over_default(self):
        router = ModelRouter(health_tracker=ProviderHealthTracker())
        with patch(
            "uri_core.core.model_router.load_model_roles",
            return_value={ROLE_REASONING: {"provider": "ollama", "model": "custom-configured-model"}},
        ):
            plan = router.resolve(ROLE_REASONING)
        self.assertEqual(plan.model, "custom-configured-model")

    def test_valid_configured_model_completes_successfully(self):
        """Control: once resolved, a valid model completes through attempt()
        exactly as any other successful candidate would."""
        router = ModelRouter(health_tracker=ProviderHealthTracker())
        fake = SimpleNamespace(
            complete=lambda **kwargs: ModelResponse(
                content="answer", model="custom-configured-model", provider="ollama"
            )
        )
        with patch(
            "uri_core.core.model_router.load_model_roles",
            return_value={ROLE_REASONING: {"provider": "ollama", "model": "custom-configured-model"}},
        ), patch("uri_core.core.model_router.build_provider", return_value=fake):
            response = router.attempt(ROLE_REASONING, None, system="s", user="u")
        self.assertEqual(response.content, "answer")


class TestExplicitOverridePrecedence(unittest.TestCase):
    """Case 3: an explicit per-request override (principal.model_override)
    must win over both the packaged default AND any static role config -
    this is the same precedence UnknownModelProviderError/Active-Brain
    tests already lock in for cloud providers; this covers the plain
    "ollama" adapter path specifically."""

    def test_explicit_model_override_wins_over_packaged_default(self):
        router = ModelRouter(health_tracker=ProviderHealthTracker())
        principal = SimpleNamespace(
            user_id=None,
            model_override={"provider_id": "ollama", "model": "user-picked-model"},
        )
        model = router._model_for_role(ROLE_REASONING, principal, pid="ollama")
        self.assertEqual(model, "user-picked-model")
        self.assertNotEqual(model, _ENV_DEFAULT_MODEL)

    def test_explicit_model_override_reaches_resolve(self):
        router = ModelRouter(health_tracker=ProviderHealthTracker())
        principal = SimpleNamespace(
            user_id=None,
            model_override={"provider_id": "ollama", "model": "user-picked-model"},
        )
        plan = router.resolve(ROLE_REASONING, principal)
        self.assertEqual(plan.model, "user-picked-model")


class TestUnavailableModelFailsClearly(unittest.TestCase):
    """Case 4: when the resolved default model is not actually available,
    ModelRouter must fail with a clear, honest error naming that model -
    never silently substitute a different, arbitrary model the deployment
    happens to have installed. "ollama" always being a permitted install
    default (per the module's own §7.1 pipeline) is the ONE architected
    exception, and it still surfaces the real failure, not a fake success."""

    def test_unavailable_default_model_raises_with_real_model_name(self):
        router = ModelRouter(health_tracker=ProviderHealthTracker())
        fake = SimpleNamespace(
            complete=lambda **kwargs: (_ for _ in ()).throw(
                ModelNotFoundError(
                    f"Model '{_ENV_DEFAULT_MODEL}' was not found on this Ollama server. Pull it first."
                )
            )
        )
        with patch("uri_core.core.model_router.build_provider", return_value=fake):
            with self.assertRaises(AllProvidersUnreachableError) as ctx:
                router.attempt(ROLE_REASONING, None, system="s", user="u")

        message = str(ctx.exception)
        self.assertIn(_ENV_DEFAULT_MODEL, message)
        self.assertIn("ModelNotFoundError", message)

    def test_unavailable_default_model_marks_the_real_model_unhealthy(self):
        """The health-tracker cooldown must key on the REAL model that
        failed, not an empty placeholder - otherwise a completely
        different, valid candidate could be mistakenly treated as
        unhealthy (or vice versa) due to key collision on ""."""
        tracker = ProviderHealthTracker()
        router = ModelRouter(health_tracker=tracker)
        fake = SimpleNamespace(
            complete=lambda **kwargs: (_ for _ in ()).throw(ModelNotFoundError("not found"))
        )
        with patch("uri_core.core.model_router.build_provider", return_value=fake):
            with self.assertRaises(AllProvidersUnreachableError):
                router.attempt(ROLE_REASONING, None, system="s", user="u")

        self.assertFalse(tracker.is_healthy("ollama", _ENV_DEFAULT_MODEL))
        # A genuinely different model must be unaffected by the failure above.
        self.assertTrue(tracker.is_healthy("ollama", "a-different-model"))

    def test_no_silent_substitution_when_only_candidate_fails(self):
        """With only one candidate ("ollama", the install default) and it
        failing, the router must degrade honestly (raise) rather than
        inventing a different model to try - existing architecture gives
        it no such authority."""
        router = ModelRouter(health_tracker=ProviderHealthTracker())
        attempted_models = []

        def fake_build(role, principal=None, provider_id_override=None):
            attempted_models.append(
                router._model_for_role(role, principal, pid=provider_id_override)
            )
            return SimpleNamespace(
                complete=lambda **kwargs: (_ for _ in ()).throw(ModelNotFoundError("not found"))
            )

        with patch("uri_core.core.model_router.build_provider", side_effect=fake_build):
            with self.assertRaises(AllProvidersUnreachableError):
                router.attempt(ROLE_REASONING, None, system="s", user="u")

        # Only the single real candidate model was ever tried - no
        # second, different model was silently substituted in.
        self.assertEqual(attempted_models, [_ENV_DEFAULT_MODEL])


if __name__ == "__main__":
    unittest.main()
