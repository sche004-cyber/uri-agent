"""Core data contracts for the URIv1 turn pipeline (Batch A1.1).

Step 1 (Semantic Request Decoding) produces a DecodedRequest:
    "What does the user mean and what outcome are they asking for?"

Governing Rules:
1. Meaning outranks keywords.
2. Goal outranks verb frequency.
3. Unresolved references remain unresolved (no invented historical referents).
4. Prompt context != persistent context (only current request input is used).
5. Operation != capability / tool (no tool IDs, capability IDs, or execution hints).
6. Ambiguity and uncertainty are explicitly modeled, not forced into false certainty.
7. Step 1 does not execute, does not query Graphify/history/ARN, and does not choose intelligence tiers.
8. Context dependencies state THAT context is required, without prematurely dictating the storage tier (Step 2 decides).
9. All semantic contract types are genuinely frozen and immutable (no mutable dict/list structures).

A0 contracts retained without semantic redesign:
- ContextPack
- EdgeOutcome
- IntelligenceResult
- FinalizedTurn
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


class IntentFamily(str, Enum):
    """Broad descriptive intent families (non-routing, non-authoritative)."""

    RETRIEVE = "retrieve"
    CREATE = "create"
    MODIFY = "modify"
    COMMUNICATE = "communicate"
    EXECUTE = "execute"
    ANALYZE = "analyze"
    COMPARE = "compare"
    RESEARCH = "research"
    NAVIGATE = "navigate"
    CONVERSE = "converse"
    UNSPECIFIED = "unspecified"


class OperationStatus(str, Enum):
    """Status of an operation: explicitly requested vs. explicitly prohibited."""

    REQUESTED = "requested"
    PROHIBITED = "prohibited"


class ConfidenceLevel(str, Enum):
    """Provider-neutral semantic confidence levels."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


class ReferenceKind(str, Enum):
    """Classification of anaphoric and deictic expressions requiring resolution."""

    PRONOUN = "pronoun"  # "this", "that", "these", "those", "him", "her", "them"
    PREVIOUS_ACTION = "previous_action"  # "same thing", "do it again", "as before"
    DOCUMENT_OR_FILE = "document_or_file"  # "that file", "current file", "this one", "latest letter"
    TEMPORAL_ORDINAL = "temporal_ordinal"  # "previous approval", "earlier decision", "last one"
    OTHER = "other"


class EntityCategory(str, Enum):
    """Categories of entities explicitly mentioned in the request."""

    PERSON = "person"
    ROLE = "role"
    ORGANIZATION = "organization"
    DOCUMENT = "document"
    FILE = "file"
    PROJECT = "project"
    SERVICE = "service"
    DATE = "date"
    PLACE = "place"
    OBJECT = "object"
    OTHER = "other"


class ContextDependencyCategory(str, Enum):
    """Categories of contextual dependencies identified at Step 1.

    Step 1 expresses THAT context is needed without prematurely choosing
    how or from where Step 2 should resolve it (current session, prior session,
    Graphify, or external).
    """

    CONTEXT_REQUIRED = "context_required"  # General unresolved context requirement
    PRIOR_CONTEXT_UNSPECIFIED = "prior_context_unspecified"  # Reference to prior events/actions (unspecified source)
    CURRENT_ATTACHMENT = "current_attachment"  # Explicitly present or referenced in current turn attachments
    EXTERNAL_INFORMATION = "external_information"  # Explicitly refers to external facts/sources outside user workspace


class AmbiguityKind(str, Enum):
    """Categories of meaningful uncertainty or missing information."""

    UNRESOLVED_REFERENT = "unresolved_referent"
    UNRESOLVED_ARTIFACT_TYPE = "unresolved_artifact_type"
    MULTIPLE_INTERPRETATIONS = "multiple_interpretations"
    MISSING_TARGET = "missing_target"
    VAGUE_SCOPE = "vague_scope"
    OTHER = "other"


@dataclass(frozen=True)
class IntendedOutcome:
    """The primary goal / intended outcome the user wants achieved."""

    description: str
    intent_family: IntentFamily = IntentFamily.UNSPECIFIED


@dataclass(frozen=True)
class SemanticOperation:
    """An explicit or strongly implied operation (operation != tool/capability)."""

    name: str
    status: OperationStatus = OperationStatus.REQUESTED
    target: Optional[str] = None


@dataclass(frozen=True)
class ConstraintScope:
    """Explicit boundaries, limits, and restrictions supplied in the prompt."""

    time_range: Optional[str] = None
    included_items: Tuple[str, ...] = ()
    excluded_items: Tuple[str, ...] = ()
    length_limit: Optional[str] = None
    prohibited_actions: Tuple[str, ...] = ()
    source_restrictions: Tuple[str, ...] = ()
    precision_requirements: Optional[str] = None
    language_constraints: Optional[str] = None
    draft_only: bool = False
    custom_constraints: Tuple[str, ...] = ()


@dataclass(frozen=True)
class OutputPreferences:
    """Presentation and formatting requirements for eventual output."""

    artifact_type: Optional[str] = None
    structure: Optional[str] = None
    language: Optional[str] = None
    language_variant: Optional[str] = None
    tone: Optional[str] = None
    audience: Optional[str] = None
    length: Optional[str] = None
    detail_level: Optional[str] = None
    format: Optional[str] = None


@dataclass(frozen=True)
class MentionedEntity:
    """An entity explicitly mentioned in the request text."""

    name: str
    category: EntityCategory = EntityCategory.OTHER
    qualifier: Optional[str] = None


@dataclass(frozen=True)
class SemanticReference:
    """An anaphoric or contextual reference in the prompt that may remain unresolved."""

    expression: str
    kind: ReferenceKind = ReferenceKind.OTHER
    referent_hint: Optional[str] = None
    is_resolved: bool = False


@dataclass(frozen=True)
class TemporalReference:
    """A temporal expression present in the prompt (unresolved against history)."""

    expression: str
    is_relative: bool = True
    anchor_event: Optional[str] = None


@dataclass(frozen=True)
class AttachmentReference:
    """Metadata for an attachment provided or referenced in the current turn."""

    identifier: Optional[str] = None
    name: Optional[str] = None
    mime_type: Optional[str] = None
    reference_expression: Optional[str] = None


@dataclass(frozen=True)
class ContextDependency:
    """Information required from later context layers (Step 2) to execute the request."""

    description: str
    category: ContextDependencyCategory = ContextDependencyCategory.CONTEXT_REQUIRED
    unresolved_reference: Optional[str] = None


@dataclass(frozen=True)
class SemanticAmbiguity:
    """Explicit representation of ambiguity or multiple possible interpretations."""

    kind: AmbiguityKind
    description: str
    candidates: Tuple[str, ...] = ()


@dataclass(frozen=True)
class SemanticConfidence:
    """Aspect-level confidence evaluation across semantic dimensions."""

    goal: ConfidenceLevel = ConfidenceLevel.HIGH
    operations: ConfidenceLevel = ConfidenceLevel.HIGH
    references: ConfidenceLevel = ConfidenceLevel.HIGH
    constraints: ConfidenceLevel = ConfidenceLevel.HIGH
    overall: ConfidenceLevel = ConfidenceLevel.HIGH


@dataclass(frozen=True)
class DecodedRequest:
    """Output of Step 1 (Semantic Request Decoding).

    Captures: What does the user mean and what outcome are they asking for?
    Does NOT resolve references, select tools, or query external state.
    Genuinely frozen and immutable (no mutable dict/list attributes).
    """

    raw_text: str
    goal: IntendedOutcome = field(default_factory=lambda: IntendedOutcome(description=""))
    operations: Tuple[SemanticOperation, ...] = ()
    prompt_supplied_context: Tuple[str, ...] = ()
    constraints: ConstraintScope = field(default_factory=ConstraintScope)
    output_preferences: OutputPreferences = field(default_factory=OutputPreferences)
    entities: Tuple[MentionedEntity, ...] = ()
    references: Tuple[SemanticReference, ...] = ()
    temporal_references: Tuple[TemporalReference, ...] = ()
    attachments: Tuple[AttachmentReference, ...] = ()
    dependencies: Tuple[ContextDependency, ...] = ()
    ambiguities: Tuple[SemanticAmbiguity, ...] = ()
    confidence: SemanticConfidence = field(default_factory=SemanticConfidence)

    @property
    def intent(self) -> Optional[str]:
        """Backward-compatible helper returning goal description."""
        return self.goal.description if self.goal and self.goal.description else None

    @property
    def requested_operations(self) -> Tuple[str, ...]:
        """Names of all explicitly requested operations."""
        return tuple(op.name for op in self.operations if op.status == OperationStatus.REQUESTED)

    @property
    def prohibited_operations(self) -> Tuple[str, ...]:
        """Names of all explicitly prohibited / negative operations."""
        return tuple(op.name for op in self.operations if op.status == OperationStatus.PROHIBITED)

    @property
    def unresolved_references(self) -> Tuple[SemanticReference, ...]:
        """All references that remain unresolved at Step 1."""
        return tuple(ref for ref in self.references if not ref.is_resolved)

    @property
    def has_unresolved_references(self) -> bool:
        return len(self.unresolved_references) > 0

    @property
    def has_ambiguities(self) -> bool:
        return len(self.ambiguities) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize DecodedRequest to a plain Python dictionary."""

        def _convert(val: Any) -> Any:
            if isinstance(val, Enum):
                return val.value
            if isinstance(val, tuple):
                return [_convert(x) for x in val]
            if isinstance(val, list):
                return [_convert(x) for x in val]
            if isinstance(val, dict):
                return {k: _convert(v) for k, v in val.items()}
            if hasattr(val, "__dataclass_fields__"):
                return {k: _convert(getattr(val, k)) for k in val.__dataclass_fields__}
            return val

        return _convert(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DecodedRequest:
        """Construct a DecodedRequest from a serialized dictionary."""
        goal_data = data.get("goal")
        if isinstance(goal_data, dict):
            goal = IntendedOutcome(
                description=goal_data.get("description", ""),
                intent_family=IntentFamily(
                    goal_data.get("intent_family", IntentFamily.UNSPECIFIED.value)
                ),
            )
        elif isinstance(goal_data, str):
            goal = IntendedOutcome(description=goal_data)
        else:
            goal = IntendedOutcome(description="")

        operations = tuple(
            SemanticOperation(
                name=op.get("name", ""),
                status=OperationStatus(op.get("status", OperationStatus.REQUESTED.value)),
                target=op.get("target"),
            )
            for op in data.get("operations", ())
            if isinstance(op, dict)
        )

        constraints_data = data.get("constraints") or {}
        constraints = ConstraintScope(
            time_range=constraints_data.get("time_range"),
            included_items=tuple(constraints_data.get("included_items", ())),
            excluded_items=tuple(constraints_data.get("excluded_items", ())),
            length_limit=constraints_data.get("length_limit"),
            prohibited_actions=tuple(constraints_data.get("prohibited_actions", ())),
            source_restrictions=tuple(constraints_data.get("source_restrictions", ())),
            precision_requirements=constraints_data.get("precision_requirements"),
            language_constraints=constraints_data.get("language_constraints"),
            draft_only=bool(constraints_data.get("draft_only", False)),
            custom_constraints=tuple(constraints_data.get("custom_constraints", ())),
        )

        output_prefs_data = data.get("output_preferences") or {}
        output_preferences = OutputPreferences(
            artifact_type=output_prefs_data.get("artifact_type"),
            structure=output_prefs_data.get("structure"),
            language=output_prefs_data.get("language"),
            language_variant=output_prefs_data.get("language_variant"),
            tone=output_prefs_data.get("tone"),
            audience=output_prefs_data.get("audience"),
            length=output_prefs_data.get("length"),
            detail_level=output_prefs_data.get("detail_level"),
            format=output_prefs_data.get("format"),
        )

        entities = tuple(
            MentionedEntity(
                name=ent.get("name", ""),
                category=EntityCategory(ent.get("category", EntityCategory.OTHER.value)),
                qualifier=ent.get("qualifier"),
            )
            for ent in data.get("entities", ())
            if isinstance(ent, dict)
        )

        references = tuple(
            SemanticReference(
                expression=ref.get("expression", ""),
                kind=ReferenceKind(ref.get("kind", ReferenceKind.OTHER.value)),
                referent_hint=ref.get("referent_hint"),
                is_resolved=bool(ref.get("is_resolved", False)),
            )
            for ref in data.get("references", ())
            if isinstance(ref, dict)
        )

        temporal_references = tuple(
            TemporalReference(
                expression=tref.get("expression", ""),
                is_relative=bool(tref.get("is_relative", True)),
                anchor_event=tref.get("anchor_event"),
            )
            for tref in data.get("temporal_references", ())
            if isinstance(tref, dict)
        )

        attachments = tuple(
            AttachmentReference(
                identifier=att.get("identifier"),
                name=att.get("name"),
                mime_type=att.get("mime_type"),
                reference_expression=att.get("reference_expression"),
            )
            for att in data.get("attachments", ())
            if isinstance(att, dict)
        )

        dependencies = tuple(
            ContextDependency(
                description=dep.get("description", ""),
                category=ContextDependencyCategory(
                    dep.get("category", ContextDependencyCategory.CONTEXT_REQUIRED.value)
                ),
                unresolved_reference=dep.get("unresolved_reference"),
            )
            for dep in data.get("dependencies", ())
            if isinstance(dep, dict)
        )

        ambiguities = tuple(
            SemanticAmbiguity(
                kind=AmbiguityKind(amb.get("kind", AmbiguityKind.OTHER.value)),
                description=amb.get("description", ""),
                candidates=tuple(amb.get("candidates", ())),
            )
            for amb in data.get("ambiguities", ())
            if isinstance(amb, dict)
        )

        conf_data = data.get("confidence") or {}
        confidence = SemanticConfidence(
            goal=ConfidenceLevel(conf_data.get("goal", ConfidenceLevel.HIGH.value)),
            operations=ConfidenceLevel(conf_data.get("operations", ConfidenceLevel.HIGH.value)),
            references=ConfidenceLevel(conf_data.get("references", ConfidenceLevel.HIGH.value)),
            constraints=ConfidenceLevel(conf_data.get("constraints", ConfidenceLevel.HIGH.value)),
            overall=ConfidenceLevel(conf_data.get("overall", ConfidenceLevel.HIGH.value)),
        )

        return cls(
            raw_text=data.get("raw_text", ""),
            goal=goal,
            operations=operations,
            prompt_supplied_context=tuple(data.get("prompt_supplied_context", ())),
            constraints=constraints,
            output_preferences=output_preferences,
            entities=entities,
            references=references,
            temporal_references=temporal_references,
            attachments=attachments,
            dependencies=dependencies,
            ambiguities=ambiguities,
            confidence=confidence,
        )


@dataclass(frozen=True)
class ContextPack:
    """Output of Step 2 (Context Resolution): everything Step 3 needs."""

    decoded_request: DecodedRequest
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EdgeOutcome:
    """Result of an Edge Intelligence attempt: handled, or escalate."""

    handled: bool
    result: Optional[Any] = None
    escalate_reason: Optional[str] = None


@dataclass(frozen=True)
class IntelligenceResult:
    """Result from whichever intelligence tier (edge/local/extended) handled the turn."""

    tier: str
    output: Any
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FinalizedTurn:
    """Output of Finalization: the committed, user-facing result of a turn."""

    context_pack: ContextPack
    result: IntelligenceResult
