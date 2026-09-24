"""SemanticInputEnvelope and Narrow Semantic Views (Batch A2.3).

Builds the semantic envelope ONCE per turn from:
  current_message + TurnFrame + ActiveContext
and derives narrow task views for adaptive Needle invocation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from uri_v1.turn.active_context import ActiveContext, ArtifactDescriptor, EntityDescriptor
from uri_v1.turn.turn_frame import CandidateAction, CandidateReference, TurnFrame


@dataclass(frozen=True)
class GoalView:
    """View presented to Needle for goal and intent_family interpretation."""

    current_message: str
    clauses: Tuple[str, ...]
    candidate_actions: Tuple[str, ...]
    active_topic: Optional[str] = None
    prior_operation: Optional[str] = None

    def format_prompt(self) -> str:
        lines = [f"Select the goal and intent family for this user request:\n{self.current_message}"]
        if self.candidate_actions:
            lines.append(f"Observed action verbs: {', '.join(self.candidate_actions)}")
        if self.active_topic:
            lines.append(f"Active topic: {self.active_topic}")
        if self.prior_operation:
            lines.append(f"Prior operation: {self.prior_operation}")
        return "\n".join(lines)


@dataclass(frozen=True)
class OperationView:
    """View presented to Needle for classifying candidate action IDs."""

    clauses: Tuple[str, ...]
    candidate_actions: Tuple[CandidateAction, ...]
    negation_spans: Tuple[str, ...]

    def format_prompt(self) -> str:
        lines = ["Select which candidate action IDs are requested or prohibited:"]
        lines.append("Clauses:")
        for idx, c in enumerate(self.clauses):
            lines.append(f"  [{idx}] {c}")
        if self.negation_spans:
            lines.append(f"Negation cues: {', '.join(self.negation_spans)}")
        lines.append("Candidate action IDs:")
        for act in self.candidate_actions:
            lines.append(f"  {act.id}: {act.verb}")
        return "\n".join(lines)


@dataclass(frozen=True)
class ReferenceView:
    """View presented to Needle for resolving or preserving candidate references."""

    candidate_references: Tuple[CandidateReference, ...]
    active_artifacts: Tuple[ArtifactDescriptor, ...]
    active_entities: Tuple[EntityDescriptor, ...]
    clauses: Tuple[str, ...]
    prior_operation: Optional[str] = None

    def format_prompt(self) -> str:
        lines = ["Classify candidate reference IDs against active session targets:"]
        lines.append("Clauses:")
        for idx, c in enumerate(self.clauses):
            lines.append(f"  [{idx}] {c}")
        lines.append("Candidate reference IDs:")
        for ref in self.candidate_references:
            lines.append(f"  {ref.id}: \"{ref.expression}\"")
        if self.active_artifacts:
            lines.append("Active session artifacts:")
            for art in self.active_artifacts:
                lines.append(f"  {art.id}: {art.name}")
        if self.active_entities:
            lines.append("Active session entities:")
            for ent in self.active_entities:
                lines.append(f"  {ent.id}: {ent.name}")
        if self.prior_operation:
            lines.append(f"Prior session operation: {self.prior_operation}")
        return "\n".join(lines)


@dataclass(frozen=True)
class OutputScopeView:
    """View presented to Needle for extracting output preferences and constraints."""

    explicit_formats: Tuple[str, ...]
    artifact_mentions: Tuple[str, ...]
    explicit_numbers: Tuple[str, ...]
    temporal_surface_spans: Tuple[str, ...]
    clauses: Tuple[str, ...]

    def format_prompt(self) -> str:
        lines = ["Clauses:"]
        for idx, c in enumerate(self.clauses):
            lines.append(f"  [{idx}] {c}")
        if self.explicit_formats:
            lines.append(f"Format cues: {', '.join(self.explicit_formats)}")
        if self.artifact_mentions:
            lines.append(f"Artifact cues: {', '.join(self.artifact_mentions)}")
        if self.explicit_numbers:
            lines.append(f"Number cues: {', '.join(self.explicit_numbers)}")
        if self.temporal_surface_spans:
            lines.append(f"Temporal cues: {', '.join(self.temporal_surface_spans)}")
        return "\n".join(lines)


@dataclass(frozen=True)
class SemanticInputEnvelope:
    """Combines current turn structural observations with active context."""

    current_message: str
    turn_frame: TurnFrame
    active_context: Optional[ActiveContext] = None

    @property
    def goal_view(self) -> GoalView:
        topic = self.active_context.active_topic if self.active_context else None
        prior_op = self.active_context.prior_semantic_operation if self.active_context else None
        return GoalView(
            current_message=self.current_message,
            clauses=self.turn_frame.clauses,
            candidate_actions=self.turn_frame.candidate_action_spans,
            active_topic=topic,
            prior_operation=prior_op,
        )

    @property
    def operation_view(self) -> OperationView:
        return OperationView(
            clauses=self.turn_frame.clauses,
            candidate_actions=self.turn_frame.candidate_actions,
            negation_spans=self.turn_frame.negation_spans,
        )

    @property
    def reference_view(self) -> ReferenceView:
        artifacts = self.active_context.active_artifacts if self.active_context else ()
        entities = self.active_context.active_entities if self.active_context else ()
        prior_op = self.active_context.prior_semantic_operation if self.active_context else None
        return ReferenceView(
            candidate_references=self.turn_frame.candidate_references,
            active_artifacts=artifacts,
            active_entities=entities,
            clauses=self.turn_frame.clauses,
            prior_operation=prior_op,
        )

    @property
    def output_scope_view(self) -> OutputScopeView:
        return OutputScopeView(
            explicit_formats=self.turn_frame.explicit_formats,
            artifact_mentions=self.turn_frame.artifact_mentions,
            explicit_numbers=self.turn_frame.explicit_numbers,
            temporal_surface_spans=self.turn_frame.temporal_surface_spans,
            clauses=self.turn_frame.clauses,
        )
