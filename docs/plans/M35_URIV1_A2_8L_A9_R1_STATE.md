# M35 URIv1 — A2.8L-A9-R1 STATE

**Current state:** `VERIFICATION_READY_FOR_REAUDIT`
**Milestone:** A2.8L-A9-R1 — bounded repair of A2.8L-A9 after independent audit (`REPAIR_REQUIRED`)
**Branch:** `m35-uri-v1-parallel-architecture`
**Frozen checkpoint governing this round:** `591f806` (A9 plan/manifest; unchanged by this round)
**Plan:** `docs/plans/M35_URIV1_A2_8L_RAR_EVIDENCE_TRANSPORT_FACTORIAL_PLAN.md` §16 (unchanged; no A10)
**Independent audit that triggered this round:** `docs/plans/M35_URIV1_A2_8L_A9_INDEPENDENT_AUDIT_REPORT.md` (verdict `REPAIR_REQUIRED`)
**Repair report:** `docs/plans/M35_URIV1_A2_8L_A9_R1_REPAIR_REPORT.md`
**Predecessors (preserved byte-unchanged, not superseded):** `docs/plans/M35_URIV1_A2_8L_STATE.md` (pre-A9), `docs/plans/M35_URIV1_A2_8L_A9_STATE.md` (A9)

## Role note

Per the pinned AO-4 governance's bounded-fixer authority: Claude Code found this
defect via its own independent final audit of A2.8L-A9, and repairs a
bounded, in-scope defect directly (audit -> fix -> re-audit) without
returning to Antigravity/Codex/Gemma. This is not unrestricted
implementation authority — the repair is limited to the audit's own
ER-1..ER-9 findings and the single-line IR-1 mechanism deviation; no
architecture, scope, or frozen semantic was changed.

## Mechanism change (the only production/experimental code edit this round)

`uri_v1/turn/rar_attachment_order_experimental.py:444` — the A9-2 Level-5.5
membership-restriction trigger now checks `is_attachment` over
`candidates_list` (Level 5.5's own pool) instead of `l5_pool_lexical`
(Level 5's H3-filtered ordinal pool), matching plan §16.1 A9-2's literal
text ("the pool member under evaluation"). Verified: 0/896 factorial
decisions changed; `NB-C-04` C2 D1RQ row corrected from
`WRONG_AMBIGUITY_DOMAIN` to matching its expected outcome.

## Evidence/reporting repairs (script-level; no other mechanism file touched)

New script `scripts/m35_a2_8l_a9_r1_rerun.py` (does not modify or overwrite
`scripts/m35_a2_8l_a9_rerun.py` or its A9 evidence). Implements ER-1
through ER-8 (see repair report §10; ER-9 is a governance-document text fix
flagged but not made this round).

## Headline results (unchanged qualifying cell; corrected interpretation/evidence)

- **1 qualifying cell**, unchanged: `M1G1P1D1R1Q0`.
- Necessity re-attributed per-case (no "5-way joint requirement" claim);
  `M×D` and `G×P` reported as genuine two-factor interactions on the
  qualifying-cell background.
- Transport: 88/196 mismatches (was 90), 0 unexplained, corrected
  attribution taxonomy, factor-state parity applied per plan §16.3 item 4.
- Natural/D1RQ surface: 54 raw mismatches against `expected_by_reference`,
  all three attributed causes, **0 unexplained**.
- Performance: wall time genuinely globally interleaved; CPU now
  measured (not `UNMEASURED`) via interleaved batched sampling; all four
  §10.2 threshold families pass.
- Raw-baseline equivalence (A9-4) measured and reported explicitly: all
  diffs attributable to the accepted H3 substrate, none to A2.8L's own
  factors.
- Regression: 119 tests / 178 subtests, all passing.
- Protected-file and mechanism-file hashes: unchanged / cross-process
  identical.

## RECOVERY STATE

```
required_model: none (repair round complete)
current_owner: Claude Code
resume_stage: VERIFICATION_READY_FOR_REAUDIT -- awaiting independent re-audit
pause_reason: none (stopped per the repair task's own instruction: do not
  self-accept or self-close after a bounded fixer repair)
task: A2.8L-A9-R1 bounded repair of the RAR attachment-order evidence
  transport factorial after independent-audit verdict REPAIR_REQUIRED
completed_steps:
  - IR-1 mechanism repair (one line, uri_v1/turn/rar_attachment_order_experimental.py:444)
  - verification: 0/896 factorial decisions changed; NB-C-04 C2 corrected
  - regression suite rerun (119 passed / 178 subtests)
  - new script scripts/m35_a2_8l_a9_r1_rerun.py implementing ER-1..ER-8
  - two independent fresh-process causal runs (1792 rows each, deterministic)
  - per-case minimal-set / interaction-table recomputation (ER-1/2/3)
  - D1RQ/natural surface rescored against expected outcomes (ER-4), 0 unexplained
  - transport comparison rerun with factor-state parity + corrected taxonomy (ER-5)
  - performance rerun with genuine interleaving + batched CPU sampling (ER-6)
  - raw-baseline equivalence measured and reported (ER-7)
  - A2.5 seven-cell applicability reconciled and disclosed (ER-7)
  - UNTRUSTWORTHY_ORDER_BIND reachability repaired (ER-8)
  - repair report and this STATE file written
remaining_steps:
  - independent re-audit of this repair round
  - ER-9 (overlay manifest §5 text correction) -- governance-doc edit,
    flagged, not made this round
  - User acceptance decision following re-audit
  - no next experiment may start before that acceptance decision
changed_files:
  - uri_v1/turn/rar_attachment_order_experimental.py (mechanism repair, IR-1)
  - scripts/m35_a2_8l_a9_r1_rerun.py (new)
  - docs/plans/M35_URIV1_A2_8L_A9_R1_TELEMETRY.json (new)
  - docs/plans/M35_URIV1_A2_8L_A9_R1_AGGREGATES.json (new)
  - docs/plans/M35_URIV1_A2_8L_A9_R1_RUN1_CAUSAL.json (new)
  - docs/plans/M35_URIV1_A2_8L_A9_R1_RUN2_CAUSAL.json (new)
  - docs/plans/M35_URIV1_A2_8L_A9_R1_REPAIR_REPORT.md (new)
  - docs/plans/M35_URIV1_A2_8L_A9_R1_STATE.md (new, this file)
git_state: no commit made; all files above untracked/new in the working
  tree, consistent with AO-4 release-gate pattern (Claude alone commits/
  pushes, only after independent re-audit + User go-ahead)
test_state: 119 passed / 178 subtests, all green as of this round
audit_state: NOT YET RE-AUDITED -- this file and the repair report
  constitute the bounded fixer's own self-report only
last_successful_checkpoint: causal (x2 fresh processes) + transport +
  natural + S-D + performance all completed in one orchestrated run of
  scripts/m35_a2_8l_a9_r1_rerun.py, telemetry/aggregates written to disk
retry_metadata: none (single successful run; smoke-tested with reduced
  parameters before the full-protocol run to catch defects cheaply)
```

## Next action

**STOP — INDEPENDENT RE-AUDIT REQUIRED BEFORE ACCEPTANCE OR NEXT
EXPERIMENT.** This implementer does not self-accept or self-close
A2.8L-A9-R1.
