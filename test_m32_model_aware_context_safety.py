"""M32 Batch A2: Model-Aware Context Safety and Budgeting Tests.

Covers:
1. Large-context model (gemma4:12b 262,144 tokens, gpt-4o 128,000 tokens)
2. Small-context model (artificially small window raises ContextWindowExceededError)
3. Protected system/policy content (system_policy, soul, and instructions survive 100% intact)
4. Oversized conversation (conversation trimmed oldest-first to fit budget, newest preserved)
5. Tool definitions (available_capabilities bounded/capped so verbose descriptions do not overflow)
6. Safe failure/compaction behavior (compaction succeeds when optional context is trimmable; fails honestly when not)
7. Provider metadata unavailable/fallback case (safely defaults to DEFAULT_CONTEXT_TOKENS = 8192)
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from uri_core.config.model_roles import ROLE_REASONING, build_provider
from uri_core.core.context_budget import estimate_tokens
from uri_core.core.context_trimmer import (
    estimate_request_tokens,
    trim_reasoning_request,
)
from uri_core.core.model_providers.base import (
    DEFAULT_CONTEXT_TOKENS,
    ContextWindowExceededError,
    ModelProviderConfig,
    ModelResponse,
)
from uri_core.core.model_providers.ollama_provider import (
    OllamaProvider,
    probe_model_max_context,
    resolve_model_context_tokens,
)
from uri_core.core.model_reasoning_adapter import OllamaReasoningAdapter
from uri_core.core.model_reasoning_gateway import ModelReasoningGateway


class _RecordingProvider:
    """Captures transmitted prompt payloads without making network requests."""

    def __init__(self, config=None, response_content="{}"):
        self.config = config or ModelProviderConfig(context_tokens=40960)
        self.response_content = response_content
        self.recorded_calls = []

    def complete(self, *, system, user, temperature=0.0, max_tokens=None):
        self.recorded_calls.append(
            {
                "system": system,
                "user": user,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        return ModelResponse(
            content=self.response_content,
            model=self.config.model,
            provider="fake",
        )


class LargeContextModelTests(unittest.TestCase):
    """Tests that large-context models adopt their real context window without
    stale 8192 token truncation."""

    def test_gemma4_12b_resolves_to_262k_tokens(self):
        ctx = resolve_model_context_tokens(model="gemma4:12b")
        self.assertEqual(ctx, 262144)

    def test_qwen3_14b_resolves_to_40k_tokens(self):
        ctx = resolve_model_context_tokens(model="qwen3:14b")
        self.assertEqual(ctx, 40960)

    def test_live_probe_overrides_catalogue_if_different(self):
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {
            "models": [
                {
                    "name": "custom:model",
                    "details": {"context_length": 65536},
                }
            ]
        }
        with patch("requests.get", return_value=fake_response):
            val = probe_model_max_context(model="custom:model")
            self.assertEqual(val, 65536)

            ctx = resolve_model_context_tokens(model="custom:model")
            self.assertEqual(ctx, 65536)


class SmallContextModelSafetyTests(unittest.TestCase):
    """Tests safe failure when a model's context window is genuinely too small
    to accommodate protected non-negotiable policy and identity sections."""

    def test_artificially_small_window_raises_context_window_exceeded(self):
        gateway = ModelReasoningGateway()
        # Baseline policy alone is ~2,400 tokens (~9,500 chars).
        # A tiny 1,000-token window cannot safely hold it + 800 headroom.
        request = gateway.build_reasoning_request(
            user_text="Schedule a meeting",
        )

        with self.assertRaises(ContextWindowExceededError) as ctx_err:
            trim_reasoning_request(
                request,
                context_tokens=1000,
                max_tokens_headroom=800,
                model_name="small-model:1b",
            )

        err = ctx_err.exception
        self.assertEqual(err.model, "small-model:1b")
        self.assertEqual(err.context_tokens, 1000)
        self.assertIn("Non-negotiable system policy", str(err))

    def test_gateway_reason_handles_small_window_safely_and_honestly(self):
        tiny_provider = OllamaProvider(
            config=ModelProviderConfig(context_tokens=500, model="tiny:1b")
        )
        adapter = OllamaReasoningAdapter(provider=tiny_provider)
        gateway = ModelReasoningGateway(model_callable=adapter)

        result = gateway.reason(user_text="Do something")
        self.assertEqual(result["status"], "context_window_exceeded")
        self.assertIn("exceeds configured context window", result["error"])
        self.assertEqual(result["model"], "tiny:1b")
        self.assertIsNone(result["proposal"])


class ProtectedContentPreservationTests(unittest.TestCase):
    """Verifies that system_policy, soul, and identity NEVER suffer truncation
    when trimming is performed."""

    def test_policy_and_soul_preserved_byte_for_byte_under_trimming(self):
        gateway = ModelReasoningGateway()
        policy = gateway.load_policy()
        soul = gateway.load_soul()

        # Build an oversized request packed with 20,000 tokens of trimmable evidence
        oversized_evidence = {f"item_{i}": "x" * 2000 for i in range(25)}
        request = gateway.build_reasoning_request(
            user_text="Analyze these records",
            evidence_context=oversized_evidence,
            query_context={"soul": soul, "identity": "URI Assistant"},
        )

        # Trim request against an 8,192 token window with 800 token headroom
        trimmed = trim_reasoning_request(
            request,
            context_tokens=8192,
            max_tokens_headroom=800,
            model_name="qwen3:14b",
        )

        # 1. system_policy must be byte-for-byte identical to original
        self.assertEqual(trimmed["system_policy"], policy)

        # 2. soul and identity in query_context must be untouched
        self.assertEqual(trimmed["query_context"]["soul"], soul)
        self.assertEqual(trimmed["query_context"]["identity"], "URI Assistant")

        # 3. user_request must be untouched
        self.assertEqual(trimmed["user_request"], "Analyze these records")

        # 4. Total request tokens must now fit within allowed headroom
        total_tokens = estimate_request_tokens(trimmed)
        self.assertLessEqual(total_tokens, 8192 - 800)


class OversizedConversationTrimmingTests(unittest.TestCase):
    """Verifies that an oversized conversation window is trimmed oldest-first,
    preserving the most recent turns."""

    def test_older_conversation_turns_pruned_before_recent_turns(self):
        turns = [
            {"user": f"User turn {i}: " + "z" * 200, "uri": f"URI turn {i}: " + "w" * 200}
            for i in range(40)
        ]
        gateway = ModelReasoningGateway()
        request = gateway.build_reasoning_request(
            user_text="What did we discuss last?",
            query_context={"conversation": turns},
        )

        trimmed = trim_reasoning_request(
            request,
            context_tokens=8192,
            max_tokens_headroom=800,
        )

        trimmed_conv = trimmed["query_context"]["conversation"]
        self.assertLess(len(trimmed_conv), len(turns))
        # Newest turn (turn 39) MUST be preserved
        self.assertEqual(trimmed_conv[-1]["user"], turns[-1]["user"])
        # Oldest turns (turn 0, 1, 2) should have been pruned
        self.assertNotIn(turns[0], trimmed_conv)


class ToolDefinitionsCatalogueSafetyTests(unittest.TestCase):
    """Verifies that available_capabilities catalogue is safely bounded
    without dropping capability names or usability metadata."""

    def test_tool_descriptions_capped_without_losing_names(self):
        gateway = ModelReasoningGateway()
        request = gateway.build_reasoning_request(user_text="List capabilities")

        # Artificially expand descriptions in catalogue
        catalogue = request["available_capabilities"]
        for item in catalogue:
            item["description"] = "A very long description that goes on and on " * 30

        trimmed = trim_reasoning_request(
            request,
            context_tokens=8192,
            max_tokens_headroom=800,
        )

        trimmed_caps = trimmed["available_capabilities"]
        self.assertEqual(len(trimmed_caps), len(catalogue))
        for original, bounded in zip(catalogue, trimmed_caps):
            self.assertEqual(original["name"], bounded["name"])
            self.assertEqual(original["usable"], bounded["usable"])
            self.assertLessEqual(len(bounded["description"]), 200)


class ProviderMetadataFallbackTests(unittest.TestCase):
    """Tests fallback behavior when model metadata is unavailable."""

    def test_unknown_model_offline_falls_back_to_8192(self):
        with patch.dict("os.environ", {"OLLAMA_MODEL": "unknown-nonexistent-model"}, clear=True):
            with patch("uri_core.core.model_providers.ollama_provider.probe_model_max_context", return_value=None):
                ctx = resolve_model_context_tokens(model="unknown-nonexistent-model")
                self.assertEqual(ctx, DEFAULT_CONTEXT_TOKENS)
                self.assertEqual(ctx, 8192)

    def test_explicit_env_override_always_wins(self):
        with patch.dict("os.environ", {"OLLAMA_NUM_CTX": "12345"}):
            ctx = resolve_model_context_tokens(model="gemma4:12b")
            self.assertEqual(ctx, 12345)


class EndToEndModelReasoningAdapterCompactionTests(unittest.TestCase):
    """Tests end-to-end integration between OllamaReasoningAdapter and context trimming."""

    def test_adapter_trims_oversized_payload_and_preserves_policy_in_system(self):
        provider = _RecordingProvider(
            config=ModelProviderConfig(context_tokens=8192, model="qwen3:14b"),
            response_content='{"action": null}',
        )
        adapter = OllamaReasoningAdapter(provider=provider)
        gateway = ModelReasoningGateway(model_callable=adapter)

        # Huge evidence
        huge_evidence = {f"file_{i}": "data " * 500 for i in range(30)}
        result = gateway.reason(
            user_text="Summarize",
            evidence_context=huge_evidence,
        )

        self.assertEqual(result["status"], "proposal_ready")
        self.assertEqual(len(provider.recorded_calls), 1)
        sent = provider.recorded_calls[0]

        # Check that system prompt has full policy
        self.assertIn("URI_AI_OPERATING_POLICY", sent["system"])
        # Check that total transmitted prompt + headroom does not exceed 8192
        transmitted_tokens = estimate_tokens(sent["system"]) + estimate_tokens(sent["user"])
        self.assertLessEqual(transmitted_tokens + 800, 8192)
