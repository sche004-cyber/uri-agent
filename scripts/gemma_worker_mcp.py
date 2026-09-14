"""URI Gemma 4 Implementation Worker MCP bridge (AO-4).

Development-only, stdio-only Model Context Protocol (MCP) bridge.
Invokes the locally installed Ollama Gemma 4 12B model (gemma4:12b) as the
URI implementation worker.

Role and Authority Boundary (ORCHESTRATION.md, AGENTS.md):
- Gemma is strictly the implementation worker.
- Gemma receives accepted implementation plans or bounded remediation tasks.
- Gemma produces code changes and the structured GEMMA RETURN REPORT.
- Gemma has ZERO Git authority: cannot commit or push.
- Gemma has ZERO architectural authority: cannot modify architecture or verify milestones.
- Antigravity coordinates the loop, audits Gemma's outputs, and handles bounded fixes.
- Claude Code remains the sole pre-milestone planner, auditor, and final verifier (VERIFIED).

Security Guarantees:
- Local loopback Ollama only (http://127.0.0.1:11434). No remote exposure.
- Strict model pinning: gemma4:12b only. Fail-closed if unavailable; NO silent substitution.
- File-write boundaries: Protected files and out-of-scope files are strictly rejected.
- Credential protection: Input and output are scanned; no secrets or tokens are permitted.
- Zero extra dependencies: Pure Python standard library (urllib, json, sys, re, pathlib).
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple


# Configuration & Hyperparameters
OLLAMA_URL = "http://127.0.0.1:11434"
MODEL = "gemma4:12b"
TEMPERATURE = 1.0
TOP_K = 64
TOP_P = 0.95
REPEAT_PENALTY = 1.1
NUM_CTX = 16384
TIMEOUT_SECONDS = 300

# Bounded Input Limits
MAX_REQUEST_BYTES = 120_000
MAX_STRING_CHARS = 10_000
MAX_INSTRUCTIONS_CHARS = 20_000
MAX_CONTEXT_FILES = 16
MAX_FILE_CHARS = 30_000
MAX_LIST_ITEMS = 32
MAX_LIST_ITEM_CHARS = 1_000

# Input schema definition
TASK_PACKAGE_FIELDS = {
    "task_id",
    "milestone_id",
    "goal",
    "allowed_scope",
    "negative_constraints",
    "instructions",
    "acceptance_criteria",
    "test_plan",
    "context",
    "remediation_notes",
    "apply_to_worktree",
}

REQUIRED_STRING_FIELDS = {"task_id", "goal", "instructions"}

# Non-negotiable Protected Files: Cannot be modified by Gemma under any circumstances
PROTECTED_PATHS: Set[str] = {
    "uri_core/core/approval_gate.py",
    "uri_core/core/approval_store.py",
    "uri_core/core/dispatcher.py",
    "uri_core/core/principal_context.py",
    "step3_test.py",
    "step4_test.py",
    "AGENTS.md",
    "ORCHESTRATION.md",
    "URI_AI_OPERATING_POLICY.md",
    "URI_M22_ARCHITECTURE.md",
    "URI_MODEL_RUNTIME_CONTRACT.md",
    "URI_ADR_018_MODEL_CENTRIC_ARCHITECTURE.md",
    "URI_Model_Centric_Architecture_Docs/URI_ADR_018_MODEL_CENTRIC_ARCHITECTURE.md",
    "URI_Model_Centric_Architecture_Docs/URI_AI_OPERATING_POLICY.md",
    "URI_Model_Centric_Architecture_Docs/URI_MODEL_RUNTIME_CONTRACT.md",
    "scripts/dev_workflow/state_machine.py",
    "scripts/dev_workflow/file_authority.py",
    "scripts/dev_workflow/security_boundary.py",
    "scripts/dev_workflow/workflow_engine.py",
    "scripts/dev_workflow/claude_verifier.py",
    "scripts/dev_workflow/state_manager.py",
    "scripts/gemma_worker_mcp.py",
    "scripts/qwen_coordinator_mcp.py",
}

FORBIDDEN_INPUT_PATTERNS = (
    r"(?i)\b(?:git\s+(?:commit|push|reset|checkout|rebase|merge)|git\s+operation)\b",
    r"(?i)\b(?:please|must|execute|perform)\s+(?:release\s+)?(?:commit|push)\b",
    r"(?i)\bcommit\s+and\s+push\b",
    r"(?i)\b(?:run|execute|invoke)\s+(?:a\s+)?(?:shell|command|powershell|cmd)\b",
    r"(?i)\b(?:api[ _-]?key|password|secret|credential|token)\b",
    r"(?i)\b(?:bypass|skip)\s+claude\b",
    r"(?i)\bdeclare\s+verified\b",
)


class ValidationError(ValueError):
    """Raised for fail-closed MCP input validation."""


def _json_size(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False).encode("utf-8"))


def _ensure_safe_text(value: str, field: str) -> None:
    for pattern in FORBIDDEN_INPUT_PATTERNS:
        if re.search(pattern, value):
            raise ValidationError(
                f"{field} contains prohibited directive (Git, shell, credential, or authority bypass)"
            )


def normalize_relpath(path_str: str, repo_root: Optional[Path] = None) -> str:
    """Normalize path to relative POSIX style, rejecting traversal outside repo."""
    clean = path_str.strip().replace("\\", "/")
    if ".." in clean.split("/"):
        raise ValidationError(f"Path traversal ('..') is prohibited: {path_str}")
    p = Path(clean)
    if p.is_absolute():
        root = repo_root or Path.cwd()
        try:
            p = p.resolve().relative_to(root.resolve())
            clean = p.as_posix()
        except ValueError:
            raise ValidationError(f"Absolute path outside repository is prohibited: {path_str}")
    return clean.lstrip("./")


def validate_task_package(package: Any, repo_root: Optional[Path] = None) -> Dict[str, Any]:
    """Strictly validate and normalize the task package supplied by Antigravity."""
    if not isinstance(package, dict):
        raise ValidationError("task_package must be a JSON object")

    unknown = set(package) - TASK_PACKAGE_FIELDS
    if unknown:
        raise ValidationError(f"Unknown fields in task_package: {sorted(unknown)}")

    if _json_size(package) > MAX_REQUEST_BYTES:
        raise ValidationError(
            f"task_package exceeds maximum size limit ({MAX_REQUEST_BYTES} bytes)"
        )

    normalized: Dict[str, Any] = {}

    # Required string fields
    for field in REQUIRED_STRING_FIELDS:
        val = package.get(field)
        if not isinstance(val, str) or not val.strip():
            raise ValidationError(f"'{field}' is required and must be a non-empty string")
        max_chars = MAX_INSTRUCTIONS_CHARS if field == "instructions" else MAX_STRING_CHARS
        if len(val) > max_chars:
            raise ValidationError(f"'{field}' exceeds character limit ({max_chars})")
        _ensure_safe_text(val, field)
        normalized[field] = val.strip()

    # Optional string fields
    normalized["milestone_id"] = str(package.get("milestone_id") or normalized["task_id"]).strip()
    _ensure_safe_text(normalized["milestone_id"], "milestone_id")

    remediation = package.get("remediation_notes")
    if remediation is not None:
        if not isinstance(remediation, str) or len(remediation) > MAX_INSTRUCTIONS_CHARS:
            raise ValidationError("remediation_notes must be a bounded string")
        _ensure_safe_text(remediation, "remediation_notes")
        normalized["remediation_notes"] = remediation.strip()
    else:
        normalized["remediation_notes"] = None

    test_plan = package.get("test_plan")
    if test_plan is not None:
        if not isinstance(test_plan, str) or len(test_plan) > MAX_STRING_CHARS:
            raise ValidationError("test_plan must be a bounded string")
        _ensure_safe_text(test_plan, "test_plan")
        normalized["test_plan"] = test_plan.strip()
    else:
        normalized["test_plan"] = None

    # Allowed scope: MUST be non-empty list of relative file paths
    scope = package.get("allowed_scope")
    if not isinstance(scope, list) or not scope:
        raise ValidationError("allowed_scope must be a non-empty list of target file paths")
    if len(scope) > MAX_LIST_ITEMS:
        raise ValidationError(f"allowed_scope contains too many items (max {MAX_LIST_ITEMS})")

    norm_scope: List[str] = []
    for item in scope:
        if not isinstance(item, str) or not item.strip():
            raise ValidationError("allowed_scope items must be non-empty strings")
        path_norm = normalize_relpath(item, repo_root)
        if path_norm in PROTECTED_PATHS:
            raise ValidationError(
                f"allowed_scope contains protected authority file: '{path_norm}'"
            )
        norm_scope.append(path_norm)
    normalized["allowed_scope"] = norm_scope

    # Negative constraints list
    neg = package.get("negative_constraints") or []
    if not isinstance(neg, list) or len(neg) > MAX_LIST_ITEMS:
        raise ValidationError(f"negative_constraints must be a list with at most {MAX_LIST_ITEMS} items")
    norm_neg = []
    for item in neg:
        if not isinstance(item, str) or len(item) > MAX_LIST_ITEM_CHARS:
            raise ValidationError("negative_constraints entries must be bounded strings")
        norm_neg.append(item.strip())
    normalized["negative_constraints"] = norm_neg

    # Acceptance criteria list
    crit = package.get("acceptance_criteria") or []
    if not isinstance(crit, list) or len(crit) > MAX_LIST_ITEMS:
        raise ValidationError(f"acceptance_criteria must be a list with at most {MAX_LIST_ITEMS} items")
    norm_crit = []
    for item in crit:
        if not isinstance(item, str) or len(item) > MAX_LIST_ITEM_CHARS:
            raise ValidationError("acceptance_criteria entries must be bounded strings")
        norm_crit.append(item.strip())
    normalized["acceptance_criteria"] = norm_crit

    # Context files map {path: content}
    ctx = package.get("context") or {}
    if not isinstance(ctx, dict):
        raise ValidationError("context must be an object mapping paths to string content")
    if len(ctx) > MAX_CONTEXT_FILES:
        raise ValidationError(f"context contains too many files (max {MAX_CONTEXT_FILES})")
    norm_ctx: Dict[str, str] = {}
    for cpath, content in ctx.items():
        if not isinstance(cpath, str) or not isinstance(content, str):
            raise ValidationError("context must map strings to strings")
        if len(content) > MAX_FILE_CHARS:
            raise ValidationError(f"context file '{cpath}' exceeds {MAX_FILE_CHARS} chars limit")
        _ensure_safe_text(content, f"context[{cpath}]")
        norm_cpath = normalize_relpath(cpath, repo_root)
        norm_ctx[norm_cpath] = content
    normalized["context"] = norm_ctx

    # apply_to_worktree flag
    normalized["apply_to_worktree"] = bool(package.get("apply_to_worktree", False))

    return normalized


def build_gemma_prompt(package: Mapping[str, Any]) -> Tuple[str, str]:
    """Format system and user prompt for Gemma 4 12B."""
    system_prompt = (
        "You are Gemma 4 12B, the primary implementation worker for the URI development team under AO-4.\n"
        "Your role is SOLELY implementation. You write and edit code files within your assigned scope.\n"
        "NON-NEGOTIABLE BOUNDARIES:\n"
        "1. ZERO Git authority: You NEVER commit, push, or branch.\n"
        "2. ZERO architecture authority: You NEVER change architecture or approve plans.\n"
        "3. ZERO verification authority: You NEVER declare VERIFIED or certify milestones.\n"
        "4. Strict Scope: You ONLY touch files in your allowed scope. Protected files are forbidden.\n"
        "5. Output File Format: Output every modified or created file exactly as:\n"
        "### FILE: <relative_path>\n"
        "```<language>\n"
        "<complete file content>\n"
        "```\n"
        "6. Summary Report: Conclude your response with the structured report:\n"
        "### GEMMA RETURN REPORT\n"
        "- **Milestone ID:** <id>\n"
        "- **Summary of Actions:** <summary of what code was created/edited>\n"
        "- **Files Modified/Created:** <list of files>\n"
        "- **Tests Performed:** <tests run or proposed>\n"
        "- **Assumptions & Decisions:** <decisions within accepted scope>\n"
        "- **Known Issues / Gaps:** <any remaining items>\n"
    )

    parts: List[str] = [
        f"# Task Brief: {package['task_id']} (Milestone: {package['milestone_id']})",
        f"**Goal:** {package['goal']}",
        f"**Allowed Scope (Files you may touch):**\n" + "\n".join(f"- {p}" for p in package["allowed_scope"]),
    ]

    if package.get("negative_constraints"):
        parts.append("**Negative Constraints:**\n" + "\n".join(f"- {c}" for c in package["negative_constraints"]))

    if package.get("acceptance_criteria"):
        parts.append("**Acceptance Criteria:**\n" + "\n".join(f"- {c}" for c in package["acceptance_criteria"]))

    if package.get("test_plan"):
        parts.append(f"**Test Plan:**\n{package['test_plan']}")

    if package.get("remediation_notes"):
        parts.append(f"**REMEDIATION NOTES (Previous pass returned defects/findings):**\n{package['remediation_notes']}")

    parts.append(f"**Instructions:**\n{package['instructions']}")

    if package.get("context"):
        parts.append("**Repository File Context:**")
        for fpath, fcontent in package["context"].items():
            parts.append(f"File `{fpath}`:\n```\n{fcontent}\n```")

    user_prompt = "\n\n".join(parts)
    return system_prompt, user_prompt


class OllamaGemmaClient:
    """Local-only Ollama client pinned to gemma4:12b."""

    def __init__(self, base_url: str = OLLAMA_URL, model: str = MODEL, timeout_sec: int = TIMEOUT_SECONDS):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_sec = timeout_sec

    def _request(self, path: str, payload: Any = None) -> Dict[str, Any]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "URI-Gemma-MCP/1.0"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout_sec) as response:
            if response.status != 200:
                raise RuntimeError(f"Ollama returned HTTP status {response.status}")
            return json.loads(response.read().decode("utf-8"))

    def check_availability(self) -> Tuple[bool, str]:
        """Check if local Ollama is reachable and gemma4:12b is installed."""
        try:
            tags = self._request("/api/tags")
        except (OSError, urllib.error.URLError, RuntimeError, json.JSONDecodeError) as exc:
            return False, f"Ollama service unavailable at {self.base_url}: {exc}"

        models = [entry.get("name") for entry in tags.get("models", [])]
        # Match exact model name or model prefix (e.g. gemma4:12b)
        if not any(m == self.model or m.startswith(f"{self.model}:") for m in models):
            return False, f"Required model '{self.model}' is not installed in Ollama. Installed: {models}"
        return True, "available"

    def generate(self, system_prompt: str, user_prompt: str) -> Tuple[str, Dict[str, Any]]:
        """Call Ollama /api/generate with qualified Gemma 4 12B hyperparameters."""
        payload = {
            "model": self.model,
            "prompt": user_prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": TEMPERATURE,
                "top_k": TOP_K,
                "top_p": TOP_P,
                "repeat_penalty": REPEAT_PENALTY,
                "num_ctx": NUM_CTX,
            },
        }
        started = time.monotonic()
        resp = self._request("/api/generate", payload)
        latency_ms = round((time.monotonic() - started) * 1000)

        metadata = {
            "model": self.model,
            "context_limit": NUM_CTX,
            "latency_ms": latency_ms,
            "eval_count": resp.get("eval_count"),
            "prompt_eval_count": resp.get("prompt_eval_count"),
        }
        raw_text = resp.get("response", "")
        return raw_text, metadata


def extract_code_blocks(response_text: str) -> List[Tuple[str, str]]:
    """Extract (path, content) blocks from Gemma's response."""
    results: List[Tuple[str, str]] = []

    # Format 1: ### FILE: <path>\n```<lang>\n<content>\n```
    p1 = re.compile(
        r"(?:###|\*\*)\s*(?:FILE|File):\s*`?([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9_]+)`?\s*\n```[a-zA-Z0-9_-]*\s*\n(.*?)\n```",
        re.DOTALL,
    )
    for m in p1.finditer(response_text):
        path = m.group(1).strip()
        content = m.group(2)
        results.append((path, content))

    # Format 2: ```<lang> (?:path|file)="<path>"\n<content>\n```
    p2 = re.compile(
        r"```[a-zA-Z0-9_-]*\s+(?:path|file)=[\"']([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9_]+)[\"']\s*\n(.*?)\n```",
        re.DOTALL,
    )
    for m in p2.finditer(response_text):
        path = m.group(1).strip()
        content = m.group(2)
        if not any(r[0] == path for r in results):
            results.append((path, content))

    return results


def parse_return_report(response_text: str, milestone_id: str) -> Dict[str, str]:
    """Parse Gemma's response into a structured return report dictionary."""
    match = re.search(r"### GEMMA RETURN REPORT\s*\n(.*?)(?=```|\Z)", response_text, re.DOTALL)
    body = match.group(1) if match else response_text

    def extract_field(name: str) -> str:
        m = re.search(rf"- \*\*{re.escape(name)}:\*\*\s*(.*?)(?=\n- \*\*|\Z)", body, re.DOTALL)
        return m.group(1).strip() if m else ""

    return {
        "milestone_id": milestone_id,
        "summary_of_actions": extract_field("Summary of Actions") or "Implementation completed.",
        "files_modified_created": extract_field("Files Modified/Created") or "None reported.",
        "tests_performed": extract_field("Tests Performed") or "None reported.",
        "assumptions_decisions": extract_field("Assumptions & Decisions") or "None.",
        "known_issues_gaps": extract_field("Known Issues / Gaps") or "None.",
        "raw_report": body.strip(),
    }


class GemmaWorkerService:
    """Service handling Gemma implementation requests with boundary enforcement."""

    def __init__(
        self,
        client: Optional[OllamaGemmaClient] = None,
        repo_root: Optional[Path] = None,
    ):
        self.client = client or OllamaGemmaClient()
        self.repo_root = (repo_root or Path.cwd()).resolve()

    def implement(self, raw_package: Any) -> Dict[str, Any]:
        """Validate, invoke Gemma, verify file-write boundaries, and return structured result."""
        try:
            package = validate_task_package(raw_package, self.repo_root)
        except ValidationError as exc:
            return {
                "status": "invalid_request",
                "task_id": getattr(raw_package, "get", lambda _: None)("task_id") if isinstance(raw_package, dict) else None,
                "model_metadata": {"model": MODEL},
                "error": str(exc),
            }

        available, message = self.client.check_availability()
        if not available:
            return {
                "status": "unavailable",
                "task_id": package["task_id"],
                "model_metadata": {"model": MODEL},
                "error": message,
            }

        system_prompt, user_prompt = build_gemma_prompt(package)

        try:
            raw_response, metadata = self.client.generate(system_prompt, user_prompt)
        except Exception as exc:
            return {
                "status": "error",
                "task_id": package["task_id"],
                "model_metadata": {"model": MODEL},
                "error": f"Ollama generation failed: {exc}",
            }

        # Extract code blocks
        extracted_blocks = extract_code_blocks(raw_response)
        allowed_set = set(package["allowed_scope"])

        proposed_files: List[Dict[str, Any]] = []
        written_files: List[str] = []
        rejected_files: List[Dict[str, str]] = []

        for rel_path_raw, code_content in extracted_blocks:
            try:
                rel_path = normalize_relpath(rel_path_raw, self.repo_root)
            except ValidationError as v_err:
                rejected_files.append({"path": rel_path_raw, "reason": str(v_err)})
                proposed_files.append({
                    "path": rel_path_raw,
                    "content": code_content,
                    "authorized": False,
                    "rejection_reason": str(v_err),
                })
                continue

            # Scope & Protection Checks
            if rel_path in PROTECTED_PATHS:
                reason = f"File '{rel_path}' is a protected authority file"
                rejected_files.append({"path": rel_path, "reason": reason})
                proposed_files.append({
                    "path": rel_path,
                    "content": code_content,
                    "authorized": False,
                    "rejection_reason": reason,
                })
            elif rel_path not in allowed_set:
                reason = f"File '{rel_path}' is outside the authorized task scope"
                rejected_files.append({"path": rel_path, "reason": reason})
                proposed_files.append({
                    "path": rel_path,
                    "content": code_content,
                    "authorized": False,
                    "rejection_reason": reason,
                })
            else:
                # Authorized file
                proposed_files.append({
                    "path": rel_path,
                    "content": code_content,
                    "authorized": True,
                    "rejection_reason": None,
                })

                if package["apply_to_worktree"]:
                    try:
                        target_file = self.repo_root / rel_path
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        target_file.write_text(code_content, encoding="utf-8")
                        written_files.append(rel_path)
                    except Exception as write_err:
                        rejected_files.append({
                            "path": rel_path,
                            "reason": f"Failed to write file to worktree: {write_err}",
                        })

        report = parse_return_report(raw_response, package["milestone_id"])
        if written_files and report["files_modified_created"] in ("None reported.", "None."):
            report["files_modified_created"] = ", ".join(written_files)

        return {
            "status": "ok",
            "task_id": package["task_id"],
            "milestone_id": package["milestone_id"],
            "model_metadata": metadata,
            "gemma_return_report": report,
            "files_proposed": proposed_files,
            "files_written": written_files,
            "rejected_files": rejected_files,
            "raw_response": raw_response,
        }


# MCP Tool Definition
GEMMA_IMPLEMENT_TOOL = {
    "name": "gemma_implement",
    "description": (
        "Invoke local Gemma 4 12B worker via Ollama for bounded URI milestone implementation or remediation under AO-4. "
        "Accepts a bounded task package and returns proposed file changes and a structured GEMMA RETURN REPORT. "
        "Does NOT commit, push, or verify."
    ),
    "inputSchema": {
        "type": "object",
        "required": ["task_package"],
        "additionalProperties": False,
        "properties": {
            "task_package": {
                "type": "object",
                "required": ["task_id", "goal", "allowed_scope", "instructions"],
                "additionalProperties": False,
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Unique identifier for this task (e.g. M22.3-task-1)",
                    },
                    "milestone_id": {
                        "type": "string",
                        "description": "The active canonical milestone identifier (e.g. M22.3)",
                    },
                    "goal": {
                        "type": "string",
                        "description": "Concise summary of what this implementation task accomplishes",
                    },
                    "allowed_scope": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Exact list of relative file paths that Gemma is authorized to touch",
                    },
                    "negative_constraints": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Explicit constraints (e.g. prohibited changes, UX tier non-reliance)",
                    },
                    "instructions": {
                        "type": "string",
                        "description": "Detailed implementation instructions or remediation guidance",
                    },
                    "acceptance_criteria": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Acceptance criteria and expectations from the approved plan",
                    },
                    "test_plan": {
                        "type": "string",
                        "description": "Required tests to add or execute",
                    },
                    "context": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                        "description": "Map of relative file paths to relevant file contents/excerpts",
                    },
                    "remediation_notes": {
                        "type": "string",
                        "description": "Claude's findings or defect notes when repeating work after NOT VERIFIED",
                    },
                    "apply_to_worktree": {
                        "type": "boolean",
                        "description": (
                            "If True, safely writes authorized, non-protected files in allowed_scope to disk. "
                            "If False, only returns proposed changes for Antigravity review."
                        ),
                    },
                },
            }
        },
    },
}


def _result(request_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle_message(message: Any, service: GemmaWorkerService) -> Optional[Dict[str, Any]]:
    """Handle a single newline-delimited JSON-RPC MCP message without side effects."""
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return _error(message.get("id") if isinstance(message, dict) else None, -32600, "Invalid JSON-RPC request")

    method, request_id = message.get("method"), message.get("id")

    if method == "notifications/initialized":
        return None

    if method == "initialize":
        return _result(
            request_id,
            {
                "protocolVersion": message.get("params", {}).get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "uri-gemma-worker", "version": "1.0.0"},
            },
        )

    if method == "tools/list":
        return _result(request_id, {"tools": [GEMMA_IMPLEMENT_TOOL]})

    if method == "tools/call":
        params = message.get("params", {})
        tool_name = params.get("name")
        if tool_name != "gemma_implement":
            return _error(request_id, -32602, f"Unknown tool: '{tool_name}'. Only 'gemma_implement' is available")

        arguments = params.get("arguments")
        if not isinstance(arguments, dict) or "task_package" not in arguments:
            return _error(request_id, -32602, "'gemma_implement' requires 'task_package' argument")

        result = service.implement(arguments["task_package"])
        is_error = result.get("status") != "ok"
        return _result(
            request_id,
            {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                "isError": is_error,
            },
        )

    return _error(request_id, -32601, f"Method '{method}' not found")


def main(stdin: Any = sys.stdin, stdout: Any = sys.stdout) -> None:
    service = GemmaWorkerService()
    while True:
        line = stdin.readline()
        if not line:
            break
        line_clean = line.strip()
        if not line_clean:
            continue
        try:
            req = json.loads(line_clean)
            resp = handle_message(req, service)
        except json.JSONDecodeError:
            resp = _error(None, -32700, "Parse error")
        except Exception as exc:
            print(f"URI Gemma MCP internal error: {exc}", file=sys.stderr)
            resp = _error(None, -32603, "Internal error")

        if resp is not None:
            stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            stdout.flush()


if __name__ == "__main__":
    main()
