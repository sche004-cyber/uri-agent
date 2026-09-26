"""M33.3 S2: declared wrong-binding impact and the execution-gate check.

``wrong_binding_impact`` states what happens if an action runs with the
wrong bound reference.  It is declared per action and never derived from
``effect_type``, ``approval_requirement``, or ``risk`` (User decision D1).
Undeclared or invalid means ``CONSEQUENTIAL`` (fail closed).

The gate is pure and deterministic.  It never creates, confirms, or
changes a binding, never grants approval, and never executes anything.
Callers supply the binding states; approval stays a separate gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Sequence, Tuple


class WrongBindingImpact(str, Enum):
    NONE = "NONE"
    RECOVERABLE = "RECOVERABLE"
    CONSEQUENTIAL = "CONSEQUENTIAL"


class ReferenceBindingStatus(str, Enum):
    """The only binding states that may reach execution."""

    CONFIRMED = "CONFIRMED"
    TENTATIVE = "TENTATIVE"


@dataclass(frozen=True)
class ReferenceBinding:
    ref_key: str
    candidate_id: str
    status: ReferenceBindingStatus


class GateOutcome(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NO_REFERENCE_BINDING = "NO_REFERENCE_BINDING"
    ALLOWED_CONFIRMED = "ALLOWED_CONFIRMED"
    ALLOWED_TENTATIVE_RECOVERABLE = "ALLOWED_TENTATIVE_RECOVERABLE"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    INVALID_REFERENCE_BINDING = "INVALID_REFERENCE_BINDING"


CONFIRM_ONE = "CONFIRM_ONE"
_TENTATIVE_SAFE = (WrongBindingImpact.NONE, WrongBindingImpact.RECOVERABLE)


@dataclass(frozen=True)
class WrongBindingGateDecision:
    allowed: bool
    outcome: GateOutcome
    wrong_binding_impact: WrongBindingImpact
    impact_declared: bool
    blocking_ref_keys: Tuple[str, ...] = ()
    required_clarification: Optional[str] = None

    def as_detail(self) -> dict:
        return {
            "wrong_binding_gate": self.outcome.value,
            "wrong_binding_impact": self.wrong_binding_impact.value,
            "impact_declared": self.impact_declared,
            "blocking_ref_keys": list(self.blocking_ref_keys),
            "required_clarification": self.required_clarification,
        }


def coerce_declared_impact(value: Any) -> Optional[WrongBindingImpact]:
    """Strict: ``None`` stays undeclared; an exact value string is accepted."""
    if value is None or isinstance(value, WrongBindingImpact):
        return value
    if type(value) is str:
        return WrongBindingImpact(value)
    raise ValueError("wrong_binding_impact must be a WrongBindingImpact or exact value string")


def effective_wrong_binding_impact(action: Any) -> Tuple[WrongBindingImpact, bool]:
    """Return ``(impact, declared)`` read from the live action every call."""
    declared = getattr(action, "wrong_binding_impact", None)
    if isinstance(declared, WrongBindingImpact):
        return declared, True
    return WrongBindingImpact.CONSEQUENTIAL, False


def _valid_binding(item: Any) -> bool:
    if type(item) is not ReferenceBinding:
        return False
    ref_key = getattr(item, "ref_key", None)
    candidate_id = getattr(item, "candidate_id", None)
    status = getattr(item, "status", None)
    return (
        isinstance(ref_key, str) and bool(ref_key.strip())
        and isinstance(candidate_id, str) and bool(candidate_id.strip())
        and isinstance(status, ReferenceBindingStatus)
    )


def evaluate_wrong_binding_gate(
    action: Any,
    reference_bindings: Optional[Sequence[ReferenceBinding]],
) -> WrongBindingGateDecision:
    impact, declared = effective_wrong_binding_impact(action)

    def decide(allowed: bool, outcome: GateOutcome, blocking: Tuple[str, ...] = (),
               clarification: Optional[str] = None) -> WrongBindingGateDecision:
        return WrongBindingGateDecision(allowed, outcome, impact, declared, blocking, clarification)

    if reference_bindings is None:
        return decide(True, GateOutcome.NOT_APPLICABLE)
    if not isinstance(reference_bindings, (list, tuple)):
        return decide(False, GateOutcome.INVALID_REFERENCE_BINDING)
    bindings = tuple(reference_bindings)
    if not all(_valid_binding(item) for item in bindings):
        return decide(False, GateOutcome.INVALID_REFERENCE_BINDING)
    keys = [item.ref_key for item in bindings]
    if len(set(keys)) != len(keys):
        return decide(False, GateOutcome.INVALID_REFERENCE_BINDING)
    if not bindings:
        return decide(True, GateOutcome.NO_REFERENCE_BINDING)
    tentative = tuple(b.ref_key for b in bindings if b.status is ReferenceBindingStatus.TENTATIVE)
    if not tentative:
        return decide(True, GateOutcome.ALLOWED_CONFIRMED)
    if impact in _TENTATIVE_SAFE:
        return decide(True, GateOutcome.ALLOWED_TENTATIVE_RECOVERABLE)
    return decide(False, GateOutcome.CONFIRMATION_REQUIRED, tentative, CONFIRM_ONE)
