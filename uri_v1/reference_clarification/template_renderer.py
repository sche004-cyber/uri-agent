"""Deterministic S1 wording from slot-scoped facts."""

from __future__ import annotations

from uri_v1.turn.rar_clarification_contract import ClarificationContract, ClarificationKind, ESCAPE_LABEL
from .render_contracts import RenderOutput, make_render_request


def render_template(contract: ClarificationContract) -> RenderOutput:
    request = make_render_request(contract)
    reference = request.reference
    if request.kind == ClarificationKind.CHOOSE_ONE:
        question = f'Which item do you mean by "{reference}"?'
    elif request.kind == ClarificationKind.CONFIRM_ONE:
        question = ""
    elif request.kind == ClarificationKind.CHOOSE_ATTRIBUTE:
        question = f'Which {request.axis} matches "{reference}"?'
    else:
        question = f'I could not find what "{reference}" refers to. What should I use?'
    if request.overflow:
        question += f" There are {request.overflow} other matches; you can enter one."
    labels = []
    for key, facts_tuple in request.slots:
        facts = dict(facts_tuple)
        if request.kind == ClarificationKind.CHOOSE_ATTRIBUTE:
            label = facts["value"]
        else:
            title = facts.get("title") or facts.get("type") or key
            details = [facts[k] for k in ("owner", "recency", "modified", "version", "locator", "type") if k in facts]
            label = " · ".join((title, *details))
        labels.append((key, label))
    if request.kind == ClarificationKind.CONFIRM_ONE:
        question = f"Did you mean {labels[0][1]}?"
    return RenderOutput(question, tuple(labels))


def presented_options(contract: ClarificationContract, output: RenderOutput) -> tuple[tuple[str, str], ...]:
    """URI appends the escape; renderer cannot remove it."""
    return output.labels + (("escape", ESCAPE_LABEL),)
