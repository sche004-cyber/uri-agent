"""Item 7 of the URI architecture spec: structured experience/history
records, distinct from every other kind of state this codebase already
keeps:

- temporary context: session.py's SessionManager (task/fact/workflow
  state for one in-progress conversation, cleared/overwritten turn to
  turn).
- conversation history: not modeled as a transcript anywhere in this
  codebase today (out of scope for this module).
- user profile: user_profile.py/personalization_context.py (who the
  user is - preferences, communication style).
- persistent knowledge: user_memory.py (durable facts ABOUT the user,
  explicit-consent gated) and facts.py (task-execution facts).
- reusable experience (THIS module): what URI actually did, and what
  came of it, across past interactions - retrievable later so the
  Brain can draw on real prior outcomes rather than starting cold
  every turn.

An ExperienceRecord is never written from raw conversation content.
Every record traces back to the Brain's own, already-existing
acceptance-retention judgment (see orchestrator.py's
_run_acceptance_retention_step / _model_retention_candidate) - URI does
not decide on its own that an interaction was worth remembering, and
never blindly saves every conversation as permanent memory (see this
module's docstring section on that in the operating policy, section
15). This module only shapes an already-Brain-approved candidate into
one small, structured, retrievable record and persists it - mirroring
user_memory.py's MemoryStore pattern (validated content, schema-
versioned JSON file, safe degrade-to-empty on a corrupted file) one
level up, for experience rather than personal facts.
"""

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from uri_core.core.security_guards import (
    MAX_METADATA_VALUE_LENGTH,
    looks_like_credential_value,
)

SCHEMA_VERSION = "1.0"

VALID_CATEGORIES = {
    "successful_approach",
    "user_preference",
    "reference_pattern",
    "other",
}

MAX_LIST_ITEMS = 10


class ExperienceValidationError(ValueError):
    """Raised when experience content fails safety or shape validation."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_parent_dir(path: str) -> None:
    folder = os.path.dirname(path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)


def _clean_text(value: Any, label: str) -> str:

    if value is None:
        return ""

    text = str(value)

    if len(text) > MAX_METADATA_VALUE_LENGTH:
        raise ExperienceValidationError(
            f"Experience {label} exceeds {MAX_METADATA_VALUE_LENGTH} "
            "characters."
        )

    if looks_like_credential_value(text):
        raise ExperienceValidationError(
            f"Experience {label} looks like a credential and is not "
            "permitted in an experience record."
        )

    return text


def _clean_list(value: Any, label: str) -> List[str]:

    if not isinstance(value, list):
        return []

    cleaned = []

    for item in value[:MAX_LIST_ITEMS]:
        cleaned.append(_clean_text(item, label))

    return cleaned


def _validate_category(category: str) -> None:

    if category not in VALID_CATEGORIES:
        raise ExperienceValidationError(
            f"Invalid experience category: {category!r}. Must be one "
            f"of {sorted(VALID_CATEGORIES)}."
        )


@dataclass
class ExperienceRecord:
    """One structured, bounded account of a past interaction the Brain
    itself judged worth retaining - never a full transcript. Every
    field is honest-but-optional: URI records only what it actually
    observed at the moment retention was decided (see
    orchestrator.py's _run_acceptance_retention_step), never a
    reconstruction or inference of anything it did not directly see.
    """

    experience_id: str
    category: str
    intent: str
    summary: str
    actions: List[str]
    decisions: List[str]
    results: str
    failures: List[str]
    corrections: List[str]
    learned: str
    unresolved: List[str]
    created_at: str
    schema_version: str = SCHEMA_VERSION


class ExperienceStore:
    """Loads and saves the ambient list of ExperienceRecord entries for
    this install - one JSON file, schema_version, safe degrade-to-empty
    on a corrupted file, mirroring MemoryStore's/SkillMemory's existing
    persistence pattern. Ambient (not yet per-user-scoped) for the same
    reason SkillMemory already is: UriOrchestrator itself has no
    user_id/identity boundary of its own (see identity.py) - only the
    HTTP layer (server.py) does. A future per-user-scoped experience
    store, mirroring _build_user_context's MemoryStore wiring, is
    additive later work, not a rewrite of this module's shape.
    """

    def __init__(
        self, storage_path: str = "uri_workspace/experience.json"
    ):
        self.storage_path = os.path.normpath(storage_path)

    def list_all(self) -> List[ExperienceRecord]:
        return self._load()

    def recent(self, limit: int = 5) -> List[ExperienceRecord]:
        """Most-recently-created records first, bounded to `limit` -
        the same "small, bounded reference, never an unbounded dump"
        discipline personalization_context.py/query_context.py already
        apply elsewhere in this codebase."""

        return list(reversed(self._load()))[:limit]

    def add(
        self,
        *,
        category: str,
        intent: str = "",
        summary: str,
        actions: Optional[List[str]] = None,
        decisions: Optional[List[str]] = None,
        results: str = "",
        failures: Optional[List[str]] = None,
        corrections: Optional[List[str]] = None,
        learned: str = "",
        unresolved: Optional[List[str]] = None,
    ) -> ExperienceRecord:

        _validate_category(category)

        record = ExperienceRecord(
            experience_id=str(uuid.uuid4()),
            category=category,
            intent=_clean_text(intent, "intent"),
            summary=_clean_text(summary, "summary"),
            actions=_clean_list(actions, "actions"),
            decisions=_clean_list(decisions, "decisions"),
            results=_clean_text(results, "results"),
            failures=_clean_list(failures, "failures"),
            corrections=_clean_list(corrections, "corrections"),
            learned=_clean_text(learned, "learned"),
            unresolved=_clean_list(unresolved, "unresolved"),
            created_at=_now(),
        )

        if not record.summary:
            raise ExperienceValidationError(
                "Experience summary must be a non-empty string."
            )

        entries = self._load()
        entries.append(record)
        self._save(entries)

        return record

    def _load(self) -> List[ExperienceRecord]:

        if not os.path.exists(self.storage_path):
            return []

        try:

            with open(
                self.storage_path, "r", encoding="utf-8"
            ) as file:
                data = json.load(file)

            entries = []

            for raw in data.get("experiences", []):

                entries.append(
                    ExperienceRecord(
                        experience_id=raw["experience_id"],
                        category=raw["category"],
                        intent=raw.get("intent", ""),
                        summary=raw["summary"],
                        actions=raw.get("actions", []),
                        decisions=raw.get("decisions", []),
                        results=raw.get("results", ""),
                        failures=raw.get("failures", []),
                        corrections=raw.get("corrections", []),
                        learned=raw.get("learned", ""),
                        unresolved=raw.get("unresolved", []),
                        created_at=raw.get("created_at", ""),
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

    def _save(self, entries: List[ExperienceRecord]) -> None:
        _ensure_parent_dir(self.storage_path)

        data = {
            "schema_version": SCHEMA_VERSION,
            "experiences": [asdict(entry) for entry in entries],
        }

        with open(self.storage_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)


def summarize_for_query_context(
    records: List[ExperienceRecord],
) -> List[Dict[str, Any]]:
    """Shapes ExperienceRecord entries into the small, labeled dicts
    query_context.py's "experience" section expects - mirrors
    query_context.py's own _serialize_capability discipline (plain
    dict, no behaviour, unknown-safe). Never touches storage; a
    non-ExperienceRecord entry is dropped rather than guessed at."""

    summarized = []

    for record in records:

        if not isinstance(record, ExperienceRecord):
            continue

        summarized.append(
            {
                "category": record.category,
                "intent": record.intent,
                "summary": record.summary,
                "actions": list(record.actions),
                "results": record.results,
                "unresolved": list(record.unresolved),
                "created_at": record.created_at,
            }
        )

    return summarized
