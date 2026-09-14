"""Execute M22.7 Implementation via Codex CLI.

Invokes the local Codex CLI non-interactively as the primary specialist implementer
for M22.7: Usage Metering, Budgets, and Pre-Flight Ceiling Enforcement.
"""
import subprocess
import sys
import os
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

workspace_dir = r"C:\Users\cheta\Development\uri-agent"
codex_exe = r"C:\Users\cheta\AppData\Local\OpenAI\Codex\bin\7ac07f4ce733f89a\codex.exe"

if not os.path.exists(codex_exe):
    # Fallback to PATH
    codex_exe = "codex"

task_prompt = """You are CODEX, the preferred primary specialist implementer for URI milestone M22.7.

Your task is to implement M22.7: Usage Metering, Budgets, and Pre-Flight Ceiling Enforcement, exactly as specified in `docs/plans/M22.7_USAGE_METERING_PLAN.md`.

Read and adhere to `docs/plans/M22.7_USAGE_METERING_PLAN.md` completely.

### OBJECTIVE
Implement append-only per-user usage records for every real model call made by `ModelRouter`; implement a deterministic pre-flight monthly ceiling budget check wired into `ModelRouter._budget_ok()`; implement zero-model-call dashboard aggregation; and implement `GET /usage`, `GET /usage/limits`, `PUT /usage/limits` endpoints.

### DETAILED SCOPE:

1. NEW FILE `uri_core/core/usage_meter.py`:
   - `UsageRecord` (frozen dataclass):
     - `ts: str` (UTC ISO8601 string)
     - `user_id: str`
     - `session_id: Optional[str]`
     - `role: str`
     - `provider_id: Optional[str]`
     - `model: Optional[str]`
     - `prompt_tokens: Dict[str, Any]` (e.g. `{"value": Optional[int], "confidence": "KNOWN" | "UNAVAILABLE"}`)
     - `eval_tokens: Dict[str, Any]` (e.g. `{"value": Optional[int], "confidence": "KNOWN" | "UNAVAILABLE"}`)
     - `duration_seconds: Dict[str, Any]` (e.g. `{"value": Optional[float], "confidence": "KNOWN" | "UNAVAILABLE"}`)
     - `outcome: str` ("success" | "unreachable")
     - `fallback_from: List[str]`
     - `estimated_cost: Dict[str, Any]` (e.g. `{"value": None, "confidence": "UNAVAILABLE"}`)
   - CRITICAL: Never store `system` or `user` prompt text, and never store `response.content` in `UsageRecord`!
   - `UsageMeter`:
     - `record(record: UsageRecord) -> None`: append-only, writes one JSON line to `uri_workspace/users/<user_id>/usage/<YYYY-MM>.jsonl`. Uses `user_scoped_path` convention. Must NEVER raise on write failure (log warning and gracefully return).
     - `estimate_current_month_tokens(user_id: str, role: Optional[str] = None) -> int`: sums `prompt_tokens.value + eval_tokens.value` across current month records where both are `KNOWN` (UNAVAILABLE records contribute 0).

2. NEW FILE `uri_core/core/usage_ceiling_store.py`:
   - `UsageCeilingStore(user_id: str)`:
     - Stores in `uri_workspace/users/<user_id>/usage_ceiling.json`.
     - `get_ceiling() -> Optional[int]`: returns token ceiling integer, or `None` if unlimited (default is `None`).
     - `set_ceiling(value: Optional[int]) -> None`: updates ceiling.
     - `get_warn_threshold_ratio() -> float`: returns 0.8 default.

3. NEW FILE `uri_core/core/usage_aggregator.py`:
   - `aggregate_month(user_id: str, month: Optional[str] = None) -> Dict[str, Any]`:
     - Pure fold over the specified or current month's usage JSONL + static `PROVIDER_CATALOGUE`.
     - Returns totals per role, totals per provider, count of `UNAVAILABLE` records, call counts by `outcome`, and configured ceiling/warning status from `UsageCeilingStore`.
     - INVARIANT #5: Must make ZERO model calls and NEVER import `ModelProvider` or `ModelRouter`!

4. MODIFY `uri_core/core/model_router.py`:
   - `_budget_ok(provider_id: str, role: str, principal: Optional[object], system_text: str = "", user_text: str = "") -> bool`:
     - If `principal is None` or `UsageCeilingStore(principal.user_id).get_ceiling() is None`: return `True`.
     - Otherwise estimate cost via `estimate_tokens(system_text + user_text)` from `uri_core.core.context_budget`.
     - Sum with `UsageMeter.estimate_current_month_tokens(principal.user_id)`.
     - If estimated sum >= ceiling: return `False` (ceiling reached; stops this candidate and triggers fallback).
   - `attempt(...)`:
     - On successful call: call `UsageMeter().record(...)` with `outcome="success"`, tokens/duration from `ModelResponse`, and `fallback_from=tried`.
     - On exhausting candidates (`AllProvidersUnreachableError`): call `UsageMeter().record(...)` with `outcome="unreachable"` and `UNAVAILABLE` tokens/duration before raising.
     - `ProviderAuthenticationError`: do NOT record as usage (no real model call was executed).

5. MODIFY `uri_core/app/server.py`:
   - `GET /usage`: returns `aggregate_month(principal.user_id)` for the authenticated caller.
   - `GET /usage/limits`: returns current ceiling and warn threshold ratio for caller.
   - `PUT /usage/limits`: sets caller's ceiling `{"monthly_token_ceiling": int | null}`.
   - Register all three routes in the route-classification table as `USER`-tier.

6. TESTS TO CREATE (Per Plan §7):
   - `test_usage_meter_recording.py` (criteria 1-3)
   - `test_usage_meter_no_content_stored.py` (§5.1)
   - `test_usage_ceiling_budget_enforcement.py` (criteria 4-5)
   - `test_usage_aggregator_zero_model_calls.py` (criterion 6)
   - `test_usage_import_boundary.py` (criterion 7, AST check)
   - `test_usage_endpoints_isolation.py` (criterion 8)

7. CONSTRAINTS & INVARIANTS:
   - `uri_core/core/orchestrator.py`: line count must NOT increase (`wc -l` invariant #11).
   - No M22.8 client UI or ceiling-reached flows (M22.8 scope).
   - No admin cross-user dashboard.
   - Run the tests to ensure everything passes cleanly with zero regressions against the 1,385 baseline tests.

When complete, print a clear summary of all created and modified files, test results, and confirmed invariants.
"""

print(f"Launching Codex CLI on {workspace_dir}...", flush=True)

cmd = [
    codex_exe,
    "exec",
    "--dangerously-bypass-approvals-and-sandbox",
    "-C",
    workspace_dir,
    task_prompt,
]

process = subprocess.Popen(
    cmd,
    stdin=subprocess.DEVNULL,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    encoding="utf-8",
    errors="replace",
    bufsize=1,
)

print(f"Codex process started (PID {process.pid}). Streaming output...\n", flush=True)

output_lines = []
for line in iter(process.stdout.readline, ""):
    sys.stdout.write(line)
    sys.stdout.flush()
    output_lines.append(line)

process.stdout.close()
return_code = process.wait()

print(f"\nCodex execution finished with exit code {return_code}.")
sys.exit(return_code)
