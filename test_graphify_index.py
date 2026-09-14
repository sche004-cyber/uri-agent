"""Graphify Foundation (docs/plans/M30_GRAPHIFY_FOUNDATION_PLAN.md):
a system-level, read-only capability/skill/workflow/memory-pointer
index, built from real, already-existing authorities, never a second
source of truth, never authority-bearing."""

import ast
import json
import os
import tempfile
import unittest

from uri_core.core.graphify_index import (
    DEFAULT_INDEX_PATH,
    GraphifyIndex,
    build_index,
    load_index,
    refresh,
    save_index,
)


class _FakeCapabilityDirectory:
    def __init__(self, entries):
        self._entries = entries  # {capability_id: {available, availability_known, availability_reason, summary, actions}}

    def summaries(self):
        return [
            {"capability_id": cid, "summary": entry.get("summary", "")}
            for cid, entry in self._entries.items()
        ]

    def describe(self, capability_id):
        entry = self._entries.get(capability_id)
        if entry is None:
            return None
        return {
            "capability_id": capability_id,
            "available": entry.get("available"),
            "availability_known": entry.get("availability_known"),
            "availability_reason": entry.get("availability_reason"),
            "actions": entry.get("actions", []),
            "execution_reference": entry.get("execution_reference"),
        }


class _FakeSkillMemory:
    def __init__(self, skills):
        self._skills = skills

    def list_skills(self):
        return self._skills


class _FakeMemoryEntry:
    def __init__(self, memory_id, category, consent):
        self.memory_id = memory_id
        self.category = category
        self.consent = consent


class _FakeMemoryStore:
    def __init__(self, entries):
        self._entries = entries

    def list_all(self):
        return self._entries


class IndexBuildTests(unittest.TestCase):
    def test_capabilities_skills_workflows_memory_each_produce_expected_records(self):
        directory = _FakeCapabilityDirectory({
            "Gmail": {
                "available": True, "availability_known": True, "availability_reason": None,
                "summary": "Search Gmail.", "actions": ["search_messages"],
            },
        })
        skill_memory = _FakeSkillMemory([
            {"tool_name": "remember_fact", "task_type": "disclosure", "domain": "profile"},
        ])
        memory_store = _FakeMemoryStore([
            _FakeMemoryEntry("m1", "explicit_statement", "user_provided"),
        ])

        index = build_index(
            capability_directory=directory,
            skill_memory=skill_memory,
            workflow_planner=object(),
            memory_store=memory_store,
        )

        self.assertIn("capability:Gmail", index.records)
        self.assertEqual(index.records["capability:Gmail"]["kind"], "capability")
        self.assertEqual(
            index.records["capability:Gmail"]["pointer"],
            {"registry": "CapabilityDirectory", "lookup_key": "Gmail"},
        )

        self.assertIn("skill:remember_fact:disclosure:profile", index.records)
        self.assertEqual(index.records["skill:remember_fact:disclosure:profile"]["kind"], "skill")

        self.assertIn("workflow:generic_evidence_drafting_workflow", index.records)
        self.assertEqual(
            index.records["workflow:generic_evidence_drafting_workflow"]["kind"], "workflow",
        )

        self.assertIn("memory:m1", index.records)
        self.assertEqual(index.records["memory:m1"]["kind"], "memory_pointer")
        self.assertTrue(index.records["memory:m1"]["availability"]["available"])

    def test_no_collaborators_produces_an_empty_but_valid_index(self):
        index = build_index()
        self.assertEqual(index.records, {})
        self.assertEqual(index.list_all(), [])

    def test_a_failing_collaborator_degrades_to_a_partial_index_never_raises(self):
        class _Explodes:
            def summaries(self):
                raise RuntimeError("boom")

        index = build_index(capability_directory=_Explodes())
        self.assertEqual(index.records, {})


class AvailabilityRefreshTests(unittest.TestCase):
    def test_refresh_reflects_a_real_availability_change_not_a_stale_copy(self):
        directory = _FakeCapabilityDirectory({
            "Gmail": {"available": False, "availability_known": True, "availability_reason": "unavailable_runtime"},
        })
        index = build_index(capability_directory=directory)
        self.assertFalse(index.records["capability:Gmail"]["availability"]["available"])

        directory._entries["Gmail"]["available"] = True
        directory._entries["Gmail"]["availability_reason"] = None
        refresh(index, capability_directory=directory, scope="capabilities")

        self.assertTrue(index.records["capability:Gmail"]["availability"]["available"])


class IncrementalRefreshTests(unittest.TestCase):
    def test_refreshing_one_scope_leaves_other_scopes_untouched(self):
        directory = _FakeCapabilityDirectory({
            "Gmail": {"available": True, "availability_known": True, "availability_reason": None},
        })
        skill_memory = _FakeSkillMemory([
            {"tool_name": "remember_fact", "task_type": "t", "domain": "d"},
        ])
        index = build_index(capability_directory=directory, skill_memory=skill_memory)
        skill_key = "skill:remember_fact:t:d"
        original_skill_record = index.records[skill_key]

        directory._entries["Gmail"]["available"] = False
        refresh(index, capability_directory=directory, scope="capabilities")

        self.assertFalse(index.records["capability:Gmail"]["availability"]["available"])
        self.assertEqual(index.records[skill_key], original_skill_record)


class PersistenceTests(unittest.TestCase):
    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "graphify_index.json")
            directory = _FakeCapabilityDirectory({
                "Gmail": {"available": True, "availability_known": True, "availability_reason": None},
            })
            built = build_index(capability_directory=directory)
            save_index(built, path)

            loaded = load_index(path)
            self.assertEqual(loaded.records, built.records)

    def test_missing_file_loads_to_an_empty_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "does_not_exist.json")
            self.assertEqual(load_index(path).records, {})

    def test_corrupted_file_is_quarantined_not_deleted_and_loads_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "graphify_index.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{not-valid-json")

            index = load_index(path)

            self.assertEqual(index.records, {})
            self.assertFalse(os.path.exists(path))
            self.assertTrue(os.path.exists(path + ".corrupted"))

    def test_structurally_wrong_shape_is_quarantined_not_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "graphify_index.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"records": "not-a-dict"}, handle)

            index = load_index(path)

            self.assertEqual(index.records, {})
            self.assertTrue(os.path.exists(path + ".corrupted"))

    def test_a_failed_save_never_raises(self):
        # An unwritable path (a directory component that cannot be
        # created) must degrade silently - the next startup simply
        # rebuilds from scratch, which is always a safe state.
        save_index(GraphifyIndex(), path="\0invalid\0path")  # must not raise


class RelevantSubsetTests(unittest.TestCase):
    def test_relevant_subset_is_small_and_filtered_not_the_whole_index(self):
        directory = _FakeCapabilityDirectory({
            "Gmail": {
                "available": True, "availability_known": True, "availability_reason": None,
                "summary": "Search and inspect Gmail messages and attachments.",
            },
            "Unrelated": {
                "available": True, "availability_known": True, "availability_reason": None,
                "summary": "Convert a document to a different file format.",
            },
        })
        index = build_index(capability_directory=directory)

        subset = index.relevant_subset("Search my Gmail messages for an attachment.")

        ids = {record["id"] for record in subset}
        self.assertIn("capability:Gmail", ids)
        self.assertNotIn("capability:Unrelated", ids)
        self.assertLess(len(subset), len(index.list_all()) + 1)


class DefaultIndexPathTests(unittest.TestCase):
    def test_default_index_path_is_under_the_workspace_directory(self):
        self.assertTrue(DEFAULT_INDEX_PATH.startswith("uri_workspace"))


def _imported_module_names(file_path: str) -> set:
    with open(file_path, "r", encoding="utf-8-sig") as file:
        tree = ast.parse(file.read(), filename=file_path)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


class GraphifyAuthorityBoundaryTests(unittest.TestCase):
    """Mirrors test_graph_authority_boundary.py's own AST-based proof
    exactly, applied to the new graphify_index.py module."""

    _FORBIDDEN = {
        "model_providers", "model_router", "dispatcher", "approval_gate",
        "approval_store", "decision_gates", "decision_engine", "canonical_execution",
    }
    _AUTHORITY_FILES = (
        "dispatcher.py", "approval_gate.py", "approval_store.py",
        "capability_registry.py", "capability_resolver.py",
        "decision_gates.py", "canonical_execution.py",
    )
    _CORE = os.path.join("uri_core", "core")

    def test_graphify_index_never_imports_authority_bearing_modules(self):
        imports = _imported_module_names(os.path.join(self._CORE, "graphify_index.py"))
        offending = {name for name in imports if any(f in name for f in self._FORBIDDEN)}
        self.assertEqual(offending, set())

    def test_authority_modules_never_import_graphify_index(self):
        for authority_file in self._AUTHORITY_FILES:
            path = os.path.join(self._CORE, authority_file)
            if not os.path.isfile(path):
                continue
            imports = _imported_module_names(path)
            offending = {name for name in imports if "graphify_index" in name}
            self.assertEqual(
                offending, set(),
                f"{authority_file} must never import graphify_index.py - "
                "the index must never become an authorization input.",
            )

    def test_graphify_index_module_actually_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(self._CORE, "graphify_index.py")))


if __name__ == "__main__":
    unittest.main()
