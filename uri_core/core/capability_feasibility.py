"""M20: a deterministic, non-authoritative "can this actually run right
now" snapshot of the capability catalogue.

CapabilityRegistry.is_executable already distinguishes "an execution
adapter exists" (status == "implemented") from "no adapter exists at
all" (planned/not_implemented). It does NOT distinguish "exists and
can run right now" from "exists but this runtime currently can't use
it" - a registry entry can be status="implemented" and
availability="unavailable_missing_dependency" (e.g. gmail_search
without a stored OAuth token) and still count as executable by that
property alone. That gap let a Brain proposal for such a capability be
validated, promoted to the real plan, and dispatched, only to fail at
execution - the exact "stops with a tool/skill-unavailable error"
symptom this module exists to prevent one layer earlier.

This module answers ONE question per capability - "is it usable right
now" - by combining two already-authoritative, already-existing
sources, duplicating neither:
    - CapabilityRegistry (status/availability/gap_reason/permissions/
      approval_requirement/risk) - unchanged, still the sole source of
      what a capability IS.
    - connection_status.list_connection_status() (real Gmail/Drive
      OAuth state) - unchanged, still the sole source of whether an
      external service is actually authorized on this host.

It never selects, ranks, or scores a capability - that remains
CapabilityPlanner's (deterministic fallback) and the Brain's
(everything else) job. It is purely a read-only composition layer, in
the same spirit as query_context.py: it decides nothing, it only
reports. Never imported by dispatcher.py/approval_gate.py, and never
itself a place execution or authorization logic lives.

Fail-safe direction: any failure while determining WHY a capability
might be blocked (a connection-status read failing, an unrecognized
permission) must never make the runtime MORE restrictive than it was
before this module existed - it degrades to "not blocked" for that
specific reason, never to "unusable". The one thing that is never
softened is CapabilityRegistry's own is_executable/gap_reason - if the
registry itself says a capability doesn't exist, this module never
overrides that.
"""

from typing import Any, Dict, List, Optional

from uri_core.core.capability_registry import (
    CapabilityDescriptor,
    CapabilityRegistry,
)
from uri_core.core.connection_status import list_connection_status

# Maps a registry-declared permission string to the connection_status
# service id it depends on, by prefix - the two vocabularies are
# already close (see capabilities_registry.json's "permissions" and
# connection_status.py's service ids "gmail"/"drive") but not
# identical, so this is a small, explicit, reviewable table rather
# than a guessed string transform. A permission with no entry here
# (external_web_search, read_user_attachments, system_command_execution,
# ...) simply has no connection-status dependency to check - it is
# never treated as blocked by this table.
_PERMISSION_SERVICE_PREFIXES = (
    ("gmail", "gmail"),
    ("google_drive", "drive"),
    ("drive", "drive"),
)


def _connection_status_by_service() -> Dict[str, Dict[str, str]]:
    """service_id -> {"status", "detail"} for every known external
    service. Never raises - a failure here degrades to an empty dict,
    which _permission_blocked_by then treats as "nothing known to be
    blocked" (fail-open, per this module's docstring)."""

    try:
        services = list_connection_status()
    except Exception:
        return {}

    by_service: Dict[str, Dict[str, str]] = {}

    for service in services:
        if not isinstance(service, dict):
            continue
        service_id = service.get("id")
        if isinstance(service_id, str):
            by_service[service_id] = service

    return by_service


def _permission_blocked_by(
    permissions: List[str],
    connection_by_service: Dict[str, Dict[str, str]],
) -> List[str]:
    """Plain-language reasons this capability's declared permissions
    are currently blocked by a real, unauthorized external service -
    never guessed, only ever derived from connection_status's real
    state. Empty list when nothing is blocked, connection status is
    unknown, or the capability declares no service-backed permission
    at all."""

    reasons: List[str] = []

    for permission in permissions:

        permission_text = str(permission)
        permission_lower = permission_text.lower()

        service_id = None

        for prefix, mapped_service in _PERMISSION_SERVICE_PREFIXES:
            if permission_lower.startswith(prefix):
                service_id = mapped_service
                break

        if service_id is None:
            continue

        service_state = connection_by_service.get(service_id)

        if not isinstance(service_state, dict):
            continue

        if service_state.get("status") == "connected":
            continue

        detail = service_state.get("detail") or service_state.get("status")

        reasons.append(f"{permission_text}: {detail}")

    return reasons


def _feasibility_entry(
    descriptor: CapabilityDescriptor,
    connection_by_service: Dict[str, Dict[str, str]],
) -> Dict[str, Any]:

    try:
        blocked_by = _permission_blocked_by(
            list(descriptor.permissions), connection_by_service
        )
    except Exception:
        blocked_by = []

    usable = (
        descriptor.is_executable
        and descriptor.gap_reason is None
        and not blocked_by
    )

    return {
        "id": descriptor.id,
        "description": descriptor.description,
        "usable": usable,
        "gap_reason": (
            None if usable else (descriptor.gap_reason or "blocked_by_permission")
        ),
        "blocked_by": blocked_by,
        "requires_approval": descriptor.approval_requirement
        == "user_approval_required",
        "risk": descriptor.risk,
        "interface": descriptor.interface,
    }


class CapabilityFeasibility:
    """Deterministic, read-only, non-authoritative. See module
    docstring. One instance is cheap to construct and safe to call
    once per turn - both underlying reads are small local JSON/file
    checks, no network calls."""

    def __init__(
        self,
        registry_path: str = "uri_workspace/capabilities_registry.json",
        capability_registry: Optional[CapabilityRegistry] = None,
    ):
        self.capability_registry = (
            capability_registry
            if capability_registry is not None
            else CapabilityRegistry(registry_path=registry_path)
        )

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        """capability_id -> feasibility entry for every descriptor
        CapabilityRegistry knows about (implemented AND planned/
        not_implemented alike, matching list_capabilities()'s own
        scope). Never raises: a registry read failure degrades to an
        empty snapshot, which every caller in this codebase treats as
        "nothing extra known" rather than "everything is unusable" -
        see orchestrator.py's use sites."""

        try:
            descriptors = self.capability_registry.list_capabilities()
        except Exception:
            return {}

        connection_by_service = _connection_status_by_service()

        return {
            descriptor.id: _feasibility_entry(descriptor, connection_by_service)
            for descriptor in descriptors
            if isinstance(descriptor, CapabilityDescriptor)
        }

    def usable_ids(self) -> set:
        """The subset of the snapshot that is genuinely usable right
        now - implemented, not runtime-gapped, and not blocked by an
        unauthorized permission. Never raises."""

        try:
            return {
                capability_id
                for capability_id, entry in self.snapshot().items()
                if entry.get("usable")
            }
        except Exception:
            return set()
