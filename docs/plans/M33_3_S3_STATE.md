# M33.3 S3 — frozen L1/L2 clarification qualification plan

**Current state:** `S3_CLOSED_FROZEN` after independent audit and requalification (no repair required).
**S3_PLAN_FROZEN:** YES. **S3_IMPLEMENTATION_COMPLETE:** YES. **S3_IMPLEMENTATION_AUDITED:** YES. **S3_REPAIRS_REQUIRED:** NO. **S3_REPAIRS_VERIFIED:** N/A. **S3_AUDIT_PENDING:** NO. **S3_CLOSED_FROZEN:** YES. **M33_3_COMPLETE:** NO. **NEXT_SLICE_AUTHORIZED:** NO.
**Authorization:** User S3 Plan + Implement instruction, starting at `98ce66cfe5298741905b5bd40fe6439b46d225c4`. S3 only. S1/S2 stay closed and frozen; S4–S13 remain unauthorized.
**Workstream:** `URI-REFERENCE-CLARIFICATION`.
**Independent audit and freeze evidence:** `docs/plans/M33_3_S3_REPAIR_REQUALIFICATION_AUDIT_REPORT.md`.

## 1. Authority and objective

`docs/plans/M33_3_CROSS_PLAN_STATE.md` §4 defines S3 as **“Battery L1/L2 (no model)”**, after S1. `docs/plans/M33_3_S1_STATE.md` §4.3 assigns the formal frozen L1/L2 battery, manifest and hash anchor to S3. Plan A (`M33_3_ARN_ARCHITECTURE_AND_LT1B_RENDERER_PLAN.md`) §§10–11 defines L1, L2, the proposed categories/minimums, and the all-or-nothing deterministic gates. R2–R4 and the accepted S1 state supersede older Plan A wording where they conflict. Plan B R1.4, D1–D6, the S2 frozen state, and the S1/S2 requalification reports fix upstream authority. The M33.3 planning-basis A3 document and Batch A evidence supply background only; the Batch A model scores and thresholds do not qualify S3.

S3 establishes a reproducible, versioned qualification battery over the **actual frozen S1/S2 interfaces**. It adds fixtures, a deterministic runner, telemetry, and integrity tests. It adds no production behavior, model/provider call, UI, router, persistent learning, or S13 live caller wiring.

| Level | Input and allowed mechanism | Expected behavior and failure |
|---|---|---|
| L1 deterministic core | Synthetic `RARQuery`/`RARResolution`, candidate facts, an injected S2 impact, and represented user actions; call S1 builder, template, validator, `BindingService`, safeguards, plus S2 pure gate where applicable. No model or network. | Contract kind, scope/order/overflow, option identity, template validity and escape, binding state and safety guards match fixture expectations. Any mismatch blocks S3. User interaction is represented as typed `ClarificationResponse`, not live UI. |
| L2 validator adversarial | A valid L1 contract plus a canned malformed or misleading `RenderOutput`/JSON payload; call the frozen `validate_render` interface. No model. | Every injected defect is rejected with the expected governing V-* flag. An invented candidate, omitted slot, unsupported fact, cross-slot swap, or ungrounded selection must never become accepted display text. |

L3 real renderer qualification belongs to S5 (with separate authorization), including provider-neutral adapters, pre-validation rates, latency, and User preference. Those metrics are `UNMEASURED` in S3; no L3 threshold is fabricated.

## 2. Frozen S1/S2 dependencies

- S1: `RARQuery`/`RARResolution` and D5 authority; `build_clarification`; returned ambiguity scope versus displayed cap; `CHOOSE_ONE`, `CONFIRM_ONE`, `CHOOSE_ATTRIBUTE`, `FREE_INPUT_ONLY`; `render_template`/`presented_options` and `validate_render`; `BindingService` click/free-input/attribute/Change, session/fingerprint/expiry/replay checks; process-memory safeguards and bundle contracts. The battery must use these public interfaces, never duplicate their decision logic as its oracle.
- S2: declared/undeclared `Action.wrong_binding_impact`, the three values, and pure G1–G7 execution gate. S3 tests the supplied-binding gate only; U-1 leaves live caller completeness and legacy dispatch to S13. Approval remains independent.
- S1/S2 are protected from S3 edits. The battery may find a defect; any upstream repair requires an explicitly governed extension/authorization rather than silent contract changes.

## 3. Failure-class matrix and fixture scope

The battery will contain **80 fixed cases: 60 L1 and 20 L2**. Each has stable `ARB-001`…`ARB-080` identity, one primary failure class, and optional secondary tags. Cases use synthetic, non-sensitive names; source references are the frozen contracts above. Domain variants cover same-name people, similarly named files, temporal references, attachments, email/thread ambiguity, and document versions (three per class). Structural L1 cases cover zero/one/two/five/overflow candidate boundaries; attribute discrimination and indistinguishable candidates; click/free-input scope, stale and replay guards, Change/rebind, safeguards, and S2 impact. L2 covers schema, unknown/invented/omitted slot, duplicate label, order mutation, unsupported/excluded/cross-slot fact, selection/presumption, and negation/contrast corruption. Plan A §10 L1/L2 category minimums are mandatory where the frozen S1 path supports them; cases can carry multiple justified tags. Edge OFF and generator-unavailable rows prove deterministic template availability only. Main Brain rendering and real timeout/routing belong to later slices.

| Class | Fixture/input | Required output | Prohibited outcome | Critical |
|---|---|---|---|---|
| Candidate ambiguity and scope | 0/1/2/5/>5 candidates, domains, returned subset | Governing kind, returned-scope IDs, RAR order, cap/overflow | invented, omitted, silently expanded or reordered binding scope | Yes |
| Attribute and near-identical | grounded axes/owners/locators; duplicate labels | `CHOOSE_ATTRIBUTE` or fail-closed; no direct confirmation | ungrounded axis/fact, direct certainty from narrowing | Yes |
| Typed response authority | click, free input, stale candidate, replay, wrong session/round | `BindingService` state and candidate ID from frozen contract | text-as-ID, wrong-scope or stale binding, heuristic confirmation | Yes |
| Change and safeguards | X→Y, superseded X, budget/loop limits | validated rebind or fail-closed stop | original X reused, unauthorized redo, unbounded loop | Yes |
| Impact gate | tentative/confirmed and consequential/undeclared/safe impact | S2 G1–G7 decision | approval or low impact inferred from effect | Yes |
| Adversarial renderer | canned wrong keys/facts/claims/order | expected `V-*` flag and rejection (except order-only diagnostic where URI owns order) | defect accepted as user-visible valid output | Yes |

## 4. Fixture and acceptance contract

- Files: `fixtures/m33_3_arn/battery.json` and `manifest.json` with schema `m33.3.s3.l1l2.v1`; `scripts/m33_3_s3_qualify.py` runs cases and writes `docs/plans/M33_3_S3_TELEMETRY.json` and `M33_3_S3_AGGREGATES.json`; `tests/test_m33_3_s3_battery.py` verifies behavior, schema, and integrity.
- Every case records `case_id`, `layer`, `category`, `operation`, synthetic input, fixture-driven expected state/flag, and a short contract citation. IDs and case order are fixed. Canonical JSON is UTF-8 with sorted keys, two-space indentation, one LF final newline. Manifest records byte count, case counts, and SHA-256 over CRLF→LF normalized bytes, following the existing Windows-portable frozen-battery precedent. The runner verifies the manifest before execution and never rewrites the battery.
- L1 critical gate: **100% case pass**. L2 critical gate: **100% injected-defect rejection with the expected flag**, except the `V-ORDER` diagnostic probe: the validator permits it because URI owns final option order. Structural critical gates: zero accepted invented/unknown candidate or slot, zero omitted candidate, 100% escape append and click-by-ID in applicable cases, 100% template validation. An aggregate score cannot hide any failed critical case. Runtime has no governed threshold and is `UNMEASURED`. L3 measures remain `UNMEASURED`.
- Runner records case ID, level, category, expected/observed kind or state/flag, pass/fail, and guard evidence. It does not record raw private user data. Clock-dependent response cases use explicit UTC timestamps; no randomness, provider, network, filesystem search, or model selection affects expected results. Dynamic ambiguity IDs and fingerprints are compared by identity relationships, not hardcoded values. Runtime is `UNMEASURED` because no runtime acceptance threshold exists.

## 5. Scope and stop conditions

| Class | Files or behavior |
|---|---|
| IN | New S3 fixture/manifest, deterministic runner, focused tests, telemetry/aggregates, this frozen state, implementation report, additive S3 governance records. |
| BOUNDARY | Frozen S1 public clarification APIs and S2 pure gate; deterministic RAR result contracts. |
| PROTECTED | `uri_v1/**`, `uri_core/**`, frozen S1/S2 tests, `uri_v1/turn/rar_deterministic.py`, `rar_contracts.py`, `fixtures/m33_3_batch_a/**`, `uri_ui/**`. |
| DEFERRED | S4 source-to-candidate and new fact axes; S5 model wording/L3; S6 router; S7+ learning/lease/versioning/UI; S13 live production wiring, complete binding supply, INT event and URI-RAR adoption. |

Stop if a case requires changing frozen S1/S2 semantics, protected hashes drift, a new authority decision is needed, or a provider/UI/later-slice dependency appears. Do not qualify a real renderer in this pass.

## 6. Qualification and Pass-1 endpoint

Run S3 focused tests and runner; S1 and S2 regression; deterministic RAR/ARN and governance; URI_STATE validator; protected hashes and diff hygiene. Compare any material broad-suite failure to the pre-S3 `98ce66c` baseline. Implementer qualification is **not** independent audit.

At Pass-1 completion record `S3_PLAN_FROZEN: YES`, `S3_IMPLEMENTATION_COMPLETE: YES`, `S3_AUDIT_PENDING: YES`, `S3_CLOSED_FROZEN: NO`, `M33_3_COMPLETE: NO`, and `NEXT_SLICE_AUTHORIZED: NO`. Next safe step: independent S3 audit, bounded repair/requalification, and automatic close/freeze if accepted. Stop before S4.

## 7. Pass-1 implementation checkpoint (2026-09-26)

`S3_PLAN_FROZEN: YES`; `S3_IMPLEMENTATION_COMPLETE: YES`; `S3_AUDIT_PENDING: YES`; `S3_CLOSED_FROZEN: NO`; `M33_3_COMPLETE: NO`; `NEXT_SLICE_AUTHORIZED: NO`. The final fixture manifest, count, and hash are recorded in `M33_3_S3_IMPLEMENTATION_REPORT.md`. This checkpoint adds evidence to the frozen plan; it does not independently audit or accept S3. S4–S13 remain unauthorized.

**Coverage correction before commit:** a final comparison to Plan A §10 found that the initial 64-case design undershot several L1 category minima. The plan was corrected to 80 before the battery anchor was committed; the initial 64-case hash is superseded and has no frozen status. L3-only rows stay deferred. This correction changes fixture coverage, not S1/S2 semantics or S3 authority.

## 8. Independent audit and freeze (2026-09-26)

Independent audit reproduced qualification (80/80: L1 60/60, L2 20/20), the full S1/S2/S3/RAR/governance regression suite (351 passed, 64 subtests), and the governance validator (`VALID`) from a clean worktree at HEAD `4f600e2`. Battery hash, telemetry/aggregate determinism, and all three protected anchors (`rar_deterministic.py`, `rar_contracts.py`, `fixtures/m33_3_batch_a/battery.json`) were independently recomputed and matched exactly. An independent Plan A §10 category-minimum tabulation found 27 of 29 applicable rows cleanly satisfied; two rows ("Hallucinated slot or ID" / "Invented extra candidate," and "Omitted escape option") are thinner than the literal minimum but non-zero and justified against the actual `render_validator.py` mechanism and `check_build`'s positive escape-presence invariant. Ten independent adversarial probes beyond the frozen battery found no disqualifying defect; one non-blocking, non-`FROZEN_REQUIRED` gap was disclosed (a zero-width-space-only label passes validation with no flags). Full detail: `docs/plans/M33_3_S3_REPAIR_REQUALIFICATION_AUDIT_REPORT.md`.

`S3_IMPLEMENTATION_AUDITED: YES`; `S3_REPAIRS_REQUIRED: NO`; `S3_REPAIRS_VERIFIED: N/A`; `S3_CLOSED_FROZEN: YES`; `M33_3_COMPLETE: NO`; `NEXT_SLICE_AUTHORIZED: NO`.
