"""Append-only, content-addressed result versions (plan: docs/plans/M33_3_R_S11_RESULT_VERSION_PLAN.md).

A result version is identified by the SHA-256 of its content. Content is kept
in a write-once blob store keyed by that hash, so an edited version is
preserved, not only detected. Versions are appended; no version or blob is
ever rewritten or deleted by this module.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import re
import threading
from typing import List, Optional

from uri_v1.user_storage import user_scoped_path


LEDGER_SCHEMA_VERSION = "m33.3-r.s11.result-versions.v1"
_RESULT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-]{0,127}$")
_lock = threading.RLock()


class VersionOrigin(str, Enum):
    GENERATED = "GENERATED"
    USER_EDIT = "USER_EDIT"
    REDO = "REDO"


class EditedStatus(str, Enum):
    UNEDITED = "UNEDITED"
    USER_EDITED = "USER_EDITED"
    UNKNOWN = "UNKNOWN"


class ResultVersionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ResultVersion:
    result_id: str
    version: int
    content_sha256: str
    origin: str
    parent_version: Optional[int]
    binding_id: Optional[str]
    candidate_id: Optional[str]
    trace_id: Optional[str]
    created_at: str


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class ResultVersionLedger:
    def __init__(self, user_id: str, *, root: str = "uri_workspace/users") -> None:
        self._dir = Path(user_scoped_path(user_id, "result_versions", root=root))
        self._blobs = Path(user_scoped_path(user_id, "result_blobs", root=root))

    # -- storage ---------------------------------------------------------------
    def _path(self, result_id: str) -> Path:
        if not isinstance(result_id, str) or not _RESULT_ID.match(result_id):
            raise ResultVersionError("invalid result_id")
        return self._dir / f"{result_id}.json"

    def _write_blob(self, content: bytes) -> str:
        if not isinstance(content, (bytes, bytearray)):
            raise ResultVersionError("content must be bytes")
        digest = sha256(bytes(content))
        path = self._blobs / digest
        if not path.exists():  # write-once
            self._blobs.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(bytes(content))
            os.replace(tmp, path)
        return digest

    def blob(self, digest: str) -> bytes:
        data = (self._blobs / digest).read_bytes()
        if sha256(data) != digest:
            raise ResultVersionError("blob integrity failure")
        return data

    def versions(self, result_id: str) -> List[ResultVersion]:
        path = self._path(result_id)
        if not path.exists():
            return []
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("schema_version") != LEDGER_SCHEMA_VERSION:
            raise ResultVersionError("unsupported ledger schema")
        return [ResultVersion(**v) for v in raw["versions"]]

    def head(self, result_id: str) -> Optional[ResultVersion]:
        versions = self.versions(result_id)
        return versions[-1] if versions else None

    def _append(self, result_id: str, content: bytes, origin: VersionOrigin, *, parent: Optional[int],
                binding_id: Optional[str], candidate_id: Optional[str], trace_id: Optional[str]) -> ResultVersion:
        with _lock:
            existing = self.versions(result_id)
            digest = self._write_blob(content)
            version = ResultVersion(result_id, len(existing) + 1, digest, origin.value, parent, binding_id,
                                    candidate_id, trace_id, datetime.now(timezone.utc).isoformat())
            path = self._path(result_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"schema_version": LEDGER_SCHEMA_VERSION,
                                       "versions": [asdict(v) for v in existing + [version]]}, indent=1),
                           encoding="utf-8")
            os.replace(tmp, path)
            return version

    # -- operations ------------------------------------------------------------
    def record_generated(self, result_id: str, content: bytes, *, binding_id: Optional[str] = None,
                         candidate_id: Optional[str] = None, trace_id: Optional[str] = None) -> ResultVersion:
        if self.versions(result_id):
            raise ResultVersionError("result already recorded")
        return self._append(result_id, content, VersionOrigin.GENERATED, parent=None, binding_id=binding_id,
                            candidate_id=candidate_id, trace_id=trace_id)

    def edited_status(self, result_id: str, current_content: Optional[bytes]) -> EditedStatus:
        head = self.head(result_id)
        if head is None or current_content is None:
            return EditedStatus.UNKNOWN  # fail closed
        if sha256(bytes(current_content)) != head.content_sha256:
            return EditedStatus.USER_EDITED
        # Unchanged since the head; the head itself may be a preserved user edit.
        return EditedStatus.USER_EDITED if head.origin == VersionOrigin.USER_EDIT.value else EditedStatus.UNEDITED

    def observe(self, result_id: str, current_content: bytes) -> ResultVersion:
        """Preserve the current content as a USER_EDIT version if it differs from the head."""
        head = self.head(result_id)
        if head is not None and sha256(bytes(current_content)) == head.content_sha256:
            return head
        return self._append(result_id, current_content, VersionOrigin.USER_EDIT,
                            parent=head.version if head else None, binding_id=None, candidate_id=None, trace_id=None)

    def append_redo(self, result_id: str, content: bytes, *, parent: int, binding_id: Optional[str],
                    candidate_id: Optional[str], trace_id: Optional[str]) -> ResultVersion:
        if not any(v.version == parent for v in self.versions(result_id)):
            raise ResultVersionError("redo parent version does not exist")
        return self._append(result_id, content, VersionOrigin.REDO, parent=parent, binding_id=binding_id,
                            candidate_id=candidate_id, trace_id=trace_id)
