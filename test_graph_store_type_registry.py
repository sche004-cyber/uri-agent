"""M23 (plan section 16, row 2): the extensible entity/relationship
type registry - packaged types accepted, a newly-registered type
accepted, malformed/credential-shaped values rejected regardless of
familiarity."""

import os
import tempfile
import unittest

from uri_core.config.graph_schema import (
    GraphTypeRegistry,
    GraphTypeValidationError,
    PACKAGED_ENTITY_TYPES,
    PACKAGED_RELATIONSHIP_TYPES,
    is_valid_entity_type,
    is_valid_relationship_type,
)
from uri_core.core.graph_store import GraphStore


class GraphTypeRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.registry = GraphTypeRegistry(
            storage_path=os.path.join(self.temp_dir.name, "types.json")
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_packaged_types_are_valid(self):
        for entity_type in PACKAGED_ENTITY_TYPES:
            self.assertTrue(is_valid_entity_type(entity_type))
        for rel_type in PACKAGED_RELATIONSHIP_TYPES:
            self.assertTrue(is_valid_relationship_type(rel_type))

    def test_a_new_well_formed_type_is_accepted_not_rejected_for_unfamiliarity(self):
        self.assertTrue(is_valid_entity_type("Vendor"))
        self.assertTrue(is_valid_relationship_type("SUPPLIES"))

    def test_register_entity_type_persists_and_is_idempotent(self):
        self.registry.register_entity_type("Vendor")
        self.registry.register_entity_type("Vendor")
        self.assertIn("Vendor", self.registry.known_entity_types())

        reopened = GraphTypeRegistry(storage_path=self.registry.storage_path)
        self.assertIn("Vendor", reopened.known_entity_types())

    def test_register_rejects_empty_type_name(self):
        with self.assertRaises(GraphTypeValidationError):
            self.registry.register_entity_type("")

    def test_register_rejects_credential_shaped_type_name(self):
        with self.assertRaises(GraphTypeValidationError):
            self.registry.register_entity_type("sk-abcdefghijklmnopqrstuvwxyz1234567890")

    def test_empty_and_non_string_and_credential_shaped_values_rejected(self):
        self.assertFalse(is_valid_entity_type(""))
        self.assertFalse(is_valid_entity_type(None))
        self.assertFalse(is_valid_entity_type(123))
        self.assertFalse(is_valid_entity_type("sk-abcdefghijklmnopqrstuvwxyz1234567890"))

    def test_graph_store_upsert_auto_registers_a_new_type(self):
        store = GraphStore(
            storage_path=os.path.join(self.temp_dir.name, "graph.sqlite3"),
            type_registry=self.registry,
        )
        store.upsert_node("Vendor", "Acme Supplies", user_id="u1")
        self.assertIn("Vendor", self.registry.known_entity_types())


if __name__ == "__main__":
    unittest.main()
