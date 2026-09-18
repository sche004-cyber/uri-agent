"""M32 Batch C, C1: provider-level native tool calling - unit tests.

Additive-only: every existing (system, user)-only call path is untouched
(covered by the still-green test_ollama_provider.py etc.); these tests
cover only the new `tools=`/`ModelResponse.tool_calls` surface, mocked at
the HTTP boundary (no real network), matching this repository's own
existing convention for provider tests.
"""

import unittest
from unittest.mock import MagicMock, patch

from uri_core.core.model_providers.base import ModelProviderConfig, ToolCall
from uri_core.core.model_providers.ollama_provider import OllamaProvider
from uri_core.core.model_providers.anthropic_provider import AnthropicProvider
from uri_core.core.model_providers.openai_compatible_provider import OpenAICompatibleProvider


SAMPLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "gmail_search",
            "description": "Search Gmail messages.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    }
]


class OllamaToolCallingTests(unittest.TestCase):
    def _config(self):
        return ModelProviderConfig(base_url="http://localhost:11434", model="gemma4:12b", timeout_seconds=5.0)

    @patch("requests.post")
    def test_tools_included_in_payload_when_supplied(self, mock_post):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"model": "gemma4:12b", "message": {"role": "assistant", "content": "ok"}}
        mock_post.return_value = response

        provider = OllamaProvider(config=self._config())
        provider.complete(system="s", user="u", tools=SAMPLE_TOOLS)

        sent_payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(sent_payload["tools"], SAMPLE_TOOLS)

    @patch("requests.post")
    def test_no_tools_key_when_tools_omitted(self, mock_post):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"model": "gemma4:12b", "message": {"role": "assistant", "content": "ok"}}
        mock_post.return_value = response

        provider = OllamaProvider(config=self._config())
        provider.complete(system="s", user="u")

        sent_payload = mock_post.call_args.kwargs["json"]
        self.assertNotIn("tools", sent_payload)

    @patch("requests.post")
    def test_tool_calls_parsed_from_real_ollama_shape(self, mock_post):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "model": "gemma4:12b",
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "gmail_search", "arguments": {"query": "invoice"}}}
                ],
            },
        }
        mock_post.return_value = response

        provider = OllamaProvider(config=self._config())
        result = provider.complete(system="s", user="u", tools=SAMPLE_TOOLS)

        self.assertEqual(len(result.tool_calls), 1)
        self.assertEqual(result.tool_calls[0].name, "gmail_search")
        self.assertEqual(result.tool_calls[0].arguments, {"query": "invoice"})
        self.assertTrue(result.tool_calls[0].id)

    @patch("requests.post")
    def test_empty_tuple_when_tools_offered_but_none_called(self, mock_post):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"model": "gemma4:12b", "message": {"role": "assistant", "content": "hi there"}}
        mock_post.return_value = response

        provider = OllamaProvider(config=self._config())
        result = provider.complete(system="s", user="u", tools=SAMPLE_TOOLS)

        self.assertEqual(result.tool_calls, ())

    @patch("requests.post")
    def test_none_when_tools_not_offered_at_all(self, mock_post):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"model": "gemma4:12b", "message": {"role": "assistant", "content": "hi"}}
        mock_post.return_value = response

        provider = OllamaProvider(config=self._config())
        result = provider.complete(system="s", user="u")

        self.assertIsNone(result.tool_calls)

    @patch("requests.post")
    def test_malformed_tool_call_entries_are_skipped_not_fatal(self, mock_post):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "model": "gemma4:12b",
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "gmail_search", "arguments": {"query": "invoice"}}},
                    {"not_a_function_key": True},
                    {"function": {"arguments": {"query": "no name"}}},
                ],
            },
        }
        mock_post.return_value = response

        provider = OllamaProvider(config=self._config())
        result = provider.complete(system="s", user="u", tools=SAMPLE_TOOLS)

        self.assertEqual(len(result.tool_calls), 1)
        self.assertEqual(result.tool_calls[0].name, "gmail_search")


class AnthropicToolCallingTests(unittest.TestCase):
    def _config(self):
        return ModelProviderConfig(base_url="https://api.anthropic.com", model="claude-3-5-sonnet", timeout_seconds=5.0)

    @patch("requests.post")
    def test_openai_shape_tools_translated_to_anthropic_native_shape(self, mock_post):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "model": "claude-3-5-sonnet-20241022",
            "content": [{"type": "text", "text": "ok"}],
        }
        mock_post.return_value = response

        provider = AnthropicProvider(config=self._config(), api_key="k")
        provider.complete(system="s", user="u", tools=SAMPLE_TOOLS)

        sent_payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(
            sent_payload["tools"],
            [{"name": "gmail_search", "description": "Search Gmail messages.",
              "input_schema": SAMPLE_TOOLS[0]["function"]["parameters"]}],
        )

    @patch("requests.post")
    def test_tool_use_only_response_does_not_crash_and_yields_empty_content(self, mock_post):
        # The bug this repairs: content[0]["text"] assumed the first block
        # was always text - a tool-only reply (no text block at all) would
        # have raised ProviderResponseError before this fix.
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "model": "claude-3-5-sonnet-20241022",
            "content": [
                {"type": "tool_use", "id": "toolu_1", "name": "gmail_search", "input": {"query": "invoice"}}
            ],
        }
        mock_post.return_value = response

        provider = AnthropicProvider(config=self._config(), api_key="k")
        result = provider.complete(system="s", user="u", tools=SAMPLE_TOOLS)

        self.assertEqual(result.content, "")
        self.assertEqual(len(result.tool_calls), 1)
        self.assertEqual(result.tool_calls[0].name, "gmail_search")
        self.assertEqual(result.tool_calls[0].arguments, {"query": "invoice"})
        self.assertEqual(result.tool_calls[0].id, "toolu_1")

    @patch("requests.post")
    def test_mixed_text_and_tool_use_blocks(self, mock_post):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "model": "claude-3-5-sonnet-20241022",
            "content": [
                {"type": "text", "text": "Let me check that."},
                {"type": "tool_use", "id": "toolu_2", "name": "gmail_search", "input": {"query": "x"}},
            ],
        }
        mock_post.return_value = response

        provider = AnthropicProvider(config=self._config(), api_key="k")
        result = provider.complete(system="s", user="u", tools=SAMPLE_TOOLS)

        self.assertEqual(result.content, "Let me check that.")
        self.assertEqual(len(result.tool_calls), 1)

    @patch("requests.post")
    def test_text_only_response_unaffected_when_no_tools_offered(self, mock_post):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "model": "claude-3-5-sonnet-20241022",
            "content": [{"type": "text", "text": "hello"}],
        }
        mock_post.return_value = response

        provider = AnthropicProvider(config=self._config(), api_key="k")
        result = provider.complete(system="s", user="u")

        self.assertEqual(result.content, "hello")
        self.assertIsNone(result.tool_calls)


class OpenAICompatibleToolCallingTests(unittest.TestCase):
    def _config(self):
        return ModelProviderConfig(base_url="https://api.openai.com/v1", model="gpt-4o", timeout_seconds=5.0)

    @patch("requests.post")
    def test_tools_passed_through_verbatim(self, mock_post):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "model": "gpt-4o",
            "choices": [{"message": {"role": "assistant", "content": "ok"}}],
        }
        mock_post.return_value = response

        provider = OpenAICompatibleProvider(config=self._config(), api_key="k")
        provider.complete(system="s", user="u", tools=SAMPLE_TOOLS)

        sent_payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(sent_payload["tools"], SAMPLE_TOOLS)

    @patch("requests.post")
    def test_json_string_arguments_are_decoded(self, mock_post):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "model": "gpt-4o",
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_1",
                        "function": {"name": "gmail_search", "arguments": "{\"query\": \"invoice\"}"},
                    }],
                }
            }],
        }
        mock_post.return_value = response

        provider = OpenAICompatibleProvider(config=self._config(), api_key="k")
        result = provider.complete(system="s", user="u", tools=SAMPLE_TOOLS)

        self.assertEqual(result.content, "")
        self.assertEqual(len(result.tool_calls), 1)
        self.assertEqual(result.tool_calls[0].name, "gmail_search")
        self.assertEqual(result.tool_calls[0].arguments, {"query": "invoice"})
        self.assertEqual(result.tool_calls[0].id, "call_1")

    @patch("requests.post")
    def test_malformed_json_arguments_do_not_crash_the_whole_batch(self, mock_post):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "model": "gpt-4o",
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {"id": "call_1", "function": {"name": "gmail_search", "arguments": "{not valid json"}},
                        {"id": "call_2", "function": {"name": "recall_memory", "arguments": "{}"}},
                    ],
                }
            }],
        }
        mock_post.return_value = response

        provider = OpenAICompatibleProvider(config=self._config(), api_key="k")
        result = provider.complete(system="s", user="u", tools=SAMPLE_TOOLS)

        self.assertEqual(len(result.tool_calls), 2)
        self.assertEqual(result.tool_calls[0].arguments, {})
        self.assertEqual(result.tool_calls[1].name, "recall_memory")

    @patch("requests.post")
    def test_none_when_tools_not_offered(self, mock_post):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "model": "gpt-4o",
            "choices": [{"message": {"role": "assistant", "content": "hello"}}],
        }
        mock_post.return_value = response

        provider = OpenAICompatibleProvider(config=self._config(), api_key="k")
        result = provider.complete(system="s", user="u")

        self.assertIsNone(result.tool_calls)


if __name__ == "__main__":
    unittest.main()
