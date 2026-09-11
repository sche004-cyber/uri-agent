"""M23 (plan section 16, row 1): GraphStore CRUD, dedup, provenance,
and status filtering - no FastAPI/HTTP involved, a plain
tempfile-backed SQLite store per test, mirroring every other store's
own isolated-tempdir test discipline."""

import os
import tempfile
import unittest

from uri_core.core.graph_store import GraphStore, GraphValidationError


class GraphStoreCrudTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = GraphStore(
            storage_path=os.path.join(self.temp_dir.name, "graph.sqlite3")
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_upsert_and_get_node_round_trips_every_field(self):
        node = self.store.upsert_node(
            entity_type="Person",
            canonical_name="Alice",
            attributes={"role": "advisor"},
            external_ref="person-1",
            provenance={"source_type": "manual", "recorded_by": "system"},
            user_id="u1",
        )
        fetched = self.store.get_node(node.entity_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.entity_type, "Person")
        self.assertEqual(fetched.canonical_name, "Alice")
        self.assertEqual(fetched.attributes, {"role": "advisor"})
        self.assertEqual(fetched.provenance["source_type"], "manual")
        self.assertEqual(fetched.external_ref, "person-1")

    def test_get_node_returns_none_for_unknown_id(self):
        self.assertIsNone(self.store.get_node("does-not-exist"))

    def test_dedup_by_external_ref_updates_rather_than_duplicates(self):
        first = self.store.upsert_node(
            "Person", "Alice", external_ref="person-1", user_id="u1"
        )
        second = self.store.upsert_node(
            "Person", "Alice Updated", external_ref="person-1", user_id="u1"
        )
        self.assertEqual(first.entity_id, second.entity_id)
        self.assertEqual(len(self.store.list_nodes(entity_type="Person")), 1)
        self.assertEqual(self.store.get_node(first.entity_id).canonical_name, "Alice Updated")

    def test_dedup_by_derived_id_when_no_external_ref(self):
        first = self.store.upsert_node("Person", "Bob", user_id="u1")
        second = self.store.upsert_node("Person", "Bob", user_id="u1")
        self.assertEqual(first.entity_id, second.entity_id)
        self.assertEqual(len(self.store.list_nodes(entity_type="Person")), 1)

    def test_different_users_same_name_derive_different_ids(self):
        a = self.store.upsert_node("Person", "Bob", user_id="u1")
        b = self.store.upsert_node("Person", "Bob", user_id="u2")
        self.assertNotEqual(a.entity_id, b.entity_id)

    def test_upsert_node_rejects_empty_canonical_name(self):
        with self.assertRaises(GraphValidationError):
            self.store.upsert_node("Person", "", user_id="u1")

    def test_upsert_node_rejects_credential_shaped_attribute(self):
        with self.assertRaises(GraphValidationError):
            self.store.upsert_node(
                "Person",
                "Alice",
                attributes={"note": "sk-abcdefghijklmnopqrstuvwxyz1234567890"},
                user_id="u1",
            )

    def test_delete_node_cascades_to_incident_edges(self):
        a = self.store.upsert_node("Person", "Alice", user_id="u1")
        b = self.store.upsert_node("Organization", "Acme", user_id="u1")
        edge = self.store.upsert_edge(a.entity_id, b.entity_id, "BELONGS_TO")

        self.assertTrue(self.store.delete_node(a.entity_id))
        self.assertIsNone(self.store.get_node(a.entity_id))
        self.assertIsNone(self.store.get_edge(edge.edge_id))

    def test_upsert_edge_requires_both_endpoints_to_exist(self):
        a = self.store.upsert_node("Person", "Alice", user_id="u1")
        with self.assertRaises(GraphValidationError):
            self.store.upsert_edge(a.entity_id, "missing-node", "BELONGS_TO")

    def test_edge_dedup_by_source_target_relationship_updates_rather_than_duplicates(self):
        a = self.store.upsert_node("Person", "Alice", user_id="u1")
        b = self.store.upsert_node("Organization", "Acme", user_id="u1")
        first = self.store.upsert_edge(a.entity_id, b.entity_id, "BELONGS_TO", confidence=0.5)
        second = self.store.upsert_edge(a.entity_id, b.entity_id, "BELONGS_TO", confidence=0.9)
        self.assertEqual(first.edge_id, second.edge_id)
        self.assertEqual(self.store.get_edge(first.edge_id).confidence, 0.9)
        self.assertEqual(len(self.store.list_edges(entity_id=a.entity_id)), 1)

    def test_edge_confidence_out_of_range_rejected(self):
        a = self.store.upsert_node("Person", "Alice", user_id="u1")
        b = self.store.upsert_node("Organization", "Acme", user_id="u1")
        with self.assertRaises(GraphValidationError):
            self.store.upsert_edge(a.entity_id, b.entity_id, "BELONGS_TO", confidence=1.5)

    def test_set_edge_status_changes_status_and_default_listing_excludes_it(self):
        a = self.store.upsert_node("Person", "Alice", user_id="u1")
        b = self.store.upsert_node("Organization", "Acme", user_id="u1")
        edge = self.store.upsert_edge(a.entity_id, b.entity_id, "BELONGS_TO")

        self.assertTrue(self.store.set_edge_status(edge.edge_id, "SUPERSEDED"))
        self.assertEqual(self.store.get_edge(edge.edge_id).status, "SUPERSEDED")
        self.assertEqual(self.store.list_edges(entity_id=a.entity_id, status="ACTIVE"), [])
        self.assertEqual(len(self.store.list_edges(entity_id=a.entity_id, status="SUPERSEDED")), 1)

    def test_set_edge_status_rejects_unknown_status(self):
        a = self.store.upsert_node("Person", "Alice", user_id="u1")
        b = self.store.upsert_node("Organization", "Acme", user_id="u1")
        edge = self.store.upsert_edge(a.entity_id, b.entity_id, "BELONGS_TO")
        with self.assertRaises(GraphValidationError):
            self.store.set_edge_status(edge.edge_id, "NOT_A_REAL_STATUS")

    def test_get_node_by_external_ref(self):
        node = self.store.upsert_node("User", "alice", external_ref="u1", user_id="u1")
        found = self.store.get_node_by_external_ref("User", "u1")
        self.assertIsNotNone(found)
        self.assertEqual(found.entity_id, node.entity_id)
        self.assertIsNone(self.store.get_node_by_external_ref("User", "unknown"))

    def test_corrupted_db_file_degrades_safely_rather_than_raising(self):
        path = os.path.join(self.temp_dir.name, "corrupted.sqlite3")
        with open(path, "wb") as f:
            f.write(b"this is not a valid sqlite file, deliberately")

        store = GraphStore(storage_path=path)
        # Must not raise, and the store must be immediately usable.
        node = store.upsert_node("Person", "Alice", user_id="u1")
        self.assertIsNotNone(store.get_node(node.entity_id))
        # The original corrupted bytes are quarantined, not deleted.
        quarantined = [f for f in os.listdir(self.temp_dir.name) if "corrupted.sqlite3.corrupted." in f]
        self.assertEqual(len(quarantined), 1)


if __name__ == "__main__":
    unittest.main()
