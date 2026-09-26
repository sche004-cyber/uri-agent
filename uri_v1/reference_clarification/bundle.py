"""Multi-reference presentation and dependency rebuilding."""

from __future__ import annotations

from dataclasses import replace
from typing import Callable

from uri_v1.turn.rar_clarification_contract import BindingState, ClarificationBundle, ReferenceSlot, validate_bundle
from uri_v1.turn.rar_contracts import RARQuery
from .builder import build_clarification


def visible_slots(bundle: ClarificationBundle, states: dict[str, BindingState]) -> tuple[ReferenceSlot, ...]:
    validate_bundle(bundle)
    return tuple(slot for slot in bundle.slots
                 if states.get(slot.ref_key, BindingState.PENDING) in (BindingState.PENDING, BindingState.CHANGE_PENDING)
                 and all(states.get(parent) == BindingState.CONFIRMED for parent in slot.depends_on))


def rebuild_dependent(bundle: ClarificationBundle, ref_key: str, *,
                      fresh_query: RARQuery, session_id: str, turn_id: str,
                      wrong_binding_impact: str | None,
                      parent_states: dict[str, BindingState],
                      parent_locator: str,
                      candidate_locators: dict[str, str]) -> ClarificationBundle:
    validate_bundle(bundle)
    slot = next((s for s in bundle.slots if s.ref_key == ref_key), None)
    if slot is None or not slot.depends_on:
        raise ValueError("not a dependent slot")
    if any(parent_states.get(parent) != BindingState.CONFIRMED for parent in slot.depends_on):
        raise ValueError("dependent parents are not confirmed")
    from uri_v1.turn.rar_deterministic import resolve_rar_deterministic_extended
    result = build_clarification(fresh_query, resolve_rar_deterministic_extended(fresh_query).resolution,
        session_id=session_id, turn_id=turn_id, wrong_binding_impact=wrong_binding_impact,
        provenance_required=True, parent_locator=parent_locator,
        candidate_locators=candidate_locators)
    if result.contract is None:
        raise ValueError("dependent slot did not need clarification")
    slots = tuple(replace(s, contract=result.contract) if s.ref_key == ref_key else s for s in bundle.slots)
    rebuilt = replace(bundle, slots=slots)
    validate_bundle(rebuilt)
    return rebuilt
