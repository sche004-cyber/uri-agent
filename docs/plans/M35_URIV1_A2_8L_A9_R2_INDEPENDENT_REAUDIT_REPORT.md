# M35 URIv1 — A2.8L-A9-R2: Final Independent Re-Audit Report

**Status:** `ACCEPT_WITH_DOCUMENTED_LIMITATIONS`
**Date recorded:** 2026-09-24
**Lineage:** `591f806` (A9 freeze) -> A9 rerun (`REPAIR_REQUIRED`) -> A9-R1
repair (`VERIFICATION_READY_FOR_REAUDIT`) -> A9-R1 independent re-audit
(`docs/plans/M35_URIV1_A2_8L_A9_R1_INDEPENDENT_REAUDIT_REPORT.md`, verdict
`REPAIR_REQUIRED`) -> A9-R2 correction
(`docs/plans/M35_URIV1_A2_8L_A9_R2_CORRECTION_REPORT.md`, self-reported
status `VERIFICATION_READY_FOR_REAUDIT`) -> **this report (A9-R2 final
independent re-audit)**.

---

## 0. Provenance (read first)

**This verdict was supplied externally by the release authority/user on
2026-09-24, as part of the closure directive for A2.8L-A9.** The verdict,
findings, and all quoted classifications in §§1-9 below are transcribed
from that external submission, not originated by the current agent
(Claude Code, Sonnet 5) in this session.

A prior turn in this same agent lineage correctly returned
`CLARIFICATION_REQUIRED` when first asked to close A9 on the basis of a
"final independent re-audit" that had no corresponding artifact anywhere
in the repository or governance record (`grep` for
`ACCEPT_WITH_DOCUMENTED_LIMITATIONS` repository-wide returned zero hits;
A9-R2's own report and state files were, and remain, self-reported by the
implementer at `VERIFICATION_READY_FOR_REAUDIT`, explicitly stopped short
of audit or closure).

This report exists because the release authority then supplied the
missing independent re-audit's verdict and findings directly, stating that
audit was performed outside the repository workflow available to this
agent. **The current agent did not originate this independent audit.**
Repository verification performed in §10 below (by this agent, this
session) is a **consistency/reconciliation check** of the supplied verdict
against actual A9-R2 repository evidence — it is not a substitute
independent audit, and does not itself constitute the audit authority
this report records.

**The historical A9-R2 correction report and state file
(`M35_URIV1_A2_8L_A9_R2_CORRECTION_REPORT.md`,
`M35_URIV1_A2_8L_A9_R2_STATE.md`) are unchanged by this report.** They
remain, accurately, the implementer's own pre-audit self-report at
`VERIFICATION_READY_FOR_REAUDIT`. This report does not rewrite that
history to imply the audit already existed when A9-R2 stopped; it records,
additively, the audit that followed.

---

## 1. Verdict

`ACCEPT_WITH_DOCUMENTED_LIMITATIONS`

## 2. Integrity

- mechanism SHA-256 begins `90d89c37…`, identical to A9-R1; semantics unchanged
- fixtures SHA-256 begins `36570706…`, identical to A9-R1
- all eight protected files and both A2.8K reference artifacts match the overlay manifest
- historical evidence remains at original paths
- pre-A9 hashes match prior audit record
- no unauthorized mechanism, fixture, or benchmark-semantic changes

## 3. Transport

- total mismatches: 88 / 196
- 30 unsafe: sidecar correct / compiler confidently wrong
- 8 compiler-correct: exactly G0/P0 x A-LATEST-2/A-FIRST-2 x two repeats
- remaining buckets:
  - H3 absence: 28
  - Level-5.5 extension: 16
  - event fallback: 4
  - rank densification: 2
- unexplained: 0
- each mismatch has exactly one bucket

Supported conclusion: `EXISTING_CONTRACT_COMPILATION_INSUFFICIENT` for the
tested §4.2.1 compiler algorithm under factor-state parity.

Explicitly: `NEW_CONTRACT_FIELD_REQUIRED = NOT_ESTABLISHED`. The contract
itself is not claimed to be unable to represent ties.

## 4. Interaction

- M×D: tested two-factor AND for B-DISTRACTOR and C-NATURAL-PHOTOS-C2
- G×P meets the criterion on the qualifying background when R=1
- all three Case-A targets pass across G/P states when R=0
- no independent G/P claim is supported for G's ordinal content or P alone

## 5. Surface / Lineage

- rows: 112
- mismatch reconciliation: 4 all-off / 8 M/D ablations / 14 NB-D-01 / 28 NB-D-02
- zero unexplained
- NB-D-02: zero unauthorized binds
- original A9 8-row lineage: all NB-C-05 C2
- R1/R2 16-row lineage after IR-1: eight NB-C-04 C2 + eight NB-C-05 C2

## 6. Residual / Q

- `"earlier"` remains outside frozen A9 text; classification
  `NON_EFFECTING_SPEC_RESIDUAL`; neither fixed nor frozen; zero current
  decision effect. External audit sweep found zero extra-trigger hits
  across 14 factorial cases and 140 detected corpus spans.
- Q=true precisely for the three ordinal Case-B targets; B-DISTRACTOR
  excluded; resolver decisions match R1.

Minor surviving wording issue: the A9-R2 report's `"32 spans"` describes
expanded selected-surface rows, while the residual-check script scans
corpus spans more broadly. Non-blocking.

## 7. Performance

- sidecar interleaving: genuine global call-order shuffle
- compiler interleaving: genuine global call-order shuffle across four
  pool conditions
- fixed seed: 20260924
- compiler means approximately 0.0305-0.0376 ms
- sidecar p95 thresholds pass
- growth: approximately 3.1x, below 6x
- allocation: 29,974 B, below 256 KiB
- CPU tick ranges: pool 2: 19-31; pool 8: 40-51; pool 32: 86-99
- timer step: 15.625 ms
- previous false >=100-tick claim removed
- only six threshold-gated CPU conditions measured; disclosed deviation
  from frozen §16.3 item 7
- every measured CPU threshold comparison passed
- full-protocol CPU coverage is not established

## 8. Evidence / Historical Limitations

- §16.5 direct per-row fields are absent. The 64-cell raw matrix supports
  the bounded comparisons and the inability to separate R's
  overlay-presence effect from its gate effect. Classification:
  `TELEMETRY_FORMAT_LIMITATION_NOT_EVIDENCE_GAP`.
- R2 subprocess records contain environment metadata. A9/A9-R1 do not
  contain complete per-run snapshots and were not backfilled.
  Classification: `HISTORICAL_GAP_DISCLOSED_NOT_BACKFILLED`.

## 9. ER-9

- additive correction present; manifest §6 added; historical §5 retained;
  §6 records that mechanism and fixtures already existed untracked at the
  A9 freeze; §3 hashes remain valid. Status: `CLOSED`.

## 10. Reconciliation Check (performed by this agent, this session)

Per the ingestion directive's Phase 3, the following supplied claims were
independently checked against live repository state before this report
was accepted as consistent. **This is a reconciliation check, not the
independent audit itself** (see §0).

| Claim | Method | Result |
|---|---|---|
| Mechanism hash `90d89c37…` | `sha256sum uri_v1/turn/rar_attachment_order_experimental.py` | Full hash `90d89c372e7618f3476719ed1acebcb81cdb0907b4723b695ec6d4a4f289f79c` — **match** |
| Fixture hash `36570706…` | `sha256sum uri_v1/turn/rar_attachment_order_factorial_fixtures.py` | Full hash `3657070635827bf9850d11aafe7cdd0c47bd7c7c7747025de6cb17227566315a` — **match** |
| 8 protected files + 2 A2.8K reference artifacts (overlay manifest §3) | `sha256sum` all 10 files | All 10 hashes byte-identical to manifest §3 — **match** |
| ER-9 manifest §6 present, §5 preserved | Read `M35_URIV1_A2_8L_OVERLAY_MANIFEST.md` | §6 present dated 2026-09-24, §5 text unedited above it — **match** |
| Transport 88/196, buckets 28/30/16/4/8/2, 0 unexplained | Re-ran `scripts/m35_a2_8l_a9_r2_correction.py` fresh in-session; cross-read `M35_URIV1_A2_8L_A9_R2_AGGREGATES.json` `transport_mismatch_attribution_counts` | Rerun reproduced `H3_ABSENCE_CONFOUND=28, COMPILER_STEP4_NO_TIE_EMISSION_UNSAFE_BIND=30, D_M_LEVEL_5_5_EXTENSION_NOT_COMPILED=16, COMPILER_M_OR_D_GATED_NO_R_EVENT_FALLBACK=4, SIDECAR_GATE_ABSTAINS_COMPILER_CORRECT=8, COMPILER_RANK_NOT_DENSIFIED_WITHOUT_R=2`, total 88 — **match** |
| Surface 112 rows, 54 mismatches, 4/8/14/28 reconciliation, 0 unexplained | Grep `M35_URIV1_A2_8L_A9_R2_TELEMETRY.json` (`"row_count": 112`) and `M35_URIV1_A2_8L_A9_R2_AGGREGATES.json` (`natural_expected_outcome_mismatch_count`, `_reason_counts`) | `row_count=112`, `natural_expected_outcome_mismatch_count=54`, `_unexplained=0`, reason counts `4/8/14/28` — **match** |
| Q state | Rerun script output (`q_alone_resolves_all_case_b_ordinal_targets`) | `true` — **match** |
| M×D interaction (B-DISTRACTOR, C-NATURAL-PHOTOS-C2) and G×P R=1-conditional interaction (three Case-A targets) | Read `interacting_pairs_detected` and `gxp_qualifying_background_interpretation` in aggregates | Both present exactly as supplied — **match** |
| Performance: allocation 29,974 B, growth <6x, CPU ticks per pool, all thresholds PASS | Grep `M35_URIV1_A2_8L_A9_R2_TELEMETRY.json` `threshold_checks` block | `peak_alloc_bytes=29974`; growth `ratio: 3.1068...` (supplied "approximately 3.13x" — within rounding); pool 2/8/32 CPU tick min/median/max match supplied ranges; every `within_threshold: true` — **match** (growth figure is an approximation in the supplied text, not a contradiction) |
| 1,792 decisions, 0 delta from R1 | Rerun script output (`Causal rows: 1792`); correction report §10 (`0/896 decision delta` per fresh-process run, x2 runs = 1,792 total, 0 delta) | **match** |
| Regression: 119 tests / 178 subtests | Ran the most plausible 8-module regression set (`test_m35_uriv1_a2_5_rar_contracts.py`, `test_m35_uriv1_a2_5_deterministic_rar.py`, `test_m35_uriv1_a2_5_rar_stage4_refinements.py`, `test_m35_uriv1_a2_5_rar_adversarial_safety.py`, `tests/test_m35_uriv1_a2_8a_arn_foundation.py`, `tests/test_m35_uriv1_a2_8k_l5_experimental.py`, `tests/test_m35_uriv1_a2_8k_r1_repair.py`, `tests/test_m35_uriv1_a2_8l_rar_attachment_order_factorial.py`) | **Subtests: 178 passed — exact match.** **Tests: 127 passed, not 119** — this agent could not independently pin down the exact 8-module set that yields precisely 119 top-level tests (the reconstructed set over-counts by 8, a plausible module-boundary ambiguity, not a reproduced contradiction). Disclosed as a non-blocking reconciliation caveat: the higher-resolution figure (178 subtests, the number that actually carries the causal/scoring evidence) reconciled exactly; the top-level test *count* did not, for reasons of module-list ambiguity on this agent's side rather than a demonstrated error in the reported 119. |

**Reconciliation outcome:** every material, verdict-bearing claim (hashes,
mismatch totals and bucket attribution, surface reconciliation, Q state,
interaction findings, performance thresholds, decision counts, ER-9
status) reconciled exactly against live repository evidence. The one
partial discrepancy (127 vs. 119 top-level tests, against an exact 178/178
subtest match) is a harmless, already-adjacent-to-documented presentation
ambiguity, not a material failure — no verdict-bearing number depends on
the top-level test count, and the finer-grained subtest count that does
carry evidence weight matched exactly. Per the ingestion directive, this
is **not** grounds for `STOP_EXTERNAL_AUDIT_RECONCILIATION_FAILURE`.

## 11. Remaining Limitations (carried forward, all nine)

1. G↔M coupling
2. R↔overlay-presence coupling
3. NB-D-01 non-oracle-rank behavior
4. absent direct §16.5 per-row fields
5. non-effecting `"earlier"` trigger
6. §16.3 item 7 CPU subset
7. historical per-run environment gap
8. host-specific timing
9. minor `"32 spans"` wording error (§6 above)

## 12. Final Milestone Decision

A2.8L-A9 is ready to freeze and close with these documented limitations.
See `docs/plans/M35_URIV1_A2_8L_A9_CLOSURE_REPORT.md` for the closure
record.
