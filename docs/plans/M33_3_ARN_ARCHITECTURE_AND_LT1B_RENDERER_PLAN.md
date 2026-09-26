# M33.3 — ARN Clarification Architecture and <1B Text Renderer Plan

**Status:** DRAFT, revised R1 after the User architecture interview (planning only, `PLAN_M33_3_ARN_ARCHITECTURE_AND_LT1B_TEXT_GENERATOR`). Not accepted, not frozen, not registered, not committed.
**Status update (2026-09-26, additive):** revised R2 (cross-plan repairs A-R1…A-R12, User decisions D1–D4). Registered as planning identity `URI-REFERENCE-CLARIFICATION` in `URI_STATE.yaml` → `planning_artifacts`. Committed to the repository. Status `PLAN_REVISED_R2_AWAITING_INDEPENDENT_CROSS_PLAN_REAUDIT`: not accepted, not frozen, implementation NOT authorized.
**Status update (2026-09-26, additive):** revised R3 (RG-0 bounded contract repair: RG-0-F1 `CHOOSE_ATTRIBUTE` contract, RG-0-F2 Change/rebind/redo lifecycle, RG-0-F3 RAR score terminology). Status `PLAN_REVISED_R3_AWAITING_FOCUSED_INDEPENDENT_REAUDIT`: not accepted, not frozen, implementation NOT authorized.
**Status update (2026-09-26, additive):** RG-0R returned `RG_0R_ACCEPTED` (no blocking defects; R3 repairs accepted; planning phase may close). Revision R4 records User decisions D5 (CONFIRMED authority) and D6 (S1 boundary) and S1 scoping evidence F-1 to F-6. Status `PLANNING_CLOSED_RG0R_ACCEPTED_R4_RECORDED`. S1 scope: `docs/plans/M33_3_S1_STATE.md` (`S1_SCOPE_READY_FOR_IMPLEMENTATION_REVIEW`). Implementation NOT authorized.
**Branch / base:** `m35-uri-v1-parallel-architecture` @ `127c733` (Batch A frozen).
**Author role:** Claude (Architect / Pre-Auditor). Implementation is not authorized by this document.
**Date:** 2026-09-26

Nothing in this plan authorizes: runtime code changes, provider or model benchmarks, model installs, Stage B, `INT-*` events, changes to frozen Batch A evidence, P2P memory, Companion UI, or reopening the 78-row historical text gap.

---

## REVISION R1 — User architecture interview (2026-09-26). SUPERSEDES conflicting text below.

The original draft (sections 0-16 below) is kept unchanged as auditable history. Where it conflicts with this revision, this revision wins. It is still DRAFT: not accepted, not frozen, not registered, not committed.

Labels used: **[USER]** product requirement stated by the User; **[EVIDENCE]** repository evidence; **[HYPOTHESIS]** engineering hypothesis; **[EXPERIMENT]** experiment required before it becomes architecture.

### R1.1 Identity
- [USER] The workstream is not "ARN". It is the user-facing clarification and correction layer around reference resolution. ARN.1 and EXP-ARN-URIV1 stay unchanged and are reused only as mechanisms and precedent. ARN.1 is not unpaused, and nothing is called ARN.2.
- Proposed identity: `URI-REFERENCE-CLARIFICATION`, a workstream under M33.3. If it is later also registered as a reusable component, the repository casing convention (`URI-Edge`, `URI-RAR`, `URI-Memory`) suggests `URI-Reference-Clarification`. Registration is not done by this revision.
- The file name of this plan would change to `M33_3_REFERENCE_CLARIFICATION_PLAN.md` at acceptance. It is not renamed now.

### R1.2 Brain model
- [USER] "Brain" means the whole intelligence system. It has three parts: deterministic mechanisms, an Edge Brain as the default fast layer for qualified bounded tasks, and the Capable (Main) Brain as the escalation layer. What belongs at the Edge is decided by experiment.
- Consequence: D-B (Edge wording as an "exception" to Brain authority) is dissolved. Deterministic, Edge, and Capable wording are all Brain-layer text. Each is validated against the contract before display. URI's harness still owns decisions and authority.
- [USER] Deterministic wording may be the primary text wherever it is proven sufficient and acceptable, not only as a fallback. It must not be chosen merely because it is cheap if it feels rigid.

### R1.3 Wording selection replaces the fixed chain
`[TABLE SUPERSEDED by R2.5 — Capable Brain = explicitly selected model when selected; EDGE_ONLY column added; eligibility decided by the single unified router]`

The draft chains (<1B → Main Brain → template, and <1B → template) are replaced by a deterministic **ClarificationWordingPolicy**, decided per contract.

| Contract need class | Edge ON, Edge Brain warm and qualified for the class | Edge ON, not warm | Edge OFF |
|---|---|---|---|
| SIMPLE (template sufficient) | template | template | template |
| EXPLAIN (facts need explaining: conflicts, versions, same-name people) | Edge Brain, then template on failure | template (never cold-load to polish) | template |
| REASONING (needs interpretation or conversation, e.g. escalation after no progress) | Capable Brain | Capable Brain | Capable Brain |

- [USER] Never cold-load a specialist to polish wording. Never call the Capable Brain to replace cosmetic Edge wording. Edge OFF disables only Edge inference: RAR, contracts, binding, Graphify, and validation keep running.
- [HYPOTHESIS] The need class can be computed deterministically from the contract (count of discriminating keys, conflicts, candidate type, overflow). [EXPERIMENT] Validate that the class boundary matches where model wording is rated as noticeably better (R1.9).
- [EVIDENCE] The warm Qwen3.5-9B took 130-156 ms for short outputs in M33.2 B4, and 1-2 s for large prompts in A2.8B. The Capable Brain may be cheaper for short renders than assumed. [EXPERIMENT] Measure this.

### R1.4 Edge Brain qualification replaces the dedicated <1B renderer search
- [USER] "<1B" is a starting target, not a constraint. Search bottom-up for the cheapest Edge Brain, or specialist combination, that covers the routine workload. Prefer one shared Edge Brain. Add a dedicated specialist only on evidence. Optimize end-to-end latency, residency, RAM/VRAM, reliability, coverage, retries, and escalation rate. Parameter count is not the target.
- Change: this workstream does not select or search models. It contributes a clarification-wording task battery and gates to a shared Edge Brain qualification. The template and the Capable Brain are the reference arms.
- [EVIDENCE] M33.2 B4 rated SmolLM2-135M and Qwen2.5-0.5B `BYPASS / REDUNDANT` for language tasks ("fluent text but missed important rubric requirements"). SmolLM2: cold load about 390 ms, about 204 MB resident. Sample: 4 items. A2.8B: LFM2.5-350M showed scaffolding confusion. These are negative priors for sub-1B wording.

### R1.5 Binding, consequence, and ask-versus-proceed
- [USER] Consequence means the impact of a wrong reference, not whether the action writes. Confirmation is required when a wrong reference could cause a meaningful external, destructive, irreversible, security-sensitive, financial, submission/publication, or hard-to-recover effect. Read, open, search, summarize, and ordinary draft creation may proceed tentatively, with the choice visible and easy to change. Approval gates stay independent.
- `[CORRECTED by R2.6 — the production fields are `Action.effect_type` / `approval_requirement` / `risk`; there is no `requires_approval` field]` New metadata: a `wrong_binding_impact` of `NONE`, `RECOVERABLE`, or `CONSEQUENTIAL`, declared per capability/action next to `requires_approval`. [EVIDENCE] Nothing like this exists in `uri_core` today. [HYPOTHESIS] Unclassified actions are treated as `CONSEQUENTIAL` (fail closed).
- Binding states: `TENTATIVE` (shown as "Using X · Change") and `CONFIRMED`. The execution gate requires `CONFIRMED` for `CONSEQUENTIAL` actions. `CONFIRM_SINGLE` is replaced by this. `[REFINED by R2.2 / R2.4 — single-candidate kind `CONFIRM_ONE`; post-execution states TENTATIVE_APPLIED/CHANGED/REDONE/VERSIONED]` `[REFINED by R3.2 — CHANGED renamed CHANGE_PENDING; redo only after a validated rebind to CONFIRMED(Y)]`
- [USER] Two or more equally plausible candidates: always ask with clickable options, even for harmless actions.
- `[REFINED by R2.9 — deterministic TENTATIVE eligibility check; model evidence only when grounded and re-checked (D3); no durable learned evidence (D4)]` "Strongly preferred" (allowed to be TENTATIVE): [HYPOTHESIS] deterministic separation only. A lone `MODEL_SELECTION` result never counts; it is treated as ambiguous. Learned evidence may count (R1.7).
- `[REFINED by R2.8 — after bounded, non-binding pre-ask investigation inside candidate generation]` Timing: an AMBIGUOUS result asks immediately, before any action proposal. A TENTATIVE single candidate is checked for consequence at proposal time. No Capable Brain call is spent before an ambiguity question.
- `[REFINED by R3.2 — redo only after BindingService rebinds to CONFIRMED(Y) and fresh execution/approval authorization passes; edited-result preservation depends on S11]` [USER] Changing a tentative choice after use: the recoverable action is redone automatically on the new candidate. If the user had edited the old result, the redo is a new version and the edited version is kept in history.

### R1.6 Presentation
- [USER] Adaptive, minimizing user effort.
  - If the ranking clearly separates a small top group: show up to 4-5 options, plus "N more" where useful, plus the escape option.
  - If candidates are flat: first ask the most valuable grounded attribute question, then show the narrowed set.
  - Never dump a large list. Never ask an attribute question when the ranking already makes the choice obvious.
- `[CONTRACT COMPLETED by R3.1 — attribute option type, render request, ATTRIBUTE payload, validation, re-resolution transition, escape path]` `[REFINED by R4.6 — ARN.1 semantics are ported into S1, not imported (F-5); S1 axes are title/type/owner/recency only (F-4)]` New kind `CHOOSE_ATTRIBUTE`. It reuses ARN.1 `get_clarification_recommendation` (axis choice) and `UserClue` / `apply_user_clue` (binding an attribute click). An attribute option binds a `UserClue(axis, value)`, not a candidate ID.
- [HYPOTHESIS] "Clearly separated" = the RAR top driver-rule tier holds 5 or fewer candidates. `[CORRECTED by R3.3 — RAR emits deterministic diagnostic candidate_scores; they are not calibrated confidence]` RAR ranks are ordinal, and no scores exist. [EXPERIMENT] Measure clicks-to-resolution for top-N versus attribute-first on the battery and in the User rating subset.
- The cap stays at 5 as the hard maximum. Whether 4 is better is [EXPERIMENT] (clicks, errors, User rating). It is not frozen.
- [USER] Multiple ambiguous references in one turn are handled adaptively. A bundle contract holds several reference sub-contracts with dependency edges. Independent references share one combined card. Dependent references are asked in order; a dependency exists when one reference's candidates derive from another's binding. [HYPOTHESIS] Dependency can be detected from candidate provenance (parent locator).

### R1.7 Free input, re-resolution, and learning
- `[SCOPE CORRECTED by R2.7 — Graphify indexes no documents or emails; document/email broadening uses authorized retrieval capabilities]` [USER] "None of these" plus text is authoritative new evidence. It starts a new bounded cycle with a new `ambiguity_id` over session context, Graphify/context indexes, and already-authorized sources, without asking. It never silently expands into unauthorized or unbounded research. If still unresolved, say what remains unresolved and ask only the next useful question.
- Bounding reuses ARN.1 `CostCeiling` / `CostAccumulator`. "Authorized sources" = sources the user has already granted capability access to. [EXPERIMENT] Confirm that this definition is computable from existing capability grants.
- [USER] Learning is selective, visible, and editable. A choice is authoritative for the current session at once. Across sessions it is evidence, never a permanent binding. It keeps provenance, decays or is invalidated when circumstances change, and never overrides stronger current evidence.
- `[SUPERSEDED by R2.1 / R2.12 — ExperienceStore is not the learned-reference mechanism; Change events use the unified evaluation stream]` Mechanism: [EVIDENCE] `uri_core/core/experience_store.py` already has category `reference_pattern`, written only after the Brain's acceptance-retention judgment. This workstream emits a resolution-outcome retention candidate and does not persist memory itself. "Change" taps feed `ExperienceRecord.corrections` as negative evidence.
  - Dependency gap: `ExperienceRecord` has no decay, invalidation, or source fingerprint. That belongs to the memory side (the `URI-Memory` component is `NOT_STARTED`) and is outside this workstream.
- [USER] Learned evidence may break a tie only for `NONE` / `RECOVERABLE` actions, weighted by recency, repetition, context similarity, provenance, and reliability. One past choice is weak evidence.
  - `[NARROWED by R2.1 — session-only evidence now; durable learned tie-breaking DEFERRED to URI-Memory (D4)]` [HYPOTHESIS] Ship it rank-only first. Enable tie-breaking only after an [EXPERIMENT] shows an acceptable correction rate for learned tie-breaks.
  - `[SUPERSEDED by R2.1 — weighting runs in a separate session-only deterministic adjunct after RAR, not inside RAR; durable/cross-session evidence DEFERRED to URI-Memory (D4)]` The weighting is deterministic evidence scoring inside RAR, not Brain cognition. It must stay auditable.

### R1.8 Stopping
- [USER] Two separate safeguards:
  - (a) a progress-based clarification limit: a round with no meaningful narrowing stops at once, with a small hard cap as backstop;
  - (b) a per-turn resolution budget covering new-clue cycles, searches, Graphify/context investigation, model calls, retries, and elapsed time.
  - A new clue does not count toward (a) but does count toward (b). When either is hit, stop autonomous resolution and hand off to explicit conversation or the Capable Brain.
  - Values are [EXPERIMENT]. The draft's frozen "2 rounds" is withdrawn.
- "Progress" (deterministic): the candidate set strictly shrinks, or a new authoritative clue is bound.

### R1.9 Qualification changes
- [USER] Two-part judgment.
  - Independent frozen-rubric adjudication covers correctness, grounding, validity, and consistency at scale.
  - The User rates a blinded representative subset of template versus model wording for naturalness, clarity, usefulness, and whether the difference is noticeable enough to justify the latency and resources.
  - The ratings calibrate the UX criteria and never override safety or grounding failures. Later, automated adjudication runs with periodic User sampling.
- New gates:
  - `CANDIDATE_THRESHOLD_TO_BE_ESTABLISHED`: noticeable-improvement rate of model over template per need class; clicks-to-resolution; tentative-binding correction rate; learned tie-break correction rate; per-turn budget exhaustion rate; auto-redo correctness.
  - `FROZEN_REQUIRED`: a `CONSEQUENTIAL` action never executes on a TENTATIVE binding; unclassified impact is treated as `CONSEQUENTIAL`; an edited result is never overwritten by a redo; Edge OFF never invokes an Edge model; no cold load for SIMPLE or EXPLAIN wording.
- New battery categories:
  - tentative bind with visible change;
  - consequence-gated confirmation;
  - learned tie-break, allowed and forbidden;
  - multi-reference, independent and dependent;
  - attribute-first presentation;
  - redo after edit;
  - budget exhaustion;
  - no-progress stop.

### R1.10 Unchanged from the draft
RAR owns trigger, type, candidate set, IDs, rank, cap, provenance, and binding contract. `rar_deterministic.py` (A9) is untouched. Slot-keyed rendering hides IDs. URI controls option order. The escape option is a URI-appended constant. The deterministic RenderValidator runs on every tier and fails closed. A click binds through `RARDeterministicAnchor.selected_ui_id` / `ACTIVE_UI` `[REFINED by R4.4 — CONFIRMED only if the fresh re-run returns the clicked candidate through ACTIVE_UI; otherwise fail closed]`. Contract validation mirrors `validate_rar_resolution`. Graphify is optional, and its facts are `SOURCE_POINTER`. Provenance is carried per fact. Pending state uses the `turn_state` projection and the approval-expiry precedent. No numeric confidence. Privacy: local tiers only, and no content in production traces.

---

## REVISION R2 — Cross-plan repairs A-R1 … A-R12 and User decisions D1–D4 (2026-09-26). SUPERSEDES conflicting text in R1 and in the draft.

**Sources.**
- The cross-plan audit is `docs/plans/M33_3_CROSS_PLAN_AUDIT_REPORT.md` (verdict `COMPATIBLE_WITH_BOUNDED_REPAIRS`).
- The sibling plan is `docs/plans/M33_3_URI_BRAIN_ARCHITECTURE_PROPOSAL.md` (Plan B, revision R1).
- The state file and verbatim User decisions are in `docs/plans/M33_3_CROSS_PLAN_STATE.md`.

**Precedence.** R2 wins over R1 and over the draft (§0–§16) wherever they conflict. R1 and the draft remain unchanged as history, except that short `[SUPERSEDED …]` markers were added beside stale passages so a search finds them.

**Authorization.** Still DRAFT and not frozen. Implementation is **not authorized**.

### R2.0 User decisions (authoritative for this revision)
- **D1** [USER]: `gmail_create_draft` → `wrong_binding_impact = RECOVERABLE`. An unsent draft can be corrected before external communication occurs. The value is independent of `EffectType`, `ApprovalRequirement`, and `RiskLevel`. A future real send action is expected to be `CONSEQUENTIAL`. The value is never derived mechanically from `EffectType`.
- **D2** [USER]: keep `EDGE_ONLY` / `HYBRID` / `MAIN_BRAIN_PREFERRED`. The canonical mapping is Plan B R1.2 and is summarized in R2.5 below.
- **D3** [USER]: models may investigate, interpret clues, compare grounded candidates, narrow, annotate, and return structured evidence. They never create binding authority. Model preference alone never creates `TENTATIVE`. The flow is: model interpretation/investigation → structured grounded evidence → deterministic resolution/eligibility check → `TENTATIVE` / `CONFIRMED` / `CLARIFY`. A model never invents candidate IDs.
- **D4** [USER]: **DEFERRED** to URI-Memory. Durable cross-session learned reference evidence and durable learned tie-breaking are not authorized now, and no ad-hoc durable reference-memory subsystem may be built. Allowed now:
  - session-authoritative selections;
  - session-local reference evidence;
  - structured Change/correction events;
  - rank/display effects from valid session evidence.

### R2.1 (A-R1) Learned reference evidence: replaces R1.7's ExperienceStore mechanism
- [EVIDENCE] `uri_core/core/experience_store.py`:
  - records are Brain-approved prose summaries (`summary`, free-text `corrections`);
  - there are no candidate IDs, no decay, invalidation, or source fingerprint, and no delete/inspect endpoint (only `list_all` / `recent` / `add`);
  - records feed the Brain's query context, not a deterministic ranker.
  - ExperienceStore therefore cannot serve as auditable ranking input. **ExperienceStore keeps its existing role and is not repurposed** for reference memory or route learning.
- [EVIDENCE] `uri_v1/turn/rar_deterministic.py` is A9-protected (SHA-256 `e02af25bb7009d12d829c8b8fc92e487d3da75aeaa160092db617458278fb649`). `[CORRECTED by R3.3 — RAR does emit deterministic diagnostic candidate_scores (not calibrated confidence); the conclusion below rests on A9 protection]` RAR ranks are ordinal and carry no scores. The learned-evidence weighting therefore **cannot live "inside RAR"**.
- **Mechanism (replaces R1.7's "Mechanism" and "weighting … inside RAR" bullets).** A **separate deterministic session-evidence adjunct runs after RAR**. It reads:
  - the RAR resolution;
  - the `RARQuery`;
  - **session-local** evidence records only: selections, free-input clues, and Change events in the current session.
- **What the adjunct may do:**
  - reorder display among candidates that RAR left tied, and annotate them;
  - contribute session evidence to the deterministic TENTATIVE eligibility check (R2.9).
- **What the adjunct may not do:**
  - add, remove, or rename candidates;
  - change `RAROutcome`.
- The adjunct is pure and deterministic. It never modifies `rar_deterministic.py`.
- **Durable cross-session reference evidence** (provenance, decay, invalidation, cross-session tie-breaking) is **DEFERRED to URI-Memory** (D4). It is not built here. R1.7's "Ship it rank-only first" is narrowed to **session-only** evidence. Durable learned tie-breaking stays unauthorized until URI-Memory exists and a correction-rate experiment qualifies it.
- The acceptance-retention path (`orchestrator._run_acceptance_retention_step` → ExperienceStore `reference_pattern`) is untouched. This workstream no longer emits retention candidates as a learning mechanism.

### R2.2 (A-R2) Single-candidate confirmation kind
Add `ClarificationKind.CONFIRM_ONE`. It replaces the draft's `CONFIRM_SINGLE`, which R1.5 removed, and restores a valid kind for the single-candidate case.

| Kind | When | Count rule |
|---|---|---|
| `CHOOSE_ONE` | RAR `AMBIGUOUS` (at least 2 plausible) | 2 ≤ candidates ≤ `max_options` (5) |
| `CONFIRM_ONE` | Exactly one candidate exists **and** no deterministic anchor authorizes automatic binding **and** the deterministic TENTATIVE check (R2.9) does not pass (for example, a lone `MODEL_SELECTION` basis, or `wrong_binding_impact = CONSEQUENTIAL`) | exactly 1 |
| `CHOOSE_ATTRIBUTE` | Flat candidate set (R1.6) | 0 candidate options; 2 ≤ attribute options ≤ 5; each option binds a `UserClue(axis, value)` (full contract: R3.1; never confirms a candidate) |
| `FREE_INPUT_ONLY` | RAR `UNKNOWN` / `NO_CANDIDATE` and the reference is required | 0 |

- Validation additions:
  - `CONFIRM_ONE`'s single `candidate_id` must be in the `RARQuery` candidate set;
  - the escape option ("None of these / Enter something else") is always URI-appended;
  - `CONFIRM_ONE` is never auto-bound on timeout.

### R2.3 (A-R3) Risk vocabulary: remove TOOL_CATALOG tiers
- The Batch A `TOOL_CATALOG` tiers (`AUTO` / `CONFIRM` / `DESTRUCTIVE`) used in §4.1 are research vocabulary and duplicate production metadata. **They are removed from this plan.**
- Trigger and gating use three things:
  - the **binding state** (`PENDING`, `TENTATIVE`, `CONFIRMED`);
  - **`wrong_binding_impact`** (R2.6);
  - the existing production `Action` fields `effect_type`, `approval_requirement`, and `risk` (`uri_core/capabilities/base.py`).
- Replacement trigger table (supersedes §4.1):

| RAR / evidence state | Clarification action |
|---|---|
| `RESOLVED`, basis `DETERMINISTIC_ANCHOR` `[SUPERSEDED by R4.2 / R4.3 (D5) — basis alone never decides authority (F-1); only certainty-tier rule/provenance → CONFIRMED; other RESOLVED → TENTATIVE-eligible via R2.9 or CONFIRM_ONE]` | none; binding `CONFIRMED` |
| exactly 1 candidate, deterministic TENTATIVE check passes (R2.9) | none before the proposal; binding `TENTATIVE`; shown as "Using X · Change". The execution gate still blocks if the proposed action's `wrong_binding_impact` is `CONSEQUENTIAL` (R2.6), which then raises `CONFIRM_ONE`. |
| exactly 1 candidate, check fails (for example, a lone `MODEL_SELECTION` basis) | `CONFIRM_ONE` |
| `AMBIGUOUS` | `CHOOSE_ONE`, or `CHOOSE_ATTRIBUTE` if the set is flat (R1.6) |
| `UNKNOWN` / `NO_CANDIDATE`, reference required | `FREE_INPUT_ONLY` |
| `UNKNOWN`, reference not required | none; routing proceeds per R2.5 |

### R2.4 (A-R4) Post-execution lifecycle
- The per-`ambiguity_id` state machine of §7 gains post-execution states:

`[DIAGRAM SUPERSEDED by R3.2 — CHANGED renamed CHANGE_PENDING; no redo before BindingService rebinds to CONFIRMED(Y) and fresh execution/approval authorization passes]`

```
PENDING --click/confirm--> CONFIRMED --execute--> APPLIED
(exactly-1, check passes) --> TENTATIVE --execute--> TENTATIVE_APPLIED   (shown "Using X · Change")
TENTATIVE_APPLIED --Change(Y)--> CHANGED --BindingService validates Y--> CONFIRMED(Y)
CHANGED --redo recoverable action on Y--> REDONE
REDONE, when the X-derived result was user-edited --> VERSIONED  (new version for Y; edited X version kept in history, never overwritten)
PENDING --timeout/new unrelated turn--> EXPIRED
```

- Rules:
  - A `Change` from `TENTATIVE` before execution is an ordinary rebind through `BindingService` to `CONFIRMED(Y)`; no redo is needed.
- `Change` after execution is permitted only from `TENTATIVE_APPLIED`, and only for actions whose `wrong_binding_impact` is `NONE` or `RECOVERABLE`. By construction no `CONSEQUENTIAL` action reaches `TENTATIVE_APPLIED`.
  - The redo uses the same route policy as the original action (R2.5).
  - **Owner gap:** `VERSIONED` requires a result-version record. [EVIDENCE] No result/artifact versioning exists today (`uri_core/core/file_store.py` has only a schema version), and whether users can edit results in `uri_ui` is **UNVERIFIED**. A result-version owner is **planned** work (audit slice S11) and is not assumed to exist.
- **Superseded:**
  - §7's "After execution, a correction is a new request; it never silently reverses an executed action" is superseded for `TENTATIVE_APPLIED` recoverable actions. It still holds for `CONFIRMED` / `APPLIED` actions and for all `CONSEQUENTIAL` actions.
  - §7's "At most 2 user-facing ARN-C rounds" / "hard cap of 3" is superseded by R1.8's two safeguards (progress-based limit plus per-turn resource budget; values are [EXPERIMENT]).

### R2.5 (A-R5) "Capable Brain" definition and the single router
- **"Capable Brain"** means the Capable Brain chosen by the unified router:
  - if the User explicitly selected a model, **that selected model is the Capable Brain for substantive work**, with its native capabilities preserved;
  - in AUTO, it is the router's choice.
- Mode behavior (D2; canonical table in Plan B R1.2):
  - `HYBRID` is efficiency-first.
  - `MAIN_BRAIN_PREFERRED` is capability-first; Edge does supporting work only.
  - Edge OFF removes Edge inference only.
  - `EDGE_ONLY` never calls the Capable Brain silently. A REASONING-class clarification under `EDGE_ONLY` surfaces the limitation or the escalation requirement, using template wording, instead of calling the Capable Brain.
- **Replacement wording table** (supersedes R1.3's table; need classes unchanged):

| Need class | Wording tier |
|---|---|
| SIMPLE | validated deterministic template (primary; M33.2 amendment G1) |
| EXPLAIN | the Edge wording role if the router reports it eligible (qualified, Edge ON, warm, resource-admitted, mode permits); otherwise the template. Never cold-load. |
| REASONING | the Capable Brain if the router reports it available under the current mode; under `EDGE_ONLY`, a template limitation/escalation statement |

- `ClarificationWordingPolicy` only computes the need class (deterministic, from the contract). **It does not decide model eligibility.** It asks the unified router (the M33.2 `uri_core/core/edge/routing_policy.py`, extended per Plan B R1.2). There is exactly one routing authority. The RenderValidator runs on every tier.

### R2.6 (A-R6) Production field names and `wrong_binding_impact`
- Correction to R1.5:
  - production has no `requires_approval` field on `Action`. The actual fields are `Action.effect_type: EffectType` (`READ_ONLY` / `LOCAL_WRITE` / `EXTERNAL_WRITE`), `Action.approval_requirement: ApprovalRequirement` (`none` / `user_approval_required` / `admin_approval_required`), and `Action.risk: RiskLevel` (`low` / `controlled` / `high` / `critical`) (`uri_core/capabilities/base.py:15-31, 138-146`; the legacy mapping is in `uri_core/capabilities/registry.py` `KNOWN_CAPABILITY_EFFECTS`).
  - "Nothing like this exists" is corrected to: those three risk/effect/approval fields exist, but none expresses the consequence of binding the wrong reference.
- **Future production contract (not implemented by this revision):**
  - `Action.wrong_binding_impact` ∈ {`NONE`, `RECOVERABLE`, `CONSEQUENTIAL`}, beside `effect_type`, `approval_requirement`, and `risk`.
  - Undeclared means `CONSEQUENTIAL` (fail closed; unlike `effect_type`, whose legacy default is `LOCAL_WRITE`).
  - The consumer is the **execution gate**. **If binding = `TENTATIVE` and `wrong_binding_impact` = `CONSEQUENTIAL`, block execution and require confirmation (`CONFIRM_ONE`).**
  - Approval stays a separate, independent gate.
  - Granularity is the action-level maximum across the action's reference parameters; per-parameter impact is deferred until evidence shows it is needed.
- **Why it cannot be derived from `EffectType`.** `gmail_create_draft` is `EXTERNAL_WRITE`, yet a wrong attachment or recipient in an unsent draft is correctable, so it is `RECOVERABLE` (D1). A read-only action can be `NONE`. A future send action is `CONSEQUENTIAL` regardless of approval state. The value is declared per action, never computed.

### R2.7 (A-R7) Graphify scope: supersedes R1.7's "Graphify/context indexes" and §8's candidate-source list
- [EVIDENCE] `uri_core/core/graphify_index.py` records only the kinds `capability`, `skill`, `workflow`, `memory_pointer`, and `connected_service`. **It does not index documents, files, or emails.**
- Graphify is a hint/pointer within that scope, carries the `SOURCE_POINTER` evidence category, and is never proof.
- Free-input broadening and candidate generation for documents and emails use:
  - session/turn state and current attachments (`read_attached_file`);
  - the user's `file_store`;
  - authorized retrieval capabilities (`gmail_search`, `gmail_find_draft`, `drive_search`), within the grants the User has already given.
- Graphify helps only for capability/skill/workflow/memory-pointer/service references.

### R2.8 (A-R8) Pre-ask investigation (inside candidate generation)
- Before RAR's final state is presented as `AMBIGUOUS`, the single source-to-candidate producer (Plan B R1.7) may run a **bounded, read-only, authorized investigation**:
  - inspect metadata and provenance;
  - check session context;
  - search already-authorized sources;
  - read candidate content;
  - compare grounded attributes;
  - use a qualified Edge interpretation role where one exists.
- The investigation is charged to the per-turn resource budget (R1.8(b)) and uses ARN.1 `CostCeiling` / `CostAccumulator` as the bounding precedent.
- It **never binds**. Its output is additional grounded candidates, or structured evidence placed on existing candidates, which RAR and the deterministic check then evaluate.
- R1.5's "an AMBIGUOUS result asks immediately" now means immediately **after** this bounded investigation, before any action proposal and before any Capable Brain call spent on the task itself.
- It must not cost more than one easy clarification click warrants ([USER]). Budgets are [EXPERIMENT].
- The frozen Batch A battery is not altered by this requirement.

### R2.9 (A-R9) Model comparison annotates and narrows only; the deterministic TENTATIVE check
- Per D3, a model (Edge or Capable, only in a qualified role) may return structured evidence:
  - candidate annotations;
  - eliminations with reasons;
  - interpreted clue attributes (for example, sender or date range).
- A model returns only candidate IDs that the contract supplied, or slot keys. Any other ID is rejected (the `validate_rar_resolution`-style membership check).
- **Deterministic TENTATIVE eligibility check** (owned by the deterministic layer). All of the following must hold:
  - (a) exactly one candidate remains after deterministic evaluation of all grounded evidence, **or** RAR driver-rule separation leaves one candidate strictly first;
  - (b) that outcome does not depend on model preference alone. Model-contributed evidence counts only when it is grounded: it cites candidate facts or source records that the deterministic layer re-checks against the candidate set;
  - (c) session evidence (R2.1) may contribute; durable learned evidence may not (D4);
  - (d) the proposed action's `wrong_binding_impact` is `NONE` or `RECOVERABLE`.
- Otherwise the result is `CONFIRM_ONE` or `CHOOSE_ONE`.
- A lone `MODEL_SELECTION` basis never passes (R1.5, retained).

### R2.10 (A-R10) Batch A silent-miss count: NOT_APPLICABLE
- [EVIDENCE] `docs/plans/M33_3_BATCH_A_COMPLETION_REPORT.md` §7: "every explicit filename or noun phrase is a silent detection miss (20 of 27 resolvable references; 21 of 32 rows including the must-abstain `RWB-013`)".
- The draft's R-1 figure "20/27" is **correct** and is unchanged.
- The cross-plan audit's contrary finding C-13 was an audit error, corrected in the audit report §15 COR-3.

### R2.11 (A-R11) Bundle (multi-reference) clarification contract
- [EVIDENCE] `RARQuery` resolves **one** `reference_expression`. `RARCandidate` has `id`, `title`, `candidate_type`, `recency_rank`, `domain_tags`, `owner`, `is_attachment`, `exact_aliases`, and `description`. **It has no parent, locator, or dependency field.**
- Contract (new, planned; frozen dataclasses in the same proposed module):

```python
@dataclass(frozen=True)
class ReferenceSlot:
    ref_key: str                      # stable key per reference in the turn, e.g. "r1"
    contract: ClarificationContract   # the existing single-reference contract (R2.2 kinds)
    depends_on: Tuple[str, ...] = ()  # ref_keys whose binding determines this slot's candidate set

@dataclass(frozen=True)
class ClarificationBundle:
    bundle_id: str
    session_id: str
    turn_id: str
    slots: Tuple[ReferenceSlot, ...]  # one per unresolved reference
    presentation: str                 # "COMBINED" when no depends_on edges among pending slots; else "SEQUENTIAL"
```

- Rules:
  - Independent slots (no `depends_on`) appear on **one combined card**. Each slot has its own options and its own escape option, and each binds separately through `BindingService`.
  - A dependent slot is asked only after its parents are `CONFIRMED`. Its `ClarificationContract` is then **rebuilt** from a fresh `RARQuery` whose candidate set is derived from the parent binding.
  - Validation: `depends_on` targets exist in the bundle; no cycles; a slot with pending parents is never displayed.
- **Planned, not available:**
  - the `depends_on` edge must be supplied by the source-to-candidate producer from candidate provenance (for example, "attachment of email E"). `RARCandidate` carries no such field today, so R1.6's "[HYPOTHESIS] Dependency can be detected from candidate provenance (parent locator)" requires a **new provenance field** in the producer output. It is not a field that exists;
  - `CandidateFact.source` (§4) likewise has no source in today's `RARCandidate` and must be supplied by the producer.

### R2.12 (A-R12) One evaluation event stream
- A `Change` tap is recorded as one event in **Plan B's structured evaluation stream** (Plan B R1.3), with:
  - category `wrong_reference`;
  - `trace_id`, `ambiguity_id`, prior `candidate_id`, new `candidate_id`;
  - binding state `TENTATIVE_APPLIED`;
  - redo outcome.
- There is no separate feedback channel. R1.7's "Change taps feed `ExperienceRecord.corrections`" is **superseded**.
- Within the session, the event is also session-local evidence for the adjunct (R2.1).
- Durable use of such events for route learning follows Plan B R1.3. Durable use for reference evidence is deferred (D4).
- A `trace_id` on responses is new work (audit slice S7).

### R2.13 Canonical responsibility boundaries (converged with Plan B R1.10)
| Owner | Owns |
|---|---|
| Deterministic mechanisms | candidate identity and IDs; binding eligibility and state; deterministic ranking/order; validators; approval and execution gates |
| Model roles | clue interpretation; bounded investigation; annotation; synthesis; wording where qualification and policy permit; substantive work per routing mode |
| Graphify | hint/pointer within proven scope; never proof |
| Qualification | eligibility |
| Learning | preference among eligible routes only |
| ExperienceStore | existing role only |
| URI-Memory | future durable, decaying, invalidatable reference evidence |
| Unified router | the one routing authority |

### R2.14 Governance changes this revision depends on (recorded, not implemented)
- M33.2 amendments G1 (wording), G2 (explicit selection / `SUPPRESS`), and G3 (route learning is not calibration) are in `docs/architecture/M33_2_EDGE_SECOND_BRAIN_CANONICAL_ARCHITECTURE.md` (amendment block dated 2026-09-26).
- Identity: the `URI-REFERENCE-CLARIFICATION` planning identity is registered in `URI_STATE.yaml` → `planning_artifacts`. §2's `URI-ARN-CLARIFICATION` placeholder is superseded by R1.1.
- `URI-RAR` remains `EXPERIMENTAL` / not adopted.
- No INT event exists.

---

## REVISION R3 — RG-0 bounded contract repair: RG-0-F1, RG-0-F2, RG-0-F3 (2026-09-26). SUPERSEDES conflicting text in R2, R1, and the draft.

**Source.** The independent RG-0 cross-plan re-audit of R2 returned `BOUNDED_REPAIR_REQUIRED` with four findings: RG-0-F1, RG-0-F2, RG-0-F3 (this plan) and a B-R7 interface clarification (Plan B, revision R2). The RG-0 auditor found that no new User product decision is required. The findings reached this repair pass through the User's repair instruction; the RG-0 report itself is not stored in the repository (disclosed in `docs/plans/M33_3_CROSS_PLAN_STATE.md` §5a).

**Precedence.** R3 wins over R2, R1, and the draft wherever they conflict. Earlier text stays unchanged as history, except for short `[… by R3.x]` markers beside the passages R3 replaces.

**Authorization.** Still DRAFT and not frozen. Implementation is **not authorized**. R3 changes no code and no protected artifact.

**Evidence inspected for R3** (repository at `7ae6d22`):
- No `ClarificationContract`, `BindingService`, `CHOOSE_ATTRIBUTE`, attribute-option type, or clarification response type exists in any Python file. Every type named in R3 is **planned** and conceptual.
- ARN.1 `UserClue(axis, value, received_at, category=USER_CLUE)` is at `uri_core/core/arn/models.py:86`. `ARNEngine.apply_user_clue` (`uri_core/core/arn/engine.py:139`) eliminates every candidate whose normalized `metadata[axis]` differs from the clue value. `get_clarification_recommendation` (`engine.py:218`) chooses an axis on which every active candidate has a value and which splits them into at least two groups. Both operate on ARN.1 `Candidate.metadata`, not on `RARCandidate`. R3 reuses their record shape and matching semantics through a planned adapter `[SUPERSEDED by R4.6 — ported into S1 with parity tests under tests/; no uri_core import from uri_v1 (F-5)]`. It does not modify ARN.1 or drive the ARN.1 engine state machine.
- `ApprovalStore` (`uri_core/core/approval_store.py:18-26, 108-118, 298-353`) stores each proposed action's exact `arguments` and an `arguments_fingerprint` (SHA-256 over `capability_id` and `arguments`). `consume()` is single-use and fails closed when the fingerprint of the requested arguments differs from the approved one.
- `DeterministicRARTrace.candidate_scores: Tuple[Tuple[str, float], ...]` is at `uri_v1/turn/rar_deterministic.py:88` (details in R3.3).

### R3.1 (RG-0-F1) Complete `CHOOSE_ATTRIBUTE` interaction contract

R2.2 allowed `CHOOSE_ATTRIBUTE` with zero candidate options and 2 to 5 attribute options, but the contract, render request, click payload, and binding path were candidate-only. R3.1 completes the contract. It supersedes the `CHOOSE_ATTRIBUTE` row's count rule in R2.2 and R1.6's sentence "An attribute option binds a `UserClue(axis, value)`, not a candidate ID" (retained in substance, specified below).

**A. Attribute option representation (planned; no such type exists today).**

```python
class ClarificationOptionKind(str, Enum):
    CANDIDATE = "CANDIDATE"   # selecting it confirms a candidate_id
    ATTRIBUTE = "ATTRIBUTE"   # selecting it supplies a UserClue(axis, value); it never confirms a candidate

@dataclass(frozen=True)
class AttributeOption:
    option_key: str                         # "a1".."a5"; stable within one ambiguity_id; a namespace separate from candidate slots "s1".."s5"
    axis: str                               # a CandidateFact.key from the closed vocabulary (§4); one axis per contract  [S1: title/type/owner/recency only, R4.6]
    value: str                              # the grounded CandidateFact.value, verbatim as produced by the builder
    member_candidate_ids: Tuple[str, ...]   # scope candidates whose fact on `axis` equals `value`; URI-side only; never rendered; never sent to a model
    fact_sources: Tuple[str, ...] = ()      # CandidateFact.source locators behind the value where the producer supplies them
                                            # (planned per R2.11 and Plan B R2; empty until that producer exists)
```

Additions to the planned `ClarificationContract` (§4):
- `attribute_axis: Optional[str]`: set only for `CHOOSE_ATTRIBUTE`.
- `attribute_options: Tuple[AttributeOption, ...]`: 2 to `max_options` entries for `CHOOSE_ATTRIBUTE`; empty for every other kind.
- `scope_candidate_ids: Tuple[str, ...]`: the full ambiguous candidate set that the attribute split partitions. It may exceed `max_options` and is never displayed. For the other kinds it equals the IDs in `candidates`.
- `candidate_set_fingerprint` covers the fingerprints of the scope candidates and, for `CHOOSE_ATTRIBUTE`, every `(option_key, axis, value, member_candidate_ids)` tuple.

Builder rules (deterministic):
- The axis follows ARN.1 `get_clarification_recommendation` semantics. Every scope candidate must have a grounded value on the axis. The axis must split the scope into 2 to `max_options` groups, and no group may equal the whole scope. Ties break as in ARN.1: smallest largest group, then smallest size spread, then fixed closed-vocabulary order.
- There is one option per distinct value. Member sets are non-empty and disjoint, and their union is the scope.
- `candidates` is empty. No candidate can be selected from a `CHOOSE_ATTRIBUTE` contract. `overflow_count` is 0, because the options cover every scope candidate.
- If no axis qualifies, `CHOOSE_ATTRIBUTE` is not built. The builder falls back to `CHOOSE_ONE` with top-5 plus overflow (§4.2 rule 3).
- A contract never mixes candidate options and attribute options.

Contract validation additions (deterministic, raises on violation):
- `CHOOSE_ATTRIBUTE`: `candidates` is empty; 2 ≤ `len(attribute_options)` ≤ `max_options`; option keys are unique and in `a1`..`a5`; `attribute_axis` is in the closed vocabulary and equals every option's `axis`; values are unique after normalization; member sets satisfy the builder rules; `scope_candidate_ids` ⊆ the `RARQuery` candidate IDs; no scope ID is in `contrast_exclusions`.
- Every other kind: `attribute_options` is empty and `attribute_axis` is `None`.

**B. Rendering.**
- `RenderRequest` for `CHOOSE_ATTRIBUTE` (planned):
  ```json
  {"kind":"CHOOSE_ATTRIBUTE","reference":"the report","axis":"owner","scope_count":7,
   "attribute_slots":{"a1":{"value":"Priya"},"a2":{"value":"Finance team"}}}
  ```
  It carries no candidate slots, no candidate titles, and no member IDs.
- The output is `{"question": …, "labels": {"a1": …, …}}`.
- Validator changes:
  - V-SLOT-UNKNOWN, V-SLOT-MISSING, and V-EXTRA-OPTION apply to the `a*` namespace.
  - An `s*` key in a `CHOOSE_ATTRIBUTE` output, or an `a*` key in a candidate-kind output, is V-SLOT-UNKNOWN.
  - V-UNSUPPORTED-FACT checks labels against that slot's `value`, the `axis`, `reference`, and `scope_count`.
  - V-SELECTION also rejects wording that presents an attribute value as the chosen object (for example, "I'll use the one from Priya").
- Deterministic template: "I found {scope_count} {type_noun}s matching "{original_reference}". Which {axis_noun}?" Each label is the option's `value`.
- Presentation: URI sets `option_kind = ATTRIBUTE` on each attribute option from the contract, never from renderer output. Candidate options carry `option_kind = CANDIDATE`. The UI must render attribute options visibly as narrowing choices (filters), distinct from candidate-object choices. The exact visual treatment belongs to S12. The escape option is appended, as for every kind.

**C. User response payloads (planned).**

```
CANDIDATE:   {ambiguity_id, response_kind: "CANDIDATE", candidate_id, candidate_set_fingerprint}
ATTRIBUTE:   {ambiguity_id, response_kind: "ATTRIBUTE", option_key, candidate_set_fingerprint}
FREE_INPUT:  {ambiguity_id, response_kind: "FREE_INPUT", text}
```

- The `ATTRIBUTE` payload carries no `candidate_id`. The `candidate_id` field is never overloaded to carry an option key or an attribute.
- The payload does not need to carry `axis` or `value`. URI reads them from the stored contract. Display text is never trusted.
- §7's click payload `{ambiguity_id, candidate_id, candidate_set_fingerprint}` becomes the `CANDIDATE` form above.

**D. Validation of an `ATTRIBUTE` response** (in order; any failure → `REJECTED`, no clue is applied, and the rebuild path of §7 runs):
1. `ambiguity_id` identifies a stored contract in a state that BindingService admits (R3.2 table), in the same session, and not expired.
2. `response_kind` matches the contract kind. `ATTRIBUTE` is valid only for `CHOOSE_ATTRIBUTE`; `CANDIDATE` only for `CHOOSE_ONE` / `CONFIRM_ONE`; `FREE_INPUT` for every kind.
3. `option_key` exists in the stored `attribute_options`. Unknown, invented, or stale option keys are rejected.
4. `candidate_set_fingerprint` equals the stored value, and each member candidate's current fingerprint equals its stored fingerprint.
5. `axis` and `value` come only from the stored contract. If a client also sends them, they must equal the stored values, otherwise the response is rejected.
6. The option's member set is non-empty and is a subset of the current `RARQuery` candidate IDs.
- A contract accepts at most one successful response. Replays are rejected.

**E. Resolution transition (canonical).**

```
CHOOSE_ATTRIBUTE (ambiguity_id A, round k)
  --ATTRIBUTE(option_key) validated (D)-->
UserClue(axis, value), category USER_CLUE, recorded as session-local evidence (R2.1)
  --> deterministic narrowing: candidate set := the option's member_candidate_ids, re-checked against current facts
  --> new RARQuery(same reference_expression, narrowed candidates, same local_evidence, no selected_ui_id)
  --> deterministic RAR re-run (A9 unchanged)
  --> RESOLVED / AMBIGUOUS / UNKNOWN
  --> R2.3 trigger table applied to the new result, as a new round (new ambiguity_id, round_index k+1), with the rule below
```

- **Attribute selection is not candidate confirmation.** It never emits `selected_ui_id` and never directly produces `CONFIRMED`.
- If the re-run returns `RESOLVED`, or the narrowed set holds exactly one candidate and RAR does not return `UNKNOWN`, that candidate enters R2.3's "exactly 1 candidate" rows:
  - `TENTATIVE` only if the R2.9 check passes. The attribute clue counts as session evidence under R2.9(c), and the action's `wrong_binding_impact` must be `NONE` or `RECOVERABLE`.
  - Otherwise `CONFIRM_ONE`.
  - The candidate becomes `CONFIRMED` only through an explicit `CONFIRM_ONE` confirmation or a candidate click.
  - A `RESOLVED` / `DETERMINISTIC_ANCHOR` result on the narrowed set does **not** take R2.3's first row ("binding `CONFIRMED`"), because its separation came from the attribute clue, not from an anchor independent of the clue.
- `AMBIGUOUS` → `CHOOSE_ONE`, or `CHOOSE_ATTRIBUTE` on a **different** axis if the set is still flat. An axis already answered for this reference is never asked again.
- `UNKNOWN` with a narrowed set of exactly one candidate → `CONFIRM_ONE` (never `TENTATIVE`, because RAR did not support the candidate). `UNKNOWN` otherwise → `FREE_INPUT_ONLY` if the reference is required.
- Progress: an attribute selection strictly shrinks the candidate set (the options are non-degenerate by construction), so it counts as progress under R1.8(a). Every attribute round is charged to the R1.8(b) per-turn budget.

**F. Escape path.** "None of these / Enter something else" is always present. Free input on a `CHOOSE_ATTRIBUTE` contract is handled as follows:
1. If the normalized text equals exactly one rendered attribute value of this contract, it is treated as that option. The same validation (D) and transition (E) apply.
2. Otherwise the §7 free-input path runs over the scope candidate set (RAR re-run with the text as local evidence).
   - A qualified model may interpret the text into a proposed `(axis, value)` only under D3. The proposal is accepted only if the axis is in the closed vocabulary and the value equals a grounded fact of at least one scope candidate. It then enters transition E as a `UserClue`. Otherwise the text remains evidence text only.
3. `UNKNOWN` → a new bounded cycle with a new `ambiguity_id` (R1.7 / R2.7 sources).
- Safeguards are unchanged: R1.8 (a) and (b), expiry, and no silent broadening.

### R3.2 (RG-0-F2) Change / rebind / redo lifecycle

R3.2 supersedes R2.4's state diagram. R2.4's edge `CHANGED --redo recoverable action on Y--> REDONE` allowed a redo without an explicit prior rebind, and §7's BindingService admitted only a pending ambiguity. R2.4's state `CHANGED` is renamed `CHANGE_PENDING` and no longer has a direct edge to redo.

```
PENDING --candidate click / CONFIRM_ONE confirm (BindingService)--> CONFIRMED --execute--> APPLIED
(exactly 1 candidate, R2.9 check passes) --> TENTATIVE(X) --execute (impact NONE / RECOVERABLE)--> TENTATIVE_APPLIED(X)   shown "Using X · Change"
TENTATIVE(X) --Change before execution: rebind through BindingService--> CONFIRMED(Y)          (no redo needed)
TENTATIVE_APPLIED(X) --user selects Change--> CHANGE_PENDING(X)
      (a new Change round: new ambiguity_id, linked change_of = the original ambiguity_id and the applied-action reference; X's result is untouched)
CHANGE_PENDING --candidate Y selected or supplied--> REBIND_CHECK
REBIND_CHECK --BindingService validates rebind eligibility--> CONFIRMED(Y)                       (rebound)
REBIND_CHECK --any check fails--> REJECTED --> Change round rebuilt (still CHANGE_PENDING) or CHANGE_ABANDONED
CONFIRMED(Y) [from a Change round] --fresh execution authorization: execution gate, execution policy, approval for Y's arguments--> REDO_AUTHORIZED --execute--> REDONE(Y)
CONFIRMED(Y) [from a Change round] --authorization denied, or approval declined / expired--> REDO_NOT_EXECUTED   (X's result kept; the User is told the redo did not run)
REDONE(Y), when the X-derived result was user-edited --> VERSIONED   (requires S11; see I-6)
CHANGE_PENDING --timeout / cancel / unrelated turn--> CHANGE_ABANDONED --> TENTATIVE_APPLIED(X), unchanged
PENDING --timeout / new unrelated turn--> EXPIRED
```

"Candidate Y selected or supplied" means one of:
`[REFINED by R4.4 / R4.5 (D5) — a click or confirmation counts only if the fresh re-run returns Y through ACTIVE_UI; free input supplies Y directly only for a CERTAINTY-class result; a HEURISTIC result offers Y through CONFIRM_ONE; basis DETERMINISTIC_ANCHOR alone is not sufficient]`
- a click on a rendered candidate;
- a `CONFIRM_ONE` confirmation;
- free input that makes RAR return `RESOLVED` with basis `DETERMINISTIC_ANCHOR` independently of any attribute clue (§7 "If RAR returns RESOLVED, bind and resume").

An attribute selection inside a Change round narrows and re-resolves (R3.1 E). It never supplies Y by itself. In the Change round, X is shown as the current binding and is not offered as a selectable option.

**Invariants.**
- **I-1 (no redo before validated rebind).** `REDO_AUTHORIZED` is reachable only from a `CONFIRMED(Y)` that BindingService produced in a Change round. There is no edge from `CHANGE_PENDING` or `REBIND_CHECK` to redo.
- **I-2.** Y ≠ X. Choosing X again closes the round as `CHANGE_ABANDONED`, with no redo.
- **I-3.** Change after execution starts only from `TENTATIVE_APPLIED`, and only for an action whose `wrong_binding_impact` is `NONE` or `RECOVERABLE` (unchanged from R2.4). For `CONFIRMED` / `APPLIED` actions and every `CONSEQUENTIAL` action, a correction after execution is a new request (§7, retained).
- **I-4.** The redo re-executes the same recorded action (same capability and action). Only the reference argument or arguments are rebound from X to Y. Any other argument change is a new request, not a redo.
- **I-5 (fresh authorization).** The redo is a new execution. It passes every gate as if it were the first execution: the execution policy, the `wrong_binding_impact` gate (with binding `CONFIRMED(Y)`), and the approval gate. The redo uses the same route policy as the original action (R2.5, retained).
- **I-6 (edited-result preservation).** If the User edited the X-derived result before selecting Change, the redo on Y must never silently destroy, overwrite, or replace that edited result. The R1.9 `FROZEN_REQUIRED` gate "an edited result is never overwritten by a redo" is retained.
  - **Dependency on S11.** Result-version ownership and storage belong to S11 (`PLAN_REQUIRED`). This plan does not design them.
  - Any slice that implements post-execution redo before S11 exists must fail closed: if it cannot establish that the X-derived result is unedited, or that the edited version is preserved, the redo must not write over it. The preservation mechanism is S11's decision.

**BindingService admissible source states** (supersedes §7's single check "the ambiguity is pending"):

| Source state | Admissible for binding? | Result on success |
|---|---|---|
| `PENDING` (initial round: `CHOOSE_ONE`, `CONFIRM_ONE`, `CHOOSE_ATTRIBUTE`, `FREE_INPUT_ONLY`) | yes | `CONFIRMED` for a candidate response; `UserClue` and re-resolution for an attribute response (R3.1 E) |
| `TENTATIVE(X)`, not yet executed | yes, for Change | `CONFIRMED(Y)`; no redo |
| `CHANGE_PENDING(X)`, opened from `TENTATIVE_APPLIED` with impact `NONE` / `RECOVERABLE` | yes | `CONFIRMED(Y)`, then the redo path (I-5) |
| `TENTATIVE_APPLIED(X)` directly, with no Change round opened | no | Change must first open a `CHANGE_PENDING` round with its own contract |
| `CONFIRMED`, `APPLIED`, `REDO_AUTHORIZED`, `REDONE`, `VERSIONED`, `REDO_NOT_EXECUTED`, `EXPIRED`, `REJECTED`, `CHANGE_ABANDONED` | no | — |

**Rebind checks in a Change round** (all, in order; any failure → `REJECTED`, and X's binding and result stay untouched):
1. Same active session. `ambiguity_id` identifies the active Change-round contract (not the original, closed round), and its `change_of` link points to a binding that is `TENTATIVE_APPLIED` in this session.
2. The Change round has not expired.
3. Candidate membership: Y is in the Change contract's candidates, which are a subset of the `RARQuery` candidate set. Invented IDs are rejected.
4. Freshness: Y's current fingerprint equals the stored fingerprint, and the X-derived applied result still exists.
5. Provenance where required: if the contract requires producer provenance (for example, a dependent slot under R2.11), Y carries a provenance locator consistent with its parent binding.
6. Y ≠ X (I-2).
7. The recorded action's declared `wrong_binding_impact` is `NONE` or `RECOVERABLE`. It is re-read from the action's declared metadata, not from a cached value. Undeclared means `CONSEQUENTIAL`, so Change-redo is rejected and the correction becomes a new request.
- The execution policy and approval are **not** BindingService checks. They run at `REDO_AUTHORIZED` (I-5).

**Approval behavior.**
- Approvals are argument-bound and single-use. `ApprovalStore` fingerprints `(capability_id, arguments)`, and `consume()` fails closed on any argument drift.
- An approval for X's arguments never authorizes Y. No approval, grant, or cached authorization is transferred to Y, reused, or re-fingerprinted.
- The redo creates a new proposed action with Y-derived arguments, a new `action_id`, and a new `arguments_fingerprint`. If the action's `approval_requirement` requires approval, the User approves the redo explicitly. If approval is declined or expires, the state is `REDO_NOT_EXECUTED`.

**Evaluation event.** R2.12 is unchanged. The `wrong_reference` event records prior X, new Y, and the redo outcome (`REDONE`, `VERSIONED`, or `REDO_NOT_EXECUTED`).

### R3.3 (RG-0-F3) RAR score terminology

R3.3 corrects R1.6's "RAR ranks are ordinal, and no scores exist" and R2.1's "RAR ranks are ordinal and carry no scores". Both statements are factually wrong. Three separate concepts apply.

1. **Deterministic diagnostic / discrimination scores: these exist.**
   - `DeterministicRARTrace.candidate_scores` (`uri_v1/turn/rar_deterministic.py:88`) holds `(candidate_id, float)` pairs.
   - The values come from `score_candidate_relevance` ("discriminating term overlap score", line 135), which uses term document frequency over the candidate pool and the target-type hint.
   - They are populated on the `TERM_DISCRIMINATION` path and are empty by default on the other paths.
   - RAR uses them internally: a `RESOLVED` outcome on that path also requires every substantive query token to match the winner and a score margin of at least 0.5 over the runner-up (lines 874-887). The code comment states that the highest lexical score alone must not bind.
   - They are deterministic, path-dependent diagnostic values. They are not comparable across queries and are not produced on every path.
2. **Calibrated confidence or probability: NOT established.**
   - The existence of `candidate_scores` does not make them confidence. They are not probabilities, and no calibration exists.
   - `RARResolution.raw_confidence` exists as an optional field (`uri_v1/turn/rar_contracts.py:155`), but deterministic RAR does not set it.
   - §4's exclusion of numeric confidence from the clarification contract stands. No part of this plan may treat `candidate_scores` as confidence, as a probability, or as a TENTATIVE threshold.
3. **Learned ranking or preference: NOT authorized inside frozen RAR.**
   - `rar_deterministic.py` is A9-protected and frozen. Learned ranking is not added to it.
   - The R2.1 session-evidence adjunct runs after RAR, separately, on session-local evidence only. Durable learned evidence stays deferred to URI-Memory (D4).
   - This correction does not justify moving any learning into RAR.

Consequences:
- R2.1's conclusion is unchanged. The learned-evidence weighting cannot live inside RAR because `rar_deterministic.py` is A9-protected and frozen, not because RAR lacks scores.
- R1.6's "clearly separated" hypothesis keeps its driver-rule-tier definition. Using `candidate_scores` to choose between top-N and attribute-first presentation is at most an [EXPERIMENT] candidate that reads them as deterministic diagnostics. It would need its own qualification and is not adopted here.
- R2.9(a) "RAR driver-rule separation" means RAR's own resolution outcome, not a reinterpretation of the scores.
- RAR behavior and A9 are unchanged.

### R3.4 Unchanged by R3
Everything else in R2 stands, including D1–D4, R2.5 routing, R2.6 `wrong_binding_impact`, R2.7 Graphify scope, R2.8 pre-ask investigation, R2.9 TENTATIVE check, R2.11 bundles, and R2.12 events. The source-to-candidate interface distinction (existing `RARQuery` as the RAR-facing projection; the provenance-bearing evidence envelope as future S4 work) is recorded in Plan B revision R2 and applies to R2.8, R2.11, R3.1 `fact_sources`, and R3.2 check 5.

---

## REVISION R4 — Post-RG-0R addendum: User decisions D5 and D6, S1 scoping evidence F-1 … F-6 (2026-09-26). SUPERSEDES conflicting text in R3, R2, R1, and the draft.

**Source.**
- The focused independent re-audit RG-0R returned `RG_0R_ACCEPTED`: no blocking defects; RG-0-F1, RG-0-F2, RG-0-F3, and the B-R7 clarification accepted; planning phase may close; implementation not authorized. Record: `docs/plans/M33_3_RG0R_FOCUSED_INDEPENDENT_REAUDIT_REPORT.md`.
- The subsequent S1 pre-implementation scoping audit returned `S1_SCOPE_READY_WITH_BOUNDED_FOLLOWUP`. The follow-up is governance recording only. The User made decisions D5 and D6 during that audit. Its report is not stored in the repository; this revision and `docs/plans/M33_3_S1_STATE.md` are the durable record of its decisions and findings as relayed.
- Every F-item below was re-checked against the frozen source in this recording pass. Line numbers refer to `uri_v1/turn/rar_deterministic.py` (SHA-256 `e02af25b…b649`, unchanged) and `uri_v1/turn/rar_contracts.py` (SHA-256 `4cc9aa43…6819`, unchanged).

**Precedence.** R4 wins over R3, R2, R1, and the draft wherever they conflict. Earlier text stays unchanged as history, except for short `[… by R4.x]` markers beside the passages R4 refines or supersedes.

**Authorization.** R4 changes no code, no fixture, and no protected artifact. It does not alter frozen RAR or A9 behavior: the classification below lives outside frozen RAR. `CODE_IMPLEMENTATION_AUTHORIZED: NO`. `S1_IMPLEMENTATION_AUTHORIZED: NO`.

### R4.0 User decisions (2026-09-26)

- **D5 [USER] — CONFIRMED authority.** Only certainty-tier deterministic rules may produce `CONFIRMED`:
  - `EXACT_ID`;
  - `EXACT_ALIAS`;
  - `ACTIVE_UI`;
  - `CURRENT_ATTACHMENT`, only when tied to `deterministic_anchor.current_attachment_id`;
  - `EXACT_TITLE`, only when tied to `deterministic_anchor.unique_title_match` or an equivalent unique verbatim-title anchor.

  Other deterministic `RESOLVED` rules are only TENTATIVE-eligible, through the R2.9 check. `CONSEQUENTIAL` or undeclared `wrong_binding_impact` → `CONFIRM_ONE`. The same authority classification applies to typed free input. The classifier lives outside frozen RAR/A9.
- **D6 [USER] — S1 boundary.** S1 is the full state-file S1: the deterministic clarification/binding core, the deterministic template, the RenderValidator, and the `ClarificationBundle` / multi-reference contract. S1 is **not** split into S1 and S1b.

### R4.1 Evidence findings (S1 scoping audit; re-verified in this pass)

- **F-1 — basis cannot decide authority.** Frozen RAR sets `basis=RARBasis.DETERMINISTIC_ANCHOR` on every outcome it returns, including heuristic rules: `ACTIVE_POINTER` (lines 413, 421), `CONTRAST_FILTER` (493, 502), `TYPE_FILTER` (520, 544, 555), `REVISION_RELATION` (578, 587), `TEMPORAL_RELATION` (600–690), the inferred `CURRENT_ATTACHMENT` (723, 734), `TERM_DISCRIMINATION` (766–919), and `NONE` (931–952). `basis` alone therefore cannot determine binding authority. S1 uses `rule_used` plus anchor provenance, per D5.
- **F-2 — truncated ambiguity sets.** Several ambiguity paths truncate `ambiguous_candidate_ids` to two candidates: `prev_cands[:2]` (608), `older_cands[:2]` (631), `latest_cands[:2]` (676), `candidates_list[:2]` (687, 857, 901, 936), `scores[:2]` and `ambiguous_ids[:2]` (899, 905), `top_candidates[:2]` (916). S1 accepts the candidate set exactly as RAR returns it. It does not reconstruct omitted survivors from `RARQuery.candidates`, and it does not modify frozen RAR.
- **F-3 — `clause_text` is unused.** No line of `rar_deterministic.py` reads `RAREvidence.clause_text` (the field is declared at `rar_contracts.py:95`). Free-input re-resolution therefore uses the typed text as the fresh `RARQuery.reference_expression`. Placing the text only in `clause_text` would have no effect.
- **F-4 — groundable attribute axes.** `RARCandidate` (`rar_contracts.py:80–88`) carries `id`, `title`, `candidate_type`, `recency_rank`, `domain_tags`, `owner`, `is_attachment`, `exact_aliases`, `description`. Of the §4 closed fact vocabulary, only `title`, `type`, `owner`, and `recency` are groundable from it in S1. `modified`, `version`, `sender`, `thread_subject`, and `locator` require later S4 evidence producers and stay unavailable in S1.
- **F-5 — zero-import boundary.** No module under `uri_v1/` imports `uri_core` (repository grep, this pass; also `docs/governance/URI_DEVELOPMENT_EVIDENCE_REGISTRY.md` §0). The ARN.1 narrowing semantics S1 needs (`_normalized` matching, `apply_user_clue` elimination at `uri_core/core/arn/engine.py:139`, `get_clarification_recommendation` axis choice at `engine.py:218`) are ported into S1 and checked by parity tests under `tests/`. They are not imported across the boundary.
- **F-6 — exact-ID/alias precedes `ACTIVE_UI`.** RAR evaluates Level 0 (`anchor.exact_id`, then verbatim `reference_expression` against candidate IDs and `exact_aliases`, lines 283–313) before Level 1 `selected_ui_id` (line 319). A re-run carrying the clicked candidate as `selected_ui_id` can therefore return a different rule, or a different candidate. S1 must fail closed unless the fresh re-run returns the clicked candidate through `ACTIVE_UI` (R4.4).

### R4.2 Binding authority classification (the D5 classifier)

A pure deterministic function outside frozen RAR. Inputs: the `RARResolution` (or `DeterministicRARTrace`) and the `RARQuery` that produced it. Output: `CERTAINTY` or `HEURISTIC`. It never reads `basis` as authority (F-1).

| `RESOLVED` with `rule_used` | Provenance condition | Class |
|---|---|---|
| `EXACT_ID` | Level 0 (lines 283–303) | `CERTAINTY` |
| `EXACT_ALIAS` | Level 0 (lines 305–313) | `CERTAINTY` |
| `ACTIVE_UI` | `candidate_id == deterministic_anchor.selected_ui_id` (Level 1, line 319) | `CERTAINTY` |
| `CURRENT_ATTACHMENT` | `candidate_id == deterministic_anchor.current_attachment_id` (Level 1, line 329) | `CERTAINTY` |
| `CURRENT_ATTACHMENT` | any other case, including the `is_attachment` inference path (lines 716–726) | `HEURISTIC` |
| `EXACT_TITLE` | `candidate_id == deterministic_anchor.unique_title_match` (Level 1, line 339) | `CERTAINTY` |
| `EXACT_TITLE` | Level 2 unique title match (lines 350–367) where the normalized `reference_expression` equals the candidate's full title (case and surrounding whitespace only) | `CERTAINTY` (the equivalent unique verbatim-title anchor) |
| `EXACT_TITLE` | Level 2 unique match only through `stem_title` normalization (file extension stripped, delimiters collapsed) | `HEURISTIC` (conservative reading; see R4.11 item 1) |
| `ACTIVE_POINTER`, `TYPE_FILTER`, `CONTRAST_FILTER`, `REVISION_RELATION`, `TEMPORAL_RELATION`, `TERM_DISCRIMINATION`, `NONE`, any other or future value | — | `HEURISTIC` |

- Any `RESOLVED` with `basis = MODEL_SELECTION` is never `CERTAINTY`. A lone model selection yields `CONFIRM_ONE` (R1.5, R2.9, retained).
- An unknown or unmapped rule value is `HEURISTIC` (fail closed).
- `CERTAINTY` → binding `CONFIRMED`, with no clarification. This holds for every `wrong_binding_impact`, because `CONFIRMED` is what the execution gate requires for `CONSEQUENTIAL` actions.
- `HEURISTIC` → TENTATIVE-eligible only. `TENTATIVE` requires the R2.9 check to pass and `wrong_binding_impact` ∈ {`NONE`, `RECOVERABLE`}. Otherwise the result is `CONFIRM_ONE`. `CONSEQUENTIAL` or undeclared impact → `CONFIRM_ONE`.
- R3.1 E is unchanged and stays stricter: a `RESOLVED` result on an attribute-narrowed set never takes the `CONFIRMED` row, because its separation came from the clue.

### R4.3 Replacement trigger table (supersedes R2.3's table; R2.3's other text stands)

| RAR / evidence state | Clarification action |
|---|---|
| `RESOLVED`, class `CERTAINTY` (R4.2) | none; binding `CONFIRMED` |
| `RESOLVED`, class `HEURISTIC`; R2.9 check passes; impact `NONE` / `RECOVERABLE` | none before the proposal; binding `TENTATIVE`; shown as "Using X · Change". Impact is checked at proposal time (R1.5 timing); `CONSEQUENTIAL` or undeclared then raises `CONFIRM_ONE`. |
| `RESOLVED`, class `HEURISTIC`; R2.9 check fails, or impact `CONSEQUENTIAL` / undeclared | `CONFIRM_ONE` |
| exactly 1 candidate without a `RESOLVED` outcome (for example, a lone `MODEL_SELECTION` basis) | R2.3 rows 2 and 3 apply unchanged (R2.9 check; else `CONFIRM_ONE`) |
| `AMBIGUOUS` | `CHOOSE_ONE`, or `CHOOSE_ATTRIBUTE` if the set is flat (R1.6, R3.1, R4.6), over the candidate set exactly as RAR returned it (F-2) |
| `UNKNOWN` / `NO_CANDIDATE`, reference required | `FREE_INPUT_ONLY` |
| `UNKNOWN`, reference not required | none; routing proceeds per R2.5 |

The wrong interpretation "`RESOLVED` + `basis = DETERMINISTIC_ANCHOR` → always `CONFIRMED`" is **not** part of the effective contract.

### R4.4 Candidate click and `ACTIVE_UI` authority (refines §7 click binding, D-5, R1.10, R3.2 "candidate click")

- After the existing BindingService checks (R3.1 D, R3.2 table and rebind checks), BindingService re-runs RAR with the clicked `candidate_id` as `RARDeterministicAnchor.selected_ui_id`.
- The binding becomes `CONFIRMED` only if the fresh re-run returns **all** of: outcome `RESOLVED`; `rule_used == ACTIVE_UI`; `candidate_id` equal to the clicked candidate.
- Any other re-run result, including `EXACT_ID` or `EXACT_ALIAS` returning the same or a different candidate, is `REJECTED` (fail closed). No binding is created, the RAR-returned alternative is never bound, and the §7 rebuild path runs.
- A `CONFIRM_ONE` confirmation binds through the same path and the same check.
- Frozen RAR ordering is not changed. The check lives in BindingService.

### R4.5 Free-input authority (refines §7 "Free input", R3.1 F, R3.2 "Candidate Y selected or supplied")

- Typed text re-resolves through a fresh `RARQuery` whose `reference_expression` is the typed text (F-3). The candidate set is the contract's candidate set (scope set for `CHOOSE_ATTRIBUTE`), never silently broadened. Other query fields follow the stored query.
- The result is classified by R4.2 exactly like any RAR result (D5):
  - `CERTAINTY` → `CONFIRMED`;
  - `HEURISTIC` → the R2.9 check and impact, as in R4.3 (`TENTATIVE` or `CONFIRM_ONE`);
  - `AMBIGUOUS` → next round; `UNKNOWN` → a new bounded cycle (R1.7, R2.7).
- §7's "If RAR returns RESOLVED, bind and resume" means: bind with the state R4.3 assigns, not always `CONFIRMED`.
- **In a Change round (R3.2):** free input supplies Y directly only when the result is `CERTAINTY` (then `REBIND_CHECK`). A `HEURISTIC` result offers Y through `CONFIRM_ONE` inside the Change round. `TENTATIVE` is never a rebind outcome, because I-1 requires `CONFIRMED(Y)` before any redo.
- R3.1 F.1 (text equal to a rendered attribute value) is unchanged. R3.1 F.2's model interpretation of text into `(axis, value)` under D3 is not part of S1 (`docs/plans/M33_3_S1_STATE.md`).

### R4.6 Attribute narrowing in S1 (refines R3.1 A builder rules and R1.6)

- S1 attribute axes are exactly `title` (`RARCandidate.title`), `type` (`candidate_type`), `owner` (`owner`), and `recency` (from `recency_rank`, rendered deterministically) (F-4).
- An axis qualifies only if every scope candidate has a grounded value on it. A candidate with `owner = None` makes the `owner` axis non-qualifying for that scope.
- `modified`, `version`, `sender`, `thread_subject`, and `locator` are unavailable until S4 evidence producers exist. `domain_tags`, `description`, `is_attachment`, and `exact_aliases` are not attribute axes.
- `scope_candidate_ids` equals RAR's `ambiguous_candidate_ids` exactly (F-2). It is never re-expanded from `RARQuery.candidates`. `overflow_count` counts only candidates RAR returned.
- The axis choice, tie-break, and clue matching are S1 ports of ARN.1 semantics (F-5). R3.1's "planned adapter" over ARN.1 is superseded by this port: there is no import of `uri_core` from `uri_v1`.

### R4.7 S1 boundary (D6; refines §13 P1, §15, and the cross-plan state file S1 row)

- S1 is the full state-file S1: the deterministic clarification/binding core (contracts, builder, trigger, D5 classifier, R2.9 check, session adjunct, BindingService, lifecycle states, stop safeguards), the deterministic template, the RenderValidator, and the `ClarificationBundle` / multi-reference contract.
- It is not split into S1 and S1b.
- The frozen scope, deferred slices, test battery, file-impact map, implementation order, stop conditions, and protected hashes are in `docs/plans/M33_3_S1_STATE.md`.

### R4.8 Marker index (R4 markers added to earlier text)

- §3 D-5; §4.1 row 1; §7 click binding and free input — R4.4, R4.5.
- R1.6 (`CHOOSE_ATTRIBUTE` reuse) and R1.10 (click binding) — R4.4, R4.6.
- R2.3 table row 1 — R4.2, R4.3.
- R3.1 evidence note (ARN.1 adapter) and R3.1 A (`axis`) — R4.6.
- R3.2 "Candidate Y selected or supplied" — R4.4, R4.5.
- Cross-plan audit report §3 Case A — COR-7 in that report.

### R4.9 Unchanged by R4

Everything else in R3, R2, and R1 stands: D1–D4, R2.5 routing, R2.6 `wrong_binding_impact`, R2.9 (its clause (a) still means RAR's own resolution outcome; R4.2 decides only whether that outcome is `CERTAINTY` or `HEURISTIC`), R2.11 bundles, R3.1 contract, R3.2 lifecycle and invariants I-1 to I-6, R3.3 score terminology. Frozen RAR, `rar_contracts.py`, A9, and the frozen Batch A battery are unchanged.

### R4.10 Status

`PLANNING_CLOSED_RG0R_ACCEPTED_R4_RECORDED`. Planning phase closed per RG-0R. S1 scope recorded as `S1_SCOPE_READY_FOR_IMPLEMENTATION_REVIEW`. Implementation is **not authorized**.

### R4.11 Items for the implementation-authorization review (non-blocking)

1. **`EXACT_TITLE` Level 2 and `stem_title`.** D5 admits "an equivalent unique verbatim-title anchor". RAR's Level 2 ("Strict Verbatim Title Match") also matches after `stem_title` normalization (extension stripped, delimiters collapsed). R4.2 treats only a case/whitespace-normalized full-title match as `CERTAINTY`, and a stem-only match as `HEURISTIC`. This is the conservative (fail-closed) reading. The User may widen it. It does not block S1 scope.
2. **R4 fidelity.** R4 records decisions and findings relayed from the S1 scoping audit. The findings were re-verified against source here, but R4 itself has not been independently re-audited. The implementation-authorization review should confirm R4 against D5, D6, and F-1 to F-6.

---

## 0. Acceptance criteria for this plan (defined before drafting)

- AC-1: Every architectural claim about existing code cites a file that was inspected in this session.
- AC-2: The bare "ARN" identity collision is resolved explicitly, not silently.
- AC-3: RAR holds every decision listed in the planning prompt (trigger, type, candidate set, IDs, rank, limit, provenance, binding contract, resolution state). The renderer holds none.
- AC-4: The design reuses existing mechanisms where they fit and names each one.
- AC-5: Rendering is not an availability dependency. A deterministic template path exists for every ARN interaction kind.
- AC-6: Edge OFF leaves RAR, ARN state, binding, and memory fully functional.
- AC-7: Every gate is classified `FROZEN_REQUIRED` / `CANDIDATE_THRESHOLD_TO_BE_ESTABLISHED` / `INFORMATIONAL`. No target percentage appears without evidence. Unknown thresholds are `UNMEASURED` with a method to establish them.
- AC-8: No sub-1B model is selected.
- AC-9: The plan carries forward the Batch A lessons that apply (per-row provenance, untruncated text, diagnostic-text exclusion, battery pre-audit, hash anchors before runs).
- AC-10: All 17 architecture questions from the prompt have a recommended answer.

---

## 1. Evidence inspected (repository-first)

| Area | Source inspected | Relevant finding |
|---|---|---|
| Governance | `docs/governance/URI_STATE.yaml` (lines ~100, 149-171, 206-214, 353-369) | Bare `ARN` = `AMBIGUOUS_BARE_ALIAS_FORBIDDEN`. `URI-ARN-PRODUCTION` = `ARN.1`, `CLOSED_VERIFIED`, parent PAUSED, ARN.2 not authorized. `EXP-ARN-URIV1` = research in `uri_v1/arn/`, evidence only. `active_continuation` = `M33_3_BATCH_A_FROZEN_NEXT_IS_ARN_PLANNING_ONLY`. |
| Production ARN.1 | `uri_core/core/arn/models.py`, `engine.py`, `integration.py` | ARN.1 is retrieval-narrowing after NOT_FOUND. It has `Candidate(candidate_id, label, metadata)`, `UserClue(axis, value)`, `EliminatedCandidate`, `EvidenceCategory` with a no-promotion rule (`EDGE_DEDUCTION` cannot become `VERIFIED_FACT`), and `get_clarification_recommendation()` which picks a discriminating metadata axis and non-degenerate candidate groups. It never authors question text. |
| Research ARN | `uri_v1/arn/question_framing.py`, `question_validator.py`, `uncertainty_contracts.py`, `resolution_contracts.py` | Method C (model framing, deterministic validator, deterministic Method A template fallback) exists and was measured in A2.8A (93.9% validity, no observed critical-omission failure, on a 12-case corpus). `QuestionValidator` has presupposition, atomicity, grounding, and relevance gates. `AvailableCapability.ASK_USER` and `ResolutionRequirementStatus.UNRESOLVABLE_AMBIGUITY` exist as research vocabulary. |
| RAR | `uri_v1/turn/rar_contracts.py` (and `rar_deterministic.py`, A9-protected hash `e02af25b…b649`) | `RARResolution` is tri-state `RESOLVED / AMBIGUOUS / UNKNOWN`. `validate_rar_resolution` already enforces anti-invention: AMBIGUOUS needs at least 2 IDs, every ID must be a member of the candidate set. `RARFailureClass` gives ambiguity types (`MULTIPLE_PLAUSIBLE`, `TEMPORAL_RELATION`, `REVISION_RELATION`, `CONTRAST_SELECTION`, `INSUFFICIENT_METADATA`, `NO_CANDIDATE`, ...). `RARDeterministicAnchor.selected_ui_id` and `RARDriverRule.ACTIVE_UI` already exist. |
| Model evidence | `docs/plans/M35_URIV1_A2_8B_RAR_ARN_MODEL_AMPLIFICATION_REPORT.md` | LFM2.5-350M degraded under scaffolded prompts (16.7% raw, 0.0% with RAR). Root cause recorded as "scaffolding confusion": it treated context headers as instructions. This was a semantic-understanding task, not a rendering task, but it is a direct risk for a sub-1B renderer. |
| Model evidence | `docs/plans/M35_URIV1_A2_8A_ARN_FOUNDATION_REPORT.md` | The report itself says the model, then validator, then template sequence is not frozen as ARN's permanent architecture. |
| Edge (M33.2) | `uri_core/core/edge/contracts.py` | `EdgeReplyRequest(operation="reply")` and `EdgeIntelligenceProvider.propose_response` exist. `EdgeRequest` docstring: "content is never trace material". `EdgeProposal.raw_confidence_semantics` defaults to `UNAVAILABLE`. |
| Batch A mapping | `docs/plans/M33_3_BATCH_A_CONTRACT_MAPPING.md` | GAP-1: no ASK/ABSTAIN disposition in `EdgeProposal`. SB-2: `EdgeSettings.enabled` defaults True when the settings document is missing. |
| Existing clarification | `uri_core/core/approval_resumption.py` | `_clarification_envelope` is a deterministic, never model-generated, option-listing clarification with stable `action_id`s. Precedent for ID-bound options. |
| Existing expiry | `uri_core/core/approval_store.py` | `DEFAULT_EXPIRY_SECONDS = 900`, `STATUS_EXPIRED`, session-mismatch rejection. Precedent for pending-interaction expiry and staleness. |
| Existing pending state | `uri_core/core/turn_state.py` `_project_active_pointer` | `kind: "awaiting_clarification_answer"` projection exists for Brain clarification pauses. |
| Existing loop cap | `uri_core/core/state.py` | `consecutive_clarification_count` exists to stop open-ended clarification. |
| Legacy field clarification | `uri_core/core/clarification.py` | Missing-field questions per task (`noting`, `letter`). Field-filling, not reference disambiguation. Not reused for candidates. |
| Graphify | `uri_core/core/graphify_index.py`, `decision_engine.py:1062` | `GraphifyIndex` holds entry records (capabilities, skills, workflows, memory pointers, services) with `get(entry_id)` and `relevant_subset(goal_text, limit)`. Used as a hint, gated by `GRAPHIFY_HINT_ENABLED`. ARN.1 `integration.py` deliberately does not import Graphify. |

Not inspected, disclosed: the separate protected prototype checkout `C:\Users\cheta\Development\uri-agent` was not opened. All `uri_core` references in this plan mean the `uri_core/` inside this `_V1` worktree at `127c733`. The `uri_ui` Flutter code was only listed, not read; whether it already renders clickable options is unverified.

---

## 2. Identity resolution (the bare "ARN" collision)

The prompt's "ARN" is a user-facing clarification interaction owned by RAR. It matches neither existing identity exactly:

- `URI-ARN-PRODUCTION` (ARN.1) is retrieval narrowing after NOT_FOUND. Extending it means ARN.2, which is not authorized, under a PAUSED parent.
- `EXP-ARN-URIV1` is research evidence only and grants no production ownership.

`[SUPERSEDED by R1.1 / R2.14 — the identity is URI-REFERENCE-CLARIFICATION]` **Recommendation:** register a new explicit identity, `URI-ARN-CLARIFICATION` ("RAR-owned grounded clarification interaction"), as an M33.3 workstream. It reuses concepts from ARN.1 (candidate, user clue, discriminating axis, evidence non-promotion) and from EXP-ARN-URIV1 (Method C validate-then-fallback). It does not unpause the ARN milestone and does not inherit ARN.1's governance history. In prose, this plan uses "ARN-C" as the short form of `URI-ARN-CLARIFICATION`.

The name is a User decision (governance alias table). Planning proceeds with it as a placeholder.

---

## 3. Recommended architecture

`[DIAGRAM SUPERSEDED in part: renderer tier chain by R1.3/R2.5; candidate sources by R2.7/R2.8; single grounding producer per Plan B R1.7; binding payload kinds and admissible binding states by R3.1/R3.2]`

```
Input / session context
  -> Semantic Decode (only where required; unchanged)
  -> RAR deterministic resolution (unchanged; rar_deterministic.py untouched)
  -> RAR ARN-C trigger check            [RAR-owned, deterministic]
  -> RAR builds ClarificationContract    [RAR-owned: candidates, IDs, rank, cap, provenance, binding target]
  -> Renderer chain produces wording     [renderer owns wording only]
       tier 1: <1B renderer (Edge ON and a qualified renderer installed)
       tier 2: Main Brain renderer (Edge OFF, or policy chooses it)
       tier 3: deterministic template (always available)
  -> RenderValidator (deterministic, fail closed; failure drops to next tier)
  -> ClarificationPresentation to UI (options in RAR order, IDs bound, escape option always present)
  -> user click or free input
  -> BindingService validates (pending, not expired, fingerprint fresh)
  -> binding becomes RARDeterministicAnchor(selected_ui_id=...) or new RAR evidence
  -> RAR re-resolves (RESOLVED via ACTIVE_UI rule) and context resolution resumes
  -> Edge / Main Brain / tool path (unchanged authorization)
```

Design choices, with alternatives considered:

**D-1: Where the contract builder lives.** It belongs in the RAR layer, as a new module next to `rar_contracts.py`. It does not go inside `rar_deterministic.py`, which is A9-protected. The builder reads a `DeterministicRARTrace` or `RARResolution` plus the `RARQuery` and produces the contract. Rejected alternative: an ARN-C module that inspects candidates itself. That would move candidate authority out of RAR.

**D-2: How the renderer refers to candidates.**
- Option A: the model echoes real candidate IDs. Rejected, because ID mutation becomes possible.
- Option B (recommended): URI assigns opaque slot keys (`s1`..`s5`) and sends only slots. The model returns text keyed by slot. URI maps slots back to candidate IDs. The model never sees or emits real IDs, so ID mutation is structurally impossible, and the validator still checks slot coverage.
- Option C: the model writes only the question and URI templates the labels. This is the reduced-capability tier, used if B fails qualification.

**D-3: Option order.** The UI renders options in RAR rank order, taken from the contract, never from renderer output order. Ranking mutation cannot reach the user. The validator still flags reordering as a quality signal.

**D-4: The escape option.** "None of these / Enter something else" is a deterministic UI constant, always appended by URI. The renderer may propose an alternative label for it, but presence never depends on the model. This removes a failure mode rather than validating for it.

**D-5: The binding path.** `[REFINED by R4.4 — fail closed unless the re-run returns the clicked candidate through ACTIVE_UI (F-6)]` A click produces `RARDeterministicAnchor(selected_ui_id=<candidate_id>)` and re-runs RAR. This reuses the existing `ACTIVE_UI` rule instead of creating a parallel binding mechanism.

---

## 4. RAR → ARN-C typed contract

The proposed module is `uri_v1/turn/rar_clarification_contract.py`. All records are frozen dataclasses. Field names follow the `RARCandidate` and `RARResolution` style.

```python
class ClarificationKind(str, Enum):
    CHOOSE_ONE = "CHOOSE_ONE"                  # RAR AMBIGUOUS, 2..MAX candidates
    CONFIRM_SINGLE = "CONFIRM_SINGLE"          # [SUPERSEDED by R2.2: CONFIRM_ONE] 1 candidate, non-deterministic basis, risk policy requires confirmation
    FREE_INPUT_ONLY = "FREE_INPUT_ONLY"        # RAR UNKNOWN / NO_CANDIDATE
    # no other kinds in v1  [SUPERSEDED by R2.2 / R3.1: CONFIRM_ONE and CHOOSE_ATTRIBUTE added]

@dataclass(frozen=True)
class CandidateFact:
    key: str                  # from a closed vocabulary: title, type, owner, modified, version, sender, thread_subject, locator, recency
    value: str                # already human-readable, produced deterministically
    source: str               # provenance locator, e.g. "session:turn-12", "graphify:<entry_id>", "attachment:<id>"

@dataclass(frozen=True)
class ClarificationCandidate:
    candidate_id: str         # RARCandidate.id, never altered
    candidate_type: str       # RARCandidate.candidate_type
    rank: int                 # 1-based, RAR-assigned
    display_facts: Tuple[CandidateFact, ...]   # only facts the renderer may use
    discriminating_keys: Tuple[str, ...]       # which fact keys differ across displayed candidates
    plausibility_reason: str  # RARDriverRule / RARFailureClass value, e.g. "TEMPORAL_RELATION" (enum value, not prose)
    fingerprint: str          # hash of (id, version/mtime, recency_rank) for staleness checks

@dataclass(frozen=True)
class ClarificationContract:
    ambiguity_id: str                 # new UUID per ARN-C round
    session_id: str
    turn_id: str
    round_index: int                  # 1-based; see loop limit
    kind: ClarificationKind
    ambiguity_type: str               # RARFailureClass value
    original_reference: str           # RARResolution.reference_expression, verbatim span
    contrast_exclusions: Tuple[str, ...]   # candidate_ids RAR excluded because of negation/contrast (never displayed)
    candidates: Tuple[ClarificationCandidate, ...]   # 0..MAX, rank order, never padded
    overflow_count: int               # grounded candidates pruned beyond MAX (fact, not guess)
    max_options: int                  # frozen constant, 5
    free_input_allowed: bool          # always True in v1
    binding_target: str               # "RARDeterministicAnchor.selected_ui_id"
    candidate_set_fingerprint: str    # hash over ordered candidate fingerprints
    created_at: str
    expires_at: str                   # created_at + expiry (see §7)
    resolution_basis: str             # RARBasis of the triggering resolution
```

Fields deliberately excluded:
- **Numeric confidence.** RAR's `raw_confidence` is not calibrated, and Edge's `raw_confidence_semantics` defaults to `UNAVAILABLE`. `resolution_basis` plus `plausibility_reason` carry the justified signal instead.
- **Full provenance chains.** `CandidateFact.source` is enough to render and audit. Deeper evidence stays in the RAR trace and is referenced by `turn_id`.

**Contract validation (deterministic, raises on violation).** Mirrors `validate_rar_resolution`:
- Every `candidate_id` must be in the `RARQuery` candidate set.
- IDs must be unique.
- There must be at most `max_options` candidates.
- Kind-specific counts: `CHOOSE_ONE` needs at least 2, `CONFIRM_SINGLE` exactly 1, `FREE_INPUT_ONLY` 0. `[SUPERSEDED by R2.2 — kinds and counts: CHOOSE_ONE / CONFIRM_ONE / CHOOSE_ATTRIBUTE / FREE_INPUT_ONLY]`
- No candidate may appear in `contrast_exclusions`.
- Ranks must be contiguous, starting at 1.

### 4.1 Trigger rules (RAR-owned)
`[TABLE SUPERSEDED by R2.3 — Batch A TOOL_CATALOG tiers (AUTO/CONFIRM/DESTRUCTIVE) removed; use binding state + wrong_binding_impact + existing Action effect/risk/approval fields]`

| RAR state | ARN-C action |
|---|---|
| `RESOLVED`, basis `DETERMINISTIC_ANCHOR` `[SUPERSEDED by R4.2 / R4.3 (D5)]` | No clarification. |
| `RESOLVED`, basis `MODEL_SELECTION`, the downstream proposed tool risk tier is AUTO | No clarification. The selection is recorded as model-selected. |
| `RESOLVED`, basis `MODEL_SELECTION`, risk tier CONFIRM or DESTRUCTIVE | `CONFIRM_SINGLE`. The tiers are the Batch A `TOOL_CATALOG` vocabulary. |
| `AMBIGUOUS` (at least 2 IDs, already validated) | `CHOOSE_ONE`. |
| `UNKNOWN` / `NO_CANDIDATE`, and the reference is required by the pending action | `FREE_INPUT_ONLY`. |
| `UNKNOWN`, and the reference is not required | No clarification. The Main Brain proceeds or asks. |

The CONFIRM_SINGLE rule depends on a risk tier that is not known at RAR time in every path. It is an open question (§14, Q-3).

### 4.2 Candidate selection rules (frozen intent)

1. **Hard cap.** `MAX_OPTIONS = 5` candidates, plus the escape option. Fewer when fewer are plausible. Never padded.
2. **Ranking** is RAR's deterministic order. Survivors of the RAR driver-rule filters (TYPE_FILTER, CONTRAST_FILTER, TEMPORAL/REVISION relation) come first. Ties break by `recency_rank` ascending, then by `candidate_id` lexical order. No model ranking.
3. **More than 5 grounded candidates.** Show the top 5 by rank and set `overflow_count = N - 5`. The template states the count ("and N other matches"), which routes the user to free input. The alternative, ARN.1-style axis grouping (`get_clarification_recommendation`) with group options, is deferred to v2 because group options bind sets, not IDs.
4. **Near-identical candidates** (every display fact equal). The builder adds disambiguating facts in fixed order (`locator`, `modified`, `version`, `owner`). If they are still indistinguishable, the builder keeps them, and the validator requires distinct labels. If the facts cannot make them distinct, the template renders the locator.
5. **Conflicting candidate metadata.** Both facts are carried with their own `source`. The renderer may show both. It may not reconcile them.
6. **Staleness and changed sets.** See §7.
7. **Contrast and negation exclusions.** Candidates RAR removed by CONTRAST_FILTER are never displayed. Batch A `RWB-053` showed this only works when negation evidence reaches RAR. ARN-C cannot fix missing negation evidence and must not claim to.

---

## 5. <1B renderer role
`[ROLE REFRAMED by R1.4 / R2.5 — the EXPLAIN-class Edge wording role within the shared Edge Brain qualification; input/output/forbidden rules below still apply to every model tier; CHOOSE_ATTRIBUTE render request and a* slot namespace: R3.1 B]`

**Input.** A `RenderRequest` derived from the contract. It carries only the kind, `original_reference`, slot-keyed display facts, `overflow_count`, and a fixed style instruction. It carries no raw user history, no candidate IDs, no RAR internals, and no scaffolding headers. The A2.8B scaffolding-confusion finding makes a minimal flat prompt mandatory.

```json
{"kind":"CHOOSE_ONE","reference":"the report","slots":{"s1":{"title":"Q3 Budget","modified":"Sep 20","type":"document"},"s2":{"title":"Q3 Budget (draft)","modified":"Sep 12","type":"document"}},"overflow":0}
```

**Output** (strict JSON):

```json
{"question":"Which report do you mean?","labels":{"s1":"Q3 Budget — updated Sep 20","s2":"Q3 Budget draft — Sep 12"}}
```

Optionally, a `post_bind_ack` string when the contract requests it. This is off in v1: after binding, the Main Brain continues, so no extra acknowledgement is needed.

**Permitted:** the question wording; a short label per supplied slot; an optional alternative escape label.

**Forbidden:** everything in the prompt's list. Enforcement is structural where possible (slots instead of IDs, URI-controlled order, URI-appended escape option) and otherwise validated.

---

## 6. Validation and fallback

**RenderValidator** is deterministic, runs on every tier's output including the Main Brain's, and fails closed. Reject if any of the following holds:

| Check | Rule |
|---|---|
| V-SCHEMA | Output is not strict JSON with the exact keys. |
| V-SLOT-UNKNOWN | A label is keyed to a slot not in the request (invented or hallucinated candidate). |
| V-SLOT-MISSING | A requested slot has no label (omission). |
| V-EXTRA-OPTION | The output contains any option beyond the requested slots. |
| V-LABEL-DUP | Two labels are equal after normalization (indiscriminable). |
| V-UNSUPPORTED-FACT | A label or the question contains a number, date, proper-noun token, quoted string, or file-extension token not present in that slot's facts, `original_reference`, or a small closed allowlist. This is token-level provenance, not semantics. |
| V-CROSS-SLOT | A label uses a distinguishing fact value that belongs to a different slot (identity swap). |
| V-SELECTION | The question or labels contain selection or presumption language ("I'll use", "I assume", "I've selected", "going with", "recommended"), or `QuestionValidator` presupposition patterns. |
| V-EXCLUSION | Text mentions an excluded (contrast) candidate's distinguishing fact as an option. |
| V-LENGTH | The question or a label exceeds a length cap. The cap values are `UNMEASURED`; set them from template output length distribution in P2. |
| V-ORDER | The label key order differs from slot order. Flag only: order is URI-controlled, so this is not a rejection. |

Escape-option omission is not a validator check, because URI appends the escape option (D-4). The battery still includes it (§10) to prove the UI invariant.

**Fallback chain.** `[TIER ORDER SUPERSEDED by R1.3/R2.5 — SIMPLE: validated template is primary; the validator still runs on every tier]`
- Tier failure (timeout, error, validator reject) drops to the next tier.
- One regeneration retry per tier. The retry count is `UNMEASURED`; default 0 until P4 shows retries recover useful output within the latency budget.
- The template tier cannot fail validation by construction. A test proves this against all battery contracts.

**Deterministic template** (tier 3, new, modeled on `QuestionFramingEngine.frame_method_a` and `_clarification_envelope`):
- `CHOOSE_ONE`: "Which {type_noun} do you mean by "{original_reference}"?" Each label joins the discriminating facts: "{title} · {discriminating facts}".
- `CONFIRM_SINGLE`: "Did you mean {label}?" `[now CONFIRM_ONE per R2.2]`
- `[CHOOSE_ATTRIBUTE template: R3.1 B]`
- `FREE_INPUT_ONLY`: "I couldn't find what "{original_reference}" refers to. What should I use?"
- The overflow suffix is appended when `overflow_count > 0`.

---

## 7. User-binding lifecycle

State machine per `ambiguity_id`:

```
PENDING --click(candidate_id)--> BINDING_CHECK --ok--> BOUND --> RAR re-resolve (ACTIVE_UI) --> resume
PENDING --free_input(text)-----> FREE_INPUT_RESOLVE
PENDING --timeout/new unrelated turn--> EXPIRED
BINDING_CHECK --stale/expired/unknown id--> REJECTED --> RAR rebuild --> new round or FREE_INPUT_ONLY
```

- **Persistence.** The pending contract is stored in the session. The recommended surface is the existing `turn_state` pending-interaction projection (`kind: "awaiting_clarification_answer"`) plus a stored contract reference, not a new store. `ApprovalStore` is the precedent for expiry and session-mismatch rejection, and its code is reused as a pattern only: approvals are authority records, and a clarification binding is not an authorization.
- `[REFINED by R3.1 C/D and R3.2 — typed CANDIDATE / ATTRIBUTE / FREE_INPUT payloads; BindingService admits PENDING, TENTATIVE, and CHANGE_PENDING, not only pending]` **Click binding.** The UI sends `{ambiguity_id, candidate_id, candidate_set_fingerprint}`, never display text. BindingService checks, in order:
  - the ambiguity is pending;
  - same session;
  - not expired;
  - `candidate_id` is in the contract;
  - the clicked candidate's current fingerprint equals the stored fingerprint.

  If all pass, it emits `RARDeterministicAnchor(selected_ui_id=candidate_id)` and re-runs RAR, which must return `RESOLVED` / `DETERMINISTIC_ANCHOR` / `ACTIVE_UI` `[REFINED by R4.4 — rule_used must be ACTIVE_UI and candidate_id must equal the clicked candidate; any other result is REJECTED, fail closed (F-6)]`. The evidence is recorded as `USER_CLUE` / user selection. A change in other candidates does not block the binding: the user chose a concrete, still-valid item.
- **Free input.** The text is authoritative clarification input, but not an automatic binding. RAR re-runs against the same candidate set with the text as new local evidence (exact alias, title, or ID match).
  - If RAR returns `RESOLVED`, bind and resume. `[REFINED by R4.5 (D5) — the typed text is the fresh reference_expression (F-3); the binding state follows R4.3: CONFIRMED only for a CERTAINTY-class result]`
  - If RAR returns `AMBIGUOUS` with a smaller set, start the next round.
  - If RAR returns `UNKNOWN`, the text describes something outside the set. `[BROADENING SOURCES CORRECTED by R2.7 — documents/emails via authorized retrieval capabilities, not Graphify]` This starts an explicit new resolution cycle, allowed to broaden (session, Graphify, retrieval), with a new `ambiguity_id`. The broadening is recorded in telemetry. It is never a silent broadening of the original set.
- `[SUPERSEDED by R1.8 / R2.4 — progress-based limit + per-turn budget; values are EXPERIMENT]` **Loop limit.** At most 2 user-facing ARN-C rounds per original reference, counted in the contract's `round_index` and reflected in the existing `consecutive_clarification_count`. After that, ARN-C stops. The Main Brain receives the full pending state plus the user's inputs and either proceeds with an explicit statement of its assumption for an AUTO-tier action, or asks an open question for CONFIRM/DESTRUCTIVE. It never auto-binds a restricted action. The value 2 is `CANDIDATE_THRESHOLD_TO_BE_ESTABLISHED`: it is a design default, not a measured value. System-caused rebuilds (stale rejection) do not count as user rounds. A hard cap of 3 total rebuilds prevents a system loop.
- `[SUPERSEDED for TENTATIVE_APPLIED recoverable actions by R2.4 / R3.2 — Change redoes after a validated rebind and fresh authorization; still holds for CONFIRMED/APPLIED and all CONSEQUENTIAL actions]` **Correction after choosing** ("no, the other one"). If no side-effecting action has executed, a correction referring to the pending or bound contract re-runs RAR with the correction as evidence against the same set, then rebinds. After execution, a correction is a new request; it never silently reverses an executed action.
- **Expiry.** The default is to reuse the `DEFAULT_EXPIRY_SECONDS = 900` precedent. This is `CANDIDATE_THRESHOLD_TO_BE_ESTABLISHED`, to be confirmed from interaction telemetry.

---

## 8. Graphify and context relationship
`[SCOPE CORRECTED by R2.7 — Graphify kinds are capability/skill/workflow/memory_pointer/connected_service only; not documents/emails. Candidate generation is owned by the single source-to-candidate producer (Plan B R1.7) with pre-ask investigation (R2.8)]`

- ARN-C never searches. It consumes only the contract.
- Candidate sources, in order of preference:
  1. Session context: open document, attachments, recent turns, via RAR's existing inputs.
  2. Deterministic anchors.
  3. Graphify or context builder, only when session candidates are insufficient and the reference type is indexed (capabilities, skills, workflows, memory pointers, services).
- Graphify is never required for same-session ambiguity.
- **Provenance propagation.** Every `CandidateFact.source` carries a locator. `graphify:<entry_id>` comes from `GraphifyIndex.get(entry_id)` records. Session sources use `session:<turn_id>` or `attachment:<id>`. The RAR trace keeps the full chain.
- Graphify-derived facts are evidence category `SOURCE_POINTER`, not `VERIFIED_FACT`, until opened. This follows the ARN.1 evidence taxonomy and its no-promotion rule.
- No Graphify architecture change. The only need is a stable `entry_id` and a small fact projection per record, which `_record()` already produces. P1 must verify this.

---

## 9. Edge OFF and Main Brain fallback

- RAR, the contract builder, the template, the validator, the binding service, and session persistence have no Edge dependency. They run identically with Edge ON or OFF.
- The Edge ON/OFF signal is the effective `EdgeSettings.enabled` after the `uri_preflight` check. Known hazard SB-2: `enabled` defaults True when the settings document is missing. ARN-C must read the effective value and treat "renderer not installed or not qualified" the same as OFF. `DEFAULT_EDGE_RUNTIME_INVENTORY` is empty today, so tier 1 is absent by default.
- **Main Brain renderer.** It receives the same `RenderRequest` (same slots, same facts) and passes the same validator. It cannot add candidates, because output keys outside the requested slots are rejected. Broadening requires a new RAR cycle.
- `[SUPERSEDED by R1.3 / R2.5 — the wording-need-class table plus the unified router; see D2 mode mapping]` **Recommended default policy** (User decision D-B in §14):
  - Edge ON: <1B, then template.
  - Edge OFF: Main Brain, then template.

  Rationale: when Edge is ON, calling the 9B only to reword a clarification defeats Main-Brain avoidance. When Edge is OFF, the Main Brain is the standing author of user-visible wording under the canonical interaction loop.

---

## 10. Qualification battery design (not run)

Location: `fixtures/m33_3_arn/battery.json` + `manifest.json`, with an LF SHA-256 anchor recorded before any run (Batch A precedent). Case IDs: `ARB-001`...

**Three layers**, so model output is scored deterministically wherever possible:
- **L1 deterministic core** (no model): contract builder, pruning, template, binding lifecycle.
- **L2 validator adversarial** (no model): canned bad renderer outputs, each of which must be rejected.
- **L3 renderer qualification** (model): contract in, real renderer output, validator plus scoring.

**Case schema** (proposed):
- `case_id`, `layer`, `category`, `session_fixture`
- `rar_query` (the `RARQuery` fixture), `expected_rar_outcome`
- `expected_contract` (kind, ordered IDs, `overflow_count`, exclusions)
- `render_request`, `injected_output` (L2 only), `expected_validator_flags`
- `user_action` (`click` / `free_input` / `correction` / `none`), `expected_binding`, `expected_round_index`
- `edge_state`, `renderer_availability`, `expected_tier`
- `semantic_notes` (for adjudication)

| Category (prompt list) | Layer(s) | Minimum cases |
|---|---|---|
| Same-name people | L1, L3 | 3 |
| Similarly named files | L1, L3 | 3 |
| Latest / earlier / first temporal | L1, L3 | 3 |
| Attachment ambiguity | L1, L3 | 3 |
| Multiple emails / threads | L1, L3 | 3 |
| Document versions | L1, L3 | 3 |
| Conflicting candidate metadata | L1, L3 | 2 |
| One plausible, insufficient certainty (CONFIRM_SINGLE; now CONFIRM_ONE per R2.2) | L1, L3 | 2 |
| Zero candidates (FREE_INPUT_ONLY) | L1, L3 | 2 |
| Exactly two candidates | L1, L3 | 2 |
| Exactly 5 candidates | L1, L3 | 2 |
| More than 5, pruning plus overflow | L1, L3 | 2 |
| Free-input path (resolves / narrows / broadens) | L1 | 3 |
| Correction after choosing (pre- and post-execution) | L1 | 2 |
| Stale candidate at click | L1 | 2 |
| Candidate set changed before response | L1 | 2 |
| Malformed output | L2 | 3 |
| Hallucinated slot or ID | L2 | 2 |
| Invented extra candidate | L2 | 2 |
| Ranking mutation | L2 | 1 |
| Omitted candidate | L2 | 2 |
| Omitted escape option (UI invariant) | L1 | 1 |
| Unsupported descriptive fact | L2, L3 | 3 |
| Cross-slot identity swap | L2 | 2 |
| Selection or presumption language | L2 | 2 |
| Negation / contrast in wording | L1, L2, L3 | 3 |
| Edge disabled | L1 | 2 |
| Generator unavailable or timeout | L1 | 2 |
| Main Brain fallback rendering | L3 | 3 |
| Loop limit reached | L1 | 2 |

Minimum counts are design minimums, not statistical sufficiency. P2 must state and justify the final N.

**Battery rules carried from Batch A:**
- Independent pre-audit of the battery before any model run, to catch over-strict cases (cf. `RWB-072/082/103/105`).
- Frozen hash.
- No battery edits after freeze without a version bump.
- Verbatim-sourced inputs where cases derive from earlier batteries.

---

## 11. Metrics and gates

Rates are computed per renderer candidate over L3 cases. "Pre-validation" means raw renderer output. "Post-validation" means what the user would see.

| Metric | Class | Threshold | Basis / establishment method |
|---|---|---|---|
| L1 deterministic tests pass | FROZEN_REQUIRED | 100% | Deterministic code; any failure is a defect. |
| L2 validator rejects every injected defect | FROZEN_REQUIRED | 100% | Deterministic. |
| Post-validation invented / unknown candidate shown | FROZEN_REQUIRED | 0 | Structural guarantee (slots plus validator). |
| Post-validation candidate omission | FROZEN_REQUIRED | 0 | Validator V-SLOT-MISSING. |
| Post-validation ranking shown ≠ RAR rank | FROZEN_REQUIRED | 0 | URI-controlled order. |
| Escape option present | FROZEN_REQUIRED | 100% | URI-appended constant. |
| Click binds contract `candidate_id` (not text) | FROZEN_REQUIRED | 100% | Binding service. |
| Template tier passes the validator on every battery contract | FROZEN_REQUIRED | 100% | Proves availability without a model. |
| Edge OFF: contract, binding, and template path functional | FROZEN_REQUIRED | 100% of Edge-OFF cases | AC-6. |
| Pre-validation schema validity | CANDIDATE_THRESHOLD_TO_BE_ESTABLISHED | UNMEASURED | Measure the ladder. Threshold = the level at which fallback rate stays within the chosen budget. |
| Pre-validation unknown or invented slot rate | CANDIDATE_THRESHOLD_TO_BE_ESTABLISHED | UNMEASURED | Same. |
| Pre-validation unsupported-fact rate | CANDIDATE_THRESHOLD_TO_BE_ESTABLISHED | UNMEASURED | Same; also audit V-UNSUPPORTED-FACT false positives by hand. |
| Pre-validation omission rate | CANDIDATE_THRESHOLD_TO_BE_ESTABLISHED | UNMEASURED | Same. |
| Negation / contrast preservation in wording | CANDIDATE_THRESHOLD_TO_BE_ESTABLISHED | UNMEASURED | Quote-backed adjudication (Batch A adjudication method). |
| Clarification semantic correctness (question asks the right thing; labels discriminate) | CANDIDATE_THRESHOLD_TO_BE_ESTABLISHED | UNMEASURED | Independent adjudication with quotes; the template output is the baseline to beat. |
| Deterministic fallback rate | CANDIDATE_THRESHOLD_TO_BE_ESTABLISHED | UNMEASURED | This is the renderer's value metric. If the fallback rate is high, the renderer adds no value over the template. |
| Validator false-rejection rate (valid output rejected) | CANDIDATE_THRESHOLD_TO_BE_ESTABLISHED | UNMEASURED | Hand adjudication of rejects. |
| Warm latency p50/p95 | CANDIDATE_THRESHOLD_TO_BE_ESTABLISHED | UNMEASURED | Measure; compare to template (≈0) and to the 9B renderer on the same host. |
| Cold / first-load latency | INFORMATIONAL | — | Record, because the Edge runtime lifecycle loads on demand. |
| RAM / VRAM resident | CANDIDATE_THRESHOLD_TO_BE_ESTABLISHED | UNMEASURED | Measure against the M33.2 `ResourceBudget` with the 9B co-resident. |
| Output tokens | INFORMATIONAL | — | Record. |
| Retry recovery rate | INFORMATIONAL | — | Informs whether the retry count stays 0. |
| Template vs renderer preference | INFORMATIONAL | — | Optional User A/B later; not a gate. |

**Threshold establishment method (P4):**
1. Run the template and the 9B renderer as reference arms, alongside each ladder candidate.
2. Propose thresholds from the observed distribution plus the User's latency and fallback-rate tolerance.
3. Freeze the thresholds in a versioned gate file before any later requalification run. Thresholds are never set after seeing the candidate they would accept (Batch A G-R3 discipline).

---

## 12. Sub-1B candidate search methodology (no winner selected)
`[SUPERSEDED by R1.4 — this workstream contributes a wording battery to the shared Edge Brain qualification; it does not run its own model search]`

1. **Inventory first** (read-only, P4 start): list models already present in LM Studio and Ollama, and in the M33.2 Edge runtime inventory. Record size, quantization, and SHA-256 at inventory time, not post-run (Batch A Needle-hash lesson).
   - Known from repository evidence: `lfm2.5-350m` was present at A2.8B. Qwen3.5-0.8B is named as Rung 1 in the A3 plan. Its install state is unverified.
2. **Smallest first.** Order candidates by parameter count and test the smallest plausible text-only instruct models first. Advance to a larger sub-1B model only when the smaller one fails a FROZEN_REQUIRED-adjacent pre-validation signal badly enough that fallback dominates.
3. **Selection criteria.** Controlled rendering, instruction adherence, strict-JSON fidelity, and not inventing tokens. General benchmark scores do not count.
4. **Test each candidate in two decoding modes:** unconstrained, and schema-constrained (JSON schema or grammar, if the runtime supports it). Constrained decoding may change the outcome more than model choice does.
5. **Provider-neutral.** Access goes through a renderer port (`RendererPort.render(RenderRequest) -> RenderResult`) with adapters for Edge (`propose_response` with a clarification-render request subclass) and the Main Brain (LM Studio chat). No model-specific logic lives outside adapters.
6. **Known risk.** The A2.8B scaffolding-confusion result predicts failure for heavily structured prompts. The renderer prompt is flat and minimal. A failure of every sub-1B candidate is an acceptable, reportable outcome. The architecture then runs template plus Main Brain, and ARN-C is unaffected.
7. **External research** (model cards, licences) is allowed only in the separately authorized execution phase. It is not done here.

---

## 13. Implementation phases (each separately authorized)
`[PARTLY SUPERSEDED — P0 governance done by the 2026-09-26 G0 pass except plan acceptance; P4 model ladder superseded by R1.4; slice ordering and gates now in docs/plans/M33_3_CROSS_PLAN_STATE.md]`

| Phase | Content | Worker (AO-4) | Model calls |
|---|---|---|---|
| P0 | Governance: register `URI-ARN-CLARIFICATION` alias (User confirms name); freeze this plan DRAFT → ACCEPTED; create `M33_3_ARN_STATE.md` | Claude | none |
| P1 | Deterministic core in `uri_v1`: contract, builder, trigger, pruning, template, RenderValidator, BindingService, session projection; L1 tests | Codex (multi-file, authority-sensitive) | none |
| P2 | Battery L1/L2/L3 fixtures, manifest, hash anchor, scorer; independent battery pre-audit | Codex build; audit by agent other than builder | none |
| P3 | Renderer port and adapters (Edge request subclass, Main Brain), mock providers, telemetry writer (per-row provenance, untruncated text, diagnostic-text exclusion) | Codex | mock only |
| P4 | Stage A isolated renderer qualification: inventory, ladder, reference arms, threshold proposal | Separately authorized run | yes, local only |
| P5 | Independent audit / requalification of P4 evidence; freeze thresholds | Independent auditor; Claude final audit | none |
| P6 | Clickable UI in `uri_ui` (options bound to IDs, escape option, free input) | Antigravity per UI-initiative role override, if still in force | none |
| — | Production integration into `uri_core` request path | Not in this plan; needs Stage C / `INT-*` authorization | — |

**Independent audit sequence:**
- Audit after P1 (deterministic invariants).
- Battery pre-audit at P2 (before any model run).
- Harness audit at P3 (telemetry truthfulness, no truncation, provenance).
- Evidence audit at P5.
- Each audit is done by an agent other than the implementer. Verdicts are committed as repository artifacts (R4 lesson: independent reviews must be durable).

---

## 14. Risks and open questions

**Risks**
- R-1 **Upstream detection.** Batch A D0 resolved 0/27 on the real path, and 20/27 were silent detection misses. ARN-C only fires when RAR reports AMBIGUOUS or UNKNOWN. A silent miss never reaches ARN-C, so ARN-C does not fix detection and must not be credited with it.
- R-2 **Anchor delivery.** Batch A found no `RARDeterministicAnchor` delivered for open-document or attachment pronouns. The click path depends on `selected_ui_id` delivery being wired. P1 must prove this end to end.
- R-3 **Sub-1B viability.** Negative evidence from A2.8B. The template-only outcome is acceptable.
- R-4 **V-UNSUPPORTED-FACT is lexical.** A paraphrase can carry an unsupported claim without new tokens ("the final one"). Semantic adjudication in P4 measures the residual.
- R-5 **SB-2 default-ON hazard** could route to a missing renderer. Mitigated by treating not-installed as OFF.
- R-6 **Concurrent writers** in this worktree (standing hazard). Re-read governance files before edits.

**Open questions for the User** `[RESOLVED/SUPERSEDED — D-A by R1.1; D-B by R1.2/R1.3/R2.5; Q-3 by R1.5/R2.3/R2.6; Q-4 by R1.6 (cap 5 hard max, 4 vs 5 is EXPERIMENT); Q-5 by R1.6 (adaptive top-N / attribute-first); cross-plan D1–D4 in R2.0]`
- D-A **Identity name.** Is `URI-ARN-CLARIFICATION` acceptable, or should this work be ARN.2 under `URI-ARN-PRODUCTION`? The latter means unpausing the ARN milestone.
- D-B **Wording authority.** The standing canonical-loop rule says user-visible text comes from the Brain, and the ARN.1 relay says "Brain loop retains wording authority". This plan lets a <1B Edge model author clarification wording when Edge is ON, as the planning prompt requests. Confirm that this scoped exception is intended, and confirm the default chain (Edge ON: <1B, then template; or <1B, then Main Brain, then template).
- Q-3 **Risk tier at trigger time.** `CONFIRM_SINGLE` depends on the downstream risk tier, which may not be known when RAR runs. Default: trigger CONFIRM_SINGLE only once a CONFIRM/DESTRUCTIVE proposal exists (post-proposal check), not at RAR time.
- Q-4 **Cap of 5 vs 4.** This plan freezes 5 as the hard maximum. Confirm.
- Q-5 **Overflow handling.** Top-5 plus a count (recommended), or axis grouping (deferred)?

---

## 15. Files a later implementation would likely touch

**New:**
- `uri_v1/turn/rar_clarification_contract.py`: contract, validation, builder, trigger.
- `uri_v1/arn_clarification/` (package name follows the P0 identity decision):
  - `render_contracts.py`
  - `template_renderer.py`
  - `render_validator.py`
  - `binding.py`
  - `renderer_port.py`
  - `adapters/edge_renderer.py`
  - `adapters/main_brain_renderer.py`
- `fixtures/m33_3_arn/battery.json` and `manifest.json`
- `scripts/m33_3_arn_battery.py`, `scripts/m33_3_arn_scorer.py`, `scripts/m33_3_arn_run.py`
- `test_m33_3_arn_contract.py`, `test_m33_3_arn_validator.py`, `test_m33_3_arn_binding.py`, `test_m33_3_arn_structural.py`
- `docs/plans/M33_3_ARN_STATE.md`

**Modified, later:**
- `docs/governance/URI_STATE.yaml` (alias and status)
- `docs/governance/URI_AGENT_RELAY.md`
- `docs/plans/M33_3_BATCH_A_CONTRACT_MAPPING.md` (a new row, additive only)

**Integration only, not in this plan:**
- `uri_core/core/edge/contracts.py`: a clarification-render request subclass of `EdgeReplyRequest`.
- `uri_core/core/turn_state.py`: pending projection.
- `uri_ui/lib/...`: option widget.

**Read-only, never modified:**
- `uri_v1/turn/rar_deterministic.py` (A9-protected)
- `uri_core/core/arn/*`
- frozen Batch A artifacts

---

## 16. Recommended next authorized action
`[SUPERSEDED — the next step is the independent cross-plan re-audit of R2 + Plan B R1; see docs/plans/M33_3_CROSS_PLAN_STATE.md]`

`ACCEPT_M33_3_ARN_PLAN_AND_REGISTER_IDENTITY` (P0 only):
- The User answers D-A and D-B.
- Claude then registers the alias, moves this plan to ACCEPTED, creates the state file, and commits.
- P1 (deterministic core, no models) becomes routable to Codex.

No model run, Stage B, or integration follows from that action.

---

## Self-review against acceptance criteria

- AC-1 met: see §1. The legacy prototype checkout and `uri_ui` internals are disclosed as not inspected.
- AC-2 met: §2, with a placeholder name pending the User decision.
- AC-3 met: §4.1 and §4.2 give RAR every decision. §5 and D-2 through D-4 make renderer overreach structurally impossible or validated.
- AC-4 met: reused `RARDeterministicAnchor.selected_ui_id` / `ACTIVE_UI`, `validate_rar_resolution` style, ARN.1 taxonomy and axis logic, Method C pattern, `QuestionValidator` patterns, approval expiry precedent, the `turn_state` pending projection, and `consecutive_clarification_count`.
- AC-5 met: template tier plus a FROZEN_REQUIRED template-validity gate.
- AC-6 met: §9 plus an Edge-OFF gate.
- AC-7 met: §11. The only numeric thresholds are for deterministic invariants (100% / 0). The loop limit 2 and expiry 900s are labeled defaults to be established.
- AC-8 met: §12.
- AC-9 met: §10 battery rules, §11 threshold discipline, §12 hash at inventory, §13 durable audits.
- AC-10 met: trigger (4.1), schema (4), pruning (4.2), render input/output (5), validation (6), template (6), Main Brain fallback (9), click binding (7), free input (7), loop limit (7), stale (7), provenance (4, 8), session persistence (7), telemetry (11 plus P3), privacy (below), Edge ON/OFF (9).

Correction made during self-review: the first draft had the renderer produce the escape-option label as a required field and validated its presence. It was changed to a URI-appended constant (D-4), because a validation gate on something URI can guarantee structurally is weaker than the guarantee.

**Privacy (answer to Q16).**
- Renderer tiers are local only: the sub-1B model on the Edge runtime, the Main Brain on local LM Studio.
- The `RenderRequest` carries only display facts, never message bodies or raw history.
- Telemetry stores IDs, hashes, lengths, flags, tiers, and latencies. Rendered text is stored only in qualification runs, under the Batch A evidence convention, and never in production traces (`EdgeRequest`: "content is never trace material").
- Binding records store the `candidate_id` and fingerprint, not display text.
