"""URI's user profile: preferences that shape tone and autonomy.

This is a single, ambient profile per install - there is no multi-user
support yet, because there is no authentication yet (see identity.py's
UserIdentity, which explicitly carries no auth meaning by itself).
"The current user" today can only ever mean "whoever is running this
local install," so UserProfileStore does not key its data by user_id -
it stores one profile, the same way UserIdentityStore/
DeviceIdentityStore each store one identity.

The field names and value shapes mirror uri_ui/lib/models/
user_preferences.dart's UserPreferences exactly (communication_style,
autonomy_level, focus_areas), using the same string values Dart's enum
.name already produces (e.g. "concise", "askEveryTime") - so a future
milestone that has Flutter actually read/write this store needs no
translation layer. Flutter's own PreferencesStore remains the
device-local cache it already is; nothing here changes that class or
makes Flutter authoritative - this module is additive, standalone
infrastructure, not wired into Flutter this milestone.
"""

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from uri_core.core.security_guards import (
    MAX_METADATA_VALUE_LENGTH,
    looks_like_credential_value,
)

SCHEMA_VERSION = "1.0"

DEFAULT_COMMUNICATION_STYLE = "concise"
DEFAULT_AUTONOMY_LEVEL = "askEveryTime"

# Mirrors uri_ui/lib/models/user_preferences.dart's enums exactly - see
# this module's docstring. Once profile data started reaching a model
# prompt (see personalization_context.py), an unconstrained string
# here became a real prompt-injection surface, not just a data-shape
# nicety - hence the validation below, following user_memory.py's
# exact discipline (reuse security_guards.py, never invent a second
# credential/length check).
VALID_COMMUNICATION_STYLES = {"formal", "concise", "conversational"}
VALID_AUTONOMY_LEVELS = {"askEveryTime", "routineAutoApprove"}

MAX_FOCUS_AREAS = 20


class UserProfileValidationError(ValueError):
    """Raised when profile input fails safety or shape validation."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_parent_dir(path: str) -> None:
    folder = os.path.dirname(path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)


def _validate_profile_fields(
    communication_style: str,
    autonomy_level: str,
    focus_areas: List[str],
) -> None:

    if communication_style not in VALID_COMMUNICATION_STYLES:
        raise UserProfileValidationError(
            f"Invalid communication_style: {communication_style!r}. "
            f"Must be one of {sorted(VALID_COMMUNICATION_STYLES)}."
        )

    if autonomy_level not in VALID_AUTONOMY_LEVELS:
        raise UserProfileValidationError(
            f"Invalid autonomy_level: {autonomy_level!r}. Must be one "
            f"of {sorted(VALID_AUTONOMY_LEVELS)}."
        )

    if len(focus_areas) > MAX_FOCUS_AREAS:
        raise UserProfileValidationError(
            f"focus_areas exceeds {MAX_FOCUS_AREAS} entries."
        )

    for area in focus_areas:

        if not isinstance(area, str):
            raise UserProfileValidationError(
                "Each focus_areas entry must be a string."
            )

        if len(area) > MAX_METADATA_VALUE_LENGTH:
            raise UserProfileValidationError(
                f"focus_areas entry exceeds "
                f"{MAX_METADATA_VALUE_LENGTH} characters."
            )

        if looks_like_credential_value(area):
            raise UserProfileValidationError(
                "focus_areas entry looks like a credential and is "
                "not permitted in a profile."
            )


@dataclass(frozen=True)
class UserProfile:
    communication_style: str = DEFAULT_COMMUNICATION_STYLE
    autonomy_level: str = DEFAULT_AUTONOMY_LEVEL
    focus_areas: List[str] = field(default_factory=list)
    updated_at: str = ""
    schema_version: str = SCHEMA_VERSION


class UserProfileStore:
    """Loads and saves the single ambient UserProfile for this install.

    Follows UserIdentityStore's exact persistence pattern (JSON file,
    schema_version, safe degrade-to-default on a corrupted file) so
    the two stay consistent as siblings.
    """

    def __init__(
        self,
        storage_path: str = "uri_workspace/user_profile.json",
    ):
        self.storage_path = os.path.normpath(storage_path)

    def load_or_create(self) -> UserProfile:
        existing = self._load()

        if existing is not None:
            return existing

        profile = UserProfile(updated_at=_now())

        self._save(profile)

        return profile

    def save(self, profile: UserProfile) -> UserProfile:

        _validate_profile_fields(
            profile.communication_style,
            profile.autonomy_level,
            list(profile.focus_areas),
        )

        updated = UserProfile(
            communication_style=profile.communication_style,
            autonomy_level=profile.autonomy_level,
            focus_areas=list(profile.focus_areas),
            updated_at=_now(),
            schema_version=profile.schema_version,
        )

        self._save(updated)

        return updated

    def _load(self) -> Optional[UserProfile]:

        if not os.path.exists(self.storage_path):
            return None

        try:

            with open(
                self.storage_path, "r", encoding="utf-8"
            ) as file:
                data = json.load(file)

            return UserProfile(
                communication_style=data.get(
                    "communication_style",
                    DEFAULT_COMMUNICATION_STYLE,
                ),
                autonomy_level=data.get(
                    "autonomy_level", DEFAULT_AUTONOMY_LEVEL
                ),
                focus_areas=list(data.get("focus_areas", [])),
                updated_at=data.get("updated_at", ""),
                schema_version=data.get(
                    "schema_version", SCHEMA_VERSION
                ),
            )

        except (json.JSONDecodeError, OSError, TypeError):
            return None

    def _save(self, profile: UserProfile) -> None:
        _ensure_parent_dir(self.storage_path)

        with open(self.storage_path, "w", encoding="utf-8") as file:
            json.dump(
                asdict(profile), file, indent=2, ensure_ascii=False
            )
