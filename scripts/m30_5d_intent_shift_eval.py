"""M30.5D: Temporary context & intent-shift handling evaluation.

Core principle under test: LATEST USER INTENT WINS unless the new turn
plausibly satisfies the pending interaction. Builds on M30.5C's 50-case
set plus the M30.5D spec's own A-H test scenarios (some already present
in M30.5C's boundary cases under different exact wording - kept
separate here, both wordings evaluated, never deduplicated away).

Metrics kept separate per the M30.5D spec: continuation accuracy,
topic-switch accuracy, cancellation accuracy, false-continuation rate,
false-new-intent rate, memory/context preservation, mode accuracy,
capability accuracy (plus candidate recall and invalid rates,
carried over from M30.5C for the full before/after picture).

Zero execution authority - decisions only, nothing runs.
"""

import json
import sys
import time

sys.path.insert(0, ".")

from scripts.m30_5c_boundary_cleanup_eval import EXPANDED_50, _case_group as _base_case_group
from scripts.m30_4_decision_quality_analysis import real_directory, turn_state_for
from uri_core.core.decision_engine import (
    build_decision_request,
    candidate_recall_at_k,
    detect_over_tooling,
    evaluate_against_golden,
    preselect_candidate_ids,
    propose_decision,
)

FILE_CHOICE_PENDING = {
    "kind": "awaiting_selection", "question": "Which file should I use?",
    "missing_field": "file_selection", "reference": "last_goal_attempt_history",
    "originating_goal": "Convert the attached document to a Word file.", "capability_id": None,
    "action": None, "expected_type": "string", "prompt_asked": "Which file should I use?",
    "created_at": None, "state": "awaiting_answer",
}
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

# M30.5D spec's own A-H scenarios, verbatim wording where distinct from
# M30.5C's boundary cases (B and D use different exact phrasing than
# M30.5C's own boundary_new_intent_* cases - kept as separate cases,
# not merged, to test phrasing-independence of the fix).
NEW_CASES_M305D = [
    {"id": "d_continuation_roll_number", "text": "B250012CS",
     "active_pointer": ROLL_NUMBER_PENDING, "boundary_type": "answer",
     "expected": {"mode": "workflow_continuation", "capability": "extract_student_records", "min_actions": 0}},
    {"id": "d_new_intent_gmail_from_roll_pending", "text": "Check my unread emails.",
     "active_pointer": ROLL_NUMBER_PENDING, "boundary_type": "topic_switch",
     "expected": {"mode": "single_action", "capability": "Gmail", "min_actions": 1}},
    {"id": "d_continuation_email_choice", "text": "The SBI one.",
     "active_pointer": EMAIL_CHOICE_PENDING, "boundary_type": "answer",
     "expected": {"mode": "workflow_continuation", "capability": "Gmail", "min_actions": 0}},
    {"id": "d_new_intent_office_note_from_email_pending", "text": "Prepare an office note.",
     "active_pointer": EMAIL_CHOICE_PENDING, "boundary_type": "topic_switch",
     "expected": {"mode": "single_action", "capability": "draft_institutional_note", "min_actions": 1}},
    {"id": "d_continuation_file_choice", "text": "The second PDF.",
     "active_pointer": FILE_CHOICE_PENDING, "boundary_type": "answer",
     "expected": {"mode": "workflow_continuation", "capability": "convert_document", "min_actions": 0}},
    {"id": "d_new_intent_conversation_from_file_pending", "text": "What is today's date?",
     "active_pointer": FILE_CHOICE_PENDING, "boundary_type": "topic_switch_conversation",
     "expected": {"mode": "conversation", "capability": None, "min_actions": 0}},
    {"id": "d_cancellation_roll_number", "text": "never mind",
     "active_pointer": ROLL_NUMBER_PENDING, "boundary_type": "cancellation",
     "expected": {"mode": "conversation", "capability": None, "min_actions": 0}},
]

EXPANDED_57 = EXPANDED_50 + NEW_CASES_M305D


def _case_group(case):
    if case.get("boundary_type") == "topic_switch_conversation":
        return "topic_switch"
    return _base_case_group(case)


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

    # M30.5D Section 1/5/H: memory/context preservation - a STRUCTURAL
    # check, not a model-accuracy metric. When a pending interaction
    # exists, confirm it is still present (as background/candidate
    # context, not deleted) in the actual request sent to the model,
    # regardless of whether this turn used it - "old pending context
    # still exists as background but does not hijack the new turn"
    # requires it to still BE there to inspect, not be stripped away.
    context_preserved = None
    if case.get("active_pointer") is not None:
        preselected = preselect_candidate_ids(state, directory)
        request = build_decision_request(state, preselected_ids=preselected, capability_directory=directory)
        context_preserved = (
            request.get("active_pointer", {}).get("kind") == case["active_pointer"]["kind"]
            and request.get("active_pointer", {}).get("originating_goal") == case["active_pointer"]["originating_goal"]
        )

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
        "context_preserved": context_preserved,
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

    # false-continuation rate: among cases NOT expected to be
    # workflow_continuation, how often the model said it anyway
    # (the M30.5C/M30.5D core failure mode).
    non_continuation = [r for r in results if r["expected_mode"] != "workflow_continuation"]
    false_continuation_rate = (
        round(sum(1 for r in non_continuation if r["actual_mode"] == "workflow_continuation") / len(non_continuation), 3)
        if non_continuation else None
    )
    # false-new-intent rate: among cases expected to BE
    # workflow_continuation, how often the model escaped to a
    # non-continuation mode instead (the opposite failure mode).
    continuation_expected = [r for r in results if r["expected_mode"] == "workflow_continuation"]
    false_new_intent_rate = (
        round(sum(1 for r in continuation_expected if r["actual_mode"] != "workflow_continuation") / len(continuation_expected), 3)
        if continuation_expected else None
    )

    context_applicable = [r for r in results if r["context_preserved"] is not None]
    context_preservation_rate = (
        round(sum(1 for r in context_applicable if r["context_preserved"]) / len(context_applicable), 3)
        if context_applicable else None
    )

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
        "continuation_accuracy": _group_mode_accuracy(results, "workflow_continuation"),
        "workflow_continuation_capability_accuracy": _group_capability_accuracy(results, "workflow_continuation"),
        "topic_switch_accuracy": _group_mode_accuracy(results, "topic_switch"),
        "cancellation_accuracy": _group_mode_accuracy(results, "cancellation"),
        "false_continuation_rate": false_continuation_rate,
        "false_new_intent_rate": false_new_intent_rate,
        "memory_context_preservation_rate": context_preservation_rate,
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
            f"{r['id']:42s} grp={r['group']:16s} expected={r['expected_mode']:20s} "
            f"actual={r['actual_mode']!s:20s} cap={r['actual_capability']!s:26s} "
            f"cat={r['category']:20s} ctx={r['context_preserved']!s:5s}"
        )
    summary = summarize(results)
    print(json.dumps(summary, indent=2))
    return results, summary


def main():
    directory = real_directory()

    pass1, summary1 = _print_pass(
        "PASS 1: 50-case M30.5C set, M30.5D pipeline (direct delta)", EXPANDED_50, directory
    )
    print(f"\nBEFORE (M30.5C): mode_accuracy=0.800, topic_switch_accuracy=0.000, cancellation_accuracy=1.000")
    print(
        f"AFTER  (M30.5D): mode_accuracy={summary1['mode_accuracy']}, "
        f"topic_switch_accuracy={summary1['topic_switch_accuracy']}, "
        f"cancellation_accuracy={summary1['cancellation_accuracy']}\n"
    )

    pass2, summary2 = _print_pass(
        "PASS 2: 57-case set (50 + 7 M30.5D spec A-G scenarios)", EXPANDED_57, directory
    )

    with open("scripts/m30_5d_results.json", "w", encoding="utf-8") as handle:
        json.dump(
            {
                "pass1_50case": pass1, "summary1": summary1,
                "pass2_57case": pass2, "summary2": summary2,
            },
            handle, indent=2,
        )


if __name__ == "__main__":
    main()
