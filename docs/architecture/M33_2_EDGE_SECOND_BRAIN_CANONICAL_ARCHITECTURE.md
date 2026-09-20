# M33.2 — Edge / Second Brain Foundation: Canonical Architecture

**Status:** FROZEN / IMPLEMENTATION-READY — Stage 2 architecture. It is not an approval to implement. It completes Stage 2 of URI's mandatory lifecycle after the companion evidence audit; Stage 3 migration is in `docs/plans/M33_2_EDGE_SECOND_BRAIN_MIGRATION_PLAN.md`. M33.2 implementation has not started.

**Revision history:** revised 2026-09-20 after an independent plan review conducted against live repository source. The review's corrections are applied in place and marked inline as *[review 2026-09-20]* wherever they changed a prior claim, so the earlier wording is not silently overwritten. Final freeze audit 2026-09-20 revalidated this document against `631d630aa9f66b70142f55c7397995e9bafab70f` and corrected only stale baseline/governance references and the already-additive assistance contract presentation.

**Core principle:** **URI is the system. The Main Brain is optional intelligence plugged into it. The Second Brain keeps URI useful, responsive, and capable even without a Main Brain.**

## 1. Non-negotiable authority model

Models may interpret, classify, rank a bounded offered shortlist, propose tools/arguments, extract structured candidates, draft bounded answers, and describe observations. URI alone owns identity, user isolation, permissions, grants, approvals, credentials, lifecycle, dispatch, evidence, audit, settings authority, and final execution authorization.

`experience_tier` remains UX-only. Edge confidence, mode, runtime health, a valid grammar, or a 99% score never equals permission, approval, grant, credential access, evidence sufficiency, or execution authority.

## 2. Intelligence-layer topology

*[review 2026-09-20 — naming correction.]* This milestone previously named its three layers "Tier 0 / Tier 1 / Tier 2". That vocabulary is already in live production use with **incompatible** meanings and must not be reused:

- `uri_core/core/native_tool_loop.py:1` defines "Tier 0 (direct chat) and Tier 1 (native tool loop)". Live Tier 0 is a **Main-Brain completion that declined every offered tool**, not a deterministic no-model path.
- `/ask` already returns these literal envelope values to clients: `"tier": "tier0"`, `"tier1"`, `"tier1_continuation"`, `"tier1_bounded"` (`uri_core/core/native_tool_loop.py:396-397,470,478,522`).
- `uri_core/core/tool_schema.py:225` uses "Tier 2 escalation territory" to mean **workflow-procedure escalation**, not the Main Brain.
- The same M32 meanings recur in `uri_core/app/server.py:1729,1971,2006` and `uri_core/core/stream_tool_loop.py:1,14,17,161`.

M33.2 therefore uses three distinct layer names — `URI_PREFLIGHT`, `EDGE`, `MAIN_BRAIN` — and never emits `tier0`/`tier1`/`tier2` in any new field or value.

```text
authenticated request / attachment / transcript
                 |
                 v
        URI_PREFLIGHT (deterministic)
  identity, input limits, request type, URI fast paths,
  capability offer projection, risk/approval metadata
                 |
                 v
    IntelligenceRoutingCoordinator (deterministic)
       | SUPPRESS / CONFIRM / EDGE_REPLY /
       | EXECUTE_PROPOSAL / ESCALATE
       |
       +-- EDGE: EdgeIntelligenceProvider -- proposal/observation only
       |       +-- EdgeRuntime (optional: Cactus, other)
       |       +-- model adapter (optional: Needle, small text model)
       |       +-- EdgeVisionProvider / EdgeSpeechProvider / Embedder
       |
       +-- MAIN_BRAIN: existing Main Brain
               ModelRouter -> build_provider -> model-native tool loop /
               streaming / ordinary reasoning
                 |
                 v
  canonical proposal adapter (only proposed id + bounded args)
                 |
                 v
 CapabilityDirectory + schema + resolver + gates + ApprovalGate
                 |
                 v
 dispatcher / workflow / evidence / audit / user-visible result
                 |
                 v
 bounded result/evidence feedback to whichever intelligence continues
```

The coordinator is deterministic policy, not task-specific reasoning. It consumes a runtime-produced, read-only projection of risk, permission/approval requirement, availability, transcript quality, provider/runtimes health, and a bounded shortlisted capability set. It does not execute a tool and must not import dispatcher, approval gate/store, credential stores, or Graphify as an authority source.

### 2.1 Canonical entry seam for an Edge proposal

*[review 2026-09-20 — the "canonical proposal adapter" above required a named, real seam; it had none.]*

A validated Edge proposal must enter canonical execution through a **contract-injection seam** modelled on `native_tool_loop.execute_translated_batch(contract, *, results_meta, orchestrator, session_id, user_text, principal, directory, turn_state_data, capability_registry, executed_signatures)` (`uri_core/core/native_tool_loop.py:250`). That function already accepts an **already-built** Decision Contract, wraps it as `DecisionOutcome(status="ok", contract=contract)`, and runs `evaluate_gates` (`:299-300`) — exactly the shape an Edge proposal needs.

It must **not** enter through `run_canonical_for_ask` (`uri_core/core/canonical_execution.py:603`). Despite being documented as "the single M30.6 entry point for a live `/ask` call site", that function builds its own contract by calling `propose_decision(...)` internally (`:637-643`), which would force a Main-Brain call on every Edge turn — the double inference §12 forbids.

### 2.2 Parallel Edge Assistance / Main-Brain Preparation

*[added 2026-09-20 — strictly additive; does not reopen or alter §1–§13's prior content or any of the 27 review corrections above.]*

The five-state routing machine in §6 governs *which layer answers*. This subsection governs a separate, orthogonal question: when a request is going to `MAIN_BRAIN` regardless (an explicit Main-Brain request, or an `ESCALATE` outcome), may a qualified Edge capability do bounded, useful work **before or alongside** that Main-Brain call, so the Main Brain arrives with prepared context rather than starting cold? This is assistance, never an alternative answer, and it never changes which layer holds authority.

**What assistance may do.** Bounded retrieval, extraction, attachment/OCR preprocessing, capability shortlisting (§5), evidence gathering, and structured context preparation. Assistance output is *always* context handed to the Main Brain — it is never itself a reply, a proposal executed on the user's behalf, or a substitute for `EDGE_REPLY`/`EXECUTE_PROPOSAL`.

**When it may run.** Only when a prior benchmark comparison (migration plan Batch B) has shown a measured latency, cost, or quality benefit for that specific task/modality/candidate combination. Absent that evidence, the request goes straight to the Main Brain with no Edge involvement — assistance is opt-in per qualified route, never a default added to every Main-Brain call.

**Timing invariant.** Assistance work either runs **in parallel** with the Main-Brain call being dispatched, or completes within a short, declared **assistance deadline** before dispatch — never serially as `Edge → wait → Main Brain` unless that serial ordering is itself the benchmarked, evidence-backed configuration. If the deadline lapses, the Main-Brain call proceeds immediately with whatever `EdgeAssistanceResult` exists at that moment (which may be `status: "skipped"` or `"partial"`); the Main Brain is never blocked waiting on Edge. This reuses the shared `build_turn_state_and_directory` result (§12) as its input, not a second turn-state construction.

**Handoff contract.** Assistance results reach the Main Brain only through a bounded, typed, URI-owned `EdgeAssistanceResult`, added as a sibling to the proposal types in §4:

```python
@dataclass(frozen=True)
class EdgeAssistanceRequest:
    kind: str                 # "retrieval" | "extraction" | "ocr_preprocess" |
                               # "shortlist" | "evidence_gather" | "context_prep"
    deadline_ms: int           # required; no unbounded assistance call exists
    inputs: EdgeRequest         # reuses the §4.1 payload inventory - same
                                 # untrusted-content labelling rules apply

@dataclass(frozen=True)
class EdgeAssistanceResult:
    status: str                 # "completed" | "partial" | "timeout" | "skipped" | "error"
    provider_id: str
    runtime_id: str
    content: EdgeAssistancePayload  # URI-owned, versioned, bounded schema for `kind`
    provenance: list             # source pointers, never asserted as fact
    uncertainty: Optional[float]  # or UNAVAILABLE, same semantics as §4/§9.1
    completeness: str            # "full" | "partial" | "unknown"
    latency_ms: int
    errors: list
```

No raw rationale, chain-of-thought, or free-text justification is carried in `content`. The Main Brain receives `EdgeAssistanceResult` as ordinary tool/context input through its existing native-tool or prompt-construction path (`uri_core/core/native_tool_loop.py`) — assistance never gains a private channel into the Main Brain that bypasses the same turn-state/attachment/evidence handling every other input goes through.

**Provider surface.** No new protocol is introduced. `EdgeIntelligenceProvider` (§4) gains one additional method, `prepare_context(self, request: EdgeAssistanceRequest) -> EdgeAssistanceResult`, alongside its existing `classify`/`extract`/`propose_tools`/`propose_response` methods — assistance reuses the same provider, runtime, calibration, and untrusted-content rules already defined for those, rather than creating a second Edge surface.

**What this does not change.** URI remains the sole authority/execution system; `prepare_context` cannot execute a tool, cannot skip gates, and its output can never itself satisfy `EXECUTE_PROPOSAL`. Not every Main-Brain request is forced through Edge — assistance is per-route opt-in, benchmark-gated, and skippable. Strong Main Brains retain full native multi-tool use, streaming, iterative reasoning, and multimodality unchanged; assistance supplies them additional context, never a narrower interface. Routing stays provider/model agnostic — `prepare_context` is defined on the same `EdgeIntelligenceProvider` Protocol every candidate already implements.

**Truthful progress facts.** While assistance (or the Main Brain itself) is in flight, URI may surface deterministic, factual progress state for a future UI/Companion consumer — e.g. `"stage": "ocr_extraction"`, `"stage": "awaiting_main_brain"`, `"elapsed_ms"` — sourced from the same `EdgeAssistanceResult`/routing-trace fields already defined in §9.2. This is a projection of already-known facts, not new content: no model may invent, phrase, or embellish a progress message, matching §3.1's rule that URI decides facts and a model may only author user-facing prose from facts it is actually given. A progress fact with no corresponding real state (e.g. a fabricated percentage) must never be emitted.

`EdgeAssistancePayload` is a URI-owned discriminated, versioned schema with a bounded payload shape per `kind`; arbitrary provider objects and unbounded free text are rejected before handoff. This keeps the handoff typed and bounded without making it an authority-bearing proposal.

## 3. Operating modes and eligibility

Per-user `intelligence_mode` is one of:

| Mode | Normal behavior |
|---|---|
| `EDGE_ONLY` | URI_PREFLIGHT first; use an eligible Edge response/proposal. Never call the Main Brain. A complex/unsupported request returns an honest limitation or one necessary clarification. |
| `HYBRID` | URI_PREFLIGHT first; invoke Edge only when its declared model profile is eligible and policy says an inexpensive proposal/reply is plausible. Escalate explicitly when it is not. |
| `MAIN_BRAIN_PREFERRED` | URI_PREFLIGHT first; explicit Main-Brain requests, complex tasks, broad research/drafting, and native/iterative tool tasks bypass Edge and retain full Main-Brain behavior. Edge is reserved for declared fast local routes and Main-Brain-unavailable recovery; it does not add mandatory double inference. |

*[review 2026-09-20 — naming correction.]* The field is `intelligence_mode`, **not** `operating_mode` or a bare `mode`. URI already carries two unrelated `mode` vocabularies on the same user, one of which is authorization-relevant:

- **Capability mode** `{"office","diagnostic","admin"}` (`uri_core/config/modes.py:12,15`), carried on `PrincipalContext.mode`, read during gating, exposed at `GET`/`PUT /modes` (`uri_core/app/server.py:1346,1356`).
- **Decision-contract mode** `{"conversation","clarification","unsupported","single_action","multi_action","approval_required","workflow_continuation"}` (`uri_core/core/decision_engine.py:73-81`), which governs executability via `EXECUTABLE_MODES` in `canonical_execution.py`.

`intelligence_mode` is a routing preference only and is never read by either of those paths.

The user can change the preference live; the next request reads it. Deployment constraints can make an otherwise selected mode less capable, but cannot silently rewrite the saved preference.

An Edge invocation is eligible only if all are true: Edge is enabled; selected runtime/model/artifacts are declared compatible and healthy; a task/modality/schema profile is supported; capability shortlist is bounded; resource governor accepts the request; no explicit Main-Brain bypass applies; and the request does not require unavailable evidence or a capability not offered to Edge. Unknown is ineligible, not optimistic.

### 3.1 Authorship of Edge-only limitations and confirmations

*[review 2026-09-20 — this conflicted with URI's standing rule that URI never composes user-visible prose.]*

The user-visible text of a `CONFIRM` question and of an `EDGE_ONLY` limitation must be **model-authored**, produced by a constrained `propose_response` call restricted to a clarification or limitation form. URI decides the outcome deterministically and hands the model the real, already-decided facts; it does not write the sentence.

A deterministic template is permitted **only** as a validated fallback when no model draft is available or the draft fails validation, and it may restate only already-decided facts. This matches the live discipline at `uri_core/core/canonical_execution.py:447`, where the message comes from the model's own `unsupported_reason` and a hardcoded string is used only when that field is absent.

## 4. Provider- and runtime-agnostic contracts

These are new sibling contracts under a new `uri_core/core/edge/` package. They do **not** subclass `ModelProvider`: `ModelProvider` is an `ABC` exposing `complete`/`complete_stream`/`describe` for full completion/streaming/native-tool behavior (`uri_core/core/model_providers/base.py:266-323`), while an Edge provider makes bounded, typed proposals and may use a separate local runtime.

```python
class EdgeIntelligenceProvider(Protocol):
    def health(self) -> EdgeHealth: ...
    def classify(self, request: EdgeRequest) -> EdgeClassification: ...
    def propose_tools(self, request: EdgeToolRequest) -> EdgeToolProposal: ...
    def extract(self, request: EdgeExtractionRequest) -> EdgeExtractionProposal: ...
    def propose_response(self, request: EdgeReplyRequest) -> EdgeReplyProposal: ...
    def propose_companion_event(self, request: EdgeCompanionRequest) -> EdgeCompanionProposal: ...
    def prepare_context(self, request: EdgeAssistanceRequest) -> EdgeAssistanceResult: ...
    def describe(self) -> EdgeProviderDescriptor: ...

class EdgeRuntime(Protocol):
    def inventory(self) -> RuntimeInventory: ...
    def load(self, artifact: ModelArtifact, budget: ResourceBudget) -> RuntimeLease: ...
    def unload(self, lease_id: str, reason: str) -> None: ...
    def status(self) -> RuntimeStatus: ...

class EdgeVisionProvider(Protocol):
    def observe(self, request: VisionRequest) -> VisionObservationProposal: ...

class EdgeSpeechProvider(Protocol):
    def transcribe(self, request: AudioRequest) -> TranscriptProposal: ...

class EdgeEmbeddingProvider(Protocol):
    def embed(self, request: EmbeddingRequest) -> EmbeddingProposal: ...
```

*[review 2026-09-20.]* An earlier draft declared both a `descriptor` attribute and a `describe()` method returning the same `EdgeProviderDescriptor`. The redundant attribute is removed; `describe()` is the single accessor. Its name deliberately mirrors `ModelProvider.describe()` (`uri_core/core/model_providers/base.py:323`) while returning a different, Edge-specific type — implementations must not be interchangeable. `prepare_context()` is the §2.2 additive assistance method; it is shown here so the Protocol and handoff contract cannot diverge.

Every proposal carries `provider_id`, `runtime_id`, model/artifact/version hash, operation kind, bounded structured result, raw confidence *with declared semantics or `UNAVAILABLE`*, latency/resource measurements where available, and errors. It carries neither a privilege claim nor an execution result. All opaque provider fields are rejected or retained only in a quarantined debug artifact, never passed to canonical execution.

`EdgeRuntime` may have a Cactus adapter; a Needle adapter may use that runtime or another compatible runtime. Vision, speech, embedding and text model artifacts are independently selected, verified, loaded, and replaceable. No URI type implies that Cactus is a Second Brain, Needle is a vision model, or an Edge model can execute a tool.

### 4.1 Edge request payload inventory

*[review 2026-09-20 — previously undefined, which made a privacy review impossible: trace redaction was specified in detail while the model's actual input was not.]*

An `EdgeRequest` and its siblings may carry only the following, and each field must be declared per operation kind:

| Field | Contents | Notes |
|---|---|---|
| `user_text` | The current turn's user text | Required for classify/propose/reply |
| `conversation_excerpt` | A bounded, count-limited recent-turn excerpt, or absent | The bound is declared per profile; unbounded history is never sent |
| `offered_capabilities` | The bounded shortlist's `describe()` entries only (§5) | Never the full catalogue |
| `attachment_derived_text` | OCR/extracted text for attachments explicitly referenced this turn | Marked `untrusted_content` (§4.3) |
| `transcript` | ASR output when the operation is voice interpretation | Carries transcript confidence separately |
| `schema` | The requested output schema and its version | |

No credential, grant, approval record, audit record, other user's data, or internal authority state is ever placed in an Edge request. What may be *logged* about a request is separately and more narrowly constrained by §9.2.

### 4.2 Needle and Cactus integration rules

- Needle evaluation may use only a `complete()`-style proposal interface. Its `run()`/host-function execution loop is forbidden from receiving URI capabilities.
- Cactus may be evaluated as a runtime only for documented/verified platform-modality-artifact tuples. Cactus's tool calls, cloud-handoff flags, transcriptions, embeddings, and outputs remain proposals.
- All artifacts are pinned and content-hashed. Downloads, conversion, cloud handoff, telemetry, and network egress are disabled or denied in a declared local-only profile and tested under capture. If not demonstrably silent, that profile is ineligible.
- A runtime's loopback or OpenAI-compatible server is a transport, never an authorization boundary. **The adapter must additionally assert a loopback-only bind and reject any non-loopback base URL, with that rejection covered by a test** *[review 2026-09-20]* — Cactus ships an OpenAI-compatible HTTP server (`reports/Edge runtime evaluation.md:13`), and URI already treats non-loopback binding as a security decision rather than a configuration detail (`docs/plans/M22.3_SECURITY_ARCHITECTURE_PLAN.md` §5.3; the host guard in `scripts/run_uri_server.py`).

**Common vendor ownership, disclosed** *[review 2026-09-20]*: Needle ships as the package `cactus-needle` from `github.com/cactus-compute/needle` (`reports/Edge runtime evaluation.md:7`). Needle and Cactus are products of **one vendor**. Benchmarking both therefore cannot demonstrate that these contracts are vendor-agnostic. At least one independent, non-Cactus-Compute local runtime must be qualified against the same contracts before any candidate is promoted.

**Licence and redistribution are a first-class eligibility gate** *[review 2026-09-20]*: Cactus is "source-available under a license with use/funding/revenue restrictions, not a generally permissive open-source license" (`reports/Edge runtime evaluation.md:15`). A candidate that passes every technical gate but whose licence does not permit URI's intended distribution and use is **ineligible**. Licence review happens before, not after, benchmark investment.

### 4.3 Untrusted content reaching an Edge prompt

*[review 2026-09-20 — no prompt-injection or untrusted-content handling existed anywhere in this package, although the evidence base it cites requires it: `research_notes/Edge runtime evaluation/needle.md:79` and `cactus.md:80`.]*

Attachment text, OCR output, email bodies, retrieved documents, and transcripts are **untrusted content**. Any Edge proposal derived from a request containing untrusted content is itself untrusted, and this is live-relevant rather than theoretical:

- Attachment metadata already enters the proposal context, and capabilities declaring `reads_current_attachments` are surfaced for ambiguous wording (`uri_core/core/decision_engine.py:395-401`); attachment JSON is injected into the prompt at `uri_core/core/native_tool_loop.py:457-463`.
- `execute_translated_batch` **auto-executes** single-capability calls that are both read-only and approval-free, concurrently (`uri_core/core/native_tool_loop.py:125,263-274`).

Gates correctly stop privileged actions, so the residual surface is an injected instruction steering a *read-only, approval-free* proposal. Required rules: untrusted content is delimited and labelled in the request; an untrusted-derived proposal is marked in the trace; and injection-derived proposals against read-only approval-free capabilities are an explicit test case, not an assumption (see the migration plan's Batch B security row and Batch C tests).

## 5. Capability shortlisting and proposal translation

```text
existing CapabilityDirectory summaries
  + existing `preselect_candidate_ids` / `plausible_matches`
  + a caller-scoped capability/grant feasibility view (see below)
  + optional Graphify pointer relevance / optional embedding rank
                      |
          deterministic bounded shortlist (default target 5-20)
                      |
     `describe()` only those entries; remove unsupported/unknown
                      |
 Edge chooses one offered capability/action and bounded arguments
                      |
 EdgeProposalTranslator -> existing canonical proposal/tool-call shape
                      |
 tool schema validation -> CapabilityResolver -> decision gates
 -> ApprovalGate -> canonical execution -> evidence/audit
```

### 5.1 The reused preselection primitive fails open — Edge must not

*[review 2026-09-20.]* `preselect_candidate_ids` (`uri_core/core/decision_engine.py:331`) defaults to `limit=5` and, per its own docstring (`:359-361`), "Returns None (never an empty list treated as 'nothing plausible') when preselection cannot run at all, so the caller falls back to showing every capability rather than silently showing none."

For the Main Brain that fail-open behavior is deliberate and safe. For Edge it would defeat both the bounded-shortlist requirement and the migration plan's "no full-catalogue prompt" test. Therefore: **a `None` result makes the Edge invocation ineligible** — route `SUPPRESS` or `ESCALATE`. It never means "offer everything".

Separately, the returned list is **not** bounded by `limit`. It unions lexical matches, `originating_goal` matches, every `_foundational_ids` entry, and every `reads_current_attachments` capability (`:373-401`). The 5–20 target is therefore a property Edge must enforce itself, using this deterministic truncation priority:

1. Foundational ids (never dropped).
2. Capabilities declaring `reads_current_attachments`, when the turn has attachments.
3. Highest-scoring lexical/`originating_goal` matches, in score order, until the bound is reached.

If truncation would drop a category-1 or category-2 entry, the shortlist is over-bounded and the invocation is ineligible rather than silently narrowed.

### 5.2 Caller-scoped feasibility is a prerequisite, not an existing capability

*[review 2026-09-20 — correcting a claim this document previously made.]* An earlier draft listed "current principal's existing capability/grant feasibility view" as an available input. Live code does not provide that:

- `CapabilityFeasibility.snapshot()` calls `_connection_status_by_service()` (`uri_core/core/capability_feasibility.py:198`), which calls `list_connection_status()` with **no `user_id` and no `service_store`** (`:74`), so it resolves to the repo-root `token.json` rather than the caller's scoped token (`uri_core/core/connection_status.py:130`).
- It is explicitly fail-open: a failure "degrades to an empty dict, which `_permission_blocked_by` then treats as 'nothing known to be blocked'" (`uri_core/core/capability_feasibility.py:68-71`).
- The caller-scoped projection exists only at `_connection_status_for_user()` (`uri_core/app/server.py:629-635`), which the directory construction path `build_turn_state_and_directory` (`uri_core/core/decision_engine.py:1047-1058`) does not use. Today's per-user isolation comes from the per-user orchestrator cached in `_user_contexts` (`uri_core/app/server.py:339,640-642`).

This is a **pre-existing** gap, not one M33.2 introduces. Because the migration plan's Batch C stop condition depends on caller-scoped shortlisting, a caller-scoped feasibility seam is recorded as an explicit **Batch C prerequisite**.

### 5.3 Translation rules

Graphify and embeddings can influence orientation/ranking only. They cannot add a capability, make one available, infer a grant, or outrank a deterministic deny. The translator must reject an id/action absent from the offered shortlist, any duplicate/oversized argument shape, malformed output, and proposals with an unsupported contract version. It must preserve existing native `ToolCall` translation/canonical semantics rather than create an Edge dispatcher.

## 6. Deterministic routing state machine

`IntelligenceRoutingDecision` is an auditable enum plus machine-readable reasons. It evaluates, in this order: request class/explicit user choice; `intelligence_mode`; URI_PREFLIGHT fast-path eligibility; input or transcript confidence; runtime/model availability and resource budget; task complexity; offered capability risk/approval/permission state; calibration availability/version; and appropriate confidence.

| State | Deterministic condition and result |
|---|---|
| `SUPPRESS` | Do not call Edge: a URI_PREFLIGHT result exists, Edge disabled/unavailable/ineligible, explicit Main request, or mode policy says bypass. Continue URI_PREFLIGHT or the selected Main Brain; record reason. |
| `CONFIRM` | Ambiguous/low-quality input, sensitive action, critical field uncertainty, or policy requires confirmation. Ask a bounded clarification whose wording is model-authored per §3.1; no execution follows from confirmation alone. |
| `EDGE_REPLY` | A low-risk, bounded direct answer has valid output, current calibration, and calibrated reply confidence at or above the user's threshold. Return it with no authority claim. |
| `EXECUTE_PROPOSAL` | Edge proposed an offered capability/action and schema-valid bounded args. Send it through the §2.1 contract-injection seam into existing canonical validation/gates; the gate may deny or create approval rather than execute. |
| `ESCALATE` | Complexity, uncertainty, stale/missing calibration, unsupported modality/schema, insufficient evidence, or an ineligible/failed proposal requires the Main Brain. If no healthy Main Brain exists, return an explicit limitation/clarification per §3.1 — not a fabricated Edge completion. |

For sensitive voice actions, low transcript confidence wins over high action confidence: `CONFIRM` or deny/escalate according to existing policy. `99%` only changes an intelligence-routing decision; it never bypasses the later gate.

**Threshold comparison semantics** *[review 2026-09-20 — previously undefined while boundary tests were already promised]*: the stored threshold is an integer percent and the calibrated score is a float in `0..1`. The single comparison used everywhere is:

```text
eligible_for_EDGE_REPLY  ==  round(calibrated * 100) >= reply_confidence_threshold_percent
```

Rounding is half-up on the percent value, the comparison is inclusive, and no other rounding or scaling is performed anywhere in the routing path.

**Relationship to Parallel Edge Assistance** *[added 2026-09-20]*: this table is unchanged by §2.2. `ESCALATE` and an explicit Main-Brain request both mean "the Main Brain answers"; §2.2 governs only whether qualified, benchmark-proven Edge assistance additionally prepares context for that Main-Brain call. Assistance is never itself a sixth routing state and never substitutes for `EDGE_REPLY` or `EXECUTE_PROPOSAL`.

## 7. Persistent settings and ownership

`EdgeSettingsStore(user_id)` persists versioned `edge_intelligence.json` under existing `user_scoped_path` (`uri_core/core/portable_paths.py:47`, which rejects any non-UUID `user_id` rather than building a path). It follows the atomic tmp-plus-`os.replace` write pattern already used by `ProviderConfigStore` (`uri_core/core/provider_registry.py:263-269`) and exposes no credential material.

```json
{
  "schema_version": "1.0",
  "revision": 1,
  "updated_at": "RFC3339",
  "enabled": true,
  "intelligence_mode": "HYBRID",
  "reply_confidence_threshold_percent": 90,
  "edge": {"runtime_id": "candidate", "model_id": "candidate"},
  "vision": {"provider_id": null, "model_id": null, "enabled": false},
  "speech": {"provider_id": null, "model_id": null, "enabled": false},
  "assistance": {"enabled": false, "default_deadline_ms": 800}
}
```

*[review 2026-09-20 — the earlier schema carried both a top-level `enabled` and an `edge.enabled`, with no precedence rule.]* There is now exactly **one** Edge text-intelligence switch: the top-level `enabled`. `edge` carries selection only. `vision.enabled` and `speech.enabled` remain separate modality switches, and each is additionally subordinate to the top-level `enabled`: when `enabled` is false, no Edge modality runs.

**`assistance` field, added 2026-09-20** — strictly additive, does not change the precedence rule above: `assistance.enabled` is subordinate to the top-level `enabled` exactly like `vision`/`speech` (no Edge assistance runs when Edge itself is disabled), and it also requires the specific assistance route to have passed the Batch B benchmark comparison (§2.2) — a user cannot enable an unqualified route. `default_deadline_ms` is the fallback assistance deadline (§2.2) when a qualified route does not declare its own.

The threshold is an integer `0..100`, defaults to the conservative product baseline of `90`, and is read on every routing decision (no restart/cache delay). The model has no settings-write method. Runtime/model availability, artifact permissions, resource ceilings, local-only/network policy, and deployment disablement live in a separate deployment-owned `EdgeRuntimeInventory`/policy; effective routing is the intersection of user preference and deployment eligibility.

**Concurrency** *[review 2026-09-20]*: `revision` and the `409` conflict response have no precedent in this repository — `ProviderConfigStore.load()`/`save()` is a lock-free read-modify-write (`uri_core/core/provider_registry.py:253-269`), and no `revision` field exists anywhere in `uri_core/`. A bare read-compare-write would lose the revision check through its own TOCTOU window. The revision check, the mutation, and the atomic write must therefore occur inside **one** lock, following existing in-repo lock precedents (`uri_core/core/usage_meter.py:16`, `uri_core/app/server.py:3210`, `uri_core/core/capability_resolver.py:55`).

**Cross-device sync is reserved, not implemented in M33.2** *[review 2026-09-20]*: an earlier draft specified `source_device_id` plus `revision`/`updated_at` optimistic-concurrency sync with client reload/merge. No sync transport is in M33.2's scope, and no merge rule for a flat scalar document was ever defined. `revision` and `updated_at` are retained because the single-node `409` path needs them; `source_device_id` is removed until a milestone actually owns sync. Runtime inventory, measurements, artifacts, credentials, grants, and audit records are not user preferences and will not sync as such.

## 8. Control-panel backend contract (for M33.3, not its UI)

Authenticated, caller-scoped endpoints are proposed:

```text
GET  /intelligence/settings
PUT  /intelligence/settings        # full validated preference, revision required
GET  /intelligence/status          # effective selected/available runtime/model; no secrets
GET  /intelligence/routing/latest  # bounded last routing summary for caller/session
GET  /intelligence/trace           # paged, redacted, caller-scoped trace projection
```

No `/intelligence/*` route exists today, so the namespace is free. Every one of these endpoints takes the authenticated principal dependency and is caller-scoped. *[review 2026-09-20]* The existing `GET /audit/shadow-comparison` (`uri_core/app/server.py:2225-2244`) is explicitly **not** the template: it takes no principal dependency and reads process-global state.

`GET /intelligence/settings` returns saved preferences plus `effective` state and valid mode values. `PUT` returns `409` on revision conflict, `422` for invalid ids/modes/threshold, and cannot set deployment constraints. `status` distinguishes `not_configured`, `unavailable`, `missing_artifact`, `loading`, `ready`, `resource_limited`, `disabled_by_policy`, and `error`; it never reports an optimistic connected/ready state.

**Status durability** *[review 2026-09-20]*: if Edge health mirrors `ProviderHealthTracker`, that state is in-memory, per-process, keyed `(provider_id, model)`, on a 60-second cooldown, and explicitly never persisted (`uri_core/core/model_router.py:38,51-63`). After a restart, `status` must report `not_configured` or `unavailable` and re-derive from a real check; it must never report a remembered `ready`.

`routing/latest` has exactly: Edge/Main provider/model identifiers when called, raw/calibrated confidence with availability/semantics, threshold, decision state, bounded reason codes, shortlist size, proposed/selected capability id, main-brain-called boolean, latency measurements, and result/evidence status. The same DTO is the M33.3 control-panel contract; M33.2 provides it without creating the M33.3 UI.

## 9. Calibration and observability

### 9.1 Calibration

Raw vendor confidence is untrusted metadata. `CalibrationProfile` is deployment-owned, immutable/versioned, and keyed at minimum by provider/runtime/model-artifact hash, quantization/preprocessing, operation kind, prompt/schema version, OS/device/backend and dataset split. A profile contains a documented mapping or explicitly `UNAVAILABLE`; it is never trained online from a single user's traffic.

M33.2 starts with **one global per-user manual reply threshold**, not adaptive thresholds. It records enough outcome types to decide later whether calibrated profiles must diverge for direct replies, intent classification, capability selection, argument extraction, structured extraction, and voice interpretation. A profile can initially fall back to a documented global calibration mapping, but a stale/missing/mismatched profile makes direct Edge reply ineligible.

Event outcomes may be labelled by a frozen benchmark, deterministic schema/argument validation, execution/evidence result, or explicit user correction. Main-Brain agreement alone is not truth. Later fitting uses held-out data, reliability diagrams, ECE/max error/NLL and task-quality measures; it does not change any user's threshold automatically.

Note that raw confidence can be legitimately absent: Needle documents confidence as a calibrated-head/decode-probability minimum and returns `None` for fine-tuned weights whose calibration head was not updated (`reports/Edge runtime evaluation.md:7`). `UNAVAILABLE` is an expected value, not an error.

### 9.2 Trace contract

Append-only, best-effort `EdgeRoutingTraceEvent`. It stores no raw prompt, attachment/audio/image content, credential, unbounded model rationale, or private chain-of-thought.

*[review 2026-09-20 — precedent correction.]* Two different existing patterns were previously conflated under a single citation:

- `record_shadow_trace` (`uri_core/core/decision_engine.py:1006-1019`) is the precedent for **best-effort, never-raising** append. It is **not** a precedent for isolation or retention: it writes to a process-global, unrotated, unbounded `uri_workspace/decision_engine_shadow_log.jsonl` (`:933`).
- `UsageMeter.record` (`uri_core/core/usage_meter.py:96-109`) is the precedent for **caller-scoped, month-partitioned, lock-guarded** append via `usage_path(user_id, "%Y-%m")` under `_locked_append` (`:16`), and for logging failures that never leak exception text.

The Edge trace follows `UsageMeter` for storage layout and isolation, and `record_shadow_trace` for failure isolation. **Retention:** trace files are partitioned per user per month and pruned after a declared retention window; the window is a deployment setting with a conservative default, and pruning is covered by test. `GET /intelligence/trace` pages within the caller's own partitions only.

```json
{
  "event": "edge_routing",
  "timestamp": "RFC3339",
  "user_id": "implicit by scoped storage; never exposed cross-user",
  "session_id": "optional",
  "request_length_bucket": "21-80",
  "intelligence_layer": "EDGE",
  "decision": "EXECUTE_PROPOSAL",
  "reason_codes": ["shortlist_ready"],
  "untrusted_content_present": true,
  "edge": {"provider_id": "…", "runtime_id": "…", "model_id": "…"},
  "confidence": {"raw": 0.91, "raw_semantics": "declared", "calibrated": 0.84, "profile_version": "…"},
  "threshold_percent": 90,
  "shortlist_size": 8,
  "capability_id": "optional registered id",
  "main_brain": {"called": false, "provider_id": null, "model_id": null},
  "latency_ms": {"edge": 0, "main": null, "total": 0},
  "resource": {"rss_bytes": null, "cpu_ms": null, "battery": "UNAVAILABLE"},
  "outcome": "proposal_validated|escalated|denied|executed|error",
  "evidence_result": "none|created|unavailable"
}
```

`request_length_bucket` reuses `_bucket_length` (`uri_core/core/decision_engine.py:936-947`) unchanged. The field is `intelligence_layer`, never `tier` — see §2.

*[review 2026-09-20 — forward-reference correction.]* An earlier draft required this trace to "align naming/retention/redaction with the future M35 Runtime Trace". A repository-wide search finds the phrase "Runtime Trace" **only in M33.2's own documents**; M35's actual reservation (`docs/governance/URI_ACTIVE_MILESTONE.md` §1c, M35) contains no such item. This DTO is therefore offered as the contract a future companion or trace consumer **may** adopt. It is not evidence of an M35 commitment and must not be a closure gate for M33.2.

**Assistance and progress facts in the trace, added 2026-09-20** — additive only, the schema above is unchanged: an `EdgeAssistanceResult` (§2.2) may optionally be summarized into this same trace event as `assistance: {"kind": ..., "status": ..., "latency_ms": ..., "deadline_ms": ...}`, following the identical redaction rule — no raw content, no rationale. The truthful runtime progress facts §2.2 permits for a future UI/Companion consumer are projections of these same fields (`decision`, `outcome`, `assistance.status`, `latency_ms`); nothing new is computed or invented for display purposes.

## 10. Modal siblings and resource governor

### Vision and reconstruction direction

`EdgeVisionProvider` returns observations with source reference, optional geometry, confidence/semantics, model/artifact, and uncertainty — not facts, permissions, or graph writes. Tiering of visual work is: deterministic OCR/barcode/metadata; lightweight classifier/detector; small local VLM; Main-Brain multimodal. Existing `PDFReader` (`uri_core/services/pdf_reader.py:9`) text/OCR is reused at the URI_PREFLIGHT layer but does not currently preserve layout geometry.

Future document reconstruction is deliberately staged: image/PDF → OCR/layout observations → structured extraction proposals → deterministic document engine → editable DOCX. Heading, table, alignment, section, signature-region geometry and critical uncertainty must survive as evidence/observation metadata. M33.2 creates contracts and benchmark fixtures only, not the reconstruction engine.

### Voice

`EdgeSpeechProvider.transcribe()` returns a transcript, segment/timestamp data where supported, transcript confidence or `UNAVAILABLE`, provenance and errors. A distinct Edge interpretation/tool proposal receives that transcript. URI separately logs transcript and action confidence; transcript uncertainty controls confirmation/blocking for sensitive actions. Routine voice operation with no Main Brain is an eventual acceptance case only after ASR, intent, capability and authority tests pass.

### Structured extraction

`EdgeExtractionProposal` has a requested schema version, field values, field-level confidence where available, source/evidence pointers, and critical-field uncertainty. Typical fields include document type, reference number, date, authority, subject, decision, deadline and action item. It is schema-validated, becomes an evidence/knowledge *candidate*, and never directly writes Graphify or a current fact.

### Resource Governor

`EdgeResourceGovernor` receives runtime-declared, measured capability and deployment budget; it returns `admit`, `queue`, `unload_then_admit`, `defer`, or `reject` with reason. States are `UNAVAILABLE`, `NOT_LOADED`, `LOADING`, `RESIDENT`, `ON_DEMAND`, `SUSPENDED`, `UNLOADING`, and `FAILED`.

Text models may be resident; vision/VLM models normally load on demand; inactive heavier leases may sleep/unload. Budgets cover declared/observed RAM, CPU/GPU where observable, timeout/cancellation, disk/cache, foreground priority and mobile battery/thermal signals. URI must not claim OS priority, NPU/GPU acceleration, thermal visibility, background survival, or battery controls where a runtime/platform cannot demonstrate them. Unknown telemetry yields conservative admission or Main-Brain escalation, never an invented resource reserve.

**Process, worker and multi-user scope** *[review 2026-09-20 — previously unstated, which left an N-users-times-N-leases hazard implicit]*: the runtime lease pool and the governor's budget are scoped to **one shared, thread-safe pool per server process**. They are explicitly **not** per-user and must not be attached to a `_user_contexts` entry (`uri_core/app/server.py:339`), which caches one orchestrator per user for the process lifetime and is never evicted. Server endpoints are synchronous `def` handlers, so FastAPI runs them on a threadpool and concurrent admission is real. The launcher currently starts a single worker (`scripts/run_uri_server.py:196-203`), but the governor must state its per-process budget explicitly so a future multi-worker deployment multiplies budgets knowingly rather than accidentally.

## 11. Failure behavior

| Failure | Required deterministic behavior |
|---|---|
| Runtime/model/artifact unavailable or not loaded | Mark truthful status; no retry storm; quick `SUPPRESS`/`ESCALATE`, or an Edge-only limitation per §3.1. |
| Timeout/resource exhaustion/cancellation | Cancel/retire lease when supported; record bounded error; do not reuse partial proposal; escalate only if policy/time permits. |
| Malformed/unknown-schema output | Reject proposal; trace `invalid_output`; do not execute or reinterpret it. |
| Raw confidence unavailable or calibration stale/mismatched | Never `EDGE_REPLY`; use `ESCALATE`, `CONFIRM`, or an Edge-only limitation. |
| Capability/model mismatch | Do not offer the capability; safe `ESCALATE`/unsupported response. |
| Shortlist unavailable (`preselect_candidate_ids` returns `None`) | Ineligible: `SUPPRESS`/`ESCALATE`. Never fall back to the full catalogue (§5.1). |
| Main Brain absent, quota exhausted, network failure, slow or timeout | Explicit `main_unavailable` state. Edge may handle only independently eligible bounded work; complex work produces limitation/clarification, not a weak forced answer. |
| Vision/speech unavailable | Continue supported text/URI_PREFLIGHT behavior; report modality unavailable. |
| Version/model mismatch or telemetry/egress violation | Quarantine candidate/profile; disable it for that effective route; preserve audit/benchmark evidence. |

## 12. Compatibility and performance invariants

- Preserve `ModelRouter`, provider factory, `ProviderConfigStore`, existing Main Brain adapters, native model tool loop, and `/ask/stream`. Explicit Main-Brain use retains provider-native tools, iteration and streaming.
- Reuse canonical proposal translation, `CapabilityDirectory`, resolver, gates, approvals, dispatcher, evidence and audit. No Edge executor, authority store, capability registry, or Graphify truth store.
- URI_PREFLIGHT bypasses model calls; explicit Main/complex paths bypass unnecessary Edge; Edge-unavailable detection is fast; there is no mandatory serial Edge-plus-Main inference. An Edge proposal may trigger a traceable escalation, while a separately qualified assistance route may run only in parallel with, or within its declared pre-dispatch deadline before, the Main-Brain call.
- **Shared per-turn projection, corrected** *[review 2026-09-20]*: an earlier draft required "a shortlist/context projection is built once per request and reused". That is not achievable as stated, because the two layers need different projections — the native Main-Brain path deliberately offers the **full** catalogue, iterating every `directory.summaries()` entry in `build_tool_schemas` (`uri_core/core/tool_schema.py:214-226`), while Edge requires a bounded 5–20 shortlist (§5). What is genuinely shared once per turn is the `build_turn_state_and_directory` result (`uri_core/core/decision_engine.py:1029`), already established as the de-duplication point by M32 D2 (`uri_core/core/native_tool_loop.py:440-447`). The Edge shortlist and the Main-Brain tool catalogue are two distinct projections derived from that one shared result.
- Maintain current user scoping in paths/endpoints and current model-provider credential isolation. Edge settings/telemetry contain no credentials and cannot grant access.
- **Parallel Edge Assistance reuses the same shared result** *[added 2026-09-20]*: §2.2's assistance work is built from the same shared `build_turn_state_and_directory` result described above, not a third projection. Because assistance runs in parallel with or ahead of Main-Brain dispatch rather than serially before it, it must never add a synchronous wait on the Main-Brain critical path — see §2.2's deadline rule.

## 13. Non-goals and unresolved decisions

**Excluded:** M33.3 UI redesign; Knowledge Fabric/Sources/Watches; Companion personality/animation; full reconstruction/DOCX engine; autonomous execution; model-controlled settings/permissions/credentials; adaptive thresholds; Needle/Cactus lock-in; runtime installation; OS-permission changes; cross-device settings sync; unrelated integrations.

**Need independent review, not a user decision yet:** whether `EDGE_ONLY` ships enabled by default; exact initial fixture corpus/data-retention period; first eligible Windows and Android candidates; local-only process-level egress enforcement mechanism; and whether a future companion/trace consumer adopts this trace DTO unchanged or versions it. None justifies implementation before benchmark evidence.

**Consequence the `EDGE_ONLY`-default decision must be made with** *[review 2026-09-20]*: the default `reply_confidence_threshold_percent` of `90` (§7), combined with "a stale/missing/mismatched profile makes direct Edge reply ineligible" (§9.1) and the absence of any calibration profile at first ship, makes `EDGE_REPLY` **structurally unreachable at launch**. If `EDGE_ONLY` also ships enabled by default, those users receive limitation or clarification responses for everything that is not a valid tool proposal. That may be the right conservative choice, but it must be chosen deliberately rather than discovered in use.
