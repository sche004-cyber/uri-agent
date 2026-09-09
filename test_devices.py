"""Unit tests for uri_core.core.devices (M22.2) - device-grouped views
and revocation over AuthSessionStore's persisted sessions. See
devices.py's own module docstring: this module owns no storage of its
own, so these tests exercise it purely through a real, temp-backed
AuthSessionStore."""

import os
import tempfile
import unittest

from uri_core.core.auth_session import AuthSessionStore
from uri_core.core.devices import list_devices_for_user, revoke_device


class DevicesTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.store = AuthSessionStore(
            storage_path=os.path.join(
                self.temp_dir.name, "auth_sessions.json"
            )
        )

    def test_list_devices_groups_by_device_id(self):
        self.store.create("user-a", device_id="phone")
        self.store.create("user-a", device_id="phone")
        self.store.create("user-a", device_id="laptop")

        devices = list_devices_for_user(self.store, "user-a")

        by_id = {d.device_id: d for d in devices}
        self.assertEqual(set(by_id), {"phone", "laptop"})
        self.assertEqual(by_id["phone"].session_count, 2)
        self.assertEqual(by_id["laptop"].session_count, 1)

    def test_list_devices_excludes_sessions_with_no_device_id(self):
        self.store.create("user-a", device_id=None)
        self.store.create("user-a", device_id="phone")

        devices = list_devices_for_user(self.store, "user-a")

        self.assertEqual([d.device_id for d in devices], ["phone"])

    def test_list_devices_returns_nothing_for_a_user_with_no_sessions(
        self,
    ):
        self.assertEqual(
            list_devices_for_user(self.store, "nobody"), []
        )

    def test_list_devices_never_shows_another_users_devices(self):
        self.store.create("user-a", device_id="a-phone")
        self.store.create("user-b", device_id="b-phone")

        devices = list_devices_for_user(self.store, "user-a")

        self.assertEqual([d.device_id for d in devices], ["a-phone"])

    def test_revoke_device_revokes_every_session_on_that_device(self):
        token_1 = self.store.create("user-a", device_id="phone")
        token_2 = self.store.create("user-a", device_id="phone")
        other_device_token = self.store.create(
            "user-a", device_id="laptop"
        )

        revoked_count = revoke_device(self.store, "user-a", "phone")

        self.assertEqual(revoked_count, 2)
        self.assertIsNone(self.store.resolve(token_1))
        self.assertIsNone(self.store.resolve(token_2))
        self.assertEqual(
            self.store.resolve(other_device_token), "user-a"
        )

    def test_revoke_device_unknown_device_id_revokes_nothing(self):
        self.store.create("user-a", device_id="phone")

        revoked_count = revoke_device(
            self.store, "user-a", "never-registered"
        )

        self.assertEqual(revoked_count, 0)

    def test_revoke_device_never_touches_another_users_session_even_with_the_same_device_id(
        self,
    ):
        # device_id is client-reported and not guaranteed unique across
        # accounts - see auth_session.py's own module docstring.
        victim_token = self.store.create("user-b", device_id="shared-name")
        self.store.create("user-a", device_id="shared-name")

        revoke_device(self.store, "user-a", "shared-name")

        self.assertEqual(self.store.resolve(victim_token), "user-b")


if __name__ == "__main__":
    unittest.main()
