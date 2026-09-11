"""M23: the extensible entity/relationship type registry for URI's
Graph Intelligence subsystem (see docs/plans/M23_GRAPH_INTELLIGENCE_PLAN.md
section 6).

Deliberately NOT a closed enum - this module owns only the *packaged*
default type sets. GraphStore (uri_core.core.graph_store) validates a
submitted type string against PACKAGED_ENTITY_TYPES/
PACKAGED_RELATIONSHIP_TYPES union'd with whatever this module's
register_*() functions have additionally persisted, so a genuinely new,
well-formed type (e.g. a future domain's "Vendor") can be registered
without editing this file or redeploying. A type is rejected only when
it is empty, non-string, or credential-shaped - never merely because it
is unfamiliar (see is_valid_entity_type/is_valid_relationship_type).

Deliberately domain-general: nothing here (or in graph_store.py) names
any specific institution. Student/Department/Hostel are the same
domain-general educational-institution concepts already named in this
milestone's own accepted plan, not a hard-coded reference to any one
school.

Same install-scope, JSON-persisted extension pattern as
capability_grants.json (see capability_resolver.py) - one small file,
loaded fresh on every read, atomically replaced on every write.
"""

from __future__ import annotations

import json
import os
import threading
from typing import Set

from uri_core.core.security_guards import looks_like_credential_value

PACKAGED_ENTITY_TYPES: Set[str] = {
    "User",
    "Person",
    "Organization",
    "Student",
    "Department",
    "Hostel",
    "Document",
    "File",
    "Email",
    "Fact",
    "Memory",
    "Decision",
    "Rule",
    "Event",
    "Task",
    "Capability",
    "Source",
}

PACKAGED_RELATIONSHIP_TYPES: Set[str] = {
    "MENTIONS",
    "RELATED_TO",
    "BELONGS_TO",
    "SUPPORTED_BY",
    "DERIVED_FROM",
    "SUPERSEDES",
    "CONTRADICTS",
    "AFFECTS",
    "DEPENDS_ON",
    "CREATED_BY",
    "APPROVED_BY",
    "USES_CAPABILITY",
    "LOCATED_IN",
}

DEFAULT_EXTENSIONS_PATH = "uri_workspace/graph_type_extensions.json"

_MAX_TYPE_LENGTH = 64


class GraphTypeValidationError(ValueError):
    """Raised when a type name is empty, non-string, too long, or
    credential-shaped - never merely because it is unfamiliar."""


def _load_extensions(storage_path: str) -> dict:
    if not os.path.isfile(storage_path):
        return {"entity_types": [], "relationship_types": []}
    try:
        with open(storage_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {
                "entity_types": [
                    str(t) for t in data.get("entity_types", []) if isinstance(t, str)
                ],
                "relationship_types": [
                    str(t) for t in data.get("relationship_types", []) if isinstance(t, str)
                ],
            }
    except Exception:
        return {"entity_types": [], "relationship_types": []}
    return {"entity_types": [], "relationship_types": []}


def _save_extensions(storage_path: str, data: dict) -> None:
    dir_name = os.path.dirname(storage_path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)
    temp_path = f"{storage_path}.tmp.{os.getpid()}"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    if os.path.exists(storage_path):
        os.replace(temp_path, storage_path)
    else:
        os.rename(temp_path, storage_path)


class GraphTypeRegistry:
    """One install-scope store of additionally-registered entity/
    relationship type names, layered on top of the packaged defaults
    above. Not per-user - the type vocabulary (unlike the graph data
    itself) is shared configuration, the same way CapabilityRegistry's
    catalogue is shared while capability_grants.json's per-user grants
    are not."""

    def __init__(self, storage_path: str = DEFAULT_EXTENSIONS_PATH):
        self.storage_path = os.path.normpath(storage_path)
        self._lock = threading.Lock()

    def _validate_type_name(self, type_name: str) -> None:
        if not isinstance(type_name, str) or not type_name.strip():
            raise GraphTypeValidationError(
                "Type name must be a non-empty string."
            )
        if len(type_name) > _MAX_TYPE_LENGTH:
            raise GraphTypeValidationError(
                f"Type name exceeds {_MAX_TYPE_LENGTH} characters."
            )
        if looks_like_credential_value(type_name):
            raise GraphTypeValidationError(
                "Type name looks like a credential and is not permitted."
            )

    def register_entity_type(self, type_name: str) -> None:
        self._validate_type_name(type_name)
        with self._lock:
            data = _load_extensions(self.storage_path)
            if type_name not in data["entity_types"]:
                data["entity_types"].append(type_name)
                _save_extensions(self.storage_path, data)

    def register_relationship_type(self, type_name: str) -> None:
        self._validate_type_name(type_name)
        with self._lock:
            data = _load_extensions(self.storage_path)
            if type_name not in data["relationship_types"]:
                data["relationship_types"].append(type_name)
                _save_extensions(self.storage_path, data)

    def known_entity_types(self) -> Set[str]:
        with self._lock:
            data = _load_extensions(self.storage_path)
        return PACKAGED_ENTITY_TYPES | set(data["entity_types"])

    def known_relationship_types(self) -> Set[str]:
        with self._lock:
            data = _load_extensions(self.storage_path)
        return PACKAGED_RELATIONSHIP_TYPES | set(data["relationship_types"])


_shared_type_registry = GraphTypeRegistry()


def is_valid_entity_type(type_name: str, registry: "GraphTypeRegistry" = None) -> bool:
    """True for any packaged or registered entity type name. False only
    for an empty/non-string/credential-shaped value - an unfamiliar but
    well-formed name is accepted (a caller that wants strict enforcement
    should register the type first via register_entity_type)."""
    reg = registry or _shared_type_registry
    if not isinstance(type_name, str) or not type_name.strip():
        return False
    if looks_like_credential_value(type_name):
        return False
    return True


def is_valid_relationship_type(type_name: str, registry: "GraphTypeRegistry" = None) -> bool:
    if not isinstance(type_name, str) or not type_name.strip():
        return False
    if looks_like_credential_value(type_name):
        return False
    return True
