# M33.2 Batch B.4 — Real Edge-Model Qualification

**Status:** DRAFT → ACCEPTED (standing auto-approval, `ORCHESTRATION.md`
§1.5 — qualification-only, reuses already-frozen extension points, does not
touch core project structure, product identity, or the security/authority
model)
**Authorized by:** direct User instruction, 2026-09-20, immediately after
Claude's independent audit closed Batch B.3 (`d395c1c`/`d6b97d7`).
**Depends on:** Batch B `906c527`, Batch B.1 `a792a8c`, Batch B.2 `b98620a`,
Batch B.3 `d395c1c` (all CLOSED/ACCEPTED) — this batch reuses their
infrastructure directly rather than building anything new.

## Purpose

Batches B/B.1/B.2/B.3 built a complete, real, tested harness — benchmark
scoring, resource instrumentation, vision/audio perception scoring, and
user-space model lifecycle/sourcing — but never ran it against real model
weights for more than isolated, individually-`UNAVAILABLE` probes. B.4 does
not build new infrastructure. It sources the small number of genuinely
missing real artifacts, wires them into extension points the existing code
already defines, runs the existing harnesses for real, and produces one
qualification verdict per candidate and per practical combination. This is
the evidence `docs/architecture/M33_2_EDGE_SECOND_BRAIN_CANONICAL_ARCHITECTURE.md`
§2.2 ("Parallel Edge Assistance") already requires before any Edge route may
ever be considered eligible: *"Only when a prior benchmark comparison
(migration plan Batch B) has shown a measured latency, cost, or quality
benefit for that specific task/modality/candidate combination."* B.4
produces that evidence; it does not act on it, does not enable it, and does
not change `EDGE_ONLY`/`enabled` defaults (§13, still explicitly
unresolved).

Confirmed by direct inspection before drafting this plan (primary evidence,
not assumption):

- `uri_core/core/edge/adapters/ensemble.py`'s `build_candidate_configurations()`
  already implements exactly the four combinations the User requested —
  configuration A (Needle only), B (Needle + SmolLM2), C (Needle + tiny
  reasoner), D (Needle + SmolLM2 + tiny reasoner) — as real extension points
  taking injected `needle`/`language`/`reasoner` callables. Every
  configuration currently reports `unavailable` only because no real
  callable has ever been injected; the dispatch, scoring, and resource
  instrumentation are already real and already tested (B.1's 15/15).
- `uri_core/core/edge/adapters/vision.py` and `speech.py` already gate real
  candidates on `URI_EDGE_VLM_MODEL_PATH`/`URI_EDGE_STT_MODEL_PATH` and a
  Tesseract-binary probe; B.2's 16/16 already exercises the fixture and
  truthfully-unavailable-actual paths.
- `uri_core/core/edge_lifecycle/` (B.3) already provides confined storage,
  checksum-verified import/download, hardware probing, and lazy state
  management — the correct, already-accepted mechanism for sourcing any
  real weights this batch needs. B.4 must not build a second sourcing path.
- Direct environment inspection at plan time: `cactus-needle==3.0.2` is
  installed and importable as `needle` in a dedicated `.venv-needle`
  virtual environment (not the project's main `.venv`) — this, not a
  contradiction, is why B.1/B.2/B.3's own test runs (which use the main
  environment) always saw Needle as `PACKAGE_NOT_INSTALLED`. The User's own
  manual real-environment Needle testing (recorded in B.3's completion
  report addendum) used this environment. `pytesseract`+`Pillow` are
  installed in the main environment, but no `tesseract` binary is on PATH.
  `faster-whisper`, `torch`, `transformers`, and any GGUF/local-inference
  runtime are installed nowhere. `requirements.txt` declares none of them.
  `fixtures/m33_2_edge_benchmark/corpus.json` is a frozen, SHA-256-manifested,
  20-item corpus already shaped for tool-routing/argument-extraction (each
  item carries `operation`, `arguments`, `expected`, `offered_capabilities`)
  across five tiers (`deterministic`, `reflex`, `language-only`,
  `bounded-reasoning`, `escalate`) — this is the "accepted qualification
  corpus" for Needle routing/competing-tool-selection/argument-extraction,
  reused as-is.

## Scope: what B.4 implements

### 1. Needle 3 — real qualification
Use the already-installed `cactus-needle` 3.0.2 (`.venv-needle`, or the
implementer's equivalent reproducible environment — document exactly which).
Build the real `needle` callable `ensemble.py`'s `build_candidate_configurations()`
already expects. Measure against the existing corpus: routing accuracy,
competing-tool selection (`offered_capabilities` items already model this),
argument extraction, and structured-record extraction (extend the corpus
additively with a small, frozen, SHA-256-manifested set of structured-output
items if the existing 20 items do not already cover this shape — same
discipline as B.1's own tier expansion; document the addition, do not
silently grow it). Record real resource/latency evidence via the existing
benchmark instrumentation (`rss_*`, `load_time_ms`, `ttft_ms`/`ttft_p95_ms`,
GPU/VRAM `unavailable`-or-real). Use the User's own manual real-environment
Needle evidence (B.3 completion report addendum) as corroborating,
already-real evidence for this candidate — dated to when the User actually
ran it, never backdated into B.3's automated report.

### 2. Lightweight language worker — SmolLM2-135M-Instruct
Source real weights through B.3's `edge_lifecycle` only —
`download_model_artifact()` with a declared checksum, or `import_model_file()`
for a local file — into URI-controlled storage
(`uri_workspace/edge_models/`). **Do not** source this by instructing the
already-adopted Ollama runtime to pull a new model: B.3's own frozen scope
explicitly limited Ollama interaction to *detecting/adopting* runtimes and
*discovering already-downloaded* models "without downloading anything" —
asking Ollama to fetch something new would write outside URI-controlled
storage and invoke a third-party executable, both outside what B.3
authorized and outside what this plan authorizes. The one narrow exception:
if a matching small model happens to already be present in the adopted
Ollama runtime's existing model list (discovered, not requested), it may be
used as-is via Ollama's own local API — genuine adoption of something
already there, not a new pull. Downloaded weights need a local inference
runtime to actually execute them — **new dependency, explicitly flagged**:
a CPU-capable, pip-installable, no-elevation GGUF runtime (e.g.
`llama-cpp-python`), added to `requirements.txt` only if genuinely used,
and shared with item 3 rather than added twice. Wire the real weights into
a `language` callable and inject it into configurations B and D. Measure
against the same corpus's `language-only` tier.

### 3. Bounded local reasoner — DeepSeek-R1-Distill-Qwen-1.5B or Qwen2.5-1.5B-Instruct
B.1 deferred the choice between these two to implementation-time
measurement and never actually measured either with real weights (both
remained `UNAVAILABLE` — no env var was ever set). B.4 is the first batch to
source real weights for at least one of them (both if the implementer
judges it cheap to do — total weights are ~1.5B-class, not "more large
models"). Source through `edge_lifecycle`'s checksum-verified
download/import only, same boundary as item 2 (adoption of an
already-present matching Ollama model is fine; requesting a new Ollama pull
is not). Reuses item 2's GGUF runtime dependency if one was added; do not
add a second one. Wire into configurations C and D. Measure against the
`bounded-reasoning` tier and explicitly compute whether the reasoner's
quality gain over configuration B (no reasoner) justifies its measured
RAM/load-time/latency cost — this comparison is this item's actual
deliverable, not just a pass/fail qualification.

### 4. Speech/STT — local Whisper-family path
The installed Needle API currently exposes no confirmed audio/STT surface
(B.2's `PACKAGE_NOT_INSTALLED` finding, and the User's own real-environment
Needle testing independently confirms no obvious audio/STT surface either —
consistent, corroborating findings, not a new conflict). Use the
already-named `faster-whisper` path (`uri_core/core/edge/adapters/speech.py`,
B.3's `edge_pack.py` `speech_to_text` component). **New dependency,
explicitly flagged, not added silently:** `faster-whisper` (pure-Python +
CTranslate2 backend, pip-installable, no elevation, no OS modification) must
be added to `requirements.txt` if used. Source the smallest practical
checkpoint (e.g. `tiny.en` or `base`) through `edge_lifecycle`'s
checksum-verified download into URI-controlled storage, point
`URI_EDGE_STT_MODEL_PATH` at it, and measure against B.2's `audio_corpus.json`
(WER/CER, confidence, resource/latency) using the harness B.2 already built.

### 5. OCR — local Tesseract path
`pytesseract`/`Pillow` are already installed; only the `tesseract` binary is
missing. Per B.1/B.2/B.3's own "portable, licensed, no elevation" discipline
for any runtime install: the implementer must determine, and document,
whether a genuinely portable (no installer, no elevation, redistributable
under its license — Tesseract is Apache-2.0) Windows Tesseract distribution
exists and install it only into URI-controlled storage via B.3's
portable-runtime-installation path (plan item 5 of B.3's own scope). If no
such portable distribution can be confirmed, OCR remains truthfully
`UNAVAILABLE` with guidance — never a forced system-level install, never a
fabricated result. Measure against B.2's `vision_corpus.json` OCR-shaped
items using the already-built V1 OCR path.

### 6. Small VLM — best effort, may legitimately stay unavailable
B.2 already deferred the exact VLM package/model to implementation time and
found it `UNAVAILABLE` (`URI_EDGE_VLM_MODEL_PATH` unset, no candidate
sourced). The only realistic small local VLM options require a real
inference framework (e.g. `transformers`+`torch`, or a GGUF vision runtime)
— a materially heavier dependency addition than any other item in this
batch. The implementer evaluates whether a genuinely small (≤ ~1B
parameter), license-clear, easily-runnable candidate exists without adding
a second major ML framework alongside whatever item 2/3 already added; if
one exists cheaply (e.g. it reuses the same runtime already added for
items 2/3), qualify it against B.2's `vision_corpus.json` V2 path. If not,
this item **truthfully reports `UNAVAILABLE` with the reason recorded** —
this is an acceptable, honest outcome for this item, not a batch failure.
Do not add a second inference framework solely to force a VLM result.

### 7. Comparison matrix and resident/on-demand/bypass decision
Using the already-real per-candidate evidence from items 1-6, produce one
consolidated comparison covering the User's requested practical
combinations: Needle only (A); Needle + language (B); Needle + reasoner
(C); Needle + language + reasoner (D); Edge + speech; Edge + vision; and a
Main-Brain-bypass control using the already-installed, already-production
`qwen3.5:9b`/`gemma4:12b` through the existing `OllamaProvider`
(Main-Brain path — not a new Edge candidate, not a new provider, reused
exactly as it already exists) as the "stronger local model" comparison
point for reasoning-tier tasks. For each candidate and combination, record
resident-vs-`ON_DEMAND` recommendation (using B.3's exact frozen §10
vocabulary — no new states) and an explicit bypass recommendation ("URI
should call the Main Brain directly for this task/modality" where the
Edge candidate's measured quality/latency/RAM tradeoff does not justify
using it). The deliverable answers, with real numbers: which specialists
materially improve URI, which are redundant, which should stay resident,
which should be `ON_DEMAND`, and when to bypass Edge for a stronger Main
Brain — not merely "does every model load."

### 8. Per-candidate evidence record (uniform reporting shape, not a uniform interface)
For every real candidate qualified (or truthfully found unqualifiable),
record: exact model/runtime/version; source and license (B.3's
`ModelArtifactRecord` fields, reused as-is); installation/runtime state
(B.3's `RuntimeLifecycleState` vocabulary); actual supported capabilities
and constraints/context limits as that provider actually reports them —
**never normalized into one fake shared confidence scale or one
lowest-common-denominator interface**; each candidate's own
`score_semantics` (already a first-class B.1 concept:
`calibrated_confidence` / `probability` / `raw_logit_derived` / `none`) is
preserved and reported per-candidate, exactly as B.1 already requires;
cold-load time, TTFT/TTFT-p95 where measurable, RSS before/after load,
GPU/VRAM where observable (`unavailable` if not, never fabricated — same
discipline as B.3's `hardware.py`); unload/reload behavior exercised
through B.3's `LazyRuntimeStateManager`; zero-egress/local-only behavior
confirmed per candidate; and task accuracy against the relevant frozen
corpus (`corpus.json` / `vision_corpus.json` / `audio_corpus.json`,
extended additively only where item 1 requires it).

## Known limitations carried forward (disclosed, not silently inherited)

`corpus.json` has 4 items per tier (20 total) and `vision_corpus.json`/
`audio_corpus.json` are similarly small, synthetic, URI-owned sets (B.1/B.2's
own disclosed carry-forward residuals). B.4 measures real candidates against
these corpora as-is — real weights against a small corpus is still real,
honest evidence, but the resulting accuracy numbers carry the same
small-sample caveat B.1/B.2 already disclosed for the harness itself; this
plan does not resolve that residual, only inherits it truthfully rather than
presenting per-candidate accuracy as more statistically meaningful than a
~4-20 item corpus supports.

## Explicit non-goals / boundaries

- No new architecture layer, no new benchmark/scoring/instrumentation
  machinery, no new sourcing/storage mechanism — every item above wires
  real components into extension points `ensemble.py`, `vision.py`,
  `speech.py`, and `edge_lifecycle/` already define. If an item genuinely
  cannot be qualified without inventing new architecture, it stops and
  escalates rather than inventing one.
- No production promotion, no wiring into `orchestrator.py`, `server.py`,
  the dispatcher, capability registry, or any execution-authority surface.
  Every candidate/combination remains proposal/observation-tier evidence,
  exactly as B.1/B.2/B.3's candidates were.
- No change to `EDGE_ONLY`/`enabled` defaults (§13's own still-unresolved
  decision) and no activation of §2.2 Parallel Edge Assistance — this batch
  produces the evidence that mechanism requires; it does not flip it on.
- No Batch C work, no M31 UI implementation of any kind.
- No privileged/OS-level/system-wide installation, matching B.3's
  still-excluded list unconditionally; any runtime install stays inside
  URI-controlled storage via B.3's existing portable-runtime path.
- No large/unnecessary model downloads. `qwen3.5:9b`/`gemma4:12b` are used
  only as an existing, already-installed Main-Brain-path comparison
  control — never downloaded, never treated as Edge candidates.
- No forced result: any item that cannot be genuinely, honestly qualified
  (most likely VLM, possibly OCR if no portable Tesseract distribution is
  confirmed) must report `UNAVAILABLE` with a truthful, documented reason
  rather than a fabricated or lowest-common-denominator substitute.
- Each new Python dependency (at minimum, likely `faster-whisper` for item 4
  and one shared GGUF inference runtime for items 2/3; possibly a vision
  framework for item 6 only if it turns out to be genuinely cheap — see
  item 6) must be explicitly flagged in the completion report, not added
  silently, per B.1/B.2/B.3's own convention. No dependency is added twice
  where one already covers the need.
- Sub-batching is explicitly rejected: one consolidated implementation run
  covering items 1-8, followed by one independent Claude audit — not a
  model-by-model series of separate handoffs.

## Files expected to change

- `uri_core/core/edge/adapters/ensemble.py` — real `needle`/`language`/
  `reasoner` callables wired in (likely a small new "real component
  factory" module or function alongside the existing fixture builders;
  the existing `build_candidate_configurations()` signature is reused
  unchanged).
- `uri_core/core/edge/adapters/vision.py`, `speech.py` — real VLM/OCR/STT
  callables wired into the existing, already-gated extension points; no
  interface change expected.
- `uri_core/core/edge_lifecycle/` — used, not modified, unless a genuinely
  additive field is needed on an existing record (same "additive only"
  discipline as B.3 itself observed for `contracts.py`, which B.3 ended up
  not needing to touch at all).
- `fixtures/m33_2_edge_benchmark/corpus.json` (+`manifest.json`) — additive
  structured-extraction items only if genuinely needed for item 1,
  frozen and SHA-256-manifested exactly like every prior addition.
- `requirements.txt` — additive only, each addition explicitly flagged in
  the completion report (see Non-goals).
- A new live runner script, mirroring B.1/B.2's pattern (e.g.
  `scripts/m33_2_batch_b4_live_qualification_runner.py` or similar), that
  sources real components, injects them into the existing adapters, runs
  the existing harnesses, and writes evidence bundles — same provenance
  discipline as B.1/B.2.
- New fixture/evidence directory, e.g. `temp_evidence/m33_2_batch_b4/`.
- New focused test file(s), e.g.
  `test_m33_2_batch_b4_real_model_qualification.py`.
- New completion report + STATE file at closure
  (`docs/plans/M33_2_BATCH_B4_*`), same pattern as A/B/B.1/B.2/B.3.

**Not expected to change:** `orchestrator.py`, `server.py`, dispatcher,
approval, credential, capability registry, any UI file, `routing_policy.py`,
`trace.py`, `provider_registry.py`, `GET /providers`,
`EdgeRuntimeInventory`'s immutability contract, `EDGE_ONLY`/`enabled`
defaults, §2.2 Parallel Edge Assistance activation.

## Stop condition

Implementation stops at `VERIFICATION_READY` with a completion report
covering every item above: per-candidate evidence records (item 8); the
comparison matrix and resident/`ON_DEMAND`/bypass recommendations (item 7);
every truthfully-`UNAVAILABLE` item with its documented reason; every new
dependency explicitly flagged; and confirmation that no still-excluded
(privileged/OS-level) operation, no production wiring, and no `EDGE_ONLY`/
`enabled` default change occurred anywhere. No commit/push until Claude's
independent audit runs and returns a verdict, per standing release
authority. No Batch C work, no M31 UI work, no implementation of this plan
performed by Claude directly — Antigravity routes implementation to Codex
per standing AO-4 routing (complex, multi-file, real-model-integration work
fits "complex/precision-critical" routing over Gemma's bounded-task
profile, same rationale as B.1/B.2/B.3).
