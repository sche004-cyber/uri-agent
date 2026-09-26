"""Project only grounded RARCandidate fields into S1 display facts."""

from __future__ import annotations

from uri_v1.turn.rar_contracts import RARCandidate
from uri_v1.turn.rar_clarification_contract import CandidateFact


def fact_value(candidate: RARCandidate, axis: str) -> str | None:
    if axis == "title":
        return candidate.title or None
    if axis == "type":
        return candidate.candidate_type or None
    if axis == "owner":
        return candidate.owner or None
    if axis == "recency":
        return f"recency {candidate.recency_rank}"
    return None


def project_facts(candidate: RARCandidate, sources: dict[str, str] | None = None) -> tuple[CandidateFact, ...]:
    sources = sources or {}
    return tuple(CandidateFact(key, value, sources.get(key, "")) for key in ("title", "type", "owner", "recency")
                 if (value := fact_value(candidate, key)) is not None)
