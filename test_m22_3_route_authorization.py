"""M22.3: route classification enumeration and the negative
authorization matrix for the five endpoints S1 closes - see
docs/plans/M22.3_SECURITY_ARCHITECTURE_PLAN.md sections 14.1/14.2 and
15.

Two concerns, kept in one file because they share the same fixture:

1. Every route registered on `server.app` appears in
   route_classification.ROUTE_CLASSIFICATION, and the counts match - a
   route added without updating that table fails this test immediately
   (invariant: "a new route can never silently default to public").
2. The five previously-unauthenticated mutating endpoints now require
   ADMIN: 401 anonymous, 403 for a logged-in non-admin, success for a
   logged-in ADMIN.
"""

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from uri_core.app import edge, route_classification, server
from uri_core.core.auth_session import AuthSessionStore
from uri_core.core.user_accounts import ROLE_ADMIN, UserAccountStore


class RouteEnumerationTests(unittest.TestCase):
    """No login/account state needed - this only inspects app.routes."""

    def _classified_http_routes(self):
        classified = []
        for route in server.app.routes:
            methods = getattr(route, "methods", None)
            path = getattr(route, "path", None)
            if not methods or path is None:
                continue
            for method in methods:
                if method in {"HEAD", "OPTIONS"}:
                    continue
                classified.append((method, path))
        return classified

    def test_every_registered_route_is_classified(self):
        routes = self._classified_http_routes()

        unclassified = [
            route
            for route in routes
            if route not in route_classification.ROUTE_CLASSIFICATION
        ]

        self.assertEqual(
            unclassified,
            [],
            f"Route(s) missing from ROUTE_CLASSIFICATION: {unclassified}",
        )

    def test_route_count_matches_the_expected_baseline(self):
        routes = self._classified_http_routes()

        self.assertEqual(
            len(set(routes)),
            route_classification.EXPECTED_ROUTE_COUNT,
            "Route count drifted from the M22.3 baseline (39) - update "
            "EXPECTED_ROUTE_COUNT and ROUTE_CLASSIFICATION together if "
            "this is a deliberate addition/removal.",
        )

    def test_classification_table_has_no_stray_entries(self):
        routes = set(self._classified_http_routes())

        stray = [
            entry
            for entry in route_classification.ROUTE_CLASSIFICATION
            if entry not in routes
        ]

        self.assertEqual(
            stray,
            [],
            f"ROUTE_CLASSIFICATION references route(s) not actually "
            f"registered on the app: {stray}",
        )

    def test_deferred_public_routes_are_still_present_and_public(self):
        for route in route_classification.DEFERRED_PUBLIC_ROUTES:
            self.assertEqual(
                route_classification.ROUTE_CLASSIFICATION[route],
                route_classification.PUBLIC,
            )

    def test_five_s1_routes_are_admin(self):
        for route in route_classification.ADMIN_GATED_ROUTES:
            self.assertEqual(
                route_classification.ROUTE_CLASSIFICATION[route],
                route_classification.ADMIN,
            )


class AdminGatedEndpointsTests(unittest.TestCase):

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

        admin = self._signup("m22-3-admin")
        self.admin_token = admin["token"]
        self.assertEqual(
            self.client.get(
                "/auth/me", headers=self._auth(self.admin_token)
            ).json()["role"],
            ROLE_ADMIN,
        )

        user = self._signup("m22-3-plain-user")
        self.user_token = user["token"]

    def tearDown(self):
        server._user_account_store = self._original_user_account_store
        server._auth_session_store = self._original_auth_session_store
        server._user_contexts = self._original_user_contexts
        edge.reset_rate_limiters()

    def _signup(self, username, password="correct-horse-1"):
        response = self.client.post(
            "/auth/signup", json={"username": username, "password": password}
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    ADMIN_ROUTES = (
        ("post", "/skills/nonexistent-skill/enable"),
        ("post", "/skills/nonexistent-skill/disable"),
        ("delete", "/skills/nonexistent-skill"),
        ("post", "/connections/gmail/authorize"),
        ("delete", "/connections/gmail"),
    )

    def _call(self, method, path, headers=None):
        return getattr(self.client, method)(path, headers=headers)

    def test_anonymous_caller_gets_401_on_every_admin_route(self):
        for method, path in self.ADMIN_ROUTES:
            with self.subTest(route=(method, path)):
                response = self._call(method, path)
                self.assertEqual(response.status_code, 401, response.text)

    def test_non_admin_user_gets_403_on_every_admin_route(self):
        for method, path in self.ADMIN_ROUTES:
            with self.subTest(route=(method, path)):
                response = self._call(
                    method, path, headers=self._auth(self.user_token)
                )
                self.assertEqual(response.status_code, 403, response.text)

    def test_admin_reaches_the_handler_on_every_admin_route(self):
        # Passing the ADMIN gate is what's under test here, not whatever
        # domain-level outcome the handler itself produces afterwards
        # (e.g. 404 for a skill that was never installed) - 401/403
        # would only ever come from the dependency, never from the
        # handler body.
        for method, path in self.ADMIN_ROUTES:
            with self.subTest(route=(method, path)):
                response = self._call(
                    method, path, headers=self._auth(self.admin_token)
                )
                self.assertNotIn(response.status_code, (401, 403))

    def test_expired_or_malformed_token_still_401s_on_admin_routes(self):
        response = self._call(
            "post",
            "/skills/nonexistent-skill/enable",
            headers={"Authorization": "Bearer not-a-real-token"},
        )
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
