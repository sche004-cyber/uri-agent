# M35 URIv1 — A2.8J: RAR-SAFE Qualification — Independent Final Audit

**Auditor:** Claude (Opus 5.5), independent final auditor. Did not implement A2.8J.
**Date:** 2026-09-24
**Governing plan:** `docs/plans/M35_URIV1_A2_8J_RAR_SAFE_QUALIFICATION_PLAN.md` (treated as frozen)
**Audited report:** `docs/plans/M35_URIV1_A2_8J_EXECUTION_REPORT.md`
**Verdict:** **REPAIR_REQUIRED** (see §21)

Evidence labels used throughout: **VERIFIED FACT**, **REPRODUCED RESULT**, **AUDITOR INTERPRETATION**, **UNVERIFIED CLAIM**, **OUT-OF-SCOPE OBSERVATION**, **UNMEASURED**.

All audit reproduction outputs were written to the session scratchpad, not to the repository. No authoritative telemetry/aggregates file was overwritten (post-audit SHA-256 prefixes: telemetry `895057a2697587d0`, aggregates `58fc5b3d10988eb0`, unchanged by this audit). No implementation file was modified.

---

## Acceptance criteria for this audit (defined before review)

The audit returns ACCEPTED only if all of the following hold:

- A1. Frozen files are byte-identical to pre-A2.8J recorded state.
- A2. RAR-SAFE is isolated; baseline RAR is behaviourally unchanged.
- A3. Implementation matches plan §5 S1/S2/S3 and changes nothing else in the cascade.
- A4. Corpus battery and counterfactual probes reproduce from source, bit-identical on decision fields.
- A5. The headline ICB claim holds case-by-case.
- A6. Every coverage loss (corpus and probes) is disclosed and correctly explained.
- A7. Plan §6 criteria 1–10 are each met with evidence.
- A8. No benchmark contamination.
- A9. Report's factual statements match repository evidence.

---

## 1. Repository / branch / HEAD verification

- VERIFIED FACT: worktree `C:/Users/cheta/Development/Uri/_V1`, branch `m35-uri-v1-parallel-architecture`, HEAD `e8e3b65259c45fc823addc3ef8969425a265bd1b` (so the expected baseline is HEAD itself, not only an ancestor).
- VERIFIED FACT: tracked-file diff vs HEAD touches only `SKILL.md` and `docs/governance/URI_AGENT_RELAY.md` (pre-existing, unrelated to A2.8J).
- VERIFIED FACT: the entire `uri_v1/` tree, all `scripts/m35_*` files, and all root `test_m35_uriv1_a2_5_*` files are **untracked**. Git history cannot attest to their prior content. Byte-integrity therefore rests on SHA-256 values recorded in earlier audit documents (see §16), not on git.
- VERIFIED FACT: no commit or push occurred for A2.8J (HEAD unchanged; all A2.8J files untracked).
- Legacy prototype `C:\Users\cheta\Development\uri-agent` was not accessed or modified.

## 2. Governing evidence inspected

Plan, STATE, execution report, telemetry, aggregates (all read in full or reproduced); `rar_safe_experimental.py` (full); `rar_deterministic.py` (helpers + cascade, via AST-level function diff); both A2.8J runners (full); harness `build_candidate_pool` and `s2_query_for_reference`; A2.8H runner scoring helpers (AST comparison); A2.8I audit (hash table, baseline figures); corpus JSON for NB-B-05, NB-E-01/02/03, NB-L-03, NB-H-06, NB-C-04 plus live D1RQ output and built candidate pools; five existing RAR test files (run twice: against baseline and against RAR-SAFE).

UNVERIFIED CLAIM: the "mission brief" that plan §4/§6 cites (17-point report, §9/§10/§13/§14/§17 numbering) is not present in the repository. Criteria were judged against plan §6 text only. This does not change the verdict.

UNVERIFIED CLAIM: the STATE history entry records a User directive re-routing implementation from Codex to Claude Sonnet. Only the STATE file attests this. Governance-only; does not affect the technical verdict.

## 3. Working-tree and scope-diff audit

- VERIFIED FACT: A2.8J-created files (by mtime ordering after the plan at 13:48): `uri_v1/turn/rar_safe_experimental.py` (14:05), both A2.8J scripts (14:07, 14:09), telemetry/aggregates (14:11), report (14:13), STATE (14:14). Frozen files carry earlier mtimes: `rar_contracts.py` 2026-09-21, `rar_deterministic.py` 2026-09-22, D1RQ 2026-09-24 13:13 (all before the plan). mtime is supporting evidence only; SHA-256 is primary.
- VERIFIED FACT: no existing test file imports `rar_safe_experimental`; RAR-SAFE is referenced only by the two A2.8J scripts.
- VERIFIED FACT: RAR-SAFE has no dedicated unit tests. Plan §4 did not require them. The §3.1–§3.3 "direct verification" constructions in the report exist in no committed script; this audit re-created them (§5–§7) and they reproduce.

## 4. Frozen-plan compliance

| Plan §6 criterion | Result |
|---|---|
| 1 Frozen files byte-unmodified | MET (hash vs A2.8I record; git cannot attest) |
| 2 RAR-SAFE isolated, RAR unchanged | MET |
| 3 Existing tests pass against RAR; conflicting tests flagged and classified | **PARTIALLY MET** — pass reproduced; conflict flagging **not done** (7 conflicts exist, §15) |
| 4 79-case corpus, both variants, C1/C2/C3, per-level table | MET (reproduced bit-identical) |
| 5 Three counterfactual batteries with before/after ICB | MET (reproduced bit-identical) |
| 6 7 mechanical questions per RESOLVED | MET at rule-class granularity; Q2 claim ("recorded in trace") not persisted in telemetry (minor) |
| 7 Every coverage loss individually audited and disclosed | **NOT MET** — 14 Probe A coverage losses undisclosed (§13); one corpus-loss rationale factually wrong (§12) |
| 8 `UNMEASURED` used honestly, no fabricated figures | **NOT MET** — a measured figure (Probe A correct 23→9) was replaced by non-quantitative wording (§13) |
| 9 Seven next-step questions answered | Answered, but recommendations rest on the incomplete Probe A picture |
| 10 No commit/push | MET |

Prohibited-scope check (plan §3): no recency wiring, no T2 detection, no session state/aliases/stemming, no D1RQ change, no Known C/D repair, no production integration. VERIFIED FACT: all respected.

## 5. S1 audit (Level 4b zero-substantive-evidence binding)

- VERIFIED FACT: S1 changes only the 4b singleton branch. When `substantive_query_tokens` (ref tokens minus STOPWORDS, GENERIC_TYPE_WORDS, PRONOUNS, and the target type word) is empty, the singleton is not bound; the pool narrows to the type-matched subset and the cascade continues. This is the exact tightening plan §5 described ("tightening that existing check, not adding a new one").
- VERIFIED FACT: the definition of "substantive" is the same expression baseline 4b already used. It is RAR's existing semantics, not new vocabulary.
- REPRODUCED RESULT: S1 closes NB-B-05:r1@C2 (span `"that in an email"`, coarse_type `email`, one email in pool).
- Can unrelated evidence satisfy the gate? **Yes, by design of the unchanged baseline rule.** When any substantive token exists, 4b binds if *any one* token matches the candidate, ignoring unmatched tokens. REPRODUCED RESULT (Probe A, NB-H-06 C1 oracle shape): `"the other scan, the one from last week"` binds `scan_0034.pdf` on `"scan"` alone while `"other"`, `"last"`, `"week"` are unmatched. This is S1-adjacent, not S1 itself.
- Inconsistent definition across levels (new, undisclosed, see §18 U2): S1 excludes the target type word, but Level 6's `substantive` does not. REPRODUCED RESULT (synthetic): `"the letter"`, type `letter`, pool {Offer letter, record} → baseline binds at 4b; RAR-SAFE falls through S1 and **binds the same candidate at Level 6** (`TERM_DISCRIMINATION`) on the type word alone. Similarly, an S1-narrowed singleton with `is_attachment=True` is bound by Level 5.5 on `"the attachment"`. Neither is a regression against baseline, and neither occurs on the corpus. Both show that S1 is a 4b-local gate, not a cascade-wide zero-evidence invariant.
- Legitimate singleton resolutions suppressed: yes — all 4 corpus losses and 6 Probe A losses (§12, §13).
- Plan match: yes.

## 6. S2 audit (Level 5 commit against contradictory lexical evidence)

- VERIFIED FACT: `level6_would_contradict_binding()` is called at exactly the four Level-5 single-match commit points (revised / previous / earlier / latest-current). On `True`, control falls through to the next stage. Cascade order is unchanged; Level 6 is not moved earlier; no case-specific logic.
- VERIFIED FACT: the gate reuses Level 6's absent-entity rule (any substantive token absent from the pool ⇒ contradiction) plus a "misdirected" clause (token absent from the winner but present on another candidate).
- No circular reasoning or downstream leakage found: the gate is a pure function of reference tokens and the current pool, with no state mutation. VERIFIED FACT.
- **REPRODUCED RESULT: S2 is invoked 0 times on the 79-case natural corpus** (instrumented run). With `recency_rank=0` everywhere, no Level-5 single-match branch is ever reached. S2 contributes nothing to the headline 2→0; it is exercised only by Probe A. The report does not state this.
- **False contradiction signals suppress valid recency bindings — confirmed, material, undisclosed.** The gate excludes only a 9-word `_RECENCY_VOCABULARY` (the report calls it "8-word"). The report justifies this as "the closed set of recency literals `rar_deterministic.py`'s own RC-1 docstring and `RAREvidence.recency_hint` already define." **That claim is inaccurate.** `rar_deterministic.classify_unresolved_failure` already defines `revision_words = {revised, revision, draft, original, version, v1, v2}` and `temporal_words = {previous, earlier, latest, first, last, prior}`. Level 5.5 already defines `{attached, attachment, attaches}` as attachment-semantics triggers. None of `version`, `draft`, `revision`, `first`, `last`, `prior`, `attached` is excluded, so each is treated as an "absent entity" that contradicts the binding. REPRODUCED RESULT, tokens that fired the gate:
  - `"the earlier version"` (RAR-FIX-13) → `version`
  - `"the revised draft"` (unit test) → `draft`
  - `"the current version"` (RC-1 test) → `version`
  - `"the one before that"` (NB-D-02) → `before`
  - `"the older version of the Harbour Street lease"` (NB-D-05) → `older`, `version`
  - `"the last thing you did for me"` (NB-D-06) → `last`, `thing`
  - `"my most recent letter"` (NB-L-04) → `most`, `recent`
  - `"the attached file"` (NB-C-05) → `attached`
- Absent-entity interpretation: the gate inherits Level 6's all-or-nothing rule. Any descriptive word not in a title (for example `used` or `before` in NB-D-04) contradicts, even when the winner matches `agenda`, `september`, and `meeting`. AUDITOR INTERPRETATION: under this rule, Level 5 can commit only when the span contains nothing beyond recency words and title tokens. That is close to disabling Level 5 for natural temporal phrasing.
- Plan match: the mechanism matches plan §5. The exclusion-set justification does not match plan §5's instruction to use "RAR's own existing semantics".

## 7. S3 audit (Level 4a contrast/exclusion validation)

- VERIFIED FACT: the only change is `... and eliminated_ids` on the contrast-shortcut condition. There is no `"the other"` literal special-casing.
- VERIFIED FACT: `eliminated_ids` is populated only by (a) the explicit `rejected_in_turn` structural tag or (b) a negation-span token with df==1 overlapping a candidate (the baseline RC-2 rule). It is evidence-backed.
- Can candidate count still masquerade as exclusion evidence elsewhere? The Level-6 `if eliminated_ids: AMBIGUOUS` pre-check and the 4b `CONTRAST_FILTER` rule label both key on real elimination. No other pool-size-as-exclusion path was found. VERIFIED FACT.
- REPRODUCED RESULT: valid contrast still resolves (synthetic `"the other one"`, 2-pool, `"not the signed"` eliminates one → `CONTRAST_FILTER` binds the survivor under both variants). No valid contrast case on the corpus regressed.
- Causal vs fixture fix: S3 fixes the causal defect of the **shortcut**. The broader hazard ("the other X" binds the excluded X) **persists via 4b whenever a type hint is present and any descriptor token matches**. REPRODUCED RESULT: Probe A NB-H-06 C1, and synthetic `"the other scan"` + type `pdf` + single `scan_0034.pdf` → RAR-SAFE binds via `TYPE_FILTER`. On the real corpus row (no coarse type), the correct RAR-SAFE abstention comes from Level 6 treating `"other"` as an absent entity. That is a correct outcome for an incidental reason (§18 U4).
- Plan match: yes.

## 8. Cascade-integrity audit

REPRODUCED RESULT: an AST-extracted unified diff of `resolve_rar_deterministic_extended` vs `resolve_rar_safe_experimental` shows only:

1. Docstring and comment edits.
2. Refactor of the candidate-token union into `_candidate_tokens()`. Equivalence verified: title ∪ domain tags ∪ aliases, as in baseline Levels 3/4b/6.
3. S3 condition (`and eliminated_ids`).
4. S1 restructuring of the 4b singleton branch. The non-empty-substantive path is logically identical to baseline.
5. S2 wrappers at four Level-5 commit points.

Level order, return types, `RARResolution` fields, `rule_used`/`failure_class` semantics, `validate_rar_resolution` invocation, and Level 7 are unchanged. Abstentions are explicit `UNKNOWN`/`AMBIGUOUS` values, not exceptions. Instrumentation (`perf_counter`) is outside decision logic.

**Semantic change the report understates:** S1 and S2 do not "return abstention". They **fall through** to later levels with a changed pool (S1 narrows to the singleton). Later levels can therefore resolve what an earlier gate refused: L5 recency, L5.5 attachment, or L6 type-word match (§5). The report's "structural contract and cascade ordering remain identical" is true for ordering and contract. It is not true for reachability: RAR-SAFE creates new paths into Levels 5, 5.5, and 6 for pools that baseline would have bound at 4b or 5.

## 9. 79-case reproduction

REPRODUCED RESULT: `run_battery()` + `compute_aggregates()` (imported, `main()` not called) produced 900 records over 79 cases. The records are **identical to the authoritative telemetry on every field except `latency_ms`**. Every aggregates key except the probe block matches exactly. Corpus SHA-256 is `0ea5447354481041181538244ef70b6dc58a72267dd95263d61dbdb55ab07380` pre- and post-run, the same value recorded since A2.8D. VERIFIED FACT: the scoring helpers (`_classify`, `build_query`, and the logic of `find_matching_found_expr`/`boundary_violation`) are identical to `scripts/m35_a2_8h_run.py` (AST comparison; differences are docstrings only).

## 10. Baseline vs RAR-SAFE aggregate comparison

REPRODUCED RESULT (n=84 ground-truth rows per variant per condition):

| Cell | Correct | ICB | Correct abstention (+family mismatch) | Missed resolvable | Silent miss* |
|---|---|---|---|---|---|
| RAR C1 | 22 | 1 | 15 + 3 | 34 | 10 |
| RAR-SAFE C1 | 18 | 0 | 16 + 3 | 38 | 10 |
| RAR C2 | 13 | 1 | 17 + 8 | 36 | 10 |
| RAR-SAFE C2 | 13 | 0 | 17 + 8 | 37 | 10 |
| C3 (both) | 0 | 0 | 75 | — | 10 |

\* One of the 10 "SILENT_DETECTION_MISS" rows is a `NO_REFERENCE` row with no detection (a scoring-label quirk inherited from A2.8H). This is why the report's §5 columns sum to 85 over n=84. It is non-material.

Report arithmetic errors (non-material): §1 says "26/84 = 26.19%"; the correct figure is 22/84 = 26.19% (A2.8I also records 22/84).

Full paired transition list at C1/C2: exactly 6 case:refs change between variants. No other row changes on any field (§11, §12). `DETECTOR_FALSE_POSITIVE_BINDING` = 0, invented candidates = 0, boundary violations = 0 for both variants.

## 11. Case-level audit — incorrect confident bindings (headline 2 → 0)

| # | Case | Cond | Baseline | Expected | RAR-SAFE | Safeguard | Safer? |
|---|---|---|---|---|---|---|---|
| 1 | NB-B-05:r1 | C2 | RESOLVED `obj-c06f97` ("Query on invoice INV-20417", the only email) via TYPE_FILTER | RESOLVED `obj-d58a27` (Q3 budget summary; "that" = last discussed) | UNKNOWN / PRONOUN_BINDING (L6) → MISSED_RESOLVABLE_CASE | S1 | Yes. The binding was wrong; the abstention is honest. The `email` type hint came from D1RQ crossing the preposition ("that **in an email**"), so the type described the destination, not the referent. |
| 2 | NB-H-06:r1 | C1 | RESOLVED `scan_0034.pdf` via CONTRAST_FILTER with **zero eliminations** (the pool started at size 1) | UNKNOWN (the "other scan" is not in the pool) | UNKNOWN / NO_CANDIDATE (L6) → CORRECT_ABSTENTION | S3 | Yes. The final abstention is triggered by L6 treating `"other"` as an absent entity (§7). |

REPRODUCED RESULT: the headline claim **2 → 0 ICB at C1+C2 is true**, attributable to S1 (1) and S3 (1), with **S2 contributing 0**.

## 12. Case-level audit — the four corpus coverage losses (all C1, all S1)

Common mechanism (REPRODUCED): the D1RQ span is a determiner plus a type noun. The coarse type equals that noun. The pool holds exactly one candidate of that type. S1 sees zero substantive tokens and narrows to the singleton. Level 6 sees no substantive tokens and returns UNKNOWN / PRONOUN_BINDING. The baseline bound the correct candidate via TYPE_FILTER.

| Case | Span / pool | Why baseline was right | Why SAFE abstains | Justified by invariant? | Auditor classification |
|---|---|---|---|---|---|
| NB-E-01:r1 | "the spreadsheet"; roster.xlsx + 2 PDFs | Explicit definite description; the type is unique in the pool; no contradicting evidence | S1 zero-substantive | Yes, literally | Unnecessary coverage regression (over-conservative) |
| NB-E-02:r1 | "the PDF"; 1 PDF + xlsx + docx | Same | Same | Yes, literally | Unnecessary coverage regression |
| NB-E-03:r1 | "the email" (D1RQ dropped "from Priya"); Onboarding-dates email + **Priya Nair contact record** | Same | Same | Yes, literally | Unnecessary coverage regression. The report's rationale is **factually wrong**: it says the pool "has no person-record candidate", but the C1 pool contains `obj-0e93c8` "Contact: Priya Nair - HR". "Priya" never reached RAR because the span is only "the email". |
| NB-L-03:r1 | "the spreadsheet"; roster.xlsx + lease PDF ("Two files there") | Same | Same | Yes, literally | Unnecessary coverage regression |

AUDITOR INTERPRETATION: the four losses and the one S1 gain do **not** differ in pool composition, as report §11 claims. They differ in **where the type hint came from**:

- In the four losses, the type word is the head of the user's own definite description.
- In NB-B-05, the span head is a pronoun ("that") and the type word sits in a trailing prepositional phrase captured by a detector boundary error.

A deterministic refinement could plausibly recover all four without reopening NB-B-05: treat the type word as evidence only when it is the head noun of a determiner phrase, not when the span head is a pronoun. The 6 Probe A S1 losses (pronoun spans "it", "that", "she", "this" with oracle types) would correctly stay abstentions under such a rule. This is **UNMEASURED**: it was analysed, not implemented or run. No plan threshold exists, so the 4 losses do not by themselves fail acceptance. They do mean S1 is over-broad relative to the evidence actually present.

## 13. Counterfactual probe audit

REPRODUCED RESULT: all three probes are bit-identical to `AGGREGATES.json::counterfactual_probes`.

**Probe A — recency truthful-rank (60 rows).** REPRODUCED: ICB 10 → 3; **correct 23 → 9**.

- What Probe A proves: once real ranks exist, S2 plus S1 remove 7 of 10 recency-era ICBs on oracle queries.
- What Probe A does not prove: that S2 detects *contradiction*. Of the 7 closures, only 3 come from genuine lexical contradiction:
  - NB-J-02 ("contract", "jonas")
  - NB-J-04 ("template")
  - NB-D-01 C2 ("minutes" is on another candidate)
- The other 4 closures come from temporal or attachment function words firing the gate:
  - NB-D-02 C2 (`before`)
  - NB-L-09 C2 (`uploaded`, `before`)
  - NB-C-05 C1 and C2 (`attached`)
- **14 correct resolutions are lost** in Probe A. **The execution report does not disclose this.** Report §6 writes "Correct resolutions | (baseline; recorded in telemetry) | unchanged where S2 does not fire", while the aggregates file it cites records `correct_before_RAR: 23, correct_after_RAR_SAFE: 9`. The losses are:
  - S1, 6 rows: NB-B-01, NB-B-04, NB-B-05, NB-C-02, NB-G-01, NB-L-03 (all C1)
  - S2 false contradiction, 8 rows: NB-D-02 C1, NB-D-04 C1, NB-D-05 C1, NB-D-06 C1 and C2, NB-D-07 C1, NB-L-04 C1 and C2
- The 3 residual ICBs are REPRODUCED as disclosed: NB-C-04 C1 and C2 (L5 zero-evidence), and NB-H-06 C1 (4b partial match).

**Probe B — T2 perfect span (14 rows).** REPRODUCED: ICB 3 → 3 (NB-G-04:r1 C2, NB-I-02:r2 C2, NB-I-06:r2 C2, all via Level-6 TERM_DISCRIMINATION); correct 7 → 7. The probe correctly shows that perfect spans do not resolve the failure class, because Level-6 domain-tag scoring (New F) remains the limiting mechanism. It is a valid out-of-scope control. It also means the plan §2 hypothesis that one invariant "unifies ... New F" is **not supported**: nothing in the S1/S2/S3 set reaches New F.

**Probe C — NB-H-06 real D1RQ (2 rows).** REPRODUCED: ICB 1 → 0. It isolates the shortcut mechanism on the real query, and S3 addresses that mechanism causally. It does not test the typed variant, where the hazard persists (Probe A, §7).

Tests-encode-implementation check: the probes use frozen corpus labels and the harness's pre-existing oracle query builder. No expectation was derived from RAR-SAFE output. VERIFIED FACT.

## 14. Benchmark-contamination analysis

- The corpus hash is unchanged since A2.8D. VERIFIED FACT.
- Scoring logic is identical to A2.8H. VERIFIED FACT.
- No case IDs appear in executable RAR-SAFE logic; they appear in comments only (lines 34, 56, 400). VERIFIED FACT.
- Both variants use the same queries, pools, and classifier. VERIFIED FACT.
- Aggregates include all rows. `regressions_new_icb_under_safe` checks only transitions into ICB. This audit's full transition scan found no other changed rows. VERIFIED FACT.
- No relabeling or post-hoc expectation change was found.

**Conclusion: no benchmark contamination.**

## 15. Regression-test reproduction

- REPRODUCED RESULT: the five named files run against baseline RAR give **75 passed, 48 subtests passed, 0 failed**. This matches the report.
- **Additional check not performed by the implementer.** This audit ran the same five files with `resolve_rar_deterministic_extended` swapped for `resolve_rar_safe_experimental` (scratchpad pytest plugin; no file edited). Result: **7 failed** (3 tests + 4 subtests), 72 passed, 44 subtests passed.

| Test / fixture | Query | Cause | Conflict type |
|---|---|---|---|
| `test_level_4_type_filtering_single_match` | "the workflow", type workflow | S1 | Test encodes the singleton type-filter binding that S1 intentionally removes. Invariant vs test. |
| RAR-FIX-02 | "the email", type email | S1 | Same |
| RAR-FIX-20A | "that file", type document | S1 | Same (pronoun head, closer to NB-B-05) |
| RAR-FIX-20B | "him", type person | S1 | Same |
| `test_level_5_revision_relation` | "the revised draft" | S2 (`draft`) | S2 false contradiction. `draft` is one of RAR's own revision words. |
| RAR-FIX-13 | "the earlier version" | S2 (`version`) | S2 false contradiction |
| `test_rc1_current_unique_recency_resolves` | "the current version" | S2 (`version`) | S2 false contradiction |

Plan §6 criterion 3 requires that conflicting tests are "flagged, not silently edited — the report states whether the invariant, the test, or the contract is wrong." The tests were not edited (VERIFIED FACT), but no conflict was flagged or classified. **Criterion 3 is not fully met.**

## 16. Byte-integrity verification

REPRODUCED RESULT (SHA-256, computed by this audit):

- `uri_v1/turn/rar_deterministic.py` = `e02af25bb7009d12d829c8b8fc92e487d3da75aeaa160092db617458278fb649`
- `uri_v1/turn/rar_contracts.py` = `4cc9aa43726a870ca2e9ab1b19f6bf9d72dcb74c8a2818856776af95195b6819`
- `scripts/m35_a2_8h_detector_d1rq.py` = `49f5faa9b37051fec876f5523383b4e965422976562c52e12fc38c970bfa6b82`

All three equal the values independently recorded in `M35_URIV1_A2_8I_POST_REPAIR_END_TO_END_RESIDUAL_AUDIT.md` lines 43–45, written before A2.8J. `rar_contracts.py` also matches the Stage-4B reports. The hashes were unchanged after all audit runs.

Evidence gap: git does not track these files, so byte identity to A2.8I is proven, but identity to any earlier state is not attested by git.

## 17. Known residual analysis

1. **Level-5 zero-substantive recency (NB-C-04).** REPRODUCED: `"the attachment"`, type image, two images → binds rank-0 `site_photo_02.jpg` via TEMPORAL_RELATION at C1 and C2. Expected AMBIGUOUS. S2 returns False on empty substantive tokens by design.
   - Can cause ICB: yes, once recency is wired.
   - Affects C1 and C2 in Probe A only.
   - Outside the literal S1/S2/S3 scope, but inside hypothesis clause 2 ("no binding on zero substantive evidence").
   - Does not invalidate the accepted-scope patches. It does block any claim that the invariant is enforced.
   - Suitable as a subsequent experiment.
   - Same mechanism produces a correct binding at Probe A NB-C-02 C2 ("this" → the rank-0 image), which shows the coverage cost that closing it will carry.
2. **Level-6 domain-tag cross-entity preference (New F).** REPRODUCED (Probe B): 3 ICBs, unchanged. Latent on the corpus, because it depends on T2 detection that does not exist. Outside A2.8J scope. Suitable as a subsequent experiment.
3. **4b partial-match binding (report §15 item 2).** Disclosed, but **mis-categorised** as "Known-D-adjacent" coverage, which plan §3 froze out. AUDITOR INTERPRETATION: this is a *safety* violation of hypothesis clause 1. Level 6's absent-entity / all-substantive-matched rule would reject the 4b binding (`other`, `last`, `week` unmatched), so it is exactly "a binding that the resolver's own Level-6 evidence contradicts." It is not a Known C/D coverage issue.

## 18. Undisclosed residuals and observations

- **U1 (material). S2 false-contradiction class.** Temporal, revision, and attachment function words are treated as absent entities (§6). This suppresses valid recency bindings: 8 Probe A rows and 3 existing tests. It also makes 4 of S2's 7 Probe A safety gains incidental.
- **U2. S1 is not cascade-wide.** Zero-substantive bindings (by S1's own definition) remain reachable at L6 (type word in title) and L5.5 (attachment flag) after S1 narrows the pool (§5). Not observed on the corpus. No worse than baseline.
- **U3. Contrast semantics are ignored at 4b.** "the other X" can bind the excluded X through the ordinary 4b path when a type hint is present (§7).
- **U4. Incidental correctness.** The real-corpus NB-H-06 C1 abstention depends on `"other"` being counted as an absent entity at L6. A candidate whose title or tags contain "other" would change this.
- **U5. Root cause of NB-B-05 is a detector boundary error.** D1RQ's span crosses a preposition. S1 compensates at RAR level with a blunt rule, which is the source of the 4 corpus losses (§12). D1RQ repair is frozen out of A2.8J. OUT-OF-SCOPE OBSERVATION.
- **U6. S2 is inert on the natural corpus** (0 invocations). The headline result says nothing about S2.
- **U7. Rejected competitors are not in telemetry.** Telemetry does not persist `candidate_scores` or `eliminated_candidate_ids`, so report §10 Q2 ("recorded in trace") cannot be verified from the committed evidence.
- Stale session/context effects: RAR is stateless per call, and Level 3 ("same") is unchanged. **UNMEASURED**; no corpus row exercises Level 3.
- Ambiguity collapse: no RAR-SAFE row changed AMBIGUOUS→RESOLVED or RESOLVED on ambiguous input. VERIFIED FACT (transition scan).

## 19. Safety-versus-coverage interpretation (AUDITOR INTERPRETATION)

On the natural corpus the safety gain is real: 2 active ICBs are closed, with 0 regressions, at a cost of 4 correct C1 resolutions. The losses come from an over-broad S1, not from missing evidence.

In the recency counterfactual, the variant trades 14 correct resolutions for 7 ICB closures. About half of those closures come from spurious contradiction signals, not genuine contradiction. S2 as built behaves less like a contradiction gate and more like a near-total veto on Level 5 for natural temporal phrasing. That can look safe on the ICB metric while leaving the "contradictory lexical evidence" hypothesis untested.

A near-veto is not the evidence-sufficiency invariant the plan set out to test. It also undercuts the report's recency recommendation ("S2 closes 7 of 10"), because the same gate would block most correct temporal resolutions. This conclusion does not depend on any numeric threshold.

## 20. Deviations / concerns (consolidated)

| ID | Severity | Finding |
|---|---|---|
| D1 | Material (reporting / criteria 7, 8) | Probe A coverage loss 23→9 undisclosed; report §6 wording replaces a measured value |
| D2 | Material (criterion 3) | 7 existing-test conflicts with RAR-SAFE not flagged or classified |
| D3 | Material (experiment validity) | S2 exclusion set contradicts RAR's own existing temporal/revision/attachment vocabulary, yet is justified in the report as RAR's closed vocabulary. The S2 hypothesis result is confounded by false contradictions. |
| D4 | Moderate (reporting) | §2 "hypothesis verified" overclaims: New F untouched; clause 1 violated at 4b; clause 2 violated at L5 and L6 |
| D5 | Moderate (reporting) | §15 item 2 mis-categorised as Known C/D (coverage) instead of a clause-1 safety residual |
| D6 | Minor (reporting) | NB-E-03 rationale wrong (Priya contact record is in the pool); "26/84" should be 22/84; "8-word" list has 9 words; §5 columns sum to 85 over n=84; S2's zero corpus invocations not stated |
| D7 | Minor | Fall-through reachability change (§8) is not described |

No implementation defect was found against the literal S1/S2/S3 mechanisms of plan §5, apart from D3's vocabulary justification. The implementation is isolated and plan-faithful in structure.

## 21. Final verdict

**REPAIR_REQUIRED**

The reason is not the safety claim itself: the main-corpus result reproduces exactly, and 2→0 ICB is genuine. The reasons are:

1. Plan §6 criteria 3, 7, and 8 are not met (D1, D2).
2. S2's measured effect is confounded by a vocabulary choice that the report misattributes to RAR's own semantics (D3).
3. The report's hypothesis conclusion and the classification of one residual are not supported by the evidence (D4, D5).

Required repairs (to be routed for implementation, not performed by this auditor):

- **R1.** Disclose Probe A correct-resolution counts (23→9) in the execution report and audit all 14 Probe A coverage losses individually, attributing each to S1 or S2 (plan §6 criterion 7).
- **R2.** Run the five existing RAR test files against RAR-SAFE (without editing them). Report all 7 conflicts and state for each whether the invariant, the test, or the contract is wrong (plan §6 criterion 3).
- **R3.** Resolve the S2 exclusion-set confound. Either:
  - (a) Align `_RECENCY_VOCABULARY` with RAR's existing temporal/revision/attachment vocabulary (`classify_unresolved_failure` `revision_words` ∪ `temporal_words`, Level 5.5 attachment triggers). This follows plan §5's "RAR's own existing semantics" instruction; re-run Probe A and both variants.
  - (b) Keep the set unchanged, correct the report's justification, and report per-closure which token fired the gate, separating genuine contradictions from function-word hits.

  **User or architect decision needed on (a) vs (b).** Option (a) changes RAR-SAFE code within S2's stated scope; option (b) is reporting-only.
- **R4.** Restate report §2: the invariant is not enforced cascade-wide (4b partial match, L5 zero-evidence, L6/L5.5 fall-through), and New F is not reached by it.
- **R5.** Reclassify report §15 item 2 as a clause-1 safety residual.
- **R6.** Correct the D6 factual errors and add the S2 zero-invocation fact and the fall-through reachability note (D7).

After R1–R6, re-audit: bounded to re-reproduction of any regenerated artifacts and review of the revised report.

## 22. Required next action

Route R1–R6 through Antigravity to the implementer, per standing AO-4 roles. The auditor performs no repair. R3 needs a User/architect choice between (a) and (b) before routing. No commit, no push, no promotion of RAR-SAFE, and no A2.8K work until re-audit returns ACCEPTED.
