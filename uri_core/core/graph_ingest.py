"""M23: narrow, deterministic ingestion of graph nodes from EXISTING,
already-controlled sources only (see
docs/plans/M23_GRAPH_INTELLIGENCE_PLAN.md section 9).

This is Phase 1's entire ingestion surface. No model is ever called
here, no email/Drive/file content is ever read here, and nothing here
runs as a bulk background sweep - each function is a small, pure-ish
conversion called explicitly, once, at the real point an existing
store's record legitimately reaches an already-established, strict
status (Fact.status == "VERIFIED", MemoryEntry eligible for
personalization). Each function re-applies that source's own
eligibility gate itself, rather than trusting the caller - defense in
depth, the same discipline
docs/plans/M22_MEMORY_CONTEXT_RETRIEVAL_ARCHITECTURE.md required of its
own (separate) retrieval design.

Honest note on live wiring (recorded in docs/plans/M23_STATE.md's
audit in full): this repository's Fact.verify() method - the
accountable, non-model verification gate facts.py itself documents -
has no live caller anywhere in the current runtime; nor does
fact_manager.update_evidence_fact(), the only function that ever wrote
session.evidence_facts. ingest_fact() below is wired at
fact_manager.py's actual canonical status-transition functions
(update_fact/update_evidence_fact) so it fires correctly whenever
EITHER function legitimately produces a VERIFIED-status fact - but
because neither function's one current live caller
(orchestrator.py's _resume_active_workflow) ever constructs a
VERIFIED-status Fact today, ingest_fact() is correctly wired yet
currently dormant in live use, exactly like the pre-existing EXPIRED
fact-status gap the memory-retrieval proposal already named rather
than silently assumed solved. This is not a defect this milestone
introduces or is responsible for fixing - it is named here for
honesty, matching this codebase's existing practice.
"""

from __future__ import annotations

from typing import Optional

from uri_core.core.facts import Fact
from uri_core.core.graph_store import GraphNode, GraphStore
from uri_core.core.user_memory import MemoryEntry, is_eligible_for_personalization


def _link_to_user(store: GraphStore, node: Optional[GraphNode], user_id: str) -> None:
    """Connects a newly-ingested node to its owning user's own User
    node via BELONGS_TO, so the bounded graph_context Phase 1 exposes
    (orchestrator._build_graph_context - the User node's own direct
    neighbors) actually has something real to find. Ensures the User
    node exists first (lazy, idempotent - upsert_node is dedup-safe on
    a second call)."""
    if node is None:
        return
    user_node = ingest_user_account(store, user_id)
    if user_node is None:
        return
    store.upsert_edge(
        source_id=node.entity_id,
        target_id=user_node.entity_id,
        relationship_type="BELONGS_TO",
        provenance={"source_type": node.provenance.get("source_type"), "recorded_by": "system"},
    )


def ingest_fact(store: GraphStore, fact: Fact, user_id: str) -> Optional[GraphNode]:
    """Writes/updates one Fact-typed node - ONLY when fact.status ==
    'VERIFIED' (the strictest, accountable-actor status; see facts.py).
    A PROVISIONAL/CONFIRMED/HISTORICAL/SUPERSEDED/EXPIRED fact produces
    no node and returns None - this check is re-applied here even
    though a caller should already only be calling this for a verified
    fact, per this module's own defense-in-depth discipline. On
    success, also links the node to the owning user's own User node
    via BELONGS_TO (see _link_to_user)."""
    if fact.status != "VERIFIED":
        return None

    node = store.upsert_node(
        entity_type="Fact",
        canonical_name=fact.name,
        attributes={"value": str(fact.value)},
        external_ref=fact.name,
        provenance={
            "source_type": "fact",
            "source_id": fact.name,
            "recorded_by": "system",
            "evidence_status": fact.status,
        },
        user_id=user_id,
    )
    _link_to_user(store, node, user_id)
    return node


def ingest_memory_entry(store: GraphStore, entry: MemoryEntry, user_id: str) -> Optional[GraphNode]:
    """Writes/updates one Memory-typed node - ONLY when the entry is
    eligible for personalization (consent in {user_provided,
    user_confirmed}; see user_memory.is_eligible_for_personalization).
    A pending_confirmation entry produces no node and returns None -
    re-checked here regardless of what the caller already filtered on,
    per this module's own defense-in-depth discipline. On success,
    also links the node to the owning user's own User node via
    BELONGS_TO (see _link_to_user)."""
    if not is_eligible_for_personalization(entry):
        return None

    node = store.upsert_node(
        entity_type="Memory",
        canonical_name=entry.fact.name if entry.fact else entry.memory_id,
        attributes={
            "category": entry.category,
            "content": entry.fact.value if entry.fact else "",
        },
        external_ref=entry.memory_id,
        provenance={
            "source_type": "memory",
            "source_id": entry.memory_id,
            "recorded_by": "system",
            "evidence_status": entry.consent,
        },
        user_id=user_id,
    )
    _link_to_user(store, node, user_id)
    return node


def ingest_user_account(store: GraphStore, user_id: str, username: Optional[str] = None) -> Optional[GraphNode]:
    """Writes/updates exactly one User-typed node for this install's
    logged-in user_id - lazy (called at most once per graph
    interaction, never a bulk migration sweep across every account)."""
    if not user_id:
        return None

    return store.upsert_node(
        entity_type="User",
        canonical_name=username or user_id,
        external_ref=user_id,
        provenance={
            "source_type": "user_account",
            "source_id": user_id,
            "recorded_by": "system",
        },
        user_id=user_id,
    )
