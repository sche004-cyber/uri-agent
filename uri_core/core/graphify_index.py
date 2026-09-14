"""Graphify Foundation: a system-level, read-only index of capabilities,
skills, workflows, and memory pointers - "URI's cognitive index and
GPS." See docs/plans/M30_GRAPHIFY_FOUNDATION_PLAN.md.

Separate from, and never a replacement for, M23's own per-user
`GraphStore` (`graph_store.py`/`graph_engine.py`/`graph_ingest.py`),
which continues unchanged, still serving facts/memory exactly as it
does today. This module indexes system-level, install-wide state
(what capabilities/skills/workflows exist and roughly what state
they're in), not per-user entities.

Every field this module produces is sourced from an already-existing,
already-generic authority - `CapabilityDirectory.summaries()`/
`describe()`, `SkillMemory.list_skills()`, `WorkflowPlanner`'s own
template set, `MemoryStore.list_all()` - never a second, competing
source of truth. This module stores POINTERS (a lookup key back into
the real authority), never a copy of the real content - `availability`
is refreshed fresh, never a snapshot frozen at build time.

Non-authoritative by construction: this module has no planning,
execution, approval, or authorization capability, and imports nothing
from `model_providers`/`model_router`/`dispatcher`/`approval_gate`/
`approval_store`/`decision_gates`/`decision_engine`/
`canonical_execution` - proven by `test_graphify_index_authority_
boundary.py`, mirroring `test_graph_authority_boundary.py`'s own
AST-based proof exactly.

Never blocking, never raises: every builder function below degrades to
whatever partial index it can build on any collaborator failure - a
missing, stale, or empty index is always a safe, valid state (see
`load_index`'s own quarantine-and-recover discipline, mirroring
`GraphStore`'s existing corrupted-file handling).
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

DEFAULT_INDEX_PATH = "uri_workspace/graphify_index.json"
SCHEMA_VERSION = "1.0"

_SCOPE_PREFIXES = {
    "capabilities": "capability:",
    "skills": "skill:",
    "workflows": "workflow:",
    "memory": "memory:",
}


@dataclass
class GraphifyIndex:
    """The in-memory index. `records` maps a compact id
    (`"capability:Gmail"`, `"skill:remember_fact:...:..."`,
    `"workflow:generic_evidence_drafting_workflow"`,
    `"memory:<memory_id>"`) to a small record dict - never the real
    content, only pointers and metadata (see module docstring)."""

    records: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def get(self, entry_id: str) -> Optional[Dict[str, Any]]:
        return self.records.get(entry_id)

    def list_all(self) -> List[Dict[str, Any]]:
        return list(self.records.values())

    def relevant_subset(self, goal_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """The small, relevance-filtered view the Brain actually
        receives (Turn State's `capability_index_hint`) - never the
        whole index. Reuses `capability_relevance.py`'s own already-
        generic, already-tested, directory-derived scorer (the exact
        module the Scenario 2 connection-gate repair also reuses) -
        never a new, fourth relevance heuristic. Never raises -
        degrades to an empty list on any failure."""
        try:
            from uri_core.core.capability_relevance import plausible_matches
        except Exception:
            return []

        class _SummaryView:
            def __init__(self, records: Dict[str, Dict[str, Any]]) -> None:
                self._records = records

            def summaries(self) -> List[Dict[str, Any]]:
                return [
                    {
                        "capability_id": entry_id,
                        "summary": record.get("summary", ""),
                        "actions": record.get("dependencies", []),
                    }
                    for entry_id, record in self._records.items()
                ]

        try:
            matches = plausible_matches(_SummaryView(self.records), goal_text, limit=limit)
        except Exception:
            return []
        return [
            self.records[match["capability"]]
            for match in matches
            if match.get("capability") in self.records
        ]


def _record(
    *,
    entry_id: str,
    kind: str,
    source_path: Optional[str],
    provenance: Optional[str],
    dependencies: List[str],
    availability: Dict[str, Any],
    pointer: Dict[str, Any],
    summary: str = "",
) -> Dict[str, Any]:
    return {
        "id": entry_id,
        "kind": kind,
        "summary": summary,
        "source_path": source_path,
        "provenance": provenance,
        "dependencies": list(dependencies),
        "availability": availability,
        "pointer": pointer,
    }


def _index_capabilities(capability_directory: Any) -> Dict[str, Dict[str, Any]]:
    records: Dict[str, Dict[str, Any]] = {}
    if capability_directory is None:
        return records
    try:
        summaries = capability_directory.summaries()
    except Exception:
        return records
    for summary in summaries:
        capability_id = summary.get("capability_id") if isinstance(summary, dict) else None
        if not capability_id:
            continue
        try:
            described = capability_directory.describe(capability_id) or {}
        except Exception:
            described = {}
        entry_id = f"capability:{capability_id}"
        records[entry_id] = _record(
            entry_id=entry_id,
            kind="capability",
            source_path=None,
            provenance=described.get("execution_reference"),
            dependencies=list(described.get("actions") or []),
            availability={
                "known": described.get("availability_known"),
                "available": described.get("available"),
                "reason": described.get("availability_reason"),
            },
            pointer={"registry": "CapabilityDirectory", "lookup_key": capability_id},
            summary=str(summary.get("summary") or ""),
        )
    return records


def _index_skills(skill_memory: Any) -> Dict[str, Dict[str, Any]]:
    records: Dict[str, Dict[str, Any]] = {}
    if skill_memory is None:
        return records
    try:
        skills = skill_memory.list_skills()
    except Exception:
        return records
    for skill in skills:
        if not isinstance(skill, dict):
            continue
        tool_name = skill.get("tool_name")
        task_type = skill.get("task_type", "")
        domain = skill.get("domain", "")
        entry_id = f"skill:{tool_name}:{task_type}:{domain}"
        records[entry_id] = _record(
            entry_id=entry_id,
            kind="skill",
            source_path=None,
            provenance="skill_memory",
            dependencies=[tool_name] if tool_name else [],
            availability={"known": None, "available": None, "reason": None},
            pointer={
                "registry": "SkillMemory",
                "lookup_key": {"task_type": task_type, "domain": domain},
            },
            summary=f"Learned skill for task_type={task_type!r}/domain={domain!r} -> {tool_name}",
        )
    return records


def _index_workflows(workflow_planner: Any) -> Dict[str, Dict[str, Any]]:
    records: Dict[str, Dict[str, Any]] = {}
    if workflow_planner is None:
        return records
    # WorkflowPlanner._create_steps() converges every task type on one
    # real template today (independently confirmed, docs/plans/
    # M30_8_CANONICAL_CUTOVER_LEGACY_RETIREMENT_PLAN.md §2) - already
    # exposed as a real CapabilityDirectory procedure entry
    # (`generic_evidence_drafting_workflow`). Indexed here as a pointer
    # to that same procedure, never a second definition of it.
    entry_id = "workflow:generic_evidence_drafting_workflow"
    records[entry_id] = _record(
        entry_id=entry_id,
        kind="workflow",
        source_path="uri_core/core/workflow_planner.py",
        provenance="workflow_planner",
        dependencies=[
            "retrieve_evidence", "verify_facts", "identify_missing_information",
            "prepare_decision_context", "draft_output", "review_result",
        ],
        availability={"known": True, "available": True, "reason": None},
        pointer={"registry": "CapabilityDirectory", "lookup_key": "generic_evidence_drafting_workflow"},
        summary="Generic deterministic evidence-drafting workflow template.",
    )
    return records


def _index_memory_pointers(memory_store: Any) -> Dict[str, Dict[str, Any]]:
    records: Dict[str, Dict[str, Any]] = {}
    if memory_store is None:
        return records
    try:
        entries = memory_store.list_all()
    except Exception:
        return records
    for entry in entries:
        memory_id = getattr(entry, "memory_id", None)
        if not memory_id:
            continue
        consent = getattr(entry, "consent", None)
        category = getattr(entry, "category", "")
        entry_id = f"memory:{memory_id}"
        records[entry_id] = _record(
            entry_id=entry_id,
            kind="memory_pointer",
            source_path=None,
            provenance="user_memory",
            dependencies=[],
            availability={
                "known": True,
                "available": consent in ("user_provided", "user_confirmed"),
                "reason": consent,
            },
            pointer={"registry": "MemoryStore", "lookup_key": memory_id},
            summary=f"{category} ({consent})",
        )
    return records


def build_index(
    *,
    capability_directory: Any = None,
    skill_memory: Any = None,
    workflow_planner: Any = None,
    memory_store: Any = None,
) -> GraphifyIndex:
    """Builds a fresh index from real, already-existing authorities.
    Any argument may be omitted - the resulting index simply has no
    records of that kind, never an error. Never raises."""
    records: Dict[str, Dict[str, Any]] = {}
    records.update(_index_capabilities(capability_directory))
    records.update(_index_skills(skill_memory))
    records.update(_index_workflows(workflow_planner))
    records.update(_index_memory_pointers(memory_store))
    return GraphifyIndex(records=records)


def refresh(
    index: GraphifyIndex,
    *,
    capability_directory: Any = None,
    skill_memory: Any = None,
    workflow_planner: Any = None,
    memory_store: Any = None,
    scope: Optional[str] = None,
) -> GraphifyIndex:
    """Incremental refresh. `scope=None` rebuilds every category an
    argument was supplied for. `scope` in {"capabilities", "skills",
    "workflows", "memory"} rebuilds only that one category's records,
    leaving every other record in the index completely untouched -
    the concrete mechanism behind "supports incremental refresh"
    (plan §A.3)."""
    builders = {
        "capabilities": lambda: _index_capabilities(capability_directory),
        "skills": lambda: _index_skills(skill_memory),
        "workflows": lambda: _index_workflows(workflow_planner),
        "memory": lambda: _index_memory_pointers(memory_store),
    }

    scopes = [scope] if scope is not None else list(builders)
    for one_scope in scopes:
        prefix = _SCOPE_PREFIXES[one_scope]
        for key in [k for k in index.records if k.startswith(prefix)]:
            del index.records[key]
        index.records.update(builders[one_scope]())
    return index


def load_index(path: str = DEFAULT_INDEX_PATH) -> GraphifyIndex:
    """Load a persisted index from disk. Missing, unreadable, or
    structurally corrupted -> quarantine (rename aside, never delete,
    mirroring `GraphStore`'s own precedent) and return an empty index -
    never raises, never crashes startup."""
    if not os.path.exists(path):
        return GraphifyIndex()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        records = data.get("records") if isinstance(data, dict) else None
        if not isinstance(records, dict):
            raise ValueError("graphify index file has an unexpected shape")
        return GraphifyIndex(records=records)
    except Exception:
        try:
            shutil.move(path, path + ".corrupted")
        except Exception:
            pass
        return GraphifyIndex()


def save_index(index: GraphifyIndex, path: str = DEFAULT_INDEX_PATH) -> None:
    """Persist the index. A failed save is never fatal - the next
    startup simply rebuilds from scratch, which is always a safe,
    valid state (never authoritative, per module docstring)."""
    try:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(
                {"schema_version": SCHEMA_VERSION, "records": index.records},
                handle,
                indent=2,
                ensure_ascii=False,
            )
    except Exception:
        pass
