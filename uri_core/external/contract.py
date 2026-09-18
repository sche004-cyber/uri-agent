"""M33 Batch A — versioned external capability descriptor and its static
structural validator.

Per the frozen blueprint's D1: this wraps, rather than reinvents, the
existing descriptor vocabulary `LegacyCapabilityAdapter.from_descriptor`
already consumes (`uri_core/capabilities/registry.py`) — `id`/`name`,
`description`, `permissions`, `approval_requirement`, `risk`,
`interface{parameters, returns}` — reusing `uri_core.capabilities.base`'s
`ApprovalRequirement`/`RiskLevel`/`EffectType` enums directly rather than
declaring parallel ones. What is genuinely new here (contract version,
namespaced identity, source provenance, transport, dependencies,
configuration, credential references, intent signals, aliases, and
lifecycle support) is added on top, not instead.

Per D1's own noted trap: `registry.py` sets `read_only = (approval_
requirement == "none")`, conflating approval with read-only. External
actions declare `effect_type` (from `uri_core.capabilities.base`)
explicitly instead of letting it be inferred from approval status.

This module performs ONLY static, structural, execution-free validation
of a descriptor's own shape (unknown major contract version, unsupported
schema construct, malformed structure) — never runtime input/output
validation (that is `validator.py`'s `ExternalActionValidator`, per D2),
never dependency fetching, never any import of anything the descriptor
names. A descriptor is data until a human explicitly enables it
(`lifecycle.py`) and Batch B wires dispatch — neither of which this
module does.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Mapping, Optional, Tuple

from uri_core.capabilities.base import ApprovalRequirement, EffectType, RiskLevel

# Only major version 1 is understood. An unknown major version must fail
# closed rather than be guessed-compatible — a later major version may
# have changed the meaning of an existing field, not just added new ones.
SUPPORTED_CONTRACT_MAJOR_VERSIONS: FrozenSet[int] = frozenset({1})

# The transports Batch D's fixture profiles cover. Any other value is an
# unsupported construct at this layer (Batch A declares the vocabulary;
# it does not implement any transport's execution).
SUPPORTED_TRANSPORTS: FrozenSet[str] = frozenset({"in_process", "cli", "http"})

# The bounded JSON-schema-subset keywords this contract's interface
# schemas may use, per D2. Deliberately not full JSON Schema: no $ref,
# no format, no allOf/oneOf/anyOf/not — those are explicitly unsupported
# constructs that fail closed at descriptor-validation time, not silently
# ignored at runtime the way `ActionSchema.validate` ignores them today.
SUPPORTED_SCHEMA_KEYWORDS: FrozenSet[str] = frozenset(
    {
        "type", "enum", "required", "minLength", "maxLength", "minimum",
        "maximum", "minItems", "maxItems", "pattern", "items", "properties",
        "default", "description",
    }
)
SUPPORTED_SCHEMA_TYPES: FrozenSet[str] = frozenset(
    {"string", "integer", "number", "boolean", "object", "array", "any"}
)

# Same nesting-depth bound `validator.py`'s runtime validator enforces —
# declared once here so descriptor-time and dispatch-time bounds cannot
# silently drift apart.
MAX_SCHEMA_DEPTH = 6

REQUIRED_DESCRIPTOR_FIELDS = ("contract_version", "id", "name", "description", "category", "transport", "actions")
REQUIRED_ACTION_FIELDS = ("name", "description", "interface")

_ID_PATTERN_ALLOWED = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
)


@dataclass
class DescriptorValidationResult:
    valid: bool
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"valid": self.valid, "reasons": list(self.reasons)}


@dataclass(frozen=True)
class ExternalActionDescriptor:
    """One action's contract. `interface` mirrors `ActionSchema`'s
    existing `{parameters, returns}` shape (D1) but each parameter/return
    schema node may use the bounded subset above — validated structurally
    by `contract.py`, validated at runtime against real values by
    `validator.py`'s `ExternalActionValidator`."""

    name: str
    description: str
    interface: Dict[str, Any] = field(default_factory=dict)
    effect_type: EffectType = EffectType.READ_ONLY
    approval_requirement: ApprovalRequirement = ApprovalRequirement.NONE
    risk: RiskLevel = RiskLevel.LOW
    permissions: Tuple[str, ...] = ()
    aliases: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "interface": self.interface,
            "effect_type": self.effect_type.value,
            "approval_requirement": self.approval_requirement.value,
            "risk": self.risk.value,
            "permissions": list(self.permissions),
            "aliases": list(self.aliases),
        }


@dataclass(frozen=True)
class ExternalCapabilityDescriptor:
    """A versioned, provider/model-agnostic external capability contract.
    Carries no adapter/provider/model (Brain) identity anywhere in its
    own shape, per the M33 §13 Replaceable Brain addendum — `source`/
    `transport` below name the CAPABILITY's own integration surface
    (a CLI tool, an HTTP fixture), never which Brain proposed using it."""

    contract_version: str
    id: str
    name: str
    description: str
    category: str
    transport: str
    actions: Dict[str, ExternalActionDescriptor] = field(default_factory=dict)
    source_revision: Optional[str] = None
    dependencies: Tuple[str, ...] = ()
    configuration_keys: Tuple[str, ...] = ()
    credential_refs: Tuple[str, ...] = ()
    intent_signals: Tuple[str, ...] = ()
    aliases: Tuple[str, ...] = ()

    def major_version(self) -> Optional[int]:
        try:
            return int(str(self.contract_version).split(".", 1)[0])
        except (ValueError, TypeError):
            return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "transport": self.transport,
            "actions": {name: action.to_dict() for name, action in self.actions.items()},
            "source_revision": self.source_revision,
            "dependencies": list(self.dependencies),
            "configuration_keys": list(self.configuration_keys),
            "credential_refs": list(self.credential_refs),
            "intent_signals": list(self.intent_signals),
            "aliases": list(self.aliases),
        }


def _validate_schema_node(node: Any, *, depth: int, path: str, reasons: List[str]) -> None:
    if depth > MAX_SCHEMA_DEPTH:
        reasons.append(f"{path}: schema nesting exceeds max depth {MAX_SCHEMA_DEPTH}")
        return
    if not isinstance(node, Mapping):
        reasons.append(f"{path}: schema node must be an object")
        return
    unknown = set(node.keys()) - SUPPORTED_SCHEMA_KEYWORDS
    if unknown:
        reasons.append(f"{path}: unsupported schema construct(s): {sorted(unknown)}")
    node_type = node.get("type")
    if node_type is not None and str(node_type).lower() not in SUPPORTED_SCHEMA_TYPES:
        reasons.append(f"{path}: unsupported schema type {node_type!r}")
    if "items" in node:
        _validate_schema_node(node["items"], depth=depth + 1, path=f"{path}.items", reasons=reasons)
    if "properties" in node:
        properties = node["properties"]
        if not isinstance(properties, Mapping):
            reasons.append(f"{path}.properties: must be an object")
        else:
            for prop_name, prop_schema in properties.items():
                _validate_schema_node(
                    prop_schema, depth=depth + 1, path=f"{path}.properties.{prop_name}", reasons=reasons
                )


def _validate_interface(interface: Any, *, path: str, reasons: List[str]) -> None:
    if not isinstance(interface, Mapping):
        reasons.append(f"{path}: interface must be an object")
        return
    parameters = interface.get("parameters", {})
    if not isinstance(parameters, Mapping):
        reasons.append(f"{path}.parameters: must be an object")
    else:
        for param_name, param_schema in parameters.items():
            _validate_schema_node(
                param_schema, depth=1, path=f"{path}.parameters.{param_name}", reasons=reasons
            )
    returns = interface.get("returns", {})
    if returns:
        _validate_schema_node(returns, depth=1, path=f"{path}.returns", reasons=reasons)


def _valid_id(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and all(ch in _ID_PATTERN_ALLOWED for ch in value)


def validate_descriptor(data: Mapping[str, Any]) -> DescriptorValidationResult:
    """Static structural validation only. Never imports, never fetches,
    never executes anything the descriptor names. Fails closed on an
    unknown major contract version or any unsupported schema construct,
    at any nesting depth, in any action's interface."""

    reasons: List[str] = []
    if not isinstance(data, Mapping):
        return DescriptorValidationResult(False, ["descriptor must be an object"])

    for missing in REQUIRED_DESCRIPTOR_FIELDS:
        if missing not in data:
            reasons.append(f"missing required field: {missing}")
    if reasons:
        return DescriptorValidationResult(False, reasons)

    contract_version = data.get("contract_version")
    major = None
    try:
        major = int(str(contract_version).split(".", 1)[0])
    except (ValueError, TypeError):
        pass
    if major is None or major not in SUPPORTED_CONTRACT_MAJOR_VERSIONS:
        reasons.append(
            f"unsupported or unknown contract_version {contract_version!r} "
            f"(supported majors: {sorted(SUPPORTED_CONTRACT_MAJOR_VERSIONS)})"
        )

    if not _valid_id(data.get("id")):
        reasons.append("id must be a non-empty namespaced identifier (letters/digits/._-)")

    transport = data.get("transport")
    if transport not in SUPPORTED_TRANSPORTS:
        reasons.append(f"unsupported transport {transport!r} (supported: {sorted(SUPPORTED_TRANSPORTS)})")

    actions = data.get("actions")
    if not isinstance(actions, Mapping) or not actions:
        reasons.append("actions must be a non-empty object")
    else:
        for action_name, action_data in actions.items():
            if not isinstance(action_data, Mapping):
                reasons.append(f"actions.{action_name}: must be an object")
                continue
            for missing in REQUIRED_ACTION_FIELDS:
                if missing not in action_data:
                    reasons.append(f"actions.{action_name}: missing required field: {missing}")
            if action_data.get("name") not in (None, action_name):
                reasons.append(f"actions.{action_name}: name field must match its own key")
            _validate_interface(
                action_data.get("interface", {}), path=f"actions.{action_name}", reasons=reasons
            )
            for enum_field, enum_cls in (
                ("effect_type", EffectType),
                ("approval_requirement", ApprovalRequirement),
                ("risk", RiskLevel),
            ):
                raw_value = action_data.get(enum_field)
                if raw_value is not None:
                    try:
                        enum_cls(raw_value)
                    except ValueError:
                        reasons.append(f"actions.{action_name}.{enum_field}: unsupported value {raw_value!r}")

    dependencies = data.get("dependencies", [])
    if dependencies and not isinstance(dependencies, (list, tuple)):
        reasons.append("dependencies must be a list")

    return DescriptorValidationResult(valid=not reasons, reasons=reasons)


def descriptor_from_dict(data: Mapping[str, Any]) -> ExternalCapabilityDescriptor:
    """Build a descriptor object from already-validated data. Callers
    must call `validate_descriptor` first — this performs no validation
    of its own and will raise on missing/malformed required fields."""

    actions: Dict[str, ExternalActionDescriptor] = {}
    for action_name, action_data in dict(data.get("actions", {})).items():
        actions[action_name] = ExternalActionDescriptor(
            name=action_name,
            description=action_data.get("description", ""),
            interface=dict(action_data.get("interface", {})),
            effect_type=EffectType(action_data.get("effect_type", EffectType.READ_ONLY.value)),
            approval_requirement=ApprovalRequirement(
                action_data.get("approval_requirement", ApprovalRequirement.NONE.value)
            ),
            risk=RiskLevel(action_data.get("risk", RiskLevel.LOW.value)),
            permissions=tuple(action_data.get("permissions", ())),
            aliases=tuple(action_data.get("aliases", ())),
        )
    return ExternalCapabilityDescriptor(
        contract_version=str(data["contract_version"]),
        id=str(data["id"]),
        name=str(data["name"]),
        description=str(data["description"]),
        category=str(data["category"]),
        transport=str(data["transport"]),
        actions=actions,
        source_revision=data.get("source_revision"),
        dependencies=tuple(data.get("dependencies", ())),
        configuration_keys=tuple(data.get("configuration_keys", ())),
        credential_refs=tuple(data.get("credential_refs", ())),
        intent_signals=tuple(data.get("intent_signals", ())),
        aliases=tuple(data.get("aliases", ())),
    )
