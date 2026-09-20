# M33.2 Batch B.4 — Real Edge-Model Qualification Completion Report

**Implementer:** Codex  
**Date:** 2026-09-20  
**Status:** `VERIFICATION_READY` — awaiting Claude independent audit  
**Plan authority:** `docs/plans/M33_2_BATCH_B4_REAL_MODEL_QUALIFICATION_PLAN.md`

## Outcome

B.4 completed a real, local qualification run without promoting any model
into production routing. The run reused B.1's ensemble and scoring harness,
B.2's perception candidates, and B.3's checksum-verified lifecycle/storage
and lazy-state vocabulary. No production dispatcher, orchestrator, server,
approval, credential, capability-registry, provider-catalogue, Batch C, or UI
path changed.

The evidence supports one Edge resident recommendation: **Needle 3 for
proposal-only reflex routing and structured extraction**. The tested
SmolLM2-135M language worker and Qwen2.5-0.5B reasoner did not provide enough
quality gain to justify their memory cost; both are `BYPASS / REDUNDANT` for
the measured tasks. STT, OCR, and VLM remain truthfully unavailable under the
accepted sourcing/runtime constraints.

Raw evidence is under `temp_evidence/m33_2_batch_b4/` (local generated
evidence, intentionally gitignored). The consolidated machine-readable record
is `temp_evidence/m33_2_batch_b4/consolidated_results.json`.

## Environment and sourced assets

Host observation during the final run:

- Windows AMD64; 12 physical / 24 logical CPU cores; observed CPU frequency
  4276 MHz.
- Total RAM 24,500.84 MiB; available RAM at the observation point 827.14 MiB.
- GPU and VRAM: `unavailable` (`no observable GPU API`).
- Free disk: 76,608.12 MiB.
- Needle: `cactus-needle==3.0.2` in `.venv-needle`; native engine cache
  version 3.0.1; telemetry disabled; `HF_HUB_OFFLINE=1`.
- Existing Ollama controls only: `qwen3.5:9b` and `gemma4:12b`. No pull or
  model download was requested from Ollama.

Every new runtime/model asset was downloaded by
`edge_lifecycle.download_model_artifact()` into
`uri_workspace/edge_models/` and re-hashed before execution:

| Asset | Bytes | SHA-256 | Source/version | License |
|---|---:|---|---|---|
| llama.cpp Windows CPU x64 | 18,466,610 | `8c5dc1310d9c61953d8079ebe10ee156afa935837516fef3bcad29365ab12122` | official `ggml-org/llama.cpp` release `b11063` | MIT |
| SmolLM2-135M-Instruct Q3_K_M GGUF | 93,511,232 | `61c69fc5ce91982e26c625d43be5c3c7f0f774da22f4fa4e45c37a80a22ddad4` | TensorBlock repository commit `32db44d69cedb731dc0fc96f60e01a86c6f5919d` | Apache-2.0 |
| Qwen2.5-0.5B-Instruct Q4_K_M GGUF | 491,400,032 | `74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db` | official Qwen repository commit `9217f5db79a29953eb74d5343926648285ec7e67` | Apache-2.0 |

The portable llama.cpp archive was expanded only inside its confined
`uri_workspace/edge_models/` directory. `.gitignore` now explicitly excludes
the managed asset root so model binaries cannot be accidentally committed.

### Dependency declaration

**No new Python dependency was added.** `requirements.txt` is unchanged.
Instead of compiling `llama-cpp-python` (no Python 3.13 wheel/build toolchain
was available), the run used the pinned portable llama.cpp CPU runtime above.
`faster-whisper` was not installed because a complete, multi-file checkpoint
could not be sourced with an accepted published SHA-256 for every required
file through the existing B.3 lifecycle API. This is recorded as an
environment/sourcing limitation, not a successful STT qualification.

## Corpus amendment

The frozen B.1 corpus was extended additively from 20 to 24 items with four
synthetic structured-record extraction cases. The manifest now records eight
reflex items and four items in each other tier. The existing four reflex
routing items gained additive `expected_arguments` metadata; their original
inputs and `expected` routing outputs were not rewritten. The live runner
materializes and records the resulting corpus SHA-256 in every evidence
bundle.

## Real qualification results

### Needle 3

Needle runs in a persistent JSONL subprocess hosted by
`.venv-needle\Scripts\python.exe`. The adapter calls only `Needle.complete()`;
it never passes executable URI functions and never invokes `Needle.run()`.
Returned tool calls remain untrusted proposal observations.

Final run results (eight reflex items):

- Routing / competing-tool selection: **8/8, 100%**.
- Structured-record extraction: **4/4, 100% exact**.
- Argument extraction: **2/4, 50% normalized exact**.
  - Correct: attached-file name after punctuation normalization; calendar
    date.
  - Incorrect: weather included an extra `location=tomorrow`; unread-email
    returned no `unread=true` argument.
- Provider latency: p50 **159.17 ms**, p95 **207.40 ms**.
- Cold bridge/model load: approximately **78–90 ms** across A–D final runs.
- Provider-reported peak RAM: **101.4–101.6 MB**; the Python bridge itself
  observed approximately 4.05 MB RSS after model mapping.
- GPU/VRAM and true streaming TTFT: **unavailable**. Needle's synchronous API
  exposed completion latency, not a separately observable first-token time.
- Score semantics: Needle base model's numeric `confidence` was retained as
  `calibrated_confidence`; no confidence was fabricated.
- Local-only posture: telemetry disabled, Hugging Face offline mode forced,
  already-cached engine/weights used, stdio IPC only.

This corroborates the User's B.3 addendum for tool routing, competing-tool
selection, structured records, and roughly 108–109 MB peak RAM, while adding
a measured qualification caveat: this corpus did **not** reproduce a full
argument-extraction pass.

**Verdict: `RESIDENT` for reflex routing and structured extraction only.**
Its low load/latency and ~102 MB peak materially improve these tasks. URI must
still validate every proposal and must not treat its confidence as authority.

### SmolLM2-135M-Instruct Q3_K_M

- Language-only rubric score: **0.625**, versus configuration A's escalation
  baseline of **0.333**.
- Exact language answers: **0/4**; total matrix correctness therefore did not
  improve over A (**0.667** for both A and B).
- Provider latency: p50 **100.46 ms**, p95 **131.39 ms**.
- Cold load: approximately **391–394 ms**.
- Peak llama-server RSS: approximately **203.8–203.9 MB**.
- Score semantics: `none`; llama.cpp supplied no calibrated per-answer
  probability and the adapter did not invent one.

The worker produced fluent text but missed important rubric requirements,
including the required refusal language and precise acknowledgement/reminder
wording. The 0.292 rubric gain does not justify ~204 MB resident memory for
this four-item result.

**Verdict: `BYPASS / REDUNDANT`.** Use the Main Brain for these language tasks;
do not keep SmolLM2 resident or promote it into routing.

### Qwen2.5-0.5B-Instruct Q4_K_M

- Bounded-reasoning accuracy: **2/4, 50%**, versus configuration B's **0%**
  (B has no reasoner and correctly escalates that tier).
- Provider latency: p50 **191.80 ms**, p95 **241.75 ms**.
- Cold load: approximately **638–738 ms**.
- Peak llama-server RSS: approximately **493.6–494.3 MB**.
- Score semantics: `none`.
- Failures were substantive: it answered the red/blue constraint question
  incorrectly and returned the wrong set intersection.

Both existing Main-Brain controls reached **4/4, 100%** on the same tier after
generic short-answer normalization. Their final warm p50/p95 values were:
`qwen3.5:9b` **129.87/156.18 ms** and `gemma4:12b`
**160.15/211.83 ms**. Main-Brain cold-load/RSS was not reclassified as an
Edge measurement; those values remain unavailable in the final bundle.

**Verdict: `BYPASS / REDUNDANT`.** The 50-point gain over a no-reasoner
configuration is real, but 50% quality at ~494 MB is not sufficient and is
materially worse than both already-installed controls. Bypass Edge for the
Main Brain on bounded reasoning.

## Configuration matrix

| Configuration | Full correctness | Reflex | Language rubric | Bounded reasoning | Matrix p50 / p95 | Verdict |
|---|---:|---:|---:|---:|---:|---|
| A — Needle only | 0.667 | 1.000 | 0.333 | 0.000 | 0.003 / 291.28 ms | `RESIDENT` for Needle-supported tiers |
| B — Needle + SmolLM2 | 0.667 | 1.000 | 0.625 | 0.000 | 0.005 / 304.26 ms | `BYPASS / REDUNDANT` vs A |
| C — Needle + Qwen2.5-0.5B | 0.750 | 1.000 | 0.333 | 0.500 | 0.005 / 309.73 ms | `BYPASS / REDUNDANT` |
| D — all three | 0.750 | 1.000 | 0.625 | 0.500 | 94.64 / 312.77 ms | `BYPASS / REDUNDANT` |
| Main Brain qwen3.5:9b control | reasoning-only 1.000 | n/a | n/a | 1.000 | 129.87 / 156.18 ms warm | Bypass target (`ON_DEMAND` control, not Edge) |
| Main Brain gemma4:12b control | reasoning-only 1.000 | n/a | n/a | 1.000 | 160.15 / 211.83 ms warm | Bypass target (`ON_DEMAND` control, not Edge) |

The matrix-wide p50 values include deterministic/escalation tiers with
near-zero runtime and should not be interpreted as model-call latency. The
per-worker latency figures above are the useful comparisons.

## Perception disposition

### Speech / STT

The existing B.2 `faster-whisper` adapter was exercised and reported
`UNAVAILABLE`: `URI_EDGE_STT_MODEL_PATH` is unset and the library is absent.
The accepted `audio_corpus.json` also contains `synthetic://` references, not
materialized audio files, so real WER/CER cannot be measured without a new
fixture-materialization decision. The Needle package remains unavailable in
the main venv's B.2 probe; the dedicated bridge API independently exposes no
confirmed audio/STT surface.

**Verdict: `UNQUALIFIED / UNAVAILABLE`.** Guidance: publish/freeze a complete
checkpoint SHA-256 manifest and materialized, licensed audio fixtures, then
install `faster-whisper` as an explicitly declared dependency in a future
accepted scope.

### OCR

`pytesseract` and Pillow are installed, but no Tesseract binary is on PATH and
`URI_EDGE_TESSERACT_PATH` is unset. No genuinely portable, redistribution-
clear Windows build was confirmed without relying on an installer or
system-level installation. `vision_corpus.json` likewise contains synthetic
references rather than materialized images.

**Verdict: `UNQUALIFIED / UNAVAILABLE`.** Guidance: adopt a specifically
versioned portable distribution with published integrity metadata and add
materialized synthetic image fixtures before rerunning V1.

### Small VLM

No <=1B VLM could reuse the accepted text-only llama.cpp path without an
additional multimodal projector/model asset and candidate-specific adapter;
the practical alternatives required another heavy framework or new
architecture. `URI_EDGE_VLM_MODEL_PATH` remains unset.

**Verdict: `UNQUALIFIED / UNAVAILABLE`.** No second ML framework was added to
force a result.

## Lifecycle and authority evidence

- A–D exercised `LazyRuntimeStateManager` through
  `NOT_LOADED → LOADING → RESIDENT/ON_DEMAND → UNLOADING → NOT_LOADED`.
- All three new assets were sourced through B.3's lifecycle and verified
  again before inference.
- No `ollama pull` command or pull API request occurred.
- No administrator/elevated operation, driver/CUDA install, PATH/registry/
  service/permission change, system-wide runtime install, or write outside
  URI-controlled model storage occurred.
- `uri_core/core/edge/` retains its recursive zero-network-import boundary.
- All model outputs remained observations/proposals; no model received
  execution, approval, or authorization authority.
- No candidate was promoted; `EDGE_ONLY`/`enabled` defaults are unchanged.

## Verification

1. Focused B.4 plus B.1/B.2 during development: **36 passed**.
2. Required M33.2 A/B/B.1/B.2/B.3/B.4 regression set: **60 passed in 4.01s**.
3. Full suite: **2,249 passed, 16 failed, 40 subtests passed, 3 warnings in
   738.77s**.
4. Isolated re-run of the ten non-live/non-provider failures plus
   `test_m19_office_readiness.py`: **32 passed (all M19 tests), 10 failed**.

The 16 full-suite failures are outside B.4-touched production paths and
reproduce in isolation. Exact classification:

- `step3_test.py::test_drive` and `step4_test.py::test_download`: obsolete
  tests call missing `DriveService.list_recent_files`; B.4 did not modify
  Drive code.
- `test_m20_feasibility_validation.py::UnavailableCapabilityIsNotPromotedTests::test_strict_single_action_proposal_for_unavailable_capability_falls_back`:
  current workspace capability state dispatched `web_search`; B.4 did not
  modify registry/planner/orchestrator paths.
- Two `test_m20_recovery_loop.py` failures, two
  `test_m20_semantic_interpreter_resilience.py` failures,
  `test_orchestrator_session_workflow.py::...test_session_facts_are_used_for_clarification`,
  and `test_workflow_restart_recovery.py::...test_workflow_survives_restart_and_resumes`:
  current orchestrator/provider state returns `failed`/`unavailable` instead
  of those older tests' expected fallback status; `orchestrator.py` is byte-
  unchanged from `737ddcf`.
- `test_usage_import_boundary.py::test_orchestrator_newline_count_does_not_increase`:
  baseline `orchestrator.py` has 6,121 newlines versus the stale 5,460 limit;
  B.4 did not touch it.
- `test_m21_context_window_live.py::...test_real_reasoning_prompt_is_not_silently_truncated`,
  two `test_ollama_provider_live.py` failures, and three
  `test_ollama_reasoning_adapter_live.py` failures: those tests require the
  absent `qwen3:14b` tag or expect legacy fallback success. B.4 was expressly
  prohibited from pulling it; only `qwen3.5:9b` and `gemma4:12b` are installed.

The previously documented machine-specific OAuth discrepancy in
`test_m19_office_readiness.py` did **not** reproduce: all 32 M19 tests passed
in the isolated run. This report preserves the historical note without
claiming a current failure.

## Files changed / created

- `.gitignore`
- `uri_core/core/edge/adapters/ensemble.py`
- `scripts/m33_2_needle_bridge.py`
- `scripts/m33_2_batch_b4_live_qualification_runner.py`
- `fixtures/m33_2_edge_benchmark/corpus.json`
- `fixtures/m33_2_edge_benchmark/manifest.json`
- `test_m33_2_batch_b1_ensemble_benchmark.py`
- `test_m33_2_batch_b4_real_model_qualification.py`
- `docs/plans/M33_2_BATCH_B4_COMPLETION_REPORT.md`
- `docs/plans/M33_2_BATCH_B4_STATE.md`
- `docs/governance/URI_ACTIVE_MILESTONE.md`

Pre-existing Antigravity changes in `URI_ACTIVE_MILESTONE.md`,
`URI_AGENT_RELAY.md`, and `M33_2_BATCH_B4_STATE.md` were preserved. No commit
or push was performed.

## Handoff

Implementation stops at `VERIFICATION_READY`. Antigravity should package the
diff, this report, and `temp_evidence/m33_2_batch_b4/` for Claude's independent
audit. Only Claude may declare the milestone verified or release it.
