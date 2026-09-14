"""M30.1: canonical Turn State — a READ-ONLY projection over URI's
existing live state (docs/plans/URI_CANONICAL_AGENT_LOOP_MIGRATION_PLAN.md
§2, itself derived from docs/architecture/URI_CANONICAL_AGENT_LOOP_
ARCHITECTURE.md §3).

This module answers exactly one question - "what does URI know, right
now, at this turn?" - as one coherent, structured, throwaway dict. It is
NOT a new store: nothing here is persisted, nothing here is the
authoritative copy of anything. Every field is either read fresh from an
existing store each call (`recent_conversation`, `capability_summaries`,
`active_pointer`, `attempt_history`, `session_facts`) or passed through
verbatim from a value the CALLER already fetched elsewhere
(`durable_memory_relevant`, `graph_context`) - this module never fetches
memory or graph content itself, per the M30.1 migration-plan boundary
("no new ingestion or retrieval paths").

Nothing in `uri_core/core/orchestrator.py` calls this module yet. Per
the accepted migration plan, Turn State is introduced as a standalone,
independently testable projection first - it becomes part of the live
decision path only in a later, separately-authorized milestone (M30.5
onward). Constructing or calling this module has zero effect on any
existing request; it is exercised only by its own tests today.

Field provenance (source module / authoritative owner / how it is
projected / lifetime / sensitivity) - kept here as the single place this
is documented, referenced by the M30.1 completion report rather than
duplicated:

    turn                  - the caller's own request; principal is never
                             stored here as an object, only its user_id
                             (an identifier, not a secret). Lifetime: this
                             call only.
    recent_conversation    - uri_core.core.conversation_history.
                             ConversationHistoryStore (unchanged owner).
                             Referenced: read fresh, bounded to the most
                             recent N turns, never copied durably.
    active_pointer         - uri_core.core.state.Session's existing
                             active_workflow*/active_workflow_question
                             fields (unchanged owner). Derived: this
                             module only reshapes those fields into one
                             {kind, question, missing_field, reference}
                             record: it does not read or write anything
                             Session itself does not already hold.
    attempt_history        - Session.last_goal_attempt_history (unchanged
                             owner, already produced by orchestrator.py's
                             own existing carry-forward logic). Referenced
                             verbatim.
    session_facts          - Session.fact_history (unchanged owner).
                             Summarized: name/value/status only, never
                             the full Fact record (drops verified_by/
                             verified_at/evidence_ids - internal
                             provenance this module does not need to
                             re-expose).
    capability_summaries   - uri_core.core.capability_feasibility.
                             CapabilityFeasibility (legacy, connection-
                             aware) concatenated with
                             uri_core.capabilities.MultiActionCapability
                             Registry.capability_summaries() (M27) - each
                             entry tagged with its own "source" so the
                             two catalogues' different vocabularies are
                             never silently merged into one shape this
                             early (Stage 1 §11.6's own finding: they are
                             not equivalent yet). Referenced: read fresh
                             every call, never cached.
    runtime_health         - the caller's own already-resolved active
                             provider/model id, cross-checked (if a
                             uri_core.core.model_router.
                             ProviderHealthTracker instance is given)
                             against its real, in-memory (never
                             persisted) health state. Derived.
    durable_memory_relevant, graph_context
                           - NEVER fetched here. Accepted only as an
                             already-computed value the caller passed in
                             (e.g. from the existing
                             personalization_context/graph_self_context
                             call sites) - a pure pass-through, present
                             only to prove the shape can carry this data
                             once a later milestone wires real retrieval
                             through Turn State instead of around it.
    grounded_entities      - always empty this milestone (the generalized
                             context resolver is M30.6's scope) - reported
                             as an explicit empty dict plus a note in
                             `unavailable_fields`, never fabricated.

Never included, under any circumstance: raw credentials/OAuth tokens
(only `connection_status`'s own already-redacted status/detail strings
reach `capability_summaries`, via CapabilityFeasibility, unchanged),
the `principal` object itself (only `principal.user_id`), full attachment
bytes, or raw audit-trail/security-guard internals.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from uri_core.core.capability_feasibility import CapabilityFeasibility
from uri_core.core.conversation_history import ConversationHistoryStore

try:
    from uri_core.capabilities import MultiActionCapabilityRegistry
except ImportError:  # pragma: no cover - defensive, mirrors this
    # codebase's existing "a missing optional collaborator degrades,
    # never crashes the caller" convention (e.g. capability_feasibility.py).
    MultiActionCapabilityRegistry = None  # type: ignore[assignment,misc]

try:
    from uri_core.core.model_router import ProviderHealthTracker
except ImportError:  # pragma: no cover
    ProviderHealthTracker = None  # type: ignore[assignment,misc]

DEFAULT_RECENT_CONVERSATION_LIMIT = 6


@dataclass(frozen=True)
class TurnStateResult:
    """Thin, inspectable wrapper. `.data` is the plain-dict projection
    (JSON-serializable, safe to log per the module docstring's own
    sensitivity rules); `.unavailable_fields` names every category this
    call could not populate - never silently omitted, always listed, so
    a caller (or a test) can tell "not asked for" apart from "asked for,
    genuinely absent"."""

    data: Dict[str, Any]
    unavailable_fields: List[str] = field(default_factory=list)


def _project_recent_conversation(
    conversation_history_store: Optional[ConversationHistoryStore],
    session_id: Optional[str],
    limit: int,
) -> List[Dict[str, Any]]:
    if conversation_history_store is None or not session_id:
        return []
    try:
        turns = conversation_history_store.get_session(session_id)
    except Exception:
        # Same fail-open, never-fail-the-caller discipline
        # capability_feasibility.py already applies to connection_status
        # reads - a corrupt/unreadable history file degrades to "no
        # recent conversation known", never an exception here.
        return []
    if not isinstance(turns, list):
        return []
    bounded = turns[-limit:] if limit > 0 else []
    return [
        {
            "user": turn.get("user_text", ""),
            "uri": turn.get("response_text", ""),
        }
        for turn in bounded
        if isinstance(turn, dict)
    ]


def _infer_expected_type(field_name: Optional[str]) -> Optional[str]:
    """M30.5A: a generic, field-NAME-morphology heuristic (never a
    phrase-specific routing rule) - applicable to any future
    capability's own schema field names, not invented for one case.
    Returns None (never a guessed default) when nothing matches."""
    if not field_name:
        return None
    name = field_name.lower()
    if any(token in name for token in ("id", "roll", "code", "number")):
        return "identifier"
    if "email" in name:
        return "email_address"
    if any(token in name for token in ("date", "time")):
        return "date"
    if any(token in name for token in ("count", "amount", "quantity")):
        return "integer"
    return "string"


def _project_active_pointer(session: Any) -> Dict[str, Any]:
    """M30.5A bugfix, found live while building `pending_interaction`
    support: the far more common ad hoc Brain-clarification pause
    (orchestrator.py's `_apply_clarification_pause`) NEVER sets
    `session.active_workflow`/`active_workflow_question` at all - only
    a genuine WorkflowExecutor-based pause does. A real, on-disk session
    file after exactly this scenario ("Find the student." -> pending
    roll number) was inspected directly this milestone and confirmed
    `active_workflow_question` stayed `null` throughout - meaning this
    function returned `kind: "none"` for the single most common
    continuation scenario in every prior milestone's testing, silently.
    The real pending-state signal for that path is
    `session.last_goal_attempt_history`'s last entry (written by
    `_carry_forward_goal_attempt_history`) - checked here as a second,
    equally-real source, not a fallback guess."""
    empty = {
        "kind": "none", "question": None, "missing_field": None, "reference": None,
        "originating_goal": None, "capability_id": None, "action": None,
        "known_inputs": {},
        "expected_type": None, "prompt_asked": None, "created_at": None, "state": None,
    }
    if session is None:
        return dict(empty)

    active_workflow = getattr(session, "active_workflow", None)
    question = getattr(session, "active_workflow_question", None)
    missing_field = getattr(session, "active_workflow_required_field", None)
    status = getattr(session, "active_workflow_status", None)

    if active_workflow or question:
        kind = "paused_workflow"
        if status == "waiting_for_input" or (question and not missing_field):
            kind = "awaiting_clarification_answer"
        capability_id = None
        if isinstance(active_workflow, dict):
            capability_id = active_workflow.get("capability") or active_workflow.get("task")
        return {
            "kind": kind,
            "question": question,
            "missing_field": missing_field,
            # A reference to the paused workflow itself, not a copy of it -
            # callers that need the full record still read session.active_
            # workflow directly; Turn State only needs to know ONE exists.
            "reference": "active_workflow" if active_workflow else None,
            "originating_goal": (active_workflow or {}).get("goal") if isinstance(active_workflow, dict) else None,
            "capability_id": capability_id,
            "action": (active_workflow or {}).get("action") if isinstance(active_workflow, dict) else None,
            "known_inputs": dict(getattr(session, "current_facts", None) or {}),
            "expected_type": _infer_expected_type(missing_field),
            "prompt_asked": question,
            "created_at": (active_workflow or {}).get("created_at") if isinstance(active_workflow, dict) else None,
            "state": status,
        }

    # Real, far more common path (see this function's own docstring).
    attempt_history = getattr(session, "last_goal_attempt_history", None) or []
    if attempt_history:
        last = attempt_history[-1] if isinstance(attempt_history[-1], dict) else {}
        result = last.get("result") or {}
        proposal = last.get("proposal") or {}
        if (
            result.get("status") == "awaiting_user_response"
            and proposal.get("type") == "clarification"
        ):
            question_text = proposal.get("question")
            return {
                "kind": "awaiting_clarification_answer",
                "question": question_text,
                "missing_field": proposal.get("missing_field"),
                "reference": "last_goal_attempt_history",
                "originating_goal": last.get("goal"),
                "capability_id": proposal.get("capability_id"),
                "action": proposal.get("action"),
                "known_inputs": proposal.get("known_inputs") or {},
                "expected_type": None,
                "prompt_asked": question_text,
                "created_at": None,
                "state": "awaiting_answer",
            }

    return dict(empty)


def _project_session_facts(session: Any) -> List[Dict[str, Any]]:
    fact_history = getattr(session, "fact_history", None)
    if not isinstance(fact_history, dict):
        return []
    projected: List[Dict[str, Any]] = []
    for name, facts in fact_history.items():
        if not isinstance(facts, list) or not facts:
            continue
        latest = facts[-1]
        value = getattr(latest, "value", None)
        status = getattr(latest, "status", None)
        if value is None and status is None:
            continue
        projected.append({"name": name, "value": value, "status": status})
    return projected


def _project_capability_summaries(
    capability_feasibility: Optional[CapabilityFeasibility],
    multi_action_registry: Optional["MultiActionCapabilityRegistry"],
) -> List[Dict[str, Any]]:
    summaries: List[Dict[str, Any]] = []

    if capability_feasibility is not None:
        try:
            snapshot = capability_feasibility.snapshot()
        except Exception:
            snapshot = {}
        for capability_id, entry in snapshot.items():
            summaries.append(
                {
                    "id": capability_id,
                    "source": "legacy",
                    "description": entry.get("description"),
                    "usable": entry.get("usable"),
                    "gap_reason": entry.get("gap_reason"),
                    "requires_approval": entry.get("requires_approval"),
                    "risk": entry.get("risk"),
                    # Stage 1 §11.6's own finding, made structurally
                    # visible rather than silently assumed away: this
                    # catalogue's availability truth is real and current.
                    "availability_known": True,
                }
            )

    if multi_action_registry is not None:
        try:
            multi_summaries = multi_action_registry.capability_summaries()
        except Exception:
            multi_summaries = []
        for entry in multi_summaries:
            summaries.append(
                {
                    "id": entry.get("name"),
                    "source": "multi_action",
                    "description": entry.get("description"),
                    "usable": None,
                    "gap_reason": None,
                    "requires_approval": None,
                    "risk": None,
                    # This is the exact gap Stage 1 §1/§11.6 found: M27's
                    # own summary stage carries no connection/usability
                    # signal. Recorded honestly here, not papered over -
                    # closing it is explicitly out of scope for M30.1
                    # (that is M30.2's job, per the accepted plan).
                    "availability_known": False,
                }
            )

    return summaries


def _project_runtime_health(
    active_provider_id: Optional[str],
    active_model: Optional[str],
    health_tracker: Optional["ProviderHealthTracker"],
) -> Dict[str, Any]:
    healthy: Optional[bool] = None
    if health_tracker is not None and active_provider_id and active_model:
        try:
            healthy = health_tracker.is_healthy(active_provider_id, active_model)
        except Exception:
            healthy = None
    return {
        "active_provider": active_provider_id,
        "active_model": active_model,
        # None means "unknown", not "unhealthy" - never fabricated.
        "healthy": healthy,
    }


def assemble_turn_state(
    *,
    user_text: str,
    session_id: Optional[str],
    principal: Any = None,
    session: Any = None,
    conversation_history_store: Optional[ConversationHistoryStore] = None,
    capability_feasibility: Optional[CapabilityFeasibility] = None,
    multi_action_registry: Optional["MultiActionCapabilityRegistry"] = None,
    capability_directory: Optional[Any] = None,
    active_provider_id: Optional[str] = None,
    active_model: Optional[str] = None,
    health_tracker: Optional["ProviderHealthTracker"] = None,
    durable_memory_relevant: Optional[List[Dict[str, Any]]] = None,
    graph_context: Optional[Dict[str, Any]] = None,
    capability_index_hint: Optional[List[Dict[str, Any]]] = None,
    recent_conversation_limit: int = DEFAULT_RECENT_CONVERSATION_LIMIT,
) -> TurnStateResult:
    """Pure, read-only projection. Never raises: every collaborator read
    degrades to an honest empty/None value on failure (see each helper
    above), matching this codebase's existing fail-open discipline for
    context-assembly code (capability_feasibility.py, query_context.py).

    Not called from orchestrator.py in this milestone - see module
    docstring. Callers are tests and any future opt-in observability
    tooling only.
    """

    unavailable: List[str] = []

    principal_id = getattr(principal, "user_id", None) if principal is not None else None

    recent_conversation = _project_recent_conversation(
        conversation_history_store, session_id, recent_conversation_limit
    )
    if conversation_history_store is None:
        unavailable.append("recent_conversation")

    active_pointer = _project_active_pointer(session)
    attempt_history = list(getattr(session, "last_goal_attempt_history", None) or [])
    session_facts = _project_session_facts(session)
    if session is None:
        unavailable.extend(["active_pointer", "attempt_history", "session_facts"])

    # M30.2: the CapabilityDirectory is now the preferred, canonical
    # source for capability_summaries - a strict superset of what the
    # M30.1 direct dual-source projection produced (same underlying
    # data, unified shape, honest availability_known per source). The
    # M30.1 path is kept, unchanged, as the fallback whenever no
    # directory is given, so nothing that already depends on this
    # function's M30.1 signature/behavior breaks.
    if capability_directory is not None:
        try:
            capability_summaries = capability_directory.summaries()
        except Exception:
            capability_summaries = []
    else:
        capability_summaries = _project_capability_summaries(
            capability_feasibility, multi_action_registry
        )
    if (
        capability_directory is None
        and capability_feasibility is None
        and multi_action_registry is None
    ):
        unavailable.append("capability_summaries")

    runtime_health = _project_runtime_health(active_provider_id, active_model, health_tracker)
    if active_provider_id is None or active_model is None:
        unavailable.append("runtime_health")

    if durable_memory_relevant is None:
        unavailable.append("durable_memory_relevant")
    if graph_context is None:
        unavailable.append("graph_context")
    if capability_index_hint is None:
        unavailable.append("capability_index_hint")

    # M30.6's scope, not this milestone's - reported honestly as absent
    # rather than silently omitted from the shape entirely.
    unavailable.append("grounded_entities")

    data: Dict[str, Any] = {
        "turn": {
            "user_text": user_text,
            "session_id": session_id,
            "principal_id": principal_id,
        },
        "recent_conversation": recent_conversation,
        "active_pointer": active_pointer,
        "attempt_history": attempt_history,
        "session_facts": session_facts,
        "capability_summaries": capability_summaries,
        "runtime_health": runtime_health,
        "grounded_entities": {},
        "durable_memory_relevant": durable_memory_relevant or [],
        "graph_context": graph_context or {},
        "capability_index_hint": capability_index_hint or [],
    }

    return TurnStateResult(data=data, unavailable_fields=unavailable)
