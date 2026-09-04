import os
import unittest
from unittest.mock import patch

from uri_core.services.hermes_service import HermesService


class HermesServiceCredentialTests(unittest.TestCase):
    """
    Verifies HermesService sources credentials only from
    GROQ_API_KEY / GEMINI_API_KEY, with no hardcoded fallback.

    Both SDK clients are mocked so no real network call or real
    credential is ever involved; the test env-var values below are
    arbitrary placeholders, not real secrets.
    """

    @patch("uri_core.services.hermes_service.genai")
    @patch("uri_core.services.hermes_service.OpenAI")
    def test_credentials_are_read_from_environment(
        self, mock_openai_cls, mock_genai
    ):

        with patch.dict(
            os.environ,
            {
                "GROQ_API_KEY": "placeholder-groq-value",
                "GEMINI_API_KEY": "placeholder-gemini-value",
            },
        ):

            service = HermesService()

        self.assertEqual(
            service.groq_api_key, "placeholder-groq-value"
        )

        self.assertEqual(
            service.gemini_api_key, "placeholder-gemini-value"
        )

        mock_openai_cls.assert_called_once_with(
            base_url="https://api.groq.com/openai/v1",
            api_key="placeholder-groq-value",
        )

        mock_genai.Client.assert_called_once_with(
            api_key="placeholder-gemini-value"
        )

    @patch("uri_core.services.hermes_service.genai")
    @patch("uri_core.services.hermes_service.OpenAI")
    def test_missing_credentials_are_not_silently_replaced(
        self, mock_openai_cls, mock_genai
    ):

        env_without_keys = dict(os.environ)

        env_without_keys.pop("GROQ_API_KEY", None)

        env_without_keys.pop("GEMINI_API_KEY", None)

        with patch.dict(os.environ, env_without_keys, clear=True):

            service = HermesService()

        self.assertIsNone(service.groq_api_key)

        self.assertIsNone(service.gemini_api_key)

        mock_openai_cls.assert_called_once_with(
            base_url="https://api.groq.com/openai/v1",
            api_key=None,
        )

        mock_genai.Client.assert_called_once_with(api_key=None)


class CheckModelsScriptCredentialTests(unittest.TestCase):
    """
    Static source checks for check_models.py. The script performs a
    real network call at import time, so it is checked by inspecting
    its source rather than importing/executing it.
    """

    def setUp(self):

        with open(
            "check_models.py", "r", encoding="utf-8"
        ) as file:

            self.source = file.read()

    def test_no_hardcoded_groq_key_literal(self):

        self.assertNotIn('"gsk_', self.source)

    def test_credential_is_read_from_environment(self):

        self.assertIn(
            'os.environ.get("GROQ_API_KEY")', self.source
        )


if __name__ == "__main__":
    unittest.main()
