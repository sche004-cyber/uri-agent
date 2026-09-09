"""M22.2: PrincipalContext - the resolved identity of one HTTP request.

Introduced now (see URI_M22_ARCHITECTURE.md sections 4 and 22, M22.2's
"Files affected") specifically so M22.3 (endpoint authorization) and
M22.4 (CapabilityResolver) have an existing, agreed request-identity
shape to consume rather than inventing one under time pressure while
also doing higher-risk route-classification/authority work.

M22.2 itself uses this in exactly one place: the small set of new
self-scoped endpoints it adds (GET/POST under /auth/*, all of which act
only on the calling principal's own account - see server.py). The
~25 pre-existing endpoints are deliberately NOT retrofitted to
construct or consume a PrincipalContext in this milestone; that
endpoint-by-endpoint change belongs to M22.3, when routes are actually
being classified and gated by role. Introducing the type now without
forcing that wider, out-of-scope rewrite keeps this milestone's diff to
exactly what M22.2 needs.

This module is a plain data shape only - no logic, no storage, no
import of anything beyond the standard library - so it can safely be
imported by both the edge (server.py, which is the ONLY place a
PrincipalContext may be constructed) and, later, deterministic
authority modules like the future CapabilityResolver, without ever
creating a path back into execution or approval itself.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PrincipalContext:
    """user_id/role are None together for a request with no (or no
    valid) Authorization header - the pre-login, legacy-ambient case
    every existing unauthenticated caller still relies on (see
    server.py's _resolve_context). role is never guessed or defaulted
    to a privileged value when user_id is None. device_id is the
    CLIENT's own self-reported identifier for this specific login (see
    auth_session.py) - purely informational, exactly as it already is
    everywhere else in this codebase; it must never be read as an
    authorization input."""

    user_id: Optional[str]
    role: Optional[str]
    device_id: Optional[str]
