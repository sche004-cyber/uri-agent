# M33.2 Batch B.2 — Edge Perception Qualification

**Status:** DRAFT → ACCEPTED (standing auto-approval, `ORCHESTRATION.md` §1.5 —
routine benchmark-only extension; does not touch core project structure,
product identity, or the security/authority model)
**Authorized by:** direct User instruction, 2026-09-20 (Batch B.1 ACCEPT +
Batch B.2 planning instruction)
**Depends on:** Batch B.1 `a792a8c` (CLOSED/ACCEPTED,
`docs/plans/M33_2_BATCH_B1_STATE.md`)

## Purpose

Determine experimentally how URI should provide lightweight local Vision
and Audio/Transcription while preserving the provider-agnostic Second
Brain architecture, extending the same benchmark-only harness pattern
Batch A/B/B.1 already established. Evidence-driven, not vendor-claim-
driven, per `research_notes/Edge runtime evaluation/patterns.md`.

## Why this is additive, not a new milestone

Batch A already froze the target contracts this batch benchmarks against:
`uri_core/core/edge/contracts.py` already defines real, committed
`EdgeVisionProvider.observe(VisionRequest) -> VisionObservationProposal`
and `EdgeSpeechProvider.transcribe(AudioRequest) -> TranscriptProposal`
Protocol stubs (currently minimal — `VisionRequest`/`AudioRequest` carry
only `source_id`; the Proposal types inherit `EdgeProposal`'s generic
`provider_id`/`runtime_id`/`model_id`/`raw_confidence`/
`raw_confidence_semantics`/`latency_ms`/`errors` fields with no
modality-specific fields yet). `uri_core/core/edge/settings.py` already
has real, committed `vision`/`speech` preference slots
(`{"provider_id": None, "model_id": None, "enabled": False}`), each
independently gated behind the top-level `enabled` switch.
`EdgeRuntimeInventory`/`RuntimeProfile` (`runtime_inventory.py`) are
already modality-agnostic and need no change to carry a vision/audio
runtime profile. The canonical architecture doc's §10 ("Modal siblings")
already specifies the intended tiering — vision: deterministic
OCR/barcode/metadata → lightweight classifier/detector → small local VLM
→ Main-Brain multimodal; voice: ASR → a distinct interpretation/tool
proposal, with transcript and action confidence logged and controlled
separately — this plan follows that existing direction rather than
re-deciding it.

URI has **zero existing vision or audio capability today** (confirmed by
direct search: `uri_core/services/pdf_reader.py`'s OCR is a scanned-PDF
text-extraction fallback only, not a general vision capability; no
VLM/opencv code exists anywhere; `yt_dlp_runner.py` explicitly documents
"no transcript action"; no whisper/speechrecognition/pyaudio/soundfile
code exists anywhere in the repo). So this batch is genuinely additive
against contract stubs only — it cannot conflict with or duplicate
anything live.

## Documentation-conflict finding: Needle 3 audio capability

Independent verification during this planning session found genuinely
conflicting evidence on whether Needle 3 documents audio/transcription
capability, not a clean confirmation or refutation:

- **Direct inspection** of the live `cactus-compute/needle` GitHub
  repository — full recursive tree of both the `main` branch and the
  latest release tag `v3.0.2` (no `doc/` directory exists in either), the
  raw byte content of `llms.txt` (fetched via the GitHub Contents API and
  grepped directly, not summarized — zero matches for
  `audio|wav|pcm|transcri|sample_rate|channels`; the only documented
  signatures are `agent.run(query, max_steps=8, max_new_tokens=512)` and
  `agent.complete(text, max_new_tokens=512)`, both text-only), `README.md`,
  and the `cactuscompute.com/needle` product page (which states plainly:
  "Text prompts, plus tool definitions or an extraction schema" as the
  full input surface) — all show no audio/transcription capability. This
  matches `research_notes/Edge runtime evaluation/needle.md`'s own
  existing finding (zero mentions of audio/transcription/ASR/Whisper).
- **Indexed/search-surfaced upstream evidence** separately identified
  cites a `doc/apis.md` path with `complete()`/`embed()`/`run()` accepting
  `audio=`, `audio_format="wav"`, `sample_rate`, `channels` parameters,
  and documents transcription returning `transcript` +
  `transcript_confidence` — but this exact file does not exist at the
  cited path in either the `main` branch or the latest tag of the
  directly-inspected repository.

This is recorded as a neutral planning state rather than resolved by
assertion in either direction:

**`NEEDLE_AUDIO_DOCUMENTATION_CONFLICT / RUNTIME_UNVERIFIED`**

This batch's empirical probe (below) is the actual tie-breaker, not
further documentation research. Needle remains the first low-cost speech
probe candidate; the probe's classification and automatic fallback to a
provider-agnostic alternative STT candidate make the documentation
disagreement immaterial to this batch's own progress. Note also: Needle
is itself a Cactus Compute product (not an unrelated vendor to Cactus) —
the distinct product Cactus documents Whisper/Moonshine/Parakeet
transcription support, but has no documented Windows support and a
source-available, not fully open, license, per `cactus.md`.

## Vision qualification design

Reuse the B.1 harness skeleton (`BenchmarkCandidate`/`BenchmarkResult`/
`run_benchmark`/`write_artifacts` control flow, resource instrumentation,
safety/qualification gating) — confirmed generic and reusable as-is for
that control flow. Add modality-specific, additive pieces rather than
redesigning the harness:

- A new `fixtures/m33_2_edge_perception/vision_corpus.json` — synthetic,
  URI-owned, frozen, SHA-256-manifested (same discipline as B.1), covering
  representative tasks: screenshot/application-error-state understanding,
  office-document scan/photo field extraction (name/date/reference
  number), UI-state/button recognition, simple VQA, low-quality/ambiguous
  image handling, and confidence-aware escalation. Each item carries an
  `image_path` (or a small embedded/synthetic bitmap generated at
  fixture-build time — no real user photos, no external copied images)
  plus an `expected` structured-field or answer value and, where
  relevant, a `rubric` analogous to B.1's language rubric.
- New scoring functions parallel to `_language_rubric`: field-level
  precision/recall/F1 for structured extraction tasks, exact/normalized
  match for VQA-style tasks — per `patterns.md`'s own established
  methodology (separate visual perception/OCR/layout extraction from
  reasoning; score each against labeled answers; include a
  position-sensitivity-style check per task type rather than one
  free-form score).
- Three candidate pathways benchmarked independently, not pre-selected:
  - **V1 OCR-first** — reuse the existing `pytesseract`/`Pillow`/`pymupdf`
    dependencies already declared in `requirements.txt`; genuinely zero
    new dependency for this pathway.
  - **V2 small local VLM** — a new third-party dependency the
    implementation task must flag explicitly; no VLM runtime exists in
    this repo today; candidate selection deferred to the implementer with
    the same "prepare the harness to measure it, do not assume/prefer it"
    discipline B.1 used for the tiny reasoners.
  - **V3 hybrid** — OCR + VLM fusion/confidence combination.
  The explicit comparison question is whether OCR alone is sufficient for
  common cases so a VLM can remain optional/lazy-loaded — mirroring B.1's
  own "does the full ensemble earn its footprint" framing.
- Resource governor states already defined in the architecture doc
  (`UNAVAILABLE`, `NOT_LOADED`, `LOADING`, `RESIDENT`, `ON_DEMAND`,
  `SUSPENDED`, `UNLOADING`, `FAILED`) are the vocabulary the harness
  reports runtime status in, so this benchmark evidence is directly
  reusable if/when a real `EdgeResourceGovernor` is implemented later —
  without this batch itself implementing that governor.

## Audio / transcription qualification design

- Keep the harness provider-agnostic — do not hard-code Needle.
- Needle remains the first, low-cost empirical speech probe, run before
  any alternative candidate. The probe must classify its result into
  exactly one of four states:
  - **`AVAILABLE_SUPPORTED`** — the installed Needle runtime exposes and
    successfully executes audio/transcription.
  - **`API_PRESENT_RUNTIME_UNAVAILABLE`** — an audio-capable API surface
    exists on the installed package, but required runtime/weights are
    unavailable.
  - **`NOT_SUPPORTED`** — the installed/current Needle API genuinely
    exposes no speech/audio capability (introspectable at the Python
    object/signature level, not merely "undocumented").
  - **`FAILED_QUALIFICATION`** — speech execution works, but fails URI's
    accuracy, latency, resource, confidence, or offline requirements.
  - If the probe result is anything other than `AVAILABLE_SUPPORTED`, the
    harness **automatically continues** to the alternative STT candidate
    below — the documentation conflict above must never block or manually
    gate this batch's progress.
- **Reproducibility requirement (mandatory):** the probe must record, in
  its evidence artifact, the exact installed Needle package version
  (`importlib.metadata.version("cactus-needle")` or equivalent), the git
  commit/tag it was built from if determinable, and the actual inspected
  API signature (e.g. via `inspect.signature()` on the installed
  `complete`/`embed`/`run` callables) — so the classification is
  independently reproducible from the evidence alone, without re-trusting
  either side of the documentation conflict above.
- One alternative local STT candidate is benchmarked in the same harness
  shape, selection criteria (not a pre-picked model): local-only/offline-
  capable, license-permissive, Windows-desktop-compatible (ruling out
  Cactus unless a future session finds a Windows-compatible build), no
  server/cloud dependency, quantizable/small enough to fit the same
  footprint-first discipline B.1 applied to the tiny reasoners. This is a
  harness-readiness criterion, not a candidate name — the implementer
  selects and documents the specific candidate at implementation time, the
  same way Batch B.1 deferred DeepSeek vs. Qwen selection to measurement.
- New `fixtures/m33_2_edge_perception/audio_corpus.json` — synthetic or
  URI-generated (e.g. TTS-generated or the implementer's own recorded
  short) command/dictation samples, URI-owned, SHA-256-manifested.
  Scoring: WER/CER per `patterns.md`'s own established ASR methodology
  (lock transcript normalization rules before scoring; measure WER/CER
  plus latency/RTF/footprint; do not invent a different ad hoc accuracy
  metric).
- Whichever STT candidate (Needle or the alternative) is measured, the
  harness reports: audio input accepted (bool), transcription returned,
  transcription confidence/evidence where supported (else `unavailable`,
  never fabricated — same discipline as B.1's TTFT/GPU handling), WER/CER
  on the representative corpus, latency, RAM/CPU/GPU footprint,
  offline/local-only behavior (reuse B.1's `outbound_deny=True` mandatory
  mechanism unchanged), and a qualitative suitability note for
  voice-to-intent/tool-routing (not a numeric claim — routing quality is a
  separate, already-existing "reflex" tier concern, not reinvented here).

## New third-party dependencies this plan must flag (none hidden)

- Vision: a VLM runtime/inference library (exact package deferred to
  implementation-time measurement) — genuinely new, must be called out in
  the implementation task, not added silently. OCR (V1) needs zero new
  dependency (`pytesseract`/`Pillow`/`pymupdf` already declared).
- Audio: an STT runtime/library for the chosen alternative candidate
  (exact package deferred similarly) — genuinely new. The Needle probe
  itself adds no new dependency (reuses whatever Needle integration B.1
  already prepared, if any local install exists); its classification is an
  empirical outcome, not assumed in either direction.
- Any new dependency must be pinned, declared in `requirements.txt` with
  an explanatory comment (matching this repository's existing convention,
  see `requirements.txt`'s own comments for `pymupdf`/`pytesseract`/
  `yt-dlp`), and local-only (no network calls at inference time) to
  satisfy the zero-egress boundary the existing recursive import-boundary
  test already enforces for the whole `uri_core/core/edge/` tree.

## Local-only / zero-egress compliance

Unchanged mechanism from B.1: `outbound_deny=True` mandatory,
`candidate.local_only` mandatory, no network primitives in harness code.
This batch adds nothing here except re-running the same static check
across any new adapter files — already automatically covered by
`test_m33_2_batch_a_edge_foundation.py`'s recursive `rglob("*.py")` scan
and the B.1 AST-walk test, neither of which needs updating for new files
under `uri_core/core/edge/`.

## Files expected to change

- `uri_core/core/edge/adapters/` — new `vision.py` and `speech.py` (or
  similarly named) adapter modules, following `ensemble.py`'s exact
  pattern: dict-in/dict-out, only stdlib + sibling-module imports, no
  approval/dispatch/orchestrator/registry import.
- `uri_core/core/edge/adapters/benchmark.py` — additive scoring-function
  exports if genuinely shared (e.g. a generic field-F1 helper), but the
  core `run_benchmark`/`BenchmarkResult` shape should not need
  restructuring since it is already generic dict-in/dict-out; any
  genuinely new `BenchmarkResult` field (e.g. `wer`/`cer`/`field_f1`) is
  additive with a default, not a breaking change to B.1's existing fields.
- `fixtures/m33_2_edge_perception/` (new directory) —
  `vision_corpus.json`, `audio_corpus.json`, and their manifests, same
  provenance/hash discipline as `fixtures/m33_2_edge_benchmark/`.
- `scripts/m33_2_edge_perception_benchmark.py` (new) — runs the vision and
  audio candidate matrices and writes evidence to
  `temp_evidence/m33_2_batch_b2/`, following
  `scripts/m33_2_edge_benchmark.py`'s exact pattern.
- New focused test file, e.g.
  `test_m33_2_batch_b2_perception_benchmark.py`.
- New completion report + STATE file at closure
  (`docs/plans/M33_2_BATCH_B2_*`), same pattern as A/B/B.1.

**Not expected to change:** `orchestrator.py`, `server.py`, dispatcher,
approval, credential, capability registry, any UI file,
`uri_core/core/edge/contracts.py`'s existing Protocol *signatures* (new
fields may be proposed but this plan does not require implementing them —
see non-goals), `routing_policy.py`, `settings.py`'s existing schema
(already has `vision`/`speech` slots; this batch does not need to touch
this file), `trace.py`.

## Explicit non-goals / architecture boundaries

- No production promotion of any vision/audio candidate.
- No Batch C work.
- No premature production wiring — `EdgeVisionProvider`/
  `EdgeSpeechProvider` remain unimplemented Protocol stubs; this batch
  produces benchmark evidence about candidates, not a production
  implementation of those Protocols.
- No requirement that every model (OCR/VLM/STT) be resident
  simultaneously — perception specialists stay optional/lazy-loaded.
- No architecture hard-coding to Needle, Cactus, or any specific
  vision/STT model — candidate selection stays harness-driven and
  measurement-based, same discipline as B.1's DeepSeek/Qwen deferral.
- No change to who holds execution/approval/credential authority — every
  perception output remains a structured evidence/proposal, never granted
  execution authority, matching the frozen architecture's non-negotiable
  authority model (§1 of the canonical architecture doc).
- No forcing of weaker language/reasoning workers into a Main-Brain-
  capable path, and no invocation of a perception specialist for a task
  that does not actually require that modality; the harness measures
  per-modality candidates independently and does not itself build a
  cross-modality routing policy (that remains `routing_policy.py`'s job,
  unchanged by this batch).
- Do not manually resolve the Needle documentation conflict by further
  research — the empirical probe is the tie-breaker, and progress must
  never block on it.

## Stop condition

Implementation stops at `VERIFICATION_READY` with a completion report
listing: vision candidate results (V1/V2/V3) with resource/accuracy
evidence; the Needle speech probe's classification
(`AVAILABLE_SUPPORTED`/`API_PRESENT_RUNTIME_UNAVAILABLE`/`NOT_SUPPORTED`/
`FAILED_QUALIFICATION`) with recorded package version/commit/signature;
the alternative STT candidate's results if the Needle probe was not
`AVAILABLE_SUPPORTED`; and a non-implemented recommendation for later
production architecture, explicitly distinguishing harness validation
from real candidate qualification (the same distinction Batch B.1's own
report correctly drew). No commit/push until Claude's independent audit
runs and returns a verdict, per standing release authority.
