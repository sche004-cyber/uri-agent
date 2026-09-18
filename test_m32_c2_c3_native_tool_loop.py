"""M32 Batch C, C2 (Tier 0) + C3 (Tier 1 native tool loop) - unit tests.

Model-free where possible, following this repository's own standing
convention (test_canonical_execution.py's own docstring): a fake,
injectable `model_callable` deterministically drives each scenario; a
handful of tests in this file use a real, local Ollama model where the
scenario specifically needs genuine model reasoning (marked as such).
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from uri_core.capabilities import MultiActionCapabilityRegistry
from uri_core.capabilities.gmail import GmailCapability
from uri_core.core.approval_gate import ApprovalGate
from uri_core.core.capability_registry import CapabilityRegistry
from uri_core.core.dispatcher import ToolDispatcher
from uri_core.core.model_providers.base import ModelResponse, ToolCall
from uri_core.core.multi_action_dispatch import MultiActionDispatch
from uri_core.core.native_tool_loop import (
    DEFAULT_MAX_ITERATIONS,
    TOOL_LOOP_ENV_VAR,
    native_tool_loop_enabled,
    run_native_tool_loop,
)
from uri_core.core.state import SessionManager
from uri_core.core.user_memory import MemoryStore
from test_multi_action_capabilities import FakeGmailService


def _write_registry(path, extra_tools=None):
    tools = {
        "remember_fact": {
            "file_path": "uri_core/tools/remember_fact.py",
            "class_name": "RememberFactTool",
            "method": "remember",
            "description": "test",
            "status": "implemented",
            "availability": "available",
            "permissions": [],
            "approval_requirement": "none",
            "risk": "controlled",
            "effect_type": "local_write",
        },
    }
    if extra_tools:
        tools.update(extra_tools)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"active_tools": tools}, handle)


class _Fixture:
    """A real (not mocked) orchestrator-shaped object: real SessionManager,
    real CapabilityRegistry backed by a temp registry.json, real
    ApprovalGate + ToolDispatcher, real MultiActionDispatch wired to a
    FakeGmailService (connected) - mirrors test_canonical_execution.py's
    own fixture discipline (real collaborators, no execution mocked)."""

    def __init__(self, connected_gmail=True):
        self.tmp_dir = tempfile.mkdtemp()
        self.registry_path = os.path.join(self.tmp_dir, "registry.json")
        _write_registry(self.registry_path)

        self.capability_registry = CapabilityRegistry(registry_path=self.registry_path)
        dispatcher = ToolDispatcher(registry_path=self.registry_path)
        self.approval_gate = ApprovalGate(dispatcher=dispatcher)

        gmail_registry = MultiActionCapabilityRegistry(
            [GmailCapability(FakeGmailService(connected=connected_gmail))]
        )
        self.multi_action_dispatch = MultiActionDispatch(
            registry=gmail_registry, capability_registry=self.capability_registry,
            permission_checker=lambda *_: True,
        )
        self.session_manager = SessionManager(storage_path=os.path.join(self.tmp_dir, "sessions"))

    def orchestrator(self):
        return SimpleNamespace(
            session_manager=self.session_manager,
            capability_registry=self.capability_registry,
            multi_action_dispatch=self.multi_action_dispatch,
            approval_gate=self.approval_gate,
            conversation_history=None,
        )


def _response(content="", tool_calls=()):
    return ModelResponse(content=content, model="fake", provider="fake", tool_calls=tool_calls)


class ToggleTests(unittest.TestCase):
    def test_off_by_default(self):
        os.environ.pop(TOOL_LOOP_ENV_VAR, None)
        self.assertFalse(native_tool_loop_enabled())

    def test_on_when_explicitly_set(self):
        os.environ[TOOL_LOOP_ENV_VAR] = "1"
        self.addCleanup(lambda: os.environ.pop(TOOL_LOOP_ENV_VAR, None))
        self.assertTrue(native_tool_loop_enabled())


class Tier0Tests(unittest.TestCase):
    def test_no_tool_calls_on_first_iteration_is_tier0(self):
        fixture = _Fixture()
        calls = []

        def fake_model(**kwargs):
            calls.append(kwargs)
            return _response(content="Hi! How can I help?", tool_calls=())

        result = run_native_tool_loop(
            orchestrator=fixture.orchestrator(), session_id="s1", user_text="hi",
            principal=None, model_callable=fake_model,
        )

        self.assertEqual(result["tier"], "tier0")
        self.assertEqual(result["narrative"], "Hi! How can I help?")
        self.assertEqual(result["response"]["message"], "Hi! How can I help?")
        self.assertEqual(len(calls), 1)
        # Tier 0 selection is the Brain's own choice - tools were offered.
        self.assertTrue(calls[0]["tools"])

    def test_tier0_content_is_the_reply_with_no_second_drafting_call(self):
        call_count = {"n": 0}

        def fake_model(**kwargs):
            call_count["n"] += 1
            return _response(content="Direct answer.", tool_calls=())

        fixture = _Fixture()
        run_native_tool_loop(
            orchestrator=fixture.orchestrator(), session_id="s1", user_text="what is 2+2",
            principal=None, model_callable=fake_model,
        )
        self.assertEqual(call_count["n"], 1)


class Tier1SingleActionTests(unittest.TestCase):
    def test_remember_fact_tool_call_executes_and_continues(self):
        fixture = _Fixture()
        responses = iter([
            _response(tool_calls=(ToolCall(id="c1", name="remember_fact", arguments={"request_text": "I work at NIT Sikkim."}),)),
            _response(content="Got it, I've saved that.", tool_calls=()),
        ])

        def fake_model(**kwargs):
            return next(responses)

        result = run_native_tool_loop(
            orchestrator=fixture.orchestrator(), session_id="s1", user_text="Remember that I work at NIT Sikkim.",
            principal=None, model_callable=fake_model,
        )

        self.assertEqual(result["tier"], "tier1_continuation")
        self.assertEqual(result["narrative"], "Got it, I've saved that.")
        branch = result["execution"]["branch_results"][0]
        self.assertEqual(branch["capability"], "remember_fact")
        self.assertEqual(branch["status"], "success")

    def test_unknown_tool_name_is_never_dispatched_and_loop_continues(self):
        fixture = _Fixture()
        responses = iter([
            _response(tool_calls=(ToolCall(id="c1", name="delete_everything", arguments={}),)),
            _response(content="I can't do that, but I can help another way.", tool_calls=()),
        ])

        def fake_model(**kwargs):
            return next(responses)

        result = run_native_tool_loop(
            orchestrator=fixture.orchestrator(), session_id="s1", user_text="delete everything",
            principal=None, model_callable=fake_model,
        )
        self.assertEqual(result["tier"], "tier1_continuation")
        self.assertEqual(result["execution"]["branch_results"][0]["status"], "translation_error")


class Tier1BranchPreservationTests(unittest.TestCase):
    def test_gmail_search_and_read_message_both_execute_independently(self):
        fixture = _Fixture(connected_gmail=True)
        responses = iter([
            _response(tool_calls=(
                ToolCall(id="c1", name="gmail_search_messages", arguments={"query": "invoice"}),
                ToolCall(id="c2", name="gmail_read_message", arguments={"message_id": "m-1"}),
            )),
            _response(content="Here's what I found.", tool_calls=()),
        ])

        def fake_model(**kwargs):
            return next(responses)

        result = run_native_tool_loop(
            orchestrator=fixture.orchestrator(), session_id="s1", user_text="search and list labels",
            principal=None, model_callable=fake_model,
        )
        branches = result["execution"]["branch_results"]
        self.assertEqual(len(branches), 2)
        self.assertTrue(all(b["status"] == "success" for b in branches))

    def test_approval_required_branch_does_not_block_sibling_branch(self):
        # Same Brain response proposes a safe read (search_messages) AND
        # an approval-required write (create_draft) against the same
        # capability - C3.8: the approval-required one must not prevent
        # the safe one from executing.
        fixture = _Fixture(connected_gmail=True)
        responses = iter([
            _response(tool_calls=(
                ToolCall(id="c1", name="gmail_search_messages", arguments={"query": "invoice"}),
                ToolCall(id="c2", name="gmail_create_draft", arguments={"to": "a@b.com", "subject": "s", "body": "b"}),
            )),
            _response(content="Draft needs your approval; here's what I found.", tool_calls=()),
        ])

        def fake_model(**kwargs):
            return next(responses)

        result = run_native_tool_loop(
            orchestrator=fixture.orchestrator(), session_id="s1", user_text="search and draft an email",
            principal=None, model_callable=fake_model,
        )
        branches = {b["action"]: b for b in result["execution"]["branch_results"]}
        self.assertEqual(branches["search_messages"]["status"], "success")
        self.assertEqual(branches["create_draft"]["status"], "not_executed")
        self.assertEqual(branches["create_draft"]["gate_outcome"], "APPROVAL_REQUIRED")

    def test_disconnected_gmail_reports_honest_failure_never_fabricated_success(self):
        fixture = _Fixture(connected_gmail=False)
        responses = iter([
            _response(tool_calls=(ToolCall(id="c1", name="gmail_search_messages", arguments={"query": "x"}),)),
            _response(content="Gmail isn't connected right now.", tool_calls=()),
        ])

        def fake_model(**kwargs):
            return next(responses)

        result = run_native_tool_loop(
            orchestrator=fixture.orchestrator(), session_id="s1", user_text="search gmail",
            principal=None, model_callable=fake_model,
        )
        branch = result["execution"]["branch_results"][0]
        self.assertEqual(branch["status"], "not_executed")
        self.assertIn(branch["gate_outcome"], {"DISCONNECTED", "UNAVAILABLE"})


class Tier1IdempotencyTests(unittest.TestCase):
    def test_duplicate_non_read_only_call_in_same_turn_is_not_re_dispatched(self):
        fixture = _Fixture()
        responses = iter([
            _response(tool_calls=(ToolCall(id="c1", name="remember_fact", arguments={"request_text": "x"}),)),
            _response(tool_calls=(ToolCall(id="c2", name="remember_fact", arguments={"request_text": "x"}),)),
            _response(content="Done.", tool_calls=()),
        ])

        def fake_model(**kwargs):
            return next(responses)

        result = run_native_tool_loop(
            orchestrator=fixture.orchestrator(), session_id="s1", user_text="remember x twice by mistake",
            principal=None, model_callable=fake_model, max_iterations=3,
        )
        branches = result["execution"]["branch_results"]
        statuses = [b["status"] for b in branches]
        self.assertIn("success", statuses)
        self.assertIn("skipped_duplicate", statuses)


class Tier1LoopBoundTests(unittest.TestCase):
    def test_loop_bound_is_reported_honestly_never_silently_truncated(self):
        fixture = _Fixture()

        def always_calls_a_tool(**kwargs):
            return _response(tool_calls=(ToolCall(id="c1", name="remember_fact", arguments={"request_text": "loop"}),))

        result = run_native_tool_loop(
            orchestrator=fixture.orchestrator(), session_id="s1", user_text="loop forever",
            principal=None, model_callable=always_calls_a_tool, max_iterations=2,
        )
        self.assertEqual(result["tier"], "tier1_bounded")
        self.assertEqual(result["execution"]["status"], "iteration_limit_reached")
        # Real evidence from both iterations is preserved, not discarded.
        self.assertEqual(len(result["execution"]["branch_results"]), 2)

    def test_default_bound_matches_legacy_max_brain_iterations(self):
        self.assertEqual(DEFAULT_MAX_ITERATIONS, 3)


class ModelProviderUnreachableTests(unittest.TestCase):
    def test_provider_failure_is_honest_not_fabricated(self):
        fixture = _Fixture()

        def failing_model(**kwargs):
            raise RuntimeError("model provider unreachable")

        result = run_native_tool_loop(
            orchestrator=fixture.orchestrator(), session_id="s1", user_text="hi",
            principal=None, model_callable=failing_model,
        )
        self.assertEqual(result["status"], "unavailable")
        self.assertIn("model provider unreachable", result["error"])


class C34ParallelSafetyTests(unittest.TestCase):
    """C3.4 (R4/SR-1): the exact safety property the frozen plan blocked
    parallel execution on until a real classification existed - only
    read-only + approval-free calls may ever run concurrently; anything
    else is strictly serial, and no two non-read-only calls may ever be
    scheduled at the same time as each other."""

    def _fixture_with_extra_tools(self):
        fixture = _Fixture()
        extra = {
            "system_performance": {
                "file_path": "uri_core/tools/system_performance.py", "class_name": "SystemPerformanceTool",
                "method": "report", "description": "t", "status": "implemented", "availability": "available",
                "permissions": [], "approval_requirement": "none", "risk": "controlled", "effect_type": "read_only",
            },
            "recall_memory": {
                "file_path": "uri_core/tools/recall_memory.py", "class_name": "RecallMemoryTool",
                "method": "recall", "description": "t", "status": "implemented", "availability": "available",
                "permissions": [], "approval_requirement": "none", "risk": "controlled", "effect_type": "read_only",
            },
            "web_search": {
                "file_path": "uri_core/tools/web_search.py", "class_name": "WebSearchTool",
                "method": "execute", "description": "t", "status": "implemented", "availability": "available",
                "permissions": [], "approval_requirement": "none", "risk": "controlled", "effect_type": "read_only",
            },
        }
        _write_registry(fixture.registry_path, extra_tools=extra)
        fixture.capability_registry = CapabilityRegistry(registry_path=fixture.registry_path)
        return fixture

    def test_read_only_and_approval_free_correctly_classifies_legacy_tools(self):
        from uri_core.core.native_tool_loop import _legacy_effect_map, _read_only_and_approval_free

        fixture = self._fixture_with_extra_tools()
        descriptors = _legacy_effect_map(fixture.capability_registry)
        self.assertTrue(
            _read_only_and_approval_free(
                "system_performance", "system_performance",
                legacy_descriptors=descriptors, directory_describe=lambda _id: None,
            )
        )
        self.assertFalse(
            _read_only_and_approval_free(
                "remember_fact", "remember_fact",
                legacy_descriptors=descriptors, directory_describe=lambda _id: None,
            )
        )

    def test_read_only_and_approval_free_correctly_classifies_gmail_actions(self):
        from uri_core.core.native_tool_loop import _legacy_effect_map, _read_only_and_approval_free

        fixture = self._fixture_with_extra_tools()
        descriptors = _legacy_effect_map(fixture.capability_registry)
        gmail_schema = {
            "action_schemas": {
                "search_messages": {"read_only": True, "approval_requirement": "none"},
                "create_draft": {"read_only": False, "approval_requirement": "user_approval_required"},
            }
        }
        self.assertTrue(
            _read_only_and_approval_free(
                "Gmail", "search_messages",
                legacy_descriptors=descriptors, directory_describe=lambda _id: gmail_schema,
            )
        )
        self.assertFalse(
            _read_only_and_approval_free(
                "Gmail", "create_draft",
                legacy_descriptors=descriptors, directory_describe=lambda _id: gmail_schema,
            )
        )

    def test_eligible_read_only_batch_executes_concurrently_not_serially(self):
        import time as _time

        fixture = self._fixture_with_extra_tools()
        responses = iter([
            _response(tool_calls=(
                ToolCall(id="c1", name="system_performance", arguments={}),
                ToolCall(id="c2", name="recall_memory", arguments={}),
                ToolCall(id="c3", name="web_search", arguments={"request_text": "x"}),
            )),
            _response(content="done", tool_calls=()),
        ])

        def fake_model(**kwargs):
            return next(responses)

        SLEEP = 0.15

        def slow_branch(**kwargs):
            _time.sleep(SLEEP)
            return {"tool_call_id": kwargs["tool_call_id"], "capability": kwargs["capability_id"],
                    "action": kwargs["action_name"], "status": "success"}

        with patch("uri_core.core.native_tool_loop._execute_one_branch", side_effect=slow_branch):
            start = _time.monotonic()
            run_native_tool_loop(
                orchestrator=fixture.orchestrator(), session_id="s1", user_text="do three read-only things",
                principal=None, model_callable=fake_model,
            )
            elapsed = _time.monotonic() - start

        # 3 serial calls would take >= 3*SLEEP (~0.45s); concurrent
        # execution should take close to 1*SLEEP. Generous margin for
        # scheduling jitter - this only needs to prove "not fully serial".
        self.assertLess(elapsed, SLEEP * 2.5, f"batch took {elapsed:.3f}s - looks serial, not concurrent")

    def test_non_read_only_calls_are_never_concurrent_with_each_other(self):
        import threading

        fixture = _Fixture()
        responses = iter([
            _response(tool_calls=(
                ToolCall(id="c1", name="remember_fact", arguments={"request_text": "a"}),
                ToolCall(id="c2", name="remember_fact", arguments={"request_text": "b"}),
            )),
            _response(content="done", tool_calls=()),
        ])

        def fake_model(**kwargs):
            return next(responses)

        concurrent_count = {"current": 0, "max": 0}
        lock = threading.Lock()

        def tracked_branch(**kwargs):
            with lock:
                concurrent_count["current"] += 1
                concurrent_count["max"] = max(concurrent_count["max"], concurrent_count["current"])
            import time as _t
            _t.sleep(0.02)
            with lock:
                concurrent_count["current"] -= 1
            return {"tool_call_id": kwargs["tool_call_id"], "capability": kwargs["capability_id"],
                    "action": kwargs["action_name"], "status": "success"}

        with patch("uri_core.core.native_tool_loop._execute_one_branch", side_effect=tracked_branch):
            run_native_tool_loop(
                orchestrator=fixture.orchestrator(), session_id="s1", user_text="remember two things",
                principal=None, model_callable=fake_model,
            )

        self.assertEqual(concurrent_count["max"], 1, "two non-read-only calls ran concurrently - R4/SR-1 violation")


if __name__ == "__main__":
    unittest.main()
