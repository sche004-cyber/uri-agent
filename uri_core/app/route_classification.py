"""M22.3: the single source of truth for every registered route's
PUBLIC | USER | ADMIN classification (see
docs/plans/M22.3_SECURITY_ARCHITECTURE_PLAN.md section 4).

PUBLIC             - no login concept applies (a true public route, or one
                      of the five diagnostic GETs the accepted plan
                      explicitly defers rather than reclassifies - see
                      DEFERRED_PUBLIC_ROUTES below).
USER               - the pre-existing Optional[str] =
                      Depends(_resolve_authenticated_user_id) pattern: an
                      authenticated caller gets their own isolated state,
                      an anonymous caller gets the single shared
                      legacy-ambient state. This fallback is a standing
                      architecture decision (URI_M22_ARCHITECTURE.md
                      section 20.7) retained through all of M22, not a gap
                      this table is asserting should be closed.
ADMIN              - must 401 anonymous, 403 non-admin, and succeed only
                      for a logged-in ADMIN.

This table exists specifically so a new route can never silently default
to public: test_m22_3_route_authorization.py walks app.routes and asserts
every (method, path) pair appears here, with the exact count also
checked, so an added-but-unclassified route fails CI immediately rather
than being caught only if someone remembers to test it by hand.

Do not add a route here as an act of granting it authority - this module
is a record of what server.py's own Depends(...) wiring already does; the
actual authorization decision is made in authorization.py/server.py, not
here.
"""

from typing import Dict, Tuple

PUBLIC = "PUBLIC"
USER = "USER"
ADMIN = "ADMIN"

# FastAPI's own auto-generated interactive-docs/schema routes (enabled
# by default; this milestone does not disable them). No application
# data flows through them - they only ever describe the API shape - so
# they are PUBLIC alongside the five diagnostic GETs below, and listed
# here explicitly so app.routes and this table stay in exact bijection
# (see test_m22_3_route_authorization.py's enumeration test).
FASTAPI_DOC_ROUTES: Tuple[Tuple[str, str], ...] = (
    ("GET", "/openapi.json"),
    ("GET", "/docs"),
    ("GET", "/docs/oauth2-redirect"),
    ("GET", "/redoc"),
)

# The five diagnostic GET endpoints explicitly kept PUBLIC by the User's
# accepted M22.3 decision (docs/plans/M22.3_SECURITY_ARCHITECTURE_PLAN.md,
# Decision 1 / section 5.1) - deferred to a later security/API-exposure
# milestone, not silently reclassified in either direction here.
DEFERRED_PUBLIC_ROUTES: Tuple[Tuple[str, str], ...] = (
    ("GET", "/audit/shadow-comparison"),
    ("GET", "/identity"),
    ("GET", "/skills"),
    ("GET", "/capabilities"),
    ("GET", "/connections"),
)

# The five previously-unauthenticated mutating endpoints closed by this
# milestone (S1) - now ADMIN-only, with no legacy-ambient fallback, since
# none of the five ever had one to preserve.
ADMIN_GATED_ROUTES: Tuple[Tuple[str, str], ...] = (
    ("POST", "/skills/{skill_id}/enable"),
    ("POST", "/skills/{skill_id}/disable"),
    ("DELETE", "/skills/{skill_id}"),
    ("POST", "/connections/{connection_id}/authorize"),
    ("DELETE", "/connections/{connection_id}"),
    ("GET", "/admin/users"),
    ("GET", "/admin/users/{user_id}/grants"),
    ("PUT", "/admin/users/{user_id}/grants"),
)

ROUTE_CLASSIFICATION: Dict[Tuple[str, str], str] = {
    ("GET", "/health"): PUBLIC,
    ("POST", "/auth/signup"): PUBLIC,
    ("POST", "/auth/login"): PUBLIC,
    ("POST", "/auth/logout"): USER,
    ("GET", "/auth/me"): USER,
    ("POST", "/auth/experience-tier"): USER,
    ("GET", "/modes"): USER,
    ("PUT", "/modes"): USER,
    ("GET", "/auth/devices"): USER,
    ("DELETE", "/auth/devices/{device_id}"): USER,
    ("POST", "/ask"): USER,
    ("POST", "/approve"): USER,
    ("POST", "/cancel"): USER,
    ("GET", "/tasks"): USER,
    ("GET", "/profile"): USER,
    ("POST", "/profile"): USER,
    ("GET", "/memory"): USER,
    ("POST", "/memory"): USER,
    ("PUT", "/memory/{memory_id}"): USER,
    ("DELETE", "/memory/{memory_id}"): USER,
    ("POST", "/memory/{memory_id}/confirm"): USER,
    ("POST", "/memory/{memory_id}/reject"): USER,
    ("GET", "/learning"): USER,
    ("GET", "/growth"): USER,
    ("POST", "/files"): USER,
    ("GET", "/files"): USER,
    ("DELETE", "/files/{file_id}"): USER,
    ("GET", "/files/{file_id}/content"): USER,
    ("GET", "/activity"): USER,
    ("GET", "/history"): USER,
    ("GET", "/history/{session_id}"): USER,
    ("DELETE", "/history/{session_id}"): USER,
    # M22.5: per-user provider configuration and key submission.
    # All three are USER (self-service) - not ADMIN.  The key is the
    # user's own; user_id comes only from the auth token, never from the
    # request body, so one user can never set or read another's key.
    ("POST", "/providers/keys"): USER,
    ("GET", "/providers"): USER,
    ("PUT", "/providers/config"): USER,
    ("GET", "/usage"): USER,
    ("GET", "/usage/limits"): USER,
    ("PUT", "/usage/limits"): USER,
}

for _route in DEFERRED_PUBLIC_ROUTES:
    ROUTE_CLASSIFICATION[_route] = PUBLIC

for _route in FASTAPI_DOC_ROUTES:
    ROUTE_CLASSIFICATION[_route] = PUBLIC

for _route in ADMIN_GATED_ROUTES:
    ROUTE_CLASSIFICATION[_route] = ADMIN

del _route

# 51 application routes + 4 FastAPI auto-generated doc/schema routes.
EXPECTED_ROUTE_COUNT = 55
