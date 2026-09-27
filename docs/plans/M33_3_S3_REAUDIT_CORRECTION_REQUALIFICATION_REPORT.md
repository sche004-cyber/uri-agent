# M33.3 S3 — Independent Re-Audit, Correction, Bounded Repair, and Requalification Report

**Auditor:** Claude Code, under the AO-4 final-audit / bounded-fix / release authority.
**Date:** 2026-09-27.
**Verdict:** `S3_REAUDIT_CORRECTION_REPAIR_REQUALIFICATION_ACCEPTED`. This corrects the verdict recorded at `8a2656a` ("no repair required"). The earlier report `docs/plans/M33_3_S3_REPAIR_REQUALIFICATION_AUDIT_REPORT.md` is preserved with a correction banner.

## A. Repository and baseline

- Worktree `C:\Users\cheta\Development\Uri\_V1`, branch `m35-uri-v1-parallel-architecture`.
- Starting HEAD `8a2656a507b8e80f4022cb59c1a9419d9e8b59c1`, equal to `origin/m35-uri-v1-parallel-architecture` after `git fetch`.
- Ancestry: `98ce66c` (pre-S3) → `4f600e2` (S3 implementation) → `8a2656a` (S3 audit and freeze). The task package assumed S3 was still `AUDIT_PENDING` at `4f600e2`. Repository evidence showed S3 already recorded `S3_CLOSED_FROZEN` at `8a2656a`. This audit therefore re-audits that closure.
- Unrelated dirty state was present before and after: modified `SKILL.md` and many untracked M35 research files. None of it was read into, altered, staged, or stashed.
- `git diff 8a2656a -- uri_v1 uri_core fixtures/m33_3_batch_a` is empty. No production code changed.

## B. Governing S3 contract recovered

Sources read directly: `M33_3_S3_STATE.md` (governing; §1 says it supersedes older Plan A wording on conflict), `M33_3_CROSS_PLAN_STATE.md` §4, Plan A §10 (category minimums) and §11 (gates), S1/S2 state files, `URI_STATE.yaml`.

- L1: deterministic core through the real S1 builder, template, validator, `BindingService`, safeguards, and the S2 pure gate. Gate: 100% case pass.
- L2: canned adversarial `RenderOutput` or JSON through the real `validate_render`. Gate: 100% rejection with the expected flag, except the `V-ORDER` diagnostic probe.
- Structural gates: zero accepted invented or unknown candidate or slot, zero omitted candidate, 100% escape append and click-by-ID, 100% template validation.
- Coverage: `M33_3_S3_STATE.md` §3 states that Plan A §10 L1/L2 category minimums "are mandatory where the frozen S1 path supports them".
- Integrity: canonical JSON, LF-normalized SHA-256 manifest, runner verifies the manifest before execution. Plan A §10 requires a version bump for any battery edit after freeze.
- L3, runtime, and live UI: `UNMEASURED` and deferred.

## C. Independent audit findings

1. Runner (`scripts/m33_3_s3_qualify.py`, read in full). It checks hash, byte count, schema, count, ID order, and layer counts before any case runs. Every exception becomes a failed case. The aggregate `critical_gates_passed` is `not failed`, so one failed case fails qualification. `--write` and non-write paths share the same evaluation. The `observed.get(k, True)` default in `check_build` only applies to cases with no contract, where escape and template gates do not apply. No defect.
2. L1 uses the real S1/S2 interfaces. The runner does not re-implement their decision logic as an oracle.
3. Category tabulation against Plan A §10 (fixture `category` field; fixtures have no secondary tags):
   - Row 18 "Hallucinated slot or ID" (L2, minimum 2): 1 case (ARB-064, `unknown_slot`).
   - Row 19 "Invented extra candidate" (L2, minimum 2): 1 case (ARB-065, `extra_slot`).
   - Plan A's L2 minimums sum to exactly 20. The battery used 2 of its 20 L2 slots on `duplicate_label`, which has no Plan A row.
   - Row 22 "Omitted escape option" (L1, minimum 1): no dedicated case. The template never emits an escape slot, and `presented_options` always appends one. `escape_appended` is asserted on every contract-bearing L1 case, so each of those cases already exercises the renderer-omits-escape scenario. Classified as satisfied.
   - All other applicable rows meet their minimum.
4. `URI_STATE.yaml` M33.3 `scope` still said S3 "awaits independent audit; it is not closed/frozen", while `status` said `S3_CLOSED_FROZEN`. The validator returned `VALID` because it does not check prose.

## D. Defects and gaps found

- **F1 — blocking.** Rows 18 and 19 were below their mandatory minimum. The S1 validator path supports both input shapes, so §3 makes the minimums mandatory. The `8a2656a` report called this "thin but not disqualifying" because both shapes raise the same flag. That reasoning is withdrawn: a category minimum measures input coverage, not the number of distinct flag classes.
- **F2 — governance contradiction.** The stale `scope` line described above.
- Non-blocking, carried forward and re-confirmed: a label made only of zero-width spaces passes validation (`[\w.]+` does not match it). This is a policy question, not an S3 gate. `V-LENGTH` is not exercised by the battery. It is not a Plan A row.

The User was asked how to handle F1, because S3 was already frozen. The User chose: reopen, add 2 L2 cases, requalify, re-freeze.

## E. Repairs performed

- `scripts/m33_3_s3_qualify.py`: added two `check_render` mutations and imported `ESCAPE_LABEL`. No other logic changed.
  - `candidate_id_as_slot`: the first slot key is replaced by the real candidate ID (`a`) instead of its option key (`s1`). This is a hallucinated ID.
  - `renderer_escape_slot`: the renderer appends its own `escape` slot. This is an invented extra option.
- `fixtures/m33_3_arn/battery.json`: appended ARB-081 (`hallucinated_id`) and ARB-082 (`invented_option`). Both are L2 `render` cases using ARB-064's synthetic input and expect `V-SLOT-UNKNOWN` with `valid=false`. `schema_version` changed to `m33.3.s3.l1l2.v2`. ARB-001..080 are content-identical to `8a2656a` (verified by a JSON comparison against `git show`).
- `fixtures/m33_3_arn/manifest.json`: 82 cases, 60 L1 / 22 L2, 96811 bytes, SHA-256 `3a0250aa92af755e64151a08dca0a5ea3f42f8cd767560471d720fb10af83b01`. A `supersedes` note records the v1 hash `7601125b…32fa7e`, which no longer has frozen status.
- `tests/test_m33_3_s3_battery.py`: counts changed to 82/60/22. Added `test_plan_a_rows_18_19_minimums_and_frozen_v1_prefix` and `test_wrong_expected_flag_fails_new_cases`. The second is a negative control: each new case fails when its expected flag is wrong.
- Telemetry and aggregates were regenerated. Rows ARB-001..080 in the telemetry are identical to `8a2656a`.

Rows 18 and 19 are now covered as: row 18 = ARB-064 and ARB-081; row 19 = ARB-065 and ARB-082.

## F. Qualification and reproducibility

- Pre-repair (read-only, `8a2656a`): 80/80, battery 95085 bytes, `7601125b…` — reproduced.
- Post-repair `python scripts/m33_3_s3_qualify.py --write`: `total 82, passed 82, failed 0, l1_passed 60, l2_passed 22, critical_gates_passed true, l3_model_metrics UNMEASURED, runtime_ms UNMEASURED`.
- New cases observed: ARB-081 `['V-SLOT-UNKNOWN','V-SLOT-MISSING']` valid=false. ARB-082 `['V-SLOT-UNKNOWN','V-EXTRA-OPTION']` valid=false.
- Two fresh-process `--write` runs produced byte-identical files: telemetry `2057225b83898f59910f02629a30960305b12d713934b2199fef5f807f5256b1`, aggregates `f1fa494f64f8b3baeb7d9805c2233dd4b2ae076c0d3166d416d7d0c1f387402f`.
- An independent standalone recompute of the LF-normalized battery gave 96811 bytes and `3a0250aa…3b01`, matching the manifest.

Independent adversarial probes (scratchpad only, not added to the repository):

| Probe | Result |
|---|---|
| Click with an unknown candidate ID | `REJECTED` |
| Build with zero candidates as AMBIGUOUS | `RARContractViolationError` |
| Foreign `wrong_binding_impact` string | `ValueError` at `Action` construction |
| Foreign `ReferenceBindingStatus` | `ValueError` |
| Labels as a list, or output `None` | `V-SCHEMA` |
| Label claims the other candidate's title | `V-UNSUPPORTED-FACT`, `V-CROSS-SLOT` |
| Full-width Unicode invented token | `V-UNSUPPORTED-FACT` |
| Labels duplicated except for case and whitespace | `V-LABEL-DUP` |
| `escape` used as a renamed slot key | `V-SLOT-UNKNOWN`, `V-SLOT-MISSING` |
| Empty labels | `V-SLOT-MISSING`, `V-EXTRA-OPTION` |
| Repeated in-process evaluation | identical results |

All probes failed closed. None is a new defect.

## G. Regression and protected anchors

- Focused suite (the task package's command): **355 passed, 64 subtests passed**. The previous result was 351 passed. The difference is the 2 new parametrized battery cases plus the 2 new tests.
- `python scripts/governance/uri_state_validator.py docs/governance/URI_STATE.yaml`: `VALID`.
- Protected anchors, recomputed and unchanged:
  - `rar_deterministic.py`: `e02af25b…fb649`
  - `rar_contracts.py`: `4cc9aa43…6819`
  - Batch A battery (LF): `06d0dfff…c3fa`
- No broad-suite failure occurred, so no baseline comparison was needed.

## H. Governance updates

- `M33_3_S3_STATE.md`: header flags corrected (`S3_REPAIRS_REQUIRED: YES`, `S3_REPAIRS_VERIFIED: YES`) and §9 correction record added. §8 is preserved.
- `M33_3_CROSS_PLAN_STATE.md`: S3 header and table rows annotated with the correction and new evidence path.
- `URI_STATE.yaml`: stale `scope` line fixed (F2). `s3_repairs_required: true`, `s3_repairs_verified: true`, and `s3_reaudit_correction_evidence` added. Correction text was appended to `s3_closure_note` and `status_history_note`; earlier text is kept.
- The old audit report received a correction banner. Its body is unchanged.

## I. Known limitations and deferred scope

- The zero-width-space-only label gap and the unexercised `V-LENGTH` flag are open policy or coverage questions for a future authorized slice.
- Repeated `open_change` calls without a `respond` in between are not characterized beyond the earlier single probe.
- L3 real renderer and model qualification (S5), source-to-candidate work (S4), router (S6), learning and UI (S7+), and live production wiring (S13) remain deferred and `UNMEASURED`.

## J. Commit / push

Only S3 repair, evidence, and governance files are staged: runner, battery, manifest, S3 test, telemetry, aggregates, S3 state, cross-plan state, `URI_STATE.yaml`, the old report banner, and this report. The push receipt is recorded in the session output, not in this file, because a file cannot contain its own commit hash.

## K. Final verdict

**`S3_REAUDIT_CORRECTION_REPAIR_REQUALIFICATION_ACCEPTED`**

- S1_CLOSED_FROZEN: YES
- S2_CLOSED_FROZEN: YES
- S3_CLOSED_FROZEN: YES (re-frozen at battery v2)
- M33_3_COMPLETE: NO
- NEXT_SLICE_AUTHORIZED: NO — passing S3 does not authorize S4 or any later slice.
