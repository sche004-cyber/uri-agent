# M33.2 Batch B — Accepted State

**Status:** ACCEPTED (independent review)
**Baseline before this batch:** `bf177a5` — `feat(m33.2): close accepted Batch A foundation`
**Committed and pushed at:** `906c527` — `feat(m33.2): close accepted Batch B benchmark/qualification harness`
**Recorded:** 2026-09-20

## Accepted implementation

Batch B adds only a reversible, URI-owned benchmark and qualification
harness behind the Batch A Edge contracts: `uri_core/core/edge/adapters/`
(`benchmark.py`, `__init__.py`), `scripts/m33_2_edge_benchmark.py`, the
frozen synthetic corpus/manifest under `fixtures/m33_2_edge_benchmark/`,
and its focused test `test_m33_2_batch_b_benchmark.py`. Zero tracked
production files were modified (`git diff HEAD --stat` against the prior
baseline was empty before this batch's own commit). It does not add
production Edge routing, execution bypass, a second capability registry,
a UI/settings-authority change, or any `orchestrator.py` change, and does
not begin Batch C.

The harness is proposal-only: candidates are plain dict-in/dict-out
callables, never reach approval/dispatch/capability-registry/orchestrator,
and the harness itself rejects host-function claims, out-of-shortlist
capability IDs, absent score semantics, non-local candidates, and disabled
outbound-deny mode. No vendor candidate (Cactus, Needle) is qualified or
promoted; only an internal `conventional-fixture-baseline` control ran.

## Independent audit repair

The Batch A static import-boundary test used a non-recursive
`root.glob("*.py")` over `uri_core/core/edge/`, which never scanned the new
`adapters/` subdirectory Batch B introduced — a real coverage gap, though no
forbidden import was present. Repaired both occurrences in
`test_m33_2_batch_a_edge_foundation.py` to `root.rglob("*.py")`. Re-run
confirmed `adapters/` is clean and now covered.

## Verification evidence

| Check | Result |
| --- | --- |
| Focused Batch A+B suite (post-repair) | **14/14 passed** |
| Independent full-suite re-run (fresh, not the prior WinError-5 run) | **2,202 passed, 10 failed, 7 skipped** |
| Regression classification | All 10 failures are pre-existing, unrelated to Edge/adapters (`step3_test.py::test_drive`, `step4_test.py::test_download`, `test_m20_feasibility_validation.py`, `test_m20_recovery_loop.py` ×2, `test_m20_semantic_interpreter_resilience.py` ×2, `test_orchestrator_session_workflow.py`, `test_usage_import_boundary.py`, `test_workflow_restart_recovery.py`) — same failure/skip shape as Batch A's accepted baseline (2199/10/7). **No Batch B regression.** |
| End-to-end artifact generation | Ran `scripts/m33_2_edge_benchmark.py` live: produced real `corpus_sha256` and `result.json` with genuine computed values (not placeholders). |
| Egress claim | Verified no network primitives (`socket`/`requests`/`urllib`/`http`) anywhere in new code. |

## Disclosed residuals (mandatory carry-forward, not blocking Batch B ACCEPT)

1. **ECE / maximum calibration error are unbinned** (sample-wise mean/max of
   `|p-y|`), not standard binned-confidence ECE/MCE. Harmless at the current
   2-item fixture scale but must be corrected before any real candidate
   qualification decision relies on these fields.
2. **`score_semantics` validation is presence-only** (non-empty/non-None),
   not a canonical vocabulary or range/comparability check. Must be defined
   and validated before ambiguous or incomparable vendor scores could pass.
3. **Corpus is 2 synthetic items** — proves harness plumbing only. Must be
   expanded before drawing any qualification conclusion from it.

## Next boundary

Batch B.1 may extend the benchmark/qualification harness only, to evaluate
non-production micro-model ensemble configurations (Needle 3, a
language-generation specialist, a tiny reasoner) purely as an experimental,
proposal-only measurement exercise. It must not create production language/
reasoning provider contracts, must not wire any ensemble into production
routing, and must not begin Batch C.
