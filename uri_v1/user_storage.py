"""Caller-scoped storage helpers for uri_v1 per-user stores.

`uri_v1` never imports `uri_core` (enforced by the S1/S2 boundary tests), so
this module re-implements two small, proven `uri_core` patterns instead of
importing them:
- `user_scoped_path`: `uri_core/core/portable_paths.py` (UUID-shaped user IDs
  only; anything else is refused before a path is built);
- `locked_append`: `uri_core/core/usage_meter.py` `_locked_append` (thread
  and process serialized, append-only).
"""

from __future__ import annotations

from contextlib import contextmanager
import os
import re
import threading

_USER_ID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
_append_lock = threading.Lock()


class UserPathValidationError(ValueError):
    pass


def user_scoped_path(user_id: str, filename: str, root: str) -> str:
    if not isinstance(user_id, str) or not _USER_ID_PATTERN.match(user_id):
        raise UserPathValidationError("user_id is not UUID-shaped; refusing to build a path")
    return os.path.normpath(os.path.join(root, user_id, filename))


@contextmanager
def locked_append(path: str):
    with _append_lock, open(path, "ab") as stream:
        if os.name == "nt":
            import msvcrt
            stream.seek(2**63 - 2)  # lock a byte outside the data so readers stay unblocked
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
