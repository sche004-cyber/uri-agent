"""Allowlisted lifecycle telemetry; private reasoning is never accepted."""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import psutil

from .models import InvocationTelemetryRecord, LifecycleEventRecord
from .storage import confined_path


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl(filename: str, payload: Dict[str, Any]) -> None:
    path = confined_path("logs", filename, create_parent=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, sort_keys=True, ensure_ascii=False) + "\n")


def record_network_event(
    *, url: str, purpose: str, byte_count: int, checksum_result: str,
    status: str, detail: Optional[str] = None,
) -> None:
    parsed = urlparse(url)
    payload = {
        "timestamp": utc_timestamp(),
        "target_url": url,
        "target_host": parsed.hostname,
        "purpose": purpose,
        "byte_count": int(byte_count),
        "checksum_result": checksum_result,
        "status": status,
    }
    if detail:
        payload["detail"] = detail
    _append_jsonl("network_events.jsonl", payload)


def record_lifecycle_event(
    event: str, status: str, *, runtime_id: Optional[str] = None,
    model_id: Optional[str] = None, detail: Optional[Dict[str, Any]] = None,
) -> LifecycleEventRecord:
    record = LifecycleEventRecord(
        timestamp=utc_timestamp(), event=event, status=status,
        runtime_id=runtime_id, model_id=model_id, detail=dict(detail or {}),
    )
    _append_jsonl("lifecycle_events.jsonl", asdict(record))
    return record


def record_invocation_attempt(
    model_id: str, *, invoked: bool, bypass_reason: Optional[str] = None,
    latency_ms: Optional[float] = None, rss_memory_bytes: Optional[int] = None,
) -> InvocationTelemetryRecord:
    if not isinstance(model_id, str) or not model_id:
        raise ValueError("model_id is required")
    if invoked and bypass_reason:
        raise ValueError("an invoked model cannot have a bypass reason")
    if not invoked and not bypass_reason:
        raise ValueError("a bypassed model requires a reason")
    rss = rss_memory_bytes
    if rss is None:
        try:
            rss = psutil.Process().memory_info().rss
        except (psutil.Error, OSError):
            rss = None
    record = InvocationTelemetryRecord(
        timestamp=utc_timestamp(), model_id=model_id, invoked=bool(invoked),
        bypass_reason=bypass_reason, latency_ms=latency_ms,
        rss_memory_bytes=rss,
    )
    _append_jsonl("invocations.jsonl", asdict(record))
    return record
