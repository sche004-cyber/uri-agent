"""RAR — Reference Anchor Resolution Contracts (Batch A2.5).

Architectural Distinction:
- RAR (Reference Anchor Resolution):
    "Which already-known candidate does this user reference bind to?"
    Stateless, single-turn, bounded candidate set. Answers: "Which one of these
    already-known objects does the user mean?"
- ARN (Adaptive Retrieval Narrowing):
    "The required object is not sufficiently known; perform bounded search/recovery/narrowing."
    Stateful recovery engine triggered when search returns NOT_FOUND (prototype uri_core.core.arn).

Core RAR Rule:
- Zero candidate invention.
- A resolved candidate ID MUST strictly belong to the supplied candidate set.
- An ambiguous candidate set MUST strictly contain members of the supplied candidate set.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Sequence, Tuple


class RAROutcome(str, Enum):
    """Strict tri-state outcome for Reference Anchor Resolution."""

    RESOLVED = "RESOLVED"
    UNKNOWN = "UNKNOWN"
    AMBIGUOUS = "AMBIGUOUS"


class RARBasis(str, Enum):
    """How the resolution decision was reached."""

    DETERMINISTIC_ANCHOR = "DETERMINISTIC_ANCHOR"
    MODEL_SELECTION = "MODEL_SELECTION"


class RARFailureClass(str, Enum):
    """Stable structured failure taxonomy for unresolved references."""

    NO_CANDIDATE = "NO_CANDIDATE"
    MULTIPLE_PLAUSIBLE = "MULTIPLE_PLAUSIBLE"
    PRONOUN_BINDING = "PRONOUN_BINDING"
    TEMPORAL_RELATION = "TEMPORAL_RELATION"
    REVISION_RELATION = "REVISION_RELATION"
    OWNERSHIP_RELATION = "OWNERSHIP_RELATION"
    CONTRAST_SELECTION = "CONTRAST_SELECTION"
    CROSS_REFERENCE = "CROSS_REFERENCE"
    INSUFFICIENT_METADATA = "INSUFFICIENT_METADATA"
    SEMANTIC_DISCRIMINATION = "SEMANTIC_DISCRIMINATION"


class RARDriverRule(str, Enum):
    """Fine-grained deterministic rule attribution."""

    EXACT_ID = "EXACT_ID"
    EXACT_ALIAS = "EXACT_ALIAS"
    CURRENT_ATTACHMENT = "CURRENT_ATTACHMENT"
    ACTIVE_UI = "ACTIVE_UI"
    EXACT_TITLE = "EXACT_TITLE"
    ACTIVE_POINTER = "ACTIVE_POINTER"
    TYPE_FILTER = "TYPE_FILTER"
    CONTRAST_FILTER = "CONTRAST_FILTER"
    TEMPORAL_RELATION = "TEMPORAL_RELATION"
    REVISION_RELATION = "REVISION_RELATION"
    TERM_DISCRIMINATION = "TERM_DISCRIMINATION"
    NONE = "NONE"


class RARContractViolationError(ValueError):
    """Raised when an RAR resolution violates contract invariants (e.g. candidate invention)."""


@dataclass(frozen=True)
class RARCandidate:
    """An object candidate in the bounded candidate set supplied to RAR."""

    id: str
    title: str
    candidate_type: str  # e.g., "document", "email", "workflow", "person", "spreadsheet", "media"
    recency_rank: int = 0  # 0 is most recent, 1 is previous, etc.
    domain_tags: Tuple[str, ...] = ()
    owner: Optional[str] = None
    is_attachment: bool = False
    exact_aliases: Tuple[str, ...] = ()
    description: Optional[str] = None


@dataclass(frozen=True)
class RAREvidence:
    """Local turn evidence pre-extracted from TurnFrame for resolving a reference."""

    clause_text: str = ""
    negation_spans: Tuple[str, ...] = ()
    candidate_verbs: Tuple[str, ...] = ()
    recency_hint: Optional[str] = None  # e.g., "previous", "revised", "latest", "same", "earlier"
    target_type_hint: Optional[str] = None  # e.g., "document", "email", "person", "spreadsheet"


@dataclass(frozen=True)
class RARDeterministicAnchor:
    """Deterministic cues known with certainty before any model call."""

    exact_id: Optional[str] = None
    unique_title_match: Optional[str] = None
    deterministic_recency: Optional[str] = None
    current_attachment_id: Optional[str] = None
    selected_ui_id: Optional[str] = None

    @property
    def has_any_anchor(self) -> bool:
        return any(
            x is not None
            for x in (
                self.exact_id,
                self.unique_title_match,
                self.deterministic_recency,
                self.current_attachment_id,
                self.selected_ui_id,
            )
        )


@dataclass(frozen=True)
class RARQuery:
    """Model-neutral input query for resolving a single reference expression."""

    reference_expression: str
    candidates: Tuple[RARCandidate, ...] = ()
    local_evidence: RAREvidence = field(default_factory=RAREvidence)
    deterministic_anchor: Optional[RARDeterministicAnchor] = None

    @property
    def candidate_ids(self) -> Tuple[str, ...]:
        return tuple(c.id for c in self.candidates)

    def get_candidate(self, candidate_id: str) -> Optional[RARCandidate]:
        for c in self.candidates:
            if c.id == candidate_id:
                return c
        return None


@dataclass(frozen=True)
class RARResolution:
    """Result of Reference Anchor Resolution."""

    reference_expression: str
    outcome: RAROutcome
    candidate_id: Optional[str] = None
    ambiguous_candidate_ids: Tuple[str, ...] = ()
    basis: RARBasis = RARBasis.MODEL_SELECTION
    raw_confidence: Optional[float] = None
    failure_class: Optional[RARFailureClass] = None
    rule_used: Optional[RARDriverRule] = None


def validate_rar_resolution(
    resolution: RARResolution,
    candidates: Sequence[RARCandidate],
) -> None:
    """Strictly validates RAR invariants against candidate set.

    Invariants enforced:
    1. If RESOLVED:
       - candidate_id must be non-None and non-empty.
       - candidate_id MUST be a member of candidates (Anti-Invention Gate).
       - ambiguous_candidate_ids must be empty.
    2. If AMBIGUOUS:
       - candidate_id must be None.
       - ambiguous_candidate_ids must contain at least 2 items.
       - EVERY item in ambiguous_candidate_ids MUST be a member of candidates.
    3. If UNKNOWN:
       - candidate_id must be None.
       - ambiguous_candidate_ids must be empty.
    """
    candidate_ids = {c.id for c in candidates}

    if resolution.outcome == RAROutcome.RESOLVED:
        if not resolution.candidate_id:
            raise RARContractViolationError(
                f"RAR outcome is RESOLVED but candidate_id is empty/None: {resolution}"
            )
        if resolution.candidate_id not in candidate_ids:
            raise RARContractViolationError(
                f"Candidate invention detected! Resolved ID {resolution.candidate_id!r} "
                f"is not in candidate set: {sorted(candidate_ids)}"
            )
        if resolution.ambiguous_candidate_ids:
            raise RARContractViolationError(
                f"RAR outcome is RESOLVED but ambiguous_candidate_ids is non-empty: {resolution.ambiguous_candidate_ids}"
            )

    elif resolution.outcome == RAROutcome.AMBIGUOUS:
        if resolution.candidate_id is not None:
            raise RARContractViolationError(
                f"RAR outcome is AMBIGUOUS but candidate_id is set: {resolution.candidate_id!r}"
            )
        if len(resolution.ambiguous_candidate_ids) < 2:
            raise RARContractViolationError(
                f"RAR outcome is AMBIGUOUS but fewer than 2 ambiguous_candidate_ids provided: {resolution.ambiguous_candidate_ids}"
            )
        for cid in resolution.ambiguous_candidate_ids:
            if cid not in candidate_ids:
                raise RARContractViolationError(
                    f"Candidate invention in ambiguity set! ID {cid!r} is not in candidate set: {sorted(candidate_ids)}"
                )

    elif resolution.outcome == RAROutcome.UNKNOWN:
        if resolution.candidate_id is not None:
            raise RARContractViolationError(
                f"RAR outcome is UNKNOWN but candidate_id is set: {resolution.candidate_id!r}"
            )
        if resolution.ambiguous_candidate_ids:
            raise RARContractViolationError(
                f"RAR outcome is UNKNOWN but ambiguous_candidate_ids is non-empty: {resolution.ambiguous_candidate_ids}"
            )
    else:
        raise RARContractViolationError(f"Unrecognized RAROutcome: {resolution.outcome}")


def resolve_rar_deterministically(query: RARQuery) -> Optional[RARResolution]:
    """Zero-model deterministic anchor evaluation path.

    Returns RARResolution with basis=DETERMINISTIC_ANCHOR if a deterministic match exists,
    or None if escalation to model evaluation is required.
    """
    candidate_map = {c.id: c for c in query.candidates}

    # 1. Check explicit deterministic anchors
    anchor = query.deterministic_anchor
    if anchor is not None:
        # Selected UI foreground item
        if anchor.selected_ui_id and anchor.selected_ui_id in candidate_map:
            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.RESOLVED,
                candidate_id=anchor.selected_ui_id,
                basis=RARBasis.DETERMINISTIC_ANCHOR,
            )
            validate_rar_resolution(res, query.candidates)
            return res

        # Foreground current attachment
        if anchor.current_attachment_id and anchor.current_attachment_id in candidate_map:
            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.RESOLVED,
                candidate_id=anchor.current_attachment_id,
                basis=RARBasis.DETERMINISTIC_ANCHOR,
            )
            validate_rar_resolution(res, query.candidates)
            return res

        # Explicit pasted/referenced ID
        if anchor.exact_id and anchor.exact_id in candidate_map:
            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.RESOLVED,
                candidate_id=anchor.exact_id,
                basis=RARBasis.DETERMINISTIC_ANCHOR,
            )
            validate_rar_resolution(res, query.candidates)
            return res

        # Verbatim unique title match
        if anchor.unique_title_match and anchor.unique_title_match in candidate_map:
            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.RESOLVED,
                candidate_id=anchor.unique_title_match,
                basis=RARBasis.DETERMINISTIC_ANCHOR,
            )
            validate_rar_resolution(res, query.candidates)
            return res

    # 2. Check verbatim reference expression match against candidate ID or exact aliases
    ref_norm = query.reference_expression.strip().lower()
    for c in query.candidates:
        if ref_norm == c.id.strip().lower() or any(ref_norm == a.strip().lower() for a in c.exact_aliases):
            res = RARResolution(
                reference_expression=query.reference_expression,
                outcome=RAROutcome.RESOLVED,
                candidate_id=c.id,
                basis=RARBasis.DETERMINISTIC_ANCHOR,
            )
            validate_rar_resolution(res, query.candidates)
            return res

    return None


@dataclass(frozen=True)
class RARFixture:
    """Diagnostic qualification fixture for evaluating Reference Anchor Resolution."""

    id: str
    name: str
    category: str
    turn_text: str
    query: RARQuery
    expected_outcome: RAROutcome
    expected_candidate_id: Optional[str] = None
    expected_ambiguous_candidate_ids: Tuple[str, ...] = ()
    expected_basis: Optional[RARBasis] = None
    description: str = ""

    def __post_init__(self):
        # Validate that expected resolution obeys invariants
        pseudo_res = RARResolution(
            reference_expression=self.query.reference_expression,
            outcome=self.expected_outcome,
            candidate_id=self.expected_candidate_id,
            ambiguous_candidate_ids=self.expected_ambiguous_candidate_ids,
            basis=self.expected_basis or RARBasis.MODEL_SELECTION,
        )
        validate_rar_resolution(pseudo_res, self.query.candidates)
