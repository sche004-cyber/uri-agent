# M33.2 Batch B — Completion Report

**Status: VERIFICATION_READY — awaiting independent review. Do not promote or commit.**

## Changed files

`fixtures/m33_2_edge_benchmark/{corpus.json,manifest.json}`, `scripts/m33_2_edge_benchmark.py`, `uri_core/core/edge/adapters/{__init__.py,benchmark.py}`, and `test_m33_2_batch_b_benchmark.py`.

## Boundary evidence and methodology

The harness is experimental-only and is not imported by `server.py`, the dispatcher, registry, approval, credential, or `orchestrator.py`. Candidates provide only a dict-shaped proposal/result. The harness rejects host-function claims, out-of-shortlist capabilities, absent score semantics, non-local candidates, disabled outbound-deny mode, and non-improving candidates. Corpus is frozen, synthetic, versioned, SHA-256 manifested, and records platform, latency, correctness, ECE, maximum calibration error, NLL, resource observability, and safety result. Raw manifest/result output is written to `temp_evidence/m33_2_batch_b/` (ignored runtime evidence).

## Candidates and results

The runnable control is `conventional-fixture-baseline`, an independent local text-model-shaped adapter used only to prove harness semantics. Needle is represented as proposal-only and rejected unless it supplies score semantics; Cactus is not tested because this Windows environment has no documented installed Cactus runtime/modality evidence. No vendor candidate is qualified or promoted. Resource values are explicitly `unavailable`; no CPU/GPU/RAM/VRAM claim is made.

## Privacy / egress

`run_benchmark(..., outbound_deny=True)` is mandatory and rejects a non-local candidate or any disabled deny setting before invocation. The corpus contains no user content or credentials. This is harness-level verification, not a host firewall proof; therefore no local-only vendor claim is accepted.

## Verification and residuals

Focused Batch B tests cover calculation/qualification, host-execution rejection, score-semantics rejection, and local outbound-deny gating. A combined Batch-A/B run was blocked by a Windows system-temp ACL failure (`WinError 5`); it is environmental and invalidates that run, rather than being counted as a pass. Batch A’s accepted independent evidence remains 12/12 focused and 2199 passed / 10 baseline failures / 7 skipped. Full regression and genuine local Needle/independent-model runs remain required for independent review.

Batch B remains reversible, has no production Edge routing, no settings mutation path, no UI change, no adaptive calibration, and no `orchestrator.py` change.
