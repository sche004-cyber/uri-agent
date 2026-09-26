"""Deterministic M33.3 S3 qualification over the frozen S1/S2 public paths."""

from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from uri_core.capabilities.base import Action
from uri_core.capabilities.wrong_binding import (ReferenceBinding, ReferenceBindingStatus,
                                                  evaluate_wrong_binding_gate)
from uri_v1.turn.rar_contracts import (RARBasis, RARCandidate, RAROutcome, RARQuery,
                                        RARResolution)
from uri_v1.turn.rar_clarification_contract import ClarificationResponse, ResponseKind
from uri_v1.reference_clarification.binding import BindingService
from uri_v1.reference_clarification.builder import build_clarification
from uri_v1.reference_clarification.render_contracts import RenderOutput
from uri_v1.reference_clarification.render_validator import validate_render
from uri_v1.reference_clarification.safeguards import ClarificationSafeguards
from uri_v1.reference_clarification.template_renderer import presented_options, render_template

NOW = datetime(2026, 9, 26, 0, 0, tzinfo=timezone.utc)
FIXTURES = ROOT / "fixtures" / "m33_3_arn"


def load_battery() -> tuple[dict, dict]:
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    raw = (FIXTURES / manifest["battery_file"]).read_bytes()
    normalized = raw.replace(b"\r\n", b"\n")
    if hashlib.sha256(normalized).hexdigest() != manifest["battery_lf_sha256"]:
        raise ValueError("S3 fixture hash mismatch")
    if len(normalized) != manifest["battery_bytes"]:
        raise ValueError("S3 fixture byte count mismatch")
    battery = json.loads(normalized)
    cases = battery["cases"]
    if battery["schema_version"] != manifest["schema_version"] or len(cases) != manifest["case_count"]:
        raise ValueError("S3 fixture schema/count mismatch")
    if [x["case_id"] for x in cases] != [f"ARB-{i:03d}" for i in range(1, len(cases) + 1)]:
        raise ValueError("S3 fixture IDs/order changed")
    if sum(x["layer"] == "L1" for x in cases) != manifest["l1_count"] or sum(x["layer"] == "L2" for x in cases) != manifest["l2_count"]:
        raise ValueError("S3 fixture layer counts changed")
    return battery, manifest


def make_query(data: dict) -> RARQuery:
    candidates = tuple(RARCandidate(**c) for c in data["candidates"])
    return RARQuery(data.get("reference", "which one"), candidates)


def make_resolution(query: RARQuery, outcome: str, scope: list[str]) -> RARResolution:
    status = RAROutcome(outcome)
    return RARResolution(query.reference_expression, status,
        candidate_id=scope[0] if status == RAROutcome.RESOLVED else None,
        ambiguous_candidate_ids=tuple(scope) if status == RAROutcome.AMBIGUOUS else (),
        basis=RARBasis.DETERMINISTIC_ANCHOR)


def make_round(query: RARQuery, scope: tuple[str, ...] | None = None, *, impact: str = "RECOVERABLE"):
    ids = scope if scope is not None else query.candidate_ids
    resolution = make_resolution(query, "AMBIGUOUS", list(ids))
    return build_clarification(query, resolution, session_id="s3-session", turn_id="s3-turn",
                               wrong_binding_impact=impact, now=NOW)


def check_build(case: dict) -> dict:
    data, expected = case["input"], case["expected"]
    query = make_query(data)
    try:
        built = build_clarification(query, make_resolution(query, data["resolution"], data["scope"]),
            session_id="s3-session", turn_id="s3-turn", wrong_binding_impact=data["impact"], now=NOW,
            excluded_ids=tuple(data.get("excluded", ())))
    except ValueError as exc:
        observed = {"state": "ERROR", "kind": "ERROR", "scope": [], "shown": [],
                    "overflow": 0, "axis": None, "error": True, "detail": str(exc)}
    else:
        contract = built.contract
        observed = {"state": built.state.value, "kind": contract.kind.value if contract else "DIRECT",
                    "scope": list(contract.scope_candidate_ids) if contract else list(data["scope"]),
                    "shown": [c.candidate_id for c in contract.candidates] if contract else [],
                    "overflow": contract.overflow_count if contract else 0,
                    "axis": contract.attribute_axis if contract else None, "error": False}
        if contract:
            output = render_template(contract)
            validation = validate_render(contract, output)
            options = presented_options(contract, output)
            observed["template_valid"] = validation.valid
            observed["escape_appended"] = bool(options) and options[-1][0] == "escape"
            observed["slot_identity"] = [key for key, _ in output.labels] == [c.option_key for c in contract.candidates] if contract.candidates else [key for key, _ in output.labels] == [a.option_key for a in contract.attribute_options]
            if data.get("excluded"):
                forbidden = [query.get_candidate(cid).title for cid in data["excluded"]]
                observed["exclusion_integrity"] = (tuple(data["excluded"]) == contract.contrast_exclusions and
                    not any(title in output.question + " " + " ".join(label for _, label in output.labels) for title in forbidden))
    comparable = {k: observed.get(k) for k in expected}
    passed = comparable == expected and all(observed.get(k, True) for k in ("template_valid", "escape_appended", "slot_identity", "exclusion_integrity"))
    return {"passed": passed, "expected": expected, "observed": observed}


def check_gate(case: dict) -> dict:
    data, expected = case["input"], case["expected"]
    action = Action("s3", "synthetic", wrong_binding_impact=data["impact"])
    binding = ReferenceBinding("ref", "x", ReferenceBindingStatus(data["binding"]))
    decision = evaluate_wrong_binding_gate(action, (binding,))
    observed = {"outcome": decision.outcome.value, "allowed": decision.allowed,
                "impact_declared": decision.impact_declared}
    return {"passed": all(observed[k] == v for k, v in expected.items()),
            "expected": expected, "observed": observed}


def check_response(case: dict) -> dict:
    scenario, expected = case["input"]["scenario"], case["expected"]
    data = case["input"]
    query = make_query(data)
    scope = tuple(data["scope"])
    guard = ClarificationSafeguards(0, 0) if scenario == "budget_stop" else (ClarificationSafeguards(2, 0) if scenario == "budget_cost_stop" else None)
    service = BindingService(safeguards=guard)
    if scenario in ("change_rebind", "change_post_execution"):
        initial = build_clarification(RARQuery("first", (query.candidates[0],)),
            RARResolution("first", RAROutcome.RESOLVED, candidate_id="x", basis=RARBasis.DETERMINISTIC_ANCHOR),
            session_id="s3-session", turn_id="s3-turn", wrong_binding_impact="RECOVERABLE", now=NOW)
        first = service.register(initial, RARQuery("first", (query.candidates[0],)))
        if scenario == "change_post_execution":
            service.record_execution(first.binding_id, applied_result_exists=True)
        changed = service.open_change(first.binding_id, query,
            make_resolution(query, "AMBIGUOUS", ["x", "y"]), impact_reader=lambda: "RECOVERABLE", turn_id="s3-turn")
        contract = service.store.rounds[changed.next_contract_id].contract
    else:
        built = make_round(query, scope)
        registered = service.register(built, query)
        contract = service.store.rounds[registered.next_contract_id].contract
    if scenario in ("click_replay", "wrong_session", "wrong_round", "stale_candidate", "stale_title", "candidate_removed", "other_candidate_changed", "change_rebind", "change_post_execution"):
        target = "y"
        response = ClarificationResponse(contract.ambiguity_id if scenario != "wrong_round" else "wrong-round",
            ResponseKind.CANDIDATE, candidate_id=target,
            candidate_set_fingerprint=contract.candidate_set_fingerprint)
        current = query
        if scenario == "stale_candidate":
            current = replace(query, candidates=tuple(replace(c, owner="Changed") if c.id == target else c for c in query.candidates))
        elif scenario == "stale_title":
            current = replace(query, candidates=tuple(replace(c, title="Changed.pdf") if c.id == target else c for c in query.candidates))
        elif scenario == "candidate_removed":
            current = replace(query, candidates=tuple(c for c in query.candidates if c.id != target))
        elif scenario == "other_candidate_changed":
            current = replace(query, candidates=tuple(replace(c, owner="Changed") if c.id == "x" else c for c in query.candidates))
        result = service.respond("wrong-session" if scenario == "wrong_session" else "s3-session",
            response, current, wrong_binding_impact="RECOVERABLE", now=NOW)
        if scenario == "click_replay":
            replay = service.respond("s3-session", response, current, wrong_binding_impact="RECOVERABLE", now=NOW)
            extra_ok = result.state.value == "CONFIRMED" and replay.state.value == "REJECTED"
        elif scenario in ("change_rebind", "change_post_execution"):
            extra_ok = service.store.bindings[first.binding_id].superseded_by == result.binding_id
            if scenario == "change_post_execution":
                extra_ok = extra_ok and service.store.bindings[result.binding_id].from_change
        else:
            extra_ok = True
    elif scenario == "attribute_narrow":
        option = next(o for o in contract.attribute_options if o.value == "Alice")
        result = service.respond("s3-session", ClarificationResponse(contract.ambiguity_id, ResponseKind.ATTRIBUTE,
            option_key=option.option_key, candidate_set_fingerprint=contract.candidate_set_fingerprint),
            query, wrong_binding_impact="RECOVERABLE", now=NOW)
        next_contract = service.store.rounds[result.next_contract_id].contract if result.next_contract_id else None
        extra_ok = next_contract is not None and next_contract.kind.value == "CONFIRM_ONE" and next_contract.scope_candidate_ids == ("x",)
    else:
        phrase = data["response_text"]
        result = service.respond("s3-session", ClarificationResponse(contract.ambiguity_id, ResponseKind.FREE_INPUT,
            text=phrase), query, wrong_binding_impact="RECOVERABLE", now=NOW)
        extra_ok = ("hidden" in contract.scope_candidate_ids and
                    "hidden" not in {c.candidate_id for c in contract.candidates}) if scenario == "hidden_free_input" else True
    observed = {"state": result.state.value, "candidate_id": result.candidate_id,
                "has_next_contract": result.next_contract_id is not None, "reason": result.reason,
                "extra_guard_pass": extra_ok}
    return {"passed": observed["state"] == expected["state"] and observed["candidate_id"] == expected["candidate_id"] and extra_ok,
            "expected": expected, "observed": observed}


def check_render(case: dict) -> dict:
    data, expected = case["input"], case["expected"]
    query = make_query({"reference": "which one", "candidates": data["candidates"]})
    contract = make_round(query).contract
    base = render_template(contract)
    keys = [key for key, _ in base.labels]
    labels = [label for _, label in base.labels]
    mutation = data["mutation"]
    question = base.question
    excluded = ()
    if mutation == "not_json": output = "{broken"
    elif mutation == "extra_field": output = {"question": question, "labels": dict(base.labels), "choice": "a"}
    elif mutation == "duplicate_json_key": output = '{"question":"x","question":"y","labels":{}}'
    else:
        if mutation in ("unknown_slot", "extra_slot"):
            keys[0] = "invented" if mutation == "unknown_slot" else keys[0]
            if mutation == "extra_slot": keys.append("invented"); labels.append("Invented")
        elif mutation == "reverse_order": keys.reverse(); labels.reverse()
        elif mutation == "omit_first": keys.pop(0); labels.pop(0)
        elif mutation == "omit_second": keys.pop(); labels.pop()
        elif mutation == "invented_label": labels[0] += " Mars"
        elif mutation == "invented_question": question += " Mars"
        elif mutation == "invented_location": labels[1] += " Venus"
        elif mutation == "swap_labels": labels.reverse()
        elif mutation == "borrow_owner": labels[0] += " Bob"
        elif mutation == "selected_question": question = "I'll use Budget.pdf"
        elif mutation == "assume_question": question = "I assume Budget.pdf"
        elif mutation == "excluded_question": question += " Forbidden"
        elif mutation == "excluded_label": labels[0] += " Forbidden"
        elif mutation == "excluded_second": labels[1] += " Forbidden"
        elif mutation == "duplicate_labels": labels[1] = labels[0]
        elif mutation == "duplicate_labels_case": labels[1] = labels[0].upper()
        else: raise ValueError(f"unhandled mutation {mutation}")
        if mutation.startswith("excluded_"): excluded = ("Forbidden",)
        output = RenderOutput(question, tuple(zip(keys, labels)))
    result = validate_render(contract, output, excluded_facts=excluded)
    observed = {"valid": result.valid, "flags": list(result.flags)}
    return {"passed": expected["valid"] == result.valid and expected["flag"] in result.flags,
            "expected": expected, "observed": observed}


def evaluate_case(case: dict) -> dict:
    try:
        operation = case["operation"]
        result = {"build": check_build, "respond": check_response,
                  "gate": check_gate, "render": check_render}[operation](case)
    except Exception as exc:
        result = {"passed": False, "expected": case["expected"],
                  "observed": {"exception": f"{type(exc).__name__}: {exc}"}}
    return {"case_id": case["case_id"], "level": case["layer"],
            "category": case["category"], "operation": case["operation"], **result}


def run(*, write: bool = False) -> tuple[list[dict], dict]:
    battery, manifest = load_battery()
    rows = [evaluate_case(case) for case in battery["cases"]]
    failed = [r["case_id"] for r in rows if not r["passed"]]
    aggregate = {"schema_version": manifest["schema_version"], "battery_lf_sha256": manifest["battery_lf_sha256"],
                 "total": len(rows), "passed": len(rows)-len(failed), "failed": len(failed),
                 "l1_passed": sum(r["passed"] for r in rows if r["level"] == "L1"),
                 "l2_passed": sum(r["passed"] for r in rows if r["level"] == "L2"),
                 "failed_case_ids": failed, "critical_gates_passed": not failed,
                 "l3_model_metrics": "UNMEASURED", "runtime_ms": "UNMEASURED"}
    if write:
        out = ROOT / "docs" / "plans"
        for name, value in (("M33_3_S3_TELEMETRY.json", {"cases": rows}),
                            ("M33_3_S3_AGGREGATES.json", aggregate)):
            (out / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return rows, aggregate


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    _, summary = run(write=args.write)
    print(json.dumps(summary, sort_keys=True))
    raise SystemExit(0 if summary["critical_gates_passed"] else 1)
