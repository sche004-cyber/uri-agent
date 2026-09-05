"""Prototype 1 — local login accounts.

This is deliberately the smallest safe mechanism that proves multi-user
isolation, not a production authentication system. No OAuth, no Gmail/
GitHub sign-in, no session cookies, no password-reset flow - all of
that is explicitly out of scope for this milestone (see
URI_MILESTONE_TRACKER.md).

What "safe" means here, concretely:
    - Passwords are never stored or logged in plaintext. Each account
      stores only a per-account random salt and a PBKDF2-HMAC-SHA256
      hash of (salt + password), verified with a constant-time
      comparison (hmac.compare_digest) so verification time doesn't
      leak how much of the hash matched.
    - A username is looked up case-insensitively but stored with its
      original casing for display; usernames are restricted to a
      small safe charset so they can never be mistaken for a
      filesystem path component (mirrors portable_paths.py's own
      strict-validation discipline for user_id).
    - account_id (this account's user_id) is a fresh uuid4, completely
      independent of identity.py's UserIdentityStore (the single
      ambient per-install identity that predates login). Login is what
      finally answers "which user_id" for a request; identity.py's
      device_id concept is untouched and stays local-only, per its own
      module docstring's user_id/device_id distinction.

This store is intentionally ambient/global (one accounts file for the
whole install, like capabilities_registry.json) - it is the directory
of who can log in, not per-user state itself. Per-user state
(profile/memory/growth/sessions/approvals) lives under
uri_workspace/users/<user_id>/, keyed by the user_id an account maps
to, exactly as portable_paths.py already establishes.
"""

import hashlib
import hmac
import json
import os
import re
import secrets
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional

SCHEMA_VERSION = "1.0"

_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 256

_PBKDF2_ALGORITHM = "sha256"
_PBKDF2_ITERATIONS = 260_000
_SALT_BYTES = 16


class UserAccountError(ValueError):
    """Raised for any account-creation or credential-shape failure."""


class UsernameTakenError(UserAccountError):
    """Raised when signup is attempted for an already-registered
    username (case-insensitive)."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_parent_dir(path: str) -> None:
    folder = os.path.dirname(path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)


def _validate_username(username: str) -> None:
    if not isinstance(username, str) or not _USERNAME_PATTERN.match(username):
        raise UserAccountError(
            "Username must be 3-32 characters and contain only letters, "
            "digits, '.', '_', or '-'."
        )


def _validate_password(password: str) -> None:
    if not isinstance(password, str):
        raise UserAccountError("Password must be a string.")

    if len(password) < MIN_PASSWORD_LENGTH:
        raise UserAccountError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )

    if len(password) > MAX_PASSWORD_LENGTH:
        raise UserAccountError(
            f"Password exceeds {MAX_PASSWORD_LENGTH} characters."
        )


def _hash_password(password: str, salt: str) -> str:
    derived = hashlib.pbkdf2_hmac(
        _PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        bytes.fromhex(salt),
        _PBKDF2_ITERATIONS,
    )
    return derived.hex()


@dataclass(frozen=True)
class UserAccount:
    user_id: str
    username: str
    password_salt: str
    password_hash: str
    created_at: str
    schema_version: str = SCHEMA_VERSION


class UserAccountStore:
    """Loads and saves the install's login directory (username ->
    account). Follows every other store in this codebase's exact
    persistence pattern (JSON file, schema_version, safe degrade to
    empty on a corrupted file)."""

    def __init__(
        self, storage_path: str = "uri_workspace/user_accounts.json"
    ):
        self.storage_path = os.path.normpath(storage_path)

    def create_account(self, username: str, password: str) -> UserAccount:
        _validate_username(username)
        _validate_password(password)

        accounts = self._load()

        for existing in accounts.values():
            if existing.username.lower() == username.lower():
                raise UsernameTakenError(
                    f"Username {username!r} is already registered."
                )

        salt = secrets.token_hex(_SALT_BYTES)

        account = UserAccount(
            user_id=str(uuid.uuid4()),
            username=username,
            password_salt=salt,
            password_hash=_hash_password(password, salt),
            created_at=_now(),
        )

        accounts[account.user_id] = account
        self._save(accounts)

        return account

    def authenticate(
        self, username: str, password: str
    ) -> Optional[UserAccount]:
        """Returns the matching UserAccount only on an exact username +
        password match; returns None for any other reason (unknown
        username, wrong password) without distinguishing which, so a
        caller can never use this to enumerate valid usernames."""

        if not isinstance(username, str) or not isinstance(password, str):
            return None

        accounts = self._load()

        for account in accounts.values():
            if account.username.lower() != username.lower():
                continue

            candidate_hash = _hash_password(password, account.password_salt)

            if hmac.compare_digest(candidate_hash, account.password_hash):
                return account

            return None

        return None

    def get_by_user_id(self, user_id: str) -> Optional[UserAccount]:
        return self._load().get(user_id)

    def _load(self) -> dict:
        if not os.path.exists(self.storage_path):
            return {}

        try:
            with open(self.storage_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            accounts = {}

            for raw in data.get("accounts", []):
                account = UserAccount(
                    user_id=raw["user_id"],
                    username=raw["username"],
                    password_salt=raw["password_salt"],
                    password_hash=raw["password_hash"],
                    created_at=raw.get("created_at", ""),
                    schema_version=raw.get(
                        "schema_version", SCHEMA_VERSION
                    ),
                )
                accounts[account.user_id] = account

            return accounts

        except (json.JSONDecodeError, KeyError, OSError, TypeError):
            return {}

    def _save(self, accounts: dict) -> None:
        _ensure_parent_dir(self.storage_path)

        data = {
            "schema_version": SCHEMA_VERSION,
            "accounts": [asdict(account) for account in accounts.values()],
        }

        with open(self.storage_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
