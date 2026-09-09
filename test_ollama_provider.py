import unittest
from unittest.mock import MagicMock, patch

import requests

from uri_core.core.model_providers.base import (
    DEFAULT_HEALTH_CHECK_TIMEOUT_SECONDS,
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
        with patch.dict("os.environ", {}, clear=True):
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

    def test_oversized_prompt_estimate_logs_a_warning(self):
        provider = OllamaProvider(
            config=ModelProviderConfig(
                base_url="http://localhost:11434",
                model="qwen3:14b",
                timeout_seconds=5.0,
                context_tokens=10,
            )
        )

        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.post",
            return_value=_fake_ok_response("{}"),
        ), self.assertLogs(
            "uri_core.core.model_providers.ollama_provider", level="WARNING"
        ) as logs:
            provider.complete(system="a" * 200, user="hello")

        self.assertTrue(
            any("exceeding" in message for message in logs.output)
        )


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


if __name__ == "__main__":
    unittest.main()
