# URI Canonical Agent Loop — Migration & Integration Plan

**Milestone:** M30 (see `docs/plans/M30_STATE.md`)
**Stage:** 3 of 4 (EVIDENCE → ARCHITECTURE → **MIGRATION** → IMPLEMENTATION)
**Status:** ACCEPTED (plan only, auto-approved per ORCHESTRATION.md §1.5) — **implementation (Stage 4) not authorized**
**Author:** Claude (Architect role, AO-4)
**Date:** 2026-09-12
**Authoritative inputs (frozen):** `docs/research/URI_AGENT_LOOP_ROOT_CAUSE_AUDIT.md` (Stage 1), `docs/architecture/URI_CANONICAL_AGENT_LOOP_ARCHITECTURE.md` (Stage 2)

**Naming note, stated explicitly to avoid silent drift:** the Stage 3 prompt's own mode list uses `action`; the frozen Stage 2 schema (§5) uses `single_action`. Per this document's own instruction ("use the exact accepted architecture document for final naming/schema"), **`single_action` is authoritative** throughout this plan and every milestone below. This is flagged here once rather than silently reconciled, matching this repository's own standing discipline for exactly this kind of naming discrepancy.

---

## 0. Governing constraint

Nothing in this plan modifies production code, prompts, routing, or capability wiring. Every milestone described in §17 is a **future**, separately-authorized Stage 4 implementation task. This document defines *how* that work would proceed safely, not the work itself.

---

## 1. Current-to-target component matrix

| Component | Current responsibility | Target responsibility (Stage 2) | Migration action | Classification |
|---|---|---|---|---|
| `UriOrchestrator` | Assembles context, runs ~5 interleaved decision candidates with implicit priority, dispatches, persists | Thin coordinator: Turn State → Decision Engine → gates → flat mode dispatch → Execution Engine → persist → draft | Shrinks incrementally as each phase lands; never rewritten in one pass | **ADAPT** |
| `model_reasoning_adapter.py` | Transport + `REASONING_SYSTEM_PROMPT` (action/workflow/clarification/evaluation) | Decision Engine's transport; prompt superseded by the Decision Contract prompt | Transport class reused as-is; prompt content replaced in M30.3, behind a flag | **ADAPT** |
| Legacy `semantic_interpreter.py` (Groq-shaped) | Alternate/legacy 8-key interpreter, not the default path | None — folded into Decision Engine | Confirm zero live production config selects it (§1 note below); if confirmed unused, retire directly rather than migrate | **RETIRE** (pending a one-time confirmation check, §17 M30.0) |
| `provider_semantic_interpreter.py` | Default 8-key semantic contract, independently trusted by `capability_planner.py` | Folded into Decision Engine's own goal/entity extraction; no longer independently authoritative | Its model-call transport is reused inside the Decision Engine module; its *contract* (8 keys, separately consumed elsewhere) is deprecated once nothing reads it independently | **WRAP**, then **DEPRECATE** as a standalone authority |
| `capability_planner.py` | One of five competing decision paths (keyword scoring), always computed | Unsupported-Gate engine + unreachable-model/malformed-decision fallback only | Code largely reused; call sites in `orchestrator.py` narrowed to exactly these two roles | **DEMOTE** |
| `capabilities_registry.json` / `CapabilityRegistry` | Legacy capability metadata, feasibility-aware (M20) | One physical backing store under the unified Capability Directory interface | Directory interface wraps it; no data migration required initially | **MIGRATE** (interface-level, not data-level, first) |
| `CapabilityFeasibility` | Legacy-only usable/gap_reason/blocked_by computation | The Directory's availability-gate engine, generalized to both backing stores | Extended, not rewritten — its connection-awareness logic is exactly right and is reused | **ADAPT** |
| `MultiActionCapabilityRegistry` | M27's separate registry, connection-blind at discovery | Second physical backing store under the same Directory interface | Directory interface wraps it; `check_availability()` results pulled forward to summary time (closes Stage 1 §11.6's gap) | **MIGRATE** (interface-level) |
| `CapabilityDiscoveryEngine` | M27's relevance scoring, used only within the multi-action registry | Shared: capability-summary relevance AND the Unsupported Gate's cross-check | Reused unchanged; called from two places instead of one | **KEEP** |
| `MultiActionDispatch` | M27's proposal-shape-triggered dispatcher, live-verified unreachable | Folded into the Execution Engine as the universal action-execution path | Its permission/binding/execution logic is retained; its *triggering condition* (an undocumented model-output shape) is replaced by the Decision Contract's explicit `capability`/`actions` fields | **WRAP**, then **MIGRATE** into Execution Engine |
| `MultiActionExecutor` | Deterministic validate→execute→audit for multi-action capabilities | The execution core for every action mode (single and multi) | Unchanged internally; called for legacy capabilities too, via a thin adapter (§3) | **KEEP** |
| `CapabilityContextResolver` | Gmail-specific grounded-ID resolution | Generalized resolver reading each capability's declared `grounding_metadata` | Extended to read metadata rather than Gmail-specific assumptions | **ADAPT** |
| `dispatcher.py` (`ToolDispatcher`) | Legacy tool invocation, called directly by `ApprovalGate`/`WorkflowCapabilityRouter` | Still the low-level invocation mechanic, called only via the Execution Engine | No internal change; call sites consolidated | **KEEP** |
| `ApprovalGate` | The one enforced execution boundary for legacy capabilities | Unchanged — the approval enforcement layer inside the Execution Engine | None | **KEEP unchanged** |
| `WorkflowPlanner` / `WorkflowCapabilityRouter` | Deterministic, task-type-templated workflow decision engine | Retired as a decision engine; specific templates become named Capability-Directory procedures | Inventory templates (§17 M30.2), port the ones still needed as data, retire the matching logic | **RETIRE** (decision role); **MIGRATE** (templates, selectively) |
| `WorkflowExecutor` | Executes a deterministic or Brain-composed workflow's steps | Folded into the Execution Engine's multi-action chain runner | Interface likely compatible as-is; confirmed during M30.5 | **ADAPT** |
| Learned-skill matcher (`skill_memory.py`) | Can become a direct plan (`learned_skill.get("tool_name")`) ahead of the deterministic planner | Turn State reference hint only, zero plan authority | The single line that turns a skill match directly into a plan is removed; the lookup itself is reused as a Turn State field | **DEMOTE** |
| Response drafting (`response_drafting.py`, `_draft_narrative_safely`) | Additive-only, claim-consistency-validated drafting after execution | Unchanged | None | **KEEP unchanged** |
| Memory (`user_memory.py`) | Consent-gated `add`/`propose`/`confirm`, `propose()` never called live | Same consent model; passive-candidate tier (M28, §16) actually wired to a live caller | `propose()`/`confirm()` gain a real caller during migration, not a new consent model | **ADAPT** |
| Facts / session context (`facts.py`, `state.py`) | Session-scoped facts, `Fact.verify()` never called live | Same model; `verify()` gains a real, accountable caller if/when Graph ingestion needs it | No schema change | **KEEP**, with a targeted caller addition (§8) |
| Graph Intelligence (`graph_*.py`) | Fully wired, structurally empty (ingestion triggers unreached) | Invisible infrastructure feeding Turn State, unchanged design | Ingestion triggers connected to the now-live memory/fact callers above | **KEEP** (architecture), **ADAPT** (wiring) |
| `ModelRouter` | Per-call provider resolution, health tracking, fallback | Reused unchanged for confidence-based escalation policy (Stage 2 §13) | Escalation is a new *policy* layered on top, not new plumbing | **KEEP** |
| `connection_status.py` | Real Gmail/Drive OAuth state, source of truth | Unchanged — consumed by the unified availability gate | None | **KEEP unchanged** |
| Evidence/retrieval (`evidence_context.py`, `evidence_processor.py`) | Bounded evidence assembly for drafting/verification | Unchanged | None | **KEEP unchanged** |
| Recovery/fallback logic (`workflow_recovery.py`, M20 research-recovery) | Ad hoc recovery within the old workflow/reasoning paths | Folded into the canonical loop's step-7 re-entry semantics | Logic reused; trigger points move from scattered call sites to the one loop re-entry check | **ADAPT** |

---

## 2. Turn State migration

**Principle: introduce Turn State as a read-only, additive PROJECTION of existing context sources first — it does not replace `query_context.py`, `session_context`, or `model_reasoning_gateway`'s request-building until a later phase proves it's safe to.**

**Initial (M30.1) Turn State schema — a strict subset of the full Stage 2 schema, every field sourced from something that already exists:**

| Field | Source | Authoritative owner (unchanged) |
|---|---|---|
| `turn.user_text`, `turn.session_id`, `turn.principal` | Existing `/ask` request handling | `server.py` |
| `recent_conversation` | `ConversationHistoryStore.get_session()` (already exists, already used in `query_context.conversation`) | `conversation_history.py` |
| `active_pointer` | Projected from `session.active_workflow`/`active_workflow_question` (already exists) | `state.py` `Session` |
| `capability_summaries` | Projected from `CapabilityFeasibility.snapshot()` (legacy) + `MultiActionCapabilityRegistry.capability_summaries()` (M27) — concatenated, not yet merged in shape | `capability_feasibility.py` + `uri_core/capabilities/registry.py` |
| `runtime_health` | Projected from `ModelRouter`'s existing health tracker | `model_router.py` |
| `attempt_history` | Already exists verbatim (M11 Part 2) | `orchestrator.py` |

**Explicitly deferred to a later phase (not in M30.1):** `grounded_entities` (needs the generalized context resolver, M30.6), `durable_memory_relevant`/`graph_context` (needs the memory/graph wiring, M30.8), `selected_capability_detail` (needs the Directory's progressive-schema loading, M30.2).

**Compatibility adapters:** a `TurnStateProjector` module reads the *existing* stores above and produces the Turn State shape — it does not change what those stores contain or how anything else reads them. `query_context.py` is untouched in M30.1; the Decision Engine (once introduced, M30.3) reads Turn State, everything else keeps reading `query_context` exactly as today.

**Temporary duplication, named exactly:** during M30.1–M30.7 (shadow mode through controlled canonical execution), Turn State and `query_context.py`'s request necessarily overlap (both carry `recent_conversation`, both carry capability info in different shapes). This duplication is **removed at M30.8** (canonical default cutover), when `query_context.py`'s decision-relevant fields are retired in favor of Turn State and only its drafting-relevant fields (identity, personalization, soul/policy text) remain — response drafting never needed the decision-making fields to begin with.

**How action results update Turn State:** unchanged mechanism (`attempt_history` append), now also written into `grounded_entities` once M30.6 lands.

**How recent-turn grounding works, initially:** exactly as today — `query_context.conversation`'s existing pronoun/reference-resolution prompt guidance is reused verbatim inside the Decision Engine's prompt (not reinvented) until the generalized context resolver (M30.6) makes it deterministic for capability-specific references.

**Workflow continuation state:** `active_pointer.kind = "awaiting_clarification_answer" | "paused_workflow" | "pending_approval"` is a direct rename/projection of state `orchestrator.py` already tracks (`session.active_workflow`, `ApprovalStore`'s pending records) — no new persisted field in M30.1; a real, dedicated field is only added when M30.6 needs to distinguish these three cases more precisely than today's ad hoc checks do.

**Connection/availability truth:** never duplicated — Turn State's `capability_summaries` is a read-through projection of `CapabilityFeasibility`/`connection_status.py`, computed fresh every time, never cached or copied into a second source of truth.

---

## 3. Capability Directory migration

**Do not rewrite every capability. Wrap first, merge later, per capability family:**

| Family | Adapter | What it exposes initially | What's deferred |
|---|---|---|---|
| **Legacy capabilities** (`capabilities_registry.json` entries: office drafting, memory, system performance, file conversion, web search, legacy `gmail_search`) | A thin `LegacyDirectoryAdapter` wrapping `CapabilityRegistry`/`CapabilityFeasibility` | identity, summary, availability, permissions, approval/risk (all already computed by `CapabilityFeasibility`) | Per-action schemas (legacy capabilities have never exposed one to the model — added only if/when a specific capability needs `missing_parameter` to be distinguishable, not required for every legacy tool on day one) |
| **M27 multi-action capabilities** (Gmail) | A thin `MultiActionDirectoryAdapter` wrapping `MultiActionCapabilityRegistry` | identity, summary, **and** `check_availability()` pulled forward to summary time (closing Stage 1 §11.6) | Nothing — M27's own shape already has everything else the Directory needs (actions, schemas, grounding via `CapabilityContextResolver`) |
| **Learned skills** | No directory entry at all | — | Explicitly not migrated into the Directory — per Stage 2 §12, these become a Turn State reference field, never a capability |
| **Reusable workflows/procedures** | A new, small `ProcedureDirectoryAdapter` | identity, summary, a fixed ordered `actions` list (ported from `WorkflowPlanner`'s existing task-type templates, inventoried first) | Dynamic/ad hoc multi-step plans are NOT procedures — those stay `mode=multi_action` proposals, not directory entries |
| **Connected services** (Gmail/Drive OAuth) | Unchanged — `connection_status.py` remains the sole source of connection truth, read by both adapters above | — | — |

**Canonical fields, and which adapter currently supplies which (progressive — not everything needs to be non-null on day one):**

| Field | Legacy adapter | Multi-action adapter | Procedure adapter |
|---|---|---|---|
| identity | ✅ | ✅ | ✅ |
| summary/affordance | ✅ | ✅ | ✅ |
| actions/procedures | ⚠️ (bare capability name only, no sub-actions) | ✅ | ✅ (fixed sequence) |
| parameter requirements | ❌ initially | ✅ | ✅ (inherited from steps) |
| availability | ✅ | ✅ (pulled forward, see above) | derived from constituent steps |
| connection requirement | ✅ | ✅ | derived |
| permission requirement | ✅ | ✅ | derived |
| approval/risk metadata | ✅ | ✅ | derived (any step requiring approval makes the whole procedure approval-required) |
| execution handler/reference | ✅ (`ToolDispatcher`) | ✅ (`MultiActionExecutor`) | ✅ (chain through Execution Engine) |
| result schema | ❌ initially | ✅ | derived |
| grounding metadata | ❌ initially | ✅ | derived |
| health/status | ⚠️ (via `CapabilityFeasibility`'s connection check only, no independent health signal) | ⚠️ (same) | derived |

Gaps marked ❌/⚠️ are **explicitly acceptable at M30.2** — they do not block shadow mode or even controlled canonical execution for the capabilities that already have full coverage (Gmail via M27, and any legacy capability whose `missing_parameter` distinction isn't yet needed). They are closed incrementally, per capability, not as a blocking prerequisite.

---

## 4. Decision Engine migration

Phases refined from the request's own sketch, kept reversible at every step:

**Phase A — Shadow Observation (M30.3).** `UriOrchestrator` remains fully authoritative, unchanged. A new `DecisionEngine.decide(turn_state)` call runs **in parallel**, its output logged (§5), never read by anything that affects the response. Feature flag: `enable_decision_engine_shadow` (default off).

**Phase B — Decision Comparison (M30.4).** An offline/async comparison job reads shadow logs and classifies agreement/disagreement (§5's `disagreement_classification`) between the old path's actual outcome and the new contract's proposed `mode`/`capability`. No behavior change; this phase produces the evidence Phase C's go/no-go decision needs.

**Phase C — Selected Traffic / Feature Flag (M30.5–M30.6).** `enable_decision_engine_live` gates the new path to being authoritative for a **narrow, explicitly listed** capability subset first (e.g. Gmail multi-action + `remember_fact` disclosure, the two capabilities Stage 1's live traces most directly exercised) — every other capability still resolved by the old priority chain. Expand the list only as each addition's own Layer 3 tests (§13) pass.

**Phase D — Canonical Default (M30.8).** `enable_decision_engine_live` defaults on for all capabilities; the old five-mechanism priority chain becomes the fallback, invoked only when the Decision Engine itself is unreachable or returns a malformed/rejected contract (mirroring exactly `capability_planner.py`'s demoted role, §1).

**Phase E — Retirement (M30.10).** Once a full milestone's worth of Phase D production evidence shows the fallback path is rarely/never exercised for reasons other than genuine model unavailability, the old mechanisms' *decision* code (not their reused execution/registry code) is deleted.

Every phase transition is a **flag flip**, reversible by flipping it back — never a code deletion until Phase E, and Phase E itself is evidence-gated, not calendar-gated.

---

## 5. Shadow-mode evidence

Logged per turn during Phases A–C, **privacy-safe by construction**:

| Field | Included | Notes |
|---|---|---|
| User message | **Hashed/length-bucketed, not verbatim** | Full text is available in the existing audit trail already, under its own existing access controls — shadow logs do not duplicate that separately-governed store |
| Turn State summary | Yes, structural only (which sections were populated, capability ids considered) | Never raw memory/graph content — field presence, not field value |
| Old-path decision (tool_name/plan status) | Yes | Already non-sensitive metadata |
| New Brain Decision Contract | Yes, in full (`mode`, `capability`, `actions` names, `confidence`, `reason`) | `actions[].inputs` values redacted/length-bucketed the same way user text is |
| Selected mode / capability / actions | Yes | — |
| Clarification decision | Yes, the fact and the missing-field name, not necessarily full question text | — |
| Unsupported decision | Yes | — |
| Connection/availability result | Yes (already non-sensitive, e.g. `gmail: usable=false`) | — |
| Approval requirement | Yes | — |
| Execution outcome | Yes, status only (success/failure/partial), not raw tool output content | — |
| Final response path (which mode actually executed) | Yes | — |
| Disagreement classification | Yes — a small enum: `agree`, `old_only_executed`, `new_would_have_executed_differently`, `new_more_conservative`, `new_less_conservative` | This is the actual Phase B evidence artifact |

**Never logged:** credentials/tokens, message bodies verbatim, attachment content, raw memory/graph node values, anything `security_guards.looks_like_credential_value` would flag.

---

## 6. Deterministic gate integration — order and reuse

| Order | Gate | Reuses | New code needed |
|---|---|---|---|
| 1 | Capability Directory availability gate | `CapabilityFeasibility` (legacy) + M27's `check_availability()` (pulled forward, §3) | A thin merge function only — **no duplication of either's logic** |
| 2 | Completeness / missing-parameter gate | `ActionSchema.validate()` (already exists, `uri_core/capabilities/base.py`) — generalized to legacy capabilities too, which today have no schema to validate against | Per-legacy-capability schemas, added incrementally (not required for every capability at once, §3) |
| 3 | Unsupported gate | `CapabilityDiscoveryEngine.discover_capabilities()` relevance scoring (already exists, M27) | A threshold/decision wrapper only |
| 4 | Connection/precondition gate | `connection_status.py` (already exists) | None — same gate as #1's underlying data |
| 5 | Permission gate | `CapabilityResolver.is_allowed()` (already exists, generalized for M27 via the legacy-alias table in `multi_action_dispatch.py`) | None |
| 6 | Approval gate | `ApprovalGate`/`ApprovalStore` (already exists, unchanged) | None |
| 7 | Execution/result validation | `real_tool_status()` (`dispatcher.py`, already exists) + `MultiActionExecutor`'s own status normalization | A shared wrapper reconciling the two existing status vocabularies |

**No gate in this list is a new decision-making mechanism** — every one is an existing, already-tested piece of logic, reused and in most cases merely *reached from one more call site* than before. This is the direct implementation of Stage 2's "propose, never trust" principle without inventing new authorization logic.

---

## 7. Workflow continuation migration

The concrete case named in the request — "What student roll number?" → "B250012CS" must continue, not restart — maps directly onto `mode=workflow_continuation`:

- **Pending interaction state:** `active_pointer` (§2), populated the moment a `clarification` or `approval_required` outcome pauses a turn — already exists in substance (`session.active_workflow_question`), just promoted to a first-class, always-checked Turn State field instead of something `_apply_clarification_pause` sets ad hoc.
- **Required missing fields:** carried in `active_pointer.missing_field` (a direct projection of the Decision Contract's own `clarification.missing_field`, §Stage 2 §5) — so the continuation check knows *what* answer is expected, not just *that* one is.
- **Continuation matching:** deterministic, not model-guessed as the sole signal — if `active_pointer.kind != "none"` AND the new message is short/doesn't itself look like a fresh, well-formed goal (reusing the existing `interaction_signal`/`MISSING_INFORMATION` heuristic already in `model_reasoning_adapter.py`, generalized), the Decision Engine is told this is a continuation candidate and the deterministic layer treats a `workflow_continuation` proposal as pre-corroborated; a `conversation`/fresh-goal proposal against an active pointer still requires the topic-change check below to agree before being honored.
- **Expiry/cancellation:** an `active_pointer` gets a bounded lifetime (reusing whatever session-expiry convention already exists for `session.active_workflow`) and is explicitly cleared on a real topic change (below) or an explicit user cancellation — never silently forgotten mid-session, never silently honored indefinitely across an unrelated topic.
- **Topic-change behavior:** the same deterministic recency check named in Stage 2 §9 (goal-continuity comparison) runs before honoring `workflow_continuation` — if the new message is clearly a different goal, `active_pointer` is cleared and the message is treated as fresh, directly satisfying "newest user intent wins unless explicitly continuing" (mandatory scenario 11).
- **Stale-workflow prevention:** the same expiry mechanism above, plus (once M30.8 lands) the Decision Engine's own `confidence` field — a low-confidence `workflow_continuation` proposal against a very old `active_pointer` is a candidate for an explicit "still working on X?" check rather than silent, indefinite continuation.

---

## 8. Graph Intelligence migration

**Graph Intelligence is never exposed as a Brain-facing capability at any point in this migration** — it has no Capability Directory entry (§3 explicitly excludes it), consistent with Stage 2 §10.

- **Canonical ingestion events:** exactly M23's own original design intent, finally connected to a real caller — (1) `Fact.verify()` called with a real, accountable, non-model actor at the point a fact is genuinely confirmed by a human/administrative process (not by the model); (2) `MemoryStore.confirm()` called both for today's immediate `user_provided` disclosures (already flows correctly) and — once M30.9 wires it — for a passive candidate a user explicitly confirms via the existing review UI.
- **What facts/events qualify:** unchanged from M23's own scope — `VERIFIED`-status facts, `user_confirmed`/`user_provided` memory entries only, never a `pending_confirmation` entry.
- **What runtime component writes to graph:** unchanged — `graph_ingest.py`'s existing `ingest_fact`/`ingest_memory_entry`, called from the same two call sites (`Fact.verify()`'s new caller, `MemoryStore.confirm()`'s existing caller) rather than a new ingestion path.
- **What retrieves from it, and when:** Turn State's `graph_context` field (§2, deferred to M30.9), populated only when the always-present tier doesn't already answer the goal and the goal references entities the graph might know about — never on every turn.
- **How graph-derived context enters Turn State:** the existing `graph_engine.graph_self_context()` call, already wired into `query_context.py` today, is redirected to populate Turn State's `graph_context` field instead (or in addition to, during the overlap window, §2) — the bounded, non-authoritative envelope shape is unchanged.
- **Privacy/consent boundaries:** unchanged — `ingest_memory_entry` already re-checks `is_eligible_for_personalization` itself (defense in depth, M23's own existing discipline); nothing in this migration weakens that.
- **Deduplication with durable memory:** the graph is a *derived, secondary* representation of the same underlying `MemoryEntry`/`Fact` records, not a competing source — Turn State's precedence (§9) already places `durable_memory_relevant` ahead of `graph_context`, so a fact known both ways is never presented twice with conflicting weight; the graph only ever adds *relationship* information the flat memory list doesn't carry (e.g. "connected to Y"), not a duplicate of the fact's content itself.

**M28 relationship, explicit:** wiring `MemoryStore.propose()` to a real caller (the actual content of the M28 plan) is **required** for the passive-candidate half of graph ingestion to ever fire — see §16.

---

## 9. Memory / context migration

**Precedence — Stage 2's, adopted verbatim (no deviation found necessary):**

```
latest user turn
  > recent conversation turns
  > this turn's own execution/grounded results (attempt_history)
  > active session/workflow state (active_pointer)
  > durable memory (confirmed only)
  > graph-derived context
```

This already satisfies the request's own example ("latest turn > active workflow/action context > recent conversation > relevant session facts > relevant retrieved durable memory") with one refinement carried over from Stage 2: **this turn's own real execution results outrank even active session/workflow state**, because a result that just happened is stronger evidence than a pointer describing what was merely *expected* to happen — this ordering is deliberate, not an oversight, and is unchanged from Stage 2 §9.

**Stale-memory prevention, concretely:** the deterministic recency/topic-change check (§7) is the single mechanism enforcing this precedence at runtime, not prompt wording alone — consistent with this session's own direct lesson (a prompt-only instruction was not reliably followed; a deterministic check was needed).

**M28 (passive memory candidates), evaluated against this architecture, explicit verdict: ABSORB, do not implement standalone first.** Building M28 against today's orchestrator would wire a new extraction call into exactly the fragmented decision surface this whole migration exists to remove — it would become a sixth competing mechanism if built before Turn State/Decision Engine exist, or dead weight to rewire afterward if built independently in parallel. M28's actual scope (a passive-candidate classifier + dedup/supersede logic against `MemoryStore`) is **folded into M30.9** as the concrete mechanism that finally gives Graph Intelligence (§8) and durable memory beyond explicit disclosure a real, live data source — implemented once, against the canonical loop, not twice.

---

## 10. Response-drafting ordering

**Unchanged in mechanism, clarified in position:** `_draft_narrative_safely`'s additive-only, claim-consistency-validated discipline is retained exactly as today (Stage 2 §1 principle 4, §16 "KEEP unchanged"). What changes across this migration is **what precedes it** — today, response drafting is called from roughly a dozen different branch points scattered through `orchestrator.py`'s ~300-line decision block (Stage 1 §3); under the canonical loop it is called from exactly **one** place, after the flat mode-dispatch's execution step (or immediately, for `mode=conversation`/`unsupported`, which have no execution step). This directly enforces "generic response drafting must never pre-empt a valid executable action" structurally (there is only one call site, and it is always downstream of the decision+execution steps) rather than by convention across a dozen call sites as today.

---

## 11. Failure / fallback migration

Each state below gets its own response template family from the first phase it's reachable in — **none collapse into generic clarification**, per Stage 2 §15:

| Failure | Handling |
|---|---|
| Invalid Brain Decision Contract (malformed JSON, unknown mode, missing required field) | Deterministic parse/validation rejection → falls back to the demoted `capability_planner.py` path (§1), logged as a shadow-mode disagreement (§5) during Phases A–C, as a real fallback-invocation metric during Phase D |
| Model timeout / provider unavailable | `ModelRouter`'s existing health/fallback mechanism (unchanged) → if no provider answers at all, falls back the same way as "invalid contract" above — never a fabricated result (mandatory scenario 12) |
| No capability match | `unsupported`, per the Unsupported Gate (§6, gate 3) |
| Unsupported | Own honest template (Stage 2 §15) |
| Disconnected | Own honest template naming the real connection gap |
| Missing parameter | Own honest template naming the specific missing field (structurally distinct from disconnected/unsupported per the governing decisions, §6 gate 2) |
| Approval required | Existing `ApprovalGate`/`ApprovalStore` pending-decision flow, unchanged |
| Permission denied | Own honest template, distinct from disconnected (authorization vs. connection, Stage 2 §15) |
| Tool execution failure | Own honest template from `real_tool_status()`'s real error, never silently reported as success |
| Partial result | Own honest template showing the real evidence produced before a chain halted |
| Stale continuation | Handled by §7's topic-change check — `active_pointer` cleared, message treated as fresh rather than forced into a continuation that no longer fits |
| Model provider unavailable | Same as "model timeout" above |

---

## 12. Model strategy during migration

- **Structured-output validation:** every Decision Contract is JSON-schema-validated before any deterministic gate sees it (reusing the same "reject unless it parses and every key is the right type" discipline `provider_semantic_interpreter.py`/`ModelReasoningGateway.validate_proposal()` already apply today).
- **Retry/repair behavior:** one bounded retry with a short "your last response didn't match the required shape" repair prompt (a narrow, mechanical retry — not a new reasoning round-trip) before falling back.
- **Invalid decision handling:** falls back to `capability_planner.py` (§1, §11) — never silently retried indefinitely, never silently treated as `mode=conversation` by default (that would risk masking a real actionable request as small talk).
- **Deterministic gate rejection:** a gate rejecting/downgrading a proposed mode (e.g. a claimed `unsupported` the Unsupported Gate disagrees with) is not an error — it's the architecture working as designed (Stage 2 §1 principle 2); logged, not treated as a failure requiring fallback.
- **Model escalation criteria:** exactly Stage 2 §13's policy — two consecutive `confidence: low` decisions for the same goal, a `multi_action` proposal above a step-count threshold, or two consecutive gate/model disagreements — routed through the existing `ModelRouter`, no new plumbing.
- **Fallback behavior:** qwen3:14b (or whatever local model is active) handles the common case throughout; escalation is the exception path, not the default; correctness never depends on escalation actually firing, only quality does (Stage 2 §13's own explicit invariant).

---

## 13. Test strategy

**Layer 1 — Component (existing unit tests, e.g. `test_capability_planner.py`, `test_multi_action_capabilities.py`, `test_provider_semantic_interpreter.py`):** kept running unchanged throughout every phase — they continue proving each individual mechanism's own correctness in isolation, exactly as today. None are deleted until the mechanism they test is actually retired (§1, §17).

**Layer 2 — Integration (new, added incrementally per milestone):** `TurnStateProjector` correctness (M30.1), Capability Directory adapter correctness for each family (M30.2), Decision Engine schema validation + gate interaction (M30.3–M30.6) — these prove the new *components* work together, with everything upstream/downstream faked, mirroring this repository's own existing convention (e.g. `test_orchestrator_pre_execution_sanity_check.py`'s fake-gateway pattern).

**Layer 3 — Canonical agent-loop behavior (new, mandatory from M30.5 onward):** a real message through `/ask` to a grounded, real response — no mocked orchestrator internals. **No future capability is considered integrated without a Layer 3 test**, per the request's own explicit rule; this becomes a standing acceptance criterion for every capability added after M30.5, not only for this migration's own components.

**Existing tests' migration:** Stage 1 §3/§4's own traced regressions (`test_orchestrator_decision_priority.py`, `test_orchestrator_user_interaction_hooks.py`, `test_m25_clarification_pause.py`, `test_orchestrator_pre_execution_sanity_check.py`) are **not deleted or rewritten during shadow/comparison phases (A–C)** — they continue proving the OLD path's own correctness, which must remain intact until Phase D. They are only revisited once their own mechanism is retired (§1's RETIRE/DEMOTE rows), at which point each is either deleted (if it tested a decision path that no longer exists) or re-targeted at the new equivalent (if it tested a behavior that must still hold, e.g. "a genuinely incomplete request still gets clarification").

---

## 14. Mandatory acceptance scenarios — exact expected behavior

1. **"How many unread emails do I have?" (Gmail connected)** → `mode=single_action` or `multi_action`, capability=gmail → real `list_labels`/`search_messages` execution → grounded, real count in the response. (Already live-verified working via the legacy path this session; must remain true once the Decision Engine is authoritative for this capability, M30.5 onward.)
2. **Same request, Gmail disconnected** → Directory availability gate (§6, gate 1) shows `usable=false` before the Decision Engine even proposes execution → `disconnected` failure state (§11) → a real connection-guidance message, never a generic "no access."
3. **"How many unread emails do I have and is anything important?"** → `mode=multi_action`, `actions=[list_labels, search_messages]`, both pre-planned, executed back-to-back with no re-entry (Stage 2 §8/§18 example B).
4. **"Find the student." → "B250012CS."** → turn 1: Directory shows `extract_student_records` usable, schema validation (gate 2) finds a required identifier missing → `missing_parameter`/`clarification`, `active_pointer` set with `missing_field="roll_number"`. Turn 2: continuation match (§7) confirms this short, identifier-shaped message answers the pending field → `mode=workflow_continuation` → the original capability executes with the now-complete input.
5. **"Schedule a recurring job search," no scheduler exists** → Unsupported Gate (§6, gate 3) confirms no Directory entry plausibly matches → `unsupported`, honest message, no clarification loop, nothing executes.
6. **"I work at NIT Sikkim."** → the deterministic disclosure hint (carried over from this session's fix, relocated into Turn State per Stage 2 §18 example F) plus the Decision Engine's own extraction agree → `single_action`, capability=`remember_fact` → saved, confirmed in the response — never routed to `web_search` (the hardcoded-keyword regression Stage 1 §9 case E traced is structurally impossible once `capability_planner.py` is demoted to gate-only duty, §1).
7. **"Find latest insurance email." → "Read that one." → "Check its attachment."** → turn 1 grounds a `message_id` in `grounded_entities`; turn 2's referring expression resolves against it (generalized `CapabilityContextResolver`, §1) to a real `read_message` call; turn 3 resolves the attachment reference against turn 2's real result, never inventing an id.
8. **"Prepare a reply but do not send it."** → `mode=single_action` or `multi_action` naming `create_draft`, `requires_approval=true` read directly from the Directory (never proposed by the model) → approval-pending state, drafted content shown, **no send action exists in this chain at all** — not merely "not executed this time," structurally absent from the proposal.
9. **"Convert this PDF to Word."** → `single_action`, capability=`convert_document`, executes exactly as it does today (unchanged legacy mechanics, §1).
10. **"Do you think changing careers is sensible?"** → Directory summaries show no meaningful overlap → `mode=conversation` → no capability considered for execution, no false action claim possible (Stage 2 §18 example I).
11. **Topic switch while another workflow is pending** → the topic-change check (§7, §9) clears `active_pointer` and treats the new message as a fresh goal — newest intent wins, exactly as the scenario requires, unless the new message genuinely continues the pending one.
12. **Provider failure** → `ModelRouter`'s existing fallback/health tracking engages; if no provider answers, the deterministic fallback (§11, §1's demoted `capability_planner.py`) produces an honest "could not reason about this right now" outcome — never a fabricated result.

---

## 15. Feature flags

| Flag | Introduced | Default | Governs |
|---|---|---|---|
| `enable_turn_state_projection` | M30.1 | on (read-only, no behavior change) | Whether `TurnStateProjector` runs at all (kept on once introduced — it's inert until read) |
| `enable_capability_directory` | M30.2 | on (read-only) | Whether the unified Directory interface is constructed (inert until read) |
| `enable_decision_engine_shadow` | M30.3 | off | Whether the Decision Engine runs in parallel, logged only |
| `enable_decision_engine_live` | M30.5 | off, then a scoped capability allowlist, then on | Whether the Decision Engine's output is actually acted on, and for which capabilities |
| `enable_workflow_continuation_mode` | M30.6 | off until Layer 3 tests for scenario 4/11 pass | Whether `active_pointer`-based continuation matching is honored |
| `enable_graph_ingestion_live` | M30.9 | off | Whether `Fact.verify()`/`MemoryStore.propose()`-confirm actually fire |
| `enable_legacy_decision_fallback` | M30.8 | on (cannot be turned off before Phase E) | Whether the demoted `capability_planner.py`/old priority chain remains reachable as a fallback |

Every flag above is a simple boolean read at one call site — none require a data migration to flip back off.

---

## 16. Rollback strategy

| Phase | Feature flag | Recovery checkpoint | Rollback procedure | Regression baseline | Exit criteria |
|---|---|---|---|---|---|
| M30.1 Turn State | `enable_turn_state_projection` | Pre-M30.1 `git` state | Flip flag off; `TurnStateProjector` module simply isn't called | Full existing suite green, zero `orchestrator.py` behavior diff | Projector output matches hand-traced expectations for 10+ real recent-conversation fixtures |
| M30.2 Directory | `enable_capability_directory` | Post-M30.1 | Flip flag off | Same as above, plus Directory adapter unit tests green | Directory summaries match `CapabilityFeasibility.snapshot()` + M27 summaries exactly, for every registered capability |
| M30.3 Decision Engine shadow | `enable_decision_engine_shadow` | Post-M30.2 | Flip flag off; shadow logging simply stops | No production behavior change possible in this phase by construction | N weeks of shadow logs collected, Phase B comparison job runs cleanly |
| M30.4 Decision comparison | (uses M30.3's flag) | Post-M30.3 | N/A — offline analysis only | — | Disagreement rate and category breakdown reported; go/no-go decision made explicitly, not by default |
| M30.5–6 Controlled canonical execution | `enable_decision_engine_live` (allowlist) | Post-M30.4, per-capability | Remove capability from allowlist, or flip flag fully off | All Layer 1–3 tests for the allowlisted capabilities green | Each allowlisted capability's mandatory acceptance scenario (§14) passes live, repeatedly, with zero regressions on its own existing test suite |
| M30.7 Workflow continuation | `enable_workflow_continuation_mode` | Post-M30.6 | Flip flag off; falls back to today's ad hoc clarification-only behavior | Scenarios 4 and 11 (§14) pass | Both scenarios pass on real, not faked, model output across repeated runs |
| M30.8 Canonical default | `enable_decision_engine_live` (global on) | Post-M30.7, tagged release | Flip flag off globally — full return to the pre-migration priority chain, which still exists and still works | Full regression suite green; all 12 mandatory scenarios (§14) passing live | Fallback invocation rate low and explained (genuine model unavailability only) over a real observation window |
| M30.9 Graph/memory live wiring | `enable_graph_ingestion_live` | Post-M30.8 | Flip flag off; ingestion calls simply don't fire, graph stays empty as it is today (no regression, just no improvement) | Existing graph/memory test suites green | Real ingestion observed for both `Fact.verify()` and passive-candidate-confirm paths in a real session |
| M30.10 Retirement | N/A — code deletion, the one irreversible step | Post-M30.9, extended observation window | **This is the only phase without a flag-flip rollback** — it requires a full regression suite + re-verification instead | Full suite green immediately before deletion | Fallback path (§4 Phase D) shown, over a real production/observation window, to be reached only for genuine model-unavailability reasons — never for a decision-quality reason |

**No old routing authority is retired (M30.10) until this table's own exit criteria are met** — this is the direct, explicit answer to "do not retire old routing authority until canonical-path evidence is strong enough."

---

## 17. Milestone sequence

Derived from the architecture and the dependency chain above, not copied from the request's own example numbering:

| ID | Objective | Files/modules likely affected | Dependency | Tests | Shadow/live | Acceptance gate | Rollback point |
|---|---|---|---|---|---|---|---|
| **M30.0** | Confirm the legacy Groq-shaped `semantic_interpreter.py` has zero live production callers (one-time check, not a build task) | none (read-only investigation) | none | n/a | n/a | Confirmed unused, or a real caller found and documented | n/a |
| **M30.1** | `TurnStateProjector` — read-only projection of existing stores into the initial Turn State schema (§2) | new `turn_state.py`; no existing file modified | M30.0 | Layer 2 (projector correctness) | shadow (inert until read) | §16 row M30.1 | Flag off |
| **M30.2** | Capability Directory — `LegacyDirectoryAdapter`, `MultiActionDirectoryAdapter`, `ProcedureDirectoryAdapter` (after inventorying `WorkflowPlanner`'s templates) | new `capability_directory.py`; reads `CapabilityFeasibility`, `MultiActionCapabilityRegistry`, `WorkflowPlanner` (read-only) | M30.1 | Layer 2 | shadow | §16 row M30.2 | Flag off |
| **M30.3** | Decision Engine — new prompt/schema, transport reused from `model_reasoning_adapter.py`; Phase A shadow logging (§5) | new `decision_engine.py`; `model_reasoning_adapter.py` (transport reuse, additive) | M30.1, M30.2 | Layer 2 (schema validation, retry/repair) | shadow | §16 row M30.3 | Flag off |
| **M30.4** | Decision comparison harness + Phase B analysis (offline) | new, small analysis script/job; no production module | M30.3 | n/a (analysis, not a test suite) | shadow-derived, offline | §16 row M30.4 | N/A (no production change) |
| **M30.5** | Deterministic gates (§6), wired to the Decision Engine's output, NOT yet authoritative | new thin gate-orchestration module; reuses `CapabilityFeasibility`, `ActionSchema.validate`, `CapabilityDiscoveryEngine`, `CapabilityResolver`, `ApprovalGate` | M30.3 | Layer 2 (gate interaction) | shadow | §16 row M30.5 (folded with M30.6) | Flag off |
| **M30.6** | Controlled canonical execution — `enable_decision_engine_live` allowlist (Gmail + `remember_fact` first, per Stage 1's own most-traced cases); generalized `CapabilityContextResolver`; Execution Engine wrapper unifying `ApprovalGate`+`MultiActionExecutor` | `orchestrator.py` (additive: new call site behind the flag, old path untouched), `capability_context_resolver.py` (generalized) | M30.5 | Layer 1 + 2 + **3** (mandatory from here on) | **live, allowlisted** | §16 row M30.5/6; mandatory scenarios 1, 2, 3, 6, 9, 10 passing live for allowlisted capabilities | Remove from allowlist |
| **M30.7** | Workflow continuation — `active_pointer` promoted to first-class, topic-change/stale-context checks | `orchestrator.py` (the clarification-pause call sites consolidated to one), `state.py` (Session field promotion) | M30.6 | Layer 3 (scenarios 4, 11) | live, allowlisted | §16 row M30.7 | Flag off |
| **M30.8** | Canonical default — `enable_decision_engine_live` on globally; old priority chain demoted to fallback-only; `capability_planner.py`/learned-skill direct-plan authority removed from the primary path | `orchestrator.py` (the ~300-line priority block replaced by flat dispatch); `capability_planner.py` (role narrowed); `skill_memory.py` call site (direct-plan shortcut removed) | M30.7, full regression green | Full Layer 1+2+3 | **live, default** | §16 row M30.8; all 12 mandatory scenarios (§14) passing | Flag off — full return to pre-migration behavior |
| **M30.9** | Graph Intelligence + memory live wiring — absorbs M28's actual scope (§9, §16); `Fact.verify()`/`MemoryStore.propose()`→confirm real callers | `graph_ingest.py` call sites (new callers only, no logic change), `user_memory.py` call sites, a new passive-candidate classifier module | M30.8 (needs Turn State's precedence rules live to be safe) | Layer 2 + 3 | live | §16 row M30.9 | Flag off |
| **M30.10** | Retirement — delete the old five-mechanism priority code, `WorkflowPlanner`'s decision role, the undocumented M27-trigger shape; `orchestrator.py` net shrink confirmed by `wc -l` | `orchestrator.py`, `workflow_planner.py`, `workflow_capability_router.py`, `capability_planner.py` (further narrowed or removed), `multi_action_dispatch.py` (folded fully into Execution Engine) | M30.9, extended observation window | Full suite; deleted tests confirmed to correspond only to retired mechanisms | live | §16 row M30.10 | **Irreversible — gated by the strictest criteria in this document** |

---

## 18. Existing-work reconciliation

| Effort | Disposition |
|---|---|
| **M27 (multi-action live integration)** | **Superseded as a standalone plan; its built code is retained and repurposed.** The already-implemented `MultiActionExecutor`/`CapabilityDiscoveryEngine`/`CapabilityContextResolver`/`MultiActionDispatch` are exactly the raw material M30.2/M30.6 wrap and fold into the Execution Engine — nothing is thrown away, but M27's own plan document (a direct-wire approach with no shadow phase) is no longer the path forward; this migration's phased approach supersedes it. |
| **M28 (passive memory candidate pipeline)** | **Absorbed into M30.9, not implemented standalone first** (§9, §16) — its scope is real and needed, but building it against today's orchestrator would add a sixth competing decision mechanism or require an immediate rewrite once Turn State/Decision Engine land. Its own plan document remains a valid *design reference* for M30.9's implementation, not a separate execution track. |
| **M29 (Brain Decision Contract plan)** | **Superseded by Stage 2/Stage 3 directly.** M29 was this same investigation's own preliminary draft, written before the corrected connection-awareness diagnosis (Stage 1 §1's own correction) and before the full canonical-loop design existed. Its core insight (one structured decision contract) is fully carried forward into Stage 2 §5 and this plan's M30.3 — M29 itself should be marked superseded in its own `_STATE.md`, not implemented as a separate track. |
| **Accepted UI work (M26 dashboard shell, already implemented in `uri_ui/`)** | **Continues fully independently.** It is a client consuming existing REST endpoints; nothing in this migration changes those endpoints' wire contracts in any phase through M30.9 (Turn State/Decision Engine are entirely server-side, internal to `orchestrator.py`). If M30.10's retirement work ever needs an endpoint shape change, that would be called out explicitly at that time, not assumed here. |
| **Graph Intelligence (M23)** | **Continues as designed; its live-wiring becomes this plan's own M30.9**, not a separate effort — it was already correctly built (Stage 1's own audit called its engineering sound); it only needed a real caller, which this migration provides at the point memory/fact confirmation becomes real. |

**No architectural work is implemented twice under this plan** — every prior effort's real, tested code is reused; only *decision authority* (which of them gets to unilaterally decide) changes.

---

## 19. Risks

- **Shadow-mode cost:** Phases A–C run the Decision Engine as pure overhead (an extra model call, logged and discarded) for as long as evidence-gathering takes — a real, deliberate cost paid for migration safety, not a design flaw.
- **Directory adapter drift:** two physical backing stores (legacy + M27) wrapped by one interface risk silently diverging in shape over time if only one side is updated when a new field is needed — mitigated by Layer 2 tests asserting both adapters satisfy the same interface contract, not by discipline alone.
- **`active_pointer` continuation false-positives:** a short message that happens to look like an answer to a stale pending question, but isn't, could be wrongly continued — the expiry + topic-change check (§7) is the mitigation, but its false-positive/negative rate is unmeasured until M30.7's real Layer 3 evidence exists.
- **Retirement (M30.10) is the one genuinely irreversible step** — every prior phase can be flag-flipped back; this one requires the strongest evidence bar in the plan (§16) precisely because of that asymmetry.
- **`WorkflowPlanner` template inventory (M30.2) may surface task types with no clean procedure/multi-action equivalent** — Stage 2 §19 already flagged this; if found, the affected task type's retirement is deferred past M30.10 until a real replacement exists, rather than silently dropping coverage.
- **Escalation-policy thresholds (§12) are unmeasured** — wrong thresholds risk either cost (over-escalation) or unresolved quality gaps (under-escalation); this is explicitly a tuning task for M30.6 onward, not solved by this plan.

---

## 20. Final retirement criteria (M30.10 gate, stated once more explicitly)

The old five-mechanism priority chain, `WorkflowPlanner`'s decision role, and `capability_planner.py`'s first-mover role are only deleted when **all** of the following hold simultaneously:

1. `enable_decision_engine_live` has been globally on (Phase D) for a real observation window with production traffic.
2. All 12 mandatory acceptance scenarios (§14) pass live, repeatedly, not just once.
3. The demoted fallback path (§4 Phase D) is invoked, over that window, only for genuine model-unavailability/malformed-output reasons — never because the Decision Engine produced a worse decision than the old path would have.
4. Full Layer 1+2+3 regression suite is green immediately before deletion.
5. `WorkflowPlanner`'s template inventory (§17 M30.2, risk §19) shows no orphaned task-type coverage.

Any one of these failing holds M30.10 open; none of the earlier milestones (M30.1–M30.9) are blocked by this gate — they each stand on their own rollback criteria (§16).

---

*Stage 3 complete. No implementation, migration code, routing changes, prompt changes, or capability wiring were made as part of this plan, per the User's explicit instruction. Stage 4 (implementation) is not authorized and does not begin until this plan is reviewed.*
