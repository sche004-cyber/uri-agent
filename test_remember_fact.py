"""RememberFactTool (2026-09-12): only ever writes with
consent='user_provided' (an explicit save request), never auto-
captures, never silently does nothing for a real "add this to my
profile" request."""

import os
import tempfile
import unittest

from uri_core.core.user_memory import MemoryStore
from uri_core.tools.remember_fact import RememberFactTool


class RememberFactToolTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.memory_store = MemoryStore(
            storage_path=os.path.join(self.temp_dir.name, "user_memory.json")
        )
        self.tool = RememberFactTool(memory_store=self.memory_store)

    def test_explicit_add_to_profile_request_is_saved(self):
        result = self.tool.remember(
            principal=None,
            request_text="my work place is NIT Sikkim so add this to my profile",
        )

        self.assertEqual(result["status"], "success")
        entries = self.memory_store.list_all()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].consent, "user_provided")
        self.assertIn("NIT Sikkim", entries[0].fact.value)
        # The trigger phrase itself is stripped, not stored verbatim.
        self.assertNotIn("add this to my profile", entries[0].fact.value)

    def test_bare_trigger_with_no_real_content_asks_for_the_fact(self):
        result = self.tool.remember(
            principal=None, request_text="can you save it to my profile?"
        )

        self.assertEqual(result["status"], "input_required")
        self.assertEqual(self.memory_store.list_all(), [])

    def test_no_request_text_asks_rather_than_guessing(self):
        result = self.tool.remember(principal=None, request_text="")
        self.assertEqual(result["status"], "input_required")

    def test_remember_that_phrasing_also_works(self):
        result = self.tool.remember(
            principal=None,
            request_text="remember that my favourite format is docx",
        )

        self.assertEqual(result["status"], "success")
        entries = self.memory_store.list_all()
        self.assertIn("favourite format is docx", entries[0].fact.value)


if __name__ == "__main__":
    unittest.main()
