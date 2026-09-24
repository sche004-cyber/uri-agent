# M35 URIv1 — A2.8K: Level-5 Evidence Sufficiency & Attachment Ordering — Execution Report

**Status:** `VERIFICATION_READY` (this batch). Experimental implementation and measurement only — no production modification, no promotion, no baseline/contract change, no commit, no push. Independent audit and any repair decision are reserved for the User / a subsequent Claude audit pass, per the implementation directive §0 and §24.

**Author:** Claude Sonnet (fallback-1 implementer, per the User's routing decision — Codex and Antigravity run entirely outside the Claude Code session and could not be invoked or simulated from it; see `docs/plans/M35_URIV1_A2_8K_STATE.md` history).
**Date:** 2026-09-24.
**Plan:** `docs/plans/M35_URIV1_A2_8K_L5_EVIDENCE_SUFFICIENCY_PLAN.md` (§11 records the User's §8 Q1-Q4 freeze).

---

## 0. Repository integrity

| Item | Value |
|---|---|
| Worktree | `C:\Users\cheta\Development\Uri\_V1` |
| Branch | `m35-uri-v1-parallel-architecture` |
| HEAD at start | `925de8f7` |
| Protected-file SHA-256, pre-run vs. post-run | **Identical for all 6 protected files** on both battery runs (`docs/plans/M35_URIV1_A2_8K_TELEMETRY.json` → `pre_run_protected_hashes` / `post_run_protected_hashes`). Covers `rar_deterministic.py`, `rar_contracts.py`, `rar_safe_experimental.py`, the D1RQ detector, the natural-boundary corpus, and the frozen S-D fixture file. |
| Changed/new files this batch | `uri_v1/turn/rar_l5_diagnostic_fixtures.py` (new, frozen), `uri_v1/turn/rar_l5_experimental.py` (new), `scripts/m35_a2_8k_l5_battery.py` (new), `tests/test_m35_uriv1_a2_8k_l5_experimental.py` (new), `docs/plans/M35_URIV1_A2_8K_TELEMETRY.json` (new), `docs/plans/M35_URIV1_A2_8K_AGGREGATES.json` (new), `docs/plans/M35_URIV1_A2_8K_L5_EVIDENCE_SUFFICIENCY_PLAN.md` (§11 appended), `docs/plans/M35_URIV1_A2_8K_STATE.md` (updated), this report (new). No existing production or test file was edited. |
| Git state | Nothing committed. Directive §0 authorizes experimental implementation/measurement only, not commit/push. |

## 1. S-D freeze

- Fixture count: **18** (`uri_v1/turn/rar_l5_diagnostic_fixtures.py`), authored and hashed **before** `rar_l5_experimental.py` existed (plan §7 order; recorded in STATE at the time of authoring).
- Frozen SHA-256: `ce25cd76c1652284145dc95c3d3037c6e784fe51f92a97ace6e67e7fdf371148` (unchanged from authoring to this report — verified by the battery's pre/post hash check on every run).
- Semantic categories: Class A attachment identity/ordering (8: generic 1/2/3-attachment Q1 cases, explicit-ordinal Q2 Case-A/Case-B trustworthy/untrustworthy-clock twins ×2, one lexically-distinguished-attachment case), Class B absent entity (2, present/absent twin), Class C ordering domain (3, matched/domain-violating twin + the St/Street known-limitation pair), Class D relative anchor (2, DX-2 measure-only), Class N negative controls (3).
- No fixture's query, candidates, or expected outcome was changed after this freeze. (Descriptive text only was written at authoring time and not touched afterward; see the S-D fixtures/tests discussion in §C below for how the actual measured behaviour of a fixture can still legitimately differ from its intended target when it interacts with a mechanism outside the fixture's own design, which is disclosed there rather than "fixed" by editing the frozen file.)

## 2. Flag-off equivalence gate

Verified two ways:
1. **Unit level** (`tests/test_m35_uriv1_a2_8k_l5_experimental.py::FlagOffEquivalenceTests`): `resolve_rar_l5_experimental` called with every flag off is decision-identical (outcome, candidate_id, ambiguous_candidate_ids) to `resolve_rar_deterministic_extended` on all 24 A2.5 diagnostic fixtures, all A2.5 adversarial fixtures, all 18 S-D fixtures, and the RC-1/RC-4 legacy unit-test vectors. **16 tests / 66 subtests, all pass.**
2. **Corpus scale** (battery `S-A` surface, §4 below): H0 vs. every other variant is compared row-by-row on S-A (D1RQ spans + D1RQ hints, all ranks 0 — the shape Level 5 is inert on today per plan §1.1's production-exposure note). **`s_a_regression_check_passed` is `True` for H1, H2, H3, H4, and DX1** — zero S-A rows differ from H0 for any variant.

Gate passed. Qualification proceeded.

## 3. Determinism

The full battery (S-A, S-B, S-C, S-D, S-E; all variants) was run twice. Decision fields (outcome, candidate_id, ambiguous_candidate_ids) were compared row-by-row across the two runs, excluding latency. **`determinism_check_passed: true`** (recorded in both `M35_URIV1_A2_8K_TELEMETRY.json` and `_AGGREGATES.json`).

## 4. Surfaces run

All five approved surfaces were run for H0, H1, H2, H3, H4, and DX-1 (no surface was omitted):

| Surface | Rows | Notes |
|---|---|---|
| S-A | Natural corpus, C1/C2/C3, D1RQ span+hint, ranks 0 | Regression guard — 0 diffs from H0 for any variant |
| S-B | Natural corpus, C1/C2, D1RQ span+hint, real (`created_at`) ranks | New condition; only H3/H4 produce any changed rows (16 each) |
| S-C | All 168 C1/C2 ground-truth reference rows, oracle span+hint mapping, real ranks | The Probe-A-generalised surface; primary source of the Class A-D evidence below |
| S-D | 18 frozen fixtures | §5/§8 coverage |
| S-E | 4 existing A2.5 RAR test modules (`test_m35_uriv1_a2_5_deterministic_rar`, `_rar_adversarial_safety`, `_rar_contracts`, `_rar_stage4_refinements`), resolver monkeypatched per variant in-memory, no file on disk edited | `test_m35_uriv1_a2_5_rar_contracts.py` tests `resolve_rar_deterministically`/contract invariants directly and never calls the Level 0-7 cascade — recorded as `S_E_NOT_APPLICABLE` for every variant rather than silently skipped |

DX-2 (relative-anchor tagging) is applied to the two Class-D S-D rows (`SD-D-01`, `SD-D-02`, `scoring_class: MEASURE_ONLY`); the plan does not define a DX-2 natural-corpus surface beyond the S-C rows already labelled Class D in the §1.2 inventory (`NB-D-02:r1 C2`, `NB-L-09:r2 C2`), which are discussed under §F below.

Raw data: `docs/plans/M35_URIV1_A2_8K_TELEMETRY.json` (3,636 S-A/S-B/S-C/S-D rows + 19 S-E module-runs). Aggregates: `docs/plans/M35_URIV1_A2_8K_AGGREGATES.json`.

## 5. Results by hypothesis

Zero new ICBs were introduced by **any** variant on **any** surface (S-A through S-E) — this is the single most important safety fact and holds across all six variants.

| Variant | Scoring totals (S-A+S-B+S-C+S-D pooled) | Closed ICBs vs. H0 | New ICBs vs. H0 | Lost correct resolutions vs. H0 | S-A regression | S-E conflicts |
|---|---|---|---|---|---|---|
| H0 | CORRECT_RESOLUTION 160, MISSED 175, CORRECT_ABSTENTION 165, ICB 26, family-mismatch 33 | — | — | — | — | 0 (reference) |
| H1 | CORRECT_RESOLUTION 155, MISSED 180, CORRECT_ABSTENTION 171, ICB 20, family-mismatch 33 | 6 | 0 | 5 | pass | 5 tests across 2 modules |
| H2 | CORRECT_RESOLUTION 158, MISSED 177, CORRECT_ABSTENTION 171, ICB 20, family-mismatch 33 | 6 | 0 | 2 | pass | 0 |
| H3 | CORRECT_RESOLUTION 146, MISSED 196, CORRECT_ABSTENTION 175, ICB 12, family-mismatch 30 | 14 | 0 | 15 | pass | 1 test |
| H4 | CORRECT_RESOLUTION 141, MISSED 201, CORRECT_ABSTENTION 181, ICB 6, family-mismatch 30 | 20 | 0 | 20 | pass | 5 tests across 2 modules (= H1's, unioned) |
| DX-1 | CORRECT_RESOLUTION 160, MISSED 175, CORRECT_ABSTENTION 170, ICB 21, family-mismatch 33 | 5 | 0 | 0 | pass | 0 |

(Full per-row detail — every one of the 11/8/39/50/5 changed rows for H1/H2/H3/H4/DX-1 respectively, individually — is in `M35_URIV1_A2_8K_AGGREGATES.json` under `changed_rows_vs_h0`, `new_icb_vs_h0`, `closed_icb_vs_h0`, `lost_correct_resolutions_vs_h0`, keyed by variant. This report does not repeat all 113 rows inline; every one is listed there, not only in the totals above.)

### H1 — Level-5 evidence floor. **PARTIALLY SUPPORTED.**

- Closes **all 6** target-class-A ICB instances it reaches (`NB-C-04` C1/C2, `NB-C-05` C1/C2 on S-C; `SD-A-05`, `SD-A-07` on S-D) — a mechanism distinct from H2's: for these specific spans ("the latest attachment", "the first attachment") every ref token is either a stopword, `GENERIC_TYPE_WORDS` (`attachment`), or R3(a) recency vocabulary, so the evidence floor blocks the Level-5 ordinal commit outright and the query falls through to Level 5.5, which independently returns AMBIGUOUS on ≥2 attachment candidates. Zero new ICBs anywhere.
- **Does not qualify for full SUPPORTED**: it loses 5 correct resolutions, and at least 3 of them are **not** abstention-permitted by their frozen semantics — `SD-N-03` ("the current version"), `SD-A-04`, `SD-A-06` (the Q2 Case-A trustworthy-ordering negative controls). All three are lost because `_RECENCY_VOCABULARY` excludes "version"/"current"/"latest"/"earlier" from "substantive," leaving zero substantive tokens even though the reference is a perfectly legitimate, evidence-bearing recency phrase over a small pool — and Level 6 (unmodified, byte-identical to baseline) cannot always rescue the fall-through, because Level 6's own substantive-token computation does **not** exclude that vocabulary (see §C below; this is the same root interaction H3 exhibits, and it is the central, generalizable finding of this batch).
- H1's predicted risk in the plan ("loses correct zero-evidence bindings") is confirmed exactly, and is larger than the plan anticipated: it also loses zero-evidence bindings the User's own Q2 freeze explicitly wanted preserved (Case A, trustworthy ordering), not only edge cases like "this."

### H2 — Attachment-ambiguity precedence. **PARTIALLY SUPPORTED.**

- Closes the same 6 Class-A ICB instances as H1 (`NB-C-04`, `NB-C-05` on S-C; `SD-A-05`, `SD-A-07` on S-D), via its own, different mechanism (Level 5.5 runs first whenever attachment wording is explicit, independent of whether the span has other substantive tokens). Zero new ICBs.
- Loses exactly 2 correct resolutions, both non-abstention-permitted: `SD-A-04`, `SD-A-06` (Q2 Case-A trustworthy attachment ordering) — forced to AMBIGUOUS by the same attachment-precedence rule that correctly disambiguates the untrustworthy twins. This is precisely the "only affects attachment-worded spans" tradeoff the plan predicted, confirmed with the smallest loss count of the three isolated hypotheses.
- Zero S-E conflicts (the existing A2.5 test suite has no attachment+recency-hint combination in its own fixtures, so this tradeoff is invisible to it — a coverage gap in the existing suite, not evidence H2 is free of cost).

### H3 — Evidence-compatible ordering domain. **PARTIALLY SUPPORTED** (closes 100% of its own target class, at a larger and partly unexpected cost).

- Closes **all** identified target-class-C ICB instances: `NB-D-01` C2 on S-C (the plan's single natural-corpus Class-C example) and `SD-C-02` on S-D. It also incidentally closes 2 Class-B ICBs (`NB-J-02`, `NB-J-04` — confirming the plan's "H3 will affect Class B rows as a by-product" prediction exactly) and 2 further Class-D rows (`NB-D-02` C2 r1, `NB-L-09` C2 r2), which the plan did not claim as targets but which the domain-restriction mechanism reaches anyway.
- **Every closure converts the ICB into a safe abstention (UNKNOWN/AMBIGUOUS), never into the intended correct binding.** `NB-D-01` C2 and `SD-C-02` both land on `MISSED_RESOLVABLE_CASE` (UNKNOWN), not `CORRECT_RESOLUTION`. This is the discovered central limitation (§C): once H3's domain restriction causes Level 5 to fall through, Level 6 (unmodified) treats the reference's own recency word (e.g. "latest") as a literal, missing "substantive" token — because Level 6's substantive-token computation, unlike H1/H3's, does not exclude the R3(a) recency vocabulary — and returns UNKNOWN via its absent-entity path before it ever gets to score the domain-relevant tokens ("board", "minutes") against the candidates.
- 15 disclosed correct-resolution losses, including 2 that are **not** abstention-permitted: `SD-C-03` (the St/Street known-limitation pair, exactly as predicted — H3's literal token match cannot see "St" = "Street") and `NB-D-02` C1 (a natural-corpus row the plan's own §1.2 flagged as "correct only by coincidence of pool composition," which H3's domain restriction disturbs).
- One S-E conflict: `ADV-06` ("Missing timestamps when querying latest," expected AMBIGUOUS) becomes UNKNOWN under H3, for the identical Level-6-interaction reason above — not a new incorrect binding (both are safe outcomes), but a documented "abstention-family mismatch," consistent with 0 new ICBs.
- **Corrected mid-implementation defect, disclosed for the record:** an early implementation of H3's "empty compatible domain" case incorrectly fell into baseline's *unrelated* "no ordering metadata" AMBIGUOUS fallback using the **full** (unrestricted) pool, rather than genuinely falling through past Level 5 as the plan requires ("An empty subset means Level 5 does not bind and falls through"). This was caught by `tests/test_m35_uriv1_a2_8k_l5_experimental.py::H3MechanismTests` during implementation (the St/Street case), fixed before any battery run, and the fixed behaviour is what is reported here and covered by a dedicated regression test. No battery data in this report reflects the pre-fix behaviour.

### H4 — H1 + H2 + H3 combined. **PARTIALLY SUPPORTED** (superset of costs, not a net improvement over the isolated hypotheses).

- Closes the union of what H1/H2/H3 close individually (20 ICBs — the largest of any variant), with 0 new ICBs.
- Also accumulates the union of their losses (20 lost correct resolutions — the largest of any variant, exactly equal to the ICB-closure count). Per the directive's instruction not to tune before running H4, no interaction-specific repair was attempted; the components were combined exactly as isolated. The result is that H4 trades every isolated hypothesis's individual weaknesses simultaneously for its combined strengths, rather than any weakness cancelling out. This is itself the finding: **the three mechanisms are additive in both directions (ICBs closed and correct resolutions lost), not complementary in a way that reduces net cost.**

### DX-1 — Turn-attachment tie oracle (diagnostic only). **Causal result, not a SUPPORTED/PARTIALLY-SUPPORTED verdict** (the plan scopes DX-1/DX-2 to answering §20's causal questions, not the H1-H4 classification rubric).

- Closes 5 of 6 Class-A ICB instances (`NB-C-04` C1/C2, `NB-C-05` C1 only, `SD-A-05`, `SD-A-07`) with **zero new ICBs and zero lost correct resolutions** — the cleanest result of any variant measured. Every closure is a pure gain: DX-1 never touches a case its tie assertion does not apply to.
- **Misses `NB-C-05` C2.** The tie assertion (`turn_attachments ∩ candidate_ids` for that case/cell) did not include both of the C2 pool's actual candidates as a tied pair, so Level 5's "latest" branch still committed confidently to the wrong one. This is evidence that the corpus's own `turn_attachments` field, as currently populated, does not fully and consistently describe which objects were attached together in every candidate-pool configuration — a data/harness-construction question, not a defect in DX-1's own mechanism (DX-1 is exactly as narrow as its input tie set; it makes no inference beyond what it is told).
- **Answer to plan §20/directive §10's DX-1 question:** for the 5 of 6 Class-A instances it reaches, Class A's cause is the **rank clock**, not precedence — DX-1 changes nothing about cascade order or about which level runs first, only what the ordinal comparison treats as tied, and that alone converts a wrong confident binding into a safe abstention. Precedence (H2) and the evidence floor (H1) each *also* close the same instances, but through different, coincidental routes (H1 via the "attachment" token happening to be excluded from substantive evidence; H2 via explicit reordering) — DX-1 is the only one of the three that targets the actual documented root cause directly. **This is a contract/architecture finding to escalate, not to implement here** (directive §10): RAR's contract has no field carrying "these candidate ids were attached in the same current-turn event," and `recency_rank`, sourced from `created_at`, is not that relation. `SD-A-05`/`SD-A-07`'s S-D design makes this same point deliberately with authored, unambiguous ground truth.

## 6. Central questions (directive §20)

**A. Evidence sufficiency.** Level 5 may safely bind an ordinal reference when (i) the span carries at least one substantive token outside stopwords/pronouns/generic-type-words/R3(a) recency vocabulary that also appears on the candidate the ordinal rule would select (this is what H1 tests, and it correctly removes Class-A ICBs where the span truly carries no discriminating evidence), **or** (ii) the span is a bare recency/revision word over a pool of ≤2-3 candidates where no other candidate shares the winner's role (the "SD-N" negative controls, and the many correct zero-evidence S-C rows the plan's own §1.2 lists) — condition (ii) is exactly what H1 as specified cannot distinguish from condition (i)'s absence, which is why H1 both fixes real unsafe bindings and breaks real safe ones. **Level 5 may not safely bind** when the reference is explicit-attachment-worded and ≥2 attachment candidates exist (Class A/Q1), or when the winning candidate is lexically incompatible with the span's own domain-restrictive words (Class C) — H2 and H3 respectively address these but each at a measured, disclosed cost (§5).

**B. Attachment precedence.** Level 5.5 should take precedence over Level 5's ordinal selection specifically when the reference's *only* discriminating content is the attachment-hood of the candidates and the ordinal wording is not independently evidenced as trustworthy (Q2 Case B) — H2/DX-1 both demonstrate this converts the documented Class-A ICBs to safe abstentions. It should **not** take precedence when the ordering evidence is authoritative (Q2 Case A) — H2, applied unconditionally on the presence of attachment wording alone, cannot tell the two cases apart and sacrifices the legitimate ones (`SD-A-04`, `SD-A-06`). **No hypothesis measured here can make this distinction** — only DX-1's oracle tie information can, and that information does not exist in the current RAR contract (§E).

**C. Ordering domain.** Temporal ordering should operate over an evidence-compatible subset of the pool, not the entire pool (H3's target, confirmed: closes both identified Class-C ICBs) — but **the experiment does not support adopting H3's current mechanism as specified**, because its "fall through" path routes into baseline Level 6, whose own substantive-token computation was never designed to exclude the same recency vocabulary H1/H3 exclude. The result is that H3 trades a wrong confident binding for a safe-but-uninformative abstention rather than the correct binding, and separately breaks two legitimate correct resolutions it was never meant to touch (the St/Street known limitation, and one "coincidentally correct" natural-corpus row). **Whether ordering should operate over the current-turn attachment set specifically** was not tested by H3 (H3's domain is lexical-compatibility-based, not attachment-membership-based) — that is DX-1's question, answered in §D below, not H3's.

**D. Ordering clock.** `created_at` does **not** reliably represent the relation "attached in this turn" that references like "the latest attachment" actually ask about (plan §1.1's architectural finding, confirmed empirically by DX-1 closing 5 of 6 Class-A instances purely by overriding the rank comparison for tied turn-attachments, with zero side effects). It fails specifically whenever two or more objects were attached in the same current-turn event but have different original `created_at` timestamps (the corpus's own `NB-C-04`/`NB-C-05` construction, and `SD-A-05`/`SD-A-07`'s deliberately authored twin of the trustworthy case). `created_at` remains reliable for genuinely sequential objects (invoices, revisions, minutes across different meetings) — the many `CORRECT_RESOLUTION` rows unaffected by any hypothesis.

**E. Missing evidence.** Yes — safe, general attachment-ordering resolution requires a RAR contract field for current-turn attachment membership/order that does not exist today (plan §1.1; confirmed by DX-1 needing an externally-supplied tie set that has no home in `RARCandidate`/`RARQuery`/`RAREvidence`, and by DX-1 itself missing `NB-C-05` C2 because the corpus's own `turn_attachments` field does not fully describe that case's actual attach-time relationship). **Escalating this per directive §10, not implementing it here.**

**F. Relative references (DX-2).** Two S-D rows (`SD-D-01`, `SD-D-02`) and two natural-corpus rows the original A2.5 inventory (plan §1.2) already tagged Class D (`NB-D-02` C2 r1, `NB-L-09` C2 r2) require antecedent-relative reasoning ("the one before *that*/*it*"). None of H1-H4 implement or attempt antecedent tracking; H3 incidentally converts both natural-corpus Class-D ICBs to safe abstentions as a side effect of its domain restriction (not because it understands the antecedent), which is disclosed above, not claimed as a fix. **F is not solved in this batch** (directive §20.F explicitly does not ask it to be); the capability gap is the same one plan §2's DX-2 row names: session/antecedent state, which stays deferred.

## 7. Evidence-condition table (directive §21)

| Evidence situation | Verdict | Supporting rows |
|---|---|---|
| Ordinal span has ≥1 substantive token matching the winning candidate | `LEVEL_5_BIND_SUPPORTED` | S-D `SD-N-01`; S-C rows in `H1` scoring_class=CORRECT_RESOLUTION unchanged from H0 |
| Ordinal span has zero substantive tokens, pool ≤2-3, no attachment wording | `LEVEL_5_BIND_SUPPORTED` (baseline already correct; H1 incorrectly vetoes this — see §5 H1) | S-D `SD-N-03`, `SD-A-04`, `SD-A-06`; natural-corpus rows in plan §1.2's "14 correct Level-5 rows at risk" |
| Explicit attachment wording, ≥2 attachment candidates, ordering evidence not independently verified as current-turn-authoritative | `LEVEL_5_5_PRECEDENCE_SUPPORTED` | S-C `NB-C-04`, `NB-C-05`; S-D `SD-A-05`, `SD-A-07` (H2/DX-1 both close these; DX-1 identifies the rank clock as the specific cause) |
| Explicit attachment wording, ≥2 attachment candidates, ordering evidence IS current-turn-authoritative (Q2 Case A) | `ABSTAIN_SUPPORTED` is **wrong** for this case (the correct behaviour is `LEVEL_5_BIND_SUPPORTED`); no hypothesis measured here achieves it without also mishandling the Case-B twin | `UNSUPPORTED` (H2 forces abstention here; only distinguishable given the contract field named in §E) — S-D `SD-A-04`/`SD-A-06` vs. `SD-A-05`/`SD-A-07` |
| Span's substantive tokens absent from every candidate ("the earlier contract" with no contract in the pool) | `ABSTAIN_SUPPORTED` (H3 achieves this as a byproduct) | S-D `SD-B-02`; S-C `NB-J-02`, `NB-J-04` |
| Span's substantive tokens present but only on a candidate the pool-wide ordinal rank does not select ("the latest board minutes") | `UNSUPPORTED` as currently measured — H3 removes the wrong bind but lands on an uninformative abstention via the Level-6 interaction, not the correct bind | S-D `SD-C-02`; S-C `NB-D-01` C2 |
| Lexically distinguished attachment ("the attached invoice" among 2 attachments) | `UNSUPPORTED` — no hypothesis in this batch narrows Level 5.5 lexically; every variant returns AMBIGUOUS | S-D `SD-A-08` |
| Abbreviation/alias mismatch between span and candidate title ("St" / "Street") | `UNSUPPORTED` (known, accepted limitation — not attempted) | S-D `SD-C-03` |
| Antecedent-relative reference ("the one before that/it") | `UNMEASURED` beyond tagging — DX-2 quantifies, does not resolve | S-D `SD-D-01`, `SD-D-02`; S-C `NB-D-02` C2 r1, `NB-L-09` C2 r2 |

## 8. Diagnostics summary

- **DX-1 causal result:** rank clock is the dominant, directly-fixable cause of Class A wherever the tie set is complete; one natural-corpus instance (`NB-C-05` C2) shows the corpus's own `turn_attachments` data does not fully cover every candidate-pool cell, which is a data/harness note, not a DX-1 mechanism defect. See §D.
- **DX-2 count:** 4 rows tagged relative-anchor across S-C + S-D (2 natural-corpus, 2 authored). See §F.
- **Level 5 vs. Level 5.5 interaction:** H2's unconditional precedence and H1's fall-through mechanism converge on the same 6 Class-A ICBs through independent routes, and diverge on the same 2 Case-A negative controls they both incorrectly sacrifice (`SD-A-04`, `SD-A-06` for H2; those plus `SD-N-03` for H1) — see §B.
- **Ordering-domain / ordering-clock findings:** see §C, §D above. The dominant, previously-unmeasured finding of this batch is the **H1/H3 fall-through → Level-6 recency-literal interaction** (§C) — a genuine architecture-level gap (Level 6's substantive-token computation does not share H1/H3's R3(a) exclusion) that limits both H1 and H3 more than the plan anticipated, independent of anything H1/H3 do wrong on their own terms.

## 9. Unmeasured follow-up hypotheses (not implemented; recorded per directive §17)

1. **Level 6 substantive-token exclusion should include the R3(a) recency vocabulary**, mirroring H1/H3's own definition, so that a Level-5 fall-through does not spuriously flag the reference's own recency word as a missing entity. This is the single change most likely to materially improve both H1's and H3's measured results — but it modifies Level 6, which is outside H1/H2/H3's frozen scope (Level 5/5.5 only) and outside this batch's authorization to touch `rar_deterministic.py`. **Not implemented.**
2. **Lexical narrowing inside Level 5.5** (an "H3-for-attachments" — restrict `is_attachment` candidates by the span's substantive tokens before counting, the way H3 restricts Level 5's ordinal domain) would resolve the `SD-A-08` "the attached invoice" class, currently unresolved by every variant. **Not implemented** — no hypothesis in the accepted plan covers Level 5.5's own candidate-set computation.
3. **A RAR contract field for current-turn attachment membership/order** (§E) — the architecture escalation directive §10 requires when DX-1 shows correct resolution needs evidence RAR does not carry. Confirmed needed here. **Not implemented** (contract changes are explicitly out of scope, directive §1/§18).

## 10. Scope confirmation

- Baseline `rar_deterministic.py`: **unchanged** (SHA-256 identical pre/post every run).
- `rar_contracts.py`: **unchanged**.
- `rar_safe_experimental.py`: **unchanged** (imported only for its frozen `_RECENCY_VOCABULARY` constant, byte-identical reuse, no new words).
- D1RQ detector, natural-boundary corpus: **unchanged**.
- No S1/S2/S3 work performed; H3 is explicitly distinguished from S2 in the plan (§2 scope note) and this report does not blur that line.
- No New-F/Level-6 scoring change (§9's follow-up #1 above is recorded as a finding, not implemented).
- No production recency wiring, no production promotion.
- No commit, no push.

**State set to `VERIFICATION_READY`.** No self-acceptance performed. Awaiting independent audit / User direction before any repair, promotion, or release action.
