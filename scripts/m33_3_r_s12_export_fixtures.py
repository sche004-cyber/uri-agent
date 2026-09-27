"""Export M33.3-R S12 clarification-card fixtures from real frozen S1 contracts.

Each card is built by the frozen S1 builder over a frozen S5 L3 battery case,
worded by the frozen S1 template, and carries the grounded candidate IDs,
the candidate-set fingerprint, the attribute (a*) options, and the exact
response payloads a click / attribute choice / free input must emit. The
payloads use the S1 `ClarificationResponse` field names. Fixture-only: S12 is
not connected to the production clarification core (that is S13).
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.m33_3_r_s5_qualify import build_contract, load_battery
from uri_v1.reference_clarification.template_renderer import render_template
from uri_v1.turn.rar_clarification_contract import ClarificationKind, ESCAPE_LABEL
from uri_v1.wording.need_class import classify_need

OUT = ROOT / "uri_ui" / "test" / "fixtures" / "m33_3_s12_clarification_cards.json"
SCHEMA_VERSION = "m33.3-r.s12.cards.v1"
# One card per interaction shape; IDs are frozen S5 L3 battery case IDs.
CASES = ("L3B-01", "L3B-08", "L3B-13", "L3B-15", "L3B-22", "L3B-23", "L3B-17", "L3B-07")


def card(case: dict, index: int) -> dict:
    _, contract = build_contract(case)
    out = render_template(contract)
    labels = dict(out.labels)
    ambiguity = f"amb-s12-{index:02d}"  # stable fixture ID replacing the random UUID
    trace = f"{index:02x}".rjust(32, "a")
    options, filters, payloads = [], [], {}
    if contract.kind == ClarificationKind.CHOOSE_ATTRIBUTE:
        for opt in contract.attribute_options:
            filters.append({"option_key": opt.option_key, "axis": opt.axis, "value": opt.value,
                            "label": labels[opt.option_key], "member_count": len(opt.member_candidate_ids)})
            payloads[opt.option_key] = {"ambiguity_id": ambiguity, "response_kind": "ATTRIBUTE",
                                        "option_key": opt.option_key,
                                        "candidate_set_fingerprint": contract.candidate_set_fingerprint}
    else:
        for cand in contract.candidates:
            options.append({"option_key": cand.option_key, "candidate_id": cand.candidate_id,
                            "label": labels[cand.option_key], "rank": cand.rank})
            payloads[cand.option_key] = {"ambiguity_id": ambiguity, "response_kind": "CANDIDATE",
                                         "candidate_id": cand.candidate_id,
                                         "candidate_set_fingerprint": contract.candidate_set_fingerprint}
    return {
        "case_id": case["case_id"], "ambiguity_id": ambiguity, "trace_id": trace, "kind": contract.kind.value,
        "need_class": classify_need(contract), "question": out.question, "options": options,
        "attribute_axis": contract.attribute_axis, "attribute_filters": filters,
        "overflow_count": contract.overflow_count, "escape_label": ESCAPE_LABEL,
        "candidate_set_fingerprint": contract.candidate_set_fingerprint,
        "scope_candidate_ids": list(contract.scope_candidate_ids),
        "expected_payloads": payloads,
        "expected_free_input_payload": {"ambiguity_id": ambiguity, "response_kind": "FREE_INPUT",
                                        "text": "<typed text>"},
    }


def main() -> None:
    battery, manifest = load_battery()
    by_id = {c["case_id"]: c for c in battery["cases"]}
    cards = [card(by_id[cid], i) for i, cid in enumerate(CASES, 1)]
    doc = {"schema_version": SCHEMA_VERSION, "source_battery_sha256": manifest["battery_lf_sha256"],
           "fixture_only": True, "cards": cards}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print({c["case_id"]: (c["kind"], len(c["options"]), len(c["attribute_filters"])) for c in cards})


if __name__ == "__main__":
    main()
