# M35 URIv1 — A2.8K-R2: H3 Activation-Boundary Repair Report

**Status:** `VERIFICATION_READY` (this repair). Not `ACCEPTED`, not `CLOSED`, not `PROMOTED`. Independent re-audit is still required.

**Author:** Claude Sonnet (bounded-fix authority during final verification, per standing AO-4 governance). Responds to the R1 independent re-audit's `REPAIR_REQUIRED` verdict (delivered as this repair's own directive; no separate audit artifact file exists on disk for R1 — the directive's "Starting Verdict" section is the authoritative record of that finding).
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
| git status | unchanged in shape from before this repair: all A2.8K/A2.8K-R1/A2.8K-R2 artifacts remain untracked (`??`); no file outside A2.8K's own new/modified set was touched |
| Protected file hashes | Identical to the original audit's and R1's recorded values, and identical pre/post this repair's rerun: `rar_deterministic.py e02af25b…`, `rar_contracts.py 4cc9aa43…`, `rar_safe_experimental.py 4d931731…`, D1RQ `49f5faa9…`, corpus `0ea54473…`, S-D fixtures `ce25cd76…` |
| Original A2.8K evidence | **Preserved byte-for-byte** (hash-verified before and after this repair): `M35_URIV1_A2_8K_TELEMETRY.json` (`89f97faa…`), `_AGGREGATES.json` (`7b223c90…`), `_EXECUTION_REPORT.md` (`a58c64a8…`), `_INDEPENDENT_FINAL_AUDIT.md` (`b3f19411…`) |
| R1 evidence | **Preserved byte-for-byte** (hash-verified before and after): `M35_URIV1_A2_8K_R1_TELEMETRY.json` (`53453e86…`), `_R1_AGGREGATES.json` (`5599d2d7…`), `_R1_REPAIR_REPORT.md` (`4b2d6568…`) |

---

## Activation-boundary repair

**File:** `uri_v1/turn/rar_l5_experimental.py`.

R1 gated domain-relative re-ranking on the bare `h3` flag: whenever `h3=True`, `_domain_relative_ranks()` was applied to `_l5_pool_cached`, regardless of whether `_h3_domain()` had actually excluded anything. Because `_h3_domain()` returns the full pool unchanged both when there are no substantive tokens *and* when every candidate happens to be lexically compatible, R1's dense re-ranking fired in both of those cases too — remapping ranks like `{1, 2}` down to `{0, 1}` and fabricating a rank-0 "latest"/"current" winner in a pool baseline deliberately left without one.

**Fix — genuine-narrowing detection by candidate identity, not size:**

```python
_h3_narrowed = h3 and ({c.id for c in _l5_pool_cached} != {c.id for c in candidates_list})
_domain_rank_map = _domain_relative_ranks(_l5_pool_cached, dx1_tie_ids, tie_rank) if _h3_narrowed else None
```

`_l5_pool_cached` is `_h3_domain(candidates_list, substantive)` when `h3` is on. Comparing the **id sets** (not `len(...)`) of `_l5_pool_cached` and `candidates_list` means:

- **Case A (genuine narrowing):** `_h3_domain` removed at least one candidate id → id sets differ → `_h3_narrowed = True` → domain-relative ranking activates. This is exactly R1's correct behaviour for `SD-C-02` / `NB-D-01` C2 and the audit's own `A,B,C,D → {B,D}` illustration, and any other narrowing where the resulting subset happens to have the same size as some other candidate set — identity, not count, decides it, so a domain whose membership changed but size didn't (impossible for `_h3_domain`'s pure-filter design, but the check is written to be correct regardless of that implementation detail) would also correctly activate.
- **Case B (no narrowing, same members):** `_h3_domain` filtered nothing out → id sets are equal → `_h3_narrowed = False` → the function falls back to `_effective_rank` (the original global `recency_rank`, DX-1-adjusted only) and, in the `latest`/`current` branch, to baseline's original `has_ordering` gate (see below). `test_rc1_current_conflicting_no_rank0_abstains`'s two candidates both contain `"report"`, so `_h3_domain` keeps both — id sets equal — `_h3_narrowed = False` — baseline behaviour reproduced exactly.
- **Case C (no substantive tokens):** `_h3_domain` returns `list(pool)` immediately for this case (its own first branch: `if not substantive: return list(pool)`) — the id sets are trivially equal, so this collapses into Case B automatically. No separate flag was needed or added.

The same `_h3_narrowed` boolean also now gates the `latest`/`current` branch's decision to skip baseline's `has_ordering` pre-check (previously gated on bare `h3`): when the domain is not genuinely narrowed, the original `has_ordering` gate — and therefore baseline's abstention behaviour — is preserved byte-for-byte.

No new ordering rule, contract field, precedence rule, attachment-membership semantics, event grouping, ordering provenance, or lexical synonym expansion was added. `previous`/`earlier` branches needed no separate change — they already had no `has_ordering`-style gate to restore, and their `_rank()` calls now correctly resolve through the same `_h3_narrowed`-gated map.

---

## Regression verification

| Case | Test | Result |
|---|---|---|
| Genuinely narrowed domain (gapped ranks, Case A) | `H3ActivationBoundaryTests::test_genuinely_narrowed_domain_still_reranks`, `H3MechanismTests::test_h3_rank_with_gaps_in_filtered_domain` | Pass — resolves to the domain-rank-0 candidate |
| Full domain retained, no narrowing (Case B, the audit's exact shape) | `H3ActivationBoundaryTests::test_unchanged_domain_preserves_baseline_no_rank0_abstention` | Pass — baseline and H3 decision-identical, neither `RESOLVED` |
| "The current document" (directive's second named example) | `H3ActivationBoundaryTests::test_unchanged_domain_the_current_document_case` | Pass — baseline and H3 decision-identical |
| No substantive lexical tokens (Case C) | `H3ActivationBoundaryTests::test_no_substantive_tokens_preserves_baseline` | Pass |
| `test_rc1_current_conflicting_no_rank0_abstains` itself, run directly against `resolve_rar_l5_experimental(h3=True)` | `H3ActivationBoundaryTests::test_rc1_current_conflicting_no_rank0_abstains_under_h3` | Pass — does not resolve |
| Same, run through the actual legacy test module via the battery's S-E monkeypatch | `scripts/m35_a2_8k_l5_battery.py` S-E surface, H3 | **Conflict cleared** — `test_m35_uriv1_a2_5_rar_stage4_refinements` shows 0 failures for H3 (was 1 under R1) |
| Determinism, narrowed domain | `test_genuine_narrowing_still_deterministic_across_repeated_calls` (5 repeats) | Pass |
| Determinism, unchanged domain | `test_unchanged_domain_still_deterministic_across_repeated_calls` (5 repeats) | Pass |
| R1 non-regression: `SD-C-02` / `NB-D-01` C2 | `test_sd_c_02_and_nb_d_01_shape_still_resolve_after_r2`, plus the existing `H3MechanismTests` and full battery rerun | Pass — both still `RESOLVED` correctly |

Full suite: `tests/test_m35_uriv1_a2_8k_l5_experimental.py` (24 tests) + `tests/test_m35_uriv1_a2_8k_r1_repair.py` (6 tests) + all 4 applicable A2.5 RAR modules — **104 tests / 114 subtests, all pass.**

---

## Frozen battery results (R2 rerun)

Same frozen fixtures, same surfaces (S-A/S-B/S-C/S-D/S-E), same two-run determinism protocol as R1, written to new `M35_URIV1_A2_8K_R2_TELEMETRY.json` / `_R2_AGGREGATES.json`.

- **Decision rows:** 3,636 S-A/S-B/S-C/S-D records + 19 S-E module-runs — identical counts to the original and R1 runs (same fixed surfaces).
- **Determinism:** `determinism_check_passed: true`.
- **Reconciliation** (`aggregate_changed_row_count == raw_decision_diff_count`, independently re-derived): H1 11/11, H2 8/8, **H3 45/45**, **H4 56/56**, DX-1 5/5 — all `reconciled: true`.
- **S-A regression check:** H1 `True`, H2 `True`, **H3 `False`**, **H4 `False`**, DX-1 `True` — unchanged from R1. The four S-A diffs are still `NB-D-07` r1 C1/C2 and `NB-L-04` r1 C1/C2, `AMBIGUOUS → UNKNOWN` — **these are genuinely narrowed-domain rows** (confirmed by direct inspection of `_h3_domain`'s output for them), i.e. legitimate H3 effects, not instances of the activation-boundary defect. The R1 execution report's S-A-equivalence claim for H3/H4 remains correctly retracted (as R1's own report already stated); this repair does not restore it, nor should it.
- **H3 correct resolutions / ICBs:** `CORRECT_RESOLUTION` **149** (R1: 151; original pre-R1: 146), `INCORRECT_CONFIDENT_BINDING` **12** (unchanged from R1 and from the original pre-R1 implementation).
- **H4 correct resolutions / ICBs:** `CORRECT_RESOLUTION` **144** (R1: 146), `INCORRECT_CONFIDENT_BINDING` **6** (unchanged).
- **Changed decision counts vs. H0:** H1 11, H2 8, **H3 45** (R1: 47), **H4 56** (R1: 58), DX-1 5.
- **New ICBs on any surface, any variant:** **0** (unchanged from R1 and from the original run).

**What changed between R1 and R2, exactly (direct row-level diff, not inferred):** exactly 4 rows differ (2 distinct case/ref/c_axis combinations, each affecting both H3 and H4): `NB-D-03` r1 C2 and `NB-L-06` r1 C2, both S-C surface. Under R1 both were `RESOLVED` (correctly matching their expected `RESOLVED` outcome — `CORRECT_RESOLUTION`); under R2 both revert to `H0`'s own outcome (`AMBIGUOUS` and `UNKNOWN` respectively — `MISSED_RESOLVABLE_CASE`, matching baseline exactly). Per the directive's explicit instruction not to assume R1's scores must remain identical: **this is the correct, intended consequence of the activation-boundary fix**, not a new regression against H0 — baseline itself never resolved these two rows either (`H0` scoring class for both is `MISSED_RESOLVABLE_CASE`, identical to H3/H4 under R2). R1's `CORRECT_RESOLUTION` on these two rows was produced by the same unsafe mechanism the R1 audit flagged (fabricating a rank-0 winner in an unnarrowed domain) landing, in these two specific cases, on the answer that happened to be correct. Losing that accidental correctness is the price of removing the unsafe mechanism, and is reported here plainly rather than being characterized as either a pure gain or a pure loss.

**Newly introduced regressions relative to R1:** none beyond the disclosed reversion above (which is a reversion to baseline-matching, not a new incorrect outcome). **Newly introduced regressions relative to H0 (baseline):** none — `new_icb_vs_h0` is 0 for every variant on every surface, unchanged.

Full per-row detail is in `M35_URIV1_A2_8K_R2_AGGREGATES.json` under `changed_rows_vs_h0`, `new_icb_vs_h0`, `closed_icb_vs_h0`, `lost_correct_resolutions_vs_h0`.

---

## Experimental findings (R2-supported claims only)

- **The activation-boundary defect is repaired.** Direct evidence: `test_rc1_current_conflicting_no_rank0_abstains`'s S-E conflict is cleared under H3 (0 failures, was 1 under R1); the two directive-named unnarrowed-domain shapes (`the current report` with ranks {1,2}, `the current document` with ranks {1,2}) are decision-identical to baseline under H3.
- **Genuine H3 narrowing still works.** `SD-C-02` and `NB-D-01` C2 (the R1 audit's own named examples) both still resolve correctly; the gapped-rank illustration (`A,B,C,D → {B,D}`) still resolves to the domain-rank-0 member.
- **S-E baseline safety behaviour is restored** for the specific conflict named in the R2 directive. One other, unrelated H3 S-E conflict (`ADV-06`, a genuine-empty-domain case unaffected by this repair) remains, as it did under R1 — not newly introduced, not addressed by this repair (out of its scope).
- **No new regression appears** against either H0 or R1, beyond the disclosed, intentional reversion of two rows whose R1 "correctness" was itself the product of the defect this repair removes.
- **Mechanical classification under the frozen rubric:** H1, H2, H3, H4 all remain `PARTIALLY SUPPORTED` — unchanged label, now computed on the R2-corrected implementation and the R1-corrected (and re-verified) accounting.

This repair does **not** conclude, and explicitly disclaims:
- that H3/H4 are `ACCEPTED` or that A2.8K is closed;
- that a new RAR contract field is necessary (untouched question, no new evidence generated on it);
- that any remaining H3 failure (`SD-C-03`, `NB-D-02` C1, `SD-A-08`, `ADV-06`) shares one root cause;
- anything about DX-1's causal interpretation, H1/H2's own tradeoffs, or the Level-6 interaction, all of which are untouched by this repair and stand exactly as R1 left them.

---

## Evidence produced

- `uri_v1/turn/rar_l5_experimental.py` — R2 code (`_h3_narrowed` activation-boundary check, `latest`/`current` branch gate updated, module docstring extended).
- `scripts/m35_a2_8k_l5_battery.py` — output paths and schema strings bumped to `_R2_`; no logic change (R1-B accounting was not found defective by the R1 re-audit).
- `tests/test_m35_uriv1_a2_8k_l5_experimental.py` — new `H3ActivationBoundaryTests` class (9 tests).
- `docs/plans/M35_URIV1_A2_8K_R2_TELEMETRY.json`, `_R2_AGGREGATES.json` — this repair's rerun evidence.
- This report, `docs/plans/M35_URIV1_A2_8K_R2_REPAIR_REPORT.md`.
- `docs/plans/M35_URIV1_A2_8K_STATE.md` — updated, full verdict history preserved (see below).

---

## Limitations

- **Chronology/mutability:** identical limitation to R1 and the original batch — this repository's A2.8K/A2.8K-R1/A2.8K-R2 artifacts remain entirely uncommitted. No immutable checkpoint was manufactured for this repair's own changes; git history does not independently corroborate the order of edits within this repair beyond this report's own narrative and the file timestamps on disk. Stated truthfully, not worked around.
- **No independent audit file exists for the R1 re-audit this repair responds to** — its findings are recorded only in this task's own directive text, which this report treats as the authoritative statement of what R1 needed fixing, per standard practice for a directive-driven bounded repair. A future auditor should treat that directive text (reproduced in spirit throughout this report) as the R1-audit record until/unless a separate artifact is produced.
- **The two reverted S-C rows** (`NB-D-03`, `NB-L-06`) are reported factually above; this repair does not further investigate why R1's specific fabricated rank-0 choice happened to match ground truth for those two particular rows — that would be scope creep beyond the activation-boundary fix.
- No `CLARIFICATION_REQUIRED` condition was encountered: the membership-based genuine-narrowing test is unambiguous given `_h3_domain`'s existing, unmodified pure-filter design.

---

## Independent audit handoff

The next independent auditor should independently reproduce:

1. That `_h3_narrowed` correctly returns `False` for `test_rc1_current_conflicting_no_rank0_abstains`'s exact candidate set, and `True` for `SD-C-02`'s.
2. That the `latest`/`current` branch's `has_ordering` gate is reachable and behaves byte-identically to baseline whenever `_h3_narrowed` is `False`, including via a fresh flag-off-style corpus-scale comparison, not only the unit tests.
3. The R1→R2 4-row diff (`NB-D-03` r1 C2, `NB-L-06` r1 C2, ×2 variants) directly from `M35_URIV1_A2_8K_R1_TELEMETRY.json` vs. `M35_URIV1_A2_8K_R2_TELEMETRY.json`, independently, rather than trusting this report's arithmetic.
4. That `M35_URIV1_A2_8K_R2_AGGREGATES.json`'s `reconciliation_check` genuinely matches a raw re-scan (same method as required for R1).
5. That no other unnarrowed-domain shape in the natural corpus or S-D was missed by this repair's own test coverage.
6. That original, R1, and R2 evidence files remain mutually distinguishable and byte-identical to their recorded hashes.

No promotion, acceptance, closure, commit, or push has occurred. No new experiment has been started.

**STOP — INDEPENDENT RE-AUDIT REQUIRED BEFORE ACCEPTANCE OR NEXT EXPERIMENT.**
