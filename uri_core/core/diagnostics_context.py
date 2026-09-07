"""Structured, honest runtime diagnostics for the Brain (item 2/8 of
the URI architecture spec): what actually just happened, in enough
detail that the Brain can distinguish a capability that does not
exist from one that failed to run, from one that ran and found
nothing, from one still waiting on a human decision.

This module is pure and read-only, mirroring query_context.py's exact
discipline one section further: it never touches storage itself, never
writes anything, and is never imported by capability_planner.py,
dispatcher.py, approval_gate.py, or approval_store.py. Every input is
already-real data the caller (orchestrator.py) assembled from an
existing authoritative source - this module only shapes it into one
small, bounded, labeled envelope. Nothing here is invented: a value
this module cannot honestly derive from what it was given is omitted,
never guessed at or filled in with a plausible-sounding default.

Deliberately NOT a new logging/telemetry system: the "recent_events"
section is a bounded read of AuditTrail (audit_trail.py), which already
exists and already validates/caps its own metadata at write time - this
module does not duplicate that, it only selects and truncates a few
recent entries into a shape the Brain can read alongside the rest of
query_context.
"""

from typing import Any, Dict, List, Optional

MAX_RECENT_EVENTS = 5
MAX_KNOWN_GAPS = 5
MAX_FIELD_LENGTH = 200


def _truncate(value: Any, limit: int = MAX_FIELD_LENGTH) -> Any:
    if not isinstance(value, str) or len(value) <= limit:
        return value
    return value[:limit].rstrip() + "…"


def _condense_event(event: Any) -> Optional[Dict[str, Any]]:
    """One AuditEvent (or plain dict with the same shape) -> a small,
    bounded summary: what stage, what capability/component, what
    outcome, and only the metadata fields already deemed safe to
    persist by AuditTrail at write time (already length-capped and
    credential-screened there - this only adds one more truncation
    pass in case a caller hands in raw, unvalidated data)."""

    if hasattr(event, "to_dict"):
        try:
            event = event.to_dict()
        except Exception:
            return None

    if not isinstance(event, dict):
        return None

    metadata = event.get("metadata")

    condensed_metadata = {}

    if isinstance(metadata, dict):
        for key, value in list(metadata.items())[:10]:
            condensed_metadata[str(key)] = _truncate(value)

    return {
        "event_type": event.get("event_type"),
        "status": event.get("status"),
        "capability": event.get("capability"),
        "timestamp": event.get("timestamp"),
        "metadata": condensed_metadata,
    }


def _condense_last_operation(
    last_operation: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """The current turn's most recent real, already-decided execution
    outcome - never a prediction, never "what should happen next".
    Reuses whatever the caller already has in response["execution"]/
    response["response"] (see orchestrator.py's _compact_attempt_result
    for the sibling discipline this mirrors for attempt_history)."""

    if not isinstance(last_operation, dict):
        return {}

    return {
        "capability": last_operation.get("capability"),
        "status": last_operation.get("status"),
        "component": _truncate(last_operation.get("component")),
        "error": _truncate(last_operation.get("error")),
        "message": _truncate(last_operation.get("message")),
    }


def _condense_known_gap(descriptor: Any) -> Optional[Dict[str, Any]]:
    """One CapabilityDescriptor -> a small honest "service/tool status"
    summary - only ever entries that already have a real gap_reason
    (see capability_registry.CapabilityDescriptor.gap_reason); never a
    full capability dump, that already belongs to query_context's own
    "capabilities" section."""

    gap_reason = getattr(descriptor, "gap_reason", None)

    if gap_reason is None:
        return None

    return {
        "id": getattr(descriptor, "id", None),
        "gap_reason": gap_reason,
        "availability": getattr(descriptor, "availability", None),
        "limitations": _truncate(getattr(descriptor, "limitations", None)),
    }


def build_diagnostics_context(
    last_operation: Optional[Dict[str, Any]] = None,
    recent_events: Optional[List[Any]] = None,
    known_gaps: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """Assembles one bounded, labeled diagnostics dict for a single
    Brain query - never prose, never free-form instruction text.

    - last_operation: the real, already-decided outcome of the most
      recent capability execution this turn (or None on a fresh turn
      with nothing executed yet) - e.g. {"capability": "web_search",
      "status": "unavailable", "error": "...", "component": "..."}.
    - recent_events: a list of AuditEvent (or AuditEvent.to_dict()-
      shaped plain dicts) for the current session, e.g. from
      AuditTrail.for_session(session_id) - only the most recent
      MAX_RECENT_EVENTS are kept (oldest dropped first), each condensed
      to a small summary.
    - known_gaps: a list of CapabilityDescriptor with a real
      gap_reason, e.g. from CapabilityRegistry.known_gaps() - honest
      service/tool-availability status, not a full capability dump.

    Any argument may be omitted (None) - the corresponding section
    degrades to an empty value, matching query_context.py's own
    "unknown-safe" discipline. Never raises: a malformed entry is
    dropped rather than allowed to break the whole context.
    """

    condensed_events = []

    for event in (recent_events or [])[-MAX_RECENT_EVENTS:]:
        condensed = _condense_event(event)
        if condensed is not None:
            condensed_events.append(condensed)

    condensed_gaps = []

    for descriptor in (known_gaps or [])[:MAX_KNOWN_GAPS]:
        condensed = _condense_known_gap(descriptor)
        if condensed is not None:
            condensed_gaps.append(condensed)

    return {
        "last_operation": _condense_last_operation(last_operation),
        "recent_events": condensed_events,
        "known_gaps": condensed_gaps,
    }
