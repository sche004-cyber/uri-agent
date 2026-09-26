from dataclasses import replace

import pytest

from uri_v1.reference_clarification.authority import AuthorityClass, classify_authority
from uri_v1.reference_clarification.builder import build_clarification
from uri_v1.reference_clarification.binding import BindingService
from uri_v1.reference_clarification.fingerprints import candidate_fingerprint
from uri_v1.reference_clarification.render_contracts import RenderOutput
from uri_v1.reference_clarification.render_validator import validate_render
from uri_v1.reference_clarification.template_renderer import presented_options, render_template
from uri_v1.turn.rar_clarification_contract import (
    BindingState, ClarificationKind, ClarificationResponse, ResponseKind,
    validate_contract,
)
from uri_v1.turn.rar_contracts import (
    RARBasis, RARCandidate, RARDeterministicAnchor, RARDriverRule, RAROutcome,
    RARQuery, RARResolution,
)


def candidates(count=2):
    return tuple(RARCandidate(f"id-{i}", f"Report {i}.pdf", "document", recency_rank=i,
                              owner=f"Owner {i}") for i in range(count))


def ambiguous(query, ids=None):
    return RARResolution(query.reference_expression, RAROutcome.AMBIGUOUS,
                         ambiguous_candidate_ids=ids or query.candidate_ids,
                         basis=RARBasis.DETERMINISTIC_ANCHOR)


def test_scope_cap_and_hidden_candidate_fingerprint():
    query = RARQuery("the report", candidates(7))
    built = build_clarification(query, ambiguous(query), session_id="s", turn_id="t",
                                  wrong_binding_impact="RECOVERABLE")
    contract = built.contract
    assert contract.kind == ClarificationKind.CHOOSE_ONE  # seven owner groups exceed the option cap
    assert len(contract.candidates) == 5 and contract.overflow_count == 2
    query2 = replace(query, candidates=query.candidates[:-1] + (replace(query.candidates[-1], description="changed"),))
    assert candidate_fingerprint(query.candidates[-1]) != candidate_fingerprint(query2.candidates[-1])
    assert len(contract.scope_candidate_ids) == 7
    validate_contract(contract, query)


def test_free_input_hidden_candidate_and_stale_rejection():
    query = RARQuery("the report", candidates(7))
    built = build_clarification(query, ambiguous(query), session_id="s", turn_id="t",
                                  wrong_binding_impact="RECOVERABLE")
    service = BindingService()
    service.register(built, query)
    response = ClarificationResponse(built.contract.ambiguity_id, ResponseKind.FREE_INPUT, text="id-6")
    assert service.respond("s", response, query).candidate_id == "id-6"
    next_built = build_clarification(query, ambiguous(query), session_id="s", turn_id="t",
                                       wrong_binding_impact="RECOVERABLE")
    service.register(next_built, query)
    changed = replace(query, candidates=query.candidates[:-1] + (replace(query.candidates[-1], owner="New owner"),))
    stale = ClarificationResponse(next_built.contract.ambiguity_id, ResponseKind.FREE_INPUT, text="id-6")
    assert service.respond("s", stale, changed).state == BindingState.REJECTED
    assert next_built.contract.candidate_set_fingerprint != build_clarification(
        changed, ambiguous(changed), session_id="s", turn_id="t",
        wrong_binding_impact="RECOVERABLE").contract.candidate_set_fingerprint


def test_free_input_cannot_bind_candidate_outside_rar_returned_scope():
    query = RARQuery("the report", candidates(3))
    returned = ("id-0", "id-1")
    built = build_clarification(query, ambiguous(query, returned), session_id="s", turn_id="t",
                                  wrong_binding_impact="RECOVERABLE")
    service = BindingService()
    service.register(built, query)
    response = ClarificationResponse(built.contract.ambiguity_id, ResponseKind.FREE_INPUT,
                                     text="id-2")
    result = service.respond("s", response, query, wrong_binding_impact="RECOVERABLE")
    assert result.candidate_id is None
    assert "id-2" not in {record.candidate_id for record in service.store.bindings.values()}


def test_click_requires_active_ui_and_rejects_level_zero_override():
    query = RARQuery("the report", candidates(), deterministic_anchor=RARDeterministicAnchor(exact_id="id-0"))
    built = build_clarification(query, ambiguous(query), session_id="s", turn_id="t",
                                  wrong_binding_impact="RECOVERABLE")
    service = BindingService()
    service.register(built, query)
    response = ClarificationResponse(built.contract.ambiguity_id, ResponseKind.CANDIDATE,
                                     candidate_id="id-1", candidate_set_fingerprint=built.contract.candidate_set_fingerprint)
    assert service.respond("s", response, query).state == BindingState.REJECTED
    assert not service.store.bindings


def test_click_and_free_input_authority():
    query = RARQuery("the report", candidates())
    built = build_clarification(query, ambiguous(query), session_id="s", turn_id="t",
                                  wrong_binding_impact="RECOVERABLE")
    service = BindingService()
    service.register(built, query)
    click = ClarificationResponse(built.contract.ambiguity_id, ResponseKind.CANDIDATE,
                                  candidate_id="id-1", candidate_set_fingerprint=built.contract.candidate_set_fingerprint)
    assert service.respond("s", click, query).state == BindingState.CONFIRMED
    assert service.respond("s", click, query).state == BindingState.REJECTED
    built2 = build_clarification(query, ambiguous(query), session_id="s", turn_id="t",
                                   wrong_binding_impact="RECOVERABLE")
    service.register(built2, query)
    text = ClarificationResponse(built2.contract.ambiguity_id, ResponseKind.FREE_INPUT, text="id-1")
    assert service.respond("s", text, query).state == BindingState.CONFIRMED


def test_free_input_heuristic_and_unknown_routes():
    query = RARQuery("the report", candidates())
    service = BindingService()
    for impact, expected in (("RECOVERABLE", BindingState.TENTATIVE),
                             ("CONSEQUENTIAL", BindingState.PENDING)):
        built = build_clarification(query, ambiguous(query), session_id="s", turn_id="t",
                                      wrong_binding_impact=impact)
        service.register(built, query)
        response = ClarificationResponse(built.contract.ambiguity_id, ResponseKind.FREE_INPUT,
                                         text="Report 1")
        result = service.respond("s", response, query, wrong_binding_impact=impact)
        assert result.state == expected
        if result.next_contract_id:
            assert service.store.rounds[result.next_contract_id].contract.kind == ClarificationKind.CONFIRM_ONE
    built = build_clarification(query, ambiguous(query), session_id="s", turn_id="t",
                                  wrong_binding_impact="RECOVERABLE")
    service.register(built, query)
    response = ClarificationResponse(built.contract.ambiguity_id, ResponseKind.FREE_INPUT,
                                     text="completely different")
    result = service.respond("s", response, query, wrong_binding_impact="RECOVERABLE")
    assert result.next_contract_id
    assert service.store.rounds[result.next_contract_id].contract.kind == ClarificationKind.FREE_INPUT_ONLY


@pytest.mark.parametrize("rule,expected", [
    (RARDriverRule.EXACT_ID, AuthorityClass.CERTAINTY),
    (RARDriverRule.EXACT_ALIAS, AuthorityClass.CERTAINTY),
    (RARDriverRule.ACTIVE_UI, AuthorityClass.HEURISTIC),
    (RARDriverRule.CURRENT_ATTACHMENT, AuthorityClass.HEURISTIC),
    (RARDriverRule.EXACT_TITLE, AuthorityClass.HEURISTIC),
    (RARDriverRule.ACTIVE_POINTER, AuthorityClass.HEURISTIC),
    (RARDriverRule.TYPE_FILTER, AuthorityClass.HEURISTIC),
    (RARDriverRule.CONTRAST_FILTER, AuthorityClass.HEURISTIC),
    (RARDriverRule.TEMPORAL_RELATION, AuthorityClass.HEURISTIC),
    (RARDriverRule.REVISION_RELATION, AuthorityClass.HEURISTIC),
    (RARDriverRule.TERM_DISCRIMINATION, AuthorityClass.HEURISTIC),
    (RARDriverRule.NONE, AuthorityClass.HEURISTIC),
])
def test_d5_authority(rule, expected):
    query = RARQuery("the report", candidates())
    resolution = RARResolution("the report", RAROutcome.RESOLVED, candidate_id="id-0",
                               basis=RARBasis.DETERMINISTIC_ANCHOR, rule_used=rule)
    assert classify_authority(resolution, query) == expected


def test_model_selection_never_certainty_even_with_exact_id():
    query = RARQuery("id-0", candidates())
    result = RARResolution("id-0", RAROutcome.RESOLVED, candidate_id="id-0",
        basis=RARBasis.MODEL_SELECTION, rule_used=RARDriverRule.EXACT_ID)
    assert classify_authority(result, query) == AuthorityClass.HEURISTIC
    assert build_clarification(query, result, session_id="s", turn_id="t",
        wrong_binding_impact="RECOVERABLE").contract.kind == ClarificationKind.CONFIRM_ONE


def test_d5_provenance_and_title_stem():
    c = RARCandidate("a", "Budget.pdf", "document", is_attachment=True)
    query = RARQuery("Budget", (c,))
    title = RARResolution("Budget", RAROutcome.RESOLVED, candidate_id="a",
        basis=RARBasis.DETERMINISTIC_ANCHOR, rule_used=RARDriverRule.EXACT_TITLE)
    assert classify_authority(title, query) == AuthorityClass.HEURISTIC
    full = replace(query, reference_expression="Budget.pdf")
    assert classify_authority(replace(title, reference_expression="Budget.pdf"), full) == AuthorityClass.CERTAINTY
    attachment = replace(title, rule_used=RARDriverRule.CURRENT_ATTACHMENT)
    assert classify_authority(attachment, query) == AuthorityClass.HEURISTIC
    anchored = replace(query, deterministic_anchor=RARDeterministicAnchor(current_attachment_id="a"))
    assert classify_authority(attachment, anchored) == AuthorityClass.CERTAINTY
    ui = replace(title, rule_used=RARDriverRule.ACTIVE_UI)
    assert classify_authority(ui, replace(query,
        deterministic_anchor=RARDeterministicAnchor(selected_ui_id="a"))) == AuthorityClass.CERTAINTY
    heuristic = build_clarification(query, title, session_id="s", turn_id="t",
                                    wrong_binding_impact=None)
    assert heuristic.contract.kind == ClarificationKind.CONFIRM_ONE


def test_renderer_validates_and_rejects_identity_swap():
    query = RARQuery("the report", candidates())
    contract = build_clarification(query, ambiguous(query), session_id="s", turn_id="t",
                                   wrong_binding_impact="RECOVERABLE").contract
    output = render_template(contract)
    assert validate_render(contract, output).valid
    assert presented_options(contract, output)[-1][0] == "escape"
    swapped = RenderOutput(output.question, (("s1", output.labels[1][1]), ("s2", output.labels[0][1])))
    assert not validate_render(contract, swapped).valid
