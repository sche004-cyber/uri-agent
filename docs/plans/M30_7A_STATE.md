# M30.7A State - Canonical Live Evidence Closure

**Plan:** `docs/plans/M30_7A_CANONICAL_LIVE_EVIDENCE_PLAN.md`

STATE: LIVE_VERIFIED + CLAUDE ACCEPT - M30.7A's own scope (evidence
closure + one bounded repair) is complete, honest, and independently
verified. The resulting finding, independently confirmed: M30.8 NOT
READY (6 of 12 mandatory scenarios still lack live closure; see
`docs/plans/M30_7A_CLAUDE_AUDIT.md`).

## Governance

Scope: close live-evidence gaps for the migration plan's 12 mandatory
acceptance scenarios (§14) under the current, unchanged allowlist-
scoped canonical system; resolve (not implement) the
`CANONICAL_EXECUTION_ALLOWLIST` design question for a future M30.8
plan; structurally audit (not perform) legacy-mechanism demotion; fix
one confirmed, bounded `pre_execution_check` capability_id-threading
defect; run a fresh full regression suite. M30.8 (global canonical
default, legacy retirement) remains out of scope and NOT authorized.

## History Log

- 2026-09-13: Codex applied the authorized pre-execution capability-id repair,
  added focused regression coverage (9/9 passing), and produced
  `M30_7A_CANONICAL_LIVE_EVIDENCE_REPORT.md`. The report's disposition is
  M30.8 NOT READY; no M30.8 change, legacy retirement, commit, or push.

- 2026-09-13: Claude produced `docs/plans/
  M30_8_CANONICAL_DEFAULT_CUTOVER_PRE_AUDIT.md` at User request -
  read-only, found only 3 of 12 mandatory scenarios have unambiguous
  real live proof, recommended a bounded evidence-closure milestone
  before any M30.8 authorization.
- 2026-09-13: User authorized Milestone M30.7A directly to Antigravity
  (`URI_ACTIVE_MILESTONE.md` §6a, `APPROVAL RELAY: USER DIRECT`) with a
  verbatim mandate closely matching Claude's own pre-audit findings.
  Antigravity requested Claude produce the M30.7A plan
  (`uri_workspace/dev_workflow/tasks/claude_m30_7a_plan_task.txt`).
- 2026-09-13: Claude produced `M30_7A_CANONICAL_LIVE_EVIDENCE_PLAN.md`:
  a binding LIVE_PASS/LIVE_FAIL/BLOCKED_BY_CURRENT_SCOPE/DOCUMENTED_
  ACCEPTED_RESIDUAL rubric per scenario, per-scenario execution notes
  grounded in this session's own prior evidence review, the allowlist
  A/B/C/D framing with a non-binding recommendation, a structural
  demotion audit specification, and - confirmed directly from source,
  not left as an open question - a real, bounded defect at
  `orchestrator.py:4586-4599` (`pre_execution_check`'s clarification
  branch never threads `capability_id` from the already-in-scope
  `model_capability_proposal`, the same class of gap M30.7 fixed
  elsewhere) with the exact fix specified, authorized as this
  milestone's one in-scope source repair. Marked ACCEPTED under the
  standing auto-approval rule. Authorization-channel deviation (User
  approved directly to Antigravity, not through Claude) disclosed in
  the plan document itself, not silently accepted. Handed back to
  Antigravity (`docs/governance/URI_AGENT_RELAY.md`) for routing to
  Codex. No production code written by Claude.

- 2026-09-13: Claude independently audited M30.7A directly against
  source (`orchestrator.py:4592-4600` - exact match to the specified
  fix), real telemetry (all 7 fresh-attempt session IDs in
  `canonical_execution_log.jsonl` cross-checked field-by-field against
  the report, zero discrepancies), and re-ran
  `test_workflow_continuation.py` (9/9, real observed output). Did not
  personally reproduce the full ~26-minute, 1734-test run.

  **Self-caught correction:** Claude also attempted a broader 23-file
  regression subset as extra corroboration; that command timed out,
  moved to background, and was later killed by the system for low
  memory before ever producing output. Claude's first version of this
  audit and its chat summary to the User incorrectly reported this
  subset as having run "clean" - no result was ever actually observed.
  Corrected in `docs/plans/M30_7A_CLAUDE_AUDIT.md` §6: the subset is
  excluded from the evidence basis; ACCEPT rests on the real 9/9
  focused-test result, the report's own full-suite run, and independent
  confirmation that all 8 claimed baseline failures are real files/
  tests, not on a fabricated "clean" claim. Verdict remains: **ACCEPT**
  (`docs/plans/M30_7A_CLAUDE_AUDIT.md`) - the milestone's job was
  honest evidence closure, not forcing every scenario to pass, and it
  delivered that correctly and safely. Independently confirmed the
  report's own **M30.8 NOT READY** disposition for the same
  substantive reason: 6 of 12 mandatory scenarios (2, 5, 6, 7, 8, 12)
  still lack real live closure, scenario 9 remains scope-blocked
  pending a future allowlist decision, and the M30.2 `WorkflowPlanner`
  template-inventory gap flagged in Claude's own pre-audit is now
  confirmed absent rather than merely suspected. M30.8 remains NOT
  AUTHORIZED - the User's decision, not implied by this verdict. No
  production code written by Claude.

## Release gate

Per the 2026-09-12 live-verification-gate revision: Codex implements/
verifies against this plan; Claude independently re-audits the
resulting report against real telemetry/session-state artifacts before
any `M30.8 READY`/`NOT READY` disposition is treated as final -
exactly as for every prior milestone this session (M30.6A, M30.7).
Claude does not perform live verification itself and does not simulate
Antigravity or Codex. M30.8 authorization remains the User's own,
non-delegable decision regardless of this milestone's outcome.
