import json
from dataclasses import replace

import pytest

from uri_v1.reference_clarification.builder import build_clarification
from uri_v1.reference_clarification.render_contracts import RenderOutput
from uri_v1.reference_clarification.render_validator import validate_render
from uri_v1.reference_clarification.template_renderer import render_template
from uri_v1.turn.rar_clarification_contract import CandidateFact, ClarificationKind
from uri_v1.turn.rar_contracts import RARBasis, RARCandidate, RAROutcome, RARQuery, RARResolution


def contract():
    query = RARQuery("the report", (RARCandidate("a", "Budget", "document", owner="Alice"),
                                    RARCandidate("b", "Forecast", "document", owner="Bob")))
    resolution = RARResolution("the report", RAROutcome.AMBIGUOUS,
        ambiguous_candidate_ids=query.candidate_ids, basis=RARBasis.DETERMINISTIC_ANCHOR)
    return build_clarification(query, resolution, session_id="s", turn_id="t",
                               wrong_binding_impact="RECOVERABLE").contract


def test_template_passes_all_kinds():
    choice = contract()
    one = replace(choice, kind=ClarificationKind.CONFIRM_ONE, candidates=choice.candidates[:1],
                  scope_candidate_ids=choice.scope_candidate_ids[:1], scope_fingerprints=choice.scope_fingerprints[:1])
    free = replace(choice, kind=ClarificationKind.FREE_INPUT_ONLY, candidates=(),
                   scope_candidate_ids=(), scope_fingerprints=())
    for item in (choice, one, free):
        assert validate_render(item, render_template(item)).valid


@pytest.mark.parametrize("output,expected", [
    ('not json', "V-SCHEMA"),
    ('{"question":"Which report?","labels":{},"extra":true}', "V-SCHEMA"),
    (RenderOutput("Which report?", (("s1", "Budget"),)), "V-SLOT-MISSING"),
    (RenderOutput("Which report?", (("s1", "Budget"), ("s2", "Forecast"), ("s3", "Other"))), "V-SLOT-UNKNOWN"),
    (RenderOutput("Which report?", (("a1", "Budget"), ("a2", "Forecast"))), "V-SLOT-UNKNOWN"),
    (RenderOutput("Which report?", (("s1", "Budget"), ("s2", "Budget"))), "V-LABEL-DUP"),
    (RenderOutput("I'll use Budget", (("s1", "Budget"), ("s2", "Forecast"))), "V-SELECTION"),
    (RenderOutput("Which report?", (("s1", "Mars.pdf"), ("s2", "Forecast"))), "V-UNSUPPORTED-FACT"),
    (RenderOutput("Which report?", (("s1", "Bob"), ("s2", "Forecast"))), "V-CROSS-SLOT"),
    (RenderOutput("Q" * 301, (("s1", "Budget"), ("s2", "Forecast"))), "V-LENGTH"),
])
def test_validator_rejects_bad_output(output, expected):
    assert expected in validate_render(contract(), output).flags


def test_excluded_fact_rejected_and_order_flag_only():
    c = contract()
    output = RenderOutput("Which report?", (("s1", "Budget"), ("s2", "Forecast")))
    assert "V-EXCLUSION" in validate_render(c, output, excluded_facts=("Forecast",)).flags
    reversed_output = RenderOutput(output.question, tuple(reversed(output.labels)))
    result = validate_render(c, reversed_output)
    assert result.valid and result.flags == ("V-ORDER",)


def test_near_identical_requires_grounded_locator_and_template_uses_it():
    query = RARQuery("report", (RARCandidate("a", "Report", "document"),
                                    RARCandidate("b", "Report", "document")))
    resolution = RARResolution("report", RAROutcome.AMBIGUOUS,
        ambiguous_candidate_ids=query.candidate_ids, basis=RARBasis.DETERMINISTIC_ANCHOR)
    with pytest.raises(ValueError):
        build_clarification(query, resolution, session_id="s", turn_id="t",
                            wrong_binding_impact="RECOVERABLE")
    built = build_clarification(query, resolution, session_id="s", turn_id="t",
        wrong_binding_impact="RECOVERABLE", extra_facts={
            "a": (CandidateFact("locator", "folder/A", "fixture:a"),),
            "b": (CandidateFact("locator", "folder/B", "fixture:b"),),
        })
    assert validate_render(built.contract, render_template(built.contract)).valid
