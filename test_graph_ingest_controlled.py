"""M23 (plan section 16, row 5): graph_ingest.py's narrow, deterministic
ingestion - a VERIFIED fact produces exactly one node; a
PROVISIONAL/CONFIRMED fact produces none; a pending_confirmation memory
produces none; an eligible memory produces one; re-ingesting the same
fact/memory updates rather than duplicates; no email/Drive/file-content
ingestion path exists to call (this module has no such function at
all - asserted by import inspection)."""

import ast
import os
import tempfile
import unittest

from uri_core.core.facts import Fact
from uri_core.core.graph_ingest import (
    ingest_fact,
    ingest_memory_entry,
    ingest_user_account,
)
from uri_core.core.graph_store import GraphStore
from uri_core.core.user_memory import MemoryEntry


class GraphIngestControlledTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = GraphStore(
            storage_path=os.path.join(self.temp_dir.name, "graph.sqlite3")
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _memory(self, consent, memory_id="m1"):
        return MemoryEntry(
            memory_id=memory_id,
            category="preference",
            consent=consent,
            fact=Fact(name="likes_email_digest", value="true"),
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )

    # -- Facts --------------------------------------------------

    def test_verified_fact_produces_exactly_one_node(self):
        fact = Fact(name="department", value="Engineering", status="VERIFIED")
        node = ingest_fact(self.store, fact, "u1")
        self.assertIsNotNone(node)
        self.assertEqual(len(self.store.list_nodes(entity_type="Fact")), 1)

    def test_provisional_fact_produces_no_node(self):
        fact = Fact(name="department", value="Engineering", status="PROVISIONAL")
        self.assertIsNone(ingest_fact(self.store, fact, "u1"))
        self.assertEqual(self.store.list_nodes(entity_type="Fact"), [])

    def test_confirmed_fact_produces_no_node(self):
        fact = Fact(name="department", value="Engineering", status="CONFIRMED")
        self.assertIsNone(ingest_fact(self.store, fact, "u1"))

    def test_historical_and_superseded_facts_produce_no_node(self):
        for status in ("HISTORICAL", "SUPERSEDED"):
            fact = Fact(name="department", value="Engineering", status=status)
            self.assertIsNone(ingest_fact(self.store, fact, "u1"))

    def test_reingesting_the_same_verified_fact_updates_not_duplicates(self):
        fact = Fact(name="department", value="Engineering", status="VERIFIED")
        first = ingest_fact(self.store, fact, "u1")
        second_fact = Fact(name="department", value="Engineering (updated)", status="VERIFIED")
        second = ingest_fact(self.store, second_fact, "u1")
        self.assertEqual(first.entity_id, second.entity_id)
        self.assertEqual(len(self.store.list_nodes(entity_type="Fact")), 1)

    def test_verified_fact_links_to_the_owning_users_own_user_node(self):
        fact = Fact(name="department", value="Engineering", status="VERIFIED")
        node = ingest_fact(self.store, fact, "u1")
        user_node = self.store.get_node_by_external_ref("User", "u1")
        self.assertIsNotNone(user_node)
        edges = self.store.list_edges(entity_id=node.entity_id)
        self.assertTrue(any(e.relationship_type == "BELONGS_TO" for e in edges))

    # -- Memory --------------------------------------------------

    def test_pending_confirmation_memory_produces_no_node(self):
        entry = self._memory("pending_confirmation")
        self.assertIsNone(ingest_memory_entry(self.store, entry, "u1"))
        self.assertEqual(self.store.list_nodes(entity_type="Memory"), [])

    def test_user_confirmed_memory_produces_one_node(self):
        entry = self._memory("user_confirmed")
        node = ingest_memory_entry(self.store, entry, "u1")
        self.assertIsNotNone(node)
        self.assertEqual(len(self.store.list_nodes(entity_type="Memory")), 1)

    def test_user_provided_memory_produces_one_node(self):
        entry = self._memory("user_provided")
        self.assertIsNotNone(ingest_memory_entry(self.store, entry, "u1"))

    def test_reingesting_the_same_memory_updates_not_duplicates(self):
        entry = self._memory("user_confirmed")
        first = ingest_memory_entry(self.store, entry, "u1")
        second = ingest_memory_entry(self.store, entry, "u1")
        self.assertEqual(first.entity_id, second.entity_id)
        self.assertEqual(len(self.store.list_nodes(entity_type="Memory")), 1)

    # -- User account (lazy, not a bulk sweep) --------------------

    def test_ingest_user_account_creates_one_user_node(self):
        node = ingest_user_account(self.store, "u1", username="alice")
        self.assertIsNotNone(node)
        self.assertEqual(node.canonical_name, "alice")

    def test_ingest_user_account_with_no_user_id_returns_none(self):
        self.assertIsNone(ingest_user_account(self.store, ""))

    # -- No bulk/external ingestion surface exists -----------------

    def test_module_defines_no_email_or_drive_or_file_content_ingestion_function(self):
        module_path = os.path.join("uri_core", "core", "graph_ingest.py")
        with open(module_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=module_path)

        function_names = {
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        }
        forbidden_markers = ("email", "gmail", "drive", "attachment", "file_content", "bulk")
        offending = {
            name for name in function_names
            if any(marker in name.lower() for marker in forbidden_markers)
        }
        self.assertEqual(
            offending, set(),
            "graph_ingest.py must not define any email/Drive/file-content/bulk "
            "ingestion function in Phase 1 (plan section 3/9).",
        )


if __name__ == "__main__":
    unittest.main()
