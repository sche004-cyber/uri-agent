"""Focused AO-3B tests for the non-destructive Qwen MCP bridge."""

import json
import unittest
from unittest.mock import Mock

from scripts.qwen_coordinator_mcp import (
    MODEL,
    QwenCoordinatorMcp,
    handle_message,
)


def context(**overrides):
    value = {
        "task_id": "AO-3B-safe-doc-task",
        "goal": "Review a documentation-only task and recommend a safe next state.",
        "active_milestone": "AO-3B",
        "governing_constraints": ["Qwen proposes only."],
        "allowed_scope": ["PROJECT_MEMORY.md"],
        "negative_constraints": ["Do not run shell commands."],
        "verified_baseline": ["M22.2 is complete."],
        "relevant_evidence": ["Documentation-only pilot."],
        "worker_return": None,
    }
    value.update(overrides)
    return value


def proposal(**overrides):
    value = {
        "task_understanding": "This is a documentation-only task.",
        "recommended_action": "PLAN",
        "selected_worker": "Antigravity",
        "reason": "The task is localized and needs no privileged action.",
        "allowed_scope": ["PROJECT_MEMORY.md"],
        "negative_constraints": ["No source changes."],
        "verification_requirements": ["Review the resulting diff."],
        "escalation": "none",
        "risks": ["Proposal remains advisory."],
        "recommended_next_state": "PLANNED",
    }
    value.update(overrides)
    return value


class FakeClient:
    def __init__(self, available=True, content=None):
        self.available_result = available
        self.content = content or json.dumps(proposal())
        self.calls = 0

    def available(self):
        return (True, "available") if self.available_result else (False, "Required model 'qwen3:14b' is unavailable")

    def coordinate(self, _context):
        self.calls += 1
        return {"message": {"content": self.content}}, {"model": MODEL, "context_limit": 8192, "latency_ms": 1, "prompt_eval_count": 10, "eval_count": 10}


class QwenCoordinatorMcpTests(unittest.TestCase):
    def service(self, client=None):
        return QwenCoordinatorMcp(client or FakeClient())

    def test_valid_coordinate_request_returns_proposal_without_execution(self):
        client = FakeClient()
        result = self.service(client).coordinate(context())
        self.assertEqual("ok", result["status"])
        self.assertEqual("PLAN", result["proposal"]["recommended_action"])
        self.assertEqual(1, client.calls)

    def test_malformed_request_is_rejected(self):
        result = self.service().coordinate("not-an-object")
        self.assertEqual("invalid_request", result["status"])

    def test_unknown_input_field_is_rejected(self):
        result = self.service().coordinate(context(extra="no"))
        self.assertEqual("invalid_request", result["status"])

    def test_oversized_input_is_rejected(self):
        result = self.service().coordinate(context(goal="x" * 4001))
        self.assertEqual("invalid_request", result["status"])

    def test_missing_required_field_is_rejected(self):
        value = context()
        del value["goal"]
        self.assertEqual("invalid_request", self.service().coordinate(value)["status"])

    def test_ollama_unavailable_is_structured(self):
        result = self.service(FakeClient(available=False)).coordinate(context())
        self.assertEqual("unavailable", result["status"])

    def test_unavailable_model_is_structured(self):
        result = self.service(FakeClient(available=False)).coordinate(context())
        self.assertEqual("unavailable", result["status"])

    def test_malformed_qwen_proposal_is_rejected(self):
        result = self.service(FakeClient(content="not json")).coordinate(context())
        self.assertEqual("invalid_proposal", result["status"])

    def test_unauthorized_worker_is_rejected(self):
        result = self.service(FakeClient(content=json.dumps(proposal(selected_worker="Gemma 3")))).coordinate(context())
        self.assertEqual("invalid_proposal", result["status"])

    def test_protected_scope_is_rejected(self):
        protected = "uri_core/core/approval_gate.py"
        result = self.service(FakeClient(content=json.dumps(proposal(allowed_scope=[protected])))).coordinate(context(allowed_scope=[protected]))
        self.assertEqual("invalid_proposal", result["status"])

    def test_forbidden_authority_language_is_rejected(self):
        result = self.service(FakeClient(content=json.dumps(proposal(reason="Qwen will execute the plan.")))).coordinate(context())
        self.assertEqual("invalid_proposal", result["status"])

    def test_shell_git_and_credential_requests_are_rejected(self):
        for goal in ("Run a shell command", "Perform git commit", "Use an API key"):
            with self.subTest(goal=goal):
                self.assertEqual("invalid_request", self.service().coordinate(context(goal=goal))["status"])

    def test_mcp_exposes_only_coordinate(self):
        response = handle_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, self.service())
        self.assertEqual(["coordinate"], [tool["name"] for tool in response["result"]["tools"]])

    def test_no_execution_behavior(self):
        client = FakeClient()
        service = self.service(client)
        reply = handle_message({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "coordinate", "arguments": {"task_context": context()}}}, service)
        body = json.loads(reply["result"]["content"][0]["text"])
        self.assertEqual("ok", body["status"])
        self.assertEqual(1, client.calls)
        self.assertNotIn("execute", json.dumps(body["proposal"]).lower())


if __name__ == "__main__":
    unittest.main()
