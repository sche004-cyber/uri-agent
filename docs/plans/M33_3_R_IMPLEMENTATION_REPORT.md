# M33.3-R — Implementation Report (candidate awaiting independent closing audit)

**Verdict:** `M33_3_R_IMPLEMENTATION_CANDIDATE_AWAITING_INDEPENDENT_CLOSING_AUDIT`.
**Implementer:** Claude (Opus 5.5), 2026-09-27. The testing and the self-review (§11) are the implementer's own and are **not** the independent closing audit. M33.3 is not closed or frozen by this report.
**Plan / state:** `docs/plans/M33_3_R_CONTINUOUS_EXECUTION_PLAN.md`, `docs/plans/M33_3_R_STATE.md`.

## 1. Baseline and scope

- Baseline: `m35-uri-v1-parallel-architecture` @ `c2f583909a3d13d295c997c038b0ac724f787755`, equal to `origin`.
- Authorized scope: S5, S6, S7, S8, S10, S11, S12. S9 (URI-Memory / D4) and S13 (INT-* integration) were not absorbed.
- Reopened by explicit User decision: S1, for amendment S1-A1 only (§2).

## 2. Governance

- GD-1, GD-2 and GD-3 were repaired in `docs/governance/URI_STATE.yaml` (state file §3). The validator reports VALID.
- **S1-A1** (User decision at the S5 touchpoint) widened the RenderValidator allowlist with closed-class function words only. S1, S2 and S3 were requalified, and S3 scored 82/82. The anchor was re-pinned from `903ef9fe…` to `4a29cc25…`. Record: `docs/plans/M33_3_R_S1_A1_VALIDATOR_AMENDMENT.md`.

## 3. S5 — clarification-wording qualification

- **Built:** a need-class policy (`uri_v1/wording/need_class.py`); a renderer port with template and LM Studio adapters (`renderer_port.py`), using provider-native constrained decoding and a load-state check that refuses cold loads; a policy-mode selector (`selector.py`) into which the harness injects the single `uri_core` router; the L3 battery (60 cases, `fixtures/m33_3_s5/`); and the harness (`scripts/m33_3_r_s5_qualify.py`), which records telemetry, a blind pairwise sheet and a shadow analysis.
- **Exploratory:** two rounds of 1,020 rows each. Round 2 followed a bounded prompt repair and is reported in `M33_3_R_S5_EXPLORATORY_REPORT.md`.
- **User touchpoint:** reopen the S1 allowlist; warm p95 ≤ 1.5 s; fallback ≤ 25 %; template is fine, so there is no improvement gate.
- **Gate:** `fixtures/m33_3_s5/threshold_gate.json`, frozen before the final run (LF SHA-256 `ea471fd8…aed5b`). Production configuration: constrained decoding, allowlist prompt v3.
- **Final:** a fresh run of 1,020 rows (`M33_3_R_S5_FINAL_*`). Verdict `S5_FINAL_REQUALIFIED`: all six frozen-required checks pass and all gate inputs match.

**Tier gates:**

| Tier | Result | Fallback | p95 | Rows |
|---|---|---|---|---|
| Edge wording (EXPLAIN) | FAIL | 71 % | 541 ms | 52 |
| Capable wording (REASONING) | FAIL | 67 % | 1.20 s | 6 (small sample) |

- **Qualified routes:** template only, for every need class. Wording stays template-primary, as Amendment G1 permits.
- **Informational only, not gated:** the Capable model on EXPLAIN contracts would have met the thresholds (19 % fallback, p95 1.43 s). Plan A R2.5 never routes cosmetic EXPLAIN wording to the Capable Brain, so this is not a qualified route.

## 4. S6 — router extension

`uri_core/core/edge/routing_policy.py` is extended in place; no second router exists. The additions:
- `evaluate_intelligence_route`, which covers D2 mode × AUTO/explicit × Edge ON/OFF × work role (G2 supporting and substantive);
- `route_clarification_wording`, the R2.5 table;
- `IntelligenceRoutingDecision.LIMITATION`;
- an EDGE_ONLY guard on `evaluate_routing` (pre-audit finding PA-1: `ESCALATE`/`SUPPRESS` under EDGE_ONLY handed work to the Main Brain).

Tests: 35, including exhaustive grids of 6,144 route evaluations. `evaluate_routing` is unchanged outside EDGE_ONLY across the exhaustive M33.2 input grid, and the M33.2 edge tests pass. The router is not wired into `/ask` or any production path.

## 5. S7 — trace_id and the evaluation event stream

`uri_v1/evaluation/trace_context.py` generates W3C trace-context IDs. `events.py` defines the versioned `m33.3-r.s7.evaluation.v1` event: identifiers and closed vocabularies only, strict parsing, and OTel `gen_ai.evaluation` naming without free-text explanation. `store.py` is a per-user, month-partitioned store with durable learning ON by default, an OFF switch, session evidence, inspect, delete and reset. `trace_id` is carried on the M33.3-R wording result and on the S12 card contract. The production `/ask` `trace_id` belongs to S13. Tests: 16.

## 6. S10 — lease ownership and residency

`RuntimeLease` gains additive owner provenance; the two-field constructor still works. `lease_ownership.py` adds a per-process ledger that refuses to release any lease URI does not own. LM Studio TTL, load and unload stay provider-native. Tests: 4. The protocol was written before the study (`M33_3_R_S10_RESIDENCY_STUDY_PROTOCOL.md`), and the study ran in its own window after S5 (`M33_3_R_S10_RESIDENCY_*`).

| Configuration | Result |
|---|---|
| Edge resident | cold load 2.4 s; warm p50/p95 379/555 ms; +1.7 GB GPU |
| Capable resident | cold load 4.5 s; warm p50/p95 945/1,222 ms; +6.0 GB GPU; RAM available 5.8 GB |
| Co-resident | 9.4 GB GPU; RAM available 4.3 GB; no latency change |
| On demand | 3.2 s (2B) and 6.1 s (9B) total |
| TTL 20 s | provider unloaded the model after 21.4 s idle |
| External lease | classified EXTERNAL; URI refused to unload it; still loaded after URI cleanup |

No limit was reached, and the frozen-required criteria pass.

## 7. S11 — result-version ownership

- **Discovery:** results are not editable in `uri_ui`, but they are editable outside URI (Gmail drafts, files). No versioning exists anywhere.
- **Plan:** `M33_3_R_S11_RESULT_VERSION_PLAN.md`.
- **Implementation:** `uri_v1/results/`, an append-only, content-addressed ledger plus a `RedoCoordinator` over the frozen S1 `authorize_redo`.
- **Invariant:** an edited result is never overwritten. The automatic redo stops and preserves the edit. A new version on top of an edit needs an explicit, freshly authorized request (decision D-S11-1).
- **Tests:** 7, covering both the protected edited-result path and normal regeneration.
- **Bounded fix during implementation:** once a preserved edit became the head version, it was read back as unedited.

## 8. S12 — fixture-backed clarification UI

`uri_ui/lib/{models/clarification.dart, widgets/clarification_card.dart}` add the inline card:
- ranked grounded options with no padding;
- `a*` filter chips;
- an escape button that opens free input, which is emitted verbatim;
- one answer per round;
- malformed or over-cap cards fail closed.

The fixtures are exported from real S1 contracts. Tests: Flutter 35/35 (full `uri_ui` suite 203/203, `flutter analyze` clean). A bridge test of 11 cases replays every emitted payload through the S1 `BindingService`: clicks bind the candidate ID, attribute choices narrow and never confirm, and label text used as an ID is rejected. The card is not wired into any screen or backend. The design record is `docs/design_library/approved/clarification_card_2026-09-27.md`.

## 9. S8 — route performance and offline replay

`uri_v1/evaluation/route_performance.py` adds a separate per-user store (ON/OFF, reset, version-keyed) and `choose_route`, a pure function that never returns a route outside the qualified, eligible set. `scripts/m33_3_r_s8_replay.py` runs the replay (Li et al. method), IPS and SNIPS over the frozen S5 final outcomes (`M33_3_R_S8_REPLAY_RESULTS.json`).

- **Replay over real routes:** only the template is qualified for each need class, so learned preference equals fixed routing. Exact value 1.0 for both, and IPS error 0.
- **Guards:** all pass — OFF uses fixed routing, OFF writes nothing, a version bump invalidates evidence, an unqualified route is never chosen, and reset returns fixed routing.
- **Method validation:** synthetic arms, labelled as not route evidence. The learner picks the better arm; IPS error 0.013.
- **Tests:** 7.

Everything is offline only. No online promotion takes place.

## 10. Integrated qualification

**Regression runs:**

| Run | Result |
|---|---|
| Full tracked regression + M33.3-R lanes (main worktree) | 3,239 passed, 12 failed, 65 skipped, 218 subtests |
| Clean-baseline comparison (fresh `c2f5839` checkout) | 3,146 passed, 14 failed |

**Failure attribution:**
- 11 failures are the same tests that fail on the clean baseline.
- 3 baseline failures (the S3 manifest and two S4 anchor tests) do not occur in this worktree. They only fail on a CRLF checkout.
- 1 failure (`test_m33_batch_c_durable_primitives::…one_brain_visible_projection`) also fails 3/3 on the clean baseline when run alone. It is a pre-existing Windows atomic-write failure in a shared temp directory.
- New failures caused by M33.3-R: **0**.

**Other checks:**
- S3 qualification: 82/82.
- S1–S4, M33.2 edge, RAR and Batch A suites pass within the full run.
- Protected anchors: OK. There are 8 S4 anchors, including RAR `4db77566…`, and 24 frozen LF anchors, with only the recorded S1-A1 re-pin.
- Governance validator: VALID.
- `git diff --check` on staged files: clean.
- Production scope: no `uri_core` module references the new router entry points or the lease ledger; `uri_core` never imports `uri_v1`; `uri_v1` never imports `uri_core` (boundary test); `orchestrator.py` is unchanged; no `/ask` or agent-loop wiring.
- S9/S13 not absorbed: no durable reference-memory store, no production integration, no INT-* event, no URI-RAR adoption.
- `graphify-out` was not regenerated. This follows M33.3 S1–S4 precedent (tracked graph last updated at M33.2 B2); disclosed.

## 11. Implementer self-review (not independent)

Falsification attempts and outcomes:
- **Scope.** Grep confirms no production wiring. A boundary violation (`uri_v1` importing `uri_core`) was caught by the frozen S1/S2 tests and repaired: local storage helpers now copy the proven pattern, and the harness injects the router.
- **Frozen contracts.** Only S1-A1 changed an S1–S4 file, by User decision. The S3 battery, S4 anchors and RAR are unchanged.
- **Route behavior.** Exhaustive grids cover the D2 table, EDGE_ONLY, Edge OFF and cold load.
- **Event provenance.** Raw text in identifier fields is rejected; comments are stored only as presence flags.
- **Resource measurements.** Hardware windows were serialized: S5 exploratory R1 and R2, S5 final, and S10 each ran alone, with a no-model preflight each time.
- **Version ownership.** A real defect was found by test and fixed.
- **UI ID binding.** A forged label-as-ID is rejected.
- **Offline replay.** It ran on the frozen verdict only.
- **Threshold discipline.** The gate was frozen before the final run and not changed afterwards.
- **Research and reuse.** Plan §3.

Remaining limitations and material risks:
1. The Edge and Capable wording tiers are not qualified, so model wording has no production value yet. EXPLAIN and REASONING use template wording and limitation statements.
2. REASONING has only 6 rows, so its verdict is statistically weak.
3. The need-class boundary is still a hypothesis. It was not calibrated by ratings, because the User chose "template is fine".
4. S1-A1 and prompt v3 were selected using exploratory evidence. The thresholds were the User's and were frozen before the final run.
5. The frozen S1 validator's empty-question gap is closed only in the S5 selector, not in S1.
6. S8 is degenerate on real routes: there is one qualified route per need class.
7. S11's automatic redo on an edited result stops rather than versioning (D-S11-1). S1 never records `REDONE`.
8. S12 is not placed in any screen.
9. A fresh checkout with `core.autocrlf=true` fails raw-byte anchor tests. This predates M33.3-R.
10. Round 1 of the exploratory run hit a non-fatal `lms` output-decoding error. It was fixed before round 2.
