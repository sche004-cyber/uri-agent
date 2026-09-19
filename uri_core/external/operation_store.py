"""Durable, user-scoped operation ledger primitive for M33 Batch C."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional
from uuid import uuid4

from uri_core.core.evidence_fact_integrity import IntegrityValidationError, _atomic_write_json
from uri_core.core.portable_paths import DEFAULT_USER_STATE_ROOT, user_scoped_path

OPERATION_STORE_FILENAME = "operations.json"
OPERATION_STORE_SCHEMA_VERSION = "1.0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class OperationRecord:
    operation_id: str = field(default_factory=lambda: str(uuid4()))
    capability_id: str = ""
    action: str = ""
    scope: Dict[str, Any] = field(default_factory=dict)
    version: Optional[str] = None
    budget: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    upstream_job_id: Optional[str] = None
    status: str = "pending"
    completion: Optional[Dict[str, Any]] = None
    completion_evidence_id: Optional[str] = None
    completion_consumed: bool = False
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if not self.operation_id or not self.capability_id or not self.action:
            raise IntegrityValidationError("operation identity, capability_id and action are required")
        if self.status not in {"pending", "outcome_unknown", "completed"}:
            raise IntegrityValidationError("operation has invalid durable status")
        if not isinstance(self.scope, dict):
            raise IntegrityValidationError("operation scope must be a dict")
        if self.upstream_job_id is not None and not isinstance(self.upstream_job_id, str):
            raise IntegrityValidationError("upstream_job_id must be a string or None")
        if self.status == "completed" and not self.completion_evidence_id:
            raise IntegrityValidationError("completed operation has no durable evidence id")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FileOperationStore:
    """One-user durable operation ledger; it never submits or retries work."""

    def __init__(self, *, user_id: str, root: str = DEFAULT_USER_STATE_ROOT) -> None:
        self.user_id = user_id
        self._path = user_scoped_path(user_id, OPERATION_STORE_FILENAME, root=root)
        self._records: Dict[str, OperationRecord] = {}
        self._order: List[str] = []
        self._rehydrate()

    def _rehydrate(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r", encoding="utf-8") as handle:
                document = json.load(handle)
            if (
                not isinstance(document, dict)
                or document.get("schema_version") != OPERATION_STORE_SCHEMA_VERSION
            ):
                raise ValueError("unsupported operation schema")
            rows = document.get("operations")
            if not isinstance(rows, list):
                raise ValueError("operations missing")
            for row in rows:
                record = OperationRecord(**row)
                if record.operation_id in self._records:
                    raise ValueError("duplicate operation")
                self._records[record.operation_id] = record
                self._order.append(record.operation_id)
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            raise IntegrityValidationError("durable operation store cannot be read safely") from error

    def _save(self) -> None:
        _atomic_write_json(self._path, {
            "schema_version": OPERATION_STORE_SCHEMA_VERSION,
            "operations": [self._records[operation_id].to_dict() for operation_id in self._order],
        })

    def create(self, record: OperationRecord) -> OperationRecord:
        if record.operation_id in self._records:
            return self._records[record.operation_id]
        self._records[record.operation_id] = record
        self._order.append(record.operation_id)
        try:
            self._save()
        except BaseException:
            self._records.pop(record.operation_id, None)
            self._order.pop()
            raise
        return record

    def get(self, operation_id: str) -> Optional[OperationRecord]:
        return self._records.get(operation_id)

    def list_all(self) -> List[OperationRecord]:
        return [self._records[operation_id] for operation_id in self._order]

    def mark_outcome_unknown(self, operation_id: str) -> OperationRecord:
        return self._update(operation_id, status="outcome_unknown")

    def recovered_pending(self) -> List[OperationRecord]:
        """Return restart-recovered work without submitting or retrying it.

        C2 exposes durable state to the production composition seam only.  A
        later transport/cutover may reconcile an upstream job explicitly, but
        rehydration itself must never spend money or create duplicate work.
        """
        return [
            record for record in self.list_all()
            if record.status in {"pending", "outcome_unknown"}
        ]

    def complete(self, operation_id: str, completion: Mapping[str, Any]) -> OperationRecord:
        record = self._records.get(operation_id)
        if record is None:
            raise KeyError(operation_id)
        if record.status == "completed":
            return record
        return self._update(
            operation_id,
            status="completed",
            completion=dict(completion),
            completion_evidence_id=str(uuid4()),
        )

    def claim_completion(self, operation_id: str) -> Optional[OperationRecord]:
        record = self._records.get(operation_id)
        if record is None or record.status != "completed" or record.completion_consumed:
            return None
        return self._update(operation_id, completion_consumed=True)

    def _update(self, operation_id: str, **changes: Any) -> OperationRecord:
        record = self._records.get(operation_id)
        if record is None:
            raise KeyError(operation_id)
        previous = record.to_dict()
        for key, value in changes.items():
            setattr(record, key, value)
        record.updated_at = _utc_now()
        try:
            self._save()
        except BaseException:
            self._records[operation_id] = OperationRecord(**previous)
            raise
        return record
