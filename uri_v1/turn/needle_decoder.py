"""NeedleSemanticDecoder: concrete Step-1 SemanticDecoder implementation (A2).

Pipeline:
    DecodeInput -> subprocess bridge (Needle 3, offline) -> wire dict
        -> needle_wire.normalize_wire (deterministic) -> DecodedRequest

Needle-specific code lives here and in needle_wire.py/needle_bridge_runtime.py.
``uri_v1.turn.decoder.SemanticDecoder`` stays provider-neutral -- it has no
knowledge of Needle, wire schemas, or subprocess transport.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from uri_v1.turn.contracts import DecodedRequest
from uri_v1.turn.decoder import DecodeInput, SemanticDecoder
from uri_v1.turn.needle_wire import (
    SYSTEM_PROMPT,
    WIRE_SCHEMA,
    DecodeError,
    DecodeErrorReason,
    normalize_wire,
)


class NeedleTransportError(RuntimeError):
    """Raised for subprocess/bridge-level failures (process, stdio, protocol)."""


class NeedleBridgeTransport:
    """Minimal subprocess/JSONL transport to the offline Needle bridge runtime.

    A fresh, URIv1-specific reimplementation -- not an import of
    ``uri_core.core.edge.adapters.ensemble.NeedleSubprocessAdapter``. See
    needle_bridge_runtime.py's module docstring and the A2 report section 7
    for why: the existing adapter lives in a module that also carries old
    tool-routing/benchmark-harness policy, and the batch instructions
    require reusing transport, not importing anywhere near that policy.
    The wire protocol here (ping / decode / close over stdio JSONL) mirrors
    the existing bridge's shape but is decode-only and schema-agnostic.
    """

    def __init__(
        self,
        python_executable: Path,
        bridge_script: Path,
        *,
        environment: Optional[Mapping[str, str]] = None,
    ) -> None:
        self._python_executable = Path(python_executable)
        self._bridge_script = Path(bridge_script)
        self._environment = dict(environment or {})
        self._process: Optional[subprocess.Popen] = None
        self.runtime_info: Dict[str, Any] = {}

    @property
    def pid(self) -> Optional[int]:
        return self._process.pid if self._process is not None else None

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def load(self) -> None:
        if self.is_running():
            return
        if not self._python_executable.is_file():
            raise NeedleTransportError(f"Needle Python executable not found: {self._python_executable}")
        if not self._bridge_script.is_file():
            raise NeedleTransportError(f"Needle bridge script not found: {self._bridge_script}")
        child_env = os.environ.copy()
        child_env.update(self._environment)
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
        self._process = subprocess.Popen(
            [str(self._python_executable), str(self._bridge_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
            env=child_env,
            creationflags=creationflags,
        )
        response = self._request({"operation": "ping"})
        if response.get("status") != "ready":
            raise NeedleTransportError(str(response.get("detail") or "Needle bridge failed to become ready"))
        self.runtime_info = dict(response)

    def _request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        process = self._process
        if process is None or process.poll() is not None:
            raise NeedleTransportError("Needle bridge process is not running")
        if process.stdin is None or process.stdout is None:
            raise NeedleTransportError("Needle bridge stdio is unavailable")
        process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        process.stdin.flush()
        raw = process.stdout.readline()
        if not raw:
            detail = process.stderr.read().strip() if process.stderr is not None else ""
            raise NeedleTransportError(detail or "Needle bridge exited without a response")
        try:
            response = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise NeedleTransportError(f"Needle bridge returned non-JSON output: {raw!r}") from exc
        if not isinstance(response, dict):
            raise NeedleTransportError("Needle bridge returned a non-object response")
        return response

    def decode(
        self,
        text: str,
        *,
        system: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        max_new_tokens: int = 300,
    ) -> Dict[str, Any]:
        self.load()
        envelope = self._request(
            {
                "operation": "decode",
                "system": system if system is not None else SYSTEM_PROMPT,
                "schema": schema if schema is not None else WIRE_SCHEMA,
                "text": text,
                "max_new_tokens": max_new_tokens,
            }
        )
        if envelope.get("status") == "error":
            raise NeedleTransportError(str(envelope.get("detail") or "Needle decode request failed"))
        response = envelope.get("response")
        if not isinstance(response, dict):
            raise NeedleTransportError("Needle bridge returned no response object")
        return response

    def reset(self) -> None:
        if not self.is_running():
            return
        envelope = self._request({"operation": "reset"})
        if envelope.get("status") == "error":
            raise NeedleTransportError(str(envelope.get("detail") or "Needle reset failed"))

    def close(self) -> None:
        process = self._process
        self._process = None
        if process is None:
            return
        if process.poll() is None:
            try:
                if process.stdin is not None:
                    process.stdin.write(json.dumps({"operation": "close"}) + "\n")
                    process.stdin.flush()
                process.wait(timeout=5)
            except Exception:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

    def __enter__(self) -> "NeedleBridgeTransport":
        self.load()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()


def default_venv_python(repo_root: Optional[Path] = None) -> Path:
    """Best-effort default path to the existing ``.venv-needle`` interpreter.

    URIv1 does not vendor or modify the Needle virtualenv; it locates and
    runs the existing one (see A2 report section 7). ``repo_root`` defaults
    to the sibling prototype checkout used throughout M35 planning; override
    via the NEEDLE_VENV_PYTHON environment variable or the constructor
    argument when that layout does not hold.
    """
    env_override = os.environ.get("NEEDLE_VENV_PYTHON")
    if env_override:
        return Path(env_override)
    base = repo_root or Path(r"C:\Users\cheta\Development\uri-agent")
    if sys.platform == "win32":
        return base / ".venv-needle" / "Scripts" / "python.exe"
    return base / ".venv-needle" / "bin" / "python"


class NeedleDecodeResult:
    """Outcome of a NeedleSemanticDecoder.decode() call: success xor error.

    Mirrors the deterministic-normalizer honesty rule (A2 section 17): a
    failed decode is surfaced explicitly, never silently converted into a
    fabricated DecodedRequest.
    """

    __slots__ = ("decoded_request", "error", "raw_wire", "raw_confidence", "latency_ms")

    def __init__(
        self,
        *,
        decoded_request: Optional[DecodedRequest] = None,
        error: Optional[DecodeError] = None,
        raw_wire: Optional[Dict[str, Any]] = None,
        raw_confidence: Optional[float] = None,
        latency_ms: Optional[float] = None,
    ) -> None:
        self.decoded_request = decoded_request
        self.error = error
        self.raw_wire = raw_wire
        self.raw_confidence = raw_confidence
        self.latency_ms = latency_ms

    @property
    def ok(self) -> bool:
        return self.decoded_request is not None and self.error is None


class NeedleSemanticDecoder(SemanticDecoder):
    """Step-1 SemanticDecoder backed by Needle 3, via subprocess transport."""

    def __init__(self, transport: NeedleBridgeTransport, *, max_new_tokens: int = 300) -> None:
        self._transport = transport
        self._max_new_tokens = max_new_tokens

    def decode(self, input_data: DecodeInput) -> DecodedRequest:
        """SemanticDecoder interface method: raises DecodeError on failure.

        Prefer decode_with_result() when the caller wants the failure
        surfaced as data rather than an exception (e.g. qualification runs).
        """
        result = self.decode_with_result(input_data)
        if result.error is not None:
            raise result.error
        assert result.decoded_request is not None
        return result.decoded_request

    def decode_with_result(self, input_data: DecodeInput) -> NeedleDecodeResult:
        started = time.perf_counter()
        try:
            raw_response = self._transport.decode(input_data.raw_text, max_new_tokens=self._max_new_tokens)
        except NeedleTransportError as exc:
            return NeedleDecodeResult(
                error=DecodeError(DecodeErrorReason.MALFORMED_OUTPUT, f"transport failure: {exc}"),
                latency_ms=(time.perf_counter() - started) * 1000.0,
            )
        latency_ms = (time.perf_counter() - started) * 1000.0

        if raw_response.get("success") is False:
            return NeedleDecodeResult(
                error=DecodeError(
                    DecodeErrorReason.MALFORMED_OUTPUT,
                    str(raw_response.get("error") or "Needle reported an unsuccessful response"),
                ),
                raw_wire=raw_response,
                latency_ms=latency_ms,
            )

        calls = raw_response.get("function_calls") or []
        if not calls:
            return NeedleDecodeResult(
                error=DecodeError(
                    DecodeErrorReason.MISSING_REQUIRED_STRUCTURE,
                    "Needle emitted no decode_request call",
                ),
                raw_wire=raw_response,
                raw_confidence=raw_response.get("confidence"),
                latency_ms=latency_ms,
            )
        if len(calls) > 1:
            return NeedleDecodeResult(
                error=DecodeError(
                    DecodeErrorReason.MALFORMED_OUTPUT,
                    f"Needle emitted {len(calls)} decode_request calls; expected exactly one",
                ),
                raw_wire=raw_response,
                raw_confidence=raw_response.get("confidence"),
                latency_ms=latency_ms,
            )

        call = calls[0]
        if not isinstance(call, dict) or call.get("name") != "decode_request":
            return NeedleDecodeResult(
                error=DecodeError(DecodeErrorReason.UNKNOWN_FIELD, f"unexpected call shape: {call!r}"),
                raw_wire=raw_response,
                raw_confidence=raw_response.get("confidence"),
                latency_ms=latency_ms,
            )
        wire = call.get("arguments")
        raw_confidence = raw_response.get("confidence")

        try:
            decoded_request = normalize_wire(wire, input_data, raw_confidence=raw_confidence)
        except DecodeError as exc:
            return NeedleDecodeResult(
                error=exc,
                raw_wire=raw_response,
                raw_confidence=raw_confidence,
                latency_ms=latency_ms,
            )

        return NeedleDecodeResult(
            decoded_request=decoded_request,
            raw_wire=raw_response,
            raw_confidence=raw_confidence,
            latency_ms=latency_ms,
        )

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> "NeedleSemanticDecoder":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()
