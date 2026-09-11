"""M23 (plan section 16, row 7): build_graph_context() degrades to the
all-empty shape (mirroring query_context.py's own degrade guarantee),
and query_context.build_query_context()'s new graph_context key is
additive-only - every pre-existing key's value is unchanged when
graph_context is supplied."""

import unittest

from uri_core.core.graph_context import build_graph_context
from uri_core.core.query_context import build_query_context


class GraphContextBoundaryTests(unittest.TestCase):
    def test_build_graph_context_degrades_to_all_empty_shape_on_no_input(self):
        self.assertEqual(
            build_graph_context(),
            {
                "entities": [],
                "relationships": [],
                "paths": [],
                "provenance": [],
                "confidence_status": [],
            },
        )

    def test_build_graph_context_passes_through_supplied_values(self):
        result = build_graph_context(
            entities=[{"entity_id": "e1"}],
            relationships=[{"edge_id": "r1"}],
            paths=[{"path": []}],
            provenance=[{"source_type": "fact"}],
            confidence_status=[{"confidence": 0.9, "status": "ACTIVE"}],
        )
        self.assertEqual(result["entities"], [{"entity_id": "e1"}])
        self.assertEqual(result["relationships"], [{"edge_id": "r1"}])
        self.assertEqual(result["provenance"], [{"source_type": "fact"}])

    def test_query_context_without_graph_context_degrades_to_all_empty_shape(self):
        result = build_query_context()
        self.assertEqual(
            result["graph_context"],
            {
                "entities": [],
                "relationships": [],
                "paths": [],
                "provenance": [],
                "confidence_status": [],
            },
        )

    def test_query_context_graph_context_is_additive_only(self):
        without_graph = build_query_context(
            policy_text="policy", soul_text="soul", personalization={"a": 1}
        )
        with_graph = build_query_context(
            policy_text="policy",
            soul_text="soul",
            personalization={"a": 1},
            graph_context=build_graph_context(entities=[{"entity_id": "e1"}]),
        )

        for key in without_graph:
            if key == "graph_context":
                continue
            self.assertEqual(
                without_graph[key], with_graph[key],
                f"supplying graph_context must not change the '{key}' section",
            )

        self.assertEqual(with_graph["graph_context"]["entities"], [{"entity_id": "e1"}])


if __name__ == "__main__":
    unittest.main()
