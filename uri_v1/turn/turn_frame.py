"""TurnFrame: Deeply immutable structural observation of the current turn (Batch A2.3).

Core principle:
    Code observes structure. Needle interprets relationships.

The TurnFrame contains only lexical and syntactic surface features extracted
deterministically by the turn preprocessor. It contains ZERO semantic conclusions:
  - NO goal selection
  - NO requested vs. prohibited operation classification
  - NO reference resolution
  - NO capability/tool selection
  - NO intent family inference
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

from uri_v1.turn.contracts import AttachmentReference


@dataclass(frozen=True)
class CandidateAction:
    """A detected action verb or predicate with a stable identifier."""

    id: str  # e.g. "a1", "a2"
    verb: str  # normalized verb lemma/form, e.g. "send", "draft"
    clause_index: int = 0


@dataclass(frozen=True)
class CandidateReference:
    """A detected referring expression (pronoun, demonstrative, noun phrase) with an ID."""

    id: str  # e.g. "r1", "r2"
    expression: str  # e.g. "this", "that file", "same thing", "the earlier one"
    clause_index: int = 0


@dataclass(frozen=True)
class TurnFrame:
    """Deeply immutable pre-semantic structural breakdown of a user turn."""

    raw_text: str
    normalized_text: str
    clauses: Tuple[str, ...] = ()
    negation_spans: Tuple[str, ...] = ()
    candidate_actions: Tuple[CandidateAction, ...] = ()
    candidate_references: Tuple[CandidateReference, ...] = ()
    temporal_surface_spans: Tuple[str, ...] = ()
    explicit_numbers: Tuple[str, ...] = ()
    explicit_formats: Tuple[str, ...] = ()
    artifact_mentions: Tuple[str, ...] = ()
    entity_surface_mentions: Tuple[str, ...] = ()
    quoted_spans: Tuple[str, ...] = ()
    attachments: Tuple[AttachmentReference, ...] = ()

    @property
    def has_candidate_actions(self) -> bool:
        return len(self.candidate_actions) > 0

    @property
    def has_candidate_references(self) -> bool:
        return len(self.candidate_references) > 0

    @property
    def has_negation(self) -> bool:
        return len(self.negation_spans) > 0

    @property
    def has_output_cues(self) -> bool:
        return bool(
            self.explicit_formats
            or self.artifact_mentions
            or self.explicit_numbers
            or self.temporal_surface_spans
        )

    @property
    def candidate_action_spans(self) -> Tuple[str, ...]:
        return tuple(a.verb for a in self.candidate_actions)

    @property
    def candidate_reference_spans(self) -> Tuple[str, ...]:
        return tuple(r.expression for r in self.candidate_references)
