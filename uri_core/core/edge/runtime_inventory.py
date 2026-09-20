"""Deployment-owned Edge runtime inventory and effective-policy projection."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Optional


@dataclass(frozen=True)
class RuntimeProfile:
    runtime_id: str
    models: FrozenSet[str]
    status: str = "ready"
    enabled: bool = True
    qualified_assistance_kinds: FrozenSet[str] = frozenset()


@dataclass(frozen=True)
class EdgeRuntimeInventory:
    """Immutable process/deployment policy. User preferences cannot mutate it."""
    enabled: bool = True
    runtimes: Dict[str, RuntimeProfile] = field(default_factory=dict)
    local_only: bool = True

    def selection_status(self, runtime_id: Optional[str], model_id: Optional[str]) -> str:
        if not self.enabled:
            return "disabled_by_policy"
        if not runtime_id or not model_id:
            return "not_configured"
        profile = self.runtimes.get(runtime_id)
        if profile is None:
            return "unavailable"
        if not profile.enabled:
            return "disabled_by_policy"
        if model_id not in profile.models:
            return "missing_artifact"
        return profile.status

    def validate_selection(self, runtime_id: Optional[str], model_id: Optional[str]) -> None:
        if runtime_id is None and model_id is None:
            return
        if not isinstance(runtime_id, str) or not isinstance(model_id, str):
            raise ValueError("edge runtime_id and model_id must be supplied together")
        profile = self.runtimes.get(runtime_id)
        if profile is None:
            raise ValueError("unknown Edge runtime")
        if not profile.enabled:
            raise ValueError("Edge runtime is disabled by deployment policy")
        if model_id not in profile.models:
            raise ValueError("unknown Edge model for runtime")

    def assistance_qualified(self, runtime_id: Optional[str], kind: str) -> bool:
        profile = self.runtimes.get(runtime_id or "")
        return bool(profile and kind in profile.qualified_assistance_kinds)


DEFAULT_EDGE_RUNTIME_INVENTORY = EdgeRuntimeInventory()
