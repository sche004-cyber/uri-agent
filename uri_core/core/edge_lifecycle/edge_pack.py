"""Development-only Edge-pack declarations and local readiness inspection."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from .inventory import EdgeAssetInventory, default_inventory


@dataclass(frozen=True)
class EdgePackComponent:
    role: str
    model_id: str
    runtime_id: str
    source_url: Optional[str] = None
    required_dependency: Optional[str] = None
    license: str = "unknown"


DEVELOPMENT_EDGE_PACK: Tuple[EdgePackComponent, ...] = (
    EdgePackComponent("reflex_routing", "reflex-specialist", "portable"),
    EdgePackComponent("language_generator", "SmolLM2-135M", "portable"),
    EdgePackComponent("tiny_reasoner", "Qwen2.5-1.5B", "ollama"),
    EdgePackComponent("ocr_vision", "ocr-vision-specialist", "portable", required_dependency="model asset"),
    EdgePackComponent("speech_to_text", "faster-whisper-small", "portable", required_dependency="compatible local runtime"),
)


def inspect_development_edge_pack(
    inventory: Optional[EdgeAssetInventory] = None,
) -> Tuple[Dict[str, str], ...]:
    snapshot = (inventory or default_inventory()).snapshot()
    artifacts = snapshot.get("artifacts", {})
    runtimes = snapshot.get("runtimes", {})
    results = []
    for component in DEVELOPMENT_EDGE_PACK:
        key = f"{component.runtime_id}/{component.model_id}"
        runtime = runtimes.get(component.runtime_id, {})
        detected_models = {
            item.get("model_id") for item in runtime.get("models_detected", [])
            if isinstance(item, dict)
        }
        if key in artifacts or component.model_id in detected_models:
            status = "detected_available"
            reason = "registered or detected locally"
        elif component.source_url:
            status = "ready_for_download"
            reason = "declared user-space source available"
        elif component.required_dependency:
            status = "unavailable"
            reason = component.required_dependency
        else:
            status = "ready_for_import"
            reason = "manual verified model file required"
        results.append({
            "role": component.role, "model_id": component.model_id,
            "runtime_id": component.runtime_id, "status": status,
            "reason": reason, "license": component.license,
        })
    return tuple(results)
