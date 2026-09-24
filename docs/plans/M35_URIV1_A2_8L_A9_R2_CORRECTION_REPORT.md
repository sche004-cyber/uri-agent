# M35 URIv1 — A2.8L-A9-R2: Bounded Evidence & Reporting Correction Report

**Status:** `VERIFICATION_READY_FOR_REAUDIT`
**Date:** 2026-09-24
**Lineage:** `591f806` (A9 freeze) -> A9 rerun (`REPAIR_REQUIRED`) -> A9-R1
repair (`VERIFICATION_READY_FOR_REAUDIT`) -> A9-R1 independent re-audit
(`docs/plans/M35_URIV1_A2_8L_A9_R1_INDEPENDENT_REAUDIT_REPORT.md`, verdict
`REPAIR_REQUIRED`) -> this correction round (`A9-R2`).
**Implementer:** Claude Code (Sonnet 5), acting as the authorized bounded
correction implementer for this round (per the R2 task's own role grant).
**Scope:** report/telemetry label and interpretation corrections only. No
mechanism, fixture, benchmark-semantic, or causal-factor change. No causal
rerun was required to produce these corrections; the two-fresh-process
causal battery was re-executed only because it is cheap (< 1 s) and keeps
this round's evidence artifacts self-contained and independently
re-verifiable, not because any correction required new causal data — it
reproduces A9-R1's 0/896 delta exactly (see §2).

No commit, push, acceptance, or closure has occurred. This report is an
implementer self-report and requires independent re-audit before
acceptance, exactly as A9 and A9-R1 did.

---

## 1. Integrity

| Check | Result |
|---|---|
| Mechanism hash (`rar_attachment_order_experimental.py`) | `90d89c37…`, identical to A9-R1, before and after this round |
| Fixture hash (`rar_attachment_order_factorial_fixtures.py`) | `36570706…`, identical to A9-R1 |
| 8 protected files (§13.2) | SHA-256 unchanged, matches overlay manifest §3 |
| A9-R1 evidence (`M35_URIV1_A2_8L_A9_R1_*`) | Not touched; this round writes only to `M35_URIV1_A2_8L_A9_R2_*` paths |
| A9 evidence (`M35_URIV1_A2_8L_A9_*`, non-R1) | Not touched |
| Pre-A9 evidence | Not touched |
| Unauthorized changes | None |

## 2. Transport Taxonomy (R2-1)

**Verified defect (independent re-audit §7):** the A9-R1 taxonomy's
`COMPILER_UNSAFE_BIND_NO_TIE_REPRESENTATION` bucket (38 rows) checked only
the *shape* of the two arms' outcomes (sidecar `AMBIGUOUS`, compiler
`RESOLVED`) — never which arm was actually correct against the case's
frozen expectation, despite the A9-R1 report's own docstring claiming the
bucket "restricted to the unsafe direction only".

**Repair:** `_attribute_mismatch` now computes row-level correctness via
`_row_is_correct` (scored against each case's frozen
`expected_outcome`/`expected_candidate_id`/`expected_ambiguous_candidate_ids`,
identical scoring rule used throughout the causal matrix and natural
surface) and branches the (sidecar `AMBIGUOUS`, compiler `RESOLVED`) shape
into two disjoint buckets:

| Bucket | Count | Direction |
|---|---|---|
| `COMPILER_STEP4_NO_TIE_EMISSION_UNSAFE_BIND` | **30** | sidecar correct (abstains), compiler wrong (unsafe confident bind) |
| `SIDECAR_GATE_ABSTAINS_COMPILER_CORRECT` | **8** | sidecar wrong (over-gated abstention), compiler correct |

The 8-row bucket is exactly the independent re-audit's predicted set: the
G0 and P0 cells × `A-LATEST-2`/`A-FIRST-2` × 2 repeats.

**Full corrected attribution (independently reconciled):**

| Bucket | Count |
|---|---|
| `H3_ABSENCE_CONFOUND` | 28 |
| `COMPILER_STEP4_NO_TIE_EMISSION_UNSAFE_BIND` | 30 |
| `D_M_LEVEL_5_5_EXTENSION_NOT_COMPILED` | 16 |
| `COMPILER_M_OR_D_GATED_NO_R_EVENT_FALLBACK` | 4 |
| `SIDECAR_GATE_ABSTAINS_COMPILER_CORRECT` | 8 |
| `COMPILER_RANK_NOT_DENSIFIED_WITHOUT_R` | 2 |
| **Total** | **88** |

`sum(buckets) == mismatch_count == 88`; `unexplained == 0`; total remains
`88/196`, unchanged from A9-R1.

**Contract-vs-algorithm wording:** neither new bucket name implies the RAR
contract cannot represent ties. A densified rank or an all-equal
`recency_rank` both fit the existing int field. The limitation attributed
by `COMPILER_STEP4_NO_TIE_EMISSION_UNSAFE_BIND` is in the tested §4.2.1
algorithm's step 4 branching (it never emits either a densified rank or a
tie the way the sidecar's R mechanism does), not in contract field
expressiveness. `NEW_CONTRACT_FIELD_REQUIRED` remains `NOT_ESTABLISHED`.

## 3. Interaction Wording (R2-2)

`gxp_qualifying_background_interpretation` (telemetry/aggregates, verbatim):

> On the qualifying-cell background where R=1, G∧P meets §7's
> interacting-pair test for the three Case-A targets (A-LATEST-2,
> A-FIRST-2, A-LATEST-DISTRACTOR). This interaction is CONDITIONAL ON R=1
> and is induced by the authorization/gating construction, not an
> independent two-factor causal contribution: A9-5's R ties the
> D-restricted domain unless both G and P pass; with R=0, all three Case-A
> targets pass regardless of G/P state (see
> `pairwise_interactions_qualifying_cell_background` `GxR` and `PxR`
> tables, R=0 rows). No claim is made that G's ordinal content or P
> contributes independently of this gate. The M∧D interaction
> (`B-DISTRACTOR`, `C-NATURAL-PHOTOS-C2`) is NOT gate-conditional in the
> same way and is reported separately.

M×D is preserved unconditionally (verified again this round, unchanged
from A9-R1): passes only at (M=1,D=1) for `B-DISTRACTOR` and
`C-NATURAL-PHOTOS-C2`, on any background including all-off.

## 4. Surface Labels (R2-3)

**Verified counts (unchanged):** 112 rows, 54 total expected-outcome
mismatches, 0 unexplained, 0 `NB-D-02` unauthorized binds.

**Corrected reconciliation (was 12+28+14; the 12 is now split by actual
cell/cause):**

| Reason | Count |
|---|---|
| `M_AND_D_INACTIVE_ALL_OFF_BASELINE_CELL_A9_2_NOT_APPLICABLE` | 4 |
| `M_OR_D_ABLATED_FROM_QUALIFYING_CELL_A9_2_REQUIRES_BOTH` | 8 |
| `PRE_EXISTING_NON_ORACLE_RANK_SCOPE_LIMITATION` | 14 |
| `DISCLOSED_CAPABILITY_GAP_NB_D_02` | 28 |
| **Total** | **54** |

The 4 `..._ALL_OFF_BASELINE_CELL...` rows are the all-off cell itself (not
an ablation of anything — M and D are simply never on there); the 8
`..._ABLATED_FROM_QUALIFYING_CELL...` rows are the qualifying cell's actual
one-factor M/D ablations.

**Changed-row lineage (`natural_changed_rows_lineage`, verbatim):**

> The verified 16 changed rows (8 `NB-C-04` C2 + 8 `NB-C-05` C2) are NOT a
> correction of an original A9 count from 8 to 16. A9's original count of
> 8 (all `NB-C-05` C2) was CORRECT for the pre-IR-1 implementation, under
> which `NB-C-04` C2's D1RQ span never triggered the A9-2 extension at all
> (empty `l5_pool_lexical`) and so never changed from the H3-only
> baseline. The additional 8 `NB-C-04` C2 rows exist BECAUSE IR-1 changed
> the Level-5.5 membership-restriction trigger pool from
> `l5_pool_lexical` to `candidates_list`, which is what makes `NB-C-04` C2
> responsive to the qualifying/ablation cells in the first place. Both
> counts (A9's 8, R2's 16) are correct for their respective, different
> mechanism states.

## 5. IR-1 Residual (R2-4)

- **Location:** `uri_v1/turn/rar_attachment_order_experimental.py:_ordinal_literal_present`,
  the `"earlier" in ref_tokens` branch (module line ~143).
- **Why it differs from frozen text:** A9-3 (plan §16.1) freezes
  `"earlier"` only as a `recency_hint` value, plus the pre-existing
  baseline `"latest"`/`"first"` literal-ref-token convention. The
  implementation additionally matches a literal `"earlier"` ref token even
  when `recency_hint` is not `"latest"`/`"first"`/`"earlier"`; that
  specific token-literal path was never frozen by A9-3.
- **Evidence it changes zero current decisions:** verified by
  `run_ir1_earlier_token_residual_check()` over all 14 factorial cases and
  all 32 natural-corpus D1RQ spans (all 4 natural surface cases × C1/C2 ×
  every detected span). `affected_row_count: 0`.
- **Classification:** `NON_EFFECTING_SPEC_RESIDUAL`.
- **Status:** neither removed, nor formally frozen. Remains open for a
  future bounded mechanism-conformance round (remove the extra token
  match, or freeze it via a plan amendment) if a row is ever found to
  depend on it.

## 6. Q Telemetry (R2-5)

- **Previous value:** `q_alone_resolves_all_case_b_ordinal_targets: false`.
- **Corrected value:** `true`.
- **Cause:** the flag's population checked disjointness against all four
  `_B_CASE_IDS` (including `B-DISTRACTOR`), but `B-DISTRACTOR` is not
  ordinal — it is reached only via the A9-2 Level-5.5 membership
  extension, which Q does not touch, and Q-alone has M/D off so A9-2 never
  restricts membership either. The flag now checks disjointness against
  exactly the three ordinal Case-B ids
  (`B-LATEST-WRONG-CLOCK`, `B-FIRST-WRONG-CLOCK`,
  `B-LATEST-PROVENANCE-TWIN`), matching its name.
- **Evidence:** `q_alone_failing_case_ids` (unchanged) =
  `["A-FIRST-2", "A-LATEST-2", "A-LATEST-DISTRACTOR", "B-DISTRACTOR",
  "C-NATURAL-PHOTOS-C2"]` — none of the three ordinal ids are in this set,
  so the corrected flag is `True`. `q_alone_resolves_b_distractor: false`
  is now reported separately and correctly.
- No resolver behavior was changed.

## 7. Performance (R2-6, R2-7)

**Sidecar interleaving:** unchanged from A9-R1 (already genuine global
interleaving, verified again this round).

**Compiler interleaving (R2-7, repaired):** the compiler arm previously
shuffled only the *storage index* within one (key, pool) block — the call
execution order itself was fully sequential by (key, pool), identical to
the sidecar defect A9-R1 already fixed. It now uses one shuffled global
`(key, pool, iteration)` schedule across every compiler condition, built
and executed the same way as the sidecar's schedule, with the same fixed
seed (`20260924`).

**Compiler old vs corrected metrics** (only one compiler condition exists —
the single qualifying cell `M1G1P1D1R1Q0`; A9-R1 never reported an
`all_off` compiler arm either, so this is a like-for-like comparison):

| Pool | A9-R1 (sequential) mean/p95 (ms) | R2 (interleaved) mean/p95 (ms) |
|---|---|---|
| 2 | not separately recorded* | 0.0305 / 0.0304 |
| 8 | not separately recorded* | 0.0310 / 0.0308 |
| 32 | not separately recorded* | 0.0323 / 0.0322 |
| 128 | not separately recorded* | 0.0376 / 0.0390 |

*A9-R1's `compiler_arm_results` values are still on disk
(`M35_URIV1_A2_8L_A9_R1_TELEMETRY.json`); this round does not overwrite
them. The compiler arm is not part of the §10.2 threshold gate (only the
sidecar all-off vs. winning-cell comparison is), so no threshold result
depends on this comparison in either direction.

**Threshold results (sidecar, unaffected by the compiler-arm fix, all
unchanged from A9-R1 and independently reproduced this round):**

| Check | Result |
|---|---|
| p95 wall overhead, pools 2/8/32 | within `max(0.25 ms, 2× baseline)` at all three |
| CPU overhead, pools 2/8/32 | within 2× baseline at all three |
| pool 32→128 growth | 3.14×, ≤6× bound |
| peak allocation, pool 128 | 29,974 B, <256 KiB |

**No threshold result changed from PASS.** Per R2-7's instruction, this
report states that explicitly rather than silently.

**CPU wording (R2-6, corrected):** the prior claim that every CPU batch
spans ≥100 timer ticks is removed. Actual measured coverage:

| Condition | Pool | Ticks (min / median / max) | Reached ≥100 target |
|---|---|---|---|
| all_off | 2 | 19 / 25 / 26 | No |
| all_off | 8 | 41 / 47 / 51 | No |
| all_off | 32 | 88 / 93.5 / 99 | No |
| M1G1P1D1R1Q0 | 2 | 24 / 29 / 31 | No |
| M1G1P1D1R1Q0 | 8 | 40 / 47 / 49 | No |
| M1G1P1D1R1Q0 | 32 | 86 / 94 / 97 | No |

The `cpu_batch_calls` cap (20,000) binds at pools 2 and 8, where per-call
cost is small enough that 20,000 calls does not add up to 100 ticks; pool
32 comes close (up to 99 ticks) but never reaches 100. This is now
reported directly (`cpu_batch_actual_ticks_min/median/max`,
`cpu_batch_reached_100_tick_target`) rather than assumed from the batch
sizing target. **CPU threshold still PASSES at all three pools** — the
margins (from the independent re-audit's own worst-case pairing) are large
enough (ratios 1.63× / 1.14× / 1.01× against the 2.0× limit at worst
pairing) that this correction does not change the threshold result.

**§16.3 item 7 subset disclosure:** CPU batched sampling covers only the 6
conditions the §10.2 threshold gate compares (all-off × winning cell,
pools 2/8/32) — a disclosed narrowing of §16.3 item 7's "not a subset"
instruction, carried forward unchanged from A9-R1, not newly introduced by
R2. Recorded explicitly in `performance.cpu_measurement_subset_of_frozen_16_3_item_7`.

## 8. §16.5 Telemetry Gap (R2-8)

`telemetry_gaps.section_16_5_per_row_fields` (recorded, verbatim summary):

- **Required fields:** per-row G/M separability (§16.5 item 1) and per-row
  R overlay-vs-gate attribution (§16.5 item 2).
- **Recorded directly:** No. Neither A9 nor A9-R1's causal rows
  (`_run_one`) emit these as dedicated fields.
- **Derivable evidence:** Yes. Both conclusions were derived by direct
  cross-referencing of the full 64-cell raw causal rows (grouping by
  `case_id` across every factor combination and comparing
  `scoring_class`/`no_op_reason` across the relevant ablated cells) in the
  A9 independent audit and the A9-R1 independent re-audit, not from a
  dedicated per-row field.
- **Residual classification:** `TELEMETRY_FORMAT_LIMITATION_NOT_EVIDENCE_GAP`.
  No new per-row telemetry field was added in R2 (out of report/label-
  correction scope); no causal conclusion was changed to hide this gap.

## 9. ER-9 Governance Correction (R2-9)

- **File:** `docs/plans/M35_URIV1_A2_8L_OVERLAY_MANIFEST.md`.
- **Note added:** new `## 6. R2 governance correction` section, dated
  2026-09-24, stating the independently-audited substance verbatim (§5
  correction: the mechanism/fixture modules already existed, untracked, at
  the A9 freeze; neither they nor any §3 file was modified by the A9
  amendment pass; the §3 hashes remain valid).
- **Historical wording preserved:** §5's original text is left completely
  unedited above the new §6; nothing was deleted or rewritten in place,
  per the Evidence Integrity Rules' auditable-correction-history
  requirement.

## 10. Tests / Verification

| Check | Result |
|---|---|
| Regression suite (8 modules) | 119 passed, 178 subtests passed (reproduced identically to A9-R1) |
| Two fresh-process causal runs | 1,792 rows each, deterministic, 0/896 decision delta vs A9-R1 |
| Transport reconciliation | 88/196, buckets sum to 88, 0 unexplained |
| Natural-surface reconciliation | 112 rows, 54 mismatches, 4+8+14+28 = 54, 0 unexplained, 0 `NB-D-02` unauthorized binds |
| Performance thresholds | all four families PASS, unchanged from A9-R1 |
| Protected/mechanism/fixture hashes | unchanged, verified before and after this round |
| Environment metadata | now captured per fresh-process run (`fresh_process_report.run1_environment_metadata` / `run2_environment_metadata`); A9/A9-R1's historical runs did not capture this (disclosed, not backfilled) |

## 11. Remaining Limitations

Carried forward unresolved, none repaired this round:

- G↔M coupling: G's event map acts as a membership signal; G's ordinal
  content never disagrees with supplied ranks in the frozen fixture set.
- R↔overlay-presence coupling: R's safe-abstention activates on overlay
  presence, not cleanly on the frozen G+P gate sequence alone; no frozen
  case supplies R=1 with no overlay.
- `NB-D-01` under production-shaped (non-oracle) ranks: pre-existing,
  out-of-scope limitation, identical across every cell including baseline.
- §16.5 per-row telemetry fields: format limitation, not an evidence gap
  (§8 above).
- IR-1's `"earlier"`-token residual: `NON_EFFECTING_SPEC_RESIDUAL`, not
  fixed (§5 above).
- §16.3 item 7: CPU measurement remains a disclosed subset of the full
  condition set (§7 above).
- Performance numbers are host-specific.

## 12. Files Changed / Produced

- `scripts/m35_a2_8l_a9_r2_correction.py` (new)
- `docs/plans/M35_URIV1_A2_8L_A9_R2_TELEMETRY.json` (new)
- `docs/plans/M35_URIV1_A2_8L_A9_R2_AGGREGATES.json` (new)
- `docs/plans/M35_URIV1_A2_8L_A9_R2_RUN1_CAUSAL.json` (new)
- `docs/plans/M35_URIV1_A2_8L_A9_R2_RUN2_CAUSAL.json` (new)
- `docs/plans/M35_URIV1_A2_8L_A9_R2_CORRECTION_REPORT.md` (new, this file)
- `docs/plans/M35_URIV1_A2_8L_A9_R2_STATE.md` (new)
- `docs/plans/M35_URIV1_A2_8L_A9_R1_INDEPENDENT_REAUDIT_REPORT.md` (new —
  the R1 re-audit's own report, written to disk this round for provenance;
  content is the unedited re-audit turn's output, not authored or altered
  by this correction round)
- `docs/plans/M35_URIV1_A2_8L_OVERLAY_MANIFEST.md` (edited — new §6 added,
  §5 preserved unedited; the separate R2-9 governance correction)

No mechanism, fixture, or protected file was modified. No historical A9 or
A9-R1 evidence file was modified.

## 13. Final State

`VERIFICATION_READY_FOR_REAUDIT`

## 14. Next Authorized Action

`INDEPENDENT RE-AUDIT ONLY`

**STOP.** Do not modify further files. Do not commit. Do not push.
