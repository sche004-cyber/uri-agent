import json
import os

class LocalMemoryManager:
    def __init__(self, storage_path="uri_workspace/uri_memory.json"):
        self.storage_path = os.path.normpath(storage_path)
        self._ensure_storage()

    def _ensure_storage(self):
        folder = os.path.dirname(self.storage_path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        if not os.path.exists(self.storage_path):
            default_state = {
                "preferences": {},
                "guidelines": [],
                "corrections": []
            }
            self.save_memory(default_state)

    def load_memory(self) -> dict:
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            default_state = {
                "preferences": {},
                "guidelines": [],
                "corrections": []
            }
            self.save_memory(default_state)
            return default_state

    def save_memory(self, data: dict):
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def update_preference(self, key: str, value: str):
        memory = self.load_memory()
        if "preferences" not in memory:
            memory["preferences"] = {}
        memory["preferences"][key] = value
        self.save_memory(memory)
