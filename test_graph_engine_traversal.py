"""M23 (plan section 16, row 3): graph_engine.py's six bounded
read/traversal primitives, correctness on a small fixture graph, and
the bounds (max_hops/limit) holding even when a caller asks for more
than the ceiling."""

import os
import tempfile
import unittest

from uri_core.core.graph_engine import (
    MAX_HOPS_CEILING,
    graph_explain,
    graph_get_entity,
    graph_impact,
    graph_neighbors,
    graph_path,
    graph_query,
)
from uri_core.core.graph_store import GraphStore


class GraphEngineTraversalTests(unittest.TestCase):
    """Fixture: Alice -BELONGS_TO-> Acme -DEPENDS_ON-> Eng -DEPENDS_ON->
    Payroll (a simple chain, plus one HISTORICAL edge to prove the
    default ACTIVE-only filtering)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = GraphStore(
            storage_path=os.path.join(self.temp_dir.name, "graph.sqlite3")
        )
        self.alice = self.store.upsert_node("Person", "Alice", user_id="u1")
        self.acme = self.store.upsert_node("Organization", "Acme", user_id="u1")
        self.eng = self.store.upsert_node("Department", "Eng", user_id="u1")
        self.payroll = self.store.upsert_node("Department", "Payroll", user_id="u1")
        self.unlinked = self.store.upsert_node("Person", "Stranger", user_id="u1")

        self.e1 = self.store.upsert_edge(
            self.alice.entity_id, self.acme.entity_id, "BELONGS_TO",
            provenance={"source_type": "manual"},
        )
        self.e2 = self.store.upsert_edge(
            self.acme.entity_id, self.eng.entity_id, "DEPENDS_ON", confidence=0.9,
        )
        self.e3 = self.store.upsert_edge(
            self.eng.entity_id, self.payroll.entity_id, "DEPENDS_ON", confidence=0.7,
        )
        self.historical = self.store.upsert_edge(
            self.alice.entity_id, self.payroll.entity_id, "RELATED_TO",
        )
        self.store.set_edge_status(self.historical.edge_id, "HISTORICAL")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_graph_get_entity_returns_entity_and_active_edges(self):
        result = graph_get_entity(self.store, self.alice.entity_id)
        self.assertEqual(result["entity"]["entity_id"], self.alice.entity_id)
        self.assertEqual(len(result["edges"]), 1)  # BELONGS_TO only - HISTORICAL excluded

    def test_graph_get_entity_returns_none_for_unknown_id(self):
        self.assertIsNone(graph_get_entity(self.store, "unknown"))

    def test_graph_query_filters_by_type(self):
        people = graph_query(self.store, entity_type="Person")
        self.assertEqual(len(people), 2)

    def test_graph_query_filters_by_name_contains(self):
        found = graph_query(self.store, name_contains="ali")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["canonical_name"], "Alice")

    def test_graph_neighbors_returns_entity_and_edge_pairs(self):
        neighbors = graph_neighbors(self.store, self.acme.entity_id)
        neighbor_ids = {n["entity"]["entity_id"] for n in neighbors}
        self.assertIn(self.alice.entity_id, neighbor_ids)
        self.assertIn(self.eng.entity_id, neighbor_ids)

    def test_graph_neighbors_default_excludes_historical(self):
        neighbors = graph_neighbors(self.store, self.alice.entity_id)
        neighbor_ids = {n["entity"]["entity_id"] for n in neighbors}
        self.assertNotIn(self.payroll.entity_id, neighbor_ids)

    def test_graph_neighbors_include_historical_when_asked(self):
        neighbors = graph_neighbors(self.store, self.alice.entity_id, status="HISTORICAL")
        neighbor_ids = {n["entity"]["entity_id"] for n in neighbors}
        self.assertIn(self.payroll.entity_id, neighbor_ids)

    def test_graph_neighbors_filters_by_relationship_type(self):
        neighbors = graph_neighbors(
            self.store, self.acme.entity_id, relationship_types=["DEPENDS_ON"]
        )
        self.assertEqual(len(neighbors), 1)
        self.assertEqual(neighbors[0]["entity"]["entity_id"], self.eng.entity_id)

    def test_graph_path_finds_shortest_multi_hop_path(self):
        path = graph_path(self.store, self.alice.entity_id, self.payroll.entity_id, max_hops=4)
        self.assertIsNotNone(path)
        self.assertEqual(len(path), 4)  # alice, acme, eng, payroll
        self.assertEqual(path[0]["entity"]["entity_id"], self.alice.entity_id)
        self.assertEqual(path[-1]["entity"]["entity_id"], self.payroll.entity_id)

    def test_graph_path_returns_none_when_no_path_within_bound(self):
        path = graph_path(self.store, self.alice.entity_id, self.unlinked.entity_id, max_hops=4)
        self.assertIsNone(path)

    def test_graph_path_returns_none_not_exception_for_unknown_entity(self):
        self.assertIsNone(graph_path(self.store, self.alice.entity_id, "unknown", max_hops=4))

    def test_graph_path_max_hops_is_clamped_to_ceiling_regardless_of_caller_input(self):
        # A caller-supplied max_hops far beyond the ceiling must not be
        # honored literally - the search still completes bounded by
        # MAX_HOPS_CEILING.
        path = graph_path(
            self.store, self.alice.entity_id, self.payroll.entity_id, max_hops=999999
        )
        self.assertIsNotNone(path)
        self.assertLessEqual(len(path) - 1, MAX_HOPS_CEILING)

    def test_graph_explain_returns_path_provenance_and_confidence_status(self):
        explanation = graph_explain(self.store, self.alice.entity_id, self.eng.entity_id, max_hops=4)
        self.assertIsNotNone(explanation["path"])
        self.assertEqual(len(explanation["provenance"]), 2)
        self.assertEqual(len(explanation["confidence_status"]), 2)
        self.assertEqual(explanation["confidence_status"][-1]["status"], "ACTIVE")

    def test_graph_explain_no_path_degrades_to_empty_not_exception(self):
        explanation = graph_explain(self.store, self.alice.entity_id, self.unlinked.entity_id, max_hops=4)
        self.assertIsNone(explanation["path"])
        self.assertEqual(explanation["provenance"], [])
        self.assertEqual(explanation["confidence_status"], [])

    def test_graph_impact_bounded_reverse_traversal(self):
        # Who/what would be impacted if Payroll changed - Eng and Acme
        # both DEPENDS_ON-chain to it.
        impact = graph_impact(
            self.store, self.payroll.entity_id,
            relationship_types=["DEPENDS_ON"], direction="incoming", max_hops=3,
        )
        impacted_ids = {i["entity"]["entity_id"] for i in impact}
        self.assertIn(self.eng.entity_id, impacted_ids)
        self.assertIn(self.acme.entity_id, impacted_ids)
        self.assertNotIn(self.alice.entity_id, impacted_ids)  # BELONGS_TO, not DEPENDS_ON

    def test_graph_impact_respects_max_hops_bound(self):
        impact = graph_impact(
            self.store, self.payroll.entity_id,
            relationship_types=["DEPENDS_ON"], direction="incoming", max_hops=1,
        )
        impacted_ids = {i["entity"]["entity_id"] for i in impact}
        self.assertIn(self.eng.entity_id, impacted_ids)
        self.assertNotIn(self.acme.entity_id, impacted_ids)  # 2 hops away

    def test_graph_impact_unknown_entity_returns_empty_list(self):
        self.assertEqual(graph_impact(self.store, "unknown"), [])


if __name__ == "__main__":
    unittest.main()
