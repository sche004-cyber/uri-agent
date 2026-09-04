"""Real integration test against a locally running Ollama server.

Deliberately does NOT mock Ollama - this is the one test that proves
OllamaProvider actually talks to a real Ollama process over HTTP and
gets a real completion back from a real model. It skips (rather than
fails) when Ollama isn't reachable, so the rest of the suite stays
runnable in environments without a local Ollama - but does not skip
silently: the skip reason is printed.
"""

import json
import os
import unittest
import uuid

import requests

from uri_core.core.model_providers.base import ModelProviderConfig
from uri_core.core.model_providers.ollama_provider import OllamaProvider
from uri_core.core.orchestrator import UriOrchestrator


def _ollama_reachable(base_url: str) -> bool:
    try:
        response = requests.get(f"{base_url}/api/version", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


class OllamaProviderLiveTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = ModelProviderConfig.from_env()

        if not _ollama_reachable(cls.config.base_url):
            raise unittest.SkipTest(
                f"Ollama is not reachable at {cls.config.base_url} - "
                "skipping the real integration test. Start Ollama and "
                "pull the configured model to run this."
            )

    def test_real_completion_from_configured_model(self):
        provider = OllamaProvider(config=self.config)

        response = provider.complete(
            system="Reply with exactly the JSON object: {\"ok\": true}",
            user="respond now",
            temperature=0,
        )

        self.assertEqual(response.provider, "ollama")
        self.assertEqual(response.model, self.config.model)

        parsed = json.loads(response.content.strip())
        self.assertEqual(parsed, {"ok": True})

    def test_real_orchestrator_call_succeeds_without_groq(self):
        # A fresh session_id every run - SessionManager persists workflow
        # state to uri_workspace/sessions/<session_id>.json, so reusing a
        # fixed id across runs resumes a stale paused workflow instead of
        # exercising a real first turn.
        session_id = f"ollama-live-integration-test-{uuid.uuid4()}"
        session_file = os.path.join(
            "uri_workspace", "sessions", f"{session_id}.json"
        )

        try:
            orchestrator = UriOrchestrator()

            result = orchestrator.process_user_input(
                session_id,
                "Please renew the group medical insurance policy for "
                "students before it expires.",
            )

            self.assertEqual(result["status"], "success")
            self.assertIn("semantic_analysis", result)
            self.assertIn("goal", result["semantic_analysis"])
        finally:
            if os.path.exists(session_file):
                os.remove(session_file)


if __name__ == "__main__":
    unittest.main()
