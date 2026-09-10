"""M22.3: edge-only request protections - authentication-route rate
limiting and the /ask request-size precheck. See
docs/plans/M22.3_SECURITY_ARCHITECTURE_PLAN.md sections 6.4/6.5.

Pure in-process implementation, no new dependency (the portability
ceiling in URI_M22_ARCHITECTURE.md section 11.1 is ~10 declared runtime
dependencies; this file adds none). State lives in this process's memory,
the same risk class as the existing AuditTrail - a remote attacker cannot
trigger a server restart to reset it, so process-memory state is an
acceptable trade-off here for a lightweight, no-database, no-broker
design (URI_M22_ARCHITECTURE.md section 11.3).

Fail-closed by construction: every dependency below either returns None
(request proceeds) or raises (request is refused before the route handler
runs, via FastAPI's own Depends() semantics) - there is no code path where
an internal error here results in the guarded endpoint executing anyway.
"""

import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import HTTPException, Request

# Decision 5 (accepted, docs/plans/M22.3_SECURITY_ARCHITECTURE_PLAN.md
# section 5.5) - configurable, not hardcoded inline at each call site.
LOGIN_RATE_LIMIT_MAX_ATTEMPTS = 5
LOGIN_RATE_LIMIT_WINDOW_SECONDS = 60.0

SIGNUP_RATE_LIMIT_MAX_ATTEMPTS = 3
SIGNUP_RATE_LIMIT_WINDOW_SECONDS = 300.0

# Decision 6 - 64 KB maximum conversational text (the field-level bound
# enforced on AskRequest.text itself, in server.py). This module's own
# constant is the lower-level Content-Length precheck, deliberately
# larger than the field bound to allow for JSON envelope/escaping
# overhead without ever approaching memory-exhaustion territory - it
# exists to reject an oversized body before it is read into memory at
# all, which the field-level max_length alone cannot do.
ASK_MAX_TEXT_BYTES = 64 * 1024
ASK_MAX_CONTENT_LENGTH_BYTES = 1024 * 1024


class RateLimitExceededError(Exception):
    """Internal signal only - callers use the FastAPI dependency
    functions below, which convert this into an HTTPException(429)."""

    def __init__(self, retry_after_seconds: float) -> None:
        super().__init__("Rate limit exceeded.")
        self.retry_after_seconds = retry_after_seconds


class _FixedWindowRateLimiter:
    """Process-memory, per-key fixed-window counter. Counts every call to
    check_and_record() regardless of what the caller's request turned out
    to contain (Decision 4: every attempt counts, successful or failed) -
    the caller decides what "an attempt" means only by choosing when to
    call this, never by passing an outcome flag back in."""

    def __init__(self, max_attempts: int, window_seconds: float) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def check_and_record(self, key: str) -> None:
        now = time.monotonic()
        window_start = now - self.window_seconds
        hits = self._hits[key]

        while hits and hits[0] < window_start:
            hits.popleft()

        if len(hits) >= self.max_attempts:
            retry_after = hits[0] + self.window_seconds - now
            raise RateLimitExceededError(max(retry_after, 0.0))

        hits.append(now)

    def reset(self) -> None:
        """Test-only hook, mirroring how other stores in this codebase
        are reset between tests (see e.g. AuditTrail usage in
        test_server_audit_endpoint.py's setUp()). Never called from
        production request-handling code."""
        self._hits.clear()


login_rate_limiter = _FixedWindowRateLimiter(
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS, LOGIN_RATE_LIMIT_WINDOW_SECONDS
)
signup_rate_limiter = _FixedWindowRateLimiter(
    SIGNUP_RATE_LIMIT_MAX_ATTEMPTS, SIGNUP_RATE_LIMIT_WINDOW_SECONDS
)


def _client_key(request: Request) -> str:
    client = request.client
    return client.host if client is not None else "unknown"


def _enforce(request: Request, limiter: _FixedWindowRateLimiter) -> None:
    try:
        limiter.check_and_record(_client_key(request))
    except RateLimitExceededError as exc:
        retry_after = int(exc.retry_after_seconds) + 1
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )


def enforce_login_rate_limit(request: Request) -> None:
    _enforce(request, login_rate_limiter)


def enforce_signup_rate_limit(request: Request) -> None:
    _enforce(request, signup_rate_limiter)


def reset_rate_limiters() -> None:
    """Test-only: clears both limiters' state. Call from a test's
    setUp()/tearDown() so one test's attempts can never trip another
    test's limit - see test_m22_3_rate_limiting.py."""
    login_rate_limiter.reset()
    signup_rate_limiter.reset()


def enforce_ask_content_length(request: Request) -> None:
    """Rejects an oversized /ask body via its declared Content-Length
    before FastAPI reads or parses it - the layer beneath
    AskRequest.text's own max_length, which only rejects after the full
    body has already been read into memory. A missing or unparseable
    Content-Length header is not itself rejected here (some clients omit
    it for chunked transfer); it is the field-level max_length that
    provides the final, authoritative bound in that case."""

    content_length = request.headers.get("content-length")

    if content_length is None:
        return

    try:
        size = int(content_length)
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid Content-Length header."
        )

    if size > ASK_MAX_CONTENT_LENGTH_BYTES:
        raise HTTPException(status_code=413, detail="Request body too large.")
