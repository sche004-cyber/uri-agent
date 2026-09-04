"""Bounded personalization context: confirmed UserProfile + only
consent-eligible UserMemory, assembled into a small, capped,
labeled dict for the response-drafting step (see response_drafting.py)
to use as advisory input.

This module is pure and read-only - it never touches storage itself,
never writes anything, and is never imported by capability_planner.py,
dispatcher.py, approval_gate.py, or approval_store.py. Personalization
may only ever influence how URI's response is *phrased*; it must never
reach anything that decides what URI does. See
test_capability_authority_boundary.py for the structural proof of that
boundary and test_orchestrator_response_narrative.py for the
behavioural proof.

Explicitly excluded, by design, not oversight:
    - growth_ledger.py's XP/level/achievements - cosmetic, and mixing
      it into personalization risks it quietly becoming a signal
      something reads as meaningful.
    - Any MemoryEntry whose consent is "pending_confirmation" - see
      user_memory.py's is_eligible_for_personalization(), reused here
      verbatim rather than re-derived. A pending entry is visible to
      the user for review and nothing else; it must never be treated
      as something URI can rely on when speaking to the user.
"""

from typing import Any, Dict, List, Optional

from uri_core.core.security_guards import (
    MAX_METADATA_VALUE_LENGTH,
    looks_like_credential_value,
)
from uri_core.core.user_memory import (
    MemoryEntry,
    is_eligible_for_personalization,
)
from uri_core.core.user_profile import UserProfile

# Bounds the context size regardless of how much memory a user has
# accumulated - a drafting prompt should stay small and cheap, and an
# unbounded dump risks diluting or burying the profile fields that
# usually matter more. Most-recently-updated entries are kept.
MAX_MEMORY_ENTRIES = 10


def _safe_text(value: str) -> Optional[str]:
    """Defense in depth only - every value here was already validated
    at write time (UserProfileStore.save()/MemoryStore.add()/.update()
    both already reject credential-shaped or oversized content). Never
    raises: a value that somehow still fails this check is simply
    dropped rather than allowed to break context assembly for
    everything else."""

    if not isinstance(value, str) or not value:
        return None

    if len(value) > MAX_METADATA_VALUE_LENGTH:
        return None

    if looks_like_credential_value(value):
        return None

    return value


def build_personalization_context(
    profile: Optional[UserProfile],
    memory_entries: List[MemoryEntry],
) -> Dict[str, Any]:
    """Returns a small, bounded, labeled dict - never prose, never
    free-form instruction text - so a drafting prompt can only ever
    receive personalization as clearly-labeled data, not as
    instructions to follow."""

    communication_style = None
    autonomy_level = None
    focus_areas: List[str] = []

    if profile is not None:
        communication_style = _safe_text(profile.communication_style)
        autonomy_level = _safe_text(profile.autonomy_level)
        focus_areas = [
            area
            for area in (
                _safe_text(item) for item in profile.focus_areas
            )
            if area is not None
        ]

    eligible = [
        entry
        for entry in memory_entries
        if is_eligible_for_personalization(entry)
    ]

    eligible.sort(key=lambda entry: entry.updated_at, reverse=True)

    memory: List[Dict[str, str]] = []

    for entry in eligible[:MAX_MEMORY_ENTRIES]:

        content = _safe_text(entry.fact.value)

        if content is None:
            continue

        memory.append(
            {
                "category": entry.category,
                "content": content,
            }
        )

    return {
        "communication_style": communication_style,
        "autonomy_level": autonomy_level,
        "focus_areas": focus_areas,
        "memory": memory,
    }
