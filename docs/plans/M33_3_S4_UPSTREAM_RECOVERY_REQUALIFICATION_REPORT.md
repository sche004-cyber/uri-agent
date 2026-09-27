# M33.3 S4: upstream detector/RAR recovery and requalification (implementer recovery candidate)

**Verdict:** `S4_RECOVERY_CANDIDATE_REQUALIFIED_AWAITING_INDEPENDENT_AUDIT`.
**Date:** 2026-09-27. **Role:** Claude Code as implementer of the User's "M33.3 S4 Bounded Recovery Batch" (User Option B: repair the upstream detector/RAR failures and requalify before S4 may close).
**Baseline:** worktree `C:\Users\cheta\Development\Uri_V1`, branch `m35-uri-v1-parallel-architecture`, HEAD `851c521fe1f164d11d7750fdc0bdd332e0668e47`, equal to `origin/m35-uri-v1-parallel-architecture` after `git fetch` (verified before any edit).

**This is not an independent audit.** Every S1–S4 closure in M33.3 passed an independent audit before `CLOSED_FROZEN`. This batch therefore stops at a recovery candidate. The same agent family (Claude Code) wrote the prior S4 audit report and this repair, so the next S4 audit should be performed by a different agent/session. Section 8 is an implementer self-review only.

`S1_CLOSED_FROZEN: YES` · `S2_CLOSED_FROZEN: YES` · `S3_CLOSED_FROZEN: YES` · `S4_CLOSED_FROZEN: NO` · `M33_3_COMPLETE: NO` · `NEXT_SLICE_AUTHORIZED: NO`

## 1. Acceptance criteria (defined before any edit)

1. Both failures reproduce on the unchanged baseline, with the detector, RAR, and control-path behaviour traced.
2. The repair is a general mechanism change in the detector and/or RAR. It contains no fixture IDs, no benchmark sentences, no gold-label edits, and no threshold change.
3. Every legitimate "other"/exclusion binding and every correct resolution on every available corpus is preserved, or any loss is disclosed.
4. Every consumer of the changed code is requalified: RAR fixture corpora, A9, L5, RAR-SAFE, S1–S3, ARN, Batch A deterministic rung, and governance.
5. The full S4 battery is rerun in fresh processes, is deterministic, and computes its gates in the aggregate schema.
6. The frozen S4 safety gate passes with no producer-only wrong binding, and A-F1/A-F2 stay repaired.
7. Non-target protected anchors are byte-identical. Every target anchor change is explained.
8. Governance validates. State records a candidate awaiting independent audit, not a freeze.

## 2. Pre-repair reproduction (baseline code, outside the S4 runner)

Reproduced with the frozen D1R/D1RQ detectors, `build_candidate_pool(oracle_recency=False)`, and `resolve_rar_deterministic_extended`. The control path (no producer, no anchor) gives the same result, so the S4 producer is not involved.

**`NB-B-05:r1`** — "Perfect. Put that in an email to Priya please".
- Detector (D1R and D1RQ): one span, `"that in an email"`, `coarse_type=email`, mechanism `determiner_noun_phrase`. The NP scanner treats "that" as a determiner and keeps scanning because "in" and "an" are not stop words. `_type_hint_for_phrase` then takes the last type word, "email".
- RAR: C1 has no email, so Level 4b returns `UNKNOWN` (`TYPE_FILTER`). C2 has one email (`obj-c06f97`), so Level 4b binds it: `RESOLVED`, `TYPE_FILTER`. The query has no other substantive token.
- Root cause: **detector boundary defect** (span crosses a preposition, so a destination type word becomes reference evidence). RAR 4b behaves as designed on the type evidence it is given. This is an interaction; the defect originates in the detector.

**`NB-H-06:r1`** — "no, the other scan, the one from last week".
- Detector: span `"the other scan"`, `negation_spans=("no", "the other")`, `recency_hint="earlier"`, `coarse_type=None`.
- RAR C1 (one candidate, `scan_0034.pdf`): Level 4a finds no distinguishing overlap between the negation spans and the candidate, so nothing is eliminated. The contrast shortcut then fires on pool size alone (`len(candidates_list) == 1`) and returns `RESOLVED`, `CONTRAST_FILTER`, with the scan the user just rejected. C2 abstains (`TERM_DISCRIMINATION`).
- Root cause: **RAR defect**. The shortcut assumes the survivor of an exclusion, but it never checks that an exclusion happened.

The prior records (A2.8I §5; A2.8J S1/S3; the S4 audit §3) match this reproduction.

## 3. Repair

| File | Change |
|---|---|
| `scripts/m35_a2_8f_detector_d1r.py` | `_NP_STOP_WORDS` gains `_NP_PREPOSITION_STOPS` |
| `scripts/m35_a2_8h_detector_d1rq.py` | Same change (D1RQ is a fork of D1R) |
| `uri_v1/turn/rar_deterministic.py` | RC-5: the Level 4a contrast shortcut needs `eliminated_ids` to be non-empty |

**Detector mechanism.** A determiner noun phrase never extends across a preposition. The existing stop set already stopped at `to/for/with/by/from/about/of/under/into`. The repair adds the rest of the same closed class of locative, medium, and path prepositions: `in, on, at, onto, via, inside, within, without, through, across, between, among, around, during, against, per`. Temporal prepositions (`before/after/since/until`) are deliberately excluded, because "the one before" is an ordinal reference. The existing bare-pronoun path then handles "that" with no type.

**RAR mechanism (RC-5).** "The other X" names the survivor of an exclusion, so the shortcut fires only when Level 4a removed at least one candidate (by distinguishing-term negation or a structural `rejected_in_turn` tag). Otherwise the cascade continues and later levels must justify any binding. For `NB-H-06` C1, Level 6 then returns `UNKNOWN` (absent entity: "other" matches no candidate).

**Why it is general.**
- No case ID, sentence, or candidate is named in code.
- The detector change completes an existing closed word class.
- RC-5 is the A2.8J S3 invariant applied at the one point where it was missing.
- Focused tests use new sentences and pools, not the benchmark (§6).

**Deliberately untouched.**
- Level 4b singleton type binding on zero substantive evidence (A2.8J S1). It is over-broad per the A2.8J bounded re-audit, and the detector repair removes the evidence path that `NB-B-05` used.
- Level 5 temporal commits (A2.8J S2).
- The D1R/D1RQ possessive-body scanner.
- Recency wiring, RAR-SAFE adoption, the A9/L5 forks, the scorer (A-F4), attachment identity (A-F5), the attachment anchor scope (A-F3, User decision), the corpus, and gold labels.

## 4. Affected-layer requalification

**Dependency scan.** RAR consumers: S1 `binding.py`/`bundle.py`, the A9 and L5 forks (which call baseline RAR), RAR-SAFE, `lfm_*` runtimes, Batch A `run_det`, and the A2.5/A2.8x harnesses. The D1R/D1RQ detectors are consumed by S4 and the A2.8F/H/J/K/L harnesses.

**Behaviour sweep.** Every RAR call and detector call was recorded before and after the change.
- Sources: every RAR fixture corpus (diagnostic 24, adversarial 24, challenge 100, stage-3, stage-4b, L5 diagnostic, A9 factorial) and the natural-boundary corpus (D0/D1R/D1RQ spans × C1/C2 × `oracle_recency` False/True).
- Sources (continued): Batch A inputs with their entity pools, and all edge-benchmark and ARN battery text (538 distinct utterances).
- **RAR:** 1,054 → 1,057 distinct queries. Of the 1,031 shared queries, exactly **1** changed: `"the other scan"` at NB-H-06 C1 (`RESOLVED` → `UNKNOWN`).
- **Positive contrast bindings:** all 21 other legitimate `CONTRAST_FILTER` bindings are identical. Examples: "the other mockup" after "Not the dark theme mockup", "the other one" after "Option A", and "the warden" after "Don't notify the registrar".
- **Detectors:** 29 of 538 utterances changed in D1R, and the same 29 in D1RQ. Six of the 29 are S4-corpus utterances and 23 come from other corpora. Every change stops a span at a preposition, for example:
  - "the liability clause in the contract" → "the liability clause" + "the contract"
  - "the formulas in the same spreadsheet" (type `spreadsheet`) → "the formulas" + "the same spreadsheet" (`spreadsheet`)
  - "this document on the department network printer" → "this document" + "the department network printer"
  - "that in an email" (`email`) → "that" (none)

  One cosmetic side-effect: "The key is in the box" now yields "The key is" + "the box" (a copula already inside a span before the repair).

**A2.8K-R2 L5 battery (3,655 rows).** Factorial run with old/new RAR × old/new detectors, H0 totals:

| Arm | Correct | ICB | Missed | Correct abstention |
|---|---|---|---|---|
| old RAR, old detector | 160 | 26 | 175 | 165 |
| new RAR only | 160 | 24 | 175 | 167 |
| new detector only | 160 | 24 | 177 | 165 |
| **both** | **160** | **22** | **177** | **167** |

Across all variants, 14 rows moved from `INCORRECT_CONFIDENT_BINDING` to a non-binding class. **0 rows became a wrong binding, and 0 correct resolutions were lost.** Changed rows are confined to NB-B-05, NB-H-06, NB-C-04, and NB-J-04; the latter two change only their span or failure class.

**Batch A deterministic rung (`run_det`).** The RAW/D0/SEG summary is identical before and after. The Batch A `reproduce_g_r2` check now reports `REPRODUCTION_BASELINE_UNMATCHED`. The reason: the accepted A2.8K-R2 aggregates were produced on RAR `e02af25b`, and the reproduced H0 is the improved 22-ICB row above. The Batch A `EVIDENCE_PINS` still name `e02af25b` as historical baseline evidence and were not edited, so a Batch A rerun would report `EVIDENCE_DRIFT` for `rar_deterministic.py` by design.

**Test suites** (all tracked `tests/` plus tracked root `test_m35*.py`):
- Clean baseline before any edit: **607 passed, 178 subtests passed, 0 failed, 0 skipped.**
- After the code change, before re-pinning: 603 passed, 4 failed. All 4 are hash pins on the intentionally changed files: S1 governance/parity, S1 KB4, S2 protected hashes, and the S4 runner anchor. Every behavioural S1/S2/S3/A2.5/A9/L5/ARN test passed.
- Final: **624 passed, 178 subtests passed, 0 failed** (607 plus 17 new focused tests).
- The prior audit's focused set (S1 ×5, S2, S3, S4, recovery tests, A2.8A, A2.8L, A2.8K, A2.5 ×4, governance, A2.8B/C/K-R1): **500 passed, 178 subtests.**

## 5. S4 rerun and gates (R2)

- **Size.** 79 cases, **2,466 rows** (R1: 2,442), 18 groups. The +24 rows are new unattributed spans in NB-B-01 and NB-C-04, split at a preposition. All 24 are `UNKNOWN`, with no new binding.
- **Reproducibility.** Three fresh-process replays (two scratch runs and the `--write` run) are identical on every decision field: case, arm, condition, path, ref, outcome, candidate, ambiguous IDs, rule, anchor origin, authority, classification, expected, sources, provenance, bytes, and coverage. Timings are wall-clock and excluded.
- **Scored rows (1,512, same keys as R1).** Exactly 12 changed:
  - NB-B-05 C2 (D1R/D1RQ × control/producer): `INCORRECT_CONFIDENT_BINDING` → `MISSED_RESOLVABLE_CASE` (`AMBIGUOUS`).
  - NB-H-06 C1 (same four cells): `INCORRECT_CONFIDENT_BINDING` → `CORRECT_ABSTENTION` (`UNKNOWN`).
  - NB-B-05 C1 (same four cells): `UNKNOWN` → `AMBIGUOUS`, still a miss.
- **Coverage.** Correct resolutions are 130 → 130. Grounded-target coverage stays 76/76 per non-C3 group.
- **Control vs producer.** Identical changes on both paths. The producer still gains +1/+2 correct resolutions per D1R/D1RQ group, as in R1.

| Gate (computed in `M33_3_S4_R2_AGGREGATES.json`, schema `m33.3.s4.offline_replay.v3`) | Value |
|---|---|
| `candidate_invention_or_unauthorized_source` | 0 |
| `protected_hashes_unchanged` (pre/post replay) | true |
| `annotated_wrong_binding_rows` / `_cases` | **0** / `[]` (R1: 8 / NB-B-05:r1, NB-H-06:r1) |
| `producer_only_wrong_binding_rows` | 0 |
| `false_certainty_authority_on_scored_rows` | 0 |
| `certainty_authority_on_unattributed_rows` | 8 |
| `attachment_anchor_certainty_rows` / unattributed / cases | 18 / 8 / NB-C-01, NB-C-02 |
| **`safety_gate_passed`** | **true** |

**Other checks.**
- All 30 certainty-class rows on scored references are `CORRECT_RESOLUTION`.
- Lexical (`exact_id`/`unique_title`) anchors applied outside their span: 0, so A-F1 holds.
- Authority class is computed for every resolved row by S1 `classify_authority` (`authority.py` is unchanged, `3393b5bb…`), so A-F2 holds.
- R1 and pre-repair telemetry and aggregates are unchanged.

## 6. Protected anchors

| Anchor (S4 runner set of 8) | Before | After |
|---|---|---|
| natural-boundary corpus | `0ea54473…7380` | unchanged |
| `rar_contracts.py` | `4cc9aa43…6819` | unchanged |
| Batch A battery | `06d0dfff…c3fa` | unchanged |
| A9 resolver | `90d89c37…f79c` | unchanged |
| A9 fixtures | `36570706…315a` | unchanged |
| `rar_deterministic.py` | `e02af25b…b649` | **`4db77566…1b95`** (RC-5) |
| D1R | `03479773…be75` | **`0986503d…c8b3`** (preposition stops) |
| D1RQ | `49f5faa9…6b82` | **`42332d28…0862`** (preposition stops) |

The three target changes are exactly the diffs in §3. The pre-repair bytes of D1R and D1RQ were reconstructed by reversing the inserted block and re-hash to the old anchors exactly.

The `rar_deterministic.py` pin was updated in three frozen S1/S2 test files, each with a comment naming the pre-recovery hash:
- `tests/test_m33_3_s1_governance_and_parity.py`
- `tests/test_m33_3_s1_repair.py`
- `tests/test_m33_3_s2_wrong_binding_impact.py`

No other line of those files changed. S1 `authority.py` and the RAR-SAFE, L5, and A9 modules are unchanged.

**Governance items for the independent auditor.**
- Cross-plan gate **PG-6** pins `rar_deterministic.py` at `e02af25b`. This batch re-pins it to `4db77566` under the User's Option B authorization, and the cross-plan state records the change additively. The auditor should confirm that this re-pin is within that authorization.
- `scripts/m35_a2_8f_detector_d1r.py` was untracked at `851c521`, although S4 imports it and anchors its hash. It is committed in two commits: first at its exact pre-repair bytes (`03479773…`, unmodified evidence), then with the repair, so the repair diff is auditable.
- `scripts/m35_a2_8f_run.py` (imported by S4, unmodified) remains untracked. This is a pre-existing reproducibility gap, disclosed and not absorbed.

**Governance validator.** `scripts/governance/uri_state_validator.py` returns `VALID` after the state updates.

## 7. Focused tests (`tests/test_m33_3_s4_upstream_recovery.py`, 17)

- **Destination type words never become reference evidence**, both detectors: "in an email", "in a spreadsheet", "on a file share", "via an email link".
- **Spans stop at prepositions and keep their own type**: "the pdf in the email" → "the pdf" (`pdf`).
- **Ordinal and existing boundaries are preserved**: "the one before", "the report", and a long plain NP.
- **Contrast without demonstrated exclusion never binds the only candidate**: three phrasings.
- **Contrast after a real exclusion still binds the survivor**: this is `CONTRAST_FILTER`.
- **A structural `rejected_in_turn` tag counts as a demonstrated exclusion.**

Falsification: against the pre-repair code, **11 of the 17 fail** (every defect test except "via an email link", which is a control) and the 6 preservation tests pass. After the repair, all 17 pass. The S4 gate test now pins `safety_gate_passed is True`, 2,466 rows, and the attachment-anchor counts. It also asserts that no NB-B-05/NB-H-06 D1R/D1RQ C1/C2 row resolves.

## 8. IMPLEMENTER SELF-REVIEW (not an independent audit)

**Falsification attempts and results.**

1. *Is `NB-B-05` genuinely fixed, or only moved?* The C2 row is now `AMBIGUOUS` between two candidates, with no binding and no certainty. The fix removes the type evidence. It does not suppress 4b, which still binds legitimate singleton type references. The Level 4b zero-evidence path itself remains, and a detector that emits a type word it should not would re-expose it. Disclosed as residual R-1.
2. *Is `NB-H-06` genuinely fixed?* At C1 the shortcut no longer fires, and Level 6 abstains. With `oracle_recency=True` and real ranks, Level 5 "earlier" can still bind an older scan. That binding needs a rank that production never supplies (A2.8J Known A), and RC-5 does not claim to fix it. Disclosed as residual R-2.
3. *Beyond the benchmark?* Yes. 11 new-sentence tests fail on old code. Of the 29 changed utterances, 23 come from corpora other than the S4 corpus. The 6 S4-corpus utterances are NB-B-01, NB-B-05, NB-C-04, NB-I-05, NB-J-03, and NB-J-04; only NB-B-05 changes a scored outcome. The L5 battery changes 14 rows, not 2.
4. *Valid positive cases preserved?* Yes: all 21 legitimate contrast bindings, 160/160 L5 correct, 130/130 S4 correct, and Batch A `run_det` identical.
5. *Exclusions preserved?* Negation elimination is unchanged. RC-5 only removes a binding path.
6. *Gates weakened, or annotations or corpus changed?* No. The scorer, gate formula, corpus hash `0ea54473…`, and gold labels are unchanged. Gates are computed, not asserted.
7. *A-F1/A-F2 regressed?* No (§5).
8. *Producer-only wrong bindings?* 0.
9. *Unexplained hash changes?* None (§6).
10. *Unrelated behaviour changed?* Detector span splitting changes unannotated spans. It adds 24 unattributed `UNKNOWN` rows and changes no binding. `SKILL.md` (pre-existing user modification) and all other untracked user files are untouched.

**Fixture-specificity.** Low. There is no literal "in an email", "other scan", or case ID in the code, and the stop set is a closed word class.

**Remaining limitations and residuals.**
- R-1: RAR Level 4b can bind a singleton type match on zero substantive evidence (A2.8J S1, not adopted).
- R-2: Level 5 temporal commits without a contradiction gate (A2.8J S2/Known A) once real recency ranks exist.
- R-3: D1R possessive bodies have no preposition stop. "X's copy in email" could still carry an email type. Not exercised by the corpus.
- R-4: A-F4 (acceptable alternatives ignored) and A-F5 (all files marked `is_attachment`) are unchanged.
- R-5: Semantic correctness of 816 unattributed rows is `UNMEASURED`. External validity is as stated in the S4 audit §8.3.

**Attachment-anchor limitation (A-F3).** The turn-scoped attachment anchor still gives `CERTAINTY` to every detected span in a single-attachment turn. That is 18 rows in total: 10 scored rows, all correct, and 8 unattributed rows, for example NB-C-02 "the airport" bound to the receipt. This is the User-accepted experimental design for S4 only. **Turn-wide attachment certainty is not production-approved**, and any production source gateway must scope it itself.

## 9. Governance and state

- S1 `CLOSED_FROZEN`; S2 `CLOSED_FROZEN`; S3 `CLOSED_FROZEN`.
- **S4 `S4_RECOVERY_CANDIDATE_REQUALIFIED_AWAITING_INDEPENDENT_AUDIT`**. It is not closed and not frozen. `S4_SAFETY_GATE_PASSED` is YES at the implementer level only.
- M33.3 is incomplete. `NEXT_SLICE_AUTHORIZED: NO`.
- Permitted continuation: an independent S4 audit (reproduction plus audit) by an agent other than this session. S4 freeze is conditional on that audit. S5–S13, INT events, URI-RAR adoption, and production use of the changed detector/RAR remain unauthorized.

Updated additively (history preserved): `docs/plans/M33_3_S4_STATE.md`, `docs/plans/M33_3_CROSS_PLAN_STATE.md` (header, S4 row, PG-6), and `docs/governance/URI_STATE.yaml` (M33.3 status/history, `active_continuation`, S4 planning artifact).
