"""M22.8 capability modes: narrowing-only capability filters."""

import json
import os
from copy import deepcopy
from typing import Dict, List

from uri_core.core.capability_registry import CapabilityRegistry


MODES_PATH = os.path.join("uri_workspace", "modes.json")
DEFAULT_MODE = "office"
VALID_MODES = {"office", "diagnostic", "admin"}


def _default_registry_ids() -> List[str]:
    return [descriptor.id for descriptor in CapabilityRegistry().list_capabilities()]


# No currently registered capability is solely status/reporting.  Fail closed
# until one is deliberately added instead of misclassifying a general tool.
_REGISTRY_IDS = _default_registry_ids()
DEFAULT_MODES: Dict[str, List[str]] = {
    "office": list(_REGISTRY_IDS),
    "diagnostic": [],
    "admin": list(_REGISTRY_IDS),
}


def _deep_merge(base: dict, override: dict) -> dict:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def load_modes(path: str = MODES_PATH) -> Dict[str, List[str]]:
    """Return defaults deep-merged with an optional safe JSON override."""
    defaults = deepcopy(DEFAULT_MODES)
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            override = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return defaults
    if not isinstance(override, dict):
        return defaults
    merged = _deep_merge(defaults, override)
    return {
        mode: [item for item in merged.get(mode, defaults[mode]) if isinstance(item, str)]
        if isinstance(merged.get(mode, defaults[mode]), list)
        else list(defaults[mode])
        for mode in VALID_MODES
    }
