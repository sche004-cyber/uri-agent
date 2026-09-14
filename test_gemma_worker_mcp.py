"""Unit tests for the Gemma 4 MCP Worker Bridge (AO-4).

Verifies protocol correctness, schema validation, fail-closed security boundaries,
Ollama communication, and file authorization constraints.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scripts.gemma_worker_mcp import (
    MODEL,
    PROTECTED_PATHS,
    GemmaWorkerService,
    OllamaGemmaClient,
    extract_code_blocks,
    handle_message,
    normalize_relpath,
    parse_return_report,
    validate_task_package,
    ValidationError,
)


def sample_task_package(**overrides: Any) -> Dict[str, Any]:
    package = {
        "task_id": "M22.3-task-auth-routes",
        "milestone_id": "M22.3",
        "goal": "Add endpoint authorization decorators to internal API routes.",
        "allowed_scope": ["uri_core/api/routes.py", "tests/test_routes.py"],
        "negative_constraints": ["Do not modify approval_gate.py", "Do not rely on experience_tier"],
        "instructions": "Implement role check for admin routes and unit test verifying unauthorized requests fail with 403.",
        "acceptance_criteria": ["All internal routes require valid role", "403 returned on unauthorized"],
        "test_plan": "pytest tests/test_routes.py",
        "context": {"uri_core/api/routes.py": "# Route definitions\ndef route_a(): pass\n"},
        "remediation_notes": None,
        "apply_to_worktree": False,
    }
    package.update(overrides)
    return package


SAMPLE_GEMMA_RESPONSE = """Here is the implementation of the requested endpoint authorization:

### FILE: uri_core/api/routes.py
```python
def route_a():
    # Authorized route
    return {"status": "ok"}
```

### FILE: tests/test_routes.py
```python
def test_route_a():
    assert True
```

### GEMMA RETURN REPORT
- **Milestone ID:** M22.3
- **Summary of Actions:** Implemented role checks for internal route handlers and added unit tests.
- **Files Modified/Created:** uri_core/api/routes.py, tests/test_routes.py
- **Tests Performed:** pytest tests/test_routes.py (2 passing)
- **Assumptions & Decisions:** Used standard 403 Forbidden for unauthorized callers.
- **Known Issues / Gaps:** None.
"""


class FakeOllamaClient:
    """Mock Ollama client for deterministic testing."""

    def __init__(
        self,
        available: bool = True,
        models_installed: Optional[List[str]] = None,
        response_text: str = SAMPLE_GEMMA_RESPONSE,
    ):
        self.is_available = available
        self.models = models_installed or [MODEL]
        self.response_text = response_text
        self.generate_calls: List[Tuple[str, str]] = []

    def check_availability(self) -> Tuple[bool, str]:
        if not self.is_available:
            return False, "Ollama service unavailable at http://127.0.0.1:11434: Connection refused"
        if MODEL not in self.models:
            return False, f"Required model '{MODEL}' is not installed in Ollama. Installed: {self.models}"
        return True, "available"

    def generate(self, system_prompt: str, user_prompt: str) -> Tuple[str, Dict[str, Any]]:
        self.generate_calls.append((system_prompt, user_prompt))
        metadata = {
            "model": MODEL,
            "context_limit": 16384,
            "latency_ms": 12,
            "eval_count": 150,
            "prompt_eval_count": 80,
        }
        return self.response_text, metadata


class GemmaWorkerMcpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.repo_root = Path(self.temp_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def get_service(self, client: Optional[Any] = None) -> GemmaWorkerService:
        return GemmaWorkerService(
            client=client or FakeOllamaClient(),
            repo_root=self.repo_root,
        )

    # 1. MCP Protocol & Tool Discovery
    def test_mcp_initialize(self) -> None:
        req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}}
        resp = handle_message(req, self.get_service())
        self.assertIsNotNone(resp)
        self.assertEqual(resp["id"], 1)
        self.assertEqual(resp["result"]["serverInfo"]["name"], "uri-gemma-worker")

    def test_mcp_tools_list_exposes_only_gemma_implement(self) -> None:
        req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        resp = handle_message(req, self.get_service())
        self.assertIsNotNone(resp)
        tools = resp["result"]["tools"]
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["name"], "gemma_implement")
        tool_names = [t["name"] for t in tools]
        self.assertNotIn("commit", tool_names)
        self.assertNotIn("push", tool_names)
        self.assertNotIn("verify", tool_names)
        self.assertNotIn("approve", tool_names)

    # 2. Successful Execution Flow
    def test_valid_implement_request_invokes_gemma_and_extracts_files(self) -> None:
        client = FakeOllamaClient()
        service = self.get_service(client)
        result = service.implement(sample_task_package())

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["task_id"], "M22.3-task-auth-routes")
        self.assertEqual(result["model_metadata"]["model"], MODEL)
        self.assertEqual(len(client.generate_calls), 1)

        # Check extracted files
        self.assertEqual(len(result["files_proposed"]), 2)
        paths = [f["path"] for f in result["files_proposed"]]
        self.assertIn("uri_core/api/routes.py", paths)
        self.assertIn("tests/test_routes.py", paths)
        self.assertTrue(all(f["authorized"] for f in result["files_proposed"]))

        # Check return report
        report = result["gemma_return_report"]
        self.assertEqual(report["milestone_id"], "M22.3")
        self.assertIn("role checks", report["summary_of_actions"])

    # 3. Model Pinning & Fail-Closed Behavior
    def test_ollama_unavailable_reports_explicit_error(self) -> None:
        client = FakeOllamaClient(available=False)
        service = self.get_service(client)
        result = service.implement(sample_task_package())
        self.assertEqual(result["status"], "unavailable")
        self.assertIn("unavailable", result["error"].lower())

    def test_missing_gemma4_model_reports_explicit_error_without_substitution(self) -> None:
        client = FakeOllamaClient(available=True, models_installed=["qwen3:14b", "llama3:8b"])
        service = self.get_service(client)
        result = service.implement(sample_task_package())
        self.assertEqual(result["status"], "unavailable")
        self.assertIn(f"Required model '{MODEL}' is not installed", result["error"])
        # Invariant: No fallback to qwen3:14b
        self.assertEqual(len(client.generate_calls), 0)

    # 4. Scope & Protected Path Enforcement
    def test_file_outside_allowed_scope_is_rejected(self) -> None:
        unauthorized_response = (
            "### FILE: uri_core/api/routes.py\n```python\npass\n```\n"
            "### FILE: uri_core/unauthorized_module.py\n```python\npass\n```\n"
        )
        client = FakeOllamaClient(response_text=unauthorized_response)
        service = self.get_service(client)
        result = service.implement(sample_task_package(allowed_scope=["uri_core/api/routes.py"]))

        self.assertEqual(result["status"], "ok")
        proposed = result["files_proposed"]
        self.assertEqual(len(proposed), 2)

        routes_entry = next(f for f in proposed if f["path"] == "uri_core/api/routes.py")
        self.assertTrue(routes_entry["authorized"])

        unauth_entry = next(f for f in proposed if f["path"] == "uri_core/unauthorized_module.py")
        self.assertFalse(unauth_entry["authorized"])
        self.assertIn("outside the authorized task scope", unauth_entry["rejection_reason"])
        self.assertEqual(len(result["rejected_files"]), 1)
        self.assertEqual(result["rejected_files"][0]["path"], "uri_core/unauthorized_module.py")

    def test_protected_authority_file_is_strictly_rejected(self) -> None:
        protected_response = (
            "### FILE: uri_core/core/approval_gate.py\n```python\n# modified\n```\n"
        )
        client = FakeOllamaClient(response_text=protected_response)
        service = self.get_service(client)
        # Even if someone erroneously put it in allowed_scope, validation blocks it at input!
        with self.assertRaises(ValidationError) as ctx:
            validate_task_package(sample_task_package(allowed_scope=["uri_core/core/approval_gate.py"]))
        self.assertIn("contains protected authority file", str(ctx.exception))

    def test_gemma_attempt_to_modify_protected_file_in_output_is_rejected(self) -> None:
        # If Gemma generates a protected file that was not in allowed_scope:
        protected_response = (
            "### FILE: uri_core/api/routes.py\n```python\npass\n```\n"
            "### FILE: scripts/dev_workflow/security_boundary.py\n```python\n# bypass\n```\n"
        )
        client = FakeOllamaClient(response_text=protected_response)
        service = self.get_service(client)
        result = service.implement(sample_task_package(allowed_scope=["uri_core/api/routes.py"]))

        rejected = result["rejected_files"]
        self.assertTrue(any("security_boundary.py" in r["path"] for r in rejected))
        sec_entry = next(f for f in result["files_proposed"] if "security_boundary.py" in f["path"])
        self.assertFalse(sec_entry["authorized"])

    # 5. Security Invariants & Forbidden Directives
    def test_prohibited_git_directives_in_input_rejected(self) -> None:
        for bad_directive in ["git commit -m 'done'", "git push origin master", "please commit"]:
            with self.subTest(bad_directive=bad_directive):
                pkg = sample_task_package(instructions=f"Do work and then {bad_directive}")
                result = self.get_service().implement(pkg)
                self.assertEqual(result["status"], "invalid_request")
                self.assertIn("prohibited directive", result["error"])

    def test_prohibited_claude_bypass_in_input_rejected(self) -> None:
        for bad_phrase in ["bypass claude and release", "declare verified immediately"]:
            with self.subTest(bad_phrase=bad_phrase):
                pkg = sample_task_package(instructions=bad_phrase)
                result = self.get_service().implement(pkg)
                self.assertEqual(result["status"], "invalid_request")
                self.assertIn("prohibited directive", result["error"])

    def test_credential_leak_patterns_in_input_rejected(self) -> None:
        for cred in ["export API_KEY=abc123", "password = 'secret'", "BEARER_TOKEN=xyz"]:
            with self.subTest(cred=cred):
                pkg = sample_task_package(instructions=f"Use credential: {cred}")
                result = self.get_service().implement(pkg)
                self.assertEqual(result["status"], "invalid_request")
                self.assertIn("prohibited directive", result["error"])

    def test_path_traversal_in_scope_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            validate_task_package(sample_task_package(allowed_scope=["../../etc/passwd"]))

    # 6. File-Writing to Worktree (apply_to_worktree=True)
    def test_apply_to_worktree_writes_only_authorized_files(self) -> None:
        mixed_response = (
            "### FILE: uri_core/api/routes.py\n```python\n# valid code\n```\n"
            "### FILE: unauthorized_dir/bad.py\n```python\n# bad\n```\n"
        )
        client = FakeOllamaClient(response_text=mixed_response)
        service = self.get_service(client)
        pkg = sample_task_package(
            allowed_scope=["uri_core/api/routes.py"],
            apply_to_worktree=True,
        )
        result = service.implement(pkg)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["files_written"], ["uri_core/api/routes.py"])
        written_path = self.repo_root / "uri_core" / "api" / "routes.py"
        self.assertTrue(written_path.exists())
        self.assertEqual(written_path.read_text(encoding="utf-8"), "# valid code")

        # Unauthorized file was NOT written
        unauthorized_path = self.repo_root / "unauthorized_dir" / "bad.py"
        self.assertFalse(unauthorized_path.exists())

    # 7. MCP JSON-RPC Stdio Call Handling
    def test_main_stdio_loop(self) -> None:
        import io
        from scripts.gemma_worker_mcp import main

        input_data = (
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}}) + "\n"
            + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}) + "\n"
        )
        stdin = io.StringIO(input_data)
        stdout = io.StringIO()
        main(stdin=stdin, stdout=stdout)

        lines = [json.loads(line) for line in stdout.getvalue().strip().splitlines()]
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["id"], 1)
        self.assertEqual(lines[0]["result"]["serverInfo"]["name"], "uri-gemma-worker")
        self.assertEqual(lines[1]["id"], 2)
        self.assertEqual(lines[1]["result"]["tools"][0]["name"], "gemma_implement")

    def test_mcp_tools_call_dispatch(self) -> None:
        req = {
            "jsonrpc": "2.0",
            "id": 42,
            "method": "tools/call",
            "params": {
                "name": "gemma_implement",
                "arguments": {"task_package": sample_task_package()},
            },
        }
        resp = handle_message(req, self.get_service())
        self.assertIsNotNone(resp)
        self.assertEqual(resp["id"], 42)
        self.assertIn("result", resp)
        self.assertFalse(resp["result"]["isError"])
        content_json = json.loads(resp["result"]["content"][0]["text"])
        self.assertEqual(content_json["status"], "ok")
        self.assertEqual(content_json["task_id"], "M22.3-task-auth-routes")


class LiveOllamaIntegrationTests(unittest.TestCase):
    """Integration test checking live local Ollama instance if available.

    This test is conditional and does not fail CI if Ollama is not running.
    """

    def test_live_ollama_status_and_model(self) -> None:
        client = OllamaGemmaClient()
        available, msg = client.check_availability()
        if not available:
            self.skipTest(f"Live Ollama not available: {msg}")

        self.assertTrue(available)
        self.assertEqual(msg, "available")


if __name__ == "__main__":
    unittest.main()
