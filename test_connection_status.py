"""Real external-service authorization state (Gmail/Drive) must be
reported from actual credential evidence, never assumed - and a status
query must never be able to trigger an interactive OAuth sign-in on the
server host. See uri_core/core/connection_status.py.
"""

import os
import tempfile
import unittest
from unittest.mock import patch

from uri_core.core import connection_status
from uri_core.core.connection_status import (
    STATUS_CONNECTED,
    STATUS_NEEDS_AUTHORIZATION,
    STATUS_NOT_CONNECTED,
    list_connection_status,
)


class ConnectionStatusTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        patcher = patch.object(
            connection_status, "_repo_root", return_value=self.temp_dir.name
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _write(self, name, content="{}"):
        path = os.path.join(self.temp_dir.name, name)
        with open(path, "w", encoding="utf-8") as file:
            file.write(content)
        return path

    def _status_for(self, service_id):
        for entry in list_connection_status():
            if entry["id"] == service_id:
                return entry
        self.fail(f"{service_id} missing from connection status")

    def test_no_credentials_reports_not_connected(self):
        gmail = self._status_for("gmail")

        self.assertEqual(gmail["status"], STATUS_NOT_CONNECTED)
        self.assertIn("credentials.json", gmail["detail"])

    def test_client_secret_without_token_reports_needs_authorization(self):
        self._write("credentials.json")

        gmail = self._status_for("gmail")

        self.assertEqual(gmail["status"], STATUS_NEEDS_AUTHORIZATION)
        self.assertIn("sign-in", gmail["detail"].lower())

    def test_usable_token_reports_connected(self):
        self._write("credentials.json")
        self._write("token.json")

        with patch.object(
            connection_status, "_token_is_usable", return_value=True
        ):
            gmail = self._status_for("gmail")

        self.assertEqual(gmail["status"], STATUS_CONNECTED)
        self.assertEqual(gmail["detail"], "Connected")

    def test_unparseable_token_is_not_reported_as_connected(self):
        self._write("credentials.json")
        self._write("token.json", content="not valid json{{{")

        gmail = self._status_for("gmail")

        self.assertNotEqual(gmail["status"], STATUS_CONNECTED)
        self.assertEqual(gmail["status"], STATUS_NEEDS_AUTHORIZATION)

    def test_every_known_service_is_reported(self):
        ids = {entry["id"] for entry in list_connection_status()}

        self.assertEqual(ids, {"gmail", "drive"})

    def test_status_query_never_starts_an_interactive_oauth_flow(self):
        # The whole point of this module: an HTTP status query must
        # never be able to open a consent browser on the server host.
        self._write("credentials.json")

        with patch(
            "google_auth_oauthlib.flow.InstalledAppFlow."
            "from_client_secrets_file"
        ) as flow:
            list_connection_status()

        flow.assert_not_called()


if __name__ == "__main__":
    unittest.main()
