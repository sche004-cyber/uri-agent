"""URI's capability self-knowledge: one authoritative, curated
descriptor per capability, distinguishing what CapabilityPlanner/
ToolDispatcher can actually execute today from what is merely planned
or not yet implemented.

This module is reporting/query-only. It never executes anything, never
grants authorization or approval, and must never be imported by
anything that decides what to execute (dispatcher.py) - only by
capability_planner.py's gap-reporting path (informational) and
server.py's GET /capabilities (informational).

Reads uri_workspace/capabilities_registry.json - the same file
ToolDispatcher/CapabilityPlanner already read, restructured (not
duplicated) to carry descriptor metadata alongside the existing
execution fields (file_path/class_name/method) each already-registered
tool's entry has always had. See that file for the full shape.

Deliberately does NOT read uri_workspace/skill_registry.json. That
file (362 entries, built by build_skill_registry_v1.py from an
automated inventory scan, mostly-empty descriptive fields) is not
authoritative for "what can URI actually do" - it remains consumed
only by the dormant SkillEvaluatorV1/SkillRouterV1 shadow path
(orchestrator.py's _run_skill_router_shadow), unrelated to this
module.

Two capability statuses exist alongside "implemented":
    planned         - URI conceptually knows this is a future
                      capability; no executable backing exists.
    not_implemented - same as planned, used interchangeably by intent
                      (both mean "cannot execute this"); kept as two
                      words so a curated entry can say which is true
                      today without this module treating them
                      differently. Neither is ever selectable by
                      CapabilityPlanner.plan() - see
                      test_capability_planner.py.

Unknown-safe throughout: a missing or invalid field degrades to a safe
"unknown"/empty default rather than being guessed or raising -
mirroring UserProfileStore/MemoryStore/GrowthLedgerStore's existing
"degrade rather than crash on corrupted local state" discipline.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

VALID_STATUS = {"implemented", "planned", "not_implemented"}

VALID_AVAILABILITY = {
    "available",
    "unavailable_on_runtime",
    "unavailable_missing_dependency",
    "unknown",
}

VALID_APPROVAL_REQUIREMENT = {"none", "user_approval_required"}

VALID_RISK = {"controlled", "low", "variable", "high", "unknown"}

DEFAULT_STATUS = "unknown"
DEFAULT_AVAILABILITY = "unknown"
DEFAULT_APPROVAL_REQUIREMENT = "none"
DEFAULT_RISK = "unknown"
DEFAULT_PLATFORM = "any"


@dataclass(frozen=True)
class CapabilityDescriptor:
    id: str
    description: str
    status: str
    availability: str
    permissions: List[str] = field(default_factory=list)
    approval_requirement: str = DEFAULT_APPROVAL_REQUIREMENT
    risk: str = DEFAULT_RISK
    platform: str = DEFAULT_PLATFORM
    limitations: str = ""
    interface: Optional[Dict[str, Any]] = None

    @property
    def is_executable(self) -> bool:
        """True only for a real, dispatcher-registered capability.
        planned/not_implemented/unknown-status entries are always
        False - this is the one property CapabilityPlanner's gap path
        may rely on to decide whether an entry could ever be selected."""

        return self.status == "implemented"


def _clean_choice(value: Any, valid: set, default: str) -> str:
    return value if value in valid else default


def _descriptor_from_entry(
    capability_id: str,
    entry: Dict[str, Any],
    default_status: str,
) -> CapabilityDescriptor:

    if not isinstance(entry, dict):
        entry = {}

    permissions = entry.get("permissions", [])

    if not isinstance(permissions, list):
        permissions = []

    interface = entry.get("interface")

    if not isinstance(interface, dict):
        interface = None

    return CapabilityDescriptor(
        id=capability_id,
        description=str(entry.get("description", "") or ""),
        status=_clean_choice(
            entry.get("status", default_status),
            VALID_STATUS,
            default_status,
        ),
        availability=_clean_choice(
            entry.get("availability", DEFAULT_AVAILABILITY),
            VALID_AVAILABILITY,
            DEFAULT_AVAILABILITY,
        ),
        permissions=[str(p) for p in permissions],
        approval_requirement=_clean_choice(
            entry.get(
                "approval_requirement", DEFAULT_APPROVAL_REQUIREMENT
            ),
            VALID_APPROVAL_REQUIREMENT,
            DEFAULT_APPROVAL_REQUIREMENT,
        ),
        risk=_clean_choice(
            entry.get("risk", DEFAULT_RISK), VALID_RISK, DEFAULT_RISK
        ),
        platform=str(entry.get("platform", DEFAULT_PLATFORM) or DEFAULT_PLATFORM),
        limitations=str(entry.get("limitations", "") or ""),
        interface=interface,
    )


class CapabilityRegistry:
    """Loads uri_workspace/capabilities_registry.json and exposes it as
    CapabilityDescriptor objects. Read-only - this class never writes
    to the registry file; curating it (adding/promoting a capability)
    is an out-of-band, human-reviewed file edit, not something this
    class or any runtime code path performs."""

    def __init__(
        self,
        registry_path: str = "uri_workspace/capabilities_registry.json",
    ):
        self.registry_path = os.path.normpath(registry_path)

    def _load_raw(self) -> Dict[str, Any]:

        try:

            with open(
                self.registry_path, "r", encoding="utf-8-sig"
            ) as file:
                data = json.load(file)

            return data if isinstance(data, dict) else {}

        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def list_capabilities(self) -> List[CapabilityDescriptor]:

        raw = self._load_raw()

        active_tools = raw.get("active_tools", {})

        if not isinstance(active_tools, dict):
            active_tools = {}

        planned_capabilities = raw.get("planned_capabilities", {})

        if not isinstance(planned_capabilities, dict):
            planned_capabilities = {}

        descriptors = [
            _descriptor_from_entry(
                capability_id, entry, default_status="implemented"
            )
            for capability_id, entry in active_tools.items()
        ]

        descriptors.extend(
            _descriptor_from_entry(
                capability_id, entry, default_status="not_implemented"
            )
            for capability_id, entry in planned_capabilities.items()
        )

        return descriptors

    def describe_status(
        self, capability_id: str
    ) -> Optional[CapabilityDescriptor]:

        for descriptor in self.list_capabilities():

            if descriptor.id == capability_id:
                return descriptor

        return None

    def known_gaps(self) -> List[CapabilityDescriptor]:
        """Every non-executable descriptor (planned/not_implemented/
        unknown-status) - informational only, used by
        CapabilityPlanner's gap-reporting path to explain a miss
        honestly instead of a single generic sentence. Never consulted
        for selection - see CapabilityDescriptor.is_executable."""

        return [
            descriptor
            for descriptor in self.list_capabilities()
            if not descriptor.is_executable
        ]
