from uri_core.core.orchestrator import UriOrchestrator


def print_section(title):
    print()
    print("=" * 65)
    print(title)
    print("=" * 65)
    print()


def print_status(result):

    print("Task:", result.get("task"))
    print("Next Question:", result.get("next_question"))
    print("Ready To Draft:", result.get("ready_to_draft"))
    print("Missing Fields:", result.get("missing_fields"))

    print()

    print("Relevant Evidence:")

    evidence = result.get(
        "relevant_evidence",
        {}
    )

    if not evidence:
        print("None")
    else:
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
    "URI ORCHESTRATOR DRAFT READINESS TEST"
)

uri = UriOrchestrator()

session_id = (
    "orchestrator_draft_readiness_test"
)


# =========================================================
# LEARN DOCUMENTARY EVIDENCE
# =========================================================

print_section(
    "STAGE 1: LEARNING INSURANCE EVIDENCE"
)

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
# START NOTING
# =========================================================

print_section(
    "STAGE 2: START NOTING"
)

result = uri.process_message(
    session_id=session_id,
    message=(
        "Draft a noting regarding student "
        "medical insurance."
    )
)

print_status(result)


# =========================================================
# PROVIDE APPROVAL REQUEST
# =========================================================

print_section(
    "STAGE 3: APPROVAL REQUEST PROVIDED"
)

result = uri.process_message(
    session_id=session_id,
    message=(
        "Approval for procurement of Group "
        "Medical Insurance."
    )
)

print_status(result)


# =========================================================
# PROVIDE JUSTIFICATION
# =========================================================

print_section(
    "STAGE 4: JUSTIFICATION PROVIDED"
)

result = uri.process_message(
    session_id=session_id,
    message=(
        "To provide medical insurance coverage "
        "to eligible students for the academic year."
    )
)

print_status(result)


# =========================================================
# FINAL RESULT
# =========================================================

print_section(
    "FINAL RESULT"
)

if result.get("ready_to_draft"):

    print(
        "PASS: URI COMPLETED THE FULL "
        "DRAFT-READINESS WORKFLOW."
    )

else:

    print(
        "FAIL: URI IS NOT YET READY TO DRAFT."
    )

    print(
        "Missing:",
        result.get("missing_fields")
    )


print()
print("=" * 65)
print("TEST COMPLETE")
print("=" * 65)
