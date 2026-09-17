"""Focused M30.6A tests for shared Gmail connection truth."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from uri_core.core import connection_status, google_auth_common
from uri_core.services.gmail_service import GmailService


class LoadUsableCredentialsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.token_path = os.path.join(self.temp_dir.name, "token.json")
        self.scopes = ["https://www.googleapis.com/auth/gmail.readonly"]

    @patch("uri_core.core.google_auth_common.Credentials")
    def test_valid_token_returns_credentials(self, mock_credentials):
        Path(self.token_path).write_text("{}", encoding="utf-8")
        creds = MagicMock(valid=True)
        mock_credentials.from_authorized_user_file.return_value = creds

        self.assertIs(
            google_auth_common.load_usable_credentials(self.token_path, self.scopes),
            creds,
        )

    def test_missing_token_returns_none(self):
        self.assertIsNone(
            google_auth_common.load_usable_credentials(self.token_path, self.scopes)
        )

    @patch("uri_core.core.google_auth_common.Credentials")
    def test_invalid_token_returns_none(self, mock_credentials):
        Path(self.token_path).write_text("not-json", encoding="utf-8")
        mock_credentials.from_authorized_user_file.side_effect = ValueError("bad token")

        self.assertIsNone(
            google_auth_common.load_usable_credentials(self.token_path, self.scopes)
        )


class GmailServiceConnectionTruthTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.token_path = Path(self.temp_dir.name) / "token.json"

    def _service(self):
        service = GmailService()
        service.token_path = self.token_path
        return service

    @patch("uri_core.services.gmail_service.build")
    @patch("uri_core.services.gmail_service.load_usable_credentials")
    @patch("uri_core.services.gmail_service.InstalledAppFlow")
    def test_ensure_connected_from_token_never_starts_interactive_flow(
        self, mock_flow, mock_load, mock_build
    ):
        self.token_path.write_text("{}", encoding="utf-8")
        creds = MagicMock()
        creds.has_scopes.return_value = True
        mock_load.return_value = creds
        built_service = MagicMock()
        mock_build.return_value = built_service

        service = self._service()
        result = service.ensure_connected_from_token()

        self.assertEqual(result, {"connected": True, "reason": "connected"})
        self.assertIs(service.service, built_service)
        mock_flow.from_client_secrets_file.assert_not_called()

    @patch("uri_core.services.gmail_service.load_usable_credentials")
    def test_get_connection_status_probes_stored_token(self, mock_load):
        self.token_path.write_text("{}", encoding="utf-8")
        creds = MagicMock()
        creds.has_scopes.return_value = True
        mock_load.return_value = creds

        with patch("uri_core.services.gmail_service.build", return_value=MagicMock()):
            self.assertEqual(
                self._service().get_connection_status(),
                {"connected": True, "mode": "READ_ONLY"},
            )

    @patch("uri_core.services.gmail_service.load_usable_credentials")
    def test_missing_token_is_closed_set_failure_without_loading(self, mock_load):
        result = self._service().ensure_connected_from_token()

        self.assertEqual(result, {"connected": False, "reason": "no_token"})
        mock_load.assert_not_called()


class ConnectionStatusDelegationTests(unittest.TestCase):
    @patch("uri_core.core.connection_status.load_usable_credentials")
    def test_token_check_delegates_with_refresh(self, mock_load):
        """Live UX Repair §10: previously delegated with allow_refresh=
        False, contradicting _token_is_usable's own docstring and
        disagreeing with GmailSearchService (allow_refresh=True) about
        whether the exact same token.json was usable - a real,
        live-reproduced inconsistency between the Connections screen
        and Home's real Gmail data. A refresh is non-interactive (a
        server-to-Google token-endpoint call, never a consent screen),
        so there is no reason this status check should refuse to make
        it."""
        mock_load.return_value = MagicMock()
        scopes = ["scope"]

        self.assertTrue(connection_status._token_is_usable("token.json", scopes))
        mock_load.assert_called_once_with(
            token_path="token.json", scopes=scopes, allow_refresh=True
        )


if __name__ == "__main__":
    unittest.main()
