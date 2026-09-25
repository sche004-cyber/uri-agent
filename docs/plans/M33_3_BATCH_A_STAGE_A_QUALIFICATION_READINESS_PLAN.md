# M33.3 Batch A — Edge Intelligence Stage A Qualification Readiness

**Status:** FROZEN / ACCEPTED (planning only). Implementation not started.
**Milestone:** M33.3 — Edge Intelligence Qualification & Integration
**Author:** Claude Opus 5.5 (Architect / Pre-Auditor, AO-4)
**Date:** 2026-09-25
**Baseline commit:** `1fa24fca97dec34e431e82062b27b3da222b87cd` (branch
`m35-uri-v1-parallel-architecture`; `origin/m35-uri-v1-parallel-architecture`
was verified equal to this commit with `git ls-remote` before drafting).
**Authoritative parent plan (unchanged by this document):**
`docs/plans/M35_URIV1_A3_ARCHITECTURE_SYNTHESIS_AND_NEXT_BATCH_PLAN.md`
(frozen at `47af60a`; final independent architecture re-audit verdict
`ACCEPT_WITH_DOCUMENTED_LIMITATIONS`, terminal audit state
`ARCHITECTURE_PLAN_ACCEPTED_WITH_LIMITATIONS`, limitations L1–L9 recorded in
that commit's message). Cited below as "A3 §n".
**State file:** `docs/plans/M33_3_BATCH_A_STATE.md`
**Approval basis:** AO-4 standing auto-approval (`ORCHESTRATION.md` §1.5).
This batch is isolated, non-production qualification work. It does not change
URI's core structure, product identity, security/authority model, or any
constitutional boundary, so the auto-approval escape hatch does not apply.

---

## 0. Scope in one paragraph

Batch A is the first executable batch of M33.3. It prepares and runs **Stage A
(isolated qualification) readiness work only** (A3 §10). It freezes the
real-workload battery that A3 §8 left incomplete, builds a scorer and telemetry
schema for the A3 §9 gates, measures the already-qualified reference baselines
on that battery, characterizes the unmodified deterministic path (Rung 0,
as-is), writes a documentary mapping from candidate outputs to the accepted
M33.2 Edge contracts, and records whether Rung 1 is eligible. It qualifies no
new candidate. It changes no mechanism. It creates no production integration
authority.

---

## 1. Acceptance criteria for this plan (defined before drafting)

This plan is acceptable only if all of the following hold. Section 16 records
the self-review against them.

- AC-1. The M33.3 identity, lineage, objective, and exclusions come from the
  frozen A3 plan and `URI_STATE.yaml`, not from the task prompt.
- AC-2. Every prerequisite has a primary-evidence check with a status.
- AC-3. Every research line has one admissibility class and a stated
  admissible use.
- AC-4. No gate threshold is invented. Each gate cites its source, or is
  marked `UNMEASURED` with the evidence gap stated.
- AC-5. The batch does not skip A3's ordering: Stage A before Stage B before
  Stage C; Rung 0 before Rung 1; no Rung 2 by default.
- AC-6. No file under `uri_core/`, `uri_v1/`, or `uri_ui/` is modified by this
  plan or authorized for modification by this batch.
- AC-7. No research component is promoted. No `INT-*` event is created.
- AC-8. Every conflict found between artifacts is documented, not merged into
  a hybrid.
- AC-9. Every prior result cited has a repository source. Where that source is
  untracked, the plan says so and pins its content hash.

---

## 2. Authoritative M33.3 identity (Phase 1)

| Field | Value | Source |
|---|---|---|
| Title | M33.3 — Edge Intelligence Qualification & Integration | `URI_STATE.yaml` `product_milestones[M33.3].title`; A3 §16 |
| Status before this task | `PLANNING_BASIS_FROZEN`, implementation not started | `URI_STATE.yaml` M33.3 entry; `active_continuation.status: NONE_AUTHORIZED_TO_IMPLEMENT` |
| Lineage | `continues_architecture_of: M33.2`; domain `edge_second_brain`. Extends M33.2; does not reopen it. | `URI_STATE.yaml`; A3 §16 |
| Evidence inputs | EXP-M35-URIV1-A0-A9 research line (closed, evidence only) | `URI_STATE.yaml` `research_experiments` |
| Prerequisite milestones | M33.2 (CLOSED_VERIFIED) as architecture foundation and contract owner | A3 §1, §16 |
| Objective | Qualify and, only after independent evidence, integrate the next generation of URI Edge / Second-Brain capability through the accepted M33.2 provider-neutral Edge contracts (`uri_core/core/edge/`). | A3 §16 "Purpose" |
| Defined stages | Stage A isolated qualification → Stage B replay/read-only integration through M33.2 contracts → Stage C separately authorized production-integration decision | A3 §10–§12, §16 |
| Defined ladder | Rung 0 deterministic safety/gating only → Rung 1 adaptive-feed Qwen3.5-0.8B (conditions frozen before execution) → Rung 2 (4B) only with a predeclared advantage hypothesis over resident 9B; default `4B_RUNG_NOT_YET_AUTHORIZED` | A3 §7, §16, §18 |
| Explicit exclusions | A3 §17 in full, including: no A9 reopening; no Memory Engine; no RAR productization; no 4B download/test; no competing Edge architecture under any M35 label; no constraint of the resident Main Brain to Edge-tier capability | A3 §15, §17 |
| Pre-defined batches | None. A3 defines stages and rungs, not batch IDs. This plan assigns the first batch ID. | A3 §16, §18 |

### 2.1 Conflicts found and how each is handled

- **C-1. Stale M33.3 identity.** `URI_ACTIVE_MILESTONE.md` §1c and
  `docs/plans/M33_1_REAL_INTEGRATIONS_EXTENSION_VALIDATION_PLAN.md:40` still
  describe M33.3 as "Unified URI Interaction & Capability UI". This was
  superseded at `47af60a` and reconciled in `URI_STATE.yaml`
  (`human_readable_pointer.reconciled: true`). The frozen identity governs.
  No hybrid is formed.
- **C-2. Orphaned M33.2 follow-on item.** The M33.2 migration plan (§5
  acceptance line, §7, §9 item 8) records "live control-surface confirmation"
  as an "M33.3-owned follow-on acceptance item". That text was written for the
  superseded UI identity (C-1). The frozen A3 plan does not adopt it. This plan
  does not adopt it either. Ownership of that item is **unresolved**. It does
  not affect Batch A, because Batch A has no UI and no control-surface scope.
  It must be resolved before any M33.3 work claims control-surface acceptance.
- **C-3. M33.2 migration Batches C–F were never executed.** The M33.2 final
  closure (`URI_ACTIVE_MILESTONE.md`, "M33.2 ... FINAL CLOSURE") recorded "No
  Batch C required" and closed on Batches A–B.4. Live Edge routing, calibration
  and threshold activation, modality foundations, and cross-device closure
  from that plan therefore have no owner inside M33.2. A3 §12 places any
  production-integration decision in a later, separately authorized M33.3
  Stage C. This plan does not re-scope those items into Batch A.
- **C-4. "A2.8D" names two different things.** The tracked report
  `M35_URIV1_A2_8D_EXECUTION_REPORT.md` is a reference detection/delivery
  experiment. The untracked code `uri_v1/edge/a2_8d_*.py` is a separate
  "Edge-Brain & Fast-Path" harness (Needle, LFM2.5-350M, Qwen3.5-0.8B,
  Qwen3.5-2B configurations) that was never run or reported, and whose
  `fast_path_gate.py` hardcodes answers to its own cases
  (`URI_DEVELOPMENT_EVIDENCE_REGISTRY.md:144,190,761`;
  `M35_URIV1_STEP2_NEEDLE_RAR_STATE_RECONSTRUCTION.md:17,99-110`). This plan
  cites the report only, and classifies the code as `REJECTED` (contaminated,
  no evidence).
- **C-5. Task-prompt hypothesis versus A3 ordering.** The task prompt's working
  shape included "prove compatibility with M33.2 Edge contracts". A3 §11 puts
  executable compatibility testing through the M33.2 interfaces in Stage B,
  which may start only after Stage A qualification and independent review.
  This plan therefore narrows that item to a **documentary** contract-mapping
  specification (WP-A5). Executable compatibility proof stays in Stage B.

---

## 3. Dependency closure (Phase 2)

| # | Prerequisite | Evidence inspected in this task | Status |
|---|---|---|---|
| D-1 | M33.2 accepted and closed | `URI_STATE.yaml` M33.2 `CLOSED_VERIFIED`, `currently_active: false`, `mutable: false`; `URI_ACTIVE_MILESTONE.md` M33.2 FINAL CLOSURE ("Verdict: VERIFIED / CLOSED") | SATISFIED |
| D-2 | Control layer frozen and valid | `python scripts/governance/uri_state_validator.py` → `VALID` at baseline; `python -m pytest tests/governance -q` → `37 passed` at baseline (both run in this task) | SATISFIED |
| D-3 | M33.2 Edge contracts exist and are unchanged since closure | `git diff --stat 340a009 HEAD -- uri_core/core/edge uri_core/core/edge_lifecycle scripts/m33_2_needle_bridge.py fixtures/m33_2_edge_benchmark` → empty; last commit touching `uri_core/core/edge*` is `eaf97c5` (B.4 release); `git status` shows no local change under `uri_core/` | SATISFIED |
| D-4 | M33.2 regression set still passes | Six-file set re-run in this task: **58 passed, 2 failed**. Both failures are `test_perception_corpus_schema_and_sha256_are_frozen[vision|audio]`. Root cause verified: this worktree has `core.autocrlf=true`, so the working copies are CRLF (`git ls-files --eol` → `i/lf w/crlf`). The committed LF blobs hash to the manifest values exactly (vision `0e814339…a452`, audio `e457ab64…1087`). Environmental, not a contract regression. | SATISFIED WITH DISCLOSED ENVIRONMENTAL LIMITATION (see §12, R-1) |
| D-5 | Frozen A3 plan unchanged | `git log -- docs/plans/M35_URIV1_A3_...PLAN.md` → only `47af60a`; `git status` clean for that file | SATISFIED |
| D-6 | No implementation or integration authorization already exists | `URI_STATE.yaml` `integration_events: []`; `active_continuation.status: NONE_AUTHORIZED_TO_IMPLEMENT`; no `docs/plans/M33_3_*` file existed before this task | SATISFIED |
| D-7 | Zero import boundary between `uri_core/` and `uri_v1/` | `grep` for `import uri_core`/`from uri_core` in `uri_v1/` and `import uri_v1`/`from uri_v1` in `uri_core/` → no matches (two docstring mentions of `uri_core.core.edge.adapters` in `uri_v1/turn/needle_*.py` are text, not imports) | SATISFIED |
| D-8 | A3 limitation L8 (Needle production wiring unverified) | Resolved at grep-plus-read level in this task. `evaluate_routing` has no caller outside its own module. `uri_core/app/server.py` imports only `DEFAULT_EDGE_RUNTIME_INVENTORY`, the settings store, and the trace store, and exposes settings/status/trace endpoints (`server.py:3027-3095`). `DEFAULT_EDGE_RUNTIME_INVENTORY = EdgeRuntimeInventory()` has no runtimes, so `selection_status` can never return `ready`. `NeedleSubprocessAdapter` is used only by benchmark scripts and tests. **Needle 3 is not dispatched in production today.** Runtime confirmation (a live request trace) was not performed; Stage B must still confirm it at runtime. | RESOLVED STATICALLY; runtime confirmation deferred to Stage B |

No prerequisite is unmet. M33.3 Batch A activation is not blocked.

---

## 4. Research-to-production admissibility (Phase 3)

Classes: `PRODUCTION_AUTHORITATIVE`, `ACCEPTED_RESEARCH_EVIDENCE`,
`EXPERIMENTAL_CANDIDATE_EVIDENCE`, `REJECTED`, `SUPERSEDED`,
`INFORMATIONAL_ONLY`. "Tracked" means committed to git. Untracked sources are
mutable and have no git provenance; their content hash at this baseline is
pinned in §4.1 and Batch A must re-verify it before use.

| # | Research line / artifact | Result (with source) | Class | Admissible use in M33.3 |
|---|---|---|---|---|
| E-1 | M33.2 Edge contracts, routing policy, settings, trace (`uri_core/core/edge/`, tracked) | Accepted production foundation; routing policy not wired (D-8) | `PRODUCTION_AUTHORITATIVE` | Protected contract surface (§7). Mapping target for WP-A5. Not imported by Stage A code. |
| E-2 | M33.2 B.4 Needle 3 qualification (tracked report and state) | `RESIDENT` for reflex tool routing / competing-tool selection and structured-record extraction only; routing 8/8, structured extraction 4/4, argument extraction 2/4 = 50%; p50 159.17 ms, p95 207.40 ms; peak RAM 101.4–101.6 MB (`M33_2_BATCH_B4_COMPLETION_REPORT.md:85-97`; `M33_2_BATCH_B4_STATE.md:77-79`) | `PRODUCTION_AUTHORITATIVE` for that narrow role only | Reference baseline R-NEEDLE; harness reproduction gate G-R1. Argument values stay untrusted. |
| E-3 | M33.2 B.4 Main-Brain controls | `qwen3.5:9b` warm p50/p95 129.87/156.18 ms on the bounded-reasoning tier (`M33_2_BATCH_B4_COMPLETION_REPORT.md:145-148`); host had no observable GPU API (`:35`) | `ACCEPTED_RESEARCH_EVIDENCE` | Informs latency comparison. Host-specific; not a threshold. |
| E-4 | A2.7 resident Qwen3.5-9B-Q4_K_M | `QWEN3_5_9B_SEMANTICALLY_QUALIFIED`; 100% operation retention, 100% negation ladder, 96.8% contrastive negation (`A2_7...:23,27,35`); peak VRAM ~7.43 GB on a 16 GB GPU (`:59`) | `ACCEPTED_RESEARCH_EVIDENCE` (untracked report; accepted by A3 re-audit) | Reference baseline R-9B (ceiling and escalation reference, A3 §6). Resource-measurement method (A2.7 §1.2) reused. |
| E-5 | Deterministic RAR Stage 4B, 27/136 subset | 27/136 = 19.9% proven deterministic references **over the pre-segmented 136-fixture benchmark**; 0/136 raw turns directly RAR-ready; Stage 4B "cannot measure true raw-turn standalone RAR coverage" (`A2_5_RAR_STAGE4B_EVIDENCE_RECONCILIATION_REPORT.md:22,27,133`) | `ACCEPTED_RESEARCH_EVIDENCE` classified `PROVEN_COMPONENT_CAPABILITY_WITH_BOUNDED_SCOPE` (A3 §3) | Defines the Rung 0 as-is scope. Never a production coverage figure. Always stated with 0/136 and 0/84. |
| E-6 | Stage 4B hybrid architecture | 122/136 = 89.7% match; 73.5% deterministic coverage **of the same 136-fixture population**; 6 wrong bindings (4.4%); deterministic-only ablation 75.0% (`A2_5_RAR_STAGE4B_REQUALIFICATION_AUDIT_REPORT.md:13-24`) | `ACCEPTED_RESEARCH_EVIDENCE` (`PROVEN_WITH_BOUNDED_LIMITATIONS`) | Unsafe-binding inventory input for WP-A4. Not a threshold. (Addresses A3 L3 by stating the population.) |
| E-7 | A2.8D reference detection/delivery (tracked JSON, untracked report) | Real (D0-equivalent) path 0/84 confident resolution; Category A 80/84 = 95.2%; six genuine unsafe resolutions with two mechanisms (Level-5 recency returns before Level-6 validation; Level-4a cannot represent relational exclusion) (`A2_8D_EXECUTION_REPORT.md:40-44,142`). Figures later corrected in part by A2.8E (`:3`). | `ACCEPTED_RESEARCH_EVIDENCE` (`REJECTED` as a production path, A3 §3) | Unsafe-binding inventory input for WP-A4 (addresses A3 L4). Natural-boundary corpus reusable as fixture source. |
| E-8 | RAR Natural-Boundary corpus (`uri_v1/turn/rar_natural_boundary_raw_turn_fixtures.json`, tracked) | SHA-256 `0ea54473…7380` re-verified in this task; equals the frozen value in `A2_8D_VERIFICATION_AND_QUALIFICATION_PLAN.md:61` | `ACCEPTED_RESEARCH_EVIDENCE` | Fixture source for reference-bearing battery cases. Must not be modified. |
| E-9 | A2.8J RAR-SAFE, A2.8K Level-5 sufficiency | A2.8J accepted as experimental result, "NOT a promotion of RAR-SAFE or of S3" (`A2_8J_STATE.md:3`); A2.8K H1–H4 `PARTIALLY_SUPPORTED` (`A2_8K_STATE.md:7-10`) | `EXPERIMENTAL_CANDIDATE_EVIDENCE` | Informs a future Rung 0 hardening plan only. Not run in Batch A. |
| E-10 | A9 evidence-transport factorial | Frozen; nine limitations; any further work needs a separate batch (`A2_8L_A9_CLOSURE_REPORT.md` §8–§9) | `ACCEPTED_RESEARCH_EVIDENCE`, frozen | Read-only evidence. `rar_deterministic.py` hash `e02af25b…b649` must stay equal to the overlay-manifest protected hash (`A2_8L_OVERLAY_MANIFEST.md:76`); verified equal in this task. |
| E-11 | A2.9 native problem-solving trace pilot | Native capability inspection 8/8; zero invented action names; "4/8 is a pilot result, not a qualification score" (`A2_9_STATE.md:9-17`) | `EXPERIMENTAL_CANDIDATE_EVIDENCE` (pilot) | Supports gate G-N1 (native-capability preservation) as a behavior to protect. Not a score. |
| E-12 | A2.6 Qwen3.5-2B + adaptive concurrent feeds | Mode D 254.7 ms mean, 8.1x; goal 94.7%; requested operation 73.7% and negation below the ≥90% gate; verdict `QWEN3_5_2B_SUB_THRESHOLD_ESCALATE_TO_4B` (`A2_6...:21-22,69`) | `REJECTED` for the tested Step-1 decoder role; architecture `EXPERIMENTAL_CANDIDATE_EVIDENCE` | Source of the Rung 1 harness shape and the ≥90% four-axis gate (with A3 §18). The report's "escalate to 4B" verdict is superseded by A3 §7 (`4B_RUNG_NOT_YET_AUTHORIZED`). |
| E-13 | A2.2 Qwen3.5-0.8B decoder | Reference gate 0.0%; mean latency 1,850.5 ms under a non-adaptive single-schema harness (`A2_2...:147,164,199-204`) | `REJECTED` for that tested role and harness | Evidence that Rung 1 must use a materially different (adaptive-feed) harness. |
| E-14 | A2.3 / A2.4R Needle as Step-1 semantic decoder | "Definitively rejected as Step-1 semantic decoder" (`A2_3...:16`); `REJECT NEEDLE AS STEP-1 DECODER` (`A2_4R...:24`; A3 cited `:21`, the table header two lines above) | `REJECTED` for that role only | Prevents re-testing Needle for semantic decoding. Does not affect E-2. |
| E-15 | A2.5 LFM2.5-350M | `LFM_TOO_WEAK_EVEN_WITH_DECOMPOSITION` (`A2_5_STAGE4...:19-22`) | `REJECTED` for the tested role | Not used. |
| E-16 | A2.4 / A2.4R Qwen3-14B control | 100% on tested axes; 7.4–8.5 s latency; offline control only (`A2_4R...:25`) | `INFORMATIONAL_ONLY` | Not a baseline in Batch A (latency class excluded by A3 §3). |
| E-17 | M33.2 B.4 SmolLM2-135M, Qwen2.5-0.5B | `BYPASS / REDUNDANT` (`M33_2_BATCH_B4_STATE.md:80-92`) | `REJECTED` for the tested roles | Not used. |
| E-18 | `uri_v1/edge/a2_8d_*.py`, `fast_path_gate.py`, 90-case suite (untracked) | Never run, reported, or tested; gate hardcodes benchmark answers (`URI_DEVELOPMENT_EVIDENCE_REGISTRY.md:144,190,761`) | `REJECTED` (`CONTAMINATED`) | Not usable. Battery cases must not be derived from its suite. |
| E-19 | Experimental URIv1 ARN (`uri_v1/arn/`, EXP-ARN-URIV1) | Research identity `CLOSED`, `promoted_to_production: false` (`URI_STATE.yaml` `research_experiments[EXP-ARN-URIV1]`); A2.8A reached `A2.8A_ACCEPTANCE_READY` only (`A2_8A_ARN_FOUNDATION_REPORT.md:10`) | `EXPERIMENTAL_CANDIDATE_EVIDENCE` | Not used in Batch A. Never to be confused with production ARN (ARN.1, `uri_core/core/arn/`, CLOSED_VERIFIED; parent paused). Bare "ARN" is forbidden (`URI_STATE.yaml` alias guard). |
| E-20 | Graphify / context resolution | Not covered by any inspected M33.3 evidence (A3 §4 item 5) | `UNMEASURED` / `INFORMATIONAL_ONLY` | Out of Batch A scope. |
| E-21 | Prompt-minimization findings (A2.2 unconstrained JSON 0/18, prompt-only pronoun rules fragile) | `URI_DEVELOPMENT_EVIDENCE_REGISTRY.md:238-240,838,845` | `ACCEPTED_RESEARCH_EVIDENCE` (negative precedent) | Harness rule: small-model calls use constrained/schema output; no reliance on prose pronoun instructions. |

No row above is promoted by this plan. `URI-RAR` stays `EXPERIMENTAL`;
`URI-Edge` stays `EXPERIMENTAL` on the component-portability axis
(`URI_STATE.yaml` `reusable_components`).

### 4.1 Evidence pinning at baseline `1fa24fc`

Untracked evidence has no git history. Batch A WP-A0 must re-hash these files
before use and stop on any mismatch (`EVIDENCE_PIN_MISMATCH`). Hashes are
SHA-256 of the bytes on disk, computed in this task.

| File | Tracked | SHA-256 |
|---|---|---|
| `docs/plans/M35_URIV1_A2_2_QWEN_DECODER_REPORT.md` | no | `b4869b4b9f80ca40037bdc2001a7d456db194c7f58967dcaac96aba9830eb675` |
| `docs/plans/M35_URIV1_A2_6_QWEN3_5_2B_QUALIFICATION.md` | no | `23daeff33dc7437aef83ed3f2ba45659e7e24114a23ec7eca6d7b1c59aac6cb2` |
| `docs/plans/M35_URIV1_A2_7_RESIDENT_MAIN_BRAIN_SEMANTIC_QUALIFICATION.md` | no | `02195bf1efd28c696aaaab71705d2b385fcc315f5e2a67219de9dfac10f6a08b` |
| `docs/plans/M35_URIV1_A2_5_RAR_STAGE4B_EVIDENCE_RECONCILIATION_REPORT.md` | no | `acb6a26b4dfea7661b6a35732d0685103dee0a325844ac997ecfbf7c4249c258` |
| `docs/plans/M35_URIV1_A2_5_RAR_STAGE4B_REQUALIFICATION_AUDIT_REPORT.md` | no | `0881450f1a8d0c7227720b5e69959a12d6c0f1bd68ee778435045bb58c784eca` |
| `docs/plans/M35_URIV1_A2_8D_EXECUTION_REPORT.md` | no | `12f3288359fb998d1d2a74d9e74bc8382654e29208d49ca332c752da8c2cb216` |
| `docs/plans/M35_URIV1_A2_8E_RESIDUAL_CHARACTERIZATION_REPORT.md` | no | `9d1c517b14c8ce121e09649d7dc937d95fa8e982f6e1e4d951a2d89b66a59285` |
| `docs/plans/M35_URIV1_STEP2_NEEDLE_RAR_STATE_RECONSTRUCTION.md` | no | `9ce1addad35ed5d071a76ce0d3f5663de670015fdcdb479adc88f44a8d67f081` |
| `docs/governance/URI_DEVELOPMENT_EVIDENCE_REGISTRY.md` | no | `f53d641089e629f6407aa8a405007f8f8acb006c09be2fec19c642b462584d34` |
| `uri_v1/turn/rar_stage4b_independent_fixtures.py` | no | `f5678b2da1d08937578b69cbb4e1a7f98b3cb07339baa302243597943453142e` |
| `uri_v1/turn/rar_natural_boundary_raw_turn_fixtures.json` | yes (LF in both index and working tree) | `0ea5447354481041181538244ef70b6dc58a72267dd95263d61dbdb55ab07380` |
| `uri_v1/turn/rar_deterministic.py` | yes | `e02af25bb7009d12d829c8b8fc92e487d3da75aeaa160092db617458278fb649` (git blob content) |
| `fixtures/m33_2_edge_benchmark/corpus.json` | yes (CRLF in this working tree) | `4083c21a6a309b237eca921281828053b51cd0e6a11ae3301048c631bae1e45d` (committed LF content; the CRLF working copy hashes differently) |

---

## 5. Selected first batch (Phase 4)

**Batch ID:** `M33.3-A`
**Title:** M33.3 Batch A — Edge Intelligence Stage A Qualification Readiness
**Objective:** Make Stage A measurable. Produce a frozen, scorable battery,
measured reference baselines, an as-is Rung 0 characterization, a documentary
M33.2 contract mapping, and a Rung 1 eligibility record, so that the next batch
can qualify a real candidate against predeclared, evidence-derived gates.

Why this is the smallest coherent first batch:

- A3 §8 says the battery must be completed "before any execution is
  authorized". No candidate can be qualified without it.
- A3 §9 names the resident 9B and the M33.2 Edge controls as comparison
  baselines. They have never been measured on this battery. Without them, no
  later threshold can be "selected from comparative baseline evidence"
  (the M33.2 migration plan §3 acceptance rule).
- A3 §7 puts Rung 0 first and says deterministic mechanisms come before AI.
  Batch A measures the unmodified deterministic path so that any Rung 0
  hardening batch has a measured target.
- Rung 1 execution requires ten conditions to be frozen first (A3 §7). Batch A
  records eligibility and drafts those conditions; it does not run Rung 1.

### 5.1 Work packages

All work is offline, isolated, and local. All side-effecting tools are mocks.
No work package may import `uri_core`.

**WP-A0 — Baseline, environment, and evidence pinning.**
Record HEAD, `git status`, and host metadata (OS, CPU, RAM, GPU/VRAM or
"unobservable", runtime and version, model artifact identifiers and hashes).
This closes the gap A9 disclosed as L7 (missing per-run environment metadata).
Re-hash every §4.1 file. Stop on mismatch.

**WP-A1 — Battery completion and freeze.**
Complete the A3 §8 real-workload battery.
- Use the A3 §8 schema exactly. It has **14** required fields (A3 L5 corrected
  the stated count of 12): `case_id`, `input`, `provenance`,
  `active_session_context`, `available_tools`, `expected_task_interpretation`,
  `expected_tool_selection`, `expected_arguments`,
  `allowed_abstention_or_escalation_behavior`, `prohibited_actions`,
  `expected_final_outcome`, `ambiguity_label`, `safety_label`, `scoring_rule`.
- `scoring_rule` must give a separate pass/fail rule for each scored axis in
  WP-A2, not one combined rule (A3 L5).
- Keep the ten A3 worked examples `RWB-001`..`RWB-010` verbatim as the first
  case of each of the ten task types.
- Author at least six cases per task type (at least 60 cases total). This
  minimum is a coverage choice, not a performance threshold. Each type must
  include at least one `MUST_ABSTAIN` or `REQUIRES_CONFIRMATION` case, and the
  battery must include negation-bearing and bare-pronoun cases.
- Allowed provenance: synthetic; M33.2-reused
  (`fixtures/m33_2_edge_benchmark/corpus.json`, cite item ID and committed
  blob hash); natural-boundary-reused (E-8, cite case ID). Forbidden
  provenance: anything derived from E-18. No private user or institutional
  data.
- Held-out rule: the battery is authored and frozen before any baseline or
  candidate is run against it. No case may be edited after the freeze to
  change a result. A needed correction is additive and versioned, and
  invalidates prior runs.
- Store as tracked fixtures under `fixtures/m33_3_batch_a/` with a manifest.
  The manifest hash is computed over LF-normalized bytes (CRLF→LF before
  hashing). This avoids the D-4 defect.
- Freeze checkpoint: Claude reviews the battery against this section before
  WP-A3 runs. The battery hash is recorded in the state file.

**WP-A2 — Scorer and telemetry schema.**
- Score each axis separately: interpretation, tool selection, argument
  fidelity, abstention/escalation (precision and recall), prohibited-action
  preservation, completion.
- Row telemetry reuses the existing field names `latency_ms`,
  `boundary_violation`, `rar_invoked`, `scoring_class` (A3 §9), and adds:
  `false_confident_execution`, `unauthorized_execution`,
  `invented_candidate`, `resident_main_brain_invoked`,
  `unnecessary_resident_main_brain_invocation` (new field, required by A3 §9),
  `provider_id`, `runtime_id`, `model_id`, `artifact_hash`, `timeout`,
  `fallback_taken`, and resource fields per A2.7 §1.2 layering.
- `unnecessary_resident_main_brain_invocation` is true when the 9B was called
  on a case whose `expected_final_outcome` was fully reached by a cheaper path
  in the same run condition. The scorer must define this exactly before WP-A3.
- Unit tests prove: one false-confident unauthorized execution fails G-S1
  regardless of aggregate accuracy; `SUBJECTIVE` cases are never
  auto-scored; `UNMEASURED` is emitted rather than a zero when an axis was not
  run.

**WP-A3 — Reference baselines (measurement only).**
Run the frozen battery under these conditions:
- **R-NULL:** no Edge. Every case escalates. This is the "Main Brain alone"
  reference and the denominator for unnecessary-9B-invocation.
- **R-9B:** resident Qwen3.5-9B (the A2.7-qualified `Qwen3.5-9B-Q4_K_M`
  artifact where available; any other artifact is recorded as a deviation,
  never silently substituted). Invoke it through its native tool-calling
  interface with the same offered tools. Do not give it the small-model
  prompt or schema. Translate its native calls into the scoring schema after
  the call.
- **R-NEEDLE:** Needle 3 through a **new sibling** proposal-only bridge that
  accepts per-case tool schemas. `scripts/m33_2_needle_bridge.py` is an
  accepted M33.2 artifact with fixed tool schemas and must not be modified.
  The new bridge keeps the same posture: `tools=[]` plus JSON schemas only,
  `Needle.complete()` only, never `Needle.run()`, `NEEDLE_TELEMETRY=0`,
  `DO_NOT_TRACK=1`, `HF_HUB_OFFLINE=1`. The Needle interpreter is the existing
  `.venv-needle` in the protected legacy checkout, invoked read-only as a
  subprocess, following the A2.8D precedent. Needle is scored on all axes, but
  only tool selection and structured extraction count as in-role. Argument
  results are reported as `OUT_OF_QUALIFIED_ROLE`.
- **R-DET:** the unmodified deterministic RAR path (`rar_deterministic.py` at
  hash `e02af25b…b649`) on reference-bearing cases, with abstention. This is
  the as-is Rung 0 condition.
- Harness validity runs before battery conclusions: G-R1 and G-R2 (§8).

**WP-A4 — Rung 0 as-is characterization (no mechanism change).**
- Build one consolidated unsafe-binding inventory: the 6/136 Stage 4B wrong
  bindings (E-6) and the six A2.8D non-oracle unsafe resolutions with their
  two mechanisms (E-7), de-duplicated by mechanism. This addresses A3 L4.
- Report every R-DET false-confident binding on the battery, by mechanism.
- Output: a Rung 0 hardening requirement list for a later batch. Batch A does
  not implement it. Any fix that would touch A9-frozen scope needs its own
  authorization (A3 §7).

**WP-A5 — Documentary M33.2 contract mapping (no import, no execution).**
- Map each candidate output field to `EdgeProposal`, `RoutingInput`, and
  `EdgeRoutingTraceEvent` fields in `uri_core/core/edge/contracts.py`,
  `routing_policy.py`, and `trace.py` at baseline.
- List every field with no contract home as an explicit gap. Known candidates
  to check: `RoutingInput` has no abstention or ambiguity field; the trace has
  no unnecessary-9B field; `EDGE_REPLY` needs a current calibration, but Needle
  reports `confidence = null` (`M33_2_BATCH_B3_STATE.md:63`), so Needle can
  never satisfy `EDGE_REPLY` as the contract stands.
- A gap is recorded as evidence for a later decision. Batch A does not propose
  a contract change and does not change any contract.

**WP-A6 — Rung 1 eligibility record and draft execution conditions.**
- Record the eligibility evidence found in this task: A2.2 tested
  Qwen3.5-0.8B only under a non-adaptive single-schema harness (E-13); the
  `uri_v1/edge` "Config 2b" and "Config 4" 0.8B paths were never run (E-18).
  No executed, reported adaptive-concurrent-feed test of Qwen3.5-0.8B exists.
  Status: `RUNG_1_ELIGIBLE_PENDING_CONDITION_FREEZE`.
- Draft (not freeze) the ten A3 §7 conditions: model artifact and
  quantization; deterministic preprocessing; adaptive feed design; RAR and
  context inputs; prompt/envelope; invocation policy; schema; scorer;
  baselines; stopping rules. The draft goes into the Batch A report as input
  to a later plan.
- Rung 2 status stays `4B_RUNG_NOT_YET_AUTHORIZED`.
- No model download. No Rung 1 run.

**WP-A7 — Readiness report and handoff.**
`docs/plans/M33_3_BATCH_A_COMPLETION_REPORT.md` with every gate result or
`UNMEASURED`, the Batch A verdict (§10), and all deviations. Then
`VERIFICATION_READY` for Claude's independent audit.

### 5.2 Expected file footprint (implementation)

New only: `scripts/m33_3_batch_a_*.py` (harness, scorer, new Needle bridge),
`fixtures/m33_3_batch_a/` (battery and manifest), root-level
`test_m33_3_batch_a_*.py` (repository convention; there is no `tests/` package
for application tests, per the M33.2 migration plan §2), the completion report,
and the state file. Raw run output goes to a gitignored `temp_evidence/`
subdirectory, as in M33.2 B.4. No new Python dependency is expected; any new
dependency must be flagged in the completion report, never added silently.

---

## 6. Exclusions

Batch A does not:

- modify any file under `uri_core/`, `uri_v1/`, or `uri_ui/`, or `SKILL.md`;
- import `uri_core` from any Batch A harness, script, or test (except the
  WP-A5 mapping, which is a document, not code);
- connect to M33.2 Edge interfaces at runtime (that is Stage B);
- change routing policy, inventory, settings, trace, or any other contract;
- modify `scripts/m33_2_needle_bridge.py`, M33.2 fixtures, or M33.2 tests;
- modify any frozen fixture, A9 artifact, or research report, or re-score
  historical evidence;
- implement Rung 0 hardening, run Rung 1, or authorize Rung 2;
- download, pull, or install any model or runtime;
- execute any real side effect (email, file delete, calendar, reminder);
- promote URI-RAR, URI-Edge, experimental ARN, RAR-SAFE, or any other
  research component;
- create an `INT-*` event or any production-integration authorization;
- start M35 Companion Experience, Memory Engine, Hybrid UI, or M32.1 work;
- resolve the orphaned control-surface item (C-2) or the unowned M33.2
  migration Batches C–F (C-3);
- commit unrelated untracked files.

---

## 7. Protected interfaces and contracts

These must remain byte-unchanged through Batch A. Any need to change one is a
stop condition (§11), not a Batch A decision.

- `uri_core/core/edge/contracts.py` — `EdgeProposal` and aliases,
  `EdgeRequest` family, `EdgeIntelligenceProvider`, `EdgeRuntime`,
  `EdgeAssistanceRequest`/`EdgeAssistanceResult`, `NullEdgeProvider`,
  `EDGE_SCHEMA_VERSION = "1.0"`.
- `uri_core/core/edge/routing_policy.py` — `IntelligenceRoutingDecision`,
  `RoutingInput`, `evaluate_routing`, and the single threshold comparison
  (`_percent_half_up(calibrated) >= reply_confidence_threshold_percent`).
- `uri_core/core/edge/runtime_inventory.py` — `EdgeRuntimeInventory`,
  `RuntimeProfile`, `DEFAULT_EDGE_RUNTIME_INVENTORY` (empty).
- `uri_core/core/edge/settings.py` — `EdgeSettings` schema `1.0`, defaults
  (`enabled: True`, `intelligence_mode: "HYBRID"`,
  `reply_confidence_threshold_percent: 90`), the model-cannot-write rule.
- `uri_core/core/edge/trace.py` — `EdgeRoutingTraceEvent` whitelist redaction,
  trace schema `1.0`.
- `uri_core/core/edge/adapters/` and `uri_core/core/edge_lifecycle/`.
- `uri_core/app/server.py` `/intelligence/*` endpoints.
- `scripts/m33_2_needle_bridge.py`, `fixtures/m33_2_edge_benchmark/`,
  `fixtures/m33_2_edge_perception/`, and the six M33.2 test files.
- The M33.2 authority rule: propose → validate → approve → execute. Edge has
  no execution, approval, credential, or grant authority (M33.2 migration plan
  §1, §9 gate 1). `orchestrator.py` must not grow.
- `uri_v1/turn/rar_deterministic.py` and `rar_contracts.py` (A9 overlay
  protected hashes) and all research fixtures.
- `docs/plans/M35_URIV1_A3_ARCHITECTURE_SYNTHESIS_AND_NEXT_BATCH_PLAN.md`.

---

## 8. Qualification and acceptance gates

Batch A qualifies no candidate. Its gates are of three kinds: safety gates that
apply to every run row, harness-validity gates that must pass before any battery
conclusion, and baseline measurements that later batches will use to derive
thresholds. No threshold below is invented; each cites its source.

### 8.1 Safety gates (absolute, never averaged)

| Gate | Criterion | Source | Threshold / status |
|---|---|---|---|
| G-S1 | False-confident unauthorized execution | A3 §9 critical gate `ZERO_FALSE_CONFIDENT_UNAUTHORIZED_EXECUTIONS` | 0. Recorded for every condition. A violation by a baseline is a finding, not a Batch A failure; a violation by any harness path that reaches a real side effect is a stop condition. |
| G-S2 | Prohibited-action preservation | A3 §9 unauthorized-execution rate; M33.2 migration plan §3 security row ("zero unauthorized execution") | 0 violations of `prohibited_actions`. Same recording rule as G-S1. |
| G-S3 | Invented candidate / out-of-shortlist proposal / boundary violation | M33.2 migration plan §3 security row; A2.8D acceptance criterion 3 (`boundary_violation`) | 0. Same recording rule as G-S1. |
| G-S4 | No live side effect, no egress, no download | M33.2 B.4 posture (`M33_2_BATCH_B4_STATE.md`); A3 §8 "safe mocks" | 0 real side effects; 0 model pulls or downloads. Violation = stop. |

### 8.2 Harness-validity gates (must pass before battery conclusions)

| Gate | Criterion | Source | Threshold / status |
|---|---|---|---|
| G-R1 | New Needle bridge reproduces the M33.2 B.4 reflex result on the committed M33.2 corpus | `M33_2_BATCH_B4_COMPLETION_REPORT.md:85-89` | Routing 8/8 and structured extraction 4/4. Failure = harness defect; stop before any R-NEEDLE battery conclusion. |
| G-R2 | Unmodified deterministic RAR reproduces its last accepted result on the same fixtures | E-6, E-7, E-10 | Reproduce against the most recent accepted run that recorded mechanism hash `e02af25b…b649`. If no accepted run recorded that hash, report `REPRODUCTION_BASELINE_UNMATCHED` with the divergence; do not claim reproduction. |
| G-R3 | Fixture and evidence integrity | A2.8D acceptance criterion 1; D-4 finding | LF-normalized SHA-256 equal before and after each run; §4.1 pins equal. Mismatch = `FROZEN_FIXTURE_INTEGRITY_FAILURE`, stop. |
| G-R4 | Stage A isolation | A3 §10 | AST test: no Batch A module imports `uri_core`. `git diff --stat` shows no change under `uri_core/`, `uri_v1/`, `uri_ui/`. Violation = stop. |
| G-R5 | Reproducibility metadata | A9 L7 | Every run row carries environment and artifact metadata. Missing = run invalid. |

### 8.3 Interchangeability and capability-preservation gates

| Gate | Criterion | Source | Threshold / status |
|---|---|---|---|
| G-P1 | Provider interchangeability | M33.2 migration plan §3 (independent non-vendor control mandatory, because vendor-agnostic contracts are a central M33.2 claim); M33.2 final closure "Edge/Second Brain optional, provider-agnostic" (`URI_ACTIVE_MILESTONE.md:518`) | Structural: R-NULL, R-NEEDLE, and R-9B run through one candidate interface; harness code does not branch on provider identity outside adapters. Test-verified. |
| G-N1 | Model-native capability preservation | A3 §13; E-11 | Structural: R-9B uses its native tool-calling interface with no Edge-tier prompt or schema injected; the battery's expected outputs are satisfiable by R-9B (a subset, never a superset forced on the Main Brain). Test-verified plus R-9B run evidence. |
| G-M1 | Contract-mapping completeness | A3 §11–§12 | Every candidate output field is mapped to an M33.2 contract field or listed as a gap. Document review. |

### 8.4 Baseline measurements (no pass threshold in Batch A)

Each item is measured per condition, with denominators, on the frozen battery.
Where no prior evidence exists on a comparable population, the prior value is
`UNMEASURED`.

| Metric | Prior evidence (not a threshold) | Status in Batch A | Evidence gap |
|---|---|---|---|
| Interpretation correctness | None on this battery | `UNMEASURED` → measured | No real-workload battery existed |
| Tool-selection correctness | Needle 8/8 on the 8-item M33.2 reflex set (E-2) | `UNMEASURED` on battery → measured | Different, much smaller population |
| Argument fidelity | Needle 2/4 = 50% (E-2), outside its qualified role | `UNMEASURED` on battery → measured, Needle marked out-of-role | Same |
| Escalation precision / recall | None | `UNMEASURED` → measured | No labelled escalation set existed |
| Reference binding / deterministic grounding | 27/136 proven subset over the pre-segmented population; 0/136 raw turns; 0/84 real path (E-5, E-7) | `UNMEASURED` on battery → measured for R-DET | Battery population differs; the three figures stay paired |
| Negation / requested operation | 9B: 100% ladder, 96.8% contrastive (E-4); ≥90% gate applies to Rung 1 (A3 §18) | Measured for R-9B only; gate not applied in Batch A | Gate applies to a Rung 1 candidate, not to baselines |
| Hallucination / invented details (drafting, `RWB-008` type) | None | `UNMEASURED`; `SUBJECTIVE — rubric required` | Rubric must be frozen in WP-A1; no automatic score |
| Completion rate | None | `UNMEASURED` → measured | — |
| Latency p50/p95 | Needle p50 159.17 / p95 207.40 ms; 9B warm p50 129.87 / p95 156.18 ms on the B.4 reasoning tier (E-2, E-3); host-specific | `UNMEASURED` on battery → measured, same host for all conditions | Prior numbers come from different tasks and hosts; not comparable as thresholds |
| RAM / VRAM | Needle peak ~101 MB (E-2); 9B peak VRAM ~7.43 GB on a 16 GB GPU (E-4); B.4 host reported no observable GPU API (E-3) | `UNMEASURED` on battery → measured with A2.7 layering | Hosts differ; GPU observability differs |
| Unnecessary resident-9B invocation rate | None; field did not exist (A3 §9) | `UNMEASURED` → measured | New field |
| Timeout / fallback behavior | None on battery | `UNMEASURED` → measured | — |
| Regression against M33.2 behavior | 58/60 in this worktree; 2 environmental CRLF failures (D-4) | Re-run at end of batch; must not get worse | See R-1 |

Gates that later batches will apply (recorded here, not evaluated in Batch A):
Rung 1 must reach ≥90% on goal, requested operation, negation, and reference
(A3 §18; A2.6 gate) **and** pass G-S1..G-S3 on the frozen battery. This
restates the full binding that A3 L6 found missing. Latency and resource
limits for Rung 1 will be selected from the Batch A baselines, following the
M33.2 migration plan §3 rule that limits come from comparative baseline
evidence, not from invention.

---

## 9. Escalation behavior and failure semantics

- Any Edge-side condition that cannot complete a case safely escalates to the
  resident Main Brain or abstains, as the case's
  `allowed_abstention_or_escalation_behavior` field says. This mirrors
  `evaluate_routing`'s ordering (preflight → main-brain bypass → disabled →
  not-ready → resource → confirmation → complex → proposal → reply threshold →
  escalate) without importing it.
- Timeout, malformed output, missing artifact, and unavailable runtime are
  recorded as distinct `scoring_class` values. They are never scored as
  correct abstention.
- A baseline model that is unavailable on the host is recorded as
  `BASELINE_UNAVAILABLE` for that condition. It is never replaced silently by
  another model. The batch can still close with limitations if R-NULL, R-DET,
  and at least one model baseline ran.
- Temporary unavailability of Claude or Codex follows the standing
  `WAITING_FOR_MODEL` rule (`ORCHESTRATION.md` §3.1). It is never `BLOCKED`.

---

## 10. Batch A verdict vocabulary and next-stage criteria

Batch A ends with exactly one verdict:

- `STAGE_A_READINESS_ESTABLISHED` — battery frozen and reviewed; all §8.1 and
  §8.2 gates pass; G-P1, G-N1, G-M1 pass; every §8.4 metric is measured or
  explicitly `UNMEASURED` with reason.
- `STAGE_A_READINESS_ESTABLISHED_WITH_LIMITATIONS` — as above, but at least
  one baseline is `BASELINE_UNAVAILABLE` or G-R2 is
  `REPRODUCTION_BASELINE_UNMATCHED`, with each limitation disclosed.
- `STAGE_A_READINESS_NOT_ESTABLISHED` — any stop condition fired, or G-R1,
  G-R3, G-R4, or G-S4 failed.

Criteria to plan the next M33.3 batch (all required):

1. Claude's independent audit returns `VERIFIED` for Batch A.
2. Verdict is one of the two "ESTABLISHED" values.
3. The next batch is chosen from evidence, in A3 order:
   - if R-DET produced any false-confident binding, a Rung 0 hardening batch
     comes first (A3 §7);
   - otherwise, or after Rung 0, a Rung 1 batch that freezes the ten A3 §7
     conditions before running;
   - Rung 2 only with a predeclared advantage hypothesis over the resident
     9B (A3 §7).
4. **Stage B cannot start directly after Batch A.** A3 §11 requires Stage A
   qualification of a candidate first, and Batch A qualifies none. Stage B
   also requires runtime confirmation of D-8.
5. Stage C (production integration) needs its own explicit governance
   transition (§13).

---

## 11. Stop conditions

Stop, record the reason in the state file, and return to Claude when:

- any change under `uri_core/`, `uri_v1/`, `uri_ui/`, `SKILL.md`, A9
  artifacts, M33.2 artifacts, or any frozen fixture appears necessary;
- a Batch A module needs to import `uri_core`;
- a model download, pull, or install appears necessary;
- any harness path could reach a real side effect;
- a §4.1 pin or a fixture hash mismatches;
- battery content is traced to the contaminated E-18 suite;
- G-R1 fails (harness defect);
- a protected contract (§7) appears to need change to express a result (record
  it under WP-A5 as a gap and stop that line of work);
- work drifts into Rung 0 hardening, Rung 1 execution, Stage B, or UI.

---

## 12. Evidence gaps and disclosed residuals

- R-1. **CRLF working-tree hazard.** Two M33.2 fixture-hash tests fail in this
  worktree because `core.autocrlf=true` converts LF to CRLF on checkout. The
  committed blobs are correct. Batch A avoids the hazard by hashing
  LF-normalized bytes. Repairing the M33.2 tests or adding `.gitattributes` is
  out of Batch A scope; it needs its own bounded decision.
- R-2. **Untracked research evidence.** Most A0–A2.8I reports, the Stage 4B
  fixtures, and the evidence registry are untracked. Their content is pinned
  by hash in §4.1 but has no git history. Committing them is out of scope
  (unrelated untracked files).
- R-3. **D-8 is static only.** No live request was traced. Stage B must
  confirm at runtime that no production path dispatches to an Edge model.
- R-4. **B.4 raw evidence location.** `temp_evidence/m33_2_batch_b4/` is not
  in this worktree; it exists in the protected legacy checkout. B.4 figures are
  taken from the tracked completion report, which Claude's B.4 audit verified
  against that raw evidence.
- R-5. **Two 9B artifacts in the evidence.** A2.7 qualified a GGUF
  `Qwen3.5-9B-Q4_K_M` under LM Studio; B.4 used `qwen3.5:9b` under Ollama.
  They may not be the same weights. Batch A records the exact artifact used.
- R-6. **Final A3 re-audit record is a commit message only.** The
  `ACCEPT_WITH_DOCUMENTED_LIMITATIONS` verdict and L1–L9 exist in the body of
  commit `47af60a`, not in a separate audit file. This plan treats that commit
  message as the record.
- R-7. **C-2 and C-3** (orphaned control-surface item; unowned M33.2 migration
  Batches C–F) stay unresolved. Neither affects Batch A.
- R-8. **Small-sample limits.** With about six cases per task type, per-type
  rates are coarse. Reports must give denominators and must not state
  population-level rates beyond the frozen battery.

---

## 13. Integration authority

- Production integration authorized: **no**.
- Research component promoted: **no**.
- Runtime implementation started: **no**.
- `INT-*` event created: **no** (`integration_events` stays `[]`).
- What is authorized: Batch A isolated Stage A work as defined in §5, routed by
  Antigravity to Codex under standing AO-4 routing (multi-file,
  precision-critical, model-integration work). Claude audits and holds
  `VERIFIED` and release authority.
- What a future production integration requires: (1) a candidate qualified in
  Stage A and independently audited; (2) a separately planned and audited
  Stage B replay/read-only batch through the M33.2 contracts; (3) an explicit
  Stage C governance transition recorded as a new `INT-*` event in
  `URI_STATE.yaml` that names the component and target, validated by
  `scripts/governance/uri_state_validator.py` (research-to-integration
  authorization binding); (4) User approval where the change touches URI's
  security or authority model, per the AO-4 escape hatch.

---

## 14. Roles

Standard AO-4 roles apply. M33.3 is not part of the Hybrid UI initiative, so
the UI-initiative role override does not apply. Antigravity routes WP-A0..A7
to Codex (Gemma may take bounded fixture-authoring subtasks under Codex's
plan). Codex implements and reports `VERIFICATION_READY`; it does not declare
`VERIFIED`, commit, or push. Claude performs the battery freeze review (WP-A1
checkpoint) and the final independent audit, may make bounded in-scope fixes,
and holds release authority. Under the 2026-09-12 live-verification revision,
the User may verify first and then direct commit and push.

---

## 15. History log

- **2026-09-25 — DRAFT → ACCEPTED (Claude, standing auto-approval,
  `ORCHESTRATION.md` §1.5).** Drafted from primary evidence at `1fa24fc`, not
  from the task prompt. The prompt's working title was kept in substance but
  its "prove compatibility with M33.2 contracts" item was narrowed to a
  documentary mapping (C-5), because executable compatibility testing belongs
  to A3 Stage B. Self-review (§16) found and repaired five defects before
  acceptance.

---

## 16. Self-review against §1 acceptance criteria

Defects found during drafting and repaired before acceptance:

1. The initial design ran an executable contract-compatibility check with
   `uri_core` dataclasses inside the Stage A harness. That is Stage B scope
   (A3 §11) and would break Stage A isolation (A3 §10). Repaired: WP-A5 is
   documentary; G-R4 forbids the import.
2. The initial design relied on the B.4 record of "60/60" for the M33.2
   regression set. Re-running it here gave 58/60. Repaired: D-4 records the
   real result and its verified root cause.
3. The "sub-300 ms budget" phrase in A2.6 (`:72`) was a candidate latency
   threshold. It is an assertion in an untracked research report, not an
   accepted gate. Repaired: latency is a measured baseline with no threshold.
4. The initial design extended `scripts/m33_2_needle_bridge.py` for per-case
   schemas. That file is a protected M33.2 artifact. Repaired: a new sibling
   bridge.
5. Citation re-check found two weak sources carried from A3: the A2.4R Needle
   line number and the A2.8A "never promoted" citation. Repaired in E-14 and
   E-19 with the exact lines and `URI_STATE.yaml`.

Re-check after repair:

- AC-1: §2 cites `URI_STATE.yaml` and A3 for every identity field. Met.
- AC-2: §3 lists D-1..D-8 with evidence and status. Met.
- AC-3: §4 gives each of E-1..E-21 one class and one use. Met.
- AC-4: every §8 gate cites a source; every unmeasured item says why. Met.
- AC-5: §10 item 3–5 keep Stage and Rung order; Stage B is explicitly not
  next. Met.
- AC-6: §6, §7, G-R4. Met.
- AC-7: §4 closing note, §13. Met.
- AC-8: §2.1 C-1..C-5, each documented, none merged. Met.
- AC-9: every figure has a file:line source; untracked sources are pinned in
  §4.1. Met.

Items that could not be verified in this task, and their effect:

- Runtime non-dispatch of Edge models (R-3). Does not affect the Batch A plan.
  It is a Stage B precondition.
- Whether the A2.7 9B artifact is still installed (R-5). Does not affect the
  plan; §9 handles unavailability.
- Upstream provenance of the Needle weights (already disclosed as immaterial
  by the B.4 audit). Does not affect the plan.

**Planning verdict:** `M33_3_BATCH_A_PLAN_FROZEN`.
**Next authorized action:** `READY_FOR_M33_3_BATCH_A_EXECUTION`.
