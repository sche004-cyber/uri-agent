import json
import os
import tempfile
import unittest

from uri_core.core.user_profile import UserProfile, UserProfileStore


class UserProfileStoreTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = os.path.join(
            self.temp_dir.name, "user_profile.json"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_first_call_creates_a_default_profile(self):
        store = UserProfileStore(storage_path=self.storage_path)

        self.assertFalse(os.path.exists(self.storage_path))

        profile = store.load_or_create()

        self.assertIsInstance(profile, UserProfile)
        self.assertEqual(profile.communication_style, "concise")
        self.assertEqual(profile.autonomy_level, "askEveryTime")
        self.assertEqual(profile.focus_areas, [])
        self.assertTrue(profile.updated_at)
        self.assertTrue(os.path.exists(self.storage_path))

    def test_profile_persists_across_separate_store_instances(self):
        first = UserProfileStore(
            storage_path=self.storage_path
        ).load_or_create()

        second = UserProfileStore(
            storage_path=self.storage_path
        ).load_or_create()

        self.assertEqual(first, second)

    def test_save_replaces_the_whole_profile_and_updates_timestamp(self):
        store = UserProfileStore(storage_path=self.storage_path)
        original = store.load_or_create()

        saved = store.save(
            UserProfile(
                communication_style="formal",
                autonomy_level="routineAutoApprove",
                focus_areas=["insurance", "student records"],
            )
        )

        self.assertEqual(saved.communication_style, "formal")
        self.assertEqual(saved.autonomy_level, "routineAutoApprove")
        self.assertEqual(
            saved.focus_areas, ["insurance", "student records"]
        )
        self.assertNotEqual(saved.updated_at, original.updated_at)

        reloaded = UserProfileStore(
            storage_path=self.storage_path
        ).load_or_create()

        self.assertEqual(reloaded, saved)

    def test_stored_file_contains_expected_shape(self):
        store = UserProfileStore(storage_path=self.storage_path)
        profile = store.load_or_create()

        with open(self.storage_path, "r", encoding="utf-8") as file:
            raw = json.load(file)

        self.assertEqual(
            raw["communication_style"], profile.communication_style
        )
        self.assertEqual(raw["autonomy_level"], profile.autonomy_level)
        self.assertEqual(raw["focus_areas"], profile.focus_areas)
        self.assertIn("schema_version", raw)

    def test_corrupted_file_degrades_to_a_fresh_default_profile(self):
        with open(self.storage_path, "w", encoding="utf-8") as file:
            file.write("{ not valid json")

        store = UserProfileStore(storage_path=self.storage_path)

        profile = store.load_or_create()

        self.assertEqual(profile.communication_style, "concise")

    def test_creates_parent_directory_if_missing(self):
        nested_path = os.path.join(
            self.temp_dir.name, "nested", "dir", "user_profile.json"
        )
        store = UserProfileStore(storage_path=nested_path)

        profile = store.load_or_create()

        self.assertTrue(os.path.exists(nested_path))
        self.assertTrue(profile.communication_style)


if __name__ == "__main__":
    unittest.main()
