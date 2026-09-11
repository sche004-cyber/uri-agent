"""M23 (plan section 16, row 4): two users' GraphStores are provably
separate files with no cross-read path - same shape as M21's existing
per-user isolation suite (test_m21_file_store_isolation.py)."""

import os
import tempfile
import unittest
import uuid

from uri_core.app import server


class GraphIsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self._original_user_state_root = server._USER_STATE_ROOT
        self._original_user_contexts = server._user_contexts
        server._USER_STATE_ROOT = os.path.join(self.temp_dir.name, "users")
        server._user_contexts = {}

    def tearDown(self):
        server._USER_STATE_ROOT = self._original_user_state_root
        server._user_contexts = self._original_user_contexts
        self.temp_dir.cleanup()

    def test_two_users_get_physically_separate_graph_files(self):
        alice_id = str(uuid.uuid4())
        bob_id = str(uuid.uuid4())

        alice_context = server._build_user_context(alice_id)
        bob_context = server._build_user_context(bob_id)

        self.assertNotEqual(
            alice_context.graph_store.storage_path,
            bob_context.graph_store.storage_path,
        )
        self.assertIn(alice_id, alice_context.graph_store.storage_path)
        self.assertIn(bob_id, bob_context.graph_store.storage_path)

    def test_a_node_written_to_one_users_graph_is_invisible_to_the_other(self):
        alice_id = str(uuid.uuid4())
        bob_id = str(uuid.uuid4())

        alice_context = server._get_user_context(alice_id)
        bob_context = server._get_user_context(bob_id)

        alice_node = alice_context.graph_store.upsert_node(
            "Person", "Alice's Secret Contact", user_id=alice_id
        )

        self.assertIsNotNone(alice_context.graph_store.get_node(alice_node.entity_id))
        self.assertIsNone(bob_context.graph_store.get_node(alice_node.entity_id))
        self.assertEqual(bob_context.graph_store.list_nodes(), [])

    def test_get_user_context_caches_the_same_graph_store_across_calls(self):
        user_id = str(uuid.uuid4())
        first = server._get_user_context(user_id)
        second = server._get_user_context(user_id)
        self.assertIs(first.graph_store, second.graph_store)

    def test_legacy_ambient_context_uses_the_shared_global_graph_store(self):
        context = server._resolve_context(None)
        self.assertIs(context.graph_store, server._graph_store)


if __name__ == "__main__":
    unittest.main()
