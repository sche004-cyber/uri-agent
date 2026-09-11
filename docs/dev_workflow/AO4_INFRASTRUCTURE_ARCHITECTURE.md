# AO-4 Development Infrastructure & Agent Operating Architecture

This document records the recovered and verified AO-4 multi-agent development infrastructure, permission model, and execution loop for `uri-agent`.

---

## 1. Canonical Agent Roles & Authority Matrix

| Role / Agent | Principal Responsibility | Permissions & Authority | Prohibited Actions |
| :--- | :--- | :--- | :--- |
| **Claude Code (CLI)** | **Architecture Planner & Final Approver**<br>Plans milestones, conducts pre-milestone audit, performs independent final verification (`VERIFIED` / `NOT VERIFIED`). | Final authority for release eligibility.<br>Sole automated authority to perform milestone `git commit` and `git push` after `VERIFIED`. | Does not implement milestone code changes. |
| **Antigravity (Gemini 3.8 Flash)** | **Manager & Loop Orchestrator**<br>Coordinates development cycle, tracks handoffs, prepares bounded task packages, audits Gemma's implementation, applies bounded fixes. | Repository read/write within `uri-agent` workspace.<br>Dispatches tasks to Gemma via MCP.<br>Owns UI/UX implementation and response presentation work where assigned. | Cannot replace Claude's final verification.<br>Cannot perform milestone release commit/push.<br>Cannot modify protected authority files. |
| **Gemma 4 12B (Local Ollama)** | **Primary Implementation Worker**<br>Implements code changes, updates tests, and addresses defect reports strictly within assigned scope. | Writes code files within `allowed_scope` via MCP.<br>Generates structured `GEMMA RETURN REPORT`. | **Zero Git authority** (no commit/push).<br>**Zero architectural authority**.<br>Cannot declare `VERIFIED`.<br>Cannot touch out-of-scope/protected files. |
| **Specialist / Design Agents** | **Recommendation & Design Only**<br>Proposes UI layouts, interaction patterns, URI response presentation, usability improvements. | Recommends designs and specifications. | **Must NOT implement changes**.<br>Recommendations must be reviewed by Claude for architectural viability before adoption. |
| **User** | **Final Authority & Escalation Gate**<br>Accepts milestone plans, resolves genuine architectural escalations. | Unrestricted project ownership. | Routine implementation and remediation steps proceed autonomously under accepted scope. |

---

## 2. Invocation Architecture

```
Antigravity (Gemini 3.8 Flash)
   │
   ├─► MCP Tool: uri-gemma-worker (scripts/gemma_worker_mcp.py)
   │     └─► Local Ollama (http://127.0.0.1:11434)
   │           └─► gemma4:12b (Implementation Worker)
   │
   ├─► MCP Tool: uri-qwen-coordinator (scripts/qwen_coordinator_mcp.py) [Advisory only]
   │     └─► Local Ollama (http://127.0.0.1:11434)
   │           └─► qwen3:14b [Fallback consultation only]
   │
   ├─► Specialist / Design Subagents (e.g. flutter_a11y_agent, UI designers)
   │     └─► Layout & interaction recommendations (non-implementing)
   │
   └─► Claude Code Bridge / Workflow
         └─► Claude CLI interactive session (Planning, independent verification, release)
```

### Gemma 4 Invocation via MCP
- **Tool Name:** `gemma_implement`
- **Model ID:** `gemma4:12b` (Hardcoded; fail-closed if offline; no model substitution)
- **Configuration:** `%USERPROFILE%\.gemini\config\mcp_config.json`
- **Invocation Pattern:**
  ```json
  {
    "name": "gemma_implement",
    "arguments": {
      "task_package": {
        "task_id": "<milestone-task-id>",
        "milestone_id": "<milestone-id>",
        "goal": "<task objective>",
        "allowed_scope": ["path/to/file1.py", "path/to/file2.py"],
        "instructions": "<implementation or remediation directives>",
        "apply_to_worktree": true
      }
    }
  }
  ```

---

## 3. Permission Model & Security Boundary

### Directory Boundary
All agent file operations and execution grants are strictly confined to:
```
C:\Users\cheta\Development\uri-agent
```

### Denied Boundaries
The following paths are explicitly denied from automated agent access:
- `C:\Users\cheta\.ssh\**`
- `C:\Users\cheta\.aws\**`
- `C:\Users\cheta\.gnupg\**`
- Any paths outside the workspace root (`nonWorkspaceFileAccessPolicy: AGENT_SETTING_POLICY_ASK` and `isWorkspaceOnly: true`)

### Terminal & Git Safety
- **Auto-Execution Policy:** Project-level policy is configured (`cascadeAutoExecutionPolicy: 2` / not-enforced within allowlist) to permit uninterrupted development operations.
- **Allowed Development Commands:**
  - `python`, `python.exe`, `pytest`, `pytest.exe`
  - `.\\.venv\\Scripts\\python.exe`, `.\\.venv\\Scripts\\pytest.exe`
  - `flutter`, `dart`, `pip`
  - `ollama`, `ollama.exe`
  - `git status`, `git diff`, `git log`, `git rev-parse`, `git show`, `git branch`, `git checkout`, `git add`, `git restore`, `git fetch`
  - `powershell`, `pwsh`
- **Restricted Git Operations (Release Gate Preservation):**
  - `command(git push)` and `command(git commit)` are restricted from autonomous agent execution.
  - Claude Code CLI remains the sole executing authority for release commits and repository pushes after issuing an independent `VERIFIED` report.

---

## 4. Verification & Testing Record

- **MCP Configuration Test:** Verified `%USERPROFILE%\.gemini\config\mcp_config.json` contains valid Python virtual environment paths for `uri-qwen-coordinator` and `uri-gemma-worker`.
- **Live Ollama Inference Test:** Confirmed `gemma4:12b` communication via `gemma_worker_mcp.py` (`INFRA-LOOP-CHECK`, status `ok`, latency 20,120 ms, 449 eval tokens).
- **Workspace Inspection Test:** Verified file inspection and directory traversal on `c:\Users\cheta\Development\uri-agent`.
- **Terminal Execution Test:** Verified headless non-interactive execution of Python inside `.venv` without permission prompts.
- **Git Status Test:** Verified non-modifying git inspection without permission prompts.
- **Automated Regression Suite:** 107 tests passed (including `test_gemma_worker_mcp.py`, `test_security_boundary.py`, `test_workflow.py`).

---

## 5. Visible-Terminal Worker Execution (Observability Only)

`scripts/dev_workflow/visible_worker.py` lets the User watch a routed CLI
implementation worker (Codex today) run live in its own console window,
instead of its output being silently captured by whatever process invoked
it (previously: `scripts/run_codex_m227.py`-style scripts, which pipe
stdout invisibly). It is purely observational tooling — it changes **zero**
AO-4 authority. Codex still receives exactly the same task package and
runs exactly the same command (`codex.exe exec
--dangerously-bypass-approvals-and-sandbox -C <repo> <task text>`) it
already ran before this tool existed; Codex still has no Git authority, no
`VERIFIED` authority, and no release authority, and Antigravity remains the
only thing that invokes it programmatically. The name is deliberately
generic (not `run_codex_m227.py`-style, milestone-specific) so any future
milestone, and in principle any future CLI-based worker, reuses the same
tool — see `WORKER_COMMANDS` in the module for how a new worker type would
be added.

### 5.1 How it works

Two-phase design, because a single OS process cannot simultaneously (a)
run inside a brand-new, genuinely visible console window and (b) hand its
stdout back to the process that spawned it as a pipe — those are mutually
exclusive at the console/handle level on Windows:

1. **`launch(...)`** — called by Antigravity (or a human) from an ordinary,
   non-interactive process. Validates no other run is active for the same
   `(worker, task_id)` (§5.2), then opens a **new console window**
   (`CREATE_NEW_CONSOLE`) running this same script in `run` mode inside
   it, and **returns immediately** — the caller is never blocked waiting
   on the worker, and keeps driving the loop programmatically by polling
   the status file `launch()` hands back.
2. **`run` mode** — executes *inside* that new console window; this is the
   visible process itself. It prints the task banner, sets the console
   title to `<WORKER> - <task_id>` (never a secret), then streams the
   worker's real stdout/stderr **line-by-line, unbuffered**, to two
   places at once: the console itself (what the User watches live) and
   `output.log` in the run's directory (a persistent tee, readable after
   the window closes). On exit it writes a final, machine-readable
   `status.json` and leaves the window open with a "press Enter to
   close" prompt so the User can review the tail of the output before it
   disappears (pass `--no-pause` to skip this for fully automated runs).

Antigravity never reads the console directly — it polls `status.json`
(`visible_worker.get_status(run_dir)`) or the CLI's `status`/`check-active`
subcommands, which is the actual machine-readable completion/result
contract requirement #4 asked for; the visible console is a courtesy to
the User layered on top of it, not a replacement for it.

### 5.2 Process ownership & duplicate prevention

Every `(worker, task_id)` pair gets a lock file at
`uri_workspace/dev_workflow/locks/<worker>_<task_id>.lock` (JSON: pid,
start time, run directory — never gitignored-in-name-only, the whole
`uri_workspace/dev_workflow/` tree is excluded via `.gitignore`, it is
runtime output, not source). `launch()` refuses to start a second run for
a `(worker, task_id)` pair whose lock points at a still-live PID — no
duplicate writer is ever created for the same task. A lock whose PID is no
longer running is treated as **stale**: it is reclaimed (the new launch is
allowed), but first the abandoned run's own `status.json` is corrected
from `STARTING`/`RUNNING` to `INTERRUPTED` if it never reached a terminal
state — an abandoned run is never left looking ambiguously "maybe still
running," and is never silently reinterpreted as a success.

This scopes duplicate-prevention **per task**, not globally — a smoke-test
task and a real milestone task can run concurrently under different
`task_id`s (validated live: the M22.7 Codex implementation kept running
undisturbed, in its own pre-existing `run_codex_m227.py`-launched process,
the whole time the `DEVTEST_VISIBLE_TERMINAL` smoke test below ran
alongside it). Note the current M22.7 run itself predates this tool and
was launched directly via `run_codex_m227.py`, so it holds no lock file
here — this tool cannot retroactively see out-of-band Codex invocations it
did not launch; only tasks launched *through* `visible_worker.py` are
tracked. Do not launch a same-`task_id` run through this tool while an
equivalent out-of-band run for that same milestone is known to be active.

### 5.3 Failure / recovery behavior

- A worker exit code `!= 0` → `status.json` records `FAILED` with the real
  exit code — never reported as success.
- An unhandled exception in the runner itself (not the worker process) →
  caught, recorded as `FAILED` with the exception, status/lock are still
  written (never leaves the task un-tracked).
- The console window being closed abruptly (the `X` button, logoff,
  shutdown) → a `SetConsoleCtrlHandler`-based handler makes a best-effort
  attempt to record `INTERRUPTED` in the short grace window Windows grants
  a console control handler before tearing the process down. This is
  best-effort, not a guarantee.
- **Backstop for the above:** whether or not the handler fires, the next
  `check_active`/`get_status` call for that `(worker, task_id)`
  reconciles a dead PID still claiming `STARTING`/`RUNNING` to
  `INTERRUPTED` itself (§5.2) — so a truly silent, un-tracked crash is not
  possible through this tool's own poll path even if the in-process
  handler never runs.
- None of the above automatically starts a replacement worker — a fresh
  `launch()` call (by Antigravity, after observing a terminal status) is
  always a separate, explicit decision, never an automatic retry loop
  hidden inside this module.

### 5.4 Security

Task prompts must never carry secrets (same discipline as every other AO-4
task package — Codex implements code, it does not touch
`ProviderKeyStore`/`.env` values). The console title carries only
`<worker> - <task_id>`. This module never logs `os.environ` or any other
process-environment dump. Filesystem/shell authority is unchanged from
the pre-existing Codex invocation — this tool wraps the exact same command
`run_codex_m227.py` already ran (`--dangerously-bypass-approvals-and-sandbox`
is pre-existing project practice, not introduced here); reducing that
sandbox posture, if ever desired, is a separate decision outside this
observability feature's scope.

### 5.5 Validation record (2026-09-11)

Automated: 13 hermetic tests in `tests/dev_workflow/test_visible_worker.py`
(console spawn always mocked — no real window/process in CI), covering
launch validation, duplicate refusal, stale-lock reclamation, status
polling reconciliation, and the unchanged Codex command shape. Full
`tests/dev_workflow/` suite: 71/71 passing (58 pre-existing + 13 new),
zero regressions.

Live smoke test (manual, one-off — not part of the automated suite, since
it needs a real interactive console and a live Codex credential):
`DEVTEST_VISIBLE_TERMINAL` (the `DEVTEST` prefix marks it as tooling-test
namespace per `security_boundary.py`'s existing convention — not a real
milestone), a strictly read-only, explicitly non-destructive task ("print
a line, list top-level files, do not modify/create/delete anything, do
not commit/push"). Result: a real new console window opened and was
observable; Codex genuinely reasoned about and executed the task (visible
in `output.log`); the window streamed output live rather than buffering
until the end; a duplicate `launch()` attempt while it was active was
correctly refused with a clear error and no second process; `status.json`
correctly progressed `STARTING → RUNNING → COMPLETE` (exit code 0) and the
lock file was removed on completion; `git status` confirmed zero tracked
files were touched by the smoke task itself (the `PROJECT_MEMORY.md` /
`URI_MILESTONE_TRACKER.md` / `uri_core/...` changes present in the working
tree at the time were the genuine, concurrently-running M22.7
implementation, unaffected throughout); the M22.7 Codex process (started
independently via `run_codex_m227.py`) was confirmed still running,
untouched, both before and after the smoke test.
