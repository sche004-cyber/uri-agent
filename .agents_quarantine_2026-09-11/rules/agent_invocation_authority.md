# Task-Scoped Agent Invocation Authority for URI AO-4 Development Loop

This policy establishes dedicated task-scoped agent invocation authority for all authorized agents (Antigravity, Gemma, Claude Code) participating in the URI AO-4 development operating model.

---

## 1. Authorized Agent Invocations

For work belonging to an already-defined URI AO-4 milestone, authorized agents may launch, execute, and interact with the following runtimes and infrastructure without interactive permission prompts:

### Gemma 4 / Ollama Worker Infrastructure
- `ollama`
- `ollama.exe`
- The configured local Gemma MCP bridge
- Its designated Python interpreter
- The MCP server scripts required to invoke Gemma

### Claude Code Verification Handoff
- The designated Claude Code CLI invocation
- The designated Claude verification bridge / IPC helper scripts
- The Python interpreter required to launch that handoff

### Designated Infrastructure & Scratch Paths
- Designated infrastructure paths under:
  `C:\Users\cheta\.gemini\antigravity-ide\brain\*\scratch\`
  **ONLY** when the files are directly involved in the current AO-4 URI implementation, audit, or verification workflow.
  *(Unrestricted access to the entire scratch tree remains prohibited.)*

---

## 2. Python Execution Authority

The URI AO-4 workflow is explicitly authorized to invoke:
- `C:\Users\cheta\Development\uri-agent\.venv\Scripts\python.exe`
- `python`
- `python.exe`

for repository work, test execution (`pytest`), MCP worker execution, verification scripts, and designated agent handoff infrastructure without interactive prompts.

---

## 3. Primary Workspace Authority

Within `C:\Users\cheta\Development\uri-agent`, Gemma, Antigravity, and designated development agents may perform all terminal, file, and test operations required by the accepted milestone without repeated interactive approval.

---

## 4. Cross-Workspace Authority

Outside the URI workspace, access is permitted **ONLY** when directly required to execute an already-defined AO-4 task, including:
- Invoking the Gemma MCP bridge;
- Communicating with local Ollama (`localhost:11434`);
- Invoking and communicating with active Claude Code sessions;
- Reading and writing designated Antigravity handoff/scratch artifacts;
- Executing designated verification infrastructure.

**Strict Prohibitions:**
Access to personal files, browser data, credential stores, SSH keys (`.ssh`), AWS credentials (`.aws`), GPG credentials (`.gnupg`), or unrelated projects is strictly prohibited.

---

## 5. Release Gate — Unchanged

Antigravity and Gemma remain strictly prohibited from:
- `git commit`
- `git push`
- Declaring a milestone `VERIFIED`

Claude Code remains the sole release authority after independent verification.

---

## 6. Development Loop Operating Roles

- **Gemma 4 12B:** Implementation worker.
- **Antigravity:** Loop manager, auditor, UI/response manager, bounded fixer.
- **Claude Code:** Architecture planner, independent final auditor, and sole release authority.

Agents shall execute these already-authorized AO-4 operations autonomously without stopping to ask the user for routine permissions.
