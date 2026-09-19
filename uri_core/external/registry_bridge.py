"""M33 Batch B — the registry publisher: turns a user's enabled, qualified
external capability descriptors (Batch A's `ExternalCapabilityStore`) into
real `uri_core.capabilities.base.Capability` objects, and publishes them
into a `MultiActionCapabilityRegistry` the rest of the codebase already
knows how to read (`decision_engine.py` pulls `orchestrator.multi_action_
dispatch.registry` fresh every turn - see that module's own `CapabilityDirectory`
construction).

Per D3: `MultiActionCapabilityRegistry` has no unregister and no generation
primitive, and its immutability is load-bearing. Rather than mutate one
shared registry in place, `ExternalCapabilityPublisher.publish(user_id)`
builds a FRESH registry instance for this generation and hands the caller
the reference to swap in atomically (`orchestrator.multi_action_dispatch.
registry = new_registry`) - the swap itself is the caller's job (composition
in `server.py`'s user-context construction), not this module's, so this
module never reaches into another object's internals.

Per the M33 addendum (blueprint §13): the descriptor/registry/dispatch
shape here carries no adapter/provider/model (Brain) identity anywhere -
`ExternalCapabilityDescriptor` (contract.py) already declares none, and
nothing added here does either. One integration surface serves every
Brain, exactly as `ModelProvider`/`ModelRouter` already do for text
generation.

Handlers: a real descriptor from Batch A's store is pure data - it has no
Python callable. Batch D's adapters (`uri_core/external/adapters/{cli,http,
in_process}.py`) are the shipped mechanism for turning a descriptor into a
real, dispatchable handler; they do not exist yet. Until they do, every
action built here gets a deliberately honest stub handler that returns
`{"status": "not_implemented", ...}` - never a fabricated success - unless
the caller supplies its own `handler_resolver` (tests use this to prove the
full dispatch/authorization/evidence pipeline against a real in-process
fixture without waiting for Batch D).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional

from uri_core.capabilities.base import (
    Action,
    ActionSchema,
    ApprovalRequirement,
    Capability,
    EffectType,
    RiskLevel,
)
from uri_core.capabilities.registry import MultiActionCapabilityRegistry
from uri_core.external.lifecycle import LifecycleState
from uri_core.external.store import ExternalCapabilityStore
from uri_core.external.adapters import transport_handler

# Signature: (descriptor_id, action_name) -> real handler, or None if this
# action has no real handler yet (falls back to the honest stub below).
HandlerResolver = Callable[[str, str], Optional[Callable[..., Dict[str, Any]]]]


def _stub_handler(descriptor_id: str, action_name: str) -> Callable[..., Dict[str, Any]]:
    def _handler(**_kwargs: Any) -> Dict[str, Any]:
        return {
            "status": "not_implemented",
            "message": (
                f"'{descriptor_id}.{action_name}' has no real transport adapter "
                "wired yet (Batch D). Authorization, validation and discovery "
                "are real; execution is honestly not."
            ),
        }

    return _handler


def _record_enabled_and_qualified(record: Mapping[str, Any]) -> bool:
    qualification = record.get("qualification") or {}
    lifecycle_data = record.get("lifecycle") or {}
    if qualification.get("status") != "qualified":
        return False
    state = LifecycleState.from_dict(lifecycle_data)
    return bool(state.enabled)


def _action_to_capability_action(
    descriptor_id: str, action_name: str, action_data: Mapping[str, Any], handler_resolver: Optional[HandlerResolver],
    descriptor: Mapping[str, Any],
) -> Action:
    interface = action_data.get("interface") or {}
    handler = None
    if handler_resolver is not None:
        try:
            handler = handler_resolver(descriptor_id, action_name)
        except Exception:
            handler = None
    if handler is None:
        handler = transport_handler(descriptor, action_name)
    if handler is None:
        handler = _stub_handler(descriptor_id, action_name)
    effect_raw = action_data.get("effect_type", EffectType.READ_ONLY.value)
    approval_raw = action_data.get("approval_requirement", ApprovalRequirement.NONE.value)
    risk_raw = action_data.get("risk", RiskLevel.LOW.value)
    return Action(
        name=action_name,
        description=str(action_data.get("description", "")),
        parameters=ActionSchema.coerce(interface.get("parameters", {})),
        returns=dict(interface.get("returns", {})),
        effect_type=EffectType(effect_raw) if effect_raw in {e.value for e in EffectType} else EffectType.READ_ONLY,
        approval_requirement=(
            ApprovalRequirement(approval_raw)
            if approval_raw in {a.value for a in ApprovalRequirement}
            else ApprovalRequirement.NONE
        ),
        risk=RiskLevel(risk_raw) if risk_raw in {r.value for r in RiskLevel} else RiskLevel.LOW,
        handler=handler,
        permissions=tuple(action_data.get("permissions", ())),
    )


def descriptor_record_to_capability(
    record: Mapping[str, Any], *, handler_resolver: Optional[HandlerResolver] = None
) -> Optional[Capability]:
    """Build a real, multi-action `Capability` from one store record's
    `descriptor` field. Returns None for a structurally unusable record
    (no actions) rather than raising - callers already filter to enabled/
    qualified records before calling this, so this is a last defensive
    layer, not the primary gate."""

    descriptor = record.get("descriptor") or {}
    descriptor_id = str(descriptor.get("id", ""))
    raw_actions = descriptor.get("actions") or {}
    if not descriptor_id or not isinstance(raw_actions, Mapping) or not raw_actions:
        return None

    actions: Dict[str, Action] = {}
    for action_name, action_data in raw_actions.items():
        if not isinstance(action_data, Mapping):
            continue
        action = _action_to_capability_action(descriptor_id, action_name, action_data, handler_resolver, descriptor)
        actions[action.name] = action
    if not actions:
        return None

    return Capability(
        name=descriptor_id,
        description=str(descriptor.get("description", "")),
        category=str(descriptor.get("category", "external")),
        permissions=[],  # M33 Batch B: external capabilities gate authorization
                          # per-ACTION (Action.permissions, P1's executor gate)
                          # plus the capability-level explicit-grant check
                          # (permission_binding.py) - not via this legacy
                          # capability-level `permissions` list, which
                          # `_granted_permissions`'s Gmail-only alias table
                          # does not and must not recognise for external ids.
        preconditions=[],
        actions=actions,
        aliases=tuple(descriptor.get("aliases", ())),
        intent_signals=tuple(descriptor.get("intent_signals", ())),
    )


@dataclass
class PublishResult:
    registry: MultiActionCapabilityRegistry
    published_ids: List[str]
    skipped_ids: List[str]


class ExternalCapabilityPublisher:
    """Builds one fresh, immutable registry generation per `publish()`
    call, containing every one of `user_id`'s enabled+qualified external
    capabilities, wrapped around `base_capabilities` (typically the
    existing default registry contents, e.g. `GmailCapability()`) so the
    swap is additive from the caller's perspective, never a narrowing of
    what already worked."""

    def __init__(self, store: Optional[ExternalCapabilityStore] = None):
        self.store = store or ExternalCapabilityStore()

    def publish(
        self,
        user_id: str,
        *,
        base_capabilities: Optional[List[Capability]] = None,
        handler_resolver: Optional[HandlerResolver] = None,
    ) -> PublishResult:
        registry = MultiActionCapabilityRegistry(list(base_capabilities or ()))
        published: List[str] = []
        skipped: List[str] = []
        for record in self.store.list_all(user_id):
            descriptor_id = str((record.get("descriptor") or {}).get("id", ""))
            if not _record_enabled_and_qualified(record):
                if descriptor_id:
                    skipped.append(descriptor_id)
                continue
            capability = descriptor_record_to_capability(record, handler_resolver=handler_resolver)
            if capability is None:
                skipped.append(descriptor_id or "<unknown>")
                continue
            try:
                registry.register(capability)
            except ValueError:
                # Name collision with a base capability (e.g. an external
                # descriptor id literally "Gmail") - the base registration
                # wins; never silently shadow the trusted built-in.
                skipped.append(capability.name)
                continue
            published.append(capability.name)
        return PublishResult(registry=registry, published_ids=published, skipped_ids=skipped)

    def is_published_external_capability(self, user_id: str, capability_id: str) -> bool:
        """True only if `capability_id` is an enabled+qualified external
        capability for `user_id` - the exact same test `publish()` uses,
        exposed standalone for `permission_binding.py` so authorization
        and discovery share one definition of "real", never two that
        could drift apart."""
        record = self.store.get(user_id, capability_id)
        if record is None:
            return False
        return _record_enabled_and_qualified(record)
