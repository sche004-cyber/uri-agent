"""M23: pure, read-only query/traversal primitives over one user's
GraphStore (see docs/plans/M23_GRAPH_INTELLIGENCE_PLAN.md section 7).

Every function here is read-only - none writes to the store, proven by
test_graph_authority_boundary.py, not merely documented. Every function
is bounded (max_hops/limit server-enforced regardless of caller input)
so cost never scales unbounded with graph size, the same "bounded cost
independent of store size" discipline
docs/plans/M22_MEMORY_CONTEXT_RETRIEVAL_ARCHITECTURE.md set for its own
(separate, still-unbuilt) relevance scoring. Every function defaults to
status="ACTIVE" edges only - a caller must explicitly opt in
(include_historical=True) to see HISTORICAL/SUPERSEDED relationships,
so a stale relationship can never silently read as current (plan
section 5.3, the User's constraint 5).

This module never imports uri_core.core.model_providers/model_router
(no model identity input - same invariant URI_M22_ARCHITECTURE.md
section 18.1 already requires elsewhere) and never imports
dispatcher.py/approval_gate.py/approval_store.py (mirrors
query_context.py's own existing boundary). See
test_graph_authority_boundary.py for the structural proof.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Optional, Tuple

from uri_core.core.graph_context import build_graph_context
from uri_core.core.graph_store import GraphStore

MAX_HOPS_CEILING = 6
DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def _clamp_hops(max_hops: int) -> int:
    try:
        max_hops = int(max_hops)
    except (TypeError, ValueError):
        max_hops = 4
    return max(1, min(max_hops, MAX_HOPS_CEILING))


def _clamp_limit(limit: int) -> int:
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = DEFAULT_LIMIT
    return max(1, min(limit, MAX_LIMIT))


def graph_get_entity(store: GraphStore, entity_id: str, limit: int = DEFAULT_LIMIT) -> Optional[Dict[str, Any]]:
    """One node, with its provenance, plus a bounded summary of its
    directly-incident ACTIVE edges (never the whole graph)."""
    node = store.get_node(entity_id)
    if node is None:
        return None

    edges = store.list_edges(entity_id=entity_id, status="ACTIVE", limit=_clamp_limit(limit))
    return {
        "entity": node.to_dict(),
        "edges": [e.to_dict() for e in edges],
    }


def graph_query(
    store: GraphStore,
    entity_type: Optional[str] = None,
    name_contains: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
) -> List[Dict[str, Any]]:
    """Filtered node listing. limit is always server-enforced,
    never trusted to an unbounded caller-supplied value."""
    nodes = store.list_nodes(
        entity_type=entity_type, name_contains=name_contains, limit=_clamp_limit(limit)
    )
    return [n.to_dict() for n in nodes]


def graph_neighbors(
    store: GraphStore,
    entity_id: str,
    relationship_types: Optional[List[str]] = None,
    direction: str = "both",
    status: str = "ACTIVE",
    limit: int = DEFAULT_LIMIT,
) -> List[Dict[str, Any]]:
    """One-hop neighbors, each returned with the connecting edge's own
    provenance/confidence/status - never just a bare id list, so the
    caller always has enough to explain why two entities are linked."""
    limit = _clamp_limit(limit)
    edges = store.list_edges(entity_id=entity_id, direction=direction, status=status, limit=limit)

    if relationship_types:
        wanted = set(relationship_types)
        edges = [e for e in edges if e.relationship_type in wanted]

    results = []
    for edge in edges:
        neighbor_id = edge.target_id if edge.source_id == entity_id else edge.source_id
        neighbor = store.get_node(neighbor_id)
        if neighbor is None:
            continue
        results.append({"entity": neighbor.to_dict(), "edge": edge.to_dict()})

    return results[:limit]


def _bfs_shortest_path(
    store: GraphStore, source_id: str, target_id: str, max_hops: int, status: str
) -> Optional[List[Tuple[Any, Any]]]:
    """Bounded breadth-first search - cost is bounded by
    max_hops x branching factor at each step, never by total graph
    size. Returns a list of (node, edge_taken_to_reach_it) tuples for
    every step after the source, or None if no path exists within
    max_hops. The source itself is returned as the first tuple with a
    None edge."""

    if source_id == target_id:
        node = store.get_node(source_id)
        return [(node, None)] if node else None

    visited = {source_id}
    queue = deque([(source_id, [])])

    while queue:
        current_id, path_so_far = queue.popleft()

        if len(path_so_far) >= max_hops:
            continue

        for edge in store.list_edges(entity_id=current_id, direction="both", status=status, limit=MAX_LIMIT):
            neighbor_id = edge.target_id if edge.source_id == current_id else edge.source_id
            if neighbor_id in visited:
                continue

            new_path = path_so_far + [(neighbor_id, edge)]

            if neighbor_id == target_id:
                source_node = store.get_node(source_id)
                steps: List[Tuple[Any, Any]] = [(source_node, None)]
                for step_id, step_edge in new_path:
                    steps.append((store.get_node(step_id), step_edge))
                return steps

            visited.add(neighbor_id)
            queue.append((neighbor_id, new_path))

    return None


def graph_path(
    store: GraphStore,
    source_id: str,
    target_id: str,
    max_hops: int = 4,
    status: str = "ACTIVE",
) -> Optional[List[Dict[str, Any]]]:
    """Bounded shortest path (BFS, never unbounded DFS/recursion) as an
    ordered list of {entity, edge} steps, or None when no path exists
    within max_hops (never an exception). max_hops is always clamped to
    MAX_HOPS_CEILING regardless of caller input."""
    max_hops = _clamp_hops(max_hops)

    if store.get_node(source_id) is None or store.get_node(target_id) is None:
        return None

    steps = _bfs_shortest_path(store, source_id, target_id, max_hops, status)
    if steps is None:
        return None

    return [
        {
            "entity": node.to_dict() if node else None,
            "edge": edge.to_dict() if edge else None,
        }
        for node, edge in steps
    ]


def graph_explain(
    store: GraphStore,
    source_id: str,
    target_id: str,
    max_hops: int = 4,
    status: str = "ACTIVE",
) -> Dict[str, Any]:
    """Why are these two entities connected: the bounded path plus,
    for each edge on it, its own provenance/confidence/status - real
    citations the Brain can relay, never a generated narrative (that
    remains the Brain's own job, over this structured output)."""
    path = graph_path(store, source_id, target_id, max_hops=max_hops, status=status)

    if path is None:
        return {"path": None, "provenance": [], "confidence_status": []}

    provenance = [
        step["edge"]["provenance"] for step in path if step["edge"] is not None
    ]
    confidence_status = [
        {"confidence": step["edge"]["confidence"], "status": step["edge"]["status"]}
        for step in path
        if step["edge"] is not None
    ]

    return {
        "path": path,
        "provenance": provenance,
        "confidence_status": confidence_status,
    }


def graph_impact(
    store: GraphStore,
    entity_id: str,
    relationship_types: Optional[List[str]] = ("DEPENDS_ON", "AFFECTS"),
    direction: str = "incoming",
    max_hops: int = 3,
    status: str = "ACTIVE",
) -> List[Dict[str, Any]]:
    """Bounded reverse/forward traversal along the named relationship
    types: 'what would be affected if entity_id changed.' Read-only,
    reporting-only - this result is context a human or the Brain reads;
    nothing in the dispatcher/approval path ever calls this function
    (test_graph_authority_boundary.py), and it must never be treated as
    a trigger for any execution decision."""
    max_hops = _clamp_hops(max_hops)
    wanted_types = set(relationship_types) if relationship_types else None

    if store.get_node(entity_id) is None:
        return []

    visited = {entity_id}
    frontier = [entity_id]
    impacted: List[Dict[str, Any]] = []

    for _ in range(max_hops):
        next_frontier = []
        for current_id in frontier:
            edges = store.list_edges(
                entity_id=current_id, direction=direction, status=status, limit=MAX_LIMIT
            )
            for edge in edges:
                if wanted_types and edge.relationship_type not in wanted_types:
                    continue
                neighbor_id = (
                    edge.source_id if direction == "incoming" else edge.target_id
                )
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)
                neighbor = store.get_node(neighbor_id)
                if neighbor is None:
                    continue
                impacted.append({"entity": neighbor.to_dict(), "edge": edge.to_dict()})
                next_frontier.append(neighbor_id)
        frontier = next_frontier
        if not frontier:
            break

    return impacted[:MAX_LIMIT]


def graph_self_context(store: GraphStore, user_id: str, limit: int = 10) -> Dict[str, Any]:
    """The one call orchestrator.py needs (kept out of orchestrator.py
    itself per the standing 'orchestrator.py must never grow' rule -
    new behavior belongs in a separately-callable module, invoked from
    the orchestrator, not written inside it): the current principal's
    own User node (if ever graph-ingested) plus its bounded direct
    ACTIVE neighbors, already wrapped in the Brain-facing envelope.
    Deliberately narrow - never a free-text graph-wide search, so this
    never grows the Brain's default per-turn context size (plan
    section 10). Read-only; degrades to the all-empty shape when the
    user has no graph presence yet or user_id is falsy."""
    if not user_id:
        return build_graph_context()

    self_node = store.get_node_by_external_ref("User", user_id)
    if self_node is None:
        return build_graph_context()

    record = graph_get_entity(store, self_node.entity_id, limit=limit)
    if record is None:
        return build_graph_context()

    # graph_neighbors already pairs each neighbor with the exact edge
    # connecting it to self_node - record["edges"] covers the same
    # incident-edge set, so only neighbors' edges are used here to
    # avoid double-counting the same edge twice.
    neighbors = graph_neighbors(store, self_node.entity_id, limit=limit)
    entities = [record["entity"]] + [n["entity"] for n in neighbors]
    relationships = [n["edge"] for n in neighbors]

    return build_graph_context(
        entities=entities,
        relationships=relationships,
        provenance=[e.get("provenance", {}) for e in entities],
        confidence_status=[
            {"confidence": r.get("confidence"), "status": r.get("status")} for r in relationships
        ],
    )
