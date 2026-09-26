"""S1 reference clarification records and fail-closed contract validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple

from .rar_contracts import RARQuery


class ClarificationKind(str, Enum):
    CHOOSE_ONE = "CHOOSE_ONE"
    CONFIRM_ONE = "CONFIRM_ONE"
    CHOOSE_ATTRIBUTE = "CHOOSE_ATTRIBUTE"
    FREE_INPUT_ONLY = "FREE_INPUT_ONLY"


class ClarificationOptionKind(str, Enum):
    CANDIDATE = "CANDIDATE"
    ATTRIBUTE = "ATTRIBUTE"


class ResponseKind(str, Enum):
    CANDIDATE = "CANDIDATE"
    ATTRIBUTE = "ATTRIBUTE"
    FREE_INPUT = "FREE_INPUT"


class BindingState(str, Enum):
    PENDING = "PENDING"
    TENTATIVE = "TENTATIVE"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CHANGE_PENDING = "CHANGE_PENDING"
    REBIND_CHECK = "REBIND_CHECK"
    CHANGE_ABANDONED = "CHANGE_ABANDONED"
    TENTATIVE_APPLIED = "TENTATIVE_APPLIED"
    APPLIED = "APPLIED"
    REDO_AUTHORIZED = "REDO_AUTHORIZED"
    REDO_NOT_EXECUTED = "REDO_NOT_EXECUTED"
    REDONE = "REDONE"


class WrongBindingImpact(str, Enum):
    NONE = "NONE"
    RECOVERABLE = "RECOVERABLE"
    CONSEQUENTIAL = "CONSEQUENTIAL"


AXES = ("title", "type", "owner", "recency")
MAX_OPTIONS = 5
ESCAPE_LABEL = "None of these / Enter something else"


@dataclass(frozen=True)
class CandidateFact:
    key: str
    value: str
    source: str = ""


@dataclass(frozen=True)
class ClarificationCandidate:
    candidate_id: str
    candidate_type: str
    rank: int
    display_facts: Tuple[CandidateFact, ...]
    discriminating_keys: Tuple[str, ...]
    plausibility_reason: str
    fingerprint: str
    option_key: str = ""


@dataclass(frozen=True)
class AttributeOption:
    option_key: str
    axis: str
    value: str
    member_candidate_ids: Tuple[str, ...]
    fact_sources: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ClarificationContract:
    ambiguity_id: str
    session_id: str
    turn_id: str
    round_index: int
    kind: ClarificationKind
    ambiguity_type: str
    original_reference: str
    contrast_exclusions: Tuple[str, ...]
    candidates: Tuple[ClarificationCandidate, ...]
    overflow_count: int
    max_options: int
    free_input_allowed: bool
    binding_target: str
    candidate_set_fingerprint: str
    created_at: str
    expires_at: str
    resolution_basis: str
    attribute_axis: Optional[str] = None
    attribute_options: Tuple[AttributeOption, ...] = ()
    scope_candidate_ids: Tuple[str, ...] = ()
    scope_fingerprints: Tuple[Tuple[str, str], ...] = ()
    change_of: Optional[str] = None
    current_binding_id: Optional[str] = None
    answered_axes: Tuple[str, ...] = ()
    provenance_required: bool = False
    parent_locator: Optional[str] = None
    candidate_locators: Tuple[Tuple[str, str], ...] = ()
    excluded_fact_values: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ClarificationResponse:
    ambiguity_id: str
    response_kind: ResponseKind
    candidate_id: Optional[str] = None
    option_key: Optional[str] = None
    text: Optional[str] = None
    candidate_set_fingerprint: Optional[str] = None
    axis: Optional[str] = None
    value: Optional[str] = None


@dataclass(frozen=True)
class ReferenceSlot:
    ref_key: str
    contract: ClarificationContract
    depends_on: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ClarificationBundle:
    bundle_id: str
    session_id: str
    turn_id: str
    slots: Tuple[ReferenceSlot, ...]
    presentation: str


def validate_contract(contract: ClarificationContract, query: RARQuery) -> None:
    """Validate both the displayed set and the complete RAR-returned scope."""
    scope = contract.scope_candidate_ids
    ids = tuple(c.candidate_id for c in contract.candidates)
    query_ids = set(query.candidate_ids)
    if not contract.ambiguity_id or not contract.session_id or not contract.turn_id:
        raise ValueError("missing contract identity")
    if contract.round_index < 1 or contract.max_options != MAX_OPTIONS:
        raise ValueError("invalid round or option limit")
    if not contract.free_input_allowed or contract.binding_target != "RARDeterministicAnchor.selected_ui_id":
        raise ValueError("invalid binding policy")
    if len(scope) != len(set(scope)) or not set(scope) <= query_ids:
        raise ValueError("invalid scope candidate IDs")
    if set(scope) & set(contract.contrast_exclusions):
        raise ValueError("excluded scope candidate")
    if len(ids) != len(set(ids)) or not set(ids) <= set(scope):
        raise ValueError("invalid displayed candidate IDs")
    if len(ids) > MAX_OPTIONS or tuple(c.rank for c in contract.candidates) != tuple(range(1, len(ids) + 1)):
        raise ValueError("invalid displayed ranks")
    if tuple(c.option_key for c in contract.candidates) != tuple(f"s{i}" for i in range(1, len(ids) + 1)):
        raise ValueError("invalid candidate slot keys")
    if tuple(cid for cid, _ in contract.scope_fingerprints) != scope or any(not f for _, f in contract.scope_fingerprints):
        raise ValueError("missing scope fingerprints")
    if contract.provenance_required and (not contract.parent_locator or
                                         not set(scope) <= dict(contract.candidate_locators).keys()):
        raise ValueError("missing required provenance")
    from uri_v1.reference_clarification.fingerprints import candidate_set_fingerprint
    if contract.candidate_set_fingerprint != candidate_set_fingerprint(contract.scope_fingerprints, contract.attribute_options):
        raise ValueError("invalid candidate-set fingerprint")
    if contract.kind == ClarificationKind.CHOOSE_ONE:
        if len(scope) < 2 or len(ids) < 2 or ids != scope[:MAX_OPTIONS] or contract.overflow_count != len(scope) - len(ids):
            raise ValueError("invalid choice contract")
    elif contract.kind == ClarificationKind.CONFIRM_ONE:
        if len(scope) != 1 or ids != scope or contract.overflow_count:
            raise ValueError("invalid confirmation contract")
    elif contract.kind == ClarificationKind.FREE_INPUT_ONLY:
        if scope or ids or contract.overflow_count:
            raise ValueError("invalid free-input contract")
    elif contract.kind == ClarificationKind.CHOOSE_ATTRIBUTE:
        options = contract.attribute_options
        if ids or contract.overflow_count or contract.attribute_axis not in AXES or not 2 <= len(options) <= MAX_OPTIONS:
            raise ValueError("invalid attribute contract")
        if tuple(o.option_key for o in options) != tuple(f"a{i}" for i in range(1, len(options) + 1)):
            raise ValueError("invalid attribute slot keys")
        if any(o.axis != contract.attribute_axis for o in options):
            raise ValueError("mixed attribute axes")
        if len({" ".join(o.value.casefold().split()) for o in options}) != len(options):
            raise ValueError("duplicate attribute values")
        members = [cid for o in options for cid in o.member_candidate_ids]
        if any(not o.member_candidate_ids for o in options) or len(members) != len(set(members)) or set(members) != set(scope):
            raise ValueError("invalid attribute partition")
    else:
        raise ValueError("unknown clarification kind")
    if contract.kind != ClarificationKind.CHOOSE_ATTRIBUTE and (contract.attribute_options or contract.attribute_axis is not None):
        raise ValueError("mixed option kinds")


def validate_bundle(bundle: ClarificationBundle) -> None:
    keys = [s.ref_key for s in bundle.slots]
    if not bundle.bundle_id or len(keys) != len(set(keys)) or any(not k for k in keys):
        raise ValueError("invalid bundle identity")
    graph = {s.ref_key: s.depends_on for s in bundle.slots}
    if any(s.contract.session_id != bundle.session_id or s.contract.turn_id != bundle.turn_id for s in bundle.slots):
        raise ValueError("bundle session or turn mismatch")
    seen, active = set(), set()
    def visit(key: str) -> None:
        if key in active:
            raise ValueError("bundle dependency cycle")
        if key in seen:
            return
        active.add(key)
        for parent in graph[key]:
            if parent not in graph or parent == key:
                raise ValueError("invalid bundle dependency")
            visit(parent)
        active.remove(key)
        seen.add(key)
    for key in keys:
        visit(key)
    expected = "SEQUENTIAL" if any(graph.values()) else "COMBINED"
    if bundle.presentation != expected:
        raise ValueError("invalid bundle presentation")
