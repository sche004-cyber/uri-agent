"""M33.1 Batch 2: Pinned yt-dlp CLI skill acceptance test suite.

Proves:
- Store-root consistency: actual runtime user-state root injected into
  ExternalCapabilityStore, ConnectedServiceStore, ExternalCredentialStore.
- Duplicate lifecycle authority removed: LifecycleController.remove() absent;
  ExternalCapabilityStore.remove() retained as sole hard-removal authority.
- Pinned yt-dlp descriptor qualification (version 2026.8.19, one read-only action).
- Execution through generic CLI bridge and canonical execution loop.
- Live lifecycle refresh: enable -> disable -> re-enable -> remove propagates
  immediately to registry, discovery, and Graphify without server restart.
- User isolation: capability enabled for User A is undiscoverable/undispatchable for User B.
- No vendor-specific execution-core branching in cli.py, canonical_execution.py,
  or multi_action_dispatch.py.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("URI_EXTERNAL_CREDENTIAL_SECRET", "test-external-credential-secret")

from uri_core.app import server
from uri_core.core.canonical_execution import _execute_canonical
from uri_core.core.connection_status import list_connection_status
from uri_core.external.descriptors.yt_dlp import (
    DESCRIPTOR_ID,
    PINNED_YT_DLP_VERSION,
    yt_dlp_descriptor,
)
from uri_core.external.lifecycle import LifecycleController
from uri_core.external.qualification import Qualifier
from uri_core.external.runners import yt_dlp_runner
from uri_core.external.runtime_lifecycle import (
    configure_and_refresh,
    disable_and_refresh,
    enable_and_refresh,
    register_and_refresh,
    remove_and_refresh,
)

STABLE_PUBLIC_TEST_URL = (
    "https://commons.wikimedia.org/wiki/File:Big_Buck_Bunny_4K.webm"
)


class TestM33_1Batch2YtDlp(unittest.TestCase):
    def setUp(self):
        self.temp_root = tempfile.mkdtemp(prefix="uri_test_batch2_")
        self.original_user_state_root = server._USER_STATE_ROOT
        server._USER_STATE_ROOT = self.temp_root
        self.user_a = str(uuid.uuid4())
        self.user_b = str(uuid.uuid4())
        self.context_a = server._build_user_context(self.user_a)
        self.context_b = server._build_user_context(self.user_b)

    def tearDown(self):
        server._USER_STATE_ROOT = self.original_user_state_root
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def test_store_root_consistency(self):
        """Verify the configured runtime root is injected into all external stores."""
        self.assertEqual(
            self.context_a.external_capability_store.root, self.temp_root
        )
        self.assertEqual(
            self.context_a.connected_service_store.root, self.temp_root
        )
        self.assertEqual(
            self.context_a.external_credential_store.root, self.temp_root
        )

        # Register and configure descriptor in user_a's store
        desc = yt_dlp_descriptor()
        register_and_refresh(
            self.context_a,
            self.user_a,
            desc,
            source_revision=desc["source_revision"],
        )

        # Verify state file was created strictly inside self.temp_root
        expected_store_path = os.path.join(
            self.temp_root, self.user_a, "external_capabilities.json"
        )
        self.assertTrue(os.path.exists(expected_store_path))

        # Verify no files were created under default uri_workspace/users
        default_store_path = os.path.join(
            "uri_workspace", "users", self.user_a, "external_capabilities.json"
        )
        self.assertFalse(os.path.exists(default_store_path))

        # Verify list_connection_status respects the configured root
        status = list_connection_status(
            user_id=self.user_a,
            service_store=self.context_a.connected_service_store,
        )
        self.assertIsInstance(status, list)

    def test_duplicate_lifecycle_authority_removed(self):
        """Verify LifecycleController.remove() is absent and ExternalCapabilityStore.remove() is sole authority."""
        self.assertFalse(hasattr(LifecycleController, "remove"))
        self.assertTrue(
            hasattr(self.context_a.external_capability_store, "remove")
        )

    def test_descriptor_qualification_and_structure(self):
        """Verify yt-dlp descriptor satisfies versioned contract and qualification rules."""
        desc = yt_dlp_descriptor()
        self.assertEqual(desc["contract_version"], "1.0")
        self.assertEqual(desc["id"], DESCRIPTOR_ID)
        self.assertEqual(desc["transport"], "cli")
        self.assertEqual(desc["source_revision"], PINNED_YT_DLP_VERSION)
        self.assertIn(f"yt-dlp=={PINNED_YT_DLP_VERSION}", desc["dependencies"])
        with open("requirements.txt", "r", encoding="utf-8") as handle:
            self.assertIn(
                f"yt-dlp=={PINNED_YT_DLP_VERSION}",
                handle.read(),
            )

        # Exactly ONE read-only action exposed
        self.assertEqual(list(desc["actions"].keys()), ["dump_json"])
        action = desc["actions"]["dump_json"]
        self.assertEqual(action["effect_type"], "read_only")
        self.assertEqual(action["approval_requirement"], "none")
        self.assertEqual(action["risk"], "low")

        # Must qualify cleanly with declared source_revision
        qualifier = Qualifier()
        record = qualifier.qualify(desc, source_revision=desc["source_revision"])
        self.assertEqual(record.status, "qualified")
        self.assertEqual(record.reasons, [])

    def test_execution_through_generic_cli_bridge_and_canonical_loop(self):
        """Prove execution of pinned yt-dlp through generic MultiActionDispatch and canonical loop."""
        desc = yt_dlp_descriptor()
        register_and_refresh(
            self.context_a,
            self.user_a,
            desc,
            source_revision=desc["source_revision"],
        )
        configure_and_refresh(self.context_a, self.user_a, desc["id"])
        enable_and_refresh(self.context_a, self.user_a, desc["id"])

        # 1. Generic MultiActionDispatch execution
        dispatch = self.context_a.orchestrator.multi_action_dispatch
        env = dispatch.dispatch_explicit(
            DESCRIPTOR_ID,
            "dump_json",
            {"url": STABLE_PUBLIC_TEST_URL},
            session_id="session_test_1",
            user_text="summarize video",
            principal=self.context_a.orchestrator.principal,
        )
        self.assertIsNotNone(env)
        self.assertEqual(env.get("status"), "success")
        self.assertEqual(env.get("execution", {}).get("status"), "success")
        response = env.get("response", {})
        result = response.get("result", {})
        self.assertEqual(result.get("title"), "Big Buck Bunny 4K")
        self.assertEqual(result.get("extractor"), "wikimedia.org")
        self.assertEqual(result.get("webpage_url"), STABLE_PUBLIC_TEST_URL)

        # 2. Canonical loop execution through _execute_canonical
        contract = {
            "capability": DESCRIPTOR_ID,
            "actions": [
                {"name": "dump_json", "inputs": {"url": STABLE_PUBLIC_TEST_URL}}
            ],
        }
        canonical_env = _execute_canonical(
            contract,
            orchestrator=self.context_a.orchestrator,
            session_id="session_test_2",
            user_text="fetch video metadata",
            principal=self.context_a.orchestrator.principal,
        )
        self.assertIsNotNone(canonical_env)
        self.assertEqual(canonical_env.get("status"), "success")
        canonical_result = canonical_env.get("response", {}).get("result", {})
        self.assertEqual(canonical_result.get("title"), "Big Buck Bunny 4K")
        self.assertEqual(canonical_result.get("extractor"), "wikimedia.org")

    def test_live_lifecycle_refresh_without_restart(self):
        """Prove enable -> disable -> re-enable -> remove immediately propagates without restart."""
        desc = yt_dlp_descriptor()
        register_and_refresh(
            self.context_a,
            self.user_a,
            desc,
            source_revision=desc["source_revision"],
        )
        configure_and_refresh(self.context_a, self.user_a, desc["id"])

        graphify = self.context_a.orchestrator.graphify_index

        def dispatch():
            return self.context_a.orchestrator.multi_action_dispatch

        # Initial state: qualified and configured, but NOT enabled
        self.assertIsNone(dispatch().registry.get_capability(DESCRIPTOR_ID))
        self.assertEqual(
            [c for c in dispatch().discovery.discover_capabilities("video") if c.get("capability") == DESCRIPTOR_ID],
            [],
        )
        self.assertIsNone(
            dispatch().dispatch_explicit(
                DESCRIPTOR_ID,
                "dump_json",
                {"url": STABLE_PUBLIC_TEST_URL},
                session_id="s1",
                user_text="test",
                principal=self.context_a.orchestrator.principal,
            )
        )
        self.assertNotIn(f"capability:{DESCRIPTOR_ID}", graphify.records)

        # Step 1: Enable -> immediately available in registry, discovery, dispatch, and Graphify
        enable_and_refresh(self.context_a, self.user_a, desc["id"])
        self.assertIsNotNone(dispatch().registry.get_capability(DESCRIPTOR_ID))
        discovered = dispatch().discovery.discover_capabilities("video")
        self.assertTrue(any(c.get("capability") == DESCRIPTOR_ID for c in discovered))
        self.assertIn(f"capability:{DESCRIPTOR_ID}", graphify.records)
        graph_record = graphify.records[f"capability:{DESCRIPTOR_ID}"]
        graph_serialized = json.dumps(graph_record).lower()
        for forbidden in ("command", "runner", "credential", "secret"):
            self.assertNotIn(forbidden, graph_serialized)

        # Materialize a session executor before retirement.  A refresh must
        # discard that cache with its old registry generation, so this exact
        # same session cannot execute after disable.
        live_env = dispatch().dispatch_explicit(
            DESCRIPTOR_ID,
            "dump_json",
            {"url": STABLE_PUBLIC_TEST_URL},
            session_id="s1",
            user_text="test",
            principal=self.context_a.orchestrator.principal,
        )
        self.assertEqual(live_env.get("status"), "success")

        # Step 2: Disable -> immediately denied and retired from registry, discovery, and Graphify
        disable_and_refresh(self.context_a, self.user_a, desc["id"])
        self.assertIsNone(dispatch().registry.get_capability(DESCRIPTOR_ID))
        self.assertEqual(
            [c for c in dispatch().discovery.discover_capabilities("video") if c.get("capability") == DESCRIPTOR_ID],
            [],
        )
        self.assertIsNone(
            dispatch().dispatch_explicit(
                DESCRIPTOR_ID,
                "dump_json",
                {"url": STABLE_PUBLIC_TEST_URL},
                session_id="s1",
                user_text="test",
                principal=self.context_a.orchestrator.principal,
            )
        )
        self.assertNotIn(f"capability:{DESCRIPTOR_ID}", graphify.records)

        # Step 3: Re-enable -> immediately restored
        enable_and_refresh(self.context_a, self.user_a, desc["id"])
        self.assertIsNotNone(dispatch().registry.get_capability(DESCRIPTOR_ID))
        self.assertIn(f"capability:{DESCRIPTOR_ID}", graphify.records)

        # Step 4: Remove -> immediately hard-deleted from store, registry, and Graphify
        remove_and_refresh(self.context_a, self.user_a, desc["id"])
        self.assertIsNone(
            self.context_a.external_capability_store.get(self.user_a, DESCRIPTOR_ID)
        )
        self.assertIsNone(dispatch().registry.get_capability(DESCRIPTOR_ID))
        self.assertEqual(
            [c for c in dispatch().discovery.discover_capabilities("video") if c.get("capability") == DESCRIPTOR_ID],
            [],
        )
        self.assertNotIn(f"capability:{DESCRIPTOR_ID}", graphify.records)

    def test_user_isolation(self):
        """Prove capability enabled for User A is inaccessible and undiscoverable for User B."""
        desc = yt_dlp_descriptor()
        register_and_refresh(
            self.context_a,
            self.user_a,
            desc,
            source_revision=desc["source_revision"],
        )
        configure_and_refresh(self.context_a, self.user_a, desc["id"])
        enable_and_refresh(self.context_a, self.user_a, desc["id"])

        # User A has capability active
        dispatch_a = self.context_a.orchestrator.multi_action_dispatch
        self.assertIsNotNone(dispatch_a.registry.get_capability(DESCRIPTOR_ID))
        self.assertTrue(any(c.get("capability") == DESCRIPTOR_ID for c in dispatch_a.discovery.discover_capabilities("video")))

        # User B has no capability in their registry or discovery
        dispatch_b = self.context_b.orchestrator.multi_action_dispatch
        self.assertIsNone(dispatch_b.registry.get_capability(DESCRIPTOR_ID))
        self.assertEqual(
            [c for c in dispatch_b.discovery.discover_capabilities("video") if c.get("capability") == DESCRIPTOR_ID],
            [],
        )
        self.assertNotIn(
            f"capability:{DESCRIPTOR_ID}",
            self.context_b.orchestrator.graphify_index.records,
        )

        # User B cannot execute User A's capability
        denied_b = dispatch_b.dispatch_explicit(
            DESCRIPTOR_ID,
            "dump_json",
            {"url": STABLE_PUBLIC_TEST_URL},
            session_id="session_user_b",
            user_text="try access",
            principal=self.context_b.orchestrator.principal,
        )
        self.assertIsNone(denied_b)

    def test_runner_enforces_pin_and_bounded_public_source(self):
        allowed = STABLE_PUBLIC_TEST_URL
        for unsafe in (
            "http://commons.wikimedia.org/wiki/File:Big_Buck_Bunny_4K.webm",
            "https://127.0.0.1/wiki/File:Big_Buck_Bunny_4K.webm",
            "https://commons.wikimedia.org:443/wiki/File:Big_Buck_Bunny_4K.webm",
            "https://example.com/wiki/File:Big_Buck_Bunny_4K.webm",
            allowed + "?redirect=https://127.0.0.1/",
        ):
            with self.assertRaises(ValueError):
                yt_dlp_runner.extract_metadata(unsafe)

        completed = SimpleNamespace(
            returncode=0,
            stdout=(
                '{"id":"bbb","title":"Big Buck Bunny 4K","extractor":"wikimedia.org",'
                '"webpage_url":"' + allowed + '"}'
            ),
            stderr="",
        )
        with (
            patch.object(yt_dlp_runner, "_installed_version", return_value=PINNED_YT_DLP_VERSION),
            patch.object(yt_dlp_runner.subprocess, "run", return_value=completed) as run,
        ):
            result = yt_dlp_runner.extract_metadata(allowed)
        self.assertEqual(result["id"], "bbb")
        args, kwargs = run.call_args
        self.assertIn("--ignore-config", args[0])
        self.assertEqual(args[0][-2:], ["--", allowed])
        self.assertFalse(kwargs["shell"])

        with (
            patch.object(yt_dlp_runner, "_installed_version", return_value="0.0.0"),
            patch.object(yt_dlp_runner.subprocess, "run") as run,
        ):
            with self.assertRaises(RuntimeError):
                yt_dlp_runner.extract_metadata(allowed)
        run.assert_not_called()

    def test_no_vendor_specific_execution_core_branch(self):
        """Prove that execution core files contain no vendor-specific branching for yt_dlp."""
        core_files = [
            "uri_core/external/adapters/cli.py",
            "uri_core/core/canonical_execution.py",
            "uri_core/core/multi_action_dispatch.py",
            "uri_core/capabilities/executor.py",
        ]
        for rel_path in core_files:
            with open(rel_path, "r", encoding="utf-8") as handle:
                content = handle.read()
            self.assertNotIn("yt_dlp", content, f"Vendor branch 'yt_dlp' found in {rel_path}")
            self.assertNotIn("yt-dlp", content, f"Vendor branch 'yt-dlp' found in {rel_path}")


if __name__ == "__main__":
    unittest.main()
