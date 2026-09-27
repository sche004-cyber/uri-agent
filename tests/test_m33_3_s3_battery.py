"""M33.3 S3 deterministic fixture integrity and public-path qualification."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.m33_3_s3_qualify import FIXTURES, evaluate_case, load_battery, run
from uri_core.capabilities.base import Action
from uri_core.capabilities.wrong_binding import evaluate_wrong_binding_gate, GateOutcome
from uri_v1.turn.rar_contracts import RARCandidate, RARQuery, RARResolution, RAROutcome
from uri_v1.reference_clarification.builder import build_clarification


BATTERY, MANIFEST = load_battery()


def test_fixture_manifest_is_canonical_and_portable():
    raw = (FIXTURES / "battery.json").read_bytes()
    assert b"\r" not in raw
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    assert raw == (json.dumps(BATTERY, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()
    assert hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest() == MANIFEST["battery_lf_sha256"]
    assert hashlib.sha256(raw.replace(b"\n", b"\r\n").replace(b"\r\n", b"\n")).hexdigest() == MANIFEST["battery_lf_sha256"]
    assert MANIFEST["privacy"] == "synthetic-only"


@pytest.mark.parametrize("case", BATTERY["cases"], ids=lambda c: c["case_id"])
def test_frozen_case_against_actual_s1_s2_interfaces(case):
    result = evaluate_case(case)
    assert result["passed"], result


def test_critical_gates_cannot_be_hidden_by_aggregate():
    rows, summary = run()
    assert len(rows) == 82
    assert summary["l1_passed"] == MANIFEST["l1_count"] == 60
    assert summary["l2_passed"] == MANIFEST["l2_count"] == 22
    assert summary["failed_case_ids"] == []
    assert summary["critical_gates_passed"] is True
    assert summary["l3_model_metrics"] == "UNMEASURED"


def test_adversarial_candidate_invention_fails_before_clarification():
    query = RARQuery("missing", (RARCandidate("real", "Real", "document"),))
    invented = RARResolution("missing", RAROutcome.RESOLVED, candidate_id="invented")
    with pytest.raises(ValueError, match="Candidate invention"):
        build_clarification(query, invented, session_id="s", turn_id="t", wrong_binding_impact="NONE")


def test_adversarial_malformed_binding_fails_closed():
    decision = evaluate_wrong_binding_gate(Action("a", "synthetic"), ({"ref_key": "x", "candidate_id": "y", "status": "CONFIRMED"},))
    assert decision.allowed is False
    assert decision.outcome == GateOutcome.INVALID_REFERENCE_BINDING


def test_plan_a_rows_18_19_minimums_and_frozen_v1_prefix():
    # S3 re-audit correction F1: Plan A section 10 rows 18 (hallucinated slot or ID)
    # and 19 (invented extra candidate) each require at least two L2 cases.
    by_mutation = {c["input"].get("mutation"): c for c in BATTERY["cases"] if c["layer"] == "L2"}
    hallucinated = [by_mutation[m] for m in ("unknown_slot", "candidate_id_as_slot")]
    invented = [by_mutation[m] for m in ("extra_slot", "renderer_escape_slot")]
    for case in hallucinated + invented:
        result = evaluate_case(case)
        assert result["passed"], result
        assert result["observed"]["valid"] is False
        assert "V-SLOT-UNKNOWN" in result["observed"]["flags"]
    assert "V-EXTRA-OPTION" in evaluate_case(by_mutation["renderer_escape_slot"])["observed"]["flags"]
    assert [c["case_id"] for c in BATTERY["cases"][80:]] == ["ARB-081", "ARB-082"]


def test_wrong_expected_flag_fails_new_cases():
    for case in BATTERY["cases"][80:]:
        broken = json.loads(json.dumps(case))
        broken["expected"]["flag"] = "V-ORDER"
        assert evaluate_case(broken)["passed"] is False
