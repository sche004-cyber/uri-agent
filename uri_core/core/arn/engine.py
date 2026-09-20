"""Deterministic narrowing controller for ARN.1."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional

from uri_core.core.arn.models import (
    ARNState,
    ARNStatus,
    Candidate,
    ClarificationRecommendation,
    CostCeiling,
    EliminatedCandidate,
    EvidenceCategory,
    EvidenceItem,
    Route,
    SourceRecord,
    UserClue,
)


def _normalized(value: Any) -> str:
    return " ".join(str(value).strip().casefold().split())


def _is_empty_result(result: Any) -> bool:
    if result is None:
        return True
    if isinstance(result, dict):
        status = _normalized(result.get("status", ""))
        if status in {"not_found", "not found", "empty"}:
            return True
        if result.get("data") is not None:
            return _is_empty_result(result["data"])
        return not result
    if isinstance(result, (str, list, tuple, set)):
        return len(result) == 0
    return False


class ARNEngine:
    def __init__(
        self,
        *,
        state: Optional[ARNState] = None,
        cost_ceiling: Optional[CostCeiling] = None,
    ) -> None:
        self.state = state
        self.cost_ceiling = cost_ceiling or CostCeiling()

    def _require_state(self) -> ARNState:
        if self.state is None:
            raise RuntimeError("ARN recovery has not been triggered")
        return self.state

    def _require_active(self) -> ARNState:
        state = self._require_state()
        if state.status is not ARNStatus.ACTIVE:
            raise RuntimeError(f"ARN state is terminal: {state.status.value}")
        return state

    def trigger_recovery(
        self, goal: str, initial_query: str, empty_result: Any
    ) -> ARNState:
        if not _is_empty_result(empty_result):
            raise ValueError("recovery requires an empty or NOT_FOUND result")
        if self.state is None:
            self.state = ARNState(task_goal=goal)
        elif self.state.task_goal != goal:
            raise ValueError("an ARN engine cannot change task_goal mid-task")
        if not self.is_search_repeated("initial_lookup", initial_query):
            self.record_source_checked(
                "initial_lookup", initial_query, empty_result
            )
        return self.state

    def record_source_checked(self, source: str, query: str, result: Any) -> bool:
        state = self._require_active()
        if self.is_search_repeated(source, query):
            return False
        state.sources_checked.append(
            SourceRecord(source=source, query=query, result_summary=result)
        )
        state.cost_spent.add(searches=1, cost_units=1)
        self.check_budget()
        return True

    def is_search_repeated(self, source: str, query: str) -> bool:
        if self.state is None:
            return False
        key = (_normalized(source), _normalized(query))
        if any(
            (_normalized(record.source), _normalized(record.query)) == key
            for record in self.state.sources_checked
        ):
            return True
        for eliminated in self.state.eliminated:
            metadata = eliminated.candidate.metadata
            eliminated_key = (
                _normalized(metadata.get("source", "")),
                _normalized(metadata.get("query", "")),
            )
            if eliminated_key == key:
                return True
        return False

    def add_candidates(self, candidates: Iterable[Candidate]) -> List[Candidate]:
        state = self._require_active()
        existing = {candidate.candidate_id for candidate in state.candidates}
        ruled_out = {
            eliminated.candidate.candidate_id for eliminated in state.eliminated
        }
        added: List[Candidate] = []
        for candidate in candidates:
            if not isinstance(candidate, Candidate):
                raise TypeError("candidates must contain Candidate records")
            if candidate.candidate_id in existing or candidate.candidate_id in ruled_out:
                continue
            state.candidates.append(candidate)
            existing.add(candidate.candidate_id)
            added.append(candidate)
        return added

    def eliminate_candidate(self, candidate_id: str, reason: str) -> EliminatedCandidate:
        state = self._require_active()
        if not reason or not reason.strip():
            raise ValueError("elimination reason must be non-empty")
        for index, candidate in enumerate(state.candidates):
            if candidate.candidate_id == candidate_id:
                state.candidates.pop(index)
                eliminated = EliminatedCandidate(candidate=candidate, reason=reason)
                state.eliminated.append(eliminated)
                return eliminated
        if any(item.candidate.candidate_id == candidate_id for item in state.eliminated):
            raise ValueError(f"candidate '{candidate_id}' is already eliminated")
        raise KeyError(candidate_id)

    def apply_user_clue(self, clue: UserClue) -> List[Candidate]:
        state = self._require_active()
        if not isinstance(clue, UserClue):
            raise TypeError("clue must be a UserClue record")
        had_candidates = bool(state.candidates)
        state.user_clues.append(clue)
        expected = _normalized(clue.value)
        for candidate in list(state.candidates):
            actual = candidate.metadata.get(clue.axis)
            if _normalized(actual) != expected:
                self.eliminate_candidate(
                    candidate.candidate_id,
                    f"user clue {clue.axis}={clue.value!r} did not match",
                )
        if had_candidates and not state.candidates:
            state.status = ARNStatus.USER_ELIMINATED_ALL
            state.termination_reason = "user_clue_eliminated_all_candidates"
        return list(state.candidates)

    def add_evidence(self, evidence: EvidenceItem) -> None:
        state = self._require_active()
        if not isinstance(evidence, EvidenceItem):
            raise TypeError("evidence must be an EvidenceItem")
        state.evidence.append(evidence)

    def reclassify_evidence(
        self, index: int, category: EvidenceCategory
    ) -> EvidenceItem:
        state = self._require_active()
        replacement = state.evidence[index].reclassify(category)
        state.evidence[index] = replacement
        return replacement

    def record_cost(
        self,
        *,
        searches: int = 0,
        sources_opened: int = 0,
        candidates_opened: int = 0,
        pages: int = 0,
        cost_units: int = 0,
    ) -> bool:
        state = self._require_active()
        state.cost_spent.add(
            searches=searches,
            sources_opened=sources_opened,
            candidates_opened=candidates_opened,
            pages=pages,
            cost_units=cost_units,
        )
        return self.check_budget()

    def check_budget(self) -> bool:
        state = self._require_state()
        if state.status is not ARNStatus.ACTIVE:
            return state.status is not ARNStatus.EXHAUSTED
        if state.cost_spent.ceiling_reached(self.cost_ceiling):
            state.status = ARNStatus.EXHAUSTED
            state.termination_reason = "cost_ceiling_reached"
            return False
        return True

    def mark_exhausted(self, reason: str = "all_avenues_tried") -> ARNState:
        state = self._require_active()
        state.status = ARNStatus.EXHAUSTED
        state.termination_reason = reason
        return state

    def resolve_found(self, candidate: Candidate, route: Route) -> ARNState:
        state = self._require_active()
        if not isinstance(candidate, Candidate) or not isinstance(route, Route):
            raise TypeError("candidate and route must use ARN contract types")
        if candidate.candidate_id not in {item.candidate_id for item in state.candidates}:
            self.add_candidates([candidate])
        state.successful_route = route
        state.status = ARNStatus.FOUND
        state.termination_reason = None
        return state

    def get_clarification_recommendation(
        self,
    ) -> Optional[ClarificationRecommendation]:
        state = self._require_state()
        if state.status is not ARNStatus.ACTIVE or len(state.candidates) < 2:
            return None
        axes: List[str] = []
        for candidate in state.candidates:
            for axis in candidate.metadata:
                if axis not in axes and axis not in {"source", "query"}:
                    axes.append(axis)
        choices = []
        for axis_index, axis in enumerate(axes):
            groups: Dict[str, List[str]] = defaultdict(list)
            for candidate in state.candidates:
                if axis in candidate.metadata and candidate.metadata[axis] is not None:
                    groups[str(candidate.metadata[axis])].append(candidate.candidate_id)
            if len(groups) < 2 or sum(map(len, groups.values())) != len(state.candidates):
                continue
            sizes = [len(ids) for ids in groups.values()]
            choices.append((max(sizes), max(sizes) - min(sizes), axis_index, axis, groups))
        if not choices:
            return None
        _, _, _, axis, groups = min(choices, key=lambda item: item[:3])
        plain_groups = dict(groups)
        return ClarificationRecommendation(
            suggested_axis=axis,
            candidate_groups=plain_groups,
            why=(
                f"{len(state.candidates)} candidates split into "
                f"{len(plain_groups)} non-degenerate groups by {axis}."
            ),
        )

    def get_case_summary(self) -> Dict[str, Any]:
        state = self._require_state()
        recommendation = self.get_clarification_recommendation()
        summary = state.to_dict()
        summary["clarification_recommendation"] = (
            recommendation.to_dict() if recommendation is not None else None
        )
        return summary
