# URI Project Memory

## Resume point

- **Completed baseline:** M22.7 usage metering, budgets, and pre-flight
  ceiling enforcement, implemented by Codex against the accepted
  [plan](docs/plans/M22.7_USAGE_METERING_PLAN.md), independently verified by
  Claude Code (11 Sep 2026) — see the
  [state and verification report](docs/plans/M22.7_STATE.md). All 11
  acceptance criteria independently traced against source; full regression
  suite **1,433/1,433 Python tests passing, 29 subtests passing, 0 failures**
  (reproduced from scratch after Claude's bounded fix to a pre-existing M22.6
  test-fixture isolation gap unrelated to M22.7's own changes — see the
  report for the root-cause trace). M22.6 (`5b97e12`) and M22.7 both verified
  and released this session.
- **Next milestone:** M22.8 — Modes and tiered UX (office/diagnostic/admin
  capability filters, BASIC/ADVANCED provider UI, ceiling-reached flow).
  Depends on M22.4 and M22.7, both complete. Follow
  [URI_M22_ARCHITECTURE.md](URI_M22_ARCHITECTURE.md); do not
  restart M22/M22.1/M22.2/M22.3/M22.4/M22.5 audits.

## Guardrails

- Preserve the model-centric architecture: the model proposes; the runtime
  controls authority, approval, execution, persistence, and audit.
- M22.4 CapabilityResolver/per-user grants, M22.5 provider/secrets,
  Developer Mode, and the five deferred diagnostic-GET endpoints (M22.3
  Decision 1) remain deferred.
- M22.3 closed S1 (unauthenticated mutating endpoints) and S5 (unlimited
  auth attempts); remote/mobile security readiness still requires M22.4's
  per-user capability authority before it can be claimed.

## References

- [AGENTS.md](AGENTS.md) for universal agent working rules.
- [ORCHESTRATION.md](ORCHESTRATION.md) for multi-agent roles, delegation, and workflow rules.
- [URI_MILESTONE_TRACKER.md](URI_MILESTONE_TRACKER.md) for delivery history.
- [URI_M22_ARCHITECTURE.md](URI_M22_ARCHITECTURE.md) for M22 design and plan.
- `URI_Model_Centric_Architecture_Docs/` for governing architecture, policy,
  and model/runtime contract.

## Development Operating Model (AO-4: Claude-Planned / Codex-or-Gemma-Implemented / Claude-Verified-and-Released Cycle)

- **Final Authority:** User — accepts/modifies every plan; non-delegable authority over architecture and security policy.
- **Architect, Final Auditor, Bounded Fixer & Release Authority:** Claude Code (CLI) — plans each milestone from verified state; independently audits the actual implementation; directly fixes bounded in-scope defects (`audit → fix → re-audit`); for substantial remediation, defines the requirement and hands it to Antigravity for Codex/Gemma routing; sole authority for `VERIFIED`/`NOT VERIFIED` and for `git commit`/`git push`.
- **Loop Manager / Orchestrator:** Antigravity (Gemini 3.8 Flash) — initiates tasks, routes implementation to Codex or Gemma per complexity, packages evidence for Claude's audit, implements UI/response work only where specifically assigned. Not an auditor; never declares `VERIFIED`; no commit/push authority.
- **Preferred Specialist Implementer:** Codex (CLI) — standing routed worker (not reserve/fallback) for complex, multi-file, security-sensitive, and production-call-path implementation, per Claude's accepted plan.
- **Local Bounded Implementation Worker:** Gemma 4 12B — small bounded tasks, focused edits, boilerplate, and focused test creation. No Git or architectural authority.
- **Reserve/fallback only (not the normal cycle):** Qwen 3 14B (Local Ollama) — explicit second opinion on User request only.
- **Excluded:** Gemma 3 (superseded by the qualified Gemma 4 12B above; not part of the active development team).
- **Operating Specification:** [ORCHESTRATION.md](ORCHESTRATION.md) §1 (authoritative cycle, state model, continuity rules).

### Coordinator Qualification Record (10 Sep 2026)
- **Model:** `qwen3:14b` (14.8B parameters, Q4_K_M, local Ollama)
- **Status:** **QUALIFIED WITH LIMITATIONS** (Score: 4.55 / 5.0)
- **Strengths:** Task triage (5/5), delegation accuracy (5/5), security escalation (5/5), authority separation, worker-result review (5/5), change-aware auditing (5/5), conflict handling (4/5).
- **Known Limitations & Operational Mitigations:**
  - *Negative Exclusion Blindspot:* Can fail to recall negative constraints when not in immediate context. *Mitigation:* Antigravity must deliberately assemble and inject negative constraints (prohibited work, deferred features, protected files) as first-class context in every coordinator prompt.
  - *Context Capacity Bounds:* Cannot ingest 60KB+ documents in one turn. *Mitigation:* Antigravity slices specific milestone sections before prompting Qwen.
  - *Turn Latency:* Observed ~16–38s per turn due to internal reasoning tokens. *Mitigation:* Use Qwen for batched milestone/task coordination turns rather than conversational back-and-forth.
