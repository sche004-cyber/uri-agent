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

M22.2 (see URI_M22_ARCHITECTURE.md sections 2/4/10, finding S4): tokens
are now PERSISTED - a server restart no longer silently logs out every
device, which is required before any mobile/remote client can be
trusted to stay logged in for longer than one process lifetime. Only
the SHA-256 HASH of each token is ever written to disk (see _hash_
token below); the raw token exists only in memory for the instant it
is generated and in the HTTP response that hands it to the client -
identical in spirit to how user_accounts.py never stores a plaintext
password, only a salted hash. A stolen uri_workspace/auth_sessions.json
file therefore cannot be used to authenticate as anyone; at most it
reveals which user_ids/device_ids have sessions and when they expire.

A token is a high-entropy random string (secrets.token_urlsafe), never
derived from user_id/username/password, and expires after
DEFAULT_TOKEN_TTL_SECONDS of being issued - an old token can't be
resurrected to authorize a request far later than the login it came
from, mirroring approval_store.py's own fail-closed expiry discipline.

list_for_user()/revoke_by_ref() (M22.2) exist for exactly one reason:
device management (see devices.py). Revoking "this other device I'm
logged in on" must work from a DIFFERENT client than the one being
revoked, which by definition never had that other session's raw
token - only its device_id, visible via list_for_user(). session_ref
is the storage key (the token's hash) exposed back to its OWNING user
only, purely as an opaque handle to name one session for revocation;
it is not a credential, cannot be used to authenticate, and is
distinct from resolve()'s raw-token contract exactly as file_store.py's
StoredFile.to_reference() is distinct from a real file path.
"""

import hashlib
import json
import os
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

SCHEMA_VERSION = "1.0"

DEFAULT_TOKEN_TTL_SECONDS = 24 * 60 * 60  # 24 hours

_TOKEN_BYTES = 32

DEFAULT_STORAGE_PATH = "uri_workspace/auth_sessions.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_token(token: str) -> str:
    """The only form of a token ever written to disk - see module
    docstring. Deterministic (not salted): a session lookup must be
    able to find its own record by re-hashing the presented token, the
    same way a URL-safe token itself is already unguessable without
    needing a salt."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class _TokenRecord:
    user_id: str
    expires_at: datetime
    device_id: Optional[str] = None


@dataclass(frozen=True)
class SessionInfo:
    """A device-management-safe view of one session: everything devices.py
    needs to list/group/revoke a session, and nothing that could be used
    to authenticate as it. session_ref is documented above - never a
    credential."""

    session_ref: str
    user_id: str
    device_id: Optional[str]
    expires_at: str


class AuthSessionStore:
    """Token -> (user_id, device_id) mapping, persisted as hashed
    records (see module docstring). Thread-safe: FastAPI/uvicorn may
    serve requests from more than one worker thread. Follows this
    codebase's standard store discipline - schema-versioned JSON, safe
    degrade-to-empty on a corrupted file - exactly like every other
    store in uri_core/core."""

    def __init__(
        self,
        ttl_seconds: int = DEFAULT_TOKEN_TTL_SECONDS,
        storage_path: str = DEFAULT_STORAGE_PATH,
    ):
        self._ttl_seconds = ttl_seconds
        self.storage_path = os.path.normpath(storage_path)
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
            records = self._load()
            records[_hash_token(token)] = record
            self._save(records)

        return token

    def _get_valid_record(self, token: str) -> Optional[_TokenRecord]:
        if not token:
            return None

        with self._lock:
            records = self._load()
            record = records.get(_hash_token(token))

            if record is None:
                return None

            if _now() > record.expires_at:
                del records[_hash_token(token)]
                self._save(records)
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
        if not token:
            return False

        with self._lock:
            records = self._load()
            removed = records.pop(_hash_token(token), None) is not None
            if removed:
                self._save(records)
            return removed

    def revoke_by_ref(self, session_ref: str) -> bool:
        """Revokes a session by its session_ref (see SessionInfo/module
        docstring) rather than its raw token - the only way to revoke a
        session from a DIFFERENT client than the one holding it. Never
        accepts anything else as a substitute for a real, currently
        valid session_ref: an unknown ref returns False exactly like an
        unknown raw token does in revoke() above."""

        if not session_ref:
            return False

        with self._lock:
            records = self._load()
            removed = records.pop(session_ref, None) is not None
            if removed:
                self._save(records)
            return removed

    def list_for_user(self, user_id: str) -> List[SessionInfo]:
        """Every still-valid session belonging to user_id - the read
        side of device management (see devices.py). Expired sessions
        are dropped as a side effect, exactly like _get_valid_record
        already does for a single lookup."""

        with self._lock:
            records = self._load()
            now = _now()
            live = {
                ref: record
                for ref, record in records.items()
                if record.expires_at >= now
            }
            if len(live) != len(records):
                self._save(live)

            return [
                SessionInfo(
                    session_ref=ref,
                    user_id=record.user_id,
                    device_id=record.device_id,
                    expires_at=record.expires_at.isoformat(),
                )
                for ref, record in live.items()
                if record.user_id == user_id
            ]

    # ----------------------------------------------------------
    # Persistence
    # ----------------------------------------------------------

    def _load(self) -> Dict[str, _TokenRecord]:

        if not os.path.exists(self.storage_path):
            return {}

        try:
            with open(self.storage_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            records = {}

            for token_hash, raw in data.get("sessions", {}).items():
                records[token_hash] = _TokenRecord(
                    user_id=raw["user_id"],
                    expires_at=datetime.fromisoformat(raw["expires_at"]),
                    device_id=raw.get("device_id"),
                )

            return records

        except (
            json.JSONDecodeError,
            KeyError,
            OSError,
            TypeError,
            ValueError,
        ):
            return {}

    def _save(self, records: Dict[str, _TokenRecord]) -> None:
        folder = os.path.dirname(self.storage_path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

        data = {
            "schema_version": SCHEMA_VERSION,
            "sessions": {
                token_hash: {
                    "user_id": record.user_id,
                    "expires_at": record.expires_at.isoformat(),
                    "device_id": record.device_id,
                }
                for token_hash, record in records.items()
            },
        }

        with open(self.storage_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
