# Needle 3 edge-intelligence provider candidate

Research date: 2026-09-20. Scope: planning evidence only. This note assesses the Cactus Compute `cactus-needle` / Needle 3 project, not unrelated products named Needle. It does not recommend installation or delegate any URI authority to Needle.

## What officially documented interface/runtime dependencies and platforms does Needle 3 have?

### Takeaway

Needle 3 is documented as a local, tool-call/extraction-oriented model plus a small native engine. The minimal Python package declares Python 3.9+ and `huggingface_hub`; JAX and related packages are optional training/build dependencies rather than declared inference requirements. It has unusually broad native, browser, and WASI targets, including Windows x64/ARM64, but the exact artifact version, resource use, and compatibility need URI-host testing.

### Cited Findings

- The official Python package metadata is `cactus-needle` version 3.0.1, requires Python `>=3.9`, and lists only `huggingface_hub` as a base dependency. JAX, JAXLIB, Flax, Optax, Safetensors, and SentencePiece are in the optional `train` extra; CUDA and Metal support are also optional extras. [Package metadata](https://raw.githubusercontent.com/cactus-compute/needle/main/pyproject.toml)
- Official source says the model is intended for tool calls, typed structured extraction, and embeddings; its documented Python constructor accepts decorated Python functions, Pydantic models, raw JSON Schema, or a JSON string as tools. [API reference](https://github.com/cactus-compute/needle/blob/main/doc/apis.md)
- Cactus documents native folders for macOS ARM64; Linux x86-64, ARM64, ARMv7, RISC-V, and MIPS32el; Windows x64 and ARM64; Android ARM64/ARMv7/RISC-V; iOS; watchOS; and tvOS. Native folders contain a runner, static library, and C header. [Supported-device guide](https://www.cactuscompute.com/blog/needle-supported-devices)
- The same guide documents a WebAssembly browser/Node target (`needle.js`, `needle.wasm`) and a WASI Preview 2 component target with `load`, `init`, `complete`, `embed`, and `reset` functions. [Supported-device guide](https://www.cactuscompute.com/blog/needle-supported-devices)
- The Python distribution is documented specifically for macOS Apple Silicon, Linux x86-64/ARM64 (glibc and musl), and Windows x64/ARM64, with engine artifacts fetched on first use; other targets are reached via `needle build --platform`. [Supported-device guide](https://www.cactuscompute.com/blog/needle-supported-devices)
- The native runner can serve a local HTTP endpoint and supports `--system`, `--forced`, and `--fail-input-overflow`. C and Python bindings are documented separately. [Supported-device guide](https://www.cactuscompute.com/blog/needle-supported-devices)
- The repository is Apache-2.0 licensed. [License](https://raw.githubusercontent.com/cactus-compute/needle/main/LICENSE)

### Inferences

- A URI adapter could be designed around the Python `complete()` interface, a native subprocess/local HTTP runner, C FFI, or WASI. Selection is not yet justified by evidence; URI's current deployment and process-isolation requirements should decide it.
- A Python adapter should pin the package and engine/weight artifacts, because the documented first-use experience downloads artifacts rather than supplying an immutable in-repository runtime.
- "Supported" means vendor-documented targets, not that URI has verified them. Windows x64 is the immediately relevant documented target, but needs a clean-host compatibility test.

### Gaps

- Official material reviewed does not provide a formal stability/support policy, ABI compatibility promise, CVE/SBOM process, minimum CPU/RAM requirements, or a signed release-manifest/checksum procedure for the Python wheel plus all native weight/engine downloads.
- The source documentation names 13 platform folders while listing multiple OS variants within grouped rows; URI should record the exact required artifact tag and checksum rather than rely on the marketing count.

## Does it expose a structured proposal/confidence/telemetry/tool-execution pathway relevant to a URI adapter, and what must be treated as unverified?

### Takeaway

Needle exposes grammar-constrained JSON calls, a confidence value, a reasoning string, and basic performance telemetry. However, `run()` explicitly executes supplied Python functions, so it cannot be used as URI's executor. URI must treat all returned calls, arguments, reasoning, confidence, and performance fields as untrusted provider output; only URI's deterministic runtime may validate, authorize, approve, execute, persist, audit, and report.

### Cited Findings

- `complete()` returns a single response object including `type`, success/error values, `function_calls`, `reasoning`, `confidence`, `prefill_tps`, `decode_tps`, and `peak_ram_mb`. The published example shows the call arguments as JSON. [API reference](https://github.com/cactus-compute/needle/blob/main/doc/apis.md)
- The vendor says a byte-level grammar compiled from tool schemas constrains call decoding, and that responses carry a calibrated confidence score. [Repository README](https://github.com/cactus-compute/needle/blob/main/README.md)
- The published confidence contract says confidence is the minimum of a calibrated post-hoc head and call-token decoding probability; the default engine threshold is 0.1 and low-confidence calls are escalated/withheld. It also states that fine-tuned weights report confidence as `None`, because the calibration head is not updated. [API reference](https://github.com/cactus-compute/needle/blob/main/doc/apis.md)
- The official response example distinguishes `function_calls` from `suppressed_calls`; its suggested routing example is application code, not an authorization system. [Needle 3 product guide](https://www.cactuscompute.com/needle)
- `run()` is documented as a full agent loop in which Needle selects calls, executes the supplied Python functions, feeds their results back to the model, and returns executed results. The separate `complete()` example lets the host execute a returned call and feed back a result manually. [API reference](https://github.com/cactus-compute/needle/blob/main/doc/apis.md)
- The native C API accepts Needle compact or OpenAI-style tool schemas and returns calls; the vendor says a native API has one process-global model and conversation. [Supported-device guide](https://www.cactuscompute.com/blog/needle-supported-devices)
- The project states that binary telemetry is enabled by default. Its documentation describes it as anonymous usage counts (function name, package version, OS, random install id), says prompts/outputs/data are excluded, and documents opt-out through `NEEDLE_TELEMETRY=0` or `DO_NOT_TRACK=1`; CI is said to be excluded automatically. [Project reference](https://github.com/cactus-compute/needle/blob/main/llms.txt)

### Inferences

- URI's safe integration shape is **proposal only**: invoke `complete()` (or an equivalently isolated native/WASI call), parse a bounded provider response, discard or retain `reasoning` only under URI's data policy, translate `function_calls` to URI proposals, and run URI's existing deterministic schema validation, route classification, authorization, approval, execution, persistence, audit, and feedback loop. Do not pass executable URI tools/functions to `run()`.
- Grammar-valid JSON and a calibrated score can reduce parse failures or support UX/routing signals; neither proves intent, policy conformance, role eligibility, route safety, grounding, or authorization. Confidence must never be an approval/authorization input.
- `prefill_tps`, `decode_tps`, and `peak_ram_mb` are useful candidate observations only. URI must measure externally as well, because they are provider-reported fields.
- URI should default-deny all outbound traffic for the provider process. The vendor's own documentation makes an explicit disable configuration necessary because telemetry is on by default.

### Gaps

- No reviewed official source specifies a cryptographic integrity/authenticity protocol for provider response fields, telemetry payloads/endpoints, a machine-readable telemetry-disable acknowledgement, or a supported audit log export.
- No reviewed material establishes confidence calibration on URI's schemas, adversarial inputs, distributions, platforms, sliced models, or fine-tuned models. The vendor explicitly says tuned weights lack confidence; therefore a tuned Needle 3 provider has no documented calibrated confidence output.
- The documented `reasoning` is model-generated prose. It is not a deterministic explanation or proof and must not be used as policy evidence. The exact full error, truncation, cancellation, timeout, and concurrency semantics relevant to a URI adapter remain unverified.
- Official documentation claims tool grounding/repair behavior, but URI should not accept it as a replacement for its own canonical validation; no URI-specific corpus or independent audit was located.

## What benchmark and network-silence/telemetry validation should URI require before accepting it?

### Takeaway

Vendor figures are useful sizing hypotheses, not acceptance evidence. Require a reproducible URI corpus and a cold/warm benchmark on each target host, then prove that the fully provisioned, runtime process emits no network traffic under both normal and failure paths. The default-on telemetry disclosure makes observed network-silence testing a release gate, not merely a configuration review.

### Cited Findings

- Cactus reports 400--4,000 decode tokens/s and 1,000--10,000 prefill tokens/s on Raspberry Pi 5 across depths, and says each response reports prefill/decode throughput and peak RAM. [Supported-device guide](https://www.cactuscompute.com/blog/needle-supported-devices)
- Cactus describes Needle 3 as an 8--29 MB binary family and reports an 8 MB four-layer to 29 MB 20-layer range in the repository; another official device guide describes 29 MB at 20 layers and smaller artifacts at lower depths. [Repository README](https://github.com/cactus-compute/needle/blob/main/README.md); [Supported-device guide](https://www.cactuscompute.com/blog/needle-supported-devices)
- The product page identifies its advertised benchmark suites and metrics: Mobile Actions (961 rows, exact call), DroidCall (200 rows, calls in order), BFCL v4 (3,641 rows, AST match/no call on irrelevant), DSTC8 (1,813 turns, field F1), and SNIPS variants (700 rows each, field F1). [Vendor benchmark page](https://www.cactuscompute.com/needle)
- The vendor's offline instructions require prefetching/copying the engine and `needle3.cact`, can use `NEEDLE3_LIB_PATH`, and recommend `HF_HUB_OFFLINE=1` so missing assets fail instead of downloading. It claims inference itself does not touch the network. [API reference](https://github.com/cactus-compute/needle/blob/main/doc/apis.md); [Supported-device guide](https://www.cactuscompute.com/blog/needle-supported-devices)
- The vendor advises disabling default binary telemetry with both `NEEDLE_TELEMETRY=0` and `DO_NOT_TRACK=1`. [Repository README](https://github.com/cactus-compute/needle/blob/main/README.md)

### Inferences

- URI acceptance benchmark: pin the exact wheel, engine, archive, depth, tool schemas, host OS/CPU/RAM, and configuration; record SHA-256 values; run at least cold start and warm steady-state. Measure wall-clock p50/p95/p99 end-to-end proposal latency, time to first result, process CPU, RSS/peak working set, model/engine disk footprint, error/timeout/restart rate, and output-size limits independently of provider self-reporting.
- URI correctness/security corpus: include permitted and forbidden routes, unauthenticated and every relevant role, cross-user/tenant identifiers, malformed/oversized input, ambiguous requests, prompt injection, tool-schema injection, stale or conflicting context, unsupported requests, low-confidence outputs, and multi-step result feedback. Score exact valid proposal mapping, false-positive proposal rate, false-negative rate, malformed-output rate, unauthorized/forbidden proposal rate, and deterministic runtime rejection. The pass condition must include **zero unauthorized execution**, because URI executes nothing from provider output without its own chain.
- Compare `complete()`/proposal-only operation with any other candidate in identical hardware and corpus conditions. Do not benchmark `run()`: it would test the provider's direct execution loop rather than URI's canonical loop.
- Network-silence gate: perform a separate connected provisioning phase; then execute an offline runtime phase with all artifacts present, `HF_HUB_OFFLINE=1`, `NEEDLE_TELEMETRY=0`, and `DO_NOT_TRACK=1`. Use OS-level packet capture/firewall audit plus DNS and proxy logs, deny all egress from the provider process/container, and assert no DNS, TCP/UDP, QUIC, HTTP(S), package/model fetch, telemetry, crash reporting, or retry traffic during normal requests, invalid requests, missing-file errors, model-load errors, and process restarts. Preserve the capture/configuration/artifact hashes as audit evidence.
- Run the network gate twice: before and after an attempted upgrade/reprovisioning, because default artifact fetching and default telemetry are documented behaviors. A clean failure under denied egress is acceptable; a silent fallback, unlogged cloud handoff, or any outbound attempt is not.

### Gaps

- URI has not set acceptance thresholds for latency, memory, proposal accuracy, false-positive rate, or allowed hardware. Those are product/architecture decisions, not facts established by the Needle sources.
- Vendor benchmark claims have not been independently reproduced on URI hardware or URI tool schemas. The sources do not provide a URI-relevant confidence calibration report, a third-party network-silence attestation, or results for Windows URI deployment.
