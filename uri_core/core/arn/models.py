"""Typed, task-scoped contracts for Adaptive Retrieval Narrowing (ARN).

The records in this module are bookkeeping only.  They carry no capability,
credential, permission, approval, or execution authority and are never
persisted by ARN.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EvidenceCategory(str, Enum):
    VERIFIED_FACT = "VERIFIED_FACT"
    USER_CLUE = "USER_CLUE"
    EDGE_DEDUCTION = "EDGE_DEDUCTION"
    ELIMINATED_CANDIDATE = "ELIMINATED_CANDIDATE"
    SOURCE_POINTER = "SOURCE_POINTER"
    UNRESOLVED_QUESTION = "UNRESOLVED_QUESTION"


class EvidencePromotionError(ValueError):
    """Raised when untrusted deduction is promoted to verified fact."""


@dataclass(frozen=True)
class EvidenceItem:
    category: EvidenceCategory
    value: Any
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def reclassify(self, category: EvidenceCategory) -> "EvidenceItem":
        category = EvidenceCategory(category)
        if (
            self.category is EvidenceCategory.EDGE_DEDUCTION
            and category is EvidenceCategory.VERIFIED_FACT
        ):
            raise EvidencePromotionError(
                "EDGE_DEDUCTION cannot be promoted to VERIFIED_FACT"
            )
        return EvidenceItem(
            category=category,
            value=self.value,
            source=self.source,
            metadata=dict(self.metadata),
        )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["category"] = self.category.value
        return data


@dataclass(frozen=True)
class SourceRecord:
    source: str
    query: str
    result_summary: Any
    checked_at: str = field(default_factory=utc_now)


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    label: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EliminatedCandidate:
    candidate: Candidate
    reason: str
    eliminated_at: str = field(default_factory=utc_now)
    category: EvidenceCategory = EvidenceCategory.ELIMINATED_CANDIDATE


@dataclass(frozen=True)
class UserClue:
    axis: str
    value: Any
    received_at: str = field(default_factory=utc_now)
    category: EvidenceCategory = EvidenceCategory.USER_CLUE


@dataclass(frozen=True)
class Route:
    source: str
    locator: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ClarificationRecommendation:
    suggested_axis: str
    candidate_groups: Dict[str, List[str]]
    why: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CostCeiling:
    """Configurable ceiling; reaching any configured maximum exhausts ARN."""

    max_searches: int = 20
    max_sources_opened: int = 20
    max_pages: int = 100
    max_sources_checked: Optional[int] = None
    max_candidates: int = 50
    max_cost_units: int = 200

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if value is not None and (not isinstance(value, int) or value <= 0):
                raise ValueError(f"{name} must be a positive integer")


@dataclass
class CostAccumulator:
    sources_queried: int = 0
    sources_opened: int = 0
    candidates_opened: int = 0
    pages_scanned: int = 0
    cost_units: int = 0

    @property
    def sources_checked(self) -> int:
        return self.sources_queried

    def add(
        self,
        *,
        searches: int = 0,
        sources_opened: int = 0,
        candidates_opened: int = 0,
        pages: int = 0,
        cost_units: int = 0,
    ) -> None:
        increments = {
            "searches": searches,
            "sources_opened": sources_opened,
            "candidates_opened": candidates_opened,
            "pages": pages,
            "cost_units": cost_units,
        }
        if any(not isinstance(value, int) or value < 0 for value in increments.values()):
            raise ValueError("cost increments must be non-negative integers")
        self.sources_queried += searches
        self.sources_opened += sources_opened
        self.candidates_opened += candidates_opened
        self.pages_scanned += pages
        self.cost_units += cost_units

    def ceiling_reached(self, ceiling: CostCeiling) -> bool:
        source_limit = ceiling.max_sources_checked or ceiling.max_searches
        return any(
            (
                self.sources_queried >= ceiling.max_searches,
                self.sources_queried >= source_limit,
                self.sources_opened >= ceiling.max_sources_opened,
                self.candidates_opened >= ceiling.max_candidates,
                self.pages_scanned >= ceiling.max_pages,
                self.cost_units >= ceiling.max_cost_units,
            )
        )


class ARNStatus(str, Enum):
    ACTIVE = "ACTIVE"
    FOUND = "FOUND"
    USER_ELIMINATED_ALL = "USER_ELIMINATED_ALL"
    EXHAUSTED = "EXHAUSTED"


@dataclass
class ARNState:
    task_goal: str
    sources_checked: List[SourceRecord] = field(default_factory=list)
    candidates: List[Candidate] = field(default_factory=list)
    eliminated: List[EliminatedCandidate] = field(default_factory=list)
    user_clues: List[UserClue] = field(default_factory=list)
    clarification_asked: bool = False
    successful_route: Optional[Route] = None
    cost_spent: CostAccumulator = field(default_factory=CostAccumulator)
    status: ARNStatus = ARNStatus.ACTIVE
    evidence: List[EvidenceItem] = field(default_factory=list)
    termination_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.task_goal, str) or not self.task_goal.strip():
            raise ValueError("task_goal must be a non-empty string")

    def to_dict(self) -> Dict[str, Any]:
        def convert(value: Any) -> Any:
            if isinstance(value, Enum):
                return value.value
            if hasattr(value, "to_dict"):
                return value.to_dict()
            if hasattr(value, "__dataclass_fields__"):
                return {key: convert(item) for key, item in asdict(value).items()}
            if isinstance(value, list):
                return [convert(item) for item in value]
            if isinstance(value, dict):
                return {key: convert(item) for key, item in value.items()}
            return value

        return {key: convert(value) for key, value in self.__dict__.items()}
