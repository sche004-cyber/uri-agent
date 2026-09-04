import json
import os
import tempfile
import unittest

from uri_core.core.capability_registry import (
    CapabilityDescriptor,
    CapabilityRegistry,
)


class CapabilityRegistryTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.registry_path = os.path.join(
            self.temp_dir.name, "capabilities_registry.json"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write(self, data: dict) -> None:
        with open(self.registry_path, "w", encoding="utf-8") as file:
            json.dump(data, file)

    def test_missing_file_returns_empty_list(self):
        registry = CapabilityRegistry(registry_path=self.registry_path)
        self.assertEqual(registry.list_capabilities(), [])

    def test_corrupted_file_degrades_to_an_empty_list(self):
        with open(self.registry_path, "w", encoding="utf-8") as file:
            file.write("{ not valid json")

        registry = CapabilityRegistry(registry_path=self.registry_path)
        self.assertEqual(registry.list_capabilities(), [])

    def test_active_tool_becomes_implemented_descriptor(self):
        self._write(
            {
                "active_tools": {
                    "draft_note": {
                        "file_path": "x.py",
                        "class_name": "X",
                        "method": "run",
                        "description": "Draft a note.",
                        "status": "implemented",
                        "availability": "available",
                        "permissions": [],
                        "approval_requirement": "none",
                        "risk": "controlled",
                        "platform": "any",
                        "limitations": "",
                    }
                }
            }
        )

        registry = CapabilityRegistry(registry_path=self.registry_path)
        descriptors = registry.list_capabilities()

        self.assertEqual(len(descriptors), 1)
        descriptor = descriptors[0]
        self.assertIsInstance(descriptor, CapabilityDescriptor)
        self.assertEqual(descriptor.id, "draft_note")
        self.assertEqual(descriptor.status, "implemented")
        self.assertTrue(descriptor.is_executable)

    def test_planned_capability_becomes_not_implemented_descriptor(self):
        self._write(
            {
                "planned_capabilities": {
                    "pc_system_optimization": {
                        "description": "Optimize the PC.",
                        "status": "not_implemented",
                        "availability": "unavailable_missing_dependency",
                        "permissions": ["system_command_execution"],
                        "approval_requirement": "user_approval_required",
                        "risk": "high",
                        "platform": "windows_powershell",
                        "limitations": "No execution adapter exists yet.",
                    }
                }
            }
        )

        registry = CapabilityRegistry(registry_path=self.registry_path)
        descriptors = registry.list_capabilities()

        self.assertEqual(len(descriptors), 1)
        descriptor = descriptors[0]
        self.assertEqual(descriptor.status, "not_implemented")
        self.assertFalse(descriptor.is_executable)
        self.assertEqual(descriptor.approval_requirement, "user_approval_required")
        self.assertEqual(descriptor.risk, "high")

    def test_active_tool_missing_descriptor_fields_defaults_safely(self):
        # Legacy-shaped entry: only the execution fields ToolDispatcher
        # needs, none of the new descriptor metadata. Must not raise,
        # and must default rather than guess.
        self._write(
            {
                "active_tools": {
                    "legacy_tool": {
                        "file_path": "x.py",
                        "class_name": "X",
                        "method": "run",
                    }
                }
            }
        )

        registry = CapabilityRegistry(registry_path=self.registry_path)
        descriptor = registry.describe_status("legacy_tool")

        self.assertIsNotNone(descriptor)
        self.assertEqual(descriptor.status, "implemented")
        self.assertEqual(descriptor.availability, "unknown")
        self.assertEqual(descriptor.approval_requirement, "none")
        self.assertEqual(descriptor.risk, "unknown")
        self.assertEqual(descriptor.permissions, [])

    def test_invalid_enum_values_degrade_to_unknown_not_guessed(self):
        self._write(
            {
                "active_tools": {
                    "weird_tool": {
                        "file_path": "x.py",
                        "class_name": "X",
                        "method": "run",
                        "availability": "definitely_works_trust_me",
                        "risk": "totally_safe",
                        "approval_requirement": "whatever",
                    }
                }
            }
        )

        registry = CapabilityRegistry(registry_path=self.registry_path)
        descriptor = registry.describe_status("weird_tool")

        self.assertEqual(descriptor.availability, "unknown")
        self.assertEqual(descriptor.risk, "unknown")
        self.assertEqual(descriptor.approval_requirement, "none")

    def test_describe_status_returns_none_for_unknown_id(self):
        self._write({"active_tools": {}})
        registry = CapabilityRegistry(registry_path=self.registry_path)
        self.assertIsNone(registry.describe_status("nope"))

    def test_known_gaps_excludes_implemented_capabilities(self):
        self._write(
            {
                "active_tools": {
                    "real_tool": {
                        "file_path": "x.py",
                        "class_name": "X",
                        "method": "run",
                        "status": "implemented",
                    }
                },
                "planned_capabilities": {
                    "future_thing": {
                        "description": "Not built yet.",
                        "status": "not_implemented",
                    }
                },
            }
        )

        registry = CapabilityRegistry(registry_path=self.registry_path)
        gaps = registry.known_gaps()

        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0].id, "future_thing")

    def test_known_gaps_are_never_executable(self):
        self._write(
            {
                "planned_capabilities": {
                    "future_thing": {
                        "description": "Not built yet.",
                        "status": "not_implemented",
                    }
                }
            }
        )

        registry = CapabilityRegistry(registry_path=self.registry_path)

        for gap in registry.known_gaps():
            self.assertFalse(gap.is_executable)

    def test_real_registry_file_loads_without_error(self):
        # Exercises the actual, restructured
        # uri_workspace/capabilities_registry.json shipped with this
        # milestone - proves the real file matches the schema this
        # module expects.
        registry = CapabilityRegistry()
        descriptors = registry.list_capabilities()

        ids = {descriptor.id for descriptor in descriptors}
        self.assertIn("extract_student_records", ids)
        self.assertIn("draft_institutional_note", ids)
        self.assertIn("draft_institutional_order", ids)
        self.assertIn("fetch_drive_spreadsheet", ids)
        self.assertIn("pc_system_optimization", ids)

        pc_optimization = registry.describe_status("pc_system_optimization")
        self.assertEqual(pc_optimization.status, "not_implemented")
        self.assertFalse(pc_optimization.is_executable)


if __name__ == "__main__":
    unittest.main()
