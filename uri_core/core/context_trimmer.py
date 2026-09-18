"""Deterministic context budgeting and trimming for URI model requests.

Enforces model context window limits with strict section protection:
- Non-negotiable protected sections (system policy, soul/identity,
  user request, contract scaffolding, core instructions, capability names)
  are NEVER silently dropped or truncated.
- Budgetable sections (evidence_context, attempt_history, session_context,
  query_context.conversation, experience, attachments) are trimmed in
  fixed priority order using existing deterministic bounding utilities
  (fit_within_budget, bound_json_value).
- Output headroom (max_tokens / num_predict) is strictly reserved.
- Small-window failure shape: if irreducible protected sections alone exceed
  the model context window, ContextWindowExceededError is raised honestly
  rather than silently sending a prompt that will be degraded by the provider.
"""

import copy
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from uri_core.core.context_budget import bound_json_value, estimate_tokens, fit_within_budget
from uri_core.core.model_providers.base import ContextWindowExceededError

_LOG = logging.getLogger(__name__)

# Estimated token overhead for the base system prompt instructions and scaffolding
DEFAULT_SYSTEM_INSTRUCTIONS_TOKENS = 1000
DEFAULT_OUTPUT_HEADROOM_TOKENS = 800


def estimate_request_tokens(
    request: Dict[str, Any],
    extra_system_tokens: int = DEFAULT_SYSTEM_INSTRUCTIONS_TOKENS,
) -> int:
    """Estimates the total token count of a reasoning request as it will be
    transmitted to the model provider (system prompt + user JSON payload).

    Accounts for system_policy being extracted to the system prompt in the
    reasoning adapter, preventing double-counting.
    """
    policy = request.get("system_policy", "")
    policy_tokens = estimate_tokens(str(policy)) if policy else 0
    system_tokens = policy_tokens + extra_system_tokens

    # User payload has system_policy emptied when transmitted
    req_user_payload = dict(request)
    if "system_policy" in req_user_payload:
        req_user_payload["system_policy"] = ""

    try:
        user_json = json.dumps(req_user_payload, ensure_ascii=False, default=str)
    except Exception:
        user_json = str(req_user_payload)

    user_tokens = estimate_tokens(user_json)
    return system_tokens + user_tokens


def _cap_capabilities(capabilities: List[Dict[str, Any]], max_desc_len: int = 160) -> List[Dict[str, Any]]:
    """A2.4: Binds capability entries so verbose descriptions or gap reasons
    do not inflate prompt size, while keeping names and usability metadata intact.
    """
    capped: List[Dict[str, Any]] = []
    for entry in capabilities:
        if not isinstance(entry, dict):
            continue
        capped_entry = dict(entry)
        desc = capped_entry.get("description", "")
        if isinstance(desc, str) and len(desc) > max_desc_len:
            capped_entry["description"] = desc[:max_desc_len].rstrip() + "..."
        gap = capped_entry.get("gap_reason")
        if isinstance(gap, str) and len(gap) > 100:
            capped_entry["gap_reason"] = gap[:100].rstrip() + "..."
        blocked = capped_entry.get("blocked_by")
        if isinstance(blocked, list) and len(blocked) > 3:
            capped_entry["blocked_by"] = blocked[:3]
        capped.append(capped_entry)
    return capped


def trim_reasoning_request(
    request: Dict[str, Any],
    context_tokens: int,
    max_tokens_headroom: int = DEFAULT_OUTPUT_HEADROOM_TOKENS,
    model_name: str = "",
) -> Dict[str, Any]:
    """Fits `request` within `context_tokens` with `max_tokens_headroom` output buffer.

    Strict priority order for trimming:
      1. evidence_context (bound and fit)
      2. attempt_history (bound results, keep most recent first)
      3. session_context (bound execution_history and large facts)
      4. query_context.conversation (keep newest turns first, trim older)
      5. query_context.experience & attachments (trim to budget)
      6. available_capabilities (cap description lengths)

    PROTECTED SECTIONS (NEVER TRIMMED):
      - system_policy
      - user_request
      - instruction
      - contract_version
      - pending_proposal
      - query_context.identity
      - query_context.soul

    If after trimming all budgetable sections the protected sections alone still
    exceed the allowable budget, raises ContextWindowExceededError.
    """
    allowed_prompt_tokens = max(0, context_tokens - max_tokens_headroom)
    current_tokens = estimate_request_tokens(request)

    if current_tokens <= allowed_prompt_tokens:
        return request

    _LOG.info(
        "Trimming reasoning request: estimated ~%d tokens exceeds allowed ~%d "
        "(context_tokens=%d, headroom=%d). Applying staged reduction.",
        current_tokens,
        allowed_prompt_tokens,
        context_tokens,
        max_tokens_headroom,
    )

    trimmed = copy.deepcopy(request)

    # -------------------------------------------------------------------------
    # Stage 1: Trim evidence_context
    # -------------------------------------------------------------------------
    evidence = trimmed.get("evidence_context")
    if isinstance(evidence, dict) and evidence:
        bounded_evidence = {}
        for k, v in evidence.items():
            bounded_evidence[k] = bound_json_value(v, max_chars=400)
        trimmed["evidence_context"] = bounded_evidence

        if estimate_request_tokens(trimmed) <= allowed_prompt_tokens:
            return trimmed

        # If still over budget, aggressively prune evidence items if very large
        if estimate_request_tokens(trimmed) > allowed_prompt_tokens:
            trimmed["evidence_context"] = {
                k: bound_json_value(v, max_chars=150)
                for k, v in list(bounded_evidence.items())[:5]
            }
            if estimate_request_tokens(trimmed) <= allowed_prompt_tokens:
                return trimmed

    # -------------------------------------------------------------------------
    # Stage 2: Trim attempt_history (keep most recent first)
    # -------------------------------------------------------------------------
    history = trimmed.get("attempt_history")
    if isinstance(history, list) and history:
        # Bound individual results first
        bounded_history = []
        for entry in history:
            if isinstance(entry, dict):
                item = dict(entry)
                if "result" in item:
                    item["result"] = bound_json_value(item["result"], max_chars=300)
                bounded_history.append(item)
            else:
                bounded_history.append(entry)

        # Most recent attempts are at the end; reverse, fit, reverse
        reversed_history = list(reversed(bounded_history))
        remaining_budget = max(200, allowed_prompt_tokens // 4)
        fitted_reversed = fit_within_budget(reversed_history, max_tokens=remaining_budget)
        trimmed["attempt_history"] = list(reversed(fitted_reversed))

        if estimate_request_tokens(trimmed) <= allowed_prompt_tokens:
            return trimmed

    # -------------------------------------------------------------------------
    # Stage 3: Trim session_context
    # -------------------------------------------------------------------------
    session = trimmed.get("session_context")
    if isinstance(session, dict) and session:
        bounded_session = dict(session)
        # Check active_workflow.execution_history
        wf = bounded_session.get("active_workflow")
        if isinstance(wf, dict):
            wf_copy = dict(wf)
            exec_hist = wf_copy.get("execution_history")
            if isinstance(exec_hist, list) and exec_hist:
                # Keep newest, bound
                bounded_exec = [bound_json_value(x, max_chars=200) for x in exec_hist]
                wf_copy["execution_history"] = bounded_exec[-5:]
            bounded_session["active_workflow"] = wf_copy

        # Bound large fact blobs in session
        for key in ("current_facts", "evidence_facts", "facts"):
            if key in bounded_session and isinstance(bounded_session[key], dict):
                bounded_session[key] = {
                    fk: bound_json_value(fv, max_chars=200)
                    for fk, fv in bounded_session[key].items()
                }

        trimmed["session_context"] = bounded_session
        if estimate_request_tokens(trimmed) <= allowed_prompt_tokens:
            return trimmed

    # -------------------------------------------------------------------------
    # Stage 4: Trim query_context.conversation
    # -------------------------------------------------------------------------
    qc = trimmed.get("query_context")
    if isinstance(qc, dict):
        qc_copy = dict(qc)
        conversation = qc_copy.get("conversation")
        if isinstance(conversation, list) and conversation:
            # Keep newest conversation turns (end of list)
            rev_conv = list(reversed(conversation))
            remaining_for_conv = max(100, allowed_prompt_tokens // 5)
            fitted_rev = fit_within_budget(rev_conv, max_tokens=remaining_for_conv)
            qc_copy["conversation"] = list(reversed(fitted_rev))

        # Stage 5: Trim experience and attachments in query_context
        for k in ("experience", "attachments"):
            val = qc_copy.get(k)
            if isinstance(val, list) and val:
                qc_copy[k] = fit_within_budget(val, max_tokens=150)

        trimmed["query_context"] = qc_copy
        if estimate_request_tokens(trimmed) <= allowed_prompt_tokens:
            return trimmed

    # -------------------------------------------------------------------------
    # Stage 6: Cap available_capabilities (A2.4)
    # -------------------------------------------------------------------------
    caps = trimmed.get("available_capabilities")
    if isinstance(caps, list) and caps:
        trimmed["available_capabilities"] = _cap_capabilities(caps, max_desc_len=120)
        if estimate_request_tokens(trimmed) <= allowed_prompt_tokens:
            return trimmed

    # -------------------------------------------------------------------------
    # Stage 7: Check if trimmed request fits. If not, small-window failure shape
    # -------------------------------------------------------------------------
    final_tokens = estimate_request_tokens(trimmed)
    if final_tokens > allowed_prompt_tokens:
        msg = (
            f"Prompt estimated at ~{final_tokens} tokens with {max_tokens_headroom} token output "
            f"headroom ({final_tokens + max_tokens_headroom} total) exceeds configured context window "
            f"({context_tokens} tokens) for model '{model_name}'. "
            "Non-negotiable system policy, identity, and core instructions cannot be safely accommodated."
        )
        _LOG.error(msg)
        raise ContextWindowExceededError(
            msg,
            model=model_name,
            prompt_tokens=final_tokens,
            max_tokens=max_tokens_headroom,
            context_tokens=context_tokens,
        )

    return trimmed
