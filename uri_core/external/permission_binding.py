"""M33 Batch B — permission binding: descriptor permissions bind to the
grant store on top of P1's corrected seam.

The explicit grant a new external capability id requires IS its own
lifecycle `enabled` flag (`uri_core/external/lifecycle.py`,
`uri_core/external/store.py`) - per-user, durable, atomic, and already
the product of a deliberate, explicit operator action (detect -> qualify
-> configure -> enable, each a separate step `LifecycleController`
refuses to skip). Inventing a second, parallel grant record for the same
fact would be two sources of truth for one authorization decision; this
module reads the one that already exists rather than duplicating it.

This is deliberately NOT `uri_core.core.capability_resolver.
CapabilityGrantsStore` - that store's own documented "zero-behaviour-
change migration default" means a user with no persisted grant record
defaults to the FULL current registry ceiling (`capability_resolver.py`
`get_grants()`'s own docstring). That default is correct for the legacy
capability set it was built for, and exactly wrong here: a new external
capability id must never be reachable for a user who has never touched
it. `external_permission_resolver()` below fails closed on every missing
record - there is no ceiling to fall back to.
"""

from __future__ import annotations

from typing import Any, Optional

from uri_core.external.registry_bridge import ExternalCapabilityPublisher
from uri_core.external.store import ExternalCapabilityStore

_shared_publisher = ExternalCapabilityPublisher()


def _principal_user_id(principal: Any) -> Optional[str]:
    user_id = getattr(principal, "user_id", None)
    return user_id if isinstance(user_id, str) and user_id else None


def external_permission_resolver(
    capability_id: str,
    principal: Any,
    *,
    publisher: Optional[ExternalCapabilityPublisher] = None,
) -> bool:
    """The one authorization question this module answers: is
    `capability_id` an external capability this exact `principal` has
    explicitly enabled? Fails closed on every ambiguous or missing case:
    no principal, no user_id, no store record, not qualified, not
    enabled - all `False`, never a guess and never a registry-wide
    default. Never raises (matches `MultiActionDispatch._legacy_
    capability_allowed`'s own "any exception denies" contract, so a
    caller wiring this in as `external_permission_resolver` sees the
    exact same failure discipline as the legacy checker path)."""

    user_id = _principal_user_id(principal)
    if not user_id:
        return False
    active_publisher = publisher or _shared_publisher
    try:
        return active_publisher.is_published_external_capability(user_id, capability_id)
    except Exception:
        return False


def make_permission_resolver(store: Optional[ExternalCapabilityStore] = None):
    """Returns a resolver bound to a specific store (test isolation) -
    the shared module-level `external_permission_resolver` above uses
    the default, real, on-disk store."""

    publisher = ExternalCapabilityPublisher(store=store or ExternalCapabilityStore())

    def _resolver(capability_id: str, principal: Any) -> bool:
        return external_permission_resolver(capability_id, principal, publisher=publisher)

    return _resolver
