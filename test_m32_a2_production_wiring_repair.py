"""M32 Batch A2 production-wiring repair, 2026-09-18.

Sonnet's architecture review found that the context-trimming mechanism
built for A2 (context_trimmer.trim_reasoning_request) never actually ran
on the real production path: OllamaReasoningAdapter.__call__ gated its
trim call on `self._explicit_provider is not None`, but every production
construction site (server.py) constructs the adapter with no injected
provider, so that branch is production's normal path and was completely
unprotected except by OllamaProvider.complete()'s raw hard refusal - with
no trim attempt first. The drafting call (response_drafting.draft_response)
had no trimming at all, on either path.

These tests exercise the adapters exactly as production constructs them -
no injected provider, get_router() patched to a fake router rather than a
fake provider - so a regression back to the old (test-path-only) wiring
would fail here even though every pre-existing test (which always injects
a provider) would keep passing.
"""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from uri_core.core.context_budget import estimate_tokens
from uri_core.core.model_providers.base import ModelResponse
from uri_core.core.model_reasoning_adapter import (
    OllamaReasoningAdapter,
    _REASONING_MAX_TOKENS,
)
from uri_core.core.model_reasoning_gateway import ModelReasoningGateway
from uri_core.core.response_drafting import (
    DRAFTING_MAX_TOKENS,
    DraftRequest,
    ResponseDraftingError,
    draft_response,
)


class _FakeRouter:
    """Stands in for ModelRouter: resolve() reports a fixed candidate
    without building a provider; attempt() records the exact kwargs it
    was called with and returns a fixed ModelResponse. Never touches a
    real provider or network."""

    def __init__(self, provider_id, model, response_content):
        self._plan = SimpleNamespace(provider_id=provider_id, model=model)
        self._response_content = response_content
        self.recorded_calls = []

    def resolve(self, role, principal):
        return self._plan

    def attempt(self, role, principal, **complete_kwargs):
        self.recorded_calls.append(complete_kwargs)
        return ModelResponse(
            content=self._response_content, model=self._plan.model, provider=self._plan.provider_id
        )


class _RefusingRouter:
    """A router whose attempt() must never be reached - used to prove
    trimming/refusal happens strictly before any provider call."""

    def __init__(self):
        self.recorded_calls = []

    def resolve(self, role, principal):
        return SimpleNamespace(provider_id="ollama", model="tiny:1b")

    def attempt(self, role, principal, **complete_kwargs):
        self.recorded_calls.append(complete_kwargs)
        raise AssertionError(
            "router.attempt() must not be reached when trimming cannot "
            "fit the request - the whole point of trim-before-send"
        )


class ReasoningRouterPathTrimmingTests(unittest.TestCase):
    """OllamaReasoningAdapter() with NO injected provider - the exact
    construction every production call site (server.py) uses."""

    def test_router_path_trims_oversized_request_before_send(self):
        router = _FakeRouter("ollama", "gemma4:12b", '{"action": null}')

        with patch(
            "uri_core.core.model_providers.ollama_provider.resolve_model_context_tokens",
            return_value=8192,
        ), patch("uri_core.core.model_reasoning_adapter.get_router", return_value=router):

            adapter = OllamaReasoningAdapter()  # production shape: no provider=
            gateway = ModelReasoningGateway(model_callable=adapter)

            huge_evidence = {f"item_{i}": "x" * 2000 for i in range(25)}
            result = gateway.reason(user_text="Summarize", evidence_context=huge_evidence)

        self.assertEqual(result["status"], "proposal_ready")
        self.assertEqual(len(router.recorded_calls), 1)
        sent = router.recorded_calls[0]
        transmitted_tokens = estimate_tokens(sent["system"]) + estimate_tokens(sent["user"])
        self.assertLessEqual(transmitted_tokens + _REASONING_MAX_TOKENS, 8192)

    def test_router_path_preserves_policy_and_identity_under_trimming(self):
        router = _FakeRouter("ollama", "gemma4:12b", '{"action": null}')

        with patch(
            "uri_core.core.model_providers.ollama_provider.resolve_model_context_tokens",
            return_value=8192,
        ), patch("uri_core.core.model_reasoning_adapter.get_router", return_value=router):

            adapter = OllamaReasoningAdapter()
            gateway = ModelReasoningGateway(model_callable=adapter)
            policy = gateway.load_policy()

            huge_evidence = {f"item_{i}": "x" * 2000 for i in range(25)}
            gateway.reason(
                user_text="Summarize",
                evidence_context=huge_evidence,
                query_context={"soul": "URI SOUL TEXT", "identity": "URI"},
            )

        sent = router.recorded_calls[0]
        self.assertIn(policy, sent["system"])
        transmitted = json.loads(sent["user"])
        self.assertEqual(transmitted["query_context"]["soul"], "URI SOUL TEXT")
        self.assertEqual(transmitted["query_context"]["identity"], "URI")

    def test_router_path_small_window_fails_honestly_without_reaching_provider(self):
        router = _RefusingRouter()

        with patch(
            "uri_core.core.model_providers.ollama_provider.resolve_model_context_tokens",
            return_value=500,
        ), patch("uri_core.core.model_reasoning_adapter.get_router", return_value=router):

            adapter = OllamaReasoningAdapter()
            gateway = ModelReasoningGateway(model_callable=adapter)
            result = gateway.reason(user_text="Do something")

        self.assertEqual(result["status"], "context_window_exceeded")
        self.assertIn("exceeds configured context window", result["error"])
        self.assertEqual(len(router.recorded_calls), 0)


class DraftingRouterPathTrimmingTests(unittest.TestCase):
    """draft_response() with NO injected provider - the shape
    orchestrator.py's _draft_narrative_safely actually uses in production."""

    def test_router_path_trims_oversized_query_context(self):
        router = _FakeRouter("ollama", "gemma4:12b", "All done.")
        huge_conversation = [
            {"user": f"turn {i}: " + "z" * 300, "uri": f"reply {i}: " + "w" * 300}
            for i in range(60)
        ]
        request = DraftRequest(
            user_text="what happened?",
            outcome={"execution": {"status": "success"}, "response": {}, "known_gaps": None},
            personalization={},
            policy_text="POLICY TEXT",
            query_context={"conversation": huge_conversation, "identity": "", "soul": ""},
        )

        with patch(
            "uri_core.core.model_providers.ollama_provider.resolve_model_context_tokens",
            return_value=8192,
        ), patch("uri_core.core.response_drafting.get_router", return_value=router):
            text = draft_response(request, principal=None)

        self.assertEqual(text, "All done.")
        self.assertEqual(len(router.recorded_calls), 1)
        sent = router.recorded_calls[0]
        transmitted_tokens = estimate_tokens(sent["system"]) + estimate_tokens(sent["user"])
        self.assertLessEqual(transmitted_tokens + DRAFTING_MAX_TOKENS, 8192)

        payload = json.loads(sent["user"])
        self.assertEqual(payload["user_request"], "what happened?")
        self.assertEqual(payload["outcome"], request.outcome)

    def test_router_path_small_window_raises_response_drafting_error_without_reaching_provider(self):
        router = _RefusingRouter()
        request = DraftRequest(
            user_text="x" * 5000,
            outcome={"execution": {"status": "success"}, "response": {}, "known_gaps": None},
            personalization={},
            policy_text="POLICY TEXT",
        )

        with patch(
            "uri_core.core.model_providers.ollama_provider.resolve_model_context_tokens",
            return_value=50,
        ), patch("uri_core.core.response_drafting.get_router", return_value=router):
            with self.assertRaises(ResponseDraftingError):
                draft_response(request, principal=None)

        self.assertEqual(len(router.recorded_calls), 0)


class HeadroomSingleSourceTests(unittest.TestCase):
    """The output headroom used to gate trimming must be the exact same
    value passed as max_tokens to complete() for that call - two
    independently hardcoded constants that happen to agree today is
    exactly the drift risk flagged in review."""

    def test_reasoning_max_tokens_matches_trim_headroom(self):
        router = _FakeRouter("ollama", "gemma4:12b", '{"action": null}')
        with patch(
            "uri_core.core.model_providers.ollama_provider.resolve_model_context_tokens",
            return_value=8192,
        ), patch("uri_core.core.model_reasoning_adapter.get_router", return_value=router):
            adapter = OllamaReasoningAdapter()
            gateway = ModelReasoningGateway(model_callable=adapter)
            gateway.reason(user_text="hi")

        self.assertEqual(router.recorded_calls[0]["max_tokens"], _REASONING_MAX_TOKENS)
        self.assertEqual(_REASONING_MAX_TOKENS, 800)

    def test_drafting_max_tokens_matches_trim_headroom_and_differs_from_reasoning(self):
        router = _FakeRouter("ollama", "gemma4:12b", "ok")
        request = DraftRequest(
            user_text="hi",
            outcome={"execution": {"status": "success"}, "response": {}},
            personalization={},
            policy_text="POLICY",
        )
        with patch(
            "uri_core.core.model_providers.ollama_provider.resolve_model_context_tokens",
            return_value=8192,
        ), patch("uri_core.core.response_drafting.get_router", return_value=router):
            draft_response(request, principal=None)

        self.assertEqual(router.recorded_calls[0]["max_tokens"], DRAFTING_MAX_TOKENS)
        self.assertEqual(DRAFTING_MAX_TOKENS, 300)
        self.assertNotEqual(DRAFTING_MAX_TOKENS, _REASONING_MAX_TOKENS)


if __name__ == "__main__":
    unittest.main()
