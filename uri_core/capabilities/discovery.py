"""Affordance-based progressive capability discovery.

This is ranking, not a hard-coded intent router.  It compares a request with
the registered descriptions and schemas, leaving final workflow reasoning to
the model and deterministic authority to the executor.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Set

from .registry import MultiActionCapabilityRegistry


_STOP_WORDS = {"a", "an", "and", "are", "do", "for", "have", "i", "in", "is", "it", "me", "my", "of", "on", "the", "that", "to", "with", "you", "your"}


def _terms(text: str) -> Set[str]:
    tokens = re.findall(r"[a-z0-9_]+", (text or "").lower())
    return {token[:-1] if token.endswith("s") and len(token) > 3 else token for token in tokens if token not in _STOP_WORDS}


class CapabilityDiscoveryEngine:
    def __init__(self, registry: MultiActionCapabilityRegistry):
        self.registry = registry

    def discover_capabilities(self, request: str, limit: int = 3) -> List[Dict[str, Any]]:
        query = _terms(request)
        candidates: List[Dict[str, Any]] = []
        for summary in self.registry.capability_summaries():
            affordance = _terms(" ".join([summary["name"], summary["description"], summary["category"], *summary["actions"]]))
            overlap = sorted(query & affordance)
            score = len(overlap) / max(1, len(query | affordance))
            if overlap:
                candidates.append({"capability": summary["name"], "score": score, "matched_affordances": overlap})
        return sorted(candidates, key=lambda item: (-item["score"], item["capability"]))[:limit]

    def discover_actions(self, capability_name: str, request: str, limit: int = 5) -> List[Dict[str, Any]]:
        capability = self.registry.get_capability(capability_name)
        if capability is None:
            return []
        query = _terms(request)
        results: List[Dict[str, Any]] = []
        for action in capability.list_actions():
            schema_terms = " ".join(action.parameters.parameters.keys())
            affordance = _terms(f"{action.name} {action.description} {schema_terms}")
            overlap = sorted(query & affordance)
            if overlap:
                results.append({"action": action.name, "score": len(overlap) / max(1, len(query | affordance)), "matched_affordances": overlap})
        return sorted(results, key=lambda item: (-item["score"], item["action"]))[:limit]

    def discover(self, request: str, limit: int = 3) -> Dict[str, Any]:
        capabilities = self.discover_capabilities(request, limit=limit)
        return {
            "capabilities": [
                {
                    **candidate,
                    "actions": self.discover_actions(candidate["capability"], request),
                }
                for candidate in capabilities
            ]
        }
