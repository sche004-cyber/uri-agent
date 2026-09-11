# URI Multi-Agent Development Operating Architecture (AO-4)

**Status:** Canonical Operating Architecture — Claude-Planned / Gemma-Implemented / Antigravity-Audited Cycle Activated
**Authority:** Governing Development Policy
**Baseline:** M22.2 (`34839ce`)
**Supersedes:** AO-2 (Qwen Coordination Loop). Qwen 3 14B is retained only as an
explicitly invoked reserve/fallback; it is no longer the day-to-day
coordinator. This is a role change within the same canonical document, not a
competing workflow.

---

## 1. Canonical Team Model

The development operating model is a fixed, non-discretionary cycle: **Claude
Code** plans each milestone and performs final verification, the **User**
accepts or modifies each plan before any implementation begins, **Gemma 4
12B** implements exactly the accepted plan (backend and UI, when the plan
requires UI work), and **Antigravity** independently audits the actual
implementation, fixes bounded problems, and enforces the commit/push gate.
The **User** retains final authority throughout.

> [!IMPORTANT]
> **Team Roster Invariant:** Qwen 3 14B is **NOT** part of the normal cycle.
> It is an explicitly invoked reserve/fallback only — used solely when the
> User separately invokes it for a second opinion, never as a default
> coordination step. Codex (CLI) likewise sits outside the normal cycle: it
> remains available only via explicit user invocation for large mechanical
> refactors, under the same reserve/fallback status as Qwen. Gemma 3 (the
> prior, unqualified model) remains excluded; **Gemma 4 12B** is the
> qualified implementer referenced throughout this document.

```
        ┌──────────────────────────────────────────────────────────────┐
        │                    USER (Final Authority)                    │
        │   • ACCEPT / MODIFY each plan before implementation begins   │
        │   • Sole authority to release after Claude says VERIFIED     │
        └───────────▲───────────────────────────────────────┬──────────┘
                    │ Accept / Modify                        │ Accepted plan
                    │                                         ▼
        ┌───────────┴──────────────┐            ┌─────────────────────────┐
        │       CLAUDE CODE        │            │      GEMMA 4 12B        │
        │  1. Plan (fresh, from    │            │  3. Implement exactly   │
        │     verified repo state) │            │     the accepted scope  │
        │  5. Final verification   │            │  • Backend + UI when    │
        │     (VERIFIED/NOT)       │            │    required             │
        │  No architectural        │            │  • No Git authority     │
        │  authority for Gemma or  │            │  • No architectural     │
        │  Antigravity to bypass   │            │    authority             │
        └───────────▲──────────────┘            └────────────┬────────────┘
                    │ Report + evidence                       │ Files changed +
                    │ for independent review                  │ tests performed
                    │                                          ▼
        ┌───────────┴──────────────────────────────────────────┐
        │                     ANTIGRAVITY                       │
        │  4. Audit the actual implementation (not just Gemma's │
        │     report): correctness, test sufficiency, security  │
        │     boundaries, UI/backend parity, portability;       │
        │     fix bounded problems; rerun affected tests.        │
        │  6. Commit + push ONLY after Claude says VERIFIED.     │
        │  Never declares a milestone VERIFIED itself.           │
        └─────────────────────────────────────────────────────┘

        Reserve / fallback only (never part of the normal cycle):
        QWEN 3 14B — explicit second-opinion invocation only.
        CODEX (CLI) — explicit large-mechanical-refactor invocation only.
```

### 1.1 The Normal Cycle (authoritative sequence)

1. **CLAUDE** inspects the verified current repository state, creates a
   fresh milestone plan/recommendation, defines implementation scope,
   acceptance criteria, tests, security considerations, and UI impact
   (`UI IMPACT: NONE` or `UI IMPACT: REQUIRED`, §1.4), persists the plan, and
   waits for USER ACCEPT / MODIFY. State: `DRAFT`.
2. **USER** accepts the plan as written, or modifies it. No implementation
   begins before acceptance. State on accept: `ACCEPTED`.
3. **GEMMA 4 12B** implements the accepted milestone — backend and UI when
   the plan requires UI work — following the exact accepted scope, using the
   qualified Gemma configuration. Gemma has no Git authority and no
   architectural authority: it implements what was accepted, it does not
   redesign it. Gemma reports files changed and tests performed. State:
   `IMPLEMENTING`.
4. **ANTIGRAVITY** inspects the actual implementation, not only Gemma's
   report: audits code correctness, audits whether tests are actually
   correct and sufficient, runs the relevant tests, audits security
   boundaries, audits UI/backend parity, audits portability implications
   where applicable, fixes bounded problems when required, reruns affected
   tests, and performs additional self-tests only when evidence requires
   them. Antigravity produces a persistent implementation/audit/result
   report. Antigravity must **not** declare the milestone `VERIFIED` if
   required evidence is missing. States: `AUDITING`, then `FIXING` if fixes
   are applied, then back to `AUDITING`/`VERIFYING`.
5. **CLAUDE** independently reviews Antigravity's report and evidence,
   verifies the accepted plan was actually satisfied, verifies the tests and
   fixes are credible, reviews remaining findings and UI status, and decides
   `VERIFIED` / `NOT VERIFIED`. State: `VERIFYING` → `VERIFIED` (or back to
   `FIXING`/`BLOCKED` if not verified).
6. **RELEASE** — only after Claude says `VERIFIED`: Antigravity commits,
   pushes, and stops. State: `COMPLETE`.
7. **NEXT CYCLE** — Claude reviews the newly committed milestone and its
   findings and creates a **fresh** plan for the next milestone; it does not
   simply repeat the previous plan. Returns to step 1, state `DRAFT`.

### 1.2 Role Definitions

| Role | Entity | Primary Responsibilities | Strict Constraints |
|---|---|---|---|
| **Final Authority** | **User** | ACCEPT/MODIFY every plan before implementation; consequential architecture decisions; security policies; irreversible actions; resolving agent conflicts; sole authority to release after Claude's `VERIFIED`. | Non-delegable. No AI can override. |
| **Planner & Final Verifier** | **Claude Code** (CLI) | Fresh milestone planning from verified repo state (scope, acceptance criteria, tests, security considerations, UI impact); independent final review of Antigravity's audit/fixes; `VERIFIED`/`NOT VERIFIED` decision. | Plans only from verified state, never from an unverified prior claim. Does not implement the milestone it plans. Cannot be bypassed for either the plan-acceptance gate or the verification gate. |
| **Implementer** | **Gemma 4 12B** | Implements exactly the accepted plan's scope — backend and UI when the plan requires UI work — using the qualified Gemma configuration; reports files changed and tests performed. | No Git authority. No architectural authority — implements the accepted plan, does not redesign it. Must not expand scope beyond what was accepted. |
| **Control Surface, Auditor & Fixer** | **Antigravity** (Gemini 3.8 Flash) | Independently audits the actual implementation (correctness, test sufficiency, security boundaries, UI/backend parity, portability); fixes bounded problems; reruns affected tests; produces the persistent audit/result report; commits and pushes only after Claude's `VERIFIED`. | Must inspect real code and real test runs, not just Gemma's report. Must never declare `VERIFIED` itself. Must never commit/push before Claude's `VERIFIED`. |
| **Reserve / Fallback (not in normal cycle)** | **Qwen 3 14B** (Local Ollama) | Explicit second-opinion review, only when the User separately invokes it. | Zero authority in the normal cycle. Never silently substituted in for Claude or Antigravity. |
| **Reserve / Fallback (not in normal cycle)** | **Codex** (CLI) | Explicit large-mechanical-refactor invocation, only when the User separately invokes it. | Zero authority in the normal cycle. Never silently substituted in for Gemma. |

### 1.3 Continuity Rules

The cycle must not be broken by temporary model failure, agent
unavailability, network problems, or quota exhaustion. **Waiting is a valid
state.** Specifically:

- **Never silently substitute an agent or transfer authority.** No worker may
  assume another worker's role (e.g. Antigravity may not plan a fresh
  milestone; Gemma may not audit its own work; Qwen may not silently replace
  Claude's verification) even temporarily.
- **If Gemma is unavailable:** preserve state at `ACCEPTED` or wherever
  implementation stopped, and either wait (`WORKER_FAILED` or
  `WAITING_FOR_QUOTA`, as applicable) or use explicitly recorded fallback
  handling if the User has pre-authorized one for this milestone. Do not
  reassign the implementation to Antigravity or Codex without the User
  explicitly saying so for that instance.
- **If Antigravity is unavailable:** do not bypass its audit gate. An
  implementation that has not been through Antigravity's audit cannot reach
  `VERIFYING`. State: `WAITING_FOR_ANTIGRAVITY`.
- **If Claude is unavailable or quota is exhausted:** an already-`ACCEPTED`
  plan may continue through `IMPLEMENTING` (Gemma) and `AUDITING`/`FIXING`
  (Antigravity) — that work is not blocked. But no fresh strategic plan is
  invented by any other agent, and no milestone reaches `VERIFIED` without
  Claude. State: `WAITING_FOR_CLAUDE`, holding at `AUDITING`/`VERIFYING`
  until Claude returns. On return, Claude resumes from the preserved state
  (`READY_TO_RESUME`), not from scratch.

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
(Gemma implements backend and UI together, under the same accepted plan), and
Antigravity's audit (step 4) must explicitly include UI/backend parity
verification before the milestone can reach `VERIFYING`. A milestone plan
that touches backend contracts a UI consumes (auth fields, roles, new
endpoints, response shapes) must not declare `UI IMPACT: NONE` merely because
implementing the UI side was deferred — deferral is a plan decision Claude
must state explicitly, not an implicit consequence of the declaration.

---

## 2. Active Coordination Loop

Development follows the fixed cycle in §1.1: Claude plans, the User gates
acceptance, Gemma implements, Antigravity audits/fixes, Claude gives final
verification, and only then does release happen.

```
                          USER MILESTONE REQUEST
                               ↓
                 CLAUDE — INSPECT VERIFIED STATE, DRAFT PLAN
                 (scope, acceptance criteria, tests, security,
                  UI IMPACT: NONE|REQUIRED)  →  state: DRAFT
                               ↓
                 USER — ACCEPT / MODIFY  →  state: ACCEPTED
                               ↓
                 GEMMA 4 12B — IMPLEMENT ACCEPTED SCOPE
                 (backend + UI when required; no Git; no
                  architectural authority)  →  state: IMPLEMENTING
                               ↓
                 ANTIGRAVITY — AUDIT ACTUAL IMPLEMENTATION
                 (correctness, test sufficiency, security boundaries,
                  UI/backend parity, portability; fix bounded issues;
                  rerun tests)  →  state: AUDITING / FIXING
                               ↓
                 CLAUDE — INDEPENDENT FINAL REVIEW
                 (plan satisfied? tests/fixes credible? gaps
                  accurately classified?)  →  state: VERIFYING
                               ↓
                        VERIFIED?  ── NO ──► back to FIXING / BLOCKED
                               │
                              YES
                               ↓
                 ANTIGRAVITY — COMMIT + PUSH  →  state: COMPLETE
                               ↓
                 CLAUDE — REVIEW COMMITTED STATE, DRAFT FRESH
                 NEXT-MILESTONE PLAN (not a repeat)  →  state: DRAFT
```

1. **Claude plans:** inspects verified repo state, drafts a fresh milestone
   plan (scope, acceptance criteria, tests, security considerations, UI
   impact per §1.4), and persists it.
2. **User gates:** accepts the plan as written or modifies it; nothing is
   implemented before this gate.
3. **Gemma implements:** builds exactly the accepted scope, backend and UI
   together when the plan requires UI work, and reports files changed and
   tests performed.
4. **Antigravity audits:** independently inspects the real implementation
   (not only Gemma's report), fixes bounded problems, reruns affected tests,
   and produces a persistent audit/result report. Antigravity never declares
   `VERIFIED`.
5. **Claude verifies:** independently reviews Antigravity's report and
   evidence, checks plan satisfaction, test/fix credibility, and gap
   classification, and issues `VERIFIED` / `NOT VERIFIED`.
6. **Release:** only after `VERIFIED`, Antigravity commits and pushes, then
   stops.
7. **Next cycle:** Claude reviews the newly committed milestone and its
   findings and drafts a fresh plan for the next milestone — never a repeat
   of the previous one.

Qwen and Codex do not appear in this loop; they are invoked only per §1.1's
reserve/fallback note, on explicit User instruction.

---

## 3. Coordination State Model

The development process operates under a persistent, resumable state
machine. States are durable — a milestone's current state must be
recoverable after an interruption, not re-derived from scratch. Claude and
Antigravity each own the transitions in their stage (§1.1); the User owns
the accept/modify and release gates.

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
  WAITING_FOR_ANTIGRAVITY, READY_TO_RESUME
```

| State | Description | Entered when | Exit |
|---|---|---|---|
| `DRAFT` | Claude has drafted a fresh milestone plan and persisted it. | Start of a cycle, or after `COMPLETE`. | User reviews and accepts/modifies. |
| `ACCEPTED` | User has accepted the plan (as written, or as modified). | User gate passed. | Gemma begins implementation. |
| `IMPLEMENTING` | Gemma is implementing the accepted scope. | After `ACCEPTED`. | Gemma reports files changed and tests performed. |
| `AUDITING` | Antigravity is inspecting the actual implementation. | After `IMPLEMENTING`, or after a `FIXING` pass. | Antigravity's audit report is produced. |
| `FIXING` | Antigravity is applying bounded fixes found during audit. | Audit finds a fixable problem. | Returns to `AUDITING` to re-verify the fix, then reruns affected tests. |
| `VERIFYING` | Claude is independently reviewing Antigravity's report and evidence. | After `AUDITING` completes with no outstanding fixes. | Claude issues `VERIFIED` or sends back to `FIXING`/`BLOCKED`. |
| `VERIFIED` | Claude has confirmed the plan was satisfied with credible evidence. | Claude's explicit decision. | Antigravity releases. |
| `COMPLETE` | Commit and push are done; milestone closed. | After release. | Claude starts the next cycle at `DRAFT`. |
| `BLOCKED` | A genuine blocker exists that no agent in the cycle can resolve alone (e.g. an unresolved plan ambiguity, a real regression with no bounded fix). | Any stage, when progress cannot continue safely. | User intervention. |
| `WORKER_FAILED` | Gemma or Antigravity failed to complete its stage (crash, tool failure, non-recoverable error). | During `IMPLEMENTING`, `AUDITING`, or `FIXING`. | Retry, or User-authorized explicit fallback for that instance only. |
| `WAITING_FOR_QUOTA` | A required agent has hit a quota/rate limit. | Any stage. | Resumes automatically once quota is available, or User intervenes. |
| `WAITING_FOR_CLAUDE` | Claude is unavailable or quota-exhausted; an already-`ACCEPTED` plan continues through `IMPLEMENTING`/`AUDITING`/`FIXING`, but nothing reaches `VERIFIED` and no fresh plan is drafted. | Claude unavailable while a plan is already `ACCEPTED`. | Claude returns and resumes verification from preserved state. |
| `WAITING_FOR_ANTIGRAVITY` | Antigravity is unavailable; its audit gate is never bypassed. | Implementation complete but no audit possible. | Antigravity returns and audits. |
| `READY_TO_RESUME` | A returning agent (most often Claude after `WAITING_FOR_CLAUDE`) has the preserved state and evidence in hand and can resume exactly where the cycle left off. | Whenever a waiting state's blocking condition clears. | Resumes the specific in-flight stage — never restarts the cycle from `DRAFT` unless the stage was `DRAFT` itself. |

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

At §1.1 step 5, Claude reviews Antigravity's audit report and the actual
implementation evidence (test logs, diffs — not summaries alone) and issues
one of:
- `VERIFIED` — the accepted plan's acceptance criteria are satisfied with
  credible evidence, gaps are accurately classified as deferred/accepted,
  and no protected boundary was crossed.
- `NOT VERIFIED` — with the specific unmet criterion, missing evidence, or
  regression named, returning the cycle to `FIXING` (bounded issues) or
  `BLOCKED` (issues requiring User input).

*Rule:* Neither Gemma nor Antigravity may declare a milestone `VERIFIED`;
only Claude does, and only from real evidence it has independently examined.

---

## 5. Antigravity Audit, Fix & Release Responsibilities

Antigravity is the independent auditor, bounded fixer, and release control
surface. Antigravity retains **exclusive authority** over:

1. **Implementation Audit:** Inspecting the actual code Gemma produced —
   correctness, test sufficiency (not just test presence), security
   boundaries, UI/backend parity, and portability implications — never
   accepting Gemma's report as a substitute for inspection.
2. **Shell & Tool Execution:** Running terminal commands, Python
   interpreters, Flutter tools, and test suites to independently verify
   Gemma's claimed results.
3. **Bounded Fixes:** Applying fixes for problems found during audit that
   are within the accepted plan's scope, then rerunning affected tests. A
   fix that would require expanding scope beyond the accepted plan is
   escalated to `BLOCKED` for Claude/User, not applied unilaterally.
4. **Audit Reporting:** Producing the persistent implementation/audit/result
   report Claude reviews at step 5. Antigravity must not declare
   `VERIFIED` if required evidence is missing — it hands the gap to Claude
   instead of papering over it.
5. **Version Control Authority:** Staging, committing, tagging, and pushing
   git changes — but **only after Claude has said `VERIFIED`**. Committing
   or pushing before that gate is a process violation regardless of how
   confident Antigravity's own audit was.
6. **Circuit Breakers:** Aborting Gemma's execution immediately if it
   attempts unauthorized architectural changes, scope expansion, or
   destructive operations.

---

## 6. Worker Delegation & Escalation Rules

### 6.1 Gemma 4 12B Implementation (the normal-cycle implementer)
- Implements exactly the scope accepted at §1.1 step 2 — backend and, when
  `UI IMPACT: REQUIRED`, the corresponding `uri_ui/` work in the same
  milestone.
- Writes or updates the tests the accepted plan calls for.
- Has no Git authority and no architectural authority: it does not decide
  scope, does not redesign the accepted plan, and does not commit.
- Reports files changed and tests performed back to Antigravity for audit.

### 6.2 Antigravity Direct Fixes (bounded, audit-driven only)
- Antigravity may make small, bounded corrections discovered during its
  audit (§5.3) — it is not a second implementer for new scope.
- Documentation, tracking, and project memory maintenance after a verified
  release.

### 6.3 Reserve / Fallback Delegation (explicit invocation only, never default)
- **Codex (CLI):** substantial multi-file mechanical refactors, only when
  the User explicitly invokes it for that instance; it does not
  automatically absorb Gemma's role if Gemma is unavailable (§1.3).
- **Qwen 3 14B (Local Ollama):** an explicit second-opinion review, only
  when the User separately requests it; it does not replace Claude's
  planning or verification role under any circumstance.

### 6.4 Claude Code — Not a Delegation Target, a Fixed Stage
Claude's planning (step 1) and final verification (step 5) are not
discretionary escalations chosen by another worker; they are mandatory
stages of every milestone (§1.1). Nothing in this document authorizes
skipping either stage, regardless of how routine a milestone appears.

### 6.5 User Escalation (Final Authority)
Any worker **MUST escalate to the User** for:
- Changes to governing documents (`ADR-018`, `URI_AI_OPERATING_POLICY.md`,
  `URI_MODEL_RUNTIME_CONTRACT.md`).
- Modifications to security policies or approval gate relaxation.
- Breaking changes to persistence, wire APIs, or user data isolation.
- Irreversible destructive actions.
- Unresolved disagreements between the plan and the implementation, or
  between Antigravity's audit and Claude's verification.
- Milestone start, pause, `BLOCKED` resolution, or plan modification.

---

## 7. Qwen 3 14B Qualification Record (Reserve / Fallback Role Only)

This record is retained as historical qualification evidence for Qwen's
**reserve/fallback** role (§1.1, §6.3) — an explicit, User-invoked second
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

### 10.1 Plan Handoff (Claude → User → Gemma)
Claude's persisted Milestone Plan (§4.2) is the Task Brief for the normal
cycle — there is no separate coordinator-drafted brief. Once the User
accepts (or modifies) it, the accepted plan's Scope, Out-of-Scope/Protected
Files, Acceptance Criteria, Test Plan, and UI Impact sections are handed to
Gemma unchanged.

### 10.2 Implementer Return Report (Gemma → Antigravity)
Gemma reports back in this format:

```markdown
### GEMMA RETURN REPORT
- **Milestone ID:** [Matching the accepted plan]
- **Summary of Actions:** [What was performed]
- **Files Modified/Created:** [List with line-count delta]
- **Tests Performed:** [Exact test commands and pass/fail counts, as run]
- **Assumptions & Decisions:** [Any design choices made during implementation, within accepted scope]
- **Known Issues / Gaps:** [Remaining items or unverified edges]
```

### 10.3 Audit/Result Report (Antigravity → Claude)
Antigravity's persistent report, produced before Claude's final review
(§1.1 step 5), must include:

```markdown
### ANTIGRAVITY AUDIT REPORT
- **Milestone ID:** [Matching the accepted plan]
- **Code Correctness Findings:** [What was inspected, what was found]
- **Test Sufficiency Assessment:** [Do the tests actually cover the claimed behavior, not just pass]
- **Security Boundary Check:** [Result against the plan's security considerations]
- **UI/Backend Parity Check:** [Required whenever UI IMPACT: REQUIRED]
- **Portability Implications:** [When applicable]
- **Fixes Applied:** [Bounded fixes made, and the rerun test results for each]
- **Evidence:** [Actual test run output/counts — not a restated claim]
- **Outstanding Gaps:** [Named explicitly; never omitted to make the report look clean]
```
Antigravity must not mark a milestone `VERIFIED` in this report — that
decision belongs solely to Claude (§4.3).

### 10.4 Persistent State File (handoff artifact, not a coordinator)

Each milestone plan (`docs/plans/<ID>_..._PLAN.md`) has a sibling
`docs/plans/<ID>_STATE.md` file, created by Claude at `ACCEPTED` (§1.1
step 2) and updated in place by whichever worker owns the current
stage. It carries: the current state (§3's vocabulary), an append-only
History Log of transitions, and the §10.2/§10.3 report templates for
Gemma and Antigravity to fill in directly. Its purpose is narrow: the
cycle must be resumable from **disk**, not from any one agent's
conversation history, so a session restart, quota exhaustion, or
model unavailability never loses evidence or forces the cycle to
restart from `DRAFT`. This file is a state record only — it has no
authority of its own, drives no execution, and is not a substitute for,
or a competitor to, `scripts/qwen_coordinator.py`'s proposal-schema
mechanism (which remains Qwen-reserve-only, §1.3) or any future
implementer-driver tooling. It is development-only tracking and is
never read by, or shipped inside, the URI runtime itself.
