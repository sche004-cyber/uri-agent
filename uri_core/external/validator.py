"""M33 Batch A — bounded JSON-schema-subset validator for external action
inputs and outputs, per the frozen blueprint's D2.

`ActionSchema.validate` (`uri_core/capabilities/base.py`) enforces only
required-present, unknown-key rejection, and top-level type matching —
it silently ignores `enum`, length/range/item bounds, `pattern`, nested
`properties` (no recursion), and never validates output at all. This
module is the separate validator D2 requires, layered on top without
changing `ActionSchema`'s own behavior for any existing capability.

Bounded, deliberately: the supported construct set and max nesting depth
are the exact ones `contract.py`'s `validate_descriptor` already accepts
at descriptor time — an action whose descriptor passed structural
validation can never surprise this validator with a construct it does
not know, and vice versa.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, List, Mapping, Optional

from uri_core.external.contract import MAX_SCHEMA_DEPTH, SUPPORTED_SCHEMA_TYPES

# Bounded so a hostile/malformed descriptor's `pattern` cannot itself be
# used as a resource-exhaustion vector against this validator.
MAX_PATTERN_LENGTH = 512
MAX_STRING_LENGTH_CHECKED = 1_000_000

# Distinct outcomes, per A2: malformed output is its own outcome, never
# folded into the generic "nothing came back" case.
OUTCOME_OK = "ok"
OUTCOME_INVALID_INPUT = "invalid_input"
OUTCOME_NO_RESULT = "no_result"
OUTCOME_INVALID_OUTPUT = "invalid_output"


@dataclass
class ValidationOutcome:
    outcome: str
    errors: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.outcome == OUTCOME_OK

    def to_dict(self) -> dict:
        return {"outcome": self.outcome, "errors": list(self.errors)}


def _type_ok(value: Any, expected: str) -> bool:
    expected = str(expected).lower()
    if expected == "any":
        return True
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "object":
        return isinstance(value, Mapping)
    if expected == "array":
        return isinstance(value, (list, tuple))
    return False


def _validate_value(value: Any, schema: Any, *, path: str, depth: int, errors: List[str]) -> None:
    if depth > MAX_SCHEMA_DEPTH:
        errors.append(f"{path}: exceeds max schema depth {MAX_SCHEMA_DEPTH}")
        return
    if not isinstance(schema, Mapping):
        errors.append(f"{path}: schema node must be an object")
        return

    expected_type = schema.get("type")
    if expected_type is not None:
        if str(expected_type).lower() not in SUPPORTED_SCHEMA_TYPES:
            errors.append(f"{path}: unsupported schema type {expected_type!r}")
            return
        if not _type_ok(value, expected_type):
            errors.append(f"{path}: expected type {expected_type}")
            return

    enum_values = schema.get("enum")
    if enum_values is not None and value not in enum_values:
        errors.append(f"{path}: value not in allowed enum {list(enum_values)!r}")

    if isinstance(value, str):
        text = value[:MAX_STRING_LENGTH_CHECKED]
        min_len = schema.get("minLength")
        if isinstance(min_len, int) and len(text) < min_len:
            errors.append(f"{path}: shorter than minLength {min_len}")
        max_len = schema.get("maxLength")
        if isinstance(max_len, int) and len(text) > max_len:
            errors.append(f"{path}: longer than maxLength {max_len}")
        pattern = schema.get("pattern")
        if isinstance(pattern, str):
            if len(pattern) > MAX_PATTERN_LENGTH:
                errors.append(f"{path}: pattern exceeds max length {MAX_PATTERN_LENGTH}")
            else:
                try:
                    if re.fullmatch(pattern, text) is None:
                        errors.append(f"{path}: does not match pattern")
                except re.error:
                    errors.append(f"{path}: schema pattern is not a valid regular expression")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        if isinstance(minimum, (int, float)) and value < minimum:
            errors.append(f"{path}: below minimum {minimum}")
        maximum = schema.get("maximum")
        if isinstance(maximum, (int, float)) and value > maximum:
            errors.append(f"{path}: above maximum {maximum}")

    if isinstance(value, (list, tuple)):
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(value) < min_items:
            errors.append(f"{path}: fewer than minItems {min_items}")
        max_items = schema.get("maxItems")
        if isinstance(max_items, int) and len(value) > max_items:
            errors.append(f"{path}: more than maxItems {max_items}")
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, item in enumerate(value):
                _validate_value(item, item_schema, path=f"{path}[{index}]", depth=depth + 1, errors=errors)

    if isinstance(value, Mapping):
        properties = schema.get("properties")
        if properties is not None:
            for prop_name, prop_schema in properties.items():
                if prop_name in value:
                    _validate_value(
                        value[prop_name], prop_schema, path=f"{path}.{prop_name}", depth=depth + 1, errors=errors
                    )


class ExternalActionValidator:
    """Built from one action's declared `interface` (the same
    `{parameters, returns}` shape `contract.py` stores). Validates real
    input values before dispatch and real output values after — the
    output side `ActionSchema` never covers today."""

    def __init__(self, interface: Mapping[str, Any]):
        self.parameters: Mapping[str, Any] = dict(interface.get("parameters", {}))
        self.required = tuple(interface.get("required", ()))
        self.returns: Mapping[str, Any] = dict(interface.get("returns", {}))

    def validate_input(self, inputs: Optional[Mapping[str, Any]]) -> ValidationOutcome:
        if inputs is None:
            inputs = {}
        if not isinstance(inputs, Mapping):
            return ValidationOutcome(OUTCOME_INVALID_INPUT, ["inputs must be an object"])

        errors: List[str] = []
        for name in self.required:
            if name not in inputs or inputs[name] is None:
                errors.append(f"missing required parameter: {name}")
        for name in inputs:
            if name not in self.parameters:
                errors.append(f"unknown parameter: {name}")
        for name, schema in self.parameters.items():
            if name in inputs and inputs[name] is not None:
                _validate_value(inputs[name], schema, path=name, depth=1, errors=errors)

        if errors:
            return ValidationOutcome(OUTCOME_INVALID_INPUT, errors)
        return ValidationOutcome(OUTCOME_OK)

    def validate_output(self, output: Any) -> ValidationOutcome:
        """`output is None` is `no_result` — the action produced nothing,
        which is a distinct, often-retryable condition. A present but
        schema-violating output is `invalid_output` — the action DID
        return something, and it was wrong, which the caller must never
        conflate with 'nothing came back' (A2)."""

        if output is None:
            return ValidationOutcome(OUTCOME_NO_RESULT)
        if not self.returns:
            return ValidationOutcome(OUTCOME_OK)

        errors: List[str] = []
        _validate_value(output, self.returns, path="$return", depth=1, errors=errors)
        if errors:
            return ValidationOutcome(OUTCOME_INVALID_OUTPUT, errors)
        return ValidationOutcome(OUTCOME_OK)
