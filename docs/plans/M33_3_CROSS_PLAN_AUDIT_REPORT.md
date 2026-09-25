# M33.3 — Cross-Plan Architecture Audit: URI-REFERENCE-CLARIFICATION (Plan A) × URI Brain Architecture (Plan B)

**Type:** Independent cross-plan architecture audit (read-only). Durable repository record of a verdict first returned in a Claude Code session on 2026-09-26.
**Auditor:** Claude (Opus 5.5), acting as independent cross-plan auditor. Claude did not author Plan B (authored by Codex). Claude authored Plan A's earlier drafts; this is disclosed as a limitation on independence for Plan A.
**Date:** 2026-09-26
**Baseline:** branch `m35-uri-v1-parallel-architecture` @ `127c7339ad61d2929a7dda04e58e511d26241401`.
**Verdict:** `COMPATIBLE_WITH_BOUNDED_REPAIRS`. The verdict does not authorize implementation.

## Provenance of this record

- The audit was returned in chat. It is recorded here so a later re-auditor does not depend on chat or session memory.
- The body below (§0 to §14) reproduces the returned report's substance and structure. Wording is lightly normalized from the chat's compressed style into full sentences. No finding, severity, number, or classification was changed in §0 to §14.
- Corrections found after the audit are recorded separately in §15. They are not silently folded into the body.

---

## 0. Materials and acceptance criteria

- **Plan A:** `docs/plans/M33_3_ARN_ARCHITECTURE_AND_LT1B_RENDERER_PLAN.md`, revision R1. At audit time the file was untracked and uncommitted. SHA-256 at audit time: `dcc262903eaa061d936e49b0d9c0dca3cfb2e2e485f2e01dfd58d48760f6e7da`.
- **Plan B:** not in the repository at audit time. It was recovered from Codex's final message in session transcript `~/.codex/sessions/2026/09/26/rollout-2026-09-26T03-31-00-01a0da96-071c-72f0-8562-0f71ac9457db.jsonl` (timestamp 2026-09-25T22:51:31.958Z, titled "URI Brain Architecture — evidence-grounded proposal for review"). The User's interview answers in the same session were also read.
- **Not used:** later Codex runs of the same audit prompt (2026-09-26 04:27–04:37).

**Acceptance criteria (defined before auditing):**
- Every claim cites a file inspected in the audit session.
- User requirements are kept separate from qualified capability.
- Unverifiable items are marked `UNVERIFIED` or `UNMEASURED`.
- No repair, run, or write happens during the audit.

**Self-review corrections made before return:**
- The first draft treated ExperienceStore as a viable reuse. It is not (C-4).
- The first draft accepted Graphify as a document candidate source. `graphify_index.py` indexes only `capability`, `skill`, `workflow`, `memory_pointer`, and `connected_service` (C-11).

## 1. Cross-plan verdict

`COMPATIBLE_WITH_BOUNDED_REPAIRS`.

Both plans share these principles:
- runtime authority;
- deterministic candidate identity;
- non-sequential routing;
- qualification as a hard gate;
- Edge OFF removes Edge inference only;
- independent approval gates.

The conflicts fall into three groups:
- two accepted M33.2 rules that need governance amendments (C-1, C-2);
- Plan A internal inconsistencies and one wrong mechanism (C-4 to C-7);
- undefined seams.

Four User decisions (D1 to D4) were identified. They gate specific slices only. The verdict does not authorize implementation.

## 2. Responsibility matrix (summary of findings)

| Decision | Current owner (evidence) | Conflict? | Recommended canonical owner |
|---|---|---|---|
| Deterministic preflight | `URI_PREFLIGHT` (M33.2 §3/§6); live `decision_engine.build_turn_state_and_directory` | no | existing preflight, extended |
| Task/context grounding | `turn_state`, `context_builder`/`query_context`, production first-match `CapabilityContextResolver`; research `uri_v1` TurnFrame | overlap, unowned | one source-to-candidate producer emitting the `RARQuery` candidate set |
| RAR | `uri_v1/turn` research only; `URI-RAR` `EXPERIMENTAL`; zero `uri_core` imports | no | RAR, after `URI-RAR` adoption |
| ARN.1 | production NOT_FOUND narrowing (`canonical_execution.py:722`) | no | ARN.1, unchanged |
| Graphify | hint/pointer; no document or email index | no (both plans overstate reach) | hint only |
| Candidate ranking | RAR ordinal ranks, no scores | yes (C-3, C-4) | RAR deterministic order; a model annotates only |
| Candidate IDs | `validate_rar_resolution` anti-invention | no | RAR |
| Clarification wording | M33.2 §3.1: model-authored, template only as fallback | yes (C-1) | Plan A policy, after amendment |
| Binding | none in production | no | Plan A `BindingService` → `RARDeterministicAnchor.selected_ui_id` / `ACTIVE_UI` |
| Tentative binding | none | yes (C-14) | Plan A definition |
| Wrong-binding impact | none; `Action` has `effect_type` / `approval_requirement` / `risk` | naming overlap | new `Action` field (§8) |
| Edge routing | `uri_core/core/edge/routing_policy.py` pure module, **not wired** | duplicate router risk | one router, extending `routing_policy` |
| Explicit model selection | ModelRouter; M33.2 `SUPPRESS` on explicit Main request | yes (C-2) | router, after amendment |
| Model lifecycle and residency | `EdgeResourceGovernor` (Edge only); `RuntimeLease(lease_id, runtime_id)` has no owner field | extends | M33.2 governor, extended |
| Redo/Change | none; no result versioning in `file_store` | owner missing | new result-version owner (gap) |
| Response evaluation | none exists | duplicate signal (C-10) | Plan B event schema |
| ExperienceStore | Brain-gated prose, user-scoped; `list_all` / `recent` / `add` only; no delete endpoint | yes (C-4) | unchanged; not the mechanism |
| Route learning | `FallbackRoutingStore` is manual config; M33.2 §8 calibration never trained online | tension (C-9) | new store (Plan B) |
| Knowledge/memory | `user_memory`, `graph_store`; `URI-Memory` `NOT_STARTED` | no | URI-Memory (future) |
| Audit/telemetry | `EdgeRoutingTraceEvent` (M33.2 §9) | no response `trace_id` | extend the trace with a `trace_id` |
| Stop safeguards | `state.consecutive_clarification_count`; ARN.1 `CostAccumulator` | no | Plan A, reusing both |

**Owned by neither plan:**
- raw-turn reference detection into RAR;
- coexistence or retirement of `CapabilityContextResolver`;
- result versioning;
- response `trace_id`;
- `intelligence_mode` mapping;
- Capable Brain lease ownership;
- result editability in `uri_ui` (UNVERIFIED).

## 3. End-to-end case trace (Cases A–M)

**Current production reality (applies to every case):** RAR, the clarification layer, and the Edge router are unwired. `/ask` is Main Brain native loop plus first-match `CapabilityContextResolver`.

- **A. "Open the report", one deterministic candidate.**
  - Resolves to RAR `RESOLVED` / `DETERMINISTIC_ANCHOR` only if a driver rule fires. Binding CONFIRMED. Deterministic route; open (READ_ONLY, impact NONE).
  - Seam: one candidate is not the same as a deterministic anchor. Otherwise C-5 applies.
- **B. Several equal candidates.**
  - `AMBIGUOUS` → `CHOOSE_ONE`. SIMPLE template with at most 5 options plus the escape option. A click binds via `ACTIVE_UI`.
  - Seam S-1: the pre-ask investigation has no owner in Plan A.
- **C. Tentatively preferred through current plus learned evidence.**
  - TENTATIVE is allowed because the impact is NONE ("Using X · Change").
  - Blocked today: there is no structured learned-evidence source (C-4). Effective behavior is `CHOOSE_ONE` with X first.
- **D. "Email the report to the Director".**
  - No send capability exists. The nearest is `gmail_create_draft` (EXTERNAL_WRITE).
  - A send is CONSEQUENTIAL, so identity must be confirmed first. The draft classification was undecided (D1).
- **E. Two independent ambiguous references.**
  - Bundle contract with one combined card. Capable Brain goes directly to the comparison.
  - Seam: the bundle schema is prose only, and `RARQuery` is single-reference.
- **F. Dependent references.**
  - Sequential asks. The "parent locator" dependency is a hypothesis; the field is UNVERIFIED.
- **G. "None of these" + "the one Priya sent last week".**
  - New `ambiguity_id` and a new bounded cycle over authorized sources (`gmail_search`). Graphify cannot find emails.
  - Seam S-2: the owner of clue interpretation is undefined.
- **H. Change after tentative use.**
  - Rebind to Y, then redo and replace the result.
  - Conflict: Plan A §7 says "correction after execution is a new request". The post-execution states are missing (C-6).
- **I. Change after the user edited the result.**
  - Needs a new version, with the edited one kept.
  - Gap: no result versioning exists. `uri_ui` editability is UNVERIFIED.
- **J. Edge OFF.**
  - Deterministic mechanisms run. EXPLAIN falls back to the template. REASONING goes to the Capable Brain if the mode allows.
  - Seams: SB-2 default-ON hazard; `EDGE_ONLY` + REASONING is undefined (C-8).
- **K. Explicit strong model, two-line draft.**
  - The selected model authors it.
  - Conflict with M33.2 `SUPPRESS` (C-2). Plan A does not map "Capable Brain" to the selected model.
- **L. AUTO with a qualified trivial Edge task.**
  - Edge via the contract-injection seam.
  - Today: no wired Edge route; Edge drafting is UNMEASURED.
- **M. Repeated "Should have escalated".**
  - Structured feedback leads to lower Edge preference for that class and a requalification flag. Learning cannot qualify anything.
  - Seam: M33.2 §8 forbids online calibration training (C-9).

## 4. Contract conflicts

| ID | Conflict | Severity | Smallest repair |
|---|---|---|---|
| C-1 | Template-primary wording vs M33.2 §3.1 "model-authored; template only as fallback". Live code already has deterministic text: `canonical_execution.py:441`, `approval_resumption._clarification_envelope`. | HIGH (governance) | Amend M33.2 §3.1 |
| C-2 | Edge supporting work under explicit selection vs `SUPPRESS` ("explicit Main request") | MEDIUM | Amend M33.2 §6 |
| C-3 | Plan B model-assisted candidate comparison vs Plan A "no model ranking" | MEDIUM | A model annotates or narrows only |
| C-4 | Plan A learned evidence via `ExperienceRecord.corrections`, "inside RAR". ExperienceStore is prose, Brain-gated, with no IDs, decay, or delete. `rar_deterministic.py` is A9-protected (hash `e02af25b…b649`) with ordinal ranks and no scores. | HIGH for that slice | Separate deterministic adjunct; session-only |
| C-5 | A lone `MODEL_SELECTION` is treated as ambiguous, but `CHOOSE_ONE` needs ≥2 and `CONFIRM_SINGLE` was removed. The single-candidate kind is undefined. | MEDIUM | Keep a single-candidate confirm kind |
| C-6 | Stale draft text beside R1: §4.1 TOOL_CATALOG tiers, §7 post-execution rule, loop limit 2, §9 default chains | MEDIUM | Mark superseded; add post-execution states |
| C-7 | "Next to `requires_approval`" and "nothing like this exists" vs `Action.approval_requirement` / `effect_type` / `risk` (`uri_core/capabilities/base.py:138-146`) | LOW | Correct the text |
| C-8 | `intelligence_mode` has no mapping to AUTO / selected / local-only / Edge OFF | MEDIUM | User decision D2 |
| C-9 | Per-user online route preference vs M33.2 §8 "never trained online" | LOW | State that preference is not calibration |
| C-10 | Change tap and thumbs-down "wrong reference" are two channels for one signal | LOW | One event schema |
| C-11 | Graphify treated as a document/email candidate source | LOW | Name the authorized-source capabilities |
| C-12 | Plan B omits A2.8H (research detector D1R reached 16/84; 1 incorrect confident binding) | LOW | Add a D1R/D1RQ arm (see §15 correction) |
| C-13 | Plan A "20/27 silent misses"; the Batch A completion report line 199 shows 21. **Withdrawn, see §15 COR-3.** | LOW | Correct |
| C-14 | Plan B "sufficiently supported candidate" is undefined | LOW–MEDIUM | Adopt Plan A TENTATIVE criteria |
| C-15 | Pre-ask investigation (User answer) vs Plan A "AMBIGUOUS asks immediately" | LOW | Investigation inside candidate generation |

## 5. Duplication and missing interfaces

- **Duplications:**
  - three routers (Plan A wording policy, Plan B router, M33.2 `IntelligenceRoutingDecision`);
  - overlapping context builders;
  - four risk vocabularies (`EffectType`, `RiskLevel`, `ApprovalRequirement`, Batch A TOOL_CATALOG tiers) plus the new impact field;
  - several learning stores;
  - lifecycle registries;
  - pending-interaction state machines.
- **Missing interfaces:**
  - `RARQuery` producer from real state;
  - bundle contract;
  - clue-interpretation owner;
  - response `trace_id`;
  - evaluation event schema;
  - result-version record;
  - `RuntimeLease.owner`;
  - Capable Brain lease;
  - route-decision record;
  - `intelligence_mode` mapping.

## 6. Governance changes required

1. M33.2 §3.1 amendment (deterministic primary wording for SIMPLE; validator on every tier). This is an amendment, not a hidden exception.
2. M33.2 §6 `SUPPRESS` / `MAIN_BRAIN_PREFERRED` amendment for explicit selection.
3. Versioned `intelligence_mode` mapping.
4. Register `URI-REFERENCE-CLARIFICATION`; mark Plan A §2 `URI-ARN-CLARIFICATION` superseded.
5. Accept the capability-contract extension (`wrong_binding_impact`).
6. Commit Plan B into the repository.
7. `URI-RAR` adoption decision before any production integration.
8. M33.2 §8: route preference is not calibration.

## 7. Learning and memory decision

- **Option B, with qualifications.** No existing mechanism satisfies the durable requirement, which rules out option C.
- **Can exist now:**
  - session-authoritative choice;
  - rank-only session evidence;
  - structured Change/correction events;
  - a route-performance/evaluation store (after trace IDs).
- **Depends on URI-Memory or an interim store (D4):** durable cross-session reference evidence with decay and invalidation, and learned tie-breaking (also gated by an experiment).

## 8. `wrong_binding_impact` decision

- **Home:** a new optional field on the production `Action` (`uri_core/capabilities/base.py`), beside `effect_type`, `approval_requirement`, and `risk`. It propagates through `LegacyCapabilityAdapter`.
- **Values:** `NONE` / `RECOVERABLE` / `CONSEQUENTIAL`.
- **Default:** undeclared means `CONSEQUENTIAL`.
- **Not derivable from `EffectType`:** `gmail_create_draft` is EXTERNAL_WRITE yet only a draft.
- **Consumer:** the execution gate. `CONSEQUENTIAL` together with `TENTATIVE` means block and `CONFIRM`.
- **Granularity:** approval stays independent. Per-parameter impact is deferred; the action-level maximum applies.

## 9. Dependency graph

- G0 governance comes first.
- S1 is the RC deterministic core in `uri_v1` on fixtures, after the Plan A repairs.
- S3 (battery L1/L2) follows S1.
- S5 (wording qualification) follows S3.
- The contract/binding schema freeze must precede S12 (UI).
- D1 gates S2 (the impact field).
- S4 (source-to-candidate replay) is independent, with its own plan. It gates S13 (production integration, plus `URI-RAR` adoption and INT authorization) and S9 (learned tie-break).
- D2 + G2 gate S6 (unified router). S6 precedes S7 (trace ID and evaluation), and S7 precedes S8 (route store and learning replay).
- S10 (leases and residency) is independent.
- S11 (result versioning) gates Case H/I redo.

**Plan B's first experiment is a prerequisite only for S13, S9, and presentation tuning on real metadata.** It is not a prerequisite for S1, S2, S3, governance, or S10.

## 10. Pre-implementation gates

- **PG-1:** Plan A repairs are applied and re-reviewed before S1.
- **PG-2:** D1 is answered and the impact-field extension is accepted before S2.
- **PG-3:** D2 is answered and G2 is accepted before S6.
- **PG-4:** G1 is accepted before any production wording path.
- **PG-5:** S4 has its own pre-audited plan, and frozen artifacts stay untouched.
- **PG-6:** the A9 hash is checked before and after any RAR-touching slice.

## 11. Plan repairs

- **Plan A (A-R1 to A-R12):**
  1. Replace the ExperienceStore mechanism.
  2. Add a single-candidate confirm kind.
  3. Replace the TOOL_CATALOG tiers.
  4. Add post-execution states and supersede the stale rules.
  5. Make the Capable Brain the selected model; add `EDGE_ONLY`; consult the unified router.
  6. Correct the field names.
  7. Correct the Graphify scope.
  8. Add pre-ask investigation.
  9. Model comparison annotates only.
  10. Change 20/27 to 21.
  11. Add a bundle contract.
  12. Unify the Change event.
- **Plan B (B-R1 to B-R9):**
  1. Add A2.8H evidence and a D1R/D1RQ arm.
  2. Add a mode mapping.
  3. State that preference is not calibration; keep the route store separate.
  4. Name `wrong_binding_impact`; adopt the TENTATIVE criteria.
  5. Correct the Graphify scope.
  6. Correct lease and governor facts.
  7. Declare a single `RARQuery` producer.
  8. Commit Plan B.
  9. State that `routing_policy` is unwired.

## 12. Implementation readiness at audit time

| Slice | Classification |
|---|---|
| G0 | READY_TO_IMPLEMENT (governance only) |
| S1 | PLAN_REPAIR_REQUIRED |
| S2 | BLOCKED (D1) |
| S3 | PLAN_REPAIR_REQUIRED |
| S4 | EXPERIMENT_REQUIRED |
| S5 | EXPERIMENT_REQUIRED |
| S6 | BLOCKED (D2, G2) |
| S7 | PLAN_REPAIR_REQUIRED |
| S8 | EXPERIMENT_REQUIRED |
| S9 | BLOCKED (D4, experiment) |
| S10 | EXPERIMENT_REQUIRED |
| S11 | PLAN_REPAIR_REQUIRED |
| S12 | BLOCKED (S1 freeze) |
| S13 | BLOCKED (S4, URI-RAR, INT) |

## 13. User decisions identified

- **D1:** `gmail_create_draft` impact.
- **D2:** `intelligence_mode` mapping.
- **D3:** whether a model-assisted preference may create TENTATIVE.
- **D4:** whether durable reference evidence waits for URI-Memory or gets an interim store.

All four were subsequently answered by the User on 2026-09-26. They are recorded in `docs/plans/M33_3_CROSS_PLAN_STATE.md`.

## 14. Final state at audit time

- CROSS_PLAN_STATUS: `COMPATIBLE_WITH_BOUNDED_REPAIRS`
- FILES_CHANGED: none
- EXPERIMENTS_RUN: none
- IMPLEMENTATION_AUTHORIZED: NO

UNVERIFIED at audit time:
- `uri_ui` option rendering and result editability;
- a `RARCandidate` parent-locator field;
- residency figures (cited from reports, not re-measured).

None of these changed the verdict.

---

## 15. Post-audit corrections (auditable history)

- **COR-1 (2026-09-26, found during the G0 repair pass).**
  - **What changed:** C-12 and §2 attributed A2.8H's incorrect confident binding to `NB-H-06` and cited only D1R 16/84.
  - **Corrected evidence:** `docs/plans/M35_URIV1_A2_8I_POST_REPAIR_END_TO_END_RESIDUAL_AUDIT.md` §3, item 8 records one incorrect confident binding at C1 and one at C2, and corrects the C2 identity to `NB-B-05:r1`, not `NB-H-06`. The same audit also confirms the D1RQ research detector at 22/84 (26.2%) C1 resolution coverage and 13/84 C2, with 0 regressions versus D1R.
  - **Effect:** none on the verdict. The corrected figures are used in Plan B revision R1 (B-R1).
- **COR-3 (2026-09-26, found during the G0 repair pass). C-13 was an audit error.**
  - **What changed:** the audit read the "Silent detection miss" column of `docs/plans/M33_3_BATCH_A_COMPLETION_REPORT.md` §7 (D0 row: 21) as a count over the 27 resolvable references.
  - **Corrected evidence:** the same report's prose states "every explicit filename or noun phrase is a silent detection miss (20 of 27 resolvable references; 21 of 32 rows including the must-abstain `RWB-013`)". Plan A's "20/27" is correct.
  - **Effect:** repair A-R10 is `NOT_APPLICABLE` (no change to Plan A's figure). There is no effect on the verdict.
- **COR-4 (2026-09-26). Section reference.** C-9, §6 item 8, and §2 cite "M33.2 §8" for the calibration rule "never trained online from a single user's traffic". In `docs/architecture/M33_2_EDGE_SECOND_BRAIN_CANONICAL_ARCHITECTURE.md` that rule is in **§9.1 Calibration** (§8 is the control-panel backend contract). The substance is unchanged. Amendment G3 was placed in §9.1.
- **COR-2 (2026-09-26).** Plan B's SHA-256 was not recorded at audit time. The G0 repair pass recorded it from the same transcript message and confirmed that the transcript contains exactly one Plan B proposal message. See the Plan B artifact's provenance block.
