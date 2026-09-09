"""Configurable per-role model/provider selection seam (M21).

The M21 audit found that every real model call site in this codebase
independently hardcoded `provider or OllamaProvider()` - four separate
places (provider_semantic_interpreter.py, model_reasoning_adapter.py,
response_drafting.py, document_composer.py) that would each need
editing to point URI at a different model or backend, with no single
place a deployment could configure that from. `ModelProvider` itself
(model_providers/base.py) has always been a clean, provider-agnostic
ABC; what was missing was config and a factory, not an abstraction.

This module supplies exactly that seam - nothing more:

    - a named ROLE per real call site, so each can be configured
      independently (the semantic-interpretation classifier, the
      reasoning/planning call, the drafting/narrative call, and
      document composition have genuinely different needs - see the
      M21 audit's finding that all four shared one model despite
      radically different prompt sizes and purposes);
    - `build_provider(role)`, the one function every call site now
      uses instead of constructing OllamaProvider() directly;
    - `DEFAULT_MODEL_ROLES` / `load_model_roles()`, following the exact
      "packaged defaults, deep-merged with an optional deployment JSON
      override" pattern uri_core/config/institutional_rules.py already
      established - not a new pattern.

Deliberately NOT here, by design (M21 scope):

    - No second ModelProvider implementation ships in this module.
      Every role defaults to "ollama", the only provider this codebase
      implements. Configuring a role's "provider" to anything else
      raises a clear ValueError at construction time rather than
      silently falling back - the same "never silently substitute"
      discipline web_search.py already applies to a missing API key.
      Adding a real second provider (e.g. an API-backed one) is
      explicitly deferred to a future milestone once this seam is
      proven; see the M21 audit's recommendation not to ship an
      unneeded second provider prematurely.
    - No change to what governs execution, approval, or authority.
      Which provider answers a role's prompt is purely which text
      generator URI calls - it never gains, weakens, or bypasses the
      ApprovalGate/ToolDispatcher boundary; only a validated capability-
      name string ever crosses that boundary regardless of which model
      proposed it (unchanged, see capability_authority_boundary tests).
"""

import json
import os
from typing import Any, Dict, Optional

from uri_core.core.model_providers import ModelProvider, OllamaProvider
from uri_core.core.model_providers.base import ModelProviderConfig

# One role per real model-call site in this codebase today.
ROLE_SEMANTIC_INTERPRETATION = "semantic_interpretation"
ROLE_REASONING = "reasoning"
ROLE_DRAFTING = "drafting"
ROLE_DOCUMENT_COMPOSITION = "document_composition"

ROLES = (
    ROLE_SEMANTIC_INTERPRETATION,
    ROLE_REASONING,
    ROLE_DRAFTING,
    ROLE_DOCUMENT_COMPOSITION,
)

# Every role defaults to "ollama" with no per-role override - i.e.
# every call site keeps behaving exactly as it did before this module
# existed (reading OLLAMA_BASE_URL/OLLAMA_MODEL/OLLAMA_TIMEOUT_SECONDS/
# OLLAMA_NUM_CTX from the environment via ModelProviderConfig.from_env())
# unless a deployment JSON override says otherwise for a specific role.
DEFAULT_MODEL_ROLES: Dict[str, Dict[str, Any]] = {
    role: {"provider": "ollama"} for role in ROLES
}

# A deployment override, if present, is read from here - absent by
# default, mirroring institutional_rules.py's INSTITUTIONAL_RULES_PATH
# exactly. Each key is a role name; each value may set "provider" and/
# or any of "base_url"/"model"/"timeout_seconds"/"context_tokens" to
# override that one role without touching any other.
MODEL_ROLES_PATH = os.path.join("uri_workspace", "model_roles.json")


class UnknownModelProviderError(ValueError):
    """Raised when a role is configured for a provider this codebase
    does not implement - a clear, immediate configuration error rather
    than a silent fallback to Ollama."""


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Override wins per key; nested dicts merge rather than replace -
    the same helper institutional_rules.py already defines, duplicated
    here (not imported) so this module has no dependency on drafting
    config, matching how model_providers/base.py and
    institutional_rules.py already have no dependency on each other."""

    merged = dict(base)
    for key, value in override.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_model_roles(path: str = MODEL_ROLES_PATH) -> Dict[str, Dict[str, Any]]:
    """The active per-role provider configuration: the packaged
    all-Ollama defaults, deep-merged with a deployment override JSON if
    one exists at [path]. Never raises - a missing or malformed
    override degrades to the defaults, mirroring
    institutional_rules.load_institutional_rules()'s exact discipline."""

    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            override = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {role: dict(config) for role, config in DEFAULT_MODEL_ROLES.items()}

    if not isinstance(override, dict):
        return {role: dict(config) for role, config in DEFAULT_MODEL_ROLES.items()}

    return _deep_merge(DEFAULT_MODEL_ROLES, override)


def build_provider(
    role: str,
    roles_path: str = MODEL_ROLES_PATH,
) -> ModelProvider:
    """The one factory every real model-call site uses instead of
    constructing OllamaProvider() directly. `role` should be one of the
    ROLE_* constants above, but an unrecognized role is treated exactly
    like one with no override (full Ollama-from-env defaults) rather
    than raising - a role name is a configuration-organizing label,
    never itself a source of authority, and this module choosing to be
    resilient to an unlisted role never bypasses the real, closed set
    of provider IMPLEMENTATIONS enforced below.

    Local remains the default and requires zero configuration: with no
    uri_workspace/model_roles.json present, every role resolves to
    OllamaProvider built from the same OLLAMA_* environment variables
    ModelProviderConfig.from_env() has always read."""

    role_config = load_model_roles(roles_path).get(role, {})
    provider_name = role_config.get("provider", "ollama")

    env_config = ModelProviderConfig.from_env()
    config = ModelProviderConfig(
        base_url=role_config.get("base_url", env_config.base_url),
        model=role_config.get("model", env_config.model),
        timeout_seconds=role_config.get(
            "timeout_seconds", env_config.timeout_seconds
        ),
        context_tokens=role_config.get(
            "context_tokens", env_config.context_tokens
        ),
    )

    if provider_name == "ollama":
        return OllamaProvider(config=config)

    raise UnknownModelProviderError(
        f"Role '{role}' is configured for provider '{provider_name}', but "
        "this codebase only implements 'ollama'. Add a new ModelProvider "
        "subclass (see model_providers/base.py) and wire it into "
        "build_provider() before configuring a role to use it."
    )
