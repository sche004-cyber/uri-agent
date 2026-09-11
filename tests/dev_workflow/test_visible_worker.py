"""Regression tests for scripts/dev_workflow/visible_worker.py.

Never spawns a real console window or a real Codex/Codex-like process -
`launch()`'s actual console spawn is mocked throughout, so these tests are
hermetic and safe to run in any environment. The live, real-console smoke
test (a genuinely visible terminal running a harmless bounded Codex task)
is a manual, one-off validation step recorded in
docs/dev_workflow/AO4_INFRASTRUCTURE_ARCHITECTURE.md - not part of the
automated suite, since it requires an interactive console and a live
Codex CLI/API credential.
"""

import json
import os
import shutil
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.dev_workflow import visible_worker as vw


class VisibleWorkerTestBase(unittest.TestCase):
    def setUp(self):
        self._orig_locks = vw.LOCKS_DIR
        self._orig_runs = vw.RUNS_DIR
        self.tmp_root = Path(__file__).resolve().parent / "_tmp_visible_worker"
        if self.tmp_root.exists():
            shutil.rmtree(self.tmp_root)
        self.tmp_root.mkdir(parents=True)
        vw.LOCKS_DIR = self.tmp_root / "locks"
        vw.RUNS_DIR = self.tmp_root / "runs"

        self.task_file = self.tmp_root / "task.txt"
        self.task_file.write_text("Harmless bounded smoke-test task.", encoding="utf-8")

    def tearDown(self):
        vw.LOCKS_DIR = self._orig_locks
        vw.RUNS_DIR = self._orig_runs
        if self.tmp_root.exists():
            shutil.rmtree(self.tmp_root, ignore_errors=True)


class LaunchValidationTests(VisibleWorkerTestBase):
    def test_unknown_worker_rejected(self):
        with self.assertRaises(ValueError):
            vw.launch(worker="not-a-real-worker", task_id="DEVTEST_X", task_file=self.task_file)

    def test_missing_task_file_rejected(self):
        with self.assertRaises(FileNotFoundError):
            vw.launch(worker="codex", task_id="DEVTEST_X", task_file=self.tmp_root / "nope.txt")

    @patch("scripts.dev_workflow.visible_worker._spawn_console_process")
    def test_launch_creates_run_dir_status_and_lock(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.pid = 424242
        mock_popen.return_value = mock_proc

        result = vw.launch(worker="codex", task_id="DEVTEST_LAUNCH", task_file=self.task_file, no_pause=True)

        status_path = Path(result["status_file"])
        self.assertTrue(status_path.exists())
        status = json.loads(status_path.read_text(encoding="utf-8"))
        self.assertEqual(status["status"], "STARTING")
        self.assertEqual(status["worker"], "codex")
        self.assertEqual(status["task_id"], "DEVTEST_LAUNCH")

        lock_path = vw._lock_path("codex", "DEVTEST_LAUNCH")
        self.assertTrue(lock_path.exists())
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        self.assertEqual(lock["pid"], 424242)

        # The new console is spawned non-interactively from the test's
        # point of view - launch() must not block waiting on it.
        mock_popen.assert_called_once()
        (run_args,), _ = mock_popen.call_args
        self.assertIn("run", run_args)
        self.assertIn("DEVTEST_LAUNCH", run_args)


class DuplicatePreventionTests(VisibleWorkerTestBase):
    @patch("scripts.dev_workflow.visible_worker._spawn_console_process")
    def test_second_launch_for_same_task_is_refused(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.pid = os.getpid()  # a genuinely live PID (this test process itself)
        mock_popen.return_value = mock_proc

        vw.launch(worker="codex", task_id="DEVTEST_DUP", task_file=self.task_file, no_pause=True)

        with self.assertRaises(RuntimeError):
            vw.launch(worker="codex", task_id="DEVTEST_DUP", task_file=self.task_file, no_pause=True)

        # Only one console-spawn actually happened.
        mock_popen.assert_called_once()

    @patch("scripts.dev_workflow.visible_worker._spawn_console_process")
    def test_different_task_id_is_not_blocked(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.pid = os.getpid()
        mock_popen.return_value = mock_proc

        vw.launch(worker="codex", task_id="DEVTEST_A", task_file=self.task_file, no_pause=True)
        vw.launch(worker="codex", task_id="DEVTEST_B", task_file=self.task_file, no_pause=True)

        self.assertEqual(mock_popen.call_count, 2)

    @patch("scripts.dev_workflow.visible_worker._spawn_console_process")
    def test_stale_lock_from_dead_pid_is_reclaimed_and_marked_interrupted(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.pid = 9999999  # never a real PID
        mock_popen.return_value = mock_proc

        result = vw.launch(worker="codex", task_id="DEVTEST_STALE", task_file=self.task_file, no_pause=True)
        # Simulate the run having actually reached RUNNING before the
        # process vanished without writing a terminal status.
        status_path = Path(result["status_file"])
        status = json.loads(status_path.read_text(encoding="utf-8"))
        status["status"] = "RUNNING"
        status["pid"] = 9999999
        status_path.write_text(json.dumps(status), encoding="utf-8")

        # A fresh launch for the same task must succeed (not be refused
        # as a duplicate) since the prior PID is dead...
        mock_proc2 = MagicMock()
        mock_proc2.pid = os.getpid()
        mock_popen.return_value = mock_proc2
        vw.launch(worker="codex", task_id="DEVTEST_STALE", task_file=self.task_file, no_pause=True)

        # ...and the abandoned run's own status must have been corrected
        # to INTERRUPTED, never left claiming RUNNING or COMPLETE.
        old_status = json.loads(status_path.read_text(encoding="utf-8"))
        self.assertEqual(old_status["status"], "INTERRUPTED")

    def test_check_active_returns_none_when_no_lock(self):
        self.assertIsNone(vw.check_active("codex", "DEVTEST_NEVER_RUN"))


class StatusPollingTests(VisibleWorkerTestBase):
    def test_get_status_reconciles_dead_pid_running_to_interrupted(self):
        run_dir = vw.RUNS_DIR / "codex_DEVTEST_POLL_1"
        run_dir.mkdir(parents=True)
        status_path = run_dir / "status.json"
        status_path.write_text(
            json.dumps({"status": "RUNNING", "pid": 9999999, "worker": "codex", "task_id": "DEVTEST_POLL"}),
            encoding="utf-8",
        )

        status = vw.get_status(run_dir)
        self.assertEqual(status["status"], "INTERRUPTED")

    def test_get_status_leaves_complete_untouched(self):
        run_dir = vw.RUNS_DIR / "codex_DEVTEST_POLL_2"
        run_dir.mkdir(parents=True)
        status_path = run_dir / "status.json"
        status_path.write_text(
            json.dumps({"status": "COMPLETE", "pid": 9999999, "exit_code": 0}),
            encoding="utf-8",
        )

        status = vw.get_status(run_dir)
        self.assertEqual(status["status"], "COMPLETE")

    def test_get_status_missing_run_returns_none(self):
        self.assertIsNone(vw.get_status(vw.RUNS_DIR / "does_not_exist"))


class ConsoleSpawnTests(VisibleWorkerTestBase):
    def test_spawn_uses_new_console_creationflag_on_windows(self):
        with patch("scripts.dev_workflow.visible_worker.subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock(pid=1)
            vw._spawn_console_process(["dummy"])
            _, kwargs = mock_popen.call_args
            if os.name == "nt":
                self.assertEqual(kwargs.get("creationflags"), vw.subprocess.CREATE_NEW_CONSOLE)


class NoNewWriterInvariantTests(VisibleWorkerTestBase):
    """Requirement #6 (single-writer safety): visible-terminal support must
    launch exactly the same worker command as before, never a second
    concurrent process for the same task."""

    def test_codex_command_shape_unchanged(self):
        cmd = vw.WORKER_COMMANDS["codex"]("a task", r"C:\Users\cheta\Development\uri-agent")
        self.assertIn("exec", cmd)
        self.assertIn("--dangerously-bypass-approvals-and-sandbox", cmd)
        self.assertIn("-C", cmd)
        self.assertIn(r"C:\Users\cheta\Development\uri-agent", cmd)
        self.assertIn("a task", cmd)


if __name__ == "__main__":
    unittest.main()
