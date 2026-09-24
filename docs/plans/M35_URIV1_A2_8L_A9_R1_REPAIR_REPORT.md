# M35 URIv1 — A2.8L-A9-R1: Bounded Repair Report

**Status:** `VERIFICATION_READY_FOR_REAUDIT`
**Date:** 2026-09-24
**Lineage:** `591f806` (A9 freeze) -> `M35_URIV1_A2_8L_A9_*` (A9 rerun, self-reported `VERIFICATION_READY`) -> `M35_URIV1_A2_8L_A9_INDEPENDENT_AUDIT_REPORT.md` (verdict `REPAIR_REQUIRED`) -> this repair round (`A9-R1`).
**Implementer:** Claude Code, acting under standing AO-4 bounded-fixer authority (audit -> fix -> re-audit within an accepted milestone's scope; the bounded defect was found by this same session's own independent audit).
**Historical evidence preserved, not overwritten:** `M35_URIV1_A2_8L_TELEMETRY.json`/`_AGGREGATES.json`/`_EXECUTION_REPORT.md`/`_STATE.md` (pre-A9), `M35_URIV1_A2_8L_A9_*` (A9), `M35_URIV1_A2_8L_A9_INDEPENDENT_AUDIT_REPORT.md`. This round writes only to `M35_URIV1_A2_8L_A9_R1_*` paths.

No commit, push, acceptance, or closure has occurred. This report is a implementer self-report and requires independent re-audit before acceptance, exactly as the A9 rerun did.

---

## 1. Mechanism repair (IR-1)

**Frozen requirement (plan §16.1, A9-2, verbatim):** "whenever `candidate.is_attachment is True` **for the pool member under evaluation**, D restricts Level 5.5's attachment-identity counting to M's transported current-turn membership set". Level 5.5's own pool is `candidates_list`.

**Deviation found by the independent audit:** the implementation gated the extension on `any(c.is_attachment for c in l5_pool_lexical)` — Level 5's H3-word-match-filtered pool, not Level 5.5's own pool. For a reference whose substantive tokens matched no candidate title/tag (`l5_pool_lexical` empty), the extension silently never fired.

**Repair:** [`uri_v1/turn/rar_attachment_order_experimental.py:444`](uri_v1/turn/rar_attachment_order_experimental.py:444) — `l5_pool_lexical` -> `candidates_list`. One line, plus an explanatory comment. No other line of the mechanism module was touched.

**Verification:**

| Check | Result |
|---|---|
| Factorial decisions changed (896 cell×case combinations) | **0** |
| `NB-C-04` C2 D1RQ span `"the damage in the attachment bad enough"`, qualifying cell, both rank modes | now `AMBIGUOUS` over exactly `{47b0e3d6…, a85f2c19…}` — correct, matches the corresponding factorial case's expected outcome |
| Regression (114 pytest tests + `test_m35_uriv1_a2_5_candidate_invention_fix.py`) | 119 passed, 178 subtests passed |
| Protected files (§13.2, 8 files) | SHA-256 unchanged, matches overlay manifest §3 |

## 2. Full A9-R1 rerun (repaired mechanism, corrected evidence pipeline)

Two independent fresh OS-process causal runs (subprocess invocations), same protocol shape as A9: 1,792 rows each, cross-process and within-run decision-identical.

| Metric | Value |
|---|---|
| Causal rows | 1,792 (64×14×2) |
| Fresh-process determinism | `True` |
| Repeat reconciliation | `True`, 0 missing/duplicate keys |
| Qualifying cells (A9 gate, `C-LEXICAL-ATTACHMENT` excluded) | **1 / 64**: `M1G1P1D1R1Q0` |
| Literal all-controls gate | **0** (unchanged; `C-LEXICAL-ATTACHMENT` still unreachable by design) |
| Minimal sufficient sets | `M1G1P1D1R1Q0` |
| Necessary factors (global) | M, G, P, D, R |
| Protected-file hashes | unchanged, pre/post |
| Mechanism/fixture hashes | identical across both fresh processes |

**The qualifying cell is unchanged from the pre-repair A9 run.** The repair fixes an execution-surface defect (D1RQ span with no lexical H3 match), not the factorial's own 14 authored/natural cases, none of which triggered the deviation.

## 3. Per-case necessity (ER-1, ER-2, ER-3 repair)

Per-case minimal passing factor sets, computed directly from the raw 64-cell rerun:

| Case | Minimal passing sets |
|---|---|
| `A-LATEST-2`, `A-FIRST-2` | `{}` (baseline already passes) |
| `A-LATEST-DISTRACTOR` | `{M,D}` **or** `{G,P,R}` |
| `B-LATEST-WRONG-CLOCK`, `B-FIRST-WRONG-CLOCK`, `B-LATEST-PROVENANCE-TWIN` | `{R}` **or** `{Q}` |
| `B-DISTRACTOR`, `C-NATURAL-PHOTOS-C2` | `{M,D}` |
| all other controls | `{}` |

No case requires more than three factors. **Repaired claim, replacing "genuine 5-way joint requirement":**

> Qualification on the A9 gate requires all five factors M, G, P, D, R (Q off) simultaneously present *somewhere in the case set*, but the requirement is a conjunction of three separable, disjoint sub-requirements, not a five-way interaction: (i) M∧D — acting only through the A9-2 Level-5.5 extension — for `B-DISTRACTOR` and `C-NATURAL-PHOTOS-C2`; (ii) R for abstention on the three ordinal Case-B targets (Q is an alternative for those specific targets but breaks Case-A); (iii) given R=1, G∧P to prevent R's domain-wide tie on the three Case-A ordinal targets. G's necessity in (iii) is gate-induced: R ties the domain whenever G is unavailable, and G's ordinal content never disagrees with the supplied `recency_rank` in any frozen fixture (verified by a reversed-ordinal probe during the independent audit). G's event map also functions as an implicit membership signal — a non-member candidate has no event and is isolated in a lowest-ordinal singleton group.

**D/M (ER-1):** removing M or D breaks **no** ordinal Case-A/B target — `A-LATEST-DISTRACTOR` still resolves correctly with M=0 or D=0 (R's `_event_ordinal_rank_map` ranks the no-event distractor last regardless). D/M are necessary in the qualifying cell **only** through the A9-2 Level-5.5 extension, for `B-DISTRACTOR` and `C-NATURAL-PHOTOS-C2`. The prior claim that D/M are necessary "via the Level-5 mechanism" for ordinal targets is withdrawn as unsupported by the raw ablation rows.

**Qualifying-cell-background interactions (ER-3):** recomputed with the repaired classifier; per §7's own definition (neither single factor passes, the pair does, on the qualifying background), the raw rows show genuine two-factor interactions:

- `M×D` on `B-DISTRACTOR` and `C-NATURAL-PHOTOS-C2`
- `G×P` on `A-LATEST-2`, `A-FIRST-2`, `A-LATEST-DISTRACTOR`

The prior claim that "no case exposed a genuine two-factor sufficient repair" is withdrawn.

## 4. G, R, P, Q interpretation (ER-2, task item)

- **G** is required as a *gate* in the tested construction: without G, R ties every candidate in the D-restricted domain. G's ordering never disagrees with the supplied ranks in the current fixture set, so no frozen case demonstrates G's ordinal *content* mattering independently of M — G's necessity claim carries this caveat, corrected from the prior report's factually wrong stated reason.
- **R↔overlay-presence coupling (unresolved, unchanged from A9):** R's safe-abstention activates on overlay presence, not cleanly on the G+P gate outcome alone; no frozen case supplies R=1 with no overlay, so this remains an open case-set-level limitation, disclosed as before.
- **P** has a demonstrated, decision-relevant effect (the `A-LATEST-2` / `B-LATEST-PROVENANCE-TWIN` minimal pair), but that effect is observable only through R's authorization gate (P has no other consumer in this factor set, by design).
- **Q characterization (repaired, task item):** Q alone (`M0G0P0D0R0Q1`) is sufficient for all three ordinal Case-B targets, because unconditional Level-5.5 precedence abstains before the ordinal branch ever runs. It fails the global qualification gate only because the same unconditional precedence also preempts the three Case-A ordinal targets. Q is **incompatible with Case-A under this tested construction**, not globally useless — it is a narrower, correct mechanism for Case-B-only abstention. (`q_characterization` block in the aggregates.)

## 5. Surface validation (ER-4, ER-7)

**D1RQ + natural surface, 112 raw rows, scored against `expected_by_reference` (new):**

| Metric | Value |
|---|---|
| Rows | 112, 7 required cells, 0 missing/duplicate keys |
| `NB-D-02` unauthorized new-bind count | **0** |
| Expected-outcome mismatches (raw count) | 54 |
| — attributed `ABLATION_EXPECTED_A9_2_REQUIRES_M_AND_D` | 12 (`NB-C-04`/`NB-C-05` C2 under M-off or D-off ablations — the A9-2 extension correctly requires *both*; mirrors the factorial ablation table) |
| — attributed `DISCLOSED_CAPABILITY_GAP_NB_D_02` | 28 (plan §5.3's own disclosed relative-anchor gap; abstention, not a wrong bind) |
| — attributed `PRE_EXISTING_NON_ORACLE_RANK_SCOPE_LIMITATION` | 14 (`NB-D-01` under production-shaped, non-oracle ranks; see §7 below) |
| **Unexplained mismatches** | **0** |

**Changed-rows statement corrected (was: "8 changed rows, all NB-C-04/NB-C-05"):** the actual changed set is `{NB-C-04 C2: 8, NB-C-05 C2: 8}` — 16 total, split evenly across both cases' C2 pool condition. `NB-C-04` C1 and `NB-C-05` C1 never change (no non-turn distractor present to exclude).

**S-D confirmation:** 0 unexpected mismatches at baseline and the qualifying cell, unchanged.

**Raw-baseline equivalence (ER-7 / A9-4, newly measured and reported):**

| Surface | Raw ≠ sidecar-all-off count | All attributable to |
|---|---|---|
| S-D battery (18 fixtures) | 3 (`SD-B-02`, `SD-C-02`, `SD-C-03`) | A2.8K's accepted, always-on H3 substrate (A9-4) |
| D1RQ/natural (112 rows) | 3 | Same (H3 domain restriction on non-attachment natural rows) |

No diff is attributable to A2.8L's own six factors; all are the already-accepted H3 mechanism's effect, exactly as A9-4 states. This is the explicit measurement A9-4 required and the prior A9 report omitted.

**A2.5 reconciliation (ER-7):** the A2.5 regression modules exercise `resolve_rar_deterministic_extended` directly, carry no cell-flag parameter, and A2.8L never modifies that protected file. "Under every candidate winning cell" does not apply to them structurally; their obligation is regression (pass, byte-unchanged), satisfied and reported in §2/§6. Recorded explicitly (`a2_5_reconciliation` block) rather than silently skipped.

### New finding surfaced by the ER-4 scoring repair (not attributable to A9 or this repair)

`NB-D-01`'s factorial counterpart (`C-DOMAIN-RANK-NATURAL`) is scoped by the frozen fixtures to `oracle_recency=True` only. Under production-shaped (all-zero) ranks, `NB-D-01` returns `AMBIGUOUS` instead of the corpus's recorded `RESOLVED` expectation, identically across every cell including baseline — this is a pre-existing characteristic of "latest"-wording resolution without a `created_at` oracle, not a regression introduced by A9, A9-R1, or the IR-1 mechanism fix (the qualifying cell's decision on this row is identical before and after IR-1). Flagged here for visibility; no repair authorized or attempted, out of this task's bounded scope.

## 6. Transport repair (ER-5)

**Factor-state parity (plan §16.3 item 4) applied:** the compiler arm now receives an overlay filtered to the same G/P state as the sidecar (event-group/ordinal data stripped when G is off; provenance cleared when P is off) and an effective `m` flag of `M ∧ D` (D gates whether the sidecar ever applies M's restriction at all, so the compiler must not project on M alone either). The frozen §4.2.1 algorithm's 8 steps are unchanged; only the harness-level overlay/flag input to the unmodified `compile_and_resolve_via_existing_contract` was filtered.

| Metric | A9 (pre-repair) | A9-R1 (parity-repaired) |
|---|---|---|
| T | 7 | 7 |
| Rows | 196 | 196 |
| Mismatches | 90 | **88** |
| Unexplained | 0 | **0** |

**Corrected attribution taxonomy:**

| Bucket | Count | Note |
|---|---|---|
| `H3_ABSENCE_CONFOUND` | 28 | unchanged |
| `COMPILER_UNSAFE_BIND_NO_TIE_REPRESENTATION` | 38 | renamed/narrowed from the prior 42-row tie bucket, restricted to the unsafe direction only (sidecar correctly abstains; compiler confidently binds) |
| `D_M_LEVEL_5_5_EXTENSION_NOT_COMPILED` | 16 | unchanged |
| `COMPILER_M_OR_D_GATED_NO_R_EVENT_FALLBACK` | 4 | renamed from `COMPILER_M_GATED_NO_GPR_FALLBACK`; corrected mechanism (was misattributed to "H3's domain-relative rank fallback" — the actual mechanism is R's `_event_ordinal_rank_map` event-evidence fallback); count rose 2->4 because parity now also gates the compiler's projection on D, surfacing the D-ablated cell's equivalent gap |
| `COMPILER_RANK_NOT_DENSIFIED_WITHOUT_R` | 2 | unchanged |
| **Total** | **88** | sum matches `mismatch_count`; 0 unexplained |

The 4-row net reduction from 90 (details: 2 rows removed at the G-off and P-off cells, where parity now correctly withholds rank projection the un-repaired compiler previously performed unconditionally; 2 rows added at the D-off cell, where parity now correctly withholds ALL projection the un-repaired compiler previously performed on M alone) matches the independent audit's predicted 3-unique-row (×2 repeats = 6, net observed 2) discrepancy in direction and location; the exact net count differs slightly from the audit's scratchpad estimate because that estimate used a simplified counterfactual, not the full harness.

**Ties are representable in the existing `recency_rank` field** (a densified rank or an all-equal tie both fit the existing int field) — this is a limitation of the frozen §4.2.1 algorithm's step-4 branching, not of the RAR contract's field set. `NEW_CONTRACT_FIELD_REQUIRED` remains **unestablished**.

**Conclusion (unchanged in kind, recomputed):** `EXISTING_CONTRACT_COMPILATION_INSUFFICIENT`, scoped exactly to the tested §4.2.1 algorithm as executed under factor-state parity.

## 7. Performance repair (ER-6)

**Wall time:** genuinely interleaved across ALL cells and pools — a single global `(condition, iteration)` schedule (32 conditions × 2,000 iterations = 64,000 entries) shuffled once with the fixed seed `20260924`, executed in that shuffled order. The prior run only shuffled the storage index within one (cell, pool) block; execution itself was sequential by condition.

**CPU:** interleaved batched sampling (independent-audit-recommended method), scoped to the 6 conditions the §10.2 threshold gate actually uses (`all_off`, `M1G1P1D1R1Q0` × pools 2/8/32):

- Empirically measured `process_time_ns` granularity on this host: **15,625,000 ns** (one Windows scheduler tick) — recorded directly, not assumed from the nominal `get_clock_info` value.
- Per-condition batch size sized from that condition's own measured wall-time mean so each batch spans ≥100 measured ticks (≈1.56s); 30 interleaved batches per condition; batch *order* across all 6 conditions shuffled with the same seed.
- Median per-call CPU estimate reported per condition.

| Pool | Baseline CPU (ms) | Winning CPU (ms) | Threshold (2×) | Within |
|---|---|---|---|---|
| 2 | 0.0188 | 0.0230 | 0.0375 | True |
| 8 | 0.0367 | 0.0367 | 0.0734 | True |
| 32 | 0.0894 | 0.0822 | 0.1787 | True |

`cpu_evaluable: True` — CPU is no longer `UNMEASURED`.

| Check | Result |
|---|---|
| p95 wall overhead, pools 2/8/32 | within `max(0.25ms, 2×baseline)` at all three |
| pool 32→128 growth | 3.14×, ≤6× bound |
| peak allocation, pool 128 | 29,974 B, <256 KiB |
| CPU overhead, pools 2/8/32 | within 2×baseline at all three, now evaluable |

All four §10.2 threshold families pass on the repaired protocol.

## 8. Other required items

- **ER-8 (`UNTRUSTWORTHY_ORDER_BIND` reachability):** repaired — a confident bind to a *member* of the expected ambiguous set, on a Case-B target, is now classified `UNTRUSTWORTHY_ORDER_BIND`; a bind *outside* the expected set remains `INCORRECT_CONFIDENT_BINDING` for any case family. Verified reachable in the repaired raw rows (the `−R` ablation's three Case-B confident binds now classify this way).
- **ER-9 (overlay manifest §5 text):** the manifest's §5 statement "no mechanism code exists" is factually false as of the A9 commit (the mechanism module has existed since before the A9 freeze). This requires an amendment commit to the manifest file itself, which is a governance-document edit outside this bounded code/evidence repair's file scope; flagged for a follow-up documentation-only amendment, not fixed by this report.
- **R↔overlay-presence coupling, P's authorization-gated effect:** both re-verified and re-disclosed identically to the independent audit's findings (§4 above); no mechanism-code change was authorized or made to resolve either coupling.

## 9. Regression / integrity

| Check | Result |
|---|---|
| Regression suite (8 modules) | 119 passed, 178 subtests passed |
| A2.5 seven-cell applicability | `NOT_CELL_PARAMETERIZABLE` (§5, explicitly reconciled) |
| Fresh-process determinism | `True` (two genuine subprocess invocations) |
| Repeat reconciliation | `True`, 0 missing/duplicate |
| Protected-file hashes (8 files) | unchanged, match manifest §3 |
| Mechanism/fixture hashes | identical across both fresh processes |
| Pre-A9 and A9 evidence | untouched (this round writes only to `_A9_R1_*` paths) |

## 10. ER-1 through ER-9 disposition

| Item | Repair made | Status |
|---|---|---|
| IR-1 | A9-2 trigger pool corrected (`l5_pool_lexical`→`candidates_list`) | fixed |
| ER-1 | D/M necessity re-attributed to the A9-2 extension only | fixed |
| ER-2 | G gate-induced caveat corrected; P/R caveats re-disclosed | fixed |
| ER-3 | "5-way" claim replaced with 3-sub-requirement account; `M×D`/`G×P` interactions reported | fixed |
| ER-4 | D1RQ/natural surface now scored against expected outcome; changed-row statement corrected | fixed |
| ER-5 | Factor-state parity applied to compiler arm; taxonomy split/corrected/renamed | fixed |
| ER-6 | Genuine global wall-time interleaving; interleaved batched CPU sampling | fixed |
| ER-7 | Raw-baseline equivalence measured and reported; A2.5 applicability reconciled | fixed |
| ER-8 | `UNTRUSTWORTHY_ORDER_BIND` reachability repaired | fixed |
| ER-9 | Overlay manifest §5 inaccuracy | **not fixed** (governance-doc edit outside this round's file scope; flagged) |

## 11. Remaining / stop conditions hit

None of the task's STOP conditions were hit: the A9-2 repair did not require broader mechanism changes, the frozen A9-2 text was not ambiguous once "the pool member under evaluation" was read against Level 5.5's own pool variable, no factorial decision changed unexpectedly, no protected file needed modification, and the transport parity requirement did not conflict with any other frozen requirement (§4.2.1's steps are unchanged; only harness-level input filtering was added).

**Remaining, not authorized for this round:** ER-9's manifest-text correction (a governance-document amendment); the newly surfaced `NB-D-01` non-oracle-rank scope limitation (pre-existing, out of A9/A9-R1 scope); independent re-audit of this repair itself.

**STOP — INDEPENDENT RE-AUDIT REQUIRED BEFORE ACCEPTANCE OR NEXT EXPERIMENT.**
