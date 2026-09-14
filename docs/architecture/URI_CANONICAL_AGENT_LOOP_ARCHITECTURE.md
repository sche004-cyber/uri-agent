# URI Canonical Agent Loop Architecture

**Stage:** 2 (design only — no implementation, no migration code, no routing changes, no prompt changes, no new capabilities)
**Author:** Claude (Architect role, AO-4)
**Date:** 2026-09-12
**Input:** `docs/research/URI_AGENT_LOOP_ROOT_CAUSE_AUDIT.md` (Stage 1, cited throughout by section number, e.g. "Stage 1 §4")

---

## 1. Architectural principles

Derived directly from Stage 1's ranked root causes (§15) and the external-research synthesis (§10):

1. **One decision step, not five.** Every symptom traced in Stage 1 came from fragmented authority, not from any single mechanism being badly built. The fix is structural: one component classifies the situation and proposes what to do; everything else either feeds it or enforces its output.
2. **Propose, never trust.** The model (whichever one answers) only ever proposes. Availability, permission, approval, and "this is genuinely unsupported" are always independently, deterministically verified before being acted on — never taken as the model's own claim. This is the ReAct/OpenHands "observation is real, not assumed" principle (Stage 1 §10) applied consistently everywhere, not just at execution.
3. **Progressive, not flat.** Capability visibility scales with relevance: a one-line summary is always present, a full action schema is loaded only once a capability is actually selected. This is M27's own discovery design (Stage 1 §12) — the fix is making it universal, not inventing it.
4. **Additive drafting, never inventive.** Final response text is drafted only from already-decided, already-real execution/decision fields — this principle is already correct in the current codebase and is unchanged here.
5. **Consolidate, don't accumulate.** A new reasoning mechanism replaces or absorbs what it supersedes. Nothing is added "beside" an existing decision path again — this is the single biggest lesson of Stage 1 §2's timeline.
6. **The orchestrator coordinates; it does not decide.** No priority ordering, no reconciliation logic, lives in the orchestrator. It calls exactly one decision authority and dispatches on its answer.
7. **Weak-model-safe by construction.** Every load-bearing truth (availability, permission, grounding, unsupported) is deterministic. A weaker model produces more clarifications and more fallback-safety-net use — never a wrong action, a hallucinated capability, or an invented ID.

---

## 2. Canonical agent loop

The requested `OBSERVE → assemble Turn State → decide → discover → load schemas → plan → validate → execute → record → re-enter? → respond` shape is **not adopted unmodified** — Stage 1 evidence (particularly §9 case B, the model_reasoning_adapter.py prompt-bulk lesson, and the two-classifier disagreement bug) argues against a separate model-driven "discover" round-trip between OBSERVE and DECIDE. Discovery is **data assembled into Turn State**, not a model call of its own. The canonical loop:

```
1. OBSERVE / ASSEMBLE TURN STATE
   owner: Turn State Assembler (new, deterministic)
   in:   session_id, raw user_text, principal
   out:  canonical Turn State (§3)
   model: no.  persisted: reads from persisted stores, writes nothing yet.
   continues without another call: n/a (this stage has no model call to skip)

2. DECIDE
   owner: Decision Engine (new; one canonical model-backed component)
   in:   Turn State
   out:  Brain Decision Contract (§5) — goal, mode, capability, actions,
         clarification, unsupported_reason, requires_approval, confidence, reason
   model: yes — exactly ONE authoritative call (internal implementation may
          use a cheap sub-call for goal/entity extraction feeding a second,
          but only the FINAL contract is ever treated as authoritative by
          anything downstream — see §13).
   persisted: the decision itself is recorded (audit trail), not yet the outcome.

3. DETERMINISTIC VALIDATE
   owner: Capability Directory + a small Completeness/Unsupported Gate (new,
          deterministic — absorbs today's CapabilityFeasibility +
          CapabilityDiscoveryEngine's relevance scoring, generalized)
   in:   the Decision Contract, real registry/connection/permission state
   out:  a CONFIRMED contract (mode may be downgraded/corrected here — e.g.
         a claimed "unsupported" that the directory shows a real match for
         is rejected back to single_action; a claimed single_action against
         a disconnected capability is redirected to the `disconnected`
         failure state, §15)
   model: no. deterministic only.
   persisted: no new state, pure validation.

4. ROUTE (thin dispatch on `mode`)
   owner: Orchestrator (thin coordinator, §14)
   in:   confirmed contract
   out:  a call to exactly one of: conversation-response path,
         clarification-pause path, unsupported-response path,
         Execution Engine (single/multi/workflow_continuation),
         approval-pending path
   model: no.

5. EXECUTE (only for action modes)
   owner: Execution Engine (new; subsumes ApprovalGate/ToolDispatcher +
          MultiActionExecutor behind one interface, §16)
   in:   capability id, action name(s), bound inputs (grounded IDs resolved
         from Turn State, never invented)
   out:  real result(s), one per action
   model: no. deterministic only. This is the one real ground-truth boundary.
   persisted: yes — audit trail, approval store state, any capability-owned
              state (e.g. a created draft).
   continues without another model call: YES, for every step whose plan
   was already fully specified by step 2's contract and whose result
   doesn't change what should happen next (e.g. a two-step Gmail chain
   planned in one Decision Contract executes both steps back-to-back).

6. RECORD
   owner: Turn State Assembler (writes back)
   in:   execution result(s)
   out:  updated attempt_history / grounded-entity table / capability
         availability deltas (e.g. a mid-chain rate-limit becomes a
         `temporarily_unavailable` fact for the NEXT decision)
   model: no.
   persisted: yes.

7. RE-ENTER? (deterministic check, not automatic)
   owner: Orchestrator, consulting the Decision Contract's own
          "does this result look complete relative to the stated goal"
          signal (produced by the Decision Engine when it planned
          multiple dependent steps, or by a lightweight completeness
          check when a chain step's result is ambiguous)
   → if incomplete/ambiguous/needs a follow-up decision: loop to step 2
     with the new result folded into Turn State's attempt_history.
   → if complete: proceed to step 8.
   model: only if looping (that IS the next DECIDE call, not a separate one).

8. RESPOND
   owner: Response Drafter (unchanged from today — additive-only,
          claim-consistency validated)
   in:   the final, real, already-decided execution/response fields
   out:  natural-language reply
   model: yes (drafting only — cannot alter what happened).
   persisted: session/turn history.
```

**Why this deviates from the requested skeleton:** "discover relevant capability" and "load scoped action contracts" are folded into step 1 (Turn State always carries capability summaries; a selected capability's full schema is loaded as part of validating/executing that specific proposal in steps 3–5, not as an independent model-facing round trip) — this directly avoids re-introducing the two-call, two-authority pattern Stage 1 identified as a root cause. "Plan" is not a separate step from "decide" — for URI's scale (single-user-turn, bounded action chains), separating them added a reconciliation seam (Stage 1 §4) without a corresponding benefit; the Decision Contract IS the plan.

---

## 3. Canonical Turn State schema

```json
{
  "turn": {
    "user_text": "...",
    "session_id": "...",
    "principal": { "user_id": "...", "role": "..." }
  },
  "recent_conversation": [ {"user": "...", "uri": "..."} ],
  "active_pointer": {
    "kind": "none | paused_workflow | pending_approval | awaiting_clarification_answer",
    "question": "... or null",
    "reference": "opaque id or null"
  },
  "attempt_history": [ {"goal": "...", "proposal": {...}, "result": {...}} ],
  "capability_summaries": [
    {"id": "gmail", "description": "...", "usable": true, "gap_reason": null,
     "requires_approval": false, "risk": "low"}
  ],
  "runtime_health": { "brain_reachable": true, "active_provider": "lm_studio/qwen3:14b" },
  "grounded_entities": { "$search.result.messages[0]": {"message_id": "..."} },
  "durable_memory_relevant": [ {"content": "...", "category": "..."} ],
  "graph_context": { "entities": [], "relationships": [] },
  "selected_capability_detail": { "actions": [...], "schemas": {...} }
}
```

| Field | Tier |
|---|---|
| `turn`, `recent_conversation` (bounded, e.g. last 6 turns), `active_pointer`, `capability_summaries` (name/description/usable only), `runtime_health` | **ALWAYS PRESENT** — small, cheap, every turn, no model call needed to produce them |
| `selected_capability_detail` (full action schema), `grounded_entities` for the capability just selected | **ON-DEMAND** — loaded once the Decision Engine has named a capability, never before |
| `durable_memory_relevant`, `graph_context` | **RETRIEVED WHEN RELEVANT** — keyword/entity-scoped to the current goal, never a full dump; computed only when `recent_conversation`+`turn` don't already answer the goal |
| `attempt_history` (full) | **RETRIEVED WHEN RELEVANT** — only non-empty on a re-entry (loop step 7) or an explicit follow-up reference |
| Raw credentials/tokens, other users' data, dispatcher-internal file paths/class names, `pending_confirmation` memory entries as if established, raw audit-trail/security-guard internals | **NEVER DIRECTLY EXPOSED TO MODEL** |

The model never receives "the entire body of URI." A pure-conversation turn (example I, §18) sees only the ALWAYS-PRESENT tier — no memory, no graph, no capability schema.

---

## 4. Decision ownership

Direct answers to the primary question's checklist, all resolved to the **Decision Engine** (proposing) + a small number of **deterministic verifiers** (confirming), never to the old five mechanisms independently:

| Responsibility | Owner |
|---|---|
| Interpreting the current user goal | Decision Engine (one call — supersedes the separate semantic-interpreter authority, §13) |
| Conversation vs. action | Decision Engine's `mode` |
| Selecting capability | Decision Engine proposes; **Capability Directory** deterministically validates the name is real and usable |
| Single-action vs. multi-action | Decision Engine's `mode` (`single_action`/`multi_action`) |
| Clarification | Decision Engine proposes; a deterministic **Completeness Gate** (generalizes this session's bounded fix into a first-class, reusable check) confirms it isn't overriding an already-resolved goal |
| Unsupported | Decision Engine may propose it; the **Unsupported Gate** (built from `CapabilityDiscoveryEngine`'s relevance scoring, generalized) must independently agree before it is honored — never the model's sole claim |
| Approval-required | Purely deterministic — read directly from the Capability Directory's `approval_requirement`, never proposed or overridable by the model |
| Whether another reasoning step is needed after execution | The same Decision Engine, re-entered (loop step 7) — not a separate "sanity check" or "post-execution evaluation" mechanism |

**Explicitly not the automatic owner:** the current Brain proposal mechanism, `capability_planner.py`, `WorkflowPlanner`, and `MultiActionDispatch` are none of them the new owner as-is. Each contributes a proven piece (schema/registry shape, discovery scoring, execution mechanics) to the new components below, but none retains independent decision authority (§16).

---

## 5. Brain Decision Contract

**Yes, URI needs one canonical structured contract** — this is the direct fix for Stage 1's central finding (§1, §15.1).

```json
{
  "goal": "the user's actual objective, plain text",
  "mode": "conversation | clarification | unsupported | single_action | multi_action | approval_required | workflow_continuation",
  "capability": "registered capability id, or null",
  "actions": [ {"name": "...", "inputs": {...}} ],
  "clarification": { "question": "...", "missing_field": "..." } | null,
  "unsupported_reason": "string or null",
  "requires_approval": false,
  "confidence": "high | medium | low",
  "reason": "short justification"
}
```

Distinctions covered (at minimum, per the request): `conversation`, `clarification`, `unsupported`, `single_action`, `multi_action`, `approval_required`, and — added beyond the minimum, directly closing a Stage 1 gap (§4, the "answer to my own question re-triggers clarification" bug) — **`workflow_continuation`**: a first-class mode for "this turn is resuming `active_pointer`," checked before the Decision Engine is even allowed to treat the message as a fresh goal.

**Where the old mechanisms fit under this contract, explicitly:**
- **Semantic interpretation** — folded in. Goal/entity extraction becomes the Decision Engine's own first field, not a separately-authoritative prior call whose output (`task_type`, `requires_clarification`) other components read independently. (Its transport code is retained, §16.)
- **Capability planning** (`capability_planner.py`) — demoted to a helper: the deterministic engine behind the Unsupported Gate, and the safety-net fallback when the Decision Engine itself is unreachable or returns malformed output.
- **Workflow planning** — a proposed `multi_action`/named-procedure `actions` list under this same contract, not an independent decision (§12).
- **Multi-action planning** (M27) — becomes the universal Execution Engine for every `single_action`/`multi_action` contract, not a separately-triggered parallel path only reachable by an undocumented shape (§16).
- **Learned skills** — a Turn State input (a hint the Decision Engine may weigh), never a path that can produce a plan on its own (§13).

No two of these ever independently produce a competing decision again — there is one contract, one producer, one set of deterministic verifiers.

---

## 6. Capability discovery model

One **Capability Directory** (logically one interface; may be backed by more than one physical store during migration — Stage 3's concern, not this design's) is the single source of truth capabilities enter through:

```
implemented
  → registered            (one registration call: identity, actions, schemas,
                            availability_provider, permissions, approval
                            requirements, execution handler — §17)
  → discoverable           (appears in capability_summaries, ALWAYS-PRESENT tier)
  → availability known     (usable/gap_reason computed fresh per turn by the
                            registered availability_provider — real connection/
                            health state, not a static flag)
  → Brain-visible when relevant  (full action schema loaded ON-DEMAND, only
                            after the Decision Engine names this capability —
                            M27's own progressive-discovery shape, made universal)
  → executable             (Execution Engine, one interface for all capabilities)
  → result returned         (folded into attempt_history/grounded_entities for
                            the next decision, same turn or next)
  → follow-up grounded      (a generalized CapabilityContextResolver reads each
                            capability's declared grounding metadata, §17, to
                            resolve "read that one" against real prior results —
                            not a Gmail-specific mechanism)
```

Avoided by construction: **huge flat tool lists** (only summaries are always-present; full schemas are progressive) — **capability-specific prompt patches** (the Decision Engine's prompt is capability-agnostic; all per-capability detail lives in directory data, never prompt text) — **one-intent-per-phrase routing** (`capability_planner`-style keyword scoring is retired as a decision mechanism entirely, kept only as the Unsupported Gate's cross-check and the unreachable-model fallback, §16).

---

## 7. Runtime self-knowledge model

**Does URI need a canonical self-model, or is dynamic discovery enough?** Dynamic discovery is the right call — a static self-model would drift the moment a service connects/disconnects. Stage 1's actual problem was never "dynamic discovery is wrong," it was **two parallel dynamic-discovery systems with inconsistent vocabulary and inconsistent freshness** (legacy `CapabilityFeasibility` vs. M27's connection-blind summaries). The fix is **one** dynamic Capability Directory snapshot, computed fresh every turn, not a switch to static self-knowledge.

**States, represented deterministically, never inferred from phrasing:**

| State | Computed by | Distinct from |
|---|---|---|
| `supported_ready` | `usable == true` in the directory snapshot | — |
| `supported_disconnected` | `usable == false`, `gap_reason` names a real connection/auth gap | permanently_unsupported (the capability EXISTS, just isn't authorized right now) |
| `supported_missing_parameter` | NOT an availability state at all — a **planning-time** outcome: the capability is `usable == true`, but the proposed `actions[].inputs` fails schema validation for a required field | disconnected/unsupported (this is the fix for Stage 1 §9 case D's core confusion — availability and completeness are now structurally different checks, computed by different components, and can never collapse into the same response shape) |
| `approval_required` | `requires_approval` read directly from the directory, never proposed | — |
| `temporarily_unavailable` | a live health signal (rate-limited, transient network failure — reusing `ModelRouter`'s `ProviderHealthTracker` pattern, generalized to capabilities) | disconnected (this was working moments ago and is expected to recover; disconnected is a standing authorization gap) |
| `permanently_unsupported` | the **Unsupported Gate**: no entry in the directory's summaries, run through `CapabilityDiscoveryEngine`'s relevance scoring against the stated goal, scores above a real threshold — a genuine deterministic check, not the model's unchecked say-so (mirrors `conversational_classifier.py`'s existing two-signal discipline, applied here) | supported_disconnected (nothing registered even claims to do this, vs. something registered that merely isn't connected) |

This is not phrase-specific: every state above is a registry/health lookup or a relevance-score threshold, never a regex on the user's words.

---

## 8. Execution feedback loop

Every execution result carries, structurally, back into the next decision:

| Signal | Where it lands |
|---|---|
| Structured result (real data) | `attempt_history[-1].result` |
| Execution evidence | Audit trail (unchanged mechanism) + `attempt_history` |
| State changes (e.g. a draft created) | Capability-owned state (unchanged — e.g. Gmail draft store) + a grounded-entity record if applicable |
| Grounded entity references (message_id, thread_id, file_id...) | `grounded_entities`, keyed for the generalized context resolver |
| Errors | A typed failure state (§15), never a bare exception string |
| Availability updates (e.g. mid-chain rate limit) | `capability_summaries` for the NEXT decision — a `temporarily_unavailable` fact, not silence |
| Approval state | The approval store's existing pending/decided/consumed lifecycle (unchanged), reflected in `active_pointer` |

**Reasoning loops again when:** the Decision Contract itself planned a dependent multi-step chain where a later step depends on an earlier result the model hasn't seen yet, or a chain step's real result is ambiguous relative to the stated goal (the direct descendant of today's `evaluation.satisfied` idea — kept, but now expressed as one more re-entry into the SAME contract, not a bespoke second mechanism).

**Runtime continues deterministically (no re-entry) when:** every remaining step in an already-planned chain is fully specified and no step's result changes what comes next — e.g., example B (§18): `list_labels` then `search_messages` were both named in one Decision Contract and execute back-to-back without a second model call.

---

## 9. Memory / session / graph relationship

**Precedence, explicit (directly answers "old memory must never override the current topic"):**

```
latest user turn
  > recent conversation turns
  > this turn's own execution/grounded results (attempt_history)
  > active session/workflow state (active_pointer)
  > durable memory (confirmed only)
  > graph-derived context
```

Enforced two ways, not prompt-wording alone (Stage 1's own lesson — a prompt-only rule was not reliably followed by qwen3:14b): (1) Turn State's own section ordering places recency-tier fields structurally closer to `turn`/`recent_conversation` than durable-memory/graph fields; (2) a deterministic recency check (the same kind of goal-continuity comparison already proven this session) can suppress durable-memory/graph retrieval entirely when the current goal is clearly a new topic, rather than relying on the model to correctly deprioritize stale context it was handed anyway.

**Passive memory candidates** (the M28 plan) are explicitly **not memory** for decision purposes — they live in a review-only tier (`pending_confirmation`), never entering `durable_memory_relevant` until a real user confirmation promotes them. This boundary is unchanged from today's `is_eligible_for_personalization` gate and is the correct existing design (Stage 1 did not fault this part).

**How retrieval enters Turn State without flooding context:** `durable_memory_relevant` and `graph_context` are both keyword/entity-scoped to the current goal (not a full store dump) and are only populated at all when the always-present tier doesn't already answer the goal — mirroring Anthropic's "just-in-time context" principle (Stage 1 §10) rather than the model_reasoning_gateway's current "always attach everything CapabilityFeasibility knows" pattern.

---

## 10. Graphify role

Combination of **B (invisible retrieval/context infrastructure) and C (part of Turn State assembly)** — explicitly **not A** (never a directly-discoverable, Brain-named capability) and not a fourth co-equal pillar (D) — it is one contributor to the memory/context tier defined in §9, not an independent architecture layer.

- **What feeds it:** the same ingestion design M23 already built (`Fact` confirmation with a real, accountable verification actor; `MemoryStore.confirm()` on both immediate `user_provided` and passive-candidate-then-confirmed entries per M28) — Stage 1's finding was that these triggers are *unwired*, not that the design is wrong. This architecture keeps the design and requires the triggers to actually be live (a Stage 3 migration item, not an architecture change).
- **When ingestion occurs:** at the exact moment a fact/memory becomes durable-and-confirmed — unchanged from M23's intent.
- **What retrieves from it:** Turn State's `graph_context` field, scoped to entities mentioned in the current goal, via the existing bounded traversal primitives (`graph_engine.py`'s six read primitives — unchanged, already correctly bounded).
- **How it reaches reasoning:** as one already-summarized JSON section within Turn State, exactly as today — never as something the model calls directly.
- **Does the Brain need to know "Graphify" exists as a named capability?** No. Its output appears, unlabeled as to source, indistinguishable to the model from any other contextual fact. This is a direct, explicit answer to "do not expose internal infrastructure merely because it exists."

---

## 11. Workflow role

The current deterministic `WorkflowPlanner`/`WorkflowCapabilityRouter` **does not remain a separate decision engine.** Workflows become two things, both owned by existing components rather than a third:

1. **Named, deterministic, reusable procedures** — registered in the same Capability Directory as a capability-shaped entity (its own summary, its own declared action sequence), so discovery treats "run the standard onboarding checklist" exactly like any other capability. Invoked when the Decision Contract's `mode=multi_action`/`actions` names the procedure.
2. **Ad hoc multi-step plans** the Decision Engine proposes fresh for a novel request — just a `mode=multi_action` `actions` list, executed by the Execution Engine (§16) like any other multi-action chain. No separate "workflow" concept survives as an independent decision-maker.

Long-running/background job execution (if ever needed beyond a single turn's synchronous chain) is explicitly **out of scope** here — flagged as an open question (§20), not solved by folding it into either of the above.

---

## 12. Learned-skill role

A learned skill is **none** of: a capability, an action bundle, a workflow, executable code, or policy. It is **context** — specifically, a Turn State hint ("a request shaped like this previously succeeded via capability X, N times") the Decision Engine may weigh exactly like any other contextual signal. It has **zero authority to become a plan on its own** — this closes today's `learned_skill.get("tool_name")` direct-to-plan shortcut (Stage 1 §4) entirely; the existing docstring's own stated intent ("REFERENCE ONLY") becomes, under this architecture, actually and structurally true rather than true-in-theory-but-bypassable.

---

## 13. Model strategy

**What the model owns:** understanding intent/goal, proposing `mode`+capability+actions, interpreting real execution results to decide whether to loop, drafting the final natural-language response.

**What stays deterministic, never trusted from the model:** authorization, schema validation of proposed inputs, capability availability truth, connection truth, approval enforcement, execution itself, audit trail, and grounding-ID resolution (a grounded ID is always resolved from a real prior result via the generalized context resolver — never accepted verbatim from the model's own proposal text).

**Escalation strategy:**
- **qwen3:14b handles the Decision Contract for the common case** — a scoped Turn State, one capability domain, ordinary confidence. This session's own evidence (the disclosure-classification fix) shows this model's compliance gaps are cheaply closed with a deterministic cross-check, not necessarily a bigger model.
- **The router escalates to a stronger model** specifically when: the Decision Engine's own `confidence` field comes back `low` twice in a row for the same goal (a real, measured signal — not a guess); `mode=multi_action` is proposed with more than a small step threshold; or the Unsupported/Completeness Gates disagree with the model's claim twice running. This reuses the existing `ModelRouter`/provider abstraction (M22.6) — a routing *policy* change, not new plumbing.
- **Capability discovery reduces model burden before any escalation is needed** — because the always-present Turn State tier is deliberately small (progressive discovery, §6), most turns never approach a context size that would justify a bigger model on cost/latency grounds alone.
- **The architecture does not depend on a frontier model to remain correct**, by construction: every load-bearing truth is deterministic (§1 principle 2). A weaker model degrades to more clarifications and more fallback use — never to a wrong action executing, a hallucinated capability, or an invented grounded ID.

---

## 14. Orchestrator role

**Confirmed by Stage 1 evidence: a thin coordinator**, not the Brain, and not a decision-maker. Its full responsibility under this architecture:

1. Call the Turn State Assembler.
2. Call the Decision Engine exactly once (plus internal re-entries per loop step 7 — still one logical call site).
3. Call the deterministic validators (Capability Directory, Completeness Gate, Unsupported Gate).
4. Dispatch on `mode` — a flat match, not a priority chain: `conversation` / `clarification` / `unsupported` / `single_action` / `multi_action` / `approval_required` / `workflow_continuation`, each routing to exactly one downstream call.
5. Call the Execution Engine for action modes.
6. Persist Turn State updates.
7. Call the Response Drafter.

**It contains no implicit priority ordering among competing decision systems** — there is exactly one decision system to dispatch on. This is very likely a **net reduction** in `orchestrator.py`'s current line count (Stage 1 §3 traced roughly 300 lines of interleaved priority logic that this design replaces with a single flat dispatch), consistent with the standing "must never grow" rule being something this design satisfies by consolidation rather than by restraint alone.

---

## 15. Failure-state model

Explicit, distinct states — **none collapse into generic clarification or conversational fallback**:

| State | Trigger | Distinct from |
|---|---|---|
| `unsupported` | Unsupported Gate confirms no directory entry plausibly matches | `disconnected` (something registered vs. nothing registered) |
| `disconnected` | Capability Directory shows `usable=false` with a connection-shaped `gap_reason` | `unsupported` |
| `permission_denied` | Execution Engine's permission check fails for the resolved principal | `disconnected` (authorization vs. connection) |
| `approval_needed` | Directory's `requires_approval=true`, no real prior decision exists | `permission_denied` |
| `tool_failure` | A real execution exception during a capability's own handler | `retryable_failure` (see below) |
| `partial_result` | A multi-action chain halted partway with some real evidence already produced | `tool_failure` (there IS usable evidence here) |
| `retryable_failure` | A health-tracked, transient condition (rate limit, timeout) | `tool_failure` (this one is expected to recover) |
| `missing_parameter` | Schema validation on proposed `actions[].inputs` fails for a required field, capability itself `usable=true` | `disconnected`/`unsupported` (the capability is fine; the proposal is incomplete) |
| `stale_context` | The deterministic recency check (§9) detects the new message is not continuing the prior goal | `ambiguous_request` |
| `ambiguous_request` | Genuinely multiple plausible interpretations remain after Turn State is fully assembled | `missing_parameter` (this isn't "one field missing," it's "which of several things did you mean") |

Each state gets its own honest response template family, still narrative-drafted (additive-only, §1 principle 4) — never fabricating beyond the real, already-known state. Several of these (`disconnected`, `permission_denied`, `approval_needed`) are **already known before the Decision Engine is even called**, since they come straight from Turn State's `capability_summaries` — the Brain is told the real state rather than having to infer it from a raw failure.

---

## 16. Retain / consolidate / demote / deprecate / retire matrix

| Component | Disposition | Why |
|---|---|---|
| Semantic interpreter / `provider_semantic_interpreter.py` | **DEPRECATE** as an independent authority | Its extraction role folds into the Decision Engine; its actual model-call transport is **retained**, reused as the Decision Engine's own transport. |
| `model_reasoning_adapter.py` | **CONSOLIDATE** | Becomes the (revised) prompt/transport for the Decision Engine; `REASONING_SYSTEM_PROMPT` is superseded by the Decision Contract prompt. |
| `capability_planner.py` | **DEMOTE TO HELPER** | Deterministic Unsupported-Gate engine + unreachable-model fallback only — never a competing first-mover again. |
| `WorkflowPlanner` / `WorkflowCapabilityRouter` | **RETIRE as an independent decision engine; CONSOLIDATE its templates** into named Capability-Directory procedures (§11) | Its standalone decision-making role is fully absorbed; specific templates may be ported, not the mechanism. |
| `MultiActionDispatch` | **CONSOLIDATE into the Execution Engine** | Its dispatch/permission/binding logic is exactly right — it becomes universal instead of Gmail-only-and-effectively-unreached. |
| `MultiActionExecutor` | **RETAIN** | Becomes the execution core for every action mode, single and multi. |
| `CapabilityDiscoveryEngine` | **RETAIN** | Becomes part of the unified Capability Directory's relevance scoring, reused for the Unsupported Gate. |
| Learned-skill matcher (`skill_memory.py`) | **DEMOTE TO HELPER** | Turn State reference input only (§12) — its own "reference only" docstring intent finally made structurally true. |
| Response drafting (`response_drafting.py`, `_draft_narrative_safely`) | **RETAIN unchanged** | Already correct — additive-only, claim-consistency validated. |
| `dispatcher.py` | **RETAIN** | Still the low-level legacy tool-invocation mechanic, now called only via the Execution Engine, never directly. |
| `ApprovalGate` | **RETAIN unchanged** | Already the one correctly-enforced execution boundary. |
| Graphify / Graph Intelligence (`graph_*.py`) | **RETAIN** | Architecture unchanged (§10); its ingestion triggers must actually be wired live — a migration item (Stage 3), not a design change. |
| Memory / facts (`user_memory.py`, `facts.py`) | **RETAIN**, with the passive-candidate tier (M28) as the real live path that makes durable memory — and therefore graph ingestion — non-dormant | Consent model (`user_provided`/`user_confirmed`/`pending_confirmation`) is already correct and unchanged. |
| `LegacyCapabilityAdapter` | **RETAIN** as the migration bridge | Folds remaining single-purpose legacy tools into the unified Capability Directory over time (Stage 3 concern). |

---

## 17. Future add-on contract

A new capability declares, once, at registration — the canonical loop discovers it automatically, with **no orchestrator edit, no new prompt text, no new keyword branch anywhere**:

| Field | Purpose |
|---|---|
| `identity` | id, category, human description |
| `actions` | name, description, per-action parameter schema |
| `capability_summary` | auto-derived from `identity`/`actions` — never separately authored, so it can never drift out of sync with the real schema |
| `availability_provider` | a callable returning `usable`/`gap_reason` — reuses the unified feasibility interface; connection-aware automatically if it declares a service dependency |
| `permissions` | the existing grant-alias mechanism, generalized beyond Gmail |
| `approval_requirements` | per-action, existing `ApprovalRequirement` enum — unchanged |
| `execution_handler` | the existing `Action.handler` convention — unchanged |
| `result_schema` | declared `returns` — already part of `ActionSchema` |
| `grounding_metadata` | which output fields are groundable IDs a later turn might reference — feeds the generalized context resolver instead of a Gmail-specific one |
| `health_status` | an optional live-health hook, generalizing `ModelRouter`'s `ProviderHealthTracker` pattern to capabilities |
| `context_requirements` | which Turn State sections this capability's actions need (e.g. "needs a prior search result") — declared, not hardcoded into the resolver |

Registration alone makes the capability appear in `capability_summaries` and become selectable by the Decision Contract — this is the direct mechanism by which "every future add-on must automatically fit the same lifecycle" is satisfied.

---

## 18. End-to-end example traces

**A. Gmail unread count (connected).** Turn State: `capability_summaries` shows `gmail: usable=true`. Decision Engine → `{mode: single_action, capability: gmail, actions: [{name: list_labels}]}`. Validate: usable, no approval needed. Execute: real unread count returned, no re-entry needed. Respond: drafted from the real count.

**B. Gmail unread + important messages.** Decision Engine → `{mode: multi_action, actions: [{name: list_labels}, {name: search_messages, inputs: {query: "is:unread"}}]}`. Both steps were fully specified in one contract and neither result changes the other's plan → Execution Engine runs both back-to-back, **no re-entry**. Respond from the aggregated real results.

**C. Disconnected Gmail (same request as A).** Turn State's `capability_summaries` already shows `gmail: usable=false, gap_reason=not_connected` — this is known BEFORE the Decision Engine is called. Whether the Engine proposes `single_action` anyway or recognizes the gap itself, the deterministic gate intercepts before the Execution Engine is ever invoked and returns the `disconnected` failure state (§15) — never attempts execution, never says "I'll check" with nothing behind it.

**D. Unsupported scheduled job search.** No directory entry, scored through `CapabilityDiscoveryEngine`, plausibly matches "recurring scheduled search." The Unsupported Gate confirms this independent of whatever the Decision Engine itself proposed. Final mode: `unsupported`, `unsupported_reason` set, one honest response, **no clarification loop**, nothing executes.

**E. Office note generation.** Straightforward `single_action`, `capability=draft_institutional_note`, `requires_approval=false` per the directory — executes and drafts, unchanged from today's already-correct mechanics.

**F. "I work at NIT Sikkim."** Turn State carries a lightweight, deterministic disclosure hint (this session's regex heuristic, relocated from "a competing keyword-scoring planner" to "advisory Turn State input") alongside the raw text. Decision Engine → `{mode: single_action, capability: remember_fact, actions: [{name: save, inputs: {content: "I work at NIT Sikkim"}}]}` in the SAME call that extracted the goal — no second, independently-authoritative classifier exists to disagree with it. If the model still misclassifies, the deterministic hint gives the validator something concrete to catch it against.

**G. File conversion.** `single_action`, `capability=convert_document`, attachment-based execution — unchanged mechanics.

**H. "Find email" → "Read that one" → "Check attachment."** Turn 1: `single_action(search_messages)` → result's message list recorded in `grounded_entities`. Turn 2 ("read that one"): the generalized context resolver resolves the referring expression against the real prior result → Decision Engine proposes `single_action(read_message)` with the resolved, never-invented `message_id` bound. Turn 3 ("check attachment"): same pattern against the read message's real attachment list.

**I. Pure conversation.** "Do you think changing careers is sensible?" — Turn State's `capability_summaries` show no meaningful overlap with the goal. Decision Engine → `{mode: conversation}`, no capability, no actions. Response drafted directly as conversation — no capability executes, and none was ever claimed.

---

## 19. Risks / tradeoffs

- **Latency/prompt-bulk risk in one bigger decision call** vs. today's several smaller ones. Mitigated by progressive Turn State tiers, but the actual cost is unmeasured — a Stage 3 concern.
- **Folding semantic interpretation into the Decision Engine removes today's cheap, narrow, fast first classification pass.** For the simplest turns this may cost more tokens than the old two-call approach; the confidence-based escalation policy (§13) only partially offsets this and is unproven.
- **Unifying two capability registries into one directory interface is real engineering work**, not free — physical data-model migration is explicitly deferred to Stage 3.
- **The Unsupported Gate's relevance-score threshold can itself be wrong** in either direction (false negative: a real match scores too low and gets called unsupported; false positive: a genuinely novel phrasing for an existing capability). It needs the same conservative, two-signal discipline `conversational_classifier.py` already applies, not blind trust in a single score.
- **Retiring `WorkflowPlanner`'s standalone role risks losing coverage** for edge-case task types its templates handled that neither Brain-composed multi-action nor named procedures yet replicate — needs a real inventory before retirement, not assumed here.
- **Confidence-based model escalation needs real usage data** to tune thresholds correctly; wrong thresholds either escalate too often (cost) or too rarely (quality regressions this design is meant to prevent).

---

## 20. Open questions

- Physical migration path for unifying the two capability registries — full merge vs. a shared interface over two physical stores? (Stage 3.)
- Real thresholds/mechanics for confidence-based escalation — needs measurement, not architectural judgment alone.
- Should named reusable procedures (§11, `WorkflowPlanner`'s replacement) be authored as data (JSON) or code, and by whom?
- How uniformly can `grounding_metadata` (§17) actually generalize the context resolver beyond Gmail-shaped cases across every existing capability — not fully evaluated here.
- Long-running/background job execution beyond a single turn's synchronous chain is explicitly out of scope — not designed in this document.
- How much of Turn State assembly can be pre-computed/cached per session vs. rebuilt fresh every turn, for latency — not measured.

---

*Stage 2 complete. No implementation, migration code, routing changes, prompt changes, or new capabilities were made as part of this design, per the User's explicit instruction. Stage 3 (safe migration from the current architecture to this design) is separate, not-yet-authorized work.*
