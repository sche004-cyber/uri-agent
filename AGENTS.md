# URI Agent Guide

Start from the documented baseline; do not repeat completed architecture or
security audits merely to resume work.

## Current state

- The completed baseline is M22.2 at commit `34839ce`; its delivery record is
  1,141/1,141 tests passing.
- The next milestone is **M22.3: endpoint authorization and route
  classification**. Its scope and acceptance criteria are in
  [URI_M22_ARCHITECTURE.md](URI_M22_ARCHITECTURE.md).
- Uncommitted `uri_ui` Windows/platform work is active and unverified. It is
  not a milestone and must not be represented as one until scoped, verified,
  and committed.

## Governing documents

Read these before changing architecture, authority, model behaviour, or
milestone status:

1. [ADR-018](URI_Model_Centric_Architecture_Docs/URI_ADR_018_MODEL_CENTRIC_ARCHITECTURE.md)
   — model-centric intelligence and lightweight deterministic runtime.
2. [URI AI Operating Policy](URI_Model_Centric_Architecture_Docs/URI_AI_OPERATING_POLICY.md)
   — identity, behaviour, and non-negotiable safeguards.
3. [Model ↔ Runtime Contract](URI_Model_Centric_Architecture_Docs/URI_MODEL_RUNTIME_CONTRACT.md)
   — untrusted model proposals and runtime authority.
4. [URI M22 Architecture](URI_M22_ARCHITECTURE.md) — M22 sequence, security
   findings, dependencies, and deferred work.
5. [Milestone Tracker](URI_MILESTONE_TRACKER.md) and
   [Project Memory](PROJECT_MEMORY.md) — current delivery state and handoff.
6. [Multi-Agent Orchestration Architecture](ORCHESTRATION.md)
   — canonical AO-4 agent team roles, coordination loop, and workflow rules.

Do not duplicate or weaken these documents in implementation notes.

## Canonical Development Team (AO-4) — Authoritative Process

The development operating model follows the authoritative cycle established by the User (see [ORCHESTRATION.md](ORCHESTRATION.md) for the full detail this summary condenses):

1. **Claude (CLI):** Architect / Pre-Auditor / Final Auditor / Bounded Fixer / Release Authority.
   - Plans and pre-audits each next milestone before implementation.
   - Performs the independent final audit of the implementation, tracing actual production paths rather than trusting a worker's report.
   - If Claude finds a **bounded** defect within accepted scope, Claude fixes it directly, then independently re-audits (`audit → fix → re-audit`). Does not hand NOT VERIFIED findings back to Gemma/Codex by default.
   - If a defect requires **substantial** remediation, Claude defines the requirement and hands it to Antigravity for Codex/Gemma routing — Claude does not perform substantial implementation itself merely because it holds bounded-fix authority, and never silently expands an accepted milestone's scope while fixing something.
   - Once independently VERIFIED, Claude alone performs `git commit` and `git push` to `origin/master`.
   - Immediately plans and pre-audits the next milestone; the workflow does not stop merely because a milestone was pushed.
2. **Antigravity (Gemini 3.8 Flash):** Development Loop Manager / Orchestrator.
   - Manages execution of the accepted milestone: initiates tasks, prepares precise task-initiation packages, and invokes the appropriate worker (Claude, Codex, Gemma, or a specialist agent) as the workflow requires.
   - Routes implementation to Codex (preferred for complex/multi-file/security-sensitive/production-call-path work) or Gemma (bounded/small/repetitive/boilerplate work).
   - Sends task-initiation prompts to Gemma/Codex and packages evidence for Claude's audit.
   - Implements UI, UX-facing behavior, and URI response/reply interface work only where specifically assigned.
   - Coordinates agents, maintains milestone state, and ensures the next valid workflow stage is actually initiated.
   - **Is NOT the formal auditor/verifier.** Must not declare VERIFIED, must not replace Claude's independent verification, and must not commit or push a milestone release.
3. **Codex (CLI):** Preferred Specialist Coder / Implementer.
   - The preferred implementation worker for complex implementation, multi-file work, architectural implementation, security-sensitive work, persistence/integration work, difficult debugging, precision-critical changes, repository-wide reasoning, and production call-path changes.
   - Implements against the accepted Claude plan (or a Claude-defined remediation requirement).
   - Does not approve its own implementation, declare VERIFIED, redefine accepted architecture, commit, or push.
4. **Gemma 4 12B (local, via Ollama/MCP):** Local Bounded Implementation Worker.
   - Used primarily for small bounded implementation tasks, focused edits, repetitive work, boilerplate, focused test creation, and low-risk tasks that comfortably fit its context/capabilities.
   - Do not force complex implementation through Gemma when Codex is the more appropriate implementation worker.
   - No Git authority; no final release audit.
5. **Specialist / Design Agents:** Advisory only — may propose architecture improvements, UI/UX, interface layouts, and URI response/reply presentation/interaction-workflow improvements. Do not implement. Where a proposal materially affects architecture or milestone behavior, Claude reviews it before it becomes implementation guidance.
6. **User:** Final Authority. Accepts/modifies every milestone plan; non-delegable authority over architecture and security policy. Release itself is performed solely by Claude (item 1), not by the User directly.

### Standing Development Cycle
```
CLAUDE PLANS → CLAUDE PRE-AUDITS → USER ACCEPTS → ANTIGRAVITY INITIATES TASKS (ROUTES TO CODEX OR GEMMA PER COMPLEXITY) → CODEX/GEMMA IMPLEMENTS → ANTIGRAVITY MANAGES UI/RESPONSE WORK WHERE ASSIGNED → ANTIGRAVITY SENDS RELEVANT EVIDENCE TO CLAUDE → CLAUDE AUDITS → [BOUNDED DEFECT: CLAUDE FIXES DIRECTLY → CLAUDE RE-AUDITS] OR [SUBSTANTIAL DEFECT: CLAUDE DEFINES REMEDIATION → ANTIGRAVITY ROUTES TO CODEX/GEMMA → CLAUDE RE-AUDITS] → VERIFIED → CLAUDE COMMITS/PUSHES → CLAUDE PLANS NEXT MILESTONE → USER ACCEPTS → REPEAT
```


## Non-negotiable boundaries

- The model may reason and propose; the runtime validates, authorizes,
  approves, executes, persists, audits, and reports.
- Preserve the propose → validate → approve → execute chain across both URI runtime behavior and development orchestration. Coordinator and model outputs are untrusted proposals and cannot grant capability, approval, or execution authority.
- Keep deterministic runtime controls focused on safety, authority, state
  integrity, and execution; do not replace model reasoning with task-specific
  hard-coded logic.
- Keep user data isolated. `experience_tier` is UX-only and must never become
  an authorization input.
- Do not treat a route as safe merely because a caller is authenticated:
  route classification and role enforcement are M22.3's explicit work.
- In prompt context assembly for the coordinator, Antigravity must explicitly inject negative constraints (prohibited features, deferred work, protected files) as first-class context to prevent scope drift.

## Working practice

- Inspect only the files necessary for the assigned scope. Preserve unrelated
  dirty-worktree changes.
- Do not modify application code or tests during documentation-only work.
- For an implementation milestone, make the smallest coherent change, add or
  update the milestone's required tests, and run proportionate verification.
- Record a milestone as complete only after its specified verification and
  commit checkpoint. Do not use uncommitted work as evidence of completion.
- Update the tracker and project memory when a milestone changes state; link
  to governing documents instead of copying architecture into them.

