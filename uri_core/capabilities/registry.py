"""Registry with progressive discovery for reusable capability actions."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional

from .base import Action, ActionSchema, ApprovalRequirement, Capability, EffectType, RiskLevel

KNOWN_CAPABILITY_EFFECTS: Dict[str, EffectType] = {
    # Pure reads (no state change)
    "extract_student_records": EffectType.READ_ONLY,
    "fetch_drive_spreadsheet": EffectType.READ_ONLY,
    "system_performance": EffectType.READ_ONLY,
    "recall_memory": EffectType.READ_ONLY,
    "read_attached_file": EffectType.READ_ONLY,
    "gmail_search": EffectType.READ_ONLY,
    "gmail_find_draft": EffectType.READ_ONLY,
    "web_search": EffectType.READ_ONLY,
    "drive_search": EffectType.READ_ONLY,
    "fetch_url": EffectType.READ_ONLY,
    # Local writes (URI / local state mutation)
    "draft_institutional_note": EffectType.LOCAL_WRITE,
    "draft_institutional_order": EffectType.LOCAL_WRITE,
    "generate_document": EffectType.LOCAL_WRITE,
    "remember_fact": EffectType.LOCAL_WRITE,
    "convert_document": EffectType.LOCAL_WRITE,
    # External writes (side-effect in third-party services)
    "gmail_create_draft": EffectType.EXTERNAL_WRITE,
    "drive_upload": EffectType.EXTERNAL_WRITE,
}


class MultiActionCapabilityRegistry:
    """Stores capability descriptions without flattening them into tools.

    ``capability_summaries`` is suitable for initial model context.  Action
    schemas are intentionally returned only from ``describe_capability`` once
    a capability has been selected.
    """

    def __init__(self, capabilities: Optional[Iterable[Capability]] = None):
        self._capabilities: Dict[str, Capability] = {}
        for capability in capabilities or ():
            self.register(capability)

    def register(self, capability: Capability) -> None:
        if not isinstance(capability, Capability):
            raise TypeError("registry accepts Capability instances only")
        if capability.name in self._capabilities:
            raise ValueError(f"capability already registered: {capability.name}")
        self._capabilities[capability.name] = capability

    def get_capability(self, name: str) -> Optional[Capability]:
        return self._capabilities.get(name)

    def capability_summaries(self) -> List[Dict[str, Any]]:
        # Deliberately unchanged shape (M33 Batch B): capability_directory.
        # py's `_multi_action_entries` reads `aliases`/`intent_signals`/
        # per-action descriptions directly off the `Capability` object via
        # `get_capability()` instead of from this method, so this exact
        # return shape - asserted literally by
        # test_progressive_discovery_keeps_action_schemas_out_of_initial_
        # summary - never has to change for that extension.
        return [
            {
                "name": capability.name,
                "description": capability.description,
                "category": capability.category,
                "preconditions": list(capability.preconditions),
                "actions": [action.name for action in capability.list_actions()],
            }
            for capability in self._capabilities.values()
        ]

    def describe_capability(self, name: str) -> Optional[Dict[str, Any]]:
        capability = self.get_capability(name)
        if capability is None:
            return None
        return {
            "name": capability.name,
            "description": capability.description,
            "category": capability.category,
            "permissions": list(capability.permissions),
            "preconditions": list(capability.preconditions),
            "availability": capability.check_availability(),
            "actions": [self._describe_action(action) for action in capability.list_actions()],
            "aliases": list(capability.aliases),
            "intent_signals": list(capability.intent_signals),
        }

    @staticmethod
    def _describe_action(action: Action) -> Dict[str, Any]:
        schema = action.parameters
        return {
            "name": action.name,
            "description": action.description,
            "parameters": schema.parameters,
            "required": list(schema.required),
            "returns": action.returns or schema.returns,
            "read_only": action.read_only,
            "approval_requirement": action.approval_requirement.value,
            "risk": action.risk.value,
        }


class LegacyCapabilityAdapter:
    """Projects an existing single-purpose capability into one action.

    This is intentionally one-way and side-effect free.  It allows callers to
    migrate registrations incrementally while the existing legacy registry
    remains authoritative for legacy production dispatch.
    """

    @staticmethod
    def from_descriptor(
        descriptor: Any,
        handler: Any = None,
        *,
        category: str = "legacy",
        preconditions: Optional[List[str]] = None,
    ) -> Capability:
        if isinstance(descriptor, Mapping):
            source = descriptor
            capability_id = str(source.get("id") or source.get("name") or "legacy")
            description = str(source.get("description", ""))
            permissions = list(source.get("permissions", []))
            approval = source.get("approval_requirement", "none")
            risk = source.get("risk", "controlled")
            interface = source.get("interface") or {}
        else:
            capability_id = str(getattr(descriptor, "id", getattr(descriptor, "name", "legacy")))
            description = str(getattr(descriptor, "description", ""))
            permissions = list(getattr(descriptor, "permissions", []))
            approval = getattr(descriptor, "approval_requirement", "none")
            risk = getattr(descriptor, "risk", "controlled")
            interface = getattr(descriptor, "interface", None) or {}
        raw_effect = (
            source.get("effect_type")
            if isinstance(descriptor, Mapping)
            else getattr(descriptor, "effect_type", None)
        )
        if raw_effect:
            try:
                effect_type = EffectType(raw_effect)
            except ValueError:
                effect_type = EffectType.LOCAL_WRITE
        else:
            effect_type = KNOWN_CAPABILITY_EFFECTS.get(capability_id, EffectType.LOCAL_WRITE)

        action = Action(
            name=capability_id,
            description=description or f"Execute legacy capability {capability_id}.",
            parameters=ActionSchema.coerce(interface.get("parameters", {})),
            returns=dict(interface.get("returns", {})),
            effect_type=effect_type,
            approval_requirement=ApprovalRequirement(approval if approval in {item.value for item in ApprovalRequirement} else "none"),
            risk=RiskLevel(risk if risk in {item.value for item in RiskLevel} else "controlled"),
            handler=handler,
        )
        return Capability(
            name=capability_id,
            description=description or f"Legacy URI capability {capability_id}.",
            category=category,
            permissions=permissions,
            preconditions=list(preconditions or []),
            actions={action.name: action},
        )
