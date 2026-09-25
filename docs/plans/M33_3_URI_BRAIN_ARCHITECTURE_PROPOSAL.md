# M33.3 — URI Brain Architecture Proposal (Plan B)

**Status:** `PROPOSAL_REVISED_R1_AWAITING_INDEPENDENT_CROSS_PLAN_REAUDIT`. Planning and review only. Not accepted, not frozen. Implementation is **NOT authorized**.
**Canonical identity:** `M33_3_PLAN_URI_BRAIN_ARCHITECTURE` (registered in `docs/governance/URI_STATE.yaml` → `planning_artifacts`).
**Sibling plan:** `docs/plans/M33_3_ARN_ARCHITECTURE_AND_LT1B_RENDERER_PLAN.md` (Plan A, identity `URI-REFERENCE-CLARIFICATION`).
**Cross-plan audit:** `docs/plans/M33_3_CROSS_PLAN_AUDIT_REPORT.md`, verdict `COMPATIBLE_WITH_BOUNDED_REPAIRS`.
**Cross-plan state and User decisions D1–D4:** `docs/plans/M33_3_CROSS_PLAN_STATE.md`.

## Provenance

| Item | Value |
|---|---|
| Original author | Codex (CLI), in a User architecture-interview session |
| Recovered from | `C:\Users\cheta\.codex\sessions\2026\09\26\rollout-2026-09-26T03-31-00-01a0da96-071c-72f0-8562-0f71ac9457db.jsonl`: the final assistant message, timestamp `2026-09-25T22:51:31.958Z` (2026-09-26 04:21 IST) |
| Original length | 24,463 characters |
| SHA-256 of the original message text (UTF-8, LF) | `cf08a0892a8b87508b771edb3a856da652ef19f57ffdc7fb66245108962b8a9b` |
| Uniqueness check | A scan of every Codex rollout dated 2026-09 found exactly one assistant message titled "URI Brain Architecture". No later revision exists. |
| Relation to audit | This is the exact text cross-audited on 2026-09-26 (audit report §0) |
| Brought into the repository | 2026-09-26, by the G0 + cross-plan repair pass (Claude). This is repair B-R8. |
| Revisions | R0 = the original, preserved verbatim below. R1 = the repair revision in this header. |

Section R0 is byte-for-byte the recovered message text. It was not edited. Its links point to absolute local paths as written by the author. Where R0 conflicts with R1, **R1 wins**. R0 stays as auditable history.

Labels: **[USER]** User requirement or decision · **[EVIDENCE]** repository evidence · **[HYPOTHESIS]** · **[EXPERIMENT]** needs an experiment before it becomes architecture.

---

## REVISION R1 — Cross-plan repairs B-R1 … B-R9 and User decisions D1–D4 (2026-09-26)

### R1.0 User decisions applied here (authoritative; full text in the cross-plan state file)
- **D1** [USER]: `gmail_create_draft` has `wrong_binding_impact = RECOVERABLE`. An unsent draft can be corrected before any external communication occurs. The classification is independent of `EffectType`, `ApprovalRequirement`, and `RiskLevel`. A future real send action is expected to be `CONSEQUENTIAL`. `wrong_binding_impact` is never derived mechanically from `EffectType`.
- **D2** [USER]: keep `EDGE_ONLY`, `HYBRID`, and `MAIN_BRAIN_PREFERRED`. See R1.2.
- **D3** [USER]: qualified Edge or Capable models may investigate, interpret clues, compare grounded candidates, narrow, annotate, and return structured evidence. They may not create binding authority. Model preference alone never creates a `TENTATIVE` binding. The required flow is: model interpretation/investigation → structured grounded evidence → deterministic resolution/eligibility check → `TENTATIVE` / `CONFIRMED` / `CLARIFY`. A model never invents candidate IDs.
- **D4** [USER]: **DEFERRED** to URI-Memory. Durable cross-session learned reference evidence and durable learned tie-breaking are not authorized now, and no ad-hoc durable reference-memory subsystem may be built. Allowed now: session-authoritative selections, session-local reference evidence, structured Change/correction events, and rank/display effects from valid session evidence.

### R1.1 (B-R1) Evidence baseline additions: A2.8H / A2.8I research detectors
§2 and §17 of R0 cite only the D0 non-oracle path (0/84). The later research detectors add the following.

[EVIDENCE] Sources: `docs/plans/M35_URIV1_A2_8H_EXECUTION_REPORT.md` §0, §4; independently re-verified in `docs/plans/M35_URIV1_A2_8I_POST_REPAIR_END_TO_END_RESIDUAL_AUDIT.md` §3. Both files are untracked in git; SHA-256 values are recorded in the cross-plan state file.

| Path (79-case natural-boundary raw-turn corpus, n = 84 references) | Detection recall (C1) | Resolution coverage C1 | Resolution coverage C2 | Incorrect confident bindings |
|---|---|---|---|---|
| D0 (production-shaped TurnFrame detection) | 15.5% | 0/84 | 0/84 | 0 |
| D1 (research detector) | 67.9% | 14.3% | 8.3% | 1 |
| D1R (research detector) | 75/84 = 89.3% | 16/84 = 19.0% | 10.7% | 1 |
| D1RQ (D1R plus deterministic query-construction repair) | 89.3% | 22/84 = 26.2% | 13/84 = 15.5% | 1 at C1, 1 at C2, unchanged |

- A2.8I corrected the identity of the C2 incorrect binding to `NB-B-05:r1`, not `NB-H-06` as A2.8H stated.
- `INVENTED_CANDIDATE` = 0 and boundary violations = 0 in all cells.
- D1/D1R/D1RQ are **research detectors** (`scripts/m35_a2_8*_detector_*.py`, untracked). They are not production, not qualified for production, and not wired anywhere.
- The first experiment (§15–16, stage 1) adds **D1R and D1RQ as comparison arms** beside the current non-oracle path. No coverage gain counts as safe without error analysis of the persisting incorrect confident binding.

### R1.2 (B-R2) Canonical mode mapping [USER D2]
There are three independent dimensions. None replaces another:
- **Policy:** `intelligence_mode` ∈ {`EDGE_ONLY`, `HYBRID`, `MAIN_BRAIN_PREFERRED`} (M33.2 §3).
- **Model choice:** AUTO, or an explicitly selected model.
- **Edge availability:** Edge ON / OFF (`EdgeSettings.enabled`, after preflight).

| Combination | Behavior |
|---|---|
| AUTO + `HYBRID` | Efficiency-first. Deterministic mechanisms run first. A qualified Edge may do substantive bounded work. The Capable Brain is used when Edge is not qualified or not sufficient. |
| AUTO + `MAIN_BRAIN_PREFERRED` | Capability-first. Deterministic mechanisms still run. Substantive model work normally goes directly to the Capable Brain. A qualified Edge may do **supporting** work only. |
| Explicit model selected (any mode except the `EDGE_ONLY` limit below) | The selected model **is** the Capable Brain for substantive model work. Deterministic URI mechanisms stay active. Qualified supporting Edge work stays permitted. The model's native capabilities (reasoning, iterative/parallel tools, structured output, multimodality, agentic continuation) are preserved. Edge never replaces or downgrades the selected model's substantive role. |
| Edge OFF | Removes Edge inference only. Deterministic mechanisms stay active. The Capable Brain stays available unless another explicit policy forbids it. |
| `EDGE_ONLY` | Deterministic mechanisms plus qualified Edge only. The Capable Brain is **never** called silently. A task beyond that envelope surfaces the limitation or the escalation requirement instead of violating the mode. |

- `HYBRID` and `MAIN_BRAIN_PREFERRED` are distinct and must not be merged.
- R0 §7 proposed a "local-only / Auto / selected-provider" control needing "a versioned mapping". That proposal is **superseded** by this table. A network/local-only restriction, if later wanted, is a separate policy dimension and needs its own decision.
- **Required governance amendment:** `M33.2 AMENDMENT G2 (2026-09-26)` in `docs/architecture/M33_2_EDGE_SECOND_BRAIN_CANONICAL_ARCHITECTURE.md` §3 and §6. It narrows `SUPPRESS` on explicit selection to substantive work and states that Edge OFF and explicit selection are independent.
- **Unified router [canonical boundary]:** one routing authority, the M33.2 `routing_policy` extended, owns Edge eligibility, Edge OFF, explicit selection, warmth/resource state, and Capable escalation. Plan A's clarification-wording policy consults this router. It is not a second router.

### R1.3 (B-R3) Learning boundaries
- Route preference is **not** model calibration. It never changes an M33.2 §9.1 `CalibrationProfile` (the cross-plan audit called this section "§8"; the section number in the architecture document is §9.1), a reply-confidence threshold, or a qualification threshold (M33.2 amendment G3).
- Route-performance and response-evaluation storage is a new, separate, per-user store. It is **not** ExperienceStore. ExperienceStore keeps its existing role (Brain-approved experience summaries for query context, `uri_core/core/experience_store.py`) and is not repurposed for route learning or reference memory.
- Route learning cannot qualify an unqualified path, re-qualify a failed route, or expand an unqualified role. It changes **preference among already-qualified, eligible routes only**. Qualification sets eligibility; learning sets preference.
- Plan A "Change" taps and 👍 / 👎 / ✎ feedback feed **one** structured evaluation event stream, attached to the response/operation trace. A Change on a tentatively bound reference is recorded as an evaluation event with category `wrong_reference` and structured fields (the prior and new candidate IDs, ambiguity ID, trace ID). It is not a separate channel. Event schema: [EXPERIMENT] (R0 §12 categories are not frozen). The trace needs a `trace_id` on responses, which is new work.

### R1.4 (B-R4) Consequence and TENTATIVE criteria
- R0 §8 "action consequences" and "sufficiently supported candidate" are replaced with the canonical terms below.
- The canonical field is **`wrong_binding_impact`** ∈ {`NONE`, `RECOVERABLE`, `CONSEQUENTIAL`}:
  - It lives on the production `Action` contract (`uri_core/capabilities/base.py`), beside the existing `effect_type`, `approval_requirement`, and `risk`.
  - Undeclared means `CONSEQUENTIAL` (fail closed).
  - The execution gate is the consumer. **If binding = `TENTATIVE` and `wrong_binding_impact` = `CONSEQUENTIAL`, block execution and require confirmation.**
  - Approval stays a separate gate.
  - Granularity is the action-level maximum; per-parameter impact is deferred.
  - Future contract only. **Not implemented by this revision.**
- The TENTATIVE criteria adopt Plan A R2 (as amended by D1 and D3):
  - exactly one candidate must be strongly preferred by **deterministic** evidence (RAR driver-rule separation, or valid session evidence);
  - the action's `wrong_binding_impact` must be `NONE` or `RECOVERABLE`;
  - the chosen object is shown with an easy Change;
  - two or more equally plausible candidates always produce a clickable question;
  - model output may contribute only structured grounded evidence that the deterministic check evaluates (D3);
  - learned cross-session evidence does not contribute (D4, deferred).

### R1.5 (B-R5) Graphify scope
- [EVIDENCE] `uri_core/core/graphify_index.py` records only kinds `capability`, `skill`, `workflow`, `memory_pointer`, and `connected_service`. It does not index documents, files, or emails.
- Graphify is a hint/pointer mechanism within that scope and is never proof.
- R0 §2/§3/§8 references to "Graphify" as a grounding source for documents are corrected. Documents and emails are grounded through authorized retrieval capabilities (for example `gmail_search`, `drive_search`, `read_attached_file`, the user `file_store`), session/turn state, and attachments.

### R1.6 (B-R6) Lifecycle and residency facts
- [EVIDENCE] `uri_core/core/edge/contracts.py`: `RuntimeLease` has only `lease_id` and `runtime_id`. **There is no owner field.**
- [EVIDENCE] M33.2 §10's `EdgeResourceGovernor` and lifecycle states cover **Edge runtimes only**. No accepted contract manages Capable Brain (LM Studio / Ollama Main Brain) residency or leases.
- The following are **new work, not existing functionality**:
  - lease-ownership provenance ("URI owns its leases, not the whole runtime");
  - Capable Brain residency and leases;
  - cooperation with externally owned models.
- They extend the M33.2 governor and must not duplicate it.
- Residency thresholds remain [EXPERIMENT] (the stage 3 residency study).

### R1.7 (B-R7) One canonical grounding output
- The output of R0 §3's "Ground only the context this task needs" stage is defined as **the `RARQuery` candidate set** (candidates with IDs, types, provenance locators, and deterministic anchors), per `uri_v1/turn/rar_contracts.py` `RARQuery` / `RARCandidate` / `RARDeterministicAnchor`.
- There is **one** source-to-candidate producer. `context_builder` / `query_context`, `CapabilityContextResolver`, and `uri_v1` TurnFrame / `active_context` are inputs to it or predecessors of it, not competing owners.
- Plan A consumes only this output.
- The producer is **not implemented** by this revision. Its feasibility is what the stage 1 experiment measures.
- Coexistence or retirement of production `CapabilityContextResolver` (first-match) is an open design item for the integration slice.

### R1.8 (B-R8) Repository governance
- This file is the durable, governed artifact for Plan B.
- It is registered in `URI_STATE.yaml` → `planning_artifacts` as `M33_3_PLAN_URI_BRAIN_ARCHITECTURE`, status planning/review only.
- R0 §18's statement "I made no repository changes" is true of R0's authoring; this repository copy was added later by the G0 pass.

### R1.9 (B-R9) Production wiring status
- [EVIDENCE] `uri_core/core/edge/routing_policy.py` (`evaluate_routing`, `IntelligenceRoutingDecision`) is referenced only inside `uri_core/core/edge/`. No production path (`uri_core/app/server.py`, `orchestrator.py`, `native_tool_loop.py`) imports it.
- **The M33.2 Edge routing policy is not wired into production.** Production `/ask` has no Edge route. Needle 3's role qualification (M33.2 B4) is not a live route.

### R1.10 Canonical responsibility boundaries (converged with Plan A R2)
| Owner | Owns |
|---|---|
| Deterministic mechanisms | candidate identity; candidate IDs; binding eligibility; binding state; deterministic ranking/order where defined; validators; approval and execution gates |
| Model roles (Edge / Capable) | clue interpretation; bounded investigation; candidate annotation; synthesis; wording where qualification and policy permit; substantive work per routing mode |
| Graphify | hint/pointer within proven scope; never proof |
| Qualification | eligibility |
| Learning | preference among eligible routes only |
| ExperienceStore | existing role only |
| URI-Memory (`NOT_STARTED`) | future owner of durable, decaying, invalidatable reference evidence |
| Unified router | the single routing authority (R1.2) |

### R1.11 Superseded R0 statements (search index for re-audit)
- R0 §7: "proposed local-only / Auto / selected-provider product control needs a versioned mapping" → superseded by R1.2.
- R0 §8: "act on a sufficiently supported candidate" → superseded by R1.4.
- R0 §8: "I recommend the bounded deterministic exception" → realized as M33.2 amendment G1 (an explicit amendment, not an exception).
- R0 §2/§3/§8: Graphify as a candidate source → corrected by R1.5.
- R0 §9–10: "Separate a provider/model registry from leases" → clarified by R1.6 (new work; `RuntimeLease` has no owner).
- R0 §11–12: route learning → bounded by R1.3.
- R0 §2 and §17 evidence rows → supplemented by R1.1.
- R0 §6 "Retrieval interpretation / ranking" role and R0 §8 "Model-assisted comparison" → bounded by D3. Models return annotations, eliminations, or evidence only. The deterministic layer owns ranking order, candidate identity, and binding state.

### R1.12 Status
`BRAIN_ARCHITECTURE_STATUS`: `PROPOSAL_REVISED_R1_AWAITING_INDEPENDENT_CROSS_PLAN_REAUDIT`.
- The first experiment (stage 1 source-to-candidate replay) still needs its own separately scoped, pre-audited plan and authorization.
- No experiment, implementation, freeze, or INT event is authorized.

---

## R0 — Original proposal, verbatim (2026-09-25T22:51:31.958Z, Codex)

# URI Brain Architecture — evidence-grounded proposal for review

**Status: READY_FOR_EXPERIMENT.** Your latest answers resolve the remaining product decisions that would change the topology. This is a proposed design and research sequence, not a frozen architecture or authorization to run it. I made no repository changes and ran no experiments.

## 1. Repository baseline

The live backend is `uri_core/`; `uri_v1/` is a parallel research line with no production import path. M33.2 established the Edge architecture and narrowly qualified one Needle 3 role. M33.3 Batch A is frozen as *qualification methodology* only: it qualified no new Edge candidate, authorized no Stage B integration, and created no integration event. ARN.1’s deterministic narrowing core is verified; later ARN work is not authorized. The [current-state record](C:/Users/cheta/Development/Uri/_V1/docs/governance/URI_STATE.yaml) takes precedence over older milestone prose where they differ.

The current worktree contains extensive pre-existing uncommitted research and documentation. I have treated it as evidence where relevant, not as accepted production architecture.

## 2. Evidence matrix

“Qualified” below always means **for the stated role and conditions**, never for a whole model or all URI tasks.

| Component or claim | Status and measured evidence | Depend on it now? |
|---|---|---|
| Runtime authority and native tool loop | Live `uri_core` path. Models propose; runtime validates, authorizes, executes, and reports results. | Yes, as the governing boundary. [Contract](C:/Users/cheta/Development/Uri/_V1/URI_Model_Centric_Architecture_Docs/URI_MODEL_RUNTIME_CONTRACT.md) |
| ARN.1 deterministic narrowing after `NOT_FOUND` | Verified production component. It records task-local successful routes and distinguishes candidate evidence. | Yes within its current scope; it is not a general ambiguity solver. [Completion](C:/Users/cheta/Development/Uri/_V1/docs/plans/ARN_1_COMPLETION_REPORT.md) |
| Graphify hints | Live pointer mechanism; about 1.156 ms lookup on a 71-record activation set. Larger-scale behavior is **UNMEASURED**. | As a discovery hint, never as proof that a document or reference is correct. [State](C:/Users/cheta/Development/Uri/_V1/docs/plans/M34_GRAPHIFY_HINT_ACTIVATION_STATE.md) |
| Needle 3 reflex routing and structured-record extraction | M33.2 role-qualified: 8/8 routing, 4/4 structured extraction; provider p50/p95 about 159/207 ms, peak RAM about 101 MB. Argument extraction was 2/4 and is unqualified. The route is not wired into the production `/ask` path. | Candidate for *that narrow role* when an integration is separately authorized. [B4 state](C:/Users/cheta/Development/Uri/_V1/docs/plans/M33_2_BATCH_B4_STATE.md) |
| Deterministic research RAR | 27/136 correctly covered a narrow, presegmented fixture subset. The whole raw turn was the reference in 0/136; the non-oracle path confidently resolved 0/84. A broader matching approach had six unsafe binds in 136. | No production coverage claim. The grounding/delivery seam must be repaired and retested. [A3 synthesis](C:/Users/cheta/Development/Uri/_V1/docs/plans/M35_URIV1_A3_ARCHITECTURE_SYNTHESIS_AND_NEXT_BATCH_PLAN.md) |
| Qwen3.5-9B | Stronger semantic reference in a 38-case battery, including 6/6 negation-ladder cases. This does **not** qualify it for every task or action. A separate 60-case run measured a 6.08 s cold load and 3,409/6,961 ms task p50/p95; host RAM reached 21.7 GB and system GPU memory about 7.32 GB. | A capable semantic comparator, subject to route and action qualification. Co-residency is **UNMEASURED**. [A3 synthesis](C:/Users/cheta/Development/Uri/_V1/docs/plans/M35_URIV1_A3_ARCHITECTURE_SYNTHESIS_AND_NEXT_BATCH_PLAN.md), [Batch A report](C:/Users/cheta/Development/Uri/_V1/docs/plans/M33_3_BATCH_A_COMPLETION_REPORT.md) |
| Tiny models as general Step-1 decoders | Needle 3 failed critical negation/reference cases in that role. Qwen3.5-0.8B had 0% strict reference success under its tested feed and mean 1.85 s. LFM2.5-350M and Qwen3.5-2B were faster in other feeds but missed critical semantics, including negation. | Rejected **for the tested broad decoder roles**; this does not reject a newly specified bounded role. [A3 synthesis](C:/Users/cheta/Development/Uri/_V1/docs/plans/M35_URIV1_A3_ARCHITECTURE_SYNTHESIS_AND_NEXT_BATCH_PLAN.md) |
| M33.3 Main-Brain avoidance | Independent re-audit verified **zero** avoided calls; 22 remain unverified. Its 78-row historical intermediate-text gap limits stronger claims. | No claimed Edge speedup or production qualification from this batch. [R4 audit](C:/Users/cheta/Development/Uri/_V1/docs/plans/M33_3_BATCH_A_R4_INDEPENDENT_REAUDIT_REPORT.md) |
| Edge drafting, clarification rendering, OCR, speech, vision, route learning, automatic preference adaptation | Product directions or research proposals; case-specific reliability and end-to-end cost are **UNMEASURED**. | No automatic production routing yet. |

## 3. Proposed topology

The hierarchy is a **set of eligible destinations, not a pipeline every request must traverse**:

```text
Request + user mode + selected model + authorized capabilities
                         │
             Deterministic preflight
       session, permissions, available routes,
          explicit IDs, risk, resource leases
                         │
        Ground only the context this task needs
       session / sources / RAR / ARN.1 / Graphify
                         │
          Qualification and route decision
          ├─ deterministic completion
          ├─ qualified Edge role or specialist
          ├─ local Capable Brain
          └─ authorized stronger/cloud Brain
                         │
       Model proposal or deterministic action
                         │
     Runtime validate → authorize/approve → execute
                         │
            Result → continuation if needed
                         │
        Response + optional evaluation signal
                         │
      Separate knowledge and route-learning stores
```

A known file ID can go directly from preflight to a validated open action. A complex Office Order draft can go directly to the selected Capable Brain with grounded sources. URI should not pay for semantic decoding, RAR, Edge inference, and Main inference in series unless each step has shown value for that task class.

## 4–5. Component responsibilities and the deterministic/AI boundary

The deterministic core owns identity, permissions, user mode, explicit selection, source provenance, candidate IDs, resource admission, action consequences, validation, confirmation, execution, persistence, and audit. It may complete bounded work whose correctness is established by rules and grounded data.

Models may interpret, reason, draft, choose among *offered* tools, and propose bindings. Their output remains an untrusted proposal. A model’s confidence cannot turn a candidate into a verified identity or expand action authority. This follows [ADR-018](C:/Users/cheta/Development/Uri/_V1/URI_Model_Centric_Architecture_Docs/URI_ADR_018_MODEL_CENTRIC_ARCHITECTURE.md) and the [operating policy](C:/Users/cheta/Development/Uri/_V1/URI_Model_Centric_Architecture_Docs/URI_AI_OPERATING_POLICY.md).

**Architectural correction to the initial sketch:** a universal Step-1 semantic decoder would impose latency and reproduce an experimentally weak seam. Semantic interpretation belongs in the cheapest *qualified* route that actually needs it. A capable model can receive a bounded grounded context directly.

## 6. Edge Brain and specialists

A distinct **logical Edge layer** is useful: it gives routine, bounded intelligence a contract, resource budget, and qualification boundary independent of the Capable Brain. It should be a replaceable collection of roles, not a promise that one tiny model can handle them all. Approximately **<1B** remains the strong product target, not a license to broaden Edge work when a larger model happens to score better.

Every proposed role needs the same contract: task and modality envelope; grounded input and source IDs; constrained output or abstention; versioned model, prompt and schema; measured failure and calibration; resource ceiling; escalation rule; and a held-out benchmark against deterministic and Capable Brain baselines.

| Role | Residual problem and proposed boundary | Present conclusion |
|---|---|---|
| Reflex tool choice / record extraction | Simple competing-tool or structured-record cases that rules cannot reliably distinguish. Output is a proposed offered capability/record, validated by runtime. | Narrow Needle 3 evidence exists; production integration does not. |
| Argument extraction | Bounded slots from an already understood request; missing or conflicting slots cause abstention. | Needle result 2/4 is insufficient. Test only a newly defined residual class. |
| Clarification rendering | Explain grounded candidate differences when a short deterministic question is inadequate. It cannot create options or IDs. | **UNMEASURED**; simple wording needs no model. |
| Retrieval interpretation / ranking | Compare authorized, grounded candidates when names and metadata are insufficient. Return evidence and uncertainty. | **UNMEASURED**; Graphify hints cannot supply truth. |
| Bounded drafting | Only a precisely defined, low-consequence task class in Auto mode; assess result quality as well as execution. | **UNMEASURED**. Explicitly selected Capable Brain authors substantive drafts, even short ones. |
| OCR, speech, vision and embeddings | Add a modality or retrieval capability only for a measured residual need. Output carries provenance and uncertainty. | No current general Edge qualification. Load on demand if eventually qualified. |

This challenges an easy but costly interpretation of “Edge first”: trying Edge on every request would add double inference, errors, and escalation. Edge is **first-class in the route policy**, not mandatory first execution.

## 7. Capable and cloud Brains

The local Capable Brain handles meaningful reasoning, synthesis, substantive drafting, uncertain judgment, multi-step work, and complex tool use. In Auto mode, URI selects the least costly qualified local or authorized cloud route expected to finish reliably. An explicitly selected model is the preferred author of substantive work; Edge may perform qualified supporting steps.

URI’s harness should offer the stronger model native tools and context appropriate to its provider: iterative and parallel tool calls, structured output, multimodal input, and agentic continuation where supported. The model still crosses the same runtime authority boundary. The accepted [M33.2 architecture](C:/Users/cheta/Development/Uri/_V1/docs/architecture/M33_2_EDGE_SECOND_BRAIN_CANONICAL_ARCHITECTURE.md) already distinguishes Edge, hybrid, and Main-preferred behavior; the proposed **local-only / Auto / selected-provider** product control needs a versioned mapping to those existing settings, not an unexplained second policy system.

Auto cloud escalation needs an already connected, user-authorized provider and a visible route trace. It does not authorize email sending, form submission, deletion, or any other external action. In local-only mode, URI reports a limitation or offers a local route rather than silently using cloud.

## 8. Context, RAR, ARN, and Graphify

Build a small, provenance-rich **task context** only when needed: selected items and attachments, recent turn state, authorized source metadata/content, candidate IDs, and capability state. Graphify can point URI toward a source; URI must check that source and its permissions. RAR should bind a reference only to grounded candidates, preserving ambiguity. ARN.1’s verified narrowing applies to its current `NOT_FOUND` path; a future clarification renderer is separate proposed work despite the similar “ARN” name.

Before asking, URI may make a bounded read-only search through already-authorized evidence. Model-assisted comparison is permitted only for a qualified candidate-set task and must report inference as inference. For a low-consequence reversible action, URI may act on a sufficiently supported candidate while showing the selection and an easy correction. Consequential, external, destructive, or hard-to-reverse actions require clarification if identity remains unresolved.

A simple clarification can immediately say “Which report do you mean?” with up to about four or five **grounded** selectable candidates, no padding, and a “None of these / Enter something else” path. Selection binds a candidate ID; free input governs the next attempt. This user requirement **conflicts with M33.2’s accepted rule that visible confirmation wording be model-authored**. The future architecture revision must resolve that conflict explicitly. I recommend the bounded deterministic exception you specified, with Edge wording only when it measurably helps.

## 9–10. Native capability and residency

Available capability may exceed simultaneously resident capability. That is practical through installed on-demand models, but fast completion under switching pressure is **unproven on this machine**. Separate a provider/model registry from leases for resources URI owns. Track each lease’s ownership, placement, context/KV allocation, load state, observed memory, and reuse. Never infer permission to evict a model merely from seeing it in LM Studio or Ollama.

Compare permanent 9B residency, idle unload, cold demand load, Edge plus Main co-residency, CPU/GPU placement, and partial offload. The existing 9B run reached about 7.32 GB system GPU memory and 21.7 GB host RAM; that is reason to measure co-residency, not declare it impossible. The measured 6.08 s cold load makes demand loading a meaningful latency trade-off. Disk mapping and partial GPU offload are supported desktop mechanisms, but mapped weights still incur access and memory costs; the ESP32/TinyStories technique is not evidence that URI can cheaply stream a 9B model for every token. [LM Studio documents idle TTL and auto-evict behavior](https://lmstudio.ai/docs/developer/core/ttl-and-auto-evict); [llama.cpp documents loading and GPU layer placement](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).

On the Ryzen 9 5900X, 24 GB RAM, RX 7900 GRE 16 GB, and Windows target, measure the **actual provider/backend** in use. Do not assume CUDA behavior or transfer a result from a different offload configuration. No always-resident 9B policy is ready to freeze.

## 11–12. Route learning and cost

Create a **separate per-user route-performance store** from URI knowledge and memory. A minimal record would hold task/capability class, qualified route and versions, context/provenance fingerprints, objective execution and task outcomes, explicit feedback if given, retries/escalation, latency and resources. Store raw conversation or correction text only when separately needed and governed; structured evidence is the default.

Durable learning defaults **ON** with ON/OFF, inspect, delete, and reset controls. OFF prevents new durable route/response-evaluation records while allowing normal operation and temporary task/session evidence, which is discarded when no longer needed. Resetting route preferences must not erase document knowledge.

Qualification is a hard eligibility gate. Within the **same independently qualified capability class**, accumulated evidence may gradually shift preference among routes. A route’s qualification, permission, safety requirement, or Edge/Capable boundary cannot be learned into existence. Weight negative feedback promptly; decay or invalidate evidence after model, tool, prompt, schema, qualification, or relevant context changes; reduce preference or roll back when measured quality deteriorates. Keep this inspectable and reversible.

Attach optional 👍, 👎, and correction controls to the actual response/operation trace. Record technical execution, actual task completion, explicit acceptance, rejection, correction, and route performance separately. No response is a neutral signal. A “wrong reference” correction primarily examines context/RAR; poor wording examines drafting; a failed action examines tool binding and execution. One feedback item must not permanently change routing.

For each eligible route, estimate **end-to-end** cost: preparation + load/switch + inference + tools + expected retries + failure/escalation cost + resource pressure. Compare p50/p95 task completion and correctness by workload stratum; do not set an arbitrary universal millisecond target. The current route may be faster than a tiny-model chain that eventually calls the Main Brain anyway.

## 13–14. Failure, escalation, and hardware controls

Unknown task class, stale qualification, unsupported modality, missing evidence, resource denial, or failed bounded proposal should lead to an appropriate qualified route or an honest limitation. Do not retry a side effect without checking whether it executed. Preserve the action chain across local and cloud routes. Separate user permission to use a Brain from permission to perform an action.

The resource governor should budget at the shared **process** level, because concurrent users can compete for the same leases. It should measure CPU/RAM/VRAM where the runtime exposes them, context/KV growth, load/unload time, switching, queue delay, memory pressure, and coexistence. Missing telemetry is unknown, not spare capacity. The [M33.2 resource design](C:/Users/cheta/Development/Uri/_V1/docs/architecture/M33_2_EDGE_SECOND_BRAIN_CANONICAL_ARCHITECTURE.md) already defines lifecycle states and a shared pool; new work should extend and verify those contracts rather than duplicate them.

## 15–16. Empirical program and incremental sequence

| Stage | Bounded question and comparison | Pass/stop evidence |
|---|---|---|
| **First: source-to-candidate boundary** | Offline, production-shaped replay: can actual session, file, attachment and authorized-source state produce the grounded candidates and anchors RAR needs? Compare current non-oracle path, deterministic IDs/anchors, and a bounded context capsule on held-out raw turns. | Report coverage, abstentions, false binds, provenance, and end-to-end preparation latency. Stop if consequential false binding occurs; do not call a coverage gain safe without error analysis. No production wiring or frozen-battery edits. |
| Edge residual qualification | On failures left by the first stage, compare deterministic completion, the narrowly qualified Needle role, a smallest plausible specialist, and direct Capable Brain. Use task-specific held-out cases including negation, conflict, missing evidence, and malformed output. | Independent role qualification, output validation, quality, p50/p95 total latency, retries, escalation, RAM/VRAM. Reject a specialist when its total route loses or its critical failures persist. |
| Residency study | Same workloads under resident, idle-unloaded, on-demand, co-resident, and feasible placement/offload policies. | First-token and task latency, cold start, switching, memory, thrashing, completion. Stop any configuration that disrupts external leases or exceeds configured limits. |
| Routing and learning replay | Replay only among already-qualified routes; compare fixed routing with gradual learned preference, version invalidation, negative feedback, and rollback. | Quality and latency by class, regressions, explainability, reset/OFF behavior; no online promotion. |
| Governed integration and live validation | After separate stage authorization, connect one qualified role through the canonical agent loop and UI. | Component, integration, agent-loop and live user-visible evidence under the [four-stage lifecycle](C:/Users/cheta/Development/Uri/_V1/docs/governance/URI_FOUR_STAGE_DEVELOPMENT_LIFECYCLE.md). |

Use realistic office tasks: open a known file, locate a precedent, answer “what did we decide?”, extract tool arguments, draft an email reply **without sending it**, produce an Office Order or PDF when requested, set a reminder, resolve ambiguous references, and handle document or multimodal input. Keep simple and complex strata separate. A successful provider call is not necessarily a good draft or a completed task.

## 17. Material risks and open measurements

- **Grounding is the immediate bottleneck.** The 27/136 presegmented RAR result cannot be presented as raw-turn coverage beside the 0/84 non-oracle result. The current context resolver’s first-match behavior also needs an ambiguity-safe boundary before reuse. [A3 synthesis](C:/Users/cheta/Development/Uri/_V1/docs/plans/M35_URIV1_A3_ARCHITECTURE_SYNTHESIS_AND_NEXT_BATCH_PLAN.md)
- **Edge scope creep could worsen both speed and quality.** The tested small decoders failed precisely the negation and reference cases a universal early decoder would need to handle.
- **Current Edge role qualification is not production routing.** M33.2’s narrow Needle result must not be described as a live `/ask` fast path; M33.3 Batch A adds no new qualified candidate.
- **Learning can bias toward superficially fast failures.** Objective completion and explicit user evaluation must remain distinct, with negative evidence and version invalidation.
- **Shared runtime residency can disrupt other users or apps.** URI needs lease provenance and measured coexistence before automatic eviction policies.
- **No further product-level choice presently blocks this proposal.** Case-specific thresholds, first model artifacts, retention periods, and residency settings should follow measurements and the appropriate architecture review; they need not be guessed now.

## 18. Recommendation and direct answers

**First experiment:** the offline, non-oracle source-to-candidate boundary study in Stage 1 above. It attacks the largest documented gap before spending time on another decoder. Its output should be a held-out case table, grounded-candidate provenance, false-bind analysis, and latency/resource trace—not a production feature.

Answers to the ten design questions:

1. **Distinct Second Brain?** Yes as a logical, qualified Edge layer; no evidence supports a universal mandatory model pass.
2. **One model or cluster?** Replaceable roles sharing contracts; add a specialist only for a measured residual failure.
3. **Permanently resident?** Only components whose measured reuse and resource cost justify it; no permanent 9B mandate.
4. **On demand?** Infrequent specialists and possibly Main Brain, subject to measured cold and switching costs.
5. **Bypass Main?** Deterministic work and independently qualified simple Edge classes; honor explicit model choice for substantive work.
6. **Escalate?** Complexity, uncertainty, unqualified class, critical semantic failure, or unsupported evidence/modality.
7. **Stronger selected model?** Expose native capabilities through the canonical tool loop and preserve its authorship of substantive work.
8. **More available than resident?** Yes via installed on-demand loading; usefulness under this hardware load remains to be measured.
9. **Minimum viable structure?** Existing deterministic runtime and native loop, an ambiguity-safe grounded context boundary, explicit qualification-aware router, and one narrow Edge role only when independently integrated.
10. **Still experimental?** Raw-turn RAR coverage, Edge drafting/clarification/arguments/modalities, cloud route quality, co-residency, dynamic route learning, and practical latency thresholds.

**BRAIN_ARCHITECTURE_STATUS:** `READY_FOR_EXPERIMENT`  
**FIRST_EXPERIMENT:** Offline, held-out source-to-candidate grounding and RAR-boundary replay.  
**ARCHITECTURAL_COMMITMENTS:** Preserve runtime authority, native Capable Brain abilities, user model choice, role-specific qualification, separate action permissions, and no learned promotion of unqualified routes. These are existing constraints and your stated requirements; this proposal itself is **not frozen**.  
**UNPROVEN_HYPOTHESES:** An Edge cluster’s net speedup, raw-turn reference reliability, resident versus demand-loaded 9B, co-residency, bounded Edge drafting and clarification, and automatic preference learning.  
**NEXT_AUTHORIZATION_REQUIRED:** A separately scoped, governed plan and authorization for the **offline first experiment only**. No experiment, implementation, architecture freeze, commit, or push has been performed.
