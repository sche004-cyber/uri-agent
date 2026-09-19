"""M16 Priority 1: the read_attached_file capability. Reads only what
the user actually attached to THIS session, and reports every real
outcome honestly. See uri_core/tools/read_attached_file.py.
"""

import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

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


class ReadAttachedFileExplicitContextTests(unittest.TestCase):
    """No filesystem fixture: prove explicit turn identity outranks history."""

    def _tool(self, records, session_records):
        class _Store:
            def get(self, file_id):
                return records.get(file_id)

            def list_for_session(self, session_id):
                return session_records.get(session_id, [])

            def path_for(self, file_id):
                return file_id

        return ReadAttachedFileTool(file_store=_Store())

    @staticmethod
    def _record(file_id, filename, session_id="s1"):
        return SimpleNamespace(
            file_id=file_id, filename=filename, media_type="text/plain",
            size_bytes=1, session_id=session_id,
        )

    def test_explicit_current_turn_file_excludes_older_session_file(self):
        current = self._record("x", "current.txt")
        old = self._record("y", "older.txt")
        tool = self._tool({"x": current, "y": old}, {"s1": [old, current]})
        with patch("uri_core.tools.read_attached_file.extract_file_text", return_value={"status": "success", "text": "x"}):
            result = tool.execute(session_id="s1", current_turn_attachment_ids=["x"])
        self.assertEqual([document["filename"] for document in result["documents"]], ["current.txt"])

    def test_multiple_explicit_files_follow_validated_order(self):
        first = self._record("x", "first.txt")
        second = self._record("z", "second.txt")
        old = self._record("y", "older.txt")
        tool = self._tool({"x": first, "z": second, "y": old}, {"s1": [old, first, second]})
        with patch("uri_core.tools.read_attached_file.extract_file_text", return_value={"status": "success", "text": "ok"}):
            result = tool.execute(session_id="s1", current_turn_attachment_ids=["z", "x"])
        self.assertEqual([document["filename"] for document in result["documents"]], ["second.txt", "first.txt"])

    def test_no_explicit_context_keeps_legacy_session_behavior(self):
        first = self._record("x", "first.txt")
        second = self._record("z", "second.txt")
        tool = self._tool({"x": first, "z": second}, {"s1": [first, second]})
        with patch("uri_core.tools.read_attached_file.extract_file_text", return_value={"status": "success", "text": "ok"}):
            result = tool.execute(session_id="s1")
        self.assertEqual(result["documents"][0]["filename"], "second.txt")

    def test_invalid_explicit_context_fails_closed(self):
        record = self._record("x", "current.txt")
        tool = self._tool({"x": record}, {"s1": [record]})
        for ids in ([], [""], ["missing"], ["x"] * 21, ["x"]):
            session_id = "other" if ids == ["x"] else "s1"
            result = tool.execute(session_id=session_id, current_turn_attachment_ids=ids)
            self.assertEqual(result["status"], "invalid_attachment_context")


if __name__ == "__main__":
    unittest.main()
