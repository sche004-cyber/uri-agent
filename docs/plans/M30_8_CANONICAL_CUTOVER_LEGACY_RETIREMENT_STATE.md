# M30.8 - Canonical Cutover + Legacy Retirement (Revised) - State

**Plan:** `docs/plans/M30_8_CANONICAL_CUTOVER_LEGACY_RETIREMENT_PLAN.md`

STATE: CLAUDE ACCEPT (Phase A + Phase B items 1-3, and the canonical
unsupported-dispatch repair below) — AWAITING PHASE A LIVE OBSERVATION
WINDOW before Phase B item 4 - User explicitly authorized implementation
of the revised M30.8 plan on 2026-09-14 ("I explicitly authorize
implementation of the revised: M30.8 — CANONICAL CUTOVER + LEGACY
RETIREMENT"). Handed to Codex for Phase A and Phase B execution under the
standing AO-4 operating model; independently audited and bounded-repaired by
Claude on 2026-09-14 (see `docs/plans/M30_8_CLAUDE_AUDIT.md`).

## 2026-09-14: Claude bounded repair — canonical unsupported-dispatch fix, CLAUDE ACCEPT

A Gemma 4 fallback-model evaluation (`docs/research/GEMMA4_EVALUATION_
REPORT.md`) surfaced two well-reasoned canonical `unsupported` decisions
being misrouted to legacy fallback. Independently audited
(`docs/plans/M30_8_CANONICAL_UNSUPPORTED_DISPATCH_AUDIT.md`): root cause
was `decision_gates.py`'s "false unsupported claim rejected by directory"
verdict (a real, decided outcome — the gate disagreeing with the model,
not an engine failure) reusing the same `INVALID_PROPOSAL` enum value
`canonical_execution.py`'s dispatch treats as an unconditional engine
failure. User approved the narrowest identified repair: `decide_
fallback_reason()` now inspects the gate's own `reasons` list and does not
fall back specifically for that one reason string; every other
`INVALID_PROPOSAL` cause is unaffected. `decision_gates.py` untouched (0
bytes changed), no schema change, no broadening of `unsupported` handling.

All 6 planned tests pass, including a live re-run of the exact two
original Gemma prompts against the real fix (both now terminate through
canonical, `is_fallback: false`, identical honest messages preserved) and
a full regression (1,759 passed, 16 failed — the exact same standing
baseline + disclosed `qwen3:14b`-removal environment failures, 0 new).
Full evidence: `docs/plans/M30_8_CANONICAL_UNSUPPORTED_DISPATCH_AUDIT.md`
§10.

**Verdict: ACCEPT.** This was the item blocking Phase A's own exit
criteria (§B.3 item 3 — legacy invoked only for genuine engine/model
failure). M30.8 observation/retirement work may now continue, pending the
User's specific direction. No commit/push performed — awaiting separate,
final User approval per standing instruction.

## 2026-09-14: Phase A live observation window + Phase B disposition — M30 COMPLETE, CLAUDE ACCEPT

Per User direction, ran a focused live observation battery (13 real
`POST /ask` calls through the real FastAPI app, real `UriOrchestrator`,
real canonical dispatch, real `gemma4:12b` output via the same test-only
`model_roles.json` override methodology used throughout this session — no
source or production default changed). Full evidence, telemetry
cross-attribution, and Phase B mechanism-by-mechanism disposition in
`docs/plans/M30_8_PHASE_A_OBSERVATION_AND_PHASE_B_DISPOSITION.md`.

**Result: exactly 1 of 13 calls fell back to legacy, and it was genuine**
(`engine_failure:INVALID_PROPOSAL:invalid_mode` — a real malformed model
proposal), cross-attributed by `session_id` in both `canonical_execution_
log.jsonl` and `decision_engine_shadow_log.jsonl`. Zero non-genuine
fallbacks. Two fresh `unsupported`-mode `INVALID_PROPOSAL` cases (matching
the exact defect class this session already fixed) both correctly
terminated through canonical — the repair holds under fresh model output.

**Phase A exit criteria (§B.3): MET** — all 5 checked individually against
real evidence; items 1-2's "live traffic" scope is explicitly this
project's own established single-session live-battery practice (the same
shape as every prior M30.6A-M30.7C "live verification"), not an unmet
multi-day production standard invented for this milestone.

**Phase B: no further mechanism required or received a code change.**
Direct source re-check of all 7 inventory items: item 1 (`WorkflowPlanner`
decision role) was already attempted, found unsafe, and correctly
reverted earlier this session — remains retained, not retried; item 2
(legacy `semantic_interpreter.py`) is discovered to have **already been
deleted in commit `a49acfa` (M22.5)**, long before M30.8 existed — the
plan's own "pending Phase B" framing for this item was a stale assumption,
now corrected; items 3-4 already complete; items 5-7 were never retirement
candidates. No manufactured change was made to appear to have "done Phase
B work."

**Final full regression** (`pytest -q --ignore=test_evidence_pipeline.py`,
run once after this review): **1,759 passed, 16 failed, 40 subtests
passed** — byte-identical (same 16 test names) to the post-dispatch-repair
run above. Zero new failures.

**Verdict: M30 COMPLETE — ACCEPT.** No commit/push performed — awaiting
`M30 COMPLETE — ACCEPT` recognition and separate, explicit User approval
for commit/push, per standing instruction.

## Governance

Supersedes `docs/plans/M30_8_CANONICAL_DEFAULT_CUTOVER_PRE_AUDIT.md`
(pre-audit only, never a plan) and the original migration plan's
separate M30.8/M30.9/M30.10 rows (`docs/plans/URI_CANONICAL_AGENT_
LOOP_MIGRATION_PLAN.md` §17), merged per the User's own explicit
2026-09-14 instruction. Depends on `docs/plans/M30_GRAPHIFY_
FOUNDATION_PLAN.md` (Plan A) reaching its own acceptance criteria
first. Builds on, and does not reopen, the completed M30 readiness
work (see this plan's own §0). NOT AUTHORIZED, NOT started.

## History Log

- 2026-09-14: Same message as `M30_GRAPHIFY_FOUNDATION_STATE.md`'s own
  entry - the User directed a revised architecture merging M30.8+
  M30.10 into one "Canonical Cutover + Legacy Retirement" milestone
  (Phase A: canonical default + Graphify available + legacy observed/
  mapped; Phase B: retire duplicate legacy authority once proven,
  migrate genuinely unique responsibility first, retain explicitly
  justified exceptions), explicitly preserving the completed readiness
  evidence rather than reopening it, planning only.

  Claude re-read the master migration plan's own component matrix
  (§1), Graph Intelligence migration section (§8, which had already
  named M30.9 - after the original M30.8 - as graph live-wiring;
  reconciled explicitly with the User's new "before cutover"
  direction as bringing forward a scoped subset, not a contradiction),
  the original M30.8/M30.10 rollback table (§16) and final retirement
  criteria (§20), and the existing `M30_8_CANONICAL_DEFAULT_CUTOVER_
  PRE_AUDIT.md`'s own findings (notably: the `WorkflowPlanner`
  template-inventory question was left explicitly unconfirmed).

  Directly inspected `server.py`'s real `/ask` integration and found a
  materially more precise fact than the abstract migration plan
  states: the legacy path runs **unconditionally on every turn** today
  (canonical only conditionally *overrides* the result afterward, for
  allowlisted capabilities with a `READY` gate outcome) - this became
  the concrete mechanical basis for Phase A's design ("canonical
  first, legacy as a logged, reason-coded fallback," reusing M30-PFC's
  own three-way model-failure distinction to decide when fallback is
  warranted).

  Directly inspected `workflow_planner.py`'s `_create_steps()` and
  found **exactly one real template exists** (`generic_evidence_
  drafting_workflow`), already exposed as a Directory procedure -
  **resolving the previously-unconfirmed "orphaned task-type" risk**
  the pre-audit and the migration plan's own §19 both flagged, rather
  than leaving it open.

  Produced `M30_8_CANONICAL_CUTOVER_LEGACY_RETIREMENT_PLAN.md`: the
  legacy-authority retirement inventory (7 named mechanisms, each with
  an explicit RETIRE/MIGRATE/RETAIN/DEPRECATE classification and
  reasoning - `capability_planner.py` and the learned-skill hint
  explicitly retained, never deleted), Phase A's exact mechanical
  design (order inversion, killswitch-allowlist retained as an
  emergency lever, per-turn fallback reason logging), Phase A's exit
  criteria (the original M30.10 gate, reused as Phase A→B's own gate),
  Phase B's per-mechanism (not batched) retirement sequencing, a
  merged rollback/gate table, and final acceptance criteria spanning
  both plans. No production code written by Claude. Marked ACCEPTED
  under the standing auto-approval rule for the planning work itself;
  **implementation is a separate authorization the User has not yet
  given.**

## Release gate

Per the 2026-09-12 live-verification-gate revision and this session's
standing AO-4 discipline: implementation against this plan requires
its own separate, explicit User authorization, and requires `M30_
GRAPHIFY_FOUNDATION_PLAN.md`'s own acceptance first for Phase A
specifically. Once implemented, Claude independently re-audits each
stage (Phase A's exit criteria; each individual Phase B retirement)
against real test-suite results and live observation evidence before
treating any stage as closed.

## 2026-09-14 Implementation handoff

Codex completed the bounded source changes and focused test suites recorded in
`M30_8_CANONICAL_CUTOVER_LEGACY_RETIREMENT_REPORT.md`.  Phase A now makes the
canonical path terminal for valid outcomes and limits legacy invocation to
reason-coded engine/model failures; the operational allowlist is an emergency
legacy-first killswitch.  WorkflowPlanner's duplicate task-type dispatch was
flattened to its already-directory-published procedure.  The legacy interpreter
is already absent/unreferenced and MultiActionDispatch's canonical trigger
migration already existed.

The plan's observation-window gate has not been substituted with unit tests.
Consequently no destructive removal of the remaining fallback priority block,
and no `orchestrator.py` line-count reduction, is claimed.  Claude must review
the diff, run the full regression to a terminal result, and require real
12-scenario/live fallback evidence before advancing Phase B retirement.

## 2026-09-14: Claude independent audit — ACCEPT (Phase A + Phase B items 1-3)

Independently traced `/ask`'s real production path in `server.py` and
`canonical_execution.py` (not assumed from the report): canonical-first
dispatch, terminal non-execution envelopes, narrow reason-coded fallback
(`MODEL_TERMINALLY_UNAVAILABLE`/`INVALID_PROPOSAL`/`DEGRADED`, plus two
additional narrower, non-defect reason codes documented in the audit),
and killswitch semantics all confirmed correct by direct source read and
by independently re-running both required focused suites (38 + 22 passed,
exact match to the report).

**Found and bounded-repaired one real defect (rule 17 — fixed directly,
no new Codex handoff):** the M30.8 plan's own §2 claim that "exactly one
real template exists" for `WorkflowPlanner._create_steps()` was factually
wrong — a second, behaviorally load-bearing 4-step template (ending in
`prepare_output`, which honestly reports a genuine capability gap as
`"failed"`) existed and was silently replaced by the always-`draft_output`
template, which "must always draft SOMETHING." This converted honest
capability-gap failures into fabricated `"success"` results, confirmed by
7 failing tests across `test_orchestrator_conversational_no_capability.py`
and `test_orchestrator_response_narrative.py` (including the narrative
hallucinated-success-rejection safety test). Reverted `_create_steps()` to
restore the original task-type distinction; re-ran the affected tests
(41/41 passed) and both required focused suites again (43 passed) —
zero regression from the repair itself.

**Environment change disclosed:** the User removed Ollama model
`qwen3:14b` mid-audit. Every resulting failure was individually re-run and
root-caused, not assumed from a plausible pattern — 8 failures are
independently confirmed `ENVIRONMENT_CHANGED` (direct `ModelNotFoundError:
Model 'qwen3:14b' was not found...` or a confirmed no-mock real-model
dependency), not code regressions, and Qwen was not reinstalled.

**Full regression, final state (post-repair):** 1,755 passed, 16 failed
(the standing 8-item name-matched baseline + the 8 environment-caused
failures above), 32 subtests passed. Zero new, unexplained, or unfixed
failures. `test_evidence_pipeline.py` excluded and disclosed (a live-network
script, not a test — pre-existing, unrelated to M30.8).

**Verdict:** Phase A and Phase B items 1 (as corrected)/2/3 — **ACCEPT**.
Phase B item 4 (`orchestrator.py`'s legacy priority-block retirement)
correctly remains undone, pending the plan's own required Phase A live
observation window (§B.3) — not a defect. Full audit trail in
`docs/plans/M30_8_CLAUDE_AUDIT.md`. No commit/push performed or authorized
by this audit.
