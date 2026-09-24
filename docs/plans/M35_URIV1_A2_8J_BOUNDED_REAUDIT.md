# M35 URIv1 — A2.8J: Bounded Independent Re-Audit of R1–R6

**Auditor:** Claude (Opus 5.5)
**Date:** 2026-09-24
**Prior verdict:** REPAIR_REQUIRED (`docs/plans/M35_URIV1_A2_8J_INDEPENDENT_FINAL_AUDIT.md`)
**Audited repair:** `docs/plans/M35_URIV1_A2_8J_REPAIR_REPORT.md` plus the R3(a) REPAIR ADDENDUM in `docs/plans/M35_URIV1_A2_8J_EXECUTION_REPORT.md`
**Verdict:** **ACCEPTED** (experimental result accepted; this is not a promotion recommendation for RAR-SAFE as a whole — see §15)

Labels: **VERIFIED FACT**, **REPRODUCED RESULT**, **AUDITOR INTERPRETATION**, **UNMEASURED**, **OUT OF SCOPE**.

**Independence disclosure.** The R1–R6 repair was carried out in the same conversation as this audit, by Claude acting under its AO-4 bounded-fix authority. The same agent is therefore re-auditing a repair it made. To offset this:

- Every claim below was re-derived mechanically from source, from the regenerated artifacts, and from pre-repair evidence kept in the audit scratchpad since the first audit (`audit_tel.json`, `audit_agg.json`, `audit_probes.json`).
- The repair boundary was proven byte-for-byte rather than taken from the repair report.

The User may still want another reviewer. This disclosure does not change the verdict.

---

## 1. Repair-boundary verification

- **VERIFIED FACT (byte-level):** in the current `uri_v1/turn/rar_safe_experimental.py` (SHA-256 `4d9317311bdda0eaabc4ff5277bd3ac8b7628d83871dbd2da607954d946032a5`), put back only the original `_RECENCY_VOCABULARY` comment and assignment block, keeping LF line endings. The result hashes to `670d4e9c67cd7ff7a4f5e741baf38ab4be2b05d883716a1797dbfe76ab5d51cd`, exactly the pre-repair hash recorded in the first audit. Nothing else in the file changed:
  - S1, S3, and the S2 call sites and clauses are unchanged.
  - Cascade order is unchanged.
  - No case-specific logic was added.
- **VERIFIED FACT:** `_RECENCY_VOCABULARY` evaluates to 19 words. The 10 added words are `revision, draft, version, v1, v2, first, last, prior, attached, attaches`. None was removed.
- **VERIFIED FACT:** the runner and probe script hashes are unchanged from the first audit:
  - `m35_a2_8j_rar_safe_battery.py` `45047e05…`
  - `m35_a2_8j_counterfactual_battery.py` `fd55363a…`

  The harness (`6d666873…`, last modified 05:55) and `rar_fixtures.py` (last modified 2026-09-21) are older than the plan. No expected outcome, probe, or query builder was weakened.
- **VERIFIED FACT:** the plan's last-modified time (13:48) predates both the first audit and the repair, so the plan is unchanged. The five test files' last-modified times are 2026-09-21/22, so they are unchanged. HEAD is still `e8e3b65`, with no commit or push.
- **OUT OF SCOPE:** `tasks/m35_uriv1_a2_8j_sonnet_implementation_task.txt` (untracked, 14:01) predates both the implementation and the repair. It is a handoff file, not an artifact of the repair.

## 2. Protected-file integrity

REPRODUCED RESULT (SHA-256, after the repair):

| File | SHA-256 | Matches pre-A2.8J record |
|---|---|---|
| `rar_deterministic.py` | `e02af25bb7009d12d829c8b8fc92e487d3da75aeaa160092db617458278fb649` | yes |
| `rar_contracts.py` | `4cc9aa43726a870ca2e9ab1b19f6bf9d72dcb74c8a2818856776af95195b6819` | yes |
| `m35_a2_8h_detector_d1rq.py` | `49f5faa9b37051fec876f5523383b4e965422976562c52e12fc38c970bfa6b82` | yes |
| corpus fixture JSON | `0ea5447354481041181538244ef70b6dc58a72267dd95263d61dbdb55ab07380` | yes |

The baseline RAR test suite still passes: 75 passed, 48 subtests passed, 0 failed.

## 3. R1–R6 PASS/FAIL

| Repair | Result | Evidence |
|---|---|---|
| R1 Probe A disclosure | **PASS** | The addendum discloses 23→9 before and after the repair. All 14 losses are listed and attributed: 6 to S1 and 8 to S2 (reproduced). Trigger-token errata are in §8. |
| R2 test-conflict classification | **PASS** | All 7 pre-repair and 4 post-repair conflicts are classified (reproduced). Count errata are in §9. |
| R3 S2 vocabulary alignment | **PASS** | Only the vocabulary constant changed (§1). 18 of the 19 words trace to baseline RAR. `earliest` does not: it is a carry-over from the original implementation, it appears nowhere in `rar_deterministic.py`, and the repair's code comment discloses it as retained. No temporal, revision, or attachment vocabulary in baseline RAR was left out (see §3a). |
| R4 hypothesis conclusion | **PASS** | The addendum's R4 section now says the invariant is not enforced across the cascade. It names each gap: the 4b partial match, L5 zero evidence, L5.5/L6 fall-through, and New F. |
| R5 "other scan" classification | **PASS** | Now classified as a clause-1 safety residual, left unrepaired and kept as evidence. |
| R6 factual corrections | **PASS** | Corrected in place and marked: 22/84, the 9-word count, the NB-E-03 Priya Nair pool record, and the fall-through behavior. The original text is kept as correction history. |

### 3a. R3 source verification

- VERIFIED FACT: in `rar_deterministic.py`:
  - line 196 `revision_words = {revised, revision, draft, original, version, v1, v2}`
  - line 201 `temporal_words = {previous, earlier, latest, first, last, prior}`
  - line 711 `_ATTACHMENT_TRIGGER_TOKENS = {attached, attachment, attaches}`
- VERIFIED FACT: the other baseline literals are the Level 5 hint strings `revised/previous/earlier/latest/current` (lines 568–655), `same` at Level 3 (383), and `other` at Level 4a (487). All are present in the set.
- VERIFIED FACT: `attachment` is already excluded through `GENERIC_TYPE_WORDS`.
- VERIFIED FACT: `earliest` has 0 occurrences in `rar_deterministic.py` and none in the `rar_contracts.py` recency_hint comment. The harness maps `earliest`→`earlier`, and the word has no effect on any measured row.
- VERIFIED FACT: baseline RAR has no other temporal, revision, or attachment word set. The words `before`, `older`, `recent`, `most`, `thing`, and `used` appear in none of these sets.

AUDITOR INTERPRETATION: R3 aligned S2 with baseline semantics and did not tune it to the benchmark.

## 4. Natural-corpus reproduction

REPRODUCED RESULT:

- A new battery run matches the committed telemetry on every field except `latency_ms` (900/900 rows).
- The committed telemetry matches the **pre-repair** telemetry kept in the audit scratchpad (900/900).
- All aggregate keys match both the committed file and the pre-repair aggregates.

Unchanged results:

- **ICB 2→0**: NB-B-05:r1@C2 (S1) and NB-H-06:r1@C1 (S3).
- The same 4 coverage losses: NB-E-01, NB-E-02, NB-E-03, NB-L-03 at C1, all S1.
- 0 regressions, 0 invented candidates, 0 boundary violations.

**S2 invocations: 0** (instrumented).

VERIFIED FACT on the mechanism: this corpus uses `oracle_recency=False`, so every `recency_rank` is 0. Level 5's `revised` branch needs a `revised` token or tag, which never occurs here. `previous` needs rank==1, `earlier` needs rank>0, and `latest/current` needs `has_ordering`. None of these can be satisfied, so no single-match commit point that S2 guards is ever reached.

## 5. Probe A reproduction

REPRODUCED RESULT: n=60. The committed `counterfactual_probes` block matches the regenerated one exactly.

| | Baseline RAR | RAR-SAFE pre-repair | RAR-SAFE post-repair |
|---|---|---|---|
| ICB | 10 | 3 | **5** |
| Correct | 23 | 9 | **9** |
| S2 calls / contradiction returned | — | 23 / 16 | **23 / 14** |

The only rows that differ between pre- and post-repair are NB-C-05:r1 at C1 and at C2. Probe B (3→3 ICB, 7→7 correct) and Probe C (1→0) match the pre-repair evidence exactly.

## 6. All five post-repair Probe A ICBs

| # | Case | Oracle query | Expected (corpus rationale) | RAR-SAFE | Level | Guard opportunity | Why it stayed confident |
|---|---|---|---|---|---|---|---|
| 1 | NB-C-04:r1 C1 | "the attachment", hint `latest`, type image; two photos uploaded 1 s apart | AMBIGUOUS: "binding to either single photo is a wrong confident binding" | RESOLVED site_photo_02 (rank 0) | L5 `TEMPORAL_RELATION` | 4b had 2 type matches, so the multi-match branch ran and S1 did not apply. S2 was called with 0 substantive tokens and returned False by its own contract. S3 did not apply (no negation). | Nothing gates a zero-evidence recency commit at L5. The baseline makes the same binding. |
| 2 | NB-C-04:r1 C2 | same; 3-member pool | AMBIGUOUS | same binding | L5 | same | same |
| 3 | NB-C-05:r1 C1 | "the attached file", hint `latest`, type document; two re-attached docx files | AMBIGUOUS: "recency among the attachments must not be used to pick one" | RESOLVED Board_minutes_Sep (rank 0) | L5 | 4b multi-match (2 docs), so S1 did not apply. S2 had 0 substantive tokens and returned False. | Same zero-evidence L5 path. Baseline makes the same binding. |
| 4 | NB-C-05:r1 C2 | same; pool adds the Lease v2 draft (rank 0) | AMBIGUOUS | RESOLVED Lease_…_v2_draft.docx | L5 | 4b multi-match (3 docs). S2 returned False. | same |
| 5 | NB-H-06:r1 C1 | "the other scan, the one from last week", hint `earlier`, type pdf, negation "no, the other"; pool = {scan_0034.pdf} | UNKNOWN (the other scan is not in the pool) | RESOLVED scan_0034.pdf | L4b `TYPE_FILTER` (ordinary singleton path) | S3 blocked the contrast shortcut because nothing was eliminated. S1 ran, but 4b's substantive list is non-empty (`other, scan, last, week`), so the any-match rule bound on `scan`. S2 was never reached. | 4b ignores the unmatched tokens and the contrast marker. This is the R5 residual. |

VERIFIED FACT: the corpus's own `reason` fields for NB-C-04 and NB-C-05 say recency must not choose between these attachments. The ICB labels are therefore sound, and they were not changed.

## 7. NB-C-05 causal analysis

Each step of the reported mechanism was checked against the code and the instrumented gate:

1. `attached` is in baseline `_ATTACHMENT_TRIGGER_TOKENS` (line 711). **Correct.**
2. R3(a) excludes it from S2's substantive set. **Correct.** The instrumented gate saw `['attached']` before the repair and `[]` after.
3. S2 sees an empty substantive set. **Correct.**
4. An empty set means no contradiction (`rar_safe_experimental.py` returns False when there are no substantive tokens). **Correct.**
5. "S1 cannot help because it gates Level 4b rather than Level 5." **Correct but incomplete.** The more precise reason: S1 covers only the **singleton** branch of 4b, and this pool has 2 or 3 same-type candidates. S1 would not fire here even at 4b. It also has no Level 5 counterpart.
6. Level 5 `latest` binds rank 0. **Correct.**
7. Same hazard class as NB-C-04. **Correct.** Both are zero-substantive recency commits at L5.

Additional fact not stated in the repair: the pre-repair abstention happened only because S2 falsely treated `attached` as a missing entity. Control then fell through to L5.5, which saw two `is_attachment` candidates and returned AMBIGUOUS. L5 runs before L5.5, so an explicit attachment reference is intercepted by recency whenever a recency hint is present.

AUDITOR INTERPRETATION on attributing the change from 3 to 5 ICBs: this is **exposure of a pre-existing architectural gap, not a defect introduced by R3(a)**.

- Baseline RAR binds these two rows confidently as well.
- R3(a) removed a protection that was itself a result of the vocabulary defect the first audit flagged.
- The pre-repair "safety gain" on NB-C-05 was therefore an artifact and should not have been credited to S2.
- R3(a) did introduce a behavior change on these rows. It did not create the hazard.

## 8. The 14 Probe A coverage losses

REPRODUCED RESULT: the post-repair losses are the same 14 rows as before the repair.

- **6 from S1** (C1): NB-B-01, NB-B-04, NB-B-05, NB-C-02, NB-G-01, NB-L-03. Each is a pronoun or bare type span with an oracle type hint and a singleton type match.
- **8 from S2.** The tokens that fired the gate after the repair:

| Row | Token(s) that contradicted |
|---|---|
| NB-D-02 C1 "the one before that" | `before` |
| NB-D-04 C1 "the earlier agenda, the one we used before the September meeting" | `used`, `before` (the winner does contain agenda/september/meeting) |
| NB-D-05 C1 "the older version of the Harbour Street lease" | `older` **and `street`**. `street` is absent from the whole pool (titles say `St`), which is the Known-D abbreviation case the plan froze out. |
| NB-D-06 C1/C2 "the last thing you did for me" | `thing` |
| NB-D-07 C1 "the invoice before the latest one" | `before` (`invoice` is on the winner) |
| NB-L-04 C1/C2 "my most recent letter" | `most`, `recent` |

Recovering these would need one of the following:

- new non-entity vocabulary (`before`, `older`, `most`, `recent`, `thing`, `used`) that baseline RAR does not define;
- Known-D normalization (`St`/`Street`), which the plan freezes out;
- a change to S2's all-or-nothing absent-entity rule, which would be a redesign.

Each of these goes beyond the frozen plan. The refusal was correct and is not counted against the implementation.

AUDITOR INTERPRETATION: S2's contradiction test inherits Level 6's all-or-nothing absent-entity rule. For natural temporal phrasing, almost any descriptive word counts as a contradiction. That is a property of the hypothesis as specified, not an implementation defect.

## 9. Existing-test conflicts

REPRODUCED RESULT: with RAR-SAFE swapped in (no file edited) there are 4 failures: 1 test and 3 subtests. There were 7 before the repair. The 3 S2 conflicts now pass: `test_level_5_revision_relation`, RAR-FIX-13, and `test_rc1_current_unique_recency_resolves`.

| Remaining conflict | Query | Classification |
|---|---|---|
| `test_level_4_type_filtering_single_match` | "the workflow", type workflow | Intentional S1 consequence. The test assumes type uniqueness is enough to bind, which A2.8J deliberately challenges. It is also evidence that S1 is **too conservative** for a determiner + type-noun reference with no contradicting evidence. |
| RAR-FIX-02 | "the email", type email | Same as above |
| RAR-FIX-20A | "that file", type document | Intentional S1 consequence. The pronoun-headed span has the same shape as NB-B-05, so S1's refusal is defensible here. |
| RAR-FIX-20B | "him", type person | Intentional S1 consequence, same shape as RAR-FIX-20A. |

None of the four is an unintended regression.

## 10. S1 conclusion

AUDITOR INTERPRETATION:

- S1 has demonstrated safety value: it closes the one active ICB found on the natural corpus (NB-B-05@C2) with 0 regressions.
- It is over-broad. It causes 4 natural-corpus losses, 6 Probe A losses, and 2 test conflicts on definite type-noun references, all with no contradicting evidence.
- The evidence supports S1's direction, but not S1 as currently specified.
- The phrase-head / type-evidence refinement is still **UNMEASURED**.

## 11. S2 conclusion

With the vocabulary artifact removed (R3 fixed exactly the defect the first audit identified), the evidence supports the following:

- **Natural corpus:** no effect; S2 is never invoked.
- **Probe A:** S2 blocked 13 rows.
  - 5 of them prevented baseline ICBs. Only 3 of those blocks rest on genuine lexical contradiction:
    - NB-D-01 C2, via the misdirected-entity clause (`minutes` is on another candidate);
    - NB-J-02, where `contract` and `jonas` are absent;
    - NB-J-04, where `template` is absent.

    The other 2 (NB-D-02 C2, NB-L-09 C2) reach the right outcome for incidental reasons (`before`, `uploaded`).
  - 8 blocked correct bindings.
- **Zero-evidence path:** by its own contract S2 cannot guard it. 4 ICBs pass through (NB-C-04 ×2, NB-C-05 ×2).

**Conclusion:** S2 as specified mostly **shifts failure modes and is too conservative**. Its genuine safety value is small: 3 of 10 baseline ICBs, against 8 correct resolutions lost. It does not guard the Level 5 path that matters most. The hypothesis clause "no binding that Level 6's absent-entity evidence contradicts", applied at Level 5, is **not supported** for adoption.

The misdirected-entity clause on its own produced the only clean gain. A narrower S2 limited to that clause is a possible later experiment; it is **UNMEASURED**.

This is a valid negative result, not an implementation defect.

## 12. S3 conclusion

AUDITOR INTERPRETATION:

- S3 is a narrow, causal fix to the contrast shortcut. It closes NB-H-06@C1 on the real D1RQ query with no regressions, and valid contrast still resolves.
- The broader hazard, "the other X" binding the excluded X through the ordinary 4b path when a type hint is present, is not addressed. That is the R5 residual.
- The evidence supports S3 as an isolated safeguard.

## 13. Residual mechanisms (confirmed unrepaired and disclosed)

- **L5 zero-substantive recency.** NB-C-04, and now NB-C-05, both at C1 and C2. Unrepaired. VERIFIED FACT.
- **New F / L6 cross-entity scoring.** Probe B still has 3 ICBs (NB-G-04:r1, NB-I-02:r2, NB-I-06:r2, all C2), matching the pre-repair values exactly. Unrepaired.
- **L4b partial-match clause-1 residual** ("the other scan"). Unrepaired, now classified as safety.
- **S1 phrase-head refinement.** UNMEASURED and not implemented.
- **New observation (L5/L5.5 precedence):** a recency hint lets Level 5 capture explicit attachment references before Level 5.5 can return AMBIGUOUS. This is part of the L5 zero-evidence residual, not a separate class.

## 14. Experimental validity

**VERIFIED FACT / REPRODUCED RESULT:**

- A2.8J tested S1, S2, and S3 as the frozen plan specifies.
- Every measurement reproduces bit-identically on decision fields.
- No corpus, label, test, or probe was altered.
- The repair changed exactly one authorized constant.

**Limitations (UNMEASURED):**

- There is a single synthetic 79-case corpus with small pools.
- Probe A uses oracle queries and oracle ranks.
- Generalization is untested.

These limit how far the conclusions reach. They do not make the experiment invalid.

### Non-blocking errata in the repair documents

These are recorded here instead of triggering another repair loop. None changes a measured number, a classification outcome, or a conclusion.

- **E1.** Execution report addendum, line 357, says "2 of the 3 unit/fixture test conflicts caused by S2 … are fixed". Verified: **all 3** are fixed, as the addendum's own R2 table states.
- **E2.** Repair report §3 says "3 tests/subtests failing on S1" but lists **4**. Verified: 4.
- **E3.** Repair report §5 says the set is "a strict superset of what strict baseline-derivation produces" and "quoted verbatim". Verified: 18 of 19 words derive from baseline; `earliest` is a disclosed carry-over from the pre-repair set, not a baseline word.
- **E4.** Addendum loss table: NB-D-05 is blocked by `older` **and** `street`, not "`older` alone". NB-D-07 is blocked by `before`; `invoice` is on the winner. NB-D-01 C2's gain comes from the misdirected-entity clause (`minutes` on another candidate), not from the wording "absent from the winning candidate's pool position".
- **E5.** Repair step 5 of the NB-C-05 explanation should say that S1 covers only the 4b singleton branch (see §7).

## 15. Promotion implication (experimental conclusion only; no promotion performed)

- **All of RAR-SAFE:** not supported.
- **S3 alone:** supported as a candidate, subject to normal promotion governance.
- **S1:** direction supported, current form not supported; it needs the refinement experiment first.
- **S2 as specified:** not supported.
- Recency wiring and T2 detection remain unqualified: the L5 zero-evidence gap and New F are both open.

## 16. Final verdict

**ACCEPTED.** R1–R6 were carried out correctly and within the authorized scope. The repaired A2.8J evidence is truthful and reproducible. It gives a valid qualification result under the frozen plan:

- S1: partially supported.
- S2: not supported.
- S3: supported.

The remaining errata (E1–E5) are corrected by this record and do not block acceptance. This verdict does not authorize promotion, commit, or push.

## 17. Exact next action

Return to the User for the next architecture decision. Candidate next experiments, none started:

1. An L5 zero-substantive-evidence gate (NB-C-04/NB-C-05), including the L5/L5.5 precedence question for attachment references.
2. An S1 phrase-head / type-evidence refinement.
3. A narrower S2 limited to the misdirected-entity clause.
4. New F / L6 scoring.
5. Isolated S3 promotion.

Release actions (commit/push of the A2.8J artifacts) need an explicit User go-ahead.
