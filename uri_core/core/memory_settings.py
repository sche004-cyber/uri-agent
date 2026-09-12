"""Per-user, JSON-persisted Memory & Context preferences.

These are presentation and context-budget preferences only.  They neither
grant authority nor alter the consent filter used by personalization_context.
"""

import json
import os
from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class MemorySettings:
    persistent_memory: bool = True
    user_profile: bool = True
    memory_budget: int = 1200
    profile_budget: int = 400
    memory_provider: str = "builtin"
    context_engine: str = "compressor"
    auto_compression: bool = True
    compression_threshold: int = 6000
    compression_target: int = 3000
    protected_recent_messages: int = 6


_FIELDS = set(MemorySettings.__dataclass_fields__)
_INTEGER_FIELDS = {
    "memory_budget", "profile_budget", "compression_threshold",
    "compression_target", "protected_recent_messages",
}


class MemorySettingsValidationError(ValueError):
    pass


class MemorySettingsStore:
    def __init__(self, storage_path: str = "uri_workspace/memory_settings.json"):
        self.storage_path = os.path.normpath(storage_path)

    def load(self) -> MemorySettings:
        try:
            with open(self.storage_path, encoding="utf-8") as handle:
                raw = json.load(handle)
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            raw = {}
        if not isinstance(raw, dict):
            raw = {}
        allowed = {key: value for key, value in raw.items() if key in _FIELDS}
        try:
            return MemorySettings(**allowed)
        except TypeError:
            return MemorySettings()

    def update(self, values: Dict[str, Any]) -> MemorySettings:
        unknown = set(values) - _FIELDS
        if unknown:
            raise MemorySettingsValidationError("Unknown memory settings field.")
        merged = asdict(self.load())
        merged.update(values)
        for field in _INTEGER_FIELDS:
            value = merged[field]
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise MemorySettingsValidationError(f"{field} must be a non-negative integer.")
        if merged["memory_provider"] != "builtin":
            raise MemorySettingsValidationError("Only the built-in memory provider is available.")
        if merged["context_engine"] != "compressor":
            raise MemorySettingsValidationError("Only the compressor context engine is available.")
        if merged["compression_target"] > merged["compression_threshold"]:
            raise MemorySettingsValidationError("compression_target cannot exceed compression_threshold.")
        settings = MemorySettings(**merged)
        folder = os.path.dirname(self.storage_path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        temporary = self.storage_path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(asdict(settings), handle, indent=2)
        os.replace(temporary, self.storage_path)
        return settings
