"""Session-local evidence may annotate or reorder ties but never bind."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SessionEvidence:
    session_id: str
    selections: list[str] = field(default_factory=list)
    clues: list[tuple[str, str]] = field(default_factory=list)
    corrections: list[tuple[str, str]] = field(default_factory=list)

    def record_selection(self, candidate_id: str) -> None:
        self.selections.append(candidate_id)

    def record_clue(self, axis: str, value: str) -> None:
        self.clues.append((axis, value))

    def record_correction(self, old_id: str, new_id: str) -> None:
        self.corrections.append((old_id, new_id))
