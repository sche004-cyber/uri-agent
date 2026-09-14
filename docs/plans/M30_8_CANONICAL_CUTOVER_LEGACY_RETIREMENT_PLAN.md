# M30.8 - Canonical Cutover + Legacy Retirement (Revised Plan, Read-Only, NOT Implemented)

STATE: ACCEPTED (plan only) - implementation NOT yet performed, per
the User's explicit "Do NOT implement... Return both plans for User
review before implementation." Claude (Architect/Planner) output per
the standing AO-4 development cycle. **No production source was
modified to produce this document.** Sibling state file:
`docs/plans/M30_8_CANONICAL_CUTOVER_LEGACY_RETIREMENT_STATE.md`.
Companion plan: `docs/plans/M30_GRAPHIFY_FOUNDATION_PLAN.md` (Plan A) -
a hard precondition of this plan's Phase A. **Supersedes** the prior
`docs/plans/M30_8_CANONICAL_DEFAULT_CUTOVER_PRE_AUDIT.md` (read-only
pre-audit only, never a plan) and the original migration plan's
separate M30.8/M30.9/M30.10 rows (`docs/plans/
URI_CANONICAL_AGENT_LOOP_MIGRATION_PLAN.md` §17) - merged per the
User's own explicit 2026-09-14 instruction.

**Product decision this plan implements (User, 2026-09-14):** replace
the previous separate milestones with one - "M30.8 — Canonical Cutover
+ Legacy Retirement." Phase A: canonical Brain becomes default
authority, Graphify foundation is available, legacy invocation is
observed and mapped. Phase B: where canonical responsibility is
demonstrably covered, remove the duplicate legacy decision authority -
migrate any genuinely required responsibility first, retain only
explicitly justified exceptions. Principle: "If two paths reach the
same destination, URI should retain the safer, faster, simpler path...
Remove it when canonical coverage is proven," never merely because it
is old.

---

## 0. Readiness baseline this plan builds on (not reopened)

Per the User's own explicit instruction, the completed M30 readiness
work is **not reopened**:

- **M30-PFC: CLAUDE ACCEPT** (provider-failure false-consent repair;
  three-way `MODEL_NOT_ATTEMPTED`/`MODEL_REACHED_BUT_INVALID`/
  `MODEL_TERMINALLY_UNAVAILABLE` distinction, fail-closed only on
  terminal unavailability).
- **Scenario 2: CLOSED** (Gmail `DISCONNECTED` gate repair -
  `decision_gates.py`'s Availability/Connection check is now reachable
  and authoritative regardless of the model's own proposal framing;
  live-confirmed `gate_outcome: "DISCONNECTED"`, `capability_id:
  "Gmail"`).
- **Scenario 8: CLOSED** (real canonical `Gmail`/`create_draft`/
  `APPROVAL_REQUIRED` content-envelope evidence).
- **Scenario 12: CLOSED** (honest, deterministic, visible provider-
  unavailable fallback, live-confirmed post-M30-PFC, at both the
  canonical and legacy layers).
- **Scenario 7: non-blocking**, substantially live-proven (real
  `search_messages`/`read_message` against genuine attachment-bearing
  test-account data; only the fully autonomous NL-narration step
  remains model-variance-limited, not a code gap).
- **Scenarios 4/5/9: unchanged** (accepted residual / accepted
  limitation / deferred, respectively - not reopened).
- **Regression:** 1,743 total items, 8 pre-existing failures (exact,
  name-for-name baseline match), 0 new failures.

This plan only reopens any of the above if the revised architecture
below materially invalidates an assumption underneath it. **None of it
does** - Phase A's own design (§B.2) explicitly reuses the same
Decision Engine/gates/canonical-execution modules this evidence was
gathered against; nothing about merging M30.8+M30.10 or adding
Graphify changes what those modules do for an already-allowlisted
capability.

---

## 1. Current, real integration architecture - inspected directly, not assumed from the abstract migration plan

**This is more precise than the original migration plan's own
description of "the ~300-line priority block replaced by flat
dispatch" - the actual implementation integrates at the `server.py`
route level, not inside `orchestrator.py`, consistent with this
project's own standing "`orchestrator.py` must never grow" rule.**
Confirmed by direct reading of `uri_core/app/server.py`'s `/ask`
handler:

1. **Workflow-continuation early-exit** (`URI_ENABLE_WORKFLOW_
   CONTINUATION_MODE`, M30.7) - runs first; can skip the legacy path
   entirely, but only for an in-progress, `waiting_for_input`
   workflow whose continuation the canonical Decision Contract
   confirms.
2. **Legacy path** (`context.orchestrator.process_user_input(...)`) -
   **runs unconditionally on every turn**, unless step 1 already
   short-circuited. This is the critical, previously-undocumented-at-
   this-precision fact this plan's design depends on: **today, the
   full legacy decision pipeline is computed on every single turn,
   regardless of whether canonical execution is enabled or will end up
   overriding the result.**
3. **Decision Engine shadow** (`URI_ENABLE_DECISION_ENGINE_SHADOW`,
   M30.3) - runs after step 2, logs a comparison, never touches
   `result`.
4. **Canonical live execution** (`URI_ENABLE_DECISION_ENGINE_LIVE`,
   M30.6) - runs after step 2; `run_canonical_for_ask()` returns a
   real, already-executed result **only** for an explicitly
   allowlisted capability (`CANONICAL_EXECUTION_ALLOWLIST =
   {"Gmail", "remember_fact"}`) whose deterministic gate outcome was
   `READY`. If it returns `None` (not allowlisted, or gate not ready),
   `result` from step 2 (legacy) is used completely unchanged.

**The direct consequence for this plan:** "canonical becomes default
authority" is not, today, a matter of flipping one flag from allowlist
to global - it also requires **inverting which path is computed
first**, because right now legacy is *always* fully computed (an
unconditional cost and an unconditional source of truth whenever
canonical opts out), and canonical only ever conditionally overrides
it after the fact. Phase A's design (§B.2) makes this inversion
explicit rather than leaving it implicit.

---

## 2. Legacy-authority retirement inventory

Built directly from the migration plan's own component matrix (§1)
and re-verified against current source in this session (not merely
copied):

| Mechanism | Current role | Canonical equivalent | Retirement classification |
|---|---|---|---|
| `capability_planner.py` | Legacy keyword-scoring first-mover; also the current fallback when nothing else resolves | Unsupported-Gate cross-check (`_plausible_match_exists`/`plausible_matches`, already generic - Scenario 2's own repair reuses this exact module) + the demoted fallback role the migration plan already assigns it | **RETAIN as fallback only** - never fully deleted; its role narrows to exactly two jobs (gate cross-check input, genuine-unavailability fallback), matching the migration plan's own `DEMOTE` classification, not `RETIRE` |
| Learned-skill matcher (`skill_memory.py`'s `elif learned_skill:` direct-plan branch) | **Already demoted this session** (M30-PFC) - fires only when NOT in `MODEL_TERMINALLY_UNAVAILABLE` state; the empty-match defense-in-depth is also already fixed | Turn State reference hint only (migration plan's own original target) | **Already substantially retired** - the remaining work is confirming, once canonical is default-authoritative (Phase A), that this branch is reached rarely/never in practice (Phase A's own observation window, §B.3), not a new code change |
| `WorkflowPlanner`/`WorkflowCapabilityRouter` | A sixth, independent, task-type-keyed decision engine | **Already effectively covered**: direct inspection of `_create_steps()` confirms **exactly one real template exists** (`generic_evidence_drafting_workflow` - every task-type branch converges on the same generic sequence), and it is **already exposed as a real Capability Directory procedure entry** (`capability_directory.py`'s hardcoded procedure record, `foundational: False`) | **RETIRE the decision role in Phase B once Phase A's observation confirms it is never the actual deciding path** - the "orphaned task-type" risk the migration plan's own §19 and the prior pre-audit both flagged as unconfirmed is **resolved by this inspection**: there is no second template to lose, so this is a low-risk retirement candidate, not a genuinely open question anymore |
| `MultiActionDispatch` (M27) legacy trigger shape | A parallel, undocumented-model-output-shape-triggered dispatcher | Folded into the Execution Engine (its registry/executor logic is real and reused; only its *triggering condition* changes to the Decision Contract's explicit fields) | **MIGRATE the trigger, KEEP the executor** - per the migration plan's own `WRAP`, then `MIGRATE` classification; not a deletion candidate, a wiring change |
| Legacy `semantic_interpreter.py` (Groq-shaped) | Alternate/legacy 8-key interpreter, not the default path | None - folded into the Decision Engine | **RETIRE, pending the one-time M30.0 confirmation check** (verify zero live production config selects it) - this check has **not yet been independently re-confirmed this session**; it is a cheap, bounded, read-only check that should run early in Phase A, not assumed |
| `provider_semantic_interpreter.py`'s independent 8-key contract authority | Independently trusted by `capability_planner.py` today | Folded into the Decision Engine's own extraction; the transport is reused, the contract stops being independently authoritative | **DEPRECATE as a standalone authority once `capability_planner.py`'s own role narrows to fallback-only** (Phase B) - the transport itself is `KEEP`, per the matrix |
| `orchestrator.py`'s always-computed legacy `process_user_input()` call | Runs unconditionally every turn (§1 finding) | N/A - this is the *invocation pattern*, not a decision mechanism itself | **INVERT in Phase A** (§B.2) - stop being unconditional; become the fallback path, invoked (and counted) only when canonical does not produce a usable `READY` result |

**Explicitly not in this inventory, and not touched by this plan:**
`ApprovalGate`, `dispatcher.py`/`ToolDispatcher`, `MultiActionExecutor`,
`connection_status.py`, `ModelRouter`, response drafting - all
migration-plan `KEEP unchanged` rows, unaffected by cutover or
retirement.

---

## B. Revised M30.8 plan

### B.1 Phase A precondition - Graphify Foundation

Phase A does not begin until `docs/plans/M30_GRAPHIFY_FOUNDATION_PLAN.md`'s
own 6 acceptance criteria are independently met (its own §"Acceptance
criteria") - this is a hard gate, not a parallel workstream. Rationale,
directly from this session's own Scenario 2 finding: Graphify's
compact capability/availability map is exactly the kind of small,
relevant context subset that lets the Brain (and, later, the
deterministic gates) reason about "does this capability exist and is
it connected" without depending on the model's own unreliable self-
report of "unsupported" - the same class of problem Scenario 2's
repair fixed at the gate level. Having the foundation in place before
cutover reduces (does not eliminate - Scenario 2's fix is still the
authoritative mechanism) the surface area for the same failure mode
recurring elsewhere as canonical becomes default.

### B.2 Phase A - canonical default authority, legacy inverted to fallback, observed and mapped

**Mechanical change** (the concrete meaning of "canonical Brain
becomes default authority," grounded in §1's real integration
architecture, not the abstract description):

1. `CANONICAL_EXECUTION_ALLOWLIST` is retired as a *gate* (every
   capability the Directory knows about is eligible), while the
   underlying allowlist mechanism itself is **kept as an emergency
   killswitch** (an empty or narrowed allowlist remains a valid, fast
   rollback lever - §D) - not deleted, repurposed.
2. The `/ask` handler's step order (§1) is **inverted**: the canonical
   pipeline (Decision Engine → gates → canonical execution) runs
   *first*. The legacy path (`orchestrator.process_user_input`) is
   invoked **only when** the canonical gate outcome is not `READY`
   for a reason other than a genuine, deterministic, non-decision-
   quality cause - reusing M30-PFC's own three-way distinction
   directly: `MODEL_NOT_ATTEMPTED`/`MODEL_REACHED_BUT_INVALID` still
   permit canonical's own honest handling (`UNSUPPORTED`/
   `DISCONNECTED`/`MISSING_PARAMETER`/etc. are all real, correct,
   *canonical* answers, not fallback triggers); only `MODEL_
   TERMINALLY_UNAVAILABLE` or an `INVALID_PROPOSAL`/`DEGRADED` gate
   outcome (a genuine engine/parse failure, not a content decision)
   invokes the legacy path as fallback.
3. **Every legacy fallback invocation is logged with its own reason
   code** (reusing `decision_engine_shadow_log.jsonl`'s existing
   `gate_outcome`/`gate_reasons` shape - additive fields, not a new
   log file) - this *is* "legacy invocation is observed and mapped,"
   concretely: a real, queryable record of every turn where legacy
   ran, and exactly why canonical did not handle it alone.
4. Graphify's foundation (Plan A) is available and loaded - consumed
   optionally by the Decision Engine's own prompt context (the small,
   relevance-filtered `capability_index_hint`, Plan A §A.4) as
   additional grounding, never as a new decision authority.

**What does NOT change in Phase A:** no legacy mechanism is deleted;
`capability_planner.py`, `WorkflowPlanner`, `MultiActionDispatch`'s
executor, and the learned-skill hint all continue to exist exactly as
they do today - only *how often* and *why* they are reached changes
(from "every turn, unconditionally" to "only on canonical fallback,
with a logged reason").

### B.3 Phase A exit criteria - real observation, not a one-time test pass

Directly reusing the original migration plan's own M30.10 retirement
gate (§20), applied here as Phase A's own exit bar into Phase B rather
than a separate later milestone:

1. Canonical-default (inverted order, §B.2) has run for a real
   observation window with production/live traffic - not a single
   test session.
2. All 12 mandatory acceptance scenarios (migration plan §14) pass
   live, repeatedly, not just once - this session's own readiness
   evidence (§0) already covers Scenarios 2/8/12 concretely and
   satisfies 6/7's own mechanism proof; the observation window
   confirms this holds under the *inverted* order specifically, not
   only under the M30.6 allowlist-scoped order the evidence was
   originally gathered against.
3. The legacy fallback path is invoked, over that window, **only for
   genuine model-unavailability/malformed-output/engine-failure
   reasons** (per the logged reason codes, §B.2 item 3) - never
   because canonical produced a worse decision than legacy would have.
   A real disagreement of this second kind is not a Phase A failure to
   silently tolerate - it is a signal to pause and investigate before
   proceeding to Phase B, per this repository's own Verification-First
   standard.
4. Full Layer 1+2+3 regression suite is green immediately before Phase
   B begins.
5. `WorkflowPlanner`'s template inventory shows no orphaned task-type
   coverage - **already substantially resolved by this plan's own §2
   inspection** (exactly one template, already a Directory procedure);
   Phase A's observation window re-confirms this holds under real,
   repeated live traffic rather than static inspection alone.

### B.4 Phase B - retire duplicate legacy authority where canonical coverage is proven

**Principle, applied per-mechanism, never as one big-bang deletion:**
each row in §2's inventory is retired independently, only once its own
specific coverage is proven by Phase A's observation data for that
mechanism - a mechanism with real, distinct remaining responsibility
(e.g. `capability_planner.py`'s fallback role, `MultiActionExecutor`'s
execution mechanics) is never retired; only genuinely duplicate
*decision* authority is.

**Concrete Phase B actions, per §2's inventory:**

1. **`WorkflowPlanner`/`WorkflowCapabilityRouter`'s decision role** -
   retire (delete the task-type-keyed dispatch logic); the one real
   template stays, already living as a Directory procedure - no
   functional loss, confirmed by §2's own inspection.
2. **Legacy `semantic_interpreter.py`** - retire, once the M30.0
   confirmation check (§2, not yet re-run this session) confirms zero
   live callers.
3. **`MultiActionDispatch`'s legacy trigger shape** - retired in favor
   of the Decision Contract's explicit fields; its executor/permission/
   binding logic is retained, called from the canonical path instead.
4. **`orchestrator.py`'s ~300-line interleaved priority block** -
   replaced by the flat, already-inverted dispatch from Phase A (§B.2);
   this is where `orchestrator.py` is expected to *shrink* for the
   first time in this migration, consistent with the User's own
   "orchestrator.py must never grow" rule finally paying off in reverse.
5. **`capability_planner.py`, learned-skill hint, `provider_semantic_
   interpreter.py`'s 8-key contract** - **NOT deleted**; each retains
   its explicitly justified, narrower remaining role (fallback
   decision-maker / advisory Turn State hint / reused transport,
   respectively) - named here so "retain only explicitly justified
   exceptions" has a concrete, closed list, not an open-ended one.

**Migration-first discipline:** step 1 above is the one case where a
genuinely unique legacy responsibility (however small) exists - it is
migrated (already done, per §2's inspection) *before* any deletion, not
after, satisfying "migrate any genuinely required responsibility
first" literally, not just in spirit.

---

## C. Explicit legacy-authority retirement inventory

(Consolidated view of §2, restated as the standalone deliverable the
User's own outline requests as item C.)

| # | Mechanism | Action | Sequencing | Risk if wrong |
|---|---|---|---|---|
| 1 | `WorkflowPlanner`/`WorkflowCapabilityRouter` decision role | RETIRE | Phase B, after §B.3's exit criteria | Low - only one template exists, already ported |
| 2 | Legacy `semantic_interpreter.py` | RETIRE | Phase B, after a fresh M30.0-style zero-caller confirmation | Low if confirmed; do not skip the confirmation |
| 3 | `MultiActionDispatch` legacy trigger shape | MIGRATE (trigger only) | Phase B | Low - executor logic untouched |
| 4 | `orchestrator.py`'s always-computed legacy call | INVERT (fallback-only) | Phase A (mechanical prerequisite for everything else) | Medium - this is the actual behavior change; mitigated by §B.3's observation-window gate before Phase B |
| 5 | `capability_planner.py` | RETAIN (narrowed) | Unchanged through both phases | N/A - explicitly not a retirement candidate |
| 6 | Learned-skill direct-plan hint | Already substantially DEMOTED (M30-PFC) | Confirm-only in Phase A's observation | Low - repair already live, tested, closed |
| 7 | `provider_semantic_interpreter.py` standalone contract authority | DEPRECATE (as authority; transport KEEP) | Phase B, tied to item 5's fallback-only narrowing | Low |

---

## D. Migration/rollback gates

Directly adapting the original migration plan's own §16 rollback table
(rows M30.8 and M30.10), merged for this revised, single milestone:

| Stage | Flag/lever | Rollback procedure | Regression baseline | Exit criteria |
|---|---|---|---|---|
| Graphify Foundation (Plan A) | N/A (purely additive; absence degrades to empty, §A.3) | Remove the two new `StartupService` registrations; server behavior is unaffected (nothing else yet reads the new index) | Full suite green, zero behavior diff for any existing consumer | Plan A's own 6 acceptance criteria (its own document) |
| Phase A (canonical default, inverted order) | `CANONICAL_EXECUTION_ALLOWLIST` widened to "all" is the mechanical flag; reducible back to the current two-entry allowlist, or to empty (full legacy-first behavior), at any time without a data migration | Narrow or empty the allowlist - this is the same emergency killswitch already proven in M30.6, not a new mechanism | Full regression green; all 12 mandatory scenarios (§14) passing live | §B.3's 5 exit criteria, all holding simultaneously |
| Phase B (retirement, per §C) | **No flag-flip rollback for a deleted mechanism** - each item in §C is retired only after its own Phase A observation evidence is strong enough, and only one at a time, so a problem surfaces against a single, identifiable change | Revert the specific commit that retired that one mechanism; nothing else in §C is affected, since retirements are independent, not batched | Full suite green immediately before each individual retirement | Per-mechanism: the specific evidence named in §C's own row for that mechanism |

**No legacy mechanism in §C is retired until Phase A's own exit
criteria (§B.3) are met for the system as a whole, and that specific
mechanism's own row-level evidence is separately satisfied** - directly
carrying forward the original migration plan's own binding rule ("no
old routing authority is retired until canonical-path evidence is
strong enough"), now applied per-mechanism rather than as one
all-or-nothing gate.

---

## E. Final acceptance criteria

1. **Graphify Foundation accepted** (its own plan's 6 criteria) before
   Phase A begins.
2. **Phase A's mechanical change is live and correct:** canonical
   pipeline runs first for every turn; legacy is invoked only as a
   logged, reason-coded fallback (§B.2); the killswitch allowlist
   mechanism still works (proven by a test that narrows it and
   confirms immediate reversion to legacy-first behavior).
3. **Phase A's observation-window exit criteria (§B.3) all hold**
   simultaneously, over real traffic, not a single test run.
4. **Each Phase B retirement (§C) is independently justified** by its
   own named evidence before it happens - no batch deletion.
5. **`orchestrator.py` measurably shrinks** once Phase B's item 4
   lands (the first net reduction in this migration, confirmed by
   `wc -l` against the pre-Phase-B baseline - the mirror image of
   M23's own "must never increase" proof, now proving a decrease).
6. **Full Layer 1+2+3 regression suite green** at every stage
   transition (Graphify → Phase A → each Phase B retirement) - never
   an unobserved or killed run treated as a result.
7. **This session's existing readiness evidence (§0) remains valid**
   throughout - re-verified, not re-litigated, if and only if a later
   phase's own design turns out to materially change an assumption it
   rested on (none currently identified).
8. **The User's own final review and explicit authorization** for
   Graphify, for Phase A, and for each Phase B retirement remain
   required and non-delegable - this document does not substitute for
   any of them.

---

Stopping here. No production source modified. No implementation
performed. M30.8 (as originally scoped) and this revised replacement
are both NOT started - this plan is for the User's review and separate
implementation authorization only.
