"""Execute Codex for Forensic UI Failure Audit via stdin piping."""
import subprocess
import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

workspace_dir = r"C:\Users\cheta\Development\uri-agent"
codex_cmd = r"C:\Users\cheta\AppData\Roaming\npm\codex.cmd"
task_file = os.path.join(workspace_dir, "uri_workspace", "dev_workflow", "tasks", "codex_visual_failure_audit_task.txt")

with open(task_file, "r", encoding="utf-8") as f:
    task_prompt = f.read()

print(f"Launching Codex CLI on {workspace_dir} with Forensic UI Failure Audit task...", flush=True)

cmd = [
    codex_cmd,
    "exec",
    "--dangerously-bypass-approvals-and-sandbox",
    "-C",
    workspace_dir,
    "-",
]

process = subprocess.Popen(
    cmd,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    encoding="utf-8",
    errors="replace",
    bufsize=1,
)

process.stdin.write(task_prompt)
process.stdin.close()

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
