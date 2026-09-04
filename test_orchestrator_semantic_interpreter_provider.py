import os
import unittest
from unittest.mock import patch

from uri_core.core.orchestrator import UriOrchestrator
from uri_core.core.provider_semantic_interpreter import (
    ProviderSemanticInterpreter,
)


class OrchestratorDefaultsToProviderSemanticInterpreterTests(
    unittest.TestCase
):

    def test_construction_without_groq_api_key_does_not_raise(self):
        env_without_key = dict(os.environ)
        env_without_key.pop("GROQ_API_KEY", None)

        with patch.dict(os.environ, env_without_key, clear=True):
            orchestrator = UriOrchestrator()

        self.assertIsInstance(
            orchestrator.semantic_interpreter,
            ProviderSemanticInterpreter,
        )

    def test_injected_semantic_interpreter_is_used_instead_of_default(self):
        sentinel = object()

        orchestrator = UriOrchestrator(semantic_interpreter=sentinel)

        self.assertIs(orchestrator.semantic_interpreter, sentinel)


if __name__ == "__main__":
    unittest.main()
