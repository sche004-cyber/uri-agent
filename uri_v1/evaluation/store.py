"""Per-user evaluation event storage with durable-learning ON/OFF controls.

Layout and failure handling reuse the M33.2 Edge trace precedent
(`uri_core/core/edge/trace.py`): caller-scoped `user_scoped_path`,
month-partitioned JSONL, `_locked_append`, and best-effort writes that never
raise or log content. Plan B §11-12: durable learning defaults ON; OFF stops new
durable records while session-local evidence still works; inspect, delete and
reset are supported. This store is separate from ExperienceStore.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import threading
from typing import Dict, List


from uri_v1.user_storage import locked_append as _locked_append, user_scoped_path

from .events import EvaluationEvent, EvaluationEventError, event_from_dict

logger = logging.getLogger(__name__)
SETTINGS_SCHEMA_VERSION = "m33.3-r.s7.evaluation-settings.v1"
_lock = threading.RLock()


class EvaluationEventStore:
    def __init__(self, user_id: str, *, root: str = "uri_workspace/users") -> None:
        self.user_id, self.root = user_id, root
        self._folder = user_scoped_path(user_id, "evaluation_events", root=root)
        self._settings_path = user_scoped_path(user_id, "evaluation_settings.json", root=root)
        self._session: Dict[str, List[EvaluationEvent]] = {}

    # -- durable-learning control ------------------------------------------
    def durable_enabled(self) -> bool:
        try:
            raw = json.loads(Path(self._settings_path).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return True  # Plan B §12: durable learning defaults ON
        except (OSError, json.JSONDecodeError):
            return False  # unreadable control fails closed: no durable writes
        if not isinstance(raw, dict) or raw.get("schema_version") != SETTINGS_SCHEMA_VERSION \
                or type(raw.get("durable_enabled")) is not bool:
            return False
        return raw["durable_enabled"]

    def set_durable_enabled(self, enabled: bool) -> None:
        if type(enabled) is not bool:
            raise ValueError("enabled must be boolean")
        with _lock:
            os.makedirs(os.path.dirname(self._settings_path), exist_ok=True)
            tmp = self._settings_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump({"schema_version": SETTINGS_SCHEMA_VERSION, "durable_enabled": enabled}, handle)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, self._settings_path)

    # -- recording -----------------------------------------------------------
    def record(self, event: EvaluationEvent) -> Dict[str, bool]:
        """Keep the event as session evidence; persist it only when durable learning is ON."""
        if not isinstance(event, EvaluationEvent):
            raise EvaluationEventError("only validated EvaluationEvent values are recorded")
        with _lock:
            self._session.setdefault(event.session_id or "", []).append(event)
        durable = False
        if self.durable_enabled():
            try:
                stamp = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00")).astimezone(timezone.utc)
                path = os.path.join(self._folder, stamp.strftime("%Y-%m") + ".jsonl")
                os.makedirs(self._folder, exist_ok=True)
                with _locked_append(path) as stream:
                    stream.write((json.dumps(event.redacted(), ensure_ascii=True, sort_keys=True,
                                             allow_nan=False) + "\n").encode("utf-8"))
                durable = True
            except Exception:
                logger.warning("Unable to append evaluation event")
        return {"session": True, "durable": durable}

    def session_events(self, session_id: str | None) -> List[EvaluationEvent]:
        with _lock:
            return list(self._session.get(session_id or "", ()))

    def discard_session(self, session_id: str | None) -> None:
        with _lock:
            self._session.pop(session_id or "", None)

    # -- inspect / delete / reset --------------------------------------------
    def list_events(self, *, limit: int = 100) -> List[EvaluationEvent]:
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("limit must be from 1 through 1000")
        events: List[EvaluationEvent] = []
        folder = Path(self._folder)
        if folder.exists():
            for path in sorted(folder.glob("*.jsonl")):
                for line in path.read_text(encoding="utf-8").splitlines():
                    try:
                        events.append(event_from_dict(json.loads(line)))
                    except (json.JSONDecodeError, EvaluationEventError, TypeError):
                        continue  # corrupt or foreign lines are skipped, never trusted
        return events[-limit:]

    def delete_event(self, event_id: str) -> bool:
        removed = False
        with _lock:
            folder = Path(self._folder)
            for path in sorted(folder.glob("*.jsonl")) if folder.exists() else ():
                kept = []
                for line in path.read_text(encoding="utf-8").splitlines():
                    try:
                        if json.loads(line).get("event_id") == event_id:
                            removed = True
                            continue
                    except (json.JSONDecodeError, AttributeError):
                        pass
                    kept.append(line)
                tmp = str(path) + ".tmp"
                Path(tmp).write_text("".join(x + "\n" for x in kept), encoding="utf-8")
                os.replace(tmp, path)
        return removed

    def reset(self) -> int:
        """Delete all durable evaluation events for this user. Returns files removed."""
        count = 0
        with _lock:
            folder = Path(self._folder)
            for path in folder.glob("*.jsonl") if folder.exists() else ():
                path.unlink()
                count += 1
        return count
