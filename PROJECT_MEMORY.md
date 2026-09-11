# URI Project Memory

## Resume point

- **Completed baseline:** M22.4, commit *this commit* (11 Sep 2026),
  independently verified by Claude Code as third-layer reviewer, with
  **1,241/1,241 backend tests passing** and **106/106 Flutter tests
  passing** at delivery. See
  [URI_MILESTONE_TRACKER.md](URI_MILESTONE_TRACKER.md)'s M22.4 row for the
  full verification record.
- **Next milestone:** M22.5 — Provider registry and encrypted key storage.
  Follow [URI_M22_ARCHITECTURE.md](URI_M22_ARCHITECTURE.md); do not
  restart M22/M22.1/M22.2/M22.3/M22.4 audits.

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

## Development Operating Model (AO-4: Claude-Planned / Gemma-Implemented / Antigravity-Audited Cycle)

- **Final Authority:** User — accepts/modifies every plan; sole release authority after Claude's `VERIFIED`.
- **Planner & Final Verifier:** Claude Code (CLI) — plans each milestone from verified state; issues `VERIFIED`/`NOT VERIFIED`.
- **Implementer:** Gemma 4 12B — implements exactly the accepted plan, backend and UI together when required. No Git or architectural authority.
- **Auditor, Fixer & Release Control:** Antigravity (Gemini 3.8 Flash) — audits the actual implementation, fixes bounded problems, reruns tests, commits/pushes only after Claude's `VERIFIED`.
- **Reserve/fallback only (not the normal cycle):** Qwen 3 14B (Local Ollama) — explicit second opinion on User request. Codex (CLI) — explicit large mechanical refactors on User request.
- **Excluded:** Gemma 3 (superseded by the qualified Gemma 4 12B above; not part of the active development team).
- **Operating Specification:** [ORCHESTRATION.md](ORCHESTRATION.md) §1 (7-step cycle, state model, continuity rules).

### Coordinator Qualification Record (10 Sep 2026)
- **Model:** `qwen3:14b` (14.8B parameters, Q4_K_M, local Ollama)
- **Status:** **QUALIFIED WITH LIMITATIONS** (Score: 4.55 / 5.0)
- **Strengths:** Task triage (5/5), delegation accuracy (5/5), security escalation (5/5), authority separation, worker-result review (5/5), change-aware auditing (5/5), conflict handling (4/5).
- **Known Limitations & Operational Mitigations:**
  - *Negative Exclusion Blindspot:* Can fail to recall negative constraints when not in immediate context. *Mitigation:* Antigravity must deliberately assemble and inject negative constraints (prohibited work, deferred features, protected files) as first-class context in every coordinator prompt.
  - *Context Capacity Bounds:* Cannot ingest 60KB+ documents in one turn. *Mitigation:* Antigravity slices specific milestone sections before prompting Qwen.
  - *Turn Latency:* Observed ~16–38s per turn due to internal reasoning tokens. *Mitigation:* Use Qwen for batched milestone/task coordination turns rather than conversational back-and-forth.


