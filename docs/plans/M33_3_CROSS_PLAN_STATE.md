# M33.3 — Cross-Plan State: URI-REFERENCE-CLARIFICATION × URI Brain Architecture

**Current state:** `CROSS_PLAN_REPAIRED_AWAITING_INDEPENDENT_REAUDIT`
**Implementation authorized:** **NO.** No slice S1–S13 is open. No INT event exists. `URI-RAR` is not adopted.
**Branch / repair baseline:** `m35-uri-v1-parallel-architecture` @ `127c7339ad61d2929a7dda04e58e511d26241401`.
**Date:** 2026-09-26

## 1. Artifacts

| Role | Path | Identity | Status |
|---|---|---|---|
| Plan A | `docs/plans/M33_3_ARN_ARCHITECTURE_AND_LT1B_RENDERER_PLAN.md` (revision R2) | `URI-REFERENCE-CLARIFICATION` (planning identity; the bare alias "ARN" stays forbidden) | `PLAN_REVISED_R2_AWAITING_INDEPENDENT_CROSS_PLAN_REAUDIT` |
| Plan B | `docs/plans/M33_3_URI_BRAIN_ARCHITECTURE_PROPOSAL.md` (revision R1 over verbatim R0) | `M33_3_PLAN_URI_BRAIN_ARCHITECTURE` | `PROPOSAL_REVISED_R1_AWAITING_INDEPENDENT_CROSS_PLAN_REAUDIT` |
| Cross-plan audit | `docs/plans/M33_3_CROSS_PLAN_AUDIT_REPORT.md` | — | verdict `COMPATIBLE_WITH_BOUNDED_REPAIRS` (with post-audit corrections COR-1 to COR-4) |
| M33.2 amendments | `docs/architecture/M33_2_EDGE_SECOND_BRAIN_CANONICAL_ARCHITECTURE.md`: header amendment note; G1 under §3.1; G2 note under §3 table and G2 block under §6 table; G3 under §9.1 | — | recorded (User-directed); fidelity subject to re-audit |
| Canonical state | `docs/governance/URI_STATE.yaml` → `planning_artifacts`, `architecture_decisions`, `active_continuation` | — | updated additively |

Plan B provenance: recovered verbatim from Codex session `rollout-2026-09-26T03-31-00-01a0da96-071c-72f0-8562-0f71ac9457db.jsonl` (message 2026-09-25T22:51:31.958Z). The SHA-256 of the R0 text is `cf08a0892a8b87508b771edb3a856da652ef19f57ffdc7fb66245108962b8a9b`. A scan of all 2026-09 Codex rollouts found exactly one such message.

## 2. User decisions (recorded exactly, 2026-09-26)

**D1: wrong-binding impact for Gmail drafts.**
- `gmail_create_draft` is `RECOVERABLE`.
- Reason: creating an unsent draft can be corrected before external communication occurs.
- The classification is independent of `EffectType`, `ApprovalRequirement`, and `RiskLevel`.
- A future real send action is expected to be `CONSEQUENTIAL`.
- `wrong_binding_impact` must not be derived mechanically from `EffectType`.

**D2: intelligence/routing modes.**
- KEEP `EDGE_ONLY`, `HYBRID`, and `MAIN_BRAIN_PREFERRED`. Do not replace them with AUTO / selected-model / Edge-OFF, because those are different dimensions.
- **AUTO + HYBRID:** deterministic mechanisms first; a qualified Edge may perform substantive bounded work; the Capable Brain is used when Edge is not qualified or not sufficient.
- **AUTO + MAIN_BRAIN_PREFERRED:** deterministic mechanisms still run; substantive model work normally goes directly to the Capable Brain; a qualified Edge may perform supporting work.
- **Explicit model selected:**
  - the selected model becomes the Capable Brain for substantive model work;
  - deterministic URI mechanisms remain active;
  - qualified supporting Edge work remains permitted;
  - model-native capabilities must be preserved.
- **Edge OFF:** removes Edge inference only; deterministic URI mechanisms remain active; the Capable Brain remains available unless another explicit policy forbids it.
- **EDGE_ONLY:** deterministic URI mechanisms plus qualified Edge only; never silently call the Capable Brain; if the task exceeds those capabilities, surface the limitation or escalation requirement instead of violating the mode.
- HYBRID is efficiency-first. MAIN_BRAIN_PREFERRED is capability-first. Do not merge them.

**D3: model-assisted reference investigation.**
- Qualified Edge or Capable models MAY: investigate; interpret clues; compare grounded candidates; narrow candidates; annotate candidates; return structured evidence.
- They MAY NOT independently create binding authority. Model preference alone must not directly create a TENTATIVE binding.
- Required flow: model interpretation/investigation → structured grounded evidence → deterministic resolution/eligibility check → TENTATIVE / CONFIRMED / CLARIFY.
- RAR and deterministic mechanisms remain authoritative for candidate identity and binding state. Model output must never invent candidate IDs.

**D4: durable reference evidence. Status: `DEFERRED`** (not unresolved).
- Durable cross-session learned reference evidence is deferred to URI-Memory.
- **Allowed now:**
  - session-authoritative selections;
  - session-local reference evidence;
  - structured correction/Change events;
  - rank/display effects from valid session evidence.
- **Not authorized now:**
  - a new ad-hoc durable cross-session reference-memory subsystem;
  - durable learned tie-breaking without URI-Memory qualification.

## 3. Repair application index

| Repair | Where applied |
|---|---|
| A-R1 | Plan A R2.1 (+ markers at R1.7) |
| A-R2 | Plan A R2.2 (+ marker at §4 enum) |
| A-R3 | Plan A R2.3 (+ marker at §4.1) |
| A-R4 | Plan A R2.4 (+ markers at §7 loop limit and correction rule) |
| A-R5 | Plan A R2.5 (+ markers at R1.3, §3, §6 fallback chain, §9) |
| A-R6 | Plan A R2.6 (+ marker at R1.5) |
| A-R7 | Plan A R2.7 (+ markers at R1.7, §8) |
| A-R8 | Plan A R2.8 (+ marker at R1.5 timing) |
| A-R9 | Plan A R2.9 (+ marker at R1.5 "strongly preferred") |
| A-R10 | `NOT_APPLICABLE`: evidence confirms 20/27 (Plan A R2.10; audit COR-3) |
| A-R11 | Plan A R2.11 |
| A-R12 | Plan A R2.12 |
| B-R1 | Plan B R1.1 |
| B-R2 | Plan B R1.2; M33.2 G2 |
| B-R3 | Plan B R1.3; M33.2 G3 |
| B-R4 | Plan B R1.4 |
| B-R5 | Plan B R1.5 |
| B-R6 | Plan B R1.6 |
| B-R7 | Plan B R1.7 |
| B-R8 | Plan B file itself, with provenance block; `URI_STATE.yaml` `planning_artifacts` |
| B-R9 | Plan B R1.9; M33.2 G2 last paragraph |

## 4. Slice readiness (after repair, pending re-audit)

| Slice | Content | Classification | Gate(s) |
|---|---|---|---|
| G0 | Governance: Plan B durable, identities registered, decisions recorded | DONE by this pass (subject to re-audit) | — |
| S1 | RC deterministic core in `uri_v1` against fixtures (contracts incl. `CONFIRM_ONE` and bundle, builder, template, validator, `BindingService`, lifecycle states, session adjunct, stop safeguards) | BLOCKED until re-audit passes | PG-1 |
| S2 | `Action.wrong_binding_impact` production field + execution-gate check | BLOCKED until re-audit passes and the capability-contract extension is accepted | PG-2 (D1 now answered) |
| S3 | Battery L1/L2 (no model) | after S1 | PG-1 |
| S4 | Offline source-to-candidate / RAR-boundary replay (Plan B stage 1, with D0/D1R/D1RQ arms) | EXPERIMENT_REQUIRED; needs its own pre-audited plan | PG-5, PG-6 |
| S5 | Wording qualification (template vs Edge vs Capable, User blind rating) | EXPERIMENT_REQUIRED | S1, S3 |
| S6 | Unified router extension (mode mapping, explicit selection, Edge OFF) | BLOCKED until re-audit passes | PG-3 (D2 now answered; G2 recorded) |
| S7 | Response `trace_id` + structured evaluation event stream | PLAN_REQUIRED (no slice plan exists) | — |
| S8 | Route-performance store + learning replay | EXPERIMENT_REQUIRED | S6, S7 |
| S9 | Durable learned reference tie-break | **DEFERRED** (D4: URI-Memory) | URI-Memory + correction-rate experiment |
| S10 | Lease ownership + Capable Brain residency study | EXPERIMENT_REQUIRED | — |
| S11 | Result-version owner (Case H/I redo) | PLAN_REQUIRED (no owner exists; `uri_ui` editability UNVERIFIED) | — |
| S12 | Clickable UI options in `uri_ui` | BLOCKED | S1 contract freeze |
| S13 | Production integration into `uri_core` | BLOCKED | S4 results, `URI-RAR` adoption, INT authorization |

## 5. Gates

- **RG-0 (next):** an independent cross-plan re-audit of Plan A R2, Plan B R1, the M33.2 amendments G1–G3, and this state file. It is performed by an agent other than the author of this repair pass.
- **PG-1:** RG-0 passes before S1.
- **PG-2:** RG-0 passes and the `wrong_binding_impact` capability-contract extension is explicitly accepted before S2.
- **PG-3:** RG-0 passes (including G2 fidelity) before S6.
- **PG-4:** G1 fidelity is confirmed by RG-0 before any production wording path.
- **PG-5:** S4 has its own plan, independently pre-audited, with hash anchors. The frozen Batch A battery (`06d0dfff…c3fa`) and A9 stay untouched.
- **PG-6:** the A9 `rar_deterministic.py` SHA-256 `e02af25bb7009d12d829c8b8fc92e487d3da75aeaa160092db617458278fb649` is verified before and after any RAR-touching slice.

## 6. Protected artifacts at repair time (verified unchanged)

| Artifact | SHA-256 |
|---|---|
| `uri_v1/turn/rar_deterministic.py` (A9-protected) | `e02af25bb7009d12d829c8b8fc92e487d3da75aeaa160092db617458278fb649` |
| `uri_v1/turn/rar_contracts.py` | `4cc9aa43726a870ca2e9ab1b19f6bf9d72dcb74c8a2818856776af95195b6819` |
| `fixtures/m33_3_batch_a/battery.json` (LF-normalized, frozen) | `06d0dfffd8ecabff8b98ea7d24c1574904aa16fa172a3956e0a5fb95d6d1c3fa` |
| `docs/plans/M33_3_BATCH_A_COMPLETION_REPORT.md` (cited for 20/27) | `91eedf19fe2ecd3a8568f55acdf44c7e59582c08952ee3a14edbef2ffe413e4f` |
| `docs/plans/M35_URIV1_A2_8H_EXECUTION_REPORT.md` (untracked; cited by Plan B R1.1) | `4084a2eb4391c9ffb0da1f3a5fb504743327f53400a0115cc514d400db45935d` |
| `docs/plans/M35_URIV1_A2_8I_POST_REPAIR_END_TO_END_RESIDUAL_AUDIT.md` (untracked; cited by Plan B R1.1) | `bc16074239df33e40cc3cc19a9b0795feae14562c6ad992a13cc4b241d0670f8` |

## 7. Re-audit handoff

The re-auditor should verify at least the following from repository evidence alone:
1. Plan B R0 matches the recorded SHA-256 and the transcript source.
2. Every A-R and B-R repair maps to the text in §3.
3. D1–D4 appear exactly as in §2 and are applied consistently.
4. The M33.2 amendments are additive, preserve the prior text, and match D2 and the G1/G3 intent.
5. No stale contradiction survives unmarked for:
   - ExperienceStore reference learning;
   - Graphify document/email retrieval;
   - model-created TENTATIVE;
   - explicit-model `SUPPRESS`;
   - template-only fallback;
   - TOOL_CATALOG tiers;
   - 20/27;
   - "correction is always a new request";
   - duplicate routers;
   - durable learning before URI-Memory.
6. No production code, frozen artifact, or research code changed.
7. Plan A R2.11 invents no existing field (the `depends_on` / provenance source is marked planned).

**Known limitation:** this repair pass was performed by Claude, which also authored Plan A and the cross-plan audit. Independence of RG-0 is therefore required.
