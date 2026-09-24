# M35 URIv1 — A2.8K Independent Final Audit

**Verdict:** `REPAIR_REQUIRED`

**Audit date:** 2026-09-24  
**Auditor:** Codex, independent audit pass  
**Audited branch:** `m35-uri-v1-parallel-architecture`  
**Audited HEAD:** `925de8f71f73ecf67713392ca9ce959de7a12d07`  
**Starting batch state:** `VERIFICATION_READY`

The saved raw measurements are deterministic and reproduce exactly. H1 and H2 were implemented faithfully enough to classify. H3 was not: it filters the candidate domain but continues to interpret the candidates' absolute, full-pool ranks instead of computing the ordinal relation within the filtered domain. The aggregate generator also omits outcome and ambiguous-candidate changes when the scoring class and resolved candidate remain unchanged. Those defects make the report's H3/H4 causal interpretation and its S-A equivalence claim unreliable. They are bounded and repairable without redesigning the experiment, so the batch is not `EXPERIMENT_INVALID`, but it is not ready to close.

No implementation repair was made during this audit.

---

## 1. Verdict

`REPAIR_REQUIRED`

Two bounded defects prevent reliable interpretation:

1. **H3 does not compute ordinal position within its evidence-compatible domain.** `_h3_domain` filters candidates, but the Level-5 branches still test their original global `recency_rank` values (`rank == 0`, `rank == 1`, `rank > 0`). For `SD-C-02`, the only compatible board-minutes candidate retains global rank 1, so H3 does not recognize it as the latest member of the compatible domain. It falls through to Level 6 and returns `UNKNOWN`. The execution report attributes this failure solely to Level 6; that causal attribution is incomplete.
2. **Decision-diff accounting is incomplete.** `compute_aggregates` treats a row as unchanged whenever scoring class and `actual_candidate_id` match. It does not compare `actual_outcome` or `actual_ambiguous_ids`. Independent comparison of the frozen decision tuple—outcome, candidate id, ambiguous candidate ids—finds 45 H3 changes rather than 39 and 56 H4 changes rather than 50. Four changes for each occur on S-A, disproving the report's claim that S-A is decision-identical for every variant.

The current raw outputs remain useful evidence about the code that actually ran. They are not sufficient evidence for the frozen H3 hypothesis or H4 as its combination.

---

## 2. Repository and integrity verification

- Expected worktree path in the directive used `Uri_V1`; the actual and plan-recorded worktree is `C:\Users\cheta\Development\Uri\_V1`. The audited repository is the latter.
- Branch: `m35-uri-v1-parallel-architecture` — verified.
- HEAD: `925de8f71f73ecf67713392ca9ce959de7a12d07` — verified.
- A2.8K state: `VERIFICATION_READY` at audit start — verified.
- A2.8K has no commit and no push — verified from Git status/history.
- No production promotion or call-site integration exists — verified by source search.
- The worktree contains extensive pre-existing uncommitted/untracked M35 and governance work outside A2.8K. This prevents Git from providing an immutable A2.8K chronology, but no unrelated file was modified by this audit.

Protected files are clean relative to HEAD, match the saved pre/post-run hashes, and match current disk bytes:

| File | SHA-256 |
|---|---|
| `uri_v1/turn/rar_deterministic.py` | `e02af25bb7009d12d829c8b8fc92e487d3da75aeaa160092db617458278fb649` |
| `uri_v1/turn/rar_contracts.py` | `4cc9aa43726a870ca2e9ab1b19f6bf9d72dcb74c8a2818856776af95195b6819` |
| `uri_v1/turn/rar_safe_experimental.py` | `4d9317311bdda0eaabc4ff5277bd3ac8b7628d83871dbd2da607954d946032a5` |
| D1RQ (`scripts/m35_a2_8h_detector_d1rq.py`) | `49f5faa9b37051fec876f5523383b4e965422976562c52e12fc38c970bfa6b82` |
| natural-boundary corpus | `0ea5447354481041181538244ef70b6dc58a72267dd95263d61dbdb55ab07380` |
| frozen S-D fixtures | `ce25cd76c1652284145dc95c3d3037c6e784fe51f92a97ace6e67e7fdf371148` |

The A2.8K files present are exactly the nine files listed in STATE, plus this audit artifact. All nine were untracked at audit start; therefore Git cannot independently attribute their internal edit history.

---

## 3. Freeze chronology

**Classification:** `PARTIALLY VERIFIED`

Evidence supporting the claimed order:

- the plan records the User's Q1-Q4 freeze;
- the S-D file contains 18 fixtures and its current hash matches STATE and both saved battery hash snapshots;
- filesystem times are consistent with plan → S-D → experimental source/tests → telemetry/report/state;
- current fixtures faithfully encode the frozen decisions;
- no current fixture-specific branch or benchmark literal appears in the experimental resolver.

What cannot be independently verified:

- all A2.8K artifacts are uncommitted and mutable;
- the STATE chronology and hash record were themselves last written after implementation and measurement;
- there is no immutable checkpoint proving the S-D hash existed before hypothesis code;
- filesystem timestamps alone are not sufficient proof of authorship order;
- the battery file's current creation/write time is eight seconds after the saved telemetry timestamp, so timestamps cannot establish that the current battery bytes are exactly the bytes that originally generated the saved output, even though the current file reproduces it exactly.

The freeze claim is credible and consistent, but not independently `VERIFIED` to an immutable standard.

---

## 4. User-semantic verification

S-D faithfully represents the approved distinctions:

- Q1: `SD-A-02` and `SD-A-03` expect `AMBIGUOUS` for generic attachment references with multiple compatible attachments; `SD-A-01` permits the single-attachment resolution.
- Q2 Case A: `SD-A-04` and `SD-A-06` expect deterministic resolution when ordering evidence is authoritative, regardless of near-time language.
- Q2 Case B: `SD-A-05` and `SD-A-07` expect ambiguity when historical rank is not current-turn attachment order.
- Q3: `SD-D-01` and `SD-D-02` are measure-only and do not claim antecedent understanding.
- Q4: H3 uses exact lexical compatibility only; it adds no fuzzy matching, stemming, new aliases, abbreviation normalization, or semantic retrieval. `SD-C-03` preserves the St/Street limitation.

One implementation mismatch remains: the H3 code does not make the rank relation relative to the compatible domain, so the approved H3 semantics are not faithfully executed.

---

## 5. Flag-off equivalence

Flag-off equivalence is verified.

- Fresh focused run: **86 tests passed, 114 subtests passed** across the A2.8K test module and the four applicable A2.5 modules.
- Unit comparison includes outcome, candidate id, and ambiguous-candidate set across diagnostic fixtures, adversarial fixtures, S-D, and legacy refinement vectors.
- Fresh corpus-scale comparison of H0 with the experimental resolver with all mechanisms disabled found no decision difference.

The report's separate claim that every enabled variant is unchanged on S-A is not a flag-off result and is false for H3/H4; see §6 and §18.

---

## 6. Independent reproduction

The battery was invoked twice in memory so the saved evidence files were not overwritten.

- Fresh rows: **3,636** S-A/S-B/S-C/S-D records and **19** S-E module-run records.
- Saved versus fresh decision/scoring mismatches: **0**.
- Fresh run 1 versus fresh run 2 mismatches: **0**.
- Fresh S-E versus saved S-E mismatches: **0**.
- Protected pre/post hashes: identical.

Rows per variant:

| Surface | Rows |
|---|---:|
| S-A | 252 |
| S-B | 168 |
| S-C | 168 |
| S-D | 18 |

The saved telemetry is fully reproducible for the implementation that exists.

Independent full-decision comparison versus H0 finds:

| Variant | Reported changed rows | Actual decision changes |
|---|---:|---:|
| H1 | 11 | 11 |
| H2 | 8 | 8 |
| H3 | 39 | **45** |
| H4 | 50 | **56** |
| DX-1 | 5 | 5 |

The six omitted H3/H4 rows are four S-A rows, one S-B row, and one S-C row per variant. Each changes from `AMBIGUOUS` to `UNKNOWN` without changing the coarse scoring class (`MISSED_RESOLVABLE_CASE`), so the aggregate comparator misses it.

---

## 7. Independent scoring

An independent classifier derived directly from expected outcome, intended ids, actual outcome, and actual candidate id produced **0 scoring mismatches** across all 3,636 rows.

The pooled scoring totals in the execution report are accurate. Zero new incorrect confident bindings is also accurate for the code that ran. The defect is in changed-decision enumeration, not in the coarse scoring totals.

The aggregate result “zero new ICBs” was specifically challenged and reproduced for all variants on all measured surfaces. It should not be generalized beyond these corpora.

---

## 8. H1 audit

**Mechanical frozen-rubric classification:** `PARTIALLY SUPPORTED`

- closes 6 measured Class-A ICB instances;
- introduces 0 new ICBs;
- loses 5 correct resolutions;
- `SD-N-03`, `SD-A-04`, and `SD-A-06` are genuine non-abstention-permitted violations of frozen semantics;
- the remaining S-E conflicts are also real losses of established correct Level-5 behavior.

H1 tests the presence of any non-excluded substantive token. It does **not** test whether that token matches the ordinal winner. Therefore the report's broader evidence-condition wording—“substantive token matching the winning candidate”—is not established by H1 alone.

H1's success is materially dependent on the inherited exclusion vocabulary: “attachment” is excluded because it is generic, and `latest`/`first`/`earlier` are excluded by the imported recency vocabulary. This is a legitimate test of the frozen H1 definition, but not a vocabulary-independent proof of evidence sufficiency.

The Level-6 interaction is causal for several fall-through outcomes: after H1 blocks Level 5, baseline Level 6 treats recency words such as `current` or `latest` as substantive missing-entity tokens. It is not the cause of H1 blocking the valid Level-5 resolution; it determines the downstream failure family after that block.

---

## 9. H2 audit

**Mechanical frozen-rubric classification:** `PARTIALLY SUPPORTED`

- closes the same 6 measured Class-A ICB instances;
- introduces 0 new ICBs;
- loses exactly 2 correct resolutions: `SD-A-04` and `SD-A-06`;
- has no S-E conflict.

The causal limitation follows from H2's inputs, not merely fixture construction. H2 sees explicit attachment wording and `is_attachment`, but no provenance saying whether rank represents current-turn attachment order, historical creation order, or another relation. It must behave identically for the Case-A/Case-B twins, so it cannot preserve one and abstain on the other.

This establishes an information deficit. It does not establish a particular transport mechanism.

---

## 10. H3 audit

**Mechanical frozen-rubric classification of the implemented variant:** `PARTIALLY SUPPORTED`  
**Hypothesis-fidelity status:** `NOT VERIFIED — REPAIR REQUIRED`

The reported counts for the coarse scoring transition are reproducible: 14 ICB closures, 0 new ICBs, and 15 lost correct resolutions. The current variant also creates 45 complete decision changes, not 39.

The central defect is at the rank boundary. H3 builds a compatible subset but does not derive positions within it. Examples:

- `SD-C-02`: the compatible minutes candidate has global rank 1. It is the only—and therefore latest—member of the compatible domain, but H3 looks for global rank 0, finds none, and falls through.
- `NB-D-01` C2: the same pattern occurs on the natural corpus.

Consequently the experiment establishes only the narrower result:

> The tested lexical filter prevents some unsafe global-pool selections and converts them to abstentions.

It does not establish that a correctly implemented evidence-compatible ordinal domain behaves as reported. The claimed Level-6/recency-vocabulary interaction is real, but it occurs after an upstream H3 rank-relative defect and cannot carry the full causal explanation.

The St/Street loss remains a genuine frozen known limitation. `NB-D-02` C1 remains a genuine correct-resolution loss for the implementation that ran.

---

## 11. H3 pre-measurement repair audit

**Classification:** `INSUFFICIENT_EVIDENCE`

The frozen plan clearly requires an empty compatible domain to fall through, and the current implementation does so. If the disclosed edit occurred before measurement, it was a legitimate plan-conformance repair rather than a hypothesis change. The current regression test also targets that behavior.

However, the original defective implementation does not exist in Git or another immutable artifact, and the chronology is recorded only in mutable, uncommitted STATE/report text plus filesystem times. The audit therefore cannot independently prove what changed or that it changed before results were observed.

No S-D expected outcome changed in the current evidence set, and the frozen hash remains stable across both saved and fresh runs.

---

## 12. Level-6 / recency-vocabulary interaction audit

The interaction is real.

- H1/H3 exclude `_RECENCY_VOCABULARY` when computing their experimental substantive tokens.
- Baseline Level 6 excludes only stopwords, generic type words, and pronouns.
- A Level-5 fall-through can therefore make words such as `latest`, `current`, `earlier`, `version`, or `draft` appear to Level 6 as missing entity evidence.
- Representative traces change from Level-5 `TEMPORAL_RELATION` to Level-6 `TERM_DISCRIMINATION` and return `UNKNOWN`.

Affected evidence includes H1 losses such as `SD-N-03`, H3/H4 `SD-C-02`, and the `ADV-06` S-E family mismatch. The precise row set depends on both the fall-through trigger and candidate tokens.

This is pre-existing baseline Level-6 behavior exposed by the experiment. Changing it would modify Level 6 and is outside A2.8K. Any claim that adding the recency exclusion would improve net behavior remains `UNMEASURED`.

It must not be described as the sole explanation for H3 because H3 first fails to compute relative ordinal positions within the filtered domain.

---

## 13. H4 audit

**Mechanical frozen-rubric classification of the implemented variant:** `PARTIALLY SUPPORTED`  
**Hypothesis-fidelity status:** `NOT VERIFIED — inherits H3 repair requirement`

The coarse sets are literally additive:

- H4's 20 ICB closures exactly equal the union of H1/H2/H3 closures;
- H4's 20 correct-resolution losses exactly equal their union;
- the report's 50 coarse changed rows equal the union of the three coarse changed-row sets;
- the correct full-decision count is 56, also the exact union of the isolated mechanisms' full-decision changes.

Thus “additive rather than complementary” is established for this measured implementation. It cannot be generalized to a corrected H3 without rerunning H4.

---

## 14. DX-1 causal audit

DX-1 changes only the rank/tie input consumed by Level-5 ordinal branches. It does not alter candidate pools, spans, hints, attachment flags, cascade order, Level 5.5 logic, or expected outcomes.

It closes 5 of 6 measured Class-A ICBs with 0 new ICBs and 0 lost correct resolutions. This proves that tying the supplied attachment members is a **sufficient intervention** for those five rows and that rank differentiation is a causal contributor.

It does **not** prove that the rank clock is the sole root cause or that precedence is irrelevant. Level 5 still precedes Level 5.5; that precedence is an enabling contributor whenever an attachment-worded ordinal is settled before attachment ambiguity is considered.

`NB-C-05` C2 is misclassified in the execution report. The corpus's `turn_attachments` lists the two actual current-turn attachments completely. C2 adds a third, newer file-reference candidate that is not in `turn_attachments`. DX-1 correctly ties the two supplied attachment ids at their minimum rank, but Level 5 ignores attachment membership and still selects the third global rank-0 file. This demonstrates an interaction among candidate-pool scope, missing attachment-membership use at Level 5, rank semantics, and cascade precedence—not incomplete `turn_attachments` data.

**Causal conclusion:** partial causality plus a sufficient intervention on 5/6 rows; not sole clock causality.

---

## 15. Contract and architecture inference audit

### Information requirement

The experiment supports this narrow statement:

> Distinguishing trustworthy from untrustworthy attachment ordering requires evidence about current-turn attachment membership and the provenance/meaning of the ordering relation; current RAR inputs do not provide that distinction to Level 5.

Membership alone is insufficient for Q2 Case A versus Case B. Order or event grouping/tie information, plus the semantic provenance of that relation, is required.

### Transport requirement

`NEW CONTRACT FIELD REQUIRED` is **not experimentally established**. The experiment did not compare preprocessing, deterministic anchors, an upstream rank transformation, existing contextual structures, or another representation. A new RAR contract field is one plausible design, not a proven necessity.

### Ordering versus membership

The demonstrated gap is a combination:

- current-turn membership;
- ordering or same-event grouping/tie relation;
- provenance that tells the resolver whether the ordering represents the relation expressed by the user.

---

## 16. DX-2 audit

Four antecedent-relative rows are correctly identified: two S-D rows and two natural-corpus S-C rows.

No H1-H4 mechanism understands the antecedent. H3 converting natural Class-D ICBs to abstentions is not a solution. The defensible result is:

`CAPABILITY GAP CONFIRMED / SOLUTION UNMEASURED`

---

## 17. Evidence-condition-table audit

Required corrections to the execution report's table:

| Reported condition | Audit disposition |
|---|---|
| Substantive token matching the winner → `LEVEL_5_BIND_SUPPORTED` | Too broad. H1 checks token presence, not winner match; evidence supports only the measured rows. |
| Zero-substantive, non-attachment ordinal → `LEVEL_5_BIND_SUPPORTED` | Supported only for measured negative controls, not as a general pool-size rule. |
| Untrusted explicit attachment ordering → `LEVEL_5_5_PRECEDENCE_SUPPORTED` | Narrowly supported as a safe intervention; H2 cannot determine trustworthiness from its inputs. |
| Trustworthy explicit attachment ordering → bind | Frozen semantics support it; no tested mechanism distinguishes it from the untrusted twin. |
| Absent entity → `ABSTAIN_SUPPORTED` | Supported for measured rows; H3's broader mechanism remains nonconformant. |
| Latest compatible entity → `UNSUPPORTED` | Correct for the implementation that ran; the frozen H3 hypothesis remains unmeasured because ranks were not made domain-relative. |
| Lexically distinguished attachment | `UNSUPPORTED` by measured mechanisms. |
| St/Street | `UNSUPPORTED`; known limitation. |
| Antecedent-relative | `UNMEASURED` beyond capability-gap tagging. |

General claims must remain bounded to the corpus and authored S-D cases.

---

## 18. Classification-rubric audit

Applying the frozen scoring rubric mechanically to the observed rows yields:

| Variant | Classification | Audit qualification |
|---|---|---|
| H1 | `PARTIALLY SUPPORTED` | Valid for implemented H1. |
| H2 | `PARTIALLY SUPPORTED` | Valid for implemented H2. |
| H3 | `PARTIALLY SUPPORTED` | Mechanical label only; frozen hypothesis not faithfully implemented. |
| H4 | `PARTIALLY SUPPORTED` | Mechanical label only; inherits H3 defect. |

The audit does not substitute a new scoring method. It separately records mechanism-fidelity failure.

S-A is not unchanged for H3/H4. The omitted rows are:

- `NB-D-07` r1 C1 and C2;
- `NB-L-04` r1 C1 and C2.

Each changes `AMBIGUOUS` → `UNKNOWN`. Therefore the report's S-A regression-pass claim is false for H3/H4 even though their coarse scoring class is unchanged.

---

## 19. S-E conflict audit

- H1: five conflicts across two modules. These are genuine regressions against valid established semantics, although they are expected consequences of H1's broad evidence floor.
- H2: zero conflicts.
- H3: `ADV-06` changes expected `AMBIGUOUS` to `UNKNOWN`. This is a family-only mismatch, but the frozen adversarial fixture permits only `AMBIGUOUS`, so it is still a real test conflict.
- H4: union of H1's five regressions and H3's one family mismatch.
- DX-1: zero conflicts.
- Contract module: correctly marked `S_E_NOT_APPLICABLE`; it does not invoke the extended Level 0-7 resolver binding that the harness swaps.

Safe abstention is not treated as automatically non-regressive.

---

## 20. Contamination and post-hoc-change audit

No case ids, fixture ids, benchmark names, corpus candidate ids, timestamp threshold, or literal fixture-specific branch appears in `rar_l5_experimental.py`. H1/H2/H3/DX-1 are general deterministic mechanisms. No post-hoc vocabulary addition is visible; H1/H3 import the pre-existing A2.8J `_RECENCY_VOCABULARY` unchanged.

No S-D hash change is visible between the saved runs, fresh audit runs, and current disk state.

However, because all A2.8K artifacts are uncommitted and no immutable pre-measurement checkpoint exists, the audit cannot prove that no silent repair occurred before saved telemetry. The disclosed H3 repair is handled separately in §11. No additional post-result repair is evident in current source or state.

---

## 21. Experimental limitations

- The natural oracle inventory contains only nine original Level-5 ICBs.
- S-D is authored and small; it increases causal control but not external validity.
- S-C uses oracle spans/hints; S-B is more realistic but inherits D1RQ behavior.
- D1RQ hints are clause-level and may encode words outside the reference span.
- `created_at` simulates a possible future recency source; it is not current production rank wiring.
- Current `turn_attachments` is corpus context, not a RAR contract input.
- DX-1 supplies membership/tie information externally and only to Level 5.
- Pooled totals obscure important surface behavior, including H3/H4's four S-A outcome changes.
- Coarse scoring treats `AMBIGUOUS`→`UNKNOWN` as the same miss when the expected result is `RESOLVED`; full decision comparison is therefore essential.
- The uncommitted worktree weakens chronology and post-hoc-change assurance.

These limits do not erase the reproducible observations; they constrain causal and architectural generalization.

---

## 22. Corrections required

Before closure, a bounded repair pass must:

1. make H3's ordinal relation domain-relative, with explicit tests for `latest`, `previous`, and `earlier` after filtering;
2. define the intended rank semantics in the plan-compatible implementation without changing S-D expected outcomes;
3. compare full decisions in aggregates: outcome, candidate id, and ambiguous-candidate ids (set-equivalent where ordering is not semantic);
4. rerun H3 and H4 on S-A through S-E twice;
5. regenerate telemetry/aggregates and write a repair report, preserving this audit and the original execution report;
6. correct the DX-1 `NB-C-05` C2 explanation;
7. remove the claim that a new RAR contract field is proven necessary;
8. distinguish Level-6 interaction from the upstream H3 rank-relative defect;
9. provide an immutable checkpoint or otherwise explicitly retain the chronology limitation.

H1/H2 need no implementation repair for this audit verdict; their measured tradeoffs are valid negative/mixed evidence.

---

## 23. Residuals and unmeasured hypotheses

- Level-6 recency-vocabulary exclusion remains an `UNMEASURED FOLLOW-UP HYPOTHESIS`.
- Lexical narrowing inside Level 5.5 remains unmeasured.
- Antecedent/session resolution remains unmeasured.
- The transport design for attachment membership/order/provenance remains unmeasured.
- A corrected, domain-relative H3 is not a new hypothesis; it is the faithful implementation still required for the already-frozen H3.

---

## 24. What the evidence supports

- H1 and H2 each close the six measured Class-A ICBs but lose valid resolutions; both are `PARTIALLY SUPPORTED` and not production-ready.
- H2 cannot distinguish trustworthy from untrustworthy attachment order using its current inputs.
- The Level-6 recency-token mismatch is real and causally determines several fall-through outcomes.
- The implemented lexical filtering prevents measured unsafe global-pool bindings, but often only by abstaining.
- DX-1 tie intervention is sufficient for five of six measured Class-A rows with no measured cost.
- H4 is exactly additive for the implementation that ran.
- Four antecedent-relative rows remain an unsolved capability gap.
- No measured variant introduces a new ICB on these surfaces.

---

## 25. What the evidence does not support

- It does not validate the frozen H3 hypothesis as implemented.
- It does not establish that Level 6 is the sole cause of H3's misses.
- It does not establish that the rank clock is the sole Class-A root cause or that precedence is irrelevant.
- It does not establish incomplete `turn_attachments` for `NB-C-05` C2.
- It does not establish that a new RAR contract field is necessary.
- It does not establish S-A equivalence for H3/H4.
- It does not authorize any mechanism for production.
- It does not resolve antecedent-relative references.
- It does not prove immutable freeze/repair chronology.

---

## 26. Recommended next experimental question

First repair and rerun the already-approved experiment; do not begin a new hypothesis batch.

After faithful H3/H4 evidence exists, the next pre-registered question should be:

> Given explicit current-turn attachment membership, ordering/event-group provenance, and distractor candidates, which factor—domain restriction, domain-relative ordinal rank, or Level-5.5 precedence—is necessary and sufficient to preserve trustworthy Case-A bindings while abstaining on Case-B twins?

A small factorial battery should independently vary membership completeness, same-event ties, authoritative order, and non-turn file distractors. That is a recommendation only, not authorization to implement.

---

## Audit actions and stop confirmation

Files changed by this audit:

- `docs/plans/M35_URIV1_A2_8K_INDEPENDENT_FINAL_AUDIT.md` — created.
- `docs/plans/M35_URIV1_A2_8K_STATE.md` — audit verdict/history only.

No H1/H2/H3/H4/DX-1 code, Level 6, RAR contract, D1RQ, baseline RAR, fixture, scoring implementation, telemetry, aggregate, or execution report was modified. No commit, push, production promotion, or next experiment occurred.
