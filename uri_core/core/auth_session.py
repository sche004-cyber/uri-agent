"""Prototype 1/2 — login session tokens.

An AuthSessionStore token is a THIRD, distinct kind of identifier from
identity.py's user_id/device_id and state.py's conversation session_id
- keep all four separate, per identity.py's own module docstring:

    user_id          - durable, portable, who a person is (identity.py)
    device_id        - durable, local-only, which install (identity.py) -
                        this is the RUNTIME's own device_id (the PC
                        running the backend), unrelated to the field
                        below.
    conversation      - one in-progress /ask exchange (state.py)
    session_id
    auth token       - this module: proves an HTTP client just logged
    (this module)      in as a specific user_id, nothing more. It
                        grants no capability by itself beyond "which
                        user_id's state should this request see" - see
                        server.py's _resolve_authenticated_user_id.

Prototype 2 (multi-client + runtime awareness) adds a fifth, optional
concept carried ONLY by a token record, never by anything above: the
CLIENT's own self-reported device_id (a phone's Flutter install vs a
PC's Flutter install, each generating and persisting its own id
client-side - see uri_ui/lib/services/device_identity.dart). This is
metadata about the login/connection, not user state: it is bound once
at create() time (login/signup), never written into UserProfileStore/
MemoryStore/GrowthLedgerStore, and never used to look up or authorize
anything - resolve() below still answers "which user_id" exactly as
before Prototype 2; get_device_id() is a separate, purely informational
read for GET /auth/me. Two different logins for the same user_id (two
different devices, or the same device logging in twice) always get two
independent tokens/records, each with its own device_id - this is what
lets the same user connect from multiple clients simultaneously while
still being able to tell them apart.

Tokens live only in this process's memory, exactly like
audit_trail.py's AuditTrail ("Audit events live only in this process's
memory... and reset on restart" - server.py's
GET /audit/shadow-comparison docstring) - a restart always requires
logging in again. That is a deliberate prototype simplification, not
an oversight: this milestone proves isolation between logged-in users
within a running server, not durable session persistence.

A token is a high-entropy random string (secrets.token_urlsafe), never
derived from user_id/username/password, and expires after
DEFAULT_TOKEN_TTL_SECONDS of being issued - an old token can't be
resurrected to authorize a request far later than the login it came
from, mirroring approval_store.py's own fail-closed expiry discipline.
"""

import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

DEFAULT_TOKEN_TTL_SECONDS = 24 * 60 * 60  # 24 hours

_TOKEN_BYTES = 32


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class _TokenRecord:
    user_id: str
    expires_at: datetime
    device_id: Optional[str] = None


class AuthSessionStore:
    """In-memory token -> (user_id, device_id) mapping. Thread-safe:
    FastAPI/uvicorn may serve requests from more than one worker
    thread."""

    def __init__(self, ttl_seconds: int = DEFAULT_TOKEN_TTL_SECONDS):
        self._ttl_seconds = ttl_seconds
        self._tokens: Dict[str, _TokenRecord] = {}
        self._lock = threading.Lock()

    def create(
        self, user_id: str, device_id: Optional[str] = None
    ) -> str:
        token = secrets.token_urlsafe(_TOKEN_BYTES)

        record = _TokenRecord(
            user_id=user_id,
            expires_at=_now() + timedelta(seconds=self._ttl_seconds),
            device_id=device_id,
        )

        with self._lock:
            self._tokens[token] = record

        return token

    def _get_valid_record(self, token: str) -> Optional[_TokenRecord]:
        if not token:
            return None

        with self._lock:
            record = self._tokens.get(token)

            if record is None:
                return None

            if _now() > record.expires_at:
                del self._tokens[token]
                return None

            return record

    def resolve(self, token: str) -> Optional[str]:
        """Returns the user_id a still-valid token was issued for, or
        None for an unknown, empty, or expired token. Never raises -
        callers (see server.py) turn None into a 401 themselves."""

        record = self._get_valid_record(token)
        return record.user_id if record is not None else None

    def get_device_id(self, token: str) -> Optional[str]:
        """Returns the client-reported device_id bound to a still-valid
        token (see this module's docstring), or None for an unknown/
        expired token, or None when the login/signup call that created
        this token never supplied one (device_id is optional - every
        Prototype 1 caller that predates this field keeps working).
        Purely informational: never used to authorize or look up
        anything, unlike resolve()'s user_id."""

        record = self._get_valid_record(token)
        return record.device_id if record is not None else None

    def revoke(self, token: str) -> bool:
        with self._lock:
            return self._tokens.pop(token, None) is not None
