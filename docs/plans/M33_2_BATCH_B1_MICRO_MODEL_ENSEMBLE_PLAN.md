# M33.2 Batch B.1 — Micro-Model Ensemble Qualification

**Status:** DRAFT → ACCEPTED (standing auto-approval, `ORCHESTRATION.md` §1.5 —
routine benchmark-only extension; does not touch core project structure,
product identity, or the security/authority model)
**Authorized by:** direct User instruction, 2026-09-20 (Batch B ACCEPT +
Batch B.1 start instruction)
**Depends on:** Batch B `906c527`/`e3911f3` (CLOSED/ACCEPTED,
`docs/plans/M33_2_BATCH_B_STATE.md`)

## Purpose

Determine experimentally whether URI's lightweight Edge/Second-Brain
benefits from specialized micro-models beyond a single generalist, without
prematurely changing production architecture. Evidence-driven, not
vendor-claim-driven, per `research_notes/Edge runtime evaluation/patterns.md`.

## Configurations to test (independently, via the harness only)

- **A.** URI deterministic core + Needle 3
- **B.** Core + Needle 3 + SmolLM2-135M-Instruct
- **C.** Core + Needle 3 + one tiny reasoner (candidate below)
- **D.** Core + Needle 3 + SmolLM2-135M-Instruct + tiny reasoner

Hypothesized roles (not assumed correct — the benchmark must confirm or
reject each):
- Needle 3 → intent/tool routing, extraction, structured proposals.
- SmolLM2-135M-Instruct → lightweight language/response generation.
- Tiny reasoner → bounded local reasoning.
- Main Brain → optional escalation only, never required for a
  deterministic or reflex-tier task.

## Candidate tiny reasoner(s) considered

Two candidates to benchmark, not pre-select — footprint is itself an
acceptance criterion, so both must clear the harness's resident-memory and
load-time bars before either is preferred:

1. **DeepSeek-R1-Distill-Qwen-1.5B** — reasoning-distilled specifically
   (chain-of-thought behavior trained in), largest footprint of the two;
   tests whether reasoning-specialization is worth ~10x SmolLM2's size.
2. **Qwen2.5-1.5B-Instruct** — general instruct model, not
   reasoning-distilled; serves as the control to isolate whether any gain
   over Needle-alone comes from "more parameters" rather than genuine
   reasoning specialization.

Both are local-only, license-permissive, and quantizable to GGUF for the
existing local-runtime pattern already used for Needle evaluation. Neither
is installed or wired by this plan — Batch B.1 only prepares the harness to
measure them if/when weights are available locally; an unavailable runtime
is recorded as `unavailable`, never silently converted to a pass (per
Batch A/B's truthful-limitation-classification standard).

## Benchmark / corpus expansion

Current corpus (`fixtures/m33_2_edge_benchmark/corpus.json`) is 2 items and
proves harness plumbing only — a disclosed Batch B residual. Batch B.1 must
expand it into task-tier buckets so results can be attributed to the right
tier rather than one blended score:

- **deterministic** — tasks requiring no model (control: must never invoke
  any candidate).
- **reflex/routing** — intent/tool-selection/extraction tasks (Needle's
  hypothesized tier).
- **language-only** — response-generation quality with no routing/reasoning
  demand (SmolLM2's hypothesized tier).
- **bounded-reasoning** — tasks needing multi-step local inference within a
  fixed step/token budget (tiny-reasoner's hypothesized tier).
- **escalate** — tasks that should be honestly declined/escalated to the
  Main Brain rather than answered locally (tests over-confidence, not just
  coverage).

Corpus stays synthetic, URI-owned, frozen, and SHA-256-manifested, same
provenance discipline as Batch B. Target: enough items per tier for the
metric fixes below to be meaningful (tens, not thousands — this is still an
experimental harness, not a production eval suite).

## Metric corrections carried forward from Batch B (mandatory, in scope here)

1. **Replace unbinned ECE/MCE** (`uri_core/core/edge/adapters/benchmark.py`
   `_metrics()`) with standard confidence-binned calculation: bin by
   predicted-score decile (or coarser, given small n), compute per-bin
   `|accuracy − mean-confidence|`, weight by bin population for ECE, take
   the max for MCE. NLL stays per-sample log-loss (already correct).
2. **Replace presence-only `score_semantics` validation** with a canonical,
   enumerated vocabulary (e.g. `{"probability", "calibrated_confidence",
   "raw_logit_derived", "none"}`) and range validation (`0.0–1.0` where the
   semantics claims a probability); reject anything outside the enum or out
   of range as `REJECTED` (ambiguous/incomparable), not silently accepted.
3. Add the new tiers' own metrics: routing/extraction accuracy (tier
   "reflex"), bounded-reasoning task success under a fixed step budget
   (tier "bounded-reasoning"), language-generation usefulness as a rubric
   score not a raw LM-loss proxy (tier "language-only"), and escalation
   rate (fraction of "escalate"-tier items correctly declined vs. tier
   "deterministic"/"reflex" items incorrectly escalated).

## Resource/latency instrumentation (new)

`BenchmarkResult.resource` is currently hardcoded
`{"cpu_gpu_ram_vram": "unavailable"}`. Batch B.1 must make this genuinely
observable where the platform allows it, and continue to say `unavailable`
truthfully where it does not:
- resident memory (RSS) before/after each candidate loads, via
  `resource.getrusage`/`psutil` if already a dependency (check first; do
  not add a new third-party dependency without flagging it as a plan
  change) — CPU-only observation is achievable on Windows without new
  privileged access.
- model/runtime load time (wall clock, already have the pattern from
  `run_benchmark`'s `time.perf_counter` use).
- TTFT (time to first token) — only measurable for candidates whose
  `invoke` can report a partial/streaming timestamp; record `unavailable`
  for non-streaming candidates rather than approximating.
- total latency — already implemented (p50/p95).
- GPU/VRAM utilization — record `unavailable` unless a GPU and its
  observability library are confirmed present; do not fabricate a number.

## Local-only / zero-egress compliance

Unchanged mechanism from Batch B: `outbound_deny=True` mandatory,
`candidate.local_only` mandatory, no network primitives in harness code.
Batch B.1 adds nothing here except re-running the same static check
(`grep` for socket/requests/urllib/http) across any new adapter files.

## Failure and ambiguity handling

Extend `safety` beyond `pass`/`reject` only if a genuine new failure mode is
found (e.g. a candidate that times out vs. one that returns garbage vs. one
that claims host execution) — do not add states speculatively. Every
tier's "no result" case (timeout, crash, missing runtime) must be recorded
as its own outcome, never folded into "correct" or "incorrect".

## Files expected to change

- `uri_core/core/edge/adapters/benchmark.py` — binned ECE/MCE, canonical
  `score_semantics` enum, new tier-aware metrics, resource instrumentation.
- `uri_core/core/edge/adapters/` — new candidate-adapter modules per tested
  configuration (A/B/C/D), still dict-in/dict-out, still never importing
  approval/dispatch/registry/orchestrator (must pass the now-recursive
  `test_m33_2_batch_a_edge_foundation.py` boundary test unchanged).
- `fixtures/m33_2_edge_benchmark/corpus.json` (+ `manifest.json`) — tier
  expansion.
- `scripts/m33_2_edge_benchmark.py` — run all four configurations, write
  per-configuration artifacts to `temp_evidence/m33_2_batch_b1/`.
- New focused test file, e.g. `test_m33_2_batch_b1_ensemble_benchmark.py`.
- New completion report + STATE file at closure
  (`docs/plans/M33_2_BATCH_B1_*`), same pattern as Batch A/B.

**Not expected to change:** `orchestrator.py`, `server.py`, dispatcher,
approval, credential, capability registry, any UI file, any Batch A/B
contract file (`contracts.py`, `routing_policy.py`, `runtime_inventory.py`,
`settings.py`, `trace.py`).

## Explicit non-goals / architecture boundaries

- No `EdgeLanguageProvider` or `EdgeReasoningProvider` production contract.
- No wiring of any ensemble configuration into production routing or the
  Main Brain escalation path.
- No Batch C work.
- No claim that the full ensemble is superior — the report must explicitly
  state, with evidence, whether Needle-alone, Needle+SmolLM2, or
  Needle+tiny-reasoner already captures most of the value, and whether the
  full 4-model configuration's footprint is justified by its incremental
  capability.
- No change to who holds execution/approval/credential authority — the
  harness produces measurements, never proposals that bypass
  propose→validate→approve→execute.

## Stop condition

Implementation stops at `VERIFICATION_READY` with a completion report
listing exact configurations tested, measured footprint/latency,
capability results per tier, failures/limitations, any specialist found
redundant, and a non-implemented recommendation for later production
architecture. No commit/push until Claude's independent audit runs and
returns a verdict, per standing release authority.
