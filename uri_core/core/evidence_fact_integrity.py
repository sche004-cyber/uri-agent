import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from uri_core.core.security_guards import (
    MAX_METADATA_VALUE_LENGTH,
    looks_like_credential_key,
    looks_like_credential_value,
)


"""
Evidence infrastructure (tier 1 of the trust progression).

    Evidence
        -> EvidenceRecord / EvidenceStore   (this module)
        -> canonical Fact                   (uri_core.core.facts)
        -> verification state + provenance  (Fact.verify(), Fact.evidence_ids)
        -> SessionState / orchestrator       (future integration)

This module intentionally holds ONLY the observed/retrieved-evidence
tier. It does not model facts, claims, or verification - those live
on the canonical `Fact` (uri_core.core.facts), which now carries its
own `evidence_ids`, `confidence`, and `verify()`. An earlier version
of this module also defined a separate FactClaim/EvidenceFactLedger
that duplicated Fact's name/value/status concept as a second,
parallel store; that has been removed in favor of this single-
canonical-Fact design (see the architecture checkpoint that approved
this change).

`EvidenceStore` is a persistence abstraction so a future file/
database-backed implementation can replace InMemoryEvidenceStore
without changing callers.
"""


# An evidence excerpt is the evidentiary content itself, not an
# annotation - unlike metadata, it should not be squeezed down to a
# small fixed size or legitimate institutional evidence (a full OCR
# paragraph, a multi-row extract, a quoted clause) would be
# truncated or rejected. This bound exists only to stop this store
# from becoming a second copy of entire raw source documents.
MAX_EXCERPT_LENGTH = 10000


class IntegrityValidationError(ValueError):
    """Raised when an evidence record fails deterministic
    validation (including the credential/size guard)."""


class ProvenanceError(ValueError):
    """Raised when a claim references evidence that does not
    exist in the store."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_metadata(metadata: Dict[str, Any]) -> None:

    if not isinstance(metadata, dict):
        raise IntegrityValidationError("metadata must be a dict")

    for key, value in metadata.items():

        if looks_like_credential_key(key):
            raise IntegrityValidationError(
                f"metadata key '{key}' looks credential-related "
                "and is not permitted"
            )

        if isinstance(value, str):

            if looks_like_credential_value(value):
                raise IntegrityValidationError(
                    f"metadata value for key '{key}' looks like a "
                    "credential and is not permitted"
                )

            if len(value) > MAX_METADATA_VALUE_LENGTH:
                raise IntegrityValidationError(
                    f"metadata value for key '{key}' exceeds "
                    f"{MAX_METADATA_VALUE_LENGTH} characters"
                )


@dataclass
class EvidenceRecord:
    """
    Something URI actually observed or retrieved: an email, a PDF,
    a spreadsheet row, a manual note.

    `excerpt` is the evidentiary content relied upon. It is bounded
    (MAX_EXCERPT_LENGTH) only to stop this store from silently
    becoming a duplicate copy of entire raw source documents - it
    is not meant to constrain normal evidence processing.
    """

    source_type: str

    evidence_id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )

    retrieved_at: str = field(default_factory=_utc_now)

    source_reference: Optional[str] = None
    excerpt: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):

        if not self.source_type or not isinstance(
            self.source_type, str
        ):
            raise IntegrityValidationError(
                "source_type is required and must be a "
                "non-empty string"
            )

        if self.source_reference is not None:

            if looks_like_credential_value(self.source_reference):
                raise IntegrityValidationError(
                    "source_reference looks like a credential and "
                    "is not permitted"
                )

        if self.excerpt is not None:

            if looks_like_credential_value(self.excerpt):
                raise IntegrityValidationError(
                    "excerpt looks like a credential and is not "
                    "permitted"
                )

            if len(self.excerpt) > MAX_EXCERPT_LENGTH:
                raise IntegrityValidationError(
                    f"excerpt exceeds {MAX_EXCERPT_LENGTH} "
                    "characters"
                )

        _validate_metadata(self.metadata)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EvidenceStore(ABC):
    """
    Persistence abstraction for evidence records. Concrete backends
    (in-memory, file, database) implement this interface; callers
    never depend on a specific backend.
    """

    @abstractmethod
    def add(self, record: EvidenceRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, evidence_id: str) -> Optional[EvidenceRecord]:
        raise NotImplementedError

    @abstractmethod
    def query(
        self, source_type: Optional[str] = None
    ) -> List[EvidenceRecord]:
        raise NotImplementedError

    @abstractmethod
    def resolve(
        self, evidence_ids: List[str]
    ) -> List[EvidenceRecord]:
        raise NotImplementedError


class InMemoryEvidenceStore(EvidenceStore):
    """
    Append-only in-memory evidence store, suitable for tests and
    any in-process use where durability isn't required.
    """

    def __init__(self):
        self._records: Dict[str, EvidenceRecord] = {}
        self._order: List[str] = []

    def add(self, record: EvidenceRecord) -> None:

        if not isinstance(record, EvidenceRecord):
            raise IntegrityValidationError(
                "only EvidenceRecord instances may be added"
            )

        self._records[record.evidence_id] = record
        self._order.append(record.evidence_id)

    def get(self, evidence_id: str) -> Optional[EvidenceRecord]:
        return self._records.get(evidence_id)

    def query(
        self, source_type: Optional[str] = None
    ) -> List[EvidenceRecord]:

        results = [self._records[eid] for eid in self._order]

        if source_type is not None:
            results = [
                r for r in results if r.source_type == source_type
            ]

        return results

    def resolve(
        self, evidence_ids: List[str]
    ) -> List[EvidenceRecord]:
        """
        Resolve a canonical Fact's evidence_ids against this store.
        Raises ProvenanceError if any referenced id is unknown -
        this is how "invalid provenance" is caught.
        """

        resolved = []

        for evidence_id in evidence_ids:

            record = self._records.get(evidence_id)

            if record is None:
                raise ProvenanceError(
                    f"unknown evidence_id '{evidence_id}'"
                )

            resolved.append(record)

        return resolved


class EvidenceLedger:
    """
    Convenience facade over an EvidenceStore. This is the entry
    point future orchestrator/workflow/tool code should call to
    record evidence and resolve a Fact's provenance, without
    depending on how evidence is actually persisted.
    """

    def __init__(self, store: Optional[EvidenceStore] = None):

        if store is not None:
            self.store = store
        else:
            self.store = InMemoryEvidenceStore()

    def record(
        self,
        source_type: str,
        source_reference: Optional[str] = None,
        excerpt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EvidenceRecord:

        record = EvidenceRecord(
            source_type=source_type,
            source_reference=source_reference,
            excerpt=excerpt,
            metadata=dict(metadata or {}),
        )

        self.store.add(record)

        return record

    def get(self, evidence_id: str) -> Optional[EvidenceRecord]:
        return self.store.get(evidence_id)

    def for_source_type(
        self, source_type: str
    ) -> List[EvidenceRecord]:
        return self.store.query(source_type=source_type)

    def resolve_for_fact(self, fact) -> List[EvidenceRecord]:
        """
        Resolve the evidence supporting a canonical Fact (any
        object exposing `.evidence_ids`).
        """
        return self.store.resolve(list(fact.evidence_ids))
