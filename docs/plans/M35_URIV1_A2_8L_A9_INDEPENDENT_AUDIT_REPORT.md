# M35 URIv1 — A2.8L-A9 Independent Audit & Acceptance Review

**Verdict:** `REPAIR_REQUIRED`
**Date:** 2026-09-24
**Branch / HEAD:** `m35-uri-v1-parallel-architecture` / `591f80656fc8c21ce7766986c6485ef630d69f76` (A9 freeze commit)
**Audited state:** `docs/plans/M35_URIV1_A2_8L_A9_STATE.md` (`VERIFICATION_READY`)
**Auditor:** Claude Code (Opus 5.5), fresh session, audit-only. No implementation, fixture, script, telemetry, or governance file was modified. All reproduction and counterfactual probes ran from the session scratchpad; the only repository write is this report.

**Independence disclosure.** The A9 implementer was also a Claude Code session (one-off role exception recorded in the A9 state file). This audit shares no session context with it and re-derived every result from raw files and fresh execution, but it is the same model family, not a different vendor.

---

## 0. Acceptance criteria used (defined before the audit)

1. Repository/governance: correct baseline; A9 amendments are exactly those committed at `591f806`; protected files and pre-A9 evidence unchanged; A9 evidence additive.
2. Reproduction: two genuine fresh OS processes; 1,792 rows each; zero missing/duplicate keys; decision-identical; analysis and transport conclusion reproduce byte-identically.
3. Factorial: `M1G1P1D1R1Q0` independently derived as the sole qualifying cell from raw rows; every necessity/sufficiency/interaction claim matches raw ablation evidence at per-case level, with the §16.4/§16.5 caveats applied accurately.
4. Surfaces: 112 raw natural/D1RQ rows over the 7 required cells; zero `NB-D-02` unauthorized binds; report statements about those rows match the raw rows.
5. Regression: 114 tests / 178 subtests pass.
6. Transport: T=7, 90/196 mismatches; every mismatch causally (not only rule-) attributed; conclusion limited to the tested §4.2.1 algorithm; `NEW_CONTRACT_FIELD_REQUIRED` absent; §16.3 item 4 factor-state parity met or disclosed.
7. Performance: §10.2/§16.3 protocol executed as pre-registered (including randomized/interleaved order and adequate CPU timer); thresholds evaluated.
8. Claims: every material claim in the report/state/aggregates is SUPPORTED by raw evidence or narrowed.

---

## 1. Repository / governance integrity

| Check | Result |
|---|---|
| HEAD = `591f806`; A9 commit touches only the plan and overlay manifest | Confirmed (`git show --stat`). |
| 8 protected files (§13.2) | SHA-256 recomputed independently; identical to manifest §3, A9 telemetry pre/post, and pre-A9 telemetry. All tracked; `git diff` empty. |
| A2.8K R2 telemetry/aggregates | Hashes match manifest §3 (`9f40f53a…`, `f1be0393…`). |
| Plan and manifest vs `591f806` | No working-tree diff. |
| Mechanism/fixture modules | `dabc0797…` / `36570706…`; identical to A9 telemetry pre/post and both fresh-process runs. Pre-A9 telemetry recorded no mechanism hash, but the 1,792 pre-A9 decision rows are identical to the A9 rows, which is behavioral evidence that the mechanism did not change between runs. |
| Pre-A9 evidence preserved | The pre-A9 script, telemetry, aggregates, report, and state all have modification times 20:15–20:20, before the A9 commit at 20:46 and the A9 rerun at 21:00. They are untracked, so no committed hash exists; preservation is supported by modification time and decision identity, not by a recorded hash. |
| Other working-tree modifications | `SKILL.md` and `docs/governance/URI_AGENT_RELAY.md` are modified, but both date from 2026-09-23/24 before A2.8L (A2.8J-era relay handoff). They are unrelated to A9 and were not assessed further. |
| Manifest §5 text | States "no mechanism code exists". That is false at the A9 commit: the mechanism module has existed since 20:16. This is a low-severity documentation inaccuracy in a committed file. |

**Conformance of the mechanism to the A9 text.** The A9 report says the modules implement A9-1 through A9-5 "byte-for-byte". That claim is **overstated**:

- **A9-2 (deviation, decision-relevant).** The frozen text says D restricts Level-5.5 counting "whenever `candidate.is_attachment is True` for the pool member under evaluation". The code (`rar_attachment_order_experimental.py:444`) adds a condition: `any(c.is_attachment for c in l5_pool_lexical)`. That makes the extension depend on the H3 lexical pool being non-empty. If a span has substantive tokens that match no candidate, H3 returns an empty pool, the extension never fires, and M/D are recorded as `ORDINAL_TRIGGER_NOT_MATCHED`. See §5 for the resulting surface failure.
- **A9-3 (minor).** The code also triggers on an `"earlier"` token in the reference text (`:143`). A9-3 freezes `"earlier"` as a hint value only, plus the literal `"latest"`/`"first"` tokens. No frozen case or surface row exercises this difference.

## 2. Fresh reproduction

The rerun script was copied to the scratchpad with only the four output paths redirected, then executed. The submitted evidence files were hash-checked before and after the run and did not change.

- Two genuine child OS processes (`subprocess.run([sys.executable, …, "--causal-only"])`); 1,792 rows each; 1,792 unique keys; 0 duplicates.
- Cross-process decisions are identical, and within-run repeats are identical.
- Every aggregate key (`qualifying_analysis`, both interaction tables, transport conclusion/counts/attribution, `NB-D-02` count, determinism, and hash flags) is **byte-identical** to the submitted aggregates. Causal rows (excluding latency), transport rows, natural rows, and S-D rows are also identical.
- Regression: `114 passed, 178 subtests passed` (the seven modules listed in the report). An additional A2.5 module (`test_m35_uriv1_a2_5_candidate_invention_fix.py`, 5 tests) also passes.

**Result: reproduction SUPPORTED.**

## 3. Factorial / causal audit

An independent scorer was written from the fixture expectations, not from the rows' `scoring_class`. It agrees with the implementer's scoring on all 896 cell×case rows.

- Qualifying cells under the A9 gate: **only `M1G1P1D1R1Q0`**. With the literal all-controls gate, **0** cells qualify, because `C-LEXICAL-ATTACHMENT` fails in all 64 cells. That independently reproduces part of the preserved pre-A9 literal result. **SUPPORTED.**
- One-factor ablations of the qualifying cell (raw rows):

| Ablation | Failing gated cases | Outcome |
|---|---|---|
| −M | `B-DISTRACTOR`, `C-NATURAL-PHOTOS-C2` | AMBIGUOUS including non-turn distractor |
| −D | `B-DISTRACTOR`, `C-NATURAL-PHOTOS-C2` | same |
| −G | `A-LATEST-2`, `A-FIRST-2`, `A-LATEST-DISTRACTOR` | AMBIGUOUS (R domain-wide tie) |
| −P | `A-LATEST-2`, `A-FIRST-2`, `A-LATEST-DISTRACTOR` | AMBIGUOUS (R domain-wide tie) |
| −R | `B-LATEST-WRONG-CLOCK`, `B-FIRST-WRONG-CLOCK`, `B-LATEST-PROVENANCE-TWIN` | confident member bind |
| +Q | `A-LATEST-2`, `A-FIRST-2`, `A-LATEST-DISTRACTOR` | L5.5 preempts ordinal: AMBIGUOUS |

- Minimal passing factor sets per case, over all 64 cells:

| Case | Minimal passing sets |
|---|---|
| `A-LATEST-2`, `A-FIRST-2` | `{}` (pass in the all-off cell) |
| `A-LATEST-DISTRACTOR` | `{M,D}` **or** `{G,P,R}` |
| `B-LATEST-WRONG-CLOCK`, `B-FIRST-WRONG-CLOCK`, `B-LATEST-PROVENANCE-TWIN` | `{R}` **or** `{Q}` |
| `B-DISTRACTOR`, `C-NATURAL-PHOTOS-C2` | `{M,D}` |
| all other gated controls | `{}` |

### 3.1 D / M

- **Demonstrated:** M and D are necessary in the qualifying cell **only** through the A9-2 Level-5.5 extension, for `B-DISTRACTOR` and `C-NATURAL-PHOTOS-C2`.
- **Not demonstrated, and contradicted by raw rows:** the report says D/M "are necessary for the ordinal Case-A/B targets *via the Level-5 mechanism*". Ablating M or D breaks **no** ordinal target. `A-LATEST-DISTRACTOR` still resolves correctly with M=0 or D=0, because R's event-ordinal rank map ranks the no-event distractor last. The qualifying-background table `MxD` on `A-LATEST-DISTRACTOR` is PASS in all four cells. The Level-5 ordinal-domain restriction is therefore redundant in the qualifying cell. This statement violates §16.4 rule 3. **UNSUPPORTED.**
- The C2 and `B-DISTRACTOR` claim is SUPPORTED.

### 3.2 G / M

- G's ordinal **content** is never decision-relevant in the frozen set. For all three Case-A fixtures, the G order equals the supplied member-rank order. A reverse-ordinal probe does flip the decision, which proves the content is consumed, but the frozen fixtures never make G's content disagree with the supplied ranks.
- G's necessity in the qualifying cell is **gate-induced**. With R=1, missing G makes R tie the whole domain (A9-5 / code `:490–496`). The qualifying-background table `GxR` shows G is irrelevant when R=0 (`G=0,R=0` PASS).
- The G↔M coupling is concrete. G's event map works as a membership signal, because non-members have no event and are ranked last. This is why `{G,P,R}` is an alternative to `{M,D}` for `A-LATEST-DISTRACTOR`.
- The report's stated reason is factually wrong. It says the case set lacks a row where G is ablated while M's membership is still visible, but `M1G0P1D1R1Q0` is exactly that row, with M present. **OVERSTATED / mis-described.**

### 3.3 R / overlay presence

- R is necessary within the tested 64-cell space: R=0 produces confident member binds on all three ordinal Case-B targets. `{Q}` is an alternative that abstains on Case-B but breaks Case-A.
- The coupling is confirmed from code and a probe. R's safe-abstention runs only when `_case_is_overlay_bearing`. With an empty overlay, an ordinal Case-B query binds confidently (`sd-a5-x`) even in `M1G1P1D1R1Q0`. With a membership-only overlay (no G/P data), R ties. R therefore activates on overlay presence, not on the G+P gate state. No frozen case separates the two.
- The report's disclosure of this is adequate. **SUPPORTED_WITH_CAVEAT.** Safety note for any future promotion: R's abstention is conditional on an overlay existing.

### 3.4 P

- P's content is decision-relevant. The `A-LATEST-2` / `B-LATEST-PROVENANCE-TWIN` minimal pair differs only in provenance, and the two outcomes differ at the qualifying cell.
- P has no consumer outside R (by A1 design), so P's effect exists only when R=1.
- "P is clean" relative to the two disclosed couplings is acceptable if the report adds that P's effect is observable only through R's authorization gate. **SUPPORTED_WITH_CAVEAT.**

### 3.5 Q

Q0 establishes two things:

1. Q is not necessary.
2. Q=1 on the qualifying background breaks all three Case-A targets, because L5.5 preempts the ordinal branch.

The data also show that Q alone is **sufficient** for the three ordinal Case-B targets. Q is therefore not "useless". It is incompatible with Case-A under the frozen precedence semantics. This confirms HQ on authored fixtures only; it does not show Q is globally harmful.

## 4. Interaction analysis

- **All-off background.** No pair qualifies, so no pair meets §7's interaction rule. This is correct but uninformative, as the report says.
- **Qualifying-cell background.** The report's own tables contradict its narrative:
  - `MxG` on `B-DISTRACTOR`: `M=1,G=0` is PASS, so G is irrelevant there. The report says the case passes "only when both M and G/D are at their qualifying values"; that is wrong for G.
  - `MxD` on `B-DISTRACTOR`: only `M=1,D=1` passes. This is a genuine two-factor joint requirement.
  - `GxP` on Case-A (with R=1): only `G=1,P=1` passes. This is a genuine two-factor joint requirement.
  - Under §7's own definition, with the background set to the qualifying cell, `{M,D}` and `{G,P}` meet the interacting-pair test: neither single factor repairs the case, the pair does, and the pair belongs to the minimal sufficient set. The claim that no case shows "a genuine two-factor … repair" is therefore **incorrect**.
- **"Genuine 5-way joint requirement" is OVERSTATED.** No case needs more than three factors, and the three sub-requirements cover disjoint case subsets. Required replacement wording:

> "Qualification on the A9 gate requires all five factors M, G, P, D, R (with Q off), but the requirement is a conjunction of three separable sub-requirements, not a five-way interaction: (i) M∧D, acting only through the A9-2 Level-5.5 extension, is required for `B-DISTRACTOR` and `C-NATURAL-PHOTOS-C2`; (ii) R is required for abstention on the three ordinal Case-B targets (Q is an alternative for those targets but breaks Case-A); (iii) given R=1, G∧P is required only to prevent R's domain-wide tie on the Case-A targets. G's necessity is gate-induced (its ordinal content never disagrees with supplied ranks in the frozen fixtures) and is coupled to membership (G's event map ranks non-members last). R's abstention is coupled to overlay presence. No single case requires more than three factors, and none requires all five."

## 5. Mandatory surface validation (raw rows)

- 112 rows; 112 unique keys. Each of 4 cases has 28 rows. Each of the 7 required cells (baseline, qualifying, five ablations) has 16 rows. **SUPPORTED.**
- `NB-D-02`: all 28 rows are `UNKNOWN` in both baseline and every cell. There are **0** unauthorized binds. **SUPPORTED.** The invariance is structural: `NB-D-02` runs with an empty overlay, and R needs overlay presence. It is weak evidence of safety beyond this row.
- **Misstatement.** The report says "Rows changed from baseline: 8 (all `NB-C-04`/`NB-C-05`) … same membership-restriction mechanism". In fact all 8 changed rows are **`NB-C-05` C2**, and **no `NB-C-04` row changed**.
- **`NB-C-04` C2 under the qualifying cell is WRONG_AMBIGUITY_DOMAIN** on both rank modes. The ambiguity set includes the non-turn distractor `f60d4a7b…`, although the factorial counterpart `C-NATURAL-PHOTOS-C2` passes.
  - **Cause:** the D1RQ span `'the damage in the attachment bad enough'` yields substantive tokens `damage/bad/enough`. H3's lexical pool is empty, so the A9-2 deviation noted in §1 suppresses the extension.
  - **Counterfactual** (scratchpad copy, one-line change to the literal A9-2 trigger `any(c.is_attachment for c in candidates_list)`): **0 of 896** factorial decisions change, and `NB-C-04` C2 becomes correct (AMBIGUOUS over exactly the two turn attachments) on both rank modes.
  - The row is unchanged from baseline, so it is not "introduced" under §9 criterion 7. It is still a frozen-text conformance defect exposed on a mandatory surface, and the report did not disclose it.
- The D1RQ surface scores only `CHANGED`/`UNCHANGED`/`NB-D-02`, never correctness against `expected_by_reference`. That is why this defect was missed.
- The S-D confirmation runs flag-on cells with an **empty overlay**, so its "0 unexpected mismatches" is structurally expected and is weak evidence.
- The requirement in §16.3 item 2 to run the A2.5 surface under every winning cell and its ablations was not met. The A2.5 test modules do not exercise the A2.8L resolver under cell flags. The report does not disclose this.
- The raw-baseline equivalence measurement required as "separately reported" by A9-4 is absent from the A9 telemetry.

## 6. Regression

`114 passed, 178 subtests passed`, reproduced. **SUPPORTED.** There are no environmental exclusions. The A2.8L test file is implementer-authored and untracked, and it does not cover the confirmation surfaces.

## 7. Transport audit

- T=7, 196 rows, 90 mismatches, 0 compiler errors. The bucket sum is 90, with 0 `UNEXPLAINED`. Repeat-1 and repeat-2 attributions are identical. **Counts SUPPORTED.**
- Attribution is rule-based. Case-id membership assigns two of the buckets, and the state file says the taxonomy was "iteratively refined against the actual observed mismatch patterns". Each bucket was therefore checked causally:

| Bucket | Rows | Causal check | Verdict |
|---|---|---|---|
| `H3_ABSENCE_CONFOUND` | 28 | Raw baseline ≠ sidecar all-off on both controls; the compiler equals raw baseline. Mismatch occurs even in the all-off cell. | SUPPORTED. The two arms share no common baseline for these controls. |
| `D_M_LEVEL_5_5_EXTENSION_NOT_COMPILED` | 16 | Occurs only in the four M1∧D1 cells; the compiler passes through unmodified. | SUPPORTED |
| `COMPILER_NO_TIE_ABSTENTION_REPRESENTATION` | 42 | 30 rows: sidecar abstains correctly and the compiler binds unsafely on Case-B. 12 rows (G0/P0 cells, Case-A): the sidecar is the **wrong** arm (abstains through a gate) and the compiler resolves correctly. | SUPPORTED_WITH_CAVEAT. The bucket must be split by correctness direction. The name must not suggest a contract limitation: a tie-emitting compiler using only existing `recency_rank` (all members set to 0 when R=1 and not authorized) reproduces the sidecar on all 18 ordinal rows at the qualifying, G0, and P0 cells. The gap is in step 4 of the algorithm, not in contract expressiveness. |
| `COMPILER_M_GATED_NO_GPR_FALLBACK` | 2 | `M0G1P1D1R1Q0` `A-LATEST-DISTRACTOR`: the sidecar is correct and the compiler binds the distractor. The bucket description credits "H3's own domain-relative rank fallback". The actual mechanism is R's `_event_ordinal_rank_map`, which ranks the no-event distractor last. | Count SUPPORTED; mechanism description WRONG |
| `COMPILER_RANK_NOT_DENSIFIED_WITHOUT_R` | 2 | `M1G1P1D1R0Q0` `A-LATEST-DISTRACTOR`: the sidecar's `_fallback_rank_map` densifies the narrowed domain; the compiler's projected pool has no rank-0 member and returns AMBIGUOUS. | SUPPORTED. It is distinct from the tie bucket (R=0 densify versus R=1 tie), so the two should not be merged. |

- **§16.3 item 4 factor-state parity not met and not disclosed.** The compiler receives only `m`, `r`. Step 2 projects whenever M=1, ignoring D. Step 4 reads provenance and event groups from the overlay whether or not G/P are on, and the diagnostics show `RANKS_PROJECTED` in the G0 and P0 cells. A parity-honoring variant (projection needs M∧D; rank projection needs R∧G∧P) gives 44 unique mismatches instead of 45:
  - `A-LATEST-DISTRACTOR` in the G0 and P0 cells (4 rows) disappears. Those rows are caused by the non-parity, not by missing tie output.
  - `A-LATEST-DISTRACTOR` in the D0 cell appears.
  - The 90-row count is therefore valid only for the as-executed, non-parity compiler. The plan's own §4.2.1 algorithm has no G/P/D inputs, so the requirement conflicts internally with the unamended algorithm. That conflict should have been disclosed.
- **Conclusion.** `EXISTING_CONTRACT_COMPILATION_INSUFFICIENT` **for the tested §4.2.1 algorithm** is SUPPORTED, with or without parity. At the qualifying cell, three ordinal Case-B rows (×2 repeats) show the compiler binding confidently where the sidecar abstains. Those rows are not affected by H3, L5.5, or parity.
- **Scope.** The tie counterfactual is outside the frozen plan and must not be claimed as sufficiency. It does show that the evidence does **not** lean toward a representational gap in existing contracts. `NEW_CONTRACT_FIELD_REQUIRED` was not produced or established. **Confirmed.**

## 8. Performance audit

- Wall p95 (pools 2/8/32), growth, and peak allocation reproduce within noise:
  - fresh reproduction p95: 0.0252 / 0.0387 / 0.0898 ms against 0.25 ms allowed;
  - growth 3.52× (submitted 3.2×);
  - peak allocation 29,926 B.
  - All three are within threshold with large margin.
- **Protocol deviation (undisclosed).** The "randomized/interleaved" schedule is not implemented. The code measures each (cell, pool) block sequentially and shuffles only the index where each sample is stored (`rng.shuffle(schedule)`). Execution is never interleaved across cells or pools; the in-code comment says it builds a shuffled (cell, pool, iteration) list, and it does not. The seed is therefore inert. With margins this large, the threshold outcome is very unlikely to change, but the claim that the §10.2 protocol was executed is **OVERSTATED**.
- **CPU: `CPU_REMEASUREMENT_REQUIRED`.**
  - §16.3 item 6 (frozen) requires "a CPU timer with resolution adequate to the measured durations" and the *measured* clock resolution. §9 criterion 13 requires the CPU measurements to be present.
  - Empirical `process_time_ns` granularity on this host is **15,625,000 ns** (one Windows scheduler tick). The recorded `1e-7` is only the nominal `get_clock_info` value.
  - `UNMEASURED` is honestly disclosed, not faked, but it leaves a pre-registered acceptance criterion unmet. The fix is cheap and does not touch the mechanism.
  - **Method:** batched, interleaved CPU sampling with the same unchanged call.
    1. Record the observed smallest nonzero `process_time_ns` step first.
    2. For each (cell, pool), run B ≥ 30 batches. Each batch is K calls, with K chosen so the batch CPU time is ≥ 100 ticks (≈ 1.6 s; K ≈ 15–20k at pool 32). Quantization error is then ≤ 1%.
    3. Randomize batch order across all cells and pools with the recorded seed.
    4. Report per-call CPU as `batch_cpu / K`, then the median across batches, and apply the ≤ 2× median threshold.
  - A scratchpad check gave ≈ 0.094 ms (all-off) and ≈ 0.086 ms (winning) per call at pool 32, from a single 2,000-call batch. This is indicative only; the batch was not interleaved or repeated and is not a substitute measurement.

## 9. Claims-versus-evidence register

| Claim | Classification |
|---|---|
| 1/64 qualifying; `M1G1P1D1R1Q0` is the sole minimal sufficient cell | SUPPORTED |
| Pre-A9 literal result (0 qualifying) preserved separately | SUPPORTED (reproducible from raw rows under the literal gate) |
| Mechanism "byte-for-byte" A9-1…A9-5 conformant | OVERSTATED (A9-2 trigger deviation; A9-3 extra token) |
| "Necessary factors M, G, P, D, R" | SUPPORTED_WITH_CAVEAT (necessary only within this factor space and case set; see §3) |
| D/M necessary "via the Level-5 mechanism" for ordinal targets | UNSUPPORTED (contradicted by the −M/−D ablations) |
| D/M necessary for `B-DISTRACTOR`/C2 via A9-2 | SUPPORTED |
| G necessity with the stated §16.5-1 reasoning | OVERSTATED (gate-induced; stated reason factually wrong) |
| R necessity with the overlay-presence caveat | SUPPORTED_WITH_CAVEAT |
| P "clean" | SUPPORTED_WITH_CAVEAT (effect only through R) |
| "Genuine 5-way joint requirement" / "no two-factor repair" | OVERSTATED / incorrect on the qualifying background |
| Qualifying-background `MxG`/`B-DISTRACTOR` example | UNSUPPORTED (G irrelevant) |
| 112 rows, 7 cells, 0 `NB-D-02` binds | SUPPORTED |
| "8 changed rows, all `NB-C-04`/`NB-C-05`" | UNSUPPORTED (all `NB-C-05`; `NB-C-04` C2 stays wrong-domain) |
| S-D 0 unexpected mismatches | SUPPORTED_WITH_CAVEAT (empty overlay; structurally expected) |
| A2.5 surface under all 7 cells | UNSUPPORTED (not executed under cell flags) |
| 114 / 178 regression | SUPPORTED |
| Fresh-process determinism; reconciliation; hashes unchanged | SUPPORTED |
| T=7, 90/196, 5 buckets sum 90, 0 unexplained | SUPPORTED (counts); attribution SUPPORTED_WITH_CAVEAT (tie bucket mixed direction; M-gated bucket mechanism wrong; parity not met) |
| `EXISTING_CONTRACT_COMPILATION_INSUFFICIENT` (tested §4.2.1 only) | SUPPORTED |
| `NEW_CONTRACT_FIELD_REQUIRED` not established | SUPPORTED |
| Full 200/2000 randomized/interleaved protocol | OVERSTATED (not interleaved) |
| Wall p95 / growth / allocation within thresholds | SUPPORTED |
| CPU `UNMEASURED` | Honest disclosure, but criterion 13 unmet: `CPU_REMEASUREMENT_REQUIRED` |
| Failure-class taxonomy | Minor defect: `UNTRUSTWORTHY_ORDER_BIND` can never be emitted, because the bound id is always inside the expected set. All 48 Case-B member binds are labelled `INCORRECT_CONFIDENT_BINDING`. Pass/fail is unaffected. |

---

## 10. Verdict and required repairs

**`REPAIR_REQUIRED`.** The core causal result reproduces exactly: one qualifying cell, determinism, hashes, the transport conclusion scoped to the tested algorithm, and the wall-time and allocation thresholds. The following are still required before acceptance.

**Implementation-conformance repair (mechanism; needs a separately authorized implementer, then a rerun):**

- **IR-1.** Make the A9-2 trigger match the frozen text: gate the Level-5.5 membership restriction on `is_attachment` in the candidate pool, not in the H3 lexical pool (`rar_attachment_order_experimental.py:444`). Remove the extra `"earlier" in ref_tokens` match, or freeze it through a plan amendment. The scratchpad counterfactual predicts 0 factorial decision changes and a corrected `NB-C-04` C2 D1RQ row. Only the rerun can establish that.
- *Alternative:* keep the code and amend the plan (A10) to freeze the H3-gated trigger. The `NB-C-04` C2 wrong-domain row then becomes a disclosed limitation of the frozen mechanism.

**Evidence and reporting repairs (script and report; no mechanism change):**

- **ER-1.** Rewrite the D/M attribution: necessity only via A9-2, and the Level-5 ordinal restriction redundant in the qualifying cell.
- **ER-2.** Rewrite the G caveat (gate-induced; content never decision-relevant in the frozen fixtures; G's event map acts as membership) and the P caveat (effect only through R).
- **ER-3.** Replace the "5-way" wording with the §4 text above. Correct the `MxG` example. Report `{M,D}` and `{G,P}` as interacting pairs on the qualifying background.
- **ER-4.** Score the D1RQ/natural surface for correctness against `expected_by_reference`. Correct the "8 changed rows" statement. Disclose the `NB-C-04` C2 outcome (or its post-IR-1 result).
- **ER-5.** Transport:
  - split `COMPILER_NO_TIE_ABSTENTION_REPRESENTATION` by correctness direction and rename it as an algorithm step-4 limitation (ties are representable in `recency_rank`);
  - correct the `COMPILER_M_GATED_NO_GPR_FALLBACK` mechanism description;
  - disclose that §16.3 item 4 parity was not met and conflicts with the unamended §4.2.1, and report the parity-honoring arm or the 4-row discrepancy.
- **ER-6.** Performance: implement genuine cross-cell/pool interleaving, and remeasure CPU with the batched method in §8. Record the empirically measured timer step.
- **ER-7.** Report the raw-baseline equivalence measurement required by A9-4. State that the A2.5 modules were not run under cell flags, or run an equivalent surface.
- **ER-8.** Fix the `UNTRUSTWORTHY_ORDER_BIND` classification reachability, or disclose it.
- **ER-9.** Correct overlay manifest §5 ("no mechanism code exists"), which requires an amendment commit.

**Unverifiable items:**

- Byte-level preservation of the untracked pre-A9 artifacts cannot be proven by a recorded hash. Modification times and decision identity support it. This does not affect the verdict.
- Performance numbers are host-specific.

No acceptance, closure, commit, or push was performed by this audit.
