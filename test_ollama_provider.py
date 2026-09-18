import unittest
from unittest.mock import MagicMock, patch

import requests

from uri_core.core.model_providers.base import (
    DEFAULT_HEALTH_CHECK_TIMEOUT_SECONDS,
    ContextWindowExceededError,
    ModelNotFoundError,
    ModelProviderConfig,
    ModelProviderStatus,
    ModelResponse,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from uri_core.core.model_providers.ollama_provider import OllamaProvider


def _config():
    return ModelProviderConfig(
        base_url="http://localhost:11434",
        model="qwen3:14b",
        timeout_seconds=5.0,
    )


def _fake_ok_response(content="{}", model="qwen3:14b"):
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "model": model,
        "message": {"role": "assistant", "content": content},
    }
    return response


def _fake_stream_response(lines, status_code=200):
    """M32 D5: a fake `requests.post(..., stream=True)` response whose
    `.iter_lines()` yields the given NDJSON strings (as bytes, matching
    the real `requests` library's own default) - one JSON object per
    Ollama streaming convention line."""
    response = MagicMock()
    response.status_code = status_code
    response.iter_lines.return_value = [line.encode("utf-8") for line in lines]
    return response


class ModelProviderConfigTests(unittest.TestCase):

    def test_defaults_when_env_unset(self):
        with patch.dict(
            "os.environ",
            {},
            clear=True,
        ):
            config = ModelProviderConfig.from_env()

        self.assertEqual(config.base_url, "http://localhost:11434")
        self.assertEqual(config.model, "qwen3:14b")

    def test_reads_overrides_from_env(self):
        with patch.dict(
            "os.environ",
            {
                "OLLAMA_BASE_URL": "http://remote-host:11434",
                "OLLAMA_MODEL": "llama3:8b",
                "OLLAMA_TIMEOUT_SECONDS": "12",
            },
            clear=True,
        ):
            config = ModelProviderConfig.from_env()

        self.assertEqual(config.base_url, "http://remote-host:11434")
        self.assertEqual(config.model, "llama3:8b")
        self.assertEqual(config.timeout_seconds, 12.0)

    def test_context_tokens_default_when_env_unset(self):
        # M32: With no role config and no OLLAMA_NUM_CTX, a provider built
        # for a model whose real window is known/discoverable uses that window (40960 for qwen3:14b),
        # not the legacy stale 8192.
        with patch.dict("os.environ", {}, clear=True):
            config = ModelProviderConfig.from_env()

        self.assertEqual(config.context_tokens, 40960)

    def test_context_tokens_fallback_when_model_unknown(self):
        # M32: When provider metadata is unavailable (unknown model, no probe),
        # safely falls back to conservative DEFAULT_CONTEXT_TOKENS (8192).
        with patch.dict("os.environ", {"OLLAMA_MODEL": "unknown-model-xyz"}, clear=True):
            with patch("uri_core.core.model_providers.ollama_provider.probe_model_max_context", return_value=None):
                config = ModelProviderConfig.from_env()

        self.assertEqual(config.context_tokens, 8192)

    def test_context_tokens_reads_override_from_env(self):
        with patch.dict(
            "os.environ",
            {"OLLAMA_NUM_CTX": "16384"},
            clear=True,
        ):
            config = ModelProviderConfig.from_env()

        self.assertEqual(config.context_tokens, 16384)

    def test_from_env_skips_probe_when_num_ctx_set(self):
        """M32 D4: OLLAMA_NUM_CTX already defines the context size, so the
        live /api/tags probe (probe_model_max_context) must never be
        called at all - not merely overridden after the fact."""
        with patch.dict("os.environ", {"OLLAMA_NUM_CTX": "16384"}, clear=True):
            with patch(
                "uri_core.core.model_providers.ollama_provider.probe_model_max_context"
            ) as probe:
                config = ModelProviderConfig.from_env()

        probe.assert_not_called()
        self.assertEqual(config.context_tokens, 16384)

    def test_from_env_does_probe_when_num_ctx_unset(self):
        """Control: with no OLLAMA_NUM_CTX, discovery must still run -
        proves the skip above is conditional on the env var, not a
        blanket disablement of probing."""
        with patch.dict("os.environ", {}, clear=True):
            with patch(
                "uri_core.core.model_providers.ollama_provider.probe_model_max_context",
                return_value=None,
            ) as probe:
                ModelProviderConfig.from_env()

        probe.assert_called()


class BuildProviderContextProbeSkipTests(unittest.TestCase):
    """M32 D4: build_provider("ollama") must not hit the live /api/tags
    probe when OLLAMA_NUM_CTX already defines the context window - the
    exact case this batch targets."""

    def test_build_provider_skips_probe_when_num_ctx_set(self):
        from uri_core.config.model_roles import ROLE_REASONING, build_provider

        with patch.dict("os.environ", {"OLLAMA_NUM_CTX": "16384"}, clear=True):
            with patch(
                "uri_core.core.model_providers.ollama_provider.probe_model_max_context"
            ) as probe:
                provider = build_provider(ROLE_REASONING)

        probe.assert_not_called()
        self.assertEqual(provider.config.context_tokens, 16384)

    def test_resolve_model_context_tokens_skips_probe_when_num_ctx_set(self):
        """The direct-call path response_drafting.py / model_reasoning_
        adapter.py use (resolve_model_context_tokens(model=...)) must
        also skip the probe - it checks OLLAMA_NUM_CTX itself, first."""
        from uri_core.core.model_providers.ollama_provider import resolve_model_context_tokens

        with patch.dict("os.environ", {"OLLAMA_NUM_CTX": "16384"}, clear=True):
            with patch(
                "uri_core.core.model_providers.ollama_provider.probe_model_max_context"
            ) as probe:
                tokens = resolve_model_context_tokens(model="qwen3:14b")

        probe.assert_not_called()
        self.assertEqual(tokens, 16384)


class OllamaProviderMockedTests(unittest.TestCase):
    """No real network access - Ollama's HTTP layer is faked so these
    exercise OllamaProvider's own request-building and error-mapping
    logic in isolation. The real (unmocked) integration test lives in
    test_ollama_provider_live.py."""

    def test_successful_completion_returns_content(self):
        provider = OllamaProvider(config=_config())

        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.post",
            return_value=_fake_ok_response('{"a": 1}'),
        ) as mock_post:
            result = provider.complete(system="sys", user="hello")

        self.assertIsInstance(result, ModelResponse)
        self.assertEqual(result.content, '{"a": 1}')
        self.assertEqual(result.provider, "ollama")

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["model"], "qwen3:14b")
        self.assertEqual(kwargs["json"]["stream"], False)
        self.assertEqual(kwargs["json"]["think"], False)
        self.assertEqual(
            kwargs["json"]["messages"],
            [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "hello"},
            ],
        )

    def test_timeout_raises_provider_timeout_error(self):
        provider = OllamaProvider(config=_config())

        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.post",
            side_effect=requests.exceptions.Timeout(),
        ):
            with self.assertRaises(ProviderTimeoutError):
                provider.complete(system="sys", user="hello")

    def test_connection_error_raises_provider_unavailable_error(self):
        provider = OllamaProvider(config=_config())

        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.post",
            side_effect=requests.exceptions.ConnectionError(),
        ):
            with self.assertRaises(ProviderUnavailableError):
                provider.complete(system="sys", user="hello")

    def test_404_raises_model_not_found_error(self):
        provider = OllamaProvider(config=_config())

        response = MagicMock()
        response.status_code = 404
        response.text = '{"error":"model \'qwen3:14b\' not found"}'

        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.post",
            return_value=response,
        ):
            with self.assertRaises(ModelNotFoundError):
                provider.complete(system="sys", user="hello")

    def test_non_200_non_404_raises_provider_response_error(self):
        provider = OllamaProvider(config=_config())

        response = MagicMock()
        response.status_code = 500
        response.text = "internal error"

        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.post",
            return_value=response,
        ):
            with self.assertRaises(ProviderResponseError):
                provider.complete(system="sys", user="hello")

    def test_malformed_json_body_raises_provider_response_error(self):
        provider = OllamaProvider(config=_config())

        response = MagicMock()
        response.status_code = 200
        response.json.side_effect = ValueError("not json")

        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.post",
            return_value=response,
        ):
            with self.assertRaises(ProviderResponseError):
                provider.complete(system="sys", user="hello")

    def test_missing_message_content_raises_provider_response_error(self):
        provider = OllamaProvider(config=_config())

        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"model": "qwen3:14b"}

        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.post",
            return_value=response,
        ):
            with self.assertRaises(ProviderResponseError):
                provider.complete(system="sys", user="hello")

    def test_sends_configured_num_ctx(self):
        # M21: the actual fix for the audit's core finding - every real
        # completion must send options.num_ctx, since Ollama otherwise
        # silently loads the model at its own 4096-token default regardless
        # of prompt size.
        provider = OllamaProvider(
            config=ModelProviderConfig(
                base_url="http://localhost:11434",
                model="qwen3:14b",
                timeout_seconds=5.0,
                context_tokens=16384,
            )
        )

        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.post",
            return_value=_fake_ok_response("{}"),
        ) as mock_post:
            provider.complete(system="sys", user="hello")

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["options"]["num_ctx"], 16384)

    def test_response_carries_prompt_and_eval_token_counts(self):
        provider = OllamaProvider(config=_config())

        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "model": "qwen3:14b",
            "message": {"role": "assistant", "content": "hi"},
            "prompt_eval_count": 123,
            "eval_count": 45,
        }

        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.post",
            return_value=response,
        ):
            result = provider.complete(system="sys", user="hello")

        self.assertEqual(result.prompt_tokens, 123)
        self.assertEqual(result.eval_tokens, 45)
        self.assertIsInstance(result.duration_seconds, float)
        self.assertGreaterEqual(result.duration_seconds, 0.0)

    def test_response_without_token_counts_degrades_to_none(self):
        # An older/different backend that doesn't report these fields must
        # never be mistaken for one reporting zero tokens.
        provider = OllamaProvider(config=_config())

        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.post",
            return_value=_fake_ok_response("{}"),
        ):
            result = provider.complete(system="sys", user="hello")

        self.assertIsNone(result.prompt_tokens)
        self.assertIsNone(result.eval_tokens)

    def test_oversized_prompt_estimate_raises_context_window_exceeded(self):
        provider = OllamaProvider(
            config=ModelProviderConfig(
                base_url="http://localhost:11434",
                model="qwen3:14b",
                timeout_seconds=5.0,
                context_tokens=10,
            )
        )

        with self.assertRaises(ContextWindowExceededError) as ctx:
            provider.complete(system="a" * 200, user="hello")

        self.assertIn("exceeds configured context window", str(ctx.exception))
        self.assertEqual(ctx.exception.context_tokens, 10)


class OllamaProviderDescribeTests(unittest.TestCase):
    """describe() must be cheap, timeout-bounded, and exception-safe -
    never a real completion, never raising, always returning a
    ModelProviderStatus even when Ollama is unreachable."""

    def test_reachable_ollama_reports_available(self):
        provider = OllamaProvider(config=_config())

        response = MagicMock()
        response.status_code = 200

        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.get",
            return_value=response,
        ) as mock_get:
            status = provider.describe()

        self.assertIsInstance(status, ModelProviderStatus)
        self.assertTrue(status.available)
        self.assertIsNone(status.detail)
        self.assertEqual(status.provider_name, "ollama")
        self.assertEqual(status.model_name, "qwen3:14b")
        self.assertEqual(status.location, "local")
        # M21: context_window now reports the actual configured num_ctx
        # every complete() call sends (see ModelProviderConfig.context_tokens)
        # instead of always being None - a mocked /api/tags body carries no
        # real model details, so no model-max warning is appended to detail.
        self.assertEqual(status.context_window, 8192)
        self.assertEqual(status.supports, ("text",))

        _, kwargs = mock_get.call_args
        self.assertLessEqual(
            kwargs["timeout"], DEFAULT_HEALTH_CHECK_TIMEOUT_SECONDS
        )

    def test_never_calls_complete_endpoint(self):
        provider = OllamaProvider(config=_config())

        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.post"
        ) as mock_post, patch(
            "uri_core.core.model_providers.ollama_provider.requests.get",
            return_value=MagicMock(status_code=200),
        ):
            provider.describe()

        mock_post.assert_not_called()

    def test_connection_error_reports_unavailable_not_raised(self):
        provider = OllamaProvider(config=_config())

        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.get",
            side_effect=requests.exceptions.ConnectionError(),
        ):
            status = provider.describe()

        self.assertFalse(status.available)
        self.assertIsNotNone(status.detail)

    def test_timeout_reports_unavailable_not_raised(self):
        provider = OllamaProvider(config=_config())

        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.get",
            side_effect=requests.exceptions.Timeout(),
        ):
            status = provider.describe()

        self.assertFalse(status.available)
        self.assertIsNotNone(status.detail)

    def test_non_200_reports_unavailable_not_raised(self):
        provider = OllamaProvider(config=_config())

        response = MagicMock()
        response.status_code = 500

        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.get",
            return_value=response,
        ):
            status = provider.describe()

        self.assertFalse(status.available)
        self.assertIsNotNone(status.detail)

    def test_health_check_timeout_is_bounded_even_with_a_slow_config(self):
        provider = OllamaProvider(
            config=ModelProviderConfig(
                base_url="http://localhost:11434",
                model="qwen3:14b",
                timeout_seconds=60.0,
            )
        )

        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.get",
            return_value=MagicMock(status_code=200),
        ) as mock_get:
            provider.describe()

        _, kwargs = mock_get.call_args
        self.assertLessEqual(
            kwargs["timeout"], DEFAULT_HEALTH_CHECK_TIMEOUT_SECONDS
        )

    def test_external_base_url_reports_external_location(self):
        provider = OllamaProvider(
            config=ModelProviderConfig(
                base_url="http://remote-host:11434",
                model="qwen3:14b",
                timeout_seconds=5.0,
            )
        )

        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.get",
            return_value=MagicMock(status_code=200),
        ):
            status = provider.describe()

        self.assertEqual(status.location, "external")

    def test_context_window_reports_configured_value(self):
        provider = OllamaProvider(
            config=ModelProviderConfig(
                base_url="http://localhost:11434",
                model="qwen3:14b",
                timeout_seconds=5.0,
                context_tokens=16384,
            )
        )

        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.get",
            return_value=MagicMock(status_code=200),
        ):
            status = provider.describe()

        self.assertEqual(status.context_window, 16384)

    def test_model_max_context_parsed_from_tags_body_free_of_extra_call(self):
        # M21: the model's own maximum supported context is available in
        # the SAME /api/tags body describe() already fetches for
        # availability - no /api/show call is made.
        provider = OllamaProvider(
            config=ModelProviderConfig(
                base_url="http://localhost:11434",
                model="qwen3:14b",
                timeout_seconds=5.0,
                context_tokens=100000,
            )
        )

        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "models": [
                {
                    "name": "qwen3:14b",
                    "details": {"context_length": 40960},
                }
            ]
        }

        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.get",
            return_value=response,
        ) as mock_get:
            status = provider.describe()

        mock_get.assert_called_once()
        self.assertEqual(status.context_window, 100000)
        self.assertIn("exceeds this model's maximum", status.detail)
        self.assertIn("40960", status.detail)

    def test_model_max_context_within_configured_window_reports_no_warning(self):
        provider = OllamaProvider(
            config=ModelProviderConfig(
                base_url="http://localhost:11434",
                model="qwen3:14b",
                timeout_seconds=5.0,
                context_tokens=8192,
            )
        )

        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "models": [
                {"name": "qwen3:14b", "details": {"context_length": 40960}}
            ]
        }

        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.get",
            return_value=response,
        ):
            status = provider.describe()

        self.assertIsNone(status.detail)


class OllamaProviderCompleteStreamTests(unittest.TestCase):
    """M32 D5: OllamaProvider.complete_stream() - no real network access
    (mocked NDJSON lines, mirroring OllamaProviderMockedTests' own
    convention). Real, live-Ollama evidence for this same method is
    reported separately (M32_POST_BATCH_C_LATENCY_ARCHITECTURE_PLAN.md
    §14) rather than duplicated as an offline test."""

    def test_content_only_stream_yields_deltas_and_final_response(self):
        provider = OllamaProvider(config=_config())
        lines = [
            '{"model":"qwen3:14b","message":{"role":"assistant","content":"Hel"},"done":false}',
            '{"model":"qwen3:14b","message":{"role":"assistant","content":"lo"},"done":false}',
            '{"model":"qwen3:14b","message":{"role":"assistant","content":""},"done":true,'
            '"prompt_eval_count":5,"eval_count":2}',
        ]
        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.post",
            return_value=_fake_stream_response(lines),
        ) as mock_post:
            chunks = list(provider.complete_stream(system="sys", user="hello"))

        self.assertEqual([c.content for c in chunks], ["Hel", "lo", ""])
        self.assertFalse(any(c.is_tool_call for c in chunks))
        self.assertTrue(chunks[-1].done)
        self.assertEqual(chunks[-1].final_response.content, "Hello")
        self.assertEqual(chunks[-1].final_response.prompt_tokens, 5)
        self.assertEqual(chunks[-1].final_response.eval_tokens, 2)
        self.assertIsNone(chunks[-1].final_response.tool_calls)

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["stream"], True)
        self.assertTrue(kwargs.get("stream"))

    def test_ttft_measured_on_first_content_chunk_only(self):
        provider = OllamaProvider(config=_config())
        lines = [
            '{"model":"m","message":{"role":"assistant","content":"A"},"done":false}',
            '{"model":"m","message":{"role":"assistant","content":"B"},"done":false}',
            '{"model":"m","message":{"role":"assistant","content":""},"done":true}',
        ]
        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.post",
            return_value=_fake_stream_response(lines),
        ):
            chunks = list(provider.complete_stream(system="sys", user="hello"))

        self.assertIsNotNone(chunks[-1].ttft_seconds)
        self.assertGreaterEqual(chunks[-1].final_response.duration_seconds, chunks[-1].ttft_seconds)

    def test_tool_call_stream_yields_zero_content_and_parses_final_tool_calls(self):
        provider = OllamaProvider(config=_config())
        lines = [
            '{"model":"m","message":{"role":"assistant","content":"",'
            '"tool_calls":[{"id":"call_1","function":{"name":"get_weather",'
            '"arguments":{"city":"Paris"}}}]},"done":false}',
            '{"model":"m","message":{"role":"assistant","content":""},"done":true}',
        ]
        tools = [{"type": "function", "function": {"name": "get_weather", "parameters": {}}}]
        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.post",
            return_value=_fake_stream_response(lines),
        ):
            chunks = list(provider.complete_stream(system="sys", user="hi", tools=tools))

        self.assertTrue(all(c.content == "" for c in chunks))
        self.assertTrue(chunks[0].is_tool_call)
        final = chunks[-1].final_response
        self.assertEqual(final.content, "")
        self.assertEqual(len(final.tool_calls), 1)
        self.assertEqual(final.tool_calls[0].name, "get_weather")
        self.assertEqual(final.tool_calls[0].arguments, {"city": "Paris"})

    def test_404_raises_model_not_found_error(self):
        provider = OllamaProvider(config=_config())
        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.post",
            return_value=_fake_stream_response([], status_code=404),
        ):
            with self.assertRaises(ModelNotFoundError):
                list(provider.complete_stream(system="sys", user="hello"))

    def test_timeout_raises_provider_timeout_error(self):
        provider = OllamaProvider(config=_config())
        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.post",
            side_effect=requests.exceptions.Timeout(),
        ):
            with self.assertRaises(ProviderTimeoutError):
                list(provider.complete_stream(system="sys", user="hello"))

    def test_connection_error_raises_provider_unavailable_error(self):
        provider = OllamaProvider(config=_config())
        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.post",
            side_effect=requests.exceptions.ConnectionError(),
        ):
            with self.assertRaises(ProviderUnavailableError):
                list(provider.complete_stream(system="sys", user="hello"))

    def test_malformed_json_line_raises_provider_response_error(self):
        provider = OllamaProvider(config=_config())
        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.post",
            return_value=_fake_stream_response(["not valid json"]),
        ):
            with self.assertRaises(ProviderResponseError):
                list(provider.complete_stream(system="sys", user="hello"))

    def test_context_window_exceeded_raised_before_any_request(self):
        provider = OllamaProvider(config=ModelProviderConfig(
            base_url="http://localhost:11434", model="qwen3:14b",
            timeout_seconds=5.0, context_tokens=10,
        ))
        with patch("uri_core.core.model_providers.ollama_provider.requests.post") as mock_post:
            with self.assertRaises(ContextWindowExceededError):
                list(provider.complete_stream(
                    system="a long system prompt that exceeds the tiny window",
                    user="and more user text on top of it",
                ))
        mock_post.assert_not_called()

    def test_response_is_closed_after_stream_completes(self):
        provider = OllamaProvider(config=_config())
        response = _fake_stream_response([
            '{"model":"m","message":{"role":"assistant","content":"ok"},"done":true}',
        ])
        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.post",
            return_value=response,
        ):
            list(provider.complete_stream(system="sys", user="hello"))

        response.close.assert_called_once()

    def test_response_is_closed_even_on_404(self):
        provider = OllamaProvider(config=_config())
        response = _fake_stream_response([], status_code=404)
        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.post",
            return_value=response,
        ):
            with self.assertRaises(ModelNotFoundError):
                list(provider.complete_stream(system="sys", user="hello"))

        response.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
