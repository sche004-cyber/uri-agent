"""Live, session-safe bridge for multi-action capabilities.

This module deliberately contains the new capability protocol rather than
teaching ``orchestrator.py`` Gmail-specific routing.  A model proposal is
untrusted input: it may select a registered action, but it never supplies
permissions or approval.  ``MultiActionExecutor`` remains the only execution
boundary for this architecture.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, Mapping, Optional

from uri_core.capabilities import MultiActionCapabilityRegistry, MultiActionExecutor
from uri_core.capabilities.context_resolver import CapabilityContextResolver
from uri_core.capabilities.discovery import CapabilityDiscoveryEngine
from uri_core.capabilities.gmail import GmailCapability
from uri_core.core.capability_resolver import CapabilityResolver


# These are authorization aliases only.  They reuse the existing, audited
# capability-grant records rather than creating a second grants store for the
# same Gmail service.  They do not dispatch through the legacy tools.
_ACTION_GRANT_CAPABILITY = {
    "list_labels": "gmail_search",
    "search_messages": "gmail_search",
    "read_message": "gmail_search",
    "read_thread": "gmail_search",
    "read_attachment": "gmail_search",
    "create_draft": "gmail_create_draft",
    "apply_label": "gmail_search",
    "archive_message": "gmail_search",
}


class MultiActionDispatch:
    """Owns progressive discovery and per-session multi-action state.

    The instance can be injected with a fake registry/service or permission
    checker in tests.  In production it uses one existing ``GmailService``
    through ``GmailCapability`` and delegates caller authorization to the
    existing capability-grant resolver.
    """

    def __init__(
        self,
        registry: Optional[MultiActionCapabilityRegistry] = None,
        *,
        granted_permissions: Optional[Iterable[str]] = None,
        permission_checker: Optional[Callable[[str, Any], bool]] = None,
        capability_registry: Any = None,
    ) -> None:
        self.registry = registry or MultiActionCapabilityRegistry([GmailCapability()])
        self.discovery = CapabilityDiscoveryEngine(self.registry)
        self._explicit_permissions = (
            set(granted_permissions) if granted_permissions is not None else None
        )
        self.permission_checker = permission_checker
        self.capability_registry = capability_registry
        self._executors: Dict[str, MultiActionExecutor] = {}
        self._selected_capabilities: Dict[str, str] = {}

    def model_context(self, session_id: str, user_text: str) -> Dict[str, Any]:
        """Return summaries first and schemas only after a selection.

        This is context for a model, not an authorization result.  It never
        exposes another session's selected capability or resolved identifiers.
        """
        selected = self._selected_capabilities.get(str(session_id))
        if selected:
            detail = self.registry.describe_capability(selected)
            if detail is not None:
                return {
                    "stage": "capability_detail",
                    "selected_capability": selected,
                    "capability": detail,
                    # This wrapper deliberately keeps a multi-action proposal
                    # distinct from the legacy model-contract ``action``
                    # field, whose capability names are validated by the
                    # legacy registry before this boundary runs.
                    "proposal_shape": {
                        "multi_action": {
                            "capability": selected,
                            "action": "registered action name",
                            "inputs": "object matching that action schema",
                        }
                    },
                }
        return {
            "stage": "capability_summaries",
            "capabilities": self.registry.capability_summaries(),
            "relevant_capabilities": self.discovery.discover_capabilities(user_text),
            "selection_shape": {"selected_capability": "registered capability name"},
        }

    def dispatch(
        self,
        model_reasoning: Mapping[str, Any],
        *,
        session_id: str,
        user_text: str,
        principal: Any = None,
        user_approved: bool = False,
        admin_approved: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Handle an explicit multi-action proposal, otherwise return None.

        ``user_approved`` and ``admin_approved`` are trusted runtime inputs for
        an explicit approval-resume integration only.  They are intentionally
        never read from a model proposal.
        """
        proposal = self._proposal(model_reasoning)
        if proposal is None:
            return None

        selected = self._selection(proposal)
        action = self._action(proposal)
        workflow = self._workflow(proposal)
        if selected and action is None and workflow is None:
            if self.registry.get_capability(selected) is None:
                return self._unavailable(selected, None, "unavailable_capability")
            self._selected_capabilities[str(session_id)] = selected
            return {
                "handled": True,
                "status": "success",
                "plan": {"status": "capability_selected", "capability": selected, "source": "multi_action"},
                "execution": {"status": "discovery_ready", "capability": selected},
                "response": {"capability": self.registry.describe_capability(selected)},
            }

        if action is not None:
            capability, action_name, inputs = action
            if self.registry.get_capability(capability) is None:
                return None  # It belongs to the existing legacy path.
            self._selected_capabilities[str(session_id)] = capability
            if not self._action_permitted(capability, action_name, principal):
                return self._permission_denied(capability, action_name)
            executor = self._executor_for(session_id, principal)
            bound_inputs = self._bind_context(executor, action_name, inputs, user_text)
            result = executor.execute(
                capability,
                action_name,
                bound_inputs,
                user_approved=user_approved,
                admin_approved=admin_approved,
            )
            return self._execution_response(capability, action_name, result, bound_inputs)

        if workflow is not None:
            if not workflow or any(self.registry.get_capability(step["capability"]) is None for step in workflow):
                return None  # a legacy workflow continues through its established executor
            for step in workflow:
                if not self._action_permitted(step["capability"], step["action"], principal):
                    return self._permission_denied(step["capability"], step["action"])
            self._selected_capabilities[str(session_id)] = workflow[0]["capability"]
            executor = self._executor_for(session_id, principal)
            result = executor.execute_chain(
                workflow,
                user_approved=user_approved,
                admin_approved=admin_approved,
            )
            status = "success" if result.get("status") == "success" else result.get("status", "failed")
            return {
                "handled": True,
                "status": "success" if status in {"success", "halted"} else "unavailable",
                "plan": {"status": "multi_action_workflow", "source": "multi_action"},
                "execution": {"status": status, "capability": "multi_action", "result": result},
                "response": result,
            }
        return None

    def dispatch_explicit(
        self,
        capability: str,
        action_name: str,
        inputs: Mapping[str, Any],
        *,
        session_id: str,
        user_text: str,
        principal: Any = None,
        user_approved: bool = False,
        admin_approved: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """M30.6: the same single-action execution path as `dispatch()`'s
        own `action is not None` branch (permission check, context-bound
        inputs, `MultiActionExecutor.execute()`), taken directly from an
        already-validated Brain Decision Contract's `capability`/
        `actions[0]` fields instead of being parsed out of a
        `model_reasoning` proposal's undocumented shape. Per the accepted
        migration plan (§1, MultiActionDispatch row): "its triggering
        condition... is replaced by the Decision Contract's explicit
        capability/actions fields" - this is that replacement, not a
        second execution mechanism. Returns None only if `capability`
        is not registered here (the caller's own allowlist/gate check
        must already guarantee this doesn't happen in practice)."""
        if self.registry.get_capability(capability) is None:
            return None
        self._selected_capabilities[str(session_id)] = capability
        if not self._action_permitted(capability, action_name, principal):
            return self._permission_denied(capability, action_name)
        executor = self._executor_for(session_id, principal)
        bound_inputs = self._bind_context(executor, action_name, inputs, user_text)
        result = executor.execute(
            capability, action_name, bound_inputs,
            user_approved=user_approved, admin_approved=admin_approved,
        )
        return self._execution_response(capability, action_name, result, bound_inputs)

    def dispatch_chain_explicit(
        self,
        steps: Iterable[Mapping[str, Any]],
        *,
        session_id: str,
        principal: Any = None,
        user_approved: bool = False,
        admin_approved: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """M30.6: the multi-action equivalent of `dispatch_explicit()`
        above, for a Brain Decision Contract whose `mode` is
        `multi_action` (two or more real actions from `actions`,
        already gate-approved). `steps` is `[{"capability", "action",
        "inputs"}, ...]`, taken directly from the contract - never
        parsed from a `model_reasoning` proposal shape."""
        steps = list(steps)
        if not steps or any(self.registry.get_capability(step["capability"]) is None for step in steps):
            return None
        for step in steps:
            if not self._action_permitted(step["capability"], step["action"], principal):
                return self._permission_denied(step["capability"], step["action"])
        self._selected_capabilities[str(session_id)] = steps[0]["capability"]
        executor = self._executor_for(session_id, principal)
        result = executor.execute_chain(
            steps, user_approved=user_approved, admin_approved=admin_approved,
        )
        status = "success" if result.get("status") == "success" else result.get("status", "failed")
        return {
            "handled": True,
            "status": "success" if status in {"success", "halted"} else "unavailable",
            "plan": {"status": "multi_action_workflow", "source": "multi_action"},
            "execution": {"status": status, "capability": "multi_action", "result": result},
            "response": result,
        }

    @staticmethod
    def _proposal(model_reasoning: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
        if not isinstance(model_reasoning, Mapping):
            return None
        result = model_reasoning.get("result", model_reasoning)
        if not isinstance(result, Mapping):
            return None
        proposal = result.get("proposal", result.get("multi_action"))
        return proposal if isinstance(proposal, Mapping) else None

    def _selection(self, proposal: Mapping[str, Any]) -> Optional[str]:
        value = proposal.get("selected_capability", proposal.get("capability_selection"))
        if isinstance(value, Mapping):
            value = value.get("capability") or value.get("name")
        return str(value) if isinstance(value, str) and value else None

    def _action(self, proposal: Mapping[str, Any]):
        raw = proposal.get("multi_action") or proposal.get("action")
        if not isinstance(raw, Mapping):
            return None
        capability = raw.get("capability")
        action = raw.get("action") or raw.get("action_name") or raw.get("operation")
        inputs = raw.get("inputs", raw.get("arguments", {}))
        if not isinstance(capability, str) or not isinstance(action, str) or not isinstance(inputs, Mapping):
            return None
        return capability, action, dict(inputs)

    def _workflow(self, proposal: Mapping[str, Any]):
        raw = proposal.get("multi_action_workflow")
        if raw is None and isinstance(proposal.get("multi_action"), Mapping):
            raw = proposal["multi_action"].get("steps")
        if isinstance(raw, Mapping):
            raw = raw.get("steps")
        if not isinstance(raw, list):
            return None
        steps = []
        for index, step in enumerate(raw):
            if not isinstance(step, Mapping):
                return []
            capability, action = step.get("capability"), step.get("action") or step.get("action_name")
            inputs = step.get("inputs", step.get("arguments", {}))
            if not isinstance(capability, str) or not isinstance(action, str) or not isinstance(inputs, Mapping):
                return []
            steps.append({"id": str(step.get("id", step.get("step_id", index))), "capability": capability, "action": action, "inputs": dict(inputs)})
        return steps

    def _executor_for(self, session_id: str, principal: Any) -> MultiActionExecutor:
        key = str(session_id)
        executor = self._executors.get(key)
        if executor is None:
            executor = MultiActionExecutor(
                self.registry,
                granted_permissions=self._granted_permissions(principal),
                context_resolver=CapabilityContextResolver(),
            )
            self._executors[key] = executor
        else:
            executor.granted_permissions = self._granted_permissions(principal)
        return executor

    def _granted_permissions(self, principal: Any) -> set:
        if self._explicit_permissions is not None:
            return set(self._explicit_permissions)
        # The executor's capability-level permission is the Gmail read
        # connection boundary.  Per-action legacy grant aliases below add the
        # compose restriction for draft creation.
        if self._legacy_capability_allowed("gmail_search", principal):
            return {"gmail.readonly"}
        return set()

    def _action_permitted(self, capability: str, action: str, principal: Any) -> bool:
        if self._explicit_permissions is not None or self.permission_checker is not None:
            return True
        legacy_id = _ACTION_GRANT_CAPABILITY.get(action)
        return bool(legacy_id and self._legacy_capability_allowed(legacy_id, principal))

    def _legacy_capability_allowed(self, capability_id: str, principal: Any) -> bool:
        if self.permission_checker is not None:
            try:
                return bool(self.permission_checker(capability_id, principal))
            except Exception:
                return False
        try:
            return CapabilityResolver.is_allowed(
                capability_id,
                principal=principal,
                capability_registry=self.capability_registry,
            )
        except Exception:
            return False

    @staticmethod
    def _bind_context(executor, action: str, inputs: Mapping[str, Any], user_text: str) -> Dict[str, Any]:
        grounded = executor.context_resolver.resolve(action, user_text)
        # Explicit inputs win, but omitted fields may only be filled with a
        # real identifier/header returned on this session's earlier turn.
        return {**grounded, **dict(inputs)}

    @staticmethod
    def _execution_response(capability, action, result, inputs):
        raw_status = result.get("status", "failed")
        execution_status = "awaiting_approval" if raw_status == "approval_required" else raw_status
        response = result.get("result", result)
        return {
            "handled": True,
            "status": "success" if execution_status in {"success", "ok", "awaiting_approval"} else "unavailable",
            "plan": {"status": "capability_selected", "capability": capability, "action": action, "inputs": inputs, "source": "multi_action"},
            "execution": {"status": execution_status, "capability": capability, "action": action, "raw_status": raw_status},
            "response": response,
        }

    @staticmethod
    def _permission_denied(capability, action):
        return {
            "handled": True, "status": "unavailable",
            "plan": {"status": "capability_selected", "capability": capability, "action": action, "source": "multi_action"},
            "execution": {"status": "permission_denied", "capability": capability, "action": action},
            "response": {"status": "permission_denied", "message": "This Gmail action is not granted to the current user."},
        }

    @staticmethod
    def _unavailable(capability, action, status):
        return {
            "handled": True, "status": "unavailable",
            "plan": {"status": "capability_selected", "capability": capability, "action": action, "source": "multi_action"},
            "execution": {"status": status, "capability": capability, "action": action},
            "response": {"status": status},
        }
