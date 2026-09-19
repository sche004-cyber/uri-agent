"""M33.1 Batch 3 — reviewed GitHub package lifecycle acceptance evidence."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("URI_EXTERNAL_CREDENTIAL_SECRET", "test-external-credential-secret")

from uri_core.app import server
from uri_core.external.adapters import cli
from uri_core.external.descriptors.strip_json_comments import DESCRIPTOR_ID, V2_REVISION, V3_REVISION
from uri_core.external.packages import strip_json_comments as package
from uri_core.external.runners import strip_json_comments_runner as runner
from uri_core.external.runtime_lifecycle import (
    configure_and_refresh,
    disable_and_refresh,
    enable_and_refresh,
    remove_and_refresh,
)


class GenericCliOutputContractTests(unittest.TestCase):
    def _descriptor(self, output=None):
        config = {"command": ["fixed-cli"], "timeout_seconds": 3}
        if output is not None:
            config["output"] = output
        return {"transport_config": config}

    def test_default_json_output_is_backward_compatible(self):
        completed = SimpleNamespace(returncode=0, stdout='{"value": 1}')
        with patch.object(cli.subprocess, "run", return_value=completed) as run:
            result = cli.execute(self._descriptor(), "action", {"value": 1})
        self.assertEqual(result, {"status": "success", "result": {"value": 1}})
        self.assertFalse(run.call_args.kwargs["shell"])

    def test_text_output_wraps_raw_stdout_without_json_parsing(self):
        completed = SimpleNamespace(returncode=0, stdout='{"still": // comment\n 1}')
        with patch.object(cli.subprocess, "run", return_value=completed):
            result = cli.execute(self._descriptor("text"), "action", {"value": 1})
        self.assertEqual(result, {"status": "success", "result": {"text": completed.stdout}})

    def test_unknown_output_mode_fails_closed_without_running_command(self):
        with patch.object(cli.subprocess, "run") as run:
            result = cli.execute(self._descriptor("yaml"), "action", {})
        self.assertEqual(result["status"], "invalid_input")
        run.assert_not_called()


class PackageStagingTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="uri_batch3_stage_")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_reviewed_lockfile_is_complete_and_staging_suppresses_scripts(self):
        revision = V3_REVISION

        def fake_npm(command, **kwargs):
            self.assertEqual(command[1:], ["ci", "--ignore-scripts", "--omit=dev"])
            self.assertFalse(kwargs["shell"])
            staged_cli = Path(kwargs["cwd"]) / "node_modules" / package.PACKAGE_NAME / "cli.js"
            staged_cli.parent.mkdir(parents=True)
            staged_cli.write_text("// fixed fixture", encoding="utf-8")
            return SimpleNamespace(returncode=0)

        with patch.object(package.subprocess, "run", side_effect=fake_npm):
            staged = package.stage_install(state_root=self.root, revision=revision)
        self.assertTrue((staged.path / "node_modules" / package.PACKAGE_NAME / "cli.js").is_file())
        self.assertNotIn(str(uuid.uuid4()), str(staged.path))
        self.assertEqual(staged.dependency_lock["revision"], revision)

        source = package._reviewed_source(revision)
        raw, lock = package._read_and_validate_lock(source, revision)
        self.assertTrue(raw)
        self.assertGreater(len(lock["packages"]), 1)
        for path, entry in lock["packages"].items():
            if path:
                self.assertTrue(entry["resolved"].startswith("https://registry.npmjs.org/"))
                self.assertTrue(entry["integrity"].startswith("sha512-"))

    def test_corrupt_lockfile_is_rejected_before_staging_or_activation(self):
        source = Path(self.root) / "source"
        source.mkdir()
        (source / "package.json").write_text("{}", encoding="utf-8")
        (source / "package-lock.json").write_text("not json", encoding="utf-8")
        with self.assertRaises(package.PackageQualificationError):
            package._read_and_validate_lock(source, V3_REVISION)

    def test_runner_uses_only_fixed_node_cli_and_no_whitespace_flag(self):
        artifact = Path(self.root) / "artifact"
        cli_path = artifact / "node_modules" / package.PACKAGE_NAME / "cli.js"
        cli_path.parent.mkdir(parents=True)
        cli_path.write_text("// reviewed fixture", encoding="utf-8")
        node = Path(self.root) / "node.exe"
        node.write_text("fixed fixture", encoding="utf-8")
        completed = SimpleNamespace(returncode=0, stdout='{"value":1}', stderr="")
        with patch.object(runner.subprocess, "run", return_value=completed) as run:
            result = runner.execute_text(str(artifact), str(node), '{ // x\n "value": 1 }', remove_whitespace=True)
        self.assertEqual(result, '{"value":1}')
        command = run.call_args.args[0]
        self.assertEqual(command, [str(node.resolve()), str(cli_path.resolve()), "--no-whitespace"])
        self.assertFalse(run.call_args.kwargs["shell"])


class Batch3LifecycleAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="uri_batch3_live_")
        self.original_root = server._USER_STATE_ROOT
        server._USER_STATE_ROOT = self.root
        self.user_a, self.user_b = str(uuid.uuid4()), str(uuid.uuid4())
        self.context_a = server._build_user_context(self.user_a)
        self.context_b = server._build_user_context(self.user_b)

    def tearDown(self):
        server._USER_STATE_ROOT = self.original_root
        shutil.rmtree(self.root, ignore_errors=True)

    def _install_v2_enable(self):
        result = package.install_and_register(self.context_a, self.user_a, revision=V2_REVISION)
        self.assertTrue(result.ok)
        configure_and_refresh(self.context_a, self.user_a, DESCRIPTOR_ID)
        enable_and_refresh(self.context_a, self.user_a, DESCRIPTOR_ID)

    def _dispatch_a(self, text='{\n // preserved only as input\n "value": 1\n}', *, session_id="batch3-a"):
        return self.context_a.orchestrator.multi_action_dispatch.dispatch_explicit(
            DESCRIPTOR_ID,
            "strip_json_comments",
            {"text": text, "remove_whitespace": False},
            session_id=session_id,
            user_text="clean JSON",
            principal=self.context_a.orchestrator.principal,
        )

    def test_real_install_execute_live_retirement_update_remove_and_isolation(self):
        # v2 is installed into a shared immutable cache, but only User A gets
        # a lifecycle record/registry entry.
        self._install_v2_enable()
        dispatch_a = self.context_a.orchestrator.multi_action_dispatch
        self.assertIsNotNone(dispatch_a.registry.get_capability(DESCRIPTOR_ID))
        self.assertTrue(any(x.get("capability") == DESCRIPTOR_ID for x in dispatch_a.discovery.discover_capabilities("json")))
        self.assertIn(f"capability:{DESCRIPTOR_ID}", self.context_a.orchestrator.graphify_index.records)
        record = self.context_a.orchestrator.graphify_index.records[f"capability:{DESCRIPTOR_ID}"]
        serialized = json.dumps(record).lower()
        for forbidden in ("command", "runner", "credential", "secret", "node_modules"):
            self.assertNotIn(forbidden, serialized)

        # Generic descriptor -> qualifier -> registry -> CLI transport ->
        # MultiActionDispatch result/evidence path.  No package branch exists
        # in the adapter or execution core.
        live = self._dispatch_a()
        self.assertEqual(live["status"], "success")
        cleaned = live["response"]["result"]["text"]
        self.assertNotIn("preserved only as input", cleaned)
        self.assertEqual(json.loads(cleaned), {"value": 1})

        # User B cannot see, operate, execute, or inherit Graphify state.
        dispatch_b = self.context_b.orchestrator.multi_action_dispatch
        self.assertIsNone(dispatch_b.registry.get_capability(DESCRIPTOR_ID))
        self.assertNotIn(f"capability:{DESCRIPTOR_ID}", self.context_b.orchestrator.graphify_index.records)
        self.assertIsNone(dispatch_b.dispatch_explicit(
            DESCRIPTOR_ID, "strip_json_comments", {"text": "{}"},
            session_id="batch3-b", user_text="steal", principal=self.context_b.orchestrator.principal,
        ))
        self.assertIsNone(disable_and_refresh(self.context_b, self.user_b, DESCRIPTOR_ID))
        self.assertFalse(package.remove_and_refresh(self.context_b, self.user_b))

        # Disable immediately retires the exact live generation; re-enable
        # restores it without rebuilding the server context.
        disable_and_refresh(self.context_a, self.user_a, DESCRIPTOR_ID)
        self.assertIsNone(self.context_a.orchestrator.multi_action_dispatch.registry.get_capability(DESCRIPTOR_ID))
        self.assertNotIn(f"capability:{DESCRIPTOR_ID}", self.context_a.orchestrator.graphify_index.records)
        self.assertIsNone(self._dispatch_a())
        enable_and_refresh(self.context_a, self.user_a, DESCRIPTOR_ID)
        self.assertIsNotNone(self.context_a.orchestrator.multi_action_dispatch.registry.get_capability(DESCRIPTOR_ID))
        self.assertIn(f"capability:{DESCRIPTOR_ID}", self.context_a.orchestrator.graphify_index.records)

        old = self.context_a.external_capability_store.get(self.user_a, DESCRIPTOR_ID)
        old_path = old["descriptor"]["transport_config"]["command"][-2]
        update = package.update_and_refresh(self.context_a, self.user_a, revision=V3_REVISION)
        self.assertTrue(update.ok)
        current = self.context_a.external_capability_store.get(self.user_a, DESCRIPTOR_ID)
        self.assertEqual(current["qualification"]["source_revision"], V3_REVISION)
        self.assertNotEqual(current["descriptor"]["transport_config"]["command"][-2], old_path)
        self.assertTrue(current["lifecycle"]["enabled"])
        after_failed_update = self._dispatch_a(session_id="batch3-after-update")
        self.assertEqual(after_failed_update["status"], "success", after_failed_update)

        # A failed fresh staging attempt never replaces the active v3 record.
        with patch.object(package, "stage_install", side_effect=package.PackageQualificationError("bad artifact")):
            with self.assertRaises(package.PackageQualificationError):
                package.update_and_refresh(self.context_a, self.user_a, revision=V2_REVISION)
        self.assertEqual(
            self.context_a.external_capability_store.get(self.user_a, DESCRIPTOR_ID)["qualification"]["source_revision"],
            V3_REVISION,
        )
        after_rejected_stage = self._dispatch_a(session_id="batch3-after-rejected-stage")
        self.assertEqual(after_rejected_stage["status"], "success", after_rejected_stage)

        active_artifact = Path(current["descriptor"]["transport_config"]["command"][-2])
        self.assertTrue(package.remove_and_refresh(self.context_a, self.user_a))
        self.assertIsNone(self.context_a.external_capability_store.get(self.user_a, DESCRIPTOR_ID))
        self.assertIsNone(self.context_a.orchestrator.multi_action_dispatch.registry.get_capability(DESCRIPTOR_ID))
        self.assertNotIn(f"capability:{DESCRIPTOR_ID}", self.context_a.orchestrator.graphify_index.records)
        self.assertFalse(active_artifact.exists())

    def test_corrupt_user_state_fails_closed_and_does_not_leak_to_another_user(self):
        self._install_v2_enable()
        path = Path(self.root) / self.user_a / "external_capabilities.json"
        path.write_text("{not json", encoding="utf-8")
        rebuilt_a = server._build_user_context(self.user_a)
        self.assertIsNone(rebuilt_a.orchestrator.multi_action_dispatch.registry.get_capability(DESCRIPTOR_ID))
        self.assertNotIn(f"capability:{DESCRIPTOR_ID}", rebuilt_a.orchestrator.graphify_index.records)
        self.assertIsNone(self.context_b.orchestrator.multi_action_dispatch.registry.get_capability(DESCRIPTOR_ID))

    def test_no_package_branch_in_generic_execution_core(self):
        for path in (
            "uri_core/external/adapters/cli.py",
            "uri_core/core/canonical_execution.py",
            "uri_core/core/multi_action_dispatch.py",
            "uri_core/core/orchestrator.py",
        ):
            content = Path(path).read_text(encoding="utf-8")
            self.assertNotIn("strip_json_comments", content)
            self.assertNotIn("strip-json-comments", content)


if __name__ == "__main__":
    unittest.main()
