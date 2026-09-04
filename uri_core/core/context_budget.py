import json
import re
from typing import Any, Callable, Optional

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# ---------------------------------------------------------------------------
# Token / context-size estimation
# ---------------------------------------------------------------------------

def estimate_characters(text: str) -> int:
    """Deterministic character-count proxy for token usage."""
    return max(0, len(text))


def estimate_json_size(value: Any) -> int:
    """Serialized JSON character size of a model-context payload."""
    return len(json.dumps(value, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Context budget layer
# ---------------------------------------------------------------------------

class ContextBudget:
    """
    Deterministic context/token budget layer for model invocations.

    DISCOVER BROADLY, LOAD NARROWLY.

    The Skill Registry may contain many capabilities, but a model
    invocation receives only the small subset relevant to the current
    task.

    This component never executes capabilities and never authorizes
    side effects. The URI runtime remains authoritative.
    """

    # Categories that are not direct routable capabilities for model
    # selection. They remain in the registry for discovery and metadata,
    # but are not presented as selectable actions.
    EXCLUDED_FROM_CAPABILITY_SELECTION = {
        "model_provider",
        "model_infrastructure",
        "hermes_specialist",
        "specialized",
    }

    # Categories that represent model-facing capabilities the model may
    # reason about and propose.
    CAPABILITY_SELECTION_CATEGORY_WHITELIST = {
        "uri_core_capability",
        "on_demand_skill",
        "integration",
        "development",
        "skill_optimization",
    }

    def __init__(
        self,
        registry_items: Optional[list] = None,
        token_estimator: Optional[Callable[[str], int]] = None,
        max_capabilities: int = 20,
        max_tokens: int = 20000,
        context_purpose: str = "model_reasoning",
    ):
        if max_capabilities < 1:
            raise ValueError("max_capabilities must be >= 1")
        if max_tokens < 1:
            raise ValueError("max_tokens must be >= 1")

        self.registry_items = list(registry_items or [])
        self.token_estimator = token_estimator or estimate_characters
        self.max_capabilities = max_capabilities
        self.max_tokens = max_tokens
        self.context_purpose = context_purpose

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_context(
        self,
        request_text: str,
        intent: Optional[dict] = None,
        session_context: Optional[dict] = None,
        evidence_context: Optional[dict] = None,
    ) -> dict:
        """
        Build a compact model-context package containing only relevant
        capabilities.
        """
        signal_words = self._signal_words(
            request_text=request_text,
            intent=intent,
        )

        scored = self._score_items(signal_words)

        selected = self._select_by_priority(scored)

        selected = self._trim_to_capability_budget(selected)

        selected = self._trim_to_token_budget(selected)

        optimization_candidates = self._optimization_candidates()

        return {
            "capabilities": selected,
            "optimization_candidates": optimization_candidates,
            "token_estimate": self._estimate(selected),
            "budget_max_tokens": self.max_tokens,
            "budget_max_capabilities": self.max_capabilities,
            "selected_count": len(selected),
            "total_available": len(self.registry_items),
            "context_purpose": self.context_purpose,
            "signal_summary": {
                "request_text": request_text,
                "signal_word_count": len(signal_words),
            },
        }

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _signal_words(self, request_text: str, intent: Optional[dict]):
        parts = [str(request_text or "").lower()]
        if isinstance(intent, dict):
            for key in ("task_type", "domain", "requested_output"):
                value = intent.get(key)
                if isinstance(value, str) and value.strip():
                    parts.append(value.lower())
            entities = intent.get("entities")
            if isinstance(entities, list):
                for entity in entities:
                    if isinstance(entity, str) and entity.strip():
                        parts.append(entity.lower())
                    elif isinstance(entity, dict):
                        for v in entity.values():
                            if isinstance(v, str) and v.strip():
                                parts.append(v.lower())
        joined = " ".join(parts)
        return set(_TOKEN_RE.findall(joined))

    def _score_items(self, signal_words: set):
        scored = []
        for item in self.registry_items:
            category = item.get("category", "")
            if category not in self.CAPABILITY_SELECTION_CATEGORY_WHITELIST:
                continue

            name = str(item.get("name", "")).lower()
            purpose = str(item.get("purpose", "")).lower()
            item_text = f"{name} {purpose} {category}"
            item_tokens = set(_TOKEN_RE.findall(item_text))

            overlap = len(signal_words & item_tokens)

            # URI core capabilities and optimization skills are always
            # eligible, even with no keyword overlap.
            if (
                overlap == 0
                and category != "uri_core_capability"
                and category != "skill_optimization"
            ):
                continue

            score = overlap * 10

            if category == "uri_core_capability":
                score += 50
            elif category == "integration":
                score += 3
            elif category == "on_demand_skill":
                score += 2
            elif category == "development":
                score += 1
            elif category == "skill_optimization":
                score += 1

            if category == "skill_optimization" and self._optimization_condition_met(item):
                score += 25

            scored.append((score, item))

        scored.sort(key=lambda pair: (-pair[0], pair[1].get("name", "").lower()))
        return scored

    def _select_by_priority(self, scored):
        return [item for _score, item in scored[:self.max_capabilities]]

    def _trim_to_capability_budget(self, selected):
        if len(selected) <= self.max_capabilities:
            return selected
        return selected[:self.max_capabilities]

    def _trim_to_token_budget(self, selected):
        while selected and self._estimate(selected) > self.max_tokens:
            selected = selected[:-1]
        return selected

    def _estimate(self, items):
        snapshot = [_capability_snapshot(item) for item in items]
        payload = json.dumps(snapshot, ensure_ascii=False)
        return self.token_estimator(payload)

    # ------------------------------------------------------------------
    # Optimization candidates
    # ------------------------------------------------------------------

    def _optimization_candidates(self):
        if self.context_purpose != "model_reasoning":
            return []
        result = []
        for item in self.registry_items:
            if item.get("category") != "skill_optimization":
                continue
            if not self._optimization_condition_met(item):
                continue
            result.append(item)
        result.sort(key=lambda item: item.get("name", "").lower())
        return result

    def _optimization_condition_met(self, item):
        conditions = item.get("invocation_conditions", [])
        if not isinstance(conditions, list):
            return False
        if self.context_purpose == "model_reasoning":
            return "pre_reasoning" in conditions
        return False


# ---------------------------------------------------------------------------
# Snapshot helpers
# ---------------------------------------------------------------------------

_CAPABILITY_SNAPSHOT_FIELDS = frozenset({
    "name",
    "normalized_name",
    "category",
    "purpose",
    "input_requirements",
    "output_type",
    "token_saving_potential",
    "execution_risk",
    "model_facing",
    "runtime_facing",
    "invocation_conditions",
    "integration_status",
    "hermes_should_handle",
})


def _capability_snapshot(item: dict) -> dict:
    """Return a compact model-facing snapshot of a capability item."""
    return {key: item[key] for key in _CAPABILITY_SNAPSHOT_FIELDS if key in item}
