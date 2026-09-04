"""Real integration tests for the model-reasoning shadow against a
locally running Ollama server. Deliberately does NOT mock Ollama - see
test_ollama_provider_live.py for the same pattern used in the previous
milestone. Skips (rather than fails) when Ollama isn't reachable.
"""

import os
import unittest
import uuid

import requests

from uri_core.core.model_providers.base import ModelProviderConfig
from uri_core.core.model_providers.ollama_provider import OllamaProvider
from uri_core.core.model_reasoning_adapter import OllamaReasoningAdapter
from uri_core.core.model_reasoning_gateway import ModelReasoningGateway
from uri_core.core.orchestrator import UriOrchestrator


def _ollama_reachable(base_url: str) -> bool:
    try:
        response = requests.get(f"{base_url}/api/version", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


class OllamaReasoningAdapterLiveTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = ModelProviderConfig.from_env()

        if not _ollama_reachable(cls.config.base_url):
            raise unittest.SkipTest(
                f"Ollama is not reachable at {cls.config.base_url} - "
                "skipping the real reasoning-shadow integration test."
            )

    def test_real_gateway_reasoning_produces_a_valid_or_rejected_proposal(
        self,
    ):
        # No mocking of Ollama: real HTTP call, real qwen3:14b, through
        # the real, unmodified ModelReasoningGateway.reason() pipeline
        # (build request -> call model -> parse -> validate).
        adapter = OllamaReasoningAdapter(provider=OllamaProvider(config=self.config))
        gateway = ModelReasoningGateway(model_callable=adapter)

        result = gateway.reason(
            user_text=(
                "Please renew the group medical insurance policy for "
                "students before it expires."
            )
        )

        self.assertIn(
            result["status"],
            ("proposal_ready", "model_proposal_rejected"),
        )

        # Whatever the model proposed as an action, if anything, must
        # be a real registered capability or nothing - never something
        # made up. This is ModelReasoningGateway's own validation
        # (unmodified) doing its job, checked here against a genuine
        # live model response rather than a hand-written fixture.
        proposal = result.get("proposal") or {}
        action = proposal.get("action")

        if result["status"] == "proposal_ready" and action:
            self.assertIn(
                action["capability"],
                gateway.registered_capability_names(),
            )

    def test_real_orchestrator_shadow_stays_observational(self):
        # A fresh session_id every run - see test_ollama_provider_live.py
        # for why (SessionManager persists workflow state to disk).
        session_id = f"reasoning-shadow-live-{uuid.uuid4()}"
        session_file = os.path.join(
            "uri_workspace", "sessions", f"{session_id}.json"
        )

        try:
            gateway = ModelReasoningGateway(
                model_callable=OllamaReasoningAdapter(
                    provider=OllamaProvider(config=self.config)
                )
            )
            orchestrator = UriOrchestrator(model_reasoning_gateway=gateway)

            result = orchestrator.process_user_input(
                session_id,
                "Please renew the group medical insurance policy for "
                "students before it expires.",
            )

            self.assertEqual(result["status"], "success")
            self.assertEqual(
                result["model_reasoning"]["status"], "shadow_completed"
            )

            # The shadow ran for real, but the actual execution path
            # (plan/workflow/execution) is still whatever the
            # deterministic runtime produced - completely independent
            # of what the shadow proposed.
            self.assertIn("execution", result)
        finally:
            if os.path.exists(session_file):
                os.remove(session_file)

    def test_ollama_unavailable_produces_controlled_shadow_failure(self):
        # Real networking code, pointed at a port nothing is listening
        # on - proves unavailability is handled cleanly rather than
        # breaking the deterministic path, without mocking Ollama's
        # HTTP layer itself.
        unreachable_config = ModelProviderConfig(
            base_url="http://localhost:19999", timeout_seconds=2
        )
        gateway = ModelReasoningGateway(
            model_callable=OllamaReasoningAdapter(
                provider=OllamaProvider(config=unreachable_config)
            )
        )
        orchestrator = UriOrchestrator(model_reasoning_gateway=gateway)

        session_id = f"reasoning-shadow-unavailable-{uuid.uuid4()}"
        session_file = os.path.join(
            "uri_workspace", "sessions", f"{session_id}.json"
        )

        try:
            result = orchestrator.process_user_input(
                session_id,
                "Please renew the group medical insurance policy for "
                "students before it expires.",
            )

            self.assertEqual(result["status"], "success")
            self.assertEqual(
                result["model_reasoning"]["status"], "shadow_failed"
            )
        finally:
            if os.path.exists(session_file):
                os.remove(session_file)


if __name__ == "__main__":
    unittest.main()
