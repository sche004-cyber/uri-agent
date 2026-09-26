"""S1 port of ARN.1 axis recommendation and clue elimination semantics."""

from __future__ import annotations

from typing import Sequence

from uri_v1.turn.rar_contracts import RARCandidate
from uri_v1.turn.rar_clarification_contract import AXES
from .facts import fact_value


def normalized(value: object) -> str:
    return " ".join(str(value).strip().casefold().split())


def apply_user_clue(candidates: Sequence[RARCandidate], axis: str, value: str) -> tuple[RARCandidate, ...]:
    if axis not in AXES:
        raise ValueError("unsupported attribute axis")
    expected = normalized(value)
    return tuple(c for c in candidates if (actual := fact_value(c, axis)) is not None
                 and normalized(actual) == expected)


def recommend_axis(candidates: Sequence[RARCandidate], answered_axes: Sequence[str] = (),
                   max_options: int = 5) -> tuple[str, dict[str, tuple[str, ...]]] | None:
    if len(candidates) < 2:
        return None
    choices = []
    for index, axis in enumerate(AXES):
        if axis in answered_axes:
            continue
        normalized_groups: dict[str, tuple[str, list[str]]] = {}
        for candidate in candidates:
            value = fact_value(candidate, axis)
            if value is None:
                break
            key = normalized(value)
            if key not in normalized_groups:
                normalized_groups[key] = (value, [])
            normalized_groups[key][1].append(candidate.id)
        else:
            groups = {value: ids for value, ids in normalized_groups.values()}
            if 2 <= len(groups) <= max_options:
                sizes = [len(ids) for ids in groups.values()]
                choices.append((max(sizes), max(sizes) - min(sizes), index, axis, groups))
    if not choices:
        return None
    _, _, _, axis, groups = min(choices, key=lambda item: item[:3])
    return axis, {value: tuple(ids) for value, ids in groups.items()}
