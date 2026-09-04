"""Read-only aggregation over AuditTrail's shadow-comparison events.

UriOrchestrator already records one small, structured AuditEvent per
turn for each shadow path (skill_router_shadow_evaluation,
model_reasoning_shadow_evaluation), each carrying an explicit
agrees_with_planner boolean comparing the shadow's pick against the
tool the deterministic runtime actually selected (see
_record_skill_router_audit / _record_model_reasoning_audit in
orchestrator.py - both unmodified by this module).

This module only reads that already-recorded data and summarizes it -
it records nothing, executes nothing, and has no opinion about
whether a shadow "should" be trusted more. AuditEvent.metadata is
already validated (uri_core/core/audit_trail.py) to reject anything
credential-shaped and to cap value length, so summarizing/passing
through these events carries no new information-disclosure risk.
"""

from typing import Any, Dict, List, Optional

from uri_core.core.audit_trail import AuditEvent

SKILL_ROUTER_EVENT_TYPE = "skill_router_shadow_evaluation"
MODEL_REASONING_EVENT_TYPE = "model_reasoning_shadow_evaluation"

DEFAULT_RECENT_LIMIT = 10


def _event_summary(event: AuditEvent) -> Dict[str, Any]:
    return {
        "timestamp": event.timestamp,
        "session_id": event.session_id,
        "status": event.status,
        "shadow_capability": event.capability,
        "planner_tool_name": event.metadata.get("planner_tool_name"),
        "agrees_with_planner": event.metadata.get("agrees_with_planner"),
    }


def summarize_shadow_comparisons(
    events: List[AuditEvent],
    recent_limit: int = DEFAULT_RECENT_LIMIT,
) -> Dict[str, Any]:
    """
    Aggregate a list of shadow-comparison AuditEvents (all of the same
    event_type - callers filter before calling this) into counts, an
    agreement rate, and a small most-recent-first sample.

    Events missing agrees_with_planner (shouldn't happen given how
    orchestrator.py records these, but not assumed) are counted as
    neither agreements nor disagreements, and are noted separately so
    the total always reconciles.
    """

    total = len(events)
    agreements = 0
    disagreements = 0
    unknown = 0

    for event in events:
        agrees = event.metadata.get("agrees_with_planner")

        if agrees is True:
            agreements += 1
        elif agrees is False:
            disagreements += 1
        else:
            unknown += 1

    agreement_rate: Optional[float] = None
    comparable = agreements + disagreements

    if comparable > 0:
        agreement_rate = round(agreements / comparable, 4)

    recent = sorted(
        events, key=lambda e: e.timestamp, reverse=True
    )[:recent_limit]

    return {
        "total": total,
        "agreements": agreements,
        "disagreements": disagreements,
        "unknown": unknown,
        "agreement_rate": agreement_rate,
        "recent": [_event_summary(event) for event in recent],
    }


def build_shadow_comparison_report(
    all_events: List[AuditEvent],
    recent_limit: int = DEFAULT_RECENT_LIMIT,
) -> Dict[str, Any]:
    """
    Split a flat list of AuditEvents (e.g. the full contents of an
    AuditTrail) by shadow event_type and summarize each independently.
    """

    skill_router_events = [
        e for e in all_events if e.event_type == SKILL_ROUTER_EVENT_TYPE
    ]

    model_reasoning_events = [
        e
        for e in all_events
        if e.event_type == MODEL_REASONING_EVENT_TYPE
    ]

    return {
        "skill_router": summarize_shadow_comparisons(
            skill_router_events, recent_limit
        ),
        "model_reasoning": summarize_shadow_comparisons(
            model_reasoning_events, recent_limit
        ),
    }
