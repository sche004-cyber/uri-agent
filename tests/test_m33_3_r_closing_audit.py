"""Independent closing-audit falsification regressions; no production integration."""
from dataclasses import replace
from datetime import datetime, timezone
import json

import pytest

from scripts.m33_3_r_s5_qualify import build_contract, load_battery
from uri_v1.reference_clarification.render_validator import validate_render
from uri_v1.reference_clarification.template_renderer import render_template
from uri_v1.evaluation.trace_context import is_valid_span_id, is_valid_trace_id, new_trace_id
from uri_v1.evaluation.events import make_event, EvaluationEventError
from uri_v1.evaluation.route_performance import (
    RouteKey, RoutePerformanceRecord, RoutePerformanceStore, PreferenceConfig,
    choose_route, record_reward,
)
from uri_core.core.edge.lease_ownership import LeaseOwnershipLedger, new_uri_instance_id


@pytest.mark.parametrize("fact", ["May", "Will", "2027", "Mars", "report.pdf"])
def test_s1_amendment_does_not_admit_ungrounded_dates_names_or_values(fact):
    contract = build_contract(load_battery()[0]["cases"][0])[1]
    rendered = render_template(contract)
    output = {"question": f"Which file from {fact} do you mean?", "labels": dict(rendered.labels)}
    assert "V-UNSUPPORTED-FACT" in validate_render(contract, output).flags


def test_s1_amendment_still_accepts_ordinary_grammar():
    contract = build_contract(load_battery()[0]["cases"][0])[1]
    rendered = render_template(contract)
    output = {"question": "Which of these is the one you mean, or is it another?", "labels": dict(rendered.labels)}
    assert validate_render(contract, output).valid


def test_s7_identifiers_are_exact_and_require_event_provenance():
    assert not is_valid_trace_id("1" * 32 + "\n")
    assert not is_valid_trace_id("0" * 32 + "\n")
    assert not is_valid_span_id("1" * 16 + "\n")
    event = make_event(new_trace_id(), "FEEDBACK_NEGATIVE", "WORDING".lower())
    for changes in ({"event_id": None}, {"event_id": ""}, {"session_id": "secret\n"}):
        with pytest.raises(EvaluationEventError):
            replace(event, **changes)


def record(**changes):
    values = dict(route=RouteKey("EXPLAIN", "EDGE", "edge", "v1"), outcome="SUCCESS",
                  feedback="none", latency_ms=1, timestamp=datetime.now(timezone.utc).isoformat())
    values.update(changes)
    return RoutePerformanceRecord(**values)


@pytest.mark.parametrize("changes", [
    {"trace_id": "private conversation text"}, {"trace_id": "0" * 32},
    {"latency_ms": float("inf")}, {"latency_ms": True},
    {"timestamp": "2026-09-27"}, {"schema_version": "other"},
    {"route": {"raw_text": "conversation"}},
])
def test_s8_rejects_unstructured_or_unusable_records(changes):
    with pytest.raises(ValueError):
        record(**changes)


def test_s8_negative_feedback_cannot_reward_a_successful_but_disliked_route():
    negative = record(feedback="negative")
    assert record_reward(negative, PreferenceConfig()) == (0.0, 3.0)
    default = RouteKey("EXPLAIN", "DETERMINISTIC", "template", "v1")
    records = [record(route=default, outcome="FALLBACK")] * 10 + [negative] * 10
    assert choose_route("EXPLAIN", default, [default, negative.route], records,
                        now=datetime.now(timezone.utc))[0] == default


def test_s8_malformed_settings_fail_closed(tmp_path):
    store = RoutePerformanceStore("00000000-0000-0000-0000-000000000008", root=str(tmp_path))
    store.set_enabled(False)
    from pathlib import Path
    Path(store._settings).write_text(json.dumps([]), encoding="utf-8")
    assert not store.enabled()
    assert not store.record(record())


def test_s10_matching_instance_name_does_not_confer_other_lease_ownership():
    ledger = LeaseOwnershipLedger()
    own = ledger.record_acquired(runtime_id="lmstudio", model_id="edge", provider_instance_id=new_uri_instance_id())
    for changed in (replace(own, runtime_id="ollama"), replace(own, model_id="external"),
                    replace(own, lease_id="forged"), replace(own, owner_kind="EXTERNAL")):
        assert not ledger.may_unload(changed)
    for runtime, model in (("ollama", "edge"), ("lmstudio", "external")):
        classified = ledger.classify(runtime, [(own.provider_instance_id, model)])[0]
        assert classified.owner_kind == "EXTERNAL"
        assert not ledger.may_unload(classified)
    assert not ledger.may_unload(own)
    assert not ledger.may_unload(own.provider_instance_id)
    assert ledger.active() == ()


def test_s8_replay_refuses_stale_gate_evidence(tmp_path, monkeypatch):
    from scripts import m33_3_r_s8_replay as replay
    for name, contents in (("GATE", {"production_config": {"prompt_version": "new"}}),
                           ("FINAL_TELEMETRY", []),
                           ("FINAL_AGGREGATES", {"gate_evaluation": {"gate_sha256": "old"}})):
        path = tmp_path / (name + ".json")
        path.write_text(json.dumps(contents), encoding="utf-8")
        monkeypatch.setattr(replay, name, path)
    with pytest.raises(ValueError, match="current frozen gate"):
        replay.load_inputs()


def test_s8_synthetic_method_uses_held_out_evaluation_and_checks_snips():
    from scripts.m33_3_r_s8_replay import method_validation
    result = method_validation(808)
    assert result["training_events"] == 1000
    assert result["held_out_events"] == 4000
    assert result["passed"] and result["learner_chose"] == "B"
    assert abs(result["snips_estimate"] - 0.9) < 0.05
    assert result["replay_accepted"] > 0


def test_s11_unknown_persisted_origin_cannot_be_read_back_as_unedited(tmp_path):
    from uri_v1.results.version_ledger import ResultVersionLedger, ResultVersionError
    ledger = ResultVersionLedger("00000000-0000-0000-0000-000000000008", root=str(tmp_path))
    ledger.record_generated("result", b"content")
    path = ledger._path("result")
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["versions"][0]["origin"] = "UNKNOWN_ORIGIN"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ResultVersionError, match="unknown version origin"):
        ledger.edited_status("result", b"content")
    with pytest.raises(ResultVersionError):
        ledger.blob("../external-file")
    with pytest.raises(ResultVersionError):
        ledger.head("result\n")
