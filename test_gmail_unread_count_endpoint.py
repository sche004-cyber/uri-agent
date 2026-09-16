"""HTTP boundary coverage for the dashboard's real unread-count read."""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from uri_core.app.server import app


class GmailUnreadCountEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("uri_core.services.gmail_search_service.GmailSearchService")
    def test_returns_the_service_count_from_a_real_http_request(self, service_class):
        service_class.return_value.get_unread_count.return_value = {
            "success": True,
            "unread_count": 7,
        }

        response = self.client.get("/gmail/unread-count")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True, "unread_count": 7})
        service_class.return_value.get_unread_count.assert_called_once_with()

    @patch("uri_core.services.gmail_search_service.GmailSearchService")
    def test_preserves_the_service_error_shape(self, service_class):
        service_class.return_value.get_unread_count.return_value = {
            "success": False,
            "error": "Gmail authentication failed",
        }

        response = self.client.get("/gmail/unread-count")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"success": False, "error": "Gmail authentication failed"},
        )
        service_class.return_value.get_unread_count.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
