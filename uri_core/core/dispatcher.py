import json
import importlib
import os
from uri_core.core.friction_logger import FrictionLogger

# Structured error_type values (item 4/8 of the URI architecture spec):
# distinct diagnostic categories the Brain can tell apart, rather than
# one generic "error" status with only a human-readable message. None
# of these change execute_tool()'s existing "status"/"message" keys or
# their existing text - every field below is additive, so any caller
# that only ever read "status"/"message"/"data" keeps working exactly
# as before.
ERROR_CAPABILITY_UNREGISTERED = "capability_unregistered"
ERROR_LOAD_FAILURE = "component_load_failure"
ERROR_EXECUTION_EXCEPTION = "execution_exception"


class ToolDispatcher:
    def __init__(self, registry_path="uri_workspace/capabilities_registry.json"):
        self.registry_path = os.path.normpath(registry_path)
        self.friction_logger = FrictionLogger()

    def execute_tool(self, tool_name: str, **kwargs):
        try:
            # Load the registry safely
            with open(self.registry_path, "r", encoding="utf-8-sig") as f:
                registry = json.load(f)

            tools = registry.get("active_tools", {})
            if tool_name not in tools:
                self.friction_logger.log_failure(tool_name, f"Tool '{tool_name}' missing from registry.")
                return {
                    "status": "error",
                    "message": f"URI lacks the capability: {tool_name}",
                    "error_type": ERROR_CAPABILITY_UNREGISTERED,
                    "capability": tool_name,
                    "component": None,
                }

            tool_info = tools[tool_name]

            # Convert file path to a Python module path (e.g., uri_core/tools/xyz.py -> uri_core.tools.xyz)
            module_path = tool_info["file_path"].replace("/", ".").replace("\\", ".").replace(".py", "")
            class_name = tool_info["class_name"]
            method_name = tool_info["method"]
            component = f"{module_path}.{class_name}.{method_name}"

            try:
                # Dynamically load the module and class
                module = importlib.import_module(module_path)
                tool_class = getattr(module, class_name)

                # Instantiate the class and execute the method
                instance = tool_class()
                method = getattr(instance, method_name)

            except Exception as load_exc:
                # Distinct from a runtime execution crash below: the
                # capability is registered, but its own code/module
                # could not even be loaded (missing file, import error,
                # renamed class/method) - a different diagnosable cause
                # than the tool running and then failing.
                self.friction_logger.log_failure(
                    tool_name, f"Load failure: {str(load_exc)}"
                )
                return {
                    "status": "error",
                    "message": f"Execution failed: {str(load_exc)}",
                    "error_type": ERROR_LOAD_FAILURE,
                    "capability": tool_name,
                    "component": component,
                }

            result = method(**kwargs)
            return {"status": "success", "data": result}

        except Exception as e:
            # Log any runtime crashes to trigger Hermes eventually
            self.friction_logger.log_failure(tool_name, f"Execution crash: {str(e)}")
            return {
                "status": "error",
                "message": f"Execution failed: {str(e)}",
                "error_type": ERROR_EXECUTION_EXCEPTION,
                "capability": tool_name,
                "component": None,
            }
