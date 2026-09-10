"""M22.3: authentication-route rate limiting - Decisions 4 and 5, see
docs/plans/M22.3_SECURITY_ARCHITECTURE_PLAN.md sections 5.4/5.5/6.4.

Login: 5 attempts / 60 seconds / IP. Signup: 3 attempts / 300 seconds /
IP. Every attempt counts, successful or failed (Decision 4) - the
limiter is not a failure counter.

TestClient's default client host is fixed ("testclient") for every
request in a process, so these tests reset the module-level limiter
state in setUp()/tearDown() (edge.reset_rate_limiters()) rather than
relying on IP variation - this is also exactly what protects the rest
of the suite (e.g. test_m22_2_roles_sessions.py's several sequential
signups/logins) from tripping the same limiter.
"""

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from uri_core.app import edge, server
from uri_core.core.auth_session import AuthSessionStore
from uri_core.core.user_accounts import UserAccountStore


class RateLimitingTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self._original_user_account_store = server._user_account_store
        self._original_auth_session_store = server._auth_session_store
        self._original_user_contexts = server._user_contexts

        server._user_account_store = UserAccountStore(
            storage_path=os.path.join(self.temp_dir.name, "user_accounts.json")
        )
        server._auth_session_store = AuthSessionStore(
            storage_path=os.path.join(self.temp_dir.name, "auth_sessions.json")
        )
        server._user_contexts = {}

        edge.reset_rate_limiters()

        self.client = TestClient(server.app)

    def tearDown(self):
        server._user_account_store = self._original_user_account_store
        server._auth_session_store = self._original_auth_session_store
        server._user_contexts = self._original_user_contexts
        edge.reset_rate_limiters()

    # ------------------------------------------------------------
    # /auth/login: 5 / 60s / IP
    # ------------------------------------------------------------

    def test_login_allows_up_to_the_threshold(self):
        for _ in range(edge.LOGIN_RATE_LIMIT_MAX_ATTEMPTS):
            response = self.client.post(
                "/auth/login",
                json={"username": "nobody", "password": "wrong"},
            )
            # Wrong credentials -> 401, not 429, while under threshold.
            self.assertEqual(response.status_code, 401, response.text)

    def test_login_trips_429_past_the_threshold(self):
        for _ in range(edge.LOGIN_RATE_LIMIT_MAX_ATTEMPTS):
            self.client.post(
                "/auth/login",
                json={"username": "nobody", "password": "wrong"},
            )

        response = self.client.post(
            "/auth/login", json={"username": "nobody", "password": "wrong"}
        )

        self.assertEqual(response.status_code, 429, response.text)
        self.assertIn("retry-after", {k.lower() for k in response.headers.keys()})

    def test_login_counts_successful_attempts_too(self):
        # Decision 4: every attempt counts, not just failures. A
        # sequence of otherwise-valid logins must still trip the
        # limiter at the same threshold as failed ones.
        signup = self.client.post(
            "/auth/signup",
            json={"username": "rate-limit-user", "password": "correct-horse-1"},
        )
        self.assertEqual(signup.status_code, 200, signup.text)

        # The signup call itself already consumed one signup-limiter
        # slot, not a login-limiter slot - login and signup have
        # independent counters.
        for _ in range(edge.LOGIN_RATE_LIMIT_MAX_ATTEMPTS):
            response = self.client.post(
                "/auth/login",
                json={
                    "username": "rate-limit-user",
                    "password": "correct-horse-1",
                },
            )
            self.assertEqual(response.status_code, 200, response.text)

        tripped = self.client.post(
            "/auth/login",
            json={"username": "rate-limit-user", "password": "correct-horse-1"},
        )
        self.assertEqual(tripped.status_code, 429, tripped.text)

    # ------------------------------------------------------------
    # /auth/signup: 3 / 300s / IP
    # ------------------------------------------------------------

    def test_signup_allows_up_to_the_threshold(self):
        for i in range(edge.SIGNUP_RATE_LIMIT_MAX_ATTEMPTS):
            response = self.client.post(
                "/auth/signup",
                json={"username": f"signup-user-{i}", "password": "correct-horse-1"},
            )
            self.assertEqual(response.status_code, 200, response.text)

    def test_signup_trips_429_past_the_threshold(self):
        for i in range(edge.SIGNUP_RATE_LIMIT_MAX_ATTEMPTS):
            self.client.post(
                "/auth/signup",
                json={"username": f"signup-user-{i}", "password": "correct-horse-1"},
            )

        tripped = self.client.post(
            "/auth/signup",
            json={"username": "one-too-many", "password": "correct-horse-1"},
        )

        self.assertEqual(tripped.status_code, 429, tripped.text)
        # The rejected 4th signup must never have created an account.
        self.assertIsNone(
            server._user_account_store.authenticate(
                "one-too-many", "correct-horse-1"
            )
        )

    # ------------------------------------------------------------
    # Fail-closed / isolation
    # ------------------------------------------------------------

    def test_login_and_signup_limiters_are_independent(self):
        for i in range(edge.SIGNUP_RATE_LIMIT_MAX_ATTEMPTS):
            self.client.post(
                "/auth/signup",
                json={"username": f"independent-{i}", "password": "correct-horse-1"},
            )
        # Signup limiter is now tripped; login must be unaffected.
        response = self.client.post(
            "/auth/login", json={"username": "independent-0", "password": "wrong"}
        )
        self.assertEqual(response.status_code, 401, response.text)

    def test_reset_hook_actually_clears_state(self):
        for _ in range(edge.LOGIN_RATE_LIMIT_MAX_ATTEMPTS):
            self.client.post(
                "/auth/login", json={"username": "x", "password": "wrong"}
            )
        tripped = self.client.post(
            "/auth/login", json={"username": "x", "password": "wrong"}
        )
        self.assertEqual(tripped.status_code, 429)

        edge.reset_rate_limiters()

        recovered = self.client.post(
            "/auth/login", json={"username": "x", "password": "wrong"}
        )
        self.assertEqual(recovered.status_code, 401)


class RateLimiterUnitTests(unittest.TestCase):
    """Direct tests of the limiter's counting/window logic, independent
    of HTTP - proves the fail-closed and every-attempt properties at
    the unit level rather than only through the HTTP surface above."""

    def setUp(self):
        edge.reset_rate_limiters()

    def tearDown(self):
        edge.reset_rate_limiters()

    def test_within_window_same_key_trips_after_max_attempts(self):
        limiter = edge._FixedWindowRateLimiter(max_attempts=2, window_seconds=60.0)

        limiter.check_and_record("1.2.3.4")
        limiter.check_and_record("1.2.3.4")

        with self.assertRaises(edge.RateLimitExceededError):
            limiter.check_and_record("1.2.3.4")

    def test_different_keys_do_not_share_a_budget(self):
        limiter = edge._FixedWindowRateLimiter(max_attempts=1, window_seconds=60.0)

        limiter.check_and_record("1.1.1.1")
        # A different IP must not be affected by another IP's count.
        limiter.check_and_record("2.2.2.2")

    def test_reset_clears_all_keys(self):
        limiter = edge._FixedWindowRateLimiter(max_attempts=1, window_seconds=60.0)
        limiter.check_and_record("1.1.1.1")
        limiter.reset()
        limiter.check_and_record("1.1.1.1")  # would raise if not reset


if __name__ == "__main__":
    unittest.main()
