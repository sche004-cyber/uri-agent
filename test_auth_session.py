"""Unit tests for uri_core.core.auth_session (Prototype 1)."""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from uri_core.core.auth_session import AuthSessionStore


class AuthSessionStoreTests(unittest.TestCase):

    def test_create_then_resolve_returns_the_same_user_id(self):
        store = AuthSessionStore()

        token = store.create("user-123")

        self.assertEqual(store.resolve(token), "user-123")

    def test_two_tokens_for_different_users_never_collide(self):
        store = AuthSessionStore()

        token_a = store.create("user-a")
        token_b = store.create("user-b")

        self.assertNotEqual(token_a, token_b)
        self.assertEqual(store.resolve(token_a), "user-a")
        self.assertEqual(store.resolve(token_b), "user-b")

    def test_resolve_returns_none_for_unknown_token(self):
        store = AuthSessionStore()

        self.assertIsNone(store.resolve("never-issued"))

    def test_resolve_returns_none_for_empty_token(self):
        store = AuthSessionStore()

        self.assertIsNone(store.resolve(""))

    def test_revoke_makes_the_token_unresolvable(self):
        store = AuthSessionStore()
        token = store.create("user-123")

        revoked = store.revoke(token)

        self.assertTrue(revoked)
        self.assertIsNone(store.resolve(token))

    def test_revoking_an_unknown_token_returns_false(self):
        store = AuthSessionStore()

        self.assertFalse(store.revoke("never-issued"))

    def test_two_calls_to_create_for_the_same_user_yield_different_tokens(
        self,
    ):
        store = AuthSessionStore()

        first = store.create("user-123")
        second = store.create("user-123")

        self.assertNotEqual(first, second)
        # Both remain independently valid - logging in from a second
        # client does not invalidate the first client's session.
        self.assertEqual(store.resolve(first), "user-123")
        self.assertEqual(store.resolve(second), "user-123")

    def test_token_expires_after_its_ttl(self):
        store = AuthSessionStore(ttl_seconds=60)

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
        store = AuthSessionStore(ttl_seconds=60)

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


if __name__ == "__main__":
    unittest.main()
