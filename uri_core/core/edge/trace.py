"""Redacted, caller-scoped, best-effort Edge routing trace storage."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from uri_core.core.portable_paths import user_scoped_path
from uri_core.core.usage_meter import _locked_append

logger = logging.getLogger(__name__)
TRACE_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class EdgeRoutingTraceEvent:
    timestamp: str
    decision: str
    intelligence_layer: str
    reason_codes: Tuple[str, ...] = ()
    session_id: Optional[str] = None
    request_length_bucket: Optional[str] = None
    untrusted_content_present: bool = False
    edge: Dict[str, Optional[str]] = field(default_factory=dict)
    confidence: Dict[str, Any] = field(default_factory=dict)
    threshold_percent: Optional[int] = None
    shortlist_size: Optional[int] = None
    capability_id: Optional[str] = None
    main_brain: Dict[str, Any] = field(default_factory=dict)
    latency_ms: Dict[str, Optional[int]] = field(default_factory=dict)
    resource: Dict[str, Any] = field(default_factory=dict)
    outcome: str = "none"
    evidence_result: str = "none"
    schema_version: str = TRACE_SCHEMA_VERSION

    def redacted(self) -> Dict[str, Any]:
        data = asdict(self)
        # Deliberately whitelist the contract; unknown/raw content cannot leak.
        return {key: data[key] for key in EdgeRoutingTraceEvent.__dataclass_fields__}


class EdgeRoutingTraceStore:
    def __init__(self, user_id: str, *, root: str = "uri_workspace/users", retention_months: int = 3) -> None:
        self.user_id, self.root, self.retention_months = user_id, root, retention_months

    def _path(self, month: str) -> str:
        return user_scoped_path(self.user_id, os.path.join("edge_trace", month + ".jsonl"), root=self.root)

    def record(self, event: EdgeRoutingTraceEvent) -> bool:
        try:
            stamp = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError("timestamp must be timezone-aware")
            path = self._path(stamp.astimezone(timezone.utc).strftime("%Y-%m"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with _locked_append(path) as stream:
                stream.write((json.dumps(event.redacted(), ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8"))
            return True
        except Exception:
            logger.warning("Unable to append Edge routing trace")
            return False

    def latest(self) -> Optional[Dict[str, Any]]:
        events = self.list_events(limit=1)
        return events[-1] if events else None

    def list_events(self, *, limit: int = 50) -> List[Dict[str, Any]]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit must be from 1 through 100")
        folder = Path(user_scoped_path(self.user_id, "edge_trace", root=self.root))
        events: List[Dict[str, Any]] = []
        try:
            for path in sorted(folder.glob("*.jsonl")):
                for line in path.read_text(encoding="utf-8").splitlines():
                    try:
                        value = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(value, dict) and value.get("schema_version") == TRACE_SCHEMA_VERSION:
                        events.append(value)
        except FileNotFoundError:
            pass
        return events[-limit:]
