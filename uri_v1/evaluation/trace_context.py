"""Response trace identifiers in W3C Trace Context format.

A `trace_id` is 32 lowercase hex characters and never all zeros, exactly the
W3C `traceparent` trace-id field, so a later OpenTelemetry exporter can use it
unchanged. It is an opaque correlation handle: it carries no content.
"""

from __future__ import annotations

import re
import secrets

_TRACE_ID = re.compile(r"^[0-9a-f]{32}$")
_SPAN_ID = re.compile(r"^[0-9a-f]{16}$")
_INVALID_TRACE_ID = "0" * 32
_INVALID_SPAN_ID = "0" * 16


def new_trace_id() -> str:
    while True:
        value = secrets.token_hex(16)
        if value != _INVALID_TRACE_ID:
            return value


def new_span_id() -> str:
    while True:
        value = secrets.token_hex(8)
        if value != _INVALID_SPAN_ID:
            return value


def is_valid_trace_id(value: object) -> bool:
    return isinstance(value, str) and bool(_TRACE_ID.match(value)) and value != _INVALID_TRACE_ID


def is_valid_span_id(value: object) -> bool:
    return isinstance(value, str) and bool(_SPAN_ID.match(value)) and value != _INVALID_SPAN_ID


def require_trace_id(value: object) -> str:
    if not is_valid_trace_id(value):
        raise ValueError("trace_id must be 32 lowercase hex characters and not all zeros")
    return value  # type: ignore[return-value]


def traceparent(trace_id: str, span_id: str, *, sampled: bool = True) -> str:
    """Render a W3C `traceparent` header value (version 00)."""
    require_trace_id(trace_id)
    if not is_valid_span_id(span_id):
        raise ValueError("span_id must be 16 lowercase hex characters and not all zeros")
    return f"00-{trace_id}-{span_id}-{'01' if sampled else '00'}"
