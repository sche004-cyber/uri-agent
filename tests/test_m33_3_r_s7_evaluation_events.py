"""M33.3-R S7: trace_id and the structured evaluation event stream."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
import uuid

import pytest

from uri_v1.evaluation import trace_context as tc
from uri_v1.evaluation.events import (
    EVALUATION_SCHEMA_VERSION, EvaluationCategory, EvaluationEvent, EvaluationEventError, EvaluationEventType,
    RedoOutcome, event_from_dict, make_event, wrong_reference_event,
)
from uri_v1.evaluation.store import EvaluationEventStore

USER = str(uuid.UUID(int=7))
TS = "2026-09-27T10:00:00Z"


def test_trace_id_is_w3c_format_and_unique():
    ids = {tc.new_trace_id() for _ in range(500)}
    assert len(ids) == 500 and all(tc.is_valid_trace_id(x) for x in ids)
    assert not tc.is_valid_trace_id("0" * 32)
    assert not tc.is_valid_trace_id("A" * 32)
    assert not tc.is_valid_trace_id("abc")
    span = tc.new_span_id()
    trace = tc.new_trace_id()
    assert tc.traceparent(trace, span) == f"00-{trace}-{span}-01"
    with pytest.raises(ValueError):
        tc.traceparent("0" * 32, span)


def test_wrong_reference_change_event_matches_plan_a_r2_12():
    trace = tc.new_trace_id()
    event = wrong_reference_event(trace, ambiguity_id="amb-1", prior_candidate_id="doc-1", new_candidate_id="doc-2",
                                  redo_outcome="REDO_NOT_EXECUTED", timestamp=TS)
    data = event.redacted()
    assert data["category"] == "wrong_reference" and data["event_type"] == "CHANGE"
    assert data["binding_state"] == "TENTATIVE_APPLIED" and data["trace_id"] == trace
    assert data["evaluation_name"] == "uri.wrong_reference" and data["label"] == "changed"
    assert data["schema_version"] == EVALUATION_SCHEMA_VERSION
    assert event_from_dict(json.loads(json.dumps(data))) == event


@pytest.mark.parametrize("bad", [
    dict(prior_candidate_id="doc-1", new_candidate_id="doc-1"),
    dict(binding_state="CONFIRMED"),
    dict(ambiguity_id=None),
])
def test_change_rules_fail_closed(bad):
    values = dict(ambiguity_id="amb", prior_candidate_id="a", new_candidate_id="b", binding_state="TENTATIVE")
    values.update(bad)
    with pytest.raises(EvaluationEventError):
        make_event(tc.new_trace_id(), "CHANGE", "wrong_reference", timestamp=TS, **values)
    with pytest.raises(EvaluationEventError):
        make_event(tc.new_trace_id(), "CHANGE", "wording", timestamp=TS,
                   ambiguity_id="amb", prior_candidate_id="a", new_candidate_id="b", binding_state="TENTATIVE")


@pytest.mark.parametrize("field,value", [
    ("session_id", "the quarterly budget report for Alice"),
    ("prior_candidate_id", "Q3 Budget (draft).docx"),
    ("task_class", "please email bob about the contract"),
    ("route_model_id", "model with spaces"),
    ("result_id", "x" * 200),
])
def test_raw_text_cannot_enter_identifier_fields(field, value):
    with pytest.raises(EvaluationEventError):
        make_event(tc.new_trace_id(), "FEEDBACK_NEGATIVE", "drafting", timestamp=TS, **{field: value})


def test_unknown_fields_and_bad_values_rejected_on_parse():
    good = make_event(tc.new_trace_id(), "FEEDBACK_POSITIVE", "route", timestamp=TS,
                      route_target="EDGE", route_model_id="qwen3.5-2b").redacted()
    with pytest.raises(EvaluationEventError):
        event_from_dict({**good, "comment": "raw user text"})
    with pytest.raises(EvaluationEventError):
        event_from_dict({**good, "category": "unknown"})
    with pytest.raises(EvaluationEventError):
        event_from_dict({**good, "label": "negative"})
    with pytest.raises(EvaluationEventError):
        event_from_dict({**good, "schema_version": "v0"})
    with pytest.raises(EvaluationEventError):
        make_event(tc.new_trace_id(), "FEEDBACK_POSITIVE", "route", timestamp=TS, route_target="MAIN")
    with pytest.raises(EvaluationEventError):
        make_event(tc.new_trace_id(), "EDIT_CORRECTION", "drafting", timestamp=TS)
    with pytest.raises(EvaluationEventError):
        make_event("not-a-trace", "FEEDBACK_POSITIVE", "route", timestamp=TS)
    with pytest.raises(EvaluationEventError):
        make_event(tc.new_trace_id(), "FEEDBACK_POSITIVE", "route", timestamp="2026-09-27T10:00:00")


def test_comment_text_is_never_stored_only_presence(tmp_path):
    event = make_event(tc.new_trace_id(), "FEEDBACK_NEGATIVE", "wording", timestamp=TS, comment_present=True)
    store = EvaluationEventStore(USER, root=str(tmp_path))
    store.record(event)
    raw = "".join(p.read_text(encoding="utf-8") for p in Path(tmp_path).rglob("*.jsonl"))
    assert '"comment_present": true' in raw and "comment\":" not in raw.replace("comment_present", "")


def test_store_on_off_session_evidence_inspect_delete_reset(tmp_path):
    store = EvaluationEventStore(USER, root=str(tmp_path))
    assert store.durable_enabled() is True  # default ON
    first = make_event(tc.new_trace_id(), "FEEDBACK_POSITIVE", "route", timestamp=TS, session_id="sess-1")
    assert store.record(first) == {"session": True, "durable": True}
    store.set_durable_enabled(False)
    second = make_event(tc.new_trace_id(), "FEEDBACK_NEGATIVE", "route", timestamp=TS, session_id="sess-1")
    assert store.record(second) == {"session": True, "durable": False}
    assert [e.event_id for e in store.list_events()] == [first.event_id]  # OFF writes nothing durable
    assert [e.event_id for e in store.session_events("sess-1")] == [first.event_id, second.event_id]
    store.discard_session("sess-1")
    assert store.session_events("sess-1") == []
    store.set_durable_enabled(True)
    third = make_event(tc.new_trace_id(), "FEEDBACK_NEGATIVE", "route", timestamp="2026-10-02T00:00:00Z")
    store.record(third)
    assert {p.name for p in Path(tmp_path).rglob("*.jsonl")} == {"2026-09.jsonl", "2026-10.jsonl"}
    assert store.delete_event(first.event_id) is True
    assert [e.event_id for e in store.list_events()] == [third.event_id]
    assert store.reset() == 2 and store.list_events() == []


def test_unreadable_control_fails_closed_and_corrupt_lines_are_skipped(tmp_path):
    store = EvaluationEventStore(USER, root=str(tmp_path))
    Path(store._settings_path).parent.mkdir(parents=True, exist_ok=True)
    Path(store._settings_path).write_text("{broken", encoding="utf-8")
    assert store.durable_enabled() is False
    store.set_durable_enabled(True)
    event = make_event(tc.new_trace_id(), "FEEDBACK_POSITIVE", "route", timestamp=TS)
    store.record(event)
    path = next(Path(tmp_path).rglob("2026-09.jsonl"))
    path.write_text(path.read_text() + '{"trace_id": "x"}\nnot json\n', encoding="utf-8")
    assert [e.event_id for e in store.list_events()] == [event.event_id]


def test_store_rejects_unvalidated_values_and_user_ids(tmp_path):
    store = EvaluationEventStore(USER, root=str(tmp_path))
    with pytest.raises(EvaluationEventError):
        store.record({"trace_id": tc.new_trace_id()})
    with pytest.raises(Exception):
        EvaluationEventStore("../escape", root=str(tmp_path))


def test_event_is_immutable_and_revalidated():
    event = make_event(tc.new_trace_id(), "FEEDBACK_POSITIVE", "route", timestamp=TS)
    with pytest.raises(Exception):
        event.category = EvaluationCategory.OTHER  # type: ignore[misc]
    with pytest.raises(EvaluationEventError):
        replace(event, trace_id="0" * 32)
