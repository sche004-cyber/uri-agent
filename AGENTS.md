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

## Canonical Development Team (AO-4)

The development operating model is a fixed cycle, not a discretionary
coordination loop: Claude plans, the User gates acceptance, Gemma
implements, Antigravity audits/fixes and controls release, Claude gives
final verification. See [ORCHESTRATION.md](ORCHESTRATION.md) §1 for the full
7-step cycle, state model, and continuity rules.

- **User:** Final authority. Accepts or modifies every milestone plan before
  implementation begins; sole authority to release after Claude's
  `VERIFIED`; final authority for architecture decisions, security policies,
  and gate relaxation.
- **Claude Code (CLI):** Plans every milestone from verified repo state
  (scope, acceptance criteria, tests, security considerations, UI impact)
  and performs the independent final verification (`VERIFIED`/`NOT
  VERIFIED`) after Antigravity's audit. Does not implement.
- **Gemma 4 12B:** The normal-cycle implementer. Builds exactly the accepted
  plan's scope — backend and UI together when the plan requires UI work. No
  Git authority, no architectural authority.
- **Antigravity (Gemini 3.8 Flash):** Independently audits Gemma's actual
  implementation (not just its report), fixes bounded problems, reruns
  tests, and controls commit/push — but only after Claude's `VERIFIED`.
  Never declares a milestone verified itself.
- **Qwen 3 14B (Local Ollama):** Reserve/fallback only — an explicit,
  User-invoked second opinion. Not part of the normal cycle.
- **Codex (CLI):** Reserve/fallback only — explicit, User-invoked large
  mechanical refactors. Not part of the normal cycle.
- **Gemma 3:** Excluded from the active development team (superseded by the
  qualified Gemma 4 12B above).

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

