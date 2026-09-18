"""Deterministic validation, authority checks, execution, and audit trail."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

from .base import ApprovalRequirement
from .context_resolver import CapabilityContextResolver
from .registry import MultiActionCapabilityRegistry


class MultiActionExecutor:
    def __init__(
        self,
        registry: MultiActionCapabilityRegistry,
        *,
        granted_permissions: Optional[Iterable[str]] = None,
        audit_sink: Optional[Callable[[Dict[str, Any]], None]] = None,
        context_resolver: Optional[CapabilityContextResolver] = None,
    ) -> None:
        self.registry = registry
        self.granted_permissions = set(granted_permissions or ())
        self.audit_sink = audit_sink
        self.context_resolver = context_resolver or CapabilityContextResolver()
        self.audit_log: List[Dict[str, Any]] = []

    def execute(
        self,
        capability_name: str,
        action_name: str,
        inputs: Optional[Mapping[str, Any]] = None,
        *,
        user_approved: bool = False,
        admin_approved: bool = False,
    ) -> Dict[str, Any]:
        capability = self.registry.get_capability(capability_name)
        if capability is None:
            return self._record(capability_name, action_name, "unavailable_capability", {})
        action = capability.get_action(action_name)
        if action is None or action.handler is None:
            return self._record(capability_name, action_name, "unavailable_action", {})
        availability = capability.check_availability()
        if not availability.get("available"):
            return self._record(capability_name, action_name, "unavailable", {"availability": availability})
        missing_permissions = sorted(set(capability.permissions) - self.granted_permissions)
        if missing_permissions:
            return self._record(
                capability_name, action_name, "permission_denied", {"missing_permissions": missing_permissions}
            )
        # M33 P1: action-level gate, between the capability-level check
        # above and schema validation. A no-op for every action that
        # declares no permissions of its own (every action as of P1) -
        # this is the primitive Batch B's external capabilities use to
        # require a scope narrower than their capability's own grant.
        missing_action_permissions = sorted(set(action.permissions) - self.granted_permissions)
        if missing_action_permissions:
            return self._record(
                capability_name, action_name, "permission_denied",
                {"missing_action_permissions": missing_action_permissions},
            )
        errors = action.parameters.validate(inputs)
        if errors:
            return self._record(capability_name, action_name, "invalid_input", {"errors": errors})
        if action.approval_requirement == ApprovalRequirement.USER_APPROVAL_REQUIRED and not user_approved:
            return self._record(capability_name, action_name, "approval_required", {"approval_requirement": action.approval_requirement.value})
        if action.approval_requirement == ApprovalRequirement.ADMIN_APPROVAL_REQUIRED and not admin_approved:
            return self._record(capability_name, action_name, "approval_required", {"approval_requirement": action.approval_requirement.value})
        try:
            result = action.handler(**dict(inputs or {}))
            if not isinstance(result, Mapping):
                result = {"value": result}
            result = dict(result)
            status = str(result.get("status", "success"))
            response = self._record(capability_name, action_name, status, {"result": result})
            if status in {"success", "ok"} or "success" not in result:
                self.context_resolver.record_action_result(capability_name, action_name, result)
            return response
        except Exception as exc:  # integration boundary: never leak an unstructured failure
            return self._record(capability_name, action_name, "execution_error", {"error": str(exc)})

    def execute_chain(
        self,
        steps: Sequence[Mapping[str, Any]],
        *,
        user_approved: bool = False,
        admin_approved: bool = False,
    ) -> Dict[str, Any]:
        completed: Dict[str, Dict[str, Any]] = {}
        for index, step in enumerate(steps):
            step_id = str(step.get("id", index))
            inputs = self._resolve_references(step.get("inputs", {}), completed)
            response = self.execute(
                str(step.get("capability")), str(step.get("action")), inputs,
                user_approved=user_approved, admin_approved=admin_approved,
            )
            completed[step_id] = response
            if response["status"] not in {"success", "ok"}:
                return {"status": "halted", "halted_at": step_id, "steps": completed}
        return {"status": "success", "steps": completed}

    def _resolve_references(self, value: Any, completed: Mapping[str, Mapping[str, Any]]) -> Any:
        if isinstance(value, Mapping):
            if set(value) == {"$from"}:
                return self._lookup_reference(str(value["$from"]), completed)
            return {key: self._resolve_references(item, completed) for key, item in value.items()}
        if isinstance(value, list):
            return [self._resolve_references(item, completed) for item in value]
        if isinstance(value, str) and value.startswith("$"):
            return self._lookup_reference(value[1:], completed)
        return value

    @staticmethod
    def _lookup_reference(reference: str, completed: Mapping[str, Mapping[str, Any]]) -> Any:
        path = reference.replace("[", ".").replace("]", "").split(".")
        current: Any = completed.get(path[0])
        for part in path[1:]:
            if isinstance(current, Mapping):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
                current = current[int(part)]
            else:
                return None
        return current

    def _record(self, capability: str, action: str, status: str, detail: Dict[str, Any]) -> Dict[str, Any]:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "capability": capability,
            "action": action,
            "status": status,
            **detail,
        }
        self.audit_log.append(entry)
        if self.audit_sink:
            self.audit_sink(dict(entry))
        return entry
