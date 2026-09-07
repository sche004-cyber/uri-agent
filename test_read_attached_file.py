"""M16 Priority 1: the read_attached_file capability. Reads only what
the user actually attached to THIS session, and reports every real
outcome honestly. See uri_core/tools/read_attached_file.py.
"""

import os
import tempfile
import unittest

from uri_core.core.file_store import FileStore
from uri_core.tools.read_attached_file import ReadAttachedFileTool


class ReadAttachedFileToolTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.store = FileStore(
            storage_dir=os.path.join(self.temp_dir.name, "uploads")
        )
        self.tool = ReadAttachedFileTool(file_store=self.store)

    def test_no_session_asks_rather_than_guessing(self):
        result = self.tool.execute()

        self.assertEqual(result["status"], "input_required")

    def test_no_attachment_is_reported_not_invented(self):
        result = self.tool.execute(session_id="s1")

        self.assertEqual(result["status"], "not_found")
        self.assertIn("No file has been attached", result["message"])

    def test_attached_text_file_is_read(self):
        self.store.save(
            filename="minutes.txt",
            content=b"Minutes of the hostel maintenance meeting.",
            session_id="s1",
        )

        result = self.tool.execute(session_id="s1")

        self.assertEqual(result["status"], "success")
        document = result["documents"][0]
        self.assertEqual(document["filename"], "minutes.txt")
        self.assertIn("hostel maintenance", document["text"])

    def test_only_this_sessions_files_are_ever_read(self):
        self.store.save(
            filename="other.txt",
            content=b"Another conversation's private file.",
            session_id="other-session",
        )

        result = self.tool.execute(session_id="s1")

        self.assertEqual(result["status"], "not_found")

    def test_unsupported_attachment_is_reported_not_faked(self):
        # .docx is storable; with python-docx absent the extractor
        # fails honestly rather than inventing content.
        self.store.save(
            filename="scan.png",
            content=b"not really an image",
            session_id="s1",
        )

        result = self.tool.execute(session_id="s1")

        self.assertEqual(result["status"], "unreadable")
        self.assertIn("could not read", result["message"])
        self.assertNotIn("text", result["documents"][0])

    def test_most_recent_attachments_come_first(self):
        self.store.save(
            filename="first.txt", content=b"first", session_id="s1"
        )
        self.store.save(
            filename="second.txt", content=b"second", session_id="s1"
        )

        result = self.tool.execute(session_id="s1")

        self.assertEqual(
            result["documents"][0]["filename"], "second.txt"
        )

    def test_a_deleted_file_is_reported_as_unavailable(self):
        record = self.store.save(
            filename="gone.txt", content=b"data", session_id="s1"
        )
        os.remove(self.store.path_for(record.file_id))

        result = self.tool.execute(session_id="s1")

        self.assertEqual(result["status"], "unreadable")
        self.assertIn(
            "no longer available", result["documents"][0]["error"]
        )


if __name__ == "__main__":
    unittest.main()
