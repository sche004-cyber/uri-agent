"""Adaptive Retrieval Narrowing deterministic core (ARN.1)."""

from uri_core.core.arn.engine import ARNEngine
from uri_core.core.arn.integration import (
    attach_not_found_recovery,
    is_not_found_result,
    trigger_not_found_recovery,
)
from uri_core.core.arn.models import (
    ARNState,
    ARNStatus,
    Candidate,
    ClarificationRecommendation,
    CostAccumulator,
    CostCeiling,
    EliminatedCandidate,
    EvidenceCategory,
    EvidenceItem,
    EvidencePromotionError,
    Route,
    SourceRecord,
    UserClue,
)

__all__ = [
    "ARNEngine",
    "ARNState",
    "ARNStatus",
    "Candidate",
    "ClarificationRecommendation",
    "CostAccumulator",
    "CostCeiling",
    "EliminatedCandidate",
    "EvidenceCategory",
    "EvidenceItem",
    "EvidencePromotionError",
    "Route",
    "SourceRecord",
    "UserClue",
    "attach_not_found_recovery",
    "is_not_found_result",
    "trigger_not_found_recovery",
]
