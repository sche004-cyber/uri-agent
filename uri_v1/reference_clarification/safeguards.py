"""Parameterized progress and per-turn budget guards."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ClarificationSafeguards:
    max_no_progress_rounds: int
    max_turn_cost: int
    no_progress_rounds: int = 0
    cost_spent: int = 0

    def charge(self, *, cost: int = 1, made_progress: bool = False) -> bool:
        if cost < 0:
            raise ValueError("negative cost")
        self.cost_spent += cost
        self.no_progress_rounds = 0 if made_progress else self.no_progress_rounds + 1
        return self.cost_spent <= self.max_turn_cost and self.no_progress_rounds <= self.max_no_progress_rounds
