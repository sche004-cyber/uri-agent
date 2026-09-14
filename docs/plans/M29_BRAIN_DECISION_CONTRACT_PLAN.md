# M29: Structured Brain Decision Contract

## Status: ACCEPTED (auto-approved per ORCHESTRATION.md §1.5, 2026-09-12) — PLAN ONLY, NOT IMPLEMENTED

## 1. Root architectural diagnosis

Investigated: `model_reasoning_adapter.py`, `model_reasoning_gateway.py`,
`capability_planner.py`, `capability_feasibility.py`, `connection_status.py`,
`multi_action_dispatch.py` (M27), `capabilities/registry.py`,
`orchestrator.py`'s decision-priority region (the block just fixed).

**Corrected from the earlier live-verification report**: connection state is
NOT universally missing from the Brain's context. `ModelReasoningGateway`
already sends `available_capabilities` built from
`CapabilityFeasibility.snapshot()`, which merges `CapabilityRegistry` with
real `connection_status.list_connection_status()` state — each legacy
capability already arrives with `usable`/`gap_reason`/`blocked_by`
(e.g. `gmail_search: usable=false, gap_reason="not_connected"`). This is a
real M20 mechanism that works today for every *legacy* capability, and
`orchestrator._executable_capability_ids()` already deterministically
rejects a Brain proposal naming a currently-unusable one.

The gap is narrower and more specific than originally reported:

1. **The M27 multi-action registry does not carry this same feasibility
   signal at the discovery stage.** `MultiActionDispatch.model_context()`
   sends `capability_summaries()` (name/description/category/actions only —
   see `registry.py`). `check_availability()`/connection state is only
   attached by `describe_capability()`, which fires *after* a capability is
   already selected. The Brain currently has no way to know, before
   selecting, whether Gmail is actually connected via this path.
2. **`REASONING_SYSTEM_PROMPT` (model_reasoning_adapter.py) never documents
   the `multi_action`/`selected_capability`/`proposal` output shape
   `MultiActionDispatch._proposal()` looks for at all.** The Brain is never
   told this response shape exists or how to use it. In practice this means
   M27's dispatch path is close to unreachable via ordinary model output —
   confirmed by today's live traces, where the Gmail fix actually landed
   through the *legacy* `gmail_search`/`capability_planner` path, never
   through `MultiActionDispatch`.
3. **No deterministic "this is permanently unsupported" signal exists.**
   `capability_planner_plan`'s `planning_required` + `known_gaps` already
   distinguish "not_implemented" from "unavailable_runtime" internally
   (`capability_planner.py`'s existing gap-awareness tests), but this
   distinction never reaches the Brain's decision or the final response
   shape as a first-class `unsupported` field — so a request with no
   backing capability at all (e.g. "schedule a recurring job search") is
   indistinguishable, in the response contract, from one that's merely
   missing a parameter. Both currently produce `waiting_for_input`.
4. **The reasoning contract is response/action-shaped, not decision-shaped.**
   `REASONING_SYSTEM_PROMPT`'s JSON keys (`intent`, `facts`, `clarification`,
   `evaluation`, `action`, `workflow`, `retention_candidate`) ask the Brain
   to produce artifacts, never to first classify *which of six situations
   this is*. `orchestrator.py`'s own branching (model_capability_proposal /
   model_workflow_proposal_present / learned_skill / capability_planner_plan
   / multi_action_result / initial_clarification, all interleaved across
   ~300 lines) is *inferring* the situation after the fact from whichever
   keys happen to be non-null — which is exactly how a redundant
   clarification could silently outrank an already-resolved disclosure
   (the defect just fixed) and how M27's multi-action path stays dark.

## 2. Proposed structured decision schema

```json
{
  "goal": "the user's actual objective, plain text",
  "mode": "conversation | single_action | multi_action | clarification | approval_required | unsupported",
  "capability": "registered capability id, or null",
  "actions": ["action name(s) for a multi-action capability, or [] "],
  "needs_clarification": false,
  "clarification_reason": null,
  "unsupported": false,
  "unsupported_reason": null,
  "requires_approval": false,
  "reason": "short justification for this decision"
}
```

`mode` is the single field orchestrator branches on — it replaces today's
"infer the situation from which keys are non-null" pattern with one
explicit classification. `needs_clarification`/`unsupported`/
`requires_approval` are kept as separate booleans (not folded entirely into
`mode`) because `capability` and `actions` can be non-null *alongside*
`requires_approval` (an identified, executable, but approval-gated action)
— `mode` names the overall routing outcome, the booleans carry the detail
that outcome needs.

Validation, entirely deterministic, never trusting the model's claim:
- `capability` must be in the union of `CapabilityFeasibility.usable_ids()`
  (legacy) and the multi-action registry's registered names — exactly the
  existing "never trust a proposed name" discipline
  (`ModelReasoningGateway.validate_proposal()`,
  `orchestrator._executable_capability_ids()`), extended to cover both
  registries instead of only the legacy one.
- `mode == "unsupported"` is only ever *accepted* as unsupported after a
  deterministic re-check: this module must confirm no capability in either
  registry's summaries plausibly matches the stated goal before honoring
  the model's own claim of "unsupported" (mirrors why
  `is_conversational_no_capability_required` requires two independent
  signals, not one — a single free-form model field should never be the
  sole authority for a boundary this consequential).
- `mode == "clarification"` when a `capability` is already confidently
  identified is rejected back to `single_action`/`multi_action` unless
  `clarification_reason` names a specific missing parameter — this is the
  generalized, schema-level form of the bounded fix just shipped (no more
  ad hoc `requires_clarification is False` boolean-matching; the contract
  itself now makes "I already know enough" explicit and required to say
  why not, when the model still wants to ask).

## 3. Module boundaries

- **`model_reasoning_adapter.py`** — role clarified, not removed: stays the
  transport layer only (ModelProvider → raw completion text, system-prompt
  assembly for interaction_signal/retention/research addenda). Its
  `REASONING_SYSTEM_PROMPT` is **superseded** by the new decision-contract
  prompt (see §7 migration) — one active schema at a time, never two
  competing ones live simultaneously.
- **New module `uri_core/core/brain_decision.py`** — owns the new contract
  end to end:
  - `build_decision_context(...)`: assembles the compact, request-scoped
    payload — latest turn, recent grounded conversation (reuses
    `ConversationHistoryStore`/existing `query_context.conversation`,
    unchanged), attempt history (unchanged), and a **unified capability
    summary** merging `CapabilityFeasibility.snapshot()` (legacy,
    connection-aware) with the multi-action registry's
    `capability_summaries()` *plus* each multi-action capability's own
    `check_availability()` pulled forward to summary time (closing gap #1
    above) — one list, not two, so the Brain reasons over one real picture
    of what's usable right now instead of two disjoint catalogues.
  - `BRAIN_DECISION_SYSTEM_PROMPT`: documents the schema in §2, explicitly
    teaches the model when `mode` is `multi_action` vs `single_action` vs
    `unsupported`, and folds in (rather than duplicates) the existing
    conversation-recency/repeated-clarification guidance already proven
    in `REASONING_SYSTEM_PROMPT`.
  - `decide(...)`: calls the model through the *existing* transport
    (`model_reasoning_adapter`'s provider/router plumbing, reused not
    rewritten), parses and deterministically validates the result per §2,
    and degrades to `mode: "unavailable"` on any failure — never raises,
    matching every other model-facing boundary in this codebase.
- **`capability_planner.py`** — role clarified: remains the deterministic,
  zero-model-call fallback, used only when `brain_decision.decide()`
  returns `unavailable` (model unreachable/malformed) — exactly its
  existing position in today's priority chain, just formalized as the
  named fallback for a single call instead of one of several interleaved
  candidates. Its own scoring logic (including the just-shipped disclosure
  detection) is unchanged.
- **`multi_action_dispatch.py`** — role clarified: remains the *only*
  execution boundary for multi-action capabilities. `brain_decision.py`
  never re-implements discovery, permission-checking, or execution — when
  `decide()` returns `mode: "multi_action"`, orchestrator calls
  `MultiActionDispatch.dispatch()`/`execute_chain()` exactly as it does
  today, just reached through one explicit branch instead of an implicit
  "did the model happen to return a `multi_action` key" check.
- **`orchestrator.py`** — gains exactly one new call site
  (`brain_decision.decide(...)`) and a thin `match mode:`-shaped dispatch
  (six short branches: conversation/single_action/multi_action/
  clarification/approval_required/unsupported), replacing the current
  ~300-line interleaved block that infers the situation from
  model_capability_proposal/model_workflow_proposal_present/learned_skill/
  capability_planner_plan/multi_action_result/initial_clarification. Net
  effect on `orchestrator.py` is very likely a **reduction** in inline
  branching complexity, not growth — but see §7 for why this is a phased
  migration rather than a single risky rewrite of this exact hot path.

## 4. Runtime sequence

```
latest user turn
  -> recent grounded conversation context (ConversationHistoryStore, unchanged)
  -> unified capability/runtime-state summary (legacy CapabilityFeasibility
     + multi-action registry summaries, connection-aware for BOTH)
  -> brain_decision.decide(...)  [ONE model call, new contract]
  -> mode:
       conversation        -> existing _draft_narrative_safely path, no execution
       clarification       -> _apply_clarification_pause (unchanged)
       unsupported         -> new, honest "URI cannot currently do this" response
                              (deterministic template, optionally paraphrased
                              by the existing narrative-drafting/validation
                              pipeline - never a free-form model claim)
       single_action       -> existing ApprovalGate.execute_tool path (unchanged)
       multi_action        -> MultiActionDispatch.dispatch()/execute_chain() (unchanged)
       approval_required   -> existing ApprovalGate pending-decision path (unchanged)
  -> execution result (deterministic, from the real tool/executor)
  -> response drafting (_draft_narrative_safely, unchanged - drafts ONLY from
     the already-decided execution/response fields, never invents)
```

Every box after `brain_decision.decide(...)` already exists and is already
tested; this milestone's actual surface area is the decision step itself
and the thin dispatch that reads its `mode`.

## 5. Recent-context priority

Unchanged and already correct: `query_context.conversation` (recent turns),
`attempt_history` (this turn's own real results), and durable memory
(`personalization_context`, gated by `is_eligible_for_personalization`)
already flow in that precedence order into every model call. This milestone
does not touch that ordering — it only replaces *what the model is asked to
decide*, not *what it's given to decide with*. The "stale context" test in
§8 is a regression proof this stays true, not a new mechanism to build.

## 6. Legacy / M27 compatibility

- `LegacyCapabilityAdapter` (`capabilities/registry.py`) is untouched —
  still the one-way migration path for a single-purpose legacy capability
  into the multi-action shape, used only where a team chooses to migrate
  one.
- Every existing legacy capability keeps working through
  `ApprovalGate.execute_tool`/`ToolDispatcher` exactly as today —
  `brain_decision.py` only decides `mode`/`capability`/`actions`; it never
  bypasses or duplicates dispatch.
- M27's `MultiActionDispatch` gains no new public method — this milestone
  makes it *reachable* (by finally documenting its shape to the model and
  feeding it connection-aware summaries), it does not change its contract.

## 7. Migration / backward-compatibility strategy

Phased, reusing this codebase's own established pattern for introducing a
new decision mechanism safely (`enable_model_reasoning_shadow`/
`enable_skill_router_shadow` already exist as constructor flags for exactly
this purpose):

- **Phase 1 (this milestone's implementation, when authorized):** build
  `brain_decision.py` and the new prompt behind a new
  `enable_brain_decision_contract` flag, defaulted off. When on, orchestrator
  logs the new decision alongside the existing pipeline's outcome (shadow
  mode) without acting on it yet - pure comparison data.
- **Phase 2:** once shadow-mode logs show the new contract matches or
  improves on the test scenarios in §8 across a real sample of traffic,
  flip the flag on for real: `brain_decision.decide()` becomes the
  authoritative call, the six-branch dispatch replaces the current
  interleaved block, `capability_planner.plan()` becomes the named
  `unavailable`-only fallback.
- **Phase 3 (separate, later milestone):** once Phase 2 is stable, retire
  the now-dead branching left in `orchestrator.py` (model_capability_proposal/
  model_workflow_proposal_present/pre-execution sanity check's original
  shape/initial_clarification's old boolean-matching guard) and the old
  `REASONING_SYSTEM_PROMPT` schema, shrinking `orchestrator.py` rather than
  adding to it net.

This keeps every existing test green through Phase 1 (nothing observable
changes with the flag off) and makes Phase 2's cutover a single, reversible
flag flip rather than a big-bang rewrite of the most-audited, most fragile
region of `orchestrator.py`.

## 8. Required tests (mapped to the User's scenarios)

New `test_brain_decision_contract.py` (fake model_callable, no network):
- **Connected Gmail**: decision returns `mode="multi_action"` (or
  `single_action` for the legacy tool, whichever the unified summary
  represents it as), executes, no generic access-denial text.
- **Disconnected Gmail**: unified summary shows `usable=false,
  gap_reason="not_connected"`; decision must not silently propose it -
  either `unsupported=false` with an honest connection-required
  `reason`, or the deterministic validation layer downgrades a
  hallucinated proposal to that same honest response. Never a generic
  "I do not have access" with no explanation.
- **Supported + missing parameter** ("find the student"): `mode=
  "clarification"`, `clarification_reason` names the missing
  identifier, capability is still named (not discarded).
- **Permanently unsupported** ("schedule a recurring job search", no
  scheduling capability registered anywhere): `mode="unsupported"`,
  `unsupported_reason` set, no clarification loop, no capability
  executed, no "I'll start searching" language possible (the response
  template for this mode never includes such phrasing).
- **Known context reused**: two-turn scenario (open to any role -> asked
  to schedule) does not re-ask what's already been told; still resolves
  to `unsupported` (no capability exists) rather than a redundant
  question, per the case above.
- **Pure conversation**: `mode="conversation"`, zero capability/action
  dispatch of any kind.
- **Multi-action**: "how many unread emails and anything important" ->
  `mode="multi_action"`, `actions=["list_labels", "search_messages"]` (or
  equivalent), executed via `MultiActionDispatch.execute_chain`.
- **Approval-required**: a mutating action (e.g. `create_draft`) ->
  `mode="approval_required"`, `requires_approval=true`, pauses for a real
  decision exactly like today's `ApprovalGate` flow, never executes.
- **Stale context**: a new, unrelated topic after an unresolved prior turn
  must decide based on the NEW topic, not silently continue the old one -
  regression-proves §5 is unchanged.

Existing suites that must stay green unchanged: `test_capability_planner.py`,
`test_provider_semantic_interpreter.py`, `test_orchestrator_decision_
priority.py`, `test_orchestrator_user_interaction_hooks.py`,
`test_orchestrator_pre_execution_sanity_check.py`, `test_m25_clarification_
pause.py`, `test_multi_action_capabilities.py`.

## 9. Risks

- **Prompt compliance**: already-observed (this session) that the local
  qwen3:14b model does not reliably follow added prompt instructions
  alone. The deterministic validation layer in §2 is the safety net, not
  the prompt wording - every `mode`/`capability` claim is re-checked
  against real registry/connection state before being trusted, same
  discipline as the disclosure-detection fix just shipped.
- **Regression risk in the most fragile code region**: `orchestrator.py`'s
  decision block has been touched by M11, M13, M20, and M27 already, each
  layering more interleaved logic. The phased shadow-mode migration (§7)
  exists specifically to avoid a big-bang rewrite risk here.
- **Two schemas transiently live during Phase 1**: shadow mode necessarily
  means both the old and new contract are computed for a period - real but
  bounded (extra model call, log volume) cost, paid deliberately for
  migration safety.
- **Unified capability summary size**: merging legacy + multi-action
  catalogues could grow the decision request's context, which this exact
  model has already shown sensitivity to (prompt-bulk observations in
  `model_reasoning_adapter.py`'s own comments). Needs a compactness budget,
  mirroring `context_budget.py`'s existing `bound_json_value`/
  `fit_within_budget` (reuse, not reinvent).

## 10. History log

- 2026-09-12: Drafted and marked ACCEPTED (plan only) by Claude, per the
  User's explicit request to plan the structured Brain Decision Contract
  following the accepted bounded decision-priority fix. Investigation
  corrected an earlier live-verification claim (connection state is
  partially, not entirely, absent from the Brain's context - see §1).
  Not implemented. Release/implementation gate: awaiting the User's
  review of this plan and explicit direction on Phase 1 authorization.
