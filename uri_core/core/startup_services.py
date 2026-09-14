"""Generic Startup Services lifecycle - see docs/plans/
M30_GRAPHIFY_FOUNDATION_PLAN.md §A.5.

Before this module existed, `server.py`'s `_lifespan()` (the one place
"real application startup" work belongs) called exactly one hardcoded
function. Every future startup need would otherwise become a second
one-off `if` branch bolted onto the same spot. This module replaces
that with a small, generic, extensible list: a `StartupService` is
anything with a `start()` method; `run_startup_services()` runs each
one in order, and one service's failure never blocks another's, or
prevents the server from starting at all.
"""

from __future__ import annotations

from typing import Any, Protocol, Sequence, runtime_checkable


@runtime_checkable
class StartupService(Protocol):
    """Anything with a no-argument `start()` method. Not a base class -
    a registered service need not inherit from anything, matching this
    codebase's existing preference for structural typing over
    inheritance hierarchies (e.g. `AvailabilityCheck` in
    `uri_core/capabilities/base.py`)."""

    def start(self) -> None: ...


def run_startup_services(services: Sequence[Any]) -> None:
    """Runs each service's `start()` in order. A service that raises is
    skipped - it never prevents a later service from running, and
    never prevents `_lifespan()` from completing (the server must
    still start even if one startup service fails)."""
    for service in services:
        try:
            service.start()
        except Exception:
            continue
