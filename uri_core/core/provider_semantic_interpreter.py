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
"""

import json
from typing import Optional

from .model_providers import ModelProvider
from uri_core.config.model_roles import ROLE_SEMANTIC_INTERPRETATION, build_provider

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
    def __init__(self, provider: Optional[ModelProvider] = None):
        self.provider = provider or build_provider(ROLE_SEMANTIC_INTERPRETATION)

    def interpret(self, user_text: str) -> dict:
        response = self.provider.complete(
            system=SYSTEM_PROMPT,
            user=user_text,
            temperature=0,
            max_tokens=500,
        )

        content = response.content.strip()

        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()

        result = json.loads(content)

        missing = [key for key in REQUIRED_KEYS if key not in result]

        if missing:
            raise ValueError(
                f"Semantic interpreter returned incomplete result. Missing: {missing}"
            )

        return result
