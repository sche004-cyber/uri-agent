import json
import os
from datetime import datetime

class FrictionLogger:
    def __init__(self, log_path="uri_workspace/friction_log.json"):
        self.log_path = os.path.normpath(log_path)
        self._ensure_log()

    def _ensure_log(self):
        folder = os.path.dirname(self.log_path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        if not os.path.exists(self.log_path):
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump({"failures": {}}, f, indent=4)

    def log_failure(self, task_name: str, error_context: str):
        try:
            # utf-8-sig safely strips any hidden Windows BOM characters
            with open(self.log_path, "r", encoding="utf-8-sig") as f: 
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {"failures": {}}

        if task_name not in data["failures"]:
            data["failures"][task_name] = []
            
        data["failures"][task_name].append({
            "timestamp": datetime.now().isoformat(),
            "error_context": error_context
        })

        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def check_threshold(self, task_name: str, threshold: int = 3) -> bool:
        try:
            with open(self.log_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return False
            
        task_failures = data.get("failures", {}).get(task_name, [])
        return len(task_failures) >= threshold
