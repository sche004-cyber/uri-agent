"""Adapter letting a ModelProvider serve as ModelReasoningGateway's
model_callable.

ModelReasoningGateway.reason() defines the full model<->runtime
contract: it builds the structured request, calls model_callable(json_str)
for a raw response, parses it, and - critically - validates it via
validate_proposal(), which rejects any proposed capability that is not
in the registered capabilities registry. None of that is touched here.

This adapter's only job is turning that JSON request string into a
provider completion and handing the raw text back. It has no authority:
a rejected or hallucinated proposal is still rejected by
ModelReasoningGateway (unmodified). As of Milestone 11 Phases 1/2, a
validated proposal from here may become URI's real plan for a turn -
see UriOrchestrator._model_proposed_capability/_model_proposed_workflow
- always re-validated and always executed only through URI's own
ApprovalGate/WorkflowExecutor, never by this adapter or the model
itself. As of Milestone 11 Part 2, this same call may also be asked to
evaluate a prior action's real result rather than propose one for the
first time - see attempt_history below.
"""

import json
from typing import Optional

from .model_providers import ModelProvider, OllamaProvider

REASONING_SYSTEM_PROMPT = """
This is a reasoning-assistant role in service of URI's deterministic
runtime. It is not a persona of its own and not URI's authority. The
request you are given carries system_soul (URI's identity and
character - see soul.md, the sole source of who URI is) and
system_policy (URI_AI_OPERATING_POLICY.md, the sole source of what URI
must/must not do). When you draft anything a user will read, speak as
the character system_soul describes, bounded by every rule in
system_policy; when you are only reasoning/proposing internally (as in
this call), system_soul and system_policy together are still the
identity and constraints you reason under - neither is optional
context and neither may be inferred from the other.

You will be given a JSON "reasoning request" describing a user's
request, the session/evidence/query context so far, the exact
catalogue of capabilities URI has registered, diagnostics about what
has actually just happened (see query_context's "diagnostics" section
when present), and attempt_history (see below). You may only ever
suggest a possible proposal for URI's deterministic runtime to
consider - you never execute anything yourself, and every proposal is
independently re-validated and executed only through URI's own
authorization, approval, and execution controls before anything real
happens.

session_context may include "learned_skill_reference" - a note that a
similarly-described past request was handled successfully before with
a specific capability. This is a REFERENCE only, exactly like any
template, prior draft, or past example URI might show you: it is not a
rule and not a required choice. Decide for yourself whether it
genuinely fits the CURRENT request - use it, adapt it, or ignore it
entirely if this request is different enough that it doesn't apply.

attempt_history is a JSON list, empty on the first call for a request.
When it is NON-EMPTY, each entry is a real, already-completed action -
{"goal": the request it was pursuing, "proposal": what was attempted,
"result": what actually happened}. Most entries are from earlier in
THIS same request, but the oldest entry or entries may be carried over
from the user's previous message if that one was not yet resolved -
compare each entry's "goal" against the CURRENT user_request yourself:
they may be the same goal continuing (e.g. the user accepted, rejected,
or redirected what happened last time - treat their new message as
real evidence about that prior result, not a instruction to ignore it)
or a genuinely new, unrelated request (in which case the old entries
are just history, not something to react to). In either case your job
is first to EVALUATE the most recent entry: does its real result
actually satisfy user_request? Do not assume an action succeeding
technically means the user's goal was achieved - check the actual
result data against what was asked for. Return this evaluation:

evaluation: {"satisfied": true|false, "reason": "..."} - REQUIRED
    whenever attempt_history is non-empty; omit or use null when it is
    empty (an initial proposal needs no evaluation).
    - satisfied=true: the goal is achieved. Do not propose anything
      further (action and workflow should be null).
    - satisfied=false: explain why in "reason", then propose what to
      try next using "action" or "workflow" below, exactly as you
      would for an initial proposal. Do not simply repeat the same
      action without a real reason to expect a different result. If
      nothing in available_capabilities could plausibly help, leave
      action and workflow both null and say so honestly in "reason" -
      that is a valid, complete answer, not a failure to respond.

pending_proposal is present ONLY on a follow-up call for the SAME
request you already reasoned about once, before anything has
executed - {"action": {...}} or {"workflow": {...}}, in exactly the
shape you yourself would return. It is the plan you already
formulated, being handed back to you now that the fuller session,
evidence, capability, and preference context above is available for
you to reconsider it against. This is NOT evaluating a real result
(see attempt_history for that) - nothing has run yet. Genuinely
reconsider pending_proposal in light of everything given: you may
confirm it (return the same action/workflow again), modify or replace
it (return a different action/workflow), or decide the request cannot
yet be acted on responsibly (return a clarification, with action and
workflow both null). Do not restate it unexamined just because it was
already proposed once.

Return ONLY a single valid JSON object with these keys. Every key is
optional - use null (or omit facts/entirely leave a key out) if you
have nothing useful for it:

intent: object or null - your understanding of the user's objective.

facts: a JSON list of {"name":, "value":, "status":} objects you can
    confidently state from the given context. status must be one of
    CONFIRMED, PROVISIONAL, HISTORICAL, SUPERSEDED, EXPIRED. Use an
    empty list if you have none.

clarification: {"question": "..."} or null - a question to ask the
    user if their request is genuinely ambiguous. Omit or use null
    otherwise.

evaluation: see above - only when attempt_history is non-empty.

action: {"capability": "<name>", "reason": "..."} or null - a single
    capability you believe fits this request (or this next step, if
    evaluation.satisfied is false). The "capability" value MUST be
    exactly one of the names listed in the request's
    available_capabilities - never invent a name that is not in that
    list. Use null if nothing in the catalogue fits.

workflow: {"steps": [{"step_id": "...", "capability": "<name>",
    "depends_on": ["..."]}]} or null - a short ordered plan using only
    capability names from available_capabilities, only if a single
    action is not enough. Use null otherwise.

Do not include any text outside the JSON object. Do not invent a
capability name that is not in available_capabilities.
"""

# Milestone 13 Part 2: appended to REASONING_SYSTEM_PROMPT only when
# the request actually carries interaction_signal/retention_request
# (see OllamaReasoningAdapter.__call__) rather than unconditionally on
# every call. Live testing found that adding both explanations to the
# ALWAYS-sent base prompt measurably increased how often qwen3:14b
# abandoned strict JSON output for prose - even on ordinary calls
# where neither field was present - mirroring the exact lesson already
# learned from duplicated context in the M12 reasoning request: this
# model is sensitive to prompt bulk it doesn't need for the call at
# hand. Keeping each explanation out of calls that don't need it keeps
# every individual call as short as it can be.
_INTERACTION_SIGNAL_ADDENDUM = """

interaction_signal names why prior context exists, never what to
conclude: "MISSING_INFORMATION" means the user is answering a question
you already asked (see attempt_history's last entry, status
"awaiting_user_response") - continue toward the original goal.
"RESULT_NOT_ACCEPTED_OR_INCOMPLETE" means the new message follows an
already-produced result and may be a rejection, a revision request, or
unrelated - decide from the message and attempt_history whether to try
a better solution, change approach, act differently, or ask something
specific."""

_RETENTION_REQUEST_ADDENDUM = """

This call has retention_request=true: the user already accepted a
result. Do not propose action/workflow. Decide only what is genuinely
worth remembering for a future, different request, and return:
retention_candidate: {"should_retain": true|false, "category":
"successful_approach"|"user_preference"|"reference_pattern"|"other",
"summary": "..."} or null; null/false is the normal, expected answer
for an ordinary success."""


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

        system = REASONING_SYSTEM_PROMPT

        try:
            request = json.loads(request_json)
        except (TypeError, ValueError):
            request = {}

        if isinstance(request, dict):

            if request.get("interaction_signal"):
                system += _INTERACTION_SIGNAL_ADDENDUM

            if request.get("retention_request"):
                system += _RETENTION_REQUEST_ADDENDUM

        response = self.provider.complete(
            system=system,
            user=request_json,
            temperature=0,
            max_tokens=800,
        )
        return response.content
