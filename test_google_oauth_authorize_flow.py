"""2026-09-12 (User directive): POST /connections/{id}/authorize must
actually start the Google OAuth consent flow (not just report what
would be required), while staying loopback-only and never launching a
real browser/network call during tests - GmailService.connect() is
mocked in every test here.
"""

import os
import tempfile
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


class GoogleAuthorizeFlowTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp()

        def _patched_usp(uid, fn, root=None):
            return os.path.join(cls._tmp, uid, fn)

        cls._usp_patch = patch(
            "uri_core.core.provider_registry.user_scoped_path",
            side_effect=_patched_usp,
        )
        cls._usp_patch.start()

        import uri_core.app.server as server_mod
        from uri_core.core.user_accounts import UserAccountStore
        from uri_core.core.auth_session import AuthSessionStore

        cls._server_mod = server_mod
        cls._orig_user_account_store = server_mod._user_account_store
        cls._orig_auth_session_store = server_mod._auth_session_store
        cls._orig_user_contexts = server_mod._user_contexts

        server_mod._user_account_store = UserAccountStore(
            storage_path=os.path.join(cls._tmp, "user_accounts.json")
        )
        server_mod._auth_session_store = AuthSessionStore(
            storage_path=os.path.join(cls._tmp, "auth_sessions.json")
        )
        server_mod._user_contexts = {}

        cls._client = TestClient(server_mod.app)

    @classmethod
    def tearDownClass(cls):
        cls._usp_patch.stop()
        cls._server_mod._user_account_store = cls._orig_user_account_store
        cls._server_mod._auth_session_store = cls._orig_auth_session_store
        cls._server_mod._user_contexts = cls._orig_user_contexts
        import shutil
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def setUp(self):
        from uri_core.app import edge
        edge.reset_rate_limiters()
        self._server_mod._google_auth_flow_state["running"] = False
        self._server_mod._google_auth_flow_state["last_error"] = None

    def _login(self, username: str) -> str:
        resp = self._client.post(
            "/auth/signup", json={"username": username, "password": "Password123!"}
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        return resp.json()["token"]

    def _headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    @patch("uri_core.app.server._repo_root_for_credentials")
    def test_no_credentials_reports_not_started(self, mock_root):
        mock_root.return_value = self._tmp  # empty dir - no credentials.json
        token = self._login("oauth_no_creds")

        resp = self._client.post(
            "/connections/gmail/authorize", headers=self._headers(token)
        )

        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["started"])
        self.assertIn("credentials.json", resp.json()["detail"])

    @patch("uri_core.services.gmail_service.GmailService.connect")
    @patch("uri_core.app.server._repo_root_for_credentials")
    def test_credentials_present_actually_starts_the_flow(
        self, mock_root, mock_connect
    ):
        mock_root.return_value = self._tmp
        with open(os.path.join(self._tmp, "credentials.json"), "w") as fh:
            fh.write("{}")
        mock_connect.return_value = {"success": True}

        token = self._login("oauth_starts")
        resp = self._client.post(
            "/connections/gmail/authorize", headers=self._headers(token)
        )

        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertTrue(resp.json()["started"])

        # The background thread should reach the mocked connect() call
        # promptly - poll briefly rather than sleeping a fixed guess.
        for _ in range(50):
            if mock_connect.called:
                break
            time.sleep(0.02)
        self.assertTrue(mock_connect.called)

        os.remove(os.path.join(self._tmp, "credentials.json"))

    @patch("uri_core.services.gmail_service.GmailService.connect")
    @patch("uri_core.app.server._repo_root_for_credentials")
    def test_a_second_call_while_one_is_running_is_refused(
        self, mock_root, mock_connect
    ):
        mock_root.return_value = self._tmp
        with open(os.path.join(self._tmp, "credentials.json"), "w") as fh:
            fh.write("{}")

        release = {"go": False}

        def _slow_connect():
            while not release["go"]:
                time.sleep(0.01)
            return {"success": True}

        mock_connect.side_effect = _slow_connect

        token = self._login("oauth_concurrent")
        first = self._client.post(
            "/connections/gmail/authorize", headers=self._headers(token)
        )
        self.assertTrue(first.json()["started"])

        second = self._client.post(
            "/connections/gmail/authorize", headers=self._headers(token)
        )
        self.assertFalse(second.json()["started"])
        self.assertIn("already in progress", second.json()["detail"])

        release["go"] = True
        for _ in range(50):
            if not self._server_mod._google_auth_flow_state["running"]:
                break
            time.sleep(0.02)

        os.remove(os.path.join(self._tmp, "credentials.json"))


if __name__ == "__main__":
    unittest.main()
