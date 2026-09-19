"""Offline, descriptor-driven execution adapters for M33 Batch D.

Adapters receive only a vetted descriptor and the action's already-bound
inputs.  They neither select capabilities nor grant permission; those remain
the registry/dispatch/executor boundaries.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Optional

from uri_core.external.validator import ExternalActionValidator


def transport_handler(
    descriptor: Mapping[str, Any], action_name: str,
) -> Optional[Callable[..., dict]]:
    """Return the fixed transport handler for a validated descriptor.

    This is deliberately a closed transport vocabulary, not dynamic import or
    arbitrary command execution.  A bad descriptor yields no handler and the
    established registry bridge reports its honest unavailable result.
    """
    actions = descriptor.get("actions")
    action = actions.get(action_name) if isinstance(actions, Mapping) else None
    if not isinstance(action, Mapping):
        return None
    validator = ExternalActionValidator(action.get("interface") or {})
    transport = descriptor.get("transport")
    if transport == "in_process":
        from .in_process import execute
    elif transport == "cli":
        from .cli import execute
    elif transport == "http":
        from .http import execute
    else:
        return None

    def _handler(**inputs: Any) -> dict:
        checked = validator.validate_input(inputs)
        if not checked.ok:
            return {"status": checked.outcome, "errors": checked.errors}
        result = execute(descriptor, action_name, dict(inputs))
        if not isinstance(result, Mapping):
            return {"status": "invalid_output", "errors": ["transport result must be an object"]}
        result = dict(result)
        if result.get("status") not in {"success", "ok"}:
            return result
        output = result.get("result")
        checked = validator.validate_output(output)
        if not checked.ok:
            return {"status": checked.outcome, "errors": checked.errors}
        return result

    return _handler
