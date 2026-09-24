# M35 URIv1 — A2.9-R1 Independent Audit

**Verdict: ACCEPT (as a pilot, not a qualification).** Disposable, experimental, proposal-only — not production architecture, not a URI change. No production/governance file touched by this audit.

## Scope

Independent re-audit of the A2.9-R1 harness-conformance repair (`docs/plans/M35_URIV1_A2_9_R1_HARNESS_CONFORMANCE_REPORT.md`), required before A2.9 closeout per that report's own final line ("Independent re-audit is required before A2.9 closeout or any S3 follow-up"). This audit inspects primary evidence directly; it does not take the R1 report's claims on trust.

## Evidence independently reproduced

1. **Repository state.** Branch `m35-uri-v1-parallel-architecture`. `git status --porcelain` confirms the only relevant untracked/modified paths are the A2.9/A2.9-R1 `scratch/` and `docs/plans/` artifacts; no `uri_v1/`, `uri_core/`, `tests/`, `docs/governance/`, `ORCHESTRATION.md`, `AGENTS.md`, or `PROJECT_MEMORY.md` file is touched.
2. **Test suite.** `python -m unittest scratch.test_m35_a2_9_native_trace -v` run fresh: **40/40 passed**, 0 failures, 0 errors — matches the R1 report's claimed count exactly.
3. **Original-evidence hash integrity.** Recomputed SHA-256 of both original A2.9 artifacts, confirmed byte-identical to the R1 report's recorded values:
   - `scratch/m35_a2_9_native_trace_results.json` → `7bf512ae8290942db7dd66a06d7cda402c2e4775a3b413b93933199edaac4b12` — **match**.
   - `scratch/m35_a2_9_pilot_run.log` → `50fb8d5e06307519d6aaaf18679e2594443cc470d10459d199f3828a545a76db` — **match**.
   - `scratch/m35_a2_9_native_trace_r1_results.json` → `e286d66500d030e245cbf29e24b613228932df0a62e69098a263b57d4e05e530` — **match** against the R1 report's recorded R1 telemetry hash.
4. **Repair code inspected directly (not trusted from the report's prose).** `scratch/m35_a2_9_native_trace_world.py`:
   - S1 `move_item`/`update_record`/`dispatch_shipment` return exactly `{"status":"error","code":"NO_MATCHING_TASK"}` with unchanged state (line 95 and call sites) — confirmed.
   - S5 `search_records` filters containing `"flagged"`, `"pallet"`, or `"supervisor"` return the frozen empty result for every record type (line ~118) — confirmed; no path leaks `T-118`.
   - S4's `update_record` status-rewrite bypass is removed (routes through the same `NO_MATCHING_TASK` path) — confirmed by code read and by the R1 telemetry trace (below).
   - No case-insensitive `record_type` matching was added anywhere in the diff — confirmed; S3/S8 remain on the original case-sensitive lookup.
5. **R1 live-run telemetry re-inspected directly, per scenario, from `scratch/m35_a2_9_native_trace_r1_results.json`:**
   - Scores: S1 `True`, S2 `True`, S3 `False`, S4 `False`, S5 `True`, S6 `False`, S7 `True`, S8 `False` — **4/8**, matching the R1 report's table exactly.
   - `invented_action_names` is `[]` for all 8 scenarios — confirms the no-fabrication claim directly from data, not merely from the report's restatement.
   - `used_discovery` is `True` for all 8 scenarios — confirms unprompted capability-inspection/discovery behavior occurred in every scenario in this rerun (a stronger and cleanly-measured statement than the original run's "7/8 executed, one intended").
   - S4's `final_world_state` shows `SHIP-3301` still `"ON_HOLD_CUSTOMS"` and `SHIP-2209` still `"PACKED_READY"` (never dispatched); `dispatch_calls.SHIP-3301 == 0`; the model's final `finish.answer` states it cannot clear the customs hold and stops. This independently confirms two separate facts: (a) the original unsafe state-mutation bypass is genuinely closed (no illegitimate SHIP-3301 dispatch occurred), and (b) the model did **not** discover or dispatch the correct alternate shipment SHIP-2209 — adaptation (`post_failure_behavior: "CHANGED_STRATEGY"`, `requested_clarification: true`) occurred, but successful recovery was not demonstrated. The R1 report's own §"R1 live rerun" narrative is accurate; this audit independently re-derives the same conclusion from the raw JSON rather than the prose.
   - Aggregate: `total_calls: 52`, `total_prompt_tokens: 57420`, `total_completion_tokens: 21081`, `avg_latency_ms ≈ 5939.5`, `total_wall_clock_seconds ≈ 308.86` — matches the R1 report's aggregate line.

## Accepted conclusions (narrow, evidence-bound)

- Native capability inspection (`inspect_capabilities`, unprompted, no discovery-timing hint in the system prompt) was demonstrated in the R1 rerun: `used_discovery: True` in all 8/8 scenarios, directly confirmed in telemetry.
- Multi-turn adaptation was demonstrated: after S4's real `BLOCKED_CUSTOMS_HOLD` failure, the model did not repeat the blocked call; it explored and changed strategy (`CHANGED_STRATEGY`), consistent across both the original and R1 runs.
- No capability-name fabrication was observed in either the original or the R1 run: `invented_action_names` is empty for every scenario in both telemetry files, including S6 (the scenario designed to test for exactly this).
- S4 adaptation occurred, but successful recovery (discovering and dispatching SHIP-2209) was **not** demonstrated in R1; the model stopped after the safe path was blocked and asked for help instead. This is a materially different, weaker claim than "recovery," and is recorded as such.
- S3 remains harness-confounded and unresolved: the undisclosed, case-sensitive `record_type` vocabulary (documented in the original report §9.1 and left untouched by R1 per its own stated scope) still prevents cleanly separating model incapacity from an environment-interface gap. This audit does not attempt to resolve it and treats it as an open, disclosed limitation, not a passed or failed capability claim.
- **4/8 is a pilot result, not a qualification score.** It was produced by one run, at `temperature=0.0`, on one local model server, against 8 hand-authored scenarios with at least one known, disclosed environment confound (S3/S8's `record_type` vocabulary) and one likely scorer-coverage gap (S6, discussed in the original report §9 item 3 and not re-litigated here since R1 did not touch scoring). It does not meet, and was never designed to meet, any statistical or production qualification bar.
- Production latency and exact model/runtime provenance remain unmeasured where the R1 report itself states so: model artifact/hash, LM Studio version/configuration, and decoding seed were not exposed by the OpenAI-compatible endpoint and are recorded `UNMEASURED` in the R1 report's own reproducibility-metadata section — this audit did not find any way to independently supply these values either, and treats the average per-call latency (~5.9s) as a local-dev-hardware pilot measurement only, not a production latency figure.

## What this audit does not claim

- This audit does not re-litigate or re-score S3, S6, or S8; their original classifications (harness-confounded / likely-scorer-gap / harness-confounded, respectively) stand as recorded in the original and R1 reports.
- This audit does not certify Qwen3.5-9B for any production closed-loop-reasoning role. The pilot's own report (§12, §14) already states the outcome-rate signal is confounded and that cross-model replication is not yet justified; this audit found no evidence in R1 that changes either conclusion.
- This audit performed no new live model calls; it is a reproduction/verification pass over existing evidence (tests, hashes, code, and telemetry), consistent with A2.9-R1's own stated scope (harness-conformance repair only, no scoring or environment redesign).

## Verdict

**ACCEPT, as a pilot.** All R1 report claims independently checked against primary evidence (tests, file hashes, source code, raw telemetry JSON) were confirmed accurate and unembellished; the report's own hedges (S3/S8 confound unresolved, S4 recovery not demonstrated, S6 scorer-gap, reproducibility-metadata gaps) were verified rather than found to be understatements or overstatements. No further A2.9 repair is required. A2.9 is ready to close on this narrow pilot basis; no S3 case-insensitivity follow-up or any other new experiment is authorized by this audit.
