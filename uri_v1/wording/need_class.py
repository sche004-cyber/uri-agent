"""Deterministic ClarificationWordingPolicy need class (Plan A R1.3 / R2.5).

The policy only computes the need class from the contract. It never decides
model eligibility; the unified router (`route_clarification_wording`) does.

[HYPOTHESIS, Plan A R1.3] The class boundary is computable from the contract:
- REASONING: the clarification has already run several rounds without
  resolving (R1.8 hand-off to explicit conversation / the Capable Brain).
- EXPLAIN: facts need explaining: attribute-first rounds, identical titles
  (same-name people, copies), versions/dates, contrast exclusions, display
  overflow, or two or more discriminating facts.
- SIMPLE: everything else (a template question plus grounded options).
S5 measures whether this boundary matches where model wording is rated better.
"""

from __future__ import annotations

from uri_v1.turn.rar_clarification_contract import ClarificationContract, ClarificationKind

NEED_CLASS_POLICY_VERSION = "m33.3-r.s5.need-class.v1"


class WordingNeedClass:
    """String values shared with `uri_core` routing_policy.WordingNeedClass
    (uri_v1 never imports uri_core; the router accepts these strings)."""
    SIMPLE = "SIMPLE"
    EXPLAIN = "EXPLAIN"
    REASONING = "REASONING"


REASONING_ROUND_THRESHOLD = 3
_EXPLAIN_KEYS = frozenset({"version", "modified", "sender", "thread_subject", "locator"})


def classify_need(contract: ClarificationContract) -> str:
    if contract.round_index >= REASONING_ROUND_THRESHOLD:
        return WordingNeedClass.REASONING
    if contract.kind == ClarificationKind.CHOOSE_ATTRIBUTE:
        return WordingNeedClass.EXPLAIN
    if contract.contrast_exclusions or contract.overflow_count:
        return WordingNeedClass.EXPLAIN
    candidates = contract.candidates
    titles = [next((f.value for f in c.display_facts if f.key == "title"), "").casefold() for c in candidates]
    if len(titles) > 1 and len(set(titles)) < len(titles):
        return WordingNeedClass.EXPLAIN
    keys = set(candidates[0].discriminating_keys) if candidates else set()
    if keys & _EXPLAIN_KEYS or len(keys - {"title"}) >= 2:
        return WordingNeedClass.EXPLAIN
    return WordingNeedClass.SIMPLE
