"""URI Qwen Coordinator MCP bridge (AO-3B).

Development-only, stdio-only bridge.  It accepts curated context from the MCP
host and returns an untrusted coordination proposal.  It deliberately has no
repository, shell, subprocess, Git, credential, or worker-invocation access.
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Iterable, List, Mapping, Tuple


OLLAMA_URL = "http://127.0.0.1:11434"
MODEL = "qwen3:14b"
NUM_CTX = 8192
TEMPERATURE = 0.2
TIMEOUT_SECONDS = 180
MAX_REQUEST_BYTES = 20_000
MAX_GOAL_CHARS = 4_000
MAX_WORKER_RETURN_CHARS = 6_000
MAX_LIST_ITEMS = 32
MAX_LIST_ITEM_CHARS = 500
MAX_PROPOSAL_BYTES = 12_000

INPUT_FIELDS = {
    "task_id",
    "goal",
    "active_milestone",
    "governing_constraints",
    "allowed_scope",
    "negative_constraints",
    "verified_baseline",
    "relevant_evidence",
    "worker_return",
}
LIST_FIELDS = {
    "governing_constraints",
    "allowed_scope",
    "negative_constraints",
    "verified_baseline",
    "relevant_evidence",
}
REQUIRED_STRING_FIELDS = {"task_id", "goal", "active_milestone"}
PROPOSAL_FIELDS = {
    "task_understanding",
    "recommended_action",
    "selected_worker",
    "reason",
    "allowed_scope",
    "negative_constraints",
    "verification_requirements",
    "escalation",
    "risks",
    "recommended_next_state",
}
VALID_ACTIONS = {"TRIAGE", "PLAN", "DELEGATE", "REVIEW", "AUDIT", "ESCALATE"}
VALID_WORKERS = {"Antigravity", "Codex", "Claude Code", "User"}
VALID_ESCALATIONS = {"none", "Claude Code", "User"}
VALID_STATES = {
    "IDLE", "TRIAGED", "PLANNED", "DELEGATED", "IMPLEMENTING", "TESTING",
    "REVIEWING", "AUDITING", "AWAITING_APPROVAL", "VERIFIED", "COMMITTED", "PUSHED",
}
PROTECTED_PATHS = {
    "uri_core/core/approval_gate.py",
    "uri_core/core/approval_store.py",
    "step3_test.py",
    "step4_test.py",
    "URI_Model_Centric_Architecture_Docs/URI_ADR_018_MODEL_CENTRIC_ARCHITECTURE.md",
    "URI_Model_Centric_Architecture_Docs/URI_AI_OPERATING_POLICY.md",
    "URI_Model_Centric_Architecture_Docs/URI_MODEL_RUNTIME_CONTRACT.md",
}
FORBIDDEN_INPUT_PATTERNS = (
    r"(?i)\bc:\\users\\cheta\\development\\uri-agent",
    r"(?i)\b(?:git\s+(?:commit|push|reset|checkout|rebase|merge)|git\s+operation)\b",
    r"(?i)\b(?:run|execute|invoke)\s+(?:a\s+)?(?:shell|command|powershell|cmd)\b",
    r"(?i)\b(?:api[ _-]?key|password|secret|credential|token)\b",
)
FORBIDDEN_PROPOSAL_PATTERNS = (
    r"(?i)\b(?:i|qwen|coordinator)\s+(?:will|can|have|am)\s+(?:execute|run|modify|write|delete|commit|push|approve|authorize)\b",
    r"(?i)\b(?:run|execute|invoke)\s+(?:a\s+)?(?:shell|command|powershell|cmd)\b",
    r"(?i)\b(?:git\s+(?:commit|push|reset|checkout|rebase|merge)|git\s+operation)\b",
    r"(?i)\b(?:api[ _-]?key|password|secret|credential|token)\b",
    r"(?i)\b(?:redefine|replace|override)\b.{0,80}\b(?:antigravity|coordinator|control surface|architecture)\b",
)


class ValidationError(ValueError):
    """Raised for fail-closed MCP input or proposal validation."""


def _json_size(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False).encode("utf-8"))


def _ensure_safe_text(value: str, field: str) -> None:
    for pattern in FORBIDDEN_INPUT_PATTERNS:
        if re.search(pattern, value):
            raise ValidationError(f"{field} contains prohibited repository, shell, Git, or credential instruction")


def validate_task_context(task_context: Any) -> Dict[str, Any]:
    """Validate the complete, bounded context supplied by Antigravity."""
    if not isinstance(task_context, dict):
        raise ValidationError("task_context must be an object")
    if set(task_context) != INPUT_FIELDS:
        unknown = sorted(set(task_context) - INPUT_FIELDS)
        missing = sorted(INPUT_FIELDS - set(task_context))
        raise ValidationError(f"task_context fields invalid; unknown={unknown}, missing={missing}")
    if _json_size(task_context) > MAX_REQUEST_BYTES:
        raise ValidationError("task_context exceeds maximum serialized size")

    normalized: Dict[str, Any] = {}
    for field in REQUIRED_STRING_FIELDS:
        value = task_context[field]
        if not isinstance(value, str) or not value.strip() or len(value) > MAX_GOAL_CHARS:
            raise ValidationError(f"{field} must be a non-empty string within {MAX_GOAL_CHARS} characters")
        _ensure_safe_text(value, field)
        normalized[field] = value.strip()

    worker_return = task_context["worker_return"]
    if worker_return is not None and (not isinstance(worker_return, str) or len(worker_return) > MAX_WORKER_RETURN_CHARS):
        raise ValidationError("worker_return must be null or a bounded string")
    if worker_return:
        _ensure_safe_text(worker_return, "worker_return")
    normalized["worker_return"] = worker_return.strip() if worker_return else None

    for field in LIST_FIELDS:
        value = task_context[field]
        if not isinstance(value, list) or len(value) > MAX_LIST_ITEMS:
            raise ValidationError(f"{field} must be a list with at most {MAX_LIST_ITEMS} entries")
        if any(not isinstance(item, str) or not item.strip() or len(item) > MAX_LIST_ITEM_CHARS for item in value):
            raise ValidationError(f"{field} entries must be non-empty bounded strings")
        # Constraints deliberately may say "do not run shell commands"; only
        # untrusted goal/evidence/worker-return text is instruction-filtered.
        normalized[field] = [item.strip() for item in value]
    return normalized


def _system_message() -> str:
    return """You are URI's Qwen coordination layer. You only propose; you never execute,
approve, authorize, invoke tools, access files, access credentials, run shell commands, or use Git.
Return ONLY one JSON object with exactly these fields: task_understanding, recommended_action,
selected_worker, reason, allowed_scope, negative_constraints, verification_requirements, escalation,
risks, recommended_next_state. All list fields must be JSON arrays of strings. recommended_action
must be TRIAGE, PLAN, DELEGATE, REVIEW, AUDIT, or ESCALATE. selected_worker must be Antigravity,
Codex, Claude Code, or User. escalation must be none, Claude Code, or User. recommended_next_state
must be exactly one of IDLE, TRIAGED, PLANNED, DELEGATED, IMPLEMENTING, TESTING, REVIEWING, AUDITING,
AWAITING_APPROVAL, VERIFIED, COMMITTED, or PUSHED. This is advisory only."""


class OllamaCoordinatorClient:
    """Fixed local-only client; it accepts no caller-controlled URL or model."""

    def _request(self, path: str, payload: Any = None, timeout: int = 10) -> Dict[str, Any]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            OLLAMA_URL + path,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "URI-Qwen-MCP/1.0"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise RuntimeError(f"Ollama returned HTTP {response.status}")
            return json.loads(response.read().decode("utf-8"))

    def available(self) -> Tuple[bool, str]:
        try:
            tags = self._request("/api/tags")
        except (OSError, urllib.error.URLError, RuntimeError, json.JSONDecodeError) as exc:
            return False, f"Ollama unavailable: {exc}"
        installed = {entry.get("name") for entry in tags.get("models", [])}
        if MODEL not in installed:
            return False, f"Required model {MODEL!r} is unavailable"
        return True, "available"

    def coordinate(self, task_context: Mapping[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        request = {
            "model": MODEL,
            "stream": False,
            "messages": [
                {"role": "system", "content": _system_message()},
                {"role": "user", "content": json.dumps(task_context, ensure_ascii=False)},
            ],
            "options": {"num_ctx": NUM_CTX, "temperature": TEMPERATURE},
        }
        started = time.monotonic()
        response = self._request("/api/chat", request, timeout=TIMEOUT_SECONDS)
        metadata = {
            "model": MODEL,
            "context_limit": NUM_CTX,
            "latency_ms": round((time.monotonic() - started) * 1000),
            "prompt_eval_count": response.get("prompt_eval_count"),
            "eval_count": response.get("eval_count"),
        }
        return response, metadata


def _validate_string(value: Any, name: str, maximum: int = 2_000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValidationError(f"proposal.{name} must be a non-empty bounded string")
    return value.strip()


def _validate_string_list(value: Any, name: str) -> List[str]:
    if not isinstance(value, list) or len(value) > MAX_LIST_ITEMS:
        raise ValidationError(f"proposal.{name} must be a bounded list")
    return [_validate_string(item, name, MAX_LIST_ITEM_CHARS) for item in value]


def validate_proposal(raw_content: Any, task_context: Mapping[str, Any]) -> Dict[str, Any]:
    """Parse Qwen's JSON proposal and ensure it cannot claim authority."""
    if not isinstance(raw_content, str) or len(raw_content.encode("utf-8")) > MAX_PROPOSAL_BYTES:
        raise ValidationError("Qwen proposal is missing or oversized")
    cleaned = re.sub(r"<think>.*?</think>", "", raw_content, flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        proposal = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValidationError("Qwen proposal is not strict JSON") from exc
    if not isinstance(proposal, dict) or set(proposal) != PROPOSAL_FIELDS:
        raise ValidationError("proposal fields are invalid")

    normalized = {
        "task_understanding": _validate_string(proposal["task_understanding"], "task_understanding"),
        "recommended_action": _validate_string(proposal["recommended_action"], "recommended_action", 32),
        "selected_worker": _validate_string(proposal["selected_worker"], "selected_worker", 32),
        "reason": _validate_string(proposal["reason"], "reason"),
        "allowed_scope": _validate_string_list(proposal["allowed_scope"], "allowed_scope"),
        "negative_constraints": _validate_string_list(proposal["negative_constraints"], "negative_constraints"),
        "verification_requirements": _validate_string_list(proposal["verification_requirements"], "verification_requirements"),
        "escalation": _validate_string(proposal["escalation"], "escalation", 32),
        "risks": _validate_string_list(proposal["risks"], "risks"),
        "recommended_next_state": _validate_string(proposal["recommended_next_state"], "recommended_next_state", 32),
    }
    if normalized["recommended_action"] not in VALID_ACTIONS:
        raise ValidationError("proposal recommended_action is not allowed")
    if normalized["selected_worker"] not in VALID_WORKERS or normalized["selected_worker"] == "Gemma 3":
        raise ValidationError("proposal selected_worker is not allowed")
    if normalized["escalation"] not in VALID_ESCALATIONS:
        raise ValidationError("proposal escalation is not allowed")
    if normalized["recommended_next_state"] not in VALID_STATES:
        raise ValidationError("proposal recommended_next_state is not allowed")
    if not set(normalized["allowed_scope"]).issubset(set(task_context["allowed_scope"])):
        raise ValidationError("proposal expands the allowed scope")
    if set(normalized["allowed_scope"]) & PROTECTED_PATHS:
        raise ValidationError("proposal touches a protected path")

    combined = json.dumps(normalized, ensure_ascii=False)
    for pattern in FORBIDDEN_PROPOSAL_PATTERNS:
        if re.search(pattern, combined):
            raise ValidationError("proposal claims prohibited authority or requests a prohibited capability")
    security_task = re.search(r"(?i)\b(?:security|authorization|auth|route)\b", task_context["goal"])
    if security_task and normalized["escalation"] not in {"Claude Code", "User"}:
        raise ValidationError("security or authorization task bypasses required escalation")
    return normalized


class QwenCoordinatorMcp:
    """One-operation application service, kept testable apart from stdio."""

    def __init__(self, client: OllamaCoordinatorClient | None = None):
        self._client = client or OllamaCoordinatorClient()

    def coordinate(self, task_context: Any) -> Dict[str, Any]:
        try:
            context = validate_task_context(task_context)
        except ValidationError as exc:
            return {"status": "invalid_request", "proposal": None, "model_metadata": {"model": MODEL}, "error": str(exc)}
        available, message = self._client.available()
        if not available:
            return {"status": "unavailable", "proposal": None, "model_metadata": {"model": MODEL}, "error": message}
        try:
            response, metadata = self._client.coordinate(context)
            proposal = validate_proposal(response.get("message", {}).get("content"), context)
        except (ValidationError, OSError, urllib.error.URLError, RuntimeError, json.JSONDecodeError) as exc:
            return {"status": "invalid_proposal", "proposal": None, "model_metadata": {"model": MODEL}, "error": str(exc)}
        return {"status": "ok", "proposal": proposal, "model_metadata": metadata}


TOOL = {
    "name": "coordinate",
    "description": "Return an untrusted Qwen coordination proposal from curated task context; never executes work.",
    "inputSchema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["task_context"],
        "properties": {"task_context": {"type": "object", "additionalProperties": False}},
    },
}


def _result(request_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle_message(message: Any, service: QwenCoordinatorMcp) -> Dict[str, Any] | None:
    """Handle one newline-delimited JSON-RPC MCP message without side effects."""
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return _error(message.get("id") if isinstance(message, dict) else None, -32600, "Invalid JSON-RPC request")
    method, request_id = message.get("method"), message.get("id")
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return _result(request_id, {"protocolVersion": message.get("params", {}).get("protocolVersion", "2024-11-05"), "capabilities": {"tools": {}}, "serverInfo": {"name": "uri-qwen-coordinator", "version": "1.0.0"}})
    if method == "tools/list":
        return _result(request_id, {"tools": [TOOL]})
    if method == "tools/call":
        params = message.get("params", {})
        if params.get("name") != "coordinate" or set(params) - {"name", "arguments"}:
            return _error(request_id, -32602, "Only coordinate(task_context) is available")
        arguments = params.get("arguments")
        if not isinstance(arguments, dict) or set(arguments) != {"task_context"}:
            return _error(request_id, -32602, "coordinate requires exactly task_context")
        result = service.coordinate(arguments["task_context"])
        return _result(request_id, {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}], "isError": result["status"] != "ok"})
    return _error(request_id, -32601, "Method not found")


def main(stdin: Iterable[str] = sys.stdin, stdout: Any = sys.stdout) -> None:
    service = QwenCoordinatorMcp()
    for line in stdin:
        try:
            response = handle_message(json.loads(line), service)
        except json.JSONDecodeError:
            response = _error(None, -32700, "Parse error")
        except Exception as exc:  # Protocol loop must remain fail-closed.
            print(f"URI Qwen MCP internal error: {exc}", file=sys.stderr)
            response = _error(None, -32603, "Internal error")
        if response is not None:
            stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            stdout.flush()


if __name__ == "__main__":
    main()
