# M33.3 — ARN Clarification Architecture and <1B Text Renderer Plan

**Status:** DRAFT, revised R1 after the User architecture interview (planning only, `PLAN_M33_3_ARN_ARCHITECTURE_AND_LT1B_TEXT_GENERATOR`). Not accepted, not frozen, not registered, not committed.
**Status update (2026-09-26, additive):** revised R2 (cross-plan repairs A-R1…A-R12, User decisions D1–D4). Registered as planning identity `URI-REFERENCE-CLARIFICATION` in `URI_STATE.yaml` → `planning_artifacts`. Committed to the repository. Status `PLAN_REVISED_R2_AWAITING_INDEPENDENT_CROSS_PLAN_REAUDIT`: not accepted, not frozen, implementation NOT authorized.
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
- Binding states: `TENTATIVE` (shown as "Using X · Change") and `CONFIRMED`. The execution gate requires `CONFIRMED` for `CONSEQUENTIAL` actions. `CONFIRM_SINGLE` is replaced by this. `[REFINED by R2.2 / R2.4 — single-candidate kind `CONFIRM_ONE`; post-execution states TENTATIVE_APPLIED/CHANGED/REDONE/VERSIONED]`
- [USER] Two or more equally plausible candidates: always ask with clickable options, even for harmless actions.
- `[REFINED by R2.9 — deterministic TENTATIVE eligibility check; model evidence only when grounded and re-checked (D3); no durable learned evidence (D4)]` "Strongly preferred" (allowed to be TENTATIVE): [HYPOTHESIS] deterministic separation only. A lone `MODEL_SELECTION` result never counts; it is treated as ambiguous. Learned evidence may count (R1.7).
- `[REFINED by R2.8 — after bounded, non-binding pre-ask investigation inside candidate generation]` Timing: an AMBIGUOUS result asks immediately, before any action proposal. A TENTATIVE single candidate is checked for consequence at proposal time. No Capable Brain call is spent before an ambiguity question.
- [USER] Changing a tentative choice after use: the recoverable action is redone automatically on the new candidate. If the user had edited the old result, the redo is a new version and the edited version is kept in history.

### R1.6 Presentation
- [USER] Adaptive, minimizing user effort.
  - If the ranking clearly separates a small top group: show up to 4-5 options, plus "N more" where useful, plus the escape option.
  - If candidates are flat: first ask the most valuable grounded attribute question, then show the narrowed set.
  - Never dump a large list. Never ask an attribute question when the ranking already makes the choice obvious.
- New kind `CHOOSE_ATTRIBUTE`. It reuses ARN.1 `get_clarification_recommendation` (axis choice) and `UserClue` / `apply_user_clue` (binding an attribute click). An attribute option binds a `UserClue(axis, value)`, not a candidate ID.
- [HYPOTHESIS] "Clearly separated" = the RAR top driver-rule tier holds 5 or fewer candidates. RAR ranks are ordinal, and no scores exist. [EXPERIMENT] Measure clicks-to-resolution for top-N versus attribute-first on the battery and in the User rating subset.
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
RAR owns trigger, type, candidate set, IDs, rank, cap, provenance, and binding contract. `rar_deterministic.py` (A9) is untouched. Slot-keyed rendering hides IDs. URI controls option order. The escape option is a URI-appended constant. The deterministic RenderValidator runs on every tier and fails closed. A click binds through `RARDeterministicAnchor.selected_ui_id` / `ACTIVE_UI`. Contract validation mirrors `validate_rar_resolution`. Graphify is optional, and its facts are `SOURCE_POINTER`. Provenance is carried per fact. Pending state uses the `turn_state` projection and the approval-expiry precedent. No numeric confidence. Privacy: local tiers only, and no content in production traces.

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
- [EVIDENCE] `uri_v1/turn/rar_deterministic.py` is A9-protected (SHA-256 `e02af25bb7009d12d829c8b8fc92e487d3da75aeaa160092db617458278fb649`). RAR ranks are ordinal and carry no scores. The learned-evidence weighting therefore **cannot live "inside RAR"**.
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
| `CHOOSE_ATTRIBUTE` | Flat candidate set (R1.6) | 0 candidate options; 2 ≤ attribute options ≤ 5; each option binds a `UserClue(axis, value)` |
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
| `RESOLVED`, basis `DETERMINISTIC_ANCHOR` | none; binding `CONFIRMED` |
| exactly 1 candidate, deterministic TENTATIVE check passes (R2.9) | none before the proposal; binding `TENTATIVE`; shown as "Using X · Change". The execution gate still blocks if the proposed action's `wrong_binding_impact` is `CONSEQUENTIAL` (R2.6), which then raises `CONFIRM_ONE`. |
| exactly 1 candidate, check fails (for example, a lone `MODEL_SELECTION` basis) | `CONFIRM_ONE` |
| `AMBIGUOUS` | `CHOOSE_ONE`, or `CHOOSE_ATTRIBUTE` if the set is flat (R1.6) |
| `UNKNOWN` / `NO_CANDIDATE`, reference required | `FREE_INPUT_ONLY` |
| `UNKNOWN`, reference not required | none; routing proceeds per R2.5 |

### R2.4 (A-R4) Post-execution lifecycle
- The per-`ambiguity_id` state machine of §7 gains post-execution states:

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

`[DIAGRAM SUPERSEDED in part: renderer tier chain by R1.3/R2.5; candidate sources by R2.7/R2.8; single grounding producer per Plan B R1.7]`

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

**D-5: The binding path.** A click produces `RARDeterministicAnchor(selected_ui_id=<candidate_id>)` and re-runs RAR. This reuses the existing `ACTIVE_UI` rule instead of creating a parallel binding mechanism.

---

## 4. RAR → ARN-C typed contract

The proposed module is `uri_v1/turn/rar_clarification_contract.py`. All records are frozen dataclasses. Field names follow the `RARCandidate` and `RARResolution` style.

```python
class ClarificationKind(str, Enum):
    CHOOSE_ONE = "CHOOSE_ONE"                  # RAR AMBIGUOUS, 2..MAX candidates
    CONFIRM_SINGLE = "CONFIRM_SINGLE"          # [SUPERSEDED by R2.2: CONFIRM_ONE] 1 candidate, non-deterministic basis, risk policy requires confirmation
    FREE_INPUT_ONLY = "FREE_INPUT_ONLY"        # RAR UNKNOWN / NO_CANDIDATE
    # no other kinds in v1

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
| `RESOLVED`, basis `DETERMINISTIC_ANCHOR` | No clarification. |
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
`[ROLE REFRAMED by R1.4 / R2.5 — the EXPLAIN-class Edge wording role within the shared Edge Brain qualification; input/output/forbidden rules below still apply to every model tier]`

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
- **Click binding.** The UI sends `{ambiguity_id, candidate_id, candidate_set_fingerprint}`, never display text. BindingService checks, in order:
  - the ambiguity is pending;
  - same session;
  - not expired;
  - `candidate_id` is in the contract;
  - the clicked candidate's current fingerprint equals the stored fingerprint.

  If all pass, it emits `RARDeterministicAnchor(selected_ui_id=candidate_id)` and re-runs RAR, which must return `RESOLVED` / `DETERMINISTIC_ANCHOR` / `ACTIVE_UI`. The evidence is recorded as `USER_CLUE` / user selection. A change in other candidates does not block the binding: the user chose a concrete, still-valid item.
- **Free input.** The text is authoritative clarification input, but not an automatic binding. RAR re-runs against the same candidate set with the text as new local evidence (exact alias, title, or ID match).
  - If RAR returns `RESOLVED`, bind and resume.
  - If RAR returns `AMBIGUOUS` with a smaller set, start the next round.
  - If RAR returns `UNKNOWN`, the text describes something outside the set. `[BROADENING SOURCES CORRECTED by R2.7 — documents/emails via authorized retrieval capabilities, not Graphify]` This starts an explicit new resolution cycle, allowed to broaden (session, Graphify, retrieval), with a new `ambiguity_id`. The broadening is recorded in telemetry. It is never a silent broadening of the original set.
- `[SUPERSEDED by R1.8 / R2.4 — progress-based limit + per-turn budget; values are EXPERIMENT]` **Loop limit.** At most 2 user-facing ARN-C rounds per original reference, counted in the contract's `round_index` and reflected in the existing `consecutive_clarification_count`. After that, ARN-C stops. The Main Brain receives the full pending state plus the user's inputs and either proceeds with an explicit statement of its assumption for an AUTO-tier action, or asks an open question for CONFIRM/DESTRUCTIVE. It never auto-binds a restricted action. The value 2 is `CANDIDATE_THRESHOLD_TO_BE_ESTABLISHED`: it is a design default, not a measured value. System-caused rebuilds (stale rejection) do not count as user rounds. A hard cap of 3 total rebuilds prevents a system loop.
- `[SUPERSEDED for TENTATIVE_APPLIED recoverable actions by R2.4 — Change redoes automatically; still holds for CONFIRMED/APPLIED and all CONSEQUENTIAL actions]` **Correction after choosing** ("no, the other one"). If no side-effecting action has executed, a correction referring to the pending or bound contract re-runs RAR with the correction as evidence against the same set, then rebinds. After execution, a correction is a new request; it never silently reverses an executed action.
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
