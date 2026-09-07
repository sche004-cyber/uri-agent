"""M16 Priority 1: secure storage of user-supplied files. The client's
filename must never influence where anything is written, an unsupported
or oversized file must be refused with a real reason, and no path
outside the store's own directory may ever be produced. See
uri_core/core/file_store.py.
"""

import os
import tempfile
import unittest

from uri_core.core.file_store import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_BYTES,
    FileStore,
    FileValidationError,
    sanitize_filename,
)


class SanitizeFilenameTests(unittest.TestCase):

    def test_directory_components_are_stripped(self):
        self.assertEqual(
            sanitize_filename("../../etc/passwd"), "passwd"
        )
        self.assertEqual(
            sanitize_filename(r"..\..\windows\system32\cmd.exe"),
            "cmd.exe",
        )

    def test_empty_or_non_string_degrades_to_a_safe_default(self):
        self.assertEqual(sanitize_filename(""), "upload")
        self.assertEqual(sanitize_filename(None), "upload")
        self.assertEqual(sanitize_filename("   "), "upload")

    def test_leading_dots_are_removed(self):
        self.assertEqual(sanitize_filename("...hidden.pdf"), "hidden.pdf")

    def test_forbidden_characters_are_removed(self):
        self.assertNotIn("|", sanitize_filename('re|port?.pdf'))


class FileStoreTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.store = FileStore(
            storage_dir=os.path.join(self.temp_dir.name, "uploads")
        )

    def test_saved_file_is_retrievable_and_contained(self):
        record = self.store.save(
            filename="report.pdf",
            content=b"%PDF-1.4 fake",
            media_type="application/pdf",
            session_id="s1",
        )

        path = self.store.path_for(record.file_id)

        self.assertIsNotNone(path)
        self.assertTrue(os.path.exists(path))
        # Stored under a server-generated name, never the client's.
        self.assertNotIn("report", os.path.basename(path))
        self.assertTrue(
            os.path.realpath(path).startswith(
                os.path.realpath(self.store.storage_dir) + os.sep
            )
        )

    def test_original_filename_is_kept_for_display_only(self):
        record = self.store.save(
            filename="../../secret/report.pdf",
            content=b"data",
            session_id="s1",
        )

        self.assertEqual(record.filename, "report.pdf")
        self.assertTrue(record.stored_name.endswith(".pdf"))

    def test_unsupported_extension_is_refused_with_a_real_reason(self):
        with self.assertRaises(FileValidationError) as caught:
            self.store.save(
                filename="payload.exe", content=b"MZ", session_id="s1"
            )

        self.assertIn("not accepted", str(caught.exception))

    def test_empty_file_is_refused(self):
        with self.assertRaises(FileValidationError):
            self.store.save(
                filename="empty.txt", content=b"", session_id="s1"
            )

    def test_oversized_file_is_refused(self):
        with self.assertRaises(FileValidationError) as caught:
            self.store.save(
                filename="big.txt",
                content=b"x" * (MAX_FILE_BYTES + 1),
                session_id="s1",
            )

        self.assertIn("limit", str(caught.exception))

    def test_files_are_listed_per_session_only(self):
        self.store.save(
            filename="a.txt", content=b"a", session_id="s1"
        )
        self.store.save(
            filename="b.txt", content=b"b", session_id="s2"
        )

        self.assertEqual(len(self.store.list_for_session("s1")), 1)
        self.assertEqual(len(self.store.list_for_session("s2")), 1)
        self.assertEqual(len(self.store.list_for_session("other")), 0)

    def test_reference_never_exposes_a_path(self):
        record = self.store.save(
            filename="a.txt", content=b"a", session_id="s1"
        )

        reference = record.to_reference()

        self.assertEqual(
            set(reference.keys()),
            {"file_id", "filename", "media_type", "size_bytes"},
        )
        self.assertNotIn("stored_name", reference)

    def test_unknown_id_resolves_to_nothing(self):
        self.assertIsNone(self.store.path_for("no-such-id"))
        self.assertIsNone(self.store.get("no-such-id"))

    def test_references_for_skips_unknown_ids(self):
        record = self.store.save(
            filename="a.txt", content=b"a", session_id="s1"
        )

        references = self.store.references_for(
            [record.file_id, "made-up-id"]
        )

        self.assertEqual(len(references), 1)
        self.assertEqual(references[0]["file_id"], record.file_id)

    def test_tampered_index_cannot_escape_the_store_directory(self):
        record = self.store.save(
            filename="a.txt", content=b"a", session_id="s1"
        )
        # Simulate a hand-edited/corrupted index pointing outside.
        records = self.store._load()
        records[0].stored_name = "../../../etc/passwd"
        self.store._save(records)

        self.assertIsNone(self.store.path_for(record.file_id))

    def test_delete_removes_both_bytes_and_index_entry(self):
        record = self.store.save(
            filename="a.txt", content=b"a", session_id="s1"
        )
        path = self.store.path_for(record.file_id)

        self.assertTrue(self.store.delete(record.file_id))
        self.assertFalse(os.path.exists(path))
        self.assertIsNone(self.store.get(record.file_id))
        self.assertFalse(self.store.delete(record.file_id))

    def test_corrupted_index_degrades_to_empty(self):
        self.store.save(filename="a.txt", content=b"a", session_id="s1")

        with open(self.store.index_path, "w", encoding="utf-8") as file:
            file.write("not json{{{")

        self.assertEqual(self.store.list_for_session("s1"), [])

    def test_every_allowed_extension_is_actually_storable(self):
        for extension in sorted(ALLOWED_EXTENSIONS):
            record = self.store.save(
                filename=f"sample{extension}",
                content=b"content",
                session_id="s1",
            )
            self.assertTrue(record.stored_name.endswith(extension))


if __name__ == "__main__":
    unittest.main()
