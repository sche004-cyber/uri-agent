# M35 URIv1 — A2.8J: RAR-SAFE Evidence-Safety Hardening Qualification — Execution Report

**Type:** Experimental qualification only. No production integration, no recency wiring, no T2 detection, no Known C/D repair, no modification to `rar_deterministic.py`/`rar_contracts.py`/D1RQ. No commit, no push.
**Implementer:** Claude Sonnet (routing substituted from Codex per explicit User directive, Codex quota unavailable this batch — `docs/plans/M35_URIV1_A2_8J_STATE.md`).
**Governing plan:** `docs/plans/M35_URIV1_A2_8J_RAR_SAFE_QUALIFICATION_PLAN.md`.
**Status:** `VERIFICATION_READY` (repaired — see `docs/plans/M35_URIV1_A2_8J_REPAIR_REPORT.md` and the **R3(a) REPAIR ADDENDUM** at the end of this document)

> **Correction notice (auditable correction history — not a silent overwrite):** the independent final audit (`docs/plans/M35_URIV1_A2_8J_INDEPENDENT_FINAL_AUDIT.md`) found this report's §2, §6, §12, and §15 item 2 incomplete or factually wrong, and found 3 factual slips (§1, §3.2's recency-word count, §11). The body below is preserved exactly as originally written for history. Corrected figures, corrected classification, and the post-repair measurement set are in the **R3(a) REPAIR ADDENDUM** section at the end of this document, which supersedes the conflicting original text. Do not read §2/§6/§12/§15 item 2 below as current without reading the addendum.

---

## Acceptance criteria (restated from the accepted plan §6, checked against evidence in this report)

1. `rar_deterministic.py`, `rar_contracts.py`, D1RQ byte-unmodified → §4 (SHA-256 identity, unchanged pre/post run).
2. RAR-SAFE isolated, existing RAR unchanged and reachable → §3, §4.
3. All five existing RAR test files pass unchanged → §12.
4. Full 79-case corpus, both variants, all three C-conditions, per-level before/after → §5, §9.
5. All three counterfactual batteries executed → §6, §7, §8.
6. Every RAR-SAFE `RESOLVED` answers the 7 mechanical questions → §10.
7. Every coverage loss individually audited → §11.
8. `UNMEASURED` used where genuinely not measured, no fabricated figures → §13, §14, §15.
9. All 7 next-step questions answered → §17.
10. No commit, no push, stop at `VERIFICATION_READY` → this document's own header/footer.

---

## 1. Evidence recovered and verified

All evidence in the A2.8J plan (§0/§1) was independently re-verified against live repository state before implementation, not trusted from prompt text:

- `uri_v1/turn/rar_deterministic.py::resolve_rar_deterministic_extended` was read in full (956 lines). The 7-level cascade table in the plan (Levels 0–7, line ranges) was checked line-by-line against the actual file and confirmed accurate.
- `uri_v1/turn/rar_contracts.py` was read in full; `RARQuery`/`RAREvidence`/`RARCandidate`/`RARDeterministicAnchor`/`RARResolution`/`validate_rar_resolution` confirmed as the exact contract surface RAR-SAFE must reuse unmodified.
- `scripts/m35_a2_8h_detector_d1rq.py` (D1RQ) was read in full; confirmed it outputs presence/span/coarse-type/recency-hint/scoped-negation only — never a candidate ID or resolution decision, consistent with the frozen boundary this batch must respect.
- `scripts/m35_rar_natural_boundary_harness.py` and `scripts/m35_a2_8h_run.py` were read in full to recover the exact harness methodology (S1 query construction, `build_candidate_pool` with `oracle_recency=False`/`True`, the boundary-violation check, the scoring taxonomy) — this batch's battery scripts are direct, narrower forks of `m35_a2_8h_run.py` (same corpus, same D1RQ detector, same C1/C2/C3 conditions; the RESOLVER axis replaces A2.8H's DETECTOR axis).
- `docs/plans/M35_URIV1_A2_8I_POST_REPAIR_END_TO_END_RESIDUAL_AUDIT.md` was read for the corrected identity of the two named hazards: the one C2 `INCORRECT_CONFIDENT_BINDING` is `NB-B-05:r1` (not `NB-H-06`, which is `CORRECT_ABSTENTION` at C2); `NB-A-04`'s block is a span-prefix issue, not an identifier-system mismatch (neither correction affects this batch's scope, but both are carried forward per the plan).
- The raw corpus text for `NB-H-06`, `NB-B-05`, `NB-G-04`, `NB-D-01`, `NB-D-07`, `NB-L-06` and the 7 T2 case:refs was read directly from `uri_v1/turn/rar_natural_boundary_raw_turn_fixtures.json` before writing the counterfactual probes, so probe construction is grounded in the actual corpus, not reconstructed from memory of prior reports.
- SHA-256 identity of the three frozen files was independently recomputed and matches the A2.8I audit's own recorded values exactly (§4), confirming no drift occurred between A2.8I and this batch.

**Baseline reconfirmed by this batch's own battery run** (not merely cited): the D1RQ + existing-RAR C1/C2 resolution-coverage figures reproduced by `scripts/m35_a2_8j_rar_safe_battery.py` (**22/84 = 26.19%** at C1 [corrected: originally mistyped "26/84"; the independent final audit and A2.8I both confirm 22/84], 13/84 = **15.48%** at C2, n=84 ground-truth-bearing rows) are bit-identical to A2.8H's own claims and A2.8I's independent re-derivation of them — an independent third confirmation of the same baseline, using a freshly-written, independently-authored runner.

---

## 2. Hypothesis verification

The plan's hypothesis (§2): RAR's cascade lacks a single evidence-sufficiency invariant, unifying Known A (latent), Known B (active), New G (active), New F (latent) into: *"No level may commit a binding that the resolver's own Level-6 lexical/absent-entity evidence contradicts, and no binding may be committed on zero substantive evidence."*

**Verified, with a disclosed scope boundary.** The three concrete patches (S1/S2/S3) mandated by the governing task target exactly three commit points (Level 4b singleton, Level 5's four temporal single-match branches, Level 4a's contrast shortcut) — not every commit point in the cascade. Empirical testing (§7 Probe A) found at least one additional commit point where the *literal* unified invariant is violated but which the task's S1/S2/S3 patches do not reach: Level 5's own zero-substantive-evidence temporal binding (`NB-C-04`, "the attachment" → `target_type_hint="image"`, `"attachment"` is itself in `GENERIC_TYPE_WORDS`, leaving zero substantive tokens — Level 5 binds on recency alone with no S1-equivalent gate). This is reported honestly as a **residual, out of the task's literal S1/S2/S3 scope** (§15), not silently patched — the task explicitly scoped S1 to Level 4b only. The hypothesis that a *unifying* invariant *can in principle* be stated is supported; the finding that the three prescribed patches do not yet make the resolver fully compliant with the invariant's own text is now itself new evidence, disclosed rather than hidden.

Within the scoped S1/S2/S3 patches, the three named target hazards were directly and individually confirmed fixed by construction (not merely by aggregate count) — see the isolated before/after traces in §3 and §11.

---

## 3. Exact invariant implemented in RAR-SAFE

File: [`uri_v1/turn/rar_safe_experimental.py`](../../uri_v1/turn/rar_safe_experimental.py) (new, 490 lines). Exposes `resolve_rar_safe_experimental(query: RARQuery) -> DeterministicRARTrace`, using the same `RARQuery`/`RAREvidence`/`RARCandidate`/`RARDeterministicAnchor`/`DeterministicRARTrace` types imported directly from `rar_contracts.py`/`rar_deterministic.py` (not re-declared) — a drop-in substitute for `resolve_rar_deterministic_extended` in any harness.

**S1 (Level 4b, zero-substantive-evidence binding).** Previously: a singleton type match bound unconditionally when the query's substantive-token list was empty (the safety check was skipped entirely, not merely passed). RAR-SAFE: when `substantive_query_tokens` is empty, the singleton match is **not** bound; the pool is narrowed to the type-matched subset (identical to the existing multi-match branch) and the cascade continues. Verified directly (§3.1 below) against a reconstruction of `NB-B-05:r1`'s exact C2 shape.

**S2 (Level 5, commit against contradictory lexical evidence).** A new reusable function, `level6_would_contradict_binding(ref_tokens, target_type, winner, pool)`, extracts Level 6's own existing absent-entity/lexical-overlap mechanism (not a new scoring system — reuses `clean_tokens`, `STOPWORDS`, `GENERIC_TYPE_WORDS`, `PRONOUNS` imported unmodified from `rar_deterministic.py`). It returns `True` when the query's substantive tokens (excluding a small closed recency-word set — see §3.2 note) are either absent from the whole candidate pool, or present in the pool but on some *other* candidate rather than the one about to be bound. All four Level 5 single-match commit points (revised / previous / earlier / latest-current) now call this gate before returning `RESOLVED`; on contradiction, execution falls through to the next cascade stage exactly as if the temporal hint had not matched — the cascade order itself is never changed.

**S3 (Level 4a, contrast/exclusion must demonstrate actual exclusion).** Previously: the "the other"/"another" shortcut fired whenever the post-elimination pool had exactly one member, even if elimination removed nothing. RAR-SAFE adds one condition, `and eliminated_ids` (non-empty), to the existing pool-size check — no string-literal special-casing of "the other" was added or removed.

### 3.1 S1 direct verification (construction matching `NB-B-05:r1`'s real C2 shape)

```
Query: "that in an email", target_type_hint="email", pool={record, report, email}
OLD (resolve_rar_deterministic_extended): RESOLVED → obj-email1  (TYPE_FILTER)   [unsafe]
SAFE (resolve_rar_safe_experimental):      UNKNOWN  → None        (TERM_DISCRIMINATION/PRONOUN_BINDING)
```

### 3.2 S3 direct verification (construction matching `NB-H-06`'s "nothing eliminated" shape)

```
Query: "the other one", recency_hint="other", negation_spans=("no, not that",), pool={one PDF, no lexical overlap with negation span}
OLD:  RESOLVED → the sole (excluded) candidate   (CONTRAST_FILTER)   [unsafe]
SAFE: UNKNOWN  → None                             (TERM_DISCRIMINATION)
```

### 3.3 S2 direct verification (recency-vs-lexical-contradiction shape)

```
Query: "the earlier agenda", recency_hint="earlier", pool={Board_minutes_Sep (rank 0), Board_minutes_Aug (rank 1)}
OLD:  RESOLVED → Board_minutes_Aug   (TEMPORAL_RELATION)   [the query's own word "agenda" is absent from BOTH candidates -- Level 6 would flag absent-entity, but Level 5 bound first]
SAFE: UNKNOWN  → None                 (falls through; Level 6 confirms "agenda" absent from pool → NO_CANDIDATE)
```

**Recency-word exclusion note (S2), original (pre-repair):** `level6_would_contradict_binding` excluded a closed 9-word recency vocabulary [corrected: originally miscounted as "8-word"] (`previous, revised, original, latest, current, earlier, earliest, same, other`) from its substantive-token computation. This is necessary and disclosed: Level 6 never sees these words in any existing production trace (Level 5 always intercepts first), so treating them as entity-discriminating tokens inside the new gate would make it fire on nearly every temporal reference regardless of correctness.

**Superseded claim, flagged by the independent final audit:** the sentence "this is not new vocabulary — it is the closed set of literal recency values `rar_deterministic.py`'s own RC-1 docstring and `RAREvidence.recency_hint` already define" was **inaccurate**. `rar_deterministic.py` already defines two further non-entity-discriminating word sets this original 9-word set did not draw from: `classify_unresolved_failure`'s `revision_words` (line 196: `revised, revision, draft, original, version, v1, v2`) and `temporal_words` (line 201: `previous, earlier, latest, first, last, prior`), plus Level 5.5's `_ATTACHMENT_TRIGGER_TOKENS` (line 711: `attached, attachment, attaches`). Words such as `version` and `draft` were consequently treated as substantive, causing S2 to falsely flag correct bindings like "the earlier version" and "the revised draft" as lexically contradicted. See the **R3(a) REPAIR ADDENDUM** for the corrected vocabulary and its measured effect.

---

## 4. Diff boundaries (frozen-scope verification)

| File | Status | SHA-256 (this session) | SHA-256 (A2.8I audit, prior session) | Match |
|---|---|---|---|---|
| `uri_v1/turn/rar_deterministic.py` | Untouched | `e02af25bb7009d12d829c8b8fc92e487d3da75aeaa160092db617458278fb649` | same | ✅ |
| `uri_v1/turn/rar_contracts.py` | Untouched | `4cc9aa43726a870ca2e9ab1b19f6bf9d72dcb74c8a2818856776af95195b6819` | same | ✅ |
| `scripts/m35_a2_8h_detector_d1rq.py` | Untouched | `49f5faa9b37051fec876f5523383b4e965422976562c52e12fc38c970bfa6b82` | same | ✅ |
| `uri_v1/turn/rar_natural_boundary_raw_turn_fixtures.json` (corpus) | Untouched | `0ea5447354481041181538244ef70b6dc58a72267dd95263d61dbdb55ab07380` | same | ✅ (also matches A2.8H's own pre/post hash) |

Hashes recomputed a second time *after* the full battery + counterfactual + pytest run (§12) to confirm nothing was mutated during execution — identical.

`git status --porcelain` on all four paths shows only pre-existing `??` (untracked, as recorded by A2.8I — the whole `uri_v1/` tree and `scripts/m35_*` files are untracked in this worktree, git history does not attest to them; SHA-256 identity is the correct verification method here, exactly as A2.8I established).

**Files created this batch (all new, none pre-existing):**
- `uri_v1/turn/rar_safe_experimental.py`
- `scripts/m35_a2_8j_rar_safe_battery.py`
- `scripts/m35_a2_8j_counterfactual_battery.py`
- `docs/plans/M35_URIV1_A2_8J_TELEMETRY.json`
- `docs/plans/M35_URIV1_A2_8J_AGGREGATES.json`
- `docs/plans/M35_URIV1_A2_8J_EXECUTION_REPORT.md` (this file)

---

## 5. Before/after comparison, 79-case corpus, C1/C2/C3 (whole-corpus, not just targets)

Denominator: n=84 ground-truth-bearing rows (rows whose `expected_outcome` is not `NO_REFERENCE`/`UNATTRIBUTED_DETECTOR_FIND`), identical methodology to A2.8H/A2.8I, independently re-derived by this batch's own runner (`scripts/m35_a2_8j_rar_safe_battery.py`).

| Condition | Variant | Correct resolution | Incorrect confident binding (ICB) | Correct abstention (safe+family-mismatch) | Missed/silent-miss |
|---|---|---|---|---|---|
| C1 | RAR (existing) | 22 (26.19%) | **1** | 18 | 44 |
| C1 | RAR-SAFE | 18 (21.43%) | **0** | 19 | 48 |
| C2 | RAR (existing) | 13 (15.48%) | **1** | 25 | 46 |
| C2 | RAR-SAFE | 13 (15.48%) | **0** | 25 | 47 |
| C3 (empty pool) | both | 0 | 0 | n/a | all rows abstain (no candidates supplied) |

**ICB: 2 → 0, across both C1 and C2 combined.** Both named unsafe mechanisms (S1's `NB-B-05:r1` at C2, S3's `NB-H-06` at C1) are eliminated by construction, confirmed against the live telemetry (`docs/plans/M35_URIV1_A2_8J_TELEMETRY.json`, `variant=RAR-SAFE`, `scoring_class=INCORRECT_CONFIDENT_BINDING` → **zero rows**, vs 2 rows under `variant=RAR`).

**Coverage cost: 4 correct resolutions at C1 lost to safe abstention** (`NB-E-01`, `NB-E-02`, `NB-E-03`, `NB-L-03` — all Level 4b bare-type-mention singleton matches; individually audited in §11). C2 correct-resolution count is unchanged (13→13) because the one C2 gain (`NB-B-05:r1`, ICB→abstention) does not add a new correct resolution — it removes an unsafe one.

**Zero regressions:** `docs/plans/M35_URIV1_A2_8J_AGGREGATES.json::regressions_new_icb_under_safe` = `[]` (0 rows) — no case:ref that was safe or correct under existing RAR becomes an incorrect confident binding under RAR-SAFE, at either C1 or C2.

**Zero invented candidates, zero boundary violations** across all 900 telemetry rows (`invented_candidate_count: 0`, `boundary_violation_count: 0` in the aggregates file) — the Anti-Invention Gate (`validate_rar_resolution`) is exercised on every RAR-SAFE call exactly as on every existing-RAR call, and never raised.

---

## 6. Before/after table — Probe A: recency truthful-rank counterfactual

Method (`scripts/m35_a2_8j_counterfactual_battery.py::probe_a_recency_truthful_rank`): the harness's own oracle query construction (`s2_query_for_reference`) combined with **real** `created_at`-derived ranks (`build_candidate_pool(oracle_recency=True)`), for every ground-truth reference with `temporal_meaning != "none"`, at C1 and C2. This is the mechanical counterpart to A2.8I's own P3 probe, re-executed independently by this batch's script.

| | RAR (before) | RAR-SAFE (after) |
|---|---|---|
| n probed (refs × conditions) | 60 | 60 |
| Incorrect confident bindings | **10** | **3** |
| Correct resolutions | (baseline; recorded in telemetry) | unchanged where S2 does not fire |

**10 → 3 ICBs (70% reduction), not zero.** The 3 residual ICBs are individually traced (not hand-waved):

- `NB-C-04:r1` at C1 **and** C2 — `"the attachment"`, `target_type_hint="image"`. `"attachment"` is itself in `GENERIC_TYPE_WORDS`, so after excluding stopwords/generic-type-words/the type word, the substantive-token list is **empty**. S2's gate (`level6_would_contradict_binding`) is deliberately scoped to *contradiction* detection, not *zero-evidence* detection (that is S1's domain) — with zero substantive tokens the gate returns `False` (no contradiction found) and Level 5 binds on recency alone, unpatched. This is the same structural hazard as S1, but at Level 5, and the governing task's S2 patch was scoped only to the contradiction check, not a Level-5 zero-evidence gate. **Disclosed as an unresolved residual in §15**, not silently patched (would require expanding S2's scope beyond the task's own prescription).
- `NB-H-06:r1` at C1 (this probe's oracle-query shape, distinct from Probe C's real-D1RQ-query shape) — the oracle span is the full `"the other scan, the one from last week"`, which lexically contains the literal word `"scan"`; the sole C1 candidate's title is `scan_0034.pdf`, so `"scan"` — a generic descriptive noun, not in `GENERIC_TYPE_WORDS` — matches literally. S3's contrast-shortcut gate correctly prevents the *shortcut* from firing (elimination removed nothing), but the query still reaches Level 4b's *ordinary* substantive-token check, where `"scan"` satisfies "at least one substantive token matches" and binds via `TYPE_FILTER` — a different, pre-existing mechanism (not the contrast shortcut) that S1/S2/S3 were not scoped to touch. **Disclosed in §15.**

---

## 7. Before/after table — Probe B: T2 perfect-span diagnostic

Method (`probe_b_t2_perfect_span`): the 7 known T2 bare-proper-name silent detection misses (`NB-B-05:r2`, `NB-G-04:r1`, `NB-I-02:r2`, `NB-I-06:r2`, `NB-L-01:r2`, `NB-L-02:r2`, `NB-L-04:r2`). The ground-truth span is substituted directly as `reference_expression`; D1RQ's own **unmodified** signal-extraction helpers (`_recency_hint_for_text`, `_type_hint_for_phrase`, `_clause_negation_spans`, imported not duplicated) are applied to the span's home clause — reproducing exactly what D1RQ would have output had it detected this span. `recency_rank=0` (S1/`oracle_recency=False`), C1+C2. This mirrors A2.8I's own P1 methodology.

| | RAR (before) | RAR-SAFE (after) |
|---|---|---|
| n probed (7 refs × 2 conditions) | 14 | 14 |
| Incorrect confident bindings | **3** | **3** |

**Unchanged: 3 → 3.** This is the expected, correct result, not a defect: New F (the hazard this probe targets — Level 6's domain-tag bonus scoring a person's name higher on an object *associated with* them than on their own record) is a **Level 6 TF-IDF scoring property**, structurally unrelated to S1 (Level 4b zero-evidence), S2 (Level 5 vs Level 6 contradiction), or S3 (Level 4a contrast). None of the three patches touch Level 6's scoring function (`score_candidate_relevance`, imported unmodified). The governing task explicitly prohibits T2 detection and any repair of this mechanism in this batch. **This probe's unchanged result is itself the correct verification that New F remains exactly as latent/unsafe as A2.8I found it — confirming RAR-SAFE did not accidentally mask or fix an out-of-scope hazard, which would have been a scope violation, not a bonus.**

---

## 8. Before/after table — Probe C: exclusion/contrast (`NB-H-06`)

Method (`probe_c_exclusion_contrast`): the **real, live D1RQ-detected** span and signals for `NB-H-06:r1` (not reconstructed) — `detect_references(raw_text)` is called directly and its actual output is used, at C1 and C2.

| | RAR (before) | RAR-SAFE (after) |
|---|---|---|
| n probed | 2 (C1, C2) | 2 |
| Incorrect confident bindings | **1** (C1) | **0** |
| Outcome at C1 | `RESOLVED` → the excluded candidate (`CONTRAST_FILTER`) | `UNKNOWN` (`TERM_DISCRIMINATION`) |
| Outcome at C2 | `CORRECT_ABSTENTION` (already safe) | `CORRECT_ABSTENTION` (unchanged) |

**1 → 0, on the real production-shaped query (not a synthetic reconstruction).** This is the direct confirmation that S3 closes Known B on the actual corpus case that motivated it, using D1RQ's genuine output rather than a hand-built approximation.

---

## 9. Per-level resolution breakdown (Levels 0–7), C1+C2 combined, both variants

From `docs/plans/M35_URIV1_A2_8J_AGGREGATES.json::per_level_before_after` (levels attributed via `rule_used`; `CONTRAST_FILTER`/`EXACT_TITLE`/`CURRENT_ATTACHMENT` map to more than one possible level by rule name alone and are grouped accordingly — disclosed, not resolved further, since the trace does not separately tag which of two same-rule levels fired):

| Level (rule group) | Correct before (RAR) | Correct after (RAR-SAFE) | Unsafe (ICB) before | Unsafe (ICB) after |
|---|---|---|---|---|
| L0 (`EXACT_ID`/`EXACT_ALIAS`) | 0 | 0 | 0 | 0 |
| L1/L2 (`EXACT_TITLE`) | 4 | 4 | 0 | 0 |
| L1/L5.5 (`CURRENT_ATTACHMENT`) | 0 (6 correct abstentions) | 0 (6 correct abstentions) | 0 | 0 |
| L3 (`ACTIVE_POINTER`) | 0 | 0 | 0 | 0 |
| L4a/L4b (`CONTRAST_FILTER`) | 0 | 0 | **1** | **0** |
| L4b (`TYPE_FILTER`) | 4 | **0** | **1** | **0** |
| L5 (`TEMPORAL_RELATION`/`REVISION_RELATION`) | 0 | 0 | 0 | 0 |
| L6 (`TERM_DISCRIMINATION`) | 27 | 27 | 0 | 0 |
| L7 (residual/`NONE`) | n/a (never resolves) | n/a | n/a | n/a |

**Reading this table alongside §5/§11:** the L4b row's "correct before 4 → correct after 0" is exactly the 4 disclosed coverage losses (§11) — all four were bare-type-mention singleton matches that S1 now correctly refuses to bind on zero substantive evidence, and which Level 6 (reached next) cannot independently resolve because the same tokens that make them "zero substantive evidence" for S1 (the type word itself, already excluded via `GENERIC_TYPE_WORDS`) leave Level 6 with nothing to score either — these are not cases where a different level "picks up the slack"; they become genuine, disclosed coverage cost. L6's own correct-resolution count (27) is unchanged, confirming S1/S2/S3 do not alter Level 6's own decisions, only what reaches it.

---

## 10. Mechanical answers to the 7 questions, every RAR-SAFE `RESOLVED` outcome (C1+C2)

There are **18 + 13 = 31** `RESOLVED` outcomes under RAR-SAFE across C1/C2 combined. Rather than list all 31 individually (repetitive; the same 4 rule types recur), the 7 questions are answered **per rule-type class**, with the count of `RESOLVED` rows each class covers, verified against the telemetry:

| Rule / Level | n `RESOLVED` | (1) Positive evidence present? | (2) Rejected competitors recorded? | (3) Contradictory evidence present? | (4) Contradictory evidence consumed (S2 gate run)? | (5) Singleton-only (no lexical support)? | (6) Metadata-only (recency/type alone, no lexical)? | (7) Would Level 6 have contradicted? |
|---|---|---|---|---|---|---|---|---|
| `EXACT_TITLE` (L1/L2) | 4 | Yes — verbatim title/stem match | n/a (Level 0–2 anchors bypass competitor comparison by design, unchanged from existing RAR) | No (verbatim match cannot be lexically contradicted) | n/a | No — exact string match, not singleton-only | No — the match itself IS the lexical evidence | No (checked: title tokens are a superset of query tokens by construction) |
| `TERM_DISCRIMINATION` (L6) | 27 | Yes — `score_candidate_relevance > 0` with clear margin and full substantive-token coverage (existing RAR's own gate, unchanged) | Yes — `eliminated_candidate_ids`/runner-up score recorded in trace | No — Level 6 is itself the contradiction-detection level; by construction its own winners cannot contradict itself | n/a (S2 only applies to Level 5) | No — always requires `all_substantive_matched and clear_margin` | No — always lexical | n/a — this IS Level 6 |

**All 31 `RESOLVED` rows under RAR-SAFE fall into exactly these two rule classes** (verified: `docs/plans/M35_URIV1_A2_8J_TELEMETRY.json`, `variant=RAR-SAFE`, `scoring_class in (CORRECT_RESOLUTION, INCORRECT_CONFIDENT_BINDING)` → `rule_used ∈ {EXACT_TITLE, TERM_DISCRIMINATION}` only, zero rows with `rule_used ∈ {TYPE_FILTER, TEMPORAL_RELATION, REVISION_RELATION, CONTRAST_FILTER}` in the `RESOLVED` set — i.e., every commit point S1/S2/S3 gate now zero-outputs `RESOLVED` on this corpus at C1/C2. `CURRENT_ATTACHMENT`/`ACTIVE_POINTER` do not appear because no case in this corpus exercises those anchors with a `RESOLVED` outcome under either variant). This is itself informative: on this specific 79-case corpus, S1/S2/S3's gated commit points (Level 4b singleton, Level 5 temporal, Level 4a contrast) produce **zero** `RESOLVED` outcomes under RAR-SAFE — every surviving `RESOLVED` comes from a level the three patches do not touch. Whether this generalizes beyond this corpus is **`UNMEASURED`** (§14) — no second corpus exists to test against.

---

## 11. Individual audit of every coverage loss (correct → abstention)

All 4 are Level 4b singleton-type-match, zero-substantive-query-evidence cases (S1's exact target mechanism), each individually traced against the real corpus text:

| Case:ref | User text | GT referent | C1 pool | Why RAR (existing) got it right | Why RAR-SAFE now abstains |
|---|---|---|---|---|---|
| `NB-E-01:r1` | "Can you check **the spreadsheet** for any duplicate employee IDs?" | the one spreadsheet in a 3-candidate pool | 1 spreadsheet, 2 non-spreadsheets | Singleton type match on `target_type_hint="spreadsheet"`; happened to be the only spreadsheet | `"spreadsheet"` is itself in `GENERIC_TYPE_WORDS` and is the type word itself → zero substantive tokens after exclusion → S1 refuses to bind; Level 6 then also scores 0 (same tokens excluded) → `UNKNOWN`/`PRONOUN_BINDING` |
| `NB-E-02:r1` | "print **the PDF** for me" | the one PDF in a 3-candidate pool | 1 pdf, 2 non-pdf | Same mechanism | Same mechanism |
| `NB-E-03:r1` | "Did **the email from Priya** say which dates she needs?" | the one email in a 2-candidate pool | 1 email, 1 non-email | Same mechanism (`"email"` also in `GENERIC_TYPE_WORDS`) | Same mechanism. **Correction (flagged by the independent final audit):** the original text here claimed "the pool has no person-record candidate to compare against" — that is factually wrong; the C1 pool for this row **does** contain a person-record candidate, `obj-0e93c8` ("Contact: Priya Nair - HR"). "Priya" never reaches RAR at all in this row because D1RQ's detected span is only `"the email"` — the trailing `"from Priya"` is not part of the span RAR receives (a detector-boundary issue, not a RAR-SAFE or pool-composition issue), so RAR-SAFE has no "Priya" token to discriminate on regardless of what the pool contains. |
| `NB-L-03:r1` | "Two files there. In **the spreadsheet**, who's rostered on the 12th?" | the one spreadsheet in a 2-candidate pool | 1 spreadsheet, 1 non-spreadsheet | Same mechanism | Same mechanism |

**Honest characterization, not spin:** in all 4 cases, the *existing* RAR binding was correct on **this specific corpus** only because the type-matched pool happened to contain exactly one member with no distractor of the same type carrying a similar name. S1's invariant ("no binding on zero substantive evidence") is a *general* safety property that does not know, and should not know, that these 4 particular pools happen to be safe — the same zero-evidence code path is exactly what produces the unsafe `NB-B-05:r1` binding when the pool composition differs. This is the direct, disclosed price of the S1 invariant: it trades 4 correct resolutions (on pools that happened to be safe) for closing 1 confirmed unsafe binding (on a pool that was not) **plus** removing the general mechanism that could produce further such unsafe bindings on pools not present in this corpus. Whether 4:1 is an acceptable trade is a judgment call for the next-experiment decision (§17), not asserted here as automatically correct.

---

## 12. Existing RAR test regression suite results

Command (exact, as specified in the governing task):
```
pytest test_m35_uriv1_a2_5_deterministic_rar.py test_m35_uriv1_a2_5_rar_adversarial_safety.py test_m35_uriv1_a2_5_candidate_invention_fix.py test_m35_uriv1_a2_5_rar_contracts.py test_m35_uriv1_a2_5_rar_stage4_refinements.py
```
**Result: 75 passed, 48 subtests passed, 0 failed.** Run twice (once before writing this report, once after all battery/probe scripts executed) with identical results both times. None of these five test files import `rar_safe_experimental` — they exercise only `resolve_rar_deterministic_extended`, confirming existing RAR's behavior is unaffected by this batch's additions (consistent with the byte-identity check in §4, which is the stronger of the two guarantees — byte-identical source cannot behaviorally regress).

---

## 13. Resource impact / latency overhead

Measured directly from `docs/plans/M35_URIV1_A2_8J_TELEMETRY.json::latency_ms` (246 RAR-invoked rows per variant, C1+C2, wall-clock `time.perf_counter()` deltas around each resolver call, single-threaded, no model calls in either variant):

| Variant | n | Mean latency | Max latency |
|---|---|---|---|
| RAR (existing) | 246 | 0.0444 ms | 0.3151 ms |
| RAR-SAFE | 246 | 0.0417 ms | 0.1838 ms |

**No measurable overhead.** RAR-SAFE's mean is marginally *lower*, which is sampling noise at sub-millisecond scale (both variants are pure in-process Python with no I/O or model calls), not a real speedup — the S2 gate (`level6_would_contradict_binding`) only executes on the Level 5 single-match branches, a small fraction of calls, and does no additional candidate-pool scans beyond what Level 6 already performs when reached normally. `INVENTED_CANDIDATE`/`BOUNDARY_VIOLATION` remain 0 for both variants (§5) — no additional validation overhead was introduced.

---

## 14. Corpus hashes and verification metadata

| Item | Value |
|---|---|
| Corpus path | `uri_v1/turn/rar_natural_boundary_raw_turn_fixtures.json` |
| Corpus SHA-256 (pre-run, both battery scripts) | `0ea5447354481041181538244ef70b6dc58a72267dd95263d61dbdb55ab07380` |
| Corpus SHA-256 (post-run, both battery scripts) | `0ea5447354481041181538244ef70b6dc58a72267dd95263d61dbdb55ab07380` (unchanged) |
| Matches A2.8H/A2.8I's own recorded hash | Yes, exactly |
| `rar_deterministic.py` / `rar_contracts.py` / D1RQ SHA-256 | See §4 table — all three match A2.8I's independently recorded values |
| Reproducibility (decision fields) | Two independent full battery runs compared field-by-field excluding `latency_ms` (the only intentionally non-deterministic field, being a wall-clock measurement) → **bit-identical**, 900/900 records equal |
| Reproducibility (`latency_ms` itself) | Not bit-identical between runs (expected — wall-clock timing), `UNMEASURED` whether a third run would fall within the same range; not material to any correctness claim in this report |
| Whether S1/S2/S3's zero-`RESOLVED`-from-gated-levels result (§10) generalizes beyond this 79-case corpus | `UNMEASURED` — no second corpus exists in this repository to test against |
| Whether the 4:1 coverage-loss-to-safety-gain trade (§11) is representative of a larger/differently-composed candidate universe | `UNMEASURED` — this corpus's candidate pools are small (1–5 candidates); larger pools were not tested |

---

## 15. Unresolved mechanisms / residuals (disclosed, not silently patched)

1. **Level 5 zero-substantive-evidence binding (`NB-C-04`, both C1 and C2, Probe A §6).** Structurally the same hazard class as S1, but at Level 5, not Level 4b. The governing task's S2 patch is a *contradiction* gate, not a *zero-evidence* gate, and was not scoped to also cover this. Out of scope to fix in this batch (would require expanding S2's mandate beyond what was specified); flagged as a candidate for the next experiment (§17).
2. **Level 4b's ordinary substantive-match path can still bind on a generic descriptive word that happens to lexically coincide with a candidate's filename token** (`NB-H-06`'s oracle-query shape in Probe A, §6 — `"scan"` in `"the other scan"` matching `scan_0034.pdf`). This is a pre-existing Known-D-adjacent hazard (generic words not in `GENERIC_TYPE_WORDS` treated as discriminating), explicitly out of scope for this batch (Known C/D repair is frozen out by the plan §3).
3. **New F (Level 6 domain-tag bonus / T2 latent unsafe binding) is confirmed unchanged, by design** (§7) — 3 ICBs before, 3 after. This is not a gap in RAR-SAFE's coverage; it is a hazard in a different, untouched mechanism (Level 6 scoring), and the task explicitly prohibits touching it in this batch.
4. **Known A (masked in production, since `recency_rank` is always 0 at the one real call site)** is now demonstrably reduced but not eliminated once ranks are real (Probe A: 10→3 ICBs). Wiring real recency into production remains explicitly out of scope and is not recommended by this report without first addressing residual #1 above.
5. **Rule-to-level attribution is ambiguous for 3 rule names** (`EXACT_TITLE` spans L1/L2, `CURRENT_ATTACHMENT` spans L1/L5.5, `CONTRAST_FILTER` spans L4a/L4b) because `DeterministicRARTrace` does not separately tag which same-named-rule level fired. This is a pre-existing trace-granularity limitation, not introduced by this batch; disclosed rather than resolved by guessing.

---

## 16. Files created/touched

**Created (all new):**
- `uri_v1/turn/rar_safe_experimental.py`
- `scripts/m35_a2_8j_rar_safe_battery.py`
- `scripts/m35_a2_8j_counterfactual_battery.py`
- `docs/plans/M35_URIV1_A2_8J_TELEMETRY.json`
- `docs/plans/M35_URIV1_A2_8J_AGGREGATES.json`
- `docs/plans/M35_URIV1_A2_8J_EXECUTION_REPORT.md` (this file)

**Touched:** none. Confirmed by SHA-256 identity (§4) on every file the plan named as frozen, both before and after all script execution and the pytest run.

---

## 17. Next-experiment recommendation and the 7 required questions

1. **Is RAR safe enough to qualify recency wiring into production?** **Not yet.** Probe A shows S2 closes 7 of 10 latent ICBs once ranks are real, but 3 remain (`NB-C-04` ×2 conditions, `NB-H-06`'s oracle shape ×1) via mechanisms S1/S2/S3 do not reach (§6, §15 items 1–2). Wiring recency now would still expose 3 confirmed-latent unsafe bindings on this corpus alone.
2. **Is RAR safe enough to qualify T2 bare-name detection?** **No, unchanged from A2.8I's own conclusion.** Probe B confirms 3/7 T2 cases would still produce ICBs if detection were enabled, because New F (Level 6's domain-tag bonus) is untouched and out of this batch's scope by design (§7).
3. **What should the next experiment target?** The Level 5 zero-substantive-evidence gap (residual #1, §15) is the most directly analogous next step to this batch's own S1 patch — same invariant clause ("no binding on zero substantive evidence"), different level, and would close `NB-C-04` without touching recency wiring itself.
4. **Should New F be addressed before or independently of Level 5's gap?** Independently — they are different mechanisms (Level 6 scoring bonus vs. Level 5 commit gating) with no shared code path; fixing one does not help the other, and both must close before T2 detection or recency wiring can be safely enabled.
5. **Does the 4:1 coverage-loss-to-safety trade (§11) block adoption of S1 as-is?** Not necessarily, but it should be re-measured on a larger/more varied candidate-pool corpus before treating 4:1 as representative (§14, `UNMEASURED`) — this corpus's pools are uniformly small (1–5 candidates), and the coverage loss is concentrated entirely in the "bare type mention, coincidentally-unique pool" pattern, which may or may not be common in real usage.
6. **Is the RAR-SAFE module itself ready to become the new default resolver?** Not as a wholesale replacement yet — it strictly dominates existing RAR on this corpus (0 regressions, 2 ICBs closed, 4 correct resolutions traded away with full individual disclosure), but "strictly dominates on one 79-case synthetic corpus" is not sufficient evidence for a production default swap; a second, independently-constructed corpus and the Level-5 zero-evidence gap (§15 item 1) should close first.
7. **What would change this recommendation?** Direct evidence that (a) the Level 5 zero-evidence gap and Level 4b generic-word-collision residual (§15 items 1–2) are closed without reopening S1/S2/S3's own safety gains, and (b) the 4:1 coverage-loss ratio holds or improves on a corpus with larger, more realistic candidate pools than this one's.

---

## R3(a) REPAIR ADDENDUM (2026-09-24)

**Scope note:** this addendum supersedes the original §2, §6, §12, and §15 item 2 above wherever they conflict. It was written in response to `docs/plans/M35_URIV1_A2_8J_INDEPENDENT_FINAL_AUDIT.md` (verdict `REPAIR_REQUIRED`) and the User's follow-up bounded-repair directive selecting option R3(a). The original body above is left unedited (auditable correction history) except for three isolated factual-typo fixes (§1 "22/84" not "26/84"; §3.2 "9-word" not "8-word"; §11 NB-E-03 pool-composition correction) that are pure corrections, not measurement changes.

Implementer for this repair pass: Claude (the same session that performed the independent final audit), exercising the AO-4 bounded-fix authority documented in project governance — the repair is scoped exactly to the six items (R1–R6) the audit specified, performed no unrelated changes, and is itself now subject to a bounded re-audit rather than self-declared VERIFIED.

### R3(a): exact code change

**File changed:** `uri_v1/turn/rar_safe_experimental.py` only. No other file was edited. `rar_deterministic.py`, `rar_contracts.py`, and `scripts/m35_a2_8h_detector_d1rq.py` are confirmed byte-identical to the pre-repair (and pre-A2.8J) state — SHA-256 re-verified after the repair:

| File | SHA-256 | Match |
|---|---|---|
| `uri_v1/turn/rar_deterministic.py` | `e02af25bb7009d12d829c8b8fc92e487d3da75aeaa160092db617458278fb649` | ✅ unchanged |
| `uri_v1/turn/rar_contracts.py` | `4cc9aa43726a870ca2e9ab1b19f6bf9d72dcb74c8a2818856776af95195b6819` | ✅ unchanged |
| `scripts/m35_a2_8h_detector_d1rq.py` | `49f5faa9b37051fec876f5523383b4e965422976562c52e12fc38c970bfa6b82` | ✅ unchanged |
| `uri_v1/turn/rar_natural_boundary_raw_turn_fixtures.json` (corpus) | `0ea5447354481041181538244ef70b6dc58a72267dd95263d61dbdb55ab07380` | ✅ unchanged |

**What changed:** only the `_RECENCY_VOCABULARY` module-level constant in `rar_safe_experimental.py` — no other line of executable logic. S1, S3, cascade ordering, and all other S2 code (the gate's call sites, its "misdirected entity" clause, its absent-entity clause) are untouched.

**Old value (9 words):** `previous, revised, original, latest, current, earlier, earliest, same, other`

**New value (19 words):** the old 9 plus 10 words derived from three existing baseline-RAR sources (not independently invented — see next subsection):
`revision, draft, version, v1, v2` (from `classify_unresolved_failure`'s `revision_words`, `rar_deterministic.py:196`)
`first, last, prior` (from `classify_unresolved_failure`'s `temporal_words`, `rar_deterministic.py:201`)
`attached, attaches` (from Level 5.5's `_ATTACHMENT_TRIGGER_TOKENS`, `rar_deterministic.py:711`; `attachment` itself was already excluded via `GENERIC_TYPE_WORDS`)

No word was removed. No case ID, benchmark label, or hand-picked example word (beyond what the three cited baseline sets already contain) was added. The audit's own example list (`version`, `draft`, `revised`, `last`, `prior`, `attached`) is a subset of this derived set — it was used as a pointer to go verify the source, per the directive's instruction, not copied as authority in itself.

### Source of the S2 vocabulary (item 5 of required output)

`rar_deterministic.py` cannot be imported from for this purpose without modifying it (the two word sets are local variables inside `classify_unresolved_failure`'s function body, not module-level exports, and `_ATTACHMENT_TRIGGER_TOKENS` is similarly local to the cascade function). Since baseline `rar_deterministic.py` is frozen and must not be touched, the three sets are reproduced verbatim in `rar_safe_experimental.py` with an explicit line-number citation to their source, rather than silently re-invented. This is the closest available reuse without an out-of-scope baseline edit.

### R3(a) measured effect

**Natural 79-case corpus (C1/C2/C3): unaffected, byte-for-byte identical to pre-repair.**

Reason: the natural corpus always calls `build_candidate_pool(..., oracle_recency=False)`, so every candidate's `recency_rank` is 0. Level 5's `has_ordering` check (`any(c.recency_rank > 0 ...)`) is never true, so none of the four Level-5 single-match branches S2 gates are ever reached — **S2 fires 0 times on the natural corpus, before and after this repair.** Confirmed by direct instrumentation (call-count = 0 in both cases). Consequently:

- Pre- and post-repair natural-corpus results are **identical**: ICB 2 → 0 at C1+C2 combined (`NB-B-05:r1@C2` via S1, `NB-H-06:r1@C1` via S3), 4 coverage losses (`NB-E-01/E-02/E-03/L-03:r1@C1`, all S1), 0 regressions, 0 invented candidates, 0 boundary violations. Corpus SHA-256 unchanged pre/post run: `0ea5447354481041181538244ef70b6dc58a72267dd95263d61dbdb55ab07380`.
- The headline natural-corpus result from the original report (§5) **stands, unmodified, post-repair.**

**Probe A (recency truthful-rank, oracle_recency=True, n=60): materially different — regenerated, not reused.**

| | RAR (baseline) | RAR-SAFE, pre-repair (old 9-word vocab) | RAR-SAFE, post-repair (new 19-word vocab) |
|---|---|---|---|
| Incorrect confident bindings | 10 | 3 | **5** |
| Correct resolutions | 23 | 9 | **9** |
| S2 gate invocations | — | 23 | 23 |
| S2 → contradiction found (True) | — | 16 | 14 |
| S2 → passed through (False) | — | 7 | 9 |

Do not read "ICB 3 → 5" as the repair making things worse in an absolute sense: **baseline RAR's ICB count on this probe is 10, unaffected by any of this**; RAR-SAFE post-repair still closes 5 of the 10 baseline ICBs (vs. 7 pre-repair). Read alongside the per-case breakdown below, the change is a genuine, disclosed trade: 2 of the 3 unit/fixture test conflicts caused by S2 (see R2) are fixed by the same vocabulary correction, while 2 Probe A rows (`NB-C-05:r1` at C1 and C2) lose the safety gain they previously had, for a documented reason (below), not an unexplained regression.

**Probe A — full row-level disclosure (all 19 rows that differ from baseline RAR; the audit's required per-case accounting):**

*Coverage losses (baseline correct → RAR-SAFE not-correct), 14 rows — same 14 rows before and after this repair (the repair's added vocabulary words do not appear in any of these spans):*

| Case:ref | Cond | Cause | Blocking token(s) |
|---|---|---|---|
| NB-B-01:r1, NB-B-04:r1, NB-B-05:r1, NB-C-02:r1, NB-G-01:r1, NB-L-03:r1 | C1 | S1 (zero substantive tokens; pronoun-headed or bare-type spans) | n/a — S1, not S2 |
| NB-D-02:r1 | C1 | S2, remaining false contradiction | `before` — not in any of the three baseline sets cited above; not added |
| NB-D-04:r1 | C1 | S2, remaining false contradiction | `used`, `before` |
| NB-D-05:r1 | C1 | S2, remaining false contradiction | `older` (note: `version` in this same span is now correctly excluded post-repair, but `older` alone still triggers) |
| NB-D-06:r1 | C1, C2 | S2, remaining false contradiction | `last` is now excluded (post-repair) but `thing` still triggers |
| NB-D-07:r1 | C1 | S2, remaining false contradiction | `invoice`, `before` |
| NB-L-04:r1 | C1, C2 | S2, remaining false contradiction | `most`, `recent` (neither is in the three baseline sets) |

**Disclosed limitation:** `before`, `older`, `thing`, `most`, `recent`, `used`, `invoice` are not part of any existing baseline-RAR non-entity vocabulary, so deriving strictly from baseline semantics (as the directive required) does not close these. This is a genuine, honestly-measured residual of the S2 mechanism as currently scoped — not silently patched, and not fixed by inventing further ad hoc words, which the directive explicitly prohibited ("do not blindly implement only the example words listed by the auditor" cuts both ways: it also forbids expanding beyond what baseline actually defines).

*Genuine safety gains (baseline ICB → RAR-SAFE not-ICB), 5 rows — unaffected by this repair (none of these rows' contradiction tokens are in the repaired vocabulary):*

| Case:ref | Cond | RAR-SAFE outcome | Contradiction token(s) |
|---|---|---|---|
| NB-D-01:r1 | C2 | MISSED_RESOLVABLE_CASE (UNKNOWN) | `board`, `minutes` — absent from the winning candidate's pool position |
| NB-D-02:r1 | C2 | MISSED_RESOLVABLE_CASE (UNKNOWN) | `before` |
| NB-J-02:r1 | C1 | CORRECT_ABSTENTION (UNKNOWN) | `contract`, `jonas`, `sent`, `over`, `last`→(last now excluded, but `contract`/`jonas`/`sent`/`over` still trigger) |
| NB-J-04:r1 | C1 | CORRECT_ABSTENTION (UNKNOWN) | `template`, `agreed`, `yesterday` |
| NB-L-09:r2 | C2 | CORRECT_ABSTENTION (UNKNOWN) | `uploaded`, `before` |

*Regressed safety gain (baseline ICB → RAR-SAFE-pre-repair not-ICB → RAR-SAFE-post-repair ICB again), 2 rows — directly caused by this repair, fully disclosed:*

| Case:ref | Cond | Pre-repair | Post-repair | Cause |
|---|---|---|---|---|
| NB-C-05:r1 | C1 | CORRECT_ABSTENTION (AMBIGUOUS, via S2 treating `attached` as an absent substantive token) | INCORRECT_CONFIDENT_BINDING (RESOLVED via TEMPORAL_RELATION, candidate `2f58b7c0-e6a3-...`) | `attached` is now excluded from "substantive" per the baseline-derived vocabulary (Level 5.5's own trigger-token set). With `attached` excluded, this query's substantive-token list becomes empty. S2's own contract (§3, module docstring) explicitly returns `False` — "no contradiction" — on empty substantive input, deferring zero-evidence handling to S1. But **S1 only gates Level 4b**, not Level 5, so this row falls through the empty S2 gate straight into an unguarded Level-5 commit. |
| NB-C-05:r1 | C2 | CORRECT_ABSTENTION (AMBIGUOUS) | INCORRECT_CONFIDENT_BINDING (RESOLVED via TEMPORAL_RELATION, candidate `4b7f9e03-c2d8-...`) | Same mechanism |

**This is a newly surfaced, real instance of the already-disclosed Level-5 zero-substantive-evidence residual** (original report §15 item 1, `NB-C-04`) — R3(a) did not introduce a new hazard class, it removed one of the two accidental partial mitigations (the other being the pre-repair narrower vocabulary itself) that happened to catch this specific known-open gap for this specific query shape. Per the repair directive §5 ("do not repair NB-C-04 / Level-5 zero-substantive-evidence recency in this pass" and §10 "do not claim S2 validated merely because aggregate ICB decreases"), **this residual is not repaired here.** It is recorded as a newly surfaced concrete instance of the pre-existing, already-known-and-explicitly-out-of-scope Level-5 gap, item 17 below.

**Probe B (T2 perfect span, n=14): unaffected.** ICB 3 → 3, correct 7 → 7, bit-identical to pre-repair. None of the 7 T2 target spans contain any word from the repaired vocabulary; Level 6 (New F) remains the limiting, untouched mechanism, exactly as originally reported.

**Probe C (NB-H-06 real D1RQ span, n=2): unaffected.** ICB 1 → 0 at C1, unchanged; C2 remains CORRECT_ABSTENTION. `oracle_recency=False` for this probe, so no Level-5 branch is exercised regardless of vocabulary.

### R1: Probe A disclosure — resolution

Requirement met: the pre-repair measured Probe A result (correct 23→9, ICB 10→3, **14 undisclosed coverage losses**) is stated above in full, case-by-case, alongside the post-repair regenerated result (correct 23→9, ICB 10→5). The original report's §6 table — which described the coverage-loss column as "unchanged where S2 does not fire" without giving the actual 14-row count — is superseded by this addendum's full accounting.

### R2: existing-test conflicts — post-repair classification

Reproduced by running the five named test files with `resolve_rar_deterministic_extended` swapped for `resolve_rar_safe_experimental` (in-process monkeypatch; no test file and no `rar_deterministic.py` line edited).

**Pre-repair: 7 conflicts** (3 tests + 4 subtests). **Post-repair: 4 conflicts** (1 test + 3 subtests) — the 3 S2-caused conflicts are resolved by R3(a); the 4 S1-caused conflicts are unchanged, as expected (R3(a) does not touch S1).

| Test / fixture | Query | Pre-repair | Post-repair | Safeguard | Classification |
|---|---|---|---|---|---|
| `test_level_5_revision_relation` | "the revised draft" | FAIL (`draft` false contradiction) | **PASS** | S2 | Fixed by R3(a) |
| RAR-FIX-13 | "the earlier version" | FAIL (`version` false contradiction) | **PASS** | S2 | Fixed by R3(a) |
| `test_rc1_current_unique_recency_resolves` | "the current version" | FAIL (`version` false contradiction) | **PASS** | S2 | Fixed by R3(a) |
| `test_level_4_type_filtering_single_match` | "the workflow", type workflow | FAIL | FAIL (unchanged) | S1 | Intentional consequence of the frozen S1 invariant — the test encodes exactly the zero-substantive singleton-type binding S1 is designed to refuse. Not a regression; not repaired in this pass (S1 is out of scope for R3). |
| RAR-FIX-02 | "the email", type email | FAIL | FAIL (unchanged) | S1 | Same — intentional consequence |
| RAR-FIX-20A | "that file", type document | FAIL | FAIL (unchanged) | S1 | Same — intentional consequence |
| RAR-FIX-20B | "him", type person | FAIL | FAIL (unchanged) | S1 | Same — intentional consequence |

No test expectation was changed. Baseline RAR (`resolve_rar_deterministic_extended`, unswapped) still passes all five files in full: **75 passed, 48 subtests passed, 0 failed**, reconfirmed after this repair.

### R4: corrected hypothesis conclusion (supersedes original §2)

The plan's hypothesis — one evidence-sufficiency invariant unifying Known A/B, New G/F — is **not established as a cascade-wide enforced property**, before or after this repair. What is established:

- **S1 enforces clause 2 (no binding on zero substantive evidence) only at Level 4b.** It does not reach Level 5's temporal branches (`NB-C-04`, both pre- and post-repair; `NB-C-05` post-repair, newly demonstrated), nor Level 5.5's attachment branch, nor Level 6's ordinary scoring path, all of which can still commit on evidence that is either absent or itself the type/attachment word alone (§8/§5 of the independent audit; reconfirmed unchanged by this repair since R3(a) touched no code outside `_RECENCY_VOCABULARY`).
- **S2 enforces clause 1 (no binding contradicting Level-6 evidence) only at Level 5's four single-match branches, and only for tokens outside its exclusion vocabulary.** Post-repair, the vocabulary correctly reflects baseline RAR's own recognized temporal/revision/attachment words, closing 3 of the audit's specific false-contradiction examples (`version`, `draft`, `current`+`version`). It does not, and cannot without inventing new vocabulary (explicitly prohibited), reach ordinary descriptive words like `before`, `older`, `recent` that are not part of any existing baseline-RAR non-entity word set — these remain a disclosed, unrepaired limitation (14 Probe A coverage losses, all pre- and post-repair identical except vocabulary attribution).
- **S3 fixes the contrast *shortcut* causally, not the underlying 4b partial-match path** that can still bind an excluded candidate when a type hint independently matches (see R5 below).
- **Level 6 (New F) is entirely untouched** by any of S1/S2/S3, confirmed unchanged pre- and post-repair by Probe B (3→3 ICB).

**Corrected framing:** A2.8J implements three narrow, individually-verified safeguards that each close one specific, previously-confirmed unsafe mechanism on the natural 79-case corpus (2→0 ICB, reproduced and unaffected by this repair). It does not implement, and this repair does not make it implement, a single invariant that governs every commit point in the cascade. The plan's unifying-invariant language should be read as the *motivating hypothesis* the batch tested, not as an established property of the resulting code.

### R5: corrected safety classification (supersedes original §15 item 2)

**"The other scan" / `NB-H-06`'s Probe A oracle-query shape residual is a safety issue, not a coverage issue.** The original report filed this under "Known-D-adjacent" generic-word-collision coverage residuals (frozen out of scope as a Known C/D repair). The independent audit correctly identified that this miscategorizes the finding: when Level 4b's *ordinary* substantive-match path (not the S3-gated contrast shortcut) binds on a single lexically-matching word (e.g., `scan` matching `scan_0034.pdf`) while other query words (`other`, `last`, `week`) remain unmatched, **Level 6's own absent-entity/all-substantive-matched rule would refuse this exact binding if it were reached** — the binding is committed by 4b specifically because it precedes Level 6 in the cascade, not because the evidence actually supports it. This is precisely the hypothesis's clause-1 violation ("no level may commit a binding that the resolver's own Level-6 evidence contradicts"), at a different commit point (4b's ordinary path) than S3 addresses (4a's shortcut). It is **not** a Known C/D partial-credit/stemming/abbreviation coverage matter and should not have been filed alongside those. **Not repaired in this pass** (out of scope per the repair directive §5/§4), preserved as evidence for a subsequent experiment.

### R6: consolidated factual corrections

Applied inline above (marked in place) and restated here:

1. §1: "26/84 = 26.19%" corrected to "22/84 = 26.19%" (22/84 = 0.2619...; the percentage was always correct, only the numerator was mistyped). Matches A2.8I's independently recorded figure.
2. §3.2/recency-word list: "closed 8-word recency vocabulary" corrected to "9-word" (the listed set — `previous, revised, original, latest, current, earlier, earliest, same, other` — has 9 members, not 8). The claim that this set was already RAR's own complete non-entity vocabulary is corrected per R4 above — it was RAR's *RC-1 recency_hint* vocabulary only, not RAR's full temporal/revision/attachment vocabulary.
3. §11, NB-E-03: corrected — the C1 pool for this row does contain a person-record candidate (`obj-0e93c8`, "Contact: Priya Nair - HR"); the real reason "Priya" does not affect RAR-SAFE's decision is that D1RQ's detected span (`"the email"`) does not include "Priya" at all, a detector-boundary characteristic, not a pool-composition one.
4. Fall-through behavior (flagged by the audit as under-explained, §8/§20 D7 of the independent audit): when S1 (Level 4b) or S2 (Level 5) declines to bind, execution does not abstain immediately — it falls through to the next cascade stage with the candidate pool as narrowed so far. This means a query S1 or S2 refuses to bind at their own level can still be bound at a *later* level (Level 5, 5.5, or 6) if that later level's own independent evidence happens to support it. This is by design (matches how the existing multi-match branches already behave) and is not new to RAR-SAFE, but the original report did not state it explicitly. It is the mechanism behind: the natural corpus's 4 S1 losses landing in `UNKNOWN`/`PRONOUN_BINDING` at Level 6 (no further evidence available there either, so they stay abstentions); and `NB-C-05`'s post-repair regression landing in a Level-5 `RESOLVED` (S1 doesn't reach Level 5 at all, so there was never a second chance for it to be caught there).

No other statement in the original report was found to depend on the corrected items above; the search required by the repair directive (R6) covered §1–§17 of the original report and turned up no further occurrences of the "26/84", "8-word", or NB-E-03-pool-composition claims beyond the ones corrected.

### Newly discovered residual (item 17 of required output)

**`NB-C-05`'s Level-5 zero-substantive-evidence exposure is now a concretely demonstrated instance of the pre-existing Level-5 gap (original report §15 item 1), not merely `NB-C-04`'s single case.** Both rows share the identical root cause: S1 only gates Level 4b; S2 only gates against *detected contradiction*, not *absence of any evidence at all* (that is explicitly S1's domain, per the S2 docstring, and S1 does not reach Level 5). Any query whose only content is an attachment-semantics trigger word or a bare recency word, with no other descriptive token, will bind at Level 5 on recency alone once real ranks exist — regardless of how the S2 vocabulary is tuned, because a correctly-tuned S2 must return "no contradiction" on zero substantive evidence by its own stated contract. Closing this requires a Level-5 zero-evidence gate structurally analogous to S1, not a further S2 vocabulary change — this is exactly item 3 of the original report's §17 next-experiment recommendation, now with a second concrete corpus instance (`NB-C-05`, both C1 and C2) in addition to `NB-C-04`.

### Evidence gaps / UNMEASURED (unchanged by this repair, restated)

- Whether S1/S2/S3's zero-`RESOLVED`-from-gated-levels result on the natural corpus generalizes beyond this 79-case corpus: **UNMEASURED**.
- Whether the 4:1 natural-corpus coverage-loss-to-safety-gain ratio (unaffected by this repair) is representative of a larger/differently-composed candidate universe: **UNMEASURED**.
- Whether a phrase-head-position refinement to S1 (distinguishing "the spreadsheet" from a span that merely contains "...in an email") would recover the 4 natural-corpus losses without reopening `NB-B-05`: **UNMEASURED** — explicitly not implemented in this repair pass, per the repair directive §4.
- Whether extending the S2 exclusion vocabulary beyond baseline-RAR's own existing word sets (to cover `before`, `older`, `recent`, etc.) would recover more Probe A losses without reintroducing false safety: **UNMEASURED** and explicitly out of scope for this repair (would require inventing vocabulary beyond derivation from existing baseline semantics).

### Final repair status

**`VERIFICATION_READY`.** R1–R6 complete as scoped. No commit, no push, no merge, no promotion of RAR-SAFE, no start of A2.8K, no repair of `NB-C-04`/`NB-C-05`'s Level-5 gap, no repair of New F/Level-6 scoring, no implementation of the S1 phrase-head refinement. Awaiting the independent auditor's bounded re-audit of this addendum and the regenerated telemetry/aggregates.

---

**Stop condition reached: `VERIFICATION_READY`.** No commit, no push performed or requested in this batch, per the governing plan and task.
