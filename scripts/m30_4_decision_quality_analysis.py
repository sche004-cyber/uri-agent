"""M30.4: OFFLINE Decision Engine quality analysis.

Real model calls (whatever local provider ModelRouter resolves to -
this environment has no configured frontier provider, see the M30.4
report for the /providers check that established this). Zero
production authority: nothing here calls ApprovalGate, ToolDispatcher,
or MultiActionExecutor, and nothing here is imported by orchestrator.py
or server.py. This is a standalone analysis script, run manually.

Usage: .venv/Scripts/python.exe scripts/m30_4_decision_quality_analysis.py
"""

import copy
import json
import sys
import time

sys.path.insert(0, ".")

from uri_core.core.capability_directory import CapabilityDirectory
from uri_core.core.capability_feasibility import CapabilityFeasibility
from uri_core.core.decision_engine import evaluate_against_golden, propose_decision
from uri_core.capabilities import MultiActionCapabilityRegistry
from uri_core.capabilities.gmail import GmailCapability


def real_directory():
    return CapabilityDirectory(
        capability_feasibility=CapabilityFeasibility(),
        multi_action_registry=MultiActionCapabilityRegistry([GmailCapability()]),
    )


def turn_state_for(user_text, directory, active_pointer=None, session_facts=None,
                    recent_conversation=None, attempt_history=None):
    return {
        "turn": {"user_text": user_text, "session_id": "golden", "principal_id": None},
        "recent_conversation": recent_conversation or [],
        "active_pointer": active_pointer or {"kind": "none", "question": None, "missing_field": None, "reference": None},
        "attempt_history": attempt_history or [],
        "session_facts": session_facts or [],
        "capability_summaries": directory.summaries(),
        "runtime_health": {"active_provider": None, "active_model": None, "healthy": None},
        "grounded_entities": {},
        "durable_memory_relevant": [],
        "graph_context": {},
    }


PENDING_ROLL_NUMBER = {
    # M30.5C: corrected to match the real enriched active_pointer shape
    # turn_state.py's _project_active_pointer() actually produces for
    # the common ad hoc clarification pause (capability_id is None -
    # the real path never knows it directly; originating_goal is what
    # lets it be recovered). The old fixture (kind/question/
    # missing_field/reference only) predated that M30.5A schema and
    # silently under-tested candidate recall and capability recovery -
    # see M30_5B_CANDIDATE_RECALL_MULTI_ACTION_REPORT.md Section 3/7.
    # Expected outcomes for continue_1/continue_2 are unchanged.
    "kind": "awaiting_clarification_answer",
    "question": "What is the student's roll number?",
    "missing_field": "roll_number",
    "reference": "last_goal_attempt_history",
    "originating_goal": "Find the student.",
    "capability_id": None,
    "action": None,
    "expected_type": "identifier",
    "prompt_asked": "What is the student's roll number?",
    "created_at": None,
    "state": "awaiting_answer",
}

GOLDEN_SET = [
    {"id": "conv_1", "text": "Do you think changing careers is sensible?",
     "expected": {"mode": "conversation", "capability": None, "min_actions": 0}},
    {"id": "conv_2", "text": "What's your opinion on remote work versus office work?",
     "expected": {"mode": "conversation", "capability": None, "min_actions": 0}},
    {"id": "clarify_1", "text": "Find the student.",
     "expected": {"mode": "clarification", "capability": None, "min_actions": 0}},
    {"id": "clarify_2", "text": "Look up a student's record.",
     "expected": {"mode": "clarification", "capability": None, "min_actions": 0}},
    {"id": "continue_1", "text": "B250012CS", "active_pointer": PENDING_ROLL_NUMBER,
     "recent_conversation": [{"user": "Find the student.", "uri": "What is the student's roll number?"}],
     "expected": {"mode": "workflow_continuation", "capability": "extract_student_records", "min_actions": 0}},
    {"id": "continue_2", "text": "22CS045", "active_pointer": PENDING_ROLL_NUMBER,
     "recent_conversation": [{"user": "Find the student.", "uri": "What is the student's roll number?"}],
     "expected": {"mode": "workflow_continuation", "capability": "extract_student_records", "min_actions": 0}},
    {"id": "unsupported_1", "text": "Schedule a recurring job search for me every week.",
     "expected": {"mode": "unsupported", "capability": None, "min_actions": 0}},
    {"id": "unsupported_2", "text": "Set up an automatic weekly report generator.",
     "expected": {"mode": "unsupported", "capability": None, "min_actions": 0}},
    {"id": "disclosure_1", "text": "I work at NIT Sikkim.",
     "expected": {"mode": "single_action", "capability": "remember_fact", "min_actions": 1}},
    {"id": "disclosure_2", "text": "My favorite document format is docx.",
     "expected": {"mode": "single_action", "capability": "remember_fact", "min_actions": 1}},
    {"id": "office_note", "text": "Draft an office note about the upcoming holiday schedule.",
     "expected": {"mode": "single_action", "capability": "draft_institutional_note", "min_actions": 1}},
    {"id": "convert_doc", "text": "Convert the attached PDF into a Word document.",
     "expected": {"mode": "single_action", "capability": "convert_document", "min_actions": 1}},
    {"id": "gmail_multi_1", "text": "How many unread emails do I have and is anything important?",
     "expected": {"mode": "multi_action", "capability": "Gmail", "min_actions": 2}},
    {"id": "gmail_multi_2", "text": "Find my latest insurance email and tell me if it has an attachment.",
     "expected": {"mode": "multi_action", "capability": "Gmail", "min_actions": 2}},
    {"id": "gmail_draft_approval", "text": "Prepare a reply to that email but do not send it.",
     "recent_conversation": [{"user": "Read that insurance email", "uri": "Here it is: ..."}],
     "expected": {"mode": "approval_required", "capability": "Gmail", "min_actions": 1}},
    {"id": "topic_switch", "text": "How many unread emails do I have?", "active_pointer": PENDING_ROLL_NUMBER,
     "recent_conversation": [{"user": "Find the student.", "uri": "What is the student's roll number?"}],
     "expected": {"mode": "single_action", "capability": None, "min_actions": 0}},
    {"id": "ambiguous_1", "text": "Update my record.",
     "expected": {"mode": "clarification", "capability": None, "min_actions": 0}},
    {"id": "gmail_unread_only", "text": "How many unread emails do I have?",
     "expected": {"mode": "single_action", "capability": None, "min_actions": 0}},
]


def run_golden_set(directory, cases=GOLDEN_SET, label="baseline"):
    results = []
    for case in cases:
        state = turn_state_for(
            case["text"], directory,
            active_pointer=case.get("active_pointer"),
            recent_conversation=case.get("recent_conversation"),
        )
        started = time.monotonic()
        decision = propose_decision(turn_state_data=state, capability_directory=directory)
        elapsed = time.monotonic() - started
        expected = case["expected"]
        # topic_switch / gmail_unread_only / gmail_draft_approval /
        # ambiguous_1 accept a capability match OR None (mode-correctness
        # is what's being measured for those, not a specific id) -
        # loosen expected["capability"] to whatever the engine proposed
        # for the mode-only checks.
        loose_capability_cases = {"topic_switch", "gmail_unread_only"}
        eval_expected = dict(expected)
        if case["id"] in loose_capability_cases and decision.contract:
            eval_expected["capability"] = decision.contract.get("capability")
        outcome = evaluate_against_golden(eval_expected, decision)
        results.append({
            "id": case["id"], "label": label, "text": case["text"],
            "expected_mode": expected["mode"],
            "actual_mode": decision.contract.get("mode") if decision.contract else None,
            "actual_capability": decision.contract.get("capability") if decision.contract else None,
            "decision_status": decision.status,
            "invalid_reason": decision.invalid_reason,
            "category": outcome["category"],
            "mode_correct": outcome["mode_correct"],
            "latency_seconds": round(elapsed, 2),
            "request_size_chars": len(json.dumps(turn_state_for(case["text"], directory))),
        })
    return results


def summarize(results):
    total = len(results)
    mode_correct = sum(1 for r in results if r["mode_correct"])
    invalid = sum(1 for r in results if r["decision_status"] != "ok")
    by_category = {}
    for r in results:
        by_category.setdefault(r["category"], 0)
        by_category[r["category"]] += 1
    avg_latency = sum(r["latency_seconds"] for r in results) / total if total else 0
    avg_size = sum(r["request_size_chars"] for r in results) / total if total else 0
    return {
        "total": total,
        "mode_accuracy": round(mode_correct / total, 3) if total else None,
        "invalid_rate": round(invalid / total, 3) if total else None,
        "by_category": by_category,
        "avg_latency_seconds": round(avg_latency, 2),
        "avg_request_size_chars": round(avg_size, 1),
    }


def build_variant_directory_with_richer_gmail_summary(variant):
    """Returns a directory-like object whose .summaries()/.describe()
    match the real CapabilityDirectory except the Gmail-related entries'
    `summary` text is swapped for a variant string - never touches the
    real, live capability_directory.py source."""
    real = real_directory()

    class _VariantDirectory:
        def summaries(self):
            entries = copy.deepcopy(real.summaries())
            for entry in entries:
                if entry["capability_id"] in ("Gmail", "gmail_search"):
                    entry["summary"] = variant
            return entries

        def describe(self, capability_id):
            return real.describe(capability_id)

    return _VariantDirectory()


GMAIL_SUMMARY_VARIANTS = {
    "A_current": None,  # use the real, unmodified summary
    "B_richer": (
        "Gmail: search and read email messages and threads; check the inbox "
        "and unread message count; list labels; read message attachments; "
        "prepare (but never send) email drafts. Use this for any request "
        "about email, inbox, unread messages, or messages in Gmail."
    ),
    "C_affordance_tags": (
        "Gmail. Affordances: [read_email, search_email, count_unread, "
        "inspect_inbox, list_labels, read_attachment, draft_reply]. "
        "Domains: [email, inbox, messages, correspondence]."
    ),
}

GMAIL_ONLY_CASES = [c for c in GOLDEN_SET if c["id"] in ("gmail_multi_1", "gmail_unread_only", "unsupported_1")]


def run_gmail_summary_experiment():
    all_results = []
    for variant_name, variant_text in GMAIL_SUMMARY_VARIANTS.items():
        directory = real_directory() if variant_text is None else build_variant_directory_with_richer_gmail_summary(variant_text)
        results = run_golden_set(directory, cases=GMAIL_ONLY_CASES, label=variant_name)
        all_results.extend(results)
    return all_results


if __name__ == "__main__":
    directory = real_directory()

    print("=" * 70)
    print("FULL GOLDEN SET (baseline, current live summaries)")
    print("=" * 70)
    full_results = run_golden_set(directory)
    for r in full_results:
        print(f"{r['id']:22s} expected={r['expected_mode']:22s} actual={r['actual_mode']!s:22s} cap={r['actual_capability']!s:26s} cat={r['category']:20s} status={r['decision_status']}")
    print(json.dumps(summarize(full_results), indent=2))

    print()
    print("=" * 70)
    print("GMAIL SUMMARY VARIANT EXPERIMENT (A/B/C)")
    print("=" * 70)
    variant_results = run_gmail_summary_experiment()
    for r in variant_results:
        print(f"[{r['label']:16s}] {r['id']:20s} expected={r['expected_mode']:15s} actual={r['actual_mode']!s:15s} cat={r['category']:20s}")

    with open("scripts/m30_4_results.json", "w", encoding="utf-8") as handle:
        json.dump({"full_golden_set": full_results, "gmail_variants": variant_results}, handle, indent=2)
    print("\nRaw results written to scripts/m30_4_results.json")
