"""M30.2: Capability Directory - proves the directory projects a
coherent, honest view over real collaborators (CapabilityFeasibility,
MultiActionCapabilityRegistry) without inventing metadata a source
doesn't provide, without flattening full action schemas into the
Level-1 summary view, and without leaking anything sensitive.

Uses REAL uri_core.core.capability_feasibility.CapabilityFeasibility
and REAL uri_core.capabilities.MultiActionCapabilityRegistry /
GmailCapability where the test calls for "real collaborator"
verification, plus small fakes for the honesty/edge-case tests where a
controlled fixture is clearer.

Nothing here touches orchestrator.py or the /ask path - the directory
is not wired into production execution in this milestone.
"""

import json
import os
import tempfile
import unittest

from uri_core.core.capability_directory import CapabilityDirectory
from uri_core.core.capability_feasibility import CapabilityFeasibility
from uri_core.core.capability_registry import CapabilityRegistry
from uri_core.core.turn_state import assemble_turn_state
from uri_core.capabilities import MultiActionCapabilityRegistry
from uri_core.capabilities.gmail import GmailCapability


def _write_registry(path, active_tools):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"active_tools": active_tools}, handle)


class RealLegacyRegistryTests(unittest.TestCase):
    """Directory built from the REAL, repository-shipped
    capabilities_registry.json (default path)."""

    def setUp(self):
        self.feasibility = CapabilityFeasibility()
        self.directory = CapabilityDirectory(capability_feasibility=self.feasibility)

    def test_directory_builds_successfully_from_real_legacy_registry(self):
        summaries = self.directory.summaries()
        self.assertTrue(len(summaries) > 0)
        ids = {entry["capability_id"] for entry in summaries}
        self.assertIn("draft_institutional_note", ids)

    def test_legacy_capability_appears_with_canonical_summary(self):
        entry = self.directory.describe("draft_institutional_note")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["source"], "legacy")
        self.assertIn("summary", entry)
        self.assertEqual(entry["actions"], ["draft_institutional_note"])

    def test_legacy_availability_from_capability_feasibility_is_projected(self):
        entry = self.directory.describe("draft_institutional_note")
        self.assertTrue(entry["availability_known"])
        self.assertIn(entry["available"], (True, False))


class RealMultiActionRegistryTests(unittest.TestCase):

    def setUp(self):
        self.registry = MultiActionCapabilityRegistry([GmailCapability()])
        self.directory = CapabilityDirectory(multi_action_registry=self.registry)

    def test_directory_builds_successfully_from_real_multi_action_registry(self):
        summaries = self.directory.summaries()
        ids = {entry["capability_id"] for entry in summaries}
        self.assertIn("Gmail", ids)

    def test_multi_action_gmail_appears_as_one_capability_with_scoped_actions(self):
        summary = next(e for e in self.directory.summaries() if e["capability_id"] == "Gmail")
        self.assertEqual(summary["source"], "multi_action")
        for action in (
            "list_labels", "search_messages", "read_message", "read_thread",
            "read_attachment", "create_draft", "apply_label", "archive_message",
        ):
            self.assertIn(action, summary["actions"])

    def test_unknown_multi_action_availability_remains_availability_known_false(self):
        summary = next(e for e in self.directory.summaries() if e["capability_id"] == "Gmail")
        self.assertFalse(summary["availability_known"])
        self.assertIsNone(summary["available"])

    def test_permission_metadata_is_projected_without_enforcing_anything(self):
        summary = next(e for e in self.directory.summaries() if e["capability_id"] == "Gmail")
        self.assertTrue(summary["permission_required"])
        # Projecting the flag never executes or grants anything - the
        # directory has no execute()/authorize() method at all.
        self.assertFalse(hasattr(self.directory, "execute"))
        self.assertFalse(hasattr(self.directory, "authorize"))


class ProgressiveDiscoveryTests(unittest.TestCase):

    def setUp(self):
        self.registry = MultiActionCapabilityRegistry([GmailCapability()])
        self.feasibility = CapabilityFeasibility()
        self.directory = CapabilityDirectory(
            capability_feasibility=self.feasibility, multi_action_registry=self.registry
        )

    def test_summary_view_excludes_full_action_schemas(self):
        for entry in self.directory.summaries():
            self.assertNotIn("action_schemas", entry)

    def test_detail_view_exposes_selected_capability_actions(self):
        detail = self.directory.describe("Gmail")
        self.assertIn("action_schemas", detail)
        self.assertIn("list_labels", detail["action_schemas"])
        self.assertIn("parameters", detail["action_schemas"]["list_labels"])

    def test_describe_unknown_capability_returns_none_not_fabricated(self):
        self.assertIsNone(self.directory.describe("does_not_exist_anywhere"))


class ApprovalMetadataTests(unittest.TestCase):

    def test_approval_metadata_is_projected_correctly(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        registry_path = os.path.join(temp_dir.name, "capabilities_registry.json")
        _write_registry(
            registry_path,
            {
                "risky_tool": {
                    "file_path": "x.py", "class_name": "X", "method": "run",
                    "status": "implemented", "availability": "available",
                    "approval_requirement": "user_approval_required",
                }
            },
        )
        feasibility = CapabilityFeasibility(
            capability_registry=CapabilityRegistry(registry_path=registry_path)
        )
        directory = CapabilityDirectory(capability_feasibility=feasibility)

        entry = directory.describe("risky_tool")
        self.assertTrue(entry["approval_required"])


class UnsupportedRegisteredEntryTests(unittest.TestCase):

    def test_not_implemented_capability_remains_explicitly_unsupported(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        registry_path = os.path.join(temp_dir.name, "capabilities_registry.json")
        _write_registry(
            registry_path,
            {
                "future_thing": {
                    "file_path": "x.py", "class_name": "X", "method": "run",
                    "status": "not_implemented", "availability": "unknown",
                }
            },
        )
        feasibility = CapabilityFeasibility(
            capability_registry=CapabilityRegistry(registry_path=registry_path)
        )
        directory = CapabilityDirectory(capability_feasibility=feasibility)

        entry = directory.describe("future_thing")
        self.assertFalse(entry["available"])
        self.assertEqual(entry["availability_reason"], "not_implemented")


class OverlapDetectionTests(unittest.TestCase):

    def test_legacy_gmail_vs_multi_action_gmail_overlap_is_identified_not_merged(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        registry_path = os.path.join(temp_dir.name, "capabilities_registry.json")
        _write_registry(
            registry_path,
            {
                "gmail_search": {
                    "file_path": "x.py", "class_name": "X", "method": "run",
                    "status": "implemented", "availability": "available",
                    "description": "Search the connected Gmail account.",
                }
            },
        )
        feasibility = CapabilityFeasibility(
            capability_registry=CapabilityRegistry(registry_path=registry_path)
        )
        registry = MultiActionCapabilityRegistry([GmailCapability()])
        directory = CapabilityDirectory(
            capability_feasibility=feasibility, multi_action_registry=registry
        )

        overlaps = directory.overlaps()
        self.assertEqual(len(overlaps), 1)
        self.assertEqual(overlaps[0]["legacy_id"], "gmail_search")
        self.assertEqual(overlaps[0]["multi_action_id"], "Gmail")
        # M30.2: neither side is ever silently RETIRED - both remain
        # fully resolvable via describe(), regardless of Brain-facing
        # visibility policy.
        self.assertIsNotNone(directory.describe("gmail_search"))
        self.assertIsNotNone(directory.describe("Gmail"))
        # M30.5A's own accepted Gmail-overlap policy: the Brain-visible
        # summaries() view shows exactly ONE canonical identity when a
        # richer multi-action equivalent exists - "gmail_search" is
        # suppressed from THIS view (not deleted, see describe() above),
        # "Gmail" remains. Pass resolve_overlaps=False for the
        # unfiltered, everything-registered view this test used before
        # M30.5A introduced the policy.
        visible_ids = {e["capability_id"] for e in directory.summaries()}
        self.assertNotIn("gmail_search", visible_ids)
        self.assertIn("Gmail", visible_ids)
        unfiltered_ids = {e["capability_id"] for e in directory.summaries(resolve_overlaps=False)}
        self.assertIn("gmail_search", unfiltered_ids)
        self.assertIn("Gmail", unfiltered_ids)


class PrivacyTests(unittest.TestCase):

    def test_no_credentials_tokens_or_secrets_appear_in_serialized_output(self):
        feasibility = CapabilityFeasibility()
        registry = MultiActionCapabilityRegistry([GmailCapability()])
        directory = CapabilityDirectory(
            capability_feasibility=feasibility, multi_action_registry=registry
        )

        serialized = json.dumps(directory.summaries())
        for token_shaped in ("token.json", "credentials.json", "client_secret", "api_key", "access_token"):
            self.assertNotIn(token_shaped, serialized.lower())


class TurnStateCompatibilityTests(unittest.TestCase):

    def test_turn_state_uses_directory_when_given(self):
        registry = MultiActionCapabilityRegistry([GmailCapability()])
        feasibility = CapabilityFeasibility()
        directory = CapabilityDirectory(
            capability_feasibility=feasibility, multi_action_registry=registry
        )

        result = assemble_turn_state(
            user_text="anything", session_id="s1", capability_directory=directory
        )

        ids = {e["capability_id"] for e in result.data["capability_summaries"]}
        self.assertIn("Gmail", ids)
        self.assertIn("draft_institutional_note", ids)

    def test_turn_state_m30_1_direct_projection_still_works_without_a_directory(self):
        # The M30.1 signature/behavior must remain unchanged for any
        # existing caller that never passes capability_directory.
        feasibility = CapabilityFeasibility()
        result = assemble_turn_state(
            user_text="anything", session_id="s1", capability_feasibility=feasibility
        )
        self.assertTrue(len(result.data["capability_summaries"]) > 0)


if __name__ == "__main__":
    unittest.main()
