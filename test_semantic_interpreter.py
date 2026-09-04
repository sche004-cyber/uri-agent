import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from uri_core.core.semantic_interpreter import SemanticInterpreter


def _make_response(content):

    message = SimpleNamespace(content=content)

    choice = SimpleNamespace(message=message)

    return SimpleNamespace(choices=[choice])


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


class SemanticInterpreterConstructionTests(unittest.TestCase):

    def test_construction_without_api_key_does_not_raise(self):

        env_without_key = dict(os.environ)

        env_without_key.pop("GROQ_API_KEY", None)

        with patch.dict(os.environ, env_without_key, clear=True):

            interpreter = SemanticInterpreter()

        self.assertIsNone(interpreter.client)

    def test_injected_client_is_stored_and_not_replaced(self):

        fake_client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kwargs: _make_response(
                        json.dumps(VALID_RESULT)
                    )
                )
            )
        )

        interpreter = SemanticInterpreter(client=fake_client)

        self.assertIs(interpreter.client, fake_client)

        interpreter.interpret("draft a note")

        self.assertIs(interpreter.client, fake_client)

    @patch("uri_core.core.semantic_interpreter.Groq")
    def test_lazy_client_is_built_from_env_only_when_needed(
        self, mock_groq_cls
    ):

        mock_instance = mock_groq_cls.return_value

        mock_instance.chat.completions.create.return_value = (
            _make_response(json.dumps(VALID_RESULT))
        )

        with patch.dict(
            os.environ, {"GROQ_API_KEY": "test-key"}
        ):

            interpreter = SemanticInterpreter()

            # Constructing must not touch Groq at all.
            mock_groq_cls.assert_not_called()

            self.assertIsNone(interpreter.client)

            interpreter.interpret("draft a note")

        mock_groq_cls.assert_called_once_with(api_key="test-key")

        self.assertIs(interpreter.client, mock_instance)


class SemanticInterpreterBehaviorTests(unittest.TestCase):
    """
    Existing interpret() behavior, exercised through an injected
    fake client so no network access or API key is required.
    """

    def _interpreter_with_response(self, content):

        fake_client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kwargs: _make_response(content)
                )
            )
        )

        return SemanticInterpreter(client=fake_client)

    def test_interpret_parses_valid_json_response(self):

        interpreter = self._interpreter_with_response(
            json.dumps(VALID_RESULT)
        )

        result = interpreter.interpret("draft a note")

        self.assertEqual(result, VALID_RESULT)

    def test_interpret_strips_markdown_code_fences(self):

        fenced_content = (
            "```json\n" + json.dumps(VALID_RESULT) + "\n```"
        )

        interpreter = self._interpreter_with_response(fenced_content)

        result = interpreter.interpret("draft a note")

        self.assertEqual(result, VALID_RESULT)

    def test_interpret_raises_on_missing_required_key(self):

        incomplete_result = dict(VALID_RESULT)

        del incomplete_result["suggested_next_step"]

        interpreter = self._interpreter_with_response(
            json.dumps(incomplete_result)
        )

        with self.assertRaises(ValueError):

            interpreter.interpret("draft a note")


if __name__ == "__main__":
    unittest.main()
