"""Execute M26 Hard Reference Design via Codex CLI.

Invokes the local Codex CLI non-interactively as the specialist design worker
to implement the pixel-perfect HTML preview and update design specifications
strictly against docs/design_references/uri_dashboard_reference.jpg.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

workspace_dir = r"C:\Users\cheta\Development\uri-agent"
task_file = Path(workspace_dir) / "uri_workspace" / "dev_workflow" / "tasks" / "m26_codex_hard_reference_task.txt"

if not task_file.exists():
    print(f"Error: Task file not found: {task_file}", file=sys.stderr)
    sys.exit(1)

task_prompt = task_file.read_text(encoding="utf-8")

# Resolve Codex executable
codex_exe = shutil.which("codex") or r"C:\Users\cheta\AppData\Roaming\npm\codex.cmd"
if not os.path.exists(codex_exe):
    codex_exe = "codex"

print(f"Resolved Codex executable: {codex_exe}", flush=True)
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
