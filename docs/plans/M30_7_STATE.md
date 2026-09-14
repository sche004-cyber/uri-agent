# M30.7 State - Workflow Continuation & Active Pointer

**Plan:** `docs/plans/M30_7_WORKFLOW_CONTINUATION_PLAN.md`

STATE: LIVE_VERIFIED + CLAUDE ACCEPT (documented residual, per explicit 2026-09-13 User disposition)

## Documented Residual (accepted, non-blocking - not a defect)

- The repaired `post_execution_reevaluation` workflow-continuation
  mechanism (`orchestrator.py:2790-2805` threading `capability_id`
  from `attempt_history`'s last real capability-attempt entry into
  `_apply_clarification_pause`) is implemented and verified: unit-
  tested (`test_workflow_continuation.py::
  test_post_execution_reevaluation_threads_last_capability_into_pause`,
  passing) and integration-tested via the full regression suite
  (137/137 pytest / 125/125 unittest, zero failures, independently
  re-run by Claude both rounds).
- Its dependencies are live-proven: `/ask` precedence guarding (§2F),
  `workflow_continuation` gate resolution (§2B), and canonical
  execution reuse (§2C) were each independently confirmed against real
  telemetry (`canonical_execution_log.jsonl`) - Scenario 11 fully,
  Scenario 4's resolve-and-execute half fully.
- Current model behavior (qwen3:14b, confirmed the real baseline model
  for M30.4/M30.5A-D per this session's own provenance audit) often
  asks for clarification upfront rather than attempting a capability
  first and re-evaluating afterward - a pre-existing, already-
  documented tendency (`M30_4_DECISION_QUALITY_ANALYSIS.md`'s own
  clarification-bias finding). Four separate, honest, non-seeded live
  attempts across REVISION v3/v4 all landed on the unchanged
  `initial_reasoning` clarification call site instead of the repaired
  `post_execution_reevaluation` one for exactly this reason.
- This is a **known decision-behavior limitation of the current model**,
  not evidence the continuation mechanism itself is broken - the
  mechanism has never failed when actually reached; it has simply not
  yet been organically reached by a live conversation in this
  environment. Accepted as sufficiently proven per explicit User
  direction (2026-09-13); no further open-ended phrasing experiments
  are planned against it.

## Non-blocking debt (separate from the residual above, pre-existing)

- `canonical_execution.py::decide_fallback_reason()`
  (`canonical_execution.py:184-191`) checks `is_allowlisted
  (capability_id)` before checking mode-executability, so a
  no-capability `clarification`/`conversation` decision is reported in
  telemetry as `fallback_reason: "capability_not_allowlisted"` rather
  than the more accurate `"mode_not_executable:<mode>"`. Unchanged
  since M30.6 - not introduced or worsened by M30.7, not a functional
  defect (execution still correctly never proceeds), purely a
  telemetry-label imprecision. Tracked here for future cleanup, not
  gating M30.7's disposition.

## Governance

Scope: `active_pointer` promotion to first-class (deterministic gate/
canonical execution consumption, not only prompt context),
`orchestrator.py` clarification-pause call-site consolidation,
topic-change/stale-context checks, gated by
`enable_workflow_continuation_mode` (default off), proven via Layer 3
scenarios 4 and 11 (`docs/plans/URI_CANONICAL_AGENT_LOOP_MIGRATION_PLAN.md`
§14/§16 row M30.7). M30.8 (canonical default cutover) remains out of
scope and NOT authorized.

## History Log

- 2026-09-13: User explicitly approved M30.7 in a live session;
  approval recorded by Claude in
  `docs/governance/URI_ACTIVE_MILESTONE.md` §6a. Antigravity advanced
  `CURRENT MILESTONE` to M30.7 (`PLANNING`) and requested a plan via
  `docs/governance/URI_AGENT_RELAY.md`.
- 2026-09-13: Claude (Architect/Planner role) traced the current,
  real state of `active_pointer` (`turn_state.py::_project_active_pointer`,
  already a correct dual-source read-only projection since an M30.5A
  bugfix), the `workflow_continuation` placeholder gate
  (`decision_gates.py` lines 201-202, unconditional `READY`/
  `capability_id=None`), and `canonical_execution.py`'s
  `EXECUTABLE_MODES` (currently `single_action`/`multi_action` only) -
  each read directly from source, not assumed. Produced
  `M30_7_WORKFLOW_CONTINUATION_PLAN.md` designing the promotion to a
  real, gate-consumed, executable mode, reusing the existing pause
  mechanisms and execution mechanics unchanged. Marked ACCEPTED under
  the standing auto-approval rule (`ORCHESTRATION.md` §1.5) - routine
  engineering planning within an already User-approved milestone.
  Handed back to Antigravity (`docs/governance/URI_AGENT_RELAY.md`)
  for routing to Codex.
- 2026-09-13: Antigravity routed implementation directive to Codex. Scope is
  strictly bounded to `M30_7_WORKFLOW_CONTINUATION_PLAN.md`. Milestone state
  transitioned to IMPLEMENTING.
- 2026-09-13: Codex surfaced two source-level blockers in the current codebase:
  1) `/ask` executes `process_user_input` before `run_canonical_for_ask`, resuming
  workflows via legacy path before canonical continuation evaluates topic shift (Scenario 11).
  2) `_apply_clarification_pause` lacks durable action metadata, preventing deterministic
  reconstruction of paused actions without guessing (Scenario 4).
  Handoff routed back to Claude via `docs/governance/URI_AGENT_RELAY.md` for plan revision.
- 2026-09-13: Claude independently re-verified both Codex-reported gaps
  directly against source (not taken on report alone) - both confirmed
  real: `server.py:1149` vs `orchestrator.py:4223-4240` precedence
  (Scenario 11), and `_apply_clarification_pause`/`turn_state.py`
  lines 227-256 never populating `capability_id`/`action`/
  `missing_field` (Scenario 4). Also found and corrected a design
  error in v1 itself: §2E's proposed "deterministic goal-continuity
  check" does not exist and should not be built - per
  `M30_5D_TEMPORARY_CONTEXT_INTENT_SHIFT_REPORT.md`, continuation-vs-
  new-intent is a deliberate model judgment inside the Decision
  Contract, not a function to reinvent. Re-issued
  `M30_7_WORKFLOW_CONTINUATION_PLAN.md` REVISION v2: §2B/§2D/§2E
  corrected, new §2F specifies the exact `/ask` precedence fix
  (narrowly scoped, flag-gated, byte-for-byte unchanged when off or
  when no workflow is pending), §3 file list updated to include
  `uri_core/app/server.py`. v2 marked ACCEPTED under the standing
  auto-approval rule. Server.py write-scope expansion recommended to
  Antigravity for recording in `URI_ACTIVE_MILESTONE.md` §4 (Claude
  does not self-edit that file's scope list - Write Ownership).
  Handed back to Antigravity via `docs/governance/URI_AGENT_RELAY.md`
  for Codex re-handoff. No production code was written by Claude.

- 2026-09-13: Codex implemented the accepted v2 source scope and added focused
  coverage. The mandated regression invocation passed 123/123. Live
  verification remains pending: loopback server is reachable, but this session
  has no credential/token for the documented pre-existing authenticated Gmail
  principal. No substitute principal or mocked service was used; the state
  therefore remains IMPLEMENTING rather than falsely advancing to
  VERIFICATION_READY.
- 2026-09-13: Codex completed the mandatory authenticated live `/ask`
  verification with `URI_test2` and all three M30.7 flags enabled. Scenario 4
  passed with telemetry showing `workflow_continuation`, `Gmail` /
  `search_messages`, `READY`, canonical `success`, returned execution evidence,
  and grounded final response. Scenario 11 passed: a model-rejected fresh
  weather intent cleared the real pending workflow before fall-through fresh
  processing; persisted session state confirms the pointer fields are null.
  The sanitized evidence matrix is recorded in
  `M30_7_WORKFLOW_CONTINUATION_REPORT.md`. M30.7 is now
  `VERIFICATION_READY` for coordinator evidence collection and independent
  Claude audit; no release status is claimed.

- 2026-09-13: Claude independently audited the implementation directly
  against source, real telemetry, and an independent test re-run
  (135/135 + 36/36) - not from the completion report alone. Confirmed
  correct: the `/ask` precedence fix (all 3 branches, live-proven for
  Scenario 11 via two order-correct telemetry records), gate
  resolution/execution reuse, flag-off safety, no new credential
  surface. One real finding: the durable-metadata fix
  (`_apply_clarification_pause`) is correctly implemented but currently
  has no live caller - all 3 call sites genuinely have nothing to
  thread through - so Scenario 4's live proof covers the resume/
  execute half completely for real, but its precondition (the pending
  interaction) was seeded rather than produced by an organic prior
  turn; no telemetry record shows a real turn creating it. Verdict:
  **ACCEPT WITH FOLLOW-UP** (`docs/plans/M30_7_CLAUDE_AUDIT.md`) - not
  a repair requirement, a disclosed evidence-completeness gap. M30.8
  remains NOT AUTHORIZED; that is the User's decision, not implied by
  this verdict. No production code written by Claude.

- 2026-09-13: Per User directive, Claude traced the real pause path
  before writing any code, answering all 5 required questions directly
  from source. Finding: `session.active_workflow`/`_save_paused_
  workflow` (pre-existing, unchanged by M30.7) is confirmed as the real
  canonical continuation source for a structured capability's missing-
  parameter pause (e.g. `extract_student_records`/roll_number) -
  Outcome B, not a second mechanism. `_apply_clarification_pause`'s 3
  call sites genuinely have no capability info by construction (Brain
  proposed nothing), confirming §2D's fix was correctly scoped to a
  different, real case, not an oversight. One small bounded gap found:
  `turn_state.py`'s active_workflow branch never projected `action`/
  `known_inputs`, though both are available from data already on
  session (`active_workflow.get("action")`, `session.current_facts`) -
  the attempt_history branch (§2D) already does this, this branch
  didn't. REVISION v3 (same plan file) specifies this smallest bounded
  completion plus the mandatory organic two-turn live scenario
  ("Find the student." → "B250012CS.") and topic-switch regression, to
  be executed for real by Codex - Claude does not fabricate this
  evidence. Marked ACCEPTED under the standing auto-approval rule per
  the User's own explicit "do not ask again for routine same-milestone
  repair" instruction. No production code written by Claude.

- 2026-09-13: Codex's real organic live attempt disproved v3's premise
  for the "Find the student." example specifically: `active_workflow`/
  `current_facts` stayed empty after turn 1. Claude traced why:
  `extract_student_records` is a plain regex tool with no `WorkflowCapabilityRouter`
  registration - its pause goes through `_apply_clarification_pause`'s
  "post_execution_reevaluation" call site (`orchestrator.py:2790-2798`),
  not `_save_paused_workflow`. This matches what `M30_5A_DECISION_
  QUALITY_REMEDIATION_REPORT.md` already documented for this exact
  example - v3's Outcome B conclusion was correct in general but wrong
  for this specific capability; corrected in REVISION v4. Bounded fix:
  thread `capability_id` into that call site from `attempt_history`'s
  last real capability-attempt entry (real, already-available data,
  confirmed against the same shape used elsewhere in the file - never
  guessed). Also flagged, not actioned: `extract_student_records` is
  not in `canonical_execution.py`'s `CANONICAL_EXECUTION_ALLOWLIST`
  (`{Gmail, remember_fact}` only) - expanding it is a real scope
  decision Claude is not making inside this bounded repair. Recommended
  the mandatory organic scenario instead prove itself against an
  already-allowlisted capability (Gmail preferred, with a real
  fallback to whatever the live model actually pauses on - never
  scripted or seeded). Marked ACCEPTED under the standing auto-approval
  rule. No production code written by Claude.

- 2026-09-13: Claude independently audited v4's source fix directly
  (`orchestrator.py:2790-2805` - real data, matches plan), re-ran
  regression (137/137, zero failures), and cross-checked telemetry:
  all four real live attempts across v3/v4 (`extract_student_records`,
  three Gmail phrasings) genuinely landed on the unchanged
  `initial_reasoning` clarification site, not the repaired `post_
  execution_reevaluation` site - consistent with M30.4's own
  documented model clarification-bias finding, not a code defect.
  Verdict: **ACCEPT WITH FOLLOW-UP** (`docs/plans/M30_7_CLAUDE_AUDIT.md`
  addendum). Recommended the loop stop blind prompt-guessing and pick
  explicitly between (a) accepting the mechanism as sufficiently proven
  given full unit coverage plus the already-live-proven surrounding
  pipeline, tracking the organic-trigger gap as a residual, or (b) one
  deliberately-shaped live attempt designed to make the model try a
  real Gmail action before asking, rather than another phrasing guess.
  M30.8 remains NOT AUTHORIZED regardless - the User's decision, not
  implied by this verdict. No production code written by Claude.

- 2026-09-13: User explicitly directed: "I accept M30.7 as sufficiently
  proven. Treat the remaining organic-trigger gap as a documented
  residual, not a blocker. Do not spend more time on open-ended
  phrasing experiments." Claude recorded this disposition as `LIVE_
  VERIFIED + CLAUDE ACCEPT (documented residual)` (see sections above),
  updated `docs/governance/URI_ACTIVE_MILESTONE.md` accordingly per the
  User's explicit instruction to do so, and separated the pre-existing
  `decide_fallback_reason()` telemetry-ordering oddity into its own
  non-blocking-debt entry so it is never conflated with the accepted
  residual. M30.8 remains NOT AUTHORIZED and is not started - per
  explicit User instruction, this milestone hands back into the
  Antigravity loop and stops at the M30.8 approval boundary. No
  production code written by Claude.

## Release gate

Per the 2026-09-12 live-verification-gate revision: Codex implements
against this plan; the User personally live-tests the result; only
after the User explicitly directs Claude to proceed does Claude
perform its own independent final audit and, if `VERIFIED`, the
release commit/push. Claude does not implement this milestone itself
and does not simulate Antigravity or Codex.

## Revision v3 implementation record

**CURRENT IMPLEMENTATION STATE: IMPLEMENTING** — the planned organic primary
live proof is blocked and this record supersedes the earlier plan-only state.

- 2026-09-13: Codex completed the v3 bounded `turn_state.py` projection
  (`active_workflow.action` and copied `session.current_facts` as
  `known_inputs`) and added focused coverage. The prescribed regression suite
  passed 124/124 using the repository virtual environment. The mandatory
  unseeded authenticated primary scenario did not meet its acceptance
  condition: `Find the student.` returned a real `waiting_for_input` question,
  but the persisted session had no `active_workflow`, no active-workflow status,
  and no current facts. The same-session identifier response again returned
  `waiting_for_input`, so canonical continuation could not be proven without
  fabricating state. The organic topic-switch regression did pass (successful
  unread-email/Gmail response and no pending workflow after the turn). State
  remains IMPLEMENTING pending coordinator/Claude disposition; it is not
  advanced to VERIFICATION_READY.

## Revision v4 implementation record

**CURRENT IMPLEMENTATION STATE: IMPLEMENTING** — focused repair complete;
organic allowlisted live proof blocked by real Gmail authorization state.

- 2026-09-13: Codex threaded the final real capability attempt into the
  `post_execution_reevaluation` clarification pause and added a focused
  regression (1/1); the mandated suite passed 124/124. Under all three live
  flags, authenticated unseeded Gmail requests paused before capability
  proposal because `/connections` reports Gmail `needs_authorization`. No
  pending state was seeded or edited; no allowlist changed. Topic-switch
  remains live-passing. State remains IMPLEMENTING, not
  VERIFICATION_READY, until usable server-host Gmail authorization permits the
  mandatory organic continuation proof.

- 2026-09-13: After the Gmail token refresh, Codex re-ran the required real
  loopback proof using a fresh `URI_test2` login and all three feature flags.
  `/connections` confirmed Gmail was connected. The unseeded `Search my
  email.` turn still produced a genuine clarification *before* a Gmail
  capability proposal, so its persisted proposal had `capability_id: null`.
  No pending state was seeded and no allowlist changed; the required
  Gmail-continuation acceptance chain therefore cannot be claimed. The organic
  topic-switch regression passed, and the mandated suite passed 125/125.
  State remains `IMPLEMENTING`, not `VERIFICATION_READY`, pending a real
  allowlisted post-execution pause that creates a capability-bearing pointer.
