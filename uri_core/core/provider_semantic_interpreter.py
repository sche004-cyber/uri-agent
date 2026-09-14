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

Personal disclosure (2026-09-12): when the user is telling URI a fact
ABOUT THEMSELVES in first person (their workplace, name, preference,
contact detail, or similar) - e.g. "I work at X", "my favorite format
is docx", "call me Y" - this is NOT a request for information about
whatever they mentioned. Even if the disclosure names a place,
organization, or other entity, do not classify it as an information-
retrieval/search request about that entity. Instead:
- task_type must be "personal information disclosure".
- goal must state that the user is sharing a fact about themselves,
  preserving the actual fact (e.g. "the user's workplace is X").
- requested_output must be "save this fact about the user to memory".
- requires_clarification must be false (the disclosure is already
  complete information, not a question needing an answer).
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

# 2026-09-12: the SYSTEM_PROMPT's own "personal disclosure" instruction
# (above) asks the model to classify a first-person self-disclosure
# distinctly, but a small local model does not reliably follow it -
# live-verified: "I work at NIT Sikkim" kept coming back classified as
# an information-retrieval request about NIT Sikkim regardless of the
# added prompt guidance. This deterministic raw-text check is the
# authoritative fallback: URI's own runtime, not the model's prompt
# compliance, decides this classification. Mirrors capability_planner's
# existing keyword-based routing convention - not a change to how the
# Brain itself reasons, only to what URI's semantic layer reports.
import re as _re

_DISCLOSURE_PATTERNS = [
    _re.compile(pattern, _re.IGNORECASE)
    for pattern in (
        r"\bi work (at|for) (?P<fact>.+)",
        r"\bi study (at|in) (?P<fact>.+)",
        r"\bi live (in|at) (?P<fact>.+)",
        r"\bi(?:'m| am) from (?P<fact>.+)",
        r"\bmy (workplace|job|role) is (?P<fact>.+)",
        r"\bmy name is (?P<fact>.+)",
        r"\bcall me (?P<fact>.+)",
        r"\bmy (favorite|favourite) (?P<fact>.+)",
        r"\bi prefer (?P<fact>.+)",
        r"\bmy email is (?P<fact>.+)",
        r"\bmy phone(?: number)? is (?P<fact>.+)",
    )
]


def _detect_personal_disclosure(user_text: str) -> bool:
    return any(pattern.search(user_text or "") for pattern in _DISCLOSURE_PATTERNS)


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

        return self._parse(response.content, user_text)

    def _complete(self, provider: ModelProvider, user_text: str) -> dict:
        response = provider.complete(
            system=SYSTEM_PROMPT,
            user=user_text,
            temperature=0,
            max_tokens=500,
        )
        return self._parse(response.content, user_text)

    def _parse(self, content: str, user_text: str = "") -> dict:
        content = content.strip()

        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()

        result = json.loads(content)

        missing = [key for key in REQUIRED_KEYS if key not in result]

        if missing:
            raise ValueError(
                f"Semantic interpreter returned incomplete result. Missing: {missing}"
            )

        if _detect_personal_disclosure(user_text):
            result["task_type"] = "personal information disclosure"
            result["goal"] = f"the user is sharing a fact about themselves: {user_text}"
            result["requested_output"] = "save this fact about the user to memory"
            result["requires_clarification"] = False

        return result
