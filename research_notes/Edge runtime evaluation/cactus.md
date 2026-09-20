# Cactus local inference runtime evaluation (planning-only)

**Research snapshot:** 2026-09-20. This is an evidence note for an optional URI M33.2 runtime candidate; it is not an installation recommendation or an approval to integrate. Sources below are Cactus Compute's published documentation, source repository, and release notes only. “Not documented” means no supporting primary-source statement was found in the reviewed material, not proof of impossibility.

## What can Cactus verifiably host today, and what is not supported or documented?

### Takeaway

Cactus documents local text completion/tool-call proposals, VLM image input, speech transcription/streaming, text/image/audio embeddings, local vector indexing/RAG, and model-specific audio understanding. It is a model runtime, not an authority system: its own API returns parsed function calls and can make cloud-handoff decisions, so URI must treat every result as untrusted model output and retain validation, authorization, approval, execution, persistence, audit, and user-data isolation outside the adapter.

### Cited Findings

- The published supported-model table identifies text completion models; tool-call-capable models; VLMs with vision plus text/image embedding; Whisper, Moonshine, and Parakeet transcription/speech-embedding models; a VAD model; and dedicated text-embedding models. The table does **not** list text-to-speech/speech synthesis. [Cactus v1.9 supported models](https://docs.cactuscompute.com/v1.9/#supported-models)
- Cactus's Python API documents `cactus_complete`, `cactus_transcribe`, streaming transcription, `cactus_embed`, `cactus_image_embed`, `cactus_audio_embed`, local RAG, and a vector-index API. [Python API](https://docs.cactuscompute.com/latest/python/)
- The same API documents image messages for named VLM families and audio messages for Gemma4; simultaneous image-plus-audio is illustrated. This verifies model-dependent multimodal input, not universal multimodal support for every model. [Python API: vision and audio](https://docs.cactuscompute.com/latest/python/#vision-vlm)
- `cactus_complete` accepts optional tool definitions and returns parsed `function_calls`; the Android API similarly exposes completion with tools. The docs show a proposal interface only—no runtime-owned tool-execution or URI policy/authorization layer is documented. [Engine API](https://github.com/cactus-compute/cactus/blob/main/docs/cactus_engine.md); [Android API](https://docs.cactuscompute.com/v1.9/android/)
- The repository advertises a C API plus Swift, Kotlin, Flutter, React Native, Python, and Rust bindings; it also documents an OpenAI-compatible local HTTP server bound by default to `127.0.0.1:8080`. [Repository README](https://github.com/cactus-compute/cactus); [CLI server options](https://github.com/cactus-compute/cactus#using-this-repo)
- The repository states that any Hugging Face model can be converted, but labels that capability experimental and says Liquid, Gemma, Whisper, Parakeet, and Qwen families are especially tested. Separately, the engine documentation says non-Cactus model conversion can quantize weights but local runtime-bundle generation is unavailable while its graph builder is rewritten. Therefore “any HF model” is not evidence of deployable compatibility for a URI-selected model. [Repository README](https://github.com/cactus-compute/cactus); [Engine API getting started](https://github.com/cactus-compute/cactus/blob/main/docs/cactus_engine.md)
- Cactus reports an internal CQ weight format and warns that some releases change it, requiring cached weights to be re-downloaded. A URI adapter therefore needs explicit runtime/weight compatibility pinning and rollback treatment. [Runtime and weights compatibility](https://docs.cactuscompute.com/v1.9/docs/compatibility/)

### Inferences

- Cactus is technically plausible as a narrow, optional inference backend for text, vision, speech-to-text, and embeddings. It must never be represented as URI's Second Brain, coordinator, execution authority, or policy engine; its function calls, confidence, cloud-handoff status, transcription, embeddings, and generated text are all inputs to URI's existing deterministic controls.
- No primary source reviewed documents TTS, arbitrary audio generation, video generation/understanding, safety/policy enforcement, tenant isolation, endpoint authorization, durable URI memory semantics, or a supported generic model interchange format. Those are out of scope until separately evidenced.

### Gaps

- No primary-source quality, accuracy, hallucination, multilingual, privacy, or safety benchmark was found for the exact models URI may use. Cactus's published performance table is vendor-reported and is not URI workload evidence.
- The documentation is versioned at v1.9 while the repository release page lists later releases; acceptance must evaluate a pinned release, matching weights, and the exact selected model rather than combining claims across versions.

## Does it permit independent model replacement and local-only operation? What are the platform, lifecycle, telemetry, and network boundaries?

### Takeaway

Model paths and local bundle management permit replacement at the API level, but Cactus's format/version coupling and experimental conversion limit portability. Android arm64 is explicitly documented; Windows is not. Local inference is feasible only as an explicitly configured and empirically network-silent mode because downloads, opt-out telemetry, and optional automatic cloud handoff are all documented network-capable paths.

### Cited Findings

- The C API initializes a model from a caller-supplied weight-folder path; the Python API exposes `cactus_init(model_path, ...)`, and the Android API exposes `Cactus.create(modelPath)`. This supports selecting/replacing an already-compatible local model bundle independently of a fixed hosted model. [Engine API](https://github.com/cactus-compute/cactus/blob/main/docs/cactus_engine.md); [Python lifecycle API](https://docs.cactuscompute.com/latest/python/); [Android API](https://docs.cactuscompute.com/v1.9/android/)
- Model acquisition is networked by default when absent: `cactus download` fetches a pre-built bundle from Cactus Compute's Hugging Face organization, and `ensure_model` downloads a missing bundle. `cactus run` can download or convert a model when it is not found. [Engine API](https://github.com/cactus-compute/cactus/blob/main/docs/cactus_engine.md); [Python model downloads](https://docs.cactuscompute.com/latest/python/#model-downloads); [Repository README](https://github.com/cactus-compute/cactus)
- Cloud fallback is explicitly optional at setup (`cactus auth`), but the CLI's `serve` command exposes automatic cloud handoff and a `--no-cloud-handoff` disable flag. Completion results surface both `cloud_handoff` and a confidence threshold. Cactus therefore has an outbound inference path unless it is deliberately disabled and tested. [Cactus v1.9 docs](https://docs.cactuscompute.com/v1.9/); [CLI server options](https://github.com/cactus-compute/cactus#using-this-repo); [Python completion API](https://docs.cactuscompute.com/latest/python/#completion)
- The engine API says anonymous usage telemetry is sent to Cactus Compute, is opt-out, and exposes environment/app-ID, flush, and shutdown calls. This directly contradicts any assumption that an untouched integration is network-silent. The reviewed API documentation does not state the configuration/API that disables Cactus Engine telemetry. [Engine API telemetry](https://github.com/cactus-compute/cactus/blob/main/docs/cactus_engine.md)
- Lifecycle/resource controls documented in the Python binding are `cactus_destroy` (release model), `cactus_reset` (clear KV cache), and `cactus_stop` (abort generation); completion/prefill responses report time-to-first-token, total time, token rates, RAM use, and token counts. Logging can be reduced to `NONE`. [Python lifecycle and completion API](https://docs.cactuscompute.com/latest/python/); [Engine API logging and performance tips](https://github.com/cactus-compute/cactus/blob/main/docs/cactus_engine.md)
- Android support is explicit: `cactus build --android` produces `libcactus.so`; the documented target is Android API 24+ on `arm64-v8a`. Cactus also documents Kotlin Multiplatform iOS arm64 artifacts. [Android/Kotlin documentation](https://docs.cactuscompute.com/v1.9/android/)
- Cactus's own platform page names iOS, Android, macOS, and wearables. Its public source setup instructions cover macOS and Ubuntu/Debian; the reviewed official documentation and platform page do not list a Windows build, binary, SDK target, or Windows support matrix. [Cactus Engine platform page](https://www.cactuscompute.com/engine); [Cactus v1.9 docs](https://docs.cactuscompute.com/v1.9/)
- Cactus is source-available, not a generally permissive open-source runtime: its license restricts the free grant by use type and organization funding/revenue, and otherwise requires a separate commercial license. [Cactus license](https://github.com/cactus-compute/cactus/blob/main/LICENSE)

### Inferences

- For URI, “independent replacement” should mean: URI owns the selected model ID, local artifact path, version/weight manifest, hash/signature verification, compatibility rules, rollback, and explicit opt-in/opt-out—not merely that a Cactus CLI accepts a model path. No evidence reviewed proves that arbitrary URI models can be converted and executed reliably.
- Treat Windows support as **unknown/not documented**, not supported. A Windows adapter cannot be accepted on inference from Android/macOS/Linux materials or from the presence of generic C/C++ code.
- Local-only operation is an acceptance condition, not a documentation claim: pre-provision weights; disable/refuse cloud handoff; do not invoke download/convert/auth flows during normal execution; configure/disable telemetry if a verified supported mechanism exists; and enforce outbound denial at the host/network layer.

### Gaps

- No reviewed primary source provides an explicit Engine telemetry opt-out switch, exhaustive telemetry schema, destination list, retry/backoff behavior, or proof that telemetry cannot occur before application configuration. This must be resolved from a pinned source revision and runtime network capture.
- No reviewed primary source defines Windows support, Windows hardware acceleration, installer/package, ABI, minimum RAM, power profile, background execution behavior, model eviction, concurrency limits, process supervision, or a memory/thermal budget API.
- “Battery-efficient” is a product claim, but no primary-source battery-drain methodology/results were found for a URI-like workload. The published device benchmark table reports latency/throughput/RAM, not energy consumption. [Cactus v1.9 benchmark](https://docs.cactuscompute.com/v1.9/#benchmark-missing-latency--no-npu-support-yet)

## What acceptance benchmarks must URI run before accepting an adapter?

### Takeaway

Acceptance must be a pinned-version, real-device, end-to-end adapter evaluation—not a successful demo or vendor benchmark. It must prove that URI retains authority and that an intentionally local configuration remains network-silent while meeting explicit performance, memory, cancellation, thermal, battery, and recovery budgets on the platforms URI actually supports.

### Cited Findings

- Cactus includes a benchmark command and its C/Python results expose latency, prefill/decode throughput, RAM use, and token counts; this provides observable measurements but does not establish URI acceptance thresholds. [Repository benchmark description](https://github.com/cactus-compute/cactus); [Python completion API](https://docs.cactuscompute.com/latest/python/#completion)
- Cactus documents early stop/reset/destroy controls and a local HTTP server with configurable host/port. These are relevant surfaces for cancellation, cleanup, process-boundary, and loopback-only tests. [Python lifecycle API](https://docs.cactuscompute.com/latest/python/); [CLI server options](https://github.com/cactus-compute/cactus#using-this-repo)
- Cactus's documentation explicitly identifies downloads, telemetry, cloud handoff, and a cloud API key path. Each requires negative testing in a local-only mode. [Engine API](https://github.com/cactus-compute/cactus/blob/main/docs/cactus_engine.md); [CLI server options](https://github.com/cactus-compute/cactus#using-this-repo)

### Inferences

- **Configuration and supply-chain gate.** Pin one Cactus release/commit, exact engine binary, model artifact, weights-format tag, hashes/signatures, model license, and Cactus commercial-license determination. Demonstrate cold start and offline restart solely from approved local artifacts; verify compatibility, upgrade, downgrade, corrupted-artifact, missing-artifact, and rollback behavior. Do not accept automatic downloads, conversion, or implicit model substitution.
- **Platform gate.** On every URI-supported target—separately Windows x64/ARM64 if Windows remains in scope, and Android API/device tiers if Android is in scope—compile/package, load the model, and run the canonical adapter loop. Windows has no reviewed support claim, so it needs a successful supported build plus maintenance/support evidence before it can be an acceptance target; otherwise record it as unavailable.
- **Performance/resource gate.** With URI's representative prompt sizes, streaming/non-streaming calls, embeddings, image and speech inputs where selected, measure cold/warm TTFT, prefill/decode throughput, end-to-end latency percentiles, peak and steady RSS/PSS, model/disk/cache size, CPU/GPU/NPU utilization, foreground/background behavior, failure rate, and concurrent-request behavior. Set product budgets before the test; compare against those budgets and a baseline runtime rather than vendor numbers.
- **Thermal and battery gate.** On physical Android devices at battery/charging/thermal states representative of URI use, run sustained interactive, continuous transcription, vision, embedding/index, idle, and cancellation loops. Record energy per request/minute, battery-percent/hour, temperature/thermal throttling state, performance degradation over time, and recovery after cooling. Include low-memory/budget hardware, not only flagships.
- **Network-silence gate.** Use an outbound-deny firewall plus packet/DNS/TLS/process telemetry capture for install (if evaluated), first launch, model load, normal inference, errors, idle, shutdown, and repeated restart. Pre-provision artifacts. Attempt low-confidence requests, ensure cloud handoff is disabled, omit credentials, and exercise telemetry flush/shutdown. Acceptance requires zero non-loopback runtime connections and no attempted outbound traffic in the declared local-only profile; loopback server exposure must remain `127.0.0.1` and be authenticated/contained according to URI's local-process policy.
- **Lifecycle/resilience gate.** Repeatedly start/load/reset/stop/destroy; cancel during prefill, decode, VLM processing, and streaming STT; kill/restart the worker; inject malformed responses, out-of-memory/disk-full/permission-denied, incompatible weights, and server-port conflict. Verify bounded cleanup time, no stuck microphone/file handles, no persistent sensitive prompts/audio in logs or caches, no leaked process/port/memory, and a safe URI fallback/error state.
- **Authority and isolation gate.** Feed malicious/invalid tool calls, model-generated routes/URLs, cross-user identifiers, prompt injection from RAG documents, malformed embeddings/transcripts, and forged `cloud_handoff`/confidence metadata through the real URI canonical agent loop. Verify URI—not Cactus—validates schema and tenant context, decides authorization/approval, executes nothing from a model proposal directly, persists/audits only authorized results, and returns execution outcomes to reasoning. This is required even if the adapter calls the local HTTP endpoint, because OpenAI compatibility is an integration shape, not an authorization boundary.
- **Observability/privacy gate.** Confirm URI-owned structured metrics and audit fields are sufficient without enabling vendor telemetry. Verify logging level/callback configuration, redact prompts, output, audio paths, tokens, model locations, credentials, and identifiers; inspect runtime artifacts/caches and network captures after every test.

### Gaps

- URI has not yet stated numerical acceptance budgets for latency, memory, disk, battery, thermal, availability, or model quality. Those must be defined by M33.2 planning before a candidate can pass/fail; this note intentionally does not invent them.
- No Cactus primary source reviewed establishes that telemetry can be disabled for the Engine, or supplies a supported Windows runtime. Until resolved, the local-only and Windows gates are potentially disqualifying rather than routine checks.
