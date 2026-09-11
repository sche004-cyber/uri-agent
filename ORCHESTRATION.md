# URI Multi-Agent Development Operating Architecture (AO-4)

**Status:** Canonical Operating Architecture — Claude-Planned / Codex-or-Gemma-Implemented / Claude-Verified-and-Released Cycle Activated
**Authority:** Governing Development Policy
**Baseline:** M22.2 (`34839ce`)
**Supersedes:** AO-2 (Qwen Coordination Loop) and the earlier Gemma-implemented /
Antigravity-audited-and-released AO-4 revision. Qwen 3 14B is retained only as
an explicitly invoked reserve/fallback; it is no longer the day-to-day
coordinator. This is a role change within the same canonical document, not a
competing workflow.

---

## 1. Canonical Team Model

The development operating model is a fixed, non-discretionary cycle: **Claude
Code** plans each milestone, performs the independent final audit (tracing
actual production paths rather than trusting a worker's report), directly
fixes bounded in-scope defects it finds, and is the sole authority for
`VERIFIED` and for `git commit`/`git push`; the **User** accepts or modifies
each plan before any implementation begins and is the non-delegable final
authority over architecture and policy; **Antigravity** manages the loop —
initiating tasks and routing implementation to **Codex** (preferred for
complex, multi-file, security-sensitive, or production-call-path work) or
**Gemma 4 12B** (bounded, small, or repetitive work) — and implements
UI/response-surface work only where specifically assigned. Neither Codex,
Gemma, nor Antigravity may declare a milestone `VERIFIED` or perform
`git commit`/`git push`.

> [!IMPORTANT]
> **Team Roster Invariant:** Qwen 3 14B is **NOT** part of the normal cycle.
> It is an explicitly invoked reserve/fallback only — used solely when the
> User separately invokes it for a second opinion, never as a default
> coordination step. Codex (CLI), by contrast, **is** part of the normal
> cycle as of this revision — the preferred implementation worker for
> complex/security-sensitive work (§6.1), routed to by Antigravity exactly
> like Gemma, not a reserve/fallback. Gemma 3 (the prior, unqualified model)
> remains excluded; **Gemma 4 12B** is the qualified local worker referenced
> throughout this document, used for bounded/small work (§6.2).

```
        ┌──────────────────────────────────────────────────────────────┐
        │                    USER (Final Authority)                    │
        │   • ACCEPT / MODIFY each plan before implementation begins   │
        │   • Non-delegable authority over architecture and policy     │
        └───────────▲───────────────────────────────────────┬──────────┘
                    │ Accept / Modify                        │ Accepted plan
                    │                                         ▼
        ┌───────────┴──────────────┐            ┌─────────────────────────┐
        │       CLAUDE CODE        │            │   CODEX  /  GEMMA 4 12B │
        │  1. Plan (fresh, from    │            │  3. Implement exactly   │
        │     verified repo state) │            │     the accepted scope  │
        │  6. Final audit; fixes   │            │  • Codex: complex/multi-│
        │     bounded defects      │            │    file/security work   │
        │     directly, re-audits  │            │  • Gemma: bounded/small │
        │  7. Sole VERIFIED /      │            │    work                 │
        │     NOT VERIFIED         │            │  • No Git authority     │
        │     authority            │            │  • No architectural     │
        │  8. Sole commit/push     │            │    authority; no VERIFIED│
        │     authority            │            │    authority            │
        └───────────▲──────────────┘            └────────────┬────────────┘
                    │ Evidence packages                       │ Files changed +
                    │ for independent audit                   │ tests performed
                    │                                          ▼
        ┌───────────┴──────────────────────────────────────────┐
        │                     ANTIGRAVITY                       │
        │  4. Initiate implementation tasks; route to Codex or  │
        │     Gemma per §6's complexity rule; manage handoffs   │
        │     and milestone state; implement UI/response work   │
        │     only where specifically assigned.                  │
        │  5. Package evidence and send to Claude for audit.    │
        │  Not an auditor. Never declares VERIFIED. No commit/  │
        │  push authority — release belongs solely to Claude.   │
        └─────────────────────────────────────────────────────┘

        Reserve / fallback only (never part of the normal cycle):
        QWEN 3 14B — explicit second-opinion invocation only.
```

### 1.1 The Authoritative Cycle (Standing Workflow)

1. **CLAUDE (Architect / Pre-Auditor):** Inspects verified current repo state, plans and pre-audits the next milestone before implementation, defines scope, acceptance criteria, tests, and UI impact, persists plan in `docs/plans/*_PLAN.md` and `docs/plans/*_STATE.md` (`STATE: DRAFT`), and waits for USER ACCEPT / MODIFY.
2. **USER (Final Authority):** Accepts or modifies the plan. No implementation begins before user acceptance (`STATE: ACCEPTED`).
3. **ANTIGRAVITY (Loop Manager / Orchestrator):** Initiates implementation tasks with precise task-initiation packages, and routes each task to the appropriate worker per §6's complexity rule — **Codex** preferred for complex/multi-file/security-sensitive/production-call-path work, **Gemma 4 12B** for bounded/small/repetitive/boilerplate work — coordinates agents, and maintains milestone state (`STATE: IMPLEMENTING`). Antigravity implements assigned UI, UX-facing behavior, and URI response/reply interface work only where specifically assigned.
4. **CODEX or GEMMA 4 12B (Implementer, per Antigravity's routing):** Implements the assigned backend/core code and test requirements per the accepted plan. Neither has Git authority, architectural authority, or the ability to approve its own work or declare `VERIFIED`.
5. **ANTIGRAVITY (Handoff Delivery):** Collects implementation evidence, packages relevant verification materials, and sends them to Claude for final audit (`STATE: VERIFYING`). Antigravity is not an auditor and does not substitute its judgment for Claude's audit.
6. **CLAUDE (Final Auditor / Bounded Fixer / Release Authority):** Independently audits the actual git diff, source code, tests, security boundaries, and architectural invariants, tracing actual production paths rather than trusting an implementer's or Antigravity's report.
   - If Claude finds a **bounded** defect within the accepted milestone's scope, Claude fixes it directly, re-runs tests, and re-audits (`audit → fix → re-audit`). A `NOT VERIFIED` result does NOT automatically return work to Gemma or Codex.
   - If a defect requires **substantial** remediation (not a bounded fix), Claude defines the required remediation and hands it to Antigravity, which routes the implementation task to Codex (preferred) or Gemma per §6 — Claude does not perform substantial implementation itself merely because it holds bounded-fix authority, and does not silently expand the accepted milestone's scope while fixing anything.
   - If any defect remains unresolvable within scope, Claude records `STATE: NOT VERIFIED` with clear findings.
   - Once satisfied with concrete evidence, Claude marks `STATE: VERIFIED`.
7. **RELEASE (Claude Sole Authority):** Solely Claude performs `git commit` and `git push` to `origin/master`.
8. **NEXT CYCLE:** Immediately after pushing, Claude inspects released state, pre-audits and plans the next milestone, and creates the plan and STATE artifact (`STATE: DRAFT`), waiting for User acceptance. The workflow does not stop merely because a milestone was pushed.

### 1.2 Role Definitions

| Role | Entity | Primary Responsibilities | Strict Constraints |
|---|---|---|---|
| **Final Authority** | **User** | Architectural acceptance gate; accepts/modifies every milestone plan before implementation; non-delegable authority over architecture and security policy. | Non-delegable. No AI can override. |
| **Architect, Final Auditor, Bounded Fixer & Release Authority** | **Claude Code** (CLI) | Milestone planning & pre-audits; independent final audit of git diff, source, and tests, tracing actual production paths rather than trusting reports; directly fixes **bounded** in-scope defects (`audit → fix → re-audit`); for **substantial** remediation, defines the requirement and hands it to Antigravity for Codex/Gemma routing rather than implementing it itself; sole authority for `VERIFIED`, `git commit`, and `git push`; immediately plans and pre-audits the subsequent milestone after release. | Does not delegate final verification. Fixes only bounded in-scope defects directly; does not silently expand an accepted milestone's scope. Does not perform primary/substantial implementation. |
| **Loop Manager / Orchestrator** | **Antigravity** (Gemini 3.8 Flash) | Manages the execution loop; prepares task-initiation packages; routes each implementation task to Codex or Gemma per §6's complexity rule; coordinates handoffs between workers and Claude; maintains milestone state; implements UI, UX-facing behavior, and URI response/reply interface work only where specifically assigned. | Not an auditor; never declares `VERIFIED`; **no commit/push authority**. |
| **Preferred Specialist Implementer** | **Codex** (CLI) | Implements complex, multi-file, architectural, security-sensitive, integration, or production-call-path work from Claude's accepted plan. | No Git authority; does not approve its own work, declare `VERIFIED`, or redefine accepted architecture. |
| **Local Bounded Implementation Worker** | **Gemma 4 12B** | Implements small bounded tasks, focused edits, repetitive work, boilerplate, and focused test creation per accepted plan/task package. | No Git authority; no architectural authority; not forced onto complex work Codex is better suited to. |
| **Specialist / Design Agents** | Auxiliary Agents | Propose architecture improvements, UI/UX, interface layouts, and reply/interaction designs. | Advisory/recommendation only; no code implementation. Claude reviews any proposal that materially affects architecture or milestone behavior before it becomes implementation guidance. |

### 1.3 Standing Rules & Continuity

The authoritative development operating process establishes:
- **Claude Directly Fixes Bounded Defects:** A `NOT VERIFIED` audit result does not automatically return work to Gemma or Codex. Claude directly fixes bounded defects within accepted scope, then independently re-audits (`audit → fix → re-audit`).
- **Substantial Remediation Routes Through Antigravity:** When a defect exceeds a bounded fix, Claude defines the required remediation and hands it to Antigravity, which initiates Codex (preferred for complex/security-sensitive work) or Gemma (bounded work) — Claude's bounded-fix authority never becomes unrestricted implementation authority.
- **Role Discipline:** Antigravity initiates tasks, maintains state, routes work to Codex/Gemma, and implements UI/UX/response surfaces only where specifically assigned; it does not audit and does not substitute its judgment for Claude's final audit. Codex and Gemma implement core code per accepted plan or Claude-defined remediation; neither has Git or architectural authority.
- **Waiting is a Valid State:** If an agent or worker is unavailable, state is preserved until available rather than inventing unauthorized bypasses. Temporary Claude/Codex unavailability is `WAITING_FOR_MODEL`, never `BLOCKED` and never a failed task — see §3's Permanent Quota-Exhaustion Invariant.
- **Standing Release Gate:** Claude alone performs `git commit` and `git push` upon independent `VERIFIED` status, then immediately plans the next milestone. The workflow does not stop merely because a milestone was pushed.

- **If Claude is unavailable or quota is exhausted:** an already-`ACCEPTED`
  plan may continue through `IMPLEMENTING` (Codex or Gemma) — that work is not blocked. But no fresh strategic plan is
  invented by any other agent, and no milestone reaches `VERIFIED` without
  Claude. State holds at `VERIFYING` (or `WAITING_FOR_MODEL` with `required_model: Claude`) until Claude returns. On return, Claude resumes from the preserved state
  (`READY_TO_RESUME`), not from scratch.

### 1.5 Default Auto-Approval Policy (2026-09-11 User Authorization)

**All future milestone plans are auto-approved by default.** This is a permanent standing rule, not a one-off grant for a single milestone. Claude does not stop to ask the User for ACCEPT/MODIFY on routine milestones, implementation choices, reversible architectural refinements, tests, refactoring, UI work, provider work, recovery logic, or similar engineering decisions — it proceeds directly from `DRAFT` to `ACCEPTED` (recorded as `Claude, standing User authorization` in the plan's history log, citing this section) and hands off to Antigravity for implementation, exactly as if the User had explicitly accepted it.

**The escape hatch is narrow and mandatory:** Claude must still stop and ask the User before proceeding when a decision would **materially change URI's core project structure, fundamental product identity, security/authority model, or another established constitutional boundary** — the same category of decision §6.6's User Escalation list already names (changes to governing documents, security-policy/approval-gate relaxation, breaking changes to persistence/wire APIs/user data isolation, irreversible destructive actions). When genuinely uncertain whether a plan crosses this line, Claude asks rather than assumes auto-approval — the default is proceed, the exception is stop, and the exception is deliberately narrow so it stays meaningful.

This does not touch any other gate: Claude's plan is still pre-audited against verified repository state before auto-approval (§1.1 step 1 is unchanged — auto-approval skips the User's own review of an already-rigorous plan, it does not skip the plan or its rigor), Antigravity still routes implementation per §6, and only Claude still declares `VERIFIED`/releases (§1.1 steps 6-7, unchanged). Auto-approval is a change to who reviews the plan before implementation begins, not a change to who verifies or releases it.

### 1.4 UI Impact Declaration

Every milestone plan Claude persists in step 1 must carry an explicit UI
impact declaration:

```
UI IMPACT: NONE
```
or
```
UI IMPACT: REQUIRED
```

When `UI IMPACT: REQUIRED`, UI implementation is part of the same milestone
(the routed implementer — Codex or Gemma — builds backend and UI together
under the same accepted plan, unless the plan specifically assigns the UI
portion to Antigravity), and the implementation must be independently
audited by Claude for UI/backend parity before the milestone can reach
`VERIFYING`. A milestone plan that touches backend contracts a UI consumes
(auth fields, roles, new endpoints, response shapes) must not declare
`UI IMPACT: NONE` merely because implementing the UI side was deferred —
deferral is a plan decision Claude must state explicitly, not an implicit
consequence of the declaration.

---

## 2. Active Coordination Loop

Development follows the fixed cycle in §1.1: Claude plans, the User gates
acceptance, Antigravity routes implementation to Codex or Gemma, Claude
independently audits (fixing bounded defects directly, or defining
substantial remediation for Antigravity to route), and only Claude releases.

```
                          USER MILESTONE REQUEST
                               ↓
                 CLAUDE — INSPECT VERIFIED STATE, DRAFT PLAN
                 (scope, acceptance criteria, tests, security,
                  UI IMPACT: NONE|REQUIRED)  →  state: DRAFT
                               ↓
                 USER — ACCEPT / MODIFY  →  state: ACCEPTED
                               ↓
                 ANTIGRAVITY — ROUTE TO CODEX OR GEMMA
                 (Codex: complex/multi-file/security-sensitive;
                  Gemma: bounded/small; no Git; no architectural
                  authority)  →  state: IMPLEMENTING
                               ↓
                 ANTIGRAVITY — PACKAGE EVIDENCE FOR CLAUDE
                 (files changed, tests performed — not an audit)
                               ↓
                 CLAUDE — INDEPENDENT FINAL AUDIT
                 (traces actual production paths; plan satisfied?
                  tests credible? security boundaries held?)
                  →  state: VERIFYING
                               ↓
                        VERIFIED?  ── NO, bounded ──► CLAUDE FIXES
                               │                       DIRECTLY, RE-AUDITS
                               │◄──────────────────────────┘
                        ── NO, substantial ──► CLAUDE DEFINES REMEDIATION
                               │                → ANTIGRAVITY ROUTES TO
                               │                  CODEX/GEMMA → CLAUDE
                               │◄─────────────────RE-AUDITS
                              YES
                               ↓
                 CLAUDE — COMMIT + PUSH  →  state: COMPLETE
                               ↓
                 CLAUDE — REVIEW COMMITTED STATE, DRAFT FRESH
                 NEXT-MILESTONE PLAN (not a repeat)  →  state: DRAFT
```

1. **Claude plans:** inspects verified repo state, drafts a fresh milestone
   plan (scope, acceptance criteria, tests, security considerations, UI
   impact per §1.4), and persists it.
2. **User gates:** accepts the plan as written or modifies it; nothing is
   implemented before this gate.
3. **Antigravity routes and the implementer builds:** Antigravity initiates
   the task, routing it to Codex (complex/multi-file/security-sensitive) or
   Gemma (bounded/small) per §6; the routed implementer builds exactly the
   accepted scope and reports files changed and tests performed.
4. **Antigravity packages the handoff:** collects the implementation
   evidence and sends it to Claude — this is a handoff, not an audit;
   Antigravity never declares `VERIFIED`.
5. **Claude audits:** independently inspects the actual diff, source, and
   tests (never taking a report at face value), checks plan satisfaction,
   test/fix credibility, and security boundaries, and issues `VERIFIED` /
   `NOT VERIFIED`. Bounded defects are fixed by Claude directly and
   re-audited; substantial defects are defined by Claude and routed back
   through Antigravity to Codex/Gemma.
6. **Release:** only after `VERIFIED`, Claude alone commits and pushes.
7. **Next cycle:** immediately after pushing, Claude reviews the newly
   committed milestone and its findings and drafts a fresh plan for the next
   milestone — never a repeat of the previous one.

Qwen does not appear in this loop; it is invoked only per §1.1's
reserve/fallback note, on explicit User instruction. Codex **does** appear
in this loop as of this revision — it is a standing routed implementer
(§6.1), not a reserve/fallback.

---

## 3. Coordination State Model

The development process operates under a persistent, resumable state
machine. States are durable — a milestone's current state must be
recoverable after an interruption, not re-derived from scratch. Claude and
Antigravity each own the transitions in their stage (§1.1); the User owns
the accept/modify gate, and Claude alone owns the release gate.

```
DRAFT ──► ACCEPTED ──► IMPLEMENTING ──► AUDITING ──► FIXING ──► AUDITING
                                                          │
                                                          ▼
                                                     VERIFYING
                                                     │        │
                                                    YES        NO
                                                     │          │
                                                     ▼          ▼
                                                 VERIFIED    FIXING / BLOCKED
                                                     │
                                                     ▼
                                                 COMPLETE ──► DRAFT (next cycle)

  Off-path / waiting states, entered from wherever the interruption occurs:
  BLOCKED, WORKER_FAILED, WAITING_FOR_QUOTA, WAITING_FOR_CLAUDE,
  WAITING_FOR_ANTIGRAVITY, WAITING_FOR_MODEL, READY_TO_RESUME
```

| State | Description | Entered when | Exit |
|---|---|---|---|
| `DRAFT` | Claude has drafted a fresh milestone plan and persisted it. | Start of a cycle, or after `COMPLETE`. | User reviews and accepts/modifies. |
| `ACCEPTED` | User has accepted the plan (as written, or as modified). | User gate passed. | Antigravity routes implementation to Codex or Gemma. |
| `IMPLEMENTING` | Codex or Gemma (per Antigravity's routing) is implementing the accepted scope. | After `ACCEPTED`. | The routed implementer reports files changed and tests performed. |
| `AUDITING` | Claude is independently inspecting the actual implementation (with Antigravity having packaged the handoff evidence). | After `IMPLEMENTING`, or after a `FIXING` pass. | Claude's audit reaches a verdict or finds a fixable problem. |
| `FIXING` | Claude is applying a bounded fix found during audit directly, or has handed a substantial remediation to Antigravity for Codex/Gemma routing. | Audit finds a fixable problem. | Returns to `AUDITING` to re-verify the fix, then reruns affected tests. |
| `VERIFYING` | Claude is finalizing its independent review of the implementation and evidence. | After `AUDITING` completes with no outstanding fixes. | Claude issues `VERIFIED` or sends back to `FIXING`/`BLOCKED`. |
| `VERIFIED` | Claude has confirmed the plan was satisfied with credible evidence. | Claude's explicit decision. | Claude releases. |
| `COMPLETE` | Commit and push are done; milestone closed. | After release. | Claude starts the next cycle at `DRAFT`. |
| `BLOCKED` | A genuine blocker exists that no agent in the cycle can resolve alone (e.g. an unresolved plan ambiguity, a real regression with no bounded fix). | Any stage, when progress cannot continue safely. | User intervention. |
| `WORKER_FAILED` | Codex, Gemma, or Antigravity failed to complete its stage (crash, tool failure, non-recoverable error). | During `IMPLEMENTING`, `AUDITING`, or `FIXING`. | Retry, re-route to the other implementer, or User-authorized explicit fallback for that instance only. |
| `WAITING_FOR_QUOTA` | A required agent has hit a quota/rate limit. | Any stage. | Resumes automatically once quota is available, or User intervenes. |
| `WAITING_FOR_CLAUDE` | Claude is unavailable or quota-exhausted; an already-`ACCEPTED` plan continues through `IMPLEMENTING`, but nothing reaches `AUDITING`/`VERIFIED` and no fresh plan is drafted. | Claude unavailable while a plan is already `ACCEPTED`. | Claude returns and resumes verification from preserved state. |
| `WAITING_FOR_ANTIGRAVITY` | Antigravity is unavailable; task initiation/routing/handoff cannot proceed. | Plan accepted but no worker has been initiated, or implementation complete but no handoff packaged. | Antigravity returns and resumes. |
| `WAITING_FOR_MODEL` | Claude or Codex is temporarily unavailable (quota exhaustion, rate limiting, a temporary provider outage, or another recoverable failure — see §3.1). | Antigravity detects a recoverable model-unavailability signal for Claude or Codex, at any stage. | The required model becomes available again; Antigravity restores the recovery packet and transitions to `READY_TO_RESUME`. |
| `READY_TO_RESUME` | A returning agent (most often Claude after `WAITING_FOR_CLAUDE`) has the preserved state and evidence in hand and can resume exactly where the cycle left off. | Whenever a waiting state's blocking condition clears. | Resumes the specific in-flight stage — never restarts the cycle from `DRAFT` unless the stage was `DRAFT` itself. |

### 3.1 The Permanent Quota-Exhaustion Invariant (2026-09-11 User Authorization)

Antigravity must **never** terminate, abandon, fail, or bypass the development loop merely because Claude or Codex has exhausted its quota or is temporarily unavailable. This is a permanent standing invariant, not optional per-milestone behavior — implemented in `scripts/dev_workflow/state_machine.py` (`WorkflowState.WAITING_FOR_MODEL`, `classify_unavailability()`, `TemporaryUnavailabilityReason`, `PermanentFailureReason`) and `state_manager.py` (`RecoveryState`), and tested in `tests/dev_workflow/test_workflow.py`.

**Temporary vs. permanent, classified explicitly, never guessed.** `classify_unavailability(reason)` is the single authoritative classifier:
- **Temporary** (→ `WAITING_FOR_MODEL`, never `BLOCKED`, never a failed task): quota exhaustion, token/session limit exhaustion, rate limiting, a temporary provider outage, temporary capacity unavailability, a recoverable network failure.
- **Permanent** (→ `BLOCKED` with a `BLOCK_REASON`, the only case model-unavailability may block a milestone): an invalid/removed model ID, a provider that was never configured, revoked credentials, denied account access — genuine configuration failures, not availability blips.
- An unrecognized reason raises rather than defaulting either way — Antigravity must classify explicitly or escalate.

**While `WAITING_FOR_MODEL`, Antigravity must NOT:** terminate the milestone; mark the task failed; skip the missing model; silently substitute Codex for Claude or Claude for Codex in either direction; ask the User to manually restart the milestone; restart the milestone from the beginning; discard partial work; or create a duplicate task. It also must not ask the User what to do — Antigravity owns the pause/resume process and may report status (e.g. "M22.8 paused, waiting for Codex quota/provider availability, last completed checkpoint: ..., resume stage: ...") without requiring approval.

**Recovery state, persisted before waiting.** Before entering `WAITING_FOR_MODEL` or `BLOCKED`, Antigravity persists a `RecoveryState` block (`### RECOVERY STATE` in the milestone's `STATE.md`, per §10.4) carrying: `required_model`, `current_owner`, `resume_stage`, `pause_reason`, `task`, `completed_steps`, `remaining_steps`, `changed_files`, `git_state`, `test_state`, `audit_state`, `last_successful_checkpoint`, `retry_metadata`. This must survive an application/terminal/session/machine restart — it lives on disk in the STATE.md file, not in any agent's conversation memory.

**Resume is idempotent, never a blind restart.** `WAITING_FOR_MODEL → READY_TO_RESUME` (the "MODEL_RESUMED" event is this transition, not a separate stored state) restores the checkpoint and continues from `resume_stage`. Before resuming Codex implementation, verify existing partial work against the actual repository state and diff rather than blindly rerunning the whole implementation. Before resuming Claude planning/auditing, provide a compact recovery packet (the persisted `RecoveryState`) containing completed findings and remaining work, not a full restart briefing.

**Role ownership is unchanged by this invariant:** Claude remains Planner/Architect/Final Auditor, Codex remains Implementer/Tester/Repair Engineer, Antigravity remains Workflow Controller/Mediator/Independent Reviewer. If Claude exhausts quota, Antigravity waits for Claude. If Codex exhausts quota, Antigravity waits for Codex. Antigravity must never take over either role simply to keep the loop moving — that would itself be the silent-substitution failure mode this invariant exists to prevent.

---

## 4. Claude Planning & Verification Contract

### 4.1 Planning Input (what Claude inspects before drafting a plan)

Before drafting a fresh milestone plan (§1.1 step 1), Claude inspects the
**verified current repository state**, not a claimed or in-progress one:

1. **Governing Policy & Rules:** `AGENTS.md` and `ORCHESTRATION.md`.
2. **Current Project State:** `PROJECT_MEMORY.md` (resume point, verified
   baseline, remaining gaps) and `URI_MILESTONE_TRACKER.md`.
3. **Prior Milestone Architecture:** The relevant milestone section(s) of
   `URI_M22_ARCHITECTURE.md`, plus any prior plan document for context.
4. **Actual repo state:** the real diff/log since the last verified
   commit — never a worker's summary of it — when a plan follows a just-
   verified milestone.

### 4.2 Plan Output Contract

Every plan Claude persists (§1.1 step 1) must include:

```markdown
### MILESTONE PLAN
- **Milestone ID:** [e.g. M22.4]
- **Baseline:** [commit hash + verified test count this plan builds on]
- **Objective:** [Concise goal]
- **Scope:** [Exact files/areas in scope]
- **Out-of-Scope / Protected Files:** [Explicit list, e.g. orchestrator.py]
- **Acceptance Criteria:** [Concrete, checkable criteria]
- **Test Plan:** [What must be tested and how]
- **Security Considerations:** [Threat/boundary analysis relevant to this milestone]
- **UI IMPACT:** [NONE | REQUIRED — see §1.4]
- **Deferred Items:** [Explicitly named work not in this milestone's scope]
```

### 4.3 Final Verification Contract

At §1.1 step 6, Claude independently audits the actual implementation and
evidence (test logs, diffs — not summaries alone) and issues one of:
- `VERIFIED` — the accepted plan's acceptance criteria are satisfied with
  credible evidence, gaps are accurately classified as deferred/accepted,
  and no protected boundary was crossed.
- `NOT VERIFIED` — with the specific unmet criterion, missing evidence, or
  regression named, returning the cycle to `FIXING` (Claude fixes bounded
  issues directly, or defines substantial remediation for Antigravity to
  route to Codex/Gemma) or `BLOCKED` (issues requiring User input).

*Rule:* Neither Codex, Gemma, nor Antigravity may declare a milestone
`VERIFIED`; only Claude does, and only from real evidence it has
independently examined.

---

## 5. Antigravity Loop Management, Task Routing & Handoff Responsibilities

Antigravity manages the execution loop and routes implementation work. It is
**not** the auditor, the bounded fixer, or the release authority — those
belong solely to Claude (§4.3, §1.1 steps 6-7). Antigravity's responsibilities:

1. **Task Initiation:** Preparing precise task-initiation packages from
   Claude's accepted plan (or Claude-defined remediation requirements) and
   initiating the appropriate worker.
2. **Worker Routing:** Routing each implementation task to Codex (preferred
   for complex/multi-file/security-sensitive/production-call-path work) or
   Gemma (bounded/small/repetitive/boilerplate work) per §6's complexity
   rule — never forcing complex work through Gemma merely because it is
   available.
3. **Handoff Packaging:** Collecting the routed implementer's reported files
   changed and tests performed, and sending that evidence to Claude for
   independent audit. This is a packaging/delivery function, not an audit —
   Antigravity does not itself assess correctness, test sufficiency, or
   security boundaries as a substitute for Claude's inspection.
4. **State Maintenance:** Keeping the milestone's `STATE.md` history log
   current as the cycle moves through its stages, and ensuring the next
   valid workflow stage is actually initiated rather than silently stalling.
5. **Assigned UI/Response Implementation:** Implementing UI, UX-facing
   behavior, or URI response/reply interface work only when a plan
   specifically assigns that work to Antigravity rather than to the routed
   Codex/Gemma implementer.
6. **Circuit Breakers:** Aborting a worker's execution immediately if it
   attempts unauthorized architectural changes, scope expansion, or
   destructive operations, and escalating to Claude/User rather than
   resolving the conflict itself.

**Antigravity must NOT:** declare a milestone `VERIFIED`; perform
`git commit`/`git push` for a milestone release under any circumstance;
substitute its own judgment for Claude's independent final audit; or apply
its own "bounded fixes" as a stand-in for Claude's audit-driven fix
authority — a defect Antigravity notices during task management is reported
to Claude, not silently patched.

---

## 6. Worker Selection & Delegation Rules

Antigravity chooses the implementation worker according to task complexity:
- **Routine / small / bounded / boilerplate / focused tests:** → **Gemma 4 12B**
- **Complex / important / multi-file / security-sensitive / architectural / production-call-path:** → **Codex**
- **UI / URI response / presentation, only when specifically assigned:** → **Antigravity**
- **Architectural planning / final audit / bounded fixes / release:** → **Claude** (never delegated)

### 6.1 Codex (Preferred Specialist Coder / Implementer)
- The preferred implementation worker for complex coding, architectural
  implementation, difficult integrations, refactoring, multi-file changes,
  security-sensitive implementation, and production-call-path fixes — a
  standing routed worker as of this revision, not a reserve/fallback.
- Implements from Claude's accepted plan (or Claude-defined remediation
  requirement): exact task objective, relevant paths, constraints, protected
  files, required tests, and acceptance criteria.
- Does not approve its own work, declare `VERIFIED`, commit, push, or
  redefine accepted architecture.

### 6.2 Gemma 4 12B (Local Bounded Worker via Ollama/MCP)
- Available through local Ollama/MCP infrastructure for small bounded
  implementation tasks, repetitive work, boilerplate, focused test creation,
  and low-risk edits.
- Do not force complex implementation through Gemma when Codex is the more
  appropriate implementation worker. If Gemma struggles with context,
  incomplete implementation, repeated production-path misses, or poor
  output quality, route the task to Codex rather than repeatedly retrying
  Gemma.
- Has no Git authority and no architectural authority.

### 6.3 Specialist / Design Agents (Advisory Only)
- May propose architecture improvements, UI/UX, interface layouts,
  interaction/workflow improvements, and URI response/reply presentation.
- Do not implement. Where a proposal materially affects architecture or
  milestone behavior, Claude reviews it (`ACCEPT`, `MODIFY`, `REJECT`,
  `ARCHITECTURAL_ESCALATION`) before it becomes implementation guidance.

### 6.4 Qwen 3 14B (Reserve / Fallback Only, Explicit Invocation)
- An explicit, User-invoked second-opinion review only — never a default
  coordination step, never a substitute for Claude's planning or
  verification role, and never automatically substituted in if Codex or
  Gemma is unavailable.

### 6.5 Claude Code — Not a Delegation Target, a Fixed Stage
Claude's planning (§1.1 step 1) and final audit (§1.1 step 6) are not
discretionary escalations chosen by another worker; they are mandatory
stages of every milestone. Nothing in this document authorizes skipping
either stage, regardless of how routine a milestone appears. Claude's
bounded-fix authority is not a license for primary implementation: for
substantial remediation, Claude defines the requirement and hands it to
Antigravity for Codex/Gemma routing (§1.1 step 6).

### 6.6 User Escalation (Final Authority)
Any worker **MUST escalate to the User** for:
- Changes to governing documents (`ADR-018`, `URI_AI_OPERATING_POLICY.md`,
  `URI_MODEL_RUNTIME_CONTRACT.md`).
- Modifications to security policies or approval gate relaxation.
- Breaking changes to persistence, wire APIs, or user data isolation.
- Irreversible destructive actions.
- Unresolved disagreements between the plan and the implementation, or
  between a worker's report and Claude's audit.
- Milestone start, pause, `BLOCKED` resolution, or plan modification.

---

## 7. Qwen 3 14B Qualification Record (Reserve / Fallback Role Only)

This record is retained as historical qualification evidence for Qwen's
**reserve/fallback** role (§1.1, §6.4) — an explicit, User-invoked second
opinion, never the day-to-day coordinator role AO-2 originally assigned it.
The local Qwen 3 14B installation was formally evaluated on 10 Sep 2026
across 8 practical URI coordination benchmarks (Tests A through H).

### 7.1 Model Profile
- **Model Tag:** `qwen3:14b` (Ollama, local)
- **Parameters:** 14.8B (Q4_K_M quantization)
- **VRAM / Offload:** ~10 GB VRAM, 100% GPU offload
- **Operational Window:** 8,192 tokens configured (default Ollama 4,096)
- **Generation Speed:** ~45.5 tokens/sec
- **Observed Turn Latency:** 16–38 seconds (due to internal reasoning tokens)

### 7.2 Qualification Status
**QUALIFIED WITH LIMITATIONS** (Overall Score: **4.55 / 5.0**)

### 7.3 Category Scores
1. **Task Triage:** 5/5 — Flawlessly identified M22.3 baseline, acceptance criteria, and sequence.
2. **Delegation Accuracy:** 5/5 — Appropriately delegated substantial coding to Codex, UI/local to Antigravity.
3. **Architecture Awareness:** 4/5 — Deeply understands model-centric vs deterministic runtime separation.
4. **Security / Escalation Discipline:** 5/5 — Instantly escalated security boundaries and route auth to Claude.
5. **Scope Discipline:** 4/5 — Strong on positive scope; required assistance on negative scope exclusions.
6. **Worker Handoff Quality:** 5/5 — Generated comprehensive Task Briefs with exact verification commands.
7. **Worker-Result Review:** 5/5 — Caught subtle security defects (unauthenticated approval gate bypass).
8. **Change-Aware Audit Reasoning:** 5/5 — Isolated touched endpoints and reused prior M22.2 test evidence.
9. **Context Retention:** 4/5 — Maintained multi-turn context; occasionally dropped deferred feature lists.
10. **Conflict Handling:** 4/5 — Correctly applied document precedence and escalated policy conflicts to User.
11. **Latency / Practicality:** 3/5 — 16–38s latency requires batched turns rather than high-frequency chatter.

### 7.4 Key Strengths
- Rigidly enforces security invariants (e.g. immediately caught attempt to use `experience_tier` for authorization).
- Accurately respects worker specializations (Codex for bulk code, Claude for security/architecture).
- Natural change-aware auditing discipline without prompting.

### 7.5 Known Limitations & Mitigations
- **Negative Exclusion Blindspot:** Can fail to recall negative constraints (e.g. out-of-scope messaging channels) when not in immediate context.
  *Mitigation:* Antigravity explicitly injects negative constraints into every prompt packet.
- **Context Capacity Bounds:** Cannot ingest 60KB+ documents in one turn.
  *Mitigation:* Antigravity slices specific milestone sections before prompting Qwen.
- **Turn Latency:** 16–38s reasoning time.
  *Mitigation:* Use Qwen for milestone/task-level coordination turns, not character-by-character typing.

---

## 8. Document Precedence Hierarchy

When resolving ambiguities or conflicting requirements, agents must strictly follow this nine-level precedence hierarchy:

1. **Level 1: User Explicit Decisions** (Direct user instructions, approvals, manual overrides).
2. **Level 2: Security & Authority Invariants** (Propose → validate → approve → execute; untrusted model output; data isolation).
3. **Level 3: Governing Architecture Decisions** ([ADR-018](URI_Model_Centric_Architecture_Docs/URI_ADR_018_MODEL_CENTRIC_ARCHITECTURE.md)).
4. **Level 4: Runtime ↔ Model Contract** ([URI_MODEL_RUNTIME_CONTRACT.md](URI_Model_Centric_Architecture_Docs/URI_MODEL_RUNTIME_CONTRACT.md)).
5. **Level 5: AI Operating Policy** ([URI_AI_OPERATING_POLICY.md](URI_Model_Centric_Architecture_Docs/URI_AI_OPERATING_POLICY.md)).
6. **Level 6: Current Milestone Architecture Specification** ([URI_M22_ARCHITECTURE.md](URI_M22_ARCHITECTURE.md)).
7. **Level 7: Project Memory & Tracking State** ([PROJECT_MEMORY.md](PROJECT_MEMORY.md), [URI_MILESTONE_TRACKER.md](URI_MILESTONE_TRACKER.md)).
8. **Level 8: Worker Task Instructions & Plans** (Milestone task briefs and implementation plans).
9. **Level 9: Model Reasoning & Worker Proposals** (Coordinator proposals, worker drafts, suggestions).

*Invariant:* A lower-level proposal or instruction can **never** override a higher-level constraint.

---

## 9. Change-Aware Auditing Policy

- **Baseline Invariance:** Completed milestones (M1 through M22.2) are proven ground truth; do not re-audit baseline architecture merely to resume work.
- **Delta Isolation:** Before auditing, determine exact changed files using `git diff --stat <baseline>`.
- **Targeted Verification:** Audit only new code paths, modified boundary imports, or newly added endpoints.
- **Evidence Reuse:** Explicitly cite prior verification records (e.g. "M22.2 role isolation verified by `test_m22_2_roles_sessions.py`") rather than re-running or re-proving untouched modules.

---

## 10. Standard Milestone Handoff Protocols

### 10.1 Plan Handoff (Claude → User → Antigravity → Codex/Gemma)
Claude's persisted Milestone Plan (§4.2) is the Task Brief for the normal
cycle — there is no separate coordinator-drafted brief. Once the User
accepts (or modifies) it, the accepted plan's Scope, Out-of-Scope/Protected
Files, Acceptance Criteria, Test Plan, and UI Impact sections are handed
unchanged to whichever implementer (Codex or Gemma) Antigravity routes the
task to per §6.

### 10.2 Implementer Return Report (Codex or Gemma → Antigravity)
The routed implementer reports back in this format:

```markdown
### IMPLEMENTER RETURN REPORT
- **Milestone ID:** [Matching the accepted plan]
- **Implementer:** [Codex | Gemma 4 12B]
- **Summary of Actions:** [What was performed]
- **Files Modified/Created:** [List with line-count delta]
- **Tests Performed:** [Exact test commands and pass/fail counts, as run]
- **Assumptions & Decisions:** [Any design choices made during implementation, within accepted scope]
- **Known Issues / Gaps:** [Remaining items or unverified edges]
```

### 10.3 Handoff Evidence Package (Antigravity → Claude)
Antigravity's persistent handoff, produced before Claude's final audit
(§1.1 step 6), must include:

```markdown
### ANTIGRAVITY HANDOFF PACKAGE
- **Milestone ID:** [Matching the accepted plan]
- **Implementer Used:** [Codex | Gemma 4 12B, and why — per §6's routing rule]
- **Implementer Return Report:** [§10.2, attached or linked]
- **Files Changed:** [Actual diff summary]
- **Tests the Implementer Reported:** [Exact commands and counts, as reported — not independently re-run by Antigravity as a substitute for Claude's audit]
- **Anything Antigravity Noticed:** [Named explicitly for Claude's attention; Antigravity does not resolve or paper over it — that is Claude's audit function]
```
Antigravity must not mark a milestone `VERIFIED` in this package — that
decision belongs solely to Claude (§4.3), who independently re-runs and
verifies the relevant tests itself rather than trusting this package's
reported counts.

### 10.4 Persistent State File (handoff artifact, not a coordinator)

Each milestone plan (`docs/plans/<ID>_..._PLAN.md`) has a sibling
`docs/plans/<ID>_STATE.md` file, created by Claude at `ACCEPTED` (§1.1
step 2) and updated in place by whichever worker owns the current
stage. It carries: the current state (§3's vocabulary), an append-only
History Log of transitions, the §10.2/§10.3 report templates for
the routed implementer and Antigravity to fill in directly, and a
`### RECOVERY STATE` block (§3.1) that stays an empty template until a
`WAITING_FOR_MODEL`/`BLOCKED` pause actually happens. Its purpose is
narrow: the cycle must be resumable from **disk**, not from any one agent's
conversation history, so a session restart, quota exhaustion, or
model unavailability never loses evidence or forces the cycle to
restart from `DRAFT`. This file is a state record only — it has no
authority of its own, drives no execution, and is not a substitute for,
or a competitor to, `scripts/qwen_coordinator.py`'s proposal-schema
mechanism (which remains Qwen-reserve-only, §6.4) or any future
implementer-driver tooling. It is development-only tracking and is
never read by, or shipped inside, the URI runtime itself.
