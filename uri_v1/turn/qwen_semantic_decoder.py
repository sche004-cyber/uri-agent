"""Qwen14BSemanticDecoder: Step-1 Semantic Decoder backed by Qwen3-14B (Batch A2.4).

Executes single-pass, structured semantic decoding across:
  - Mode A: Raw semantic decode (message only)
  - Mode B: TurnFrame assisted (message + surface cues)
  - Mode C: TurnFrame + ActiveContext assisted (conversational working memory)
"""

from __future__ import annotations

from enum import Enum
import json
import time
from typing import Any, Dict, Optional, Union

from uri_v1.turn.active_context import ActiveContext
from uri_v1.turn.contracts import DecodedRequest
from uri_v1.turn.decoder import DecodeInput, SemanticDecoder
from uri_v1.turn.local_semantic_wire import (
    QWEN14B_WIRE_SCHEMA,
    QWEN14B_WIRE_SCHEMA_NAME,
    SYSTEM_PROMPT_MODE_A,
    SYSTEM_PROMPT_MODE_B,
    SYSTEM_PROMPT_MODE_C,
    SYSTEM_PROMPT_MODE_D,
    format_mode_a_prompt,
    format_mode_b_prompt,
    format_mode_c_prompt,
    format_mode_d_prompt,
    normalize_qwen14b_wire,
)
from uri_v1.turn.needle_wire import DecodeError, DecodeErrorReason
from uri_v1.turn.qwen_decoder import QwenLocalTransport, QwenTransportError
from uri_v1.turn.qwen_wire import parse_wire_json
from uri_v1.turn.turn_frame import TurnFrame
from uri_v1.turn.turn_frame_builder import build_turn_frame


class DecoderMode(str, Enum):
    """2x2 ablation ladder modes for architecture-aligned evaluation."""

    RAW = "mode_a_raw"
    TURN_FRAME = "mode_b_turn_frame"
    ACTIVE_CONTEXT = "mode_c_active_context"
    TURN_FRAME_ACTIVE_CONTEXT = "mode_d_turn_frame_active_context"


class Qwen14BDecodeResult:
    """Outcome of a Qwen3-14B decode invocation."""

    __slots__ = (
        "decoded_request",
        "error",
        "mode",
        "raw_wire",
        "raw_content",
        "reasoning_content",
        "prompt_tokens",
        "completion_tokens",
        "reasoning_tokens",
        "latency_ms",
        "turn_frame",
        "active_context",
    )

    def __init__(
        self,
        *,
        decoded_request: Optional[DecodedRequest] = None,
        error: Optional[DecodeError] = None,
        mode: str = DecoderMode.RAW.value,
        raw_wire: Optional[Dict[str, Any]] = None,
        raw_content: Optional[str] = None,
        reasoning_content: Optional[str] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        reasoning_tokens: Optional[int] = None,
        latency_ms: Optional[float] = None,
        turn_frame: Optional[TurnFrame] = None,
        active_context: Optional[ActiveContext] = None,
    ) -> None:
        self.decoded_request = decoded_request
        self.error = error
        self.mode = mode
        self.raw_wire = raw_wire
        self.raw_content = raw_content
        self.reasoning_content = reasoning_content
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.reasoning_tokens = reasoning_tokens
        self.latency_ms = latency_ms
        self.turn_frame = turn_frame
        self.active_context = active_context

    @property
    def ok(self) -> bool:
        return self.decoded_request is not None and self.error is None


class Qwen14BSemanticDecoder(SemanticDecoder):
    """Step-1 Semantic Decoder backed by Qwen3-14B on LM Studio."""

    def __init__(
        self,
        transport: Optional[QwenLocalTransport] = None,
        *,
        default_mode: DecoderMode = DecoderMode.RAW,
        max_tokens: int = 800,
        temperature: float = 0.0,
    ) -> None:
        self._transport = transport or QwenLocalTransport(model_id="qwen3-14b", timeout=120.0)
        self.default_mode = default_mode
        self.max_tokens = max_tokens
        self.temperature = temperature

    def decode(self, input_data: DecodeInput) -> DecodedRequest:
        res = self.decode_with_result(input_data)
        if res.error is not None:
            raise res.error
        assert res.decoded_request is not None
        return res.decoded_request

    def decode_with_result(
        self,
        input_data: Union[DecodeInput, str],
        *,
        mode: Optional[DecoderMode] = None,
        active_context: Optional[ActiveContext] = None,
        max_tokens: Optional[int] = None,
    ) -> Qwen14BDecodeResult:
        if isinstance(input_data, str):
            input_data = DecodeInput.from_text(input_data)

        raw_text = input_data.raw_text
        use_mode = mode if mode is not None else self.default_mode
        use_max_tokens = max_tokens if max_tokens is not None else self.max_tokens

        turn_frame: Optional[TurnFrame] = None
        prompt_text: str = raw_text
        system_prompt: str = SYSTEM_PROMPT_MODE_A

        if use_mode == DecoderMode.RAW:
            prompt_text = format_mode_a_prompt(raw_text)
            system_prompt = SYSTEM_PROMPT_MODE_A

        elif use_mode == DecoderMode.TURN_FRAME:
            turn_frame = build_turn_frame(raw_text, attachments=input_data.attachments)
            prompt_text = format_mode_b_prompt(raw_text, turn_frame)
            system_prompt = SYSTEM_PROMPT_MODE_B

        elif use_mode == DecoderMode.ACTIVE_CONTEXT:
            prompt_text = format_mode_c_prompt(raw_text, active_context)
            system_prompt = SYSTEM_PROMPT_MODE_C

        elif use_mode == DecoderMode.TURN_FRAME_ACTIVE_CONTEXT:
            turn_frame = build_turn_frame(raw_text, attachments=input_data.attachments)
            prompt_text = format_mode_d_prompt(raw_text, turn_frame, active_context)
            system_prompt = SYSTEM_PROMPT_MODE_D

        started = time.perf_counter()
        try:
            resp = self._transport.complete(
                prompt_text,
                system=system_prompt,
                constrained=True,
                schema=QWEN14B_WIRE_SCHEMA,
                schema_name=QWEN14B_WIRE_SCHEMA_NAME,
                max_tokens=use_max_tokens,
                temperature=self.temperature,
            )
        except QwenTransportError as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            return Qwen14BDecodeResult(
                error=DecodeError(DecodeErrorReason.MALFORMED_OUTPUT, f"Transport failure: {exc}"),
                mode=use_mode.value,
                latency_ms=elapsed_ms,
                turn_frame=turn_frame,
                active_context=active_context,
            )

        content = resp["content"]
        reasoning = resp["reasoning_content"]
        latency_ms = resp["latency_ms"]

        if not content.strip():
            return Qwen14BDecodeResult(
                error=DecodeError(
                    DecodeErrorReason.MISSING_REQUIRED_STRUCTURE,
                    "Qwen3-14B emitted empty content (tokens exhausted in reasoning)",
                ),
                mode=use_mode.value,
                raw_content=content,
                reasoning_content=reasoning,
                prompt_tokens=resp["prompt_tokens"],
                completion_tokens=resp["completion_tokens"],
                reasoning_tokens=resp["reasoning_tokens"],
                latency_ms=latency_ms,
                turn_frame=turn_frame,
                active_context=active_context,
            )

        try:
            wire_dict = parse_wire_json(content)
        except DecodeError as exc:
            return Qwen14BDecodeResult(
                error=exc,
                mode=use_mode.value,
                raw_content=content,
                reasoning_content=reasoning,
                prompt_tokens=resp["prompt_tokens"],
                completion_tokens=resp["completion_tokens"],
                reasoning_tokens=resp["reasoning_tokens"],
                latency_ms=latency_ms,
                turn_frame=turn_frame,
                active_context=active_context,
            )

        try:
            decoded_req = normalize_qwen14b_wire(wire_dict, input_data, active_context=active_context)
        except DecodeError as exc:
            return Qwen14BDecodeResult(
                error=exc,
                mode=use_mode.value,
                raw_wire=wire_dict,
                raw_content=content,
                reasoning_content=reasoning,
                prompt_tokens=resp["prompt_tokens"],
                completion_tokens=resp["completion_tokens"],
                reasoning_tokens=resp["reasoning_tokens"],
                latency_ms=latency_ms,
                turn_frame=turn_frame,
                active_context=active_context,
            )

        return Qwen14BDecodeResult(
            decoded_request=decoded_req,
            mode=use_mode.value,
            raw_wire=wire_dict,
            raw_content=content,
            reasoning_content=reasoning,
            prompt_tokens=resp["prompt_tokens"],
            completion_tokens=resp["completion_tokens"],
            reasoning_tokens=resp["reasoning_tokens"],
            latency_ms=latency_ms,
            turn_frame=turn_frame,
            active_context=active_context,
        )
