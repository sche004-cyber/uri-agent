# URI Agent Loop — Root Cause Architecture Audit

**Stage:** 1 (diagnosis only — no implementation, no migration code, no prompt changes, no routing patches)
**Author:** Claude (Architect / Auditor role, AO-4)
**Date:** 2026-09-12
**Method:** Direct source inspection (not documentation alone) of every module named in the request, `git log` reconstruction of the full commit history (64 commits, initial commit → current), live `/ask` traces already gathered this session, and external research on production agent architectures (cited in §10).

---

## 1. Executive diagnosis

**The core question, answered directly:** URI's decision-making loop today is not one loop — it is at least **four independent decision mechanisms that were each added to solve a real problem, and none of them replaced the one before it.** They sit side by side in `orchestrator.py`, and which one actually decides what URI does for a given message depends on an implicit, undocumented priority order between them, re-derived turn by turn from which output fields happen to be non-null. No single component "owns" the decision. Authority is fragmented across time (four milestones, M11/M13/M20/M27), not just across modules.

This is not primarily a model-weakness problem. Separated by category:

- **Model limitation (real, but secondary):** qwen3:14b does not reliably follow an added prompt instruction on its own (directly observed this session — a new "personal disclosure" prompt rule was silently ignored until backed by a deterministic regex override). This affects prompt-compliance-dependent behavior, not architecture.
- **Orchestration limitation (primary):** the turn-processing method in `orchestrator.py` computes up to five different "what should happen" candidates (a Brain single-action proposal, a Brain workflow proposal, a learned-skill match, a deterministic `CapabilityPlanner` match, and — as of M27 — a multi-action dispatch result) and picks among them with interleaved `if`/`elif` priority, not a single authoritative decision step. This is the direct, proven cause of the "URI knows how to do X but does something else" symptom class (traced live this session for two concrete cases).
- **State/context limitation (real, but narrower than first believed):** connection state for *legacy* capabilities already reaches the Brain (`CapabilityFeasibility.snapshot()` → `available_capabilities`, M20). It does **not** reach the Brain for M27's multi-action registry at discovery time, and the Brain is never told the multi-action output shape exists at all (§4, §11).
- **Capability-discovery limitation (real):** M27's `MultiActionCapabilityRegistry` is a second, parallel discovery system with no shared vocabulary with the legacy `CapabilityRegistry`/`CapabilityPlanner`. A capability can be "discoverable" by one system and invisible to the other.
- **Prompt-contract limitation (primary, and the most fixable one):** the reasoning prompt (`REASONING_SYSTEM_PROMPT`) asks the model to produce *artifacts* (`action`, `workflow`, `clarification`) rather than first classify *which of several situations this is*. This forces every caller (`orchestrator.py`) to infer the situation after the fact from which keys are non-null — exactly the shape that let a redundant clarification silently outrank an already-resolved request (found and bounded-fixed earlier this session).
- **Integration limitation (real, and structural):** M27 (multi-action Gmail) is fully built, fully tested in isolation, and was live-verified this session to be **unreachable through normal model output** — the prompt never documents its shape. M23 (Graph Intelligence) is fully built, wired end-to-end, and structurally **almost always empty** in live use because its two real ingestion triggers (`Fact.verify()`, `MemoryStore.propose()`→confirm) are themselves never invoked by any live code path. Two entire milestones are "integrated" in the sense of "the code is wired together" and "dark" in the sense of "no real data or real model behavior ever flows through them."
- **Competing planner/decision-path limitation (the deepest one):** `capability_planner.py` (deterministic keyword scoring), the Brain's own `action`/`workflow` proposal (M11), `MultiActionDispatch` (M27), and `WorkflowPlanner`/`WorkflowCapabilityRouter` (pre-M11 deterministic workflow fallback) are four separate mechanisms that can each independently decide "what capability should run," reconciled only by an ad hoc priority chain inside `orchestrator.py`'s single largest method.

**Would a frontier model fix this?** No, not by itself. A stronger model would follow the existing prompt more reliably and would be less likely to hallucinate a bad clarification — but it would still be handed the same fragmented, artifact-oriented contract, would still not know M27's proposal shape exists (the prompt doesn't document it regardless of model quality), and would still have no way to know the Graph Intelligence subsystem exists or is empty. A frontier model would make today's architecture behave *better on average*, not *coherent*. See §8 for the explicit, case-by-case argument.

---

## 2. Historical reasoning-architecture timeline

Reconstructed from `git log` (oldest → newest) and cross-checked against `docs/plans/*` and each milestone's own `_STATE.md` history log. "Owner before" = what handled this responsibility immediately prior; "replaced?" = whether the new component actually took over that responsibility or the old one kept running alongside it.

| Commit / Milestone | Component introduced | Problem it solved | Owner before | Replaced or accumulated? |
|---|---|---|---|---|
| `38587b8` Skill Evaluator/Router | `skill_memory.py`, skill router V1 | Learn from past successful task/capability pairings | Nothing (new capability) | New — but note: wired in as a **shadow path** (`7b96a5d`: "Wire Skill Router V1 into orchestrator as an audited shadow path"). This is the *first* instance of the pattern that recurs at M11, M20, and M27: introduce new decision logic in shadow/reference mode alongside the existing path, never fully replacing it. |
| `a02d0b4` / `3c7c2b8` | `ModelProvider` abstraction, `ModelReasoningGateway` wired to Ollama in **shadow mode** | Give URI a real model backend | Nothing real (pre-model, deterministic-only) | **Accumulated.** Explicitly shadow mode — computed and logged, not acted on. |
| `89169c1` Milestone 6 | `capability_registry.py`, `CapabilityPlanner` | "Capability awareness" — URI must know what it can/can't do rather than assume | Nothing (first deterministic capability-selection layer) | New — this becomes THE deterministic decision-maker for capability selection for the next 5 milestones. |
| `b967ff3` Milestone 7 | `ApprovalGate` | One enforced execution boundary (approval-required capabilities can't bypass a real user decision) | Direct `ToolDispatcher` calls | **Replaced** — this is one of the few cases in this history where the new component genuinely became the *only* path (`approval_gate.py`'s own docstring: "the ONE execution boundary this codebase should ever call"). Still true today. |
| `655c6a0` | Deterministic conversational/no-capability-required classifier | Avoid a dishonest "capability gap" message for "hello" | Fell through to `WorkflowPlanner`'s generic fallback | **New, narrow, additive** — a small, well-scoped carve-out ahead of the existing fallback, not a replacement of it. |
| `0a79817` Milestone 10A | `query_context.py` (`build_query_context`) | One unified, additive, Brain-facing context envelope | Ad hoc per-caller context assembly | **Consolidating** — this is the one clear case of convergence: every subsequent context addition (M18 experience, M20 diagnostics, M21 conversation, M22 capabilities, M23 graph) is an additive key in this *same* function, not a new parallel context path. |
| `0fcfc85`/`6738289` Milestone 11 Phase 1/2 | The Brain's own `action`/`workflow` proposal becomes a real plan (`_model_proposed_capability`/`_model_proposed_workflow`) | Let the model actually decide, not just shadow-log | `CapabilityPlanner` (deterministic-only) | **Accumulated, not replaced.** `CapabilityPlanner` is explicitly kept as "the fallback, exactly as before this milestone" (see `orchestrator.py`'s own comment at the call site). This is the moment URI's decision-making forks into two live paths (Brain proposal vs. deterministic planner) reconciled by priority order — the shape that persists, and grows, through M13, M20, and M27. |
| `4879965` Milestone 12 | "Real Brain reasoning reliably reaches execution" | Ensure the Brain's proposal isn't silently dropped | — | Hardening of the M11 fork, not a new decision path. |
| `181d7ba`/`2df41e1` Milestone 13 Part 1/2 | Pre-execution sanity check, interaction signals (`MISSING_INFORMATION`, `RESULT_NOT_ACCEPTED_OR_INCOMPLETE`, `REPEATED_CLARIFICATION_MUST_ACT`), the initial-clarification honor path | Let the Brain reconsider/ask before executing; stop infinite repeated-question loops | Nothing — action just executed once decided | **Accumulated.** This is where `_apply_clarification_pause` gets its **unconditional** priority over the deterministic planner (the exact defect found and bounded-fixed this session) — added specifically to fix one regression (a missing roll number silently overridden) without a mechanism to distinguish that case from an already-resolved one. |
| M18 (`ec261b6`) | `MemoryStore.propose()`/`confirm()`, per-user memory/learning isolation | Consent-gated durable memory, Brain-proposed facts | Nothing (memory didn't exist) | New, but **structurally unreached today**: nothing in the live orchestrator ever calls `propose()` (confirmed directly this session and independently re-confirmed by M23's own audit — see §7). |
| `66d1433` M20 | `capability_feasibility.py` (`CapabilityFeasibility`), reachable recovery, bounded research | Close the gap where a registered-but-currently-unusable capability (e.g. Gmail with no token) looked identical to a usable one | Raw `CapabilityRegistry.is_executable` (implemented/not, nothing about *right now*) | **Additive, integrated correctly** — this one genuinely closed its gap for the legacy registry. It has no equivalent for the registry M27 adds two milestones later (§11). |
| M22.3–M22.9 | Auth, roles, provider registry, `ModelRouter`, usage metering, modes/tiers, PWA | Multi-user identity, provider abstraction, cost control | — | Orthogonal to decision-making; not part of this fork. |
| M23 (`dfee5a8`) | Graph Intelligence (`graph_store.py`/`graph_engine.py`/`graph_ingest.py`/`graph_context.py`) | Structured entity/relationship context for the Brain | Nothing (flat, unlinked stores) | **Wired, but starved.** Fully integrated into `query_context` (proven by this session's own grep — `graph_self_context` is called and the result flows into the same envelope the Brain reads). Its own `_STATE.md` **already discloses**, at release time, that its primary ingestion trigger (`Fact.verify()`) has no live caller and is therefore "dormant in live production use" (§7). |
| Post-`a237b21` (this session) M27 | `MultiActionDispatch`, `MultiActionCapabilityRegistry`, `CapabilityDiscoveryEngine`, `CapabilityContextResolver`, `MultiActionExecutor` (`uri_core/capabilities/`) | Progressive, schema-based multi-action Gmail capability with a proper propose→validate→execute chain | `capability_planner.py` + `gmail_search` (a single-purpose legacy tool) | **Accumulated, and live-verified dark.** A fifth decision path, checked *before* the M11/M13 chain in `orchestrator.py`, that only activates if the model's raw JSON output happens to contain a `proposal`/`multi_action`/`selected_capability` key — a shape `REASONING_SYSTEM_PROMPT` never documents. The real Gmail fix this session went through the *legacy* path, never through M27. |
| This session, prior to Stage 1 | Bounded decision-priority fix | Stop the Brain's own unconditional clarification from silently overriding an already-resolved deterministic match | — | A **bounded patch to the symptom** (one guard clause), explicitly not a redesign — which is why this audit was requested next. |

**Direct answer to "did URI accumulate multiple decision systems rather than converging onto one":** yes, demonstrably. `query_context.py` (M10A onward) is the one clear counter-example of real convergence — every later milestone added *context* to it additively rather than building a parallel context assembler. Decision-making did the opposite: M11, M13, M20, and M27 each added a **new mechanism that can independently decide what URI does**, and none of the later ones absorbed or retired the earlier ones. `capability_planner.py` from M6 is still live and still consulted, unchanged in role, seven milestones and one major subsystem (M27) later.

---

## 3. Current real `/ask` decision path (traced against code, not docs)

Traced directly in `uri_core/core/orchestrator.py`'s `process_user_input` (the method the `/ask` route calls) this session, including two live `curl` reproductions. Line numbers as of this audit (`orchestrator.py`, 5,604 lines).

```
POST /ask (server.py)
  │  input: {session_id, text}; user_id from auth dependency
  ▼
UriOrchestrator.process_user_input(session_id, user_text, principal)
  │
  ├─ semantic_result = semantic_interpreter.interpret(user_text)      [MODEL CALL #1]
  │    provider_semantic_interpreter.py — fixed 8-key contract
  │    (goal/task_type/domain/entities/requested_output/requires_evidence/
  │    requires_clarification/suggested_next_step). Deterministic
  │    override added this session forces this contract's own fields for
  │    a recognized first-person disclosure — the ONE place in today's
  │    architecture where a model's classification is deterministically
  │    corrected rather than merely scored against.
  │
  ├─ model_reasoning = self._run_model_reasoning(...)                  [MODEL CALL #2]
  │    model_reasoning_adapter.py — REASONING_SYSTEM_PROMPT.
  │    Input: user_request, session/evidence/query_context (incl.
  │    query_context.conversation = recent turns, available_capabilities
  │    from CapabilityFeasibility, query_context.multi_action_capabilities
  │    from MultiActionDispatch.model_context — two SEPARATE capability
  │    lists), attempt_history, pending_proposal, interaction_signal.
  │    Output: {intent, facts, clarification, evaluation, action,
  │    workflow, retention_candidate} — an ARTIFACT set, not a decision.
  │
  ├─ capability_planner_plan = capability_planner.plan(semantic_result)
  │    DETERMINISTIC. Keyword/phrase scoring against the 8-key semantic
  │    contract only — never sees model_reasoning's output, never sees
  │    conversation history, never sees connection state directly (only
  │    indirectly, via whatever CapabilityFeasibility.snapshot() already
  │    filtered upstream inside model_reasoning_gateway, which this
  │    planner does not consult either — it is a fully independent,
  │    parallel classifier over the SAME semantic_result).
  │    Computed unconditionally, every turn, whether or not it is used.
  │
  ├─ model_capability_proposal = _model_proposed_capability(model_reasoning)
  │    Re-validates model_reasoning's "action" field against the
  │    executable-id allowlist (CapabilityFeasibility-derived). None if
  │    absent/invalid.
  │
  ├─ model_workflow_proposal = _model_proposed_workflow(...)   (similar, for "workflow")
  │
  ├─ multi_action_result = self.multi_action_dispatch.dispatch(model_reasoning, ...)
  │    [M27] Looks for a "proposal"/"multi_action" key in the SAME
  │    model_reasoning output REASONING_SYSTEM_PROMPT never asked for.
  │    Live-verified this session: always None in practice, because the
  │    model is never told this shape exists.
  │    IF NOT NONE → returns immediately. Short-circuits everything below,
  │    including the deterministic capability_planner_plan already computed.
  │
  ├─ IF model_capability_proposal or model_workflow_proposal_present:
  │      → optional pre-execution sanity check (a THIRD model call,
  │        M13 Part 1) → may itself return "clarification_needed" and
  │        short-circuit here too.
  │      → else: this proposal becomes `plan`.
  │  ELIF (neither present):
  │      → initial_clarification = _model_clarification(model_reasoning)
  │      → [BOUNDED FIX, this session] skipped only when semantic_result
  │        says requires_clarification=False AND capability_planner_plan
  │        is already "capability_selected" — otherwise still wins
  │        unconditionally, short-circuiting here.
  │  ELIF learned_skill (skill_memory match):
  │      → plan = learned_skill's remembered tool_name.
  │  ELSE:
  │      → plan = capability_planner_plan (the deterministic fallback,
  │        the ONLY branch where the earlier keyword-scoring computation
  │        is actually used).
  │
  ├─ IF plan.status == "capability_selected":
  │      dispatch_result = self.approval_gate.execute_tool(tool_name, ...)
  │      [DETERMINISTIC EXECUTION — the one real, enforced boundary]
  │      real_tool_status(dispatch_result) — unwraps the tool's OWN status,
  │      not just "did the Python call raise."
  │      → response["execution"], response["response"] built from REAL
  │        tool output only.
  │      → self._draft_narrative_safely(...)                [MODEL CALL, drafting only]
  │        drafts ONLY from already-decided execution/response fields —
  │        this is the one place in the pipeline that genuinely cannot
  │        invent an action; it can only phrase one that already happened.
  │      → return response.
  │
  ├─ ELIF plan.status == "planning_required":
  │      → is_conversational_no_capability_required() deterministic gate
  │        (greeting/farewell/bare self-question only) → fixed template,
  │        optionally paraphrased.
  │      → else: Brain-composed workflow attempt (M11 Phase 2, a FOURTH
  │        model-decides-the-plan path) → WorkflowExecutor.
  │      → else: WorkflowPlanner.create_workflow() (pre-M11 deterministic
  │        fallback, a FIFTH mechanism) → WorkflowCapabilityRouter → execute.
  │      → else (nothing matched anywhere): the one honest deterministic
  │        fallback message, "URI understands the request but cannot
  │        safely execute it" — NOT narrative-drafted (no model call).
  │
  └─ persist session, return response.
```

**Per-stage summary table:**

| Stage | Module/function | Model involved? | Deterministic logic? | Runtime state available? | Execution evidence returned? | Can a fallback intercept here? |
|---|---|---|---|---|---|---|
| Semantic interpretation | `provider_semantic_interpreter.py` | Yes (call #1) | Yes (this session's disclosure override) | No | No | No |
| Reasoning/proposal | `model_reasoning_adapter.py` + `model_reasoning_gateway.py` | Yes (call #2) | Validation only (allowlist) | Partial — legacy capability feasibility yes, multi-action feasibility no | No (pre-execution) | N/A |
| Deterministic plan | `capability_planner.py` | No | Yes, fully | No (keyword scoring over semantic_result only) | No | This IS a fallback |
| Multi-action dispatch | `multi_action_dispatch.py` | Reads model output, no separate call | Permission/registry checks only | Partial (registry summaries, no live connection state at summary stage) | Yes, if reached | Yes — can short-circuit everything below it |
| Pre-execution sanity check | `orchestrator.py` M13 | Yes (call #3, conditional) | Priority logic around it | Same as reasoning stage | No | Yes — can return clarification |
| Initial-clarification honor | `orchestrator.py` M13 | No (reuses call #2's output) | Yes (this session's bounded guard) | Reads semantic_result + capability_planner_plan | No | Yes — can short-circuit |
| Learned skill | `skill_memory.py` | No | Yes (match lookup) | Historical success record only | No | Reference only, re-executed via the same path below |
| Execution | `approval_gate.py` → `dispatcher.py` | No | Yes, the one real boundary | Yes (registry + connection status, for legacy) | Yes | No — this is the ground truth |
| Deterministic workflow fallback | `workflow_planner.py` / `workflow_capability_router.py` | No | Yes | Partial | Yes | This IS the fallback-of-last-resort |
| Response drafting | `response_drafting.py` via `_draft_narrative_safely` | Yes (call #4, optional) | Validation (claim-consistency) | Reads only already-decided fields | Reads it, never produces it | No — additive only |

---

## 4. Decision ownership map

**Direct answer: authority is fragmented across (at minimum) five candidates, reconciled by implicit priority order, not by design.**

1. **The Brain's own `action`/`workflow`/`clarification` output (M11/M13)** — has first priority when present and validated. Can unilaterally decide to ask a question (this session's found defect: even overriding an already-resolved deterministic match).
2. **`MultiActionDispatch` (M27)** — has priority OVER #1's downstream consumption when its narrow proposal shape is detected, but only ever fires if the Brain happens to emit an undocumented shape. In practice, live-verified: essentially never fires.
3. **`skill_memory` (learned skills)** — reference-only when #1 has nothing, consulted before the deterministic planner.
4. **`capability_planner.py`** — the original (M6) deterministic decision-maker, still fully implemented and still scored every turn, but now only the ANSWER OF LAST RESORT among four higher-priority candidates.
5. **`WorkflowPlanner`/`WorkflowCapabilityRouter`** — a SIXTH mechanism, deterministic, only reached when nothing above produced a single-capability plan; itself contains its own internal decision logic (task-type-keyed workflow templates) independent of `capability_planner.py`'s scoring.

**Where intent is interpreted more than once:** twice, unconditionally, every turn — `provider_semantic_interpreter.py` (8-key contract) and `model_reasoning_adapter.py` (the separate `action`/`workflow`/`clarification` call). They do not share a schema, are not reconciled against each other except by the ad hoc guard added this session, and can disagree (proven live: `semantic_result.requires_clarification == False` while the *second* call's `clarification` field was non-null).

**Where capabilities are selected more than once:** at minimum three times per turn when nothing short-circuits early — `capability_planner_plan` is always computed; `_model_proposed_capability`/`_model_proposed_workflow` are always computed; `multi_action_dispatch.dispatch()` is always attempted. Only one is actually used, decided by priority order, not by which is most likely correct.

**Where clarification can be triggered:** four distinct call sites in `orchestrator.py` (`_apply_clarification_pause` is called from four different places — initial reasoning, pre-execution sanity check, post-execution re-evaluation, and the M13 Part 2 acceptance-retention loop) — each with its own local reasoning about when to fire, none sharing one canonical "is clarification actually still needed" check.

**Where unsupported requests can fall through:** exactly one deterministic, honest terminus exists (`orchestrator.py`'s final `"URI understands the request but cannot safely execute it"`), but it is reached only if EVERY upstream mechanism (Brain proposal, multi-action, learned skill, capability planner, Brain-composed workflow, deterministic workflow planner) independently failed to produce anything — there is no single, first-class "this is permanently unsupported" signal computed once and trusted; it is inferred by exhaustion.

**Where generic response drafting can occur before execution:** never, by design — `_draft_narrative_safely` is additive-only and always runs after `execution`/`response` are already decided. This part of the architecture is genuinely sound. The user-reported symptom ("I'll begin searching...") was not drafting running early; it was the **clarification/fallback layer producing a question the Brain free-associated**, which then got narrative-drafted like anything else — a subtly different failure (§9, case with "schedule a job search").

**Where fallback logic can override a valid action path:** confirmed, live, twice this session (§9 cases A, C/E) — the initial-clarification honor path, before this session's bounded fix, unconditionally overrode a correct, already-available deterministic plan.

---

## 5. Brain-input map — what actually reaches the model at decision time

Audited by reading the actual request-building code (`model_reasoning_gateway.py::build_request`, `query_context.py::build_query_context`), not by listing what exists in the repo.

| Candidate input | Actually reaches the model? | Where / how |
|---|---|---|
| Latest user turn | **Yes** | `user_request` |
| Recent conversation turns | **Yes** | `query_context.conversation` (list of `{user, uri}` records) |
| Active-session state | **Yes, partial** | `session_context` (fact_history, last_goal_text/attempt_history) |
| Action results (this turn) | **Yes** | `attempt_history` |
| Grounded entity IDs (e.g. "that message", "its attachment") | **Only for M27's multi-action path**, via `CapabilityContextResolver` — and only once a multi-action capability is actually reached, which today it live-verifiably is not | `MultiActionDispatch.model_context`/`_bind_context` |
| Durable memory | **Yes, filtered** | `personalization_context`, gated by `is_eligible_for_personalization` (excludes `pending_confirmation`) — but note §7: this store is almost always empty of anything beyond explicit disclosures, since passive/proposed capture was never wired (M28) |
| Session facts | **Yes** | `session_context` (fact_history) |
| Connection state | **Yes for legacy capabilities, no for multi-action** | `available_capabilities` (via `CapabilityFeasibility.snapshot()`, real `connection_status`); `query_context.multi_action_capabilities` (via `capability_summaries()`, no connection/availability field until AFTER selection) |
| Capability availability (usable right now) | **Yes for legacy, no for multi-action at discovery time** | Same as above |
| Capability summaries | **Yes, two separate lists, no shared vocabulary** | `available_capabilities` (legacy) + `query_context.multi_action_capabilities` (M27) |
| Action schemas | **No, until a multi-action capability is already selected** (`describe_capability()` fires post-selection only); legacy capabilities never expose a parameter schema to the model at all — the model only ever proposes a bare capability name | — |
| Permissions | **Partially** — `blocked_by`/`gap_reason` strings for legacy capabilities; multi-action permission checks happen only at execution time, never shown to the model | `capability_feasibility.py` |
| Approval requirements | **Yes for legacy** (`requires_approval` field in the feasibility entry); multi-action approval requirement is not surfaced pre-selection | — |
| Provider/model status | **No** — nowhere in `build_request`'s payload is there a field describing which provider/model is currently active, healthy, or degraded | — |
| Unsupported-capability information | **No first-class field** — `known_gaps` exists in `capability_planner_plan` and is fed to `_draft_narrative_safely` (drafting stage) but is **never included in the reasoning request** that decides what to do — the model never sees "here is what URI definitely cannot do" before proposing | — |
| Graph/Graphify-derived context | **Yes, structurally wired, almost always empty** | `query_context.graph_context` via `graph_self_context` — see §7 for why it's usually an empty envelope |
| Workflow state | **Yes, partial** | `session.active_workflow`/`active_workflow_question` when a workflow is already paused |
| Pending approvals | **No** — not part of the reasoning request; only surfaced via the separate `/tasks` read endpoint for the UI, never fed back to the Brain's own next decision | — |
| Tool health | **No** — no field describing whether e.g. Ollama/qwen3:14b itself is degraded, rate-limited, or on a fallback provider this turn | — |

**Direct answer:** the Brain sees a real, honest, reasonably rich picture of *legacy* capability feasibility and recent conversation — better than the earlier live-verification report gave it credit for. It sees essentially nothing about M27's multi-action capabilities' real availability, nothing about provider/tool health, nothing about pending approvals, and no first-class "here's what's definitely impossible" signal at decision time (only after the fact, at drafting time).

---

## 6. Capability lifecycle audit

Ten-stage framework applied to nine representative capabilities. `✅` = stage passes, `⚠️` = partial/conditional, `❌` = fails.

| Capability | 1 Impl. | 2 Reg. | 3 Discoverable | 4 Runtime avail. known | 5 Brain-visible when relevant | 6 Executable | 7 Result → reasoning | 8 Follow-up grounded | 9 Perm/approval enforced | 10 E2E via chat |
|---|---|---|---|---|---|---|---|---|---|---|
| Gmail (legacy `gmail_search`) | ✅ | ✅ | ✅ | ✅ (CapabilityFeasibility) | ✅ | ✅ | ✅ | ❌ (no context resolver for the legacy tool) | ⚠️ (read-only enforced; no per-action grant) | ✅ — live-verified this session (post-fix) |
| Gmail (M27 multi-action) | ✅ | ✅ (separate registry) | ⚠️ (summaries only, no availability) | ❌ (not until post-selection) | ❌ (prompt never documents the shape) | ✅ (executor works when reached) | ✅ (context_resolver records results) | ✅ (this is M27's actual strength) | ✅ (permission checks, approval-required drafts) | ❌ — live-verified unreachable via normal chat |
| Google Drive | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ⚠️ | ⚠️ (not re-tested this audit; same legacy path as Gmail) |
| File conversion (`convert_document`) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | N/A (single-turn) | ✅ | ✅ (added and tested this session) |
| Web search | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ (feeds `attempt_history`, not entity-grounded) | ✅ | ✅ |
| Memory (`remember_fact`/`recall_memory`) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | N/A | ✅ | ✅ (this session, after the disclosure fix) |
| Memory (passive/proposed) | ✅ (store methods exist) | N/A | N/A | N/A | ❌ | N/A | N/A | N/A | ✅ (gate exists) | ❌ — no live caller anywhere (confirmed, M28's planning finding) |
| Graph/Graphify (M23) | ✅ | N/A (not capability-shaped) | N/A | N/A | ✅ (wired) | N/A (read-only context) | N/A | N/A | ✅ (proven non-authoritative by its own AST boundary test) | ❌ — structurally empty in live use (see §7) |
| System performance | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | N/A | ✅ | ✅ (this session) |
| Office drafting (`draft_institutional_note`/`order`) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ | ✅ (oldest, most-tested path) |
| Workflow/task execution (multi-step) | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ | ⚠️ | ✅ | ⚠️ (works for the fixed task-type templates `WorkflowPlanner` knows; nothing for e.g. "schedule a recurring search" — no template, no graceful "unsupported") |

**Pattern across the failures:** every capability that fails stage 10 fails for a **different** reason at a **different** earlier stage — M27's Gmail fails at 4/5 (prompt doesn't document it), passive memory fails at 5 (no caller), Graph Intelligence fails at 10 by way of its ingestion triggers being unreached (not a Graph problem — a Fact/Memory-flow problem). There is no single shared root cause across these three; that itself is evidence of fragmentation rather than one identifiable bug.

---

## 7. Graphify / Graph assessment

**Naming clarification, stated plainly because the request's phrasing could refer to either:** this repository contains **two unrelated things with "graph" in the name**:

1. **`.claude/skills/graphify`** — a Claude-Code-only developer tool (this session's own coding assistant) that builds a knowledge graph of *this codebase's source files* for faster navigation by an implementer/auditor. It has zero runtime relationship to URI's own agent loop, is never imported by any `uri_core/*` module, and is irrelevant to everything else in this audit.
2. **`uri_core/core/graph_*.py` (M23, "Graph Intelligence")** — URI's own runtime knowledge-graph subsystem: entities, typed relationships, provenance, bounded traversal, feeding a `graph_context` section into the Brain's own request. This is almost certainly what the audit's questions are actually about (they ask "should the Brain know Graphify exists," "does normal reasoning use it" — questions that only make sense for #2).

The rest of this section is about **#2, URI's own Graph Intelligence.**

**What was it intended to do?** Give URI a structured entity/relationship representation — "how is X connected to Y," multi-hop traversal, provenance ("why does URI believe this") — spanning what today are flat, unlinked stores (facts, memory, evidence).

**What modules exist?** `graph_schema.py` (type registry), `graph_store.py` (SQLite-backed per-user CRUD), `graph_engine.py` (six bounded read primitives + `graph_self_context`, the one orchestrator call site), `graph_ingest.py` (three narrow ingestion functions), `graph_context.py` (the `query_context`-shaped envelope builder).

**What data does it hold?** In principle: nodes for verified facts, confirmed memory entries, and one `User` node per account, plus `BELONGS_TO` edges linking them. **In practice, live-verified this session by direct trace (and independently disclosed by M23's own release audit, quoted in full):** `Fact.verify()` — the only function that would ever ingest a `VERIFIED` fact — has no live caller anywhere in the current runtime (confirmed again this audit: `grep -rn "\.verify("` across `uri_core/` finds only docstring/comment mentions, zero real call sites). `MemoryStore.propose()` — the only function that would ever create a `pending_confirmation` entry a user could later confirm into a graph-eligible `user_confirmed` fact — also has no live caller (this is exactly M28's planning finding, reached independently from a different angle). **The graph is therefore, for a real user in real live use, essentially always empty except for the one lazily-created `User` node.**

**Who consumes it?** `orchestrator.py`'s `_build_query_context` (feeds it into the Brain's request) and six read-only `GET /graph/*` routes (for direct inspection/future UI, currently unused by any client).

**Does normal reasoning ever use it?** Structurally yes (wired, additive, correctly bounded, non-authoritative — this part of M23 is genuinely well-built and its own audit is unusually honest about the gap). Practically, **no** — there is almost never anything in it to use.

**Is it infrastructure, memory, retrieval, world-model, or a user-facing capability?** Infrastructure/context — explicitly and correctly designed as non-authoritative, Brain-context-only (proven by its own AST import-boundary test: no execution/authorization module imports any `graph_*` module). It is not user-facing today (no UI consumes the six read routes).

**Should the Brain know it exists directly, or should it stay invisible and feed scoped context?** The current design already answers this correctly in principle — it feeds scoped, bounded context (`graph_context`) rather than exposing itself as a capability the Brain must reason about querying. This is the right shape. The problem is not the design; it's that the pipes feeding it are disconnected from live usage.

**What live behavior currently improves because Graph Intelligence exists? If the answer is "none," say so.** **The answer is none.** Given zero verified facts and zero confirmed passive memory ever reach it in live use today, `graph_context` is, for practically every real turn, the same empty envelope it would be if M23 had never been built. This is not a flaw in M23's own engineering (its tests, isolation, and non-authoritative boundary are all real and correctly proven) — it is a symptom of the same fragmentation this whole audit is about: a well-built subsystem whose only two real data sources are themselves unreached by the live decision loop.

---

## 8. Model-vs-architecture diagnosis

**qwen3:14b's actual, observed limitations this session:**
- **Schema/prompt compliance**: added a new prompt instruction (personal-disclosure classification); the model continued producing the old, wrong classification across multiple live calls until a deterministic regex override was added. This is a real, directly observed compliance limitation, not a hypothesis.
- **Conversational reference resolution**: not directly stress-tested this session, but `REASONING_SYSTEM_PROMPT`'s own accumulated guidance ("resolve pronouns from the last conversation entry," "don't repeat the same clarifying question," the `REPEATED_CLARIFICATION_MUST_ACT` escalation after three identical questions) is itself indirect evidence that this model needs unusually explicit, repeated correction to hold a topic across turns — each addendum in `model_reasoning_adapter.py` documents exactly one observed failure of this kind.
- **Tool/capability selection under two undocumented, overlapping catalogues**: not tested directly (M27's shape is never reached), but predictable from the M27 finding alone — asking any model to choose between two capability lists with different shapes, only one of which it's told how to act on, is an architecture problem regardless of model strength.

**Failures no model — however strong — could solve without an architecture change:**
- M27 unreachable because the prompt never documents its output shape. A frontier model given the exact same prompt would also never emit that shape, because nothing in the prompt tells it the shape exists.
- Graph Intelligence empty because nothing calls `Fact.verify()`/`MemoryStore.propose()`. No amount of model quality changes whether those Python functions are ever invoked.
- No first-class "unsupported" signal reaches the Brain pre-decision (`known_gaps` is drafting-stage-only, §5) — a frontier model reasoning without ever being told "these are the capabilities that definitely don't exist" will still, at best, *guess* correctly that something is unsupported from absence of evidence, not *know* it deterministically. The architecture, not the model, is what would make this reliable.
- Multiple decision paths reconciled by undocumented priority order (§4) — a stronger model makes each individual proposal better; it does not resolve the fact that up to five mechanisms independently decide and only one wins by accident of ordering.

**Would replacing qwen3:14b with a frontier model fix URI's current architectural failures? Explicit answer: No.** It would very likely reduce the *rate* of clearly model-attributable symptoms (the ignored prompt instruction, some fraction of redundant clarifications, better multi-step reasoning within whatever single call it's given). It would not make M27 reachable, would not populate the graph, would not give the Brain a first-class unsupported signal, and would not resolve five decision paths into one. Those are properties of what the model is *given* and how its output is *used*, not of the model itSelf.

---

## 9. Real failure-case root-cause analysis

**A. "Gmail connected, URI says it has no email access."**
- Local bug: `capability_planner.py`'s `web_search` scoring carried a hardcoded `"nit sikkim"` literal and overly broad single-word keywords, plus `gmail_search`'s own keyword list required an exact phrase like `"unread email"`/`"gmail"`/`"inbox"` that a differently-worded request could miss.
- Deeper architectural cause: the model's *own*, separate `_run_model_reasoning` call could independently decide to ask a redundant clarifying question ("are you looking for unread emails in a specific account") **even when the semantic interpreter's own structured contract already said `requires_clarification: false`** and the deterministic planner had (or would have) a confident match — that clarification had unconditional priority (§3, §4).
- Model weakness contribution: partial — the clarification question itself was a plausible-sounding but unnecessary model output, consistent with the observed prompt-compliance/redundant-question pattern.
- Would a stronger model alone fix it: **No** — the priority-order defect meant even a *correct* deterministic answer already computed could be silently discarded regardless of model quality. (Bounded-fixed this session; verified live: `gmail_search` now returns a real 531-unread-message count.)

**B. "M27 multi-action system existed and passed tests, but normal model output could not reach it."**
- Local bug: none — `MultiActionDispatch`/`MultiActionCapabilityRegistry`/`MultiActionExecutor` are correctly implemented and pass their own tests.
- Deeper architectural cause: `REASONING_SYSTEM_PROMPT` (the only place that tells the model what output shapes are valid) never mentions the `multi_action`/`selected_capability`/`proposal` keys `MultiActionDispatch._proposal()` looks for. A second, undocumented schema was added beside a fully-documented one.
- Model weakness contribution: none — no model, however capable, emits an output shape it was never told exists.
- Would a stronger model alone fix it: **No.**

**C. "Job preferences were already supplied, but URI asked again."**
- Local bug: none isolated to one keyword rule this time.
- Deeper architectural cause: identical to case A's root cause — the Brain's own first-call clarification had unconditional priority over an already-resolved deterministic classification (the disclosure had, in fact, already been saved via `remember_fact` in the same conversation).
- Model weakness contribution: yes, partial — the model was handed the recent-turn context (§5 confirms `query_context.conversation` does reach it) and still re-asked, which is a genuine reference-resolution lapse, compounded by the architecture giving that lapse unconditional priority.
- Would a stronger model alone fix it: **Partially** — a stronger model would re-ask less often, but the architecture still gives any clarification impulse, right or wrong, priority over an already-decided fact.

**D. "Unsupported scheduled job search entered clarification loops."**
- Local bug: none.
- Deeper architectural cause: no capability for recurring/scheduled search exists anywhere in either registry, and there is no first-class "nothing in either catalogue matches this goal" signal computed before deciding to ask a clarifying question (§5's `known_gaps` is drafting-stage-only). The semantic interpreter itself correctly reported `requires_clarification: true` here (genuinely, since nothing matches) — but "genuinely nothing matches" and "genuinely missing one parameter" produce the identical downstream shape (`waiting_for_input`), so the user experience is indistinguishable from an ordinary, solvable clarification.
- Model weakness contribution: none identified — this is a pure architecture/contract gap (this is the primary motivating case for the M29 Brain Decision Contract plan's `unsupported` field).
- Would a stronger model alone fix it: **No** — the contract gives it no vocabulary to express "this is impossible," only "I need more information."

**E. "'I work at NIT Sikkim' was hijacked by web search and semantic misclassification."**
- Local bug: `capability_planner.py`'s hardcoded `"nit sikkim"` literal in `web_search` scoring (a known regression, flagged once already in an earlier M24 audit and evidently never actually removed until this session); `remember_fact`'s own scoring only recognized magic trigger phrases, never a plain first-person disclosure.
- Deeper architectural cause: two independent, unsynchronized intent-classification layers (semantic interpreter's 8-key contract vs. the reasoning call's free-form output) with no shared "this is a self-disclosure" vocabulary until this session added one (a deterministic regex override in `provider_semantic_interpreter.py`, since the prompt-only instruction was not reliably followed).
- Model weakness contribution: real — the model did not follow an added prompt instruction reliably, which is why a deterministic override was needed rather than a prompt fix alone.
- Would a stronger model alone fix it: **Partially** — the hardcoded keyword bug would still exist regardless of model choice; a stronger model would likely have followed the prompt instruction and made the deterministic override less necessary, but the architecture (two unsynchronized classifiers) would remain.

**F. "Individually-tested milestones do not reliably compose end-to-end."**
- Local bug: not applicable — this is the composite symptom, not a single bug.
- Deeper architectural cause: this is §1–§4's central finding, restated as a case — each milestone's own test suite proves that milestone's own mechanism works in isolation (true for M11, M20, M27, M23 alike); none of their test suites prove that mechanism actually wins the priority race against the other four in a real turn. This audit found that gap directly (M27, live-verified never reached; M23, live-verified always empty) using exactly the technique those test suites don't apply: tracing a real request through the *entire* orchestrator method rather than unit-testing one mechanism with everything else mocked out.
- Model weakness contribution: none.
- Would a stronger model alone fix it: **No.**

**G. "Graphify exists but its real contribution to reasoning is unclear."**
- Local bug: none in M23 itself.
- Deeper architectural cause: M23's own release audit already disclosed the exact gap (§7) — its ingestion depends on two functions (`Fact.verify()`, `MemoryStore.propose()`) neither of which any live code path calls. This is not a Graph Intelligence defect; it is a downstream consequence of the same "wired but never actually invoked" pattern found independently in M27 and (separately) motivating the M28 passive-memory plan.
- Model weakness contribution: none.
- Would a stronger model alone fix it: **No** — there is nothing here for a stronger model to reason its way around; the data simply isn't produced.

---

## 10. External architecture research (cited)

Compared against how production/research agent systems handle the same seven questions this audit asked about URI.

**What the model sees.** MCP formalizes tool discovery as an explicit client-server handshake — a client queries what tools a server offers and receives "a machine-readable list of functions... describing each available action, its inputs, and output format" before ever invoking one ([Model Context Protocol specification](https://modelcontextprotocol.io/specification/2025-11-25); [CodiLime, "Model Context Protocol (MCP) explained"](https://codilime.com/blog/model-context-protocol-explained/)). Anthropic's own engineering guidance is explicit that a tool must be described as if "writing for an alien collaborator who needs every detail spelled out" ([Anthropic, "Writing effective tools for AI agents"](https://www.anthropic.com/engineering/writing-tools-for-agents)) — URI's M27 registry violates this directly: the *model* is never told the multi-action proposal shape exists at all, which is a strictly worse position than "the tool description is imperfect" (§9, case B).

**How runtime state is represented.** LangGraph's core primitive is an explicit, typed state object that "persists and is updated throughout the graph's execution," visible to every node ([Medium, "LangGraph — Architecture and Design"](https://medium.com/@shuv.sdr/langgraph-architecture-and-design-280c365aaf2c); [LangChain docs, Graph API overview](https://docs.langchain.com/oss/python/langgraph/graph-api)) — one shared, structured state, not several parallel context-assembly functions computed independently per call. URI's `query_context.py` is the one place this pattern is followed correctly (§2); the reasoning/planning layer around it is not.

**How tools are discovered / tool-explosion is avoided.** Both MCP-Zero and ScaleMCP exist specifically because naively injecting every tool's full schema into every prompt does not scale — "this expansion creates significant context overhead, as traditional approaches inject all server JSON-Schemas into system prompts simultaneously" ([MCP-Zero](https://arxiv.org/pdf/2506.01056); [ScaleMCP](https://arxiv.org/pdf/2505.06416)). URI's own M27 `CapabilityDiscoveryEngine` already implements the right *shape* of the correct answer here (summaries first, full action schema only after selection) — it is simply never reached (§9, case B), and the legacy path has no progressive-discovery concept at all (every legacy capability name is exposed flatly, unconditionally, every turn).

**How action schemas are scoped.** The same MCP/ScaleMCP sources converge on scoping schemas to relevance rather than dumping the full catalogue. URI has this capability (M27's two-stage discovery) sitting unused beside a legacy path that has no such scoping.

**How results feed back.** ReAct's foundational insight — "the observation is a real result from outside the model, so the next thought is built on a fact the tool returned, not on an assumption the model made" ([Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models," arXiv:2210.03629](https://react-lm.github.io/)) — is one thing URI already gets right structurally: `attempt_history` and `_draft_narrative_safely`'s additive-only discipline both enforce exactly this (a drafted reply can never claim more than the real execution result supports). OpenHands formalizes the same idea as an explicit "event-stream abstraction capturing actions and observations, forming a perception–action loop" ([OpenHands docs, Agent architecture](https://docs.openhands.dev/sdk/arch/agent); [OpenHands paper, arXiv:2407.16741](https://arxiv.org/pdf/2407.16741)) — a single canonical event log every component reads, rather than URI's several independently-computed candidate plans.

**How unsupported actions are handled.** None of the surveyed systems treat "no tool matches" as an afterthought inferred by exhaustion; MCP's discovery handshake and LangGraph's explicit conditional edges both make "no matching capability" a first-class, examinable state rather than a fallthrough. URI's equivalent (§5, §9 case D) is structurally the weakest point found in this audit: `known_gaps` exists and is even correctly computed, but never reaches the decision step, only the drafting step.

**How memory is separated from active context.** Letta/MemGPT's three-tier model — "Core Memory... like RAM, Recall Memory... like a disk cache, Archival Memory... like cold storage" ([Letta, "Agent Memory: How to Build Agents That Learn and Remember"](https://www.letta.com/blog/agent-memory/); [Letta MemGPT docs](https://docs.letta.com/guides/legacy/memgpt_agents_legacy)) — cleanly separates what's always in context from what's fetched on demand. URI's separation (session facts vs. durable `MemoryStore` vs. Graph Intelligence) is architecturally similar in *intent*, but two of its three tiers (durable memory beyond explicit disclosure, and the graph) are populated by triggers no live code path fires (§7) — the tiering exists; the pipes into it mostly don't.

**How multiple actions are planned.** LangGraph's plan-then-execute pattern uses one `planner_node` producing a plan the graph's state carries forward, and one `executor_node` consuming it step by step ([Latenode, "LangGraph AI Framework 2025"](https://latenode.com/blog/ai-frameworks-technical-infrastructure/langgraph-multi-agent-orchestration/langgraph-ai-framework-2025-complete-architecture-guide-multi-agent-orchestration-analysis)) — one plan, one owner. URI has the *raw materials* for this (M27's `execute_chain`) but no single planning step decides whether a request needs one action or several; that judgment is smeared across `model_workflow_proposal`, `WorkflowPlanner`, and `MultiActionDispatch`'s own workflow branch, three separate places that could each say "this needs multiple steps."

**How weaker models are supported.** Anthropic's context-engineering guidance recommends "just in time" context (lightweight references loaded on demand rather than everything up front) and treating tool responses with "pagination, range selection, filtering... for any tool responses that could use up lots of context" specifically because smaller/weaker models degrade faster under prompt bulk ([Anthropic, "Effective context engineering for AI agents"](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)). `model_reasoning_adapter.py`'s own comments independently rediscovered this exact lesson for qwen3:14b (conditionally-appended prompt addenda, explicitly to avoid "prompt bulk it doesn't need") — this is one place URI's own engineering already matches current best practice, arrived at empirically rather than by design.

**Synthesis, not a product list:** every system surveyed converges on the same shape URI is missing — **one shared, typed state; one planning step that classifies the situation before producing artifacts; tool/capability visibility scoped to relevance; and a first-class "nothing matches" state.** URI already has working, tested components for most of these pieces (`query_context.py` for shared state, M27's discovery engine for scoping, `capability_planner.py`'s `known_gaps` for the unsupported signal) — they are simply not yet composed into the one decision step every surveyed architecture treats as canonical.

---

## 11. Duplicate / competing decision systems (explicit inventory)

1. **Two intent-classification calls per turn** with no shared schema: `provider_semantic_interpreter.py` (8-key contract) and `model_reasoning_adapter.py` (`action`/`workflow`/`clarification`/`evaluation`).
2. **Two capability-selection mechanisms** that can each independently produce a final plan: `capability_planner.py` (deterministic keyword scoring) and the Brain's own `action` proposal (`_model_proposed_capability`).
3. **Two capability registries with no shared vocabulary**: `capability_registry.py`/`CapabilityRegistry` (legacy, feasibility-aware) and `uri_core/capabilities/registry.py`/`MultiActionCapabilityRegistry` (M27, progressive-discovery-aware, connection-blind at discovery time).
4. **Two multi-step-workflow mechanisms**: `WorkflowPlanner`/`WorkflowCapabilityRouter` (deterministic, task-type-template-based, pre-M11) and the Brain-composed workflow path (`_model_proposed_workflow` → `_build_model_workflow` → `WorkflowExecutor`) and, arguably, a **third**, `MultiActionExecutor.execute_chain` (M27).
5. **Four independent call sites that can each trigger a clarification pause**, none sharing one canonical "is this actually still needed" check (§4).
6. **Two feasibility/availability computations**: `CapabilityFeasibility` (legacy, connection-aware) and `MultiActionCapabilityRegistry.capability_summaries()`/`check_availability()` (M27, connection-blind until post-selection) — computing the same underlying question ("can this actually run right now") independently, with different answers reaching the model at different times.

---

## 12. Components that should likely be retained (unchanged in role)

- `ApprovalGate` / `ToolDispatcher` — the one genuinely single, enforced execution boundary. Nothing about this audit's findings implicates it.
- `query_context.py` — the one clear example of real convergence; every future context source should keep extending this, not create a parallel assembler.
- `_draft_narrative_safely` / `response_drafting.py`'s additive-only, claim-consistency-checked discipline — structurally sound, matches ReAct's observation-grounding principle exactly.
- `CapabilityFeasibility` — correctly closes the "registered but not usable right now" gap for the legacy registry; the model to extend to the multi-action registry, not replace.
- `MultiActionCapabilityRegistry` / `CapabilityDiscoveryEngine` / `MultiActionExecutor` / `CapabilityContextResolver` (M27's actual machinery, as distinct from its lack of prompt integration) — the progressive-discovery/propose-validate-execute shape is exactly what the external research converges on; it needs to be *reached*, not redesigned.
- `graph_store.py`/`graph_engine.py`'s isolation, provenance, and non-authoritative-boundary guarantees — correctly engineered; the subsystem needs real ingestion triggers, not architectural changes.
- `capability_planner.py`'s deterministic scoring — a reasonable, fast, zero-model-call fallback; its *role* (last resort, not one of five competing first movers) needs clarifying, not its logic.

## 13. Components that should likely be consolidated

- The two intent-classification calls (§11.1) — candidates to converge into one decision step that both classifies the situation and identifies a capability, rather than two separately-schemaed calls reconciled after the fact.
- The two capability registries (§11.3) — need a shared feasibility/availability computation (extend `CapabilityFeasibility`-style connection-awareness to the multi-action registry) even if the registries themselves stay physically separate for migration reasons.
- The four clarification-triggering call sites (§11.5) — candidates for one shared "is clarification still warranted given what's now known" check, reused from all four places rather than reimplemented at each.
- The three multi-step-workflow mechanisms (§11.4) — at minimum, one of them should become the canonical planner for "this needs more than one action," with the others explicitly demoted to fallback or retired.

## 14. Components that may eventually be retired

- `WorkflowPlanner`'s task-type-keyed template matching, if the Brain-composed workflow path and/or `MultiActionExecutor.execute_chain` prove sufficient once actually reachable — candidate for retirement, not certain (needs a migration/shadow period, not a guess).
- The unconditional-priority form of `_apply_clarification_pause`'s initial-reasoning call site, once a proper decision contract (M29-scale) makes "is clarification genuinely needed" a first-class, validated field rather than something inferred and then guarded after the fact (this session's bounded fix is a patch on the current shape, not the end state).
- Duplicate feasibility computation once/if the two registries share one.

## 15. Top 5 root causes, ranked by importance

1. **No single decision step classifies the situation before artifacts are produced.** Every other finding in this audit — the M27 dead path, the redundant clarifications, the two intent classifiers, the ambiguity between "missing a parameter" and "no capability exists" — traces back to this one gap. (§1, §3, §4, §9 cases A/C/D/E)
2. **New decision mechanisms were consistently added beside existing ones, never replacing them** (the M11→M13→M20→M27 pattern, itself following the earlier M-skill-router shadow-mode precedent). This is a process pattern as much as a code pattern — four milestones in a row chose "add a new path, reconcile by priority" over "replace or consolidate." (§2, §4, §11)
3. **Prompt contracts are not kept in sync with what the runtime is actually capable of dispatching.** M27's entire multi-action system exists, is tested, and is invisible to the model because nobody updated the one prompt that tells it what output shapes are valid. (§9 case B, §10)
4. **Ingestion triggers for two "downstream" subsystems (durable memory beyond explicit disclosure, and the graph) were never wired to any live code path**, so both are structurally starved regardless of how well-built they are. (§7, §9 case G)
5. **No first-class "this is permanently unsupported" signal exists at decision time** — only after the fact, at drafting time, and only as a byproduct of a different mechanism (`known_gaps`) never designed for this purpose. This is what turns a genuinely unsupported request into an indistinguishable, potentially endless clarification loop. (§5, §9 case D)

## 16. What we previously overlooked, and when

- The claim "connection state does not reach the Brain's context" (this session's own earlier live-verification report, made before this Stage 1 audit) was **too broad** — it was true for M27's multi-action registry and false for the legacy registry, which already had real connection-aware feasibility since M20. Overlooked at the time because the check was a single grep for `connection_status` text inside `orchestrator.py` itself, missing that the actual data path runs through `model_reasoning_gateway.py`/`capability_feasibility.py` instead. Corrected in this audit (§1, §5, and explicitly in the M29 plan already drafted).
- M23's Graph Intelligence being structurally empty was **already disclosed by its own release audit** at the time it shipped — it was not a new discovery this session, but it had not previously been connected to the *pattern* (the same "wired but unreached" shape recurring across M23, M27, and M28's motivating gap) until this audit looked at all three side by side.
- The priority-order defect fixed earlier this session was treated, at the time, as a bounded, local fix (one guard clause). This audit is the first point at which it's named as one instance of a *general* architectural pattern (§4, §11.5) rather than a one-off bug.

## 17. Questions that still remain unanswered

- Should the two capability registries (legacy `CapabilityRegistry` vs. M27's `MultiActionCapabilityRegistry`) be physically merged, or is a shared feasibility/availability interface between two physically separate registries sufficient? This audit did not evaluate migration cost for existing legacy capabilities in enough depth to recommend one over the other.
- What should happen to `skill_memory`'s learned-skill mechanism under a unified decision contract — does "a similar request succeeded before with capability X" become one more input to a single decision step, or does it stay a separate reference layer ahead of that step, as today?
- Is `WorkflowPlanner`'s deterministic template mechanism worth keeping as a fallback-of-last-resort once/if the Brain-composed and M27 chain-execution paths are both genuinely reachable, or does it become dead weight? This needs real usage data, not architectural judgment alone.
- What is the actual cost (latency, token budget, qwen3:14b-specific prompt-bulk sensitivity — see `model_reasoning_adapter.py`'s own documented lesson) of a single, richer decision call that must now carry both capability catalogues, connection state, and an explicit unsupported-check, compared to today's multiple smaller calls? Not measured in this audit.
- Should `Fact.verify()` ever actually be wired to a live caller, or was it correctly identified (by this repository's own earlier work) as a deliberately unbuilt, separately-reviewed capability for accountability reasons that should stay that way? This audit found the gap; it did not evaluate whether closing it is even desired.
- Is Graph Intelligence's current worth-having case strong enough to prioritize wiring its two ingestion triggers, given it currently improves zero live behavior — or should M23 remain dormant until/unless a concrete downstream consumer (a UI, a specific reasoning need) is identified first?

---

*Stage 1 complete. No implementation, migration code, prompt changes, routing patches, or regex additions were made as part of this audit, per the User's explicit instruction. Stage 2 (canonical agent-loop design) is a separate, not-yet-authorized piece of work.*
