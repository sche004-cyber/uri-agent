# Edge runtime evaluation patterns

## Why raw model confidence needs URI-side calibration and what calibration/evaluation data should be retained

### Takeaway

An edge model's reported score is not, by itself, evidence that its probability of correctness is reliable for URI's actual inputs. URI should treat confidence as an untrusted proposal: calibrate and evaluate it separately for each immutable model artifact, execution configuration, task, and operating slice; retain the evidence needed to reproduce the mapping and to detect its decay under shift.

### Cited Findings

- Modern neural networks can become less calibrated even while classification error improves; the ICML study evaluates expected calibration error (ECE), maximum calibration error, and negative log likelihood, and reports temperature scaling as an effective post-hoc method in many tested settings. [Guo et al., *On Calibration of Modern Neural Networks*](https://proceedings.mlr.press/v70/guo17a.html)
- Temperature scaling is fitted after training by optimizing a single temperature on a held-out validation set while leaving model weights fixed. This makes a calibration split and the model/configuration it was fitted against first-class evaluation artifacts, rather than an implementation detail. [Guo et al.](https://proceedings.mlr.press/v70/guo17a/guo17a.pdf)
- A NeurIPS benchmark found that conventional post-hoc calibration can fall short under dataset shift; it evaluates both accuracy and calibration under shifted distributions. [Ovadia et al., *Can You Trust Your Model's Uncertainty?*](https://proceedings.neurips.cc/paper/2019/hash/8558cb408c1d76621371888657d2eb1d-Abstract.html)
- NIST states that accuracy measures should use realistic, representative test sets, document the methodology, and may disaggregate results for data segments; ongoing testing or monitoring is used to assess validity and reliability after deployment. [NIST AI RMF 1.0](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf)

### Inferences

- Retain a versioned, access-controlled evaluation record for every calibration/release candidate: model and tokenizer/preprocessor hashes; quantization; runtime, execution-provider, OS, and driver versions; prompt/schema version; calibration split identity and provenance; ground truth/outcome; raw score or logits when available; calibrated score; predicted output; abstain/fallback decision; latency/resource trace; and an error/shift slice label. Retain aggregate reliability diagrams plus ECE, maximum calibration error, NLL, and task-quality metrics—not a score alone. This is the minimum reproducibility trail implied by held-out calibration and NIST's methodology/monitoring guidance.
- Fit and validate on disjoint data; report both in-distribution and URI-representative stress slices (language, noisy audio, image quality/layout, document type, device/accelerator, and offline/pressure conditions). A global threshold must not be claimed to remain calibrated after a model, quantization, prompt, runtime/provider, or input distribution changes.
- Calibration must not authorize an operation. URI can use calibrated uncertainty only as deterministic evidence for a policy-defined action such as return-with-provenance, request clarification, queue human review, or decline; the runtime still validates, authorizes, and executes separately.

### Gaps

- The sources do not establish a universal ECE target, confidence threshold, calibration-set size, or one calibration technique for generative text, VLM, ASR, and embedding retrieval. M33.2 should set task-specific acceptance bounds from measured URI risk and representative data rather than inherit a paper's result.
- A scalar confidence may not be exposed by every provider or may mean different things (token likelihood, classifier probability, similarity, decoder score, or heuristic). Capability negotiation must therefore declare confidence semantics and availability; absence of a comparable score is not a defect that URI may silently synthesize into a safety claim.

## What core benchmark categories and measurement methodologies matter for local text, VLM, ASR, and embeddings on Windows desktop and Android

### Takeaway

Benchmark quality and edge-runtime behavior must be measured separately but on the same versioned workload. Use public task suites for cross-checking, then require URI-owned representative, adversarial, and resource-pressure slices; report accuracy/quality together with tail latency, memory, power where measurable, and actual execution-provider coverage.

### Cited Findings

- MLPerf Mobile defines a benchmark run as a complete execution—including pre- and post-processing—that must meet benchmark-specific latency and quality requirements. Its rules require a consistent system and framework for a result set and audit backend code plus accuracy/performance logs. [MLPerf Mobile Inference Rules](https://github.com/mlcommons/mobile_open/blob/main/rules/mobile_inference_rules.adoc)
- The MLPerf Mobile paper describes Android-app benchmarking of latency and accuracy for mobile-targeted models and identifies power draw as material because devices are battery constrained. [Lai et al., *MLPerf Mobile Inference Benchmark*](https://proceedings.mlsys.org/paper_files/paper/2022/file/a2b2702ea7e682c5ea2c20e8f71efb0c-Paper.pdf)
- Android's NNAPI benchmark evaluates latency and accuracy and compares driver results with TensorFlow Lite CPU execution for the same models and datasets. [Android NNAPI documentation](https://developer.android.com/ndk/guides/neuralnetworks)
- Microsoft's ONNX Runtime performance test can report latency, throughput, memory use, and CPU/GPU utilization for a chosen model and execution provider, with controls for warm-up, iterations, batch size, and concurrency. [Microsoft DirectML tools documentation](https://learn.microsoft.com/en-us/windows/ai/directml/dml-tools)
- On Windows, execution providers are hardware and driver dependent; Windows ML documents CPU and DirectML as bundled, while other providers are separately available and have their own requirements. [Windows ML execution providers](https://learn.microsoft.com/en-us/windows/ai/new-windows-ml/supported-execution-providers)
- The MTEB paper introduces a broad embedding evaluation spanning 8 task types and 58 datasets across 112 languages, rather than treating a single retrieval score as a universal embedding measure. [Muennighoff et al., *MTEB*](https://arxiv.org/abs/2210.07316)
- MME evaluates MLLMs across perception and cognition subtasks, and its authors manually designed instruction-answer annotations to reduce direct public-dataset leakage and prompt-engineering confounds. [Fu et al., *MME*](https://arxiv.org/abs/2306.13394)
- MMBench's official evaluation describes circular evaluation: a multiple-choice item is counted correct only when the model succeeds across circularly shifted answer options, a protocol intended to expose position sensitivity. [MMBench official repository](https://github.com/open-compass/MMBench)
- DocVQA is a document-image VQA dataset, while FUNSD is designed for noisy scanned-form tasks including text detection, OCR, spatial layout, and entity labeling/linking. [Mathew et al., *DocVQA*](https://arxiv.org/abs/2007.00398); [Jaume et al., *FUNSD*](https://arxiv.org/abs/1905.13538)
- NIST's OpenASR evaluation plan specifies word error rate (WER), implemented by its SCTK `sclite` scorer, as the primary ASR metric; the SCTK documentation notes equal-weight word errors by default and the use of character error rate for some languages. [NIST OpenASR Evaluation Plan](https://www.nist.gov/system/files/documents/2021/08/31/OpenASR21_EvalPlan_v1_3_1.pdf); [NIST SCTK `sclite` documentation](https://github.com/usnistgov/SCTK/blob/master/doc/sclite.htm)

### Inferences

- **Common protocol.** Freeze the model artifact, tokenizer/processor, quantization, prompt/schema, runtime/provider, driver, OS build, device SKU, power state, and workload version. Measure cold and warmed runs separately; record end-to-end time (capture/preprocess/inference/postprocess), p50/p95/p99 latency, throughput or real-time factor where applicable, peak/resident memory, failures/timeouts, and energy/thermal observations where the platform can expose them. Publish raw per-run traces and the quality gate with each aggregate.
- **Local text and structured extraction.** Build a URI-owned corpus of supported intents and documents with exact target schemas. Measure parseability/schema-validity rate, required-field precision/recall/F1, value exact/normalized-match rate, relationship/table accuracy where relevant, hallucinated-field rate, refusal/abstention appropriateness, and consistency under paraphrase, option-order, long-context, malformed-input, and prompt-injection stress cases. Use FUNSD/DocVQA-style document and layout cases only as external comparators, not as proof of URI task fitness.
- **VLM.** Separate visual perception/OCR/layout extraction from reasoning, and score each against labeled answers. Include ordinary photos/screenshots, text-rich documents, tables, blur/glare/rotation/crop, small text, multi-image, and unsupported/ambiguous inputs. Use exact or normalized answer measures for extraction and task-specific VQA measures; include a position-sensitivity check inspired by MMBench rather than relying on a single free-form response. MME supplies a useful perception-versus-cognition coverage model, not an acceptance threshold.
- **ASR.** Lock transcript normalization and language/segmentation rules before scoring WER/CER. Add URI-representative accents/languages, noise, far-field speech, interruptions, jargon/names/numbers, silence, overlapping speakers, and short streaming chunks. Measure WER/CER plus deletion/insertion/substitution breakdown, endpointing/partial-result behavior, time-to-first/final transcript, real-time factor, and any word/timestamp confidence calibration; retain audio only under the project's explicit privacy/retention policy.
- **Embeddings.** Cover retrieval (recall@k, MRR, nDCG@k), semantic similarity (correlation with labeled similarity), classification/clustering where used, cross-lingual and hard-negative retrieval, and corpus/index scale. Measure embedding dimension, vector normalization/similarity function, index configuration, retrieval latency, build/update time, memory/disk footprint, and quality after quantization/dimension reduction. MTEB is a breadth baseline; URI should score its own corpus, relevance labels, and negatives independently.
- **Platform matrix.** On Windows desktop, report the selected provider and whether the full graph actually runs there; on Android, compare the selected delegate/driver with an explicit CPU baseline. Test more than one device class and constrained states. Do not pool results across devices or providers into a single "edge" score, since both official platform documentation and MLPerf rules make the framework/system configuration part of the measurement.

### Gaps

- No cited suite covers URI's specific user workflows, policy boundaries, local data shapes, languages, hardware population, or acceptable error cost. Public benchmark scores must therefore be labeled external comparators, not launch evidence.
- No universal cross-platform power/thermal metric is guaranteed by Windows or Android APIs. The plan should define what instrumentation is available per platform and report unavailable measurements as unavailable rather than estimating them.
- These sources do not establish a single fair comparison between heterogeneous VLM generation formats, ASR decoders, embedding indexes, or provider-specific graph partitioning. The plan needs per-capability contracts and fixed harnesses before comparing results.

## What non-claims and unknowns should the plan preserve around devices, resource governors, and model capability negotiation

### Takeaway

M33.2 should make capability discovery and degradation explicit, and should not promise accelerator availability, full-graph acceleration, predictable resource headroom, comparable confidence, or safe autonomous completion. The deterministic URI runtime must choose among only declared, verified capabilities and fail closed to a safe user-visible outcome when they are absent or outside policy.

### Cited Findings

- Android sets per-app heap limits that vary with device RAM; an allocation beyond capacity can raise `OutOfMemoryError`, and cached processes can be terminated at any time under system requirements. [Android memory overview](https://developer.android.com/topic/performance/memory-overview)
- Android documentation warns that approaching available-memory limits can create a steep performance cliff with thrashing and process killing. [Android memory concepts](https://developer.android.com/topic/performance/memory/guide/concepts)
- Windows ML's provider documentation makes provider availability conditional on OS, hardware, and driver requirements, and Microsoft documents provider-specific operator support/profiling as relevant to confirming graph execution. [Windows ML execution providers](https://learn.microsoft.com/en-us/windows/ai/new-windows-ml/supported-execution-providers); [Windows ML WebGPU EP](https://learn.microsoft.com/en-us/windows/ai/new-windows-ml/webgpu-ep)
- NIST AI RMF says systems should be evaluated regularly for identified safety risks, demonstrate residual risk within tolerance, and be able to fail safely, particularly outside their knowledge limits; it also notes human intervention may be needed when an AI system cannot detect or correct errors. [NIST AI RMF 1.0](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf)

### Inferences

- Preserve these explicit non-claims: no guarantee that any Windows PC or Android device has an NPU/GPU/provider; no guarantee a provider supports the whole model graph or a chosen quantization; no promise of a fixed latency, memory ceiling, battery effect, thermal state, or background survival; no equivalence between CPU, GPU, and NPU outputs; no assumption that a provider's confidence is calibrated or comparable; and no claim that a model supports a modality, language, structured output, streaming, timestamps, embeddings, or offline use merely because another provider does.
- Define a signed/versioned capability descriptor that reports facts URI can verify at startup and at run time: modality and operation; input/output schema and limits; supported languages; model/processor/quantization IDs; score/confidence semantics; execution backends and known graph coverage; resource envelope; privacy/data-residency characteristics; and declared failure modes. Unknown, stale, or unverifiable fields must mean "not eligible," not "assumed supported."
- Make the governor deterministic and policy-owned: select only a compatible verified route; preflight resource/timeout limits; monitor deadline, cancellation, memory/thermal/OS signals where exposed; bound retries; record the reason for degradation; and return a safe result such as defer, ask the user, or offer an explicitly approved alternative. A model may propose an interpretation or extraction, but never selects its own authority, retries around policy, escalates privileges, or converts low confidence into approval.
- Treat fallback as a separately benchmarked behavior. Test provider missing, graph partition/fallback, model download/corruption, OOM/process kill, timeout, offline state, cancellation, malformed media, unsupported language/schema, low/unknown confidence, and disagreement across repeated runs. The acceptance criterion is deterministic containment and clear provenance—not merely a successful second model response.

### Gaps

- The cited platform documents do not define a portable cross-vendor resource-governor API, a universal thermal signal, or a guaranteed way to prove full graph placement on every backend. M33.2 must leave vendor/provider adapters and observability as design work, with conservative behavior when signals are absent.
- The evidence does not justify a universal capability schema, fallback order, remote escalation policy, retention period, or user-experience wording. Those are URI architecture and privacy decisions that must be approved separately.
- No source makes edge inference inherently private, secure, accurate, or available. The plan should avoid such claims until URI-specific threat modeling, data-handling controls, and end-to-end validation supply evidence.
