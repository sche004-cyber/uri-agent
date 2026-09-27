# M33.3 S4: independent implementation audit, bounded repair, and requalification

**Verdict:** `S4_AUDITED_REPAIRED_REQUALIFIED_SAFETY_GATE_FAILED_NOT_FROZEN`.
**Date:** 2026-09-27. **Auditor:** Claude Code, acting as independent auditor and bounded repairer under the User's S4 audit/repair task package.
**Baseline:** branch `m35-uri-v1-parallel-architecture`, HEAD `337aec2c9870fabc126c7a9f2f32197acad4a171` (verified before any edit).
**Independence disclosure:** this session did not write the S4 plan, producer, runner, tests, or implementation report. The repository does not record which agent authored commit `337aec2`, so this audit's independence from that author cannot be proven from repository evidence alone. The audit did not use the implementer's claims as evidence. It re-derived every claim from source, the frozen corpus, and fresh replays.

`S1_CLOSED_FROZEN: YES` · `S2_CLOSED_FROZEN: YES` · `S3_CLOSED_FROZEN: YES` · `S4_CLOSED_FROZEN: NO` · `M33_3_COMPLETE: NO` · `NEXT_SLICE_AUTHORIZED: NO`

## 1. Acceptance criteria (defined before inspection)

1. **Plan fidelity.** Implementation matches `M33_3_S4_OFFLINE_SOURCE_TO_CANDIDATE_PLAN.md` §2–§5 and stays inside its §4 file boundary.
2. **Producer correctness.** The producer uses only the four allowlisted input fields. It invents no candidate, fails closed on invalid or over-budget input, and admits anchors only on grounded, unique evidence. Each `RARQuery` it emits is valid for the single reference expression it carries (`rar_contracts.py` `RARQuery` docstring).
3. **Replay correctness.** The control and producer paths use the same candidate pool and the unchanged frozen resolver and detectors. The replay covers every arm, condition, and path. Decision fields are reproducible.
4. **Scorer attribution.** Scorer-only fields are read only after producer inputs are built. Classification is correct, and no wrong binding is counted as a success.
5. **Provenance.** Every candidate has an ID, source kind, locator, and authorization basis. Telemetry contains no raw text.
6. **Wrong bindings.** Each annotated wrong binding is reproduced and root-caused to one of: production logic, scorer, fixture annotation, replay plumbing, or a genuine unresolved boundary failure.
7. **Gate definition.** The §3 safety gate and structural gates are defined correctly, applied correctly, and measured rather than asserted.
8. **Protected anchors.** All eight protected SHA-256 anchors are unchanged before and after the work. No `uri_v1/**`, `uri_core/**`, `uri_ui/**`, or S1/S2/S3/Batch A/A9 file is edited.
9. **External validity.** Limits of D0/D1R/D1RQ and of the fixture inventory are stated.
10. **Closure rule.** S4 is `CLOSED_FROZEN` only if every frozen S4 gate genuinely passes. The User's instruction for this audit adds: if the safety gate still fails because of genuine behavior, S4 is not closed.

## 2. Independent findings

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| **A-F1** | Material (authority) | **A turn-scoped lexical anchor contaminated every span.** `project()` computed one `RARDeterministicAnchor` from the whole raw turn and attached it to the `RARQuery` of every detected span. `RARQuery` resolves *one* reference expression, and frozen RAR returns immediately at Level 0/1 for any anchor it receives. So spans that do not contain the anchoring ID or title still received certainty-tier bindings: `EXACT_ID` and `EXACT_TITLE` are `CERTAINTY` under D5 / `authority.classify_authority`. Examples: `NB-L-01` "the Q3 one" was bound to `Q2_budget_forecast.xlsx` via `EXACT_TITLE`, although the user said "not the Q3 one". `NB-A-02` "the notice period is" was bound to the lease PDF via `EXACT_TITLE`. `NB-A-04` "this", "that", and "the scanned contract" were bound via `EXACT_ID`. All 34 affected rows were `UNATTRIBUTED_DETECTOR_FIND`, so the scorer excluded them from wrong-binding counts. That is why the defect was invisible in the implementer's safety numbers. | **Repaired** (§4, R-1) |
| **A-F2** | Material (gate measurement) | The §3 structural gate "zero false `CONFIRMED` authority claim" was not measured. No telemetry field recorded authority class, and the aggregate had no gate block. The implementation report stated the structural gates only in prose. | **Repaired** (§4, R-2) |
| A-F3 | Design question | `CURRENT_ATTACHMENT` is a turn-level fact with no lexical tie to any span. Plan §2.3 defines its admission at turn level only, so choosing which spans receive it was not decidable from repository authority. | **User decision, 2026-09-27:** keep it turn-scoped. It is now measured and disclosed (§5, §8) |
| A-F4 | Non-blocking | The scorer ignores `acceptable_alternatives`. As a result, 8 rows (4 control, 4 producer, symmetric) are classified `MISSED_RESOLVABLE_CASE` although their abstention matches an acceptable alternative. This is conservative and safety-neutral: no annotated wrong binding has an acceptable alternative that would excuse it (verified for `NB-B-05` and `NB-H-06`). | Recorded; not changed |
| A-F5 | Non-blocking | The producer copies the harness convention `is_attachment = (representation == "file_reference_shape")`. Every file candidate is therefore marked as an attachment, not only files actually attached in the current turn. The control path does the same, so pool parity holds. The frozen RAR inferred-attachment path needs explicit attachment tokens in the span. | Recorded as a limitation |
| A-F6 | Confirmed correct | Input allowlist, fail-closed checks (duplicate, unknown, mismatched ID, 16-candidate cap, 16,384-byte cap), candidate parity between control and producer, the unauthorized-ID guard, and pre/post hash verification all behave as the plan requires. D1R/D1RQ spans never create candidates (`boundary_violation` guard). Provenance entries carry ID, `source_kind`, `fixture://` locator, and `variant_available_candidates` basis. Telemetry rows contain no raw text or `reason`. | Accepted |
| A-F7 | Confirmed correct | Scorer attribution for the two wrong-binding cases is correct: `find_matching_found_expr("that", ["that in an email"])` is the A2.8F containment precedent. The fixture annotations are consistent with the corpus `reason` fields. | Accepted |

## 3. Root cause of the two annotated wrong-binding cases

Both cases were reproduced directly with the frozen D1R/D1RQ detectors, the harness `build_candidate_pool`, and the unchanged `resolve_rar_deterministic_extended`, outside the S4 runner. They are identical on the control path, which has no producer and no anchors. The S4 producer delivers no anchor for either case (`anchor_origin: none`). Neither case is caused by S4 producer logic, scorer logic, fixture annotation, or replay plumbing.

**`NB-B-05:r1`**. Raw turn: "Perfect. Put that in an email to Priya please". Cells: D1R/D1RQ × C2, both paths.
- **Detector defect (frozen, protected).** The D1R/D1RQ noun-phrase scanner crosses the preposition "in". It emits the span "that in an email" and sets `coarse_type=email`. "an email" is the object the user wants created, not a reference.
- **RAR defect (frozen, A9-protected).** RAR Level 4b `TYPE_FILTER` finds exactly one `email` candidate in C2 (`obj-c06f97`, "Query on invoice INV-20417"). It binds that candidate with zero substantive evidence. At C1 no email exists, so the same rule abstains.
- **Prior record.** A2.8I independently found this failure and corrected its identity (§3 item 8; §5 row 6). A2.8J U5 root-caused it to the detector boundary error. The A2.8J S1 experimental gate closes it only in `rar_safe_experimental.py`, which has not been adopted.
- **Classification:** genuine unresolved boundary failure in frozen mechanisms.

**`NB-H-06:r1`**. Raw turn: "no, the other scan, the one from last week". Cells: D1R/D1RQ × C1, both paths.
- **Detector output.** The detector emits the span "the other scan" with negation spans ("no", "the other").
- **RAR defect (frozen, A9-protected).** At RAR Level 4a, the negation spans share no distinguishing token with `scan_0034.pdf`, so nothing is eliminated. The contrast shortcut ("other" with one remaining candidate) then returns `RESOLVED` with the only candidate. That is exactly the file the user excluded. The corpus `reason` field calls this "the worst outcome". At C2, term discrimination abstains correctly.
- **Prior record.** A2.8I §5 row 32 calls this "Known B". A2.8J S3 closes the shortcut only experimentally, and a residual persists at Level 4b whenever a type hint is present (A2.8J final audit, Probe A).
- **Classification:** genuine unresolved boundary failure in frozen mechanisms.

**Why S4 cannot repair these.** Plan §4 protects the detectors, frozen RAR, A9, and the corpus. Plan §3 says a disqualifying result "may be a valid experiment output, not a reason to change frozen RAR". Fixing either case needs a detector or RAR change, or the adoption of an A2.8J experimental layer. Each of those is outside S4 and needs its own authorization.

## 4. Repairs made

**R-1. Anchor scoping (`scripts/m33_3_s4_source_to_candidate.py`).** A new `_scope_to_reference()` runs after the unchanged turn-level admission and conflict check:
- `exact_id` is delivered to a span only when that span contains the anchored ID intact.
- `unique_title_match` is delivered only when the span contains that record's title intact. The match uses the same word-boundary, case-insensitive `_intact` test that admission uses.
- `current_attachment_id` stays turn-scoped, per the User decision on A-F3.
- When a turn anchor exists but no part of it applies to the span, the anchor is `None` and the new origin label is `turn_anchor_not_in_span`.

Admission rules, conflict suppression, the allowlist, and the budgets are unchanged. This follows directly from the `RARQuery` single-reference contract and the D5 rule that certainty authority must be tied to its anchor.

**R-2. Authority and gate measurement (`scripts/m33_3_s4_replay.py`).**
- Every resolved row now records `authority_class`, computed with the S1 frozen `classify_authority`. That code is imported read-only; its hash is `3393b5bb…02cd`, and the file is unchanged.
- Each group records `certainty_authority_rows`.
- The summary, now schema `m33.3.s4.offline_replay.v2`, has a computed `gates` block with these fields: candidate invention, protected hashes, `false_certainty_authority_on_scored_rows`, `certainty_authority_on_unattributed_rows`, wrong-binding rows and case IDs, `producer_only_wrong_binding_rows`, and `safety_gate_passed`.
- The runner now writes `M33_3_S4_R1_TELEMETRY.json` and `M33_3_S4_R1_AGGREGATES.json`. The implementer's `M33_3_S4_TELEMETRY.json` and `M33_3_S4_AGGREGATES.json` are kept unchanged as pre-repair evidence, as committed at `337aec2`.

**R-3. Tests (`tests/test_m33_3_s4_replay.py`, 6 → 8 tests).**
- New: a lexical anchor never reaches "it", "the other one", or "this" in a multi-span turn.
- New: the attachment anchor stays turn-scoped while its lexical title part is dropped.
- The corpus gate test now pins the exact wrong-binding set (`NB-B-05:r1`, `NB-H-06:r1`, 8 rows), zero producer-only wrong bindings, zero false certainty on scored rows, 8 disclosed attachment-certainty rows, and `safety_gate_passed is False`.
- It also asserts that `NB-L-01`'s extra spans no longer inherit the Q2 title anchor.

**Not changed:** the safety gate definition, the scorer classification rules, the corpus, detectors, RAR, A9, and every S1/S2/S3 artifact.

## 5. Requalification results (R1 replay)

- **Size.** 79 cases, 2,442 rows, 18 groups. Row count matches the pre-repair run.
- **Reproducibility.** A second in-process replay reproduced all decision fields bit-identically: case, arm, condition, path, ref, outcome, candidate, rule, anchor origin, authority, classification. Timings are wall-clock and not deterministic.
- **Pre/post delta.** Exactly 34 rows changed. All 34 are `UNATTRIBUTED_DETECTOR_FIND`: 18 lost `EXACT_TITLE` and 16 lost `EXACT_ID`, and each now takes the frozen heuristic path (`TERM_DISCRIMINATION`). No annotated row changed classification.

| Group (producer vs control) | Correct resolutions | Annotated wrong bindings | Certainty-class rows | Grounded-target coverage |
|---|---|---|---|---|
| D0 C1 | 1 vs 0 | 0 / 0 | 1 / 0 | 76/76 |
| D0 C2 | 1 vs 0 | 0 / 0 | 1 / 0 | 76/76 |
| D1R C1 | 18 vs 16 | 1 / 1 | 7 / 2 | 76/76 |
| D1R C2 | 11 vs 9 | 1 / 1 | 7 / 2 | 76/76 |
| D1RQ C1 | 24 vs 22 | 1 / 1 | 7 / 2 | 76/76 |
| D1RQ C2 | 15 vs 13 | 1 / 1 | 7 / 2 | 76/76 |

**Gates (computed):**
- Candidate invention and unauthorized source: 0.
- Protected hashes unchanged: true.
- `false_certainty_authority_on_scored_rows`: 0. Both wrong bindings are `HEURISTIC` rules (`TYPE_FILTER`, `CONTRAST_FILTER`).
- `certainty_authority_on_unattributed_rows`: 8. All 8 come from the turn-scoped attachment anchor in `NB-C-01` and `NB-C-02` under D1R/D1RQ × C1/C2. They include `NB-C-02` "the airport", bound to the receipt attachment with `CURRENT_ATTACHMENT`. These rows are disclosed exposure under the User's decision. Their semantic correctness is `UNMEASURED`.
- `annotated_wrong_binding_cases`: `NB-B-05:r1`, `NB-H-06:r1`, 8 rows.
- `producer_only_wrong_binding_rows`: 0.
- **`safety_gate_passed: false`.**

## 6. Regression and protected anchors

- **Protected anchors.** Before and after this work, `sha256sum` matched all eight runner anchors: corpus `0ea54473…7380`, `rar_deterministic.py` `e02af25b…b649`, `rar_contracts.py` `4cc9aa43…6819`, Batch A `06d0dfff…c3fa`, A9 resolver `90d89c37…f79c`, A9 fixtures `36570706…315a`, D1R `03479773…be75`, D1RQ `49f5faa9…6b82`. The runner also re-verified them before and after each replay. `git status` shows no change under `uri_v1/`, `uri_core/`, `uri_ui/`, or `fixtures/`.
- **Tests.** S1 (5 files), S2, S3 battery, S4 (8), A2.8A ARN, A2.8L A9, A2.8K L5, A2.5 RAR deterministic / adversarial / contracts / stage-4, and `tests/governance` gave **461 passed, 178 subtests passed**. A2.8B/A2.8C/A2.8K-R1 gave **22 passed**.
- **Governance validator.** `scripts/governance/uri_state_validator.py` returned `VALID`, no DCL violations, after the state update.

## 7. Governance and state updates

- `docs/plans/M33_3_S4_STATE.md`: state becomes `S4_AUDITED_REPAIRED_SAFETY_GATE_FAILED_NOT_FROZEN`. The history is kept.
- `docs/plans/M33_3_CROSS_PLAN_STATE.md`: header and §4 S4 row are updated additively. The implementer record is kept.
- `docs/governance/URI_STATE.yaml`: M33.3 status, `active_continuation` S4 fields, and the S4 `planning_artifacts` entry are updated additively. The previous notes stay as history.
- Prior reports are not edited. That includes the implementation report, the pre-audits, and the pre-repair telemetry and aggregates.

## 8. Remaining limitations

1. **Safety gate fails.** It fails on two genuine frozen-mechanism failures. S4 cannot be promoted, called safe, or frozen.
2. **Attachment anchor certainty.** The turn-scoped attachment anchor gives `CERTAINTY`-class authority to every detected span in a single-attachment turn, including non-referring detector spans such as "the airport". This is the User-accepted design for this offline experiment. It is not endorsed for production; any production source gateway must decide attachment scoping itself.
3. **External validity.** Coverage of 76/76 depends on the curated C1/C2 inventory and is not a live retrieval result. D1R/D1RQ were previously run on this corpus, so the producer's +1/+2 gains are within-corpus differences, not generalization evidence. Live session, file, Gmail, and Drive discovery; provider permissions; UI state (`selected_ui_id`); CPU/RAM cost; and model paths are all `UNMEASURED`. Timings are local, non-deterministic wall-clock microseconds with no governed threshold.
4. **Scorer and harness conventions.** A-F4 (acceptable alternatives ignored, conservative) and A-F5 (`is_attachment` covers every file) are harness conventions that S4 did not change.
5. **Unannotated spans.** 792 unannotated detector rows have no ground truth. Their semantic correctness remains `UNMEASURED`, although A-F1 removed the certainty contamination among them.

## 9. Self-review against §1

- **Criterion 1: met.** Only `scripts/m33_3_s4_*`, `tests/test_m33_3_s4_*`, S4 telemetry, reports, and state files changed.
- **Criteria 2–3: met after R-1.** The replay was reproduced.
- **Criteria 4–5: met.** A-F4 is disclosed.
- **Criterion 6: met.** Both failures were reproduced outside the runner and match independent prior audits. Their causes lie in frozen detector and RAR code, not in S4.
- **Criterion 7: met after R-2.** The gate was neither weakened nor reinterpreted, and it still fails.
- **Criterion 8: met.**
- **Criterion 9: met** (§8).
- **Criterion 10:** S4 is not closed.
- **Unsupported claims check.** The authorship of commit `337aec2` is unverifiable (see the independence disclosure). This does not affect the verdict, because every conclusion was re-derived from primary evidence.
