"""Visible-terminal execution for CLI-based AO-4 implementation workers.

Observability-only tooling: lets the User watch a routed implementation
worker (Codex today; any future CLI-based worker via WORKER_COMMANDS) run
live in its own console window, instead of its output being silently
captured/piped by whatever invoked it. This changes nothing about AO-4
authority - it does not grant Codex (or any worker) Git authority, does
not let it declare VERIFIED, and does not touch Claude's sole release
gate. It is purely "can the User see the work happen," layered around the
exact same worker invocation that already runs today.

Boundary Guarantee: Development-only tooling. Not part of URI runtime,
never imported by it, never shipped inside it.

---------------------------------------------------------------------------
Two-phase design
---------------------------------------------------------------------------

`launch` (called by Antigravity, or a human, from an ordinary/headless
process): validates there is no other active run for the same
(worker, task_id), then opens a brand-new visible console window running
THIS SAME SCRIPT in `run` mode, and returns immediately (non-blocking) -
the caller keeps driving the loop programmatically and polls the returned
status file for completion, it does not sit blocked watching a pipe.

`run` (executes INSIDE the new console window - this is the visible
process itself): prints the task banner, streams the worker's real stdout
to both that console (visible, unbuffered) and a persistent log file
(tee), and on exit writes a final machine-readable status file the
launcher/poller can trust.

---------------------------------------------------------------------------
Per-task state on disk (all under uri_workspace/dev_workflow/, a
development-only directory - never read by the URI runtime)
---------------------------------------------------------------------------

  uri_workspace/dev_workflow/locks/<worker>_<task_id>.lock
      JSON: {"pid": <int>, "started_at": <iso8601>, "run_dir": <path>}
      Presence + a live PID means "do not launch a duplicate for this
      exact (worker, task_id)". A lock whose PID is no longer running is
      stale and is reclaimed (with the abandoned run's status file
      corrected to FAILED first - never silently treated as success).

  uri_workspace/dev_workflow/runs/<worker>_<task_id>_<timestamp>/
      status.json  - the machine-readable completion marker Antigravity
                      polls: {"status": "STARTING"|"RUNNING"|"COMPLETE"|
                      "FAILED"|"INTERRUPTED", "worker":, "task_id":,
                      "pid":, "exit_code":, "started_at":, "ended_at":,
                      "log_file":}
      output.log   - full tee of the worker's stdout/stderr, for review
                      after the fact even once the console window closes.

Security: the task prompt/package must never itself carry secrets (same
discipline as every other AO-4 task package); this module never logs
process environment variables, and the console window title carries only
the worker name and task_id - never a key, token, or file content.
"""

from __future__ import annotations

import argparse
import ctypes
import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_WORKFLOW_DIR = REPO_ROOT / "uri_workspace" / "dev_workflow"
LOCKS_DIR = DEV_WORKFLOW_DIR / "locks"
RUNS_DIR = DEV_WORKFLOW_DIR / "runs"

CODEX_EXE_CANDIDATES = (
    r"C:\Users\cheta\AppData\Local\OpenAI\Codex\bin\7ac07f4ce733f89a\codex.exe",
    "codex",
)


def _resolve_codex_exe() -> str:
    for candidate in CODEX_EXE_CANDIDATES:
        if candidate == "codex" or os.path.exists(candidate):
            return candidate
    return "codex"


def _build_codex_command(task_text: str, cwd: str) -> List[str]:
    """The exact invocation shape already in production use for Codex
    (see scripts/run_codex_m227.py) - this module changes only HOW the
    process is observed, never what command is actually run."""
    return [
        _resolve_codex_exe(),
        "exec",
        "--dangerously-bypass-approvals-and-sandbox",
        "-C",
        cwd,
        task_text,
    ]


# Pluggable per-worker command builders. Only "codex" is wired today -
# Gemma runs headless via Ollama's HTTP API (scripts/dev_workflow/
# gemma_driver.py), not a CLI subprocess, so a visible terminal has
# nothing to attach to for it yet. Adding a future CLI-based worker is a
# one-line addition here, which is the entire reason this module has a
# generic name instead of an M22.7-specific one.
WORKER_COMMANDS = {
    "codex": _build_codex_command,
}


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _lock_path(worker: str, task_id: str) -> Path:
    return LOCKS_DIR / f"{worker}_{task_id}.lock"


def _pid_is_running(pid: int) -> bool:
    """Windows-appropriate liveness check (no `psutil` dependency)."""
    if sys.platform != "win32":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return str(pid) in out.stdout
    except Exception:
        # Fail safe toward "assume still running" only for the duplicate
        # check's sake would risk a false "already active" - fail toward
        # "not running" instead so a launch is never silently blocked by
        # a liveness-check error, and rely on the lock's own PID+status
        # reconciliation as the real safety net.
        return False


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def check_active(worker: str, task_id: str) -> Optional[Dict[str, Any]]:
    """Returns the live lock dict if (worker, task_id) has an active run,
    reconciling and clearing a stale lock (dead PID) first - a crashed
    run is never left looking ambiguously "maybe still running"."""
    lock_path = _lock_path(worker, task_id)
    lock = _read_json(lock_path)
    if lock is None:
        return None

    pid = lock.get("pid")
    if isinstance(pid, int) and _pid_is_running(pid):
        return lock

    # Stale lock: the process that held it is gone. If its own status
    # file never reached a terminal state, that run crashed or the
    # console was closed - correct it to INTERRUPTED now rather than
    # leaving a permanently-ambiguous "RUNNING" marker on disk.
    run_dir = lock.get("run_dir")
    if run_dir:
        status_path = Path(run_dir) / "status.json"
        status = _read_json(status_path)
        if status and status.get("status") in ("STARTING", "RUNNING"):
            status["status"] = "INTERRUPTED"
            status["ended_at"] = _now_iso()
            status["detail"] = (
                "Process (or its console window) disappeared without "
                "writing a terminal status - treated as interrupted, "
                "never as a silent success."
            )
            _write_json(status_path, status)

    try:
        lock_path.unlink()
    except OSError:
        pass
    return None


def get_status(run_dir: str | Path) -> Optional[Dict[str, Any]]:
    """Poll helper for Antigravity: read a run's current status.json,
    reconciling a dead-PID-but-still-RUNNING record the same way
    check_active does, so a poller never sees a stale false "RUNNING"."""
    run_dir = Path(run_dir)
    status_path = run_dir / "status.json"
    status = _read_json(status_path)
    if status is None:
        return None
    if status.get("status") in ("STARTING", "RUNNING"):
        pid = status.get("pid")
        if not (isinstance(pid, int) and _pid_is_running(pid)):
            status["status"] = "INTERRUPTED"
            status["ended_at"] = _now_iso()
            status["detail"] = (
                "Process no longer running but never reached a terminal "
                "status - treated as interrupted."
            )
            _write_json(status_path, status)
    return status


def _spawn_console_process(run_args: List[str]) -> "subprocess.Popen":
    """Isolated so tests can mock exactly this call - never the shared
    `subprocess.Popen` symbol itself, which `subprocess.run` (used by
    `_pid_is_running` for the tasklist-based liveness check) also relies
    on internally; mocking `subprocess.Popen` globally would silently
    break liveness checks for the whole test process, not just this
    console spawn."""
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_CONSOLE
    return subprocess.Popen(
        run_args,
        cwd=str(REPO_ROOT),
        creationflags=creationflags,
        stdin=subprocess.DEVNULL if creationflags else None,
    )


def launch(
    worker: str,
    task_id: str,
    task_file: str | Path,
    cwd: str | Path = REPO_ROOT,
    title: Optional[str] = None,
    no_pause: bool = False,
) -> Dict[str, Any]:
    """Non-blocking: validates no duplicate is active, opens a new visible
    console running this same script in `run` mode, and returns
    immediately with the run's tracking paths. Raises RuntimeError if a
    duplicate (worker, task_id) is already active - never launches a
    second writer for the same task."""

    if worker not in WORKER_COMMANDS:
        raise ValueError(
            f"Unknown worker '{worker}'. Supported: {sorted(WORKER_COMMANDS)}"
        )

    task_file = Path(task_file).resolve()
    if not task_file.exists():
        raise FileNotFoundError(f"Task file not found: {task_file}")

    active = check_active(worker, task_id)
    if active is not None:
        raise RuntimeError(
            f"A {worker} task for '{task_id}' is already active "
            f"(pid {active.get('pid')}, started {active.get('started_at')}, "
            f"run_dir {active.get('run_dir')}). Refusing to launch a "
            "duplicate writer for the same task."
        )

    # Microsecond precision (not just seconds): two launches for
    # different task_ids, or a reclaimed-stale-lock relaunch for the
    # same task_id, can easily land in the same wall-clock second.
    # A second-resolution timestamp would then collide on run_dir,
    # letting the new run's initial STARTING status.json silently
    # overwrite the previous run's just-reconciled INTERRUPTED/COMPLETE
    # record in the same file.
    timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S_%f")
    run_dir = RUNS_DIR / f"{worker}_{task_id}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    status_path = run_dir / "status.json"
    _write_json(
        status_path,
        {
            "status": "STARTING",
            "worker": worker,
            "task_id": task_id,
            "pid": None,
            "exit_code": None,
            "started_at": _now_iso(),
            "ended_at": None,
            "log_file": str(run_dir / "output.log"),
        },
    )

    window_title = title or f"{worker.upper()} - {task_id}"

    run_args = [
        sys.executable,
        str(Path(__file__).resolve()),
        "run",
        "--worker", worker,
        "--task-id", task_id,
        "--task-file", str(task_file),
        "--cwd", str(Path(cwd).resolve()),
        "--run-dir", str(run_dir),
        "--title", window_title,
    ]
    if no_pause:
        run_args.append("--no-pause")

    console_process = _spawn_console_process(run_args)

    _write_json(
        _lock_path(worker, task_id),
        {
            "pid": console_process.pid,
            "started_at": _now_iso(),
            "run_dir": str(run_dir),
        },
    )

    return {
        "pid": console_process.pid,
        "run_dir": str(run_dir),
        "status_file": str(status_path),
        "log_file": str(run_dir / "output.log"),
    }


def _set_console_title(title: str) -> None:
    if sys.platform == "win32":
        try:
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        except Exception:
            pass


_INTERRUPTED_FLAG = {"hit": False}


def _install_close_handler(status_path: Path, lock_path: Path) -> None:
    """Best-effort: catch the console being closed (the X button / a
    forced CTRL_CLOSE_EVENT) so an abrupt close is marked INTERRUPTED
    rather than leaving status.json stuck at RUNNING forever. Windows
    grants a short grace period to a console control handler before
    tearing the process down - this is best-effort, not a guarantee;
    the launcher's own dead-PID reconciliation (check_active/get_status)
    is the real backstop if this handler doesn't get to run."""
    if sys.platform != "win32":
        return

    HANDLER_ROUTINE = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)

    def handler(ctrl_type: int) -> bool:
        # CTRL_CLOSE_EVENT=2, CTRL_LOGOFF_EVENT=5, CTRL_SHUTDOWN_EVENT=6
        if ctrl_type in (2, 5, 6) and not _INTERRUPTED_FLAG["hit"]:
            _INTERRUPTED_FLAG["hit"] = True
            status = _read_json(status_path) or {}
            status["status"] = "INTERRUPTED"
            status["ended_at"] = _now_iso()
            status["detail"] = "Console window was closed before the task finished."
            try:
                _write_json(status_path, status)
            except OSError:
                pass
            try:
                lock_path.unlink()
            except OSError:
                pass
        return False  # allow default handling to continue after ours

    global _handler_ref
    _handler_ref = HANDLER_ROUTINE(handler)
    ctypes.windll.kernel32.SetConsoleCtrlHandler(_handler_ref, True)


def _run_in_console(
    worker: str,
    task_id: str,
    task_file: str,
    cwd: str,
    run_dir: str,
    title: str,
    no_pause: bool,
) -> int:
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    run_dir_p = Path(run_dir)
    status_path = run_dir_p / "status.json"
    log_path = run_dir_p / "output.log"
    lock_path = _lock_path(worker, task_id)

    _set_console_title(title)
    _install_close_handler(status_path, lock_path)

    task_text = Path(task_file).read_text(encoding="utf-8")
    cmd = WORKER_COMMANDS[worker](task_text, cwd)

    banner = (
        f"\n[{worker.upper()} \u2014 {task_id} IMPLEMENTATION]\n\n"
        f"Task: {task_id}\n"
        f"Worker: {worker.capitalize()}\n"
        f"Repository: {cwd}\n"
        f"Status: RUNNING\n\n"
    )
    sys.stdout.write(banner)
    sys.stdout.flush()

    status = _read_json(status_path) or {}
    status.update(
        {
            "status": "RUNNING",
            "worker": worker,
            "task_id": task_id,
            "pid": os.getpid(),
            "started_at": status.get("started_at") or _now_iso(),
            "log_file": str(log_path),
        }
    )
    _write_json(status_path, status)

    exit_code: Optional[int] = None
    detail = ""
    try:
        with open(log_path, "a", encoding="utf-8", errors="replace") as log_fh:
            log_fh.write(banner)
            log_fh.flush()

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
            for line in iter(process.stdout.readline, ""):
                sys.stdout.write(line)
                sys.stdout.flush()
                log_fh.write(line)
                log_fh.flush()
            process.stdout.close()
            exit_code = process.wait()
    except Exception as exc:  # noqa: BLE001 - must always reach status write below
        detail = f"Runner crashed before the worker process finished: {exc!r}"
        exit_code = exit_code if exit_code is not None else -1

    if _INTERRUPTED_FLAG["hit"]:
        # The close handler already wrote the final status; do not
        # overwrite an INTERRUPTED record with a late COMPLETE/FAILED.
        return exit_code or 0

    final_status = "COMPLETE" if exit_code == 0 else "FAILED"
    status = _read_json(status_path) or {}
    status.update(
        {
            "status": final_status,
            "exit_code": exit_code,
            "ended_at": _now_iso(),
        }
    )
    if detail:
        status["detail"] = detail
    _write_json(status_path, status)

    try:
        lock_path.unlink()
    except OSError:
        pass

    footer = f"\nStatus: {final_status}"
    if final_status == "FAILED":
        footer += f" (exit code {exit_code})"
    footer += "\n"
    sys.stdout.write(footer)
    sys.stdout.flush()

    if not no_pause:
        try:
            input("\nPress Enter to close this window...")
        except (EOFError, KeyboardInterrupt):
            pass

    return exit_code or 0


def _cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)

    p_launch = sub.add_parser("launch", help="Open a new visible console running the worker (non-blocking).")
    p_launch.add_argument("--worker", required=True, choices=sorted(WORKER_COMMANDS))
    p_launch.add_argument("--task-id", required=True)
    p_launch.add_argument("--task-file", required=True)
    p_launch.add_argument("--cwd", default=str(REPO_ROOT))
    p_launch.add_argument("--title", default=None)
    p_launch.add_argument("--no-pause", action="store_true")

    p_run = sub.add_parser("run", help=argparse.SUPPRESS)  # internal: invoked by `launch` inside the new console
    p_run.add_argument("--worker", required=True)
    p_run.add_argument("--task-id", required=True)
    p_run.add_argument("--task-file", required=True)
    p_run.add_argument("--cwd", required=True)
    p_run.add_argument("--run-dir", required=True)
    p_run.add_argument("--title", required=True)
    p_run.add_argument("--no-pause", action="store_true")

    p_status = sub.add_parser("status", help="Print a run's current status.json.")
    p_status.add_argument("--run-dir", required=True)

    p_check = sub.add_parser("check-active", help="Check whether (worker, task-id) has an active run.")
    p_check.add_argument("--worker", required=True)
    p_check.add_argument("--task-id", required=True)

    args = parser.parse_args()

    if args.mode == "launch":
        result = launch(
            worker=args.worker,
            task_id=args.task_id,
            task_file=args.task_file,
            cwd=args.cwd,
            title=args.title,
            no_pause=args.no_pause,
        )
        print(json.dumps(result, indent=2))
        return 0

    if args.mode == "run":
        return _run_in_console(
            worker=args.worker,
            task_id=args.task_id,
            task_file=args.task_file,
            cwd=args.cwd,
            run_dir=args.run_dir,
            title=args.title,
            no_pause=args.no_pause,
        )

    if args.mode == "status":
        status = get_status(args.run_dir)
        print(json.dumps(status, indent=2) if status else "null")
        return 0

    if args.mode == "check-active":
        active = check_active(args.worker, args.task_id)
        print(json.dumps(active, indent=2) if active else "null")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(_cli())
