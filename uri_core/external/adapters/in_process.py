"""Static in-process fixture adapter.  No dynamic imports are permitted."""

from __future__ import annotations

from typing import Any, Mapping

from uri_core.capabilities.base import Action, ActionSchema, ApprovalRequirement, Capability, EffectType, RiskLevel


def execute(descriptor: Mapping[str, Any], action_name: str, inputs: Mapping[str, Any]) -> dict:
    config = descriptor.get("transport_config")
    config = config if isinstance(config, Mapping) else {}
    fixture = config.get("fixture_result")
    if not isinstance(fixture, Mapping):
        return {"status": "unavailable", "message": "in-process fixture is not configured"}
    # Fixture data is descriptor-owned and copied so one action cannot mutate
    # another action's configured result.
    return {"status": "success", "result": {**dict(fixture), "inputs": dict(inputs), "action": action_name}}


def remember_fact_capability(descriptor: Any, *, principal: Any = None) -> Capability:
    """Adapt the reviewed local-memory descriptor to the common executor.

    This explicit built-in mapping replaces the legacy dispatcher branch; it
    does not dynamically load code named by a descriptor.
    """
    interface = getattr(descriptor, "interface", None) or {}
    approval = getattr(descriptor, "approval_requirement", "none")
    risk = getattr(descriptor, "risk", "controlled")
    effect = getattr(descriptor, "effect_type", "local_write")

    def _remember(**inputs: Any) -> dict:
        from uri_core.tools.remember_fact import RememberFactTool
        return RememberFactTool().remember(principal=principal, request_text=inputs.get("request_text"))

    action = Action(
        name="remember_fact", description=str(getattr(descriptor, "description", "")),
        parameters=ActionSchema.coerce(interface.get("parameters", {})),
        returns=dict(interface.get("returns", {})), effect_type=EffectType(effect),
        approval_requirement=ApprovalRequirement(approval), risk=RiskLevel(risk), handler=_remember,
    )
    return Capability(
        name="remember_fact", description=str(getattr(descriptor, "description", "")),
        category="memory", actions={"remember_fact": action}, aliases=("remember", "save to profile"),
        intent_signals=("explicit_memory_write",),
    )
