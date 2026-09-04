import json
import importlib
import os
from uri_core.core.friction_logger import FrictionLogger

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
                return {"status": "error", "message": f"URI lacks the capability: {tool_name}"}
            
            tool_info = tools[tool_name]
            
            # Convert file path to a Python module path (e.g., uri_core/tools/xyz.py -> uri_core.tools.xyz)
            module_path = tool_info["file_path"].replace("/", ".").replace("\\", ".").replace(".py", "")
            class_name = tool_info["class_name"]
            method_name = tool_info["method"]
            
            # Dynamically load the module and class
            module = importlib.import_module(module_path)
            tool_class = getattr(module, class_name)
            
            # Instantiate the class and execute the method
            instance = tool_class()
            method = getattr(instance, method_name)
            
            result = method(**kwargs)
            return {"status": "success", "data": result}
            
        except Exception as e:
            # Log any runtime crashes to trigger Hermes eventually
            self.friction_logger.log_failure(tool_name, f"Execution crash: {str(e)}")
            return {"status": "error", "message": f"Execution failed: {str(e)}"}
