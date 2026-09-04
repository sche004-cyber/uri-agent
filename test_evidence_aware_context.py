from uri_core.core.orchestrator import UriOrchestrator


def print_section(title):
    print()
    print("=" * 65)
    print(title)
    print("=" * 65)
    print()


def print_evidence(evidence):
    if not evidence:
        print("None")
        return

    for name, fact in evidence.items():
        print(
            name,
            "->",
            fact.get("value"),
            "[",
            fact.get("status"),
            "]"
        )


# =========================================================
# CREATE URI
# =========================================================

print_section(
    "URI EVIDENCE-AWARE CONTEXT TEST"
)

uri = UriOrchestrator()

session_id = (
    "evidence_aware_context_test"
)


# =========================================================
# INITIAL MESSAGE
# =========================================================

print("INITIAL USER MESSAGE:")

initial_result = uri.process_message(
    session_id=session_id,
    message=(
        "I need information about the "
        "student medical insurance quotation."
    )
)

print(
    "Task:",
    initial_result.get("task")
)

print()


# =========================================================
# LEARN DOCUMENTARY EVIDENCE
# =========================================================

print("SEARCHING DOCUMENTARY EVIDENCE...")
print()

evidence_result = uri.process_evidence(
    session_id=session_id,
    query="SBI General Insurance"
)

print(
    "Evidence Success:",
    evidence_result.get("success")
)

print(
    "Documents Processed:",
    len(
        evidence_result.get(
            "documents_processed",
            []
        )
    )
)


# =========================================================
# START INSURANCE NOTING TASK
# =========================================================

print_section(
    "STARTING INSURANCE-RELATED NOTING TASK"
)

task_result = uri.process_message(
    session_id=session_id,
    message=(
        "Draft a noting regarding student "
        "medical insurance."
    )
)

print(
    "Task:",
    task_result.get("task")
)

print(
    "Task Switched:",
    task_result.get("task_switched")
)

print(
    "Next Question:",
    task_result.get("next_question")
)


# =========================================================
# DISPLAY RELEVANT EVIDENCE
# =========================================================

print_section(
    "RELEVANT EVIDENCE SELECTED FOR TASK"
)

relevant_evidence = (
    task_result.get(
        "relevant_evidence",
        {}
    )
)

print_evidence(
    relevant_evidence
)


# =========================================================
# VERIFY EXPECTED FACTS
# =========================================================

print_section(
    "VERIFYING EXPECTED EVIDENCE"
)

expected_facts = {
    "institution",
    "academic_year",
    "insurance_type",
    "insurer",
    "approx_total_students",
    "renewal_students",
    "fresh_students",
}

found_facts = set(
    relevant_evidence.keys()
)

missing_facts = (
    expected_facts - found_facts
)


print(
    "Expected Facts:",
    len(expected_facts)
)

print(
    "Relevant Facts Found:",
    len(found_facts)
)

print()


if missing_facts:

    print(
        "MISSING FACTS:"
    )

    for fact_name in sorted(
        missing_facts
    ):

        print(
            "-",
            fact_name
        )

else:

    print(
        "ALL EXPECTED EVIDENCE FACTS FOUND"
    )


# =========================================================
# FINAL RESULT
# =========================================================

print_section(
    "FINAL RESULT"
)

if not missing_facts:

    print(
        "PASS: URI SELECTED THE CORRECT "
        "VERIFIED EVIDENCE FOR THE TASK."
    )

else:

    print(
        "FAIL: SOME EXPECTED EVIDENCE "
        "WAS NOT SELECTED."
    )


print()
print("=" * 65)
print("TEST COMPLETE")
print("=" * 65)
