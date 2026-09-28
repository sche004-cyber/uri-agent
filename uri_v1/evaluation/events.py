"""Versioned structured evaluation events (Plan A R2.12, Plan B R1.3).

One stream carries Change taps, positive/negative feedback, and edit
corrections, each attached to a response trace. Events hold identifiers and
closed-vocabulary values only: no prompt, reply, comment, or document text.
Field names follow the OpenTelemetry GenAI `gen_ai.evaluation.result` event
where the meaning matches (`evaluation_name`, `label`); its free-text
`explanation` has no counterpart here by design.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from enum import Enum
import re
from typing import Any, Mapping, Optional
from uuid import uuid4

from .trace_context import is_valid_span_id, require_trace_id

EVALUATION_SCHEMA_VERSION = "m33.3-r.s7.evaluation.v1"
_IDENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:\-]{0,127}$")
_MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/\-@]{0,127}$")


class EvaluationEventType(str, Enum):
    CHANGE = "CHANGE"
    FEEDBACK_POSITIVE = "FEEDBACK_POSITIVE"
    FEEDBACK_NEGATIVE = "FEEDBACK_NEGATIVE"
    EDIT_CORRECTION = "EDIT_CORRECTION"


class EvaluationCategory(str, Enum):
    WRONG_REFERENCE = "wrong_reference"   # examines context / RAR
    WORDING = "wording"                   # examines drafting of clarification/reply text
    DRAFTING = "drafting"                 # examines produced drafts/results
    ACTION = "action"                     # examines tool binding and execution
    ROUTE = "route"                       # examines the chosen intelligence route
    OTHER = "other"


class RedoOutcome(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    REDO_AUTHORIZED = "REDO_AUTHORIZED"
    REDO_NOT_EXECUTED = "REDO_NOT_EXECUTED"
    REDONE = "REDONE"
    VERSIONED = "VERSIONED"


_LABEL = {
    EvaluationEventType.CHANGE: "changed",
    EvaluationEventType.FEEDBACK_POSITIVE: "positive",
    EvaluationEventType.FEEDBACK_NEGATIVE: "negative",
    EvaluationEventType.EDIT_CORRECTION: "corrected",
}
_CHANGE_BINDING_STATES = frozenset({"TENTATIVE", "TENTATIVE_APPLIED"})
_ROUTE_TARGETS = frozenset({"DETERMINISTIC", "EDGE", "CAPABLE", "LIMITATION"})


class EvaluationEventError(ValueError):
    pass


@dataclass(frozen=True)
class EvaluationEvent:
    trace_id: str
    event_type: EvaluationEventType
    category: EvaluationCategory
    timestamp: str
    event_id: str
    schema_version: str = EVALUATION_SCHEMA_VERSION
    span_id: Optional[str] = None
    session_id: Optional[str] = None
    ambiguity_id: Optional[str] = None
    prior_candidate_id: Optional[str] = None
    new_candidate_id: Optional[str] = None
    binding_state: Optional[str] = None
    redo_outcome: RedoOutcome = RedoOutcome.NOT_APPLICABLE
    route_target: Optional[str] = None
    route_model_id: Optional[str] = None
    route_policy_version: Optional[str] = None
    route_version: Optional[str] = None
    task_class: Optional[str] = None
    result_id: Optional[str] = None
    version_from: Optional[int] = None
    version_to: Optional[int] = None
    comment_present: bool = False

    @property
    def evaluation_name(self) -> str:
        return f"uri.{self.category.value}"

    @property
    def label(self) -> str:
        return _LABEL[self.event_type]

    def __post_init__(self) -> None:
        validate_event(self)

    def redacted(self) -> dict[str, Any]:
        """Whitelist projection; unknown or raw content cannot leak."""
        data = asdict(self)
        out = {f.name: data[f.name] for f in fields(EvaluationEvent)}
        for key in ("event_type", "category", "redo_outcome"):
            out[key] = out[key].value
        out["evaluation_name"] = self.evaluation_name
        out["label"] = self.label
        return out


def _ident(value: Optional[str], name: str, pattern: re.Pattern = _IDENT) -> None:
    if value is not None and (not isinstance(value, str) or not pattern.fullmatch(value)):
        raise EvaluationEventError(f"{name} must be a bounded identifier")


def validate_event(event: EvaluationEvent) -> None:
    try:
        require_trace_id(event.trace_id)
    except ValueError as exc:
        raise EvaluationEventError(str(exc)) from exc
    if event.schema_version != EVALUATION_SCHEMA_VERSION:
        raise EvaluationEventError("unsupported evaluation schema version")
    if not event.event_id:
        raise EvaluationEventError("event_id is required")
    if not isinstance(event.event_type, EvaluationEventType) or not isinstance(event.category, EvaluationCategory) \
            or not isinstance(event.redo_outcome, RedoOutcome):
        raise EvaluationEventError("closed-vocabulary field has an unknown value")
    try:
        stamp = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise EvaluationEventError("timestamp must be RFC3339") from exc
    if stamp.tzinfo is None:
        raise EvaluationEventError("timestamp must be timezone-aware")
    if event.span_id is not None and not is_valid_span_id(event.span_id):
        raise EvaluationEventError("span_id must be W3C format")
    for name in ("event_id", "session_id", "ambiguity_id", "prior_candidate_id", "new_candidate_id",
                 "route_policy_version", "route_version", "task_class", "result_id"):
        _ident(getattr(event, name), name)
    _ident(event.route_model_id, "route_model_id", _MODEL)
    if event.route_target is not None and event.route_target not in _ROUTE_TARGETS:
        raise EvaluationEventError("route_target is not a router target")
    if type(event.comment_present) is not bool:
        raise EvaluationEventError("comment_present must be boolean")
    for name in ("version_from", "version_to"):
        value = getattr(event, name)
        if value is not None and (type(value) is not int or value < 1):
            raise EvaluationEventError(f"{name} must be a positive integer")
    if event.event_type == EvaluationEventType.CHANGE:
        if event.category != EvaluationCategory.WRONG_REFERENCE:
            raise EvaluationEventError("a Change is a wrong_reference evaluation")
        if not (event.ambiguity_id and event.prior_candidate_id and event.new_candidate_id):
            raise EvaluationEventError("a Change needs ambiguity_id and prior/new candidate IDs")
        if event.prior_candidate_id == event.new_candidate_id:
            raise EvaluationEventError("a Change must name a different candidate")
        if event.binding_state not in _CHANGE_BINDING_STATES:
            raise EvaluationEventError("a Change applies only to a tentative binding")
    elif event.binding_state is not None:
        _ident(event.binding_state, "binding_state")
    if event.event_type == EvaluationEventType.EDIT_CORRECTION and not event.result_id:
        raise EvaluationEventError("an edit correction names the edited result")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def make_event(trace_id: str, event_type: EvaluationEventType | str, category: EvaluationCategory | str,
               *, timestamp: Optional[str] = None, **values: Any) -> EvaluationEvent:
    return EvaluationEvent(trace_id=trace_id, event_type=EvaluationEventType(event_type),
                           category=EvaluationCategory(category), timestamp=timestamp or _now(),
                           event_id=uuid4().hex, **values)


def wrong_reference_event(trace_id: str, *, ambiguity_id: str, prior_candidate_id: str, new_candidate_id: str,
                          binding_state: str = "TENTATIVE_APPLIED",
                          redo_outcome: RedoOutcome | str = RedoOutcome.NOT_APPLICABLE,
                          **values: Any) -> EvaluationEvent:
    """Plan A R2.12: a Change tap on a tentatively bound reference."""
    return make_event(trace_id, EvaluationEventType.CHANGE, EvaluationCategory.WRONG_REFERENCE,
                      ambiguity_id=ambiguity_id, prior_candidate_id=prior_candidate_id,
                      new_candidate_id=new_candidate_id, binding_state=binding_state,
                      redo_outcome=RedoOutcome(redo_outcome), **values)


def event_from_dict(data: Mapping[str, Any]) -> EvaluationEvent:
    """Strict parse of a stored/received event; unknown keys are rejected."""
    if not isinstance(data, Mapping):
        raise EvaluationEventError("event must be an object")
    derived = {"evaluation_name", "label"}
    allowed = {f.name for f in fields(EvaluationEvent)}
    unknown = set(data) - allowed - derived
    if unknown:
        raise EvaluationEventError(f"unknown event fields: {sorted(unknown)}")
    values = {k: v for k, v in data.items() if k in allowed}
    try:
        values["event_type"] = EvaluationEventType(values["event_type"])
        values["category"] = EvaluationCategory(values["category"])
        values["redo_outcome"] = RedoOutcome(values.get("redo_outcome", "NOT_APPLICABLE"))
    except (KeyError, ValueError) as exc:
        raise EvaluationEventError("invalid closed-vocabulary value") from exc
    event = EvaluationEvent(**values)
    for key in derived & set(data):
        if data[key] != getattr(event, key):
            raise EvaluationEventError(f"derived field {key} does not match")
    return event
