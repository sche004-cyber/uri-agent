# Independent Pre-Audit: M33.3 S4 Offline Source-to-Candidate Plan

**Scope:** Independent pre-audit only, read-only. No implementation, no edits to any file other than this plan/report.

**Documents inspected (primary evidence):**
- `docs/plans/M33_3_S4_OFFLINE_SOURCE_TO_CANDIDATE_PLAN.md` (the plan under audit)
- `docs/plans/M33_3_CROSS_PLAN_STATE.md` §§4–5 (and supporting §§1–3, 6–7 for cross-reference)
- `docs/plans/M33_3_URI_BRAIN_ARCHITECTURE_PROPOSAL.md` R2 and §§15–16 (and R1.7, R1.10–R1.12 for context)
- Frozen code: `uri_v1/turn/rar_contracts.py`, `uri_v1/turn/rar_deterministic.py`, `uri_v1/turn/turn_frame_builder.py`, `uri_v1/turn/rar_attachment_order_experimental.py`, `uri_v1/turn/rar_attachment_order_factorial_fixtures.py`, `scripts/m35_a2_8f_detector_d1r.py`, `scripts/m35_a2_8h_detector_d1rq.py`
- Frozen corpus: `uri_v1/turn/rar_natural_boundary_raw_turn_fixtures.json`

## Acceptance criteria (defined before drafting the verdict)

1. **PG-5:** S4 has its own separately scoped, pre-audited plan with correct hash anchors for every artifact it declares frozen/protected.
2. **PG-6:** the A9 `rar_deterministic.py` hash the plan cites is byte-correct against the actual repository file.
3. **Scorer isolation:** the plan's own enumeration of scorer-only/forbidden fields must fully match the frozen corpus's own authoritative "must not receive" contract, since the plan's producer-construction step (§2.1) is defined as "the harness constructs this snapshot without passing scorer-only keys" — an implementer following the plan text alone must not be able to leak a scorer field through an omission in the plan's own list.
4. **D0/D1R/D1RQ arms:** each arm's described contract (detector output shape, resolver entry point, TurnFrame path) must match the real function signatures/dataclasses, and detectors must in fact carry no candidate/anchor/binding authority as claimed.
5. **Protected anchors:** the in/out file boundary (§4) must not touch `uri_v1/**`, `uri_core/**`, `uri_ui/**`, or frozen S1/S2/S3/Batch A/A9 artifacts, and must not exceed the User's S4-only authorization anchored at commit `0caf3dd`.

## Findings

### F1 — BLOCKING: incomplete scorer-only field enumeration (scorer isolation / PG-5)

The plan (§1) states: *"`ground_truth_references`, `expected_*`, `intended_candidate_id(s)`, `reason`, category and difficulty are scorer-only."* This is presented as the authoritative list the offline producer's `SourceSnapshot` construction must exclude.

The frozen corpus itself (`rar_natural_boundary_raw_turn_fixtures.json`, `harness_input_contract.system_under_test_must_not_receive`) declares a longer list:
`ground_truth_references`, `variants[].expected_*`, `variants[].acceptable_alternatives`, `variants[].intended_candidate_id`, `reason`, `category`, `secondary_signals`, `difficulty`.

Verified directly in the fixture file: both `acceptable_alternatives` (per-reference, e.g. lines 552, 574, 618…) and `secondary_signals` (per-variant, e.g. lines 516, 582, 648…) are real populated fields sitting alongside the fields the plan does name. The plan's §1 list omits both.

**Why this is blocking:** §3's critical structural gate is "zero scorer-field leakage into producer inputs." §2.1 instructs the harness to build the `SourceSnapshot` "without passing scorer-only keys," and §1 is the only place in the plan that defines what those keys are. An implementer executing the plan exactly as written, using its stated field list as the exclusion filter, would not exclude `acceptable_alternatives` or `secondary_signals` — a direct, concrete path to violating the plan's own zero-leakage gate. This is a plan-text defect, not a corpus defect: the corpus's own contract is complete and correct; the plan's restatement of it is not.

**Required repair:** correct §1's scorer-only field list to match the corpus's `harness_input_contract.system_under_test_must_not_receive` exactly (add `acceptable_alternatives` and `secondary_signals`), and confirm the anti-leakage focused test in §3 asserts absence of all eight fields, not the six the plan currently names.

### F2 — NON-BLOCKING: malformed hash anchor for `rar_contracts.py`

Plan §1 cites `rar_contracts.py` SHA-256 as `4cc9aa43726a870ca2e9ab1b19f6bf9d72dc74c8a2818856776af95195b6819`. This string is 63 hex characters (one character short of a valid SHA-256 digest) and does not match the file.

Independently recomputed: `sha256(uri_v1/turn/rar_contracts.py)` = `4cc9aa43726a870ca2e9ab1b19f6bf9d72dcb74c8a2818856776af95195b6819` (64 chars; note the `dcb74` the plan's string is missing the `b` from). This correct value is exactly what `M33_3_CROSS_PLAN_STATE.md` §6 already records. The file itself is unmodified; only the plan's own quotation of its hash is corrupted.

All other cited hashes were independently recomputed and matched exactly:
- `rar_deterministic.py`: `e02af25b…8fb649` — match (PG-6 satisfied).
- Batch A battery `06d0dfff…d1c3fa` — match.
- A9 resolver `rar_attachment_order_experimental.py` (`90d89c37…f79c`) and fixtures `rar_attachment_order_factorial_fixtures.py` (`36570706…315a`) — match.
- D1R detector `scripts/m35_a2_8f_detector_d1r.py` (`03479773…be75`) and D1RQ detector `scripts/m35_a2_8h_detector_d1rq.py` (`49f5faa9…6b82`) — match.
- Frozen corpus `rar_natural_boundary_raw_turn_fixtures.json` (`0ea54473…07380`) — match.

**Why non-blocking:** the underlying file is untouched and the correct hash is already durably recorded elsewhere in governance state (`M33_3_CROSS_PLAN_STATE.md` §6), so an implementer who recomputes from the repository (as the pre/post-hash verification step in §3 requires) will get the true, correct value and can cross-check it against the state file. The risk is a spurious false-fail if a pre/post verification script is instead seeded by copy-pasting the plan's own typo'd string — a nuisance, not a leakage or safety defect. Should still be corrected before or during implementation for cleanliness and to avoid wasted debugging.

### D0/D1R/D1RQ arm fidelity — verified, no defect

- `resolve_rar_deterministic_extended(query: RARQuery) -> DeterministicRARTrace` (`uri_v1/turn/rar_deterministic.py:230`) matches the plan's described entry point and "unchanged" claim.
- `build_turn_frame(raw_text, attachments=None) -> TurnFrame` (`uri_v1/turn/turn_frame_builder.py:177`) matches the plan's D0 replay path.
- `D1RReference` (`scripts/m35_a2_8f_detector_d1r.py:346`) carries only `span, clause_text, coarse_type, recency_hint, negation_spans, mechanism` — confirms the plan's claim that detectors "never supply candidates, anchors, or binding authority."
- `RARDeterministicAnchor` (`uri_v1/turn/rar_contracts.py:103`) has exactly the five fields the plan's §2.3 admission rules reference (`exact_id`, `unique_title_match`, `deterministic_recency`, `current_attachment_id`, `selected_ui_id`) — the plan invents no field.
- The plan's self-disclosed limitation that D1R/D1RQ were already tuned against this same corpus, so the comparison "cannot claim independent detector generalization," is accurate and already stated in §1 — this is correctly self-aware, not a gap.

### Protected anchors and authorization — verified, no defect

- §4's in/out boundary correctly excludes `uri_v1/**`, `uri_core/**`, `uri_ui/**`, and all frozen S1/S2/S3/Batch A/A9 artifacts; it permits only new `scripts/m33_3_s4_*` and `tests/test_m33_3_s4_*` plus additive state/telemetry files.
- The plan's authorization anchor (starting HEAD `0caf3dd…`) matches the actual current branch history (`0caf3dd` = "M33.3 S3: re-audit correction, bounded repair, requalification, re-freeze", per repository log).
- Cross-plan state (`M33_3_CROSS_PLAN_STATE.md` §4) correctly lists S4 as `EXPERIMENT_REQUIRED; needs its own pre-audited plan`, gated on PG-5/PG-6, independent of S1's separate (not-yet-authorized) implementation status — no gate-ordering violation.

## Verdict

**BLOCKING_REPAIR_REQUIRED**

One blocking defect (F1: incomplete scorer-only field list, directly threatens the plan's own "zero scorer-field leakage" gate) and one non-blocking defect (F2: malformed `rar_contracts.py` hash string, cosmetic/typo, correct value already recorded elsewhere) were found. Per the plan's own §3 procedure ("A blocking finding returns the plan to draft; no code begins until accepted"), F1 must be repaired in the plan text before implementation may begin. F2 should be corrected in the same pass for cleanliness but does not by itself block implementation, since the correct value is independently verifiable and already recorded in `M33_3_CROSS_PLAN_STATE.md` §6.

No other blocking architecture or experiment-design defect was found against PG-5/PG-6, scorer isolation (beyond F1), D0/D1R/D1RQ arm fidelity, or protected-anchor/authorization boundaries.

## Unverifiable / out of scope for this pre-audit

- The plan's numeric telemetry budget cap (byte count / candidate cap for fail-closed behavior in §2.5) is left to implementation-time choice; this is a design-completeness note, not a defect, since §3 requires focused tests to exercise "budget fail-closed" explicitly.
- No runtime execution of the (not-yet-implemented) producer was possible or in scope; this audit is a static plan/contract-fidelity review only, as instructed.
