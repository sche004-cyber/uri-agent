# Autonomous Python Execution Authority & Environment Boundaries

For active AO-4 development milestones, Antigravity and authorized worker agents have explicit, autonomous authority to execute Python within the URI project environment without repeatedly prompting the user for approval for routine operations.

## Authorized Python Executables & Paths

The following executable aliases and paths are explicitly authorized for routine development execution:
- `python`
- `python.exe`
- `.\.venv\Scripts\python.exe`
- `.venv\Scripts\python.exe`
- `C:\Users\cheta\Development\uri-agent\.venv\Scripts\python.exe`

## Authorized Operational Scope

Python execution is permitted without interactive prompts when fulfilling tasks defined by the active or accepted AO-4 development loop, including:
1. **URI Scripts & Tooling:** Running repository scripts, CLI utilities, and task coordinators.
2. **Automated Testing:** Running `pytest`, test runners, test discovery, and collection.
3. **MCP Infrastructure:** Launching, managing, and connecting to local MCP servers (including Gemma/Ollama worker bridge scripts).
4. **Validation & Audit:** Running AST scans, boundary checkers, import checks, line-count verifiers, and audit scripts.
5. **State Inspection:** Inspecting project runtime state, configuration dictionaries, and database/store models.
6. **Worker Orchestration:** Executing local Gemma/Ollama worker MCP bridges, payload generation, and return parsing.
7. **Flutter/Dart Support:** Running Python-based helper or conversion scripts that support the UI/backend test or build pipelines.

## Security & Filesystem Boundaries

1. **Scoped Workspace Operations:**
   - All filesystem operations and process cwd must remain scoped to the primary URI repository (`C:\Users\cheta\Development\uri-agent`) and the Antigravity IDE artifact/scratch directory.
   - Task-scoped execution outside the workspace is permitted only when strictly required by a configured tool (e.g. global virtualenvs or local Ollama endpoints).
   - Unrestricted access to unrelated personal files, personal user directories, browser profiles, and credential vaults is strictly prohibited.

2. **Release Authority Prohibition (EXECUTION != RELEASE):**
   - Python execution authority does NOT grant `git commit`, `git push`, or milestone release authority to Antigravity or Gemma.
   - Claude Code retains exclusive, non-delegable authority for final independent verification (`VERIFIED`) and subsequent `git commit` and `git push`.
