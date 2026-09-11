"""M22.4: Per-user capability resolution and grant management.

Enforces:
    resolved = registry_capabilities ∩ user_grants[principal.user_id]
               ∩ mode_allowlist[principal.mode] ∩ node_scope[principal.node_id]

Where:
- registry_capabilities is the ceiling (what URI can actually execute).
- user_grants can only narrow (least privilege: resolved ⊆ granted ⊆ registered).
- mode_allowlist and node_scope are identity/universal sets in M22.4 (future seams).
- Zero-behaviour-change migration: if a user_id has no stored grant record,
  it defaults to the full current registry.
- Role is completely separate: ADMIN status never expands capability grants.
- Brain proposals never write to capability_grants.json.

Boundary Guarantee: Pure, testable functions with no FastAPI/HTTP dependency.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from uri_core.core.capability_registry import CapabilityDescriptor, CapabilityRegistry
from uri_core.core.principal_context import PrincipalContext
from uri_core.config.modes import DEFAULT_MODE, load_modes


DEFAULT_GRANTS_PATH = "uri_workspace/capability_grants.json"


class CapabilityGrantsStore:
    """Persistent storage for per-user capability grants (INSTALL-scope).

    Storage format:
    {
        "schema_version": 1,
        "grants": {
            "<user_id>": ["<capability_id>", ...]
        }
    }

    Two writers only:
    1. Initial/migration bootstrap (implicit fallback or explicit seeding).
    2. PUT /admin/users/{user_id}/grants (ADMIN-authenticated).
    No Brain-proposed tool call or execution path ever touches this store.
    """

    def __init__(self, storage_path: str = DEFAULT_GRANTS_PATH):
        self.storage_path = os.path.normpath(storage_path)
        self._lock = threading.Lock()

    def _load(self) -> Dict[str, List[str]]:
        """Load grants dictionary mapping user_id -> list of capability_ids.
        Degrades safely to empty dictionary on missing/corrupted file.
        """
        if not os.path.isfile(self.storage_path):
            return {}

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                grants = data.get("grants", {})
                if isinstance(grants, dict):
                    return {
                        str(uid): [str(cid) for cid in cids if isinstance(cid, (str, int))]
                        for uid, cids in grants.items()
                        if isinstance(cids, list)
                    }
        except Exception:
            return {}
        return {}

    def _save(self, grants: Dict[str, List[str]]) -> None:
        """Persist grants atomically."""
        dir_name = os.path.dirname(self.storage_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)

        data = {
            "schema_version": 1,
            "grants": grants,
        }
        temp_path = f"{self.storage_path}.tmp.{os.getpid()}"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        
        # Replace atomically
        if os.path.exists(self.storage_path):
            os.replace(temp_path, self.storage_path)
        else:
            os.rename(temp_path, self.storage_path)

    def has_user_record(self, user_id: str) -> bool:
        """Check if a user explicitly has a grant record on disk."""
        with self._lock:
            grants = self._load()
            return user_id in grants

    def get_grants(
        self,
        user_id: Optional[str],
        registry_ceiling_ids: Optional[Set[str]] = None,
    ) -> Set[str]:
        """Return granted capability IDs for a user.

        Migration invariant:
        If an authenticated user has no persisted grant record, default to
        the full current registry ceiling (zero-behaviour-change migration default).
        If no user_id is provided (anonymous / unauthenticated caller), fail closed (empty set).
        """
        if not user_id:
            return set()

        with self._lock:
            grants = self._load()
            if user_id in grants:
                # User has an explicit record: use their specific grants
                user_grant_set = set(grants[user_id])
                if registry_ceiling_ids is not None:
                    # Enforce granted ⊆ registered ceiling
                    return user_grant_set & registry_ceiling_ids
                return user_grant_set

        # Not found in store: migration default applies (full current registry)
        if registry_ceiling_ids is not None:
            return set(registry_ceiling_ids)
        return set()

    def set_grants(
        self,
        user_id: str,
        granted_ids: List[str],
        valid_registry_ids: Set[str],
    ) -> Set[str]:
        """Replace a user's grant set.

        Validates all IDs against valid_registry_ids. Rejects unknown IDs
        with ValueError (never partially applies).
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string.")

        # Reject unknown IDs
        unknown = [cid for cid in granted_ids if cid not in valid_registry_ids]
        if unknown:
            raise ValueError(f"Unknown capability ID(s): {unknown}")

        # Canonical deduplicated list
        deduped = sorted(list(set(granted_ids)))

        with self._lock:
            grants = self._load()
            grants[user_id] = deduped
            self._save(grants)

        return set(deduped)

    def list_all_user_grants(self) -> Dict[str, List[str]]:
        """Return a copy of all explicit user grants."""
        with self._lock:
            return self._load()


# Shared ambient instance
_shared_grants_store = CapabilityGrantsStore()


class CapabilityResolver:
    """Pure resolver computing the intersection of registry, grants, mode, and node."""

    @staticmethod
    def resolve(
        principal: Optional[PrincipalContext] = None,
        capability_registry: Optional[CapabilityRegistry] = None,
        grants_store: Optional[CapabilityGrantsStore] = None,
    ) -> List[CapabilityDescriptor]:
        """Resolve the executable/permitted capabilities for a principal.

        Formula:
            resolved = registry_capabilities ∩ user_grants[principal.user_id]
                       ∩ mode_allowlist[principal.mode] ∩ node_scope[principal.node_id]

        In M22.4:
        - mode_allowlist and node_scope are identity terms (universal set).
        - Least privilege is maintained: resolved subset-of granted subset-of registered.
        - principal.role is never inspected.
        """
        reg = capability_registry or CapabilityRegistry()
        store = grants_store or _shared_grants_store

        all_descriptors = reg.list_capabilities()
        registry_ids = {d.id for d in all_descriptors}

        user_id = principal.user_id if principal else None
        user_grants = store.get_grants(user_id, registry_ceiling_ids=registry_ids)

        # Intersection: registry_capabilities ∩ user_grants
        modes = load_modes()
        mode = principal.mode if principal and principal.mode else DEFAULT_MODE
        mode_allowed_ids = set(modes.get(mode, modes[DEFAULT_MODE]))
        allowed_ids = registry_ids & user_grants & mode_allowed_ids

        # Return descriptors in registry order
        return [d for d in all_descriptors if d.id in allowed_ids]

    @staticmethod
    def is_allowed(
        capability_id: str,
        principal: Optional[PrincipalContext] = None,
        capability_registry: Optional[CapabilityRegistry] = None,
        grants_store: Optional[CapabilityGrantsStore] = None,
    ) -> bool:
        """Authoritative check: is capability_id permitted for this principal?

        Authoritative consultation point: called by ApprovalGate.execute_tool
        immediately before executing or checking status.
        """
        if not capability_id:
            return False

        reg = capability_registry or CapabilityRegistry()
        store = grants_store or _shared_grants_store

        descriptor = reg.describe_status(capability_id)
        if descriptor is None:
            return False

        user_id = principal.user_id if principal else None
        if not user_id:
            return False

        registry_ids = {d.id for d in reg.list_capabilities()}
        user_grants = store.get_grants(user_id, registry_ceiling_ids=registry_ids)
        modes = load_modes()
        mode = principal.mode if principal and principal.mode else DEFAULT_MODE
        mode_allowed_ids = set(modes.get(mode, modes[DEFAULT_MODE]))
        allowed_ids = registry_ids & user_grants & mode_allowed_ids
        return capability_id in allowed_ids
