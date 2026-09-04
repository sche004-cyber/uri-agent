import json
import os
import tempfile
import unittest

from uri_core.core.identity import (
    DeviceIdentity,
    DeviceIdentityStore,
    UserIdentity,
    UserIdentityStore,
)


class UserIdentityStoreTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = os.path.join(
            self.temp_dir.name, "portable_identity.json"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_first_call_creates_a_new_identity(self):
        store = UserIdentityStore(storage_path=self.storage_path)

        self.assertFalse(os.path.exists(self.storage_path))

        identity = store.load_or_create()

        self.assertIsInstance(identity, UserIdentity)
        self.assertTrue(identity.user_id)
        self.assertTrue(identity.created_at)
        self.assertTrue(os.path.exists(self.storage_path))

    def test_identity_persists_across_separate_store_instances(self):
        # A *new* UserIdentityStore object pointed at the same path -
        # proves this is real file persistence, not in-memory caching
        # on one object.
        first = UserIdentityStore(
            storage_path=self.storage_path
        ).load_or_create()

        second = UserIdentityStore(
            storage_path=self.storage_path
        ).load_or_create()

        self.assertEqual(first.user_id, second.user_id)
        self.assertEqual(first.created_at, second.created_at)

    def test_repeated_calls_on_the_same_store_are_idempotent(self):
        store = UserIdentityStore(storage_path=self.storage_path)

        first = store.load_or_create()
        second = store.load_or_create()

        self.assertEqual(first.user_id, second.user_id)

    def test_stored_file_contains_expected_shape(self):
        store = UserIdentityStore(storage_path=self.storage_path)
        identity = store.load_or_create()

        with open(self.storage_path, "r", encoding="utf-8") as file:
            raw = json.load(file)

        self.assertEqual(raw["user_id"], identity.user_id)
        self.assertEqual(raw["created_at"], identity.created_at)
        self.assertIn("schema_version", raw)

    def test_corrupted_file_degrades_to_a_fresh_identity(self):
        with open(self.storage_path, "w", encoding="utf-8") as file:
            file.write("{ not valid json")

        store = UserIdentityStore(storage_path=self.storage_path)

        # Must not raise - mirrors SessionManager._load_session's
        # except Exception: return None safety pattern.
        identity = store.load_or_create()

        self.assertTrue(identity.user_id)

    def test_creates_parent_directory_if_missing(self):
        nested_path = os.path.join(
            self.temp_dir.name, "nested", "dir", "portable_identity.json"
        )
        store = UserIdentityStore(storage_path=nested_path)

        identity = store.load_or_create()

        self.assertTrue(os.path.exists(nested_path))
        self.assertTrue(identity.user_id)


class DeviceIdentityStoreTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = os.path.join(
            self.temp_dir.name, "device_identity.json"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_first_call_creates_a_new_identity(self):
        store = DeviceIdentityStore(storage_path=self.storage_path)

        identity = store.load_or_create()

        self.assertIsInstance(identity, DeviceIdentity)
        self.assertTrue(identity.device_id)
        self.assertTrue(os.path.exists(self.storage_path))

    def test_identity_persists_across_separate_store_instances(self):
        first = DeviceIdentityStore(
            storage_path=self.storage_path
        ).load_or_create()

        second = DeviceIdentityStore(
            storage_path=self.storage_path
        ).load_or_create()

        self.assertEqual(first.device_id, second.device_id)

    def test_corrupted_file_degrades_to_a_fresh_identity(self):
        with open(self.storage_path, "w", encoding="utf-8") as file:
            file.write("not json at all")

        store = DeviceIdentityStore(storage_path=self.storage_path)

        identity = store.load_or_create()

        self.assertTrue(identity.device_id)


class UserAndDeviceIdentityAreDistinctTests(unittest.TestCase):
    """Directly exercises the architectural rule: user_id must be
    device-independent, device_id must be local/non-portable, and the
    two must never collide or be derived from one another."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_user_id_and_device_id_are_generated_independently(self):
        user_store = UserIdentityStore(
            storage_path=os.path.join(
                self.temp_dir.name, "portable_identity.json"
            )
        )
        device_store = DeviceIdentityStore(
            storage_path=os.path.join(
                self.temp_dir.name, "device_identity.json"
            )
        )

        user_identity = user_store.load_or_create()
        device_identity = device_store.load_or_create()

        self.assertNotEqual(
            user_identity.user_id, device_identity.device_id
        )

    def test_two_devices_sharing_the_same_user_id_get_different_device_ids(
        self,
    ):
        # Simulates the same portable user_id file being carried to a
        # second device (e.g. copied/exported), while each device's
        # own device_identity.json is independent and local.
        shared_user_path = os.path.join(
            self.temp_dir.name, "portable_identity.json"
        )

        user_on_device_a = UserIdentityStore(
            storage_path=shared_user_path
        ).load_or_create()

        device_a = DeviceIdentityStore(
            storage_path=os.path.join(
                self.temp_dir.name, "device_a_identity.json"
            )
        ).load_or_create()

        # "Moving to a new device" - same portable user file, a
        # brand-new device identity file (never copied/shared).
        user_on_device_b = UserIdentityStore(
            storage_path=shared_user_path
        ).load_or_create()

        device_b = DeviceIdentityStore(
            storage_path=os.path.join(
                self.temp_dir.name, "device_b_identity.json"
            )
        ).load_or_create()

        self.assertEqual(
            user_on_device_a.user_id, user_on_device_b.user_id
        )
        self.assertNotEqual(device_a.device_id, device_b.device_id)


if __name__ == "__main__":
    unittest.main()
