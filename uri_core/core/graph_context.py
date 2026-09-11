"""M23: the Brain-facing bounded graph context envelope (see
docs/plans/M23_GRAPH_INTELLIGENCE_PLAN.md section 10).

Mirrors query_context.py's own discipline exactly: pure, no storage
access of its own, every input already computed by the caller
(orchestrator.py). Never imported by dispatcher.py/approval_gate.py/
capability_registry.py/capability_resolver.py/approval_store.py (same
boundary query_context.py already holds - see
test_graph_authority_boundary.py), and never calls
uri_core.core.model_providers/model_router.

The runtime decides what graph data may be returned, user ownership,
source validity, limits, and authorization (see graph_engine.py's own
bounding and graph_store.py's per-user isolation) - this module only
shapes already-decided, already-bounded pieces into one consistent,
labeled envelope for the Brain to read. It decides nothing and selects
nothing itself.
"""

from typing import Any, Dict, List, Optional


def build_graph_context(
    entities: Optional[List[Dict[str, Any]]] = None,
    relationships: Optional[List[Dict[str, Any]]] = None,
    paths: Optional[List[Dict[str, Any]]] = None,
    provenance: Optional[List[Dict[str, Any]]] = None,
    confidence_status: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Assembles one bounded, labeled dict - never prose, never
    free-form instruction text. Any argument may be omitted (None) -
    the corresponding section degrades to an empty list rather than
    being guessed at, matching query_context.py's own "unknown-safe"
    discipline.

    - entities: node dicts (see graph_store.GraphNode.to_dict()) the
      caller already resolved and bounded via graph_engine.py.
    - relationships: edge dicts (see graph_store.GraphEdge.to_dict())
      already resolved and bounded the same way.
    - paths: graph_engine.graph_path()/graph_explain() output, already
      computed by the caller.
    - provenance: the provenance object(s) behind whatever is included
      above - preserved verbatim, never summarized away, so "why does
      URI believe this" stays traceable to a real source record.
    - confidence_status: {confidence, status} pairs for whatever edges
      are included above - lets the Brain see which relationships are
      current (ACTIVE) versus historical, without needing to re-derive
      it from raw edge dicts.
    """
    return {
        "entities": entities or [],
        "relationships": relationships or [],
        "paths": paths or [],
        "provenance": provenance or [],
        "confidence_status": confidence_status or [],
    }
