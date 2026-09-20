"""Persistent, Edge-scoped inventory of observed and URI-managed assets."""
from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import ModelArtifactRecord, RuntimeDetectionRecord
from .storage import assert_confined, confined_path


class EdgeAssetInventory:
    def __init__(self, path: Optional[Path] = None):
        self.path = assert_confined(path) if path is not None else confined_path("inventory.json", create_parent=True)

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": "1.0", "runtimes": {}, "artifacts": {}}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("schema_version") != "1.0":
            raise ValueError("unsupported Edge asset inventory")
        data.setdefault("runtimes", {})
        data.setdefault("artifacts", {})
        return data

    def _save(self, data: Dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        staging = self.path.with_suffix(self.path.suffix + ".staging")
        staging.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(staging, self.path)

    def record_detection(self, record: RuntimeDetectionRecord) -> None:
        data = self._load()
        payload = asdict(record)
        payload.update({
            "source_type": "detected_runtime",
            "source": record.endpoint.url,
            "license": "unknown",
        })
        data["runtimes"][record.runtime_id] = payload
        self._save(data)

    def register_artifact(self, record: ModelArtifactRecord) -> None:
        data = self._load()
        key = f"{record.runtime_id}/{record.model_id}"
        data["artifacts"][key] = asdict(record)
        self._save(data)

    def deregister_artifact(self, runtime_id: str, model_id: str) -> bool:
        data = self._load()
        removed = data["artifacts"].pop(f"{runtime_id}/{model_id}", None) is not None
        if removed:
            self._save(data)
        return removed

    def snapshot(self) -> Dict[str, Any]:
        return self._load()

    def list_artifacts(self) -> List[Dict[str, Any]]:
        return list(self._load()["artifacts"].values())


def default_inventory() -> EdgeAssetInventory:
    return EdgeAssetInventory()
