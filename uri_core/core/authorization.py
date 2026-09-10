"""M22.3: pure ADMIN-role authorization decision.

This module holds exactly one decision - "does this principal hold ADMIN
- and nothing else. It has no FastAPI/HTTP dependency and no I/O, so it
can be unit-tested directly with a plain PrincipalContext and reused
anywhere a role check is needed without pulling in the web framework.

Following the same separation server.py already uses for
FileValidationError (raised in file_store.py, translated to an
HTTPException only at the edge in server.py), this module raises its own
AuthorizationError; server.py's _resolve_admin_principal dependency is the
only place that translates it into an HTTPException, with the exact
status code this module decided (401 - no principal at all, vs 403 - a
real principal with an insufficient role). The distinction matters: 401
means "you are not authenticated," 403 means "you are authenticated but
not allowed" - collapsing them would leak or hide which is true.

experience_tier is never read here, and never will be - see
principal_context.py's own docstring and
test_experience_tier_never_authorizes.py, which this module's ADMIN check
must remain reachable from without ever referencing that field.
"""

from uri_core.core.principal_context import PrincipalContext
from uri_core.core.user_accounts import ROLE_ADMIN


class AuthorizationError(Exception):
    """Raised by require_admin. status_code is the exact HTTP status the
    edge must report - never re-derived or guessed by the caller."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def require_admin(principal: PrincipalContext) -> PrincipalContext:
    """Returns principal unchanged when it holds ADMIN. Raises
    AuthorizationError(401) when there is no logged-in principal at all,
    and AuthorizationError(403) when a real principal's role is anything
    other than ADMIN (including a missing/None role on an account that
    somehow has no role recorded - never treated as privileged by
    omission)."""

    if principal.user_id is None or principal.role is None:
        raise AuthorizationError(401, "Authentication required.")

    if principal.role != ROLE_ADMIN:
        raise AuthorizationError(403, "ADMIN role required for this action.")

    return principal
