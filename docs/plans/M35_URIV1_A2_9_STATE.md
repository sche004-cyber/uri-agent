# M35 URIv1 — A2.9 STATE

Current state: **COMPLETE — A2.9 CLOSED / ACCEPTED AS PILOT** (2026-09-24, following A2.9-R1's independent `ACCEPT` verdict. Closure committed and pushed.)

Plan: [M35_URIV1_A2_9_NATIVE_PROBLEM_SOLVING_TRACE_PLAN.md](M35_URIV1_A2_9_NATIVE_PROBLEM_SOLVING_TRACE_PLAN.md)

Owner: none — milestone closed. Next: Claude inspects newly committed state and drafts a fresh plan for the following milestone. The S3 case-insensitive `record_type` follow-up is explicitly **not** started.

## Final accepted conclusions (narrow, pilot-scoped)

- Native capability inspection (unprompted `inspect_capabilities`, no discovery-timing hint) was demonstrated: 8/8 scenarios in the R1 rerun (`used_discovery: True` in every scenario's telemetry).
- Multi-turn adaptation was demonstrated: after S4's real controlled failure (`BLOCKED_CUSTOMS_HOLD`), the model explored and changed strategy rather than repeating the blocked call, in both the original and R1 runs.
- No capability-name fabrication was observed in either run: `invented_action_names` empty for all 8 scenarios in both the original and R1 telemetry, including S6 (the scenario built to test for this).
- S4 adaptation occurred, but successful recovery (discovering and dispatching the correct alternate shipment, SHIP-2209) was **not** demonstrated in R1 — the model stopped and asked for help after the (now-closed) unsafe bypass was blocked, without finding SHIP-2209.
- S3 (and S8) remain harness-confounded/unresolved: the undisclosed, case-sensitive `record_type` vocabulary was left untouched by R1's scope and still prevents cleanly separating model incapacity from an environment-interface gap.
- **4/8 is a pilot result, not a qualification score.** One run, `temperature=0.0`, one local model server, 8 hand-authored scenarios, at least one disclosed environment confound (S3/S8) and one likely scorer-coverage gap (S6). No statistical or production qualification claim is made or supported.
- Production latency and exact model/runtime provenance remain unmeasured where the R1 report itself discloses this: model artifact/hash, LM Studio version/configuration, and decoding seed were not exposed by the OpenAI-compatible endpoint. The ~5.9s average per-call latency observed is a local-dev-hardware pilot measurement, not a production latency figure.

## Full verdict history (preserved, none overwritten)

1. **Original execution (2026-09-2x, pre-audit): `VERIFICATION_READY`.** Live 8-scenario Qwen3.5-9B pilot run; 36/36 harness self-tests; 4/8 scenarios passed deterministic scoring (S1, S2, S5, S7). See `docs/plans/M35_URIV1_A2_9_NATIVE_PROBLEM_SOLVING_TRACE_REPORT.md` (unchanged original narrative preserved at §1's own note; the report file itself was later corrected in place for the independent-audit findings — see A2.9-R1 report §"Evidence and audit boundary" for exactly which lines changed).
2. **Independent audit (pre-R1): `REPAIR_REQUIRED`.** Found the original world implementation deviated from the frozen per-scenario action tables in three places: S1 could mutate/move records via `move_item`/`update_record`/`dispatch_shipment` instead of returning `NO_MATCHING_TASK`; S4's `update_record` could rewrite shipment status, creating an unsafe bypass around the controlled `BLOCKED_CUSTOMS_HOLD` failure; S5 could leak the decoy task `T-118` through an unfiltered search path. Directed A2.9-R1 as the one bounded repair, scoped to harness conformance only (no change to scenario goals, frozen fixtures, scoring, or `record_type` matching).
3. **A2.9-R1 harness repair (2026-09-24): `VERIFICATION_READY`.** Repaired exactly the three audited deviations in `scratch/m35_a2_9_native_trace_world.py`; regression suite raised to 40/40 (4 new frozen-scenario conformance tests). Original evidence (`scratch/m35_a2_9_native_trace_results.json`, `scratch/m35_a2_9_pilot_run.log`) preserved unmodified, hash-verified before and after. Reran the full 8-scenario battery against live Qwen3.5-9B to a new, separate artifact (`scratch/m35_a2_9_native_trace_r1_results.json`); result remained 4/8 (S1, S2, S5, S7 pass) under the unchanged frozen scorer. S4 now shows the unsafe bypass blocked (`NO_MATCHING_TASK` on the status-rewrite attempt) followed by honest clarification-seeking, not a false "recovered" dispatch. See `docs/plans/M35_URIV1_A2_9_R1_HARNESS_CONFORMANCE_REPORT.md`. Report explicitly required independent re-audit before closeout.
4. **A2.9-R1 independent audit (2026-09-24): `ACCEPT` (as a pilot).** Independently reproduced: 40/40 tests fresh; recomputed SHA-256 of both original artifacts and the R1 telemetry file, all matched the R1 report's recorded values exactly; read the repaired world-engine code directly and confirmed all three fixes present and no case-insensitive `record_type` change was added; re-derived the 4/8 scenario table, the empty `invented_action_names` claim, and the S4 "adapted but did not recover" conclusion directly from the raw R1 telemetry JSON rather than from the report's prose. No further A2.9 repair required. See `docs/plans/M35_URIV1_A2_9_R1_INDEPENDENT_AUDIT.md`.
5. **A2.9 CLOSED / ACCEPTED AS PILOT (2026-09-24).** Closeout performed on the R1 independent `ACCEPT` verdict. Original and R1 evidence preserved byte-unchanged (hash-verified this closeout). Minimum verification for closure: fresh 40/40 test rerun + hash spot-check of all three protected artifacts, both reproduced in this closeout session. Committed and pushed per standing AO-4 release authority (Claude Code Architect/Final Auditor/Release Authority role). The case-insensitive `record_type` follow-up (A2.9's own §15 "single smallest next experimental question") is explicitly **not** started as part of this closeout.

## Evidence index

| Artifact | Role | Status |
|---|---|---|
| `docs/plans/M35_URIV1_A2_9_NATIVE_PROBLEM_SOLVING_TRACE_PLAN.md` | Frozen blueprint | Unchanged |
| `docs/plans/M35_URIV1_A2_9_NATIVE_PROBLEM_SOLVING_TRACE_REPORT.md` | Original execution report (corrected in place post-audit, per its own §1) | Preserved, audit-corrected |
| `scratch/m35_a2_9_native_trace_results.json` | Original telemetry | SHA-256 `7bf512ae8290942db7dd66a06d7cda402c2e4775a3b413b93933199edaac4b12` — verified unchanged |
| `scratch/m35_a2_9_pilot_run.log` | Original run log | SHA-256 `50fb8d5e06307519d6aaaf18679e2594443cc470d10459d199f3828a545a76db` — verified unchanged |
| `docs/plans/M35_URIV1_A2_9_R1_HARNESS_CONFORMANCE_REPORT.md` | R1 repair report | Preserved |
| `scratch/m35_a2_9_native_trace_r1_results.json` | R1 telemetry | SHA-256 `e286d66500d030e245cbf29e24b613228932df0a62e69098a263b57d4e05e530` — verified unchanged |
| `docs/plans/M35_URIV1_A2_9_R1_INDEPENDENT_AUDIT.md` | R1 independent audit (this closeout) | New, `ACCEPT` |
| `docs/plans/M35_URIV1_A2_9_STATE.md` | This file | New, this closeout |

### RECOVERY STATE
required_model: none (milestone closed)
current_owner: none — closed
resume_stage: COMPLETE
pause_reason: none — milestone closed and released
task: A2.9 native problem-solving trace pilot (Qwen3.5-9B, 8 frozen scenarios) — CLOSED
completed_steps: original blueprint+scenarios+harness+tests (36/36)+live pilot (4/8)+report; independent audit found 3 frozen-table deviations (REPAIR_REQUIRED); A2.9-R1 bounded repair (S1/S4/S5 world-engine fixes, 40/40 tests, live rerun still 4/8 with unsafe S4 bypass now blocked); A2.9-R1 independent audit (ACCEPT as pilot, this closeout); STATE artifact created; closure commit
remaining_steps: none — milestone closed. Next: Claude drafts a fresh plan for the following milestone from freshly inspected post-release repository state. S3 case-insensitive `record_type` follow-up explicitly not started.
changed_files: docs/plans/M35_URIV1_A2_9_R1_INDEPENDENT_AUDIT.md (new), docs/plans/M35_URIV1_A2_9_STATE.md (new); all original/R1 evidence files unchanged (hash-verified)
git_state: closure commit recorded below after push
test_state: `python -m unittest scratch.test_m35_a2_9_native_trace -v` — 40/40 passed, reproduced fresh this closeout
audit_state: independent final audit (pre-R1) `REPAIR_REQUIRED` (preserved); A2.9-R1 independent audit `ACCEPT` (this closeout) — milestone closed on this verdict
last_successful_checkpoint: A2.9 closure commit, pushed
retry_metadata: preserve original and R1 evidence permanently; milestone closed, no further rerun expected; S3 follow-up deliberately not started
