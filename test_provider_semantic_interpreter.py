import json
import unittest

from uri_core.core.model_providers.base import ModelResponse
from uri_core.core.model_providers.ollama_provider import OllamaProvider
from uri_core.core.provider_semantic_interpreter import (
    ProviderSemanticInterpreter,
)

VALID_RESULT = {
    "goal": "Draft an institutional note.",
    "task_type": "noting",
    "domain": "administration",
    "entities": [],
    "requested_output": "noting",
    "requires_evidence": False,
    "requires_clarification": False,
    "suggested_next_step": "draft_output",
}


class _FakeProvider:
    """Minimal fake satisfying the ModelProvider duck-typed contract -
    no network, no Ollama, no real model call."""

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


class ProviderSemanticInterpreterConstructionTests(unittest.TestCase):

    def test_defaults_to_ollama_provider(self):
        interpreter = ProviderSemanticInterpreter()
        self.assertIsInstance(interpreter.provider, OllamaProvider)

    def test_accepts_injected_provider(self):
        fake = _FakeProvider(json.dumps(VALID_RESULT))
        interpreter = ProviderSemanticInterpreter(provider=fake)
        self.assertIs(interpreter.provider, fake)


class ProviderSemanticInterpreterBehaviorTests(unittest.TestCase):

    def test_interpret_parses_valid_json_response(self):
        fake = _FakeProvider(json.dumps(VALID_RESULT))
        interpreter = ProviderSemanticInterpreter(provider=fake)

        result = interpreter.interpret("draft a note")

        self.assertEqual(result, VALID_RESULT)
        self.assertEqual(fake.calls[0]["user"], "draft a note")

    def test_interpret_strips_markdown_code_fences(self):
        fenced = "```json\n" + json.dumps(VALID_RESULT) + "\n```"
        fake = _FakeProvider(fenced)
        interpreter = ProviderSemanticInterpreter(provider=fake)

        result = interpreter.interpret("draft a note")

        self.assertEqual(result, VALID_RESULT)

    def test_interpret_raises_on_missing_required_key(self):
        incomplete = dict(VALID_RESULT)
        del incomplete["suggested_next_step"]

        fake = _FakeProvider(json.dumps(incomplete))
        interpreter = ProviderSemanticInterpreter(provider=fake)

        with self.assertRaises(ValueError):
            interpreter.interpret("draft a note")

    def test_interpret_raises_on_truncated_json(self):
        # Regression guard for the real truncation bug found while
        # building this: a thinking-capable model can run out of token
        # budget mid-JSON. This must surface as a clear error, not be
        # silently swallowed.
        truncated = '{"goal": "Renew the policy", "task_type": "Admin'
        fake = _FakeProvider(truncated)
        interpreter = ProviderSemanticInterpreter(provider=fake)

        with self.assertRaises(json.JSONDecodeError):
            interpreter.interpret("draft a note")


if __name__ == "__main__":
    unittest.main()
