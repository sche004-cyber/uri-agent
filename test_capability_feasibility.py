import json
import os
import tempfile
import unittest
from unittest.mock import patch

from uri_core.core.capability_feasibility import CapabilityFeasibility
from uri_core.core.capability_registry import CapabilityRegistry


def _write_registry(path, active_tools=None, planned_capabilities=None):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "schema_version": "1.0",
                "active_tools": active_tools or {},
                "planned_capabilities": planned_capabilities or {},
            },
            f,
        )


class CapabilityFeasibilityTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(
            suffix=".json", delete=False
        )
        self._tmp.close()
        self.registry_path = self._tmp.name

    def tearDown(self):
        try:
            os.remove(self.registry_path)
        except OSError:
            pass

    def _feasibility(self):
        registry = CapabilityRegistry(registry_path=self.registry_path)
        return CapabilityFeasibility(capability_registry=registry)

    def test_unavailable_missing_dependency_is_not_usable(self):
        _write_registry(
            self.registry_path,
            active_tools={
                "gmail_search": {
                    "status": "implemented",
                    "availability": "unavailable_missing_dependency",
                    "permissions": [],
                }
            },
        )

        with patch(
            "uri_core.core.capability_feasibility.list_connection_status",
            return_value=[],
        ):
            snapshot = self._feasibility().snapshot()

        self.assertFalse(snapshot["gmail_search"]["usable"])
        self.assertEqual(
            snapshot["gmail_search"]["gap_reason"], "unavailable_runtime"
        )

    def test_planned_capability_is_not_usable(self):
        _write_registry(
            self.registry_path,
            planned_capabilities={
                "pc_system_optimization": {
                    "status": "not_implemented",
                    "availability": "unavailable_missing_dependency",
                    "permissions": ["system_command_execution"],
                }
            },
        )

        with patch(
            "uri_core.core.capability_feasibility.list_connection_status",
            return_value=[],
        ):
            snapshot = self._feasibility().snapshot()

        entry = snapshot["pc_system_optimization"]
        self.assertFalse(entry["usable"])
        self.assertEqual(entry["gap_reason"], "not_implemented")

    def test_unknown_availability_on_implemented_entry_is_usable(self):
        """Preserves CapabilityDescriptor.gap_reason's documented rule:
        an incomplete registry entry (availability left "unknown")
        must never become a false-positive gap."""

        _write_registry(
            self.registry_path,
            active_tools={
                "extract_student_records": {
                    "status": "implemented",
                    "availability": "unknown",
                    "permissions": [],
                }
            },
        )

        with patch(
            "uri_core.core.capability_feasibility.list_connection_status",
            return_value=[],
        ):
            snapshot = self._feasibility().snapshot()

        self.assertTrue(snapshot["extract_student_records"]["usable"])
        self.assertIsNone(snapshot["extract_student_records"]["gap_reason"])

    def test_gmail_permission_blocked_when_not_connected(self):
        _write_registry(
            self.registry_path,
            active_tools={
                "gmail_create_draft": {
                    "status": "implemented",
                    "availability": "available",
                    "permissions": ["gmail_compose"],
                }
            },
        )

        with patch(
            "uri_core.core.capability_feasibility.list_connection_status",
            return_value=[
                {
                    "id": "gmail",
                    "status": "needs_authorization",
                    "detail": "Client secret found, but sign-in has not "
                    "been completed.",
                }
            ],
        ):
            snapshot = self._feasibility().snapshot()

        entry = snapshot["gmail_create_draft"]
        self.assertFalse(entry["usable"])
        self.assertEqual(len(entry["blocked_by"]), 1)
        self.assertIn("gmail_compose", entry["blocked_by"][0])

    def test_gmail_permission_usable_when_connected(self):
        _write_registry(
            self.registry_path,
            active_tools={
                "gmail_create_draft": {
                    "status": "implemented",
                    "availability": "available",
                    "permissions": ["gmail_compose"],
                }
            },
        )

        with patch(
            "uri_core.core.capability_feasibility.list_connection_status",
            return_value=[
                {"id": "gmail", "status": "connected", "detail": "Connected"}
            ],
        ):
            snapshot = self._feasibility().snapshot()

        entry = snapshot["gmail_create_draft"]
        self.assertTrue(entry["usable"])
        self.assertEqual(entry["blocked_by"], [])

    def test_permission_with_no_known_service_is_never_blocked(self):
        _write_registry(
            self.registry_path,
            active_tools={
                "web_search": {
                    "status": "implemented",
                    "availability": "available",
                    "permissions": ["external_web_search"],
                }
            },
        )

        with patch(
            "uri_core.core.capability_feasibility.list_connection_status",
            return_value=[],
        ):
            snapshot = self._feasibility().snapshot()

        self.assertTrue(snapshot["web_search"]["usable"])
        self.assertEqual(snapshot["web_search"]["blocked_by"], [])

    def test_missing_registry_degrades_to_empty_snapshot(self):
        os.remove(self.registry_path)

        with patch(
            "uri_core.core.capability_feasibility.list_connection_status",
            return_value=[],
        ):
            snapshot = self._feasibility().snapshot()

        self.assertEqual(snapshot, {})

    def test_connection_status_failure_never_raises_and_fails_open(self):
        _write_registry(
            self.registry_path,
            active_tools={
                "drive_search": {
                    "status": "implemented",
                    "availability": "available",
                    "permissions": ["google_drive_readonly"],
                }
            },
        )

        with patch(
            "uri_core.core.capability_feasibility.list_connection_status",
            side_effect=RuntimeError("boom"),
        ):
            snapshot = self._feasibility().snapshot()

        entry = snapshot["drive_search"]
        self.assertTrue(entry["usable"])
        self.assertEqual(entry["blocked_by"], [])

    def test_usable_ids_matches_snapshot(self):
        _write_registry(
            self.registry_path,
            active_tools={
                "extract_student_records": {
                    "status": "implemented",
                    "availability": "available",
                    "permissions": [],
                },
                "gmail_search": {
                    "status": "implemented",
                    "availability": "unavailable_missing_dependency",
                    "permissions": ["gmail_readonly"],
                },
            },
        )

        with patch(
            "uri_core.core.capability_feasibility.list_connection_status",
            return_value=[],
        ):
            feasibility = self._feasibility()
            ids = feasibility.usable_ids()

        self.assertIn("extract_student_records", ids)
        self.assertNotIn("gmail_search", ids)

    def test_never_writes_to_registry(self):
        _write_registry(
            self.registry_path,
            active_tools={
                "extract_student_records": {
                    "status": "implemented",
                    "availability": "available",
                    "permissions": [],
                }
            },
        )

        before = os.path.getmtime(self.registry_path)

        with patch(
            "uri_core.core.capability_feasibility.list_connection_status",
            return_value=[],
        ):
            self._feasibility().snapshot()

        after = os.path.getmtime(self.registry_path)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
