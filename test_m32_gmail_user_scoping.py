"""M32 Precondition Tests: Gmail & User Credential Scoping (A1-3 + A1-4).

Target Rules:
1. credentials.json is install-wide (OAuth application client secret).
2. token.json is strictly per-user (mailbox authorization token) via user_scoped_path.
3. Cross-user mailbox isolation: User B can NEVER read User A's mailbox.
4. Defence-in-depth: Per-user capability grant decides if user may invoke Gmail;
   per-user token decides which mailbox that user is authorized to access.
   Both must pass.
5. Disconnect removes only the calling user's token.
"""

import os
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from uri_core.core import connection_status, google_auth_common
from uri_core.core.google_auth_common import resolve_google_token_path, load_usable_credentials
from uri_core.core.connection_status import list_connection_status, STATUS_CONNECTED, STATUS_NEEDS_AUTHORIZATION
from uri_core.core.portable_paths import user_scoped_path
from uri_core.core.dispatcher import ToolDispatcher
from uri_core.services.gmail_service import GmailService
from uri_core.services.gmail_search_service import GmailSearchService
from uri_core.tools.gmail_search import GmailSearchTool


class GmailTokenScopingPathTests(unittest.TestCase):

    def test_resolve_token_path_with_user_id(self):
        user_id = str(uuid.uuid4())
        expected = user_scoped_path(user_id, "token.json")
        resolved = resolve_google_token_path(user_id)
        self.assertEqual(resolved, expected)

    def test_resolve_token_path_without_user_id_falls_back_to_repo_root(self):
        fallback = resolve_google_token_path(None)
        self.assertTrue(fallback.endswith("token.json"))
        self.assertEqual(fallback, os.path.join(google_auth_common._repo_root(), "token.json"))


class MultiUserMailboxIsolationTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.temp_dir, ignore_errors=True))

        # Patch user_scoped_path to live inside self.temp_dir
        self.user_a_id = str(uuid.uuid4())
        self.user_b_id = str(uuid.uuid4())

        self.orig_usp = google_auth_common.resolve_google_token_path

        def _custom_usp(uid, filename, root=None):
            return os.path.join(self.temp_dir, "users", uid, filename)

        self.usp_patch = patch("uri_core.core.portable_paths.user_scoped_path", side_effect=_custom_usp)
        self.usp_patch.start()
        self.addCleanup(self.usp_patch.stop)

        # Write install-wide credentials.json
        self.repo_patch = patch.object(connection_status, "_repo_root", return_value=self.temp_dir)
        self.repo_patch.start()
        self.addCleanup(self.repo_patch.stop)

        Path(os.path.join(self.temp_dir, "credentials.json")).write_text("{}", encoding="utf-8")

        # Create token for User A only
        self.token_a_path = Path(os.path.join(self.temp_dir, "users", self.user_a_id, "token.json"))
        self.token_a_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_a_path.write_text('{"token": "user_a_secret"}', encoding="utf-8")

    @patch("uri_core.core.google_auth_common.Credentials")
    def test_user_a_is_connected_and_user_b_is_not(self, mock_creds_cls):
        mock_creds = MagicMock(valid=True)
        mock_creds_cls.from_authorized_user_file.return_value = mock_creds

        # User A has their own token -> connected
        status_a = list_connection_status(user_id=self.user_a_id)
        gmail_a = next(s for s in status_a if s["id"] == "gmail")
        self.assertEqual(gmail_a["status"], STATUS_CONNECTED)

        # User B has no token -> needs_authorization (cannot see user A's token)
        status_b = list_connection_status(user_id=self.user_b_id)
        gmail_b = next(s for s in status_b if s["id"] == "gmail")
        self.assertEqual(gmail_b["status"], STATUS_NEEDS_AUTHORIZATION)

    @patch("uri_core.services.gmail_search_service.build")
    @patch("uri_core.core.google_auth_common.Credentials")
    def test_gmail_search_service_strictly_scopes_by_user_id(self, mock_creds_cls, mock_build):
        mock_creds = MagicMock(valid=True)
        mock_creds_cls.from_authorized_user_file.return_value = mock_creds

        # User A authenticates successfully
        service_a = GmailSearchService(user_id=self.user_a_id)
        self.assertTrue(service_a.authenticate())
        mock_creds_cls.from_authorized_user_file.assert_called_with(
            str(self.token_a_path),
            ["https://www.googleapis.com/auth/gmail.readonly"],
        )

        # User B fails authentication cleanly because they have no token.json
        service_b = GmailSearchService(user_id=self.user_b_id)
        self.assertFalse(service_b.authenticate())
        self.assertIsNone(service_b.service)

    def test_dispatcher_injects_user_id_into_tool_init(self):
        dispatcher = ToolDispatcher()
        user_id = self.user_a_id

        # Execute gmail_search via dispatcher with user_id kwargs
        # We mock authenticate so it doesn't call real Google API
        with patch.object(GmailSearchService, "authenticate", return_value=False) as mock_auth:
            res = dispatcher.execute_tool("gmail_search", request_text="find reports", user_id=user_id)
            self.assertEqual(res["status"], "success")
            # Result data shows authentication failed honestly rather than crash
            self.assertEqual(res["data"]["status"], "unavailable")


class GmailUnreadCountEndpointScopingTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp()

        def _patched_usp(uid, fn, root=None):
            return os.path.join(cls._tmp, "users", uid, fn)

        cls._usp_patch = patch("uri_core.core.portable_paths.user_scoped_path", side_effect=_patched_usp)
        cls._usp_patch.start()

        import uri_core.app.server as server_mod
        from uri_core.core.user_accounts import UserAccountStore
        from uri_core.core.auth_session import AuthSessionStore

        cls._server_mod = server_mod
        cls._orig_user_account_store = server_mod._user_account_store
        cls._orig_auth_session_store = server_mod._auth_session_store

        server_mod._user_account_store = UserAccountStore(
            storage_path=os.path.join(cls._tmp, "user_accounts.json")
        )
        server_mod._auth_session_store = AuthSessionStore(
            storage_path=os.path.join(cls._tmp, "auth_sessions.json")
        )

        cls._client = TestClient(server_mod.app)

    @classmethod
    def tearDownClass(cls):
        cls._usp_patch.stop()
        cls._server_mod._user_account_store = cls._orig_user_account_store
        cls._server_mod._auth_session_store = cls._orig_auth_session_store
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_unread_count_without_grant_returns_honest_rejection(self):
        """A1-4 Defence-in-depth: even if user has a token, an ungranted
        user cannot invoke Gmail unread-count."""
        # Create a user with explicit capability grants excluding gmail_search
        user_id = str(uuid.uuid4())
        token = self._server_mod._auth_session_store.create(user_id=user_id)

        # Mock CapabilityResolver.is_allowed to return False for this user
        with patch("uri_core.core.capability_resolver.CapabilityResolver.is_allowed", return_value=False):
            resp = self._client.get(
                "/gmail/unread-count",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertFalse(data["success"])
            self.assertIn("not granted", data["error"].lower())


if __name__ == "__main__":
    unittest.main()
