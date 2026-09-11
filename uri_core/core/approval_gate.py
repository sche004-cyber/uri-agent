"""Deterministic approval enforcement (Milestone 7 — Real Approval
Gate).

This is the ONE execution boundary this codebase should ever call for
a registered capability's execute_tool() - see orchestrator.py's
process_user_input (the direct capability_selected branch) and
workflow_capability_router.py's draft_output, both of which now call
this gate instead of ToolDispatcher directly, so neither call site can
independently drift out of sync with the other or accidentally bypass
approval enforcement.

Authority split (unchanged from ADR-018 / URI_MODEL_RUNTIME_CONTRACT):
CapabilityPlanner and any model-reasoning layer may only ever PROPOSE
a tool_name and arguments. Only this gate - consulting
CapabilityRegistry (Milestone 6) for approval_requirement and
ApprovalStore (this milestone) for a real, bound, single-use user
decision - decides whether ToolDispatcher.execute_tool() is ever
actually called. No model output reaches this gate directly: it only
ever sees the deterministic runtime's own already-selected tool_name/
arguments, exactly as ToolDispatcher already did before this
milestone. approve()/reject() are only ever invoked from an explicit,
separate user action (see server.py's POST /approve, POST /cancel) -
nothing in the request-processing path can call them on its own
behalf.

For a capability whose registry entry has approval_requirement !=
"user_approval_required" (every one of the 4 real tools, today),
execute_tool() below does exactly what ToolDispatcher.execute_tool()
already did before this milestone - one cheap registry lookup, then
an unconditional pass-through. See
test_capability_planner.py/test_capability_authority_boundary.py's
Milestone 6 regression tests, still passing unmodified, and this
milestone's own regression tests in test_approval_gate.py.
"""

from typing import Any, Dict, Optional

from uri_core.core.approval_store import ApprovalError, ApprovalStore
from uri_core.core.audit_trail import AuditTrail
from uri_core.core.capability_registry import CapabilityRegistry
from uri_core.core.capability_resolver import CapabilityResolver

APPROVAL_REQUIRED_VALUE = "user_approval_required"


class ApprovalGate:
    """Duck-types ToolDispatcher's execute_tool(tool_name, **kwargs)
    signature (plus an added session_id) so any existing caller that
    only ever calls .execute_tool(...) can have this substituted in
    place of a raw ToolDispatcher with no other code change."""

    def __init__(
        self,
        dispatcher,
        capability_registry: Optional[CapabilityRegistry] = None,
        approval_store: Optional[ApprovalStore] = None,
        audit_trail: Optional[AuditTrail] = None,
        capability_grants_store: Optional[Any] = None,
        principal: Optional[Any] = None,
    ):
        self.dispatcher = dispatcher
        self.capability_registry = (
            capability_registry or CapabilityRegistry()
        )
        self.approval_store = approval_store or ApprovalStore()
        self.audit_trail = audit_trail or AuditTrail()
        self.capability_grants_store = capability_grants_store
        self.principal = principal

    def _record_audit_safely(self, **kwargs: Any) -> None:
        """Never raises - an audit-recording failure must never break
        the real approval/execution decision it's downstream of.
        Mirrors orchestrator.py's _record_skill_router_audit/
        _record_model_reasoning_audit and server.py's
        _record_growth_event_safely."""
        try:
            self.audit_trail.record(**kwargs)
        except Exception:
            return

    def execute_tool(
        self,
        tool_name: str,
        session_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Called wherever ToolDispatcher.execute_tool() used to be
        called directly. tool_name/kwargs come only from the
        deterministic runtime (CapabilityPlanner's selection, or a
        workflow step's own deterministic logic) - never from
        unvalidated model output."""

        descriptor = self.capability_registry.describe_status(
            tool_name
        )

        # M22.4 Authoritative Check: verify capability is granted for this principal
        # for registered capabilities. Unregistered tools pass through to dispatcher per M7.
        # In multi-user context (grants_store or principal configured), enforce strictly.
        # In legacy single-user ambient test fixtures (both None), maintain backward compatibility.
        if descriptor is not None:
            principal = (
                kwargs.get("principal")
                or kwargs.get("principal_context")
                or self.principal
            )
            grants_store = kwargs.get("grants_store") or self.capability_grants_store
            if grants_store is not None or principal is not None:
                if not CapabilityResolver.is_allowed(
                    tool_name,
                    principal=principal,
                    capability_registry=self.capability_registry,
                    grants_store=grants_store,
                ):
                    self._record_audit_safely(
                        event_type="capability_execution",
                        status="rejected_unauthorized",
                        session_id=session_id,
                        capability=tool_name,
                        metadata={"reason": "Capability not granted for principal"},
                    )
                    return {
                        "status": "rejected",
                        "message": f"Capability {tool_name!r} is not granted for this user.",
                    }

        approval_requirement = (
            descriptor.approval_requirement
            if descriptor is not None
            else "none"
        )

        if approval_requirement != APPROVAL_REQUIRED_VALUE:

            # Item 8 (structured turn tracing): every dispatch - not
            # only the approval-gated lifecycle below - now leaves one
            # real audit record of what was attempted and what actually
            # happened, so diagnostics_context.py has real recent
            # execution history to show the Brain even for the common,
            # no-approval-required path (every real tool today). This
            # changes no return value and no pre-existing dispatch
            # behaviour - only an additive audit record, exactly like
            # every other _record_audit_safely call in this class.
            # M16: session_id is forwarded to the capability alongside
            # the other deterministic arguments. It was previously
            # consumed here and dropped, which no capability noticed
            # because every one of them only read request_text - but a
            # session-scoped capability (read_attached_file, which may
            # only ever read files attached to THIS conversation)
            # genuinely needs it. It remains runtime-supplied context,
            # never model-supplied, so the argument boundary is
            # unchanged; tools take **kwargs and ignore what they don't
            # use.
            dispatch_result = self.dispatcher.execute_tool(
                tool_name, session_id=session_id, **kwargs
            )

            self._record_audit_safely(
                event_type="capability_execution",
                status=dispatch_result.get("status", "unknown"),
                session_id=session_id,
                capability=tool_name,
                metadata=(
                    {"error_type": dispatch_result.get("error_type")}
                    if dispatch_result.get("status") == "error"
                    else {}
                ),
            )

            return dispatch_result

        try:
            proposed = self.approval_store.propose(
                capability_id=tool_name,
                arguments=kwargs,
                session_id=session_id,
            )

        except ApprovalError as exc:

            self._record_audit_safely(
                event_type="capability_execution",
                status="proposal_rejected",
                session_id=session_id,
                capability=tool_name,
                metadata={"reason": str(exc)[:200]},
            )

            return {
                "status": "error",
                "message": (
                    "URI could not propose this action: "
                    f"{exc}"
                ),
            }

        self._record_audit_safely(
            event_type="capability_execution",
            status="proposed_awaiting_approval",
            session_id=session_id,
            capability=tool_name,
            metadata={"action_id": proposed.action_id},
        )

        return {
            "status": "awaiting_approval",
            "action_id": proposed.action_id,
            "tool_name": tool_name,
            "risk": descriptor.risk if descriptor else "unknown",
            # The registry's own human-readable description - see
            # GET /tasks, which already joins the same way. Lets a
            # client show something better than the raw tool_name as
            # a title/subtitle (see http_uri_client.dart).
            "description": descriptor.description if descriptor else None,
            "message": (
                "This action requires your explicit approval before "
                "URI can proceed."
            ),
        }

    def decide(
        self,
        action_id: str,
        approved: bool,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Records a real user decision for one proposed action and,
        only if approved, executes it immediately through the same
        self.dispatcher used by execute_tool() above - never a
        second, unaudited path to execution. Fails closed (returns an
        error, never executes) on any invalid, missing, expired, or
        mismatched approval - see ApprovalStore.decide()/consume()
        for the exact checks."""

        try:
            record = self.approval_store.decide(
                action_id, approved=approved, session_id=session_id
            )

        except ApprovalError as exc:

            self._record_audit_safely(
                event_type="capability_execution",
                status="approval_decision_rejected",
                session_id=session_id,
                metadata={
                    "action_id": action_id,
                    "reason": str(exc)[:200],
                },
            )

            return {"status": "error", "message": str(exc)}

        self._record_audit_safely(
            event_type="capability_execution",
            status="approved" if approved else "rejected",
            session_id=session_id,
            capability=record.capability_id,
            metadata={"action_id": action_id},
        )

        if not approved:
            return {"status": "cancelled", "action_id": action_id}

        try:
            self.approval_store.consume(
                action_id,
                capability_id=record.capability_id,
                arguments=record.arguments,
                session_id=session_id,
            )

        except ApprovalError as exc:

            self._record_audit_safely(
                event_type="capability_execution",
                status="consume_failed",
                session_id=session_id,
                capability=record.capability_id,
                metadata={
                    "action_id": action_id,
                    "reason": str(exc)[:200],
                },
            )

            return {"status": "error", "message": str(exc)}

        # M16: the same session_id forwarding as the no-approval path
        # above, but taken from the APPROVAL RECORD rather than a
        # caller argument - record.session_id is the session the
        # approval was actually bound to (see approval_store.py), so a
        # session-scoped capability can never be executed against a
        # different conversation than the one that was approved.
        dispatch_result = self.dispatcher.execute_tool(
            record.capability_id,
            session_id=record.session_id,
            **record.arguments,
        )

        self._record_audit_safely(
            event_type="capability_execution",
            status="executed_after_approval",
            session_id=session_id,
            capability=record.capability_id,
            metadata={"action_id": action_id},
        )

        return dispatch_result
