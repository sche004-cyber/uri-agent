"""Prototype 1 — login session tokens.

An AuthSessionStore token is a THIRD, distinct kind of identifier from
identity.py's user_id/device_id and state.py's conversation session_id
- keep all four separate, per identity.py's own module docstring:

    user_id          - durable, portable, who a person is (identity.py)
    device_id        - durable, local-only, which install (identity.py)
    conversation      - one in-progress /ask exchange (state.py)
    session_id
    auth token       - this module: proves an HTTP client just logged
    (this module)      in as a specific user_id, nothing more. It
                        grants no capability by itself beyond "which
                        user_id's state should this request see" - see
                        server.py's _resolve_authenticated_user_id.

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


class AuthSessionStore:
    """In-memory token -> user_id mapping. Thread-safe: FastAPI/
    uvicorn may serve requests from more than one worker thread."""

    def __init__(self, ttl_seconds: int = DEFAULT_TOKEN_TTL_SECONDS):
        self._ttl_seconds = ttl_seconds
        self._tokens: Dict[str, _TokenRecord] = {}
        self._lock = threading.Lock()

    def create(self, user_id: str) -> str:
        token = secrets.token_urlsafe(_TOKEN_BYTES)

        record = _TokenRecord(
            user_id=user_id,
            expires_at=_now() + timedelta(seconds=self._ttl_seconds),
        )

        with self._lock:
            self._tokens[token] = record

        return token

    def resolve(self, token: str) -> Optional[str]:
        """Returns the user_id a still-valid token was issued for, or
        None for an unknown, empty, or expired token. Never raises -
        callers (see server.py) turn None into a 401 themselves."""

        if not token:
            return None

        with self._lock:
            record = self._tokens.get(token)

            if record is None:
                return None

            if _now() > record.expires_at:
                del self._tokens[token]
                return None

            return record.user_id

    def revoke(self, token: str) -> bool:
        with self._lock:
            return self._tokens.pop(token, None) is not None
