"""M30.5A: Decision-quality remediation evaluation.

Two real, live-model runs, both against the REMEDIATED pipeline
(revised prompt + deterministic preselection + real session-based
pending_interaction + Gmail-overlap-resolved directory + tightened
Unsupported Gate matching):

  1. The exact same 18 cases from M30.4/M30.5 (unchanged) - a direct,
     apples-to-apples before/after delta against the recorded 38.9%
     baseline.
  2. The expanded 30+ case golden set (12 new cases added) - the new
     baseline going forward; no historical "before" exists for the new
     cases themselves.

Zero execution authority - decisions only, nothing runs.
"""

import json
import sys
import time

sys.path.insert(0, ".")

from scripts.m30_4_decision_quality_analysis import GOLDEN_SET as ORIGINAL_18, real_directory
from uri_core.core.capability_directory import CapabilityDirectory
from uri_core.core.decision_engine import (
    detect_over_tooling,
    evaluate_against_golden,
    propose_decision,
)


class _FakeSession:
    """Mirrors test_turn_state.py's own fake - the real Session shape
    for the ordinary ad hoc clarification pause (M30.5A's own bugfix
    target), not the rarer WorkflowExecutor-based one."""

    def __init__(self, last_goal_attempt_history=None):
        self.active_workflow = None
        self.active_workflow_status = None
        self.active_workflow_required_field = None
        self.active_workflow_question = None
        self.last_goal_attempt_history = last_goal_attempt_history
        self.fact_history = {}


PENDING_ROLL_NUMBER_SESSION = _FakeSession(
    last_goal_attempt_history=[
        {
            "goal": "Find the student.",
            "proposal": {"type": "clarification", "question": "What is the student's roll number?"},
            "result": {"status": "awaiting_user_response", "data": None},
        }
    ]
)

# 12 new cases, varied phrasing, covering categories the original 18
# under-represented: disconnected, over-tooling, attachment/file,
# additional Gmail chain steps, office workflow variety, memory
# disclosure variety, legacy/multi-action overlap explicitly.
NEW_CASES = [
    {"id": "over_tooling_1", "text": "Do you think remote work is better than office work?",
     "expected": {"mode": "conversation", "capability": None, "min_actions": 0}},
    {"id": "over_tooling_2", "text": "What's a good way to prepare for a job interview?",
     "expected": {"mode": "conversation", "capability": None, "min_actions": 0}},
    {"id": "office_order", "text": "Issue an office order appointing a new committee chair.",
     "expected": {"mode": "single_action", "capability": "draft_institutional_order", "min_actions": 1}},
    {"id": "memory_pref_1", "text": "Call me Alex from now on.",
     "expected": {"mode": "single_action", "capability": "remember_fact", "min_actions": 1}},
    {"id": "memory_pref_2", "text": "I usually prefer short, direct emails over long formal ones.",
     "expected": {"mode": "single_action", "capability": "remember_fact", "min_actions": 1}},
    {"id": "system_perf", "text": "How much CPU and memory is my computer currently using?",
     "expected": {"mode": "single_action", "capability": "system_performance", "min_actions": 1}},
    {"id": "gmail_labels_only", "text": "List my Gmail labels.",
     "expected": {"mode": "single_action", "capability": "Gmail", "min_actions": 1}},
    {"id": "gmail_attachment_chain", "text": "Check the attachment on that message.",
     "recent_conversation": [{"user": "read that email", "uri": "Here is the message: ..."}],
     "expected": {"mode": "single_action", "capability": "Gmail", "min_actions": 1}},
    {"id": "overlap_legacy_phrasing", "text": "Search my Gmail inbox for anything from the registrar.",
     "expected": {"mode": "single_action", "capability": "Gmail", "min_actions": 1}},
    {"id": "spreadsheet_fetch", "text": "Read the rows from the shared budget spreadsheet.",
     "expected": {"mode": "single_action", "capability": "fetch_drive_spreadsheet", "min_actions": 1}},
    {"id": "cgpa_lookup", "text": "What is the CGPA for roll number 21CS045?",
     "expected": {"mode": "single_action", "capability": "extract_student_records", "min_actions": 1}},
    {"id": "continuation_real_session", "text": "B250012CS",
     "use_real_pending_session": True,
     "expected": {"mode": "workflow_continuation", "capability": "extract_student_records", "min_actions": 0}},
]


def run_case(case, directory):
    if case.get("use_real_pending_session"):
        from uri_core.core.turn_state import assemble_turn_state
        result = assemble_turn_state(
            user_text=case["text"], session_id="golden",
            session=PENDING_ROLL_NUMBER_SESSION, capability_directory=directory,
        )
        state = result.data
    else:
        from scripts.m30_4_decision_quality_analysis import turn_state_for as base_turn_state_for
        state = base_turn_state_for(
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
    return {
        "id": case["id"],
        "expected_mode": expected["mode"],
        "actual_mode": decision.contract.get("mode") if decision.contract else None,
        "actual_capability": decision.contract.get("capability") if decision.contract else None,
        "decision_status": decision.status,
        "category": golden["category"],
        "mode_correct": golden["mode_correct"],
        "over_tooling": over_tooled,
        "latency_seconds": round(elapsed, 2),
        "request_size_chars": len(json.dumps(state)),
    }


def summarize(results):
    total = len(results)
    mode_correct = sum(1 for r in results if r["mode_correct"])
    invalid = sum(1 for r in results if r["decision_status"] != "ok")
    by_category = {}
    for r in results:
        by_category[r["category"]] = by_category.get(r["category"], 0) + 1
    return {
        "total": total,
        "mode_accuracy": round(mode_correct / total, 3) if total else None,
        "invalid_rate": round(invalid / total, 3) if total else None,
        "by_category": by_category,
        "avg_latency_seconds": round(sum(r["latency_seconds"] for r in results) / total, 2) if total else None,
        "over_tooling_flagged": sum(1 for r in results if r["over_tooling"]),
    }


def main():
    directory = real_directory()

    print("=" * 70)
    print("PASS 1: original 18 M30.4/M30.5 cases, REMEDIATED pipeline")
    print("=" * 70)
    pass1 = []
    for case in ORIGINAL_18:
        r = run_case(case, directory)
        pass1.append(r)
        print(f"{r['id']:22s} expected={r['expected_mode']:20s} actual={r['actual_mode']!s:20s} cap={r['actual_capability']!s:26s} cat={r['category']:20s}")
    summary1 = summarize(pass1)
    print(json.dumps(summary1, indent=2))
    print(f"\nBEFORE (M30.4/M30.5 recorded): mode_accuracy=0.389")
    print(f"AFTER  (this run):              mode_accuracy={summary1['mode_accuracy']}")

    print()
    print("=" * 70)
    print("PASS 2: expanded 30-case golden set (18 original + 12 new), REMEDIATED pipeline")
    print("=" * 70)
    pass2 = []
    for case in ORIGINAL_18 + NEW_CASES:
        r = run_case(case, directory)
        pass2.append(r)
        print(f"{r['id']:26s} expected={r['expected_mode']:20s} actual={r['actual_mode']!s:20s} cap={r['actual_capability']!s:26s} cat={r['category']:20s} over_tooling={r['over_tooling']}")
    summary2 = summarize(pass2)
    print(json.dumps(summary2, indent=2))

    with open("scripts/m30_5a_results.json", "w", encoding="utf-8") as handle:
        json.dump(
            {"pass1_original_18_remediated": pass1, "summary1": summary1,
             "pass2_expanded_30": pass2, "summary2": summary2},
            handle, indent=2,
        )


if __name__ == "__main__":
    main()
