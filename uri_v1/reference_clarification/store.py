"""Process-local S1 clarification and binding records."""

from __future__ import annotations

from dataclasses import dataclass

from uri_v1.turn.rar_clarification_contract import BindingState, ClarificationContract
from uri_v1.turn.rar_contracts import RARQuery


@dataclass
class StoredRound:
    contract: ClarificationContract
    query: RARQuery
    state: BindingState
    used: bool = False


@dataclass
class BindingRecord:
    ambiguity_id: str
    session_id: str
    candidate_id: str
    state: BindingState
    fingerprint: str
    applied_result_exists: bool = False
    from_change: bool = False
    prior_binding_id: str | None = None
    redo_reason: str | None = None
    superseded_by: str | None = None


class InMemoryClarificationStore:
    def __init__(self) -> None:
        self.rounds: dict[str, StoredRound] = {}
        self.bindings: dict[str, BindingRecord] = {}
        self.binding_queries: dict[str, RARQuery] = {}

    def add_round(self, contract: ClarificationContract, query: RARQuery,
                  state: BindingState = BindingState.PENDING) -> None:
        if contract.ambiguity_id in self.rounds:
            raise ValueError("duplicate ambiguity ID")
        self.rounds[contract.ambiguity_id] = StoredRound(contract, query, state)
