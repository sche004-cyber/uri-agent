"""M33 Batch A — orthogonal external-capability lifecycle state, per the
frozen blueprint's §6 Batch A spec: presence, qualification,
configuration, authentication, health, enabled, update_available — not
one misleading combined enum. The UI label derivation order is defined
as data (`LABEL_RULES` below), not buried in branching logic.

Nothing in this module makes any capability reachable from dispatch.
`enabled=True` here means only "the operator has vouched for it" —
exactly `SkillInstaller`'s own "enabled" discipline (`uri_core/skills/
skill_installer.py`) — never "the runtime will execute it". That
remains Batch B's separate, explicit wiring step.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

PRESENCE_ABSENT = "absent"
PRESENCE_PRESENT = "present"

QUALIFICATION_UNQUALIFIED = "unqualified"
QUALIFICATION_QUALIFIED = "qualified"
QUALIFICATION_REJECTED = "rejected"

CONFIGURATION_UNCONFIGURED = "unconfigured"
CONFIGURATION_CONFIGURED = "configured"

AUTHENTICATION_NOT_REQUIRED = "not_required"
AUTHENTICATION_UNAUTHENTICATED = "unauthenticated"
AUTHENTICATION_AUTHENTICATED = "authenticated"

HEALTH_UNKNOWN = "unknown"
HEALTHY = "healthy"
UNHEALTHY = "unhealthy"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class LifecycleState:
    descriptor_id: str
    presence: str = PRESENCE_ABSENT
    qualification: str = QUALIFICATION_UNQUALIFIED
    configuration: str = CONFIGURATION_UNCONFIGURED
    authentication: str = AUTHENTICATION_NOT_REQUIRED
    health: str = HEALTH_UNKNOWN
    enabled: bool = False
    update_available: bool = False
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return dict(asdict(self))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LifecycleState":
        return cls(
            descriptor_id=str(data.get("descriptor_id", "")),
            presence=str(data.get("presence", PRESENCE_ABSENT)),
            qualification=str(data.get("qualification", QUALIFICATION_UNQUALIFIED)),
            configuration=str(data.get("configuration", CONFIGURATION_UNCONFIGURED)),
            authentication=str(data.get("authentication", AUTHENTICATION_NOT_REQUIRED)),
            health=str(data.get("health", HEALTH_UNKNOWN)),
            enabled=bool(data.get("enabled", False)),
            update_available=bool(data.get("update_available", False)),
            updated_at=str(data.get("updated_at", _now())),
        )


# Evaluated top to bottom; the first matching predicate wins. Kept as
# ordered data (not an if/elif chain) so the derivation order itself is
# inspectable and testable independently of the label strings.
LABEL_RULES: Tuple[Tuple[Callable[[LifecycleState], bool], str], ...] = (
    (lambda s: s.presence == PRESENCE_ABSENT, "not_installed"),
    (lambda s: s.qualification == QUALIFICATION_REJECTED, "rejected"),
    (lambda s: s.qualification == QUALIFICATION_UNQUALIFIED, "unqualified"),
    (lambda s: s.configuration == CONFIGURATION_UNCONFIGURED, "needs_configuration"),
    (
        lambda s: s.authentication == AUTHENTICATION_UNAUTHENTICATED,
        "needs_authentication",
    ),
    (lambda s: s.health == UNHEALTHY, "unhealthy"),
    (lambda s: not s.enabled, "disabled"),
    (lambda s: s.update_available, "update_available"),
    (lambda s: True, "ready"),
)


def derive_label(state: LifecycleState) -> str:
    for predicate, label in LABEL_RULES:
        if predicate(state):
            return label
    return "ready"  # unreachable: the final rule above always matches


class LifecycleTransitionError(Exception):
    pass


class LifecycleController:
    """Pure state transitions, no persistence of its own — the caller
    (`store.py`) owns durability. Every transition is metadata-only."""

    def detect(self, descriptor_id: str) -> LifecycleState:
        return LifecycleState(descriptor_id=descriptor_id, presence=PRESENCE_PRESENT)

    def apply_qualification(self, state: LifecycleState, *, qualified: bool) -> LifecycleState:
        state.qualification = QUALIFICATION_QUALIFIED if qualified else QUALIFICATION_REJECTED
        state.updated_at = _now()
        return state

    def configure(self, state: LifecycleState) -> LifecycleState:
        if state.qualification != QUALIFICATION_QUALIFIED:
            raise LifecycleTransitionError("cannot configure an unqualified/rejected capability")
        state.configuration = CONFIGURATION_CONFIGURED
        state.updated_at = _now()
        return state

    def authenticate(self, state: LifecycleState) -> LifecycleState:
        if state.configuration != CONFIGURATION_CONFIGURED:
            raise LifecycleTransitionError("cannot authenticate an unconfigured capability")
        state.authentication = AUTHENTICATION_AUTHENTICATED
        state.updated_at = _now()
        return state

    def report_health(self, state: LifecycleState, *, healthy: bool) -> LifecycleState:
        state.health = HEALTHY if healthy else UNHEALTHY
        state.updated_at = _now()
        return state

    def enable(self, state: LifecycleState) -> LifecycleState:
        if state.qualification != QUALIFICATION_QUALIFIED:
            raise LifecycleTransitionError("cannot enable an unqualified/rejected capability")
        if state.configuration != CONFIGURATION_CONFIGURED:
            raise LifecycleTransitionError("cannot enable an unconfigured capability")
        state.enabled = True
        state.updated_at = _now()
        return state

    def disable(self, state: LifecycleState) -> LifecycleState:
        state.enabled = False
        state.updated_at = _now()
        return state

    def mark_update_available(self, state: LifecycleState, *, available: bool) -> LifecycleState:
        state.update_available = available
        state.updated_at = _now()
        return state
