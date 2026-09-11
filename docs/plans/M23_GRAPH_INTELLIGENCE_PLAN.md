# M23 — URI Graph Intelligence Foundation

**Status:** DRAFT (see `docs/plans/M23_STATE.md` for ACCEPTED transition and history log)
**Author:** Claude (AO-4 Planner)
**Date:** 2026-09-12
**Review tier:** independent deep review (same tier as M22.2/M22.3/M22.4/M22.5 —
this milestone touches a cross-cutting concern, adds new persistent storage,
and defines a new Brain-facing context boundary).

---

## §0. Milestone numbering — why M23, not M22.10

Two candidate numbers exist in this repository's own documents and both were
inspected before choosing:

1. **`URI_M22_ARCHITECTURE.md` §22's own dependency graph** enumerates the
   M22 sequence as exactly `M22.1 → M22.9`, all nine now `DONE, VERIFIED`
   (`M22.9` released this session, commit `9c848fe`). The same document uses
   **"M23"** repeatedly and explicitly as the label for "the next major
   phase once every M22 milestone has proven the authenticated path is a
   strict superset of its behaviour" (§20.7), for dynamic-skill-controlled
   UI enforcement (§15.1: "Specify now, build in M23"), and for
   Developer Mode's eventual home (§16.3) — i.e. this repository's own
   convention already reserves "M23" as "the next standalone phase after
   the M22 sequence closes," not a specific pre-committed scope. Graph
   Intelligence is exactly that shape: a new, standalone, cross-cutting
   subsystem with no dependency on anything M22.1–M22.9-specific.
2. **`docs/plans/M22_MEMORY_CONTEXT_RETRIEVAL_ARCHITECTURE.md`** (an
   unimplemented architecture *proposal*, never accepted as a milestone
   plan, no `M22.10_STATE.md` exists, not in `URI_MILESTONE_TRACKER.md`)
   independently proposed **"M22.10"** for itself — relevance-scored
   memory/context retrieval, a different, narrower, still-unbuilt piece of
   work. Reusing "M22.10" for graph intelligence would collide with that
   still-live reservation and could mislead a future reader into thinking
   either proposal had been addressed by the other. They are complementary
   (§14 below) but distinct.

**Decision: this milestone is M23.** This is a naming choice resolved from
direct textual repository evidence, not a coin flip or a User preference
question — it does not touch privacy, security, authority, or the user-data
model, so it is not escalated. `M22.10` remains available, unclaimed by
this milestone, for the memory-retrieval proposal if the User pursues it
later.

---

## §1. Objective

Give URI a **URI-native, model-centric-compliant Knowledge Graph /
Graph Intelligence subsystem**: structured entities, typed relationships,
bounded query/path/explain/impact primitives, and provenance on every
graph assertion — usable as **context/evidence for the Brain**, never as an
independent authorization source. This is explicitly **Phase 1: foundation**
— schema, persistence, isolation, CRUD, provenance, dedup, read primitives,
path traversal, explainability, tests, and the Brain-context integration
boundary. It is **not** automatic entity extraction, not bulk
email/document ingestion, and not a UI/visualization surface.

## §2. Architectural gap audit

### 2.1 What already exists and must be reused, not duplicated

| Existing component | What it already does | Reuse discipline for M23 |
|---|---|---|
| `uri_core/core/facts.py` (`Fact`) | Status vocabulary (`CONFIRMED/VERIFIED/PROVISIONAL/HISTORICAL/SUPERSEDED/EXPIRED`), `evidence_ids`, non-model `verify()` gate | Graph edges reuse the same three-way current/historical/superseded *spirit* via a `status` field (`ACTIVE/HISTORICAL/SUPERSEDED`); a Fact-derived node's provenance records the originating `Fact` by reference — **`facts.py` is not modified, not subclassed, not reimplemented.** |
| `uri_core/core/user_memory.py` (`MemoryStore`, `is_eligible_for_personalization`) | Consent-gated durable memory (`user_provided`/`user_confirmed`/`pending_confirmation`) | Graph ingestion from memory re-applies `is_eligible_for_personalization` itself (defense in depth, same discipline the sibling memory-retrieval proposal calls for) — **never reads `pending_confirmation` entries into the graph.** `user_memory.py` is not modified. |
| `uri_core/core/query_context.py` (`build_query_context`) | Pure, fixed-key Brain-context assembler; already extended additively 4 times (M18 experience, M20 diagnostics, M21 conversation/attachments, M22 capabilities) | Gains exactly **one new optional key**, `graph_context`, following the identical additive pattern — **the function's own discipline (pure, no storage access, degrade-to-empty) is preserved, not weakened.** |
| `uri_core/core/context_budget.py` (`fit_within_budget`, `bound_json_value`) | Deterministic, already-existing size-bounding primitives | Reused unchanged to bound `graph_context`'s entity/relationship/path lists — **no new bounding primitive is invented.** |
| `uri_core/core/portable_paths.py` (`user_scoped_path`) | The one canonical per-user path convention (UUID-validated, device-id-excluded) | Reused unchanged for the new per-user graph store file. |
| `uri_core/core/security_guards.py` (`looks_like_credential_value`) | Credential-shaped string rejection, already used by `user_memory.py` | Reused unchanged to validate any free-text node/edge attribute value. |
| `server.py::_build_user_context` (9 existing per-user stores) | The established "one store per concern, all under `uri_workspace/users/<user_id>/`" pattern | Gains a **10th store**, `graph_store`, constructed identically to the existing nine — no new construction pattern invented. |
| `test_capability_authority_boundary.py`'s AST-import technique | Proves an authority boundary by inspecting real imports, not by convention | Reused, not reinvented, for the new graph-authority boundary test (§8). |
| `capability_resolver.py` | Pure-function-over-injected-store shape, per-user grant intersection | Used only as a *structural precedent* (pure functions, no FastAPI dependency, static/testable) — **not extended or modified**; `graph_engine.py` follows `evidence_context.py`/`query_context.py`'s plainer module-function convention instead, since it is a context-shaping reader, not an authorization gate. |
| `route_classification.py` | Single source of truth for every route's `PUBLIC/USER/ADMIN` classification, enforced by an enumeration test | New `/graph/*` routes are added here explicitly, classified `USER` (self-scoped, same authenticated-or-legacy-ambient pattern as `/memory`) — **never silently left unclassified.** |

### 2.2 What must NOT be duplicated

- **`Fact`'s status/verification model** — not reimplemented as a parallel graph-native "fact" concept. A Fact stays a Fact; the graph holds a *reference* to it.
- **`MemoryStore`'s consent gate** — not bypassed or re-derived differently for graph ingestion.
- **`query_context.py`'s assembly contract** — not replaced by a graph-specific assembler; graph context is one section within the existing envelope.
- **`ApprovalGate`/`CapabilityResolver`'s authority decision** — the graph never becomes a second place a capability or action is authorized. No graph module is ever consulted by `dispatcher.py`, `approval_gate.py`, or `capability_registry.py`'s execution path (proven, not asserted — see §8).
- **A new database server/broker/cache** — `URI_M22_ARCHITECTURE.md` §11.3's "no database" rule was scoped to *"realistic multi-user counts this milestone targets"* for **flat, non-relational** per-user state (JSON/JSONL), and explicitly invites revisiting "only if a measured problem appears." Graph *traversal* (multi-hop neighbor/path/impact queries) is a different computational shape than "read one small JSON file" — exactly the kind of problem an embedded, indexed, zero-dependency, zero-process store solves. **SQLite (Python's stdlib `sqlite3`, already available, zero new declared dependency) is used — not a new server, not Neo4j, not a broker.** This is consistent with the User's own explicit instruction (constraints §9/§10) to default to SQLite unless proven unnecessary, and does not conflict with §11.3's actual rationale once read in full.

### 2.3 Gaps this milestone actually closes

- URI has no structured entity/relationship representation today — facts, memory, and evidence are each their own flat, unlinked store. There is no way to ask "how is X connected to Y," "what depends on Z," or "why does URI believe this," across store boundaries.
- No per-assertion provenance model spans stores today — `Fact.evidence_ids`/`source` exists but nothing links a Fact to a Person/Organization/Document entity graph-style.
- No bounded multi-hop traversal/explainability primitive exists anywhere in the runtime.

---

## §3. Non-goals for this milestone (explicit, per the User's Phase-1 boundary)

- **No automatic entity extraction from raw text.** Ingestion in Phase 1 is a small set of deterministic conversions triggered at the *exact* points records are already created/confirmed today (`MemoryStore.confirm()`'s call site, `Fact.verify()`'s call site) — never a bulk background sweep.
- **No email/Gmail/Drive ingestion.** Zero new read access to those sources is added.
- **No entity resolution / fuzzy matching across differently-worded mentions** — dedup in Phase 1 is exact-key-based only (§5.3), not similarity-based.
- **No temporal-graph modeling beyond the existing `created_at`/`updated_at`/`status` fields.**
- **No contradiction-detection logic** — a `CONTRADICTS` relationship type exists in the schema so a *human or a later milestone* can record one, but nothing in Phase 1 detects contradictions automatically.
- **No vector/semantic index, no embeddings, no Mem0/secondary-provider integration.**
- **No UI/visualization.** `UI IMPACT: NONE` for this milestone (§12).
- **No MCP exposure.**
- **None of this is blocked by the above** — see §14.

---

## §4. Design — storage layer

### 4.1 `uri_core/core/graph_store.py` (new)

One `GraphStore` per user, one SQLite file at
`user_scoped_path(user_id, "graph.sqlite3", root=_USER_STATE_ROOT)` —
identical construction discipline to `MemoryStore`/`ExperienceStore`.
`sqlite3` is Python's standard library — **zero new declared dependency.**

```sql
CREATE TABLE nodes (
    entity_id       TEXT PRIMARY KEY,
    entity_type     TEXT NOT NULL,
    canonical_name  TEXT NOT NULL,
    external_ref    TEXT,              -- optional: an existing store's own id
                                        -- (e.g. a Fact's identity, a
                                        -- MemoryEntry.memory_id), for exact
                                        -- dedup against re-ingestion
    attributes_json TEXT NOT NULL DEFAULT '{}',
    provenance_json TEXT NOT NULL,     -- see §5
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    schema_version  TEXT NOT NULL
);
CREATE UNIQUE INDEX ix_nodes_external_ref
    ON nodes(entity_type, external_ref) WHERE external_ref IS NOT NULL;
CREATE INDEX ix_nodes_type ON nodes(entity_type);

CREATE TABLE edges (
    edge_id             TEXT PRIMARY KEY,
    source_id           TEXT NOT NULL REFERENCES nodes(entity_id),
    target_id           TEXT NOT NULL REFERENCES nodes(entity_id),
    relationship_type   TEXT NOT NULL,
    attributes_json      TEXT NOT NULL DEFAULT '{}',
    provenance_json      TEXT NOT NULL,   -- see §5
    confidence           REAL,             -- 0.0-1.0 or NULL, same validated
                                            -- range discipline as Fact.confidence
    status                TEXT NOT NULL DEFAULT 'ACTIVE',  -- ACTIVE|HISTORICAL|SUPERSEDED
    created_at            TEXT NOT NULL,
    updated_at            TEXT NOT NULL,
    schema_version        TEXT NOT NULL
);
CREATE INDEX ix_edges_source ON edges(source_id, relationship_type, status);
CREATE INDEX ix_edges_target ON edges(target_id, relationship_type, status);
```

Corrupted/missing DB file degrades safely (fresh schema created on open,
matching every other store's "corrupted → safe empty" discipline — never a
raised exception on normal use).

### 4.2 CRUD surface (`GraphStore` methods — module-function-callable, testable with a `tempfile` DB, same isolation discipline as every existing store's tests)

- `upsert_node(entity_type, canonical_name, attributes=None, external_ref=None, provenance=...) -> GraphNode`
- `get_node(entity_id) -> Optional[GraphNode]`
- `delete_node(entity_id)` — cascades to delete edges referencing it (a hard delete path exists for correction/GDPR-style removal; nothing in Phase 1 calls this automatically).
- `upsert_edge(source_id, target_id, relationship_type, attributes=None, provenance=..., confidence=None, status="ACTIVE") -> GraphEdge`
- `get_edge(edge_id) -> Optional[GraphEdge]`
- `set_edge_status(edge_id, status)` — the primitive a future milestone (or a human correction) uses to mark an edge `HISTORICAL`/`SUPERSEDED`; Phase 1 exposes it but nothing calls it automatically beyond an explicit `SUPERSEDES`-edge convention (§5.4).
- `list_nodes(entity_type=None, limit=...) -> List[GraphNode]`
- `list_edges(entity_id=None, relationship_type=None, status="ACTIVE", limit=...) -> List[GraphEdge]`

Every write validates: `entity_type`/`relationship_type` against the
extensible registry (§6), attribute values via
`looks_like_credential_value` (rejected, matching `user_memory.py`), and
`confidence` via the same `0.0–1.0` range check `Fact.validate_confidence`
already uses (same validation *shape*, invoked independently — `facts.py`
is not imported by `graph_store.py`, keeping the modules decoupled exactly
as `user_memory.py` already keeps `MemoryEntry` decoupled from re-deriving
`Fact`'s own internals).

### 4.3 Deduplication / identity handling

- If `external_ref` is supplied (an existing store's own id — a `Fact`'s
  `name`, a `MemoryEntry.memory_id`, a `UserAccount.user_id`), the unique
  index on `(entity_type, external_ref)` means a second `upsert_node` call
  with the same pair **updates the existing node** rather than creating a
  duplicate — the exact-key dedup this milestone commits to (§3).
- If no `external_ref` is given, `entity_id` is derived deterministically:
  `uuid5(URI_GRAPH_NAMESPACE, f"{user_id}:{entity_type}:{normalize(canonical_name)}")`
  — re-asserting the same `(type, name)` pair for the same user always
  resolves to the same node.
- Edges are deduplicated the same way: `edge_id` is derived from
  `(source_id, target_id, relationship_type)` — re-asserting the same
  relationship updates it (refreshed `provenance`/`confidence`/`updated_at`)
  rather than creating a parallel duplicate edge.

---

## §5. Design — provenance

Every node and edge carries a `provenance` object (`provenance_json`):

```json
{
  "source_type": "fact | memory | user_account | manual | system",
  "source_id": "the originating store's own identifier",
  "recorded_by": "system | <user_id>",
  "recorded_at": "ISO-8601 timestamp",
  "evidence_status": "mirrors Fact.status when source_type == fact, else null"
}
```

- **§5.1 Traceability.** `graph_explain`/`graph_get_entity` always return
  provenance verbatim — never summarized away — so "why does URI believe
  this" is answerable down to the originating store record, satisfying the
  User's constraint #6.
- **§5.2 No authority inflation.** `provenance.evidence_status` is a
  *copy*, recorded at ingestion time, of the originating Fact's status —
  it is never re-derived as stronger than the source. A `PROVISIONAL` fact
  is never ingested at all (§9 — only `VERIFIED` facts and
  consent-eligible memory are eligible ingestion inputs).
- **§5.3 Edges vs. current authority (constraint #5).** `status` on an
  edge is independent of provenance — an edge can be provably real
  history (`recorded_at` two years ago, well-provenanced) while being
  `HISTORICAL`/`SUPERSEDED` today. `graph_query`/`graph_neighbors`/
  `graph_path` all default to `status="ACTIVE"` only; a caller must
  explicitly opt in (`include_historical=True`) to see anything else —
  the same "you have to ask for it" discipline `evidence_context.py`'s
  `get_verified_evidence` already applies to non-`VERIFIED` facts.
- **§5.4 `SUPERSEDES`.** Writing a `SUPERSEDES` edge (`new_entity ->
  SUPERSEDES -> old_entity`) is a plain edge write like any other; Phase 1
  does **not** automatically flip the old entity's other edges to
  `HISTORICAL` as a side effect (that would be exactly the kind of
  hard-coded task-specific inference logic ADR-018 warns against) — a
  human, or an explicit future milestone's deterministic rule, calls
  `set_edge_status` themselves. This keeps the primitive honest: existence
  of a `SUPERSEDES` edge is a fact the Brain can reason about, not a rule
  the runtime silently enforces.

---

## §6. Design — extensible type registry

`uri_core/config/graph_schema.py` (new, packaged config module, same shape
as `uri_core/config/modes.py`):

```python
PACKAGED_ENTITY_TYPES = {
    "User", "Person", "Organization", "Student", "Department", "Hostel",
    "Document", "File", "Email", "Fact", "Memory", "Decision", "Rule",
    "Event", "Task", "Capability", "Source",
}
PACKAGED_RELATIONSHIP_TYPES = {
    "MENTIONS", "RELATED_TO", "BELONGS_TO", "SUPPORTED_BY", "DERIVED_FROM",
    "SUPERSEDES", "CONTRADICTS", "AFFECTS", "DEPENDS_ON", "CREATED_BY",
    "APPROVED_BY", "USES_CAPABILITY", "LOCATED_IN",
}
```

Not a closed enum: `GraphStore` validates a submitted type string against
`PACKAGED_ENTITY_TYPES | additional_registered_types` (an install-scope,
JSON-persisted extension list, same pattern as `capability_grants.json`) —
a genuinely new, well-formed type name (e.g. a future domain's `"Vendor"`)
can be registered without touching this module or redeploying, satisfying
the User's "must permit new safe node/edge types later." Rejected only
when the value is empty, non-string, or credential-shaped — never merely
because it is unfamiliar. `NIT Sikkim` (or any institution) never appears
anywhere in this module or in `graph_store.py` — the type set is
deliberately generic (`Student`/`Department`/`Hostel` are domain-general
educational-institution concepts already present in the target-entity
list the User specified, not a hard-coded NIT Sikkim reference).

---

## §7. Design — read/query primitives (`uri_core/core/graph_engine.py`, new)

Pure module-level functions, each taking a `GraphStore` instance first —
matching `evidence_context.py`'s `(session, ...)` / `query_context.py`'s
plain-function convention, not `capability_resolver.py`'s static-method
class shape (that shape exists there because two methods share one
authority formula; these six are independent read operations over one
store, better served as plain functions, consistent with the majority of
this codebase's context-reading modules).

- **`graph_get_entity(store, entity_id) -> Optional[dict]`** — one node,
  with its provenance, plus a small summary of its directly-incident
  `ACTIVE` edges (bounded, `limit` default e.g. 50).
- **`graph_query(store, entity_type=None, name_contains=None, limit=50) -> List[dict]`** —
  filtered node listing; `limit` always enforced server-side, never
  trusted to a caller-supplied unbounded value.
- **`graph_neighbors(store, entity_id, relationship_types=None, direction="both", status="ACTIVE", limit=50) -> List[dict]`** —
  one-hop neighbors, each returned with the connecting edge's own
  provenance/confidence/status.
- **`graph_path(store, source_id, target_id, max_hops=4, status="ACTIVE") -> Optional[List[dict]]`** —
  bounded BFS (never unbounded DFS/recursion — `max_hops` hard-capped at a
  small constant, e.g. 6, regardless of caller input) returning the
  shortest path as an ordered list of `{entity, edge}` steps, or `None`
  when no path exists within the hop bound. Cost is bounded by
  `max_hops × average_branching_factor`, not by total graph size — the
  same "bounded cost independent of store size" requirement the sibling
  memory-retrieval proposal set for its own scoring (§3.3 there),
  reused here as the same standing discipline.
- **`graph_explain(store, source_id, target_id, max_hops=4) -> dict`** —
  calls `graph_path` internally, then returns
  `{"path": [...], "provenance": [...], "confidence_status": [...]}` —
  each edge on the path paired with its own provenance and status, so
  "why are these connected" is answerable with real citations, never a
  generated narrative (that's the Brain's job, over this structured
  output — §10).
- **`graph_impact(store, entity_id, relationship_types=("DEPENDS_ON", "AFFECTS"), direction="incoming", max_hops=3) -> List[dict]`** —
  bounded reverse-traversal: "what would be affected if `entity_id`
  changed" — read-only, reporting-only, explicitly documented (module
  docstring + this plan) as **never** a trigger for any execution
  decision. `graph_impact`'s result is context a human or the Brain reads;
  nothing in the dispatcher/approval path ever calls it (§8 proves this).

All six functions are read-only — none writes to the store — and this is
provable, not merely intended (§8).

---

## §8. Design — the authority boundary (constraints #2, #3, #4)

**The graph is context, never authority.** Enforced structurally, the same
way every prior M22 authority boundary was enforced, and proven by a new
AST-import test mirroring `test_capability_authority_boundary.py`:

- `uri_core/core/dispatcher.py` must never import `graph_store`,
  `graph_engine`, or `graph_context`.
- `uri_core/core/approval_gate.py` must never import them.
- `uri_core/core/capability_registry.py`/`capability_resolver.py` must
  never import them (capability grants stay authorized purely by the
  existing registry ∩ grants ∩ mode formula — a graph edge can never
  become a fourth term in that intersection).
- `graph_engine.py`/`graph_context.py` must never import
  `uri_core.core.model_providers`/`model_router` (no model identity input,
  same invariant `URI_M22_ARCHITECTURE.md` §18.1 already requires
  elsewhere) and must never import `dispatcher`/`approval_gate`/
  `approval_store` (mirrors `query_context.py`'s own existing boundary,
  verified by the same technique).
- `graph_store.py`'s write methods (`upsert_node`/`upsert_edge`/
  `delete_node`/`set_edge_status`) are called from exactly two places in
  Phase 1: `graph_ingest.py` (§9) and the new `/graph` admin-adjacent
  correction path, if any is added — **never from `dispatcher.py`,
  `approval_gate.py`, or any capability's execution adapter.**

This is the literal implementation of the User's constraint #3 ("Graph
relationships may never independently authorize an action") — not a
policy statement alone, a compiled/testable one.

---

## §9. Design — controlled ingestion from existing stores (`uri_core/core/graph_ingest.py`, new)

Phase 1 ingestion is **narrow and deterministic**, exactly per the User's
"use existing facts/memory/evidence as initial controlled inputs... do NOT
immediately ingest every email/document":

- **From `Fact`:** only when a `Fact.verify()` call succeeds (i.e. at the
  exact call site where a fact already becomes non-model-verified —
  `fact_manager.py`'s existing verification path), a small deterministic
  helper writes/updates one `Fact`-typed node (`external_ref=fact.name`,
  `provenance.source_type="fact"`, `provenance.evidence_status=fact.status`)
  — **never for a fact that is merely `PROVISIONAL`/`CONFIRMED`** (only
  the accountable, human-verified `VERIFIED` status qualifies, the
  strictest existing status, matching `evidence_context.py`'s own
  eligibility bar).
- **From `MemoryEntry`:** only when `MemoryStore.confirm()` succeeds (the
  exact call site where a memory becomes `user_confirmed`, or was already
  `user_provided`), a deterministic helper writes/updates one
  `Memory`-typed node (`external_ref=entry.memory_id`) — **re-applying
  `is_eligible_for_personalization` itself**, never trusting the caller
  (§2.1, defense in depth).
- **From `UserAccount`:** one `User`-typed node per logged-in user,
  written once at first graph interaction (lazy, not a bulk migration
  sweep) — `external_ref=user_id`.
- **No other source is touched in Phase 1.** No Gmail, no Drive, no file
  content, no raw conversation text is read by `graph_ingest.py`. This is
  the literal implementation of "foundation, not full automatic knowledge
  extraction."
- **§9.1 Untrusted-extraction seam, reserved but not built.** Per
  constraint #12, any *future* milestone that lets a model propose graph
  facts must route the proposal through the same
  propose → validate → approve pattern the Model↔Runtime Contract already
  requires for every other model output (§13 of that contract: "Model
  output is untrusted input to these controls"). Phase 1 does not build
  that path — `graph_ingest.py` never calls a model, never accepts a
  model-shaped payload, and there is no `graph_propose_*` function yet.
  This section exists so the seam is named, not silently assumed solved,
  the same discipline `M22_MEMORY_CONTEXT_RETRIEVAL_ARCHITECTURE.md` used
  for `EXPIRED`'s dead-code gap.

---

## §10. Design — the Brain-context boundary (`uri_core/core/graph_context.py`, new)

Mirrors `query_context.py`'s own discipline exactly: pure, no storage
access of its own, every input already computed by the caller.

```python
def build_graph_context(
    entities: Optional[List[Dict]] = None,
    relationships: Optional[List[Dict]] = None,
    paths: Optional[List[Dict]] = None,
    provenance: Optional[List[Dict]] = None,
    confidence_status: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    return {
        "entities": entities or [],
        "relationships": relationships or [],
        "paths": paths or [],
        "provenance": provenance or [],
        "confidence_status": confidence_status or [],
    }
```

Wired as **one new optional key** in `query_context.build_query_context()`
(`graph_context: Optional[Dict[str, Any]] = None` parameter, degrading to
`{}` exactly like every other optional section) — `query_context.py`'s own
contract is otherwise untouched.

`UriOrchestrator` gains one small new private method,
`_build_graph_context()`, mirroring `_build_query_context`'s existing
per-section pattern (`orchestrator.py:2859`) — called from the same site
`_build_query_context` is already called from
(`orchestrator.py:3158`/`676`). **Phase 1 keeps this deliberately narrow**:
`_build_graph_context()` only populates non-empty content when the current
turn's already-resolved session/task state names a specific entity
(reusing existing session/task identity fields — never a fresh free-text
graph-wide search injected into every turn's context), and the result is
passed through `context_budget.fit_within_budget` before assembly, exactly
like every other section — so **this milestone does not grow the Brain's
default per-turn context size**, satisfying the same "relevance, not a
bigger context window" spirit `M22_MEMORY_CONTEXT_RETRIEVAL_ARCHITECTURE.md`
already established, without depending on that (separate, still-unbuilt)
milestone.

**The runtime, not the graph, decides:** what graph data may be returned
(the six bounded primitives, nothing else), user ownership/isolation
(one `GraphStore` per `user_id`, never cross-user), source validity
(provenance is preserved, never invented), limits (`max_hops`, `limit`,
enforced server-side), authorization (unchanged — `CapabilityResolver`/
`ApprovalGate` are the only authority; see §8), and execution (the graph
never executes anything). The Brain performs reasoning **over** the
bounded `graph_context` object it receives — it never calls
`graph_engine.py` directly.

---

## §11. New API surface (`uri_core/app/server.py`)

All **read-only GETs**, self-scoped via the existing
`_resolve_context(user_id)` pattern (identical to `/memory`), classified
`USER` in `route_classification.py` (§2.1):

| Route | Calls | Notes |
|---|---|---|
| `GET /graph/entities/{entity_id}` | `graph_get_entity` | 404 if not found or not owned by caller. |
| `GET /graph/query?entity_type=&name_contains=&limit=` | `graph_query` | `limit` server-capped regardless of query param. |
| `GET /graph/neighbors/{entity_id}?relationship_types=&direction=&limit=` | `graph_neighbors` | |
| `GET /graph/path?source_id=&target_id=&max_hops=` | `graph_path` | `max_hops` server-capped at 6 regardless of query param. |
| `GET /graph/explain?source_id=&target_id=&max_hops=` | `graph_explain` | |
| `GET /graph/impact/{entity_id}?relationship_types=&direction=&max_hops=` | `graph_impact` | |

No write route is added in Phase 1 beyond what `graph_ingest.py` calls
internally — there is no `POST /graph/entities` exposed to a client yet
(deliberately deferred; nothing in §14's future list is blocked by this,
since a write route is additive whenever it's actually needed).

---

## §12. UI impact

**UI IMPACT: NONE.** Phase 1 is backend-only — no `uri_ui/` file is
touched. Knowledge visualization is explicitly listed in §14 as a
future capability this design does not block, not something Phase 1
builds.

## §13. `orchestrator.py` line-count impact

One new private method (`_build_graph_context`, mirroring
`_build_query_context`'s existing ~15-20 line shape) and one new
parameter passed at the two existing `_build_query_context` call sites.
Acceptance criterion: `wc -l uri_core/core/orchestrator.py` after M23
increases by no more than ~30 lines — the bulk of this milestone's logic
lives in the four new, separately-tested modules (`graph_store.py`,
`graph_engine.py`, `graph_ingest.py`, `graph_context.py`), not in
`orchestrator.py`, following the exact extraction discipline
`URI_M22_ARCHITECTURE.md` §17 already established for M22.4/M22.8.

---

## §14. Future capabilities this design does not block

Automatic entity extraction (a future `graph_ingest.py` extension, or a
new module, routed through the untrusted-model seam named in §9.1);
entity resolution/fuzzy matching (an additional dedup strategy layered
onto §4.3's exact-key dedup, not a replacement of it); temporal graph
relationships (the `created_at`/`updated_at`/`status` fields are already
there to build on); contradiction detection (the `CONTRADICTS`
relationship type already exists in the schema); graph + semantic/vector
retrieval and Mem0/secondary-memory-provider integration (nothing here
precludes a future embedding index reading the same `GraphStore` tables);
Gmail/Drive graph ingestion (new, separately-reviewed ingestion sources
added to `graph_ingest.py` or a sibling module, each still routed through
the same eligibility/provenance discipline); knowledge visualization (a
future `uri_ui/` client reading the existing read-only `/graph/*` routes);
graph-assisted research/planning (the Brain already receives
`graph_context` to reason over); cross-domain personal-companion
knowledge (the type registry is extensible per §6, not frozen); MCP
exposure (a future thin adapter over the same six pure functions); impact
analysis (`graph_impact` already Phase 1); "why does URI believe this"
(`graph_explain` already Phase 1).

**Relationship to `M22_MEMORY_CONTEXT_RETRIEVAL_ARCHITECTURE.md` (§0).**
Complementary, not overlapping: that proposal is about *relevance-ranking
what's already in flat per-section stores* (memory/experience/
conversation) for the existing `query_context.py` sections; M23 is about
*structured entities/relationships across stores* as one new section. A
future milestone could have relevance-scoring select *which* graph
entities are worth including in a turn's bounded `graph_context` — that
is explicitly left open, not designed here, and not blocked by anything
in this plan.

---

## §15. Security considerations

- **15.1** No graph module imports `dispatcher.py`/`approval_gate.py`/
  `capability_registry.py`'s execution surface/`model_providers`/
  `model_router` — proven by AST boundary test (§8, §16).
- **15.2** One `GraphStore` per `user_id`; no shared/global graph or
  cross-user query path exists anywhere in this design.
- **15.3** Every write path (`graph_ingest.py`'s three sources) re-applies
  the same eligibility gates the source store already enforces (`VERIFIED`
  facts only, consent-eligible memory only) — defense in depth, not trust
  in an upstream caller.
- **15.4** Free-text attribute values are validated with
  `looks_like_credential_value` before being persisted, same guard
  `user_memory.py` already applies.
- **15.5** All six read primitives are server-limit-capped
  (`max_hops≤6`, `limit` server-enforced) regardless of caller-supplied
  values, preventing an unbounded-cost query from either a client or a
  future Brain-initiated call.
- **15.6** Historical/superseded edges are excluded from every default
  read (`status="ACTIVE"` default) — a caller must explicitly opt in to
  see them, so a stale relationship can never silently read as current.

## §16. Test plan

| Test file (new) | Proves |
|---|---|
| `test_graph_store_crud.py` | Node/edge upsert, get, list, delete; dedup via `external_ref` and derived-id collision; provenance/status/confidence field round-trip; corrupted/missing DB degrades safely. |
| `test_graph_store_type_registry.py` | Packaged types accepted; a newly-registered type accepted; empty/credential-shaped/non-string type or attribute value rejected. |
| `test_graph_engine_traversal.py` | `graph_neighbors`/`graph_path`/`graph_explain`/`graph_impact` correctness on a small fixture graph; `max_hops`/`limit` bounds enforced even when a caller requests more; `status="ACTIVE"` default excludes `HISTORICAL`/`SUPERSEDED` edges unless explicitly included; no path found returns `None`, not an exception. |
| `test_graph_isolation.py` | Two users' `GraphStore`s are provably separate files with no cross-read path — same shape as M21's per-user isolation suite. |
| `test_graph_ingest_controlled.py` | A `VERIFIED` fact produces exactly one node/update; a `PROVISIONAL`/`CONFIRMED` fact produces none; a `pending_confirmation` memory produces none; a `user_confirmed`/`user_provided` memory produces one; re-ingesting the same fact/memory updates rather than duplicates; no email/Drive/file-content path exists to call. |
| `test_graph_authority_boundary.py` | AST-import boundary: `dispatcher.py`/`approval_gate.py`/`capability_registry.py`/`capability_resolver.py` never import any `graph_*` module; `graph_engine.py`/`graph_context.py`/`graph_ingest.py` never import `model_providers`/`model_router`/`dispatcher`/`approval_gate`/`approval_store`. |
| `test_graph_context_boundary.py` | `build_graph_context` degrades to the all-empty shape on no input (mirrors `query_context.py`'s existing degrade guarantee); `query_context.build_query_context()`'s new `graph_context` key is additive-only — every pre-existing key's value is unchanged when `graph_context` is supplied. |
| `test_server_graph_endpoints.py` | All six routes self-scoped (a second user cannot read/traverse the first user's graph — attempted cross-user `entity_id` access returns 404, not another user's data); `route_classification.py` enumeration test still passes with the six new routes classified `USER`. |

Plus full regression (`.venv/Scripts/python.exe -m unittest discover -p "test_*.py"`) — must remain 100% passing, and `flutter analyze`/`flutter test` must show **zero diff** (no `uri_ui/` file touched, per §12).

## §17. Acceptance criteria

1. `GraphStore` CRUD, dedup, provenance, and status filtering all pass their dedicated tests (§16 row 1).
2. Type registry accepts packaged + newly-registered types, rejects malformed/credential-shaped values (§16 row 2).
3. All six read primitives (`graph_get_entity`, `graph_query`, `graph_neighbors`, `graph_path`, `graph_explain`, `graph_impact`) are correct on a fixture graph and bounded regardless of caller input (§16 row 3).
4. Two users' graphs are provably isolated (§16 row 4).
5. Ingestion fires only from the three named existing call sites, re-applies eligibility gates itself, and never touches email/Drive/file content (§16 row 5).
6. The graph is provably never an authorization input — AST boundary test passes (§16 row 6).
7. `graph_context` is additive-only to `query_context.py`'s existing contract and degrades to empty (§16 row 7).
8. All six `/graph/*` routes are self-scoped and correctly classified `USER` (§16 row 8).
9. `wc -l uri_core/core/orchestrator.py` after M23 is no more than ~30 lines above its pre-M23 value (§13).
10. Full Python regression suite passes with zero failures, reproduced from scratch, not claimed from a worker's report.
11. `flutter analyze`/`flutter test` show zero diff (no `uri_ui/` file touched).
12. No `uri_core/core/{dispatcher,approval_gate,approval_store,capability_registry,capability_resolver}.py`, `capability_grants.json`, or `provider_registry.py`/`provider_keys.py` file is touched (verified via `git status`/`git diff`).

---

## §18. Implementer guidance (informational — Antigravity's own routing judgment at initiation time)

This milestone is new persistent storage, a new cross-cutting authority
boundary, and multi-file, precision-critical work (dedup/identity
derivation, bounded traversal correctness, AST boundary proofs) — squarely
**Codex-shaped** per the standing worker-selection rule
(`ORCHESTRATION.md`/`AGENTS.md`: "complex/multi-file/security-sensitive/
production-call-path work"), not Gemma-shaped bounded/boilerplate work.
This is Antigravity's own judgment call to make at initiation, not
pre-decided here.

---

## §19. What must explicitly NOT be built in this milestone

| Item | Why deferred |
|---|---|
| Automatic entity extraction from raw text/email/Drive | Explicit Phase-1 boundary (§3, §9); needs the untrusted-model-proposal seam (§9.1) that is only named, not built, here. |
| Entity resolution / fuzzy matching | Exact-key dedup only (§4.3); similarity-based resolution is future work (§14) with real false-merge risk that deserves its own review. |
| Contradiction detection | `CONTRADICTS` relationship type exists to be *recorded*, not *detected*, in Phase 1. |
| Vector/embedding index, Mem0 integration | Not needed to meet Phase-1 objectives; §9's SQLite choice does not block adding one later. |
| Any write route exposed to a client (`POST /graph/*`) | Not needed until a real caller exists; ingestion writes happen server-side only, via `graph_ingest.py`. |
| Knowledge visualization / any `uri_ui/` change | `UI IMPACT: NONE` (§12). |
| MCP exposure | Future work (§14); no MCP server exists in this repository today to extend. |
| Graph-based authorization of any kind | Constraint #3 — never built, ever, by design (§8). |
