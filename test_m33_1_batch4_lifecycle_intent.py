"""M33.1 Batch 4 - generic natural-language/UI lifecycle seam acceptance evidence."""

from __future__ import annotations

import os
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("URI_EXTERNAL_CREDENTIAL_SECRET", "test-external-credential-secret")

from uri_core.app import server
from uri_core.external import lifecycle_intent
from uri_core.external.descriptors.strip_json_comments import V2_REVISION, V3_REVISION
from uri_core.external.descriptors.yt_dlp import DESCRIPTOR_ID as YT_DLP_DESCRIPTOR_ID


class LifecycleIntentTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="uri_batch4_intent_")
        self.original_root = server._USER_STATE_ROOT
        server._USER_STATE_ROOT = self.root
        self.user_a, self.user_b = str(uuid.uuid4()), str(uuid.uuid4())
        self.context_a = server._build_user_context(self.user_a)
        self.context_b = server._build_user_context(self.user_b)

    def tearDown(self):
        server._USER_STATE_ROOT = self.original_root
        shutil.rmtree(self.root, ignore_errors=True)

    def test_invalid_and_unsupported_intents_fail_closed(self):
        self.assertEqual(
            lifecycle_intent.execute_lifecycle_intent(self.context_a, self.user_a, operation="", target_id="yt_dlp")["status"],
            "invalid_intent",
        )
        self.assertEqual(
            lifecycle_intent.execute_lifecycle_intent(self.context_a, self.user_a, operation="install", target_id="")["status"],
            "invalid_intent",
        )
        self.assertEqual(
            lifecycle_intent.execute_lifecycle_intent(self.context_a, self.user_a, operation="teleport", target_id="yt_dlp")["status"],
            "unsupported_operation",
        )
        self.assertEqual(
            lifecycle_intent.execute_lifecycle_intent(self.context_a, self.user_a, operation="install", target_id="rm -rf /")["status"],
            "unknown_target",
        )
        # A skill-only operation named against a service, and vice versa,
        # both fail closed as unknown/unsupported rather than doing anything.
        self.assertEqual(
            lifecycle_intent.execute_lifecycle_intent(self.context_a, self.user_a, operation="connect", target_id="yt_dlp")["status"],
            "unknown_target",
        )
        self.assertEqual(
            lifecycle_intent.execute_lifecycle_intent(self.context_a, self.user_a, operation="install", target_id="gmail")["status"],
            "unknown_target",
        )

    def test_yt_dlp_install_enable_disable_are_generic_and_isolated(self):
        installed = lifecycle_intent.execute_lifecycle_intent(
            self.context_a, self.user_a, operation="install", target_id="yt_dlp",
        )
        self.assertEqual(installed["status"], "success")
        self.assertIn("enabled", installed["state"])

        # Not yet enabled -> enabling now flips it live.
        enabled = lifecycle_intent.execute_lifecycle_intent(
            self.context_a, self.user_a, operation="enable", target_id="yt_dlp",
        )
        self.assertEqual(enabled["status"], "success")
        self.assertTrue(
            self.context_a.orchestrator.multi_action_dispatch.registry.get_capability(YT_DLP_DESCRIPTOR_ID) is not None
        )

        disabled = lifecycle_intent.execute_lifecycle_intent(
            self.context_a, self.user_a, operation="disable", target_id="yt_dlp",
        )
        self.assertEqual(disabled["status"], "success")
        self.assertIsNone(self.context_a.orchestrator.multi_action_dispatch.registry.get_capability(YT_DLP_DESCRIPTOR_ID))

        # User B never installed anything - enable/disable report not_installed,
        # never success, never touching User A's state.
        self.assertEqual(
            lifecycle_intent.execute_lifecycle_intent(self.context_b, self.user_b, operation="enable", target_id="yt_dlp")["status"],
            "not_installed",
        )
        self.assertIsNone(self.context_b.orchestrator.multi_action_dispatch.registry.get_capability(YT_DLP_DESCRIPTOR_ID))

    def test_sanitized_state_never_leaks_internal_fields(self):
        installed = lifecycle_intent.execute_lifecycle_intent(
            self.context_a, self.user_a, operation="install", target_id="yt_dlp",
        )
        allowed = {"presence", "qualification", "configuration", "authentication", "health", "enabled", "update_available"}
        self.assertTrue(set(installed["state"]) <= allowed)

    def test_strip_json_comments_install_update_remove_and_rejected_install_leave_no_trace(self):
        installed = lifecycle_intent.execute_lifecycle_intent(
            self.context_a, self.user_a, operation="install", target_id="strip_json_comments", revision=V2_REVISION,
        )
        self.assertEqual(installed["status"], "success")
        lifecycle_intent.execute_lifecycle_intent(self.context_a, self.user_a, operation="enable", target_id="strip_json_comments")

        updated = lifecycle_intent.execute_lifecycle_intent(
            self.context_a, self.user_a, operation="update", target_id="strip_json_comments", revision=V3_REVISION,
        )
        self.assertEqual(updated["status"], "success")

        removed = lifecycle_intent.execute_lifecycle_intent(
            self.context_a, self.user_a, operation="remove", target_id="strip_json_comments",
        )
        self.assertEqual(removed["status"], "success")
        self.assertIsNone(self.context_a.external_capability_store.get(self.user_a, "skill.strip_json_comments"))

        # A removed skill reports not_installed, not success/failure noise.
        removed_again = lifecycle_intent.execute_lifecycle_intent(
            self.context_a, self.user_a, operation="remove", target_id="strip_json_comments",
        )
        self.assertEqual(removed_again["status"], "not_installed")

    def test_install_failure_never_leaks_a_raw_exception_or_secret(self):
        with patch(
            "uri_core.external.packages.strip_json_comments.install_and_register",
            side_effect=RuntimeError("token=ghp_do_not_leak"),
        ):
            result = lifecycle_intent.execute_lifecycle_intent(
                self.context_a, self.user_a, operation="install", target_id="strip_json_comments",
            )
        self.assertEqual(result["status"], "unavailable")
        self.assertNotIn("message", result)
        self.assertNotIn("ghp_", str(result))

    def test_service_connect_requires_real_credentials_and_disconnect_is_generic(self):
        no_creds = lifecycle_intent.execute_lifecycle_intent(
            self.context_a, self.user_a, operation="connect", target_id="github",
        )
        self.assertEqual(no_creds["status"], "credentials_required")

        connected = lifecycle_intent.execute_lifecycle_intent(
            self.context_a, self.user_a, operation="connect", target_id="github",
            credentials={"token": "ghp_example"}, scopes=["repo"],
        )
        self.assertEqual(connected["status"], "success")
        self.assertEqual(connected["state"]["status"], "connected")
        self.assertNotIn("token", str(connected["state"]))
        self.assertEqual(set(connected["state"]), {"id", "status"})

        disconnected = lifecycle_intent.execute_lifecycle_intent(
            self.context_a, self.user_a, operation="disconnect", target_id="github",
        )
        self.assertEqual(disconnected["status"], "success")
        self.assertEqual(disconnected["state"]["status"], "not_connected")

        # User B's own github connection state is untouched by User A's actions.
        self.assertEqual(
            self.context_b.connected_service_store.get_status(self.user_b, "github")["status"], "not_connected",
        )

    def test_corrupt_lifecycle_or_service_state_fails_closed_without_overwrite(self):
        capability_path = Path(self.root) / self.user_a / "external_capabilities.json"
        capability_path.parent.mkdir(parents=True, exist_ok=True)
        capability_path.write_text("{not json", encoding="utf-8")
        result = lifecycle_intent.execute_lifecycle_intent(
            self.context_a, self.user_a, operation="install", target_id="yt_dlp",
        )
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(capability_path.read_text(encoding="utf-8"), "{not json")

        credential = {"token": "ghp_remains_private"}
        self.context_a.connected_service_store.connect(self.user_a, "github", credential)
        service_path = Path(self.root) / self.user_a / "connected_services.json"
        service_path.write_text("{not json", encoding="utf-8")
        disconnected = lifecycle_intent.execute_lifecycle_intent(
            self.context_a, self.user_a, operation="disconnect", target_id="github",
        )
        self.assertEqual(disconnected["status"], "unavailable")
        self.assertEqual(service_path.read_text(encoding="utf-8"), "{not json")
        self.assertEqual(
            self.context_a.external_credential_store.get_credential(self.user_a, "github"), credential,
        )

    def test_known_skill_targets_is_descriptive_only(self):
        catalog = lifecycle_intent.known_skill_targets()
        self.assertIn("yt_dlp", catalog)
        self.assertIn("strip_json_comments", catalog)
        self.assertEqual(set(catalog["yt_dlp"]["operations"]), {"install", "enable", "disable"})
        self.assertEqual(
            set(catalog["strip_json_comments"]["operations"]), {"install", "enable", "disable", "update", "remove"},
        )


if __name__ == "__main__":
    unittest.main()
