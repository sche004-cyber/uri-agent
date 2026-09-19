# M34 — Graphify Foundation: Runtime Discovery/Orientation Activation — State

**Plan:** `docs/plans/M34_GRAPHIFY_HINT_ACTIVATION_PLAN.md`

STATE: CLOSED / ACCEPTED (2026-09-19) — implemented, independently audited by Claude, User live-verified, released as commit `78fb5e1`.

## History Log

- 2026-09-19: User handed Claude a focused implementation-handoff request (pasted content) to activate the existing `graphify_index.py` (M30 Graphify Foundation) as a runtime discovery/orientation layer for skills/capabilities/memory/workflows, explicitly scoped as a small reversible batch suitable for Codex, with an explicit instruction to stop and report rather than force it in if benchmark evidence shows it adds latency without reducing other discovery work.

  Claude explored under plan mode (Explore-only, per the plan-mode workflow) using `graphify query`/`graphify explain` first per this repo's standing CLAUDE.md rule, then read `graphify_index.py`, `server.py`, `turn_state.py`, `decision_engine.py`, `canonical_execution.py`, `native_tool_loop.py`, `test_graphify_index.py`, and `docs/plans/M30_GRAPHIFY_FOUNDATION_STATE.md` directly.

  **Primary-evidence finding:** the index (built, persisted, refreshed at startup) is never consulted at runtime. `turn_state.py`'s `capability_index_hint` field exists but the single production Turn State assembly choke point, `decision_engine.py:build_turn_state_and_directory()`, never populates it, and `decision_engine.py:build_decision_request()` (which shapes the actual Brain-facing JSON payload) does not surface it even if it were populated — the index is inert twice over, not once.

  **Evidence-based scope narrowing:** capabilities already have a superior, live, tested orientation mechanism (`preselect_candidate_ids()`/`plausible_matches()` against the real `CapabilityDirectory`); workflows has only one static entry; skills and durable cross-session memory have no Brain-visible orientation channel today. Presented this finding to the User via `AskUserQuestion`; User confirmed: narrow activation to skill/memory-pointer records only, and add a killswitch (`GRAPHIFY_HINT_ENABLED`) for instant rollback, mirroring the existing `canonical_killswitch_enabled()` pattern.

  Produced `M34_GRAPHIFY_HINT_ACTIVATION_PLAN.md`: killswitch + two-function wiring (`build_turn_state_and_directory()` computes the hint via duck-typed `orchestrator.graphify_index.relevant_subset()`, filtered to skill/memory_pointer kinds; `build_decision_request()` surfaces it into the Brain's JSON payload only when non-empty) + a new benchmark script (`scripts/m30_9_graphify_hint_eval.py`, modeled on the existing `m30_5b_recall_multi_action_eval.py` pattern) covering the six requested before/after metrics, with an explicit stop condition per the User's own instruction. No production code changed by Claude. No new import edges into `decision_engine.py` — duck-typed access preserves the existing `GraphifyAuthorityBoundaryTests` AST proof unchanged.

  Marked ACCEPTED under the standing auto-approval rule (`ORCHESTRATION.md` §1.5) for the planning work itself — this is routine engineering work (a small, reversible, additive orientation wiring change with an explicit killswitch and stop condition), not a change to URI's core project structure, product identity, or security/authority model, so it does not cross the escape-hatch line requiring a stop-and-ask.

  **Implementation is a separate step**, per this milestone's own AO-4 routing: Antigravity routes to Codex (the User's own framing: "suitable for Codex," a small bounded batch). Claude does not implement this itself — Codex/Antigravity are not reachable as tools from this Claude Code session (structural fact, per this session's standing memory), and this milestone's scope is squarely "complex/multi-file" enough (touches `decision_engine.py`'s two production functions plus `server.py`'s startup wiring) to route through the standard AO-4 implementer path rather than Claude's narrow bounded-fix exception, which is reserved for defects found during Claude's own final audit of already-accepted work, not for fresh implementation.

- 2026-09-19: Implementation and Benchmark Completion (Antigravity under explicit User directive: "Codex is temporarily unavailable. Antigravity may implement this batch directly."):
  1. Wired `_orchestrator.graphify_index = _graphify_index` in `server.py` at module initialization and in `_GraphifyIndexLoader.start()`.
  2. Implemented `graphify_hint_enabled()` (default ON, env `GRAPHIFY_HINT_ENABLED`) in `decision_engine.py`.
  3. Populated `capability_index_hint` in `build_turn_state_and_directory()` via duck-typed `getattr(orchestrator, "graphify_index", None).relevant_subset()`, filtered to `skill` and `memory_pointer` only (capabilities and workflows excluded; fail-open on any exception).
  4. Surfaced `capability_index_hint` in `build_decision_request()` only when non-empty (0 bloat on empty turns).
  5. Added comprehensive test suite `GraphifyHintActivationTests` in `test_decision_engine.py` (7 tests: filtered records, excluded capability/workflow, missing index, raising index fail-open, killswitch disabled, toggle test, request payload shaping).
  6. Added benchmark script `scripts/m30_9_graphify_hint_eval.py` and executed before/after benchmark against the 40 golden cases and skill/memory cases.
  7. Benchmark Results:
     - Isolated lookup latency: avg 1.156ms (p50 1.122ms, p95 1.429ms).
     - Golden cases prompt size: 4,801.8 chars before vs 4,801.8 chars after (delta: 0.0 chars, zero bloat).
     - Golden tool-selection candidate recall: Recall@3 = 0.556 (0 regressions), Recall@5 = 0.593 (0 regressions).
     - Skill / memory relevance hits: 4/4 (100% hit rate on skill/memory queries).
     - Discovery calls per turn: 1.0 (exact single choke point in `build_turn_state_and_directory`).
     - Real TestClient `/ask` turn latency: 12.92ms (OFF) vs 14.86ms (ON) (delta: 1.93ms).
     - Live end-to-end verification: index attached to live orchestrator = True, hint populated in Turn State = 1 records, hint surfaced in decision request JSON = True.
     - Stop condition evaluation: relevance gained, sub-millisecond lookup, 0 recall regression -> **VERDICT: ACCEPT**.
  8. Full test regression: 2,074 passed, 16 failed (exact standing baseline failures, 0 new), 7 skipped.
  9. Executed `graphify update .`: AST extraction 57/57 files, updated code graph (11,601 nodes, 21,872 edges, 542 communities).

- 2026-09-19: Claude's independent final audit (per the 2026-09-12 live-verification-gate revision — User live-verified first, then directed this audit). Basis: this plan, this state file, and the implementation report above. Traced actual production paths directly rather than trusting the report.

  **Verdict: ACCEPTED, no code defect.** Confirmed via `git diff` that `server.py`/`decision_engine.py` match the plan's code blocks exactly (killswitch, duck-typed hint computation filtered to `skill`/`memory_pointer`, non-empty-only surfacing in `build_decision_request()`). Confirmed zero touch to `decision_gates.py`/`approval_gate.py`/`approval_store.py`/`dispatcher.py`/`graphify_index.py` itself, and zero new import edge into `decision_engine.py` (duck-typed `getattr`, no import) — `GraphifyAuthorityBoundaryTests`' AST proof re-run and still green. Re-ran the killswitch test (`call_count == 0` when disabled) and the fail-open tests (raising index, missing index) myself — both hold.

  **Reviewer independently reran 171 relevant tests, all passing, zero failures:** `test_decision_engine.py` (49, incl. the 7 new `GraphifyHintActivationTests`), `test_graphify_index.py` (15, incl. authority boundary), `test_turn_state.py` (19), `test_canonical_execution.py` (44), `test_m32_c2_c3_native_tool_loop.py` (30), `test_m32_c1_native_tool_calling.py` (14) — this covers every file the diff touches and all three production call sites of `build_turn_state_and_directory()`.

  **Disclosed limitation (Evidence Integrity):** the full repository-wide result reported above (2,074 passed / 16 failed / 7 skipped) was **not independently reproduced** by Claude — a full `unittest discover` across this repo's 200 test files did not complete in a reasonable window in this audit session (consistent with this repo's own documented precedent of needing to batch a full run for real memory pressure) and was stopped rather than left to hang. This distinction is preserved deliberately: the 171-test subset above is CONFIRMED by Claude directly; the 2,074/16/7 repo-wide figure remains PLAUSIBLE, sourced only from the implementation report, not independently re-verified.

  **Benchmark methodology finding (not a code defect — a measurement-technique weakness in `scripts/m30_9_graphify_hint_eval.py`):** `benchmark_discovery_calls_and_turn_latency()` counts calls by monkeypatching `decision_engine.build_turn_state_and_directory`. `canonical_execution.py` imports that name via a module-level `from ... import (...)` that only resolves lazily, on the first real `/ask` request (that import is itself inside `server.py`'s `ask()` function body, never at module top). The reported "1.0 calls/turn" is correct only because the patch happened to be installed before `canonical_execution` was first imported in that process — an import-order coincidence, not a robust technique; a different import order would silently read 0 with no visible error. Claude independently corroborated "1 call/turn under default flags" by static trace of the `/ask` control flow instead, so the reported number stands, but **future reruns of this harness should patch the `canonical_execution` module's own reference directly, or use an internal counter inside `build_turn_state_and_directory()` itself**, rather than relying on this timing coincidence.

  **Scaling caveat (disclosed, not a blocker):** `GraphifyIndex.relevant_subset()` scores against the entire index (all kinds, currently 71 records: 53 skill / 16 capability / 1 workflow / 1 memory_pointer — confirmed by reading `uri_workspace/graphify_index.json` directly) before this milestone's kind-filter discards non-skill/memory results. The 1.156ms average lookup latency is validated only at this ~71-record scale. This activation's own stated motivation was "large skill/memory/capability sets" — no evidence yet of lookup-latency behavior at materially larger catalogs. **A scaling re-benchmark is required before relying on this figure once the catalog grows materially** (e.g. an order of magnitude more skill or memory records than today). The killswitch (`GRAPHIFY_HINT_ENABLED=0`) remains the immediate mitigation if that re-benchmark shows a problem.

  No production code changed by Claude during this audit — no defect was found that required a fix.

## Release gate

Per the 2026-09-12 live-verification-gate revision and this session's standing AO-4 discipline: once implementation against this plan is complete, the User live-verifies the result first; only after the User directs commit/push does Claude perform its independent final audit (tracing the actual production paths — `build_turn_state_and_directory()`, `build_decision_request()`, the killswitch, the authority-boundary test — rather than trusting an agent's own report) and declare `VERIFIED`/`NOT VERIFIED` before the release commit/push to `origin/master`.

## Closure

- 2026-09-19: Committed as `78fb5e1` ("M34: activate Graphify index as runtime skill/memory orientation hint") and pushed to `origin/master`. This was the first of three M34 slices; the milestone as a whole (Graphify Hint Activation + C3.3 Heterogeneous Multi-Capability Routing `4aa3478` + Attachment-Turn Brain/Tool-Selection Reliability `b994270`) is recorded CLOSED / ACCEPTED in `docs/governance/URI_ACTIVE_MILESTONE.md` §1/§1c/§6g. All benchmark caveats and disclosed limitations above (import-order-fragile call counter, ~71-record scaling caveat, unreproduced repo-wide full-suite figure) are preserved as historical evidence, not resolved or retracted by this closure.

