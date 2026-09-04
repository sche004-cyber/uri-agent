"""User-scoped storage paths: turns identity.py's "seed of a future
PortableStateStore" comment into a literal, testable fact - profile,
memory, and growth-ledger state live under one directory keyed by
user_id (uri_workspace/users/<user_id>/), so a later export/sync
milestone has one clearly-identified thing to copy instead of three
unrelated ambient files with no relationship to identity.

This module is pure path/file plumbing. It does not construct any
store, does not decide when migration runs, and is not imported for
its side effects - callers (see server.py's _initialize_user_scoped_
stores, invoked at application startup, never at import) decide when
to call user_scoped_path()/migrate_legacy_file_if_needed().

device_id is deliberately never accepted or used here - device
identity stays local-only and outside the user-scoped tree, per
identity.py's user_id/device_id distinction.
"""

import os
import re
import shutil

_USER_ID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

DEFAULT_USER_STATE_ROOT = "uri_workspace/users"


class PortablePathValidationError(ValueError):
    """Raised when a user_id fails strict validation before being used
    as a filesystem path component. user_id normally comes from
    uuid.uuid4() (see identity.py) and always matches this shape; a
    mismatch means the identity file is corrupted or was hand-edited,
    and it must never be trusted to build a filesystem path (a
    traversal-shaped value like "../../etc" is exactly what this
    guards against)."""


def _ensure_parent_dir(path: str) -> None:
    folder = os.path.dirname(path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)


def user_scoped_path(
    user_id: str,
    filename: str,
    root: str = DEFAULT_USER_STATE_ROOT,
) -> str:
    """Returns root/user_id/filename, normalized. Raises
    PortablePathValidationError rather than building a path at all if
    user_id doesn't strictly match a UUID shape."""

    if not isinstance(user_id, str) or not _USER_ID_PATTERN.match(
        user_id
    ):
        raise PortablePathValidationError(
            f"user_id {user_id!r} does not look like a valid UUID and "
            "will not be used as a filesystem path component."
        )

    return os.path.normpath(os.path.join(root, user_id, filename))


def migrate_legacy_file_if_needed(
    legacy_path: str, new_path: str
) -> bool:
    """Copies legacy_path to new_path exactly once. Copy-only, never
    deletes or modifies legacy_path - it is left in place as a backup.
    A no-op (returns False) when new_path already exists (never
    overwrites user-scoped state that may have since diverged) or when
    legacy_path does not exist (nothing to migrate - e.g.
    growth_ledger.json on an install where no growth event has ever
    been recorded yet). Returns True only when a copy actually
    happened."""

    legacy_path = os.path.normpath(legacy_path)
    new_path = os.path.normpath(new_path)

    if os.path.exists(new_path):
        return False

    if not os.path.exists(legacy_path):
        return False

    _ensure_parent_dir(new_path)
    shutil.copy2(legacy_path, new_path)

    return True
