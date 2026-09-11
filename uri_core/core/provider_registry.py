"""M22.5: Provider registry - ProviderDescriptor, ModelDescriptor, and the
static catalogue of known OpenAI-compatible providers.

Every numeric field is wrapped in ConfidenceValue so its reliability
(KNOWN | ESTIMATED | UNAVAILABLE) travels with the value and can never
be read as a bare, unlabelled number (architecture doc s6.3 / invariant #4
cross-reference).

ProviderConfigStore persists a user''s per-provider configuration
(enabled flag, base_url override, model override) to
user_scoped_path(user_id, "providers.json"). It NEVER contains key
material - keys live exclusively in provider_keys.py.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from uri_core.core.portable_paths import user_scoped_path

# Confidence labels - every numeric model field must carry one of these.
KNOWN = "KNOWN"
ESTIMATED = "ESTIMATED"
UNAVAILABLE = "UNAVAILABLE"

_VALID_CONFIDENCE = {KNOWN, ESTIMATED, UNAVAILABLE}


@dataclass(frozen=True)
class ConfidenceValue:
    """A numeric field with its reliability label.

    value is None when the field is genuinely unknown (confidence must
    then be UNAVAILABLE). A confidence of KNOWN means the value is
    provider-documented; ESTIMATED means derived from public benchmarks;
    UNAVAILABLE means no reliable source exists.
    """
    value: Optional[float]
    confidence: str  # KNOWN | ESTIMATED | UNAVAILABLE

    def __post_init__(self) -> None:
        if self.confidence not in _VALID_CONFIDENCE:
            raise ValueError(
                f"confidence must be one of {_VALID_CONFIDENCE!r}, "
                f"got {self.confidence!r}"
            )
        if self.confidence == UNAVAILABLE and self.value is not None:
            raise ValueError(
                "confidence UNAVAILABLE requires value=None"
            )


@dataclass(frozen=True)
class ModelDescriptor:
    """Metadata about a model offered by a provider.

    context_tokens is wrapped in ConfidenceValue so a consumer can
    tell the difference between a provider-documented 128k window and a
    rough community estimate.
    """
    model_id: str
    display_name: str
    context_tokens: ConfidenceValue
    pricing_per_1k_tokens: ConfidenceValue = field(
        default_factory=lambda: ConfidenceValue(value=None, confidence=UNAVAILABLE)
    )


@dataclass(frozen=True)
class ProviderDescriptor:
    """Metadata about a provider backend.

    adapter is the string key build_provider() already uses: "ollama" or
    "openai_compatible".  base_url is the provider''s canonical endpoint;
    a user may override it in ProviderConfigStore.
    """
    provider_id: str
    display_name: str
    adapter: str              # "ollama" | "openai_compatible"
    base_url: str             # canonical default; user-overridable
    models: List[ModelDescriptor] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Static catalogue - only what is provider-documented is marked KNOWN;
# everything else is ESTIMATED or UNAVAILABLE.  No invented numbers.
# ---------------------------------------------------------------------------

PROVIDER_CATALOGUE: List[ProviderDescriptor] = [
    ProviderDescriptor(
        provider_id="ollama",
        display_name="Ollama (local)",
        adapter="ollama",
        base_url="http://localhost:11434",
        models=[
            ModelDescriptor(
                model_id="qwen3:14b",
                display_name="Qwen3 14B",
                context_tokens=ConfidenceValue(value=40960, confidence=KNOWN),
            ),
            ModelDescriptor(
                model_id="gemma4:12b",
                display_name="Gemma 4 12B",
                context_tokens=ConfidenceValue(value=None, confidence=UNAVAILABLE),
            ),
        ],
    ),
    ProviderDescriptor(
        provider_id="openai",
        display_name="OpenAI",
        adapter="openai_compatible",
        base_url="https://api.openai.com/v1",
        models=[
            ModelDescriptor(
                model_id="gpt-4o",
                display_name="GPT-4o",
                context_tokens=ConfidenceValue(value=128000, confidence=KNOWN),
                pricing_per_1k_tokens=ConfidenceValue(value=0.0025, confidence=KNOWN),
            ),
            ModelDescriptor(
                model_id="gpt-4o-mini",
                display_name="GPT-4o mini",
                context_tokens=ConfidenceValue(value=128000, confidence=KNOWN),
                pricing_per_1k_tokens=ConfidenceValue(value=0.00015, confidence=KNOWN),
            ),
        ],
    ),
    ProviderDescriptor(
        provider_id="openrouter",
        display_name="OpenRouter",
        adapter="openai_compatible",
        base_url="https://openrouter.ai/api/v1",
        models=[
            ModelDescriptor(
                model_id="openai/gpt-4o",
                display_name="GPT-4o via OpenRouter",
                context_tokens=ConfidenceValue(value=128000, confidence=KNOWN),
                pricing_per_1k_tokens=ConfidenceValue(value=None, confidence=UNAVAILABLE),
            ),
        ],
    ),
    ProviderDescriptor(
        provider_id="groq",
        display_name="Groq",
        adapter="openai_compatible",
        base_url="https://api.groq.com/openai/v1",
        models=[
            ModelDescriptor(
                model_id="llama-3.3-70b-versatile",
                display_name="Llama 3.3 70B",
                context_tokens=ConfidenceValue(value=128000, confidence=KNOWN),
                pricing_per_1k_tokens=ConfidenceValue(value=0.00059, confidence=KNOWN),
            ),
        ],
    ),
    ProviderDescriptor(
        provider_id="lm_studio",
        display_name="LM Studio (local)",
        adapter="openai_compatible",
        base_url="http://localhost:1234/v1",
        models=[],  # dynamic - depends on what the user has loaded
    ),
]

# Lookup by provider_id for O(1) access.
CATALOGUE_BY_ID: Dict[str, ProviderDescriptor] = {
    p.provider_id: p for p in PROVIDER_CATALOGUE
}


# ---------------------------------------------------------------------------
# Per-user provider configuration (NOT key material)
# ---------------------------------------------------------------------------

_PROVIDERS_FILENAME = "providers.json"


class ProviderConfigStore:
    """Persists per-user provider configuration.

    Stores only: which providers the user has enabled, and any base_url
    or model override the user has set.  Never stores a key.

    File location: user_scoped_path(user_id, "providers.json")
    """

    def __init__(self, user_id: str) -> None:
        self._user_id = user_id
        self._path = user_scoped_path(user_id, _PROVIDERS_FILENAME)

    def load(self) -> Dict:
        """Returns the user''s provider config dict.  Empty dict if none
        has been saved yet (meaning: no per-user overrides - use catalogue
        defaults).  Never raises."""
        try:
            with open(self._path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                return data if isinstance(data, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def save(self, data: Dict) -> None:
        """Saves the user''s provider config dict atomically."""
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        tmp = self._path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp, self._path)

    def get_provider_config(self, provider_id: str) -> Dict:
        """Returns this user''s config for provider_id, or {} if none."""
        return self.load().get(provider_id, {})

    def set_provider_config(self, provider_id: str, config: Dict) -> None:
        """Merges config into the user''s stored config for provider_id."""
        store = self.load()
        existing = store.get(provider_id, {})
        existing.update(config)
        store[provider_id] = existing
        self.save(store)
