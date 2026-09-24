# M35 URIv1 — A2.8K-R1: H3 Rank-Semantics & Full-Decision-Accounting Repair Report

**Status:** `VERIFICATION_READY` (this repair). Not `ACCEPTED`, not `CLOSED`, not `PROMOTED`. Independent re-audit is still required before any closure.

**Author:** Claude Sonnet (bounded-fix authority during final verification, per standing AO-4 governance — this repair responds to `docs/plans/M35_URIV1_A2_8K_INDEPENDENT_FINAL_AUDIT.md`, verdict `REPAIR_REQUIRED`, authored by an independent Codex audit pass).
**Date:** 2026-09-24.

---

## Repository integrity

| Item | Value |
|---|---|
| Worktree | `C:\Users\cheta\Development\Uri\_V1` |
| Branch | `m35-uri-v1-parallel-architecture` |
| Starting HEAD | `925de8f71f73ecf67713392ca9ce959de7a12d07` |
| Ending HEAD | unchanged — no commit made |
| Legacy prototype (`C:\Users\cheta\Development\uri-agent`) | not touched |
| Protected file hashes | Identical to the independent audit's recorded values, and identical pre/post this repair's rerun: `rar_deterministic.py e02af25b…`, `rar_contracts.py 4cc9aa43…`, `rar_safe_experimental.py 4d931731…`, D1RQ `49f5faa9…`, corpus `0ea54473…`, S-D fixtures `ce25cd76…` (full values in `M35_URIV1_A2_8K_R1_TELEMETRY.json`) |
| Original A2.8K evidence | **Preserved byte-for-byte.** `M35_URIV1_A2_8K_TELEMETRY.json` (SHA-256 `89f97faa…`) and `M35_URIV1_A2_8K_AGGREGATES.json` (SHA-256 `7b223c90…`) are unchanged from before this repair — verified by hash before and after. `M35_URIV1_A2_8K_EXECUTION_REPORT.md` and `M35_URIV1_A2_8K_INDEPENDENT_FINAL_AUDIT.md` are also unchanged. This repair writes new, separately-named `_R1_` telemetry/aggregates files rather than overwriting them. |

---

## Repairs implemented

### R1-A — H3 filtered-domain ordinal ranking

**File:** `uri_v1/turn/rar_l5_experimental.py`.

Added `_domain_relative_ranks()`: once H3 restricts the candidate pool to the substantive-token-compatible domain (`_h3_domain`), the "previous"/"earlier"/"latest-current" branches now evaluate each candidate's **domain-relative** rank — computed by sorting the domain by the existing (DX-1-adjusted) `recency_rank` and assigning dense positions 0..N-1, ties sharing one position — instead of the candidate's original global `recency_rank`. This is the same tie-preserving dense-rank algorithm `m35_rar_natural_boundary_harness.build_candidate_pool` already uses to turn `created_at` into `recency_rank`; no new ordering key was invented.

A second, related defect surfaced only once R1-A's own mechanism test was run against the audit's own example (`SD-C-02`-shaped case): baseline's `has_ordering` pre-check ("does this pool carry any rank>0 metadata at all") has no valid domain-relative analogue — for a domain of exactly one member, `has_ordering` is trivially false under dense re-ranking (there is nothing else to be "greater than"), which caused H3 to still fall through even after the rank fix. Per the audit's own words ("the only — and therefore latest — member of the compatible domain"), a singleton domain must resolve directly. This is fixed by branching: when `h3` is on, the `latest`/`current` branch skips the `has_ordering` gate (redundant once dense re-ranking is used — a domain where every candidate is genuinely tied collapses into the existing `len(latest_cands) > 1` → `AMBIGUOUS` branch anyway) and evaluates `latest_cands` directly against domain-relative rank 0. When `h3` is off, the original baseline-identical `has_ordering` gate is preserved exactly, for flag-off/H1/H2/DX-1 equivalence.

`previous`/`earlier` were left using the pre-existing branch structure (only their `_rank()` calls now resolve through the domain-relative map when `h3` is on) — those branches have no equivalent gate to remove, since "earlier"/"previous" require ≥2 domain members to mean anything and the existing `len == 1` / `len > 1` logic already handles that correctly under domain-relative ranks.

### R1-B — Full decision-transition accounting

**File:** `scripts/m35_a2_8k_l5_battery.py`.

`compute_aggregates`'s changed-row detector previously treated a row as unchanged whenever `(scoring_class, actual_candidate_id)` matched between H0 and a variant. Added `_decision_tuple(row)` — `(actual_outcome, actual_candidate_id, frozenset(actual_ambiguous_ids))` — and every changed-row / new-ICB / closed-ICB / lost-correct-resolution / S-A-regression computation now compares this full tuple. An independent `reconciliation_check` was added, recomputing `aggregate_changed_row_count` vs. a direct re-scan's `raw_decision_diff_count` for every variant; both are written to the aggregates file and asserted equal in the tests below.

### Exact files changed

- `uri_v1/turn/rar_l5_experimental.py` — R1-A (`_domain_relative_ranks`, `_rank`/`_l5_pool_cached` rewiring, `latest`/`current` branch split).
- `scripts/m35_a2_8k_l5_battery.py` — R1-B (`_decision_tuple`, comparator rewrite, `reconciliation_check`); output paths changed to `M35_URIV1_A2_8K_R1_TELEMETRY.json` / `_R1_AGGREGATES.json` so the pre-repair evidence is not overwritten.
- `tests/test_m35_uriv1_a2_8k_l5_experimental.py` — the one pre-repair H3 mechanism test that encoded the defective (pre-R1-A) `UNKNOWN` outcome was replaced with tests asserting the corrected `RESOLVED` outcome, plus four new R1-A-specific tests (gapped-rank filtering, tie preservation within a domain, determinism, contiguous-domain no-regression).
- `tests/test_m35_uriv1_a2_8k_r1_repair.py` — new, narrowly scoped to R1-B (`_decision_tuple` semantics, `compute_aggregates` full accounting, the reconciliation invariant, on small synthetic telemetry — does not touch or depend on the real corpus).
- `docs/plans/M35_URIV1_A2_8K_R1_TELEMETRY.json`, `_R1_AGGREGATES.json` — new, this repair's rerun evidence.
- `docs/plans/M35_URIV1_A2_8K_STATE.md` — updated (see below); `_INDEPENDENT_FINAL_AUDIT.md` verdict text untouched.

No change to `rar_deterministic.py`, `rar_contracts.py`, `rar_safe_experimental.py`, D1RQ, the natural-boundary corpus, or the frozen S-D fixtures. No change to H1's or H2's logic (only H3's rank computation and the shared `_rank`/`_l5_pool_cached` plumbing they also call through, which is a no-op for them since neither sets `h3=True`). No new RAR contract field. No attachment-membership, event-grouping, or ordering-provenance semantics added.

---

## Verification

**Narrow tests (R1-specific):**
- `tests/test_m35_uriv1_a2_8k_l5_experimental.py::H3MechanismTests` — 5 tests covering: singleton-domain resolution (the audit's own `SD-C-02` shape), a gapped-rank domain (`{A=0,B=1,C=2,D=3}` filtered to `{B,D}` → `B` resolves as domain-rank 0), tie preservation within a domain, determinism across 5 repeated calls, and no-regression when the compatible domain equals a pool that was already contiguously ranked. **All pass.**
- `tests/test_m35_uriv1_a2_8k_r1_repair.py` — 6 tests covering `_decision_tuple` set-equivalence for ambiguous ids, the exact `AMBIGUOUS→UNKNOWN`-with-same-scoring-class-and-candidate-id shape the audit found, and the reconciliation invariant on synthetic telemetry, including a multi-variant mixed-row case. **All pass.**

**Broader tests:** the full pre-existing A2.8K suite (flag-off equivalence, one mechanism test per hypothesis, DX-1 isolation — 15 of the original 16 tests unchanged, one updated as above) plus all four applicable A2.5 RAR test modules, run together: **96 tests / 114 subtests, all pass.**

**Determinism:** the repaired battery was run twice in one invocation (`main()`'s existing two-run protocol, unchanged); `determinism_check_passed: true` in `M35_URIV1_A2_8K_R1_TELEMETRY.json` (fresh S-A/S-B/S-C/S-D rows: 3,636; S-E module-runs: 19 — identical counts to the pre-repair run, since the repaired code deterministically reruns the same fixed surfaces).

**H3 rerun result:** `resolve_rar_l5_experimental(..., h3=True)` now RESOLVES both of the audit's named examples correctly rather than falling through to `UNKNOWN`:
- `SD-C-02` ("the latest board minutes", domain-incompatible newest item excluded): `RESOLVED → sd-c2-minutes` (was `UNKNOWN`).
- `NB-D-01` C2 (natural corpus): `RESOLVED → 2f58b7c0-…` — the correct board-minutes candidate (was `UNKNOWN`, itself previously `INCORRECT_CONFIDENT_BINDING` before the original A2.8K measurement).

Pooled H3 scoring totals shifted accordingly: `CORRECT_RESOLUTION` 146 → **151**, `MISSED_RESOLVABLE_CASE` 196 → **191**, `INCORRECT_CONFIDENT_BINDING` unchanged at **12** (no new ICBs; the ICB closures the pre-repair implementation already achieved are unaffected — they simply now land on the intended correct answer instead of an uninformative abstention).

**H4 rerun result:** inherits R1-A automatically (H4 = H1+H2+H3 unmodified). Pooled totals: `CORRECT_RESOLUTION` 141 → **146**, `MISSED_RESOLVABLE_CASE` 201 → **196**, `INCORRECT_CONFIDENT_BINDING` unchanged at **6**.

**Raw/aggregate reconciliation:** `reconciliation_check` in `M35_URIV1_A2_8K_R1_AGGREGATES.json` shows `aggregate_changed_row_count == raw_decision_diff_count` for every variant (H1: 11/11, H2: 8/8, H3: 47/47, H4: 58/58, DX-1: 5/5), each with `reconciled: true`.

**S-A regression check (now trustworthy):** `H1: True`, `H2: True`, `H3: False`, `H4: False`, `DX-1: True`. H3/H4 correctly now show `False` — the audit's four omitted S-A rows are present and accounted for: `NB-D-07` r1 C1/C2 and `NB-L-04` r1 C1/C2, each `AMBIGUOUS → UNKNOWN`, identical case ids to the audit's own finding (audit §18). **The report's original claim of S-A equivalence for H3/H4 is retracted**; it was an artifact of the R1-B defect, not a property of the resolver.

Full per-row detail (all 47/58 H3/H4 changed rows, not only the S-A subset) is in `M35_URIV1_A2_8K_R1_AGGREGATES.json` under `changed_rows_vs_h0`.

**Original evidence preservation:** confirmed by hash (see Repository integrity table above) both before and after this repair's battery run.

**Git status:** everything remains untracked (no commit exists for any A2.8K artifact, original or R1); `git status --short` shows only the pre-existing untracked A2.8K files plus this repair's new files. No commit or push performed.

---

## Experimental findings (re-evaluated, not overclaimed)

1. **Does H3 still fail any cases after the rank fix?** Yes. Two disclosed, unrepaired losses remain, both **outside** R1-A's scope (the audit's corrections list does not ask R1 to fix these, and neither does):
   - `SD-C-03` (St/Street): still `UNKNOWN`. The domain is genuinely **empty** here (neither candidate's tokens contain the literal `"st"`), which is the frozen, explicitly-accepted known limitation (plan §5, Q4) — not a rank-computation defect. R1-A only changes behaviour for a **non-empty** domain.
   - `NB-D-02` C1 (natural corpus): still `UNKNOWN`, unchanged from before this repair — the plan's own §1.2 already flagged this row as "correct [in baseline] only by coincidence of pool composition," and H3's domain restriction still disturbs it for reasons unrelated to rank computation (the compatible domain excludes the coincidentally-helpful item).
   - `SD-A-08` ("the attached invoice"): still `AMBIGUOUS` for every variant, unchanged — this is a Level-5.5 lexical-narrowing gap (unmeasured follow-up hypothesis #2 in the original execution report), not something R1-A touches (R1-A is scoped to the ordinal branches, not Level 5.5).

2. **Does H4 change once accounting is complete?** H4's coarse scoring totals shift in lockstep with H3 (5 more `CORRECT_RESOLUTION`, 5 fewer `MISSED_RESOLVABLE_CASE`, ICB count unchanged at 6). H4 remains exactly additive over H1/H2/H3 — this property, established by the independent audit for the pre-repair implementation (audit §13), still holds for the repaired one: H4's 58 full decision changes are the union of H1's 11, H2's 8, and H3's 47 (with the expected overlap collapsed, since H4 = H1∧H2∧H3 combined logic run once, not three separate passes summed).

3. **Are the previously omitted 12 transitions now represented?** Yes for the *shape* of the defect (4 S-A `AMBIGUOUS→UNKNOWN` rows per variant, now correctly counted for both H3 and H4 — see the S-A regression-check table above). The **exact pre-repair counts the audit reported (45 for H3, 56 for H4) are superseded**, not reproduced: R1-A changed the underlying decisions themselves (e.g. `SD-C-02`/`NB-D-01` C2 now `RESOLVED` rather than the pre-repair `UNKNOWN`), so the *correctly-accounted* full-decision-change count for the *repaired* resolver is a different, also-correct number (H3: 47, H4: 58) — both independently reconciled against the raw rows (see above). This is expected: R1-B fixed how changes are *counted*; R1-A changed *what actually changed*. Applying the fixed counter to the fixed resolver was always going to yield a third number, not the audit's pre-repair 45/56.

4. **Does the Level-6 recency-vocabulary interaction remain observable?** Yes, on the rows R1-A does not reach: `ADV-06` (S-E) still changes `AMBIGUOUS → UNKNOWN` for H3, for the same reason as before (once Level 5 falls through — here because the H3 domain is empty, `"report"` is absent from either candidate's title — Level 6 treats the literal word `"latest"` as a missing substantive token). This interaction is unchanged by R1-A because R1-A only fixes rank computation *within* a non-empty domain; it does not change what happens when the domain is empty. **Per the audit's explicit instruction, this repair does not claim Level 6 is the sole cause of any remaining H3 miss** — `SD-C-03`/`NB-D-02` C1/`SD-A-08` above are attributed to their own distinct causes (an empty lexical domain, a coincidentally-helpful excluded item, and a Level-5.5 narrowing gap, respectively), not lumped under "Level 6."

5. **Does precedence remain a contributing failure class?** Yes, unchanged by this repair — R1-A does not touch cascade order. H2's Case-A/Case-B tradeoff (`SD-A-04`/`SD-A-06` lost vs. `SD-A-05`/`SD-A-07` gained) is identical to the pre-repair measurement (H2's aggregate numbers are byte-identical: 6 closed, 2 lost, 0 new ICBs, 0 S-E conflicts). Precedence is not resolved or superseded by the rank fix; they are different mechanisms addressing different aspects of Class A.

6. **Does candidate-domain scope remain a contributing factor?** Yes. `NB-C-05` C2's DX-1 miss (audit §14) is unaffected by this repair — DX-1's code path was not touched, and its aggregate numbers are byte-identical to before (5 closed, 0 new ICBs, 0 lost). **This repair adopts the audit's corrected explanation for `NB-C-05` C2 going forward** (a membership/domain/precedence interaction — the third, newer file-reference candidate at C2 is outside `turn_attachments` and Level 5 does not consult attachment membership at all — audit §14), superseding the original execution report's "incomplete corpus data" framing, per the audit's §22.6 instruction. Nothing in this repair's own new evidence independently re-derives this; it is adopted as the audit's established correction, not re-proven here.

7. **Is the existing contract sufficient for all observed repaired cases?** No new evidence on this question was generated by this bounded repair — it did not touch attachment membership, event/order grouping, or ordering provenance, per explicit scope prohibition. The audit's §15 finding stands: a new RAR contract field is **plausible, not experimentally established as necessary**. This repair does not claim otherwise, and no contract field was added.

8. **Do unresolved cases still expose missing evidence?** Yes — `SD-A-08`, `NB-C-05` C2, and the Q2 Case-A/Case-B distinction H2 cannot make on its own inputs all remain exactly as the audit characterized them. **This repair does not conclude a new contract field is necessary from this** (per explicit instruction); it only confirms the gap is still present after the bounded fix, which touched neither membership, ordering, nor provenance semantics.

---

## Hypothesis / causality discipline (maintained)

- **Historical H3 pre-measurement repair chronology:** remains `INSUFFICIENT_EVIDENCE`. This repair does not manufacture retroactive provenance for the disclosed pre-battery edit (the empty-compatible-domain fall-through fix made during original A2.8K implementation, before any battery run). No immutable checkpoint was created retroactively; this repair's own new code changes are themselves only as auditable as this repair report + the (still uncommitted) working tree, which carries the same limitation forward. See "Deviations / Limitations" below for what this repair did do about immutable checkpointing for *its own* changes.
- **DX-1:** unchanged interpretation — partial clock causality, a sufficient intervention for 5 of 6 measured Class-A rows, not sole root cause. DX-1's own code and results are byte-unaffected by this repair (R1-A/R1-B do not touch DX-1's tie mechanism or its own aggregate rows beyond the now-correct full-decision accounting, which does not change any DX-1 count: 5 closed / 0 new / 0 lost, identical before and after).
- **Level-6 recency vocabulary:** remains `REAL INTERACTION / NOT ESTABLISHED AS SOLE CAUSE`. This repair's own findings (§4 above) narrow *which* remaining H3 misses are attributable to it (`ADV-06` only, among the cases checked here) versus attributable to other causes (empty lexical domain for St/Street, coincidental pool composition for `NB-D-02` C1, Level-5.5 narrowing for `SD-A-08`) — consistent with, not contradicting, the audit's instruction not to treat Level 6 as the sole explanation.
- **H3/H4 validity:** not marked hypothesis-valid merely because the implementation now runs differently. The corrected semantics (domain-relative ordinal position, verified by dedicated tests against the audit's own illustrative example) and the corrected, reconciled accounting are both now in place; **mechanical classification remains `PARTIALLY SUPPORTED`** for H3 and H4 under the plan's pre-registered rubric (closes its full target-ICB set with 0 new ICBs on the corrected implementation, but still has disclosed, non-abstention-permitted correct-resolution losses — `SD-C-03`, `NB-D-02` C1 for H3; the union of H1/H2/H3's losses for H4). This repair does **not** promote either to `SUPPORTED`, `ACCEPTED`, or any equivalent status.

---

## Evidence produced

- `docs/plans/M35_URIV1_A2_8K_R1_TELEMETRY.json` — 3,636 S-A/S-B/S-C/S-D rows + 19 S-E module-runs, repaired implementation, two-run determinism confirmed.
- `docs/plans/M35_URIV1_A2_8K_R1_AGGREGATES.json` — full-decision-accounted aggregates, including the new `reconciliation_check`.
- `uri_v1/turn/rar_l5_experimental.py` — R1-A code.
- `scripts/m35_a2_8k_l5_battery.py` — R1-B code + new output paths.
- `tests/test_m35_uriv1_a2_8k_l5_experimental.py` — updated/expanded (5 H3-mechanism tests total, one superseding the pre-repair-shaped test).
- `tests/test_m35_uriv1_a2_8k_r1_repair.py` — new, R1-B-specific.
- This report, `docs/plans/M35_URIV1_A2_8K_R1_REPAIR_REPORT.md`.
- `docs/plans/M35_URIV1_A2_8K_STATE.md` — updated (independent audit verdict `REPAIR_REQUIRED` preserved verbatim in history; new entry records this repair; status set to `VERIFICATION_READY`).

---

## Deviations / limitations

- **New S-E conflict introduced by R1-A, disclosed here rather than fixed:** `test_rc1_current_conflicting_no_rank0_abstains` (`test_m35_uriv1_a2_5_rar_stage4_refinements.py`) now fails under H3 (and therefore H4). That test supplies two candidates with global ranks 1 and 2 (no rank-0 candidate present at all) and asserts `"the current report"` must not resolve, on the safety principle that RC-1 must never invent a rank-0 winner when the pool structurally lacks one. Both candidates' titles contain the substantive token `"report"`, so H3's domain equals the full, unfiltered pool — but because dense re-ranking is applied to *any* domain H3 produces (not only a domain that was actually narrowed), it still remaps the pool's ranks {1,2} down to {0,1} and resolves to the rank-1 candidate. This is a faithful, literal application of the audit's own specification ("once H3 applies its candidate-domain filtering, rank must be recalculated as ordinal position inside that filtered domain" — the audit does not condition this on the domain being a strict subset), not an implementation shortcut, and this repair's scope (R1-A + R1-B only) does not authorize inventing an additional "only re-rank when something was actually excluded" carve-out, which would be a new, unrequested rule. **It is reported here as a genuine, disclosed cost of the faithful repair, requiring the next independent audit's judgment**: whether H3's domain-relative ranking should be restricted to domains that are a strict subset of the supplied pool (preserving this test's safety property) is a design question for that audit or a future bounded follow-up, not resolved by this repair.
- **Immutable checkpoint for R1's own chronology:** this repair's changes are, like the original A2.8K artifacts, currently uncommitted. This report, the updated STATE file, and the new `_R1_` telemetry/aggregates constitute the only record of what changed and in what order; git history does not (yet) independently corroborate it. This mirrors, and does not resolve, the audit's §3/§11 concern — recorded here explicitly rather than silently repeating the same gap.
- **S-B changes for H3/H4** (16 rows each, per the original execution report's per-surface breakdown) were re-verified as part of this repair's full rerun but are not individually re-itemized in this report beyond the aggregate counts; full detail is in `M35_URIV1_A2_8K_R1_AGGREGATES.json`.

---

## Independent audit handoff

The next independent auditor should verify, at minimum:

1. That `_domain_relative_ranks` in `rar_l5_experimental.py` is deterministic and correctly dense-ranks a domain with gaps (reproduce the audit's own `A=1,B=2,C=3,D=4 → {B,D} → B=0,D=1` example independently, not only via this repair's own test).
2. That the `has_ordering`-gate removal for `h3=True` in the `latest`/`current` branch is scoped correctly (flag-off/H1/H2/DX-1 paths are byte-unchanged — confirmed by this repair's flag-off equivalence tests, but worth independent re-confirmation).
3. That `compute_aggregates`'s `_decision_tuple` comparison and `reconciliation_check` genuinely close the audit's 12-row omission — independently re-derive the H3/H4 full-decision-change counts from `M35_URIV1_A2_8K_R1_TELEMETRY.json`'s raw rows rather than trusting `M35_URIV1_A2_8K_R1_AGGREGATES.json`'s own self-reported reconciliation.
4. The new `test_rc1_current_conflicting_no_rank0_abstains` S-E conflict disclosed above, and whether it changes the auditor's view of H3's fitness even for `PARTIALLY SUPPORTED` classification.
5. Whether `SD-C-03`, `NB-D-02` C1, and `SD-A-08`'s continued losses are correctly attributed in this report (§ "Experimental findings" above) rather than conflated with the R1-A defect that has now been fixed.
6. That original A2.8K evidence (`_TELEMETRY.json`, `_AGGREGATES.json`, `_EXECUTION_REPORT.md`, `_INDEPENDENT_FINAL_AUDIT.md`) remains byte-identical to what this repair found at the start (hashes recorded above).

No promotion, acceptance, closure, commit, or push has occurred. No new experiment (A2.8L or otherwise) has been started.

**STOP — INDEPENDENT RE-AUDIT REQUIRED BEFORE ACCEPTANCE OR NEXT EXPERIMENT.**
