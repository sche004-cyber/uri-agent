"""ModelProvider backed by a local or remote Ollama server's HTTP API.

Talks to Ollama's /api/chat endpoint directly - no shelling out to the
`ollama` executable. All connection details come from ModelProviderConfig
so nothing here is hardcoded beyond that config's own defaults.
"""

from typing import Optional

import requests

from .base import (
    DEFAULT_HEALTH_CHECK_TIMEOUT_SECONDS,
    ModelNotFoundError,
    ModelProvider,
    ModelProviderConfig,
    ModelProviderStatus,
    ModelResponse,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    _location_from_base_url,
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

    def describe(self) -> ModelProviderStatus:
        """A lightweight GET against Ollama's /api/tags - never a real
        completion (see ModelProvider.describe's contract) - bounded to
        DEFAULT_HEALTH_CHECK_TIMEOUT_SECONDS regardless of how long
        config.timeout_seconds allows a real completion to take, so a
        self-knowledge query never hangs waiting on the slower budget a
        real request is allowed. context_window is always None: Ollama
        does not expose this from /api/tags, and querying /api/show for
        it would be a second network call this milestone's "keep it
        cheap" requirement argues against making by default - left as
        a documented future enhancement, not a guess."""

        health_check_timeout = min(
            self.config.timeout_seconds,
            DEFAULT_HEALTH_CHECK_TIMEOUT_SECONDS,
        )

        available = False
        detail = None

        try:
            response = requests.get(
                f"{self.config.base_url.rstrip('/')}/api/tags",
                timeout=health_check_timeout,
            )

            if response.status_code == 200:
                available = True
            else:
                detail = (
                    f"Ollama returned HTTP {response.status_code} at "
                    f"{self.config.base_url}."
                )

        except requests.exceptions.Timeout:
            detail = (
                "Ollama did not respond within "
                f"{health_check_timeout}s at {self.config.base_url}."
            )

        except requests.exceptions.ConnectionError:
            detail = (
                f"Could not reach Ollama at {self.config.base_url}. "
                "Is it running?"
            )

        except requests.exceptions.RequestException as exc:
            detail = f"Request to Ollama failed: {exc}"

        return ModelProviderStatus(
            provider_name="ollama",
            model_name=self.config.model,
            location=_location_from_base_url(self.config.base_url),
            context_window=None,
            supports=("text",),
            available=available,
            detail=detail,
        )
