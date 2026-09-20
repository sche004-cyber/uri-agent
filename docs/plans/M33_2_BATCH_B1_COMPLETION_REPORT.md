# M33.2 Batch B.1 — Micro-Model Ensemble Qualification Completion Report

**Implementation status:** VERIFICATION_READY  
**Date:** 2026-09-20  
**Authority:** `docs/plans/M33_2_BATCH_B1_MICRO_MODEL_ENSEMBLE_PLAN.md`

## Outcome

Batch B.1 is implemented as a benchmark-only, proposal-only experiment. It
does not add production language/reasoning provider contracts, alter Main
Brain escalation, or wire any ensemble into production routing. The frozen
20-item URI-owned corpus contains four items in each of the five canonical
tiers. Every materialized evidence manifest records corpus SHA-256
`22429ea63098a7923cf31abd252785b6cf14512084972fbcb65bc5ecbc33f811`.

Fixture candidates qualify only as deterministic harness comparisons. They
are not evidence that the corresponding real models qualify. Actual local
configurations A–D are `UNAVAILABLE` in this environment and were not
converted into passes.

## Changed files

- `uri_core/core/edge/adapters/benchmark.py` — canonical score semantics,
  fail-closed validation order, binned ECE/MCE and NLL, tier metrics,
  candidate outcome classification, and resource/latency instrumentation.
- `uri_core/core/edge/adapters/ensemble.py` — experimental A–D definitions,
  deterministic fixture components, selectable Qwen/DeepSeek tiny-reasoner
  identifiers, and truthful runtime discovery details.
- `uri_core/core/edge/adapters/__init__.py` — experimental adapter exports.
- `fixtures/m33_2_edge_benchmark/corpus.json` — 20 frozen synthetic items,
  four per canonical tier.
- `fixtures/m33_2_edge_benchmark/manifest.json` — corpus shape/provenance and
  materialized-SHA contract.
- `scripts/m33_2_edge_benchmark.py` — nine-run fixture/actual A–D evidence
  matrix under `temp_evidence/m33_2_batch_b1/`.
- `test_m33_2_batch_b_benchmark.py` — expanded-corpus-compatible safe fixture.
- `test_m33_2_batch_b1_ensemble_benchmark.py` — B.1 metric, validation,
  instrumentation, configuration, egress, and recursive boundary coverage.
- Milestone state/governance handoff files — verification-ready transition.

## Configuration evidence

| Configuration | Runtime | Qualification | Overall | Reflex | Language rubric | Bounded reasoning | Correct escalation | False escalation |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Fixture baseline | available | QUALIFIED_FOR_COMPARISON | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |
| Fixture A: Core + Needle 3 | available | QUALIFIED_FOR_COMPARISON | 0.60 | 1.00 | 0.33 | 0.00 | 1.00 | 0.00 |
| Fixture B: A + SmolLM2 | available | QUALIFIED_FOR_COMPARISON | 0.80 | 1.00 | 1.00 | 0.00 | 1.00 | 0.00 |
| Fixture C: A + tiny reasoner | available | QUALIFIED_FOR_COMPARISON | 0.80 | 1.00 | 0.33 | 1.00 | 1.00 | 0.00 |
| Fixture D: A + SmolLM2 + tiny reasoner | available | QUALIFIED_FOR_COMPARISON | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |
| Actual A | unavailable | UNAVAILABLE | 0.00 | unavailable | unavailable | unavailable | unavailable | unavailable |
| Actual B | unavailable | UNAVAILABLE | 0.00 | unavailable | unavailable | unavailable | unavailable | unavailable |
| Actual C (Qwen2.5 control) | unavailable | UNAVAILABLE | 0.00 | unavailable | unavailable | unavailable | unavailable | unavailable |
| Actual D (Qwen2.5 control) | unavailable | UNAVAILABLE | 0.00 | unavailable | unavailable | unavailable | unavailable | unavailable |

Actual details are explicit: `URI_EDGE_NEEDLE3_MODEL_PATH`,
`URI_EDGE_SMOLLM2_135M_MODEL_PATH`, and
`URI_EDGE_QWEN2_5_1_5B_MODEL_PATH` are not set. The adapter also supports
DeepSeek-R1-Distill-Qwen-1.5B selection and reports its absent path/callable
the same way; no local weights/runtime were available for either tiny
reasoner, so no comparative model claim is possible.

## Calibration, latency, and resources

| Fixture | ECE | MCE | NLL | p50 ms | p95 ms | RSS load delta MiB | RSS benchmark delta MiB | TTFT p50 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | 0.062 | 0.062 | 0.0652 | 0.0018 | 0.0034 | 0.0000 | 3.5234 | 0.1 |
| A | 0.242 | 0.550 | 0.3425 | 0.0008 | 0.0031 | 0.0000 | 0.0000 | 0.0 |
| B | 0.152 | 0.550 | 0.2039 | 0.0011 | 0.0025 | 0.0000 | 0.0039 | 0.0 |
| C | 0.152 | 0.550 | 0.2039 | 0.0011 | 0.0024 | 0.0000 | 0.0000 | 0.0 |
| D | 0.062 | 0.062 | 0.0652 | 0.0014 | 0.0024 | 0.0000 | 0.0039 | 0.1 |

Fixture process RSS before load was 23.9961–27.5703 MiB. Fixture load times
were 0.0004–0.0008 ms. These values measure deterministic Python fixture
dispatch, not model footprint or inference performance. Actual candidates
record p50/p95/TTFT as `unavailable`; GPU and VRAM observability were also
`unavailable`. No values were fabricated or inferred from vendor claims.

## Bounded defects repaired

1. Canonical `score_semantics` now rejects before corpus tier validation or
   runtime loading, restoring the required fail-closed ordering.
2. Missing/unknown corpus tiers now return a terminal `REJECTED` result
   instead of raising an unhandled `ValueError`.
3. Probability validation now accepts real numeric 0/1 values while rejecting
   booleans, NaN, missing values, and values outside 0.0–1.0.
4. The Batch B safe fixture now answers the expanded corpus from each item's
   expected value and explicitly marks escalation-tier outputs.

## Verification

- `pytest test_m33_2_batch_b1_ensemble_benchmark.py -v`
- `pytest test_m33_2_batch_b_benchmark.py -v`
- `pytest test_m33_2_batch_a_edge_foundation.py -v`
- Combined focused result: **29 passed**.
- Live runner: **9/9 artifact directories written**, all with matching corpus
  SHA-256; five fixture runs completed and four actual runs reported
  unavailable.
- Full `pytest -q`: **2,217 passed, 10 failed, 7 skipped, 40 subtests passed**.
  The 10 failures are the exact accepted Batch B baseline set:
  `step3_test.py::test_drive`, `step4_test.py::test_download`,
  `test_m20_feasibility_validation.py`, two
  `test_m20_recovery_loop.py`, two
  `test_m20_semantic_interpreter_resilience.py`,
  `test_orchestrator_session_workflow.py`,
  `test_usage_import_boundary.py`, and
  `test_workflow_restart_recovery.py`. Batch B recorded 2,202 passes with
  this same 10-failure/7-skip shape; B.1 adds 15 passing cases and no new
  regression.
- `git diff --check`: clean (line-ending notices only).

## Recommendation and limitations

The simulated tier split behaves as designed: A covers reflex work, B adds
language coverage, C adds bounded reasoning, and D covers both. That is a
harness validation, not a real-model ranking. No specialist can truthfully be
called redundant and no footprint trade-off can be decided until local
Needle 3, SmolLM2, and both tiny-reasoner runtimes are available and measured.
Production architecture remains unchanged. Claude must independently audit
the source, artifacts, and regression evidence before any acceptance or
release action.

## Claude independent audit addendum (2026-09-20)

**VERDICT: ACCEPT — `HARNESS_COMPLETE` / `REAL_CANDIDATE_QUALIFICATION_PENDING`.**

Every claim in this report was independently re-verified against primary
evidence rather than trusted: full reads of the changed/new source
(`benchmark.py`, `ensemble.py`, `adapters/__init__.py`); a hand-computed
check of the binned ECE/MCE formula (`_metrics()`) against the new test's
expected values (ECE=0.25, MCE=0.35 on a 4-row/2-bin fixture — matches
exactly); confirmation that the `score_semantics` enum check runs before
tier validation and before `candidate.load()` (fail-closed, as claimed);
confirmation that `psutil` is a pre-existing dependency
(`requirements.txt:17`), not a new/unflagged one; independent re-execution
of the focused suite (`29 passed in 9.22s`, exact match); a from-bytes
SHA-256 recomputation of `corpus.json`
(`22429ea63098a7923cf31abd252785b6cf14512084972fbcb65bc5ecbc33f811`,
matching this report's claim exactly); direct enumeration of all 20 corpus
items confirming 4 per each of the 5 canonical tiers; spot-checks of
`temp_evidence/m33_2_batch_b1/*/result.json` confirming actual A–D
candidates honestly report `UNAVAILABLE` with the exact missing env var
named, never a fabricated pass; and two independent full-suite `pytest -q`
runs (Claude's own, and a separate sub-agent's), both producing
`10 failed, 2217 passed, 7 skipped, 40 subtests passed` with the identical
10 failure names as the accepted Batch B baseline — no new regression.

One disclosed, non-blocking limitation not previously recorded:
`reflex_accuracy` (`benchmark.py:455`) reuses the same generic
`answer == expected` comparison used for every other tier rather than a
bespoke routing/extraction-specific match. It satisfies the plan's intent
only insofar as corpus authors encode routing/extraction outcomes as the
`answer`/`expected` fields (which the actual corpus does). Real but
generic — carried forward as a limitation, not a defect blocking
acceptance.

No bounded repair was required. The implementation is sound as delivered.
Full evidence and the acceptance-criterion-by-criterion table are recorded
in this session's audit plan document.
