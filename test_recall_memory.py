"""RecallMemoryTool (2026-09-12): answers from already-consented
memory only, never writes, never fabricates."""

import os
import tempfile
import unittest

from uri_core.core.user_memory import MemoryStore
from uri_core.tools.recall_memory import RecallMemoryTool


class RecallMemoryToolTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.storage_path = os.path.join(self.temp_dir.name, "user_memory.json")
        self.memory_store = MemoryStore(storage_path=self.storage_path)
        self.tool = RecallMemoryTool(memory_store=self.memory_store)

    def test_no_entries_is_honest_not_fabricated(self):
        result = self.tool.recall(principal=None)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["entries"], [])

    def test_confirmed_entry_is_returned(self):
        self.memory_store.add(category="other", content="My name is Chetan")

        result = self.tool.recall(principal=None)

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["entries"]), 1)
        self.assertEqual(result["entries"][0]["content"], "My name is Chetan")

    def test_pending_confirmation_entry_is_never_surfaced(self):
        self.memory_store.propose(category="other", content="URI guessed this")

        result = self.tool.recall(principal=None)

        self.assertEqual(result["entries"], [])


if __name__ == "__main__":
    unittest.main()
