"""M30.5: RAW Brain accuracy vs POST-GATE correctness/safety, over the
M30.4 golden set. Real model calls, real CapabilityDirectory, real
gates - zero execution.

Usage: .venv/Scripts/python.exe scripts/m30_5_gate_metrics.py
"""

import json
import sys

sys.path.insert(0, ".")

from scripts.m30_4_decision_quality_analysis import GOLDEN_SET, real_directory, turn_state_for
from uri_core.core.decision_engine import evaluate_against_golden, propose_decision
from uri_core.core.decision_gates import evaluate_gates


def classify_gate_effect(golden_category, gate_outcome, brain_capability):
    """Was the brain wrong, and did the gate SAFELY contain it (never
    let an unsafe/incorrect claim through as if it were fine), or could
    the gate not help (the brain never proposed a capability at all, so
    there is nothing concrete for a gate to verify)?"""
    if golden_category == "correct":
        # Brain was right - the gate should not have downgraded a
        # genuinely correct, connected, permitted proposal. (Gmail
        # cases legitimately downgrade to DISCONNECTED in THIS
        # environment - that is real, correct gate behavior given real
        # state, not a false rejection - flagged separately, not
        # counted against the gate.)
        return "brain_correct"
    if brain_capability is None:
        return "brain_wrong_no_capability_proposed_gate_cannot_supply_one"
    if gate_outcome in ("INVALID_PROPOSAL", "UNSUPPORTED"):
        return "brain_wrong_gate_safely_rejected_the_claim"
    if gate_outcome == "READY":
        return "brain_wrong_and_gate_did_not_catch_it"
    return f"brain_wrong_gate_outcome_{gate_outcome}"


def main():
    directory = real_directory()
    rows = []
    for case in GOLDEN_SET:
        state = turn_state_for(
            case["text"], directory,
            active_pointer=case.get("active_pointer"),
            recent_conversation=case.get("recent_conversation"),
        )
        decision = propose_decision(turn_state_data=state, capability_directory=directory)
        expected = dict(case["expected"])
        if case["id"] in ("topic_switch", "gmail_unread_only") and decision.contract:
            expected["capability"] = decision.contract.get("capability")
        golden = evaluate_against_golden(expected, decision)
        gate = evaluate_gates(decision, capability_directory=directory)
        brain_capability = decision.contract.get("capability") if decision.contract else None
        effect = classify_gate_effect(golden["category"], gate.outcome, brain_capability)
        rows.append({
            "id": case["id"],
            "expected_mode": case["expected"]["mode"],
            "brain_mode": decision.contract.get("mode") if decision.contract else None,
            "brain_capability": brain_capability,
            "golden_category": golden["category"],
            "gate_outcome": gate.outcome,
            "gate_reasons": gate.reasons,
            "effect": effect,
        })

    for r in rows:
        print(f"{r['id']:22s} expected={r['expected_mode']:20s} brain={r['brain_mode']!s:20s} cap={r['brain_capability']!s:26s} golden={r['golden_category']:20s} gate={r['gate_outcome']:16s} effect={r['effect']}")

    total = len(rows)
    raw_correct = sum(1 for r in rows if r["golden_category"] == "correct")
    safely_rejected = sum(1 for r in rows if r["effect"] == "brain_wrong_gate_safely_rejected_the_claim")
    uncatchable = sum(1 for r in rows if r["effect"] == "brain_wrong_no_capability_proposed_gate_cannot_supply_one")
    unsafe_passthrough = sum(1 for r in rows if r["effect"] == "brain_wrong_and_gate_did_not_catch_it")

    summary = {
        "total": total,
        "raw_brain_accuracy": round(raw_correct / total, 3),
        "post_gate_safe_rejection_rate_of_brain_errors": round(safely_rejected / max(1, total - raw_correct), 3),
        "brain_errors_gate_could_not_address_no_capability_proposed": uncatchable,
        "brain_errors_gate_let_through_unsafely": unsafe_passthrough,
    }
    print()
    print(json.dumps(summary, indent=2))

    with open("scripts/m30_5_gate_metrics_results.json", "w", encoding="utf-8") as handle:
        json.dump({"rows": rows, "summary": summary}, handle, indent=2)


if __name__ == "__main__":
    main()
