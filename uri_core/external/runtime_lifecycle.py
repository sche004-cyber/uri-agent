"""M33.1 Batch 2 — runtime lifecycle operations with atomic live refresh.

Mutates authoritative external capability state in ExternalCapabilityStore,
synchronously republishes the external capability registry generation, swaps
live MultiActionDispatch registry & discovery references, and refreshes
Graphify indexes without server restart or context rebuild.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from uri_core.app.server import refresh_user_external_lifecycle


def register_and_refresh(
    context: Any,
    user_id: str,
    descriptor_data: Mapping[str, Any],
    *,
    source_revision: Optional[str] = None,
    dependency_lock: Optional[Mapping[str, str]] = None,
) -> Any:
    """Register a descriptor into the user's store and refresh live lifecycle."""
    with context.external_lifecycle_lock:
        store = context.external_capability_store
        result = store.register_descriptor(
            descriptor_data,
            user_id=user_id,
            source_revision=source_revision,
            dependency_lock=dependency_lock,
        )
        refresh_user_external_lifecycle(user_id, context=context)
        return result


def replace_qualified_and_refresh(
    context: Any,
    user_id: str,
    descriptor_data: Mapping[str, Any],
    *,
    source_revision: Optional[str] = None,
    dependency_lock: Optional[Mapping[str, str]] = None,
) -> Any:
    """Freshly qualify and atomically replace an already-managed descriptor.

    Callers stage and validate any immutable artifact before this function.
    A rejection leaves both durable and live state on the previous generation.
    """
    with context.external_lifecycle_lock:
        store = context.external_capability_store
        result = store.replace_qualified_descriptor(
            descriptor_data,
            user_id=user_id,
            source_revision=source_revision,
            dependency_lock=dependency_lock,
        )
        if result.ok:
            refresh_user_external_lifecycle(user_id, context=context)
        return result


def configure_and_refresh(context: Any, user_id: str, descriptor_id: str) -> Optional[Dict[str, Any]]:
    """Configure a qualified capability and refresh live lifecycle."""
    with context.external_lifecycle_lock:
        store = context.external_capability_store
        lifecycle = store.configure(user_id, descriptor_id)
        if lifecycle is not None:
            refresh_user_external_lifecycle(user_id, context=context)
        return lifecycle


def enable_and_refresh(context: Any, user_id: str, descriptor_id: str) -> Optional[Dict[str, Any]]:
    """Enable a qualified capability and synchronously propagate to live registry, discovery, and Graphify."""
    with context.external_lifecycle_lock:
        store = context.external_capability_store
        lifecycle = store.enable(user_id, descriptor_id)
        if lifecycle is not None:
            refresh_user_external_lifecycle(user_id, context=context)
        return lifecycle


def disable_and_refresh(context: Any, user_id: str, descriptor_id: str) -> Optional[Dict[str, Any]]:
    """Disable an active capability and synchronously retire from live registry, discovery, and Graphify."""
    with context.external_lifecycle_lock:
        store = context.external_capability_store
        lifecycle = store.disable(user_id, descriptor_id)
        if lifecycle is not None:
            refresh_user_external_lifecycle(user_id, context=context)
        return lifecycle


def remove_and_refresh(context: Any, user_id: str, descriptor_id: str) -> bool:
    """Hard-delete a capability descriptor and associated credentials, retiring immediately from live registry, discovery, and Graphify."""
    with context.external_lifecycle_lock:
        store = context.external_capability_store
        removed = store.remove(user_id, descriptor_id)
        if removed:
            refresh_user_external_lifecycle(user_id, context=context)
        return removed
