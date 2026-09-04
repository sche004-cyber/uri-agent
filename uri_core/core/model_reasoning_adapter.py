"""Adapter letting a ModelProvider serve as ModelReasoningGateway's
model_callable.

ModelReasoningGateway.reason() already defines the full shadow-reasoning
contract: it builds the structured request, calls model_callable(json_str)
for a raw response, parses it, and - critically - validates it via
validate_proposal(), which rejects any proposed capability that is not
in the registered capabilities registry. None of that is touched here.

This adapter's only job is turning that JSON request string into a
provider completion and handing the raw text back. It has no authority:
a rejected or hallucinated proposal is still rejected by
ModelReasoningGateway (unmodified), and the shadow result is never
executed - see UriOrchestrator._run_model_reasoning_shadow, also
unmodified, which only ever attaches this as observational data.
"""

import json
from typing import Optional

from .model_providers import ModelProvider, OllamaProvider

REASONING_SYSTEM_PROMPT = """
You are URI's reasoning assistant. You are NOT URI's authority.

You will be given a JSON "reasoning request" describing a user's
request, the session/evidence context so far, and the exact catalogue
of capabilities URI has registered. You may only ever suggest a
possible proposal for URI's deterministic runtime to consider - you
never execute anything, and nothing you say is trusted or acted on
directly. Your suggestion is reviewed only as a shadow comparison
against what the deterministic runtime actually decides.

Return ONLY a single valid JSON object with these keys. Every key is
optional - use null (or omit facts/entirely leave a key out) if you
have nothing useful to propose for it:

intent: object or null - your understanding of the user's objective.

facts: a JSON list of {"name":, "value":, "status":} objects you can
    confidently state from the given context. status must be one of
    CONFIRMED, PROVISIONAL, HISTORICAL, SUPERSEDED, EXPIRED. Use an
    empty list if you have none.

clarification: {"question": "..."} or null - a question to ask the
    user if their request is genuinely ambiguous. Omit or use null
    otherwise.

action: {"capability": "<name>", "reason": "..."} or null - a single
    capability you believe fits this request. The "capability" value
    MUST be exactly one of the names listed in the request's
    available_capabilities - never invent a name that is not in that
    list. Use null if nothing in the catalogue fits.

workflow: {"steps": [{"step_id": "...", "capability": "<name>",
    "depends_on": ["..."]}]} or null - a short ordered plan using only
    capability names from available_capabilities, only if a single
    action is not enough. Use null otherwise.

Do not include any text outside the JSON object. Do not invent a
capability name that is not in available_capabilities.
"""


class OllamaReasoningAdapter:
    """Callable[[str], str] - the exact shape ModelReasoningGateway
    expects for model_callable.

    Usage:
        gateway = ModelReasoningGateway(
            model_callable=OllamaReasoningAdapter()
        )
        orchestrator = UriOrchestrator(model_reasoning_gateway=gateway)
    """

    def __init__(self, provider: Optional[ModelProvider] = None):
        self.provider = provider or OllamaProvider()

    def __call__(self, request_json: str) -> str:
        response = self.provider.complete(
            system=REASONING_SYSTEM_PROMPT,
            user=request_json,
            temperature=0,
            max_tokens=800,
        )
        return response.content
