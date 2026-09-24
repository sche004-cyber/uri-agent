"""NeedleSinglePassDecoder: Architecture-aligned single-pass decoder for Needle 3 (Batch A2.4R).

Executes single-pass structured decoding across Modes A, B, C, and D under the
identical wire schema and prompt definitions as Qwen3-14B:
  - Mode A: Raw semantic decode (message only)
  - Mode B: TurnFrame assisted (message + surface cues)
  - Mode C: ActiveContext assisted (message + working memory)
  - Mode D: TurnFrame + ActiveContext assisted (message + surface cues + working memory)
"""

from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any, Dict, Optional, Union

from uri_v1.turn.active_context import ActiveContext
from uri_v1.turn.contracts import DecodedRequest
from uri_v1.turn.decoder import DecodeInput, SemanticDecoder
from uri_v1.turn.local_semantic_wire import (
    QWEN14B_WIRE_SCHEMA,
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
from uri_v1.turn.needle_decoder import (
    NeedleBridgeTransport,
    NeedleTransportError,
    default_venv_python,
)
from uri_v1.turn.needle_wire import DecodeError, DecodeErrorReason
from uri_v1.turn.qwen_semantic_decoder import DecoderMode
from uri_v1.turn.turn_frame import TurnFrame
from uri_v1.turn.turn_frame_builder import build_turn_frame

NEEDLE_TOOL_SCHEMA: Dict[str, Any] = {
    "name": "decode_request",
    "description": "Always call this tool to record the semantic decoding of the user turn.",
    "parameters": QWEN14B_WIRE_SCHEMA,
}


class NeedleSinglePassResult:
    """Outcome of a NeedleSinglePassDecoder decode invocation."""

    __slots__ = (
        "decoded_request",
        "error",
        "mode",
        "raw_wire",
        "raw_response",
        "function_calls",
        "reasoning",
        "prefill_tps",
        "decode_tps",
        "peak_ram_mb",
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
        raw_response: Optional[Dict[str, Any]] = None,
        function_calls: Optional[list] = None,
        reasoning: Optional[str] = None,
        prefill_tps: Optional[float] = None,
        decode_tps: Optional[float] = None,
        peak_ram_mb: Optional[float] = None,
        latency_ms: Optional[float] = None,
        turn_frame: Optional[TurnFrame] = None,
        active_context: Optional[ActiveContext] = None,
    ) -> None:
        self.decoded_request = decoded_request
        self.error = error
        self.mode = mode
        self.raw_wire = raw_wire
        self.raw_response = raw_response
        self.function_calls = function_calls or []
        self.reasoning = reasoning
        self.prefill_tps = prefill_tps
        self.decode_tps = decode_tps
        self.peak_ram_mb = peak_ram_mb
        self.latency_ms = latency_ms
        self.turn_frame = turn_frame
        self.active_context = active_context

    @property
    def ok(self) -> bool:
        return self.decoded_request is not None and self.error is None


class NeedleSinglePassDecoder(SemanticDecoder):
    """Architecture-aligned Step-1 Semantic Decoder backed by base Needle 3."""

    def __init__(
        self,
        transport: Optional[NeedleBridgeTransport] = None,
        *,
        default_mode: DecoderMode = DecoderMode.RAW,
        max_new_tokens: int = 400,
    ) -> None:
        if transport is None:
            venv = default_venv_python()
            bridge = Path(__file__).parent / "needle_bridge_runtime.py"
            self._transport = NeedleBridgeTransport(venv, bridge)
        else:
            self._transport = transport
        self.default_mode = default_mode
        self.max_new_tokens = max_new_tokens

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
        max_new_tokens: Optional[int] = None,
    ) -> NeedleSinglePassResult:
        if isinstance(input_data, str):
            input_data = DecodeInput.from_text(input_data)

        raw_text = input_data.raw_text
        use_mode = mode if mode is not None else self.default_mode
        use_max_tokens = max_new_tokens if max_new_tokens is not None else self.max_new_tokens

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
            resp = self._transport.decode(
                prompt_text,
                system=system_prompt,
                schema=NEEDLE_TOOL_SCHEMA,
                max_new_tokens=use_max_tokens,
            )
        except NeedleTransportError as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            return NeedleSinglePassResult(
                error=DecodeError(DecodeErrorReason.MALFORMED_OUTPUT, f"Needle transport failure: {exc}"),
                mode=use_mode.value,
                latency_ms=elapsed_ms,
                turn_frame=turn_frame,
                active_context=active_context,
            )

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        bridge_latency = resp.get("_bridge_latency_ms", elapsed_ms)

        function_calls = resp.get("function_calls") or []
        reasoning = resp.get("reasoning")
        prefill_tps = resp.get("prefill_tps")
        decode_tps = resp.get("decode_tps")
        peak_ram_mb = resp.get("peak_ram_mb")

        if not function_calls:
            return NeedleSinglePassResult(
                error=DecodeError(
                    DecodeErrorReason.MISSING_REQUIRED_STRUCTURE,
                    f"Needle emitted no decode_request call (reasoning: {reasoning!r})",
                ),
                mode=use_mode.value,
                raw_response=resp,
                function_calls=function_calls,
                reasoning=reasoning,
                prefill_tps=prefill_tps,
                decode_tps=decode_tps,
                peak_ram_mb=peak_ram_mb,
                latency_ms=bridge_latency,
                turn_frame=turn_frame,
                active_context=active_context,
            )

        call = function_calls[0]
        wire_dict = call.get("arguments")
        if not isinstance(wire_dict, dict):
            return NeedleSinglePassResult(
                error=DecodeError(
                    DecodeErrorReason.MALFORMED_OUTPUT,
                    f"Needle tool arguments is not a dictionary: {wire_dict!r}",
                ),
                mode=use_mode.value,
                raw_response=resp,
                function_calls=function_calls,
                reasoning=reasoning,
                prefill_tps=prefill_tps,
                decode_tps=decode_tps,
                peak_ram_mb=peak_ram_mb,
                latency_ms=bridge_latency,
                turn_frame=turn_frame,
                active_context=active_context,
            )

        try:
            decoded_req = normalize_qwen14b_wire(wire_dict, input_data, active_context=active_context)
        except DecodeError as exc:
            return NeedleSinglePassResult(
                error=exc,
                mode=use_mode.value,
                raw_wire=wire_dict,
                raw_response=resp,
                function_calls=function_calls,
                reasoning=reasoning,
                prefill_tps=prefill_tps,
                decode_tps=decode_tps,
                peak_ram_mb=peak_ram_mb,
                latency_ms=bridge_latency,
                turn_frame=turn_frame,
                active_context=active_context,
            )

        return NeedleSinglePassResult(
            decoded_request=decoded_req,
            mode=use_mode.value,
            raw_wire=wire_dict,
            raw_response=resp,
            function_calls=function_calls,
            reasoning=reasoning,
            prefill_tps=prefill_tps,
            decode_tps=decode_tps,
            peak_ram_mb=peak_ram_mb,
            latency_ms=bridge_latency,
            turn_frame=turn_frame,
            active_context=active_context,
        )

    def reset(self) -> None:
        self._transport.reset()

    def close(self) -> None:
        self._transport.close()
