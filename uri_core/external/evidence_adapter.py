"""Ledger-backed compatibility projections for legacy evidence consumers.

The record in ``EvidenceLedger`` is the sole authority.  Dicts returned here
are bounded, derived views retained only for existing workflow consumers.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from uri_core.core.evidence_fact_integrity import EvidenceLedger, EvidenceRecord
from uri_core.external.operation_store import FileOperationStore, OperationRecord
from uri_core.external.result_normalizer import normalize_evidence_result, project_evidence


def _text(value: Any) -> Optional[str]:
    return None if value is None else str(value)


def _render_evidence_markdown(item: Mapping[str, Any]) -> str:
    lines = [f"### {item.get('title') or '(untitled)'}"]
    detail_bits = [f"Type: {item['source_type']}"]
    if item.get("author"):
        detail_bits.append(f"From: {item['author']}")
    if item.get("date"):
        detail_bits.append(f"Date: {item['date']}")
    lines.extend((" | ".join(detail_bits), "", item.get("content") or ""))
    if item.get("source_locator"):
        lines.extend(("", f"Link: {item['source_locator']}"))
    return "\n".join(lines).strip()


def make_legacy_evidence_projection(
    *,
    source_type: str,
    source_id: Any = None,
    title: Any = None,
    content: Any = "",
    author: Any = None,
    date: Any = None,
    source_locator: Any = None,
    metadata: Optional[Mapping[str, Any]] = None,
    max_content_chars: int,
    ledger: Optional[EvidenceLedger] = None,
    evidence_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Normalize then persist once, returning the historic dict projection.

    ``ledger`` is mandatory on the authenticated production path.  It remains
    optional only for older isolated orchestrator tests that have no user
    context; those views are never installed as a durable production store.
    """
    record_metadata = dict(metadata or {})
    record_metadata.update({
        "legacy_source_id": _text(source_id),
        "legacy_title": _text(title),
        "legacy_author": _text(author),
        "legacy_date": _text(date),
    })
    record = normalize_evidence_result(
        source_type=source_type,
        source_reference=_text(source_locator),
        excerpt=content,
        metadata=record_metadata,
        evidence_id=evidence_id,
    )
    if ledger is not None:
        existing = ledger.get(record.evidence_id)
        if existing is None:
            ledger.store.add(record)
        else:
            record = existing
    return project_legacy_evidence_record(record, max_content_chars=max_content_chars)


def project_legacy_evidence_record(
    record: EvidenceRecord, *, max_content_chars: int
) -> Dict[str, Any]:
    """Render one authoritative record as the historic workflow view."""
    projection = project_evidence(record, max_length=max_content_chars)
    safe_metadata = dict(record.metadata)
    safe_metadata.pop("legacy_source_id", None)
    safe_metadata.pop("legacy_title", None)
    safe_metadata.pop("legacy_author", None)
    safe_metadata.pop("legacy_date", None)
    # Nested metadata preserves the existing top-level dict contract while
    # carrying the authoritative identity through persisted workflow state.
    safe_metadata["evidence_id"] = record.evidence_id
    if projection["truncation_disclosure"]:
        safe_metadata["truncation_disclosure"] = projection["truncation_disclosure"]
    item = {
        "source_type": record.source_type,
        "source_id": record.metadata.get("legacy_source_id"),
        "title": record.metadata.get("legacy_title"),
        "content": projection["content"],
        "author": record.metadata.get("legacy_author"),
        "date": record.metadata.get("legacy_date"),
        "source_locator": record.source_reference,
        "metadata": safe_metadata,
        "truncated": projection["truncated"],
        "provenance": None,
    }
    item["markdown"] = _render_evidence_markdown(item)
    return item


def resolve_legacy_evidence_projection(
    *, ledger: EvidenceLedger, item: Mapping[str, Any], max_content_chars: int
) -> Dict[str, Any]:
    """Rehydrate a derived workflow view from its authoritative record."""
    metadata = item.get("metadata")
    evidence_id = metadata.get("evidence_id") if isinstance(metadata, Mapping) else None
    if not isinstance(evidence_id, str) or not evidence_id:
        raise ValueError("derived evidence projection has no authoritative evidence_id")
    record = ledger.get(evidence_id)
    if record is None:
        raise ValueError("authoritative evidence_id is unavailable")
    return project_legacy_evidence_record(record, max_content_chars=max_content_chars)


def complete_operation_feedback(
    *,
    operation_store: FileOperationStore,
    ledger: EvidenceLedger,
    operation_id: str,
    completion: Mapping[str, Any],
    source_type: str = "external_operation",
) -> Optional[Dict[str, Any]]:
    """Persist one completion and one authoritative evidence record.

    The operation's durable evidence id makes replay safe across a crash after
    evidence persistence but before the one-time completion claim is saved.
    """
    operation = operation_store.complete(operation_id, completion)
    record = normalize_evidence_result(
        source_type=source_type,
        source_reference=operation.upstream_job_id or operation.operation_id,
        excerpt=completion.get("excerpt") if isinstance(completion, Mapping) else None,
        metadata={
            "operation_id": operation.operation_id,
            "capability_id": operation.capability_id,
            "action": operation.action,
            "completion": dict(completion),
        },
        evidence_id=operation.completion_evidence_id,
    )
    existing = ledger.get(record.evidence_id)
    if existing is None:
        ledger.store.add(record)
    else:
        record = existing
    if operation_store.claim_completion(operation.operation_id) is None:
        return None
    return project_legacy_evidence_record(record, max_content_chars=4000)
