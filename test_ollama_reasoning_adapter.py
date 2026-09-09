import json
import unittest

from uri_core.core.model_providers.base import ModelResponse
from uri_core.core.model_providers.ollama_provider import OllamaProvider
from uri_core.core.model_reasoning_adapter import (
    REASONING_SYSTEM_PROMPT,
    OllamaReasoningAdapter,
)
from uri_core.core.model_reasoning_gateway import ModelReasoningGateway


class _FakeProvider:
    """No network, no Ollama - records what it was called with and
    returns a fixed ModelResponse."""

    def __init__(self, content):
        self.content = content
        self.calls = []

    def complete(self, *, system, user, temperature=0.0, max_tokens=None):
        self.calls.append(
            {
                "system": system,
                "user": user,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        return ModelResponse(content=self.content, model="fake-model", provider="fake")


class OllamaReasoningAdapterConstructionTests(unittest.TestCase):

    def test_defaults_to_ollama_provider(self):
        adapter = OllamaReasoningAdapter()
        self.assertIsInstance(adapter.provider, OllamaProvider)

    def test_accepts_injected_provider(self):
        fake = _FakeProvider("{}")
        adapter = OllamaReasoningAdapter(provider=fake)
        self.assertIs(adapter.provider, fake)


class OllamaReasoningAdapterCallableContractTests(unittest.TestCase):
    """OllamaReasoningAdapter must satisfy exactly the
    Callable[[str], Any] contract ModelReasoningGateway.model_callable
    expects, without ModelReasoningGateway itself changing at all."""

    def test_call_passes_request_json_as_user_message(self):
        fake = _FakeProvider('{"action": null}')
        adapter = OllamaReasoningAdapter(provider=fake)

        request_json = json.dumps({"user_request": "draft a note"})
        result = adapter(request_json)

        self.assertEqual(result, '{"action": null}')
        self.assertEqual(fake.calls[0]["user"], request_json)
        self.assertEqual(fake.calls[0]["system"], REASONING_SYSTEM_PROMPT)
        self.assertEqual(fake.calls[0]["temperature"], 0)

    def test_gateway_accepts_adapter_as_model_callable_unmodified(self):
        # Proves the adapter is a drop-in for model_callable without any
        # change to ModelReasoningGateway itself: a valid proposal from
        # the fake-backed adapter passes the gateway's own unmodified
        # parse_model_response + validate_proposal pipeline.
        valid_proposal = json.dumps(
            {
                "intent": {"objective": "draft a note"},
                "facts": [],
                "clarification": None,
                "action": None,
                "workflow": None,
            }
        )
        fake = _FakeProvider(valid_proposal)
        adapter = OllamaReasoningAdapter(provider=fake)

        gateway = ModelReasoningGateway(model_callable=adapter)

        result = gateway.reason(user_text="draft a note")

        self.assertEqual(result["status"], "proposal_ready")
        self.assertTrue(result["validation"]["valid"])

    def test_system_policy_moves_to_system_role_and_is_not_duplicated(self):
        # M21: system_policy is static within a session; keeping it out of
        # the variable `user` payload lets Ollama reuse its prompt prefix
        # across repeated calls instead of resending ~9.5k identical
        # characters every time.
        fake = _FakeProvider('{"action": null}')
        adapter = OllamaReasoningAdapter(provider=fake)

        request = {
            "system_policy": "OPERATING POLICY TEXT",
            "user_request": "draft a note",
        }
        result = adapter(json.dumps(request))

        self.assertEqual(result, '{"action": null}')
        sent = fake.calls[0]
        self.assertIn("OPERATING POLICY TEXT", sent["system"])
        self.assertIn(REASONING_SYSTEM_PROMPT, sent["system"])
        self.assertNotIn("OPERATING POLICY TEXT", sent["user"])

        # The key stays present (contract shape unchanged) with its
        # content moved, not lost.
        transmitted = json.loads(sent["user"])
        self.assertIn("system_policy", transmitted)
        self.assertEqual(transmitted["system_policy"], "")
        self.assertEqual(transmitted["user_request"], "draft a note")

    def test_request_with_no_system_policy_is_transmitted_unchanged(self):
        fake = _FakeProvider('{"action": null}')
        adapter = OllamaReasoningAdapter(provider=fake)

        request_json = json.dumps({"user_request": "draft a note"})
        adapter(request_json)

        sent = fake.calls[0]
        self.assertEqual(sent["system"], REASONING_SYSTEM_PROMPT)
        self.assertEqual(sent["user"], request_json)

    def test_gateway_rejects_hallucinated_capability_from_adapter(self):
        # The adapter has no authority to make a bad proposal stick -
        # ModelReasoningGateway.validate_proposal() (unmodified) still
        # rejects a capability name that isn't registered.
        proposal_with_fake_capability = json.dumps(
            {
                "action": {"capability": "definitely_not_a_real_capability"},
            }
        )
        fake = _FakeProvider(proposal_with_fake_capability)
        adapter = OllamaReasoningAdapter(provider=fake)

        gateway = ModelReasoningGateway(
            model_callable=adapter,
            registry_path="uri_workspace/capabilities_registry.json",
        )

        result = gateway.reason(user_text="draft a note")

        self.assertEqual(result["status"], "model_proposal_rejected")
        self.assertFalse(result["validation"]["valid"])


if __name__ == "__main__":
    unittest.main()
