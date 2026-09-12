"""ModelProvider backed by a local or remote Ollama server's HTTP API.

Talks to Ollama's /api/chat endpoint directly - no shelling out to the
`ollama` executable. All connection details come from ModelProviderConfig
so nothing here is hardcoded beyond that config's own defaults.
"""

import logging
import time
from typing import Optional

import requests

from uri_core.core.context_budget import estimate_tokens

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

# M21: plain numeric instrumentation only (prompt/eval token counts,
# duration, configured window) - never raw prompt/response content, matching
# ModelResponse's own "no raw backend payload" discipline. This is what lets
# a real truncation (prompt_eval_count far below the true prompt size) show
# up in ordinary logs instead of silently degrading the model's answer with
# no visible signal anywhere - see the M21 audit's core finding.
_LOG = logging.getLogger(__name__)


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
            # 2026-09-12 (User directive): without this, Ollama evicts an
            # idle model from memory on its own short default timeout,
            # so the next turn pays a real 10-20s reload cost before any
            # inference even starts. URI issues several sequential calls
            # per turn (semantic analysis, reasoning, drafting) and turns
            # are rarely more than a few minutes apart in a live
            # conversation, so keeping the model resident for 60 minutes
            # of idle time removes that reload cost from every turn but
            # the very first of a session.
            "keep_alive": "60m",
            # Thinking-capable models (e.g. qwen3) generate a chain-of-
            # thought trace *before* the visible content, and that trace
            # is counted against max_tokens/num_predict - so a token
            # budget sized for the answer alone can truncate the answer
            # itself before it's written. URI's current callers all want
            # a short, deterministic, structured completion, not a
            # visible reasoning trace, so thinking is switched off here.
            # Ollama ignores this field for models that don't support it.
            "think": False,
            "options": {
                "temperature": temperature,
                # M21: previously unset, which left Ollama loading the
                # model at its own hardcoded 4096-token default regardless
                # of how large a prompt this call actually sent - measured
                # during the M21 audit to silently discard the majority of
                # every real Brain prompt (a 4935-token reasoning request
                # was evaluated as 2050 tokens, destroying the leading
                # system_policy/contract text first). Always explicit now.
                "num_ctx": self.config.context_tokens,
            },
        }

        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens

        estimated_prompt_tokens = estimate_tokens(system) + estimate_tokens(user)

        if estimated_prompt_tokens > self.config.context_tokens:
            _LOG.warning(
                "Prompt to %s/%s is ~%d tokens (rough estimate), exceeding "
                "the configured context_tokens (%d). Ollama will silently "
                "drop the earliest content (typically the system prompt) "
                "to fit - the model may not see the full request.",
                self.config.base_url,
                self.config.model,
                estimated_prompt_tokens,
                self.config.context_tokens,
            )

        url = f"{self.config.base_url.rstrip('/')}/api/chat"

        start = time.monotonic()

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

        duration_seconds = time.monotonic() - start
        prompt_tokens = data.get("prompt_eval_count")
        eval_tokens = data.get("eval_count")

        if isinstance(prompt_tokens, int):
            _LOG.info(
                "Ollama completion: model=%s prompt_tokens=%d eval_tokens=%s "
                "duration=%.2fs num_ctx=%d",
                self.config.model,
                prompt_tokens,
                eval_tokens,
                duration_seconds,
                self.config.context_tokens,
            )
            if prompt_tokens < estimated_prompt_tokens * 0.7:
                _LOG.warning(
                    "Ollama reported prompt_tokens=%d for a prompt "
                    "estimated at ~%d tokens - the request may have been "
                    "truncated to fit context_tokens=%d.",
                    prompt_tokens,
                    estimated_prompt_tokens,
                    self.config.context_tokens,
                )

        return ModelResponse(
            content=message["content"],
            model=data.get("model", self.config.model),
            provider="ollama",
            prompt_tokens=prompt_tokens if isinstance(prompt_tokens, int) else None,
            eval_tokens=eval_tokens if isinstance(eval_tokens, int) else None,
            duration_seconds=duration_seconds,
        )

    def _model_max_context(self, response) -> Optional[int]:
        """M21: the model's own trained/supported context length, parsed
        from the SAME /api/tags body describe() already fetches for
        availability - genuinely free, contrary to this method's previous
        claim that getting this number would cost a second network call.
        Real Ollama's /api/tags response nests it at
        models[].details.context_length; verified against a live server
        during the M21 audit. Returns None on any shape mismatch (a fake/
        mocked response in a test, a future Ollama version that moves the
        field) rather than guessing - never raises."""

        try:
            body = response.json()
        except Exception:
            return None

        if not isinstance(body, dict):
            return None

        for entry in body.get("models", []):
            if not isinstance(entry, dict) or entry.get("name") != self.config.model:
                continue
            details = entry.get("details")
            if isinstance(details, dict):
                value = details.get("context_length")
                if isinstance(value, int):
                    return value

        return None

    def describe(self) -> ModelProviderStatus:
        """A lightweight GET against Ollama's /api/tags - never a real
        completion (see ModelProvider.describe's contract) - bounded to
        DEFAULT_HEALTH_CHECK_TIMEOUT_SECONDS regardless of how long
        config.timeout_seconds allows a real completion to take, so a
        self-knowledge query never hangs waiting on the slower budget a
        real request is allowed.

        M21: context_window now reports the actual configured num_ctx
        (self.config.context_tokens) that every real complete() call sends
        - previously always None, which is what let a real 4096-token
        runtime default go unnoticed and undocumented for as long as it
        did (see the M21 audit). When the same /api/tags body also reports
        this model's own maximum context (see _model_max_context - free,
        no second network call, correcting this method's previous claim
        that it would cost one), a configured value larger than that
        maximum is surfaced honestly in `detail` rather than silently
        accepted."""

        health_check_timeout = min(
            self.config.timeout_seconds,
            DEFAULT_HEALTH_CHECK_TIMEOUT_SECONDS,
        )

        available = False
        detail = None
        model_max_context = None

        try:
            response = requests.get(
                f"{self.config.base_url.rstrip('/')}/api/tags",
                timeout=health_check_timeout,
            )

            if response.status_code == 200:
                available = True
                model_max_context = self._model_max_context(response)
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

        if (
            model_max_context is not None
            and self.config.context_tokens > model_max_context
        ):
            warning = (
                f"configured context_tokens ({self.config.context_tokens}) "
                f"exceeds this model's maximum supported context "
                f"({model_max_context})."
            )
            detail = f"{detail} {warning}" if detail else warning

        return ModelProviderStatus(
            provider_name="ollama",
            model_name=self.config.model,
            location=_location_from_base_url(self.config.base_url),
            context_window=self.config.context_tokens,
            supports=("text",),
            available=available,
            detail=detail,
        )
