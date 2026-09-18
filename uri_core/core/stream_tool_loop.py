"""M32 D5: streaming wrapper around the native tool loop's Tier 0 fast
path.

Does NOT modify native_tool_loop.py - `run_native_tool_loop()`'s own
source is untouched by this module. Its `model_callable` parameter is
an existing, documented injectable seam ("the router's own attempt()
bound to a role/principal in production, a fake in tests"); this module
supplies a specialized closure for that same seam that ALSO streams
live content out through a side channel while still returning the
identical `ModelResponse` shape `run_native_tool_loop()` already
expects - so its own logic (`response.tool_calls`, `response.content`,
iteration bound, translate/gate/execute) needs no change at all.

Only iteration 1 is eligible for live streaming - the dominant Tier 0
case (a plain-chat turn, no tool call). Any later iteration (reachable
only after a real tool has already executed, in a genuine multi-step
Tier 1 turn) falls through to the existing, completely unmodified
non-streaming `ModelRouter.attempt()` path - out of scope for this
batch (M32_POST_BATCH_C_LATENCY_ARCHITECTURE_PLAN.md §13.12).

Per the User's frozen §13 design and its explicit clarification: a
first content chunk never proves a turn is terminal. Every chunk of
iteration 1's stream - not just the first - is checked for
`is_tool_call`; the instant ANY chunk signals a tool call, every
content chunk already emitted for this turn is provisional only -
never persisted as a completed narrative, never treated as
authoritative completion. This module marks that transition explicitly
(`TurnStreamEvent(kind="tool_call_detected")`) the moment it happens,
then lets `run_native_tool_loop()` continue through its existing,
completely unmodified translate -> gate -> execute path - approvals,
grants, and audit are never made aware a stream was ever attempted.
"""

from __future__ import annotations

import os
import queue
import threading
from dataclasses import dataclass
from typing import Any, Dict, Iterator, Optional

from uri_core.core.capability_registry import CapabilityRegistry
from uri_core.core.model_providers.base import ProviderResponseError
from uri_core.core.model_router import get_router
from uri_core.core.native_tool_loop import (
    DEFAULT_MAX_ITERATIONS,
    ROLE_NATIVE_TOOL_LOOP,
    run_native_tool_loop,
)

# M32 D5 (R-D5-6): a bounded, deployment-configurable cap on how many
# streamed turns may be in flight at once - the same "safe, configurable
# cap" discipline D4 established for the parallel-tool-dispatch worker
# pool, applied here to open provider streaming connections/threads
# under this repo's own independently measured 97% RAM pressure
# (M32_POST_BATCH_C_LATENCY_ARCHITECTURE_PLAN.md, risk R-New-1).
DEFAULT_MAX_CONCURRENT_STREAMS = 8
MAX_CONCURRENT_STREAMS_ENV_VAR = "URI_MAX_CONCURRENT_STREAMS"


def max_concurrent_streams() -> int:
    """Runtime-configurable stream cap, read per-call (same discipline
    as native_tool_loop_enabled()/_max_parallel_tool_workers()). Falls
    back to the safe default for anything that isn't a positive
    integer."""
    raw = os.environ.get(MAX_CONCURRENT_STREAMS_ENV_VAR)
    if raw is None:
        return DEFAULT_MAX_CONCURRENT_STREAMS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_MAX_CONCURRENT_STREAMS
    return value if value >= 1 else DEFAULT_MAX_CONCURRENT_STREAMS


class StreamCapacityExceededError(Exception):
    """Raised when the configured max-concurrent-stream cap is already
    at capacity. The caller (the HTTP layer) must fall back to the
    existing non-streamed /ask behaviour for this request - never
    silently drop it, never block indefinitely waiting for a slot."""


class StreamCancelled(Exception):
    """Raised inside the streaming model_callable when the caller (e.g.
    a detected client disconnect) requests cancellation - unwinds the
    in-flight provider stream generator, triggering its own upstream
    connection cleanup (see OllamaProvider.complete_stream's own
    ``finally: response.close()``)."""


_active_streams_lock = threading.Lock()
_active_streams = 0


class _StreamSlot:
    """Context manager enforcing max_concurrent_streams(). Acquired
    synchronously, before any background thread or provider connection
    is created - a caller at capacity fails fast, never queues an
    unbounded number of half-started turns."""

    def __enter__(self) -> "_StreamSlot":
        global _active_streams
        with _active_streams_lock:
            cap = max_concurrent_streams()
            if _active_streams >= cap:
                raise StreamCapacityExceededError(
                    f"Max concurrent streams ({cap}) already in use."
                )
            _active_streams += 1
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        global _active_streams
        with _active_streams_lock:
            _active_streams -= 1
        return False


@dataclass(frozen=True)
class TurnStreamEvent:
    """One event of a streamed turn, consumed by the HTTP layer.

    kind:
      - "content": a live text delta - provisional until "done" arrives;
        never persist a "content" event's text on its own.
      - "tool_call_detected": the stream just turned out to involve a
        tool call - every prior "content" event for this turn is now
        confirmed provisional/discarded; the turn continues through the
        existing, unmodified non-streaming path.
      - "done": terminal event. ``envelope`` is the exact dict
        run_native_tool_loop() itself returned - the single source of
        truth for what actually happened and what gets persisted.
        ``narrative_interrupted`` is True when a "tool_call_detected"
        event preceded this one for the same turn.
      - "error": terminal event, the turn could not complete.
    """

    kind: str
    content: Optional[str] = None
    envelope: Optional[Dict[str, Any]] = None
    ttft_seconds: Optional[float] = None
    narrative_interrupted: bool = False
    error: Optional[str] = None


_DONE_SENTINEL = object()


def stream_first_turn(
    *,
    orchestrator: Any,
    session_id: Optional[str],
    user_text: str,
    principal: Any,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    capability_registry: Optional[CapabilityRegistry] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Iterator[TurnStreamEvent]:
    """Runs one turn through ``run_native_tool_loop()`` completely
    unmodified, streaming iteration 1's content live whenever it turns
    out to be plain content (Tier 0). Yields ``TurnStreamEvent`` items;
    the LAST event is always ``kind="done"`` or ``kind="error"``.

    ``cancel_event``, when supplied, lets the caller (an HTTP layer that
    detected a client disconnect) request cancellation - checked between
    every chunk of the in-flight provider stream. If the caller simply
    stops iterating this generator early (without ever setting
    ``cancel_event`` itself), the generator's own ``finally`` sets it on
    the caller's behalf, so cancellation is never missed either way.

    Raises ``StreamCapacityExceededError`` immediately (on first
    iteration) if ``max_concurrent_streams()`` is already at capacity -
    the caller must fall back to the existing non-streamed path.
    """
    router = get_router()
    cancel_event = cancel_event or threading.Event()
    events: "queue.Queue[Any]" = queue.Queue()
    state: Dict[str, Any] = {"iteration": 0, "ttft_seconds": None, "tool_call_signaled": False}

    def _streaming_model_callable(*, system: str, user: str, tools: Any = None) -> Any:
        state["iteration"] += 1
        if state["iteration"] != 1:
            # Only iteration 1 is eligible for live streaming - any
            # later iteration only happens after a real tool already
            # executed, and uses the existing, unmodified non-streaming
            # router path (scope decision, module docstring).
            return router.attempt(
                ROLE_NATIVE_TOOL_LOOP, principal, system=system, user=user,
                tools=tools, max_tokens=800, session_id=session_id,
            )

        stream = router.attempt_stream(
            ROLE_NATIVE_TOOL_LOOP, principal, system=system, user=user,
            tools=tools, max_tokens=800, session_id=session_id,
        )
        final_response = None
        try:
            for chunk in stream:
                if cancel_event.is_set():
                    raise StreamCancelled("cancelled mid-stream")
                if chunk.is_tool_call and not state["tool_call_signaled"]:
                    # Per the User's clarification: this transition is
                    # signalled the instant ANY chunk (not just the
                    # first) reveals a tool call - every "content" event
                    # already put on the queue for this turn is thereby
                    # confirmed provisional, never authoritative.
                    state["tool_call_signaled"] = True
                    events.put(TurnStreamEvent(kind="tool_call_detected"))
                elif chunk.content and not chunk.is_tool_call:
                    events.put(TurnStreamEvent(kind="content", content=chunk.content))
                if chunk.done:
                    final_response = chunk.final_response
                    if chunk.ttft_seconds is not None:
                        state["ttft_seconds"] = chunk.ttft_seconds
        finally:
            stream.close()

        if final_response is None:
            # The stream ended without ever producing a terminal
            # (done=True) chunk - never silently return None here:
            # run_native_tool_loop()'s own `response.tool_calls` access
            # is unconditional once model_callable returns without
            # raising (its documented contract is "returns ModelResponse
            # or raises"), so returning None would crash it with an
            # opaque AttributeError instead of the honest,
            # already-established "reasoning_failed"/"unavailable"
            # degrade every other provider failure in this codebase
            # produces.
            raise ProviderResponseError(
                "Streamed response ended without a terminal chunk - the "
                "response is incomplete."
            )
        return final_response

    def _run() -> None:
        try:
            envelope = run_native_tool_loop(
                orchestrator=orchestrator, session_id=session_id, user_text=user_text,
                principal=principal, model_callable=_streaming_model_callable,
                max_iterations=max_iterations, capability_registry=capability_registry,
            )
            events.put(TurnStreamEvent(
                kind="done", envelope=envelope, ttft_seconds=state["ttft_seconds"],
                narrative_interrupted=state["tool_call_signaled"],
            ))
        except StreamCancelled:
            events.put(TurnStreamEvent(kind="error", error="cancelled"))
        except Exception as exc:  # noqa: BLE001 - always surfaced as an honest error event, never a crash of the SSE loop
            events.put(TurnStreamEvent(kind="error", error=str(exc)))
        finally:
            events.put(_DONE_SENTINEL)

    # StreamCapacityExceededError, if the cap is already at capacity, is
    # raised HERE - synchronously, on the caller's own first iteration,
    # before any background thread or provider connection is created.
    # ONE slot is held for this generator's entire lifetime (released in
    # the finally below) - never acquired twice, never racily released
    # and re-acquired.
    slot = _StreamSlot()
    slot.__enter__()

    worker = threading.Thread(target=_run, daemon=True)
    worker.start()

    try:
        while True:
            item = events.get()
            if item is _DONE_SENTINEL:
                break
            yield item
    finally:
        # Whether the consumer drained normally or stopped early (e.g.
        # GeneratorExit from an upstream client disconnect), make sure
        # cancellation is signalled and the background thread is
        # actually joined - never an orphaned thread/connection - before
        # releasing this turn's capacity slot.
        cancel_event.set()
        worker.join(timeout=5.0)
        slot.__exit__(None, None, None)
