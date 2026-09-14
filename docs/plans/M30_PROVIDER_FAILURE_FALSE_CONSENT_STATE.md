# Provider-Failure False-Consent Memory Defect - State

**Plan:** `docs/plans/M30_PROVIDER_FAILURE_FALSE_CONSENT_REPAIR_PLAN.md`

STATE: CLAUDE ACCEPT - repair implemented, independently audited, and
verified against real evidence. See "2026-09-14: Claude ACCEPT" below.

## Governance

Treated as a privacy-relevant canonical safety defect, per explicit
User direction - not an availability/UX gap. Independent of, and
required before, M30.8 (see plan §9). Independent of M30.7C's own
separate evidence-closure scope, which may proceed on its own timeline
per the User's own separate decision.

## History Log

- 2026-09-13: Codex, then Claude independently, reproduced a defect
  where total model/provider unavailability still results in an
  unrelated statement being executed via `remember_fact` and persisted
  with a false `consent: "user_provided"` tag. Claude's own audit
  (`docs/plans/M30_7C_CLAUDE_AUDIT.md`) ruled out five of six candidate
  mechanisms via direct source inspection but left one open.
- 2026-09-13: At the User's explicit request, Claude completed the
  trace to an exact, confirmed root cause - not left as a hypothesis:
  1. `SkillMemory.find_matching_skill()` (`skill_memory.py:129-177`)
     matches on `task_type`/`domain` string equality **including
     empty-string-to-empty-string** - confirmed against the real
     `uri_workspace/skill_memory.json`, which contains a genuine entry
     with `task_type: ""`, `domain: ""`, `tool_name: "remember_fact"`,
     `success_count: 5`. A totally-degraded (provider-unreachable)
     semantic result, itself `task_type: ""`/`domain: ""`, spuriously
     matches this entry by coincidence, not relevance.
  2. `orchestrator.py`'s plan-selection cascade (lines 4704-4767) has
     an `elif learned_skill:` branch that gives a skill-memory match
     **direct execution authority** - `plan = {"status": "capability_
     selected", "tool_name": learned_skill.get("tool_name"), ...}`,
     routed straight to `ApprovalGate.execute_tool(...)`. This
     contradicts other in-file commentary claiming learned-skill
     direct-plan authority was already removed ("URI Correction Part
     1") - that removal was implemented only for the model's own
     prompt-context visibility (a separate code site, lines 770-780),
     not for this still-fully-active execution branch.
  3. `_run_acceptance_retention_step`/`_model_retention_candidate`
     (the previously-open candidate) are **ruled out**, confirmed by
     tracing their real call path: only reachable after a second,
     separate, *successful* model evaluation call, which itself fails
     safely (`evaluation is None` → honest `evaluation_unavailable`)
     under total provider unavailability - never reached in the
     reproduced scenario.
  4. `remember_fact.py`'s own `consent="user_provided"`-by-construction
     design is confirmed **not itself defective** - it correctly
     implements "if called, disclosure already happened," a premise
     that was true for every route its own documentation anticipated
     (Brain proposal, `capability_planner.py` scoring) but not for the
     `learned_skill` branch found in (2), which the tool's own
     documentation never accounts for.

  Produced `M30_PROVIDER_FAILURE_FALSE_CONSENT_REPAIR_PLAN.md`: the
  binding invariant (no genuine, live-turn intent signal → no memory
  write), the provider-failure degradation requirement, 5 required
  tests (including a same-server live re-verification and an explicit
  regression guard for the healthy-path disclosure case), a bounded
  two-candidate repair (fix `find_matching_skill()`'s empty-string
  matching and/or gate the `elif learned_skill:` branch on a live-turn
  signal - neither touches `remember_fact.py`/`MemoryStore`/consent
  model), and an explicit M30.8-blocking determination independent of
  M30.7C. Marked ACCEPTED under the standing auto-approval rule for
  the planning work itself; **implementation is a separate
  authorization the User has not yet given**. No production code
  written by Claude.

- 2026-09-13: User approved the plan with an architectural
  clarification: restore "learned skills must not have independent
  direct execution authority" as the primary safety boundary. Claude
  checked whether an unconditional version of this (Option A, full
  removal) fits bounded repair scope **before implementing anything** -
  it does not: `test_orchestrator_skill_memory_execution.py` (6 tests,
  re-run this round, 6/6 passing) exists specifically to prove learned
  skills *do* genuinely execute with no fresh Brain proposal ("Proves
  the Issue-1 fix"). Reported this exact conflict to the User per
  their own "stop and report before implementation" instruction rather
  than silently picking a side.

  User then specified the precise resolving condition: gate the
  existing fast path only during a genuine **model-failure state**
  (a required model call was attempted this turn and failed explicit/
  unreachable/timeout/fallback-exhausted) - explicitly not a merely
  *disabled* model path. Claude verified this closes the real defect
  (the reproduction's real usage-log records show genuine attempted-
  and-failed calls) while leaving all 6 existing tests untouched
  (confirmed directly: their fixtures use `enable_model_reasoning_
  shadow=False` and a fake interpreter that never raises - "disabled,"
  not "failed," under the User's own three-part test).

  Updated `M30_PROVIDER_FAILURE_FALSE_CONSENT_REPAIR_PLAN.md` §4-§7
  with the final, User-approved condition: gate `orchestrator.py`'s
  `elif learned_skill:` branch (lines 4742-4762) on "not in
  model-failure state" as the primary fix, plus `find_matching_skill()`'s
  empty-vs-empty rejection as defense-in-depth (both User-specified,
  Option A refined + Option B). Flagged one implementation precision:
  the semantic-interpretation except-handler must distinguish genuine
  unreachability from a merely-malformed-but-reached response - only
  the former is "model-failure state." Expanded required tests from 5
  to 8, including an explicit "existing legitimate learned-skill
  behavior is not silently broken" regression proof and a live re-run
  of the exact reproduced failure against a real server post-repair.
  No production source modified. Implementation remains a separate,
  not-yet-given authorization.

- 2026-09-13: User approved implementation exactly as planned (see
  history entry above) - recorded as milestone `M30-PFC` in
  `URI_ACTIVE_MILESTONE.md`, handed to Antigravity/Codex via
  `URI_AGENT_RELAY.md`. No source written by Claude.
- 2026-09-13: User conducted a broader product review of the remaining
  M30.8 readiness plan and, relevant to this repair specifically,
  broadened §5's degradation requirement to explicitly include "no
  approval-gated action, no other side-effecting capability" (not only
  `learned_skill`/`remember_fact`). Checked directly: already
  structurally satisfied by `capability_planner.py`'s own verified
  behavior - no new source scope implied. Added test #9 to plan §6
  (confirms this explicitly) and updated the required-verification
  counts in `URI_ACTIVE_MILESTONE.md`/`URI_AGENT_RELAY.md` from 8 to 9
  accordingly - a documentation/test-completeness refinement to the
  already-approved, in-progress implementation, not a new
  authorization. See `docs/plans/M30_8_BLOCKER_DISPOSITION_PLAN.md`
  § Product Decisions for the full review this update is part of.

- 2026-09-14: Claude ACCEPT. Per the User's temporary role-override
  ("Codex is near its usage limit. Claude is authorized to perform the
  bounded implementation for M30-PFC directly... Antigravity remains
  coordinator only"), Claude found the implementation already present
  on disk (written by Codex before pausing for quota) and independently
  verified every required item rather than trusting that it was
  correct:

  1. **`model_terminally_unavailable` computation** (`orchestrator.py`
     lines 4507-4514) traced and confirmed correct: derives from
     `semantic_result.get("interpretation_unreachable")` (set only when
     `AllProvidersUnreachableError` appears in the caught exception's
     `__cause__`/`__context__` chain - `orchestrator.py` lines 369-412)
     OR `model_reasoning.get("status") == "reasoning_failed"` with
     `"all providers exhausted"` in the error text. Cross-checked
     against `model_router.py`: `AllProvidersUnreachableError` (line
     34, message "All providers exhausted for role...") is the sole
     exception raised after the fallback chain exhausts
     `ProviderUnavailableError`/`ProviderTimeoutError`/
     `ModelNotFoundError`/`UnknownModelProviderError` - confirming this
     one condition correctly covers all of UNREACHABLE/TIMEOUT/
     FALLBACK_EXHAUSTED, and correctly excludes `"reasoning_disabled"`
     and malformed-but-reached responses (different status/message).
  2. **`skill_memory.py`'s defense-in-depth** (lines 150-153) confirmed
     present: `if not task_type and not domain: return None` before any
     matching is attempted.
  3. **All 9 required tests** confirmed present in
     `test_provider_failure_false_consent_repair.py`, matching plan §6
     exactly. Ran together with the 6 pre-existing
     `test_orchestrator_skill_memory_execution.py` tests: **15/15
     passed**.
  4. **`multi_action_dispatch.dispatch()`** independently read and
     confirmed to return `None` safely for a `reasoning_failed`-shaped
     `model_reasoning` (no `proposal`/`multi_action` key) - no side-
     effect gap outside the audited branch.
  5. **Live verification** - not merely trusted from the conversation-
     history file, independently cross-checked against raw telemetry:
     real usage log (`uri_workspace/users/86f1c37e.../usage/2026-09.jsonl`)
     shows genuine `outcome: "unreachable"` for both `semantic_
     interpretation` and `reasoning` roles at 2026-09-13T17:17:35Z with
     `fallback_from: ["ollama(failed:ProviderUnavailableError)"]` /
     `["ollama(unhealthy)"]`; the matching conversation turn
     (`m30_pfc_provider_failure_live.json`) returned the deterministic
     "URI could not reach its model provider..." response,
     `status: "unavailable"`; `user_memory.json` has zero Delhi/weather
     entries; `canonical_execution_log.jsonl` has no entry for that
     session - no `remember_fact` execution, no false `user_provided`
     provenance. The companion healthy-path disclosure
     ("I work at NIT Sikkim.") ran seconds later against real
     successful model calls (usage log: `outcome: "success"` at
     17:18:16-17:18:28Z) and correctly persisted with `consent:
     "user_provided"` at 17:18:24Z.
  6. **Scope boundary** confirmed via `git status`: only
     `orchestrator.py`, `skill_memory.py`, and the new test file carry
     M30-PFC changes. `remember_fact.py`, `MemoryStore`/
     `user_memory.py`, and `capability_planner.py` carry no changes
     from this repair.
  7. **Full regression**, run to a real, observed terminal result (not
     an unobserved/killed run): **8 failed, 1735 passed, 27 subtests
     passed in 1513.82s**. The 8 failures matched the plan's own cited
     baseline by name. Rather than accept that claim at face value,
     Claude independently re-derived it: temporarily `git stash`-ed
     only the two M30-PFC-touched files and re-ran the suspect test
     files against the pre-repair code. Identical failures reproduced
     in `test_m20_semantic_interpreter_resilience.py` (both tests),
     `test_m20_recovery_loop.py` (both tests), and
     `test_m20_feasibility_validation.py` - proving these are
     pre-existing, not caused by this repair. `step3_test.py::
     test_drive`/`step4_test.py::test_download` fail with an unrelated
     `DriveService` `AttributeError`, never touching orchestrator code
     this repair changed. `test_usage_import_boundary.py`'s newline-
     count guard was **already failing before this repair** (5542 >
     5460 baseline, confirmed via the same stash test) - this repair's
     ~162 added lines made an already-broken guard worse (5542 -> 5704)
     but did not cause the pre-existing violation. Changes were
     restored from the stash and re-verified intact (15/15 M30-PFC/
     learned-skill tests re-passed) after each comparison.

  **Self-audit verdict: ACCEPT.** All 7 items on the User's required-
  verification list are independently confirmed against primary
  evidence (source, telemetry, live conversation records, and a real
  completed regression run), not merely reported. No new regression
  was introduced. One pre-existing architecture-debt item is disclosed
  above (the orchestrator.py newline-count guard, already broken before
  this repair) rather than left unstated - it does not block ACCEPT,
  since fixing the file's overall size is out of this repair's approved
  scope and the guard's condition was already failing.  M30.8 remains
  NOT AUTHORIZED per the User's explicit instruction.

## Release gate

Per the 2026-09-12 live-verification-gate revision and this session's
standing AO-4 discipline: implementation against this plan requires
its own separate, explicit User authorization (not implied by this
plan's own ACCEPTED status). Once implemented, Claude independently
re-audits against real telemetry/session-state/response-body artifacts
and the required live re-verification (plan §8) before treating the
repair as closed. M30.8 remains blocked until this repair is accepted,
per plan §9 - independent of, and in addition to, M30.7C's own
separately-tracked evidence-closure gaps.
