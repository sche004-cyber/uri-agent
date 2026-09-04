"""ModelProvider backed by a local or remote Ollama server's HTTP API.

Talks to Ollama's /api/chat endpoint directly - no shelling out to the
`ollama` executable. All connection details come from ModelProviderConfig
so nothing here is hardcoded beyond that config's own defaults.
"""

from typing import Optional

import requests

from .base import (
    ModelNotFoundError,
    ModelProvider,
    ModelProviderConfig,
    ModelResponse,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)


class OllamaProvider(ModelProvider):
    def __init__(self, config: Optional[ModelProviderConfig] = None):
        self.config = config or ModelProviderConfig.from_env()

    def complete(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> ModelResponse:

        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            # Thinking-capable models (e.g. qwen3) generate a chain-of-
            # thought trace *before* the visible content, and that trace
            # is counted against max_tokens/num_predict - so a token
            # budget sized for the answer alone can truncate the answer
            # itself before it's written. URI's current callers all want
            # a short, deterministic, structured completion, not a
            # visible reasoning trace, so thinking is switched off here.
            # Ollama ignores this field for models that don't support it.
            "think": False,
            "options": {"temperature": temperature},
        }

        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens

        url = f"{self.config.base_url.rstrip('/')}/api/chat"

        try:
            response = requests.post(
                url,
                json=payload,
                timeout=self.config.timeout_seconds,
            )
        except requests.exceptions.Timeout as exc:
            raise ProviderTimeoutError(
                f"Ollama did not respond within {self.config.timeout_seconds}s."
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise ProviderUnavailableError(
                f"Could not reach Ollama at {self.config.base_url}. "
                "Is it running?"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise ProviderUnavailableError(
                f"Request to Ollama failed: {exc}"
            ) from exc

        if response.status_code == 404:
            raise ModelNotFoundError(
                f"Model '{self.config.model}' was not found on this Ollama "
                f"server ({self.config.base_url}). Pull it first."
            )

        if response.status_code != 200:
            raise ProviderResponseError(
                f"Ollama returned HTTP {response.status_code}: "
                f"{response.text[:200]}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderResponseError(
                "Ollama returned a response that was not valid JSON."
            ) from exc

        message = data.get("message")

        if not isinstance(message, dict) or not isinstance(
            message.get("content"), str
        ):
            raise ProviderResponseError(
                "Ollama response did not contain message.content."
            )

        return ModelResponse(
            content=message["content"],
            model=data.get("model", self.config.model),
            provider="ollama",
        )
