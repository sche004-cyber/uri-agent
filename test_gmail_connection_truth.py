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

    @patch("uri_core.core.google_auth_common.Request")
    @patch("uri_core.core.google_auth_common.Credentials")
    def test_successful_refresh_persists_credential_to_the_resolved_path(
        self, mock_credentials, mock_request
    ):
        """M32 D1: a successful refresh must be written back to disk so
        the NEXT load sees a still-valid token instead of refreshing
        again (docs/plans/M32_POST_BATCH_C_LATENCY_ARCHITECTURE_PLAN.md
        §2.2's measured root cause)."""
        Path(self.token_path).write_text("{}", encoding="utf-8")
        creds = MagicMock()
        creds.valid = False
        creds.expired = True
        creds.refresh_token = "real-refresh-token"
        creds.to_json.return_value = '{"refreshed": true, "token": "new-access-token"}'

        def _mark_valid(_request):
            creds.valid = True

        creds.refresh.side_effect = _mark_valid
        mock_credentials.from_authorized_user_file.return_value = creds

        result = google_auth_common.load_usable_credentials(self.token_path, self.scopes)

        self.assertIs(result, creds)
        creds.refresh.assert_called_once()
        persisted = Path(self.token_path).read_text(encoding="utf-8")
        self.assertEqual(persisted, '{"refreshed": true, "token": "new-access-token"}')

    @patch("uri_core.core.google_auth_common.Request")
    @patch("uri_core.core.google_auth_common.Credentials")
    def test_refresh_persistence_is_scoped_to_the_exact_resolved_path(
        self, mock_credentials, mock_request
    ):
        """Per-user isolation: persistence must write to exactly the
        path the caller resolved (already user-scoped upstream by
        resolve_google_token_path) and touch no other file - proves D1
        introduces no cross-user or global-state write."""
        other_users_token = os.path.join(self.temp_dir.name, "other_user_token.json")
        Path(other_users_token).write_text('{"untouched": true}', encoding="utf-8")
        Path(self.token_path).write_text("{}", encoding="utf-8")
        creds = MagicMock()
        creds.valid = False
        creds.expired = True
        creds.refresh_token = "real-refresh-token"
        creds.to_json.return_value = '{"this_users_token": true}'

        def _mark_valid(_request):
            creds.valid = True

        creds.refresh.side_effect = _mark_valid
        mock_credentials.from_authorized_user_file.return_value = creds

        google_auth_common.load_usable_credentials(self.token_path, self.scopes)

        self.assertEqual(
            Path(self.token_path).read_text(encoding="utf-8"), '{"this_users_token": true}'
        )
        self.assertEqual(
            Path(other_users_token).read_text(encoding="utf-8"), '{"untouched": true}'
        )

    @patch("uri_core.core.google_auth_common.Request")
    @patch("uri_core.core.google_auth_common.Credentials")
    def test_persist_failure_does_not_break_the_refresh_result(
        self, mock_credentials, mock_request
    ):
        """The persist step is best-effort only - a disk write failure
        must never turn an already-successful refresh into a failure."""
        Path(self.token_path).write_text("{}", encoding="utf-8")
        creds = MagicMock()
        creds.valid = False
        creds.expired = True
        creds.refresh_token = "real-refresh-token"
        creds.to_json.side_effect = RuntimeError("serialization blew up")

        def _mark_valid(_request):
            creds.valid = True

        creds.refresh.side_effect = _mark_valid
        mock_credentials.from_authorized_user_file.return_value = creds

        result = google_auth_common.load_usable_credentials(self.token_path, self.scopes)

        self.assertIs(result, creds)

    @patch("uri_core.core.google_auth_common.Request")
    @patch("uri_core.core.google_auth_common.Credentials")
    def test_second_load_after_persisted_refresh_does_not_refresh_again(
        self, mock_credentials, mock_request
    ):
        """End-to-end proof of the actual latency fix: once a refresh is
        persisted, reloading the same real (non-mocked) Credentials
        round trip through from_authorized_user_file/valid must not call
        .refresh() a second time."""
        from google.oauth2.credentials import Credentials as RealCredentials

        # Use the REAL Credentials class for this one test (only Request
        # is mocked) so from_authorized_user_file really re-parses the
        # persisted JSON, proving the round trip - not just proving a
        # mock was called with the right string.
        mock_credentials.side_effect = None
        with patch("uri_core.core.google_auth_common.Credentials", RealCredentials):
            token_payload = {
                "token": "old-access-token",
                "refresh_token": "real-refresh-token",
                "client_id": "client-id",
                "client_secret": "client-secret",
                "token_uri": "https://oauth2.googleapis.com/token",
                "scopes": self.scopes,
                "expiry": "2000-01-01T00:00:00Z",  # far in the past - always expired
            }
            import json as _json

            Path(self.token_path).write_text(_json.dumps(token_payload), encoding="utf-8")

            refresh_calls = {"n": 0}

            def _fake_refresh(creds_self, _request):
                # A plain function (not a MagicMock) so attribute lookup
                # on the instance still binds `self` correctly, exactly
                # like the real method it replaces. Simulates Google
                # issuing a fresh, far-future expiry.
                from datetime import datetime, timedelta

                refresh_calls["n"] += 1
                creds_self.token = "new-access-token"
                creds_self.expiry = datetime.utcnow() + timedelta(hours=1)

            with patch.object(RealCredentials, "refresh", new=_fake_refresh):
                first = google_auth_common.load_usable_credentials(self.token_path, self.scopes)
                self.assertIsNotNone(first)
                self.assertEqual(refresh_calls["n"], 1)

                second = google_auth_common.load_usable_credentials(self.token_path, self.scopes)
                self.assertIsNotNone(second)
                # The persisted token now has a future expiry - no second
                # refresh should have been needed.
                self.assertEqual(refresh_calls["n"], 1)


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
