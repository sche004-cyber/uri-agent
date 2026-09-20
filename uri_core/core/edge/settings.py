"""Caller-scoped, versioned Edge routing preferences; never credentials."""
from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from uri_core.core.portable_paths import user_scoped_path
from .runtime_inventory import EdgeRuntimeInventory

SCHEMA_VERSION = "1.0"
VALID_INTELLIGENCE_MODES = frozenset({"EDGE_ONLY", "HYBRID", "MAIN_BRAIN_PREFERRED"})
_settings_lock = threading.RLock()


class EdgeSettingsValidationError(ValueError): pass
class EdgeSettingsConflictError(RuntimeError): pass


@dataclass(frozen=True)
class EdgeSettings:
    schema_version: str = SCHEMA_VERSION
    revision: int = 0
    updated_at: str = ""
    enabled: bool = True
    intelligence_mode: str = "HYBRID"
    reply_confidence_threshold_percent: int = 90
    edge: Dict[str, Optional[str]] = field(default_factory=lambda: {"runtime_id": None, "model_id": None})
    vision: Dict[str, Any] = field(default_factory=lambda: {"provider_id": None, "model_id": None, "enabled": False})
    speech: Dict[str, Any] = field(default_factory=lambda: {"provider_id": None, "model_id": None, "enabled": False})
    assistance: Dict[str, Any] = field(default_factory=lambda: {"enabled": False, "default_deadline_ms": 800})


class EdgeSettingsStore:
    def __init__(self, user_id: str, *, root: str = "uri_workspace/users") -> None:
        self.user_id = user_id
        self.path = user_scoped_path(user_id, "edge_intelligence.json", root=root)

    def _read_raw(self) -> Dict[str, Any]:
        try:
            with open(self.path, encoding="utf-8") as handle:
                raw = json.load(handle)
        except FileNotFoundError:
            return {}
        except (OSError, json.JSONDecodeError) as exc:
            raise EdgeSettingsValidationError("edge settings storage is unreadable") from exc
        if not isinstance(raw, dict):
            raise EdgeSettingsValidationError("edge settings document must be an object")
        return raw

    def _validate(self, raw: Dict[str, Any]) -> EdgeSettings:
        allowed = set(EdgeSettings.__dataclass_fields__)
        unknown = set(raw) - allowed
        if unknown:
            raise EdgeSettingsValidationError("unknown edge settings field")
        merged = asdict(EdgeSettings())
        merged.update(raw)
        if merged["schema_version"] != SCHEMA_VERSION:
            raise EdgeSettingsValidationError("unsupported edge settings schema version")
        if type(merged["revision"]) is not int or merged["revision"] < 0:
            raise EdgeSettingsValidationError("revision must be a non-negative integer")
        if type(merged["enabled"]) is not bool:
            raise EdgeSettingsValidationError("enabled must be boolean")
        if merged["intelligence_mode"] not in VALID_INTELLIGENCE_MODES:
            raise EdgeSettingsValidationError("invalid intelligence_mode")
        threshold = merged["reply_confidence_threshold_percent"]
        if type(threshold) is not int or not 0 <= threshold <= 100:
            raise EdgeSettingsValidationError("reply_confidence_threshold_percent must be an integer from 0 through 100")
        edge = merged["edge"]
        if not isinstance(edge, dict) or set(edge) != {"runtime_id", "model_id"}:
            raise EdgeSettingsValidationError("edge must contain only runtime_id and model_id")
        if (edge["runtime_id"] is None) != (edge["model_id"] is None):
            raise EdgeSettingsValidationError("edge runtime_id and model_id must be supplied together")
        for modality in ("vision", "speech"):
            value = merged[modality]
            if not isinstance(value, dict) or set(value) != {"provider_id", "model_id", "enabled"} or type(value["enabled"]) is not bool:
                raise EdgeSettingsValidationError(f"invalid {modality} settings")
        assistance = merged["assistance"]
        if not isinstance(assistance, dict) or set(assistance) != {"enabled", "default_deadline_ms"} or type(assistance["enabled"]) is not bool or type(assistance["default_deadline_ms"]) is not int or assistance["default_deadline_ms"] <= 0:
            raise EdgeSettingsValidationError("invalid assistance settings")
        return EdgeSettings(**merged)

    def load(self) -> EdgeSettings:
        return self._validate(self._read_raw())

    def update(self, values: Dict[str, Any], *, expected_revision: int, inventory: EdgeRuntimeInventory) -> EdgeSettings:
        if type(expected_revision) is not int or expected_revision < 0:
            raise EdgeSettingsValidationError("revision is required")
        if not isinstance(values, dict):
            raise EdgeSettingsValidationError("settings update must be an object")
        # A model has no path into this method; callers must be authenticated HTTP/UI code.
        with _settings_lock:
            current = self.load()
            if current.revision != expected_revision:
                raise EdgeSettingsConflictError("edge settings revision is stale")
            merged = asdict(current)
            merged.update(values)
            merged["revision"] = current.revision + 1
            merged["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            candidate = self._validate(merged)
            inventory.validate_selection(candidate.edge["runtime_id"], candidate.edge["model_id"])
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(asdict(candidate), handle, sort_keys=True, ensure_ascii=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, self.path)
            return candidate
