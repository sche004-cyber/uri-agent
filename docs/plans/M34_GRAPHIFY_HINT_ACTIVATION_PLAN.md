# M34 — Graphify Foundation: Runtime Discovery/Orientation Activation

**State:** `docs/plans/M34_GRAPHIFY_HINT_ACTIVATION_STATE.md`

## Context

`graphify_index.py` (M30 Graphify Foundation, `docs/plans/M30_GRAPHIFY_FOUNDATION_PLAN.md`, state `CLAUDE ACCEPT`) already builds, persists, and incrementally refreshes a system-level index of capabilities, skills, workflows, and memory pointers, and already exposes `GraphifyIndex.relevant_subset(goal_text, limit=5)` — a small, relevance-filtered lookup reusing the same tested scorer (`capability_relevance.plausible_matches`) used elsewhere in the decision path. It is fully built at startup (`server.py`'s `_GraphifyIndexLoader`) and covered by 15 passing tests.

**Primary-evidence finding (verified by reading the actual call graph, not assumed):** the index is built and then never consulted again. `turn_state.py`'s `capability_index_hint` field exists and is documented as additive-only, but the single production entry point that assembles Turn State — `decision_engine.py:build_turn_state_and_directory()` (called from `canonical_execution.py`, `native_tool_loop.py`, and `decision_engine.py`'s own shadow path — three production call sites, one choke point) — never passes it. Worse, even if it were populated, `decision_engine.py:build_decision_request()` (the function that shapes the literal JSON payload the Brain reads) explicitly whitelists which Turn State keys reach the model, and `capability_index_hint` (along with `graph_context` and `durable_memory_relevant`, both out of scope here) is not among them. So today the index is inert twice over: never computed per turn, and even if it were, never rendered into the Brain's prompt.

**Evidence-based scope narrowing (confirmed with the User during planning):** of the four categories the index covers,
- **capabilities** already have a superior, live, tested orientation mechanism (`preselect_candidate_ids()` → `plausible_matches()` against the real `CapabilityDirectory`, already wired into `build_decision_request()`'s `preselected_ids`). Adding graphify's capability records here would be a second, redundant path over the same data.
- **workflows** currently has exactly one static template entry — not a "large set" problem.
- **skills** (`SkillMemory.list_skills()`) and **durable memory** (`MemoryStore.list_all()`) have a genuine gap: the only skill-side runtime mechanism is `orchestrator.py`'s `skill_memory.find_matching_skill()`, a silent deterministic pre-Brain short-circuit with no Brain-visible catalog awareness, and the only memory the Brain currently sees is `session_facts` (current-session disclosures only, via `turn_state.py:_project_session_facts()`) — durable cross-session memory pointers never reach the Brain's prompt at all.

This milestone therefore activates the index **for skill and memory-pointer orientation only**, per the User's decision. This is a small, additive, fully reversible change (a killswitch plus two functions), not a redesign of discovery architecture, and it removes nothing.

## Approach

### 1. Killswitch (reversibility)

Add one module-level flag in `decision_engine.py`, mirroring the existing `canonical_killswitch_enabled()`/`decision_engine_live_enabled()` pattern in `canonical_execution.py`:

```python
def graphify_hint_enabled() -> bool:
    return os.environ.get("GRAPHIFY_HINT_ENABLED", "1") != "0"
```

Default on. Setting `GRAPHIFY_HINT_ENABLED=0` disables the lookup instantly, no redeploy, no code change — the rest of the pipeline (Turn State assembly, prompt shaping) already tolerates an absent/empty hint since the field is additive-only and already tested that way (`test_turn_state.py::test_capability_index_hint_is_additive_only`).

### 2. Attach the index to the orchestrator (server.py)

`_graphify_index` currently lives only as a module-level global in `server.py`, read by nothing after startup. Add one line so the orchestrator — the object every production call site already threads through — can reach it without any new import edge into `decision_engine.py`:

- At `_graphify_index = GraphifyIndex()` (server.py:217), also set `_orchestrator.graphify_index = _graphify_index`.
- In `_GraphifyIndexLoader.start()` (server.py:726-758), after `_graphify_index = index`, also set `_orchestrator.graphify_index = index`.

This mirrors the existing `_orchestrator.graph_store = _graph_store` wiring pattern already used for M23's graph store one block above.

### 3. Compute the hint per turn (decision_engine.py: `build_turn_state_and_directory`)

Inside `build_turn_state_and_directory()` (decision_engine.py:941), before calling `assemble_turn_state`:

```python
capability_index_hint = None
if graphify_hint_enabled():
    graphify_index = getattr(orchestrator, "graphify_index", None)
    if graphify_index is not None:
        try:
            subset = graphify_index.relevant_subset(user_text, limit=5)
            capability_index_hint = [
                r for r in subset if r.get("kind") in ("skill", "memory_pointer")
            ] or None
        except Exception:
            capability_index_hint = None
```

Pass `capability_index_hint=capability_index_hint` into the `assemble_turn_state(...)` call. This is duck-typed (`getattr`, no `isinstance`, no import of `graphify_index.py`'s types) — `decision_engine.py` gains zero new import edges, so the existing `GraphifyAuthorityBoundaryTests` AST proof in `test_graphify_index.py` (graphify_index.py must never be imported by authority-bearing modules) stays trivially satisfied and does not need modification. The try/except matches this function's own existing fail-open discipline (every other collaborator read in this codebase degrades to `None`/empty on failure, never raises).

Because `build_turn_state_and_directory()` is the one choke point all three call sites already share, this activates the hint everywhere Turn State is built — no per-call-site duplication.

### 4. Surface the hint into the Brain's actual prompt (decision_engine.py: `build_decision_request`)

`build_decision_request()` (decision_engine.py:404-462) is what actually becomes the JSON string the model reads. Add, only when non-empty (avoid bloating every turn with an empty key):

```python
hint = turn_state_data.get("capability_index_hint")
if hint:
    request["capability_index_hint"] = hint
```

This keeps the field's existing name (schema-compatible with the already-shipped Turn State contract) while now only ever containing skill/memory orientation pointers per the scope decision above — never a copy of the real skill/memory content, only the same `{id, kind, summary, pointer}` shape `graphify_index.py` already produces, consistent with its "pointers only, never authoritative" module docstring.

### 5. What does not change

- `graphify_index.py` itself: untouched. No new builder, no new scope, no schema change.
- `turn_state.py`: untouched — the `capability_index_hint` kwarg and its additive-only contract already exist and are already tested.
- No registries removed: `SkillMemory`, `MemoryStore`, `CapabilityDirectory`, `skill_memory.find_matching_skill()` all continue exactly as today. This is a second, non-authoritative orientation channel layered on top, not a replacement.
- No change to `decision_gates.py`, `approval_gate.py`, `approval_store.py`, `canonical_execution.py`'s own imports, or any authorization/execution boundary.

## Benchmark (before/after, per the task's explicit requirement)

Add `scripts/m30_9_graphify_hint_eval.py`, modeled on the existing `scripts/m30_5b_recall_multi_action_eval.py` / `scripts/m30_4_decision_quality_analysis.py:turn_state_for()` pattern (reuse the existing golden-case harness rather than inventing a new one). Measure, with the killswitch flipped both ways on the same golden case set:

1. **Lookup latency** — wall-clock of `graphify_index.relevant_subset()` alone, in isolation.
2. **Prompt/tool-schema size** — `len(json.dumps(build_decision_request(...)))` before vs after.
3. **Discovery/index calls per turn** — instrument (or log-count) how many times `build_turn_state_and_directory()` actually runs for one real `/ask` request (canonical vs shadow path) — resolve empirically rather than assumed, since `canonical_killswitch_enabled()`/`decision_engine_live_enabled()` gate which paths run live.
4. **Tool-selection accuracy** — rerun the existing `evaluate_against_golden()`/`candidate_recall_at_k()` golden suite unchanged; must show zero regression (this change must not alter capability selection at all, since capabilities are explicitly out of scope).
5. **Memory lookup relevance** — for golden cases that reference a durable fact, check whether the correct `memory:<id>` pointer now appears in `capability_index_hint`.
6. **Total turn latency** — real `TestClient(app)` `/ask` call, wall-clock, killswitch on vs off.

**Explicit stop condition (per the task):** if this shows added latency (per turn or lookup) without a measurable gain in memory/skill relevance or discovery-call reduction, do not enable by default — set `GRAPHIFY_HINT_ENABLED=0` as the shipped default, document the finding in this milestone's STATE file, and stop rather than forcing it in.

## Tests to add

- `test_decision_engine.py`: `build_turn_state_and_directory()` populates `capability_index_hint` from `orchestrator.graphify_index.relevant_subset()`, filtered to `skill`/`memory_pointer` kinds only (capability/workflow records excluded even if `relevant_subset()` returns them); `None`/missing `orchestrator.graphify_index` → `None` hint, never raises; a raising `graphify_index.relevant_subset()` → `None` hint, never raises (fail-open); `GRAPHIFY_HINT_ENABLED=0` → `relevant_subset()` never called (mock/spy assertion).
- `test_decision_engine.py`: `build_decision_request()` includes `capability_index_hint` in the output dict only when non-empty; omits the key entirely when empty/`None` (no bloat).
- Full regression: `test_graphify_index.py`, `test_turn_state.py`, `test_decision_engine.py`, `test_canonical_execution.py`, and the full suite (this repo's existing baseline-diff discipline — compare failure count/names before vs after, not just "0 new failures" without a baseline).

## Verification (required before Claude's final audit/VERIFIED verdict)

1. Unit tests above pass.
2. Full regression suite: 0 new failures vs the pre-change baseline (name-for-name comparison, per this repo's standing discipline).
3. Live verification: a real `TestClient(app)` startup + `/ask` call where the user references a durable memory fact or a previously-learned skill, confirming `capability_index_hint` is non-empty in the assembled Turn State and appears in the JSON `build_decision_request()` produces — not just unit-mocked.
4. Run `scripts/m30_9_graphify_hint_eval.py` and record the six benchmark numbers above in this milestone's STATE file, with an explicit ACCEPT/stop verdict per the stop condition.
5. `graphify update .` after implementation, per this repo's standing CLAUDE.md rule.

## Implementation routing (AO-4)

Small, bounded, reversible batch — two functions in `decision_engine.py`, two lines in `server.py`, one new eval script, no new architecture. Suitable for Codex per the User's own framing of this task. Per standing AO-4 roles (2026-09-11 revision), Antigravity routes this to Codex; Claude performs the final independent audit once the User has live-verified the result and directs commit/push (2026-09-12 live-verification-gate revision).
