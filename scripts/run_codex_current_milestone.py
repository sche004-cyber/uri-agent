"""Single persistent Codex launcher for URI milestone execution.

Reads the currently authorized milestone and task directly from:
- docs/governance/URI_ACTIVE_MILESTONE.md
- docs/governance/URI_AGENT_RELAY.md

This script filename and invocation remain constant across all milestones,
eliminating per-milestone host permission boundaries.
"""

import os
import re
import subprocess
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODEX_CMD = r"C:\Users\cheta\AppData\Roaming\npm\codex.cmd"
ACTIVE_MILESTONE_PATH = os.path.join(REPO_ROOT, "docs", "governance", "URI_ACTIVE_MILESTONE.md")
AGENT_RELAY_PATH = os.path.join(REPO_ROOT, "docs", "governance", "URI_AGENT_RELAY.md")


def load_file_content(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Required governance file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def get_current_milestone_and_state(content: str):
    milestone_match = re.search(r"\*\*CURRENT MILESTONE:\*\*\s*\n([^\n]+)", content)
    state_match = re.search(r"\*\*CURRENT STATE:\*\*\s*\n([^\n]+)", content)
    milestone = milestone_match.group(1).strip() if milestone_match else None
    state = state_match.group(1).strip() if state_match else None
    return milestone, state


def get_current_relay_handoff(content: str):
    """Parse the CURRENT HANDOFF section from URI_AGENT_RELAY.md."""
    match = re.search(r"## CURRENT HANDOFF\s*\n(.*?)(?:\n---|\n## PREVIOUS HANDOFF|\Z)", content, re.DOTALL)
    if not match:
        raise ValueError("Could not locate ## CURRENT HANDOFF in URI_AGENT_RELAY.md")
    section = match.group(1)

    get_field = lambda field: (
        re.search(rf"\*\*{field}:\*\*\s*\n?([^\n]+)", section).group(1).strip()
        if re.search(rf"\*\*{field}:\*\*\s*\n?([^\n]+)", section)
        else None
    )

    handoff = {
        "from": get_field("FROM"),
        "to": get_field("TO"),
        "milestone": get_field("MILESTONE"),
        "handoff_type": get_field("HANDOFF TYPE"),
        "status": get_field("STATUS"),
    }

    # Extract authoritative artifacts
    artifacts_match = re.search(r"\*\*AUTHORITATIVE ARTIFACTS:\*\*\s*\n(.*?)(?:\n\*\*|\Z)", section, re.DOTALL)
    artifacts = []
    if artifacts_match:
        for line in artifacts_match.group(1).splitlines():
            line = line.strip().lstrip("-* ").strip("`")
            if line:
                artifacts.append(line)
    handoff["artifacts"] = artifacts

    return handoff, section


def main():
    print(f"=== URI Persistent Codex Runner ===", flush=True)
    print(f"Workspace: {REPO_ROOT}", flush=True)

    # 1. Read active milestone
    milestone_content = load_file_content(ACTIVE_MILESTONE_PATH)
    milestone, state = get_current_milestone_and_state(milestone_content)
    print(f"Current Milestone: {milestone}", flush=True)
    print(f"Current State:     {state}", flush=True)

    if not milestone or not state:
        print("ERROR: Unable to parse CURRENT MILESTONE or CURRENT STATE from URI_ACTIVE_MILESTONE.md", file=sys.stderr)
        sys.exit(1)

    if "NOT AUTHORIZED" in state.upper():
        print(f"ERROR: Current milestone state is '{state}'. Execution is NOT AUTHORIZED.", file=sys.stderr)
        sys.exit(1)

    # 2. Read agent relay handoff
    relay_content = load_file_content(AGENT_RELAY_PATH)
    handoff, handoff_text = get_current_relay_handoff(relay_content)
    print(f"Handoff Target:    {handoff['to']} (from {handoff['from']})", flush=True)
    print(f"Handoff Type:      {handoff['handoff_type']}", flush=True)
    print(f"Handoff Status:    {handoff['status']}", flush=True)

    if handoff.get("to") != "Codex":
        print(f"NOTICE: Current handoff recipient is '{handoff.get('to')}', not 'Codex'. Nothing for Codex to execute.", file=sys.stderr)
        sys.exit(0)

    # 3. Locate task prompt
    # Search artifacts for a task directive file (.txt)
    task_prompt = None
    task_path_used = None
    for art in handoff.get("artifacts", []):
        if art.endswith(".txt") and os.path.exists(os.path.join(REPO_ROOT, art)):
            task_path_used = os.path.join(REPO_ROOT, art)
            with open(task_path_used, "r", encoding="utf-8") as f:
                task_prompt = f.read()
            break

    if not task_prompt:
        # Fall back to handoff text itself if no dedicated task file exists
        print("No task .txt file found in artifacts; using structured handoff from URI_AGENT_RELAY.md as prompt.")
        task_prompt = handoff_text
    else:
        print(f"Loaded Task Directive from: {task_path_used}", flush=True)

    # 4. Check Codex CLI availability
    if not os.path.exists(CODEX_CMD):
        print(f"ERROR: Codex command not found at {CODEX_CMD}", file=sys.stderr)
        sys.exit(1)

    # 5. Launch Codex
    print(f"\nLaunching Codex CLI for milestone '{milestone}'...", flush=True)
    cmd = [
        CODEX_CMD,
        "exec",
        "--dangerously-bypass-approvals-and-sandbox",
        "-C",
        REPO_ROOT,
        "-",
    ]

    creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        creationflags=creation_flags,
    )

    process.stdin.write(task_prompt)
    process.stdin.close()

    print(f"Codex process started (PID {process.pid}). Streaming output:\n", flush=True)

    for line in iter(process.stdout.readline, ""):
        sys.stdout.write(line)
        sys.stdout.flush()

    process.stdout.close()
    return_code = process.wait()

    print(f"\nCodex execution completed with exit code {return_code}.")
    sys.exit(return_code)


if __name__ == "__main__":
    main()
