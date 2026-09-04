from uri_core.core.orchestrator import UriOrchestrator
from uri_core.services.noting_generator import generate_noting


def print_section(title):
    print()
    print("=" * 65)
    print(title)
    print("=" * 65)
    print()


print_section(
    "URI END-TO-END NOTING GENERATION TEST"
)

uri = UriOrchestrator()

session_id = "noting_generation_test"


# =========================================================
# STAGE 1: LEARN DOCUMENTARY EVIDENCE
# =========================================================

print_section(
    "STAGE 1: LEARNING DOCUMENTARY EVIDENCE"
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
# STAGE 2: START NOTING
# =========================================================

print_section(
    "STAGE 2: STARTING NOTING TASK"
)

result = uri.process_message(
    session_id=session_id,
    message=(
        "Draft a noting regarding student "
        "medical insurance."
    )
)

print("Task:", result.get("task"))
print("Next Question:", result.get("next_question"))


# =========================================================
# STAGE 3: APPROVAL REQUEST
# =========================================================

print_section(
    "STAGE 3: PROVIDING APPROVAL REQUEST"
)

result = uri.process_message(
    session_id=session_id,
    message=(
        "Approval for procurement of Group "
        "Medical Insurance."
    )
)

print("Next Question:", result.get("next_question"))
print("Ready To Draft:", result.get("ready_to_draft"))


# =========================================================
# STAGE 4: JUSTIFICATION
# =========================================================

print_section(
    "STAGE 4: PROVIDING JUSTIFICATION"
)

result = uri.process_message(
    session_id=session_id,
    message=(
        "To provide medical insurance coverage "
        "to eligible students for the academic year."
    )
)

print("Next Question:", result.get("next_question"))
print("Ready To Draft:", result.get("ready_to_draft"))


# =========================================================
# STAGE 5: GENERATE NOTING
# =========================================================

print_section(
    "STAGE 5: GENERATED NOTING"
)

if result.get("ready_to_draft"):

    noting = generate_noting(
        result.get("task_context")
    )

    print(noting)

else:

    print(
        "URI IS NOT READY TO GENERATE "
        "THE NOTING."
    )

    print(
        "Missing Fields:",
        result.get("missing_fields")
    )


# =========================================================
# FINAL RESULT
# =========================================================

print_section(
    "FINAL RESULT"
)

if result.get("ready_to_draft"):

    print(
        "PASS: URI GENERATED A CONTROLLED "
        "ADMINISTRATIVE NOTING."
    )

else:

    print(
        "FAIL: URI DID NOT REACH "
        "DRAFT READINESS."
    )


print()
print("=" * 65)
print("TEST COMPLETE")
print("=" * 65)
