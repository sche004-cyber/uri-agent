"""GET /connections must report the REAL authorization state of
external services, so the client can stop showing a hardcoded
"Connected" badge. Read-only and informational, exactly like
GET /capabilities - see uri_core/core/connection_status.py.
"""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from uri_core.app import server


class ServerConnectionsEndpointTests(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(server.app)

    def test_returns_a_connections_section(self):
        response = self.client.get("/connections")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("connections", body)
        self.assertIsInstance(body["connections"], list)

    def test_every_entry_carries_the_client_display_contract(self):
        body = self.client.get("/connections").json()

        for entry in body["connections"]:
            for field in ("id", "name", "description", "status", "detail"):
                self.assertIn(field, entry)

    def test_real_state_is_relayed_verbatim_not_reinterpreted(self):
        with patch.object(
            server,
            "list_connection_status",
            return_value=[
                {
                    "id": "gmail",
                    "name": "Gmail",
                    "description": "Read messages.",
                    "status": "needs_authorization",
                    "detail": "Sign-in not completed.",
                }
            ],
        ):
            body = self.client.get("/connections").json()

        self.assertEqual(len(body["connections"]), 1)
        self.assertEqual(
            body["connections"][0]["status"], "needs_authorization"
        )
        self.assertEqual(
            body["connections"][0]["detail"], "Sign-in not completed."
        )

    def test_endpoint_never_claims_connected_without_real_credentials(self):
        # 2026-09-12: pinned to a directory with no credentials.json/
        # token.json, rather than assuming the real repo root has
        # none - it can genuinely have both once Google sign-in has
        # actually been completed on this machine (a real, working
        # outcome, not a test-environment leak).
        import tempfile

        with patch(
            "uri_core.core.connection_status._repo_root",
            return_value=tempfile.mkdtemp(),
        ):
            body = self.client.get("/connections").json()

        statuses = {entry["status"] for entry in body["connections"]}
        self.assertNotIn("connected", statuses)


if __name__ == "__main__":
    unittest.main()
