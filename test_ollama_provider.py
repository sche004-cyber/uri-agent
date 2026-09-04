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
        self.assertIsNone(status.context_window)
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


if __name__ == "__main__":
    unittest.main()
