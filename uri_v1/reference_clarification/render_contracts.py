"""Slot-only renderer boundary; candidate IDs never leave the contract."""

from __future__ import annotations

from dataclasses import dataclass

from uri_v1.turn.rar_clarification_contract import ClarificationContract, ClarificationKind


@dataclass(frozen=True)
class RenderRequest:
    kind: ClarificationKind
    reference: str
    slots: tuple[tuple[str, tuple[tuple[str, str], ...]], ...]
    overflow: int = 0
    axis: str | None = None
    scope_count: int = 0


@dataclass(frozen=True)
class RenderOutput:
    question: str
    labels: tuple[tuple[str, str], ...]


def make_render_request(contract: ClarificationContract) -> RenderRequest:
    if contract.kind == ClarificationKind.CHOOSE_ATTRIBUTE:
        slots = tuple((o.option_key, (("value", o.value),)) for o in contract.attribute_options)
    else:
        slots = tuple((c.option_key, tuple((f.key, f.value) for f in c.display_facts)) for c in contract.candidates)
    return RenderRequest(contract.kind, contract.original_reference, slots,
                         contract.overflow_count, contract.attribute_axis,
                         len(contract.scope_candidate_ids))
