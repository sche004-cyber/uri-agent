# Terminal, Filesystem, and Development Permissions Policy

This rule governs development autonomy, workspace boundaries, and release separation for all authorized development agents (Antigravity, Gemma, and task subagents) in the AO-4 development operating model.

---

## 1. Primary Workspace Autonomy

**Primary Workspace:** `C:\Users\cheta\Development\uri-agent`

Agents have full development autonomy within the URI workspace for an active or accepted milestone, including:
- Inspecting files and directories.
- Creating, editing, renaming, and deleting project files.
- Executing Python and the project `.venv` (`python`, `python.exe`, `.venv\Scripts\python.exe`).
- Running `pytest` and test collection routines.
- Running Flutter and Dart tooling (`flutter test`, `flutter analyze`, etc.).
- Running and querying local Ollama instances.
- Invoking configured MCP workers and worker bridges.
- Executing required project scripts.
- Inspecting git state (`git status`, `git diff`, `git log`, `git show`, `git branch`).
- Performing other ordinary development operations required by the accepted task.

Agents do **NOT** need to repeatedly prompt the user for permission when performing operations that fall within this authorized development scope.

---

## 2. Task-Scoped Terminal Access Outside the URI Workspace

Terminal commands and filesystem access outside the URI workspace may be used autonomously **ONLY** when BOTH conditions are satisfied:

1. **Direct Requirement:** The operation is directly required to complete a task that has already been explicitly defined and authorized by the current AO-4 loop; **AND**
2. **Minimum Scope:** The operation is strictly limited to the minimum external scope necessary to complete that task.

### Permitted External Operations Examples
- Inspecting or configuring Ollama models and endpoints.
- Invoking locally installed development runtimes (e.g. system Python, Flutter SDK, Dart SDK).
- Interacting with local MCP server configurations required by the URI development loop.
- Inspecting tool/runtime configuration necessary to diagnose an active URI development issue.
- Using an external executable or runtime required by the accepted task.

---

## 3. Strict Outside-Workspace Boundaries

Agents must **NOT** interpret external task-scoped authority as unrestricted access to the user's host system.

### Prohibitions
- **NO** browsing of unrelated personal files or directories.
- **NO** inspection of unrelated private data.
- **NO** accessing credentials, secret stores, or auth material unless the accepted task explicitly specifies controlled handling of that credential within the established security architecture.
- **NO** accessing sensitive toolchain/identity stores (e.g. `.ssh`, `.aws`, `.gnupg`) merely for convenience.
- **NO** weakening security controls to circumvent an approval gate.
- **NO** granting broader permissions than the active task requires.

### Boundary Protocol
- Always use the narrowest possible path and command scope.
- If a required operation would exceed the defined task scope or requires establishing a new security boundary, **STOP** and surface it to the User rather than expanding permissions autonomously.

---

## 4. Release Authority Remains Separate

**Terminal and development autonomy does NOT grant release authority.**

Antigravity and Gemma may perform all development and audit operations necessary for the authorized task, including task-scoped operations outside the URI workspace, but they must **NOT**:
- `git commit`
- `git push`
- bypass Claude's final verification
- declare a milestone `VERIFIED`

**Claude Code** remains the sole final verification and release authority. After Claude independently confirms `VERIFIED`, Claude performs the milestone commit and push.

---

## 5. Agent Invocation Authority & Verification Handoff

Per [.agents/rules/agent_invocation_authority.md](agent_invocation_authority.md), agents are authorized to autonomously invoke and communicate with:
1. **Local Gemma 4 / Ollama worker infrastructure** (including Ollama endpoints, local MCP bridge scripts, and task-scoped scratch execution paths).
2. **Claude Code verification handoff** (including named pipe IPC scripts and designated handoff tooling under `scripts/` or task-scoped scratch paths).

When a milestone implementation or remediation audit is complete and the milestone state reaches `VERIFYING`, Antigravity is authorized to execute handoff scripts to deliver the verification task package directly to the active Claude Code CLI session via its local IPC pipe without interactive prompts.

