"""Offline M33.3 S4 source evidence boundary. No production imports use this module."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Mapping, Sequence

from uri_v1.turn.rar_contracts import (
    RARCandidate,
    RARDeterministicAnchor,
    RAREvidence,
    RARQuery,
)

MAX_CANDIDATES = 16
MAX_RECORD_BYTES = 16_384


class SourceBoundaryError(ValueError):
    """The offline input cannot be safely projected into a RAR query."""


@dataclass(frozen=True)
class SourceRecord:
    candidate_id: str
    title: str
    candidate_type: str
    source_kind: str
    locator: str
    created_at: str | None
    domain_tags: tuple[str, ...]
    owner: str | None
    is_attachment: bool


@dataclass(frozen=True)
class SourceSnapshot:
    raw_user_text: str
    turn_attachments: tuple[str, ...]
    candidate_ids: tuple[str, ...]
    records: tuple[SourceRecord, ...]
    record_bytes: int


@dataclass(frozen=True)
class EvidenceEnvelope:
    records: tuple[SourceRecord, ...]
    authorized_ids: tuple[str, ...]
    current_turn_attachment_ids: tuple[str, ...]
    authorization_basis: str = "variant_available_candidates"


def _record(candidate_id: str, entry: Mapping[str, object]) -> SourceRecord:
    if not candidate_id or not isinstance(candidate_id, str):
        raise SourceBoundaryError("invalid candidate ID")
    if entry.get("candidate_id") != candidate_id:
        raise SourceBoundaryError("source record ID mismatch")
    representation = entry.get("representation")
    if representation == "file_reference_shape":
        ref = entry.get("file_reference")
        extra = entry.get("benchmark_added")
        if not isinstance(ref, dict) or not isinstance(extra, dict) or ref.get("file_id") != candidate_id:
            raise SourceBoundaryError("file source ID mismatch")
        title, kind = ref.get("filename"), extra.get("object_type")
        source_kind, is_attachment = "file_snapshot", True
        created_at = extra.get("created_at")
        tags: tuple[str, ...] = ()
        owner = None
    elif representation == "synthetic_minimal":
        obj = entry.get("synthetic_minimal", entry)
        if not isinstance(obj, Mapping):
            raise SourceBoundaryError("missing synthetic source")
        title, kind = obj.get("title"), obj.get("object_type")
        source_kind, is_attachment = "synthetic_authorized_source", False
        created_at = obj.get("created_at")
        tags = tuple(str(obj[k]) for k in ("origin", "status", "direction", "counterparty") if obj.get(k))
        owner = obj.get("owner")
    else:
        raise SourceBoundaryError("unsupported source type")
    if not isinstance(title, str) or not title or not isinstance(kind, str) or not kind:
        raise SourceBoundaryError("missing source title/type")
    if created_at is not None and not isinstance(created_at, str):
        raise SourceBoundaryError("invalid source time")
    if owner is not None and not isinstance(owner, str):
        raise SourceBoundaryError("invalid source owner")
    return SourceRecord(candidate_id, title, kind, source_kind,
                        f"fixture://candidate_library/{candidate_id}", created_at, tags, owner, is_attachment)


def build_snapshot(raw_user_text: str, conversation_context: Mapping[str, object],
                   available_candidates: Sequence[str], candidate_library: Mapping[str, object]) -> SourceSnapshot:
    """Allowlist input fields; scorer fields never enter this function."""
    if not isinstance(raw_user_text, str) or not isinstance(conversation_context, Mapping):
        raise SourceBoundaryError("invalid raw turn or session context")
    ids = tuple(available_candidates)
    if len(ids) > MAX_CANDIDATES:
        raise SourceBoundaryError("candidate cap exceeded")
    if len(ids) != len(set(ids)):
        raise SourceBoundaryError("duplicate candidate IDs")
    attachments = conversation_context.get("turn_attachments") or ()
    if not isinstance(attachments, (tuple, list)) or not all(isinstance(x, str) for x in attachments):
        raise SourceBoundaryError("invalid attachments")
    records = []
    for cid in ids:
        if not isinstance(cid, str) or cid not in candidate_library:
            raise SourceBoundaryError("unknown or invalid candidate ID")
        entry = candidate_library[cid]
        if not isinstance(entry, Mapping):
            raise SourceBoundaryError("invalid source record")
        records.append(_record(cid, entry))
    payload = [r.__dict__ for r in records]
    record_bytes = len(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    if record_bytes > MAX_RECORD_BYTES:
        raise SourceBoundaryError("source record byte cap exceeded")
    return SourceSnapshot(raw_user_text, tuple(attachments), ids, tuple(records), record_bytes)


def make_envelope(snapshot: SourceSnapshot) -> EvidenceEnvelope:
    authorized = set(snapshot.candidate_ids)
    if tuple(r.candidate_id for r in snapshot.records) != snapshot.candidate_ids:
        raise SourceBoundaryError("candidate set/order mismatch")
    return EvidenceEnvelope(snapshot.records, snapshot.candidate_ids,
                            tuple(a for a in snapshot.turn_attachments if a in authorized))


def _intact(text: str, value: str) -> bool:
    return bool(re.search(r"(?<!\w)" + re.escape(value) + r"(?!\w)", text, re.IGNORECASE))


def _anchor(snapshot: SourceSnapshot, envelope: EvidenceEnvelope) -> tuple[RARDeterministicAnchor | None, str]:
    ids = [r.candidate_id for r in envelope.records if _intact(snapshot.raw_user_text, r.candidate_id)]
    titles = [r.candidate_id for r in envelope.records if _intact(snapshot.raw_user_text, r.title)]
    attachments = envelope.current_turn_attachment_ids if len(snapshot.turn_attachments) == 1 else ()
    unique_id = ids[0] if len(ids) == 1 else None
    unique_title = titles[0] if len(titles) == 1 else None
    unique_attachment = attachments[0] if len(attachments) == 1 else None
    asserted = {x for x in (unique_id, unique_title, unique_attachment) if x}
    if len(asserted) > 1 or len(ids) > 1 or len(titles) > 1:
        return None, "conflict_or_nonunique"
    if not asserted:
        return None, "none"
    return RARDeterministicAnchor(exact_id=unique_id, unique_title_match=unique_title,
                                  current_attachment_id=unique_attachment), "+".join(
        label for label, value in (("exact_id", unique_id), ("unique_title", unique_title),
                                   ("current_attachment", unique_attachment)) if value)


def _scope_to_reference(anchor: RARDeterministicAnchor | None, origin: str, envelope: EvidenceEnvelope,
                        reference_expression: str) -> tuple[RARDeterministicAnchor | None, str]:
    """A RARQuery resolves one reference expression, so a lexical ID/title anchor is
    delivered only to a span that itself contains that ID/title intact. The turn-level
    attachment anchor stays turn-scoped (User decision, 2026-09-27 S4 audit)."""
    if anchor is None:
        return None, origin
    exact_id = anchor.exact_id if anchor.exact_id and _intact(reference_expression, anchor.exact_id) else None
    title_id = None
    if anchor.unique_title_match:
        title = next(r.title for r in envelope.records if r.candidate_id == anchor.unique_title_match)
        title_id = anchor.unique_title_match if _intact(reference_expression, title) else None
    attachment = anchor.current_attachment_id
    labels = [label for label, value in (("exact_id", exact_id), ("unique_title", title_id),
                                         ("current_attachment", attachment)) if value]
    if not labels:
        return None, "turn_anchor_not_in_span"
    return RARDeterministicAnchor(exact_id=exact_id, unique_title_match=title_id,
                                  current_attachment_id=attachment), "+".join(labels)


def project(snapshot: SourceSnapshot, envelope: EvidenceEnvelope, reference_expression: str,
            recency_hint: str | None = None, negation_spans: Sequence[str] = (),
            target_type_hint: str | None = None) -> tuple[RARQuery, str]:
    if envelope.authorized_ids != snapshot.candidate_ids:
        raise SourceBoundaryError("envelope authorization mismatch")
    anchor, origin = _scope_to_reference(*_anchor(snapshot, envelope), envelope, reference_expression)
    candidates = tuple(RARCandidate(id=r.candidate_id, title=r.title, candidate_type=r.candidate_type,
                                    recency_rank=0, domain_tags=r.domain_tags, owner=r.owner,
                                    is_attachment=r.is_attachment) for r in envelope.records)
    query = RARQuery(reference_expression=reference_expression, candidates=candidates,
                     local_evidence=RAREvidence(recency_hint=recency_hint,
                                                negation_spans=tuple(negation_spans),
                                                target_type_hint=target_type_hint),
                     deterministic_anchor=anchor)
    return query, origin
