"""Observational, append-only per-user usage; never persists model content."""

import json
import logging
import os
import re
import threading
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional

from uri_core.core.portable_paths import user_scoped_path

logger = logging.getLogger(__name__)
_append_lock = threading.Lock()


@contextmanager
def _locked_append(path: str):
    # Windows CRT append alone can race between seeking EOF and writing.
    # Serialize threads and processes, keeping the data file append-only.
    with _append_lock, open(path, "ab") as stream:
        if os.name == "nt":
            import msvcrt
            # Lock a byte outside the data so observational readers stay unblocked.
            stream.seek(2**63 - 2)
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            stream.seek(0, os.SEEK_END)
            yield stream
            stream.flush()
        finally:
            if os.name == "nt":
                stream.seek(2**63 - 2)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


@dataclass(frozen=True)
class UsageRecord:
    ts: str
    user_id: str
    session_id: Optional[str]
    role: str
    provider_id: Optional[str]
    model: Optional[str]
    prompt_tokens: Dict[str, Any]
    eval_tokens: Dict[str, Any]
    duration_seconds: Dict[str, Any]
    outcome: str
    fallback_from: List[str]
    estimated_cost: Dict[str, Any]


def current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def usage_path(user_id: str, month: str) -> str:
    if not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", month):
        raise ValueError("month must be YYYY-MM")
    return user_scoped_path(user_id, os.path.join("usage", month + ".jsonl"))


def month_records(user_id: str, month: str) -> Iterator[Dict[str, Any]]:
    """Read only this user's records, tolerating an incomplete JSONL tail."""
    path = usage_path(user_id, month)
    try:
        with open(path, encoding="utf-8") as stream:
            for line in stream:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("Skipping malformed usage line")
                    continue
                if isinstance(record, dict) and record.get("user_id") == user_id:
                    yield record
    except FileNotFoundError:
        return


def known_tokens(record: Dict[str, Any]) -> int:
    """A partially measured call contributes zero to the ceiling fold."""
    fields = [record.get(name, {}) for name in ("prompt_tokens", "eval_tokens")]
    if all(isinstance(f, dict) and f.get("confidence") == "KNOWN"
           and type(f.get("value")) is int and f["value"] >= 0 for f in fields):
        return sum(f["value"] for f in fields)
    return 0


class UsageMeter:
    def record(self, record: UsageRecord) -> None:
        try:
            stamp = datetime.fromisoformat(record.ts.replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError("usage timestamp must be timezone-aware")
            path = usage_path(record.user_id, stamp.astimezone(timezone.utc).strftime("%Y-%m"))
            line = json.dumps(asdict(record), ensure_ascii=True, allow_nan=False) + "\n"
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with _locked_append(path) as stream:
                stream.write(line.encode("utf-8"))
        except Exception:
            # Do not include exception text: observational logs must not leak content.
            logger.warning("Unable to append usage record")

    def estimate_current_month_tokens(self, user_id: str, role: Optional[str] = None) -> int:
        return sum(known_tokens(record) for record in month_records(user_id, current_month())
                   if role is None or record.get("role") == role)
