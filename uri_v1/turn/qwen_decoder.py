"""QwenSemanticDecoder: Concrete Step-1 SemanticDecoder using the local Qwen model (Batch A2.2).

Pipeline:
    DecodeInput -> QwenLocalTransport (LM Studio local server) -> JSON string
        -> parse_wire_json -> normalize_qwen_wire -> DecodedRequest.

Supports both:
  - Constrained mode (schema-constrained JSON via LM Studio response_format)
  - Unconstrained mode (raw JSON completion with prompt instructions)
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from uri_v1.turn.contracts import DecodedRequest
from uri_v1.turn.decoder import DecodeInput, SemanticDecoder
from uri_v1.turn.needle_wire import DecodeError, DecodeErrorReason
from uri_v1.turn.qwen_wire import (
    QWEN_SYSTEM_PROMPT,
    QWEN_WIRE_SCHEMA,
    QWEN_WIRE_SCHEMA_NAME,
    normalize_qwen_wire,
    parse_wire_json,
)

DEFAULT_QWEN_ENDPOINT = "http://127.0.0.1:1234/v1/chat/completions"
DEFAULT_QWEN_MODEL_ID = "qwen-semantic-decoder"


class QwenTransportError(RuntimeError):
    """Raised for network, HTTP, or transport-level errors with the local Qwen runtime."""


class QwenLocalTransport:
    """HTTP client communicating with the local LM Studio OpenAI-compatible endpoint."""

    def __init__(
        self,
        endpoint_url: str = DEFAULT_QWEN_ENDPOINT,
        model_id: str = DEFAULT_QWEN_MODEL_ID,
        timeout: float = 30.0,
    ) -> None:
        self.endpoint_url = endpoint_url
        self.model_id = model_id
        self.timeout = timeout

    def complete(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        constrained: bool = True,
        schema: Optional[Dict[str, Any]] = None,
        schema_name: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.0,
    ) -> Dict[str, Any]:
        """Issues chat completion to the local runtime.

        Returns:
            Dict containing 'content', 'reasoning_content', 'prompt_tokens',
            'completion_tokens', 'reasoning_tokens', 'latency_ms', 'raw_response'.
        """
        payload: Dict[str, Any] = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": system if system is not None else QWEN_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if constrained:
            use_schema = schema if schema is not None else QWEN_WIRE_SCHEMA
            use_schema_name = schema_name if schema_name is not None else QWEN_WIRE_SCHEMA_NAME
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": use_schema_name,
                    "schema": use_schema,
                },
            }

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        started = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw_bytes = resp.read()
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            raise QwenTransportError(f"HTTP {exc.code} from {self.endpoint_url}: {err_body}") from exc
        except Exception as exc:
            raise QwenTransportError(f"Failed to connect to local Qwen runtime at {self.endpoint_url}: {exc}") from exc

        elapsed_ms = (time.perf_counter() - started) * 1000.0

        try:
            res_dict = json.loads(raw_bytes.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise QwenTransportError(f"Invalid JSON response from runtime: {raw_bytes[:200]!r}") from exc

        choices = res_dict.get("choices") or []
        if not choices:
            raise QwenTransportError(f"Runtime returned 0 choices: {res_dict!r}")

        msg = choices[0].get("message") or {}
        content = msg.get("content") or ""
        reasoning_content = msg.get("reasoning_content") or ""

        usage = res_dict.get("usage") or {}
        completion_details = usage.get("completion_tokens_details") or {}
        reasoning_tokens = completion_details.get("reasoning_tokens", 0)

        return {
            "content": content,
            "reasoning_content": reasoning_content,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "reasoning_tokens": reasoning_tokens,
            "latency_ms": elapsed_ms,
            "raw_response": res_dict,
        }


class QwenDecodeResult:
    """Outcome of a QwenSemanticDecoder decode invocation."""

    __slots__ = (
        "decoded_request",
        "error",
        "raw_wire",
        "raw_content",
        "reasoning_content",
        "prompt_tokens",
        "completion_tokens",
        "reasoning_tokens",
        "latency_ms",
        "constrained",
    )

    def __init__(
        self,
        *,
        decoded_request: Optional[DecodedRequest] = None,
        error: Optional[DecodeError] = None,
        raw_wire: Optional[Dict[str, Any]] = None,
        raw_content: Optional[str] = None,
        reasoning_content: Optional[str] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        reasoning_tokens: Optional[int] = None,
        latency_ms: Optional[float] = None,
        constrained: bool = True,
    ) -> None:
        self.decoded_request = decoded_request
        self.error = error
        self.raw_wire = raw_wire
        self.raw_content = raw_content
        self.reasoning_content = reasoning_content
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.reasoning_tokens = reasoning_tokens
        self.latency_ms = latency_ms
        self.constrained = constrained

    @property
    def ok(self) -> bool:
        return self.decoded_request is not None and self.error is None


class QwenSemanticDecoder(SemanticDecoder):
    """Step-1 SemanticDecoder backed by the installed local Qwen candidate."""

    def __init__(
        self,
        transport: Optional[QwenLocalTransport] = None,
        *,
        constrained: bool = True,
        max_tokens: int = 500,
    ) -> None:
        self._transport = transport or QwenLocalTransport()
        self.constrained = constrained
        self.max_tokens = max_tokens

    def decode(self, input_data: DecodeInput) -> DecodedRequest:
        """SemanticDecoder interface implementation. Raises DecodeError on failure."""
        res = self.decode_with_result(input_data, constrained=self.constrained, max_tokens=self.max_tokens)
        if res.error is not None:
            raise res.error
        assert res.decoded_request is not None
        return res.decoded_request

    def decode_with_result(
        self,
        input_data: DecodeInput,
        *,
        constrained: Optional[bool] = None,
        max_tokens: Optional[int] = None,
    ) -> QwenDecodeResult:
        use_constrained = self.constrained if constrained is None else constrained
        use_max_tokens = self.max_tokens if max_tokens is None else max_tokens

        started = time.perf_counter()
        try:
            resp = self._transport.complete(
                input_data.raw_text,
                constrained=use_constrained,
                max_tokens=use_max_tokens,
            )
        except QwenTransportError as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            return QwenDecodeResult(
                error=DecodeError(DecodeErrorReason.MALFORMED_OUTPUT, f"Transport failure: {exc}"),
                latency_ms=elapsed_ms,
                constrained=use_constrained,
            )

        content = resp["content"]
        reasoning = resp["reasoning_content"]
        latency_ms = resp["latency_ms"]

        if not content.strip():
            return QwenDecodeResult(
                error=DecodeError(
                    DecodeErrorReason.MISSING_REQUIRED_STRUCTURE,
                    "Model emitted empty content (exhausted in reasoning)",
                ),
                raw_content=content,
                reasoning_content=reasoning,
                prompt_tokens=resp["prompt_tokens"],
                completion_tokens=resp["completion_tokens"],
                reasoning_tokens=resp["reasoning_tokens"],
                latency_ms=latency_ms,
                constrained=use_constrained,
            )

        try:
            wire_dict = parse_wire_json(content)
        except DecodeError as exc:
            return QwenDecodeResult(
                error=exc,
                raw_content=content,
                reasoning_content=reasoning,
                prompt_tokens=resp["prompt_tokens"],
                completion_tokens=resp["completion_tokens"],
                reasoning_tokens=resp["reasoning_tokens"],
                latency_ms=latency_ms,
                constrained=use_constrained,
            )

        try:
            decoded_req = normalize_qwen_wire(wire_dict, input_data)
        except DecodeError as exc:
            return QwenDecodeResult(
                error=exc,
                raw_wire=wire_dict,
                raw_content=content,
                reasoning_content=reasoning,
                prompt_tokens=resp["prompt_tokens"],
                completion_tokens=resp["completion_tokens"],
                reasoning_tokens=resp["reasoning_tokens"],
                latency_ms=latency_ms,
                constrained=use_constrained,
            )

        return QwenDecodeResult(
            decoded_request=decoded_req,
            raw_wire=wire_dict,
            raw_content=content,
            reasoning_content=reasoning,
            prompt_tokens=resp["prompt_tokens"],
            completion_tokens=resp["completion_tokens"],
            reasoning_tokens=resp["reasoning_tokens"],
            latency_ms=latency_ms,
            constrained=use_constrained,
        )
