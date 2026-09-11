"""Optional account-wide monthly token ceiling, isolated by user identity."""

import json
import os
import tempfile
from typing import Optional

from uri_core.core.portable_paths import user_scoped_path


class UsageCeilingStore:
    def __init__(self, user_id: str) -> None:
        self._path = user_scoped_path(user_id, "usage_ceiling.json")

    def get_ceiling(self) -> Optional[int]:
        try:
            with open(self._path, encoding="utf-8") as stream:
                value = json.load(stream)["monthly_token_ceiling"]
        except FileNotFoundError:
            return None
        self._validate(value)
        return value

    @staticmethod
    def _validate(value: Optional[int]) -> None:
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError("monthly_token_ceiling must be a nonnegative integer or null")

    def set_ceiling(self, value: Optional[int]) -> None:
        self._validate(value)
        folder = os.path.dirname(self._path)
        os.makedirs(folder, exist_ok=True)
        # Unique temporary files keep concurrent updates atomic on Windows, too.
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=folder,
                                             delete=False) as stream:
                temporary = stream.name
                json.dump({"monthly_token_ceiling": value}, stream)
            os.replace(temporary, self._path)
        finally:
            if temporary is not None and os.path.exists(temporary):
                os.unlink(temporary)

    def get_warn_threshold_ratio(self) -> float:
        return 0.8
