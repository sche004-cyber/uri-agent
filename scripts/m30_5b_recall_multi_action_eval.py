"""M30.5B: Candidate recall, multi_action, and continuation-identity
evaluation.

Three real, live-model runs, all against the M30.5B pipeline (foundational-
capability preselection + originating-goal preselection union +
capability_action_affordances + rewritten mode-framing/continuation-
capability prompt):

  1. The exact same 18 cases from M30.4/M30.5/M30.5A - direct delta
     against the recorded 38.9% (M30.4/M30.5) -> 61.1% (M30.5A) chain.
  2. The 30-case M30.5A golden set (18 + 12) - direct delta against the
     recorded 63.3% M30.5A baseline.
  3. The expanded 40-case golden set (30 + 10 new M30.5B cases) - the
     new baseline going forward, covering: varied memory-disclosure
     phrasing, continuation-vs-topic-switch/cancellation, and
     continuation capability-identity generalized to email-choice and
     file-choice (not just roll-number).

Every case also gets CANDIDATE_RECALL@3 and CANDIDATE_RECALL@5 -
whether the expected capability was even preselected - kept as a
metric wholly separate from whether the model's final mode/capability
answer was correct.

Zero execution authority - decisions only, nothing runs.
"""

import json
import sys
import time

sys.path.insert(0, ".")

from scripts.m30_4_decision_quality_analysis import GOLDEN_SET as ORIGINAL_18, real_directory
from scripts.m30_4_decision_quality_analysis import turn_state_for
from scripts.m30_5a_remediation_eval import NEW_CASES as M305A_NEW_12
from scripts.m30_5a_remediation_eval import PENDING_ROLL_NUMBER_SESSION
from uri_core.core.decision_engine import (
    candidate_recall_at_k,
    detect_over_tooling,
    evaluate_against_golden,
    propose_decision,
)
from uri_core.core.turn_state import assemble_turn_state

ORIGINAL_30 = ORIGINAL_18 + M305A_NEW_12

# 10 new M30.5B cases: varied memory-disclosure phrasing (never reusing
# a phrase already in ORIGINAL_30), continuation-vs-topic-switch and
# cancellation, and continuation capability-identity generalized beyond
# the roll-number case to an email-choice and a file-choice scenario.
NEW_CASES_M305B = [
    {"id": "memory_name", "text": "My name is Chetan.",
     "expected": {"mode": "single_action", "capability": "remember_fact", "min_actions": 1}},
    {"id": "memory_style_pref", "text": "I prefer concise replies.",
     "expected": {"mode": "single_action", "capability": "remember_fact", "min_actions": 1}},
    {"id": "memory_trekking", "text": "My favourite trekking area is the Kanchenjunga base camp trail.",
     "expected": {"mode": "single_action", "capability": "remember_fact", "min_actions": 1}},
    {"id": "recall_name", "text": "Do you remember my name?",
     "expected": {"mode": "single_action", "capability": "recall_memory", "min_actions": 1}},
    {"id": "recall_general", "text": "What do you already know about me?",
     "expected": {"mode": "single_action", "capability": "recall_memory", "min_actions": 1}},
    {
        "id": "continuation_topic_switch_new_intent",
        "text": "Actually, check my unread email.",
        "active_pointer": {
            "kind": "awaiting_clarification_answer", "question": "What is the student's roll number?",
            "missing_field": "roll_number", "reference": "last_goal_attempt_history",
            "originating_goal": "Find the student.", "capability_id": None,
            "action": None, "expected_type": "identifier", "prompt_asked": "What is the student's roll number?",
            "created_at": None, "state": "awaiting_answer",
        },
        "expected": {"mode": "single_action", "capability": "Gmail", "min_actions": 1},
    },
    {
        "id": "pending_email_choice_cancellation",
        "text": "Never mind.",
        "active_pointer": {
            "kind": "awaiting_selection", "question": "Which email do you mean - the one from the registrar or the one from the bank?",
            "missing_field": "email_selection", "reference": "last_goal_attempt_history",
            "originating_goal": "Check my unread email and read the important one.", "capability_id": None,
            "action": None, "expected_type": "string", "prompt_asked": "Which email do you mean?",
            "created_at": None, "state": "awaiting_answer",
        },
        "expected": {"mode": "conversation", "capability": None, "min_actions": 0},
    },
    {
        "id": "pending_file_choice_unrelated_topic_switch",
        "text": "Order me a pizza for dinner.",
        "active_pointer": {
            "kind": "awaiting_selection", "question": "Which file should I use - the draft or the final version?",
            "missing_field": "file_selection", "reference": "last_goal_attempt_history",
            "originating_goal": "Convert the attached document to a Word file.", "capability_id": None,
            "action": None, "expected_type": "string", "prompt_asked": "Which file should I use?",
            "created_at": None, "state": "awaiting_answer",
        },
        "expected": {"mode": "unsupported", "capability": None, "min_actions": 0},
    },
    {
        "id": "continuation_email_choice_capability_recovery",
        "text": "The one from the registrar.",
        "active_pointer": {
            "kind": "awaiting_selection", "question": "Which email do you mean - the one from the registrar or the one from the bank?",
            "missing_field": "email_selection", "reference": "last_goal_attempt_history",
            "originating_goal": "Check my unread email and read the important one.", "capability_id": None,
            "action": None, "expected_type": "string", "prompt_asked": "Which email do you mean?",
            "created_at": None, "state": "awaiting_answer",
        },
        "expected": {"mode": "workflow_continuation", "capability": "Gmail", "min_actions": 0},
    },
    {
        "id": "continuation_file_choice_capability_recovery",
        "text": "Use the final version.",
        "active_pointer": {
            "kind": "awaiting_selection", "question": "Which file should I use - the draft or the final version?",
            "missing_field": "file_selection", "reference": "last_goal_attempt_history",
            "originating_goal": "Convert the attached document to a Word file.", "capability_id": None,
            "action": None, "expected_type": "string", "prompt_asked": "Which file should I use?",
            "created_at": None, "state": "awaiting_answer",
        },
        "expected": {"mode": "workflow_continuation", "capability": "convert_document", "min_actions": 0},
    },
]

EXPANDED_40 = ORIGINAL_30 + NEW_CASES_M305B


def _case_group(case):
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
    if case.get("use_real_pending_session"):
        result = assemble_turn_state(
            user_text=case["text"], session_id="golden",
            session=PENDING_ROLL_NUMBER_SESSION, capability_directory=directory,
        )
        state = result.data
    else:
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
        "category": golden["category"],
        "mode_correct": golden["mode_correct"],
        "capability_correct": golden["capability_correct"],
        "over_tooling": over_tooled,
        "recall_at_3": recall_3,
        "recall_at_5": recall_5,
        "latency_seconds": round(elapsed, 2),
        "request_size_chars": len(json.dumps(state)),
    }


def _rate(results, predicate):
    applicable = [r for r in results if predicate(r) is not None]
    if not applicable:
        return None
    return round(sum(1 for r in applicable if predicate(r)) / len(applicable), 3)


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

    recall_3_applicable = [r for r in results if r["recall_at_3"] is not None]
    recall_5_applicable = [r for r in results if r["recall_at_5"] is not None]

    return {
        "total": total,
        # 1-2: candidate recall, measured independently of the model's answer
        "candidate_recall_at_3": (
            round(sum(1 for r in recall_3_applicable if r["recall_at_3"]) / len(recall_3_applicable), 3)
            if recall_3_applicable else None
        ),
        "candidate_recall_at_5": (
            round(sum(1 for r in recall_5_applicable if r["recall_at_5"]) / len(recall_5_applicable), 3)
            if recall_5_applicable else None
        ),
        # 3-4: overall mode/capability accuracy
        "mode_accuracy": round(sum(1 for r in results if r["mode_correct"]) / total, 3) if total else None,
        "capability_accuracy": round(sum(1 for r in results if r["capability_correct"]) / total, 3) if total else None,
        # 5: multi_action accuracy (mode correctness within that group only)
        "multi_action_accuracy": _group_mode_accuracy(results, "multi_action"),
        # 6-7: workflow_continuation, mode vs capability kept distinct
        "workflow_continuation_mode_accuracy": _group_mode_accuracy(results, "workflow_continuation"),
        "workflow_continuation_capability_accuracy": _group_capability_accuracy(results, "workflow_continuation"),
        # 8: memory-disclosure accuracy (mode correctness within that group)
        "memory_disclosure_accuracy": _group_mode_accuracy(results, "memory_disclosure"),
        # 9: unsupported accuracy
        "unsupported_accuracy": _group_mode_accuracy(results, "unsupported"),
        # 10: conversation/no-tool accuracy
        "conversation_accuracy": _group_mode_accuracy(results, "conversation"),
        # 11: invalid-contract rate
        "invalid_contract_rate": round(invalid / total, 3) if total else None,
        # 12: prompt size
        "avg_request_size_chars": round(sum(r["request_size_chars"] for r in results) / total, 1) if total else None,
        # 13: latency
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
            f"{r['id']:42s} grp={r['group']:20s} expected={r['expected_mode']:20s} "
            f"actual={r['actual_mode']!s:20s} cap={r['actual_capability']!s:26s} "
            f"cat={r['category']:20s} r3={r['recall_at_3']!s:5s} r5={r['recall_at_5']!s:5s}"
        )
    summary = summarize(results)
    print(json.dumps(summary, indent=2))
    return results, summary


def main():
    directory = real_directory()

    pass1, summary1 = _print_pass(
        "PASS 1: original 18 M30.4/M30.5/M30.5A cases, M30.5B pipeline", ORIGINAL_18, directory
    )
    print(f"\nBEFORE (M30.4/M30.5): mode_accuracy=0.389")
    print(f"BEFORE (M30.5A):      mode_accuracy=0.611")
    print(f"AFTER  (M30.5B, this run): mode_accuracy={summary1['mode_accuracy']}\n")

    pass2, summary2 = _print_pass(
        "PASS 2: 30-case M30.5A golden set, M30.5B pipeline", ORIGINAL_30, directory
    )
    print(f"\nBEFORE (M30.5A): mode_accuracy=0.633")
    print(f"AFTER  (M30.5B, this run): mode_accuracy={summary2['mode_accuracy']}\n")

    pass3, summary3 = _print_pass(
        "PASS 3: expanded 40-case golden set (30 + 10 new M30.5B cases), M30.5B pipeline",
        EXPANDED_40, directory,
    )

    with open("scripts/m30_5b_results.json", "w", encoding="utf-8") as handle:
        json.dump(
            {
                "pass1_original_18": pass1, "summary1": summary1,
                "pass2_original_30": pass2, "summary2": summary2,
                "pass3_expanded_40": pass3, "summary3": summary3,
            },
            handle, indent=2,
        )


if __name__ == "__main__":
    main()
