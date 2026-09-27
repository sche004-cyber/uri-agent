"""M33.3-R S5: wording need class, renderer port/adapters, policy-mode selector, L3 battery."""

from __future__ import annotations

import io
import json

import pytest

from scripts.m33_3_r_s5_qualify import (INVENTORY, build_contract, deterministic_checks, load_battery,
                                        select_wording_policy as select_wording, settings)
from uri_core.core.edge.routing_policy import RouteTarget, WordingNeedClass
from uri_v1.evaluation.trace_context import is_valid_trace_id
from uri_v1.reference_clarification.render_contracts import make_render_request
from uri_v1.reference_clarification.template_renderer import render_template
from uri_v1.turn.rar_clarification_contract import ESCAPE_LABEL
from uri_v1.wording.need_class import classify_need
from uri_v1.wording.renderer_port import LMStudioRenderer, output_schema, request_payload

BATTERY, MANIFEST = load_battery()
CASES = {c["case_id"]: c for c in BATTERY["cases"]}


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeLMStudio:
    """Records calls; simulates load state and a completion body."""

    def __init__(self, state="loaded", text=None):
        self.state, self.text, self.completions = state, text, []

    def __call__(self, req, timeout=None):
        if isinstance(req, str):
            return FakeResponse(json.dumps({"state": self.state}).encode())
        self.completions.append(json.loads(req.data.decode()))
        self.state = "loaded"  # a real JIT request would load the model
        return FakeResponse(json.dumps({"choices": [{"text": self.text}],
                                        "usage": {"prompt_tokens": 10, "completion_tokens": 5}}).encode())


def case_with(need):
    for case in BATTERY["cases"]:
        _, contract = build_contract(case)
        if classify_need(contract) == need:
            return case, contract
    raise AssertionError(need)


def test_battery_is_hash_anchored_and_complete():
    assert MANIFEST["case_count"] == len(BATTERY["cases"]) == 60
    assert {c["part"] for c in BATTERY["cases"]} == {"A", "B"}
    assert all(c["source_case_id"].startswith("ARB-") for c in BATTERY["cases"] if c["part"] == "A")


def test_deterministic_frozen_gates_hold_on_whole_battery():
    det = deterministic_checks(BATTERY["cases"])
    assert det["violations"] == []
    assert det["template_valid_all"]
    assert set(det["need_class_counts"]) == {"SIMPLE", "EXPLAIN", "REASONING"}


def test_request_payload_hides_candidate_ids():
    for case in BATTERY["cases"]:
        query, contract = build_contract(case)
        text = json.dumps(request_payload(make_render_request(contract)))
        assert not any(cid in text for cid in query.candidate_ids), case["case_id"]


def test_schema_pins_exact_slot_keys():
    _, contract = case_with(WordingNeedClass.EXPLAIN)
    schema = output_schema(make_render_request(contract))
    keys = [k for k, _ in make_render_request(contract).slots]
    assert schema["properties"]["labels"]["required"] == keys
    assert schema["properties"]["labels"]["additionalProperties"] is False and schema["additionalProperties"] is False


def test_adapter_refuses_cold_load_and_sends_constrained_request():
    _, contract = case_with(WordingNeedClass.EXPLAIN)
    cold = FakeLMStudio(state="not-loaded")
    attempt = LMStudioRenderer("edge", "qwen3.5-2b", opener=cold).render(make_render_request(contract), contract)
    assert attempt.error == "model_not_warm_no_cold_load" and cold.completions == [] and not attempt.cold_load_observed
    template = render_template(contract)
    warm = FakeLMStudio(text=json.dumps({"question": template.question, "labels": dict(template.labels)}))
    attempt = LMStudioRenderer("edge", "qwen3.5-2b", opener=warm).render(make_render_request(contract), contract)
    assert attempt.error is None and warm.completions[0]["response_format"]["type"] == "json_schema"
    assert warm.completions[0]["temperature"] == 0.0
    unconstrained = FakeLMStudio(text="{}")
    LMStudioRenderer("edge", "qwen3.5-2b", constrained=False, opener=unconstrained).render(make_render_request(contract), contract)
    assert "response_format" not in unconstrained.completions[0]


class StubRenderer:
    def __init__(self, arm, text, state="loaded"):
        self.arm, self.text, self.state, self.calls = arm, text, state, 0

    def model_state(self):
        return self.state

    def render(self, request, contract):
        from uri_v1.wording.renderer_port import RenderAttempt
        self.calls += 1
        return RenderAttempt(self.arm, self.text, 1.0, invoked_model=self.arm, model_state_before=self.state,
                             model_state_after=self.state)


def test_invalid_model_output_falls_back_to_template_fail_closed():
    query, contract = case_with(WordingNeedClass.EXPLAIN)
    keys = [k for k, _ in make_render_request(contract).slots]
    bad = json.dumps({"question": "I'll use the first one, ok?", "labels": {**{k: "x" for k in keys}, "s99": "Invented"}})
    edge = StubRenderer("edge", bad)
    result = select_wording(contract, settings=settings("HYBRID", True), inventory=INVENTORY, edge_renderer=edge,
                            capable_renderer=None, edge_wording_qualified=True, capable_available=False,
                            resource_admitted=True)
    assert edge.calls == 1 and result.tier_used == "template" and result.fallback_reason == "validator_reject"
    assert "V-SLOT-UNKNOWN" in result.model_flags
    assert result.options[-1] == ("escape", ESCAPE_LABEL)
    assert [k for k, _ in result.options[:-1]] == keys
    assert is_valid_trace_id(result.trace_id)


def test_valid_model_output_is_shown_in_uri_order():
    _, contract = case_with(WordingNeedClass.EXPLAIN)
    template = render_template(contract)
    reversed_labels = dict(reversed(template.labels))
    edge = StubRenderer("edge", json.dumps({"question": template.question, "labels": reversed_labels}))
    result = select_wording(contract, settings=settings("HYBRID", True), inventory=INVENTORY, edge_renderer=edge,
                            capable_renderer=None, edge_wording_qualified=True, capable_available=False,
                            resource_admitted=True)
    assert result.tier_used == "edge" and [k for k, _ in result.options[:-1]] == [k for k, _ in template.labels]


def test_reasoning_under_edge_only_is_template_limitation_without_models():
    _, contract = case_with(WordingNeedClass.REASONING)
    edge, capable = StubRenderer("edge", "{}"), StubRenderer("capable", "{}")
    result = select_wording(contract, settings=settings("EDGE_ONLY", True), inventory=INVENTORY, edge_renderer=edge,
                            capable_renderer=capable, edge_wording_qualified=True, capable_available=True,
                            resource_admitted=True, auto_capable_model_id="qwen3.5-9b")
    assert result.route.target == RouteTarget.LIMITATION and result.limitation and result.tier_used == "template"
    assert edge.calls == capable.calls == 0


def test_empty_question_accepted_by_frozen_validator_is_rejected_by_s5():
    from uri_v1.reference_clarification.render_validator import validate_render
    case = next(c for c in BATTERY["cases"] if build_contract(c)[1].kind.value == "FREE_INPUT_ONLY")
    _, contract = build_contract(case)
    empty = json.dumps({"question": "", "labels": {}})
    assert validate_render(contract, empty).valid  # disclosed frozen-S1 gap
    edge = StubRenderer("edge", empty)
    from uri_v1.wording.selector import validated_output
    output, flags = validated_output(contract, empty)
    assert output is None and "S5-EMPTY-TEXT" in flags


def test_caller_trace_id_is_validated():
    _, contract = case_with(WordingNeedClass.SIMPLE)
    with pytest.raises(ValueError):
        select_wording(contract, settings=settings("HYBRID", True), inventory=INVENTORY, edge_renderer=None,
                       capable_renderer=None, edge_wording_qualified=False, capable_available=False,
                       resource_admitted=False, trace_id="nope")
