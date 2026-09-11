"""Semantic interpretation backed by a swappable ModelProvider.

Produces the exact same 8-key contract as the original, Groq-specific
SemanticInterpreter (uri_core/core/semantic_interpreter.py) - goal,
task_type, domain, entities, requested_output, requires_evidence,
requires_clarification, suggested_next_step - since CapabilityPlanner
and the rest of the deterministic pipeline depend on that shape
regardless of which model produced it.

SemanticInterpreter itself is left untouched (it has its own tests
tied to Groq's client shape); this is a separate, provider-driven
implementation of the same duck-typed interpret(user_text) -> dict
contract UriOrchestrator already relies on. Swapping models or
backends means constructing a different ModelProvider - nothing here,
or in the orchestrator, changes.

M22.6: per-call ModelRouter resolution replaces the construction-time
build_provider() cache. When an explicit provider is injected (test
path, unchanged), the router is bypassed entirely.
"""

import json
from typing import Optional

from .model_providers import ModelProvider
from uri_core.config.model_roles import ROLE_SEMANTIC_INTERPRETATION, build_provider
from uri_core.core.model_router import get_router, AllProvidersUnreachableError

SYSTEM_PROMPT = """
This is the semantic understanding layer used by URI's deterministic
runtime. It is a narrow classification role only - it does not speak
for URI's identity, purpose, or character (see
URI_AI_OPERATING_POLICY.md, the sole source of those).

Your job is to understand what the user actually wants.

Do NOT route based on individual keywords.
Do NOT invent tools.
Do NOT assume a workflow exists.

Return ONLY valid JSON with exactly these keys:

goal:
task_type:
domain:
entities:
requested_output:
requires_evidence:
requires_clarification:
suggested_next_step:

Rules:
- goal must describe the user's actual objective.
- task_type should describe the nature of the work.
- domain should identify the administrative domain where possible.
- entities must be a JSON list.
- requested_output should describe what the user expects URI to produce or accomplish.
- requires_evidence must be true or false.
- requires_clarification must be true or false.
- suggested_next_step must be the safest logical next step.
"""

REQUIRED_KEYS = [
    "goal",
    "task_type",
    "domain",
    "entities",
    "requested_output",
    "requires_evidence",
    "requires_clarification",
    "suggested_next_step",
]


class ProviderSemanticInterpreter:
    """Semantic interpreter backed by a ModelProvider or ModelRouter.

    If an explicit provider is given, it is used directly (test path —
    zero behaviour change for every test that already injects a fake
    provider). When no explicit provider is given, interpret() resolves
    a fresh provider via the process-wide ModelRouter on every call,
    satisfying M22.6's per-call resolution requirement (§0.1).

    The ``provider`` property is a backward-compatible inspection surface:
    it returns the injected provider when set, or constructs a fresh
    default provider via build_provider() for callers that inspect it
    (e.g. test_m21_provider_config.py). The actual interpret() call path
    always uses the router, not this property.
    """

    def __init__(
        self,
        provider: Optional[ModelProvider] = None,
        principal: Optional[object] = None,
    ) -> None:
        # Explicit provider bypasses the router entirely (existing test path).
        self._explicit_provider = provider
        self._principal = principal

    @property
    def provider(self) -> ModelProvider:
        """Backward-compatible accessor. Returns injected provider or a
        freshly-constructed default. The interpret() path uses the router."""
        if self._explicit_provider is not None:
            return self._explicit_provider
        return build_provider(ROLE_SEMANTIC_INTERPRETATION)

    def interpret(self, user_text: str) -> dict:
        if self._explicit_provider is not None:
            # Legacy / test path: use the injected provider directly.
            provider = self._explicit_provider
            return self._complete(provider, user_text)

        # M22.6: per-call router resolution.
        try:
            response = get_router().attempt(
                ROLE_SEMANTIC_INTERPRETATION,
                self._principal,
                system=SYSTEM_PROMPT,
                user=user_text,
                temperature=0,
                max_tokens=500,
            )
        except AllProvidersUnreachableError as exc:
            raise ValueError(
                f"Semantic interpreter unavailable: {exc}"
            ) from exc

        return self._parse(response.content)

    def _complete(self, provider: ModelProvider, user_text: str) -> dict:
        response = provider.complete(
            system=SYSTEM_PROMPT,
            user=user_text,
            temperature=0,
            max_tokens=500,
        )
        return self._parse(response.content)

    def _parse(self, content: str) -> dict:
        content = content.strip()

        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()

        result = json.loads(content)

        missing = [key for key in REQUIRED_KEYS if key not in result]

        if missing:
            raise ValueError(
                f"Semantic interpreter returned incomplete result. Missing: {missing}"
            )

        return result
