"""Lease ownership provenance (M33.3-R S10; Plan B R1.6, M33.2 §10).

Provider runtimes (LM Studio, Ollama, llama.cpp server) own residency: TTL,
idle unload, JIT loading and eviction stay provider-native. URI adds only what
it lacks: a record of which loaded instances URI itself created, so URI never
unloads or evicts a model it does not own. Seeing a model in LM Studio or
Ollama never implies permission to evict it.

Scope: one thread-safe ledger per server process (M33.2 §10), never per user.
Not wired into any production request path.
"""

from __future__ import annotations

from datetime import datetime, timezone
import threading
from typing import Dict, Iterable, List, Optional, Tuple
from uuid import uuid4

from .contracts import LEASE_OWNER_EXTERNAL, LEASE_OWNER_UNKNOWN, LEASE_OWNER_URI, RuntimeLease

URI_INSTANCE_PREFIX = "uri-lease-"


def new_uri_instance_id() -> str:
    """Provider-visible identifier for a URI-created load (e.g. `lms load --identifier`)."""
    return URI_INSTANCE_PREFIX + uuid4().hex[:12]


class LeaseOwnershipError(RuntimeError):
    pass


class LeaseOwnershipLedger:
    def __init__(self, owner_id: str = "uri-server") -> None:
        self.owner_id = owner_id
        self._lock = threading.RLock()
        self._active: Dict[str, RuntimeLease] = {}  # provider_instance_id -> lease

    def record_acquired(self, *, runtime_id: str, model_id: str, provider_instance_id: str,
                        placement: Optional[str] = None) -> RuntimeLease:
        if not provider_instance_id.startswith(URI_INSTANCE_PREFIX):
            raise LeaseOwnershipError("URI-owned loads must use a URI instance identifier")
        lease = RuntimeLease(lease_id=uuid4().hex, runtime_id=runtime_id, owner_kind=LEASE_OWNER_URI,
                             owner_id=self.owner_id, model_id=model_id, provider_instance_id=provider_instance_id,
                             acquired_at=datetime.now(timezone.utc).isoformat(), placement=placement)
        with self._lock:
            if provider_instance_id in self._active:
                raise LeaseOwnershipError("instance already leased")
            self._active[provider_instance_id] = lease
        return lease

    def owns(self, provider_instance_id: Optional[str]) -> bool:
        with self._lock:
            return bool(provider_instance_id) and provider_instance_id in self._active

    def may_unload(self, lease_or_instance: RuntimeLease | str) -> bool:
        instance = lease_or_instance.provider_instance_id if isinstance(lease_or_instance, RuntimeLease) else lease_or_instance
        return self.owns(instance)

    def require_may_unload(self, lease_or_instance: RuntimeLease | str) -> None:
        if not self.may_unload(lease_or_instance):
            raise LeaseOwnershipError("URI does not own this lease; refusing to unload or evict it")

    def record_released(self, provider_instance_id: str) -> RuntimeLease:
        with self._lock:
            lease = self._active.pop(provider_instance_id, None)
        if lease is None:
            raise LeaseOwnershipError("URI does not own this lease")
        return lease

    def active(self) -> Tuple[RuntimeLease, ...]:
        with self._lock:
            return tuple(self._active.values())

    def classify(self, runtime_id: str, observed: Iterable[Tuple[Optional[str], Optional[str]]]) -> List[RuntimeLease]:
        """Classify provider-observed (instance_id, model_id) pairs by owner.

        URI: in this ledger. EXTERNAL: a provider instance URI did not create
        (including a URI-prefixed identifier absent from the ledger, e.g. after
        a restart, which is reported but never auto-released). UNKNOWN: the
        provider exposes no instance identifier.
        """
        out: List[RuntimeLease] = []
        for instance_id, model_id in observed:
            with self._lock:
                owned = self._active.get(instance_id or "")
            if owned is not None:
                out.append(owned)
            elif instance_id:
                orphan = instance_id.startswith(URI_INSTANCE_PREFIX)
                out.append(RuntimeLease(lease_id=f"observed:{instance_id}", runtime_id=runtime_id,
                                        owner_kind=LEASE_OWNER_EXTERNAL,
                                        owner_id="uri-orphan-unverified" if orphan else None,
                                        model_id=model_id, provider_instance_id=instance_id))
            else:
                out.append(RuntimeLease(lease_id="observed:unknown", runtime_id=runtime_id,
                                        owner_kind=LEASE_OWNER_UNKNOWN, model_id=model_id))
        return out
