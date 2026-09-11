# URI Project Memory

## Resume point

- **Completed baseline:** M23 — URI-native Graph Intelligence foundation
  (commit `dfee5a8`), implemented directly by Claude under explicit User
  authorization (no Antigravity/Codex/Gemma session reachable) and
  self-audited — see
  [the state and verification report](docs/plans/M23_STATE.md), including
  two design mistakes and one standing "orchestrator.py must never grow"
  rule violation this same session found and corrected before commit. Full
  regression 1,401/1,401 tests run with the same single pre-existing,
  unrelated failure as the pre-M23 baseline (confirmed via `git stash`
  bisection, not assumed); `wc -l orchestrator.py` exactly flat at 5,460;
  `uri_ui/` untouched. Adds a per-user SQLite-backed structured
  entity/relationship graph (`GraphStore`), six bounded read-only
  traversal primitives, and one new optional `graph_context` section in
  `query_context.py` — context/evidence for the Brain, proven (not merely
  documented) to be non-authoritative. M22.9 (commit `9c848fe`) remains
  the prior baseline — PWA/mobile client branding and durable session
  handling; **its acceptance criterion 4 (hands-on device-install
  confirmation) is still outstanding**, needs the User directly. This
  closes the full M22.1–M22.9 sequence
  (`URI_M22_ARCHITECTURE.md` §22's dependency graph).
- **Next milestone:** none yet — the User will provide the next milestone
  directly. Standing role separation resumes: Claude plans/audits/
  releases, Codex/Gemma implement, unless the User grants an explicit
  one-instance exception again (as for M22.8/M22.9/M23). Do not restart
  M22/M22.1–M22.9 or M23 audits.
- **Standing governance change (11 Sep 2026, permanent):** all future
  milestone plans are auto-approved by default — Claude no longer waits for
  explicit User ACCEPT/MODIFY on routine engineering work; the User is
  interrupted only for decisions that would materially change URI's core
  structure, product identity, security/authority model, or another
  constitutional boundary. A companion permanent quota-exhaustion invariant
  requires Antigravity to place the loop into a durable, resumable
  `WAITING_FOR_MODEL` state (never `BLOCKED`, never a failed task) on
  temporary Claude/Codex unavailability. Both are implemented and tested in
  `scripts/dev_workflow/state_machine.py`/`state_manager.py`
  (`tests/dev_workflow/test_workflow.py`) and specified in full in
  [ORCHESTRATION.md](ORCHESTRATION.md) §1.5 and §3.1.

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
