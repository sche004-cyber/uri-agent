import json
import os
import tempfile
import unittest

from uri_core.core.capability_planner import CapabilityPlanner


class CapabilityPlannerRegistryRegressionTests(unittest.TestCase):
    """Proves the restructured capabilities_registry.json (Milestone 6)
    did not change CapabilityPlanner's actual selection behaviour for
    the 4 real tools - _score_tool()/_load_tools() are unmodified, but
    the registry file's shape changed, so this is what actually proves
    nothing broke."""

    def setUp(self):
        self.planner = CapabilityPlanner()

    def test_note_drafting_request_selects_draft_institutional_note(self):
        result = self.planner.plan(
            {
                "task_type": "document drafting",
                "domain": "administrative",
                "goal": "prepare a note",
                "requested_output": "office note",
                "entities": ["office note"],
            }
        )

        self.assertEqual(result["status"], "capability_selected")
        self.assertEqual(result["tool_name"], "draft_institutional_note")

    def test_order_drafting_request_selects_draft_institutional_order(self):
        result = self.planner.plan(
            {
                "task_type": "document generation",
                "domain": "administrative",
                "goal": "issue an office order",
                "requested_output": "office order",
                "entities": ["office order"],
            }
        )

        self.assertEqual(result["status"], "capability_selected")
        self.assertEqual(result["tool_name"], "draft_institutional_order")

    def test_cgpa_lookup_selects_extract_student_records(self):
        result = self.planner.plan(
            {
                "task_type": "data retrieval",
                "domain": "academic records",
                "goal": "find the cgpa",
                "requested_output": "cgpa",
                "entities": ["roll number"],
            }
        )

        self.assertEqual(result["status"], "capability_selected")
        self.assertEqual(result["tool_name"], "extract_student_records")

    def test_spreadsheet_request_selects_fetch_drive_spreadsheet(self):
        result = self.planner.plan(
            {
                "task_type": "data retrieval",
                "domain": "administrative",
                "goal": "read the spreadsheet",
                "requested_output": "spreadsheet",
                "entities": ["google sheet"],
            }
        )

        self.assertEqual(result["status"], "capability_selected")
        self.assertEqual(result["tool_name"], "fetch_drive_spreadsheet")


class CapabilityPlannerGapAwarenessTests(unittest.TestCase):
    """New in Milestone 6: the two "no candidate" branches now include
    known_gaps - informational only. A planned/not_implemented
    capability must never become a selectable candidate."""

    def test_no_confident_match_includes_known_gaps(self):
        planner = CapabilityPlanner()

        result = planner.plan(
            {
                "task_type": "something unrelated",
                "domain": "",
                "goal": "optimize my pc",
                "requested_output": "",
                "entities": [],
            }
        )

        self.assertEqual(result["status"], "planning_required")
        self.assertIn("known_gaps", result)
        gap_ids = {gap["id"] for gap in result["known_gaps"]}
        self.assertIn("pc_system_optimization", gap_ids)

    def test_known_gaps_entries_carry_a_gap_reason(self):
        # Milestone 8A correction: the response-narrative path needs
        # to distinguish "not_implemented" (no adapter at all) from
        # "unavailable_runtime" (an adapter exists but this runtime
        # can't use it) - this is the field it reads.
        planner = CapabilityPlanner()

        result = planner.plan(
            {
                "task_type": "something unrelated",
                "domain": "",
                "goal": "optimize my pc",
                "requested_output": "",
                "entities": [],
            }
        )

        gaps_by_id = {gap["id"]: gap for gap in result["known_gaps"]}
        self.assertEqual(
            gaps_by_id["pc_system_optimization"]["reason"],
            "not_implemented",
        )
        self.assertEqual(
            gaps_by_id["fetch_drive_spreadsheet"]["reason"],
            "unavailable_runtime",
        )

    def test_pc_optimization_request_is_never_selected(self):
        planner = CapabilityPlanner()

        result = planner.plan(
            {
                "task_type": "system optimization",
                "domain": "pc performance",
                "goal": "optimize my pc, clean up disk and check temperature",
                "requested_output": "pc optimization",
                "entities": ["cpu", "gpu", "ram", "temperature"],
            }
        )

        self.assertNotEqual(result["status"], "capability_selected")
        self.assertIsNone(result["tool_name"])

    def test_empty_registry_still_reports_known_gaps(self):
        temp_dir = tempfile.TemporaryDirectory()
        try:
            registry_path = os.path.join(
                temp_dir.name, "capabilities_registry.json"
            )
            with open(registry_path, "w", encoding="utf-8") as file:
                json.dump(
                    {
                        "active_tools": {},
                        "planned_capabilities": {
                            "future_thing": {
                                "description": "Not built yet.",
                                "status": "not_implemented",
                            }
                        },
                    },
                    file,
                )

            planner = CapabilityPlanner(registry_path=registry_path)
            result = planner.plan({"task_type": "anything"})

            self.assertEqual(result["status"], "planning_required")
            self.assertEqual(
                [gap["id"] for gap in result["known_gaps"]],
                ["future_thing"],
            )
        finally:
            temp_dir.cleanup()

    def test_capability_registry_failure_degrades_to_empty_gaps(self):
        # A registry that fails to load must not break planning itself
        # - _known_gaps() degrades to an empty list rather than
        # propagating the failure.
        planner = CapabilityPlanner(
            registry_path=os.path.join(
                tempfile.gettempdir(), "does-not-exist-at-all.json"
            )
        )

        result = planner.plan({"task_type": "anything"})

        self.assertEqual(result["status"], "planning_required")
        self.assertEqual(result["known_gaps"], [])

    def test_selected_capability_response_has_no_known_gaps_key(self):
        # The success branch's shape is unchanged - known_gaps only
        # appears on a genuine gap, not on every response.
        planner = CapabilityPlanner()

        result = planner.plan(
            {
                "task_type": "document drafting",
                "domain": "administrative",
                "goal": "prepare a note",
                "requested_output": "office note",
                "entities": ["office note"],
            }
        )

        self.assertEqual(result["status"], "capability_selected")
        self.assertNotIn("known_gaps", result)


if __name__ == "__main__":
    unittest.main()
