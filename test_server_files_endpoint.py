"""M16 Priority 1: the file upload/list/delete HTTP boundary. Validation
is enforced server-side, never trusted from the client, and a rejected
upload gets a real reason rather than a silent drop. See
uri_core/app/server.py's /files endpoints and core/file_store.py.
"""

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from uri_core.app import server
from uri_core.core.file_store import MAX_FILE_BYTES, FileStore


class ServerFilesEndpointTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self._original_store = server._file_store
        server._file_store = FileStore(
            storage_dir=os.path.join(self.temp_dir.name, "uploads")
        )
        self.addCleanup(
            setattr, server, "_file_store", self._original_store
        )
        self.client = TestClient(server.app)

    def _upload(self, name, content, session_id="s1", content_type="text/plain"):
        return self.client.post(
            "/files",
            data={"session_id": session_id},
            files={"file": (name, content, content_type)},
        )

    def test_upload_returns_a_bounded_reference(self):
        response = self._upload("notes.txt", b"hello")

        self.assertEqual(response.status_code, 200)
        reference = response.json()["file"]
        self.assertEqual(
            set(reference.keys()),
            {"file_id", "filename", "media_type", "size_bytes"},
        )
        self.assertEqual(reference["filename"], "notes.txt")
        # A storage path must never cross this boundary.
        self.assertNotIn("stored_name", reference)

    def test_unsupported_type_is_rejected_with_a_real_reason(self):
        response = self._upload("payload.exe", b"MZ")

        self.assertEqual(response.status_code, 400)
        self.assertIn("not accepted", response.json()["detail"])

    def test_empty_file_is_rejected(self):
        response = self._upload("empty.txt", b"")

        self.assertEqual(response.status_code, 400)

    def test_oversized_file_is_rejected(self):
        response = self._upload("big.txt", b"x" * (MAX_FILE_BYTES + 1))

        self.assertEqual(response.status_code, 400)
        self.assertIn("limit", response.json()["detail"])

    def test_traversal_filename_is_stored_under_a_safe_name(self):
        response = self._upload("../../etc/passwd.txt", b"data")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["file"]["filename"], "passwd.txt")

    def test_files_are_listed_per_session(self):
        self._upload("a.txt", b"a", session_id="s1")
        self._upload("b.txt", b"b", session_id="s2")

        body = self.client.get("/files", params={"session_id": "s1"}).json()

        self.assertEqual(len(body["files"]), 1)
        self.assertEqual(body["files"][0]["filename"], "a.txt")

    def test_delete_reports_honestly_whether_anything_was_removed(self):
        file_id = self._upload("a.txt", b"a").json()["file"]["file_id"]

        first = self.client.delete(f"/files/{file_id}").json()
        second = self.client.delete(f"/files/{file_id}").json()

        self.assertTrue(first["deleted"])
        self.assertFalse(second["deleted"])

    def test_session_id_is_required(self):
        response = self.client.post(
            "/files", files={"file": ("a.txt", b"a", "text/plain")}
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
