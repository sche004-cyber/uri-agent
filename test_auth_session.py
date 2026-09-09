"""Unit tests for uri_core.core.auth_session (Prototype 1, persisted as
of M22.2 - see this module's own docstring and
URI_M22_ARCHITECTURE.md section 4/10 finding S4)."""

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from uri_core.core.auth_session import AuthSessionStore


class AuthSessionStoreTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.storage_path = os.path.join(
            self.temp_dir.name, "auth_sessions.json"
        )

    def _store(self, ttl_seconds=None):
        kwargs = {"storage_path": self.storage_path}
        if ttl_seconds is not None:
            kwargs["ttl_seconds"] = ttl_seconds
        return AuthSessionStore(**kwargs)

    def test_create_then_resolve_returns_the_same_user_id(self):
        store = self._store()

        token = store.create("user-123")

        self.assertEqual(store.resolve(token), "user-123")

    def test_two_tokens_for_different_users_never_collide(self):
        store = self._store()

        token_a = store.create("user-a")
        token_b = store.create("user-b")

        self.assertNotEqual(token_a, token_b)
        self.assertEqual(store.resolve(token_a), "user-a")
        self.assertEqual(store.resolve(token_b), "user-b")

    def test_resolve_returns_none_for_unknown_token(self):
        store = self._store()

        self.assertIsNone(store.resolve("never-issued"))

    def test_resolve_returns_none_for_empty_token(self):
        store = self._store()

        self.assertIsNone(store.resolve(""))

    def test_revoke_makes_the_token_unresolvable(self):
        store = self._store()
        token = store.create("user-123")

        revoked = store.revoke(token)

        self.assertTrue(revoked)
        self.assertIsNone(store.resolve(token))

    def test_revoking_an_unknown_token_returns_false(self):
        store = self._store()

        self.assertFalse(store.revoke("never-issued"))

    def test_two_calls_to_create_for_the_same_user_yield_different_tokens(
        self,
    ):
        store = self._store()

        first = store.create("user-123")
        second = store.create("user-123")

        self.assertNotEqual(first, second)
        # Both remain independently valid - logging in from a second
        # client does not invalidate the first client's session.
        self.assertEqual(store.resolve(first), "user-123")
        self.assertEqual(store.resolve(second), "user-123")

    def test_token_expires_after_its_ttl(self):
        store = self._store(ttl_seconds=60)

        base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)

        with patch(
            "uri_core.core.auth_session._now", return_value=base_time
        ):
            token = store.create("user-123")
            self.assertEqual(store.resolve(token), "user-123")

        with patch(
            "uri_core.core.auth_session._now",
            return_value=base_time + timedelta(seconds=61),
        ):
            self.assertIsNone(store.resolve(token))

    def test_token_just_under_its_ttl_still_resolves(self):
        store = self._store(ttl_seconds=60)

        base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)

        with patch(
            "uri_core.core.auth_session._now", return_value=base_time
        ):
            token = store.create("user-123")

        with patch(
            "uri_core.core.auth_session._now",
            return_value=base_time + timedelta(seconds=59),
        ):
            self.assertEqual(store.resolve(token), "user-123")

    # ------------------------------------------------------------
    # M22.2: persistence across a fresh instance ("restart").
    # ------------------------------------------------------------

    def test_token_survives_a_fresh_store_instance_pointed_at_the_same_path(
        self,
    ):
        first_instance = self._store()
        token = first_instance.create("user-123", device_id="phone-1")

        second_instance = self._store()

        self.assertEqual(second_instance.resolve(token), "user-123")
        self.assertEqual(
            second_instance.get_device_id(token), "phone-1"
        )

    def test_revoke_on_one_instance_is_visible_from_another(self):
        first_instance = self._store()
        token = first_instance.create("user-123")

        second_instance = self._store()
        self.assertTrue(second_instance.revoke(token))

        third_instance = self._store()
        self.assertIsNone(third_instance.resolve(token))

    def test_raw_token_never_appears_on_disk(self):
        store = self._store()
        token = store.create("user-123")

        with open(self.storage_path, "r", encoding="utf-8") as file:
            raw_contents = file.read()

        self.assertNotIn(token, raw_contents)

    def test_expired_session_is_pruned_from_disk_on_lookup(self):
        store = self._store(ttl_seconds=60)

        base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)

        with patch(
            "uri_core.core.auth_session._now", return_value=base_time
        ):
            token = store.create("user-123")

        with patch(
            "uri_core.core.auth_session._now",
            return_value=base_time + timedelta(seconds=61),
        ):
            self.assertIsNone(store.resolve(token))

        # A fresh instance reading the same file must not resurrect
        # the expired session either - it was actually removed, not
        # merely reported as invalid this one time.
        fresh = self._store(ttl_seconds=60)
        with patch(
            "uri_core.core.auth_session._now",
            return_value=base_time + timedelta(seconds=61),
        ):
            self.assertIsNone(fresh.resolve(token))

    def test_corrupted_file_degrades_to_no_sessions(self):
        with open(self.storage_path, "w", encoding="utf-8") as file:
            file.write("{not valid json")

        store = self._store()

        self.assertIsNone(store.resolve("anything"))
        # A corrupted file never prevents a NEW session from being
        # created and resolved afterward.
        token = store.create("user-123")
        self.assertEqual(store.resolve(token), "user-123")

    # ------------------------------------------------------------
    # M22.2: list_for_user / revoke_by_ref - the device-management
    # primitives (see devices.py, which builds on these).
    # ------------------------------------------------------------

    def test_list_for_user_returns_only_that_users_live_sessions(self):
        store = self._store()
        store.create("user-a", device_id="a-phone")
        store.create("user-a", device_id="a-laptop")
        store.create("user-b", device_id="b-phone")

        sessions = store.list_for_user("user-a")

        self.assertEqual(len(sessions), 2)
        self.assertEqual(
            {s.device_id for s in sessions}, {"a-phone", "a-laptop"}
        )
        self.assertTrue(all(s.user_id == "user-a" for s in sessions))

    def test_list_for_user_never_exposes_the_raw_token(self):
        store = self._store()
        token = store.create("user-a", device_id="a-phone")

        sessions = store.list_for_user("user-a")

        self.assertEqual(len(sessions), 1)
        self.assertNotEqual(sessions[0].session_ref, token)
        # session_ref must not itself work as a bearer token.
        self.assertIsNone(store.resolve(sessions[0].session_ref))

    def test_list_for_user_excludes_expired_sessions(self):
        store = self._store(ttl_seconds=60)
        base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)

        with patch(
            "uri_core.core.auth_session._now", return_value=base_time
        ):
            store.create("user-a", device_id="a-phone")

        with patch(
            "uri_core.core.auth_session._now",
            return_value=base_time + timedelta(seconds=61),
        ):
            self.assertEqual(store.list_for_user("user-a"), [])

    def test_revoke_by_ref_revokes_a_session_from_a_different_instance(
        self,
    ):
        owning_instance = self._store()
        token = owning_instance.create("user-a", device_id="a-phone")
        session_ref = owning_instance.list_for_user("user-a")[
            0
        ].session_ref

        other_instance = self._store()
        self.assertTrue(other_instance.revoke_by_ref(session_ref))

        self.assertIsNone(owning_instance.resolve(token))

    def test_revoke_by_ref_unknown_ref_returns_false(self):
        store = self._store()
        self.assertFalse(store.revoke_by_ref("not-a-real-ref"))

    def test_revoke_by_ref_never_affects_another_users_sessions(self):
        store = self._store()
        token_a = store.create("user-a", device_id="shared-name")
        token_b = store.create("user-b", device_id="shared-name")

        ref_a = store.list_for_user("user-a")[0].session_ref

        store.revoke_by_ref(ref_a)

        self.assertIsNone(store.resolve(token_a))
        self.assertEqual(store.resolve(token_b), "user-b")


if __name__ == "__main__":
    unittest.main()
