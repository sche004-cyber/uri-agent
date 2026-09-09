"""M22.2: device-shaped views and actions over persisted login sessions.

This module owns NO state of its own - "a device" is not a new
persisted concept, it is a grouping of the session records
AuthSessionStore already persists (see auth_session.py's module
docstring), keyed by the client-reported device_id each login already
optionally carries. A dedicated module exists only because "list my
devices" / "revoke this device" is a distinct, user-facing concept
worth naming, not because it needs its own storage - see
URI_M22_ARCHITECTURE.md section 4 ("device registry with revocation").

Sessions created without a device_id (still fully supported - see
auth_session.py's own backward-compatibility note) are deliberately
excluded from the device-grouped view below: there is nothing
meaningful to group or revoke them BY, since device_id is exactly the
grouping key. Such a session remains individually revocable through
the existing token-based POST /auth/logout.
"""

from dataclasses import dataclass
from typing import List

from uri_core.core.auth_session import AuthSessionStore


@dataclass(frozen=True)
class DeviceSummary:
    """One device_id's current login state for one user - the
    client-facing shape GET /auth/devices returns. Never carries a
    session_ref/token; revocation is a separate, explicit action (see
    revoke_device below), not something this read-only view exposes."""

    device_id: str
    session_count: int
    most_recent_expires_at: str


def list_devices_for_user(
    auth_session_store: AuthSessionStore, user_id: str
) -> List[DeviceSummary]:
    """One DeviceSummary per distinct device_id with at least one
    still-valid session for user_id, sorted by device_id for a stable,
    deterministic response. Sessions with no device_id at all are
    excluded - see module docstring."""

    sessions = auth_session_store.list_for_user(user_id)

    by_device = {}

    for session in sessions:

        if session.device_id is None:
            continue

        existing = by_device.get(session.device_id)

        if existing is None:
            by_device[session.device_id] = {
                "count": 1,
                "latest": session.expires_at,
            }
        else:
            existing["count"] += 1
            if session.expires_at > existing["latest"]:
                existing["latest"] = session.expires_at

    return [
        DeviceSummary(
            device_id=device_id,
            session_count=info["count"],
            most_recent_expires_at=info["latest"],
        )
        for device_id, info in sorted(by_device.items())
    ]


def revoke_device(
    auth_session_store: AuthSessionStore, user_id: str, device_id: str
) -> int:
    """Revokes every currently-valid session belonging to user_id AND
    bound to device_id - never a session belonging to any other
    user_id, even one that happens to report the identical device_id
    string (client-reported device_id is not unique across accounts -
    see auth_session.py's own module docstring on this). Returns the
    number of sessions actually revoked (0 if none matched, never
    raises for an unknown device_id)."""

    sessions = auth_session_store.list_for_user(user_id)

    revoked = 0

    for session in sessions:

        if session.device_id != device_id:
            continue

        if auth_session_store.revoke_by_ref(session.session_ref):
            revoked += 1

    return revoked
