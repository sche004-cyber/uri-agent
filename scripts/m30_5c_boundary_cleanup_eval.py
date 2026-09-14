"""M30.5C: Pending-interaction boundary (topic-switch/cancellation),
multi_action phrasing robustness, hallucinated-capability, and
golden-set cleanup evaluation.

Builds on M30.5B's 40-case set (with the stale PENDING_ROLL_NUMBER
fixture now corrected in-place in m30_4_decision_quality_analysis.py -
see that file's own comment) plus new M30.5C cases:

  - the 5 boundary examples from the M30.5C spec verbatim (answer,
    cancel, new_intent x2, answer-by-selection).
  - 5 new multi_action phrasings beyond the two previously-passing
    mandated sentences.

Metrics kept separate per the M30.5C spec: candidate Recall@3/@5, mode
accuracy, capability accuracy, workflow_continuation mode/capability
accuracy, topic-switch accuracy, cancellation accuracy, multi_action
accuracy, memory-disclosure accuracy, conversation accuracy,
unsupported accuracy, invalid-capability rate, invalid-contract rate,
prompt size, latency.

Zero execution authority - decisions only, nothing runs.
"""

import json
import sys
import time

sys.path.insert(0, ".")

from scripts.m30_5b_recall_multi_action_eval import EXPANDED_40
from scripts.m30_4_decision_quality_analysis import real_directory, turn_state_for
from uri_core.core.decision_engine import (
    candidate_recall_at_k,
    detect_over_tooling,
    evaluate_against_golden,
    propose_decision,
)

ROLL_NUMBER_PENDING = {
    "kind": "awaiting_clarification_answer", "question": "What is the student's roll number?",
    "missing_field": "roll_number", "reference": "last_goal_attempt_history",
    "originating_goal": "Find the student.", "capability_id": None,
    "action": None, "expected_type": "identifier", "prompt_asked": "What is the student's roll number?",
    "created_at": None, "state": "awaiting_answer",
}
EMAIL_CHOICE_PENDING = {
    "kind": "awaiting_selection", "question": "Which email do you mean?",
    "missing_field": "email_selection", "reference": "last_goal_attempt_history",
    "originating_goal": "Check my unread email and read the important one.", "capability_id": None,
    "action": None, "expected_type": "string", "prompt_asked": "Which email do you mean?",
    "created_at": None, "state": "awaiting_answer",
}

# The M30.5C spec's own 5 boundary examples, verbatim wording.
NEW_CASES_M305C_BOUNDARY = [
    {"id": "boundary_answer_roll_number", "text": "B250012CS",
     "active_pointer": ROLL_NUMBER_PENDING, "boundary_type": "answer",
     "expected": {"mode": "workflow_continuation", "capability": "extract_student_records", "min_actions": 0}},
    {"id": "boundary_cancel_roll_number", "text": "Never mind.",
     "active_pointer": ROLL_NUMBER_PENDING, "boundary_type": "cancellation",
     "expected": {"mode": "conversation", "capability": None, "min_actions": 0}},
    {"id": "boundary_new_intent_roll_number", "text": "Actually, check my unread email.",
     "active_pointer": ROLL_NUMBER_PENDING, "boundary_type": "topic_switch",
     "expected": {"mode": "single_action", "capability": "Gmail", "min_actions": 1}},
    {"id": "boundary_answer_email_choice", "text": "The SBI one.",
     "active_pointer": EMAIL_CHOICE_PENDING, "boundary_type": "answer",
     "expected": {"mode": "workflow_continuation", "capability": "Gmail", "min_actions": 0}},
    {"id": "boundary_new_intent_email_choice", "text": "Forget it, prepare an office note.",
     "active_pointer": EMAIL_CHOICE_PENDING, "boundary_type": "topic_switch",
     "expected": {"mode": "single_action", "capability": "draft_institutional_note", "min_actions": 1}},
]

# 5 new multi_action phrasings beyond the two previously-passing
# mandated sentences (M30.5B Section 5) - deliberately varied, never
# reusing exact prior wording.
NEW_CASES_M305C_MULTI_ACTION = [
    {"id": "multi_phrasing_1", "text": "How many unread emails are there, and which matter?",
     "expected": {"mode": "multi_action", "capability": "Gmail", "min_actions": 2}},
    {"id": "multi_phrasing_2", "text": "Check unread mail and tell me what is important.",
     "expected": {"mode": "multi_action", "capability": "Gmail", "min_actions": 2}},
    {"id": "multi_phrasing_3", "text": "Find the latest insurance message, read it, and inspect the attachment.",
     "expected": {"mode": "multi_action", "capability": "Gmail", "min_actions": 3}},
    {"id": "multi_phrasing_4", "text": "Open the newest SBI email and check its PDF.",
     "expected": {"mode": "multi_action", "capability": "Gmail", "min_actions": 2}},
    {"id": "multi_phrasing_5", "text": "Look at unread messages, then summarise the important ones.",
     "expected": {"mode": "multi_action", "capability": "Gmail", "min_actions": 2}},
]

EXPANDED_50 = EXPANDED_40 + NEW_CASES_M305C_BOUNDARY + NEW_CASES_M305C_MULTI_ACTION


def _case_group(case):
    boundary_type = case.get("boundary_type")
    if boundary_type == "cancellation":
        return "cancellation"
    if boundary_type == "topic_switch":
        return "topic_switch"
    expected = case["expected"]
    mode = expected.get("mode")
    capability = expected.get("capability")
    if mode == "multi_action":
        return "multi_action"
    if mode == "workflow_continuation":
        return "workflow_continuation"
    if capability in ("remember_fact", "recall_memory"):
        return "memory_disclosure"
    if mode == "unsupported":
        return "unsupported"
    if mode == "conversation":
        return "conversation"
    return "other"


def run_case(case, directory):
    state = turn_state_for(
        case["text"], directory,
        active_pointer=case.get("active_pointer"),
        recent_conversation=case.get("recent_conversation"),
    )

    started = time.monotonic()
    decision = propose_decision(
        turn_state_data=state, capability_directory=directory, preselect=True,
    )
    elapsed = time.monotonic() - started

    expected = dict(case["expected"])
    golden = evaluate_against_golden(expected, decision)
    over_tooled = detect_over_tooling(decision, state, directory)
    recall_3 = candidate_recall_at_k(state, directory, expected.get("capability"), k=3)
    recall_5 = candidate_recall_at_k(state, directory, expected.get("capability"), k=5)
    return {
        "id": case["id"],
        "group": _case_group(case),
        "expected_mode": expected["mode"],
        "expected_capability": expected.get("capability"),
        "actual_mode": decision.contract.get("mode") if decision.contract else None,
        "actual_capability": decision.contract.get("capability") if decision.contract else None,
        "decision_status": decision.status,
        "invalid_reason": decision.invalid_reason,
        "category": golden["category"],
        "mode_correct": golden["mode_correct"],
        "capability_correct": golden["capability_correct"],
        "over_tooling": over_tooled,
        "recall_at_3": recall_3,
        "recall_at_5": recall_5,
        "latency_seconds": round(elapsed, 2),
        "request_size_chars": len(json.dumps(state)),
    }


def _group_mode_accuracy(results, group):
    subset = [r for r in results if r["group"] == group]
    if not subset:
        return None
    return round(sum(1 for r in subset if r["mode_correct"]) / len(subset), 3)


def _group_capability_accuracy(results, group):
    subset = [r for r in results if r["group"] == group]
    if not subset:
        return None
    return round(sum(1 for r in subset if r["capability_correct"]) / len(subset), 3)


def summarize(results):
    total = len(results)
    invalid = sum(1 for r in results if r["decision_status"] != "ok")
    invalid_capability = sum(1 for r in results if r["invalid_reason"] == "unknown_capability")

    recall_3_applicable = [r for r in results if r["recall_at_3"] is not None]
    recall_5_applicable = [r for r in results if r["recall_at_5"] is not None]

    return {
        "total": total,
        "candidate_recall_at_3": (
            round(sum(1 for r in recall_3_applicable if r["recall_at_3"]) / len(recall_3_applicable), 3)
            if recall_3_applicable else None
        ),
        "candidate_recall_at_5": (
            round(sum(1 for r in recall_5_applicable if r["recall_at_5"]) / len(recall_5_applicable), 3)
            if recall_5_applicable else None
        ),
        "mode_accuracy": round(sum(1 for r in results if r["mode_correct"]) / total, 3) if total else None,
        "capability_accuracy": round(sum(1 for r in results if r["capability_correct"]) / total, 3) if total else None,
        "workflow_continuation_mode_accuracy": _group_mode_accuracy(results, "workflow_continuation"),
        "workflow_continuation_capability_accuracy": _group_capability_accuracy(results, "workflow_continuation"),
        "topic_switch_accuracy": _group_mode_accuracy(results, "topic_switch"),
        "cancellation_accuracy": _group_mode_accuracy(results, "cancellation"),
        "multi_action_accuracy": _group_mode_accuracy(results, "multi_action"),
        "memory_disclosure_accuracy": _group_mode_accuracy(results, "memory_disclosure"),
        "conversation_accuracy": _group_mode_accuracy(results, "conversation"),
        "unsupported_accuracy": _group_mode_accuracy(results, "unsupported"),
        "invalid_capability_rate": round(invalid_capability / total, 3) if total else None,
        "invalid_contract_rate": round(invalid / total, 3) if total else None,
        "avg_request_size_chars": round(sum(r["request_size_chars"] for r in results) / total, 1) if total else None,
        "avg_latency_seconds": round(sum(r["latency_seconds"] for r in results) / total, 2) if total else None,
        "by_category": {c: sum(1 for r in results if r["category"] == c) for c in {r["category"] for r in results}},
        "over_tooling_flagged": sum(1 for r in results if r["over_tooling"]),
    }


def _print_pass(label, cases, directory):
    print("=" * 70)
    print(label)
    print("=" * 70)
    results = []
    for case in cases:
        r = run_case(case, directory)
        results.append(r)
        print(
            f"{r['id']:38s} grp={r['group']:16s} expected={r['expected_mode']:20s} "
            f"actual={r['actual_mode']!s:20s} cap={r['actual_capability']!s:26s} "
            f"cat={r['category']:20s} r3={r['recall_at_3']!s:5s} r5={r['recall_at_5']!s:5s}"
        )
    summary = summarize(results)
    print(json.dumps(summary, indent=2))
    return results, summary


def main():
    directory = real_directory()

    pass1, summary1 = _print_pass(
        "PASS 1: 40-case M30.5B set, CORRECTED fixture, M30.5C prompt", EXPANDED_40, directory
    )
    print(f"\nBEFORE (M30.5B, stale fixture): mode_accuracy=0.800")
    print(f"AFTER  (M30.5C, corrected fixture): mode_accuracy={summary1['mode_accuracy']}\n")

    pass2, summary2 = _print_pass(
        "PASS 2: 50-case set (40 + 5 boundary + 5 multi_action phrasing), M30.5C pipeline",
        EXPANDED_50, directory,
    )

    with open("scripts/m30_5c_results.json", "w", encoding="utf-8") as handle:
        json.dump(
            {
                "pass1_corrected_40": pass1, "summary1": summary1,
                "pass2_expanded_50": pass2, "summary2": summary2,
            },
            handle, indent=2,
        )


if __name__ == "__main__":
    main()
