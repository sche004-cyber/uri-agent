"""Stable fingerprints for the complete RAR candidate and round scope."""

from __future__ import annotations

import hashlib
import json
from typing import Sequence, Tuple

from uri_v1.turn.rar_contracts import RARCandidate
from uri_v1.turn.rar_clarification_contract import AttributeOption


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def candidate_fingerprint(candidate: RARCandidate) -> str:
    return _digest((candidate.id, candidate.title, candidate.candidate_type,
                    candidate.recency_rank, candidate.domain_tags, candidate.owner,
                    candidate.is_attachment, candidate.exact_aliases, candidate.description))


def candidate_set_fingerprint(
    scope_fingerprints: Sequence[Tuple[str, str]],
    attribute_options: Sequence[AttributeOption] = (),
) -> str:
    return _digest((tuple(scope_fingerprints), tuple((o.option_key, o.axis, o.value,
                    o.member_candidate_ids) for o in attribute_options)))
