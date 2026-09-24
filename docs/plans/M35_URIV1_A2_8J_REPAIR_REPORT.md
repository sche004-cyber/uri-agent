# M35 URIv1 — A2.8J: Bounded Repair Report (R1–R6)

**Status:** `VERIFICATION_READY`
**Repair authority:** Claude, exercising AO-4 bounded-fix authority (same session that performed the independent final audit) per the User's explicit bounded-repair directive selecting R3(a).
**Governing documents (all treated as authoritative, read before any change):** `docs/plans/M35_URIV1_A2_8J_RAR_SAFE_QUALIFICATION_PLAN.md`, `docs/plans/M35_URIV1_A2_8J_INDEPENDENT_FINAL_AUDIT.md`, `docs/plans/M35_URIV1_A2_8J_STATE.md`, `docs/plans/M35_URIV1_A2_8J_EXECUTION_REPORT.md`.
**Full detail:** the R3(a) REPAIR ADDENDUM appended to `docs/plans/M35_URIV1_A2_8J_EXECUTION_REPORT.md` contains the complete measurement tables this report summarizes. This document is the required standalone repair report; the addendum is the primary evidence record (auditable correction history — original report body preserved, not overwritten).

This was a bounded repair pass. No redesign, no new experiment, no scope broadening.

---

## 1. Exact files changed

**Code (one file, one constant):** `uri_v1/turn/rar_safe_experimental.py` — only the `_RECENCY_VOCABULARY` module-level set was widened from 9 words to 19 words (10 added). No other line changed. S1, S3, cascade ordering, and all other S2 logic (call sites, both contradiction clauses) are byte-for-byte unaffected.

**Regenerated (overwritten in place, per the frozen scripts' own design — not hand-edited):**
- `docs/plans/M35_URIV1_A2_8J_TELEMETRY.json` (natural-corpus battery, 900 rows)
- `docs/plans/M35_URIV1_A2_8J_AGGREGATES.json` (natural-corpus aggregates + `counterfactual_probes` block)

**Documentation (addenda appended, not overwritten):**
- `docs/plans/M35_URIV1_A2_8J_EXECUTION_REPORT.md` — R3(a) REPAIR ADDENDUM appended; 3 isolated factual-typo corrections applied inline and marked; original body otherwise preserved verbatim
- `docs/plans/M35_URIV1_A2_8J_STATE.md` — to be updated to reflect this repair (see below)
- `docs/plans/M35_URIV1_A2_8J_REPAIR_REPORT.md` — this file (new)

**Not changed:** `uri_v1/turn/rar_deterministic.py`, `uri_v1/turn/rar_contracts.py`, `scripts/m35_a2_8h_detector_d1rq.py`, `uri_v1/turn/rar_natural_boundary_raw_turn_fixtures.json`, any test file, `scripts/m35_a2_8j_rar_safe_battery.py`, `scripts/m35_a2_8j_counterfactual_battery.py`.

## 2. R1 resolution — Probe A disclosure

Pre-repair Probe A (oracle recency, n=60): **correct resolutions 23 → 9, ICB 10 → 3.** This 14-row coverage loss was measured by the original implementer's own script and written to the committed aggregates file, but was not disclosed in the execution report's prose, which said only "unchanged where S2 does not fire." All 14 losses are now individually attributed (6 to S1, 8 to S2) in the execution-report addendum, §"R1: Probe A disclosure." Post-repair, all 14 remain present (the repair's added vocabulary words do not intersect any of these 14 spans) — Probe A was regenerated, not assumed unchanged, and the regenerated result is reported, not the pre-repair number.

## 3. R2 conflict classification

Existing five-file RAR test suite run against RAR-SAFE (in-process swap; no test file edited):

- **Pre-repair: 7 conflicts** (3 tests/subtests failing on S1, 3 on S2 — RAR-FIX-02/20A/20B + `test_level_4_type_filtering_single_match` = S1; RAR-FIX-13, `test_level_5_revision_relation`, `test_rc1_current_unique_recency_resolves` = S2).
- **Post-repair: 4 conflicts**, all S1-caused, unchanged from pre-repair, and classified as **intentional consequences of the frozen S1 invariant** — each test encodes exactly the zero-substantive singleton-type binding S1 is designed to refuse. Not a regression. Not repaired (S1 is out of scope for R3).
- The 3 S2-caused conflicts are **fixed** by R3(a) — verified by direct test rerun, no expectation changed.
- Baseline RAR (unswapped) unaffected: **75 passed, 48 subtests passed, 0 failed**, reconfirmed after the repair.

Full per-test table: execution-report addendum, §"R2."

## 4. R3(a) implementation explanation

`_RECENCY_VOCABULARY` in `rar_safe_experimental.py` widened from the original 9-word RC-1-literal set to include 10 words drawn from three existing baseline-RAR non-entity-discriminating word sets: `classify_unresolved_failure`'s `revision_words` (`rar_deterministic.py:196`: `revision, draft, version, v1, v2`) and `temporal_words` (`rar_deterministic.py:201`: `first, last, prior`), and Level 5.5's `_ATTACHMENT_TRIGGER_TOKENS` (`rar_deterministic.py:711`: `attached, attaches`; `attachment` was already covered by `GENERIC_TYPE_WORDS`). No word outside these three baseline sources was added. `rar_deterministic.py` itself was not touched — the values are local to a function body there and cannot be imported without editing that frozen file, so they are reproduced with an explicit line-number citation for traceability instead.

## 5. Source of RAR semantic vocabulary/logic used by S2

See §4 above and execution-report addendum §"Source of the S2 vocabulary." In full: `rar_deterministic.py` lines 196, 201, 711 — quoted verbatim, cited by line number, not independently invented. The audit's own example words (`version`, `draft`, `attached`, etc.) were used only as a pointer to locate these baseline definitions, per the directive; they were not copied as authority by themselves, and the resulting set is a strict superset of what strict baseline-derivation produces (confirmed: every audit example word is present in one of the three cited baseline sets).

## 6. R4 corrected hypothesis conclusion

The plan's single unifying evidence-sufficiency invariant is **not established as a cascade-wide enforced property**, before or after this repair:

- S1 enforces "no zero-evidence binding" only at Level 4b.
- S2 enforces "no binding against contradictory evidence" only at Level 5's four single-match branches, and (even post-repair) only for tokens in baseline RAR's existing recognized vocabulary — ordinary descriptive words like `before`, `older`, `recent` remain unguarded, a disclosed limitation, not silently patched.
- S3 fixes the contrast shortcut causally; the ordinary 4b partial-match path is unguarded (see R5).
- Level 6 (New F) is entirely untouched, confirmed unchanged by Probe B (3→3 ICB, bit-identical pre/post repair).

Full corrected framing: execution-report addendum, §"R4."

## 7. R5 corrected safety classification

"The other scan" / `NB-H-06`'s Probe-A oracle-shape residual, originally filed under out-of-scope Known-C/D coverage, is reclassified as a **safety** finding: Level 4b's ordinary substantive-match path can commit a binding that Level 6's own absent-entity rule would refuse if reached — a clause-1 violation of the hypothesis at a commit point neither S1 nor S3 addresses. **Not repaired in this pass** (explicitly out of scope, per directive §5); preserved as evidence, execution-report addendum §"R5."

## 8. R6 factual corrections

Applied and marked in place in the execution report: (a) "26/84" → "22/84" in §1; (b) "8-word" → "9-word" recency-vocabulary count in §3.2, with the accompanying "this is RAR's own complete non-entity vocabulary" claim corrected per R4; (c) NB-E-03's §11 rationale corrected — the C1 pool does contain a person-record candidate (`obj-0e93c8`), the real reason RAR-SAFE cannot use "Priya" is that D1RQ's detected span excludes it, a detector-boundary characteristic. Fall-through behavior (S1/S2 declining to bind hands the narrowed pool to the next cascade stage, which can still resolve independently) is now stated explicitly. A full-document search for other instances of these three mistaken assumptions found none beyond the ones corrected.

## 9. Pre/post telemetry comparison

| Metric | Baseline RAR | RAR-SAFE pre-repair | RAR-SAFE post-repair |
|---|---|---|---|
| Natural corpus ICB (C1+C2) | 2 | 0 | **0 (unchanged)** |
| Natural corpus coverage losses | — | 4 | **4 (unchanged, same 4 cases)** |
| Natural corpus regressions | — | 0 | **0 (unchanged)** |
| S2 invocations, natural corpus | — | 0 | **0 (unchanged)** |
| Probe A ICB (n=60) | 10 | 3 | **5** |
| Probe A correct (n=60) | 23 | 9 | **9 (unchanged)** |
| Probe A S2 invocations | — | 23 | 23 (unchanged count; 16→14 contradictions found, 7→9 passed through) |
| Probe B ICB (n=14) | — | 3 | **3 (unchanged)** |
| Probe C ICB (n=2, C1) | 1 | 0 | **0 (unchanged)** |
| Existing-test conflicts vs RAR-SAFE | — | 7 | **4** |

Corpus/frozen-file SHA-256 hashes unchanged throughout (see §15).

## 10. Natural-corpus results

**Unaffected by R3(a).** ICB 2→0 (`NB-B-05:r1@C2` via S1, `NB-H-06:r1@C1` via S3), 4 coverage losses (`NB-E-01/E-02/E-03/L-03:r1@C1`, all S1, factual correction to NB-E-03's rationale applied per R6), 0 regressions, 0 invented candidates, 0 boundary violations. S2 fires 0 times on this corpus (all candidates have `recency_rank=0`, so Level 5's `has_ordering` gate is never satisfied) — confirmed by direct instrumentation before and after the repair.

## 11. Probe A results

Regenerated post-repair: n=60, ICB 10→5 (was 10→3), correct 23→9 (unchanged). Full 14-loss / 5-gain / 2-regressed-gain case table in the execution-report addendum. The 2-row regressed gain (`NB-C-05:r1`, C1 and C2) is a newly demonstrated instance of the already-known, already-out-of-scope Level-5 zero-substantive-evidence gap (§17 below) — not a new hazard class, and not repaired.

## 12. Probe B results

Unaffected. ICB 3→3, correct 7→7, bit-identical to pre-repair. None of the 7 T2 target spans contain any repaired-vocabulary word.

## 13. Probe C results

Unaffected. ICB 1→0 at C1 (unchanged), C2 remains CORRECT_ABSTENTION. `oracle_recency=False`, so no Level-5 branch is exercised.

## 14. RAR-SAFE test conflicts after repair

4 remaining, all S1-caused, all classified as intentional consequences of the frozen S1 invariant (not regressions, not repaired): `test_level_4_type_filtering_single_match`, and RAR-FIX-02/20A/20B (subtests of `test_all_24_diagnostic_fixtures_pass`). Full table in execution-report addendum §"R2."

## 15. Protected-file hashes

| File | SHA-256 |
|---|---|
| `uri_v1/turn/rar_deterministic.py` | `e02af25bb7009d12d829c8b8fc92e487d3da75aeaa160092db617458278fb649` |
| `uri_v1/turn/rar_contracts.py` | `4cc9aa43726a870ca2e9ab1b19f6bf9d72dcb74c8a2818856776af95195b6819` |
| `scripts/m35_a2_8h_detector_d1rq.py` | `49f5faa9b37051fec876f5523383b4e965422976562c52e12fc38c970bfa6b82` |
| `uri_v1/turn/rar_natural_boundary_raw_turn_fixtures.json` | `0ea5447354481041181538244ef70b6dc58a72267dd95263d61dbdb55ab07380` |

All four match the values independently recorded pre-A2.8J (A2.8I audit) and re-verified both before and after this repair. No unexpected modification occurred (stop condition not triggered).

## 16. Remaining known residuals (preserved, not repaired)

1. **Level-5 zero-substantive-evidence recency** (`NB-C-04`, now also concretely demonstrated by `NB-C-05` post-repair) — out of scope per directive §5.
2. **Level-6 cross-entity / New-F scoring** — Probe B retains 3 ICBs, untouched.
3. **4b ordinary-path partial-match binding** ("the other scan" residual) — reclassified as safety (R5), not repaired.
4. **S2's exclusion vocabulary does not cover non-baseline descriptive words** (`before`, `older`, `recent`, `thing`, `most`, `used`, `invoice`) — 14 Probe A losses remain; closing this would require inventing vocabulary beyond baseline derivation, explicitly out of scope.

## 17. Newly discovered residuals

**`NB-C-05:r1` (C1 and C2)** — a concrete, previously-undemonstrated instance of the pre-existing Level-5 zero-substantive-evidence gap (item 16.1 above), surfaced because excluding `attached` from S2's substantive-token computation (a correct, baseline-derived exclusion) removes the last incidental block on this query shape. No other newly discovered residual was found in this repair pass. Full explanation: execution-report addendum, "Newly discovered residual."

## 18. Evidence gaps / UNMEASURED hypotheses

- Generalization of the natural-corpus zero-`RESOLVED`-from-gated-levels result beyond this 79-case corpus: UNMEASURED.
- Representativeness of the natural-corpus 4:1 coverage-loss-to-safety-gain ratio on larger/differently-composed candidate pools: UNMEASURED.
- Whether an S1 phrase-head-position refinement would recover the 4 natural-corpus losses without reopening `NB-B-05`: UNMEASURED, explicitly not implemented (directive §4).
- Whether expanding S2's vocabulary beyond baseline-RAR's own existing word sets would recover more Probe A losses without reintroducing false safety: UNMEASURED, explicitly out of scope (would require inventing vocabulary).

## 19. Final repair status

**`VERIFICATION_READY`.** R1–R6 complete, bounded exactly to what the directive authorized. No commit, no push, no merge, no promotion of RAR-SAFE, no start of A2.8K. `NB-C-04`/`NB-C-05`'s Level-5 gap, New F/Level-6 scoring, and the S1 phrase-head refinement were explicitly not repaired, per the directive. Awaiting the independent auditor's bounded re-audit of this repair, the execution-report addendum, and the regenerated telemetry/aggregates.
