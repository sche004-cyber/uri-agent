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

M22.2 (see URI_M22_ARCHITECTURE.md section 4): adds two orthogonal,
deliberately-separate fields alongside the account itself -

    role            USER | ADMIN - a PRIVILEGE. Never self-assigned:
                    the very first account created on a fresh install
                    becomes ADMIN (see _next_role below); every
                    subsequent signup is USER. Nothing in this module
                    or anywhere reachable from it lets a caller pick
                    their own role.
    experience_tier BASIC | ADVANCED - a PREFERENCE. Purely how much
                    configuration UI a client shows this user; it
                    carries zero authority and must never be read by
                    any authorization decision anywhere in this
                    codebase - see test_experience_tier_never_
                    authorizes.py, which enforces that as a structural
                    invariant, not a convention.

status (active | suspended) is also new, reserved for a future
milestone's account-suspension flow; every account defaults to
"active" and nothing yet sets it to "suspended".

Pre-M22.2 accounts (schema_version "1.0", no role/experience_tier/
status fields at all in the stored JSON) are migrated automatically,
purely and deterministically, inside _load() below - see its
docstring. This is read-time migration, not a separate startup script:
because _load() already loads every account in the file at once, it
can correctly apply the "earliest created_at among the accounts that
still lack a role becomes ADMIN" rule without any extra bookkeeping,
and the very next write through this store (e.g. any signup or
set_experience_tier call) persists the computed values, exactly once,
as an ordinary side effect of _save() writing the full in-memory set
back to disk.
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

from uri_core.config.modes import DEFAULT_MODE, VALID_MODES

SCHEMA_VERSION = "2.0"

_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 256

_PBKDF2_ALGORITHM = "sha256"
_PBKDF2_ITERATIONS = 260_000
_SALT_BYTES = 16

# Privilege - see the module docstring above. Never confuse with
# EXPERIENCE_TIER_* below; the two must never be compared or branched
# on interchangeably.
ROLE_USER = "USER"
ROLE_ADMIN = "ADMIN"
VALID_ROLES = frozenset({ROLE_USER, ROLE_ADMIN})

# Preference - zero authority. See the module docstring above.
EXPERIENCE_TIER_BASIC = "BASIC"
EXPERIENCE_TIER_ADVANCED = "ADVANCED"
VALID_EXPERIENCE_TIERS = frozenset(
    {EXPERIENCE_TIER_BASIC, EXPERIENCE_TIER_ADVANCED}
)

STATUS_ACTIVE = "active"
STATUS_SUSPENDED = "suspended"
VALID_STATUSES = frozenset({STATUS_ACTIVE, STATUS_SUSPENDED})


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
    role: str = ROLE_USER
    experience_tier: str = EXPERIENCE_TIER_BASIC
    mode: str = DEFAULT_MODE
    status: str = STATUS_ACTIVE
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

        # Bootstrap (see module docstring): ADMIN is never self-selected
        # by a signup payload - it is assigned here, deterministically,
        # based only on whether an ADMIN already exists among the
        # accounts this store already knows about (which, thanks to
        # _load()'s own migration, always correctly reflects a
        # pre-M22.2 install's earliest account too). A fresh install's
        # very first signup is the only account that can ever receive
        # ADMIN this way.
        role = (
            ROLE_USER
            if any(
                existing.role == ROLE_ADMIN
                for existing in accounts.values()
            )
            else ROLE_ADMIN
        )

        account = UserAccount(
            user_id=str(uuid.uuid4()),
            username=username,
            password_salt=salt,
            password_hash=_hash_password(password, salt),
            created_at=_now(),
            role=role,
        )

        accounts[account.user_id] = account
        self._save(accounts)

        return account

    def set_experience_tier(
        self, user_id: str, experience_tier: str
    ) -> Optional[UserAccount]:
        """Updates ONLY the calling account's own experience_tier - a
        zero-authority preference (see module docstring). Callers (see
        server.py's POST /auth/experience-tier) must resolve user_id
        from the caller's own authenticated token, never from a
        request body, so this can never be used to change another
        account's tier. Returns the updated UserAccount, or None if
        user_id is not a known account. Raises UserAccountError for an
        invalid tier value - never silently coerces or ignores it."""

        if experience_tier not in VALID_EXPERIENCE_TIERS:
            raise UserAccountError(
                f"experience_tier must be one of "
                f"{sorted(VALID_EXPERIENCE_TIERS)}, got "
                f"{experience_tier!r}."
            )

        accounts = self._load()
        existing = accounts.get(user_id)

        if existing is None:
            return None

        updated = UserAccount(
            user_id=existing.user_id,
            username=existing.username,
            password_salt=existing.password_salt,
            password_hash=existing.password_hash,
            created_at=existing.created_at,
            role=existing.role,
            experience_tier=experience_tier,
            status=existing.status,
        )

        accounts[user_id] = updated
        self._save(accounts)

        return updated

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

    def set_mode(self, user_id: str, mode: str) -> Optional[UserAccount]:
        """Update the authenticated caller's own stored capability mode."""
        if mode not in VALID_MODES:
            raise UserAccountError(f"mode must be one of {sorted(VALID_MODES)}, got {mode!r}.")
        accounts = self._load()
        existing = accounts.get(user_id)
        if existing is None:
            return None
        updated = UserAccount(
            user_id=existing.user_id, username=existing.username,
            password_salt=existing.password_salt, password_hash=existing.password_hash,
            created_at=existing.created_at, role=existing.role,
            experience_tier=existing.experience_tier, mode=mode,
            status=existing.status, schema_version=existing.schema_version,
        )
        accounts[user_id] = updated
        self._save(accounts)
        return updated

    def get_by_user_id(self, user_id: str) -> Optional[UserAccount]:
        return self._load().get(user_id)

    def _load(self) -> dict:
        """Loads every account, defaulting fields a pre-M22.2 file
        never had. experience_tier/status default independently per
        record (a zero-authority preference and an unused-so-far
        status both default safely regardless of any other account) -
        role does not, because "does this account get ADMIN" is a
        property of the WHOLE file, not of one record in isolation.

        role migration: any record whose raw JSON has no "role" key at
        all (definitively pre-M22.2) is left unassigned during the
        first pass below; once every record is read, the one such
        record with the earliest created_at becomes ADMIN and every
        other becomes USER - see the module docstring for why this is
        safe to recompute on every _load() rather than needing a
        dedicated migration step. A record that already has a
        persisted role (anything created via create_account, on any
        version of this store) always keeps it untouched."""

        if not os.path.exists(self.storage_path):
            return {}

        try:
            with open(self.storage_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            accounts = {}
            unassigned_role_ids = []

            for raw in data.get("accounts", []):
                persisted_role = raw.get("role")

                account = UserAccount(
                    user_id=raw["user_id"],
                    username=raw["username"],
                    password_salt=raw["password_salt"],
                    password_hash=raw["password_hash"],
                    created_at=raw.get("created_at", ""),
                    role=(
                        persisted_role
                        if persisted_role in VALID_ROLES
                        else ROLE_USER
                    ),
                    experience_tier=raw.get(
                        "experience_tier", EXPERIENCE_TIER_BASIC
                    ),
                    mode=raw.get("mode") if raw.get("mode") in VALID_MODES else DEFAULT_MODE,
                    status=raw.get("status", STATUS_ACTIVE),
                    schema_version=raw.get(
                        "schema_version", SCHEMA_VERSION
                    ),
                )
                accounts[account.user_id] = account

                if persisted_role not in VALID_ROLES:
                    unassigned_role_ids.append(account.user_id)

            if unassigned_role_ids:
                earliest_id = min(
                    unassigned_role_ids,
                    key=lambda uid: accounts[uid].created_at,
                )
                # Every other unassigned record already defaulted to
                # ROLE_USER in the pass above - only the earliest one
                # needs to be promoted to ADMIN here.
                earliest = accounts[earliest_id]
                accounts[earliest_id] = UserAccount(
                    user_id=earliest.user_id,
                    username=earliest.username,
                    password_salt=earliest.password_salt,
                    password_hash=earliest.password_hash,
                    created_at=earliest.created_at,
                    role=ROLE_ADMIN,
                    experience_tier=earliest.experience_tier,
                    mode=earliest.mode,
                    status=earliest.status,
                    schema_version=earliest.schema_version,
                )

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
