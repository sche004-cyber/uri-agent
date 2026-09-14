# Graphify Foundation - Pre-Cutover Plan (Read-Only, NOT Implemented)

STATE: ACCEPTED (plan only) - implementation NOT yet performed, per
the User's explicit "Do NOT implement... Return both plans for User
review before implementation." Claude (Architect/Planner) output per
the standing AO-4 development cycle. **No production source was
modified to produce this document.** Sibling state file:
`docs/plans/M30_GRAPHIFY_FOUNDATION_STATE.md`. Companion plan:
`docs/plans/M30_8_CANONICAL_CUTOVER_LEGACY_RETIREMENT_PLAN.md` (Plan
B) - this plan (Plan A) is a hard precondition of that one's Phase A.

**Product decision this plan implements (User, 2026-09-14):** before
canonical default authority is enabled, URI must have a lightweight
Graphify foundation available as startup infrastructure - "URI's
cognitive index and GPS." Read-only/informational only. No planning,
execution, approval, or authorization authority. Not the full future
Graphify vision - a compact map of capabilities, skills, workflows,
memory pointers, entities, dependencies, connected/runtime
availability, provenance, and authoritative source locations. Loads
persisted index at startup, supports incremental refresh, preserves
pointers rather than duplicating source content, provides only the
small relevant context subset to the Brain. A reusable Startup
Services category/lifecycle, not a one-off startup exception.

---

## 0. What already exists - inspected directly, not assumed

**M23 Graph Intelligence is real, `VERIFIED`, and structurally sound -
this plan extends it, never replaces it.** Confirmed by direct source
reading and `docs/plans/M23_STATE.md`'s own final verification report:

- `uri_core/core/graph_store.py` - SQLite-backed (stdlib, zero new
  dependency), per-user, dedup by `external_ref`/derived id, type-
  validated, credential-value-rejecting, corrupted-file-quarantining.
- `uri_core/core/graph_engine.py` - six bounded read-only primitives
  (`graph_get_entity`, `graph_query`, `graph_neighbors`, `graph_path`,
  `graph_explain`, `graph_impact`) plus `graph_self_context()`, already
  the orchestrator's one call site (via `query_context.py`'s optional
  `graph_context` key). Bounded BFS, hard-clamped `max_hops`, `limit`-
  capped lists, `ACTIVE`-only by default.
- `uri_core/core/graph_ingest.py` - `ingest_fact` (VERIFIED-only),
  `ingest_memory_entry` (consent-eligible only, re-checks
  `is_eligible_for_personalization` itself), `ingest_user_account`.
- `uri_core/core/graph_context.py` - `build_graph_context()`, pure
  assembly, degrades to all-empty.
- `uri_core/config/graph_schema.py` - extensible entity/relationship
  type registry (`GraphTypeRegistry`, install-scope, JSON-persisted).
- Six read-only `/graph/*` routes, classified `USER`, self-scoped
  (cross-user access independently proven to 404, not merely assumed).
- **Independently proven non-authoritative**, not merely documented:
  an AST-based test (`test_graph_authority_boundary.py`) proves
  `dispatcher.py`/`approval_gate.py`/`approval_store.py`/
  `capability_registry.py`/`capability_resolver.py` import no `graph_*`
  module, and the `graph_*` modules import none of `model_providers`/
  `model_router`/`dispatcher`/`approval_gate`/`approval_store`.

**What M23 does NOT do today - the real gap this plan closes:**

1. **Scope.** M23 only ingests per-user `Fact`/`MemoryEntry` records -
   it has no concept of capabilities, skills, workflows, dependencies,
   or connection/runtime availability at all. The User's desired map
   (capabilities/skills/workflows/memory pointers/entities/
   dependencies/connected-runtime-availability/provenance/authoritative
   source locations) is materially broader than M23's current ingestion
   surface.
2. **Lifecycle.** There is no startup-time loading of any kind. Each
   per-user `GraphStore` is constructed lazily, on first request, via
   `_get_user_context()` (`server.py`) - never eagerly at process
   start, and never incrementally refreshed on any schedule.
3. **Wiring is dormant, confirmed by direct reading, not assumed.**
   `Fact.verify()` has no live caller anywhere in the current runtime
   (`M23_STATE.md`'s own disclosed gap, re-confirmed here); only
   `MemoryStore.confirm()`'s existing `user_provided`/`user_confirmed`
   path feeds `ingest_memory_entry` today. The graph is real
   infrastructure, structurally sound, but almost empty in practice.
4. **No generic startup-services pattern exists to hang new startup
   work off of.** `uri_core/app/server.py`'s `_lifespan()` (the FastAPI
   lifespan handler, the only place "real application startup" work
   runs, per its own docstring) calls exactly one hardcoded function,
   `_initialize_user_scoped_stores()` - not a list, not a registry, a
   single direct call. Every future startup need (this plan's own
   index load included) would otherwise become a second hardcoded
   one-off in the same spot, which is exactly the pattern the User's
   own instruction says to avoid.

---

## A. Graphify Foundation design

### A.1 Scope - a system-level index, additive to M23's per-user graph

**New: a system-level (not per-user) index**, separate from and
alongside M23's existing per-user `GraphStore` (which continues
unchanged, still serving facts/memory exactly as it does today). The
system-level index answers "what exists and what state is it in" -
never "what does this specific user know," which remains M23's job.

**What it indexes (per the User's own list, each mapped to a real,
already-existing source - never a new parallel source of truth):**

| Map category | Real source (read-only projection, never copied/duplicated) |
|---|---|
| Capabilities | `CapabilityDirectory.summaries()`/`describe()` (already generic, already the single existing source of capability truth - reused verbatim, per Plan B's own audit) |
| Skills (learned) | `SkillMemory`'s own store (`uri_workspace/skill_memory.json` shape) - indexed as reference pointers only, never given plan authority (unaffected by, and consistent with, the existing "learned skills must not have independent direct execution authority" invariant, M30-PFC) |
| Workflows | `WorkflowPlanner`'s own template(s) - see Plan B §C for the current inventory (exactly one real template today, `generic_evidence_drafting_workflow`, already exposed as a Directory procedure) |
| Memory pointers | `MemoryStore`'s own entries - **pointers only** (`memory_id`, category, consent tag, timestamp), never the raw fact content itself, mirroring M23's own existing privacy discipline |
| Entities | M23's existing per-user graph nodes, referenced by pointer (`user_id` + `external_ref`), never duplicated into the system-level index |
| Dependencies | Declared, static: each capability's own `preconditions` (e.g. `["gmail_connected"]`, already on the `Capability` base class) and, where real, the module import relationships already enforced by the existing AST-boundary tests (`test_capability_authority_boundary.py`, `test_graph_authority_boundary.py`) - read from source/registration, never inferred |
| Connected/runtime availability | `Capability.check_availability()` (already the single generic mechanism, per Plan B's Scenario 2 audit) - refreshed, never cached indefinitely (§A.3) |
| Provenance | Which registry/adapter/module a capability or workflow came from (legacy vs. multi-action vs. procedure - the Directory already tracks this internally; surfaced here, not re-derived) |
| Authoritative source locations | File/module path for each indexed item (e.g. `uri_core/capabilities/gmail/capability.py` for `Gmail`) - a pointer for a human or the Brain to resolve to the real definition, never a copy of its contents |

**Explicitly NOT built in this foundation phase** (per the User's own
"do not build the full future Graphify vision yet"): entity/relationship
graph traversal across capabilities (`graph_path`/`graph_impact`-style
multi-hop reasoning over this new system index - M23's existing
per-user graph keeps that capability for facts/memory only); any
ranking/relevance-scoring model beyond simple, already-existing lookups;
any write path from this new index back into any authority-bearing
store; any Brain-facing Capability Directory entry for Graphify itself
(mirroring M23's own §8 "never exposed as a Brain-facing capability"
rule exactly).

### A.2 Storage shape - pointers, not copies

A single, small, versioned JSON (or SQLite, matching M23's own stdlib-
only precedent) file under `uri_workspace/graphify_index.json` (system-
scoped, not per-user - alongside, not inside, `uri_workspace/users/`).
Each entry is a compact record:

```json
{
  "id": "capability:Gmail",
  "kind": "capability",
  "source_path": "uri_core/capabilities/gmail/capability.py",
  "provenance": "multi_action_registry",
  "dependencies": ["gmail_connected"],
  "availability": {"known": true, "available": null, "checked_at": null},
  "pointer": {"registry": "CapabilityDirectory", "lookup_key": "Gmail"}
}
```

**"Preserve pointers rather than duplicate source content"**,
concretely: `availability` is refreshed (§A.3), never a snapshot of a
capability's live connection state frozen at index-build time (that
would be a stale, misleading copy, exactly the failure mode the User's
instruction guards against) - `pointer.lookup_key` is what the Brain
or a future consumer resolves against the real, live
`CapabilityDirectory` for anything beyond the compact map (current
availability, action schemas, etc.). The index answers "what exists
and roughly what state is it in, and where do I look for more" - it
is never itself the source of truth for anything.

### A.3 Lifecycle - startup load + incremental refresh, never a cache pretending to be truth

- **Startup:** on process start, load the persisted index file (if
  present) into an in-memory structure; if absent or corrupted,
  quarantine-and-rebuild-fresh (mirroring `GraphStore`'s own existing
  corrupted-file discipline, `M23_STATE.md`'s own precedent - never
  crash the server over a malformed index).
- **Build/refresh:** a bounded, idempotent `refresh()` walks the real
  sources in the table above (`CapabilityDirectory.summaries()`,
  `SkillMemory`'s store, `WorkflowPlanner`'s template set,
  `MemoryStore`'s own entry list for pointers only) and re-derives the
  index records; availability fields are refreshed by calling each
  capability's own `check_availability()` - the exact same generic
  mechanism Gate 5 already uses (Plan B), never re-implemented.
- **Incremental, not full-rebuild-only:** `refresh()` accepts an
  optional scope (e.g. "just capabilities," "just this one skill") so
  a future real-time trigger (a capability registered/unregistered, a
  new learned skill recorded) can update one record without re-walking
  everything - the mechanism exists from the start, even though this
  foundation phase only wires it to fire at startup and on an explicit
  manual/administrative call, never on every turn (that would
  reintroduce per-turn cost this migration has been careful to avoid
  elsewhere, e.g. Decision Contract JSON-schema validation being
  bounded and cheap).
- **Never authoritative, never blocking:** if the index is stale,
  missing, or fails to build, every consumer (Turn State's own
  `graph_context`-adjacent field, §A.4) degrades to empty/absent -
  exactly M23's own "degrades to all-empty" discipline for
  `build_graph_context()`, reused verbatim in spirit.

### A.4 Brain-facing surface - "only the small relevant context subset"

Turn State already has an unused `graph_context: Optional[Dict[str,
Any]]` parameter (`turn_state.py`, confirmed by direct reading - never
currently populated from any real call site). This foundation:

- Does **not** repurpose that field for M23's own per-user fact/memory
  graph (that remains M23's job, unchanged, and is real future scope
  for the original plan's own M30.9 wiring - not duplicated or
  preempted here).
- Adds a small, separate, additive Turn State field (e.g.
  `capability_index_hint`) populated from a bounded lookup against
  this new system-level index - filtered to the small number of
  entries plausibly relevant to the current turn's `goal_text` (reusing
  `capability_relevance.py`'s own already-generic, already-tested,
  directory-derived scorer for "plausibly relevant," never a new
  heuristic - the exact module Plan B's own Scenario 2 repair also
  reuses, so no fourth relevance mechanism is introduced anywhere in
  this migration).
- Is read-only from the Brain's perspective, mirroring `graph_context`'s
  own existing framing exactly: informational, never a plan, never an
  execution result, never an approval signal.

### A.5 Startup Services - a reusable category, not a one-off

**New, small `uri_core/core/startup_services.py`:**

```python
class StartupService(Protocol):
    def start(self) -> None: ...

def run_startup_services(services: Sequence[StartupService]) -> None:
    for service in services:
        try:
            service.start()
        except Exception:
            continue  # one service's failure must never block another's,
                       # or prevent the server from starting at all
```

`server.py`'s `_lifespan()` becomes:

```python
async def _lifespan(_app: FastAPI):
    run_startup_services([
        UserScopedStoreInitializer(),   # wraps today's _initialize_user_scoped_stores()
        GraphifyIndexLoader(),          # new - this plan's own startup load (§A.3)
    ])
    yield
```

This is the concrete, minimal answer to "design a reusable Startup
Services category/lifecycle so Graphify is not hard-coded as a one-off
startup exception": today's *one* hardcoded call becomes the *first*
registered service under a real, generic, extensible list - not a
special case, not a parallel mechanism, and not over-built into a
plugin system this milestone doesn't need. A third future startup need
(anything) is a third list entry, never a third `if` branch bolted
onto `_lifespan()` directly.

---

## Files affected (planning only - none of this is implemented yet)

**New:**
- `uri_core/core/startup_services.py` - the `StartupService`
  protocol + `run_startup_services()` runner.
- `uri_core/core/graphify_index.py` - the system-level index builder/
  loader/refresher (§A.2/§A.3).
- New test files mirroring M23's own conventions: index build/refresh
  correctness, startup-load-from-persisted-file, corrupted-file
  quarantine-and-rebuild, an AST-based authority-boundary test proving
  `graphify_index.py` has zero authority-bearing imports (mirroring
  `test_graph_authority_boundary.py` exactly), a Turn State additive-
  only regression test (mirroring `test_graph_context_boundary.py`).

**Modified, narrowly:**
- `uri_core/app/server.py` - `_lifespan()` refactored to call
  `run_startup_services([...])` instead of one hardcoded function;
  `UserScopedStoreInitializer`/`GraphifyIndexLoader` are thin adapter
  classes wrapping existing/new logic, not a rewrite of
  `_initialize_user_scoped_stores()`'s own behavior.
- `uri_core/core/turn_state.py` - one new optional field
  (`capability_index_hint`), additive-only, proven by a test mirroring
  `test_query_context.py`'s own existing additive-key assertion.

**Explicitly NOT touched:** `graph_store.py`, `graph_engine.py`,
`graph_ingest.py`, `graph_context.py`, `graph_schema.py` (M23's own
per-user graph is unchanged - this plan builds a sibling, not a
replacement); `capability_directory.py`, `decision_gates.py`,
`decision_engine.py`, `canonical_execution.py` (read from, never
modified - this foundation is purely a new, additional consumer of
already-generic sources, per §A.1's table).

---

## Tests required

1. Index build correctness against a real `CapabilityDirectory`,
   `SkillMemory`, and `WorkflowPlanner` fixture - every registered
   capability/skill/template produces exactly one index record, with
   the correct `kind`/`source_path`/`dependencies` fields.
2. Startup load from a persisted index file - `run_startup_services()`
   populates the in-memory index without re-walking the real sources
   (a spy/mock on the Directory confirms zero calls when a valid
   persisted file exists).
3. Corrupted/missing index file - quarantine-and-rebuild-fresh, never
   a crash, mirroring `GraphStore`'s own existing test pattern.
4. Incremental refresh - refreshing a single scope (e.g. "capabilities
   only") updates only those records, leaves others untouched.
5. Availability refresh reuses the real, generic
   `Capability.check_availability()` mechanism - proven against a fake
   capability whose availability changes between two `refresh()` calls,
   confirming the index reflects the change (not a stale copy).
6. AST-based authority boundary - `graphify_index.py` imports none of
   `model_providers`/`model_router`/`dispatcher`/`approval_gate`/
   `approval_store`/`decision_gates`/`decision_engine`/
   `canonical_execution`; none of those modules imports
   `graphify_index`. Mirrors `test_graph_authority_boundary.py`
   exactly - the same proof style, applied to the new module.
7. Turn State additive-only - every existing Turn State field's value
   is unchanged when `capability_index_hint` is also populated
   (mirrors `test_graph_context_boundary.py`).
8. `StartupService` runner - one service's exception never prevents
   another registered service from running, and never prevents
   `_lifespan()` from completing (the server must still start).
9. Full existing regression suite (including all M23 graph tests, all
   decision_gates/decision_engine tests, and the full baseline)
   re-run unchanged and passing - zero regression from this purely
   additive foundation.

---

## Acceptance criteria (this plan, before Plan B's Phase A may begin)

1. Startup Services lifecycle exists and is generic (§A.5) - proven by
   test #8, and by `_initialize_user_scoped_stores()`'s own existing
   behavior being provably unchanged once wrapped (a regression test,
   not merely a refactor claim).
2. The system-level index loads at startup, degrades safely when
   absent/corrupted, and supports incremental refresh (§A.3) - tests
   #2-4.
3. The index correctly maps capabilities/skills/workflows/dependencies/
   availability/provenance/source-locations from real, already-
   generic sources - never a second, competing source of truth (test
   #1, #5).
4. Proven non-authoritative by construction, not merely by convention
   (test #6) - matching M23's own bar exactly.
5. Turn State's new field is additive-only (test #7) and the Brain
   receives only a small, relevance-filtered subset, never the whole
   index (§A.4's reuse of `capability_relevance.py`).
6. Zero regression across the full existing suite (test #9).

Once all six hold, Plan B's Phase A may begin - this plan does not
itself authorize Plan B, or M30.8, or any cutover.

---

Stopping here. No production source modified. No implementation
performed - this plan defines the required foundation for the User's
review and separate implementation authorization.
