"""Normalize untrusted adapter results into safe, bounded evidence records.

Composed in production via uri_core.external.evidence_adapter, which is
wired into orchestrator.py (C3 cutover) and server.py (operation
completion feedback).
"""

from __future__ import annotations

import re
from typing import Any, Dict, Mapping, Optional

from uri_core.core.evidence_fact_integrity import EvidenceRecord, MAX_EXCERPT_LENGTH
from uri_core.core.security_guards import looks_like_credential_key

MAX_EVIDENCE_PROJECTION_LENGTH = 4000
REDACTED = "[REDACTED]"

_SECRET_TEXT = re.compile(
    r"(?i)(?:bearer\s+[A-Za-z0-9._~+/=-]{6,}|(?:api[_-]?key|password|secret|token|authorization|access[_-]?token|refresh[_-]?token)\s*[:=]\s*(?:bearer\s+)?[A-Za-z0-9._~+/=-]{6,})"
)


def redact_text(value: Any) -> str:
    """Remove credential-shaped content before an EvidenceRecord exists."""
    return _SECRET_TEXT.sub(REDACTED, str(value or ""))


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        return redact_metadata(value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_value(item) for item in value]
    return value


def redact_metadata(metadata: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """Recursively remove credential keys and redact credential values."""
    safe: Dict[str, Any] = {}
    for key, value in dict(metadata or {}).items():
        if looks_like_credential_key(str(key)):
            continue
        safe[str(key)] = _redact_value(value)
    return safe


def normalize_evidence_result(
    *,
    source_type: str,
    source_reference: Optional[str] = None,
    excerpt: Any = None,
    metadata: Optional[Mapping[str, Any]] = None,
    evidence_id: Optional[str] = None,
) -> EvidenceRecord:
    """Redact, apply the stored 10k bound, then construct evidence.

    Truncation is represented in safe metadata so every later projection can
    disclose it rather than presenting a shortened excerpt as complete.
    """
    safe_excerpt = redact_text(excerpt) if excerpt is not None else None
    safe_metadata = redact_metadata(metadata)
    if source_reference is not None:
        source_reference = redact_text(source_reference)
    if safe_excerpt is not None and len(safe_excerpt) > MAX_EXCERPT_LENGTH:
        safe_metadata["excerpt_truncated"] = True
        safe_metadata["original_excerpt_length"] = len(safe_excerpt)
        safe_excerpt = safe_excerpt[:MAX_EXCERPT_LENGTH]
    return EvidenceRecord(
        source_type=source_type,
        **({"evidence_id": evidence_id} if evidence_id is not None else {}),
        source_reference=source_reference,
        excerpt=safe_excerpt,
        metadata=safe_metadata,
    )


def project_evidence(
    record: EvidenceRecord, *, max_length: int = MAX_EVIDENCE_PROJECTION_LENGTH
) -> Dict[str, Any]:
    """Produce the 4k model-context projection with explicit disclosure."""
    content = record.excerpt or ""
    truncated = bool(record.metadata.get("excerpt_truncated"))
    if len(content) > max_length:
        content = content[:max_length]
        truncated = True
    return {
        "evidence_id": record.evidence_id,
        "source_type": record.source_type,
        "source_reference": record.source_reference,
        "content": content,
        "truncated": truncated,
        "truncation_disclosure": (
            "Evidence content was truncated for this projection."
            if truncated else None
        ),
    }
