# M35 URIv1 — A2.8L STATE

**Current state:** `VERIFICATION_READY`
**Milestone:** A2.8L — RAR Attachment-Order Evidence Transport Factorial
**Branch:** `m35-uri-v1-parallel-architecture`
**Plan:** `docs/plans/M35_URIV1_A2_8L_RAR_EVIDENCE_TRANSPORT_FACTORIAL_PLAN.md` (`FROZEN_READY_FOR_IMPLEMENTATION`)
**Overlay manifest:** `docs/plans/M35_URIV1_A2_8L_OVERLAY_MANIFEST.md`
**Execution report:** `docs/plans/M35_URIV1_A2_8L_EXECUTION_REPORT.md`

## Role note (standing governance exception for this task)

Per the pinned AO-4 development-cycle governance, Claude Code's standing role
is Architect / Pre-Auditor / Final Auditor / Bounded Fixer / Release
Authority, not primary implementer — substantial implementation normally
routes through Antigravity to Codex/Gemma. For this specific task, the User
gave direct, explicit authorization (live session, 2026-09-24) for Claude
Code to implement A2.8L directly as a one-off exception, after Claude flagged
the role conflict and asked. This STATE file and the execution report record
that authorization; it does not change the standing AO-4 role split for any
other milestone.

## A8 freeze checkpoint (plan §5.4)

Confirmed before any mechanism code was written. All 10 hashes recorded in
the overlay manifest §3 were independently recomputed against the working
tree and matched exactly (see execution report, "Freeze-checkpoint
verification").

## Implementation summary

- Mechanism module: `uri_v1/turn/rar_attachment_order_experimental.py`
- Fixtures: `uri_v1/turn/rar_attachment_order_factorial_fixtures.py`
- Battery script: `scripts/m35_a2_8l_rar_attachment_order_factorial.py`
- Tests: `tests/test_m35_uriv1_a2_8l_rar_attachment_order_factorial.py`
  (10 tests / 64 subtests, passing)
- Telemetry/aggregates: `docs/plans/M35_URIV1_A2_8L_TELEMETRY.json`,
  `docs/plans/M35_URIV1_A2_8L_AGGREGATES.json`

No protected file (plan §13.2) was modified. Pre/post protected-file hashes
are identical. No RAR contract field was added. No production integration,
commit, or push has occurred.

## Headline results

- 1,792/1,792 causal rows generated (64 cells × 14 rows × 2 repeats).
  Determinism: passed. Repeat reconciliation: reconciled.
- **1 qualifying cell** (`M=1,G=1,P=1,D=1,R=1,Q=0`), which is also the
  single minimal sufficient set.
- **Necessary factors:** M, G, P, D, R (each ablation individually breaks a
  frozen target — verified directly).
- **Q** is destructive when ON (confirms HQ); must remain OFF.
- **Transport conclusion:** `EXISTING_CONTRACT_COMPILATION_INSUFFICIENT`
  (90/196 rows mismatch; a subset of these is an H3-absence confound in the
  compiler arm, disclosed separately in the execution report — not
  attributed to the six factors). `NEW_CONTRACT_FIELD_REQUIRED` was never
  produced, per the plan's explicit prohibition.
- Full 18-case S-D confirmation battery: zero unexpected regressions.
  Existing A2.5/A2.8K regression suite (104 tests / 114 subtests): all pass,
  unchanged.
- Performance: all provisional §10.2 thresholds met under a disclosed
  reduced-iteration sample (20 warmups / 200 iterations vs. the
  pre-registered 200/2000) — directional, not final.

## Disclosed interpretive extensions (require independent audit sign-off)

1. A3 ordinal-trigger reading: hint-or-token match for "latest"/"first"
   (reuses baseline's own existing convention; required because the frozen
   `A-FIRST-2` target reuses `SD-A-06`, whose `recency_hint` is `"earlier"`,
   not `"first"`).
2. A2.8K's H3 lexical-compatibility mechanism reused unconditionally as an
   always-on substrate beneath the six A2.8L factors (required because two
   frozen §5.2 controls are otherwise unresolvable by raw baseline alone).
3. D/M's membership restriction extended to Level 5.5's generic
   attachment-identity counting, not only Level 5's ordinal branches
   (required because the frozen causal target `B-DISTRACTOR` has no ordinal
   wording and is otherwise unreachable by any of the six factors).

## Disclosed unreachable control (confirmed with User 2026-09-24)

`C-LEXICAL-ATTACHMENT` (`SD-A-08`) cannot be resolved by any combination of
the six frozen factors (Level 5.5's `is_attachment` counting has no lexical
consumer in scope). Per explicit User direction, it is excluded from the
"passes every control" qualification gate but still run and reported in
every cell (`reachable_by_factors: false`).

## RECOVERY STATE

```
required_model: none (implementation complete)
current_owner: Claude Code
resume_stage: VERIFICATION_READY -- awaiting independent audit
pause_reason: none (not paused; stopped per frozen plan's own mandatory
  independent-audit gate before acceptance/closure)
task: A2.8L RAR attachment-order evidence transport factorial
completed_steps:
  - A8 freeze checkpoint independently reproduced and confirmed
  - mechanism module implemented (M/G/P/D/R/Q + existing-contract compiler)
  - fixture module implemented (14 frozen decision rows)
  - 64-cell x 14-row x 2-repeat causal battery executed and reconciled
  - minimal-sufficient-set / necessity / pairwise-interaction analysis computed
  - bounded transport comparison executed (T=7, cap=16, not hit)
  - confirmation/regression surfaces executed (S-D battery + existing A2.5/A2.8K suite)
  - performance pass executed (reduced iteration count, disclosed)
  - telemetry, aggregates, execution report, this STATE file, and unit tests written
remaining_steps:
  - independent audit of: the three disclosed interpretive extensions, the
    C-LEXICAL-ATTACHMENT exclusion, and the transport-comparison confound split
  - User acceptance decision (ACCEPT / MODIFY / REOPEN) following that audit
  - no next experiment may start before that acceptance decision
changed_files:
  - uri_v1/turn/rar_attachment_order_experimental.py (new)
  - uri_v1/turn/rar_attachment_order_factorial_fixtures.py (new)
  - scripts/m35_a2_8l_rar_attachment_order_factorial.py (new)
  - tests/test_m35_uriv1_a2_8l_rar_attachment_order_factorial.py (new)
  - docs/plans/M35_URIV1_A2_8L_TELEMETRY.json (new)
  - docs/plans/M35_URIV1_A2_8L_AGGREGATES.json (new)
  - docs/plans/M35_URIV1_A2_8L_EXECUTION_REPORT.md (new)
  - docs/plans/M35_URIV1_A2_8L_STATE.md (new, this file)
git_state: no commit made; all files above are untracked/new in the working tree
test_state: tests/test_m35_uriv1_a2_8l_rar_attachment_order_factorial.py
  (10 passed / 64 subtests); existing A2.5/A2.8K regression suite (104
  passed / 114 subtests) -- all green as of this run
audit_state: NOT YET INDEPENDENTLY AUDITED -- this file and the execution
  report constitute the implementer's own self-report only
last_successful_checkpoint: causal battery + transport + confirmation +
  performance all completed in one run of
  scripts/m35_a2_8l_rar_attachment_order_factorial.py, telemetry/aggregates
  written to disk
retry_metadata: none (no retries were required; the two structural gaps
  found mid-implementation were resolved via the disclosed extensions above,
  confirmed with the User once, not via retry)
```

## Next action

Per the frozen plan's own instruction and the pasted task brief: **STOP —
INDEPENDENT AUDIT REQUIRED BEFORE ACCEPTANCE OR NEXT EXPERIMENT.** This
implementer (Claude Code, acting under the one-off role exception recorded
above) does not self-accept or self-close A2.8L.
