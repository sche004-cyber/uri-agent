"""Core data structures for multi-action capabilities.

Models may inspect these descriptions and propose actions.  They never use
them to authorize themselves: validation, permission checks, approval, and
execution remain deterministic responsibilities of ``MultiActionExecutor``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple, Union


class ApprovalRequirement(str, Enum):
    NONE = "none"
    USER_APPROVAL_REQUIRED = "user_approval_required"
    ADMIN_APPROVAL_REQUIRED = "admin_approval_required"


class RiskLevel(str, Enum):
    LOW = "low"
    CONTROLLED = "controlled"
    HIGH = "high"
    CRITICAL = "critical"


class EffectType(str, Enum):
    READ_ONLY = "read_only"             # read / no state change
    LOCAL_WRITE = "local_write"         # URI / local state write
    EXTERNAL_WRITE = "external_write"   # external side effect / write


_TYPE_NAMES = {
    "str": str,
    "string": str,
    "int": int,
    "integer": int,
    "float": float,
    "number": (int, float),
    "bool": bool,
    "boolean": bool,
    "dict": dict,
    "object": dict,
    "list": list,
    "array": list,
    "any": object,
}


@dataclass(frozen=True)
class ActionSchema:
    """Declarative input schema, deliberately small and dependency-free.

    A parameter specification is ``{"type": "string", "required": True}``.
    ``required`` may also be supplied as a top-level iterable for concise
    registrations.  Unknown inputs are rejected by default so model proposals
    cannot silently flow into an integration handler.
    """

    parameters: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    required: Tuple[str, ...] = ()
    returns: Dict[str, Any] = field(default_factory=dict)
    allow_additional: bool = False

    def __post_init__(self) -> None:
        normalized: Dict[str, Dict[str, Any]] = {}
        required = set(self.required)
        for name, raw_spec in self.parameters.items():
            spec = dict(raw_spec) if isinstance(raw_spec, Mapping) else {"type": raw_spec}
            if spec.get("required"):
                required.add(name)
            normalized[str(name)] = spec
        object.__setattr__(self, "parameters", normalized)
        object.__setattr__(self, "required", tuple(sorted(required)))

    @classmethod
    def coerce(cls, value: Union["ActionSchema", Mapping[str, Any], None]) -> "ActionSchema":
        if isinstance(value, cls):
            return value
        if value is None:
            return cls()
        if not isinstance(value, Mapping):
            raise TypeError("ActionSchema must be an ActionSchema or mapping")
        if "parameters" in value or "required" in value or "returns" in value:
            return cls(
                parameters=dict(value.get("parameters", {})),
                required=tuple(value.get("required", ())),
                returns=dict(value.get("returns", {})),
                allow_additional=bool(value.get("allow_additional", False)),
            )
        return cls(parameters=dict(value))

    def validate(self, inputs: Optional[Mapping[str, Any]]) -> List[str]:
        if inputs is None:
            inputs = {}
        if not isinstance(inputs, Mapping):
            return ["inputs must be an object"]
        errors: List[str] = []
        for name in self.required:
            if name not in inputs or inputs[name] is None:
                errors.append(f"missing required parameter: {name}")
        if not self.allow_additional:
            for name in inputs:
                if name not in self.parameters:
                    errors.append(f"unknown parameter: {name}")
        for name, value in inputs.items():
            spec = self.parameters.get(name)
            if spec is None or value is None:
                continue
            expected = spec.get("type", "any")
            if not self._matches_type(value, expected):
                errors.append(f"parameter {name} must be {self._type_label(expected)}")
        return errors

    @staticmethod
    def _matches_type(value: Any, expected: Any) -> bool:
        if isinstance(expected, (list, tuple, set)):
            return any(ActionSchema._matches_type(value, item) for item in expected)
        if isinstance(expected, type):
            return isinstance(value, expected)
        expected_type = _TYPE_NAMES.get(str(expected).lower())
        if expected_type is None:
            return False
        # bool is an int subclass, but an integer schema should not admit it.
        return isinstance(value, expected_type) and not (
            expected_type is int and isinstance(value, bool)
        )

    @staticmethod
    def _type_label(expected: Any) -> str:
        if isinstance(expected, type):
            return expected.__name__
        return str(expected)


@dataclass
class Action:
    name: str
    description: str
    parameters: Union[ActionSchema, Mapping[str, Any]] = field(default_factory=ActionSchema)
    returns: Dict[str, Any] = field(default_factory=dict)
    effect_type: EffectType = EffectType.READ_ONLY
    read_only: bool = True
    approval_requirement: ApprovalRequirement = ApprovalRequirement.NONE
    risk: RiskLevel = RiskLevel.LOW
    handler: Optional[Callable[..., Dict[str, Any]]] = None

    def __post_init__(self) -> None:
        self.parameters = ActionSchema.coerce(self.parameters)
        if not isinstance(self.effect_type, EffectType):
            self.effect_type = EffectType(self.effect_type)
        # read_only is strictly synchronized with effect_type == EffectType.READ_ONLY
        self.read_only = (self.effect_type == EffectType.READ_ONLY)
        if not isinstance(self.approval_requirement, ApprovalRequirement):
            self.approval_requirement = ApprovalRequirement(self.approval_requirement)
        if not isinstance(self.risk, RiskLevel):
            self.risk = RiskLevel(self.risk)
        if self.returns and not self.parameters.returns:
            self.parameters = ActionSchema(
                parameters=self.parameters.parameters,
                required=self.parameters.required,
                returns=self.returns,
                allow_additional=self.parameters.allow_additional,
            )


AvailabilityCheck = Callable[[], Union[bool, Dict[str, Any]]]


@dataclass
class Capability:
    name: str
    description: str
    category: str
    permissions: List[str] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    actions: Dict[str, Action] = field(default_factory=dict)
    availability_check: Optional[AvailabilityCheck] = None

    def __post_init__(self) -> None:
        self.actions = {name: action for name, action in self.actions.items()}
        for name, action in self.actions.items():
            if name != action.name:
                raise ValueError(f"action key {name!r} does not match action name {action.name!r}")

    def get_action(self, name: str) -> Optional[Action]:
        return self.actions.get(name)

    def list_actions(self) -> List[Action]:
        return list(self.actions.values())

    def check_availability(self) -> Dict[str, Any]:
        if self.availability_check is None:
            return {"available": True, "missing_preconditions": []}
        result = self.availability_check()
        if isinstance(result, Mapping):
            return {
                "available": bool(result.get("available", False)),
                "missing_preconditions": list(result.get("missing_preconditions", [])),
                **{key: value for key, value in result.items() if key not in {"available", "missing_preconditions"}},
            }
        return {
            "available": bool(result),
            "missing_preconditions": [] if result else list(self.preconditions),
        }
