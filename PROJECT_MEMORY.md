# URI Project Memory

## Resume point

- **M33.1 — Real Integrations / Acquire & Manage Abilities:** **CLOSED /
  ACCEPTED** (2026-09-20). Batches 1–3 retain their accepted commits
  (`d78366d`/`0558a99`, `dd4863a`, `0fcdf29`); Batch 4 closes the materially
  distinct extension matrix and the opt-in natural-language `/ask` lifecycle
  seam. Independent closure review: 35/35 isolated Batch 2–4 lifecycle/live
  tests passed; recovered-tree full regression 2,175 passed / 23 failed / 7
  skipped / 40 subtests versus clean `5973f6d` baseline 2,165 / 15 / 7 / 40.
  Fourteen failures overlapped; seven external DNS/npm/yt-dlp failures passed
  on isolated rerun; two Drive tests are environment-sensitive and outside
  Batch 4 paths. No bounded fix required. `URI_ENABLE_LIFECYCLE_INTENT_SEAM=1`
  remains opt-in; M33.3 graphical lifecycle management remains out of scope.
  Do not double-count arbitrary `SKILL.md` prose as a distinct mechanism, and
  do not start or absorb M33.2 implementation. Full record:
  `docs/plans/M33_1_REAL_INTEGRATIONS_EXTENSION_VALIDATION_PLAN.md` §13.H.

- **M33.2 — Edge / Second Brain Foundation: CLOSED / VERIFIED** (final
  closure review, 2026-09-20, Claude independent audit of the complete
  Batch A -> B -> B.1 -> B.2 -> B.3 -> B.4 chain against primary evidence,
  fresh 60/60 regression reconfirmed this session). Final state: Edge/
  Second Brain remains optional and provider-agnostic; URI deterministic
  authority remains the sole execution boundary (confirmed by
  `test_edge_has_no_static_authority_or_execution_imports` and
  `test_authority_modules_do_not_read_edge_preference`); **Needle 3** is
  the only qualified `RESIDENT` worker, scope-limited to reflex tool
  routing and structured extraction — its 50% normalized-argument-
  extraction rate means it is explicitly **not** trusted for unrestricted
  argument extraction, which must stay an untrusted, validated proposal;
  **SmolLM2-135M-Instruct** and **Qwen2.5-0.5B-Instruct** are both
  `BYPASS / REDUNDANT` (stronger already-installed Main Brains
  `qwen3.5:9b`/`gemma4:12b` materially outperform the 0.5B reasoner and
  correctly bypass it); **STT/OCR/VLM** remain truthfully `UNQUALIFIED /
  UNAVAILABLE`; the B.3 user-space model/runtime lifecycle infrastructure
  (`uri_core/core/edge_lifecycle/`) is accepted; zero-egress Edge Core is
  intact (lifecycle code deliberately kept outside `uri_core/core/edge/`
  to avoid weakening the existing zero-egress AST tests); `installed !=
  resident != qualified` holds as a real distinction, not merely
  asserted, across this chain. No Batch C was opened — no direct evidence
  of a missing contractual requirement from the original four-stage
  package was found. Full item-by-item evidence trail: the "M33.2 — Edge
  / Second Brain Foundation — FINAL CLOSURE" entry in
  `docs/governance/URI_ACTIVE_MILESTONE.md`. Batch-level records remain at
  `docs/plans/M33_2_BATCH_{A,B,B1,B2,B3,B4}_STATE.md` and their sibling
  completion reports.

- **ARN — Adaptive Retrieval Narrowing & Task Recovery:** parent plan
  accepted; **Batch ARN.1 — Deterministic Narrowing Core is
  `CLOSED / VERIFIED`** (2026-09-20, independent final audit by Gemini per
  direct User instruction). Codex implemented the deterministic task-local
  state/evidence taxonomy, candidate and repeated-search tracking, cost
  ceilings and genuine terminal states, optional Turn State projection, and the
  canonical first-`NOT_FOUND` recovery seam. Independently reproduced evidence:
  10/10 focused ARN.1 passed, 60/60 predecessor M33.2 passed, 130/130
  relevant dispatch/decision/Turn State/orchestrator recovery tests plus 13
  subtests passed, and full regression 2,259 passed, 16 failed (all 16 verified
  historical baseline/environmental, zero ARN.1 regressions). ARN milestone is
  now PAUSED after ARN.1. Do NOT start ARN.2. Next authorized direction:
  **Resume M31 Hybrid UI after ARN.1 closure**. See
  `docs/plans/ARN_1_COMPLETION_REPORT.md` and
  `docs/plans/ARN_1_STATE.md`.

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
- **Permanent Acceptance Rule & Four-Stage Lifecycle (12 Sep 2026):** Every new add-on, capability, connector, integration, memory, graph, model, workflow, UI-to-backend feature, or extension must follow the 4-stage lifecycle (Audit → Architecture → Migration → Validation). A feature is not DONE merely because code exists or unit tests pass; it is complete only when the Brain can discover and use it through URI's canonical agent loop, execution results feed back into reasoning, and behavior is live-verified end-to-end. See [URI Four-Stage Development Lifecycle](docs/governance/URI_FOUR_STAGE_DEVELOPMENT_LIFECYCLE.md).

## References

- [AGENTS.md](AGENTS.md) for universal agent working rules.
- [ORCHESTRATION.md](ORCHESTRATION.md) for multi-agent roles, delegation, and workflow rules.
- [URI Four-Stage Development Lifecycle](docs/governance/URI_FOUR_STAGE_DEVELOPMENT_LIFECYCLE.md) for mandatory feature development lifecycle and permanent acceptance rule.
- [URI_MILESTONE_TRACKER.md](URI_MILESTONE_TRACKER.md) for delivery history.
- [URI_M22_ARCHITECTURE.md](URI_M22_ARCHITECTURE.md) for M22 design and plan.
- `URI_Model_Centric_Architecture_Docs/` for governing architecture, policy,
  and model/runtime contract.

## UI-Initiative Role Override (2026-09-16)

For the URI Hybrid UI implementation initiative only (until the User changes
it again): Claude/Codex are planning and independent-plan-review only;
Antigravity is primary implementer; Qwen 3 14B is implementation reviewer;
Antigravity performs repair of Qwen's findings. The AO-4 model below remains
the record for all other/prior milestones. See
[ORCHESTRATION.md](ORCHESTRATION.md) §0, [AGENTS.md](AGENTS.md) item 7, and
`docs/plans/UI_HYBRID_FROZEN_BLUEPRINT.md` for the full detail, including
mandatory sequencing behind M31.

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
