"""2026-09-12 (User directive): GmailSearchService must read the SAME
token.json every other Google-connected class uses (previously an
independent token.pickle, invisible to a connection the User actually
completed via Settings > Connections), and must support a real unread
count, not only a capped keyword search."""

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from uri_core.services.gmail_search_service import GmailSearchService
from uri_core.tools.gmail_search import GmailSearchTool


def _fake_token_json(path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "token": "fake-access-token",
                "refresh_token": "fake-refresh-token",
                "client_id": "fake-client-id",
                "client_secret": "fake-client-secret",
                "token_uri": "https://oauth2.googleapis.com/token",
                "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
            },
            fh,
        )


class GmailSearchServiceAuthTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.token_path = os.path.join(self.temp_dir.name, "token.json")

    def test_no_token_file_is_honest_not_an_interactive_flow(self):
        service = GmailSearchService(token_path=self.token_path)
        self.assertFalse(service.authenticate())

    @patch("uri_core.services.gmail_search_service.build")
    @patch("uri_core.services.gmail_search_service.Credentials")
    def test_reads_the_same_json_token_gmailservice_writes(
        self, mock_credentials_cls, mock_build
    ):
        _fake_token_json(self.token_path)
        mock_creds = MagicMock(valid=True)
        mock_credentials_cls.from_authorized_user_file.return_value = mock_creds

        service = GmailSearchService(token_path=self.token_path)
        ok = service.authenticate()

        self.assertTrue(ok)
        mock_credentials_cls.from_authorized_user_file.assert_called_once()
        # The path passed must be the real token.json path, never a
        # pickle file.
        called_path = mock_credentials_cls.from_authorized_user_file.call_args[0][0]
        self.assertEqual(called_path, self.token_path)

    def test_get_unread_count_reports_real_label_count(self):
        service = GmailSearchService(token_path=self.token_path)
        service.service = MagicMock()
        service.service.users.return_value.labels.return_value.get.return_value.execute.return_value = {
            "messagesUnread": 7
        }

        result = service.get_unread_count()

        self.assertEqual(result, {"success": True, "unread_count": 7})

    def test_get_unread_count_honest_when_not_authenticated(self):
        service = GmailSearchService(token_path=self.token_path)
        result = service.get_unread_count()
        self.assertFalse(result["success"])


class GmailSearchToolUnreadRoutingTests(unittest.TestCase):

    def test_how_many_unread_routes_to_count_not_keyword_search(self):
        fake_service = MagicMock()
        fake_service.get_unread_count.return_value = {
            "success": True,
            "unread_count": 3,
        }
        tool = GmailSearchTool(service=fake_service)

        result = tool.execute(request_text="how many unread messages do I have right now")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["unread_count"], 3)
        self.assertIn("3 unread", result["message"])
        fake_service.search_emails.assert_not_called()

    def test_an_ordinary_search_request_is_unaffected(self):
        fake_service = MagicMock()
        fake_service.authenticate.return_value = True
        fake_service.search_emails.return_value = [
            {"subject": "Seminar", "date": "today", "snippet": "..."}
        ]
        tool = GmailSearchTool(service=fake_service)

        result = tool.execute(request_text="find my email about the seminar")

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["results"]), 1)
        fake_service.get_unread_count.assert_not_called()


if __name__ == "__main__":
    unittest.main()
