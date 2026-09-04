import os
import tempfile
import unittest

from uri_core.core.portable_paths import (
    PortablePathValidationError,
    migrate_legacy_file_if_needed,
    user_scoped_path,
)

VALID_USER_ID = "8fd65c6b-3298-4efc-8196-a4d98145562b"


class UserScopedPathTests(unittest.TestCase):

    def test_joins_root_user_id_and_filename(self):
        path = user_scoped_path(
            VALID_USER_ID, "user_profile.json", root="uri_workspace/users"
        )

        expected = os.path.normpath(
            f"uri_workspace/users/{VALID_USER_ID}/user_profile.json"
        )
        self.assertEqual(path, expected)

    def test_accepts_uppercase_uuid(self):
        path = user_scoped_path(
            VALID_USER_ID.upper(), "user_memory.json"
        )
        self.assertIn(VALID_USER_ID.upper(), path)

    def test_rejects_non_uuid_user_id(self):
        with self.assertRaises(PortablePathValidationError):
            user_scoped_path("not-a-uuid", "user_profile.json")

    def test_rejects_empty_user_id(self):
        with self.assertRaises(PortablePathValidationError):
            user_scoped_path("", "user_profile.json")

    def test_rejects_path_traversal_shaped_user_id(self):
        with self.assertRaises(PortablePathValidationError):
            user_scoped_path("../../etc", "user_profile.json")

    def test_rejects_user_id_containing_path_separator(self):
        with self.assertRaises(PortablePathValidationError):
            user_scoped_path(
                "8fd65c6b-3298-4efc-8196-a4d98145562b/../evil",
                "user_profile.json",
            )

    def test_rejects_none_user_id(self):
        with self.assertRaises(PortablePathValidationError):
            user_scoped_path(None, "user_profile.json")


class MigrateLegacyFileIfNeededTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.legacy_path = os.path.join(
            self.temp_dir.name, "legacy", "user_profile.json"
        )
        self.new_path = os.path.join(
            self.temp_dir.name, "users", VALID_USER_ID, "user_profile.json"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write(self, path: str, content: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as file:
            file.write(content)

    def test_copies_when_target_absent_and_source_present(self):
        self._write(self.legacy_path, '{"communication_style": "concise"}')

        migrated = migrate_legacy_file_if_needed(
            self.legacy_path, self.new_path
        )

        self.assertTrue(migrated)
        self.assertTrue(os.path.exists(self.new_path))

        with open(self.new_path, "r", encoding="utf-8") as file:
            self.assertEqual(
                file.read(), '{"communication_style": "concise"}'
            )

    def test_creates_parent_directory_if_missing(self):
        self._write(self.legacy_path, "content")

        self.assertFalse(os.path.exists(os.path.dirname(self.new_path)))

        migrate_legacy_file_if_needed(self.legacy_path, self.new_path)

        self.assertTrue(os.path.exists(self.new_path))

    def test_is_noop_when_source_absent(self):
        migrated = migrate_legacy_file_if_needed(
            self.legacy_path, self.new_path
        )

        self.assertFalse(migrated)
        self.assertFalse(os.path.exists(self.new_path))

    def test_is_noop_and_does_not_overwrite_when_target_present(self):
        self._write(self.legacy_path, "legacy content")
        self._write(self.new_path, "already-migrated, diverged content")

        migrated = migrate_legacy_file_if_needed(
            self.legacy_path, self.new_path
        )

        self.assertFalse(migrated)

        with open(self.new_path, "r", encoding="utf-8") as file:
            self.assertEqual(
                file.read(), "already-migrated, diverged content"
            )

    def test_leaves_legacy_file_untouched_after_copy(self):
        self._write(self.legacy_path, "original content")

        migrate_legacy_file_if_needed(self.legacy_path, self.new_path)

        self.assertTrue(os.path.exists(self.legacy_path))

        with open(self.legacy_path, "r", encoding="utf-8") as file:
            self.assertEqual(file.read(), "original content")

    def test_is_idempotent_across_repeated_calls(self):
        self._write(self.legacy_path, "content")

        first = migrate_legacy_file_if_needed(
            self.legacy_path, self.new_path
        )
        second = migrate_legacy_file_if_needed(
            self.legacy_path, self.new_path
        )

        self.assertTrue(first)
        self.assertFalse(second)


if __name__ == "__main__":
    unittest.main()
