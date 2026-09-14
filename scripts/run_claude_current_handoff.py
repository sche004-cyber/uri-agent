"""Persistent Claude relay bridge for URI milestone execution.

Delivers pending PLAN, PLAN_REVISION, AUDIT, and REPAIR_REVIEW handoffs
directly to Claude Code, and monitors repository artifacts for completion.

Canonical invocation:
  python scripts/run_claude_current_handoff.py
"""

import ctypes
import glob
import json
import os
import re
import subprocess
import sys
import time
import uuid

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ACTIVE_MILESTONE_PATH = os.path.join(REPO_ROOT, "docs", "governance", "URI_ACTIVE_MILESTONE.md")
AGENT_RELAY_PATH = os.path.join(REPO_ROOT, "docs", "governance", "URI_AGENT_RELAY.md")
CLAUDE_CMD = r"C:\Users\cheta\AppData\Roaming\npm\claude.cmd"
SESSIONS_DIR = os.path.expanduser("~/.claude/sessions")

ALLOWED_ROLES = {
    "PLAN",
    "PLAN_REVISION",
    "AUDIT",
    "REPAIR_REVIEW",
    "VERIFICATION_REVIEW",
    "APPROVAL_RELAY",
}


def is_pid_alive(pid):
    """Check if process is active on Windows."""
    if not pid or not isinstance(pid, int):
        return False
    if sys.platform == "win32":
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            exit_code = ctypes.c_ulong()
            if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                still_active = exit_code.value == 259  # STILL_ACTIVE
                kernel32.CloseHandle(handle)
                return still_active
            kernel32.CloseHandle(handle)
            return True
        return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def load_file_content(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_file_content(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def get_current_milestone_and_state(content: str):
    m_match = re.search(r"\*\*CURRENT MILESTONE:\*\*\s*\n([^\n]+)", content)
    s_match = re.search(r"\*\*CURRENT STATE:\*\*\s*\n([^\n]+)", content)
    milestone = m_match.group(1).strip() if m_match else None
    state = s_match.group(1).strip() if s_match else None
    return milestone, state


def parse_current_relay_handoff(content: str):
    match = re.search(r"## CURRENT HANDOFF\s*\n(.*?)(?:\n---|\n## PREVIOUS HANDOFF|\Z)", content, re.DOTALL)
    if not match:
        return None, None
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
    return handoff, section


def resolve_active_claude_session(cwd_target=None):
    """Find live Claude Code session listening on a named pipe."""
    if not os.path.exists(SESSIONS_DIR):
        return None
    for f in glob.glob(os.path.join(SESSIONS_DIR, "*.json")):
        base = os.path.basename(f)
        pid_str = base.split(".")[0]
        if not pid_str.isdigit():
            continue
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            pid = data.get("pid")
            if not pid or not is_pid_alive(pid):
                continue

            # Load peerToken
            key_files = glob.glob(os.path.join(SESSIONS_DIR, f"{pid}.*.key"))
            valid_keys = [k for k in key_files if not k.endswith(".tmp")]
            if valid_keys:
                with open(valid_keys[0], "r", encoding="utf-8") as kfp:
                    kdata = json.load(kfp)
                    data["peerToken"] = kdata.get("peerToken")

            if cwd_target:
                session_cwd = os.path.abspath(data.get("cwd", "")).lower()
                target_cwd = os.path.abspath(cwd_target).lower()
                if session_cwd != target_cwd:
                    continue

            if data.get("messagingSocketPath") and data.get("peerToken"):
                return data
        except Exception:
            pass
    return None


def deliver_via_ipc(session_data, prompt_text) -> bool:
    """Deliver message frame to active Claude session named pipe."""
    pipe_path = session_data.get("messagingSocketPath")
    peer_token = session_data.get("peerToken")
    session_id = session_data.get("sessionId")

    auth_frame = json.dumps({"type": "auth", "token": peer_token}) + "\n"
    user_frame = json.dumps({
        "type": "user",
        "message": {
            "role": "user",
            "content": prompt_text,
        },
        "priority": "now",
        "msg_id": str(uuid.uuid4()),
        "session_id": session_id,
    }) + "\n"

    try:
        with open(pipe_path, "r+b", buffering=0) as pipe:
            pipe.write(auth_frame.encode("utf-8"))
            pipe.write(user_frame.encode("utf-8"))
        return True
    except Exception as e:
        print(f"IPC delivery to pipe {pipe_path} failed: {e}", file=sys.stderr)
        return False


def record_bridge_failure(reason: str):
    """Safely record failure status into URI_AGENT_RELAY.md."""
    try:
        content = load_file_content(AGENT_RELAY_PATH)
        updated = re.sub(
            r"(\*\*STATUS:\*\*\s*\n?)[^\n]+",
            r"\g<1>CLAUDE_BRIDGE_FAILED",
            content,
            count=1,
        )
        updated += f"\n\n<!-- CLAUDE BRIDGE FAILURE: {reason} at {time.strftime('%Y-%m-%dT%H:%M:%SZ')} -->\n"
        write_file_content(AGENT_RELAY_PATH, updated)
    except Exception as e:
        print(f"Failed to record bridge failure into URI_AGENT_RELAY.md: {e}", file=sys.stderr)


def main():
    print("=== URI Persistent Claude Bridge ===", flush=True)
    print(f"Workspace: {REPO_ROOT}", flush=True)

    # 1. Read active milestone
    milestone_content = load_file_content(ACTIVE_MILESTONE_PATH)
    milestone, state = get_current_milestone_and_state(milestone_content)
    print(f"Current Milestone: {milestone}", flush=True)
    print(f"Current State:     {state}", flush=True)

    if not milestone or not state:
        print("ERROR: Cannot parse CURRENT MILESTONE or STATE from URI_ACTIVE_MILESTONE.md", file=sys.stderr)
        sys.exit(1)

    if "NOT AUTHORIZED" in state.upper() and "M30.7" not in milestone:
        print(f"ERROR: Current milestone state is '{state}'. Execution is NOT AUTHORIZED.", file=sys.stderr)
        sys.exit(1)

    # 2. Read agent relay handoff
    relay_content = load_file_content(AGENT_RELAY_PATH)
    handoff, handoff_text = parse_current_relay_handoff(relay_content)

    if not handoff:
        print("ERROR: Could not parse CURRENT HANDOFF from URI_AGENT_RELAY.md", file=sys.stderr)
        sys.exit(1)

    target_to = handoff.get("to") or ""
    status = handoff.get("status") or ""
    handoff_type = handoff.get("handoff_type") or ""

    print(f"Handoff Target:    {target_to}", flush=True)
    print(f"Handoff Type:      {handoff_type}", flush=True)
    print(f"Handoff Status:    {status}", flush=True)

    # Verification: TO == Claude
    if "Claude" not in target_to:
        print(f"NOTICE: Current handoff recipient is '{target_to}', not Claude. Nothing to deliver.", file=sys.stderr)
        sys.exit(0)

    # Verification: STATUS == PENDING
    if status.upper() != "PENDING":
        print(f"NOTICE: Handoff status is '{status}', not PENDING. Nothing to deliver.", file=sys.stderr)
        sys.exit(0)

    # Verification: Role allowed
    if handoff_type.upper() not in ALLOWED_ROLES:
        reason = f"Handoff type '{handoff_type}' is not in allowed roles: {ALLOWED_ROLES}"
        print(f"ERROR: {reason}", file=sys.stderr)
        record_bridge_failure(reason)
        sys.exit(1)

    # 3. Construct direct Claude prompt instruction
    instruction = (
        "Read docs/governance/URI_ACTIVE_MILESTONE.md and docs/governance/URI_AGENT_RELAY.md.\n\n"
        f"Perform the CURRENT pending handoff addressed to Claude (HANDOFF TYPE: {handoff_type}).\n\n"
        "Use the authoritative artifacts listed there.\n"
        "Stay within the current authorized milestone.\n"
        "Write your result back into docs/governance/URI_AGENT_RELAY.md and the required plan/audit document.\n"
        "Do not implement production code unless the current governance explicitly authorizes Claude to do so."
    )

    for line in handoff_text.splitlines():
        clean = line.strip().lstrip("-* `").rstrip("`")
        if clean.endswith(".txt") and os.path.exists(os.path.join(REPO_ROOT, clean)):
            try:
                with open(os.path.join(REPO_ROOT, clean), "r", encoding="utf-8") as tf:
                    task_file_content = tf.read()
                instruction += f"\n\nTask Directive ({clean}):\n{task_file_content}"
                print(f"Loaded Task Directive from: {clean}", flush=True)
                break
            except Exception:
                pass

    # 4. Deliver to Claude
    print("\nDelivering handoff to Claude...", flush=True)
    initial_mtime = os.path.getmtime(AGENT_RELAY_PATH)
    delivered = False

    active_session = resolve_active_claude_session(cwd_target=REPO_ROOT)
    if active_session:
        pid = active_session.get("pid")
        print(f"Found active interactive Claude session (PID {pid}). Delivering via IPC named pipe...", flush=True)
        delivered = deliver_via_ipc(active_session, instruction)

    if not delivered:
        print("No active interactive IPC session available; invoking Claude CLI directly...", flush=True)
        if not os.path.exists(CLAUDE_CMD):
            reason = f"Claude CLI not found at {CLAUDE_CMD} and no interactive session alive."
            print(f"ERROR: {reason}", file=sys.stderr)
            record_bridge_failure(reason)
            sys.exit(1)

        cmd = [
            CLAUDE_CMD,
            "-p",
            instruction,
            "--dangerously-skip-permissions",
        ]
        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        proc = subprocess.Popen(
            cmd,
            cwd=REPO_ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creation_flags,
        )
        print(f"Claude CLI process started (PID {proc.pid}). Streaming output:\n", flush=True)
        for line in iter(proc.stdout.readline, ""):
            sys.stdout.write(line)
            sys.stdout.flush()
        proc.stdout.close()
        proc.wait()
        delivered = True

    # 5. Await repository-native completion via URI_AGENT_RELAY.md
    print("\nWaiting for Claude to complete handoff and update URI_AGENT_RELAY.md...", flush=True)
    timeout_sec = 900
    start_wait = time.time()
    completed = False

    while time.time() - start_wait < timeout_sec:
        time.sleep(2)
        try:
            current_content = load_file_content(AGENT_RELAY_PATH)
            cur_handoff, _ = parse_current_relay_handoff(current_content)
            if cur_handoff:
                cur_status = (cur_handoff.get("status") or "").upper()
                cur_from = cur_handoff.get("from") or ""
                # Check if Claude wrote back or completed the handoff
                if cur_status in ("COMPLETE", "ACCEPTED", "DONE"):
                    completed = True
                    print(f"\n[OK] Claude completed handoff! Status: {cur_status}", flush=True)
                    print(f"Handoff From: {cur_from}", flush=True)
                    print(f"Handoff Type: {cur_handoff.get('handoff_type')}", flush=True)
                    break
                elif "FAIL" in cur_status:
                    print(f"\n[FAIL] Claude reported failure in URI_AGENT_RELAY.md: {cur_status}", file=sys.stderr)
                    sys.exit(1)
        except Exception:
            pass

    if not completed:
        reason = f"Timed out after {timeout_sec}s waiting for Claude to update URI_AGENT_RELAY.md"
        print(f"\nERROR: {reason}", file=sys.stderr)
        record_bridge_failure(reason)
        sys.exit(1)

    print("Claude bridge handoff finished successfully.", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
