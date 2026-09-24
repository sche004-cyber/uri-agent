# M35 URIv1 — A2.8K-R2 Independent Audit

**Verdict:** `ACCEPT`

**Audit date:** 2026-09-24
**Auditor:** independent auditor (verdict delivered directly to the User; recorded here verbatim, findings not modified or supplemented by Claude)
**Audited branch:** `m35-uri-v1-parallel-architecture`
**Audited HEAD:** `925de8f71f73ecf67713392ca9ce959de7a12d07`
**Repairs audited:** `docs/plans/M35_URIV1_A2_8K_R2_REPAIR_REPORT.md` against `M35_URIV1_A2_8K_R2_TELEMETRY.json` / `_R2_AGGREGATES.json`

---

## Verdict

ACCEPT

## Reproduction & Integrity

- Verified branch `m35-uri-v1-parallel-architecture` at HEAD `925de8f`.
- Two fresh in-memory battery runs reproduced all 3,636 decision rows and 19 S-E records exactly, including the saved R2 results and determinism.
- Focused verification passed: 104 tests and 114 subtests.
- All six protected files matched their original, R1, and R2 pre/post hashes.
- Contracts and frozen S-D fixtures remained unchanged.
- Original and R1 evidence hashes matched the values recorded in the R2 report.

## Activation-Boundary Audit

R2's activation-boundary repair is valid.

- Domain-relative ranking activates only when candidate-ID membership is genuinely narrowed.
- Unchanged domains retain baseline global ranks and the Level-5 `has_ordering` gate.
- No-substantive-token queries retain baseline behavior.
- Instrumentation observed 590 narrowed-domain calls, all reranked; 460 unchanged-domain calls, none reranked; zero activation-boundary mismatches.
- Every pure-H3 unchanged-domain decision matched H0.
- `SD-C-02` and `NB-D-01` C2 remain correctly resolved.
- Gapped-rank `{1,3} -> {0,1}` behavior remains correct.

## R1 → R2 Diff

Exactly four ordinary decision rows changed:

- `NB-D-03` r1 C2 — H3: R1 `RESOLVED` → R2/H0 `AMBIGUOUS`
- `NB-D-03` r1 C2 — H4: R1 `RESOLVED` → R2/H0 `AMBIGUOUS`
- `NB-L-06` r1 C2 — H3: R1 `RESOLVED` → R2/H0 `UNKNOWN`
- `NB-L-06` r1 C2 — H4: R1 `RESOLVED` → R2/H0 `UNKNOWN`

These are legitimate reversions of R1's invalid dense reranking on unchanged domains, not new regressions against H0.

## Decision Accounting

Independent raw comparison produced:

- H1: 11 changed / 6 closed ICB / 0 new ICB / 5 lost correct
- H2: 8 / 6 / 0 / 2
- H3: 45 / 14 / 0 / 15
- H4: 56 / 20 / 0 / 20
- DX-1: 5 / 5 / 0 / 0

All 606 decision keys contain all six variants. Aggregate changed-row keys and contents exactly reconcile with the raw scan.

## H3/H4 Qualification

- H3: 149 correct resolutions, 12 ICBs
- H4: 144 correct resolutions, 6 ICBs

Frozen-rubric classifications:

- H1: `PARTIALLY_SUPPORTED`
- H2: `PARTIALLY_SUPPORTED`
- H3: `PARTIALLY_SUPPORTED`
- H4: `PARTIALLY_SUPPORTED`

Each closes target ICBs, introduces zero new ICBs, and has its correct-resolution losses disclosed.

## Regression / Safety Findings

- The former `test_rc1_current_conflicting_no_rank0_abstains` conflict is cleared for H3 and H4.
- Baseline abstention is restored for unchanged-domain and no-substantive-token cases.
- R2 introduces no new ICB and no new divergence from H0.
- Existing measured costs and residual failures remain correctly represented by `PARTIALLY_SUPPORTED`.

## Provenance Limitations

- The original independent audit exists as a repository artifact.
- The R1 independent re-audit did not have a separate repository audit file.
- A2.8K/R1/R2 artifacts were still uncommitted at audit time, so Git did not provide immutable chronology for them.
- Present bytes, hashes, and reproducibility were independently verified.

## Required Next Action

Record this independent `ACCEPT` verdict through the authorized milestone governance flow.

No additional R2 repair is required.

STOP — NO IMPLEMENTATION, PROMOTION, OR NEXT EXPERIMENT PERFORMED.

---

## Closeout note

This artifact records the independent R2 audit verdict verbatim as delivered to the User; no finding above was added, altered, or interpreted by Claude. Recorded here per instruction because the R1 independent re-audit had no equivalent standalone repository file — R2's ACCEPT does not inherit that gap; it is now filed on disk as required by this milestone's evidence-preservation rules.
