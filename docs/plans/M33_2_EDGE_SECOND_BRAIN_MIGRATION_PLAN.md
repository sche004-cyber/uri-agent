# M33.2 — Edge / Second Brain Foundation: Migration & Integration Plan

**Status:** FROZEN / IMPLEMENTATION-READY — Stage 3 plan; implementation is not started or authorized by this document.

**Architecture:** `docs/architecture/M33_2_EDGE_SECOND_BRAIN_CANONICAL_ARCHITECTURE.md`
**Evidence audit:** `docs/research/M33_2_EDGE_SECOND_BRAIN_ROOT_CAUSE_AUDIT.md`

**Revision history:** revised 2026-09-20 after an independent plan review against live repository source. Corrections are applied in place and marked *[review 2026-09-20]* where they changed a prior claim. Final freeze audit 2026-09-20 revalidated this plan against `631d630aa9f66b70142f55c7397995e9bafab70f` and corrected only stale baseline/governance references and the already-additive assistance consistency points.

## 1. Delivery guardrails

- Preserve propose → validate → approve → execute. No batch adds an Edge execution route, a model-controlled settings write, or a second capability registry.
- Preserve current Main-Brain/native-tool/streaming behavior. `ModelRouter` stays the Main-Brain path; Edge contracts are siblings.
- Use the architecture's `URI_PREFLIGHT` / `EDGE` / `MAIN_BRAIN` layer names. *[review 2026-09-20]* Do not reuse `Tier 0`/`Tier 1`/`Tier 2`: those already name different things in live code and in `/ask` envelope values (`uri_core/core/native_tool_loop.py:1,396-397`; `uri_core/core/tool_schema.py:225`).
- Protect `uri_core/core/orchestrator.py`: it must not grow. Add isolated modules and a narrow server/context seam only after a measured need is proved.
- Preserve the live dirty M33.1 Batch 4 work. Re-record baseline commit/status and test failure names before any implementation batch.
- Each batch is independently reversible behind an Edge feature/rollout gate. Disabling Edge leaves URI_PREFLIGHT and Main-Brain behavior unchanged and retains redacted audit evidence.
- M33.3 consumes backend DTOs only; it is not implemented here, and *[review 2026-09-20]* it is **not** part of M33.2's closure conditions (see §7 and §9).
- **Roadmap boundary** *[review 2026-09-20]*: M33.2 owns the Second-Brain intelligence architecture outright. The former M35 "Mini AI", "Brain ↔ Mini-AI task escalation/delegation", "Shared context/state boundaries", and "Resource/fallback policy" reservation is superseded by the M35 scope correction in `docs/governance/URI_ACTIVE_MILESTONE.md` §1c. No batch here may create, and no later milestone may duplicate, a second intelligence architecture under M35. M35 is Companion Experience — expressions, visual states, presentation, Compact Chat Mode integration — and consumes M33.2's contracts.
- **Parallel Edge Assistance is strictly additive** *[added 2026-09-20]*: architecture §2.2 defines bounded, benchmark-gated, deadline-bounded Edge preparation for Main-Brain requests. It never forces every Main-Brain request through Edge, never allows Edge to execute a tool, and never delays Main-Brain dispatch past its declared deadline. This addition does not reopen or change any of the 27 corrections already applied to the three M33.2 documents.

## 2. Batch A — contracts, settings, and policy skeleton

**Scope:** new isolated `uri_core/core/edge/` contracts for provider/runtime/vision/speech/embedding descriptors and typed proposals; `EdgeSettingsStore`; deployment-owned runtime inventory/policy; deterministic `IntelligenceRoutingDecision` evaluator with a null/unavailable provider; versioned Edge trace DTO/storage; authenticated backend settings/status DTO endpoints. Wire no real model and do not change canonical dispatch.

**Dependencies:** user-scoped path/atomic-store conventions, principal resolution, `CapabilityDirectory` projections, existing trace/usage redaction patterns.

**Prerequisite recorded explicitly** *[review 2026-09-20]*: a **caller-scoped capability/grant feasibility seam**. Today `CapabilityFeasibility` reads connection status unscoped and fail-open (`uri_core/core/capability_feasibility.py:68-76,198`; `uri_core/core/connection_status.py:130`), while the caller-scoped projection exists only at `uri_core/app/server.py:629-635` and is not used by `build_turn_state_and_directory` (`uri_core/core/decision_engine.py:1047-1058`). This is a pre-existing gap, but Batch C's stop condition depends on it, so the seam is designed in Batch A and landed before Batch C.

**Likely subsystems/files:** new `edge/contracts.py`, `edge/settings.py`, `edge/routing_policy.py`, `edge/runtime_inventory.py`, `edge/trace.py`; narrow `server.py` endpoint/context composition; tests at the repository root following this repo's existing convention of root-level `test_*.py` files *[review 2026-09-20 — there is no `tests/` package for application tests]*. Do not modify `orchestrator.py`, `approval_gate.py`, `dispatcher.py`, `canonical_execution.py`, or Graphify authority modules.

**Tests/evidence:** schema/version validation; strict `0..100` threshold; caller-only read/write; optimistic revision conflict under a single lock; model cannot write preference; invalid runtime/model/mode rejected; user isolation; deployment constraints cannot be overridden; status truthfulness including the post-restart case; trace redaction/append-only failure isolation; AST import-boundary tests proving Edge policy cannot import authority/execution modules, modelled on the existing `test_model_router_import_boundary.py` and its `FORBIDDEN_IMPORTS` set. Two additions *[review 2026-09-20]*:

- A negative test that no authorization module reads the Edge settings store or `intelligence_mode`, given that URI already has two other `mode` vocabularies, one authorization-relevant (`uri_core/config/modes.py:15`; `uri_core/core/decision_engine.py:73-81`).
- The AST technique's limitation is recorded rather than over-claimed: `test_model_router_import_boundary.py:27-35` walks `ast.Import`/`ast.ImportFrom` only, so `importlib` or `getattr` access is invisible to it. A runtime assertion covers that residue.

**Acceptance / stop:** a live authenticated settings update changes only the next request's effective routing preference without restart, and no existing `/providers`, `/ask`, gate, or approval behavior regresses. Stop on a required breaking API/persistence change or any authority-import violation.

**Non-goals:** no Needle/Cactus installation, no model inference, no UI, no adaptive calibration.

## 3. Batch B — benchmark harness and candidate qualification adapters

**Scope:** a reproducible, URI-owned benchmark harness plus experimental adapter(s) behind the contracts. Evaluate Needle proposal-only completion, at least one **independent, non-Cactus-Compute** conventional small local text-model adapter, and Cactus only where supported platform/modality evidence exists. No candidate becomes default from vendor claims.

*[review 2026-09-20 — the independent control is now mandatory, not "where practical".]* Needle ships as the package `cactus-needle` from `github.com/cactus-compute/needle` (`reports/Edge runtime evaluation.md:7`), so Needle and Cactus are one vendor's products. Benchmarking only those two cannot demonstrate that these contracts are vendor-agnostic, which is one of this milestone's central claims.

**Dependencies:** Batch A contracts/inventory/trace; frozen corpus, test-data privacy review, artifact manifest and outbound-deny test environment.

**Likely subsystems/files:** `scripts/m33_2_edge_benchmark.py`, versioned golden fixtures/manifests, adapter test doubles and candidate adapters in `edge/adapters/`, no changes to the capability registry/dispatcher.

**Benchmark matrix:**

| Dimension | Required measurement |
|---|---|
| Correctness | intent, offered-capability selection, bounded arguments, schema validity, direct reply, extraction; false Edge replies/proposals; correct/incorrect escalation; multi-tool only when a candidate genuinely supports it. |
| Calibration | raw-score availability/semantics (including the documented `None` case for fine-tuned Needle weights); calibrated score; reliability diagram, ECE/max calibration error/NLL; task and slice quality. |
| Performance | cold/warm p50/p95/p99, TTFT where streamed, throughput, startup/load/unload, Main-Brain tokens used/avoided, URI overhead. |
| Resources | peak/resident RAM, CPU, GPU/NPU when observable, disk/cache, sustained use; Android battery/thermal only when observable. |
| Platforms | Windows desktop and Android/mobile where a candidate is documented and available; record exact OS/device/driver/backend/model/quantization/artifact. Never aggregate them into one “Edge” number. |
| Safety | malformed output, timeout, OOM/resource denial, missing/corrupt artifact, unsupported schema/language/modality, cancellation, no Main Brain, telemetry/download/cloud-handoff/egress capture. |
| **Security / adversarial robustness** *[review 2026-09-20 — new]* | prompt injection embedded in attachment, OCR, email and retrieved-document content; tool-schema injection; cross-user/tenant identifiers in content; forged `cloud_handoff`, confidence and provenance metadata; oversized/duplicated argument shapes. Pass condition is **zero unauthorized execution** and zero proposal referencing a capability outside the offered shortlist. Restores requirements already present in this plan's own evidence base (`research_notes/Edge runtime evaluation/needle.md:79`; `cactus.md:80`). |
| **Licence / redistribution** *[review 2026-09-20 — new]* | the candidate's licence, its use/funding/revenue restrictions, and whether it permits URI's intended distribution and use. Reviewed **before** benchmark investment. Cactus is source-available under a restricted licence, not a permissive open-source licence (`reports/Edge runtime evaluation.md:15`). |
| **Main Brain alone vs. Main Brain + Edge assistance** *[added 2026-09-20 — new, for architecture §2.2]* | For each candidate assistance route (retrieval, extraction, OCR preprocessing, shortlisting, evidence gathering, context preparation): end-to-end latency, TTFT, total tokens, resource use, and task quality, measured for "Main Brain alone" against "Main Brain + qualified Edge assistance" on the same frozen workload. Both the parallel and the deadline-bounded pre-dispatch configurations are measured separately; serial `Edge → wait → Main Brain` is measured only as an explicit comparison point, never assumed superior. |

**Acceptance / stop:** publish raw environment/config and benchmark output; exact acceptance limits are selected from comparative baseline evidence, not invented before measurement. A candidate cannot advance if it executes a host function, lacks a declared score semantic, cannot prove no unexpected egress in local-only mode, lacks artifact provenance, fails the security/adversarial row, has a licence that does not permit URI's intended use, or does not improve a declared workload versus URI_PREFLIGHT alone or another small model. **A specific assistance route is promoted to Batch C only where "Main Brain + Edge assistance" measurably improves latency, cost, or quality over "Main Brain alone" on that route's benchmarked task** *[added 2026-09-20]*; absent that measured benefit, the route is not qualified and Batch C carries no assistance path for it.

**Non-goals:** production default, automatic artifact download, vendor-specific dispatch, UI.

## 4. Batch C — bounded Edge routing and Edge-only canonical proposal path

**Scope:** connect an experimentally qualified text adapter to the deterministic routing state machine. Add a reusable `CapabilityShortlistService` that composes existing `CapabilityDirectory`, `preselect_candidate_ids`, `plausible_matches`, the Batch A caller-scoped feasibility seam, and optional non-authoritative Graphify/embedding hints. Translate a valid Edge tool proposal into the existing canonical proposal/tool translation and gate path.

**Parallel Edge Assistance, additive scope** *[added 2026-09-20, architecture §2.2]*: implement `EdgeIntelligenceProvider.prepare_context()` and the `EdgeAssistanceRequest`/`EdgeAssistanceResult` handoff **only for the specific routes Batch B measured a benefit for**. An unqualified route carries no assistance wiring at all — this is not a general-purpose assistance framework landed ahead of evidence. Assistance dispatch (parallel or deadline-bounded pre-dispatch, per §2.2) is wired into the existing Main-Brain call site without altering `ModelRouter`, native-tool-loop iteration, or streaming behavior; the deadline is enforced so a stalled or slow Edge call never delays Main-Brain dispatch.

**Dependencies:** A, including its caller-scoped feasibility prerequisite; B candidate qualification and workload baseline; existing M32/M34 canonical/native-tool regression baseline.

**Likely affected files/subsystems:** new Edge router/shortlist/translator module; narrow server request handoff; `decision_engine` only if a measured one-time context projection seam is required; current native translator/canonical execution only through an additive, tested adapter. `orchestrator.py` remains protected.

**Adapter target, named** *[review 2026-09-20]*: the Edge proposal enters canonical execution through a contract-injection seam modelled on `native_tool_loop.execute_translated_batch(contract, …)` (`uri_core/core/native_tool_loop.py:250`), which already takes a pre-built contract and wraps it as `DecisionOutcome(status="ok", contract=…)` before `evaluate_gates` (`:299-300`). It must **not** route through `run_canonical_for_ask` (`uri_core/core/canonical_execution.py:603`), which calls `propose_decision` itself (`:637-643`) and would force a Main-Brain call on every Edge turn.

**Tests/evidence:** 5–20 shortlist bound with the architecture's deterministic truncation priority; **`preselect_candidate_ids` returning `None` makes the Edge invocation ineligible and never yields a full-catalogue prompt** *[review 2026-09-20 — the reused function's documented fallback is "show every capability" (`uri_core/core/decision_engine.py:359-361`)]*; no full-catalogue prompt; unknown/offered-later capability rejection; Graphify unavailable/stale → no authority impact; proposal schema errors; grants revoked after shortlist; approval-required and high-risk actions still create/obey current gate outcomes; **an injection-derived proposal targeting a read-only, approval-free capability is rejected or confirmed, never silently auto-executed** *[review 2026-09-20 — `uri_core/core/native_tool_loop.py:125,263-274` auto-executes exactly that class]*; no Main Brain configured bounded command follows identity → proposal → canonical validation → approval/dispatch → evidence; complex Edge-only request returns a model-authored limitation; Main-Brain-preferred and explicit-Main requests bypass Edge; streaming/native Main path unchanged.

**Acceptance / stop:** end-to-end live proof includes evidence/result feedback to the active reasoning loop, and no double inference for URI_PREFLIGHT or explicit-Main paths. Stop if canonical translation needs a parallel executor, permission/gate semantics change, or shortlisting cannot be made caller-scoped.

**Assistance tests/evidence, additive** *[added 2026-09-20]*: a qualified assistance route's deadline lapsing produces immediate Main-Brain dispatch with a `"timeout"`/`"partial"` `EdgeAssistanceResult`, never a delayed Main-Brain call; an `EdgeAssistanceResult` never satisfies `EXECUTE_PROPOSAL` or `EDGE_REPLY` on its own; a Main-Brain request with no qualified assistance route configured is dispatched exactly as it is today, with zero added latency or Edge call; `prepare_context()` cannot reach dispatcher/approval/credential modules (same AST import-boundary test as the rest of `EdgeIntelligenceProvider`); untrusted content flowing into an assistance result is labelled per architecture §4.3 before it reaches the Main Brain.

**Assistance acceptance / stop, additive** *[added 2026-09-20]*: promote a route's assistance wiring only where Batch B's "Main Brain alone vs. Main Brain + Edge assistance" comparison shows measured benefit for that route; stop if assistance ever adds latency to a Main-Brain call beyond its declared deadline, or if any assistance path is found capable of influencing gate/approval outcomes.

**Non-goals:** direct Edge tool execution, broad workflow autonomy, M33.3 UI.

## 5. Batch D — permanent threshold, calibration telemetry, and control-panel readiness

**Scope:** enable direct low-risk Edge replies only after B/C quality evidence; apply the persisted global reply threshold; add versioned calibration profile lookup, delayed correctness-label ingestion, and the control-panel read models. Make `EDGE_REPLY` unavailable on missing/stale calibration.

**Dependencies:** A setting store/trace; B calibration data; C live router; user-visible M33.3 remains deferred.

**Likely files/subsystems:** Edge calibration/telemetry modules, usage aggregation extension or separate Edge telemetry reader, backend DTOs/endpoints. Do not change `ProviderKeyStore`, approval/grant stores, capability registry, or the main provider factory.

**Tests/evidence:** threshold changes live and persists across process/session; **boundary tests at 70/90/99 exercise the architecture's single declared comparison, `round(calibrated * 100) >= reply_confidence_threshold_percent`** *[review 2026-09-20 — previously the comparison itself was undefined]*; raw vs calibrated values and configured threshold trace correctly; a model cannot alter threshold; stale/unknown profile cannot direct-reply; threshold never affects permission/approval/grant/credential/evidence test outcomes; token-avoided values are `KNOWN` only when measured; user isolation and bounded retention.

**Retention precedent, corrected** *[review 2026-09-20]*: "bounded retention" follows `UsageMeter.record` → `usage_path(user_id, "%Y-%m")` under `_locked_append` (`uri_core/core/usage_meter.py:16,96-109`), which is caller-scoped, partitioned and lock-guarded. It does **not** follow `record_shadow_trace`, which writes to a process-global, unrotated, unbounded log (`uri_core/core/decision_engine.py:933,1006-1019`) and is a precedent only for never-raising failure isolation. Pruning after the declared retention window is itself covered by test.

**Acceptance / stop:** M33.3 can render Second Brain status, configured threshold, selected route/reason, provider/model, capability, Main-Brain-called, latency and confidence exclusively from backend DTOs. Stop Edge direct replies if calibration quality/coverage is insufficient; retain proposal-only paths only where separately qualified.

**Non-goals:** adaptive/personalized thresholding, full UI, raw-content telemetry.

## 6. Batch E — vision, voice, and extraction foundations (conditional)

**Scope:** only after a documented modality candidate passes Batch B: sibling observation/transcription/extraction contracts; URI_PREFLIGHT OCR/barcode/metadata reuse; fixtures and provenance/geometry/field-confidence data shapes; resource governor modality admission. No full reconstruction pipeline.

**Dependencies:** A contracts/governor; B modality benchmarks; C authority path for any capability proposal; attachment/evidence boundaries.

**Tests/evidence:** Main Brain disabled image produces a useful, clearly uncertain Edge observation; extraction fields carry source/evidence pointer and field confidence; no direct Graphify/fact write; low transcript confidence blocks or requests confirmation for a sensitive voice action even with high intent score; missing VLM/ASR is an honest modality failure; document geometry/tables/signature regions survive fixture shape; OCR-derived text is labelled untrusted content and cannot promote a proposal past the Batch C injection rules.

**Acceptance / stop:** demonstrate a useful observation/transcript/extraction candidate in a live URI request without weakening current attachment isolation/evidence rules. Stop if required geometry/provenance cannot be preserved or resource/egress evidence fails.

**Non-goals:** camera/microphone UI, companion behavior, DOCX reconstruction, speech synthesis, general visual agent control.

## 7. Batch F — cross-device evidence and closure

**Scope:** qualified Windows/Android profiles, resource governor scenarios including the per-process shared lease pool under concurrent callers, final compatibility/regression, and rollback/operational documentation.

**Dependencies:** every preceding batch. *[review 2026-09-20]* **M33.3 is not a dependency of M33.2 closure.** An earlier draft simultaneously stated that M33.3 was needed "only for control-panel live UI acceptance, not for backend completion" and included "live UI verification once M33.3 exists" in this batch's scope, which made closure depend on a milestone that does not yet exist. M33.2 closes on backend evidence alone; live control-surface confirmation is recorded as an **M33.3-owned follow-on acceptance item**, tracked there, not here.

**Tests/evidence:** compare deterministic URI_PREFLIGHT, every qualified Needle candidate, the mandatory independent small-model candidate, and Cactus where supported; preserve exact platform artifacts; no new full-regression failures; cold/warm resource data; egress evidence; licence record per candidate; Edge-only bounded and complex scenarios; Main failure matrix; M34 Graphify hint and M32 native/streaming compatibility. **Additive** *[added 2026-09-20]*: re-confirm on every qualified assistance route (architecture §2.2) that "Main Brain + Edge assistance" still measurably outperforms "Main Brain alone" under cross-platform/cross-device conditions, that a lapsed assistance deadline never regresses Main-Brain latency, and that native multi-tool use, streaming, iterative reasoning, and multimodality on the Main Brain are unaffected by assistance being enabled or disabled.

**Acceptance / stop:** close only after component, integration, canonical-loop, benchmark, and live backend evidence meet benchmark-derived gates. Quarantine/revert candidate configuration rather than relaxing policy if an environment fails. A provider/runtime may remain unsupported on a platform without blocking other qualified profiles.

**Non-goals:** claiming universal Windows/Android parity or a universal model default.

## 8. Migration/rollback and compatibility

Migration is additive: no existing provider/config file is rewritten, and no current `/ask` route changes behavior unless Edge is explicitly enabled/eligible. Versioned settings migrate by copy/validate; unknown schema is preserved/quarantined and treated disabled. Feature gates can disable provider, direct reply, proposal routing, modality, or telemetry projection independently; they never delete user evidence or Main-Brain configuration. The single top-level `enabled` flag is the one Edge text-intelligence switch, and disabling it disables every Edge modality.

Rollback changes effective routing to URI_PREFLIGHT and the Main Brain, and marks the Edge profile unavailable. It does not silently substitute another edge model, remove audit history, auto-download artifacts, or resubmit side effects. Artifact/profile mismatch, egress violation, malformed proposal, licence failure, and resource policy failure quarantine the affected tuple rather than modifying authority policy.

## 9. Formal acceptance gates

1. **Authority:** AST/import and end-to-end tests prove Edge has no execution/approval/credential/grant authority; every capability action uses the existing canonical path via the §4 contract-injection seam. The AST test's static-only limitation is stated, with a runtime assertion covering dynamic import.
2. **Optionality:** no healthy Main Brain configured still supports a qualified bounded command; complex work explicitly limits/clarifies, in model-authored words.
3. **Truthfulness:** every status/trace distinguishes unavailable, disabled, missing artifact, stale calibration, model failure, and Main-Brain escalation; status never reports a remembered `ready` after restart.
4. **Privacy/isolation:** caller-scoped settings/trace/evidence; a declared Edge request payload inventory; no raw user content, chain-of-thought or credentials in trace; local-only egress evidence when claimed; loopback-only runtime bind asserted and tested.
5. **Quality:** benchmark-derived promotion gates cover reply/proposal/extraction/calibration and false reply/proposal/escalation rates, plus the adversarial-robustness and licence rows.
6. **Performance:** URI_PREFLIGHT and explicit-Main bypass; one shared `build_turn_state_and_directory` result per turn feeding two distinct projections; cold/warm resource evidence; no unexplained Main-Brain latency regression. **Additive** *[added 2026-09-20]*: a qualified Edge assistance route's deadline never delays Main-Brain dispatch, and every promoted assistance route has measured "Main Brain + Edge assistance" benefit over "Main Brain alone" (architecture §2.2; Batch B/C).
7. **Compatibility:** M32 native tools/streaming, M34 Graphify orientation, provider selection, approvals/permissions, canonical evidence, attachments and current UI all retain prior behavior.
8. **Lifecycle:** four-stage evidence remains linked. *[review 2026-09-20]* M33.3's control-surface validation and any future companion/trace consumer are **follow-on items owned by those milestones**, not M33.2 closure gates — the former does not exist yet, and no "Runtime Trace" scope exists in the M35 reservation (`docs/governance/URI_ACTIVE_MILESTONE.md` §1c, M35).
