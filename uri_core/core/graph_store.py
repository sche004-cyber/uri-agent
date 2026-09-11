"""M23: per-user, SQLite-backed structured entity/relationship storage
(see docs/plans/M23_GRAPH_INTELLIGENCE_PLAN.md section 4).

One GraphStore per user_id, one SQLite file at
portable_paths.user_scoped_path(user_id, "graph.sqlite3") - the exact
same per-user-directory discipline MemoryStore/ExperienceStore/
FileStore already use (see server.py::_build_user_context). sqlite3 is
Python's standard library - this introduces zero new declared
dependency and starts no server/broker/cache process; each call opens
and closes its own connection (the same "open, do the thing, close"
shape every other store's JSON load/save already follows), guarded by
one process-local lock for write serialization.

This module is pure storage/CRUD. It never authorizes anything, is
never imported by dispatcher.py/approval_gate.py/capability_registry.py/
capability_resolver.py (see test_graph_authority_boundary.py), and
never calls a model. Deduplication is exact-key only (external_ref, or
a deterministic hash of (user_id, entity_type, normalized name)) - no
fuzzy/similarity matching in Phase 1 (see the plan's section 3/14 for
why entity resolution is explicitly future work).
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from uri_core.config.graph_schema import (
    GraphTypeRegistry,
    is_valid_entity_type,
    is_valid_relationship_type,
)
from uri_core.core.security_guards import looks_like_credential_value

SCHEMA_VERSION = "1.0"

DEFAULT_GRAPH_PATH = "uri_workspace/graph.sqlite3"

# Fixed namespace for deterministic entity/edge id derivation
# (uuid.uuid5) - never changes across installs, so the same
# (user_id, entity_type, normalized name) always derives the same id
# on any machine URI runs on (portability requirement, plan section 10).
_GRAPH_ID_NAMESPACE = uuid.UUID("2b9e1f3a-9b7a-4c1e-9c6a-6a2f6c9e6a1b")

_ACTIVE_STATUSES = {"ACTIVE", "HISTORICAL", "SUPERSEDED"}
_MAX_ATTRIBUTE_VALUE_LENGTH = 2000


class GraphValidationError(ValueError):
    """Raised when a node/edge write fails shape, type, or credential
    validation - never silently coerced or partially applied."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def derive_entity_id(user_id: str, entity_type: str, canonical_name: str) -> str:
    key = f"{user_id}:{entity_type}:{_normalize(canonical_name)}"
    return str(uuid.uuid5(_GRAPH_ID_NAMESPACE, key))


def derive_edge_id(source_id: str, target_id: str, relationship_type: str) -> str:
    key = f"{source_id}:{relationship_type}:{target_id}"
    return str(uuid.uuid5(_GRAPH_ID_NAMESPACE, key))


def _validate_attributes(attributes: Dict[str, Any]) -> None:
    for key, value in attributes.items():
        if not isinstance(key, str):
            raise GraphValidationError("Attribute keys must be strings.")
        if isinstance(value, str):
            if len(value) > _MAX_ATTRIBUTE_VALUE_LENGTH:
                raise GraphValidationError(
                    f"Attribute {key!r} exceeds {_MAX_ATTRIBUTE_VALUE_LENGTH} characters."
                )
            if looks_like_credential_value(value):
                raise GraphValidationError(
                    f"Attribute {key!r} looks like a credential and is not permitted."
                )


@dataclass
class GraphNode:
    entity_id: str
    entity_type: str
    canonical_name: str
    external_ref: Optional[str]
    attributes: Dict[str, Any]
    provenance: Dict[str, Any]
    created_at: str
    updated_at: str
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "canonical_name": self.canonical_name,
            "external_ref": self.external_ref,
            "attributes": self.attributes,
            "provenance": self.provenance,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "schema_version": self.schema_version,
        }


@dataclass
class GraphEdge:
    edge_id: str
    source_id: str
    target_id: str
    relationship_type: str
    attributes: Dict[str, Any]
    provenance: Dict[str, Any]
    confidence: Optional[float]
    status: str
    created_at: str
    updated_at: str
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type,
            "attributes": self.attributes,
            "provenance": self.provenance,
            "confidence": self.confidence,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "schema_version": self.schema_version,
        }


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS nodes (
    entity_id       TEXT PRIMARY KEY,
    entity_type     TEXT NOT NULL,
    canonical_name  TEXT NOT NULL,
    external_ref    TEXT,
    attributes_json TEXT NOT NULL DEFAULT '{}',
    provenance_json TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    schema_version  TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_nodes_external_ref
    ON nodes(entity_type, external_ref) WHERE external_ref IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_nodes_type ON nodes(entity_type);

CREATE TABLE IF NOT EXISTS edges (
    edge_id            TEXT PRIMARY KEY,
    source_id          TEXT NOT NULL,
    target_id          TEXT NOT NULL,
    relationship_type  TEXT NOT NULL,
    attributes_json     TEXT NOT NULL DEFAULT '{}',
    provenance_json     TEXT NOT NULL DEFAULT '{}',
    confidence          REAL,
    status               TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL,
    schema_version       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_edges_source
    ON edges(source_id, relationship_type, status);
CREATE INDEX IF NOT EXISTS ix_edges_target
    ON edges(target_id, relationship_type, status);
"""


class GraphStore:
    """One user's structured entity/relationship store. Construct with
    a storage_path pointed at that user's own
    uri_workspace/users/<user_id>/graph.sqlite3 (see server.py); the
    zero-arg default is the legacy-ambient single-install path, mirroring
    MemoryStore()/FileStore()'s own default-constructor convention."""

    def __init__(
        self,
        storage_path: str = DEFAULT_GRAPH_PATH,
        type_registry: Optional[GraphTypeRegistry] = None,
    ):
        self.storage_path = os.path.normpath(storage_path)
        self._lock = threading.Lock()
        self._type_registry = type_registry or GraphTypeRegistry()
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        folder = os.path.dirname(self.storage_path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        conn = sqlite3.connect(self.storage_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._lock:
            try:
                conn = self._connect()
                try:
                    conn.executescript(_SCHEMA_SQL)
                    conn.commit()
                finally:
                    conn.close()
            except sqlite3.DatabaseError:
                # Corrupted file (same "safe empty" discipline every
                # other store's corrupted-file path already follows) -
                # the bad file is renamed aside, never silently
                # deleted, and a fresh schema is created in its place.
                if os.path.exists(self.storage_path):
                    quarantine = f"{self.storage_path}.corrupted.{int(datetime.now(timezone.utc).timestamp())}"
                    os.replace(self.storage_path, quarantine)
                conn = self._connect()
                try:
                    conn.executescript(_SCHEMA_SQL)
                    conn.commit()
                finally:
                    conn.close()

    # ------------------------------------------------------------
    # Nodes
    # ------------------------------------------------------------

    def upsert_node(
        self,
        entity_type: str,
        canonical_name: str,
        attributes: Optional[Dict[str, Any]] = None,
        external_ref: Optional[str] = None,
        provenance: Optional[Dict[str, Any]] = None,
        user_id: str = "",
    ) -> GraphNode:
        if not is_valid_entity_type(entity_type):
            raise GraphValidationError(f"Invalid entity_type: {entity_type!r}")
        if not isinstance(canonical_name, str) or not canonical_name.strip():
            raise GraphValidationError("canonical_name must be a non-empty string.")

        attrs = attributes or {}
        _validate_attributes(attrs)
        prov = provenance or {}

        now = _now()

        with self._lock:
            conn = self._connect()
            try:
                existing_row = None
                if external_ref:
                    existing_row = conn.execute(
                        "SELECT entity_id, created_at FROM nodes "
                        "WHERE entity_type = ? AND external_ref = ?",
                        (entity_type, external_ref),
                    ).fetchone()

                if existing_row is None:
                    entity_id = derive_entity_id(user_id, entity_type, canonical_name)
                    existing_row = conn.execute(
                        "SELECT entity_id, created_at FROM nodes WHERE entity_id = ?",
                        (entity_id,),
                    ).fetchone()
                else:
                    entity_id = existing_row["entity_id"]

                created_at = existing_row["created_at"] if existing_row else now

                conn.execute(
                    """
                    INSERT INTO nodes
                        (entity_id, entity_type, canonical_name, external_ref,
                         attributes_json, provenance_json, created_at, updated_at,
                         schema_version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(entity_id) DO UPDATE SET
                        canonical_name = excluded.canonical_name,
                        external_ref = excluded.external_ref,
                        attributes_json = excluded.attributes_json,
                        provenance_json = excluded.provenance_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        entity_id,
                        entity_type,
                        canonical_name,
                        external_ref,
                        json.dumps(attrs),
                        json.dumps(prov),
                        created_at,
                        now,
                        SCHEMA_VERSION,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

        self._type_registry.register_entity_type(entity_type)

        return GraphNode(
            entity_id=entity_id,
            entity_type=entity_type,
            canonical_name=canonical_name,
            external_ref=external_ref,
            attributes=attrs,
            provenance=prov,
            created_at=created_at,
            updated_at=now,
        )

    def get_node(self, entity_id: str) -> Optional[GraphNode]:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM nodes WHERE entity_id = ?", (entity_id,)
                ).fetchone()
            finally:
                conn.close()
        return _row_to_node(row) if row else None

    def get_node_by_external_ref(self, entity_type: str, external_ref: str) -> Optional[GraphNode]:
        """Looks a node up by the exact-key identity upsert_node's
        external_ref index already enforces, rather than requiring a
        caller to re-derive canonical_name-dependent entity_id itself
        (which would drift if the node's canonical_name ever changed
        after first ingestion - external_ref is the stable identity,
        derive_entity_id is only a fallback for nodes with none)."""
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM nodes WHERE entity_type = ? AND external_ref = ?",
                    (entity_type, external_ref),
                ).fetchone()
            finally:
                conn.close()
        return _row_to_node(row) if row else None

    def delete_node(self, entity_id: str) -> bool:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute("DELETE FROM nodes WHERE entity_id = ?", (entity_id,))
                conn.execute(
                    "DELETE FROM edges WHERE source_id = ? OR target_id = ?",
                    (entity_id, entity_id),
                )
                conn.commit()
                return cur.rowcount > 0
            finally:
                conn.close()

    def list_nodes(
        self, entity_type: Optional[str] = None, name_contains: Optional[str] = None, limit: int = 50
    ) -> List[GraphNode]:
        limit = max(1, min(limit, 200))
        query = "SELECT * FROM nodes WHERE 1=1"
        params: List[Any] = []
        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type)
        if name_contains:
            query += " AND LOWER(canonical_name) LIKE ?"
            params.append(f"%{name_contains.lower()}%")
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(query, params).fetchall()
            finally:
                conn.close()
        return [_row_to_node(r) for r in rows]

    # ------------------------------------------------------------
    # Edges
    # ------------------------------------------------------------

    def upsert_edge(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        attributes: Optional[Dict[str, Any]] = None,
        provenance: Optional[Dict[str, Any]] = None,
        confidence: Optional[float] = None,
        status: str = "ACTIVE",
    ) -> GraphEdge:
        if not is_valid_relationship_type(relationship_type):
            raise GraphValidationError(f"Invalid relationship_type: {relationship_type!r}")
        if status not in _ACTIVE_STATUSES:
            raise GraphValidationError(f"Invalid edge status: {status!r}")
        if confidence is not None:
            if not isinstance(confidence, (int, float)) or not (0.0 <= float(confidence) <= 1.0):
                raise GraphValidationError(
                    f"confidence must be between 0 and 1, got {confidence!r}"
                )

        attrs = attributes or {}
        _validate_attributes(attrs)
        prov = provenance or {}

        with self._lock:
            conn = self._connect()
            try:
                source_row = conn.execute(
                    "SELECT 1 FROM nodes WHERE entity_id = ?", (source_id,)
                ).fetchone()
                target_row = conn.execute(
                    "SELECT 1 FROM nodes WHERE entity_id = ?", (target_id,)
                ).fetchone()
                if source_row is None or target_row is None:
                    raise GraphValidationError(
                        "Both source_id and target_id must reference existing nodes."
                    )

                edge_id = derive_edge_id(source_id, target_id, relationship_type)
                existing = conn.execute(
                    "SELECT created_at FROM edges WHERE edge_id = ?", (edge_id,)
                ).fetchone()
                now = _now()
                created_at = existing["created_at"] if existing else now

                conn.execute(
                    """
                    INSERT INTO edges
                        (edge_id, source_id, target_id, relationship_type,
                         attributes_json, provenance_json, confidence, status,
                         created_at, updated_at, schema_version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(edge_id) DO UPDATE SET
                        attributes_json = excluded.attributes_json,
                        provenance_json = excluded.provenance_json,
                        confidence = excluded.confidence,
                        status = excluded.status,
                        updated_at = excluded.updated_at
                    """,
                    (
                        edge_id,
                        source_id,
                        target_id,
                        relationship_type,
                        json.dumps(attrs),
                        json.dumps(prov),
                        confidence,
                        status,
                        created_at,
                        now,
                        SCHEMA_VERSION,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

        self._type_registry.register_relationship_type(relationship_type)

        return GraphEdge(
            edge_id=edge_id,
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            attributes=attrs,
            provenance=prov,
            confidence=confidence,
            status=status,
            created_at=created_at,
            updated_at=now,
        )

    def get_edge(self, edge_id: str) -> Optional[GraphEdge]:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM edges WHERE edge_id = ?", (edge_id,)
                ).fetchone()
            finally:
                conn.close()
        return _row_to_edge(row) if row else None

    def set_edge_status(self, edge_id: str, status: str) -> bool:
        if status not in _ACTIVE_STATUSES:
            raise GraphValidationError(f"Invalid edge status: {status!r}")
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    "UPDATE edges SET status = ?, updated_at = ? WHERE edge_id = ?",
                    (status, _now(), edge_id),
                )
                conn.commit()
                return cur.rowcount > 0
            finally:
                conn.close()

    def list_edges(
        self,
        entity_id: Optional[str] = None,
        relationship_type: Optional[str] = None,
        direction: str = "both",
        status: Optional[str] = "ACTIVE",
        limit: int = 50,
    ) -> List[GraphEdge]:
        limit = max(1, min(limit, 200))
        query = "SELECT * FROM edges WHERE 1=1"
        params: List[Any] = []

        if entity_id:
            if direction == "outgoing":
                query += " AND source_id = ?"
                params.append(entity_id)
            elif direction == "incoming":
                query += " AND target_id = ?"
                params.append(entity_id)
            else:
                query += " AND (source_id = ? OR target_id = ?)"
                params.extend([entity_id, entity_id])

        if relationship_type:
            query += " AND relationship_type = ?"
            params.append(relationship_type)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(query, params).fetchall()
            finally:
                conn.close()
        return [_row_to_edge(r) for r in rows]


def _row_to_node(row: sqlite3.Row) -> GraphNode:
    return GraphNode(
        entity_id=row["entity_id"],
        entity_type=row["entity_type"],
        canonical_name=row["canonical_name"],
        external_ref=row["external_ref"],
        attributes=json.loads(row["attributes_json"] or "{}"),
        provenance=json.loads(row["provenance_json"] or "{}"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        schema_version=row["schema_version"],
    )


def _row_to_edge(row: sqlite3.Row) -> GraphEdge:
    return GraphEdge(
        edge_id=row["edge_id"],
        source_id=row["source_id"],
        target_id=row["target_id"],
        relationship_type=row["relationship_type"],
        attributes=json.loads(row["attributes_json"] or "{}"),
        provenance=json.loads(row["provenance_json"] or "{}"),
        confidence=row["confidence"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        schema_version=row["schema_version"],
    )
