"""Growth ledger: XP/level/achievements computed from real,
already-proven user-driven events - never fabricated, never read by
anything that plans, authorizes, approves, executes, or otherwise
makes a safety-relevant decision.

Every GrowthEvent is always a recorded side effect of something else
genuinely happening (see server.py's POST /memory and POST /profile
handlers, which call record_event() after their real write already
succeeded) - there is no endpoint or code path that manufactures XP
out of nothing. There is deliberately no public "add XP" surface.

total_xp/level/achievements are never stored as independent counters;
they are always computed fresh from the append-only event list by
compute_summary(), mirroring audit_comparison.py's exact philosophy:
derive stats from raw events, never maintain a separate mutable
counter that could drift from its own history.

The level number is cosmetic. It is not a trust signal and not an
authorization signal - nothing in this codebase may ever read it to
make a security- or execution-relevant decision. Contrast with
Fact.verify(), which requires a real, accountable, non-model actor:
"high level" is never a substitute for that kind of verification, and
must never become one.
"""

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from uri_core.core.security_guards import (
    MAX_METADATA_VALUE_LENGTH,
    looks_like_credential_key,
    looks_like_credential_value,
)

SCHEMA_VERSION = "1.0"

# XP awarded per event_type. A flat, documented, non-load-bearing
# table - tune freely without touching any other logic. An unknown
# event_type is valid and simply awards 0 XP, rather than raising.
XP_TABLE: Dict[str, int] = {
    "memory_recorded": 10,
    "profile_updated": 5,
}

# Achievement rules: (achievement_id, predicate over event counts by
# type). Pure and deterministic - always recomputed from history,
# never stored as a standalone "unlocked" flag.
_ACHIEVEMENT_RULES = (
    (
        "first_memory",
        lambda counts: counts.get("memory_recorded", 0) >= 1,
    ),
    (
        "getting_to_know_you",
        lambda counts: counts.get("memory_recorded", 0) >= 5,
    ),
    (
        "profile_configured",
        lambda counts: counts.get("profile_updated", 0) >= 1,
    ),
)


class GrowthLedgerValidationError(ValueError):
    """Raised when a growth event fails safety or shape validation."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_parent_dir(path: str) -> None:
    folder = os.path.dirname(path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)


def _validate_metadata(metadata: Dict[str, Any]) -> None:
    # Same discipline as AuditEvent/MemoryEntry - reuse
    # security_guards.py rather than a fourth implementation.
    for key, value in metadata.items():

        if looks_like_credential_key(str(key)):
            raise GrowthLedgerValidationError(
                f"metadata key '{key}' looks credential-related and "
                "is not permitted in a growth event."
            )

        if isinstance(value, str):

            if looks_like_credential_value(value):
                raise GrowthLedgerValidationError(
                    f"metadata value for key '{key}' looks like a "
                    "credential and is not permitted in a growth "
                    "event."
                )

            if len(value) > MAX_METADATA_VALUE_LENGTH:
                raise GrowthLedgerValidationError(
                    f"metadata value for key '{key}' exceeds "
                    f"{MAX_METADATA_VALUE_LENGTH} characters."
                )


@dataclass
class GrowthEvent:
    event_id: str
    event_type: str
    xp_delta: int
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION


def compute_level(total_xp: int) -> int:
    """Cosmetic only - see module docstring. Simple, deterministic,
    documented curve: level 1 at 0 XP, +1 level per 100 XP."""
    return 1 + max(total_xp, 0) // 100


def compute_summary(
    events: List[GrowthEvent], recent_limit: int = 10
) -> Dict[str, Any]:
    """Pure function - the only place total_xp/level/achievements are
    ever derived. Mirrors audit_comparison.summarize_shadow_comparisons
    exactly: recompute from raw events every call, store nothing
    aggregate."""

    total_xp = sum(event.xp_delta for event in events)

    counts_by_type: Dict[str, int] = {}

    for event in events:
        counts_by_type[event.event_type] = (
            counts_by_type.get(event.event_type, 0) + 1
        )

    achievements = [
        achievement_id
        for achievement_id, predicate in _ACHIEVEMENT_RULES
        if predicate(counts_by_type)
    ]

    recent = sorted(
        events, key=lambda event: event.timestamp, reverse=True
    )[:recent_limit]

    return {
        "total_xp": total_xp,
        "level": compute_level(total_xp),
        "achievements": achievements,
        "event_count": len(events),
        "counts_by_type": counts_by_type,
        "recent": [
            {
                "event_type": event.event_type,
                "xp_delta": event.xp_delta,
                "timestamp": event.timestamp,
            }
            for event in recent
        ],
    }


class GrowthLedgerStore:
    """Loads and saves the single ambient, append-only growth event
    history for this install. Same persistence pattern as MemoryStore
    (JSON file, schema_version, safe degrade-to-empty on a corrupted
    file)."""

    def __init__(
        self,
        storage_path: str = "uri_workspace/growth_ledger.json",
    ):
        self.storage_path = os.path.normpath(storage_path)

    def record_event(
        self,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GrowthEvent:

        metadata = dict(metadata or {})
        _validate_metadata(metadata)

        event = GrowthEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            xp_delta=XP_TABLE.get(event_type, 0),
            timestamp=_now(),
            metadata=metadata,
        )

        events = self._load()
        events.append(event)
        self._save(events)

        return event

    def list_all(self) -> List[GrowthEvent]:
        return self._load()

    def summary(self, recent_limit: int = 10) -> Dict[str, Any]:
        return compute_summary(self._load(), recent_limit=recent_limit)

    def _load(self) -> List[GrowthEvent]:

        if not os.path.exists(self.storage_path):
            return []

        try:

            with open(
                self.storage_path, "r", encoding="utf-8"
            ) as file:
                data = json.load(file)

            events = []

            for raw in data.get("events", []):

                events.append(
                    GrowthEvent(
                        event_id=raw["event_id"],
                        event_type=raw["event_type"],
                        xp_delta=raw["xp_delta"],
                        timestamp=raw["timestamp"],
                        metadata=raw.get("metadata", {}),
                        schema_version=raw.get(
                            "schema_version", SCHEMA_VERSION
                        ),
                    )
                )

            return events

        except (
            json.JSONDecodeError,
            KeyError,
            OSError,
            TypeError,
        ):
            return []

    def _save(self, events: List[GrowthEvent]) -> None:
        _ensure_parent_dir(self.storage_path)

        data = {
            "schema_version": SCHEMA_VERSION,
            "events": [asdict(event) for event in events],
        }

        with open(self.storage_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
