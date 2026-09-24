# M35 URIv1 — A2.8L-A9-R1 Independent Re-Audit

**Verdict:** `REPAIR_REQUIRED`
**Date:** 2026-09-24
**Auditor:** Claude Code (Opus 5.5), fresh session, re-audit-only. No mechanism,
fixture, script, telemetry, or governance file was modified. All reproduction
and counterfactual probes ran from the session scratchpad; the only
repository write from that session was this report (written retroactively
by the following R2 session, which is this same repository's continuation,
to preserve provenance for the R2 task that names this report as a source
of truth — content is unedited from the original re-audit turn's output).

**Role.** Independent re-auditor of `docs/plans/M35_URIV1_A2_8L_A9_R1_REPAIR_REPORT.md`
(status `VERIFICATION_READY_FOR_REAUDIT`), which itself repaired
`docs/plans/M35_URIV1_A2_8L_A9_INDEPENDENT_AUDIT_REPORT.md`'s verdict
`REPAIR_REQUIRED` on the original A9 rerun.

---

## 1. Verdict
**`REPAIR_REQUIRED`**

The repair only needs report and labelling fixes. No mechanism change and no
causal rerun are needed. The core A9 result holds under independent
recomputation: 1/64 qualifying cells, 0/896 decision changes, IR-1 conforms
to A9-2, transport shows 88/196 mismatches, and all four threshold families
pass. Several statements in the repair report are still materially
inaccurate, though. The main one is ER-5: the report says the tie bucket was
split by direction, but it was not.

## 2. Integrity
- **Protected files:** recomputed SHA-256 for all 8 §13.2 files plus the 2
  A2.8K R2 files. All match manifest §3 and `git status` is clean. Plan and
  manifest are identical to `591f806`.
- **Historical evidence:**
  - Pre-A9 telemetry and aggregates hashes (`50ae94e0…`, `8c0f953f…`) match
    the hash file the first audit recorded before its run. Byte-identical.
  - The A9 aggregates are key-identical to the prior auditor's scratchpad
    reproduction.
  - All A9 files have modification times of 21:00–21:03, before the audit
    (21:19) and the R1 writes (21:24 onward).
- **Fixture integrity:** `36570706…`, unchanged. Recorded the same in A9,
  R1 pre/post, and both fresh processes.
- **Authorized diff:** the mechanism file is untracked, so git has no diff.
  Rebuilt the pre-repair file from the prior auditor's scratchpad
  counterfactual copy, reverting its one-line counterfactual change. The
  rebuilt file hashes exactly to the A9 hash `dabc0797…`. Current file =
  that original + line 460 (`l5_pool_lexical` → `candidates_list`) + 16
  comment lines. The `compile_and_resolve_via_existing_contract` body is
  unchanged.
- **Unauthorized changes:** none in mechanism or fixtures, and benchmark
  semantics are unchanged.
  - **Residual:** the audit's IR-1 had a second part: remove the extra
    `"earlier" in ref_tokens` trigger (`:143`), or freeze it by amendment.
    Neither was done, and the repair report does not mention it. It has no
    effect on any decision: no factorial case or natural span uses an
    `"earlier"` token without a matching hint.

## 3. A9-2 Conformance
- **Frozen rule:** §16.1 A9-2 applies "whenever `candidate.is_attachment is
  True` for the pool member under evaluation". The evaluated pool is Level
  5.5's pool, `candidates_list`.
- **Implementation:** `rar_attachment_order_experimental.py:460` now checks
  `any(c.is_attachment for c in candidates_list)`. This implements the
  frozen text faithfully and adds no new semantics.
- **NB-C-04 C2:** in the qualifying cell and in the −G, −P and −R cells,
  the outcome is `AMBIGUOUS` over exactly `{47b0e3d6…, a85f2c19…}` on both
  rank modes. The non-turn distractor `f60d4a7b…` is excluded.
- **Factorial decision delta:** 0/896 (A9 run1 vs R1 run1). An independent
  fresh 64×14 run matches both R1 runs with 0 differences.

## 4. Factorial Result
- **Qualifying cells:** 1/64, `M1G1P1D1R1Q0`. An independent scorer built
  from fixture expectations agrees with the recorded scoring on all 1,792
  rows.
- **Pre-A9 result:** under the literal all-controls gate, 0 cells qualify,
  because `C-LEXICAL-ATTACHMENT` is unreachable.
- **D/M:** confirmed. Ablating M or D breaks no ordinal target. The M×D
  table for `A-LATEST-DISTRACTOR` passes in all four cells. D and M are
  needed only through the A9-2 Level-5.5 extension, for `B-DISTRACTOR` and
  `C-NATURAL-PHOTOS-C2`.
- **G:** confirmed as gate-induced.
  - Without G (and with R=1), R ties the domain.
  - The G event ordinal agrees with the supplied `recency_rank` in every
    Case-A and Case-B overlay.
  - G's event map also acts on membership: it ranks the no-event distractor
    last, which is why `{G,P,R}` is an alternative to `{M,D}` for
    `A-LATEST-DISTRACTOR`.
  - The data support no independent causal claim for G's content.
- **R:** necessary in the tested space: −R gives confident member binds on
  all three ordinal Case-B targets. The R↔overlay-presence coupling is
  unresolved: no case has R=1 with no overlay.
- **P:** changes decisions, but only through R's authorization gate (the
  `A-LATEST-2` / `B-LATEST-PROVENANCE-TWIN` pair).
- **Q:**
  - Q alone passes all three ordinal Case-B targets.
  - Q=1 on the qualifying background breaks all three Case-A targets.
  - "Incompatible with Case-A under the tested construction" is correct,
    and no claim of global uselessness remains.
  - **Defect:** the telemetry flag `q_alone_resolves_all_case_b_ordinal_
    targets: false` contradicts this. It is false only because the set it
    checks includes `B-DISTRACTOR`.

## 5. Interaction Result
- **M×D:** passes only at (1,1) for `B-DISTRACTOR` and `C-NATURAL-PHOTOS-
  C2`, and holds on any background. A genuine two-factor AND.
- **R:** `{R}` or `{Q}` is minimal for the three ordinal Case-B targets.
- **G×P:** passes only at (1,1) on the qualifying background for all three
  Case-A targets. The effect depends on R=1: with R=0, these targets pass
  in every G/P combination.
- **Maximum factors required by any individual case:** 3 (`{G,P,R}` for
  `A-LATEST-DISTRACTOR`).
- **Causal wording verdict:** the "genuine 5-way" and "no two-factor
  repair" claims are withdrawn. M×D is justified. G×P overstates. Required
  wording:
  > "On the qualifying-cell background (R=1), G∧P meets §7's
  > interacting-pair test for the three Case-A targets. This interaction is
  > conditional on R=1 and induced by the gate: it arises because A9-5's R
  > ties the D-restricted domain unless both G and P pass. With R=0, the
  > Case-A targets pass whatever G and P are. It is not evidence that G's
  > ordinal content or P contributes independently."

## 6. Surface Validation
- **Rows:** 112. 7 cells × 16, 4 cases × 28, 0 missing, 0 duplicate.
- **Expected scoring:** present. An independent scoring pass gives the same
  54 mismatches row for row.
- **Mismatch reconciliation:** 12 + 28 + 14 = 54, 0 unexplained.
  - **12 (label imprecise):** `NB-C-04` and `NB-C-05` C2 in the −M and −D
    cells. Each includes the distractor. Four of the 12 are the all-off
    baseline cell, not an ablation.
  - **28:** `NB-D-02`, `UNKNOWN` in every row.
  - **14:** `NB-D-01` with production-shaped all-zero ranks, which gives
    `AMBIGUOUS` in every cell.
- **NB-D-02:** 0 unauthorized binds.
- **Changed-row reconciliation:** 16 = 8 `NB-C-04` C2 + 8 `NB-C-05` C2,
  from the qualifying, −G, −P and −R cells × 2 rank modes.
  - What it compares: each cell's decision against the H3-active sidecar
    all-off decision with an empty overlay. Verified that this equals the
    all-off-cell decision on every row.
  - **Mislabel:** the report calls 16 a "correction" of the earlier "8". In
    fact the A9 value was correctly 8, all `NB-C-05`. The +8 `NB-C-04` rows
    exist only because of IR-1. The label must say this.
- **Raw-baseline equivalence:** sidecar all-off equals
  `resolve_rar_l5_experimental(h3=True)` on all 18 S-D fixtures, all 14
  factorial cases and all 32 natural queries. So the 3 + 3 raw-baseline
  differences are all attributable to H3, as claimed.

## 7. Transport
- **Parity:** meets §16.3 item 4.
  - G off removes the event maps, and P off clears provenance. Both match
    the sidecar's `g_available` / `p_authorized` gates.
  - The effective M is M∧D, which matches the rule that D consumes M (M
    alone is a no-op in the sidecar).
  - The eight §4.2.1 steps are untouched. Only the harness input is
    filtered.
- **Mismatch count:** 88/196 recomputed. Same 44 unique keys as telemetry,
  identical across repeats.
- **Attribution:** all five bucket counts reproduce and sum to 88.
  - `H3_ABSENCE_CONFOUND` = 28. The compiler equals raw baseline and the
    sidecar equals H3.
  - `D_M_LEVEL_5_5_EXTENSION_NOT_COMPILED` = 16. Correct.
  - `COMPILER_M_OR_D_GATED_NO_R_EVENT_FALLBACK` = 4, from the M0 and D0
    cells on `A-LATEST-DISTRACTOR`. The mechanism description is now
    correct.
  - `COMPILER_RANK_NOT_DENSIFIED_WITHOUT_R` = 2. Correct.
  - **`COMPILER_UNSAFE_BIND_NO_TIE_REPRESENTATION` = 38 is NOT unsafe-only.**
    8 of the rows are the G0 and P0 cells × `A-LATEST-2`/`A-FIRST-2` × 2
    repeats. In those rows the sidecar is WRONG (it abstains) and the
    compiler is CORRECT. The attributor checks only the shape of each
    outcome, never whether it is correct, so the
    `COMPILER_CORRECT_SIDECAR_OVER_GATED` branch can never be reached. The
    report's statement that the bucket is restricted to the unsafe
    direction is false.
- **Unexplained:** 0.
- **Taxonomy accuracy:** not accurate yet. The name "NO_TIE_REPRESENTATION"
  contradicts the report's own correct statement that ties can be
  represented in `recency_rank`. It needs:
  - a rename such as `COMPILER_STEP4_NO_TIE_EMISSION_UNSAFE_BIND` = 30;
  - a separate `SIDECAR_GATE_ABSTAINS_COMPILER_CORRECT` = 8.
- **Supported conclusion:** `EXISTING_CONTRACT_COMPILATION_INSUFFICIENT`,
  for the tested §4.2.1 algorithm under parity only. At the qualifying
  cell, 6 rows show a confident compiler bind where the sidecar correctly
  abstains.
- **Unsupported stronger conclusions:** `NEW_CONTRACT_FIELD_REQUIRED` is
  not established. So is any claim that the contract cannot represent
  ties.

## 8. Performance
- **Genuine interleaving:** yes for the sidecar. One global list of 64,000
  (condition, iteration) calls is shuffled with seed `20260924` and
  executed in that order.
  - **Not for the compiler arm.** The compiler-arm loop still shuffles
    only where results are stored, which is the same defect ER-6 flagged.
    The report does not disclose this.
- **Wall:** p95 overhead is within `max(0.25 ms, 2× baseline)` at pools 2,
  8 and 32.
- **Growth:** 3.14× against a 6× limit.
- **Allocation:** 29,974 B, under 256 KiB.
- **CPU timer:** measured at 15,625,000 ns. Every raw batch delta is an
  exact multiple of that step.
- **CPU methodology:** per-call cost is batch CPU ÷ K, with the median
  taken over 30 interleaved batches. Both steps are correct.
  - **The claim "each batch spans ≥100 ticks" is false.** The 20,000-call
    cap limits batches to 19–31 ticks at pool 2 and 43–50 at pool 8. At
    pool 32, where no cap applies, batches reach 85–98 ticks.
  - CPU was measured for only 6 conditions. That is disclosed, but it
    deviates from §16.3 item 7 ("not a subset").
- **CPU threshold result:** PASS, and robust.
  - Even pairing the worst batches gives ratios of 1.63 / 1.14 / 1.01
    against the 2.0 limit.
  - An independent interleaved check with 93–99 ticks per batch gave
    median ratios of 1.23 at pool 2 and 0.93 at pool 32.

## 9. Regression / Baseline
- **Tests:** 119 passed (8 modules).
- **Subtests:** 178 passed.
- **A2.5 seven-cell disposition:** a correct reconciliation of a
  requirement that does not apply. The A2.5 modules import
  `rar_deterministic`, contracts and fixtures, never the A2.8L resolver,
  so they have no factor interface. This is neither an evidence gap nor
  blocking.
- **Determinism:** two genuine subprocess runs, identical to each other
  and to an independent third fresh run.
- **Hashes:** protected and mechanism hashes are the same before and after
  the run and across processes.
- **Minor, pre-existing:** §16.3 item 8 asks for environment metadata per
  fresh-process run. Only source hashes are recorded per run.

## 10. ER Closure Matrix

| Item | Original defect | Status |
|---|---|---|
| IR-1 | A9-2 checked the wrong pool; extra `"earlier"` token trigger | **PARTIALLY_CLOSED**. Pool fixed and verified. The `"earlier"` token is neither removed, frozen, nor disclosed (no effect on decisions). |
| ER-1 | D/M attributed to "Level-5" | CLOSED |
| ER-2 | G stated reason wrong; P caveat | CLOSED |
| ER-3 | "5-way" / "no two-factor" claims; MxG example | **PARTIALLY_CLOSED**. Claims withdrawn. G×P needs the R-conditional wording in §5. |
| ER-4 | No expected-outcome scoring; "8 changed" misstated | **PARTIALLY_CLOSED**. Scoring added. Changed-row label and "ablation" label are misframed. |
| ER-5 | Tie bucket mixed directions; M-gated mechanism wrong; parity | **PARTIALLY_CLOSED**. Parity and mechanism text fixed. Direction split not done (8 rows); bucket name conflicts with ties being representable. |
| ER-6 | No interleaving; CPU unmeasured | **PARTIALLY_CLOSED**. Sidecar wall timing fixed; CPU measured and passes. Compiler arm still not interleaved (undisclosed); "≥100 ticks" claim false. |
| ER-7 | Raw-baseline equivalence missing; A2.5 applicability | CLOSED |
| ER-8 | `UNTRUSTWORTHY_ORDER_BIND` unreachable | CLOSED (48 rows) |
| ER-9 | Manifest §5 text | OPEN (non-blocking) |

## 11. Remaining Limitations
- G↔M coupling. G's event map works as a membership signal, and G's
  content never disagrees with supplied ranks in the fixtures.
- R↔overlay-presence coupling is unresolved. R's abstention only happens
  when an overlay exists. This matters for safety if the mechanism is ever
  promoted.
- `NB-D-01` with production-shaped ranks gives `AMBIGUOUS` in every cell
  and in A9. Raw baseline gives the same result, and A2.8K R2 S-A H0
  recorded it as `MISSED_RESOLVABLE_CASE`. The factorial counterpart is
  labelled "(natural, oracle ranks)". So this is
  `PRE_EXISTING_OUT_OF_SCOPE_LIMITATION`, and A9 depends on no assumption
  about it.
- `NB-D-02` safety evidence is structural: the case runs with an empty
  overlay.
- §16.5 asks for per-row telemetry fields for G/M separability and for R's
  overlay-versus-gate attribution. Neither A9 nor R1 emits them. The same
  information can be derived from the 64-cell raw rows, but the report
  should disclose the gap. The prior audit missed this.
- Performance numbers are specific to this host.
- **Independence:** the R1 implementer was the Claude session that ran the
  A9 audit. This re-audit is a fresh session but the same model family.

## 12. ER-9 Disposition
**A: `NON_BLOCKING_GOVERNANCE_DOC_CORRECTION`.** The substantive claims in
§5 are true: the §3 hashes are unaffected and nothing was touched. Only the
clause "no mechanism code exists" is false. Proposed correction, added as a
dated note so the history stays auditable rather than overwritten:
> "§5 correction (post-A9-R1 re-audit): the A2.8L mechanism and fixture
> modules already existed, untracked, in the working tree at the A9
> freeze. Neither they nor any §3 file was modified by the A9 amendment
> pass. The §3 hashes remain valid."

## 13. Final Milestone State
`A2.8L-A9-R1: REPAIR_REQUIRED (NOT VERIFIED)`. The core causal, transport
and performance results are independently verified. Only report and
labelling corrections remain. Do not accept, commit or push.

## 14. Next Authorized Action
Authorize one bounded A9-R2 correction round, followed by independent
re-audit. It covers report and telemetry labels only: no mechanism,
fixture or causal-rerun change.
1. Split transport bucket 38 into 30 unsafe binds + 8 where the compiler is
   correct, and rename it so it does not imply the contract lacks tie
   representation.
2. Correct the G×P wording.
3. Correct the changed-row and "ablation" labels.
4. Disclose the `"earlier"` residual.
5. Correct the CPU tick claim, and interleave or disclose the
   compiler-arm wall timing.
6. Fix the Q flag.
7. Disclose the §16.5 per-row telemetry gap.

The ER-9 manifest note can go through the same authorization as a separate
governance commit.

No files were modified by the original re-audit turn. Its only writes were
recomputation scripts in the session scratchpad. No commit or push.
