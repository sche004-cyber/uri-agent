"""Native Anthropic Messages API provider.

Anthropic's API is not OpenAI-compatible: it uses ``/v1/messages``, an
``x-api-key`` header, and an explicit API-version header.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import requests

from .base import (
    DEFAULT_HEALTH_CHECK_TIMEOUT_SECONDS,
    ModelProvider,
    ModelProviderConfig,
    ModelProviderStatus,
    ModelResponse,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ToolCall,
    _location_from_base_url,
)


def _to_anthropic_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """M32 C1.5: normalise the caller's OpenAI-compatible tool definitions
    ({"type": "function", "function": {"name", "description", "parameters"}})
    into Anthropic's own native shape ({"name", "description", "input_schema"}) -
    the adapter boundary the plan calls for, so only ModelResponse.tool_calls
    is ever seen upstream of any provider."""
    converted = []
    for tool in tools:
        function = tool.get("function", tool) if isinstance(tool, dict) else {}
        converted.append(
            {
                "name": function.get("name"),
                "description": function.get("description", ""),
                "input_schema": function.get("parameters", {"type": "object", "properties": {}}),
            }
        )
    return converted


class AnthropicProvider(ModelProvider):
    """ModelProvider backed by Anthropic's native Messages API."""

    def __init__(
        self,
        config: Optional[ModelProviderConfig] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self._config = config or ModelProviderConfig()
        self._api_key = api_key

    def complete(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ModelResponse:
        model_id = self._config.model
        if model_id == "claude-3-5-sonnet":
            model_id = "claude-3-5-sonnet-20241022"
        payload: dict = {
            "model": model_id,
            "max_tokens": max_tokens if max_tokens is not None else 1024,
            "messages": [{"role": "user", "content": user}],
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = _to_anthropic_tools(tools)
        headers = {
            "x-api-key": self._api_key or "",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        start = time.monotonic()
        try:
            response = requests.post(
                f"{self._config.base_url.rstrip('/')}/v1/messages",
                json=payload,
                headers=headers,
                timeout=self._config.timeout_seconds,
            )
        except requests.exceptions.Timeout as exc:
            raise ProviderTimeoutError("Anthropic request timed out.") from exc
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as exc:
            raise ProviderUnavailableError("Could not reach Anthropic.") from exc

        if response.status_code in (401, 403):
            raise ProviderAuthenticationError(
                f"Anthropic rejected credentials (HTTP {response.status_code})."
            )
        if response.status_code == 429:
            raise ProviderRateLimitError("Anthropic rate limit exceeded.")
        if response.status_code >= 500:
            raise ProviderUnavailableError(
                f"Anthropic is unavailable (HTTP {response.status_code})."
            )
        if response.status_code != 200:
            raise ProviderResponseError(
                f"Anthropic returned unexpected status {response.status_code}."
            )
        try:
            data = response.json()
            blocks = data["content"]
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderResponseError("Anthropic response did not contain content.") from exc
        if not isinstance(blocks, list):
            raise ProviderResponseError("Anthropic response content was not a list of blocks.")

        # M32 C1: a tool-calling response may carry ONLY tool_use blocks,
        # no text block at all - the previous content[0]["text"] access
        # assumed the first block was always text, which a tool-only reply
        # would violate. Text blocks are concatenated (Anthropic can emit
        # more than one); tool_use blocks become ToolCall entries.
        text_parts = []
        tool_calls_list = []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            block_type = block.get("type")
            if block_type == "text" and isinstance(block.get("text"), str):
                text_parts.append(block["text"])
            elif block_type == "tool_use":
                name = block.get("name")
                if isinstance(name, str) and name:
                    tool_input = block.get("input")
                    tool_calls_list.append(
                        ToolCall(
                            id=str(block.get("id") or f"anthropic-{len(tool_calls_list)}"),
                            name=name,
                            arguments=tool_input if isinstance(tool_input, dict) else {},
                        )
                    )
        content = "".join(text_parts)
        usage = data.get("usage") or {}
        prompt_tokens = usage.get("input_tokens")
        eval_tokens = usage.get("output_tokens")
        return ModelResponse(
            content=content,
            model=data.get("model", self._config.model),
            provider="anthropic",
            prompt_tokens=prompt_tokens if isinstance(prompt_tokens, int) else None,
            eval_tokens=eval_tokens if isinstance(eval_tokens, int) else None,
            duration_seconds=time.monotonic() - start,
            tool_calls=tuple(tool_calls_list) if tools else None,
        )

    def describe(self) -> ModelProviderStatus:
        """Return a short, exception-safe reachability probe without a completion."""
        available = False
        detail: Optional[str] = None
        try:
            response = requests.get(
                f"{self._config.base_url.rstrip('/')}/v1/models",
                headers={
                    "x-api-key": self._api_key or "",
                    "anthropic-version": "2023-06-01",
                },
                timeout=min(self._config.timeout_seconds, DEFAULT_HEALTH_CHECK_TIMEOUT_SECONDS),
            )
            available = response.status_code < 500
            if response.status_code in (401, 403):
                detail = "credential rejected"
            elif not available:
                detail = f"HTTP {response.status_code}"
        except requests.exceptions.Timeout:
            detail = "health check timed out"
        except requests.exceptions.ConnectionError:
            detail = "connection refused"
        except Exception:  # noqa: BLE001 - describe must never raise
            detail = "health check failed"
        return ModelProviderStatus(
            provider_name="anthropic",
            model_name=self._config.model,
            location=_location_from_base_url(self._config.base_url),
            context_window=None,
            supports=("text",),
            available=available,
            detail=detail,
        )
