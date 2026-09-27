"""M33.3-R S12: the UI fixture payloads bind through the frozen S1 BindingService.

The Flutter test proves the card emits exactly `expected_payloads`; this test
proves those payloads, replayed against a freshly built S1 contract for the
same battery case, bind the grounded candidate (or narrow by attribute) —
closing the UI <-> core loop without any production wiring.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.m33_3_r_s12_export_fixtures import OUT, card as export_card
from scripts.m33_3_r_s5_qualify import NOW, build_contract, load_battery
from uri_v1.reference_clarification.binding import BindingService
from uri_v1.reference_clarification.builder import BuildResult
from uri_v1.turn.rar_clarification_contract import BindingState, ClarificationResponse, ResponseKind

DOC = json.loads(Path(OUT).read_text(encoding="utf-8"))
BATTERY = {c["case_id"]: c for c in load_battery()[0]["cases"]}


def test_fixture_is_current_export_of_frozen_contracts():
    for i, card in enumerate(DOC["cards"], 1):
        assert export_card(BATTERY[card["case_id"]], i) == card
    assert DOC["fixture_only"] is True


def fresh(case_id):
    query, contract = build_contract(BATTERY[case_id])
    service = BindingService()
    registered = service.register(BuildResult(BindingState.PENDING, contract=contract), query)
    return query, service.store.rounds[registered.next_contract_id].contract, service


def to_response(payload: dict, ambiguity_id: str) -> ClarificationResponse:
    kind = ResponseKind(payload["response_kind"])
    return ClarificationResponse(ambiguity_id, kind, candidate_id=payload.get("candidate_id"),
                                 option_key=payload.get("option_key"), text=payload.get("text"),
                                 candidate_set_fingerprint=payload.get("candidate_set_fingerprint"))


@pytest.mark.parametrize("card", DOC["cards"], ids=lambda c: c["case_id"])
def test_every_emitted_payload_is_accepted_by_s1(card):
    for key, payload in card["expected_payloads"].items():
        query, contract, service = fresh(card["case_id"])
        assert payload["candidate_set_fingerprint"] == contract.candidate_set_fingerprint
        result = service.respond(contract.session_id, to_response(payload, contract.ambiguity_id), query,
                                 wrong_binding_impact=BATTERY[card["case_id"]]["input"]["impact"], now=NOW)
        if payload["response_kind"] == "CANDIDATE":
            assert result.state == BindingState.CONFIRMED and result.candidate_id == payload["candidate_id"], key
        else:  # attribute choice narrows and never produces CONFIRMED (R3.1 / F-U1)
            assert result.state != BindingState.CONFIRMED, key
            option = next(o for o in contract.attribute_options if o.option_key == key)
            if result.state == BindingState.TENTATIVE:  # one member left, recoverable impact
                assert result.candidate_id in option.member_candidate_ids, key
            else:
                assert result.candidate_id is None and result.next_contract_id is not None, key


def test_label_text_as_candidate_id_is_rejected():
    card = DOC["cards"][0]
    query, contract, service = fresh(card["case_id"])
    option = card["options"][0]
    forged = {**card["expected_payloads"][option["option_key"]], "candidate_id": option["label"]}
    result = service.respond(contract.session_id, to_response(forged, contract.ambiguity_id), query,
                             wrong_binding_impact="RECOVERABLE", now=NOW)
    assert result.state == BindingState.REJECTED


def test_free_input_title_is_authoritative_new_reference():
    card = next(c for c in DOC["cards"] if c["kind"] == "CHOOSE_ONE")
    query, contract, service = fresh(card["case_id"])
    target = query.get_candidate(card["options"][1]["candidate_id"])
    payload = {**card["expected_free_input_payload"], "text": target.id}
    result = service.respond(contract.session_id, to_response(payload, contract.ambiguity_id), query,
                             wrong_binding_impact="RECOVERABLE", now=NOW)
    assert result.candidate_id == target.id and result.state == BindingState.CONFIRMED
