"""Compact Active Context: Represents active working memory for same-session turns (Batch A2.3).

This is a compact working-context data structure, NOT full persistent history.
It carries supplied active working items (artifacts, entities, prior action) for
evaluating conversational reference resolution in Step 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple


@dataclass(frozen=True)
class ArtifactDescriptor:
    """An active artifact in current session memory."""

    id: str  # e.g. "x1", "x2"
    name: str  # e.g. "Hostel_Order_21Sep.docx"
    artifact_type: Optional[str] = None
    description: Optional[str] = None


@dataclass(frozen=True)
class EntityDescriptor:
    """An active entity (person, group, organization) in working memory."""

    id: str  # e.g. "e1", "e2"
    name: str  # e.g. "OH-1 first-year students", "Chief Warden"
    category: Optional[str] = None


@dataclass(frozen=True)
class ActiveContext:
    """Small active working context for same-session interaction."""

    active_artifacts: Tuple[ArtifactDescriptor, ...] = ()
    active_entities: Tuple[EntityDescriptor, ...] = ()
    prior_semantic_operation: Optional[str] = None
    active_topic: Optional[str] = None
    recent_relevant_turns: Tuple[str, ...] = ()
    current_workflow_summary: Optional[str] = None

    @property
    def has_active_artifacts(self) -> bool:
        return len(self.active_artifacts) > 0

    @property
    def has_active_entities(self) -> bool:
        return len(self.active_entities) > 0

    @property
    def has_prior_operation(self) -> bool:
        return bool(self.prior_semantic_operation)
