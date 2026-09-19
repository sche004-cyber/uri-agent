"""M30.2: canonical, read-only Capability Directory - a single
projection over URI's existing capability systems
(docs/plans/URI_CANONICAL_AGENT_LOOP_MIGRATION_PLAN.md §3).

This is an ADAPTER, not a third registry: it stores nothing, executes
nothing, grants nothing. Every entry it returns is derived, on demand,
from a real, already-authoritative source:

    - uri_core.core.capability_feasibility.CapabilityFeasibility
      (legacy capabilities_registry.json, already connection-aware
      since M20) - source="legacy"
    - uri_core.capabilities.MultiActionCapabilityRegistry (M27's Gmail
      multi-action capability) - source="multi_action"
    - uri_core.core.workflow_planner.WorkflowPlanner's own step
      templates, inventoried (not reimplemented) as one static
      procedure entry - source="procedure" (see
      _inventory_procedures()'s own docstring for what was actually
      found, honestly, rather than assumed)

Nothing here changes execution, authorization, or routing. Execution
still happens exactly where it always has
(uri_core.core.dispatcher.ToolDispatcher via ApprovalGate for legacy
capabilities, uri_core.capabilities.MultiActionExecutor for M27's
Gmail capability) - this module only describes what already exists so
a future Decision Engine (M30.3+) can be told about it consistently.

Progressive discovery (Stage 2 §6, reusing M27's own existing pattern
rather than inventing a second one): `summaries()` returns the compact,
always-safe Level 1 view (id/summary/availability/risk, NO action
schemas); `describe(capability_id)` returns the fuller Level 2 view
(actions, per-action parameters where known) for exactly one capability,
loaded only on demand - never flattened into `summaries()`.

Unknown stays unknown, per the accepted M30.2 scope: nothing here
invents an availability, permission, or schema value a source doesn't
actually provide. Where a source is silent, the corresponding field is
`None` and the entry's `availability_known`/`grounding_supported` flags
say so explicitly rather than defaulting to an optimistic guess.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


def _word_tokens(text: str) -> set:
    """M30.5 bugfix: overlap detection's original `.lower().split()`
    never stripped punctuation, so a summary ending "...Gmail." never
    matched the bare word "gmail" (the trailing period stayed attached
    to the token) - found live during M30.5's own gate testing, not
    theoretical. Matches discovery.py's own `_terms()` tokenization
    convention rather than inventing a second one."""
    return set(re.findall(r"[a-z0-9_]+", (text or "").lower()))

from uri_core.core.capability_feasibility import CapabilityFeasibility

try:
    from uri_core.capabilities import MultiActionCapabilityRegistry
except ImportError:  # pragma: no cover - same defensive convention as turn_state.py
    MultiActionCapabilityRegistry = None  # type: ignore[assignment,misc]


@dataclass(frozen=True)
class CapabilityDirectoryEntry:
    capability_id: str
    summary: str
    source: str  # "legacy" | "multi_action" | "procedure"
    available: Optional[bool]
    availability_known: bool
    availability_reason: Optional[str]
    connection_required: Optional[bool]
    connection_state: Optional[str]
    permission_required: bool
    approval_required: Optional[bool]
    risk: Optional[str]
    action_names: List[str] = field(default_factory=list)
    execution_reference: Optional[str] = None
    result_schema_known: bool = False
    health_status: Optional[str] = None
    grounding_supported: bool = False
    deprecated: bool = False
    # M33 Batch B: extends Level 1 visibility with what `to_summary_dict`
    # previously dropped - alternate names, per-action descriptions, and
    # normalized intent signals (blueprint §6 Batch B). Empty defaults
    # for every existing legacy/procedure entry, which declares none of
    # these; populated for multi_action entries from `Capability.aliases`/
    # `.intent_signals` and each action's own description.
    aliases: List[str] = field(default_factory=list)
    action_descriptions: Dict[str, str] = field(default_factory=dict)
    intent_signals: List[str] = field(default_factory=list)
    category: Optional[str] = None
    # M30.5B: a property of the CAPABILITY itself, declared once here -
    # never a property of any one sentence's wording. "Foundational"
    # means this capability's relevance cannot be judged by topical/
    # lexical overlap with the user's words at all (a personal
    # disclosure like "I work at NIT Sikkim" or "call me Alex" shares
    # almost no vocabulary with "save a fact the user asked to
    # remember" - the two are related by SPEECH ACT, not topic). See
    # _FOUNDATIONAL_CAPABILITY_IDS below for the reasoned, short list
    # this applies to.
    foundational: bool = False
    reads_current_attachments: bool = False

    def to_summary_dict(self) -> Dict[str, Any]:
        """Level 1 - compact, Turn-State-safe. No action schemas."""
        return {
            "capability_id": self.capability_id,
            "summary": self.summary,
            "source": self.source,
            "available": self.available,
            "availability_known": self.availability_known,
            "availability_reason": self.availability_reason,
            "connection_required": self.connection_required,
            "connection_state": self.connection_state,
            "permission_required": self.permission_required,
            "approval_required": self.approval_required,
            "risk": self.risk,
            "actions": list(self.action_names),
            "foundational": self.foundational,
            "aliases": list(self.aliases),
            "action_descriptions": dict(self.action_descriptions),
            "intent_signals": list(self.intent_signals),
            "category": self.category,
            "reads_current_attachments": self.reads_current_attachments,
        }

    def to_detail_dict(self, action_schemas: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Level 2 - loaded only once this capability is selected."""
        detail = dict(self.to_summary_dict())
        detail.update(
            {
                "execution_reference": self.execution_reference,
                "result_schema_known": self.result_schema_known,
                "health_status": self.health_status,
                "grounding_supported": self.grounding_supported,
                "deprecated": self.deprecated,
                "action_schemas": action_schemas or {},
            }
        )
        return detail


# M30.5B: reasoned, short, and explicit - not "phrase-specific
# routing" (no user wording is matched here at all). These two
# capabilities are marked foundational because ANY conversational turn
# can plausibly involve the user stating or asking about a fact about
# themselves, independent of what topic that fact concerns - unlike a
# domain-specific tool (Gmail, a spreadsheet fetch, a system-metrics
# read), their relevance is a property of the SPEECH ACT (disclosure /
# recall), not of the goal's topic vocabulary, so lexical overlap
# scoring structurally cannot judge their relevance and must not be
# asked to.
_FOUNDATIONAL_CAPABILITY_IDS = {"remember_fact", "recall_memory"}


def _is_foundational(capability_id: str, feasibility_entry: Dict[str, Any]) -> bool:
    """M33 Batch B: foundational status now reads the capability's own
    registry entry first (a `"foundational": true/false` key in
    `capabilities_registry.json`, exactly the descriptor field the
    blueprint asks for), falling back to the hardcoded
    `_FOUNDATIONAL_CAPABILITY_IDS` set only when that entry declares no
    opinion (key absent) - so today's two hardcoded ids keep working
    exactly as before (nothing in `capabilities_registry.json` declares
    the key yet) while any future entry, including an external one, can
    declare its own foundational status without another hardcoded-set
    edit."""
    declared = feasibility_entry.get("foundational")
    if isinstance(declared, bool):
        return declared
    return capability_id in _FOUNDATIONAL_CAPABILITY_IDS


def _legacy_entries(
    capability_feasibility: Optional[CapabilityFeasibility],
) -> Dict[str, CapabilityDirectoryEntry]:
    entries: Dict[str, CapabilityDirectoryEntry] = {}
    if capability_feasibility is None:
        return entries

    try:
        snapshot = capability_feasibility.snapshot()
    except Exception:
        return entries

    for capability_id, feasibility_entry in snapshot.items():
        if not isinstance(feasibility_entry, dict):
            continue
        usable = feasibility_entry.get("usable")
        gap_reason = feasibility_entry.get("gap_reason")
        blocked_by = feasibility_entry.get("blocked_by") or []
        interface = feasibility_entry.get("interface")

        connection_required = bool(blocked_by) or (
            gap_reason == "unavailable_runtime"
        )
        entries[capability_id] = CapabilityDirectoryEntry(
            capability_id=capability_id,
            summary=str(feasibility_entry.get("description") or ""),
            source="legacy",
            available=usable,
            # CapabilityFeasibility computes this fresh, in full, every
            # call (M20) - the legacy catalogue's availability truth is
            # always known, never a guess.
            availability_known=True,
            availability_reason=gap_reason,
            connection_required=connection_required if connection_required else None,
            connection_state=", ".join(blocked_by) if blocked_by else None,
            permission_required=_permission_required_for_legacy(feasibility_entry),
            approval_required=feasibility_entry.get("requires_approval"),
            risk=feasibility_entry.get("risk"),
            # A legacy capability is a single opaque unit to CapabilityPlanner/
            # ToolDispatcher today - it has no sub-actions, only itself.
            action_names=[capability_id],
            execution_reference="dispatcher.ToolDispatcher via ApprovalGate",
            # interface, when a curated registry entry provides one, is
            # the closest thing legacy capabilities have to a declared
            # schema - reused, never fabricated when absent.
            result_schema_known=isinstance(interface, dict) and bool(interface.get("returns")),
            health_status=None,  # legacy capabilities have no independent health signal (Stage 1 §5)
            grounding_supported=False,  # no legacy CapabilityContextResolver equivalent yet
            deprecated=False,
            foundational=_is_foundational(capability_id, feasibility_entry),
            category=feasibility_entry.get("category"),
            reads_current_attachments=bool(feasibility_entry.get("reads_current_attachments")),
        )

    return entries


def _permission_required_for_legacy(feasibility_entry: Dict[str, Any]) -> bool:
    blocked_by = feasibility_entry.get("blocked_by") or []
    return bool(blocked_by)


def _multi_action_entries(
    multi_action_registry: Optional["MultiActionCapabilityRegistry"],
) -> Dict[str, CapabilityDirectoryEntry]:
    entries: Dict[str, CapabilityDirectoryEntry] = {}
    if multi_action_registry is None:
        return entries

    try:
        summaries = multi_action_registry.capability_summaries()
    except Exception:
        return entries

    for summary in summaries:
        capability_id = summary.get("name")
        if not capability_id:
            continue
        actions = summary.get("actions") or []
        # M33 Batch B: read directly off the real `Capability` object
        # rather than extending `capability_summaries()`'s own return
        # shape - that shape is asserted by exact equality elsewhere
        # (test_multi_action_capabilities.py), and this achieves the
        # same "category/aliases/per-action descriptions surfaced at
        # Level 1" goal without touching it. `get_capability` is cheap
        # (an in-memory dict lookup) - no live availability_check() call,
        # so the "nothing is known yet at Level 1" comment below still
        # holds exactly as before.
        _capability_obj = multi_action_registry.get_capability(capability_id)
        _capability_aliases = list(getattr(_capability_obj, "aliases", ()) or ())
        _capability_intent_signals = list(getattr(_capability_obj, "intent_signals", ()) or ())
        _capability_action_descriptions = {
            action.name: action.description for action in (_capability_obj.list_actions() if _capability_obj else [])
        }
        # This is the exact Stage 1 §1/§11.6 gap, made representable
        # rather than papered over: M27's own summary stage carries no
        # connection/usability signal at all. describe() below CAN
        # surface a real per-action availability_check() result once a
        # capability is selected (Level 2) - but at Level 1, honestly,
        # nothing is known yet.
        entries[capability_id] = CapabilityDirectoryEntry(
            capability_id=capability_id,
            summary=str(summary.get("description") or ""),
            source="multi_action",
            available=None,
            availability_known=False,
            availability_reason=None,
            connection_required=None,
            connection_state=None,
            permission_required=True,  # every multi-action capability declares real permissions
            approval_required=None,  # varies per action - unknown at the capability level
            risk=None,  # varies per action - unknown at the capability level
            action_names=list(actions),
            execution_reference="uri_core.capabilities.MultiActionExecutor",
            result_schema_known=True,  # every Action declares a `returns` schema
            health_status=None,
            grounding_supported=True,  # CapabilityContextResolver exists for this family
            deprecated=False,
            aliases=list(_capability_aliases),
            action_descriptions=dict(_capability_action_descriptions),
            intent_signals=list(_capability_intent_signals),
            category=summary.get("category"),
        )

    return entries


# 2026-09-12: WorkflowPlanner's own _create_steps() branches on keyword
# overlap ("insurance"/"renewal", "note"/"noting") but every branch this
# audit found produces the IDENTICAL six-step sequence - this is
# genuinely ONE procedure, not several distinct named ones, despite the
# branching. Recorded here exactly as found (direct source inspection,
# uri_core/core/workflow_planner.py), not assumed from its own docstring.
_GENERIC_WORKFLOW_STEPS = [
    "retrieve_evidence",
    "verify_facts",
    "identify_missing_information",
    "prepare_decision_context",
    "draft_output",
    "review_result",
]


def _inventory_procedures() -> Dict[str, CapabilityDirectoryEntry]:
    """The full M30.2 procedure inventory. See module-level comment
    above `_GENERIC_WORKFLOW_STEPS` for what was actually found."""
    return {
        "generic_evidence_drafting_workflow": CapabilityDirectoryEntry(
            capability_id="generic_evidence_drafting_workflow",
            summary=(
                "WorkflowPlanner's one existing deterministic multi-step "
                "template (evidence retrieval through drafted output and "
                "review) - every keyword branch in workflow_planner.py's "
                "_create_steps() converges on this same sequence."
            ),
            source="procedure",
            available=True,
            availability_known=True,
            availability_reason=None,
            connection_required=False,
            connection_state=None,
            permission_required=False,
            approval_required=False,
            risk="controlled",
            action_names=list(_GENERIC_WORKFLOW_STEPS),
            execution_reference="uri_core.core.workflow_executor.WorkflowExecutor",
            result_schema_known=False,
            health_status=None,
            grounding_supported=False,
            deprecated=False,
        )
    }


def _find_overlaps(
    legacy: Dict[str, CapabilityDirectoryEntry],
    multi_action: Dict[str, CapabilityDirectoryEntry],
) -> List[Dict[str, Any]]:
    """Approximate, honestly-labeled overlap detection - a shared
    significant word between a legacy capability's id/summary and a
    multi-action capability's id/summary. This is a heuristic, not an
    authoritative identity resolution; it exists to make an overlap
    VISIBLE for human review, never to silently merge or retire either
    side (per the accepted M30.2 scope)."""

    overlaps: List[Dict[str, Any]] = []
    for multi_id, multi_entry in multi_action.items():
        multi_words = _word_tokens(multi_id + " " + multi_entry.summary)
        for legacy_id, legacy_entry in legacy.items():
            legacy_words = _word_tokens(legacy_id + " " + legacy_entry.summary)
            shared = multi_words & legacy_words
            # Require the multi-action capability's own bare id to be
            # one of the shared words (e.g. "gmail") - a weaker overlap
            # (sharing only a generic word) is not reported, to keep
            # this a real signal rather than noise.
            if multi_id.lower() in shared:
                overlaps.append(
                    {
                        "identity": multi_id,
                        "legacy_id": legacy_id,
                        "multi_action_id": multi_id,
                        "functionally_equivalent": False,
                        # The multi-action side has a much wider action
                        # surface (read_message/read_thread/read_
                        # attachment/create_draft/...) than any single
                        # legacy tool - recorded as a finding, not
                        # asserted from assumption; see the directory's
                        # own action_names on each side for the real
                        # comparison.
                        "richer_source": "multi_action"
                        if len(multi_entry.action_names) > 1
                        else "unknown",
                        "consolidation_recommended_later": True,
                    }
                )
    return overlaps


class CapabilityDirectory:
    """The one canonical, read-only directory. Constructed fresh per
    call site (cheap - both underlying reads are already-cheap local
    computations, same discipline as CapabilityFeasibility itself)."""

    def __init__(
        self,
        capability_feasibility: Optional[CapabilityFeasibility] = None,
        multi_action_registry: Optional["MultiActionCapabilityRegistry"] = None,
        include_procedures: bool = True,
    ) -> None:
        self._legacy = _legacy_entries(capability_feasibility)
        self._multi_action = _multi_action_entries(multi_action_registry)
        self._procedures = _inventory_procedures() if include_procedures else {}
        self._multi_action_registry = multi_action_registry

    def _all_entries(self) -> Dict[str, CapabilityDirectoryEntry]:
        merged: Dict[str, CapabilityDirectoryEntry] = {}
        merged.update(self._legacy)
        merged.update(self._multi_action)
        merged.update(self._procedures)
        return merged

    def _suppressed_legacy_ids(self) -> set:
        """M30.5A Gmail-overlap policy, stated explicitly (not chosen
        by registration order): when a legacy capability overlaps a
        richer multi-action capability (per _find_overlaps' own
        "richer_source" finding), the legacy sibling is suppressed from
        Brain-visible summaries() - the Brain sees exactly ONE Gmail
        identity, never three-plus ambiguous ones. Nothing is deleted:
        the legacy id remains fully resolvable via describe()/_all_
        entries() for internal execution/gate/fallback use - only its
        VISIBILITY to a fresh decision is narrowed. If a future overlap
        is NOT clearly richer on either side, neither side is
        suppressed (both stay visible) rather than guessing."""
        suppressed = set()
        for record in _find_overlaps(self._legacy, self._multi_action):
            if record.get("richer_source") == "multi_action":
                suppressed.add(record["legacy_id"])
        return suppressed

    def summaries(self, resolve_overlaps: bool = True) -> List[Dict[str, Any]]:
        """Level 1 - always-safe for Turn State / Brain visibility.
        `resolve_overlaps=True` (the default, and what Turn State/the
        Decision Engine should always use) applies the M30.5A Gmail-
        overlap policy above; pass False only for internal/diagnostic
        listing of literally everything registered (e.g. this
        directory's own overlaps()/describe() still see every id
        regardless of this flag - only summaries() is ever narrowed)."""
        suppressed = self._suppressed_legacy_ids() if resolve_overlaps else set()
        return [
            entry.to_summary_dict()
            for capability_id, entry in self._all_entries().items()
            if capability_id not in suppressed
        ]

    def describe(self, capability_id: str) -> Optional[Dict[str, Any]]:
        """Level 2 - full detail for exactly one, already-selected
        capability. Returns None for an unknown id (never fabricated)."""
        entry = self._all_entries().get(capability_id)
        if entry is None:
            return None

        action_schemas: Dict[str, Any] = {}
        availability_override: Optional[Dict[str, Any]] = None
        if entry.source == "multi_action" and self._multi_action_registry is not None:
            try:
                detail = self._multi_action_registry.describe_capability(capability_id)
            except Exception:
                detail = None
            if detail:
                for action in detail.get("actions", []):
                    action_schemas[action["name"]] = {
                        "description": action.get("description"),
                        "parameters": action.get("parameters"),
                        "required": action.get("required"),
                        "returns": action.get("returns"),
                        "read_only": action.get("read_only"),
                        "approval_requirement": action.get("approval_requirement"),
                        "risk": action.get("risk"),
                    }
                # M30.5: describe_capability() already computes a REAL,
                # live availability (Capability.check_availability(),
                # e.g. GmailCapability's own real Gmail connection
                # check) - Level 1 (summaries()) still can't know this
                # without calling it for every capability every turn,
                # but Level 2, scoped to exactly the one capability
                # already selected, can and should surface it. Closes
                # the exact gap M30.2/M30.3/M30.4 each independently
                # flagged and left open.
                availability = detail.get("availability")
                if isinstance(availability, dict) and "available" in availability:
                    availability_override = availability

        result = entry.to_detail_dict(action_schemas=action_schemas)
        if availability_override is not None:
            result["available"] = bool(availability_override.get("available"))
            result["availability_known"] = True
            if not result["available"]:
                missing = availability_override.get("missing_preconditions") or []
                result["availability_reason"] = (
                    "unavailable_runtime" if missing else "unavailable_runtime"
                )
                result["connection_required"] = True
                result["connection_state"] = ", ".join(str(m) for m in missing) or "not_connected"
        return result

    def overlaps(self) -> List[Dict[str, Any]]:
        """Duplicate/overlap findings across sources - reported, never
        silently resolved (per the accepted M30.2 scope: 'do not
        silently merge them')."""
        return _find_overlaps(self._legacy, self._multi_action)
