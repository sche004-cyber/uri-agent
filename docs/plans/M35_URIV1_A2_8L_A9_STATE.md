# M35 URIv1 — A2.8L-A9 STATE

**Current state:** `VERIFICATION_READY`
**Milestone:** A2.8L-A9 — RAR Attachment-Order Evidence Transport Factorial (frozen A9 rerun)
**Branch:** `m35-uri-v1-parallel-architecture`
**Frozen checkpoint governing this rerun:** `591f806`
**Plan:** `docs/plans/M35_URIV1_A2_8L_RAR_EVIDENCE_TRANSPORT_FACTORIAL_PLAN.md` §16 (`FROZEN_READY_FOR_RERUN`)
**Overlay manifest:** `docs/plans/M35_URIV1_A2_8L_OVERLAY_MANIFEST.md`
**Execution report:** `docs/plans/M35_URIV1_A2_8L_A9_EXECUTION_REPORT.md`
**Predecessor:** `docs/plans/M35_URIV1_A2_8L_STATE.md` (pre-A9 run; preserved byte-unchanged, not superseded — A9 §16.2 item 1 requires its literal 0-qualifying-cell reading to remain a distinct, valid finding)

## Role note (standing governance exception for this task)

Per the pinned AO-4 development-cycle governance, Claude Code's standing
role is Architect / Pre-Auditor / Final Auditor / Bounded Fixer / Release
Authority, not primary implementer. For this rerun task, the User was
explicitly asked (via AskUserQuestion) whether to authorize direct
implementation again as a one-off exception, same as the first A2.8L run,
and answered yes (live session, 2026-09-24). This does not change the
standing AO-4 role split for any other milestone.

## No mechanism code changed

Both `uri_v1/turn/rar_attachment_order_experimental.py` and
`uri_v1/turn/rar_attachment_order_factorial_fixtures.py` were inspected
before this rerun and found already A9-conformant (see execution report,
"Pre-rerun conformance check"). Zero lines were edited in either file.
Hash-verified unchanged before/after, and identical across both
independent fresh-process subprocess runs.

## Implementation summary

- New rerun script: `scripts/m35_a2_8l_a9_rerun.py`
- Two independent fresh-process causal runs (subprocess-based)
- D1RQ + natural-row confirmation surface (`NB-C-04/05`, `NB-D-01/02`,
  C1/C2) under baseline + every A9-amended qualifying cell + ablations
- Case-level 2×2 interaction tables on the qualifying-cell background
  (in addition to the pre-A9 all-off-background tables)
- Transport comparison with explicit per-mismatch cause attribution (5
  buckets, 0 unattributed)
- Full 200-warmup / 2,000-randomized-iteration performance pass with
  environment/source metadata
- Full existing A2.5/A2.8K/A2.8L regression suite: 114 tests / 178
  subtests, all passing, unchanged

No protected file (plan §13.2) was modified. Pre/post protected-file
hashes are identical. No RAR contract field was added. No production
integration, commit, or push has occurred.

## Headline results

- **1 qualifying cell** (`M=1,G=1,P=1,D=1,R=1,Q=0`), independently
  re-derived under A9-amended semantics, not assumed from the pre-A9 run.
- **Necessary factors:** M, G, P, D, R — with the D/M necessity split
  (Level-5 ordinal mechanism vs. A9-2 Level-5.5 extension) and the G/R
  coupling caveats (§16.5) both explicitly disclosed per A9 §16.4, not
  reported as clean independent-factor findings.
- **Transport:** `EXISTING_CONTRACT_COMPILATION_INSUFFICIENT`, scoped to
  the tested §4.2.1 algorithm. All 90/196 mismatches attributed to one of
  five explicit causes; zero left unexplained.
- **Performance:** wall-time and allocation thresholds all met (final,
  full-iteration protocol, not provisional). CPU-overhead threshold:
  `UNMEASURED` (Windows `process_time` granularity too coarse for this
  workload's sub-millisecond calls — a genuine instrument limitation,
  disclosed, not silently passed).
- **`NB-D-02`:** 0 unauthorized new confident bindings across all 7 cells
  tested.
- Both the original pre-A9 literal-plan result (0 qualifying cells under
  A1–A8 text alone) and this A9-amended result are preserved separately,
  per A9 §16.2.

## RECOVERY STATE

```
required_model: none (rerun complete)
current_owner: Claude Code
resume_stage: VERIFICATION_READY -- awaiting independent audit
pause_reason: none (not paused; stopped per frozen plan's own mandatory
  independent-audit gate before acceptance/closure, restated in the A9
  rerun task brief)
task: A2.8L-A9 frozen rerun of the RAR attachment-order evidence transport
  factorial
completed_steps:
  - pre-rerun conformance check: mechanism/fixture modules already A9-1..
    A9-5 conformant, zero code changes made
  - two independent fresh-process causal runs (subprocess-based), 1792
    rows each, byte-identical decision tuples and source hashes
  - minimal-sufficient-set / necessity / D-M-attribution-split / G-R-
    coupling-disclosure analysis computed
  - qualifying-cell-background 2x2 interaction tables computed (new,
    in addition to the pre-A9 all-off-background tables)
  - bounded transport comparison executed (T=7) with full per-mismatch
    cause attribution (5 buckets, 0 unexplained)
  - D1RQ + natural-row confirmation surface executed under baseline + all
    7 candidate cells (112 rows, 0 NB-D-02 violations)
  - S-D confirmation surface executed under baseline + qualifying cell
    (0 unexpected mismatches at either)
  - full existing A2.5/A2.8K/A2.8L regression suite run (114 tests / 178
    subtests, all pass, unchanged)
  - full 200/2000 randomized/interleaved performance pass with
    environment/source metadata; CPU-timing limitation disclosed as
    UNMEASURED
  - telemetry, aggregates, execution report, this STATE file written
remaining_steps:
  - independent audit of: the D/M Level-5.5-extension necessity split,
    the G/M and R/overlay-presence coupling disclosures, the 5-bucket
    transport-mismatch attribution taxonomy (2 buckets are new relative
    to the pre-A9 execution report's narrative), and the CPU-timing
    UNMEASURED resolution
  - User acceptance decision (ACCEPT / MODIFY / REOPEN) following that
    audit
  - no next experiment may start before that acceptance decision
changed_files:
  - scripts/m35_a2_8l_a9_rerun.py (new)
  - docs/plans/M35_URIV1_A2_8L_A9_TELEMETRY.json (new)
  - docs/plans/M35_URIV1_A2_8L_A9_AGGREGATES.json (new)
  - docs/plans/M35_URIV1_A2_8L_A9_RUN1_CAUSAL.json (new)
  - docs/plans/M35_URIV1_A2_8L_A9_RUN2_CAUSAL.json (new)
  - docs/plans/M35_URIV1_A2_8L_A9_EXECUTION_REPORT.md (new)
  - docs/plans/M35_URIV1_A2_8L_A9_STATE.md (new, this file)
git_state: no commit made; all files above are untracked/new in the
  working tree, consistent with the AO-4 release-gate pattern (Claude
  alone commits/pushes, only after independent audit + User go-ahead)
test_state: full A2.5/A2.8K/A2.8L regression suite -- 114 passed / 178
  subtests, all green as of this run; A2.8L-specific unit tests
  (tests/test_m35_uriv1_a2_8l_rar_attachment_order_factorial.py) included
  and unchanged
audit_state: NOT YET INDEPENDENTLY AUDITED -- this file and the execution
  report constitute the implementer's own self-report only
last_successful_checkpoint: causal (x2 fresh processes) + transport +
  confirmation + natural + performance all completed in one orchestrated
  run of scripts/m35_a2_8l_a9_rerun.py, telemetry/aggregates written to
  disk
retry_metadata: none (no retries required; the transport-mismatch
  attribution taxonomy was iteratively refined against the actual
  observed mismatch patterns before the final run, not after seeing the
  final run's own results -- the mechanism/fixture code itself was never
  touched)
```

## Next action

Per the frozen plan's own instruction and the A9 rerun task brief: **STOP
— INDEPENDENT AUDIT REQUIRED BEFORE ACCEPTANCE OR NEXT EXPERIMENT.** This
implementer (Claude Code, acting under the one-off role exception recorded
above) does not self-accept or self-close A2.8L-A9.
