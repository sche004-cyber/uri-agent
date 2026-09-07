"""Item 4/8 of the URI architecture spec: ToolDispatcher.execute_tool()
must return structured, distinguishable diagnostic information - never
only a generic "capability not found" string - so the Brain (and
diagnostics_context.py) can tell an unregistered capability apart from
a capability whose own module failed to load, apart from a real
runtime exception during execution. Every existing "status"/"message"/
"data" key and its exact text is unchanged - the new fields are purely
additive (see dispatcher.py)."""

import json
import os
import tempfile
import types
import unittest
from unittest.mock import patch

from uri_core.core.dispatcher import (
    ERROR_CAPABILITY_UNREGISTERED,
    ERROR_EXECUTION_EXCEPTION,
    ERROR_LOAD_FAILURE,
    ToolDispatcher,
)


class ToolDispatcherStructuredErrorTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.registry_path = os.path.join(
            self.temp_dir.name, "capabilities_registry.json"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_registry(self, active_tools):
        with open(self.registry_path, "w", encoding="utf-8") as file:
            json.dump({"active_tools": active_tools}, file)

    def test_unregistered_capability_reports_capability_unregistered(self):
        self._write_registry({})

        dispatcher = ToolDispatcher(registry_path=self.registry_path)
        result = dispatcher.execute_tool("does_not_exist")

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_type"], ERROR_CAPABILITY_UNREGISTERED)
        self.assertEqual(result["capability"], "does_not_exist")
        self.assertIn("does_not_exist", result["message"])

    def test_missing_module_reports_component_load_failure(self):
        self._write_registry(
            {
                "broken_tool": {
                    "file_path": "uri_core/tools/no_such_module.py",
                    "class_name": "NoSuchClass",
                    "method": "execute",
                }
            }
        )

        dispatcher = ToolDispatcher(registry_path=self.registry_path)
        result = dispatcher.execute_tool("broken_tool")

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_type"], ERROR_LOAD_FAILURE)
        self.assertEqual(result["capability"], "broken_tool")
        self.assertIn("uri_core.tools.no_such_module", result["component"])

    def test_real_execution_exception_reports_execution_exception(self):
        self._write_registry(
            {
                "flaky_tool": {
                    "file_path": "uri_core/tools/flaky_tool.py",
                    "class_name": "FlakyTool",
                    "method": "execute",
                }
            }
        )

        class FlakyTool:
            def execute(self, **kwargs):
                raise RuntimeError("simulated runtime crash")

        fake_module = types.ModuleType("uri_core.tools.flaky_tool")
        fake_module.FlakyTool = FlakyTool

        dispatcher = ToolDispatcher(registry_path=self.registry_path)

        with patch(
            "uri_core.core.dispatcher.importlib.import_module",
            return_value=fake_module,
        ):
            result = dispatcher.execute_tool("flaky_tool")

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_type"], ERROR_EXECUTION_EXCEPTION)
        self.assertEqual(result["capability"], "flaky_tool")
        self.assertIn("simulated runtime crash", result["message"])

    def test_successful_execution_is_unaffected(self):
        self._write_registry(
            {
                "reliable_tool": {
                    "file_path": "uri_core/tools/reliable_tool.py",
                    "class_name": "ReliableTool",
                    "method": "execute",
                }
            }
        )

        class ReliableTool:
            def execute(self, **kwargs):
                return {"ok": True}

        fake_module = types.ModuleType("uri_core.tools.reliable_tool")
        fake_module.ReliableTool = ReliableTool

        dispatcher = ToolDispatcher(registry_path=self.registry_path)

        with patch(
            "uri_core.core.dispatcher.importlib.import_module",
            return_value=fake_module,
        ):
            result = dispatcher.execute_tool("reliable_tool")

        self.assertEqual(result, {"status": "success", "data": {"ok": True}})


if __name__ == "__main__":
    unittest.main()
