from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from uri_v1.reference_clarification.builder import build_clarification
from uri_v1.reference_clarification.binding import BindingService
from uri_v1.reference_clarification.bundle import rebuild_dependent, visible_slots
from uri_v1.reference_clarification.safeguards import ClarificationSafeguards
from uri_v1.turn.rar_clarification_contract import (
    BindingState, ClarificationBundle, ClarificationKind, ClarificationResponse,
    ReferenceSlot, ResponseKind, validate_bundle, validate_contract,
)
from uri_v1.turn.rar_contracts import RARBasis, RARCandidate, RAROutcome, RARQuery, RARResolution


def pair():
    return (RARCandidate("x", "Report.pdf", "document", owner="Alice"),
            RARCandidate("y", "Report.pdf", "document", owner="Bob"))


def amb(query):
    return RARResolution(query.reference_expression, RAROutcome.AMBIGUOUS,
                         ambiguous_candidate_ids=query.candidate_ids,
                         basis=RARBasis.DETERMINISTIC_ANCHOR)


def test_attribute_narrows_without_confirmation_and_no_axis_repeat():
    query = RARQuery("the report", pair())
    built = build_clarification(query, amb(query), session_id="s", turn_id="t",
                                  wrong_binding_impact="RECOVERABLE")
    assert built.contract.kind == ClarificationKind.CHOOSE_ATTRIBUTE
    assert built.contract.attribute_axis == "owner"
    service = BindingService()
    service.register(built, query)
    response = ClarificationResponse(built.contract.ambiguity_id, ResponseKind.ATTRIBUTE,
        option_key="a1", candidate_set_fingerprint=built.contract.candidate_set_fingerprint)
    result = service.respond("s", response, query, wrong_binding_impact="RECOVERABLE")
    assert result.state in (BindingState.TENTATIVE, BindingState.PENDING)
    assert result.state != BindingState.CONFIRMED
    if result.next_contract_id:
        assert "owner" in service.store.rounds[result.next_contract_id].contract.answered_axes
        assert service.store.rounds[result.next_contract_id].contract.kind == ClarificationKind.CONFIRM_ONE


def test_attribute_narrowed_exact_title_still_not_confirmed():
    query = RARQuery("Report.pdf", pair())
    built = build_clarification(query, amb(query), session_id="s", turn_id="t",
                                  wrong_binding_impact="RECOVERABLE")
    service = BindingService()
    service.register(built, query)
    response = ClarificationResponse(built.contract.ambiguity_id, ResponseKind.ATTRIBUTE,
        option_key="a1", candidate_set_fingerprint=built.contract.candidate_set_fingerprint)
    assert service.respond("s", response, query, wrong_binding_impact="RECOVERABLE").state == BindingState.TENTATIVE


def test_attribute_narrowed_unknown_single_requires_confirm_one():
    query = RARQuery("unclear", pair()[:1])
    unknown = RARResolution("unclear", RAROutcome.UNKNOWN,
                            basis=RARBasis.DETERMINISTIC_ANCHOR)
    built = build_clarification(query, unknown, session_id="s", turn_id="t",
        wrong_binding_impact="RECOVERABLE", attribute_narrowed=True)
    assert built.contract.kind == ClarificationKind.CONFIRM_ONE


def test_attribute_payload_cannot_smuggle_candidate():
    query = RARQuery("the report", pair())
    built = build_clarification(query, amb(query), session_id="s", turn_id="t",
                                  wrong_binding_impact="RECOVERABLE")
    service = BindingService()
    service.register(built, query)
    response = ClarificationResponse(built.contract.ambiguity_id, ResponseKind.ATTRIBUTE,
        candidate_id="x", option_key="a1", candidate_set_fingerprint=built.contract.candidate_set_fingerprint)
    assert service.respond("s", response, query).state == BindingState.REJECTED


def test_free_text_matching_attribute_value_uses_stored_clue():
    query = RARQuery("the report", pair())
    built = build_clarification(query, amb(query), session_id="s", turn_id="t",
                                  wrong_binding_impact="RECOVERABLE")
    service = BindingService()
    service.register(built, query)
    value = built.contract.attribute_options[0].value
    result = service.respond("s", ClarificationResponse(built.contract.ambiguity_id,
        ResponseKind.FREE_INPUT, text=f" {value.lower()} "), query,
        wrong_binding_impact="RECOVERABLE")
    assert result.state in (BindingState.PENDING, BindingState.TENTATIVE)
    assert service.session_evidence["s"].clues == [("owner", value)]


def test_change_requires_rebind_and_pre_s11_redo_stops():
    query = RARQuery("the report", (RARCandidate("x", "Report X", "document"),
                                    RARCandidate("y", "Report Y", "document")))
    service = BindingService()
    original = build_clarification(query, RARResolution("the report", RAROutcome.RESOLVED,
        candidate_id="x", basis=RARBasis.DETERMINISTIC_ANCHOR), session_id="s", turn_id="t",
        wrong_binding_impact="RECOVERABLE")
    # A heuristic resolution is tentative-eligible under R2.9.
    assert original.state == BindingState.TENTATIVE
    original_id = service.register(original, query).binding_id
    service.record_execution(original_id)
    change = service.open_change(original_id, query, amb(query), impact_reader=lambda: "RECOVERABLE", turn_id="t2")
    assert change.state == BindingState.CHANGE_PENDING
    contract = service.store.rounds[change.next_contract_id].contract
    response = ClarificationResponse(contract.ambiguity_id, ResponseKind.CANDIDATE,
        candidate_id="y", candidate_set_fingerprint=contract.candidate_set_fingerprint)
    assert service.respond("s", response, query, impact_reader=lambda: "RECOVERABLE").state == BindingState.CONFIRMED
    assert service.authorize_redo(contract.ambiguity_id, fresh_authorized=True,
                                  edited_result_status="UNKNOWN") == BindingState.REDO_NOT_EXECUTED
    assert service.store.bindings[original_id].candidate_id == "x"


def test_change_to_same_binding_is_abandoned_and_preserves_x():
    query = RARQuery("the report", (RARCandidate("x", "Report X", "document"),
                                    RARCandidate("y", "Report Y", "document")))
    original = build_clarification(query, RARResolution("the report", RAROutcome.RESOLVED,
        candidate_id="x", basis=RARBasis.DETERMINISTIC_ANCHOR), session_id="s", turn_id="t",
        wrong_binding_impact="RECOVERABLE")
    service = BindingService()
    original_id = service.register(original, query).binding_id
    service.record_execution(original_id)
    change = service.open_change(original_id, query, amb(query), impact_reader=lambda: "RECOVERABLE", turn_id="t2")
    result = service.respond("s", ClarificationResponse(change.next_contract_id, ResponseKind.FREE_INPUT,
        text="Report X"), query, impact_reader=lambda: "RECOVERABLE")
    assert result.state == BindingState.CHANGE_ABANDONED
    assert service.store.bindings[original_id].state == BindingState.TENTATIVE_APPLIED


def test_fresh_redo_authorization_has_no_execution_path():
    query = RARQuery("the report", (RARCandidate("x", "Report X", "document"),
                                    RARCandidate("y", "Report Y", "document")))
    service = BindingService()
    initial = build_clarification(query, RARResolution("the report", RAROutcome.RESOLVED,
        candidate_id="x", basis=RARBasis.DETERMINISTIC_ANCHOR), session_id="s", turn_id="t",
        wrong_binding_impact="RECOVERABLE")
    original_id = service.register(initial, query).binding_id
    service.record_execution(original_id)
    change = service.open_change(original_id, query, amb(query), impact_reader=lambda: "RECOVERABLE", turn_id="t2")
    contract = service.store.rounds[change.next_contract_id].contract
    click = ClarificationResponse(contract.ambiguity_id, ResponseKind.CANDIDATE,
        candidate_id="y", candidate_set_fingerprint=contract.candidate_set_fingerprint)
    assert service.respond("s", click, query, impact_reader=lambda: "RECOVERABLE").state == BindingState.CONFIRMED
    assert service.authorize_redo(contract.ambiguity_id, fresh_authorized=True,
                                  edited_result_status="UNEDITED") == BindingState.REDO_AUTHORIZED
    assert service.store.bindings[original_id].state == BindingState.TENTATIVE_APPLIED


def test_bundle_dependencies_and_cycle():
    query = RARQuery("report", (RARCandidate("x", "X", "document"), RARCandidate("y", "Y", "document")))
    contract = build_clarification(query, amb(query), session_id="s", turn_id="t",
                                   wrong_binding_impact="RECOVERABLE").contract
    a, b = ReferenceSlot("a", contract), ReferenceSlot("b", replace(contract, ambiguity_id="other"), ("a",))
    bundle = ClarificationBundle("bundle", "s", "t", (a, b), "SEQUENTIAL")
    validate_bundle(bundle)
    assert tuple(s.ref_key for s in visible_slots(bundle, {})) == ("a",)
    assert tuple(s.ref_key for s in visible_slots(bundle, {"a": BindingState.CONFIRMED})) == ("b",)
    with pytest.raises(ValueError):
        validate_bundle(replace(bundle, slots=(replace(a, depends_on=("b",)), b)))
    with pytest.raises(ValueError):
        rebuild_dependent(bundle, "b", fresh_query=query, session_id="s", turn_id="t",
            wrong_binding_impact="RECOVERABLE", parent_states={}, parent_locator="parent-x",
            candidate_locators={"x": "parent-x", "y": "parent-x"})
    rebuilt = rebuild_dependent(bundle, "b", fresh_query=query, session_id="s", turn_id="t",
        wrong_binding_impact="RECOVERABLE", parent_states={"a": BindingState.CONFIRMED},
        parent_locator="parent-x", candidate_locators={"x": "parent-x", "y": "parent-x"})
    assert rebuilt.slots[1].contract.provenance_required


def test_progress_and_budget_independent():
    guard = ClarificationSafeguards(1, 3)
    assert guard.charge(made_progress=False)
    assert guard.charge(made_progress=True)
    assert not guard.charge(cost=2, made_progress=True)


def test_service_stops_when_budget_exhausted():
    query = RARQuery("the report", pair())
    built = build_clarification(query, amb(query), session_id="s", turn_id="t",
                                  wrong_binding_impact="RECOVERABLE")
    service = BindingService(safeguards=ClarificationSafeguards(2, 0))
    service.register(built, query)
    response = ClarificationResponse(built.contract.ambiguity_id, ResponseKind.ATTRIBUTE,
        option_key="a1", candidate_set_fingerprint=built.contract.candidate_set_fingerprint)
    assert service.respond("s", response, query).reason == "clarification budget exhausted"


def test_response_session_expiry_and_fingerprint_guards():
    query = RARQuery("report", (RARCandidate("x", "X", "document"), RARCandidate("y", "Y", "document")))
    built = build_clarification(query, amb(query), session_id="s", turn_id="t",
        wrong_binding_impact="RECOVERABLE", now=datetime(2026, 1, 1, tzinfo=timezone.utc))
    service = BindingService()
    service.register(built, query)
    contract = built.contract
    response = ClarificationResponse(contract.ambiguity_id, ResponseKind.CANDIDATE,
        candidate_id="x", candidate_set_fingerprint=contract.candidate_set_fingerprint)
    assert service.respond("other", response, query).state == BindingState.REJECTED
    assert service.store.rounds[contract.ambiguity_id].state == BindingState.PENDING
    assert service.respond("s", response, query, now=datetime(2026, 1, 2, tzinfo=timezone.utc)).state == BindingState.EXPIRED
    rebuilt = service.rebuild_rejected(contract.ambiguity_id, query)
    assert rebuilt.next_contract_id != contract.ambiguity_id


def test_contract_rejects_invented_scope_and_invalid_namespace():
    query = RARQuery("report", (RARCandidate("x", "X", "document"), RARCandidate("y", "Y", "document")))
    c = build_clarification(query, amb(query), session_id="s", turn_id="t",
        wrong_binding_impact="RECOVERABLE").contract
    with pytest.raises(ValueError):
        validate_contract(replace(c, scope_candidate_ids=("x", "invented")), query)
    with pytest.raises(ValueError):
        validate_contract(replace(c, candidates=(replace(c.candidates[0], option_key="a1"), c.candidates[1])), query)
