"""M23 (plan section 16, row 8): the six /graph/* routes are self-scoped
(a second user cannot read/traverse the first user's graph - attempted
cross-user entity_id access returns 404, not another user's data) and
correctly classified USER in route_classification.py's enumeration
(the same invariant test_m22_3_route_authorization.py already proves
for every other route)."""

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from uri_core.app import edge, route_classification, server
from uri_core.core.auth_session import AuthSessionStore
from uri_core.core.user_accounts import UserAccountStore


class GraphRouteClassificationTests(unittest.TestCase):
    """No login/account state needed - mirrors
    test_m22_3_route_authorization.py's RouteEnumerationTests."""

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

    def test_every_graph_route_is_classified_user(self):
        expected_graph_routes = {
            ("GET", "/graph/entities/{entity_id}"),
            ("GET", "/graph/query"),
            ("GET", "/graph/neighbors/{entity_id}"),
            ("GET", "/graph/path"),
            ("GET", "/graph/explain"),
            ("GET", "/graph/impact/{entity_id}"),
        }
        for route in expected_graph_routes:
            self.assertIn(route, route_classification.ROUTE_CLASSIFICATION)
            self.assertEqual(route_classification.ROUTE_CLASSIFICATION[route], route_classification.USER)

    def test_route_count_includes_the_six_new_graph_routes(self):
        routes = self._classified_http_routes()
        self.assertEqual(len(set(routes)), route_classification.EXPECTED_ROUTE_COUNT)

    def test_no_classified_route_is_missing_from_app_routes_or_vice_versa(self):
        actual = set(self._classified_http_routes())
        classified = set(route_classification.ROUTE_CLASSIFICATION.keys())
        self.assertEqual(actual, classified)


class GraphRouteBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        self._original_user_account_store = server._user_account_store
        self._original_auth_session_store = server._auth_session_store
        self._original_user_contexts = server._user_contexts
        self._original_user_state_root = server._USER_STATE_ROOT

        server._user_account_store = UserAccountStore(
            storage_path=os.path.join(self.temp_dir.name, "user_accounts.json")
        )
        server._auth_session_store = AuthSessionStore(
            storage_path=os.path.join(self.temp_dir.name, "auth_sessions.json")
        )
        server._user_contexts = {}
        server._USER_STATE_ROOT = os.path.join(self.temp_dir.name, "users")

        edge.reset_rate_limiters()
        self.client = TestClient(server.app)

    def tearDown(self):
        server._user_account_store = self._original_user_account_store
        server._auth_session_store = self._original_auth_session_store
        server._user_contexts = self._original_user_contexts
        server._USER_STATE_ROOT = self._original_user_state_root
        edge.reset_rate_limiters()
        self.temp_dir.cleanup()

    def _signup(self, username, password="correct-horse-1"):
        response = self.client.post(
            "/auth/signup", json={"username": username, "password": password}
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def _add_memory_and_confirm(self, token, category="preference", content="likes concise replies"):
        add_response = self.client.post(
            "/memory", headers=self._auth(token), json={"category": category, "content": content}
        )
        self.assertEqual(add_response.status_code, 200, add_response.text)
        memory_id = add_response.json()["memory_id"]
        confirm_response = self.client.post(
            f"/memory/{memory_id}/confirm", headers=self._auth(token)
        )
        self.assertEqual(confirm_response.status_code, 200, confirm_response.text)
        return memory_id

    def test_confirming_memory_ingests_a_graph_node_for_that_user(self):
        alice = self._signup("graph-alice")
        self._add_memory_and_confirm(alice["token"])

        query_response = self.client.get(
            "/graph/query", headers=self._auth(alice["token"]), params={"entity_type": "Memory"}
        )
        self.assertEqual(query_response.status_code, 200, query_response.text)
        self.assertEqual(len(query_response.json()["entities"]), 1)

    def test_a_users_graph_query_never_returns_another_users_entities(self):
        alice = self._signup("graph-alice2")
        bob = self._signup("graph-bob2")

        self._add_memory_and_confirm(alice["token"], content="alice's own private preference")

        bob_query = self.client.get(
            "/graph/query", headers=self._auth(bob["token"]), params={"entity_type": "Memory"}
        )
        self.assertEqual(bob_query.status_code, 200)
        self.assertEqual(bob_query.json()["entities"], [])

    def test_a_user_cannot_fetch_another_users_entity_by_id(self):
        alice = self._signup("graph-alice3")
        bob = self._signup("graph-bob3")

        self._add_memory_and_confirm(alice["token"], content="alice's own private preference")
        alice_entities = self.client.get(
            "/graph/query", headers=self._auth(alice["token"]), params={"entity_type": "Memory"}
        ).json()["entities"]
        alice_entity_id = alice_entities[0]["entity_id"]

        cross_user_attempt = self.client.get(
            f"/graph/entities/{alice_entity_id}", headers=self._auth(bob["token"])
        )
        self.assertEqual(cross_user_attempt.status_code, 404)

        own_attempt = self.client.get(
            f"/graph/entities/{alice_entity_id}", headers=self._auth(alice["token"])
        )
        self.assertEqual(own_attempt.status_code, 200)

    def test_unknown_entity_id_is_404_not_500(self):
        alice = self._signup("graph-alice4")
        response = self.client.get(
            "/graph/entities/does-not-exist", headers=self._auth(alice["token"])
        )
        self.assertEqual(response.status_code, 404)

    def test_graph_path_returns_null_path_when_none_exists_not_an_error(self):
        alice = self._signup("graph-alice5")
        self._add_memory_and_confirm(alice["token"])
        entities = self.client.get(
            "/graph/query", headers=self._auth(alice["token"]), params={"entity_type": "Memory"}
        ).json()["entities"]
        memory_entity_id = entities[0]["entity_id"]

        response = self.client.get(
            "/graph/path",
            headers=self._auth(alice["token"]),
            params={"source_id": memory_entity_id, "target_id": "unrelated-unknown-id"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["path"])

    def test_graph_impact_route_returns_bounded_list(self):
        alice = self._signup("graph-alice6")
        entities = self.client.get(
            "/graph/query", headers=self._auth(alice["token"])
        ).json()["entities"]
        # No entities yet for a fresh user - impact on an unknown id is
        # an empty list, not an error.
        response = self.client.get(
            "/graph/impact/unknown-entity", headers=self._auth(alice["token"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["impact"], [])


if __name__ == "__main__":
    unittest.main()
