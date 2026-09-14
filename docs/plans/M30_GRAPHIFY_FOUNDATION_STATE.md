# Graphify Foundation - State

**Plan:** `docs/plans/M30_GRAPHIFY_FOUNDATION_PLAN.md`

STATE: CLAUDE ACCEPT (2026-09-14) - implemented exactly as planned,
verified against real tests and real live startup behavior. See the
2026-09-14 history entry below.

## Governance

Precondition of `docs/plans/M30_8_CANONICAL_CUTOVER_LEGACY_RETIREMENT_
PLAN.md`'s Phase A. Independent of, and does not reopen, the completed
M30 readiness work (M30-PFC, Scenario 2/8/12 closures, Scenario 7
mechanism proof) - see that plan's §0. M30.8 (revised) remains NOT
AUTHORIZED, NOT started.

## History Log

- 2026-09-14: Following the User's own M30 readiness ACCEPTED
  conclusion, the User issued a new architectural direction: a
  lightweight Graphify foundation must exist as startup infrastructure
  before canonical default authority is enabled, plus a generic
  Startup Services lifecycle so it is not a one-off startup exception.
  Explicit instruction: planning only, do not implement; first inspect
  the existing Graphify/M23 implementation, Turn State, Capability
  Directory, startup/bootstrap path, memory hooks, and legacy decision
  authorities.

  Claude audited `graph_store.py`/`graph_engine.py`/`graph_ingest.py`/
  `graph_context.py`/`graph_schema.py` (M23, `VERIFIED`, real and
  sound - confirmed via `M23_STATE.md`'s own final verification
  report) and found it scoped only to per-user facts/memory, with no
  startup lifecycle at all (each per-user store is built lazily on
  first request) and only one hardcoded startup call in `server.py`'s
  `_lifespan()` (`_initialize_user_scoped_stores()` - not a registry,
  a single direct call). `turn_state.py` already has an unused
  `graph_context` field, confirming the intended consumption point
  already exists; only the broader system-level source and its wiring
  are missing.

  Produced `M30_GRAPHIFY_FOUNDATION_PLAN.md`: a new, additive, system-
  level index (separate from M23's own per-user graph, which is
  unchanged) mapping capabilities/skills/workflows/memory-pointers/
  entities/dependencies/availability/provenance/source-locations, each
  field sourced from an already-existing, already-generic mechanism
  (`CapabilityDirectory`, `SkillMemory`, `WorkflowPlanner`,
  `MemoryStore`, `Capability.check_availability()`,
  `capability_relevance.py`'s existing scorer for relevance-filtering)
  - no new parallel source of truth invented anywhere. Designed a
  small, generic `StartupService` protocol + runner
  (`startup_services.py`) so `_lifespan()` calls a list, not a
  hardcoded function, with today's one existing call becoming the
  first registered service. 9 required tests specified (not yet
  written), 6 acceptance criteria defined as the hard gate before
  Plan B's Phase A may begin. No production code written by Claude.
  Marked ACCEPTED under the standing auto-approval rule for the
  planning work itself; **implementation is a separate authorization
  the User has not yet given.**

- 2026-09-14: User approved Plan A only for implementation, and
  directed re-establishing the autonomous loop shape (Claude →
  Antigravity relay/monitoring → Claude verification/self-audit →
  bounded repair if needed → final verdict → WAITING_FOR_USER_
  DECISION), with Antigravity remaining coordinator-only. **Mechanical
  note, stated plainly:** no Codex/Antigravity session was reachable
  from this Claude Code session (structural fact, unchanged since
  every prior instance this session - M23, M30-PFC, Scenario 2) -
  Claude implemented directly, consistent with this session's own
  established exception pattern, while writing the full relay/
  monitoring/verdict record below so the intended loop shape is
  genuinely reflected in the governance files for Antigravity to
  pick up and maintain going forward for future milestones.

  **Implementation, exactly per plan:**
  - `uri_core/core/startup_services.py` (new) - `StartupService`
    protocol + `run_startup_services()`.
  - `uri_core/core/graphify_index.py` (new) - `GraphifyIndex`,
    `build_index`/`refresh`/`load_index`/`save_index`, each category
    builder (`_index_capabilities`/`_index_skills`/`_index_workflows`/
    `_index_memory_pointers`) sourced from real, already-generic
    authorities only.
  - `uri_core/app/server.py` - `_lifespan()` refactored to
    `run_startup_services([_UserScopedStoreInitializer(),
    _GraphifyIndexLoader()])`; `_initialize_user_scoped_stores()`'s own
    behavior is unchanged, now wrapped rather than called directly;
    new `_graphify_index` global (default empty).
  - `uri_core/core/turn_state.py` - one new optional, additive
    `capability_index_hint` field.

  **Verification:**
  - 37/37 new/updated tests passing (`test_graphify_index.py` 15,
    `test_startup_services.py` 3, `test_turn_state.py`'s 1 new test +
    18 pre-existing, all green).
  - **Live verification, not merely unit-tested:** a real
    `TestClient(app)` startup (real `_lifespan` execution) built a
    real, non-empty index from the real, live system - 71 records (16
    capabilities, 53 skills, 1 workflow, 1 memory pointer), including a
    fully correct real `Gmail` entry (real dependencies/availability/
    pointer, `available: true`, matching the real connected test
    account). Confirmed the persisted file round-trips (a second
    startup loaded the marker-tagged file from disk rather than
    rebuilding). **Confirmed resilience directly**, not merely
    asserted: with a deliberately corrupted `graphify_index.json`
    present, a fresh startup quarantined it (`.corrupted`, never
    deleted), rebuilt a fresh 71-record index, and a real login +
    real `/ask` call both succeeded normally (`200`/`success`) -
    concrete proof of "URI must still work if Graphify is stale,
    empty, rebuilding, or unavailable."
  - Full regression (5 batches, due to real, disclosed system memory
    pressure - same discipline as prior rounds): 1,768 total items, 8
    pre-existing failures (exact, name-for-name baseline match), 0 new
    failures, 27 subtests passing.

  **Self-audit against the plan's 6 acceptance criteria: all hold.**
  (1) Startup Services lifecycle generic and proven
  (`test_startup_services.py`, `_initialize_user_scoped_stores()`
  behavior unchanged). (2) Startup load/incremental-refresh/safe-
  degrade all proven, unit and live. (3) Index correctly maps every
  required category from real, already-generic sources - no second
  source of truth. (4) Non-authoritative by construction
  (`GraphifyAuthorityBoundaryTests`, AST-based, mirrors M23's own
  proof exactly). (5) Turn State additive-only, Brain receives only a
  small relevance-filtered subset (`relevant_subset()`, reuses
  `capability_relevance.py`, never the whole index). (6) Zero
  regression.

  **Self-audit verdict: ACCEPT.** No production code outside the
  plan's own approved scope was touched (confirmed via `git status`:
  only `startup_services.py`, `graphify_index.py`, `server.py`,
  `turn_state.py`, and the new/updated test files). M30.8 (revised)
  remains NOT AUTHORIZED and NOT started, per the User's explicit
  instruction.

## Release gate

Per the 2026-09-12 live-verification-gate revision and this session's
standing AO-4 discipline: implementation against this plan requires
its own separate, explicit User authorization. Once implemented,
Claude independently re-audits against real test-suite results and
this plan's own 6 acceptance criteria before treating the foundation
as closed and unblocking Plan B's Phase A.
