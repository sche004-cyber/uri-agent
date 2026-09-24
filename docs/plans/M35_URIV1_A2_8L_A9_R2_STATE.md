# M35 URIv1 — A2.8L-A9-R2 STATE

**Current state:** `VERIFICATION_READY_FOR_REAUDIT`
**Milestone:** A2.8L-A9-R2 — bounded evidence/reporting correction after
independent re-audit of A9-R1 (`REPAIR_REQUIRED`)
**Branch:** `m35-uri-v1-parallel-architecture`
**Frozen checkpoint governing this round:** `591f806` (A9 plan/manifest;
unchanged by mechanism, changed only by the separate R2-9 governance note
appended to the overlay manifest — see below)
**Plan:** `docs/plans/M35_URIV1_A2_8L_RAR_EVIDENCE_TRANSPORT_FACTORIAL_PLAN.md`
§16 (unchanged; no A10)
**A9-R1 re-audit that triggered this round:**
`docs/plans/M35_URIV1_A2_8L_A9_R1_INDEPENDENT_REAUDIT_REPORT.md` (verdict
`REPAIR_REQUIRED`)
**Correction report:** `docs/plans/M35_URIV1_A2_8L_A9_R2_CORRECTION_REPORT.md`
**Predecessors (preserved byte-unchanged, not superseded):**
`docs/plans/M35_URIV1_A2_8L_STATE.md` (pre-A9),
`docs/plans/M35_URIV1_A2_8L_A9_STATE.md` (A9),
`docs/plans/M35_URIV1_A2_8L_A9_R1_STATE.md` (A9-R1)

## Role note

Per the R2 task's own explicit role grant ("You are the authorized bounded
correction implementer for M35 URIv1 A2.8L-A9-R2"), this round is a
report/telemetry-label correction pass, not a new mechanism repair and not
a new causal experiment. No resolver, fixture, benchmark-semantic, or
causal-factor change was made. The one benchmark-execution correction
authorized (R2-7, compiler-arm wall interleaving) changes measurement
methodology only, not the compiler algorithm, its inputs, or any
threshold definition.

## Mechanism change this round

**None.** `uri_v1/turn/rar_attachment_order_experimental.py` and
`uri_v1/turn/rar_attachment_order_factorial_fixtures.py` are byte-identical
to A9-R1 (SHA-256 verified before and after this round: `90d89c37…` /
`36570706…`).

## Corrections applied (R2-1 through R2-10)

- **R2-1 (transport taxonomy):** split the 38-row tie bucket by row-level
  correctness into `COMPILER_STEP4_NO_TIE_EMISSION_UNSAFE_BIND` (30) and
  `SIDECAR_GATE_ABSTAINS_COMPILER_CORRECT` (8). Total remains 88/196, 0
  unexplained. `NEW_CONTRACT_FIELD_REQUIRED` remains `NOT_ESTABLISHED`.
- **R2-2 (G×P wording):** recorded the R=1-conditional, gate-induced
  interpretation as structured telemetry (`gxp_qualifying_background_interpretation`),
  not only report prose.
- **R2-3 (surface labels):** split the 12-row NB-C-04/NB-C-05 mismatch
  label into the true all-off-baseline-cell rows (4) and the true
  qualifying-cell-ablation rows (8); corrected the changed-row lineage
  statement (16 is not a correction of A9's 8 — both are correct for their
  respective pre-/post-IR-1 mechanism states).
- **R2-4 (IR-1 residual):** verified the `"earlier"`-token residual affects
  0 current rows; disclosed as `NON_EFFECTING_SPEC_RESIDUAL`, not fixed.
- **R2-5 (Q flag):** corrected `q_alone_resolves_all_case_b_ordinal_targets`
  to check only the three ordinal Case-B ids; now `True` (was `False`,
  incorrectly including non-ordinal `B-DISTRACTOR`).
- **R2-6 (CPU wording):** removed the false "≥100 ticks" claim; reports
  actual measured tick coverage per pool (max 99 at pool 32, never ≥100).
  Threshold result unaffected (still PASS at all three pools).
- **R2-7 (compiler-arm interleaving):** compiler arm now uses genuine
  global (key, pool, iteration) interleaved execution order, matching the
  sidecar. No threshold result changed from PASS.
- **R2-8 (§16.5 telemetry gap):** disclosed as
  `TELEMETRY_FORMAT_LIMITATION_NOT_EVIDENCE_GAP`; no new per-row field
  added (out of scope); no causal conclusion changed.
- **R2-9 (ER-9 governance note):** dated correction appended as new §6 to
  `docs/plans/M35_URIV1_A2_8L_OVERLAY_MANIFEST.md`; §5's original text
  preserved unedited above it.
- **R2-10 (environment metadata):** now captured per fresh-process run
  inside each subprocess; A9/A9-R1's historical gap (source hashes only,
  no full environment snapshot per run) disclosed, not backfilled.

## Headline results (all previously-verified numbers preserved unchanged)

- 1 qualifying cell, unchanged: `M1G1P1D1R1Q0`.
- 0/896 factorial decision delta vs A9-R1 (independently reproduced this
  round's own fresh-process runs).
- Transport: 88/196 mismatches (unchanged total), 0 unexplained, corrected
  6-bucket attribution (was 5 buckets with one mixed-direction bucket).
- Natural/D1RQ surface: 112 rows, 54 mismatches, 0 unexplained, corrected
  4-reason reconciliation (was 3-reason, with one reason label imprecise).
- Performance: all four §10.2 threshold families still PASS; compiler-arm
  interleaving fixed; CPU tick-coverage claim corrected.
- Regression: 119 tests / 178 subtests, all passing (reproduced).
- Protected-file, mechanism-file, and fixture-file hashes: unchanged.

## RECOVERY STATE

```
required_model: none (correction round complete)
current_owner: Claude Code
resume_stage: VERIFICATION_READY_FOR_REAUDIT -- awaiting independent re-audit
pause_reason: none (stopped per the R2 task's own instruction: this round
  has no authority to ACCEPT A9, commit, or push)
task: A2.8L-A9-R2 bounded evidence/reporting correction after the A9-R1
  independent re-audit's verdict REPAIR_REQUIRED
completed_steps:
  - wrote docs/plans/M35_URIV1_A2_8L_A9_R1_INDEPENDENT_REAUDIT_REPORT.md
    to disk (provenance file for the prior turn's re-audit output, which
    had not previously been persisted)
  - R2-1: transport taxonomy split (_row_is_correct, corrected
    _attribute_mismatch), verified 30/8 split and 88-total reconciliation
  - R2-2: G x P conditional-on-R wording recorded as structured telemetry
  - R2-3: natural-surface mismatch-reason label split (baseline-cell vs
    true-ablation-cell); changed-row lineage note added
  - R2-4: IR-1 earlier-token residual verified (0 affected rows),
    disclosed, not fixed
  - R2-5: Q-alone telemetry flag corrected and re-verified from raw rows
  - R2-6: CPU tick-coverage wording corrected against raw batch data
  - R2-7: compiler-arm wall-time benchmark given genuine global
    interleaving; old vs corrected metrics reported; no threshold changed
  - R2-8: S16.5 telemetry gap disclosed as a format limitation
  - R2-9: ER-9 governance note appended to the overlay manifest (§5
    preserved, new §6 added)
  - R2-10: per-fresh-process-run environment metadata capture added;
    historical A9/A9-R1 gap disclosed
  - two independent fresh-process causal runs (1792 rows each,
    deterministic, 0/896 delta)
  - regression suite rerun (119 passed / 178 subtests)
  - correction report and this STATE file written
remaining_steps:
  - independent re-audit of this correction round
  - User acceptance decision following re-audit
  - no next milestone/experiment may start before that acceptance decision
changed_files:
  - scripts/m35_a2_8l_a9_r2_correction.py (new)
  - docs/plans/M35_URIV1_A2_8L_A9_R2_TELEMETRY.json (new)
  - docs/plans/M35_URIV1_A2_8L_A9_R2_AGGREGATES.json (new)
  - docs/plans/M35_URIV1_A2_8L_A9_R2_RUN1_CAUSAL.json (new)
  - docs/plans/M35_URIV1_A2_8L_A9_R2_RUN2_CAUSAL.json (new)
  - docs/plans/M35_URIV1_A2_8L_A9_R2_CORRECTION_REPORT.md (new)
  - docs/plans/M35_URIV1_A2_8L_A9_R2_STATE.md (new, this file)
  - docs/plans/M35_URIV1_A2_8L_A9_R1_INDEPENDENT_REAUDIT_REPORT.md (new,
    provenance file for the prior re-audit turn)
  - docs/plans/M35_URIV1_A2_8L_OVERLAY_MANIFEST.md (edited -- new S6
    governance correction appended, S5 preserved unedited)
git_state: no commit made; all files above untracked/new (or, for the
  manifest, untracked-modified) in the working tree, consistent with AO-4
  release-gate pattern (Claude alone commits/pushes, only after
  independent re-audit + User go-ahead)
test_state: 119 passed / 178 subtests, all green as of this round
audit_state: NOT YET RE-AUDITED -- this file and the correction report
  constitute the bounded correction implementer's own self-report only
last_successful_checkpoint: causal (x2 fresh processes) + transport +
  natural + S-D + performance + all R2 corrections completed in one
  orchestrated run of scripts/m35_a2_8l_a9_r2_correction.py, telemetry/
  aggregates written to disk; regression suite rerun separately and
  confirmed green
retry_metadata: none (single successful run)
```

## Next action

**STOP — INDEPENDENT RE-AUDIT REQUIRED BEFORE ACCEPTANCE OR NEXT
EXPERIMENT.** This implementer does not self-accept or self-close
A2.8L-A9-R2, and this round has no authority to declare `VERIFIED`, commit,
or push.
