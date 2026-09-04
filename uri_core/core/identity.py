"""URI identity: distinct concepts that must never be conflated.

URI Identity - who URI is (purpose, principles, behavioral character).
    Defined by URI_AI_OPERATING_POLICY.md and loaded by
    ModelReasoningGateway (see the policy_path fix accompanying this
    module). Not represented by a Python class here - it is one
    document, the same for every user and every device.

User Identity (UserIdentity / UserIdentityStore below) - a durable
    identifier for a person, independent of any device or session.
    This is deliberately the seed of a future PortableStateStore:
    the storage path and JSON shape are exactly what an export/sync
    layer would read and write later, without changing shape. A
    user_id carries no authentication or authorization meaning by
    itself - it proves nothing about who is asking and grants access
    to nothing. It is only a stable handle that portable state
    (profile, memory, growth, story - none built yet) can eventually
    attach to.

Device Identity (DeviceIdentity / DeviceIdentityStore below) - a
    durable identifier for this local installation only. Never
    portable, never exported, never synced - a fresh install, a
    different machine, or a different device always gets a fresh
    device_id. Excluded from version control (see .gitignore) for
    the same reason credentials.json/token.json are: it identifies
    this machine, not the user.

Session identity (uri_core.core.state.SessionManager, unmodified by
    this module) is a fourth, separate concept again: one
    in-progress conversation, keyed by session_id.

None of user_id, device_id, session_id, or "URI identity" are the
same thing, and none should ever be merged into one identifier.
"""

import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional

SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class UserIdentity:
    user_id: str
    created_at: str
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class DeviceIdentity:
    device_id: str
    created_at: str
    schema_version: str = SCHEMA_VERSION


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_parent_dir(path: str) -> None:
    folder = os.path.dirname(path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)


class UserIdentityStore:
    """Generates and persists a durable, device-independent user_id.

    Backed by a local file today (no server, no sync exist yet), but
    deliberately scoped, named, and shaped as what a future
    PortableStateStore would export/import unchanged.
    """

    def __init__(
        self,
        storage_path: str = "uri_workspace/portable_identity.json",
    ):
        self.storage_path = os.path.normpath(storage_path)

    def load_or_create(self) -> UserIdentity:
        existing = self._load()

        if existing is not None:
            return existing

        identity = UserIdentity(
            user_id=str(uuid.uuid4()),
            created_at=_now(),
        )

        self._save(identity)

        return identity

    def _load(self) -> Optional[UserIdentity]:

        if not os.path.exists(self.storage_path):
            return None

        try:

            with open(
                self.storage_path, "r", encoding="utf-8"
            ) as file:
                data = json.load(file)

            return UserIdentity(
                user_id=data["user_id"],
                created_at=data["created_at"],
                schema_version=data.get(
                    "schema_version", SCHEMA_VERSION
                ),
            )

        except (json.JSONDecodeError, KeyError, OSError, TypeError):
            return None

    def _save(self, identity: UserIdentity) -> None:
        _ensure_parent_dir(self.storage_path)

        with open(self.storage_path, "w", encoding="utf-8") as file:
            json.dump(
                asdict(identity), file, indent=2, ensure_ascii=False
            )


class DeviceIdentityStore:
    """Generates and persists a durable device_id for this
    installation only. Never portable - see module docstring.
    """

    def __init__(
        self,
        storage_path: str = "uri_workspace/device_identity.json",
    ):
        self.storage_path = os.path.normpath(storage_path)

    def load_or_create(self) -> DeviceIdentity:
        existing = self._load()

        if existing is not None:
            return existing

        identity = DeviceIdentity(
            device_id=str(uuid.uuid4()),
            created_at=_now(),
        )

        self._save(identity)

        return identity

    def _load(self) -> Optional[DeviceIdentity]:

        if not os.path.exists(self.storage_path):
            return None

        try:

            with open(
                self.storage_path, "r", encoding="utf-8"
            ) as file:
                data = json.load(file)

            return DeviceIdentity(
                device_id=data["device_id"],
                created_at=data["created_at"],
                schema_version=data.get(
                    "schema_version", SCHEMA_VERSION
                ),
            )

        except (json.JSONDecodeError, KeyError, OSError, TypeError):
            return None

    def _save(self, identity: DeviceIdentity) -> None:
        _ensure_parent_dir(self.storage_path)

        with open(self.storage_path, "w", encoding="utf-8") as file:
            json.dump(
                asdict(identity), file, indent=2, ensure_ascii=False
            )
