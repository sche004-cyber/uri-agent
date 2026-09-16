"""Durable, user-scoped fallback preferences for direct model providers."""
import json
import os
from typing import Any, Dict

from uri_core.core.portable_paths import user_scoped_path


class FallbackRoutingStore:
    """Stores only validated provider/model references, never credentials."""
    _FILENAME = "fallback_routing.json"
    _EMPTY = {"primary": None, "fallback_1": None, "fallback_2": None}

    def __init__(self, user_id: str) -> None:
        self._path = user_scoped_path(user_id, self._FILENAME)

    def load(self) -> Dict[str, Any]:
        try:
            with open(self._path, encoding="utf-8") as handle:
                value = json.load(handle)
            if isinstance(value, dict):
                return {**self._EMPTY, **{key: value.get(key) for key in self._EMPTY}}
        except (OSError, json.JSONDecodeError):
            pass
        return dict(self._EMPTY)

    def save(self, config: Dict[str, Any]) -> None:
        data = {key: config.get(key) for key in self._EMPTY}
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        temp = self._path + ".tmp"
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        os.replace(temp, self._path)
