"""Reproductions from the independent S1 implementation audit."""

from hashlib import sha256
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

import pytest

from uri_v1.reference_clarification.binding import BindingService
from uri_v1.reference_clarification.builder import BuildResult, build_clarification
from uri_v1.reference_clarification.render_validator import validate_render
from uri_v1.reference_clarification.safeguards import ClarificationSafeguards
from uri_v1.reference_clarification.template_renderer import render_template
from uri_v1.turn.rar_clarification_contract import (
    BindingState, CandidateFact, ClarificationKind, ClarificationResponse, ResponseKind,
)
from uri_v1.turn.rar_contracts import RARBasis, RARCandidate, RAROutcome, RARQuery, RARResolution


def _fixture():
    query = RARQuery("the report", (
        RARCandidate("x", "Report X", "document"),
        RARCandidate("y", "Report Y", "document"),
    ))
    resolved = RARResolution(query.reference_expression, RAROutcome.RESOLVED,
                             candidate_id="x", basis=RARBasis.DETERMINISTIC_ANCHOR)
    ambiguous = RARResolution(query.reference_expression, RAROutcome.AMBIGUOUS,
                              ambiguous_candidate_ids=query.candidate_ids,
                              basis=RARBasis.DETERMINISTIC_ANCHOR)
    return query, resolved, ambiguous


def _source(service, *, applied=False):
    query, resolved, ambiguous = _fixture()
    built = build_clarification(query, resolved, session_id="s", turn_id="t",
                                wrong_binding_impact="RECOVERABLE")
    source_id = service.register(built, query).binding_id
    if applied:
        service.record_execution(source_id)
    return query, ambiguous, source_id


def _change(service, query, ambiguous, source_id):
    result = service.open_change(source_id, query, ambiguous,
                                 impact_reader=lambda: "RECOVERABLE", turn_id="t")
    contract = service.store.rounds[result.next_contract_id].contract
    response = ClarificationResponse(contract.ambiguity_id, ResponseKind.CANDIDATE,
        candidate_id="y", candidate_set_fingerprint=contract.candidate_set_fingerprint)
    return contract, response


def test_kb1_preexecution_change_retires_source():
    service = BindingService()
    query, ambiguous, source_id = _source(service)
    contract, response = _change(service, query, ambiguous, source_id)
    assert service.respond("s", response, query, impact_reader=lambda: "RECOVERABLE").state == BindingState.CONFIRMED
    with pytest.raises(ValueError):
        service.record_execution(source_id)
    assert service.open_change(source_id, query, ambiguous,
        impact_reader=lambda: "RECOVERABLE", turn_id="t").state == BindingState.REJECTED


def test_kb1_concurrent_change_rounds_only_one_can_bind():
    service = BindingService()
    query, ambiguous, source_id = _source(service, applied=True)
    first, first_response = _change(service, query, ambiguous, source_id)
    second, second_response = _change(service, query, ambiguous, source_id)
    assert service.respond("s", first_response, query, impact_reader=lambda: "RECOVERABLE").state == BindingState.CONFIRMED
    assert service.respond("s", second_response, query, impact_reader=lambda: "RECOVERABLE").state == BindingState.REJECTED
    assert service.store.bindings[source_id].applied_result_exists


def test_kb1_simultaneous_change_confirmations_have_one_winner():
    service = BindingService()
    query, ambiguous, source_id = _source(service, applied=True)
    first = _change(service, query, ambiguous, source_id)
    second = _change(service, query, ambiguous, source_id)
    start = Barrier(2)
    def confirm(item):
        start.wait()
        return service.respond("s", item[1], query, impact_reader=lambda: "RECOVERABLE").state
    with ThreadPoolExecutor(max_workers=2) as workers:
        states = tuple(workers.map(confirm, (first, second)))
    assert set(states) == {BindingState.CONFIRMED, BindingState.REJECTED}


def test_kb2_safeguards_are_session_and_turn_scoped():
    query, _, ambiguous = _fixture()
    service = BindingService(safeguards=ClarificationSafeguards(4, 1))
    def act(session, turn):
        built = build_clarification(query, ambiguous, session_id=session, turn_id=turn,
                                    wrong_binding_impact="RECOVERABLE")
        service.register(built, query)
        return service.respond(session, ClarificationResponse(built.contract.ambiguity_id,
            ResponseKind.FREE_INPUT, text="x"), query, wrong_binding_impact="RECOVERABLE")
    assert act("A", "t1").state == BindingState.CONFIRMED
    assert act("A", "t1").state == BindingState.REJECTED
    assert act("B", "t1").state == BindingState.CONFIRMED
    assert act("A", "t2").state == BindingState.CONFIRMED


def test_kb3_builder_failure_rejects_without_partial_evidence_and_can_rebuild():
    query = RARQuery("the report", (
        RARCandidate("a", "Report", "document", owner="Alice"),
        RARCandidate("b", "Report", "document", owner="Bob"),
    ))
    ambiguous = RARResolution(query.reference_expression, RAROutcome.AMBIGUOUS,
        ambiguous_candidate_ids=query.candidate_ids, basis=RARBasis.DETERMINISTIC_ANCHOR)
    service = BindingService()
    built = build_clarification(query, ambiguous, session_id="s", turn_id="t",
                                wrong_binding_impact="RECOVERABLE")
    service.register(built, query)
    response = ClarificationResponse(built.contract.ambiguity_id, ResponseKind.ATTRIBUTE,
        option_key="a1", candidate_set_fingerprint=built.contract.candidate_set_fingerprint)
    with patch("uri_v1.reference_clarification.binding.build_clarification", side_effect=ValueError("forced failure")):
        result = service.respond("s", response, query, wrong_binding_impact="RECOVERABLE")
    record = service.store.rounds[built.contract.ambiguity_id]
    assert result.state == BindingState.REJECTED
    assert record.state == BindingState.REJECTED and not record.used
    assert not service.session_evidence.get("s") or not service.session_evidence["s"].clues
    assert service.rebuild_rejected(built.contract.ambiguity_id, query).next_contract_id


def test_kb3_free_input_build_failure_is_recoverable():
    query, _, ambiguous = _fixture()
    service = BindingService()
    built = build_clarification(query, ambiguous, session_id="s", turn_id="t",
                                wrong_binding_impact="RECOVERABLE")
    service.register(built, query)
    response = ClarificationResponse(built.contract.ambiguity_id, ResponseKind.FREE_INPUT,
                                     text="unmatched reference")
    with patch("uri_v1.reference_clarification.binding.build_clarification", side_effect=ValueError("forced failure")):
        result = service.respond("s", response, query, wrong_binding_impact="RECOVERABLE")
    record = service.store.rounds[built.contract.ambiguity_id]
    assert result.state == BindingState.REJECTED
    assert record.state == BindingState.REJECTED and not record.used
    assert service.rebuild_rejected(built.contract.ambiguity_id, query).next_contract_id


def test_kb4_protected_hash_is_line_ending_portable():
    root = Path(__file__).resolve().parents[1]
    protected = {
        "uri_v1/turn/rar_deterministic.py": "e02af25bb7009d12d829c8b8fc92e487d3da75aeaa160092db617458278fb649",
        "uri_v1/turn/rar_contracts.py": "4cc9aa43726a870ca2e9ab1b19f6bf9d72dcb74c8a2818856776af95195b6819",
    }
    for name, expected in protected.items():
        lf = (root / name).read_bytes().replace(b"\r\n", b"\n")
        crlf = lf.replace(b"\n", b"\r\n")
        assert sha256(lf).hexdigest() == expected
        assert sha256(crlf.replace(b"\r\n", b"\n")).hexdigest() == expected


def test_f4_case_only_attribute_values_fall_back_when_grounded_labels_exist():
    query = RARQuery("report", (
        RARCandidate("a", "Report", "document", owner="Alice"),
        RARCandidate("b", "Report", "document", owner="alice"),
    ))
    ambiguous = RARResolution(query.reference_expression, RAROutcome.AMBIGUOUS,
        ambiguous_candidate_ids=query.candidate_ids, basis=RARBasis.DETERMINISTIC_ANCHOR)
    built = build_clarification(query, ambiguous, session_id="s", turn_id="t",
        wrong_binding_impact="RECOVERABLE", extra_facts={
            "a": (CandidateFact("locator", "A", "fixture:a"),),
            "b": (CandidateFact("locator", "B", "fixture:b"),),
        })
    assert built.contract.kind == ClarificationKind.CHOOSE_ONE
    assert validate_render(built.contract, render_template(built.contract)).valid


def test_truthy_string_does_not_grant_redo_authorization():
    service = BindingService()
    query, ambiguous, source_id = _source(service, applied=True)
    contract, response = _change(service, query, ambiguous, source_id)
    assert service.respond("s", response, query, impact_reader=lambda: "RECOVERABLE").state == BindingState.CONFIRMED
    assert service.authorize_redo(contract.ambiguity_id, fresh_authorized="false",
                                  edited_result_status="UNEDITED") == BindingState.REDO_NOT_EXECUTED


def test_forged_direct_confirmation_cannot_bypass_rar_authority():
    query, _, _ = _fixture()
    service = BindingService()
    with pytest.raises(ValueError, match="certainty"):
        service.register(BuildResult(BindingState.CONFIRMED, candidate_id="x",
            binding_id="forged", session_id="s"), query)
    assert not service.store.bindings


def test_grounded_title_word_does_not_make_template_a_selection_claim():
    query = RARQuery("report", (
        RARCandidate("a", "Recommended Report", "document"),
        RARCandidate("b", "Report B", "document"),
    ))
    ambiguous = RARResolution(query.reference_expression, RAROutcome.AMBIGUOUS,
        ambiguous_candidate_ids=query.candidate_ids, basis=RARBasis.DETERMINISTIC_ANCHOR)
    contract = build_clarification(query, ambiguous, session_id="s", turn_id="t",
        wrong_binding_impact="RECOVERABLE").contract
    assert validate_render(contract, render_template(contract)).valid
