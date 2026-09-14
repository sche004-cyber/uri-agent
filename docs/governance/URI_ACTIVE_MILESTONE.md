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

**CURRENT MILESTONE:**  
M30.8 — Canonical Cutover + Legacy Retirement — **CLAUDE ACCEPT (Phase A + Phase B items 1-3)**
(User authorized 2026-09-14: "I explicitly authorize implementation of the
revised: M30.8 — CANONICAL CUTOVER + LEGACY RETIREMENT").
Plan: `docs/plans/M30_8_CANONICAL_CUTOVER_LEGACY_RETIREMENT_PLAN.md`.
Implementer: Codex.
Plan authority & independent auditor: Claude.
Development loop coordinator: Antigravity.

**CURRENT STATE:**  
CLAUDE ACCEPT (Phase A + Phase B items 1-3) — Independently audited and verified by Claude (see `docs/plans/M30_8_CLAUDE_AUDIT.md`). Bounded repair in `workflow_planner.py` applied and verified. Zero code regressions. Awaiting Phase A live observation window before Phase B item 4.

**LOOP_STATE:**  
WAITING_FOR_USER_DECISION (M30.8 cutover independently accepted; awaiting User direction)

**CURRENT OBJECTIVE:**  
Implement the bounded repair exactly as specified in
`docs/plans/M30_PROVIDER_FAILURE_FALSE_CONSENT_REPAIR_PLAN.md`
(finalized, User-approved):

- **Primary:** gate `orchestrator.py`'s `elif learned_skill:` branch
  (lines 4742-4762) so it fires only when the current turn is **not**
  in a genuine model-failure state. Three-way distinction, exact
  User terminology, must not be collapsed into two:
  - `MODEL_NOT_ATTEMPTED` (reasoning disabled, or interpreter never
    invoked) → gate does NOT fire; existing fast path unaffected.
  - `MODEL_REACHED_BUT_INVALID` (a real response came back, just
    malformed/unparseable) → gate does NOT fire; this is not the
    failure class the User's invariant targets.
  - `MODEL_TERMINALLY_UNAVAILABLE` (UNREACHABLE / TIMEOUT /
    FALLBACK_EXHAUSTED - a required model path was attempted and
    definitively failed) → gate FIRES: fail closed before
    learned-skill execution or any persistent side effect; return a
    deterministic model-unavailable response (reuse the existing
    `drafting_provider_unreachable`-style honest-degradation pattern,
    per plan §5 - no new mechanism).
- **Defense-in-depth:** `SkillMemory.find_matching_skill()`
  (`skill_memory.py` lines 129-177) must reject an empty-`task_type`-
  and-empty-`domain` match - never a real signal.
- **Explicitly out of scope - do not redesign:** `remember_fact.py`,
  `MemoryStore`/`user_memory.py`, consent semantics, or learned-skill
  architecture beyond this exact gate.
- **Escape hatch, binding:** if the approved condition cannot be
  represented cleanly without broader architectural changes, STOP and
  return for scope approval rather than improvising a workaround.
- **Required verification (all 7, per the User's own list):** all 9
  new repair tests passing (9th added 2026-09-13 per product review §5:
  no approval-gated/side-effecting capability executes either, during
  model-failure state - see `M30_PROVIDER_FAILURE_FALSE_CONSENT_
  REPAIR_PLAN.md` §6 item 9); the existing 6 `test_orchestrator_skill_
  memory_execution.py` tests re-run unchanged and still passing; the
  exact prior provider-unreachable/weather scenario reproduced live
  against a real server, confirming a deterministic model-unavailable
  response, no learned-skill execution, no `remember_fact` execution,
  no persistent memory write, no false `user_provided` provenance;
  healthy-path explicit memory disclosure re-confirmed working; full
  regression run to a real terminal result (never an unobserved/killed
  run treated as a result); Claude's own independent audit of all of
  the above before this is treated as closed.
- **M30.8 remains NOT AUTHORIZED until this repair receives Claude
  ACCEPT** - independent of, and in addition to, M30.7C's own
  separately-tracked evidence-closure gaps (below).

**M30.7C's own prior objective (Scenario 2/8/12 evidence-closure,
best-effort Scenario 7, regression, full 12-scenario matrix) remains
recorded and resumable separately - not reopened or subsumed by this
milestone:**
- MANDATORY: Scenario 2 (corrected DISCONNECTED fixture), Scenario 8
  (approval content-envelope), Scenario 12 (visible fallback capture -
  now additionally gated behind this repair being accepted first,
  since Scenario 12 IS the defect this milestone fixes).
- BEST EFFORT: Scenario 7. NOT REOPENED: Scenarios 4, 5, 9.

M30.7B itself remains CLOSED at `LIVE_VERIFIED + CLAUDE ACCEPT`
(independently confirmed disposition: `M30.8 NOT READY`).

---

## 2. Authoritative Files

- `docs/plans/M30_PROVIDER_FAILURE_FALSE_CONSENT_REPAIR_PLAN.md`
- `docs/plans/M30_PROVIDER_FAILURE_FALSE_CONSENT_STATE.md`
- `docs/plans/M30_7C_READINESS_EVIDENCE_CLOSURE_PLAN.md`
- `docs/plans/M30_7C_STATE.md`
- `docs/plans/M30_7C_CLAUDE_AUDIT.md`
- `docs/plans/M30_8_BLOCKER_DISPOSITION_PLAN.md`
- `docs/plans/M30_7B_CLAUDE_AUDIT.md`
- `docs/plans/M30_7B_CANONICAL_READINESS_CLOSURE_REPORT.md`
- `docs/plans/M30_7B_CANONICAL_READINESS_CLOSURE_PLAN.md`
- `docs/plans/M30_7B_STATE.md`
- `docs/governance/URI_AGENT_RELAY.md`
- `docs/plans/M30_7A_CLAUDE_AUDIT.md`
- `docs/plans/M30_7A_CANONICAL_LIVE_EVIDENCE_REPORT.md`
- `docs/plans/M30_7A_CANONICAL_LIVE_EVIDENCE_PLAN.md`
- `docs/plans/M30_7A_STATE.md`
- `docs/plans/M30_7_CLAUDE_AUDIT.md`
- `docs/plans/M30_7_WORKFLOW_CONTINUATION_REPORT.md`
- `docs/plans/M30_7_WORKFLOW_CONTINUATION_PLAN.md`
- `docs/plans/M30_7_STATE.md`

- `docs/plans/M30_7_STATE.md`
- `docs/plans/URI_CANONICAL_AGENT_LOOP_MIGRATION_PLAN.md`
- `docs/architecture/URI_CANONICAL_AGENT_LOOP_ARCHITECTURE.md`
- `docs/plans/M30_6A_FINAL_LIVE_VERIFICATION.md`
- `docs/plans/M30_6A_CLAUDE_AUDIT.md`

---

## 3. Authorized Agent Roles

- **Claude:**  
  Architecture, planning, audit, and read-only research unless separately authorized to implement.
- **Antigravity:**  
  Coordinator, task relay, evidence collection, and milestone-state maintenance.
- **Codex:**  
  Implementation of the currently approved bounded milestone.
- **User:**  
  Final live-verification and next-milestone approval authority.

---

## 4. Operational Scopes

**CURRENT WRITE SCOPE (M30.8 Canonical Cutover + Legacy Retirement):**  
- `uri_core/app/server.py` — canonical-first order inversion in `/ask`, reason-coded fallback logging.
- `uri_core/core/canonical_execution.py` — unrestricted default authority (`CANONICAL_EXECUTION_ALLOWLIST=None`), terminal non-execution envelopes, emergency allowlist killswitch.
- `uri_core/core/workflow_planner.py` — bounded repair: restore honest capability-gap failure reporting while removing duplicate branch conditions.
- `test_canonical_execution.py` — test suite for canonical cutover, killswitch, and non-execution envelopes.
- `docs/plans/M30_8_*` — plan, report, audit, state files.
- `docs/governance/URI_ACTIVE_MILESTONE.md`, `docs/governance/URI_AGENT_RELAY.md`, `PROJECT_MEMORY.md`.
- **Protected boundaries preserved:** No modifications to `uri_ui/`, no security/permission/approval alterations, no git commit/push without explicit User instruction.

**M30.7C's own write scope (`docs/plans/M30_7C*` + governance files,
no source unless separately re-approved) remains recorded but is not
active for this milestone's own work.**

**CURRENT READ SCOPE:**  
- Full repository as needed to implement and verify this repair.

---

## 5. Stop Conditions & Invariants
 
- Do NOT make canonical execution global.
- Do NOT start or implement M30.8 - remains NOT AUTHORIZED until this
  repair receives Claude ACCEPT.
- Do NOT retire legacy mechanisms.
- Do NOT touch `uri_ui/`.
- Do NOT commit or push without separate explicit User instruction.
- Do NOT redesign `remember_fact`, `MemoryStore`, consent semantics, or
  learned-skill architecture beyond the approved bounded repair.
- Do NOT collapse the three-way model-failure distinction
  (`MODEL_NOT_ATTEMPTED`/`MODEL_REACHED_BUT_INVALID`/`MODEL_
  TERMINALLY_UNAVAILABLE`) into two - only the third gates the
  learned-skill fast path.
- **If the approved condition cannot be represented cleanly without
  broader architectural changes, STOP and return for scope approval**
  rather than improvising a workaround - binding, per the User's own
  explicit instruction.
- Scope strictly bounded to the M30-PFC repair as specified in
  `docs/plans/M30_PROVIDER_FAILURE_FALSE_CONSENT_REPAIR_PLAN.md`.

---

## 6. Next Milestone Status

**NEXT MILESTONE:**  
M30.8 — Canonical Default Cutover

**NEXT MILESTONE STATUS:**  
NOT AUTHORIZED (readiness bar independently confirmed MET as of
2026-09-14 - see "READINESS CONCLUSION" above: M30-PFC accepted,
mandatory Scenarios 2/8/12 closed, regression clean. **Readiness is
not authorization** - per this file's own "Do Not Self-Authorize"
rule, §7, this status stays NOT AUTHORIZED until the User explicitly
authorizes M30.8 through Claude.)

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





