# M35 URIv1 — A2.8L-A9: Frozen Rerun Execution Report

**Status:** `VERIFICATION_READY`
**Date:** 2026-09-24
**Branch:** `m35-uri-v1-parallel-architecture`
**Frozen checkpoint governing this rerun:** `591f806` (A9 plan/manifest amendment)
**Governing documents:** `docs/plans/M35_URIV1_A2_8L_RAR_EVIDENCE_TRANSPORT_FACTORIAL_PLAN.md` §16, `docs/plans/M35_URIV1_A2_8L_OVERLAY_MANIFEST.md`
**Role note:** implemented directly by Claude Code, one-off exception explicitly re-authorized by the User for this rerun (live session, 2026-09-24), same basis as the first A2.8L run recorded in `docs/plans/M35_URIV1_A2_8L_STATE.md`.

---

## A2.8L-A9 Status

`VERIFICATION_READY`. No mechanism code was changed by this rerun (verified
by hash, see below); no factorial fixture, corpus, or S-D fixture was
changed; no RAR contract field was added; no promotion, acceptance,
closure, commit, or push has occurred.

---

## Pre-rerun conformance check (not implementation)

Before writing any new code, the mechanism module
(`uri_v1/turn/rar_attachment_order_experimental.py`) and fixture module
(`uri_v1/turn/rar_attachment_order_factorial_fixtures.py`) were inspected
against the A9-frozen plan text (§16.1). Both already implement A9-1
through A9-5 byte-for-byte — their own module docstrings disclosed the
same five behaviors A9 later froze, because the first run's implementation
is what the audit examined to derive A9 in the first place. **No mechanism
code edit was required or made.** This rerun is therefore a genuine
protocol-corrected re-execution of the unchanged A9-conformant mechanism,
not a reimplementation:

- **A9-1** (`C-LEXICAL-ATTACHMENT` gate exclusion): `compute_qualifying_cells` in the new rerun script reuses the pre-A9 script's own `reachable_by_factors`-gated logic unchanged.
- **A9-2** (D/M → Level 5.5): `_attachment_domain_trigger` / `l5_5_pool` restriction in the mechanism module, unchanged.
- **A9-3** (`"earlier"` A3 hint): `_ordinal_literal_present` already matches `recency_hint == "earlier"` directly (not only via token fallback), unchanged.
- **A9-4** (H3 always-on substrate): `l5_pool_lexical = _h3_domain(...)`, computed unconditionally, unchanged.
- **A9-5** (R domain-wide tie): `_domain_wide_tie_rank_map`, unchanged.

---

## New rerun script

`scripts/m35_a2_8l_a9_rerun.py` (new file). Reuses the unmodified mechanism
and fixture modules by import. Supersedes, for the protocol items listed
below, the pre-A9 script `scripts/m35_a2_8l_rar_attachment_order_factorial.py`
(left on disk unmodified as the pre-A9 historical record, together with its
own telemetry/aggregates/execution-report/state files, none of which this
rerun touches or overwrites).

---

## Factorial Result

### Two independent fresh-process runs (rerun protocol item 1)

Each causal-matrix run was executed as a **separate OS process**
(`subprocess.run([sys.executable, __file__, "--causal-only", <path>], ...)`),
not two repeats inside one process invocation as the pre-A9 script did.
Both processes independently recomputed the mechanism/fixture source
hashes; both matched. Determinism across the two fresh processes:
**passed**.

| Metric | Value |
|---|---|
| Run 1 causal rows | 1,792 |
| Run 2 causal rows | 1,792 |
| Fresh-process determinism | `True` |
| Source hashes identical across processes | `True` |

Repeat reconciliation (independent re-scan of run 1's own in-process
repeats against the 64×14 key space): **reconciled**, no
missing/duplicate keys.

### Qualifying cells

**1 of 64** — `M=1,G=1,P=1,D=1,R=1,Q=0`, also the only minimal sufficient
set. This is numerically the same cell the pre-A9 (undisclosed-extension)
run reported — **not assumed in advance** (A9 §16.2 item 2 explicitly
forbids that assumption); it is what this rerun's independent
re-computation, under the now-frozen A9 semantics, actually found.

### Necessary factors

`M, G, P, D, R` — each ON in the sole qualifying cell; ablating any one
individually breaks a frozen target (same underlying mechanism as the
pre-A9 run; re-verified directly by this rerun's own raw rows, not
inherited).

**Per A9 §16.4 rules 1–3 (HG/HD not presumed supported; necessity
attributed to the Level-5.5 extension where applicable):**

- **D and M's necessity is attributable, in part, to the A9-2 Level-5.5
  extension, not only to the Level-5 ordinal-domain mechanism.** Ablating
  D or M breaks `B-DISTRACTOR` and `C-NATURAL-PHOTOS` C2 — both non-ordinal
  attachment targets reachable *only* through A9-2's Level-5.5
  membership-restriction extension (§16.1 A9-2), not through Level 5's
  ordinal domain restriction at all (A3 never fires for either target).
  This rerun's necessity finding for D/M is therefore split: D/M are
  necessary for the ordinal Case-A/B targets *via the Level-5 mechanism*,
  and separately necessary for `B-DISTRACTOR`/`C-NATURAL-PHOTOS` C2 *via
  the A9-2 Level-5.5 extension* — a bare "D is necessary" label without
  this split would violate A9 §16.4 rule 3.
- **G's necessity finding carries the §16.5-1 coupling caveat.** G is ON
  in the sole qualifying cell and ablating it breaks the ordinal Case-A
  targets. Per A9 §16.4 rule 1 (HG not presumed supported) and §16.5 item 1
  (G/M correlation): this rerun's case set does not include a row where G
  is ablated but M's own membership data is independently still visible to
  the resolver through a *different* channel, so G's necessity here cannot
  be cleanly separated from M's own contribution using this case set alone
  — reported per the disclosed coupling (§16.5-1), not as an
  independent-factor finding.
- **R's necessity finding carries the §16.5-2 coupling caveat.** Every
  frozen case that exercises R also supplies overlay data (§16.5 item 2);
  this rerun's case set cannot distinguish "R activates because G+P
  authorized it" from "R activates because overlay data is merely
  present" — reported as an open, case-set-level limitation, not resolved
  by this rerun (no mechanism-code change was authorized to resolve it).
- **P's necessity is clean** (not implicated in either §16.5 coupling):
  ablating P breaks the ordinal Case-A targets via the authorization gate
  exactly as A1/A2 specify, independent of the G/M or R/overlay couplings.

### Interaction tables

**All-off background** (pre-A9 probe, retained): no pairwise-interacting
pair detected — qualification requires the full 5-way `{M,G,P,D,R}`
simultaneously, undetectable by any 2×2 table with the remaining three
factors off. Unchanged finding from the pre-A9 run.

**Qualifying-cell background** (A9 §16.3 item 3, new): case-level 2×2
tables were computed with all factors *other than* the pair under test
held at the qualifying cell's own values (not all-off), for every pair and
every one of the 14 cases, recorded in
`M35_URIV1_A2_8L_A9_AGGREGATES.json` →
`pairwise_interactions_qualifying_cell_background`. This background makes
each factor's marginal effect on each specific case visible against the
otherwise-satisfied background — for example, `MxG` on `B-DISTRACTOR`
shows the case passing only when both M and G/D are at their qualifying
values, confirming the joint requirement is genuine per-case, not an
artifact of the all-off probe's inability to see it. No case exposed
a genuine two-factor sufficient repair independent of the other three
necessary factors; the exact 5-way minimal-sufficient-set result (§7)
remains the authoritative necessity finding, as it was in the pre-A9 run.

---

## Mandatory Surface Validation

### D1RQ + natural rows (rerun protocol item 4)

`NB-C-04`, `NB-C-05`, `NB-D-01`, `NB-D-02`, at C1/C2, D1RQ-detected
span/hint, both production-shaped (`oracle_recency=False`) and
created_at-oracle (`oracle_recency=True`) ranks, run under **baseline
(all-off) and every A9-amended qualifying cell plus its one-factor
ablations** (7 cells total, matching the transport comparison's own cell
set) — not a single "best cell" as the pre-A9 script's confirmation
surface did.

| Metric | Value |
|---|---|
| Total rows | 112 |
| `NB-D-02` unauthorized new-bind count | **0** |
| Silent-detection misses / boundary violations | 0 |
| Rows changed from baseline | 8 (all `NB-C-04`/`NB-C-05`, expected — same membership-restriction mechanism as their factorial-case counterparts) |
| Rows unchanged from baseline | 104 |

`NB-D-02` (the relative-anchor capability-gap control) produced **zero**
unauthorized new confident bindings under any candidate cell — the only
permitted non-baseline change (safe abstention) was not exercised either;
`NB-D-02`'s decision is identical across all 7 cells, consistent with the
plan's own framing that no cell may claim to solve it.

### A2.5 modules

Full existing A2.5/A2.8K regression suite — `test_m35_uriv1_a2_5_deterministic_rar.py`,
`test_m35_uriv1_a2_5_rar_adversarial_safety.py`,
`test_m35_uriv1_a2_5_rar_contracts.py`,
`test_m35_uriv1_a2_5_rar_stage4_refinements.py`,
`tests/test_m35_uriv1_a2_8k_l5_experimental.py`,
`tests/test_m35_uriv1_a2_8k_r1_repair.py`, plus
`tests/test_m35_uriv1_a2_8l_rar_attachment_order_factorial.py`: **114
tests / 178 subtests, all passing, unchanged** — these test files were not
touched by this rerun.

### S-D battery (confirmation surface, extended to both baseline and
qualifying cell)

| Cell | Unexpected mismatches |
|---|---|
| `M0G0P0D0R0Q0` (all-off) | 0 |
| `M1G1P1D1R1Q0` (qualifying cell) | 0 |

(`SD-A-04/05/06/07` are excluded from "unexpected" scoring — they are
A2.8L's own reused causal targets and are expected to change under the
qualifying cell, per the same rule the pre-A9 script used.)

---

## Transport Result

Unchanged §4.2.1 compiler algorithm (no mechanism-code change authorized).
`T = 7` (baseline + the sole minimal-sufficient cell + its 5 one-factor
ablations), 196 rows (2 repeats each), determinism held.

**Conclusion: `EXISTING_CONTRACT_COMPILATION_INSUFFICIENT`** — scoped, per
A9 §16.4 rule 4, exactly to this frozen §4.2.1 algorithm as executed; not a
general claim about existing-contract compilation.

**90 of 196 rows mismatch. Every mismatch is now attributed to one of five
explicit causes (A9 §16.3 item 4) — none left as an unattributed
aggregate footnote:**

| Attribution bucket | Count | Cause |
|---|---|---|
| `H3_ABSENCE_CONFOUND` | 28 | Compiler's step 6 calls raw baseline (no H3); non-attachment domain-rank controls (`C-DOMAIN-RANK-SYNTH`, `C-DOMAIN-RANK-NATURAL`) always mismatch, independent of M/G/P/D/R/Q. |
| `COMPILER_NO_TIE_ABSTENTION_REPRESENTATION` | 42 | Sidecar safely abstains (`AMBIGUOUS`) via R's A9-5 domain-wide tie; compiler's step 4 is a binary choice (project trusted rank / leave original rank) with no tie representation, so it always falls through to a confident `RESOLVE` on the un-tied original ranks. |
| `D_M_LEVEL_5_5_EXTENSION_NOT_COMPILED` | 16 | Compiler's step-1 ordinal-trigger check has no analogue for A9-2's Level-5.5 extension; non-ordinal attachment cases (`B-DISTRACTOR`, `C-NATURAL-PHOTOS` C1/C2) always fall through to an unprojected baseline call. |
| `COMPILER_M_GATED_NO_GPR_FALLBACK` | 2 | Compiler's step 2 skips ALL projection whenever M is off; sidecar can still resolve correctly without M via H3's own domain-relative rank fallback using G/P/R's event evidence directly — a compiler capability gap, not an M-attributable disagreement. |
| `COMPILER_RANK_NOT_DENSIFIED_WITHOUT_R` | 2 | Compiler's step 4 only densifies rank when R is explicitly on; sidecar's H3 fallback densifies unconditionally once the domain is genuinely narrowed by M/D. When R is ablated, the compiler's M-projected-but-unranked subset can lack a rank-0 member and falls through to `AMBIGUOUS` where the sidecar resolves. |
| **Total** | **90** | — |

**A new RAR contract field is not established as necessary** —
`NEW_CONTRACT_FIELD_REQUIRED` was never produced by this rerun, per A9
§16.4 rule 5 (unchanged prohibition).

---

## Performance

**Full pre-registered protocol** (200 warmups / 2,000 randomized/interleaved
measured iterations per cell, fixed seed `20260924`, disclosed and
recorded) — superseding the pre-A9 script's disclosed 20/200 reduction.
All-off baseline vs. the qualifying cell (`M1G1P1D1R1Q0`):

| Pool | Cell | Mean wall (ms) | p95 wall (ms) | Peak alloc (bytes) |
|---|---|---|---|---|
| 2 | all-off | 0.0213 | 0.0279 | 3,956 |
| 2 | winning | 0.0252 | 0.0257 | 4,020 |
| 8 | all-off | 0.0423 | 0.0538 | 5,682 |
| 8 | winning | 0.0393 | 0.0412 | 5,050 |
| 32 | all-off | 0.0971 | 0.1228 | 12,956 |
| 32 | winning | 0.0880 | 0.0920 | 9,572 |
| 128 | all-off | 0.3189 | 0.3904 | 44,446 |
| 128 | winning | 0.2795 | 0.2849 | 29,926 |

**Environment/source metadata (rerun protocol item 8):** Windows, Python
3.13.15, CPU `AMD64 Family 25 Model 33 Stepping 2, AuthenticAMD`, 64-bit
process. `perf_counter` nominal resolution `1e-7 s`; `process_time` nominal
resolution `1e-7 s` (see CPU-timing limitation below). Source hashes for
both mechanism/fixture files and all 8 protected files recorded per
fresh-process run in `M35_URIV1_A2_8L_A9_TELEMETRY.json` →
`fresh_process_report`.

**Threshold checks (final, not provisional — full-iteration protocol):**

| Check | Result |
|---|---|
| p95 wall overhead, pool ≤32 | `True` (within `max(0.25ms, 2×baseline)`) for pools 2, 8, 32 |
| pool 32→128 growth ratio | `True` (≈3.2×, ≤6× bound) |
| peak allocation at pool 128 | `True` (29,926 bytes, < 256 KiB) |
| median CPU-time overhead | **`UNMEASURED`** — see below |

**CPU-timing resolution limitation (disclosed, not silently passed):**
`time.process_time_ns()`'s *reported* nominal resolution (1e-7 s) is finer
than its *actual* Windows measurement granularity for calls in the
sub-millisecond range this mechanism runs in; every single-call CPU-time
sample in this run read `0`, making `median_cpu_ms` uninformative (`0.0`
for both baseline and winning cell at every pool size) and the CPU-overhead
threshold check **not evaluable** from this data. This is a genuine
measurement-instrument limitation on this OS/host, not a claim that CPU
overhead is zero or unbounded. Per the task brief's instruction, this is
recorded as `UNMEASURED`, not silently passed or silently dropped. Wall-time
and allocation thresholds (both measured with adequate resolution for this
workload) are unaffected and are final.

---

## Verification

| Item | Result |
|---|---|
| Causal row count | 1,792 (64×14×2), exact |
| Fresh-process determinism | `True` (two separate OS processes) |
| Repeat reconciliation | `True`, zero missing/duplicate keys |
| A2.5/A2.8K/A2.8L regression suite | 114 tests / 178 subtests, all passing, unchanged |
| S-D confirmation (baseline + qualifying cell) | 0 unexpected mismatches at either |
| D1RQ/natural confirmation (7 cells) | 112 rows, 0 `NB-D-02` violations |
| Protected-file (§13.2) hashes | unchanged, pre/post |
| Mechanism/fixture file hashes | unchanged, pre/post, and identical across both fresh processes |

---

## Limitations / Confounds

- **G↔M coupling (§16.5 item 1, unresolved by this rerun):** the frozen
  case set never exercises G ablated with M's own membership data still
  independently visible through a different channel, so G's necessity
  finding above is reported with this caveat, not as a clean
  independent-factor result. No mechanism-code change was authorized to
  add a case that could separate this.
- **R↔overlay-presence coupling (§16.5 item 2, unresolved by this rerun):**
  every frozen case that exercises R also supplies overlay data; this
  rerun's case set cannot distinguish R activating on the frozen G+P gate
  from R activating merely because overlay data exists. Reported as an
  open case-set-level limitation.
- **CPU-timing resolution (this rerun, new disclosure):** see Performance
  section above — `UNMEASURED`, not zero.
- **A5/A7 (plan's own, carried forward unchanged):** every Case-A target
  is authored-only (no natural-corpus Case-A external validity); every
  ordinal case is capped at two current-turn members (untested by design
  for 3+).
- **Transport conclusion scope (A9 §16.4 rule 4):** `EXISTING_CONTRACT_
  COMPILATION_INSUFFICIENT` applies only to the exact §4.2.1 algorithm as
  executed; not a general claim.
- **Original pre-A9 literal-plan result, preserved separately (A9 §16.2
  item 1):** under the plan's literal A1–A8 text alone (no A9 extensions),
  0 cells qualify. This rerun's 1-qualifying-cell result is the
  A9-amended finding and does not supersede or reproduce that literal
  reading; both are true statements about different frozen texts.

---

## Evidence Produced

- `scripts/m35_a2_8l_a9_rerun.py` (new)
- `docs/plans/M35_URIV1_A2_8L_A9_TELEMETRY.json` (new; raw causal rows,
  fresh-process report, transport rows with per-mismatch attribution,
  S-D/natural confirmation rows, full performance data)
- `docs/plans/M35_URIV1_A2_8L_A9_AGGREGATES.json` (new)
- `docs/plans/M35_URIV1_A2_8L_A9_RUN1_CAUSAL.json`,
  `_A9_RUN2_CAUSAL.json` (new; the two fresh-process subprocess outputs,
  retained on disk as the fresh-process determinism evidence)
- `docs/plans/M35_URIV1_A2_8L_A9_STATE.md` (new)
- This report.
- **Untouched, preserved byte-for-byte:** `scripts/m35_a2_8l_rar_attachment_order_factorial.py`,
  `M35_URIV1_A2_8L_TELEMETRY.json`, `_AGGREGATES.json`,
  `_EXECUTION_REPORT.md`, `_STATE.md` (the pre-A9 run's own evidence), and
  all 8 protected files (§13.2) plus the mechanism/fixture modules
  themselves (hash-verified unchanged).

---

## Independent Audit Handoff

The auditor should independently verify, at minimum:

1. Recompute the 8 protected-file hashes and the mechanism/fixture-file
   hashes against the current working tree; confirm they match
   `M35_URIV1_A2_8L_A9_TELEMETRY.json`'s recorded pre/post values, and that
   both fresh-process subprocess runs recorded identical hashes
   independently (`fresh_process_report`).
2. Re-run `python scripts/m35_a2_8l_a9_rerun.py` and confirm byte-identical
   `causal_row_count`, `fresh_process_determinism_passed`,
   `qualifying_analysis`, and `transport_comparison.conclusion` to this
   report (the performance pass will vary numerically run-to-run but
   threshold pass/fail should be stable; `UNMEASURED` CPU status should
   reproduce given the same OS).
3. Independently assess whether the necessity findings for D/M
   (Level-5.5-extension attribution split, "Necessary factors" section
   above) and for G/R (coupling caveats) are faithfully and completely
   disclosed, not merely gestured at.
4. Spot-check a sample of the 90 transport mismatches against the five
   attribution buckets above — confirm each bucket's stated mechanism
   actually explains the sampled rows, not only the aggregate count.
5. Independently assess whether the `COMPILER_NO_TIE_ABSTENTION_
   REPRESENTATION` and `COMPILER_RANK_NOT_DENSIFIED_WITHOUT_R` buckets
   (both new in this rerun, not present in the pre-A9 execution report's
   narrative) are genuinely distinct failure modes or should be merged —
   this report treats them as distinct because they trigger under
   different cell conditions (R=1-but-P/G-insufficient vs. R=0 outright).
6. Confirm the `NB-D-02` zero-violation claim against the raw 112
   `natural_confirmation` rows in the telemetry file, not only the
   aggregate count.
7. Assess whether the CPU-timing `UNMEASURED` disclosure is an acceptable
   resolution of rerun protocol item 6, or whether a different timing
   mechanism (e.g., higher-iteration-count batched CPU sampling) should be
   required before performance acceptance.

No promotion, acceptance, closure, commit, or push has occurred. No new
experiment has been started.

**STOP — INDEPENDENT AUDIT REQUIRED BEFORE ACCEPTANCE OR NEXT EXPERIMENT.**
