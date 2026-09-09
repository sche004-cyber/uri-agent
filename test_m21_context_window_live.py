"""M21 regression test: proves, against a real running Ollama server,
that URI's real reasoning prompt is no longer silently truncated.

Before M21: OllamaProvider never sent options.num_ctx, so Ollama loaded
the model at its own hardcoded default (measured at 4096 tokens during
the M21 audit) regardless of prompt size. URI's real reasoning request
(built from ModelReasoningGateway.build_reasoning_request(), the same
code path process_user_input actually uses) measured ~4935 tokens, and
Ollama's own prompt_eval_count for it was 2050 - under half - with no
error, warning, or log anywhere. This is the exact defect
M21 fixes (ModelProviderConfig.context_tokens -> options.num_ctx).

Deliberately does NOT mock Ollama - mirrors test_ollama_provider_live.py/
test_ollama_reasoning_adapter_live.py's existing pattern. Skips (rather
than fails) when Ollama isn't reachable.
"""

import json
import unittest

import requests

from uri_core.core.context_budget import estimate_tokens
from uri_core.core.model_providers.base import ModelProviderConfig
from uri_core.core.model_providers.ollama_provider import OllamaProvider
from uri_core.core.model_reasoning_adapter import OllamaReasoningAdapter
from uri_core.core.model_reasoning_gateway import ModelReasoningGateway


def _ollama_reachable(base_url: str) -> bool:
    try:
        response = requests.get(f"{base_url}/api/version", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


class _CapturingProvider:
    """Wraps a real ModelProvider, recording exactly what was sent and
    what came back - so this test can compare the real transmitted
    prompt size against Ollama's own real prompt_eval_count, without
    faking any part of the actual request/response."""

    def __init__(self, inner):
        self.inner = inner
        self.last_system = None
        self.last_user = None
        self.last_response = None

    def complete(self, *, system, user, temperature=0.0, max_tokens=None):
        self.last_system = system
        self.last_user = user
        response = self.inner.complete(
            system=system,
            user=user,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self.last_response = response
        return response


class ContextWindowLiveTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = ModelProviderConfig.from_env()

        if not _ollama_reachable(cls.config.base_url):
            raise unittest.SkipTest(
                f"Ollama is not reachable at {cls.config.base_url} - "
                "skipping the real context-window regression test."
            )

    def test_real_reasoning_prompt_is_not_silently_truncated(self):
        gateway = ModelReasoningGateway()

        request = gateway.build_reasoning_request(
            user_text=(
                "Find the emails from the registrar about the extension "
                "request and draft a reply."
            ),
            session_context={
                "session_id": "m21-live-check",
                "task": "draft",
                "current_facts": {},
                "evidence_facts": {},
                "historical_facts": {},
                "active_workflow": None,
            },
            evidence_context={},
            query_context={
                "identity": "",
                "soul": "",
                "personalization": {"preferences": ["formal tone"]},
                "session": {},
                "verified_facts": {},
                "capabilities": [],
                "diagnostics": {"last_operation": {}, "recent_events": [], "known_gaps": []},
                "experience": [],
                "attachments": [],
            },
        )
        request_json = json.dumps(request, ensure_ascii=False)

        real_provider = OllamaProvider(config=self.config)
        capturing = _CapturingProvider(real_provider)
        adapter = OllamaReasoningAdapter(provider=capturing)

        adapter(request_json)

        response = capturing.last_response
        self.assertIsNotNone(response)
        self.assertIsNotNone(
            response.prompt_tokens,
            "Ollama did not report prompt_eval_count at all - cannot "
            "verify truncation.",
        )

        transmitted_estimate = estimate_tokens(
            capturing.last_system
        ) + estimate_tokens(capturing.last_user)

        # The core regression check: before M21, this exact request
        # measured ~4935 true tokens but Ollama's prompt_eval_count was
        # 2050 (42%) - well under half. estimate_tokens is a rough
        # chars/4 proxy (documented to run ~15-20% low against a real
        # tokenizer), so 0.7 leaves comfortable margin while still
        # failing hard on real truncation.
        self.assertGreater(
            response.prompt_tokens,
            transmitted_estimate * 0.7,
            f"prompt_tokens={response.prompt_tokens} looks truncated "
            f"against an estimated transmitted size of "
            f"~{transmitted_estimate} tokens (configured "
            f"context_tokens={self.config.context_tokens}).",
        )

        # And the configured window itself must be large enough to hold
        # this real request in the first place.
        self.assertLessEqual(
            response.prompt_tokens, self.config.context_tokens
        )


if __name__ == "__main__":
    unittest.main()
