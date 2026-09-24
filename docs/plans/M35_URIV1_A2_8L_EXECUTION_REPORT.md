# M35 URIv1 — A2.8L: RAR Attachment-Order Evidence Transport Factorial — Execution Report

**Status:** `VERIFICATION_READY`
**Date:** 2026-09-24
**Branch:** `m35-uri-v1-parallel-architecture`
**Frozen checkpoint:** `804d68e`
**Governing documents:** `docs/plans/M35_URIV1_A2_8L_RAR_EVIDENCE_TRANSPORT_FACTORIAL_PLAN.md`, `docs/plans/M35_URIV1_A2_8L_OVERLAY_MANIFEST.md`

---

## A2.8L Status

`VERIFICATION_READY`. The experiment ran to completion with two disclosed
interpretive extensions and one disclosed unreachable control (all described
below and confirmed with the User before implementation proceeded). No
implementation, promotion, contract change, commit, or push has occurred.

---

## Freeze-checkpoint verification (A8, plan §5.4)

Before any mechanism code was written, all ten SHA-256 hashes recorded in
the overlay manifest §3 were independently recomputed against the working
tree and matched exactly:

`rar_contracts.py`, `rar_deterministic.py`, `rar_safe_experimental.py`,
`rar_l5_experimental.py`, `rar_l5_diagnostic_fixtures.py`,
`m35_a2_8h_detector_d1rq.py`, `m35_a2_8k_l5_battery.py`,
`rar_natural_boundary_raw_turn_fixtures.json`,
`M35_URIV1_A2_8K_R2_TELEMETRY.json`, `M35_URIV1_A2_8K_R2_AGGREGATES.json`.

Pre-run and post-run hashes of all eight protected files (plan §13.2) are
also equal (`protected_hashes_unchanged: true` in the telemetry file) —
nothing in the accepted A2.5/A2.8K/A2.8J/A2.9 surface was modified.

---

## Implementation

### Files created

1. `uri_v1/turn/rar_attachment_order_experimental.py` — the six-factor
   M/G/P/D/R/Q cascade (SIDE-CAR arm) plus the frozen 8-step
   EXISTING-CONTRACT COMPILER (§4.2.1).
2. `uri_v1/turn/rar_attachment_order_factorial_fixtures.py` — the 13
   case-template / 14-decision-row fixture set transcribed from the overlay
   manifest.
3. `scripts/m35_a2_8l_rar_attachment_order_factorial.py` — the battery
   driver (causal matrix, minimal-sufficient-set/interaction derivation,
   transport comparison, confirmation surfaces, performance pass).
4. `tests/test_m35_uriv1_a2_8l_rar_attachment_order_factorial.py` — 10 test
   methods / 64 subtests covering flag-off equivalence, all seven causal
   targets, factor necessity, compiler invariants, the provenance minimal
   pair, and determinism.
5. `docs/plans/M35_URIV1_A2_8L_TELEMETRY.json`, `_AGGREGATES.json` (this
   run's raw and derived evidence).

No protected file (§13.2) was touched. No RAR contract field was added.
`RARCandidate`, `RAREvidence`, `RARDeterministicAnchor`, `RARQuery`,
`RARResolution` are unchanged.

### Mechanisms implemented

- **M** — `AttachmentOrderOverlay.turn_membership_ids`, consumed exclusively
  by D (and, per the disclosed extension below, by the Level‑5.5
  generic-attachment counting path).
- **G** — `event_group_by_id` / `group_ordinal_by_event`, consumed by R's
  order-derivation gate (independent of P, per A1).
- **P** — `provenance` (`CURRENT_TURN_ATTACHMENT_SEQUENCE` /
  `HISTORICAL_OBJECT_CREATED_AT` / `UNKNOWN`), consumed by R's authorization
  gate (independent of G, per A1). When the gate fails, G's derived order is
  discarded (A2) and the *entire* transported-membership domain ties at rank
  0 — see "Interpretive notes" below for why a domain-wide tie (not a
  same-event-only tie) is required to make `B-LATEST-PROVENANCE-TWIN`
  abstain.
- **D** — restricts Level 5's ordinal domain (and, per the disclosed
  extension, Level 5.5's generic-attachment domain) to transported
  membership, layered on top of the accepted A2.8K H3 lexical-compatibility
  substrate, which is reused unconditionally (not gated by any A2.8L flag).
- **R** — derives dense domain-relative rank from transported event
  ordinals only when G+P jointly authorize it; otherwise ties the whole
  D-restricted domain (safe non-bind) rather than trusting the untrusted
  global rank.
- **Q** — reimplements A2.8K's H2 (unconditional Level‑5.5-before‑Level‑5
  precedence) byte-equivalent in intent, as an independent toggle.
- **EXISTING-CONTRACT COMPILER** — implements the frozen 8-step algorithm
  (§4.2.1) exactly: ordinal-trigger match → membership projection → optional
  rank projection when R+P authorize it → call the unchanged
  `resolve_rar_deterministic_extended` → validate the result is a subset of
  the original candidate universe (raises `ValueError` classified as
  `CONTRACT_VIOLATION_OR_CANDIDATE_INVENTION` otherwise, never observed in
  this run).

---

## Interpretive notes and disclosed limitations (Verification-First disclosure)

Three points required interpretation beyond the plan's literal text. Each
was necessary to make the plan's own §5.1/§5.2 targets achievable at all
under the six-factor constraint; none changes a frozen semantic definition,
and the first was explicitly confirmed with the User before proceeding.

1. **A3 ordinal-trigger literal.** §4.1's A3 names
   `recency_hint in {"latest","first"}`, but the frozen `A-FIRST-2` target
   reuses `SD-A-06` verbatim, whose `recency_hint` is `"earlier"` (its
   reference text is "the first attachment"). This module matches the
   hint **or** a literal "latest"/"first" token in the reference expression
   — reusing baseline's own established `hint == X or X in ref_tokens`
   convention, adding no new detection logic — so both `SD-A-04` and
   `SD-A-06` satisfy A3 as the plan's own table requires.

2. **H3 as an always-on substrate.** The plan requires "domain-relative
   ranking must retain the accepted A2.8K activation boundary" and includes
   non-attachment controls (`C-DOMAIN-RANK-SYNTH`, `C-DOMAIN-RANK-NATURAL`)
   that only A2.8K's H3 lexical-compatibility mechanism can resolve (raw
   baseline alone resolves both incorrectly — verified directly). A2.8L's
   resolver therefore reuses H3 (`rar_l5_experimental._h3_domain` /
   `_domain_relative_ranks`, imported unmodified) unconditionally as its
   substrate; M/G/P/D/R/Q are an additional layer on top, active only for
   the attachment-specific trigger. Flag-off equivalence was verified
   against `resolve_rar_l5_experimental(h3=True)`, not raw baseline
   (0 mismatches across all 18 S-D fixtures); this is the correct reference
   given the controls' own requirements, not raw
   `resolve_rar_deterministic_extended` (3 mismatches against raw baseline,
   all of them H3 fixing a pre-existing baseline defect, not an A2.8L
   regression).

3. **D/M extended to Level 5.5 (disclosed structural gap, confirmed with
   User 2026-09-24).** `C-LEXICAL-ATTACHMENT` (`SD-A-08`) is unreachable by
   any of the six factors: Level 5.5's `is_attachment` counting has no
   lexical consumer in M/G/P/D/R/Q as literally scoped, and both raw
   baseline and the accepted H3 mechanism return `AMBIGUOUS` for it in
   every configuration. Per explicit User direction, this control is
   **excluded from the "passes every control" qualification gate** but
   still run and reported in every cell (see `reachable_by_factors: false`
   in the fixtures and telemetry). Separately, `B-DISTRACTOR` — a §5.1
   **causal target**, not a control — has the same structural problem: its
   reference ("the attached file") carries no ordinal wording, so A3 never
   fires, yet its frozen outcome requires membership to exclude a
   non-turn distractor from Level 5.5's counting. This was resolved by
   applying the **same** D/M mechanism (membership restriction) to Level
   5.5's attachment-identity counting whenever attachment semantics are
   explicit, not only to Level 5's ordinal branches — the same two named
   factors, applied at the sibling level, not a seventh mechanism. This is
   disclosed in the module docstring and is necessary for the plan's own
   causal target to be achievable by any cell.

**A5/A7 scope limits carried forward from the plan itself:** every Case-A
target is authored-only (no natural-corpus external validity for Case-A
specifically); every ordinal case has at most two current-turn members
(3+-member generalization is untested by design).

**Newly observed confound:** the transport comparison's
EXISTING-CONTRACT-COMPILER arm calls the raw, unmodified
`resolve_rar_deterministic_extended` per the frozen algorithm's step 6 —
which does not include H3. This produces a mismatch on
`C-DOMAIN-RANK-SYNTH`/`C-DOMAIN-RANK-NATURAL` in **every** cell, including
the all-off baseline, that is attributable to H3's absence from the
compiled path, not to any of the six A2.8L factors. This is reported
separately from the factor-attributable mismatches below and should not be
read as evidence about M/G/P/D/R/Q transport sufficiency.

---

## Factorial Results

64 cells × 14 rows × 2 repeats = **1,792 causal decision rows**, exactly as
frozen. Determinism check (2 full battery runs): **passed** — every row's
`(outcome, candidate_id, ambiguous_candidate_ids)` tuple is identical across
runs. Repeat reconciliation (independent re-scan of raw rows against the
64×14 key space): **reconciled**, no missing/duplicate keys.

**Qualifying cells: 1 of 64** — `M=1,G=1,P=1,D=1,R=1,Q=0`.

This is also the only minimal sufficient set (no strict subset of its five
ON factors qualifies).

### Necessary factors

`M`, `G`, `P`, `D`, `R` — each is ON in the (only) qualifying cell, and
ablating any one of them individually breaks at least one frozen target
(verified directly, not inferred):

| Factor ablated | Targets broken |
|---|---|
| M | `B-DISTRACTOR`, `C-NATURAL-PHOTOS` C2 |
| G | `A-LATEST-2`, `A-FIRST-2`, `A-LATEST-DISTRACTOR` |
| P | `A-LATEST-2`, `A-FIRST-2`, `A-LATEST-DISTRACTOR` |
| D | `B-DISTRACTOR`, `C-NATURAL-PHOTOS` C2 |
| R | `B-LATEST-WRONG-CLOCK`, `B-FIRST-WRONG-CLOCK`, `B-LATEST-PROVENANCE-TWIN` |

Note that **G is necessary for both Case-A and Case-B**: without it, R has
no ordering evidence at all, so a genuinely trustworthy order (Case A) is
lost exactly as a genuinely untrustworthy one would be — this matches HG's
scope more broadly than its own text implies (HG as written only claims
necessity for Case-B abstention).

### Q (destructive interaction, confirmatory — matches HQ)

Toggling `Q` ON from the winning cell (`M1G1P1D1R1Q1`) breaks `A-LATEST-2`,
`A-FIRST-2`, and `A-LATEST-DISTRACTOR`: unconditional Level‑5.5-before‑Level‑5
precedence intercepts the query before the correct order can be applied,
exactly as A2.8K's H2 finding predicted (HQ). `Q` must be OFF; it is neither
necessary nor sufficient, and interacts destructively with valid Case-A
order.

### Sufficiency

No single factor is individually sufficient (`single_factor_sufficient: []`).
Only the full five-factor set `{M,G,P,D,R}` qualifies.

### Pairwise interactions

The simple 2×2 check (all other factors held OFF) found **no pairwise
interacting pair**, because qualification in this experiment genuinely
requires all five of M/G/P/D/R simultaneously — a joint five-way
requirement, not decomposable into any 2×2 table with the remaining factors
off. This is a disclosed limitation of the simple pairwise probe, not a
claim that no lower-order interaction exists; the minimal-sufficient-set
result (§7's stronger, exact criterion) is the authoritative finding here.

---

## Transport Comparison

`T = 7` (1 baseline + the single minimal sufficient cell + its 5 one-factor
ablations), well under the `T ≤ 16` cap. 196 rows run (56 × 7), two repeats
each, determinism held.

**Conclusion: `EXISTING_CONTRACT_COMPILATION_INSUFFICIENT`.**

90 of 196 rows mismatch between the SIDE-CAR and EXISTING-CONTRACT-COMPILER
arms. Excluding the H3-absence confound noted above (which appears
identically in every cell and is not attributable to M/G/P/D/R/Q), the
factor-attributable mismatches show:

- The compiler's frozen algorithm only recognizes the A3 ordinal trigger
  (`recency_hint`/token "latest"/"first" + `is_attachment`); it has no
  analogue for the disclosed Level‑5.5 membership extension, so
  `B-DISTRACTOR` and `C-NATURAL-PHOTOS` C2 (both non-ordinal) always fall
  through to an unmodified baseline call in the compiler arm, reproducing
  the 3-way (uncorrected) ambiguity instead of the sidecar's correct
  2-way membership-restricted ambiguity.
- When R is ablated from the minimal cell, the compiler (which only
  re-projects rank when R is explicitly on) leaves the projected
  candidates' original global ranks un-densified, so `A-LATEST-DISTRACTOR`
  falls through to `AMBIGUOUS` in the compiler arm where the sidecar
  correctly resolves it via H3's own domain-relative dense-rank fallback.
- Every Case-B row (`B-LATEST-WRONG-CLOCK`, `B-FIRST-WRONG-CLOCK`,
  `B-LATEST-PROVENANCE-TWIN`) confidently RESOLVES in the compiler arm
  wherever M is transported but the full G+P+R chain is not (the compiler
  has no domain-wide-tie safe-abstention mechanism at all — it either
  re-projects a trusted rank or leaves the original one, with nothing in
  between).

**A new RAR contract field is not established as necessary** — no result
here is labelled `NEW_CONTRACT_FIELD_REQUIRED`, per the plan's explicit
prohibition. The finding is scoped exactly as the plan allows:
`EXISTING_CONTRACT_COMPILATION_INSUFFICIENT` for the specific compiler
algorithm as frozen in §4.2.1, which was deliberately scoped to the
ordinal-only case and to a binary rank-projected/not-projected choice with
no tie-representation.

---

## Performance

Reduced-iteration pass (20 warmups / 200 measured iterations per cell —
disclosed reduction from the plan's pre-registered 200/2000, to fit this
session's wall-clock budget; see `PERFORMANCE_ITERATIONS_NOTE` in the
script). All-off baseline and the winning cell (`M1G1P1D1R1Q0`):

| Pool | Cell | Mean wall (ms) | p95 wall (ms) | Peak alloc (bytes) |
|---|---|---|---|---|
| 2 | all-off | 0.021 | 0.022 | 3,956 |
| 2 | winning | 0.025 | 0.025 | 4,020 |
| 8 | all-off | 0.040 | 0.041 | 5,682 |
| 8 | winning | 0.039 | 0.040 | 5,050 |
| 32 | all-off | 0.095 | 0.099 | 12,956 |
| 32 | winning | 0.089 | 0.090 | 9,572 |
| 128 | all-off | 0.314 | 0.319 | 44,446 |
| 128 | winning | 0.281 | 0.286 | 29,926 |

All provisional §10.2 thresholds are met with this reduced sample: p95
overhead at pool ≤32 is well under `max(0.25ms, 2×baseline)`; the winning
cell's pool 32→128 growth ratio is ≈3.2× (≤6× bound); peak allocation at
pool 128 (29,926 bytes) is far below the 256 KiB cap. **These results
should be treated as directional, not final** — a full 200-warmup/
2000-iteration rerun is recommended before any threshold claim is relied
upon, per the plan's own "provisional" framing of §10.2.

---

## Verification

- **Tests:** `tests/test_m35_uriv1_a2_8l_rar_attachment_order_factorial.py`
  — 10 tests / 64 subtests, all passing. Full existing A2.5/A2.8K regression
  suite (104 tests / 114 subtests: `test_m35_uriv1_a2_5_deterministic_rar.py`,
  `test_m35_uriv1_a2_5_rar_adversarial_safety.py`,
  `test_m35_uriv1_a2_5_rar_contracts.py`,
  `test_m35_uriv1_a2_5_rar_stage4_refinements.py`,
  `tests/test_m35_uriv1_a2_8k_l5_experimental.py`,
  `tests/test_m35_uriv1_a2_8k_r1_repair.py`) — all passing, unchanged.
- **Row counts:** 1,792 causal rows (64×14×2) confirmed by direct count and
  assertion in the script; no missing/duplicate cell×case key.
- **Determinism:** two independent full battery runs produce identical
  decision tuples for every row.
- **Reconciliation:** an independent re-scan of the raw rows against the
  full 64×14 key space confirms zero missing/duplicate keys and zero
  decision drift between repeats.
- **Integrity:** all 8 protected files' SHA-256 hashes are identical before
  and after the run (`protected_hashes_unchanged: true`); the 10 A8
  freeze-checkpoint hashes were independently reproduced and matched before
  any mechanism code was written.
- **Confirmation surfaces:** the full 18-case S-D battery, run under the
  winning cell, shows zero unexpected changes outside the four fixtures
  that are themselves reused A2.8L causal targets (`SD-A-04/05/06/07`,
  which change by design).

---

## Evidence Produced

- `uri_v1/turn/rar_attachment_order_experimental.py`
- `uri_v1/turn/rar_attachment_order_factorial_fixtures.py`
- `scripts/m35_a2_8l_rar_attachment_order_factorial.py`
- `tests/test_m35_uriv1_a2_8l_rar_attachment_order_factorial.py`
- `docs/plans/M35_URIV1_A2_8L_TELEMETRY.json`
- `docs/plans/M35_URIV1_A2_8L_AGGREGATES.json`
- `docs/plans/M35_URIV1_A2_8L_STATE.md`
- This report.

---

## Limitations

- **A5/A7 (plan's own, carried forward):** every Case-A target is
  authored-only (no natural-corpus Case-A external validity); every ordinal
  case is capped at two current-turn members (3+-member behavior is
  untested by design, not a validated boundary).
- **Disclosed interpretive extensions (this report, confirmed with User):**
  the A3 hint/token reading, H3-as-substrate, and the D/M-to-Level-5.5
  extension (items 1–3 above). Each is necessary for the plan's own targets
  to be achievable and is documented in the module docstring as well as
  here; none of them changes a frozen semantic definition, but all three
  are interpretive choices made during implementation, not literal
  transcriptions of the plan text.
- **C-LEXICAL-ATTACHMENT exclusion:** by explicit User direction, this
  control is excluded from the qualification gate. Its own row is still
  scored and reported (`AMBIGUOUS` in every cell, never the frozen
  `RESOLVED`) so the exclusion is auditable, not hidden.
- **Transport confound:** the compiler-arm's use of raw baseline (no H3)
  produces a mismatch on the two domain-rank controls in every cell,
  unrelated to M/G/P/D/R/Q. Disclosed above; excluded from the
  factor-attributable insufficiency narrative.
- **Performance sample size:** 20/200 instead of the pre-registered
  200/2000 (wall-clock budget). Directional only.
- **Pairwise-interaction probe:** the simple all-else-off 2×2 check cannot
  detect the genuine 5-way joint requirement this experiment found; the
  minimal-sufficient-set computation (exact, not sampled) is the
  authoritative necessity/sufficiency evidence.

---

## Independent Audit Handoff

The auditor should independently verify, at minimum:

1. Recompute the 10 A8 freeze-checkpoint hashes and the 8 protected-file
   pre/post hashes against the current working tree; confirm they match
   the values recorded in `docs/plans/M35_URIV1_A2_8L_TELEMETRY.json`.
2. Re-run `python scripts/m35_a2_8l_rar_attachment_order_factorial.py` and
   confirm byte-identical `causal_row_count`, `determinism_check_passed`,
   `qualifying_analysis`, and `transport_comparison.conclusion` to this
   report.
3. Re-run `python -m pytest tests/test_m35_uriv1_a2_8l_rar_attachment_order_factorial.py`
   and the six existing A2.5/A2.8K regression files listed above; confirm
   all pass with the exact same counts.
4. Independently assess whether the three disclosed interpretive
   extensions (A3 hint/token reading; H3-as-substrate; D/M extended to
   Level 5.5) are faithful to the plan's intent or constitute scope
   creep requiring the plan to be reopened — this is a judgment call this
   report discloses but does not itself have unilateral authority to
   validate.
5. Independently assess whether excluding `C-LEXICAL-ATTACHMENT` from the
   qualification gate (rather than reopening the plan to add a 7th
   mechanism, or accepting zero qualifying cells) was the correct
   resolution of that structural gap.
6. Spot-check a sample of the 90 transport mismatches in
   `docs/plans/M35_URIV1_A2_8L_TELEMETRY.json` → `transport_comparison.mismatches`
   against the "Transport Comparison" narrative above to confirm the
   H3-confound / factor-attributable split is accurately characterized.

**STOP — INDEPENDENT AUDIT REQUIRED BEFORE ACCEPTANCE OR NEXT EXPERIMENT.**
