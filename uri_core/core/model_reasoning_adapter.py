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

from .model_providers import ModelProvider
from uri_core.config.model_roles import ROLE_REASONING, build_provider
from uri_core.core.model_router import get_router

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

query_context.conversation is a JSON list of this session's own recent
prior turns (oldest first), each a plain {"user": "...", "uri": "..."}
record of what was actually said - not a summary, not a judgment. A
short or ambiguous user_request (e.g. "yes", "guide me through it",
"sure", "the second one", "proceed") is almost always a direct reply
to the LAST entry in this list, not a new, standalone request - resolve
its pronouns, "it"/"that"/"this", and implied subject from that last
entry before deciding this request is unclear or asking for
clarification. Only treat a short reply as genuinely ambiguous when
query_context.conversation is empty or its last entry does not
plausibly explain what the short reply is responding to.

Before asking ANY clarifying question, check query_context.conversation's
last entry: if its "uri" text already asked the user something close to
the question you are about to ask again, the user's new "user_request"
IS their answer to it - use it as the missing information and move
forward (draft, act, or ask a genuinely DIFFERENT next question), never
repeat the same or a near-identical question verbatim. Asking the exact
same clarifying question two turns in a row is always wrong: it means
the user's last answer was ignored, not that it was insufficient.

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

clarification: {"question": "..."} or null - ONE single question to
    ask the user if their request is genuinely ambiguous or missing
    information. Omit or use null otherwise. "question" must ask for
    exactly ONE piece of missing information, never several bundled
    together - even when you can already see multiple fields are
    missing. Ask for the single most important one first; the rest can
    be asked in later turns, each framed by the user's previous answer.
    WRONG (never do this): "I will need the following details: date
    and time, venue, participating teams, and any specific
    instructions." RIGHT: "What date and time is this for?" - then,
    once the user answers, a later call asks the next single question
    ("Which venue?"), informed by what was just given.

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

    When the user asks you to find, check, or verify SPECIFIC
    information described as being inside a particular website,
    section, or document (e.g. "minutes of meeting", "office orders",
    "the notice about X" on a named site) and both web_search and
    fetch_url are available, a bare web_search step alone is NOT
    enough - a list of links is not the answer to "what does it say."
    Plan web_search first to find the specific page, THEN fetch_url on
    the most relevant result URL to actually read its content, so the
    final answer states the real facts found there with a direct link
    to that exact page - never just "you may need to check the site
    yourself."

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
already-produced result - check FIRST whether the new message is
actually still about that same goal (a rejection, a revision request,
"try again", "yes"/"no" to a question about it) before assuming it is.
A message that introduces a different topic, a new fact about the
user, or a new, unrelated task is NOT a continuation just because it
happens to arrive right after a result - treat it as a fresh, standalone
request and respond to what it actually says, never as if it were
answering "do you want to retry" or continuing the old goal by default.
Only stay on the old goal when the new message is genuinely, clearly
still about it.
"REPEATED_CLARIFICATION_MUST_ACT" means you have already asked a
clarifying question about this SAME goal three turns in a row without
ever proposing an action or workflow - even though each question was
worded differently, none of them moved this forward. Asking a fourth
clarifying question is not acceptable now: use every answer already
given across attempt_history to attempt the best available action or
workflow with the information you have, even if imperfect or partial.
Only if genuinely nothing in available_capabilities could act at all
may you return a clarification instead - and if so, it must be your
single, final, most concrete and specific possible question, never
another open-ended one."""

_RETENTION_REQUEST_ADDENDUM = """

This call has retention_request=true: the user already accepted a
result. Do not propose action/workflow. Decide only what is genuinely
worth remembering for a future, different request, and return:
retention_candidate: {"should_retain": true|false, "category":
"successful_approach"|"user_preference"|"reference_pattern"|"other",
"summary": "..."} or null; null/false is the normal, expected answer
for an ordinary success."""

# M20 (W5, research recovery): appended only when attempt_history is
# non-empty - i.e. only on a re-evaluation call, following the exact
# same "don't add prompt bulk the initial proposal call doesn't need"
# discipline as _INTERACTION_SIGNAL_ADDENDUM above. Tells the Brain
# that web_search/fetch_url exist for closing an information gap, not
# for accomplishing the goal itself, and that the runtime enforces a
# hard limit regardless of what is proposed here - the instruction
# below only asks for restraint the runtime does not depend on.
_RESEARCH_RECOVERY_ADDENDUM = """

If no registered capability in available_capabilities can satisfy
user_request, and web_search or fetch_url are present in that
catalogue, you may propose one of them to gather real information
relevant to the gap - e.g. to understand what the user is actually
asking about, or to find a public source that answers it directly.
Research never creates a capability and never substitutes for one URI
actually has: after research runs, its real result is added to
attempt_history for you to evaluate again, exactly like any other
action's result. Propose research at most once per request - if it
already appears in attempt_history, do not propose it again; either
evaluate its result as sufficient, propose a genuinely different
registered capability, or honestly report that nothing available can
satisfy this request."""


class OllamaReasoningAdapter:
    """Callable[[str], str] - the exact shape ModelReasoningGateway
    expects for model_callable.

    Usage:
        gateway = ModelReasoningGateway(
            model_callable=OllamaReasoningAdapter()
        )
        orchestrator = UriOrchestrator(model_reasoning_gateway=gateway)

    M22.6: per-call ModelRouter resolution replaces construction-time
    build_provider() caching. When an explicit provider is injected
    (test path), the router is bypassed entirely.
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
        freshly-constructed default. The __call__() path uses the router."""
        if self._explicit_provider is not None:
            return self._explicit_provider
        return build_provider(ROLE_REASONING)

    def __call__(self, request_json: str) -> str:

        system = REASONING_SYSTEM_PROMPT

        try:
            request = json.loads(request_json)
        except (TypeError, ValueError):
            request = {}

        # M21: system_policy (URI_AI_OPERATING_POLICY.md, ~9.5k characters)
        # is fully static within a session - the same file, reloaded
        # verbatim, on every one of the up to ~9 Brain calls one turn can
        # make (see orchestrator.py's _continue_brain_evaluation_loop). It
        # previously travelled inside the variable `user` JSON payload,
        # which changes shape every call - defeating Ollama's own prefix/
        # KV-cache reuse across those calls and making system_policy the
        # single largest slice of every reasoning prompt (measured at 58.8%
        # of payload size during the M21 audit). Moving it into `system`
        # instead - a stable prefix across calls to the same loaded model -
        # sends the Brain exactly the same information in a position the
        # runtime can actually reuse. The "system_policy" key stays present
        # in the transmitted JSON (the documented request contract is
        # unchanged) with its content emptied, since the content itself now
        # lives in `system`. A request with no (or an empty) system_policy
        # is transmitted completely unchanged - see
        # test_ollama_reasoning_adapter.py's narrow adapter-only test,
        # which never sets this key at all.
        user_json = request_json
        policy_text = (
            request.get("system_policy")
            if isinstance(request, dict)
            else None
        )

        if isinstance(policy_text, str) and policy_text.strip():
            system = policy_text + "\n\n" + system
            request_without_policy = dict(request)
            request_without_policy["system_policy"] = ""
            user_json = json.dumps(request_without_policy, ensure_ascii=False)

        if isinstance(request, dict):

            if request.get("interaction_signal"):
                system += _INTERACTION_SIGNAL_ADDENDUM

            if request.get("retention_request"):
                system += _RETENTION_REQUEST_ADDENDUM

            if request.get("attempt_history"):
                system += _RESEARCH_RECOVERY_ADDENDUM

        complete_kwargs = dict(
            system=system,
            user=user_json,
            temperature=0,
            max_tokens=800,
        )

        if self._explicit_provider is not None:
            # Legacy / test path: use injected provider directly.
            response = self._explicit_provider.complete(**complete_kwargs)
        else:
            # M22.6: per-call router resolution.
            response = get_router().attempt(
                ROLE_REASONING,
                self._principal,
                **complete_kwargs,
            )

        return response.content
