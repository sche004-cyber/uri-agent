import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


MAX_METADATA_VALUE_LENGTH = 500

_SECRET_KEY_MARKERS = (
    "api_key",
    "apikey",
    "password",
    "secret",
    "token",
    "authorization",
    "auth_header",
    "access_token",
    "refresh_token",
    "credential",
    "private_key",
)

_SECRET_VALUE_PATTERN = re.compile(
    r"^(gsk_|sk-|AIza|AQ\.|Bearer\s)",
    re.IGNORECASE,
)


class AuditValidationError(ValueError):
    """Raised when an audit event fails deterministic validation."""


def _validate_metadata(metadata: Dict[str, Any]) -> None:

    if not isinstance(metadata, dict):
        raise AuditValidationError("metadata must be a dict")

    for key, value in metadata.items():

        lowered_key = str(key).lower()

        if any(
            marker in lowered_key for marker in _SECRET_KEY_MARKERS
        ):
            raise AuditValidationError(
                f"metadata key '{key}' looks credential-related "
                "and is not permitted in an audit event"
            )

        if isinstance(value, str):

            if _SECRET_VALUE_PATTERN.match(value.strip()):
                raise AuditValidationError(
                    f"metadata value for key '{key}' looks like a "
                    "credential and is not permitted in an audit event"
                )

            if len(value) > MAX_METADATA_VALUE_LENGTH:
                raise AuditValidationError(
                    f"metadata value for key '{key}' exceeds "
                    f"{MAX_METADATA_VALUE_LENGTH} characters; audit "
                    "events must not carry raw prompts/responses or "
                    "other large payloads"
                )


@dataclass
class AuditEvent:
    """
    A single structured, immutable-once-created audit record.

    Deliberately has no field for raw model prompts/responses or
    chain-of-thought - only small, structured metadata is permitted,
    and metadata is validated to reject anything credential-shaped.
    """

    event_type: str
    status: str

    event_id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )

    timestamp: str = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        ).isoformat()
    )

    session_id: Optional[str] = None
    workflow_id: Optional[str] = None
    capability: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):

        if not self.event_type or not isinstance(
            self.event_type, str
        ):
            raise AuditValidationError(
                "event_type is required and must be a "
                "non-empty string"
            )

        if not self.status or not isinstance(self.status, str):
            raise AuditValidationError(
                "status is required and must be a non-empty string"
            )

        _validate_metadata(self.metadata)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AuditEventStore(ABC):
    """
    Persistence abstraction for audit events.

    Concrete backends (in-memory, file, database) implement this
    interface. Callers depend only on this interface, never on a
    specific backend.
    """

    @abstractmethod
    def append(self, event: AuditEvent) -> None:
        raise NotImplementedError

    @abstractmethod
    def query(
        self,
        session_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        event_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[AuditEvent]:
        raise NotImplementedError


class InMemoryAuditEventStore(AuditEventStore):
    """
    Append-only in-memory event store. Suitable for tests and for
    any in-process use where durability isn't required.
    """

    def __init__(self):
        self._events: List[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:

        if not isinstance(event, AuditEvent):
            raise AuditValidationError(
                "only AuditEvent instances may be appended"
            )

        self._events.append(event)

    def query(
        self,
        session_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        event_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[AuditEvent]:

        results = self._events

        if session_id is not None:
            results = [
                e for e in results if e.session_id == session_id
            ]

        if workflow_id is not None:
            results = [
                e for e in results if e.workflow_id == workflow_id
            ]

        if event_type is not None:
            results = [
                e for e in results if e.event_type == event_type
            ]

        if status is not None:
            results = [e for e in results if e.status == status]

        return list(results)


class AuditTrail:
    """
    Convenience facade over an AuditEventStore.

    This is the entry point future orchestrator/workflow/tool code
    should call to record and retrieve audit events, without
    depending on how events are actually persisted.
    """

    def __init__(self, store: Optional[AuditEventStore] = None):

        if store is not None:
            self.store = store
        else:
            self.store = InMemoryAuditEventStore()

    def record(
        self,
        event_type: str,
        status: str,
        session_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        capability: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:

        event = AuditEvent(
            event_type=event_type,
            status=status,
            session_id=session_id,
            workflow_id=workflow_id,
            capability=capability,
            metadata=dict(metadata or {}),
        )

        self.store.append(event)

        return event

    def for_session(self, session_id: str) -> List[AuditEvent]:
        return self.store.query(session_id=session_id)

    def for_workflow(self, workflow_id: str) -> List[AuditEvent]:
        return self.store.query(workflow_id=workflow_id)

    def all_events(
        self, event_type: Optional[str] = None
    ) -> List[AuditEvent]:
        """
        Every recorded event, optionally narrowed to one event_type.
        Read-only - callers must not mutate the returned list's
        AuditEvent instances or rely on aliasing to self.store.
        """
        return self.store.query(event_type=event_type)
