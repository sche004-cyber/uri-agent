"""User-controlled memory: durable, provenance-tracked information
about the user, distinct from uri_core.core.facts' task-execution
facts (which stay session-scoped, e.g. "policy expires on X date").
Neither facts.py, fact_manager.py, nor state.py is modified by this
module - MemoryEntry composes Fact by reference, reusing its existing
status/confidence/source/verification model rather than duplicating
it.

Same ambient-single-store simplification as UserProfileStore/
UserIdentityStore: there is exactly one memory store per install,
because there is no authentication yet.

Explicit consent, per URI_AI_OPERATING_POLICY.md section 15 ("Do not
assume that identifying useful information grants permission to save
it"):

    user_provided      - the user directly told URI to remember this.
                          Consent is inherent in the request.
    user_confirmed      - URI proposed remembering something and the
                          user explicitly approved it.
    pending_confirmation - URI proposed remembering something; not yet
                          approved.

Nothing in this milestone ever creates a pending_confirmation entry -
that requires URI/the model noticing something during a live
conversation and proposing it, which is explicitly deferred to a
later, separately-reviewed milestone (touching orchestrator.py). The
consent field exists now so that step is additive later, not a
rewrite.

The one rule every future consumer of this store MUST respect:
anything that reads memory to influence personalization, tone, or
interpretation may only ever read entries whose consent is
"user_provided" or "user_confirmed". A "pending_confirmation" entry is
visible to the user for review and nothing else - it must never be
treated as established fact.
"""

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from uri_core.core.facts import Fact
from uri_core.core.security_guards import (
    MAX_METADATA_VALUE_LENGTH,
    looks_like_credential_value,
)

SCHEMA_VERSION = "1.0"

VALID_CATEGORIES = {
    "preference",
    "interest",
    "interaction_pattern",
    "explicit_statement",
    "other",
}

VALID_CONSENT_VALUES = {
    "user_provided",
    "user_confirmed",
    "pending_confirmation",
}


class MemoryValidationError(ValueError):
    """Raised when memory content fails safety or shape validation."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_parent_dir(path: str) -> None:
    folder = os.path.dirname(path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)


def _validate_content(content: str, notes: Optional[str]) -> None:

    if not content or not isinstance(content, str):
        raise MemoryValidationError(
            "Memory content must be a non-empty string."
        )

    for label, value in (("content", content), ("notes", notes)):

        if not value:
            continue

        if len(value) > MAX_METADATA_VALUE_LENGTH:
            raise MemoryValidationError(
                f"Memory {label} exceeds {MAX_METADATA_VALUE_LENGTH} "
                "characters."
            )

        if looks_like_credential_value(value):
            raise MemoryValidationError(
                f"Memory {label} looks like a credential and is not "
                "permitted in memory."
            )


def _validate_category(category: str) -> None:

    if category not in VALID_CATEGORIES:
        raise MemoryValidationError(
            f"Invalid memory category: {category!r}. Must be one of "
            f"{sorted(VALID_CATEGORIES)}."
        )


@dataclass
class MemoryEntry:
    memory_id: str
    category: str
    consent: str
    fact: Fact
    created_at: str
    updated_at: str
    schema_version: str = SCHEMA_VERSION


# The consent values a future personalization/interpretation consumer
# is ever allowed to treat as established. A "pending_confirmation"
# entry is real data the user can see and act on, but it is not yet
# something the user agreed URI should rely on - so it is excluded
# here, not just by convention but by a single, tested function every
# future caller should use instead of re-deriving this rule.
PERSONALIZATION_ELIGIBLE_CONSENT = frozenset(
    {"user_provided", "user_confirmed"}
)


def is_eligible_for_personalization(entry: MemoryEntry) -> bool:
    return entry.consent in PERSONALIZATION_ELIGIBLE_CONSENT


class MemoryStore:
    """Loads and saves the single ambient list of MemoryEntry records
    for this install. Follows UserProfileStore's persistence pattern
    (JSON file, schema_version, safe degrade-to-empty on a corrupted
    file) and SkillMemory's list-of-records file shape.
    """

    def __init__(
        self, storage_path: str = "uri_workspace/user_memory.json"
    ):
        self.storage_path = os.path.normpath(storage_path)

    def list_all(self) -> List[MemoryEntry]:
        return self._load()

    def get(self, memory_id: str) -> Optional[MemoryEntry]:

        for entry in self._load():

            if entry.memory_id == memory_id:
                return entry

        return None

    def add(
        self,
        *,
        category: str,
        content: str,
        confidence: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> MemoryEntry:

        _validate_category(category)
        _validate_content(content, notes)

        fact = Fact(
            name=category,
            value=content,
            status="CONFIRMED",
            source="user_explicit",
            confidence=confidence,
            notes=notes,
        )

        fact.validate_status()
        fact.validate_confidence()

        now = _now()

        entry = MemoryEntry(
            memory_id=str(uuid.uuid4()),
            category=category,
            consent="user_provided",
            fact=fact,
            created_at=now,
            updated_at=now,
        )

        entries = self._load()
        entries.append(entry)
        self._save(entries)

        return entry

    def update(
        self,
        memory_id: str,
        *,
        category: str,
        content: str,
        confidence: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> Optional[MemoryEntry]:

        _validate_category(category)
        _validate_content(content, notes)

        entries = self._load()

        for index, existing in enumerate(entries):

            if existing.memory_id != memory_id:
                continue

            fact = Fact(
                name=category,
                value=content,
                status=existing.fact.status,
                source=existing.fact.source,
                confidence=confidence,
                notes=notes,
                verified=existing.fact.verified,
                verified_by=existing.fact.verified_by,
                verified_at=existing.fact.verified_at,
            )

            fact.validate_status()
            fact.validate_confidence()

            updated = MemoryEntry(
                memory_id=existing.memory_id,
                category=category,
                # Editing your own memory doesn't change who consented
                # to it existing - consent is not exposed as an
                # editable field this milestone (nothing ever creates
                # anything other than user_provided yet).
                consent=existing.consent,
                fact=fact,
                created_at=existing.created_at,
                updated_at=_now(),
            )

            entries[index] = updated
            self._save(entries)

            return updated

        return None

    def delete(self, memory_id: str) -> bool:

        entries = self._load()
        remaining = [
            entry for entry in entries if entry.memory_id != memory_id
        ]

        if len(remaining) == len(entries):
            return False

        self._save(remaining)

        return True

    def _load(self) -> List[MemoryEntry]:

        if not os.path.exists(self.storage_path):
            return []

        try:

            with open(
                self.storage_path, "r", encoding="utf-8"
            ) as file:
                data = json.load(file)

            entries = []

            for raw in data.get("memories", []):

                fact_data = raw.get("fact", {})

                entries.append(
                    MemoryEntry(
                        memory_id=raw["memory_id"],
                        category=raw["category"],
                        consent=raw.get(
                            "consent", "user_provided"
                        ),
                        fact=Fact(**fact_data),
                        created_at=raw.get("created_at", ""),
                        updated_at=raw.get("updated_at", ""),
                        schema_version=raw.get(
                            "schema_version", SCHEMA_VERSION
                        ),
                    )
                )

            return entries

        except (
            json.JSONDecodeError,
            KeyError,
            OSError,
            TypeError,
        ):
            return []

    def _save(self, entries: List[MemoryEntry]) -> None:
        _ensure_parent_dir(self.storage_path)

        data = {
            "schema_version": SCHEMA_VERSION,
            "memories": [asdict(entry) for entry in entries],
        }

        with open(self.storage_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
