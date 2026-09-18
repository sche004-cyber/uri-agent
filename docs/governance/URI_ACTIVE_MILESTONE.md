# URI Active Milestone Control

**Single Authoritative Record of the Current Approved Development Milestone**  
*This file records permissions, scope, and state that have already been approved by the User or accepted project governance. It does NOT grant new permissions by itself.*

---

## 1. Milestone Identity & State

**PRIOR MILESTONE (CLOSED):**  
M30-PFC — Provider-Failure False-Consent Repair — **CLOSED: ACCEPTED**
(User closure instruction, 2026-09-14). CLAUDE ACCEPT verdict, full
evidence trail in `docs/plans/M30_PROVIDER_FAILURE_FALSE_CONSENT_
STATE.md` "2026-09-14: Claude ACCEPT". No new regression found; one
pre-existing, disclosed architecture-debt item (orchestrator.py
newline-count guard, already failing before this repair) does not
block ACCEPT.

**PRIOR MILESTONE (CLOSED):**  
Scenario 2 Connection Gate Repair — **CLOSED: ACCEPTED** (User
approval + Claude implementation + Claude ACCEPT, 2026-09-14). See
`docs/plans/M30_SCENARIO2_CONNECTION_GATE_STATE.md`. Single-file
(`decision_gates.py`) bounded repair; live-reconfirmed real
`DISCONNECTED` + `capability_id: "Gmail"`; zero regression (6 new + 69
existing gate/engine tests passing).

**PRIOR MILESTONE (CLOSED):**  
M30.7C — Canonical Readiness Evidence Closure, RESUMED — **COMPLETE**
(User instruction, 2026-09-14). See `docs/plans/M30_7C_READINESS_
EVIDENCE_CLOSURE_REPORT.md`. M30 readiness ACCEPTED by the User; see
that report for the rebuilt 12-scenario matrix and regression result
(1,743 total items, 8 pre-existing failures, 0 new).

**PRIOR MILESTONE (CLOSED):**  
Architecture revision, PLANNING ONLY — **COMPLETE** (User instruction,
2026-09-14). Two plans produced and returned for review:
`docs/plans/M30_GRAPHIFY_FOUNDATION_PLAN.md` (Plan A) and
`docs/plans/M30_8_CANONICAL_CUTOVER_LEGACY_RETIREMENT_PLAN.md` (Plan
B, supersedes `M30_8_CANONICAL_DEFAULT_CUTOVER_PRE_AUDIT.md` and the
original migration plan's separate M30.8/M30.9/M30.10 rows).

**PRIOR MILESTONE (CLOSED):**  
Graphify Foundation (Plan A) — **CLOSED: ACCEPTED** (User approval +
implementation + verification + Claude ACCEPT, 2026-09-14). See
`docs/plans/M30_GRAPHIFY_FOUNDATION_STATE.md`.

**PRIOR MILESTONE (CLOSED):**  
M30.8 — Canonical Cutover + Legacy Retirement — **CLOSED: COMPLETE — CLAUDE ACCEPT**
(User authorized 2026-09-14; Claude independent audit, bounded repair, Phase A live observation battery, and final ACCEPT recorded in `docs/plans/M30_8_CLAUDE_AUDIT.md` and `docs/plans/M30_8_PHASE_A_OBSERVATION_AND_PHASE_B_DISPOSITION.md`). Full regression 1,759 passed, 16 failed (exact standing baseline + Ollama environment change), 0 new.

**PRIOR MILESTONE (CLOSED):**  
URI Approved UI Functional Prototype — **CLOSED: ACCEPTED**  
(User authorization 2026-09-14; all 4 batches completed, independently audited by Claude, live-verified against running app and approved reference: Batch 1 fixed board framing/13-item nav/unread Gmail; Batch 2 card geometry/honest charts/right-rail fit; Batch 3 responsive scaling/theme propagation/local switching/continuous chat; Batch 4 typography unification/link button contrast repair). Delivered with clean analysis and 23/23 passing tests. Prototype code preserved in working tree.

**PRIOR MILESTONE (CLOSED):**  
M31 — Model & Brain UX — **CLOSED: CLAUDE VERIFIED — COMPLETE**
(Claude independent final audit, 2026-09-16). All 8 live-acceptance
defects and the 3 Round 2 pre-final findings confirmed genuinely fixed
at the source level; 4 additional defects found during this audit and
bounded-fixed in-session (Flutter attachment-chip `Chip`/`RawChip`
collision, stale route-count guard, an LM Studio Active-Brain
regression, and a shared `ModelRouter` test-double signature drift
plus one unguarded best-effort call). Full evidence, all fixes, and
regression results in `docs/plans/M31_STATE.md` ("Claude Final Audit
(2026-09-16) — VERIFIED"). Full `pytest`: 1798 passed, 10 failed (all
10 independently confirmed pre-existing via clean-`HEAD` comparison,
0 new). Full `flutter test`: 135/135. Committed and pushed to
`origin/master` per Claude's standing release authority.

**PRIOR MILESTONE (CLOSED):**  
M32 — Brain Latency / Core Execution Architecture — **CLOSED: CLAUDE
VERIFIED — COMPLETE** (User closure instruction, 2026-09-18: "Final
M32 closure approved"). Batches A–C (canonical cutover, fast/native
tiered path) plus D1–D6 (OAuth refresh persistence, single shared
`CapabilityDirectory` per turn, default-model-resolution correctness
fix, bounded context-probe skip + parallel-tool-worker cap, streaming
`POST /ask/stream`, and a committed/reproducible benchmark harness).
Two headline latency findings (redundant `CapabilityDirectory`
construction; un-persisted OAuth refresh) fixed and re-confirmed fresh
with a 10-iteration real-model measurement; one correctness defect
(default-model resolution) fixed with dedicated regression (58
`test_model_router_*` tests); two resource-exhaustion risks (unbounded
parallel-tool-dispatch threads; unbounded streaming connections) now
bounded and deployment-configurable. Zero regression: 561 passed / 5
failed (all 5 independently confirmed pre-existing, environment-only —
`qwen3:14b` not installed on the dev machine — via clean-HEAD
comparison, 0 new) across the full focused sweep, re-confirmed in this
same closure session. Full evidence, before/after metrics, the final
deferred/residual register, and the milestone-number reconciliation
record are in `docs/plans/M32_POST_BATCH_C_LATENCY_ARCHITECTURE_
PLAN.md` §10–§15 (§15.10 for the register, §15.11 for the
reconciliation, §15.12 for the CLOSE recommendation this closure
adopts). **Two items explicitly carried forward, NOT resolved by this
closure** — see "M32 residual items, carried forward" below.

**CURRENT MILESTONE:**  
None active — M32 is CLOSED (M31 was closed earlier, 2026-09-16; see
the M31 entry above). Per §1a, the Hybrid UI initiative's own
hard-dependency gate was already opened by M31's own earlier closure,
independently of M32 — see that section for the initiative's own
separate role set and status before any implementation work begins on
it. M32's closure does not itself open or affect that gate.

**M32 residual items, carried forward (NOT resolved by this closure):**
1. **Resumed approval across turns** (durable cross-turn pending-
   approval state + natural-language resumption recognition) —
   real, live-demonstrated (Batch B), confirmed still untouched through
   Batch C and D1–D6 (re-checked directly against source in this
   closure session, not merely re-quoted from earlier reports). A
   genuine functional/product gap, out of scope for a latency work
   stream, requiring its own design/implementation.
2. **Attachment-turn Brain tool-selection reliability** (chose `Gmail`
   over `read_attached_file`) — a model/prompt-reliability finding
   (Batch B), explicitly not independently re-tested since (Batch C's
   own disclosure), out of scope for D1–D6.

Neither item may be treated as resolved, implicitly or explicitly, by
this milestone's CLOSED status. Full detail: `docs/plans/M32_POST_
BATCH_C_LATENCY_ARCHITECTURE_PLAN.md` §15.9–§15.10.

**CURRENT STATE:**  
Awaiting the next milestone. No implementation authorized yet on any
surface until a fresh milestone (or the already-frozen Hybrid UI
initiative) is explicitly started per standing governance. **M33 —
External Capability Bridge is explicitly NOT started** (roadmap-
reconciled into this number per the User's 2026-09-18 instruction; see
"Roadmap Reservation" below and §1b) — do not begin it without a
separate, explicit User instruction.

**LOOP_STATE:**  
IDLE (M32 COMPLETE — awaiting next milestone initiation; M33 not started)

**M31 OBJECTIVE (achieved, preserved for reference):**  
Implement M31 Model & Brain UX per approved Figma frames 02 (node 1:71 — Connect Provider) and 04 (node 1:201 — Chat Model Selector) — API-key + local provider functionality, dynamic model discovery, verified-model inventory, `/providers/{id}/verify`, fallback routing, conversation-level model override, and the two Flutter screens. All items delivered and independently verified per `docs/plans/M31_STATE.md`. `orchestrator.py`-must-never-grow and `/ask`-unchanged-when-override-omitted regression guards both hold (confirmed by this audit's own full regression, not merely re-asserted).

**M31 Critical Invariants (held, now closed with the milestone):**
- Direct-Model Brain Separation: confirmed — zero `subprocess`/`Popen` references to `claude`/`codex` anywhere in `uri_core`.
- Subscription Transport Seam: `subscription_oauth` remains schema-only on `ProviderDescriptor.auth_transports`; Subscription card shows the honest, sourced unavailable state. Unchanged, not implemented in M31 (by design).
- Roadmap Reservation: direct subscription-backed Brain access remains a deferred requirement; M32 stays reserved for external-skill qualification/integration. **[Superseded, 2026-09-18 — preserved verbatim above as the historical M31-era record, not silently edited: M32 was subsequently assigned to Brain Latency / Core Execution Architecture (see the PRIOR MILESTONE entry above) and is now CLOSED. The external-skill-qualification/integration reservation this bullet originally named has been roadmap-reconciled to M33 — see §1b below.]**

**M32 Critical Invariants (held, now closed with the milestone):**
- `run_native_tool_loop()` (`uri_core/core/native_tool_loop.py`) — the central Tier-0/Tier-1 fast-path function this entire work stream builds around — remained completely unmodified throughout D1–D6, confirmed by `git diff --stat` before every commit; every extension (streaming, worker cap) went through its own existing seams (the injectable `model_callable` parameter) rather than editing it.
- No silent model substitution: default-model-resolution failures (D3) fail clearly and never silently pick a different, arbitrary installed model.
- Approvals/grants/audit/dispatch: unweakened throughout, confirmed by full regression after every batch and by the streaming work (D5) specifically proving a late tool call correctly aborts provisional prose and continues through the real, unmodified gate chain (verified against the real `ApprovalGate`/`ToolDispatcher`/`MultiActionDispatch` fixture, not a mock).
- Provider/model-agnostic architecture preserved throughout (D3's default-model fallback logic, D5's `complete_stream()` default fallback for unupgraded providers).
- Roadmap Reservation (current, supersedes the M31-era bullet above): **M33 is reserved for external-skill qualification/integration** — see §1b.

---

## 1a. Queued Initiative (not milestone-numbered): URI Hybrid UI Implementation

**Status:** FROZEN BLUEPRINT (2026-09-16) — planning/review complete;
implementation **not yet started**. See
`docs/plans/UI_HYBRID_FROZEN_BLUEPRINT.md` (the frozen implementation
blueprint) and `docs/plans/UI_OVERHAUL_IMPLEMENTATION_PLAN.md` /
`docs/design_library/UI_DESIGN_AUTHORITY.md` / `docs/design_library/
COMPONENT_MAPPING.md` / `docs/design_library/UI_ACCEPTANCE_CHECKLIST.md`
(inputs the blueprint incorporates and corrects).

**Roles for this initiative (2026-09-16 explicit User instruction, overrides
the CURRENT MILESTONE (M31) role table in §3 for this initiative only):**
Claude/Codex — planning and independent plan review only; Antigravity —
primary implementer; Qwen 3 14B (local) — implementation review; Antigravity
— repair of Qwen's findings. See `ORCHESTRATION.md` §0 and `AGENTS.md` item 7.

**Mandatory sequencing — hard dependency on M31: GATE OPEN (2026-09-16).**
M31 — Model & Brain UX (§1 above) reached Claude `VERIFIED` and was
committed/pushed to `origin/master` in this same audit pass — see
`docs/plans/M31_STATE.md` ("Claude Final Audit (2026-09-16) — VERIFIED")
for the full evidence trail. The hard dependency that previously blocked
this initiative is satisfied: Antigravity may now initiate UI-initiative
Batch 1 under the role set below. This gate note is preserved for its
own auditable history — the dependency it recorded is resolved, not
retroactively deleted.

**Authorization basis for this queued-initiative record:** direct User
instruction in a live session with Claude, 2026-09-16 ("Accept
READY_WITH_CHANGES... Proceed directly to incorporate your findings and
produce the Frozen UI Implementation Blueprint... Current User-confirmed
development roles are: ..."). This records the frozen blueprint and role
set; it does not advance M31's own state, and it does not authorize UI
implementation to start ahead of the M31 dependency above.

---

## 1b. Roadmap Reservation: M33 — External Capability Bridge (renumbered from M32, 2026-09-18)

**Decision:** on M32 (Brain Latency / Core Execution Architecture)'s
closure, the User directly instructed: "Keep M32 = Brain Latency /
Core Execution Architecture. Renumber the unimplemented External
Capability Bridge to M33. Update governance/planning references
consistently." This section records that decision as the current,
authoritative roadmap-numbering state.

**Why this was the cleaner direction (Claude's recommendation, adopted
by the User):** External Capability Bridge has produced planning
documents only and was never authorized to implement — its own state
file, `docs/plans/M32_STATE.md`, records "Implementation: NOT
AUTHORIZED; NOT STARTED." M32 (Brain Latency), by contrast, closes
with substantial shipped, tested, committed work across six D-batches.
Renumbering unimplemented planning work is lower-cost and lower-risk
than renaming a completed work stream's own history.

**A prior session had already partially converged on this same
number, independently.** `docs/plans/M33_EXTERNAL_CAPABILITY_BRIDGE_
BLUEPRINT.md` (dated 2026-09-17, status: FROZEN — planning finality,
implementation NOT AUTHORIZED/NOT STARTED) already exists and already
explicitly supersedes the earlier M32-numbered External Capability
Bridge drafts (`M32_EXTERNAL_CAPABILITY_BRIDGE_PLAN.md`, `../
architecture/EXTERNAL_CAPABILITY_CONTRACT.md`, `../architecture/
M32_CANONICAL_ARCHITECTURE.md`, `../research/M32_ROOT_CAUSE_AUDIT.md`,
`M32_MIGRATION_PLAN.md` — "all Codex drafts, 2026-09-15"). That
blueprint's own §10 states plainly: "Those files remain in place" —
i.e. the established convention in this repository is to supersede a
superseded planning document in place, recording the correction,
never to rename or delete it. This governance update follows that
same convention: **no `docs/plans/M32_*` External Capability Bridge
file has been renamed or deleted.** They remain exactly where they
are, as historical/superseded drafts, exactly as the M33 blueprint
itself already established one day before this reconciliation. This
governance file is simply the first place to formally record that the
number these drafts describe is now M33, matching the already-frozen
blueprint, not a new decision invented here.

**Current authoritative state:**
- **M32 = Brain Latency / Core Execution Architecture — CLOSED.** See the PRIOR MILESTONE entry in §1.
- **M33 = External Capability Bridge — NOT STARTED.** Authoritative planning document: `docs/plans/M33_EXTERNAL_CAPABILITY_BRIDGE_BLUEPRINT.md` (frozen 2026-09-17; implementation not authorized). Earlier `M32_EXTERNAL_CAPABILITY_BRIDGE_PLAN.md`/`M32_STATE.md`/`M32_CANONICAL_ARCHITECTURE.md`/`M32_ROOT_CAUSE_AUDIT.md`/`M32_MIGRATION_PLAN.md` remain in place as superseded historical drafts, per that blueprint's own §10 and this repository's standing auditable-correction-history convention — not renamed, not deleted.
- **Do NOT begin M33 implementation** without a separate, explicit User instruction — explicitly not authorized by this reconciliation record.

---

## 2. Authoritative Files
- `docs/plans/M31_MODEL_BRAIN_UX_PLAN.md`
- `docs/plans/M31_STATE.md`
- `docs/governance/URI_AGENT_RELAY.md`
- `docs/governance/URI_ACTIVE_MILESTONE.md`
- Figma nodes: `1:71` (02 — Connect Provider) and `1:201` (04 — Chat Model Selector)

---

## 3. Authorized Agent Roles (M31 — CLOSED, preserved for reference)

- **Claude:**  
  Visual and architectural authority, plan author, and final architectural auditor / release authority.
- **Antigravity:**  
  Development loop manager / orchestrator, task relay, evidence collection, visual/UX compliance audit against Figma 1:71 and 1:201, and milestone-state maintenance. (Does not edit production code or perform final audit).
- **Codex:**  
  Primary implementer (Codex only) for backend contracts and Flutter UI implementation per accepted M31 plan.
- **User:**  
  Final authority. M31 approval granted, implemented, and Claude-verified/released — see §1.

This role table stood for M31 specifically. §1a's own role table (Claude/Codex planning-and-review only, Antigravity primary implementer, Qwen implementation reviewer) governs the now-open Hybrid UI initiative instead; it does not reuse this table.

---

**WRITE SCOPE (M31 — CLOSED, preserved for reference, no longer an active grant):**  
- `uri_ui/` — Flutter UI files (providers screen, ask_uri screen, composer, models, state, widgets, tests).
- `uri_core/` — backend contracts for M31 (`core/model_router.py`, `core/provider_registry.py`, `app/server.py` for `/providers`, `/providers/{id}/verify`, `/providers/fallback-routing`, `AskRequest.model_override`, `core/fallback_routing_store.py`, `core/turn_state.py`, `core/conversation_history.py`) — strictly respecting that `orchestrator.py` must never grow.
- `tests/` — backend pytest suites for M31.
- `docs/plans/M31_*` — state, reports, verification files.
- `docs/governance/URI_ACTIVE_MILESTONE.md`, `docs/governance/URI_AGENT_RELAY.md`, `PROJECT_MEMORY.md`.
- `uri_workspace/dev_workflow/tasks/` — task directives for Codex and Claude.
- `scripts/run_codex_m31.py` — execution runner script.

No milestone write scope is currently active. The next milestone (or the Hybrid UI initiative, per its own §1a scope) must define its own before implementation starts.

---

## 5. Stop Conditions & Invariants (M31 — CLOSED; invariants below remain standing project-wide, not milestone-scoped)
 
- URI Brain providers are direct-model providers only. Claude Code, Codex, Antigravity, or other development harnesses must NEVER be introduced into the URI Brain runtime. (Confirmed holding by this audit — zero `subprocess`/`Popen` references to `claude`/`codex` anywhere in `uri_core`.)
- `subscription_oauth` is an architectural schema-ready seam on `ProviderDescriptor.auth_transports` only; it remains unimplemented. The Subscription card in Design 02 shows an honest, sourced unavailable state.
- M33 is reserved for external-skill qualification/integration (see §1b — roadmap-reconciled from M32, 2026-09-18; M32 is now used and CLOSED for Brain Latency / Core Execution Architecture, see §1). Direct subscription-backed Brain access is recorded as a deferred requirement for later roadmap reconciliation.
- Only discovered AND verified-usable models are ever selectable anywhere in the product.
- Composer model selector is the single interactive model selector in the product.
- `orchestrator.py` must never grow; keep routing logic in `model_router.py`. (Note: `orchestrator.py` is already at 6153 lines, past the `test_usage_import_boundary.py` guard's 5460 threshold, as of commit `8fa9ac6` — pre-existing, standing architecture debt confirmed to pre-date M31, not a new violation; see `docs/plans/M31_STATE.md`'s final audit section.)
- Preserve existing working code and tests; no regression in existing provider routing or `/ask` calls.
- Do NOT commit or push without separate explicit User instruction.

---

## 6. Next Milestone Status

**NEXT MILESTONE:**  
Roadmap reconciliation is now RESOLVED (see §1b, 2026-09-18): M33 is reserved in the roadmap for external-skill qualification/integration (`docs/plans/M33_EXTERNAL_CAPABILITY_BRIDGE_BLUEPRINT.md`, frozen 2026-09-17); direct subscription-backed Brain access remains a separately deferred requirement, still unassigned to any milestone number.

**NEXT MILESTONE STATUS:**  
NOT AUTHORIZED — M33 implementation has not been started and requires a separate, explicit User instruction to begin (per direct User instruction, 2026-09-18: "Do not begin M33 yet").

---

## 6f. Closure Record (M32 — Claude VERIFIED, released)

```markdown
VERDICT: VERIFIED
VERDICT AUTHORITY: CLAUDE (independent final audit, per standing AO-4 release authority)
MILESTONE: M32 — Brain Latency / Core Execution Architecture
BASIS: Batches A-C (canonical cutover, fast/native tiered execution
  path) plus D1-D6 (OAuth refresh persistence, single shared
  CapabilityDirectory per turn, default-model-resolution correctness
  fix, bounded parallel-tool-worker cap + context-probe skip,
  streaming POST /ask/stream, committed/reproducible benchmark
  harness). Every acceptance criterion each batch/D-item defined for
  itself is implemented, tested, and independently re-verified. Two
  headline latency findings (redundant CapabilityDirectory
  construction; un-persisted OAuth refresh) fixed and re-confirmed
  fresh with a 10-iteration real-model measurement in this closure
  session, not merely re-cited from earlier batches. One correctness
  defect (default-model resolution) fixed with dedicated regression
  (58 test_model_router_* tests). Two resource-exhaustion risks
  (unbounded parallel-tool-dispatch threads; unbounded streaming
  connections) bounded and deployment-configurable. Streaming
  implemented and real-verified end to end against a live model,
  including a genuine tool-call turn through the completely
  unmodified gate/dispatch chain (native_tool_loop.py has zero diff
  across all of D1-D6, confirmed via git diff --stat before every
  commit). A measurement-confidence question raised after the first
  D6 benchmark pass (multi-tool scenario variance) was independently
  re-investigated in this same closure session and traced to a
  scenario-wording mismatch against the original D1+D2 baseline
  prompt, not a code regression - corrected, and the committed harness
  fixed so it cannot silently drift again. Full regression: 561
  passed / 5 failed (all 5 independently confirmed pre-existing,
  environment-only - qwen3:14b not installed on the dev machine - via
  clean-HEAD comparison, 0 new), re-confirmed fresh in this closure
  session, not merely re-asserted from an earlier batch. Full evidence
  in docs/plans/M32_POST_BATCH_C_LATENCY_ARCHITECTURE_PLAN.md
  §10-§15.
RESIDUAL, EXPLICITLY NOT CLAIMED AS RESOLVED: (1) resumed approval
  across turns (durable cross-turn pending-approval state) - real,
  live-demonstrated in Batch B, confirmed still untouched through
  Batch C and D1-D6 by direct re-inspection of source in this closure
  session; (2) attachment-turn Brain tool-selection reliability -
  disclosed in Batch B, not independently re-tested since. Both carried
  forward per direct User instruction ("Do not claim resumed approval
  or attachment-turn tool selection as resolved") - see the residual
  register in docs/plans/M32_POST_BATCH_C_LATENCY_ARCHITECTURE_PLAN.md
  §15.10 and the PRIOR MILESTONE entry in §1 above.
RELEASE ACTION: Claude performed the release commit/push to
  origin/master per standing release authority, on direct User
  instruction this session ("Final M32 closure approved... commit D6 +
  final M32 closure + approved milestone-number reconciliation...
  push to master").
TIMESTAMP: 2026-09-18
```

---

## 6e. Approval Record (M32 Authorization)

```markdown
USER APPROVAL: APPROVED
APPROVAL RELAY: USER DIRECT
APPROVED MILESTONE: M32 — Brain Latency / Core Execution Architecture
APPROVAL BASIS: Explicit User instruction, delivered incrementally
  across D1-D6 and confirmed at final closure: "Final M32 closure
  approved. Roadmap decision: Keep M32 = Brain Latency / Core
  Execution Architecture. Renumber the unimplemented External
  Capability Bridge to M33. Update governance/planning references
  consistently. Preserve the final deferred/residual register exactly
  as reported. Do not claim resumed approval or attachment-turn tool
  selection as resolved." Each individual batch (D1+D2, D3, D4, D5,
  D6) was separately User-verified and separately authorized to
  commit/push before this final closure instruction; see the
  individual commit messages (a6fe87c, 5d76a40, f9cfc92, and this
  closure's own commit) for each batch's own citation of its specific
  authorization.
APPROVAL TIMESTAMP: 2026-09-18
```

---

## 6d. Closure Record (M31 — Claude VERIFIED, released)

```markdown
VERDICT: VERIFIED
VERDICT AUTHORITY: CLAUDE (independent final audit, per standing AO-4 release authority)
MILESTONE: M31 — Model & Brain UX
BASIS: All 8 originally-reported live-acceptance defects and the 3 Round 2
  pre-final findings independently confirmed fixed at the source level
  (not merely re-quoted from Codex/Antigravity's evidence trail). 4
  additional defects found during this audit, all bounded-fixed and
  re-verified in-session (see docs/plans/M31_STATE.md "Claude Final
  Audit (2026-09-16) — VERIFIED" for full detail). Full regression:
  pytest 1798 passed / 10 failed (all 10 confirmed pre-existing via
  clean-HEAD comparison, 0 new); flutter test 135/135; flutter analyze
  0 errors.
RELEASE ACTION: Claude performed the release commit/push to
  origin/master per standing release authority, on direct User
  instruction this session ("If VERIFIED, perform the authorized M31
  release checkpoint... commit/push M31").
TIMESTAMP: 2026-09-16
```

---

## 6c. Approval Record (M31 Authorization)

```markdown
USER APPROVAL: APPROVED
APPROVAL RELAY: USER DIRECT
APPROVED MILESTONE: M31 — Model & Brain UX
APPROVAL BASIS: Explicit User instruction: "M31 — Model & Brain UX is ACCEPTED and ready for execution. Please take ownership of URI_ACTIVE_MILESTONE.md as required by AO-4, set M31 as the active milestone, and initiate the established execution loop. Route implementation to Codex only."
APPROVAL TIMESTAMP: 2026-09-15
```

---

## 5a. Approval Record (M30-PFC Authorization)

```markdown
USER APPROVAL: APPROVED
APPROVAL RELAY: CLAUDE
APPROVED MILESTONE: M30-PFC
APPROVAL BASIS: Explicit User instruction: "I approve implementation of
  the finalized M30_PROVIDER_FAILURE_FALSE_CONSENT_REPAIR_PLAN.
  Proceed with the bounded repair exactly as planned... M30.8 remains
  NOT AUTHORIZED until this repair receives Claude ACCEPT."
APPROVAL TIMESTAMP: 2026-09-13
```

Authorizes exactly the scope in `docs/plans/M30_PROVIDER_FAILURE_
FALSE_CONSENT_REPAIR_PLAN.md` and §4/§5 above - the primary
model-failure-state gate, the empty-match defense-in-depth, the 8
required tests, live re-verification, and full regression. Does not
authorize M30.8, does not authorize any redesign beyond this exact
gate, and does not authorize commit/push.

---

## 6a. Approval Record (M30.7C Authorization)

```markdown
USER APPROVAL: APPROVED
APPROVAL RELAY: CLAUDE
APPROVED MILESTONE: M30.7C
APPROVAL BASIS: Explicit User instruction: "I approve a bounded M30.8
  readiness evidence-closure pass. Scope is limited to: MANDATORY -
  Scenario 2 ... Scenario 8 ... Scenario 12 ...; BEST EFFORT -
  Scenario 7 ...; DO NOT REOPEN - Scenario 5, 9, 4. No production
  source changes are authorized unless an unexpected real defect is
  discovered. If a defect is discovered, stop and return for scope
  approval rather than repairing it automatically."
APPROVAL TIMESTAMP: 2026-09-13
```

This approves exactly the scope in
`docs/plans/M30_7C_READINESS_EVIDENCE_CLOSURE_PLAN.md` - it does
**not** authorize M30.8, does not authorize any source change absent a
real discovered defect (and even then, only after a further, separate
approval), and does not authorize commit/push. Scenarios 4, 5, and 9
are explicitly excluded from this milestone and must not be reopened.

---

**BLOCKERS / PREREQUISITES BEFORE M30.8 CAN BE AUTHORIZED:**
1. Scenarios 2, 5, 7, 8, 12 still lack full live canonical closure:
   - Scenario 2 never reaches real `DISCONNECTED` gate outcome.
   - Scenario 5 model performs a one-time search instead of an honest refusal for recurring automation.
   - Scenario 7 lacks a real attachment-bearing email to complete the chain.
   - Scenario 8 pre-approval draft-content envelope is unobserved (approval boundary itself is proven).
   - Scenario 12 visible end-user provider-unavailable fallback message is unconfirmed.
2. Scenario 9 (`convert_document`) is confirmed `BLOCKED_BY_CURRENT_SCOPE` (not Layer-3 schema/executor-ready).
3. M30.2 `WorkflowPlanner` template inventory is confirmed absent across repository artifacts.


---

## 6b. Approval Record (M30.7B Authorization)

```markdown
USER APPROVAL: APPROVED
APPROVAL RELAY: CLAUDE
APPROVED MILESTONE: M30.7B
APPROVAL BASIS: Explicit User instruction: "I approve M30.7B — Canonical
  Readiness Closure. Record my approval in
  docs/governance/URI_ACTIVE_MILESTONE.md and initiate the loop."
APPROVAL TIMESTAMP: 2026-09-13
```

This approval authorizes M30.7B exactly as scoped in
`docs/plans/M30_7B_CANONICAL_READINESS_CLOSURE_PLAN.md` - root-cause-
first investigation of 6 named scenarios, one decision (scenario 9),
and at most the two conditional source changes named in §4. It does
**not** authorize M30.8, does not authorize any source change beyond
those two conditional boundaries, and does not authorize commit/push.
The User explicitly directed: "Keep M30.8 NOT AUTHORIZED. Do not
expand beyond the two conditional source-change boundaries already
defined in the M30.7B plan" - both instructions are binding invariants
for this milestone, not merely defaults.

---

## 6a. Prior Approval Record (M30.7A Authorization)

```markdown
USER APPROVAL: APPROVED
APPROVAL RELAY: USER DIRECT
APPROVED MILESTONE: M30.7A
APPROVAL BASIS: Explicit User request: "Create a bounded milestone: M30.7A — CANONICAL LIVE EVIDENCE CLOSURE ... to claude"
APPROVAL TIMESTAMP: 2026-09-13
```

M30.7 was closed (`LIVE_VERIFIED + CLAUDE ACCEPT (documented residual)`). M30.7A was explicitly authorized by the User to close the missing live evidence for all 12 mandatory canonical scenarios before M30.8 can be considered. State transitioned to M30.7A (`PLANNING`).

Note: this approval authorizes starting M30.7A. It does NOT authorize starting M30.8 or committing/pushing.

### Confirmation (2026-09-13, given directly to Claude)

Claude's own M30.7A plan (`docs/plans/M30_7A_CANONICAL_LIVE_EVIDENCE_PLAN.md`)
had flagged the relay-channel deviation above for the User's awareness,
not silently accepted it. The User has since directly confirmed it:

```markdown
APPROVAL AUTHORITY: USER
APPROVAL RELAY: USER DIRECT
APPROVED MILESTONE: M30.7A
PROTOCOL NOTE: This was a one-off direct approval given by the User
  outside the normal Claude-relay channel. It does not change the
  standing protocol.
CONFIRMATION TIMESTAMP: 2026-09-13
```

**Standing protocol, restated and unchanged by this confirmation:**
User approvals for future milestone advancement should normally be
communicated through Claude (per §7's User Approval Channel Protocol)
and then recorded into this shared governance file. This M30.7A
approval is a User-confirmed, valid, one-off exception - it is not a
revision to that standing protocol, does not establish "direct to
Antigravity" as an alternate channel going forward, and does not block
or invalidate M30.7A, which remains authorized and in progress
(Antigravity → Codex → evidence → Claude audit).

---

## 7. Governance & Maintenance Rules

### Update Rule
Antigravity must update this file whenever:
- A milestone is approved.
- A milestone enters `IMPLEMENTING`.
- A milestone becomes `VERIFICATION_READY`.
- Claude returns `ACCEPT` / `ACCEPT WITH FOLLOW-UP` / `REPAIR REQUIRED` / `HOLD`.
- The User marks a milestone `LIVE_VERIFIED`.
- The User authorizes the next milestone.

The file must always reflect the latest accepted project state.

### Do Not Self-Authorize
Antigravity must **NOT** change `NEXT MILESTONE STATUS: NOT AUTHORIZED` to an authorized state unless there is explicit User approval or an already-approved governing instruction that clearly authorizes that exact transition. The file records authorization; it never creates it.

### Milestone Handoff Rule
When one milestone completes and another is approved:
1. Archive the completed state in existing milestone/state/report files.
2. Update `URI_ACTIVE_MILESTONE.md`.
3. Change `CURRENT MILESTONE`.
4. Change `CURRENT STATE`.
5. Update authoritative files.
6. Update current write scope.
7. Update stop conditions.
8. Update `NEXT MILESTONE`.
9. Preserve the User as final approval authority.

### Shared Active-Milestone Invariant
`docs/governance/URI_ACTIVE_MILESTONE.md` is the **SINGLE** canonical current-state file for URI development coordination.
Claude, Codex, and Antigravity must all read this exact file before starting milestone work.
There must NOT be:
- Separate Claude milestone files.
- Separate Codex active-state files.
- Duplicated copies of `URI_ACTIVE_MILESTONE.md`.
- Agent-local milestone state treated as authoritative.

**Write Ownership:**
- **Antigravity** is the coordinator and primary writer of `URI_ACTIVE_MILESTONE.md`.
- **Claude** reads the file, audits/plans, returns verdict/evidence, and does not independently advance milestone state.
- **Codex** reads the file, implements/verifies, returns status/reports, and does not independently authorize or advance the next milestone.
- **User** remains the non-delegable final authority for next-milestone authorization.

### Autonomous Loop Execution Invariant
For the CURRENT milestone, Antigravity executes the loop automatically:
`Codex completion → Antigravity collects evidence → Claude audits → [if repair required: route to Codex → collect evidence → Claude re-audits] → update URI_ACTIVE_MILESTONE.md after each transition`

Continue until the current milestone reaches:
`LIVE_VERIFIED + CLAUDE ACCEPT`

**HARD STOP:** Do NOT start the NEXT milestone unless `docs/governance/URI_ACTIVE_MILESTONE.md` explicitly records that the User has authorized it.

### User Approval Channel Protocol (Claude Relay)
The User remains the non-delegable final authority for milestone advancement. During this development period, the User communicates approvals **ONLY through Claude**.

- **No Direct Wait in Antigravity:** Antigravity must NOT pause or wait for a direct User message inside the Antigravity chat session.
- **Claude is the Authorized Approval Relay:** Claude receives the User's explicit decision and records or relays it for Antigravity to record in `URI_ACTIVE_MILESTONE.md`.
- **Relay, Not Authority:** Claude may NOT approve a milestone on the User's behalf, infer approval from silence, or convert its own audit recommendation into User approval. It records User approval *only* when the User has explicitly granted it to Claude.
- **Canonical Approval Record Format:**
  ```markdown
  USER APPROVAL: APPROVED
  APPROVAL RELAY: CLAUDE
  APPROVED MILESTONE: <exact milestone>
  APPROVAL BASIS: Explicit User approval communicated through Claude
  APPROVAL TIMESTAMP: <timestamp>
  ```
  When this record appears in `URI_ACTIVE_MILESTONE.md`, Antigravity treats the named milestone as User-authorized and advances `CURRENT MILESTONE` automatically.

### Automatic Milestone Loop Resumption Rule
When a new milestone has been explicitly approved by the User through Claude and that approval is recorded in `docs/governance/URI_ACTIVE_MILESTONE.md`:
- **CONTINUE WITH THE LOOP AUTOMATICALLY.** Do not stop merely because the approval was relayed through Claude rather than given directly in Antigravity.
- Resume execution immediately from the newly authorized milestone:
  `Claude-approved plan → Antigravity coordination → Codex implementation → Antigravity evidence collection → Claude audit → [bounded repair if required] → Claude re-audit → live verification → update URI_ACTIVE_MILESTONE.md`
- Continue autonomously until that newly authorized milestone reaches its own hard stop or requires another NEW milestone approval.

### Routine Execution Authorization & Permission Prompt Rule
Once a milestone is explicitly authorized in `docs/governance/URI_ACTIVE_MILESTONE.md`, Antigravity is authorized to perform all routine coordination actions required to complete that **SAME** milestone without requesting additional User permission.

**Authorized Routine Actions:**
- Preparing the Codex implementation prompt.
- Handing the prompt to Codex.
- Allowing Codex to inspect authorized files.
- Allowing Codex to edit files within the milestone's approved write scope.
- Running approved tests and test suites.
- Collecting logs, results, and completion reports.
- Sending implementation evidence to Claude.
- Routing bounded repairs back to Codex after Claude audit.
- Repeating test/audit/repair cycles within the SAME milestone.
- Updating `URI_ACTIVE_MILESTONE.md` after valid state transitions.

**Permission Prompt Rule:**
If Antigravity's own execution environment presents an approval dialog for an action already covered by `URI_ACTIVE_MILESTONE.md`: use the existing approved authorization automatically where the platform permits. Do not convert routine internal milestone work into a new User-approval gate.

**Strict Boundaries — Request User Approval ONLY when:**
1. Starting a NEW milestone not yet approved.
2. Expanding beyond the current authorized write scope.
3. Performing commit/push when not already authorized.
4. Performing destructive or high-risk actions requiring explicit approval.
5. Changing security or authentication policy.
6. Encountering an architectural conflict requiring scope expansion.

### Direct Codex Execution & Permission Reduction Rule
Antigravity acts as a coordinator, not an execution proxy. The objective is to eliminate repeated host permission prompts while strictly preserving milestone governance and safety boundaries.

**Codex Direct Execution Authority:**
Within the currently approved milestone and write scope, Codex executes routine implementation directly inside `C:\Users\cheta\Development\uri-agent`:
- Reading repository files.
- Editing approved source files.
- Creating approved milestone files.
- Running the project Python interpreter and test suites (`pytest`, etc.).
- Running approved verification scripts.
- Inspecting test output and generating milestone completion reports.
- Collecting implementation evidence.

**Antigravity Non-Proxy Invariant:**
Antigravity must NOT repeatedly launch shell/Python commands (`python -c ...`, `pytest ...`, helper scripts, etc.) merely to duplicate or proxy work that Codex performs directly. Antigravity's role is:
- Milestone coordination and handoff.
- Scope enforcement.
- Repository evidence collection (via native file read tools).
- Milestone state updates.
- Relay between Codex and Claude via repository files.

**No Claude Session Scraping:**
Do NOT inspect `C:\Users\cheta\.claude\**`, Claude JSONL session logs, or private conversation histories. All Claude ↔ Antigravity ↔ Codex communication flows through repository artifacts (`URI_ACTIVE_MILESTONE.md`, `URI_AGENT_RELAY.md`, audit reports).

**Repository Trust Boundary:**
Routine Codex work remains strictly inside `C:\Users\cheta\Development\uri-agent`. Unrelated external directories are never accessed.

**Continuous Loop Invariant:**
Antigravity does not pause after generating a prompt, receiving an intermediate report, or seeing an internal state transition. The loop proceeds automatically:
`Claude plan → Antigravity coordination → Codex direct execution & evidence → Claude audit → [bounded Codex repair if needed] → Claude re-audit → live verification → update URI_ACTIVE_MILESTONE.md`

### Scheduled Monitoring Invariant
Automated scheduled monitoring is a mandatory, continuous component of this loop:
- Whenever an asynchronous background runner is active (`run_codex_current_milestone.py` or `run_claude_current_handoff.py`), Antigravity must maintain an active, periodic monitoring schedule (e.g. 180-second check-in intervals) conditioned on the task ID.
- At each monitoring interval:
  1. Inspect process health and output logs.
  2. Check repository mailbox (`URI_AGENT_RELAY.md`) and milestone state for updates.
  3. Report concise progress to the user.
  4. Automatically renew the monitoring schedule until the active runner completes.
- Upon task completion, the schedule early-terminates and the loop immediately advances to the next stage without delay.

### Handoff Monitoring Rule (No Idle Gap Invariant)
After EVERY agent handoff, Antigravity must automatically monitor the handoff to completion:
`HANDOFF → DELIVERY → MONITORING → COMPLETION DETECTION → EVIDENCE COLLECTION → NEXT LOOP ACTION`

- Applies to all agent transfers: Antigravity ↔ Claude, Antigravity ↔ Codex, Codex ↔ Claude.
- Applies to all phases: PLAN, PLAN_REVISION, IMPLEMENTATION, AUDIT, REPAIR, VERIFICATION, RE-AUDIT.
- Antigravity must never treat "handoff created" as task completion.
- Antigravity must not sit idle, wait for manual prompts, or create duplicate runner processes while a bridge is active.
- Default loop behavior is always:
  `handoff sent → monitor → collect → continue`



