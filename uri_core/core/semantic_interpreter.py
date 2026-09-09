"""M22.1: superseded by ModelProvider/build_provider (see
model_providers/base.py, config/model_roles.py, and
provider_semantic_interpreter.py for the live semantic_interpretation
role) - this pre-M21 direct Groq client is no longer part of any live
call path. Its only other importer was the dead
orchestrator.before_compatibility_fix.py, removed in M22.1; see
test_shadow_provider_unreachable.py for the enforced proof.

Retained only for test_semantic_interpreter.py's regression coverage on
environment-only credential handling (never hardcoded, never silently
substituted when absent) - see URI_M22_ARCHITECTURE.md section 18. This
module is scheduled for deletion once M22.5 (provider registry) ports
that same guarantee onto the real per-user API-key store; do not import
it from any new code."""

import json
import os
from typing import Any, Optional

from groq import Groq


class SemanticInterpreter:
    def __init__(self, client: Optional[Any] = None):
        self.client = client
        self.model_name = "qwen/qwen3.8-27b"

    def interpret(self, user_text: str) -> dict:
        if self.client is None:
            self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

        system_prompt = """
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

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_text
                }
            ],
            temperature=0,
            max_completion_tokens=500
        )

        content = response.choices[0].message.content.strip()

        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()

        result = json.loads(content)

        required_keys = [
            "goal",
            "task_type",
            "domain",
            "entities",
            "requested_output",
            "requires_evidence",
            "requires_clarification",
            "suggested_next_step"
        ]

        missing = [key for key in required_keys if key not in result]

        if missing:
            raise ValueError(
                f"Semantic interpreter returned incomplete result. Missing: {missing}"
            )

        return result
