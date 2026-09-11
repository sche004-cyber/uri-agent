"""OpenAI-compatible ModelProvider for any /chat/completions HTTP backend.

Covers: OpenAI, OpenRouter, Groq, LM Studio, llama.cpp, and any other
server that speaks the standard OpenAI chat-completions wire format.

Security contract:
- The api_key is passed in as a constructor argument; it is never read
  from environment variables or config files inside this module.  The
  one permitted caller (config/model_roles.py build_provider) fetches
  the key from ProviderKeyStore immediately before construction.
- A 401/403 response raises ProviderAuthenticationError, not
  ProviderUnavailableError.  This is the signal M22.6 ModelRouter uses
  to enforce auth-failure-stops, never-silently-falls-back.
- No raw key, no request body, no response body are ever logged.
"""

from __future__ import annotations

import time
from typing import Optional

import requests

from .base import (
    DEFAULT_HEALTH_CHECK_TIMEOUT_SECONDS,
    ModelNotFoundError,
    ModelProvider,
    ModelProviderConfig,
    ModelProviderStatus,
    ModelResponse,
    ProviderAuthenticationError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    _location_from_base_url,
)


class OpenAICompatibleProvider(ModelProvider):
    """ModelProvider backed by any /chat/completions-shaped HTTP API.

    Parameters
    ----------
    config:
        Connection parameters (base_url, model, timeout_seconds).
        Never contains a key - that arrives separately via api_key.
    api_key:
        The bearer token for this provider. Not stored beyond this
        object's lifetime; not logged; not returned across API boundaries.
        May be None for providers that run unauthenticated (e.g. LM
        Studio on localhost) - in which case no Authorization header is
        sent.
    """

    def __init__(
        self,
        config: Optional[ModelProviderConfig] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self._config = config or ModelProviderConfig()
        # Never log or expose _api_key.
        self._api_key = api_key

    # ------------------------------------------------------------------
    # ModelProvider interface
    # ------------------------------------------------------------------

    def complete(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> ModelResponse:
        payload: dict = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        url = f"{self._config.base_url.rstrip('/')}/chat/completions"
        start = time.monotonic()

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self._config.timeout_seconds,
            )
        except requests.exceptions.Timeout as exc:
            raise ProviderTimeoutError(
                f"OpenAI-compatible provider at {self._config.base_url} timed out."
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise ProviderUnavailableError(
                f"Could not connect to provider at {self._config.base_url}."
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise ProviderUnavailableError(
                f"Request to provider failed: {type(exc).__name__}"
            ) from exc

        if response.status_code in (401, 403):
            # Auth error - MUST NOT be caught and retried against a
            # different provider or key (M22.5 s5.3, M22.6 boundary).
            raise ProviderAuthenticationError(
                f"Provider at {self._config.base_url} rejected credentials "
                f"(HTTP {response.status_code})."
            )

        if response.status_code == 404:
            raise ModelNotFoundError(
                f"Model '{self._config.model}' not found at {self._config.base_url}."
            )

        if response.status_code != 200:
            raise ProviderResponseError(
                f"Provider returned unexpected status {response.status_code}."
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderResponseError(
                "Provider response was not valid JSON."
            ) from exc

        choices = data.get("choices") or []
        message = choices[0].get("message", {}) if choices else {}
        content = message.get("content", "")

        usage = data.get("usage") or {}
        prompt_tokens = usage.get("prompt_tokens")
        eval_tokens = usage.get("completion_tokens")

        return ModelResponse(
            content=content,
            model=data.get("model", self._config.model),
            provider="openai_compatible",
            prompt_tokens=prompt_tokens if isinstance(prompt_tokens, int) else None,
            eval_tokens=eval_tokens if isinstance(eval_tokens, int) else None,
            duration_seconds=time.monotonic() - start,
        )

    def describe(self) -> ModelProviderStatus:
        """Cheap, timeout-bounded, exception-safe health check.

        Hits /models (a standard OpenAI-compatible listing endpoint) with
        a short timeout. Never raises - an unreachable backend is
        available=False, not an exception.
        """
        available = False
        detail: Optional[str] = None

        headers: dict = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            resp = requests.get(
                f"{self._config.base_url.rstrip('/')}/models",
                headers=headers,
                timeout=DEFAULT_HEALTH_CHECK_TIMEOUT_SECONDS,
            )
            available = resp.status_code == 200
            if resp.status_code in (401, 403):
                detail = "credential rejected"
            elif not available:
                detail = f"HTTP {resp.status_code}"
        except requests.exceptions.Timeout:
            detail = "health check timed out"
        except requests.exceptions.ConnectionError:
            detail = "connection refused"
        except Exception:  # noqa: BLE001 - must never raise
            detail = "health check failed"

        return ModelProviderStatus(
            provider_name="openai_compatible",
            model_name=self._config.model,
            location=_location_from_base_url(self._config.base_url),
            context_window=None,
            supports=("text",),
            available=available,
            detail=detail,
        )
