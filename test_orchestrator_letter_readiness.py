from uri_core.core.orchestrator import (
    UriOrchestrator
)


def print_section(title):
    print()
    print("=" * 65)
    print(title)
    print("=" * 65)
    print()


uri = UriOrchestrator()

session_id = "orchestrator_letter_test"


print_section(
    "URI ORCHESTRATOR LETTER READINESS TEST"
)


# =========================================================
# STAGE 1: START LETTER TASK
# =========================================================

print_section(
    "STAGE 1: START LETTER TASK"
)

result = uri.process_message(
    session_id=session_id,
    message="Draft a letter"
)

print("Task:", result.get("task"))
print("Task Switched:", result.get("task_switched"))
print("Next Question:", result.get("next_question"))
print("Ready To Draft:", result.get("ready_to_draft"))
print(
    "Missing Fields:",
    result.get("missing_fields")
)


# =========================================================
# STAGE 2: PROVIDE RECIPIENT
# =========================================================

print_section(
    "STAGE 2: PROVIDE RECIPIENT"
)

result = uri.process_message(
    session_id=session_id,
    message="The Registrar, NIT Sikkim"
)

print("Next Question:", result.get("next_question"))
print("Ready To Draft:", result.get("ready_to_draft"))
print(
    "Missing Fields:",
    result.get("missing_fields")
)


# =========================================================
# STAGE 3: PROVIDE SUBJECT
# =========================================================

print_section(
    "STAGE 3: PROVIDE SUBJECT"
)

result = uri.process_message(
    session_id=session_id,
    message="Student Medical Insurance"
)

print("Next Question:", result.get("next_question"))
print("Ready To Draft:", result.get("ready_to_draft"))
print(
    "Missing Fields:",
    result.get("missing_fields")
)


# =========================================================
# STAGE 4: PROVIDE PURPOSE
# =========================================================

print_section(
    "STAGE 4: PROVIDE PURPOSE"
)

result = uri.process_message(
    session_id=session_id,
    message=(
        "To request approval for procurement "
        "of student medical insurance."
    )
)

print("Next Question:", result.get("next_question"))
print("Ready To Draft:", result.get("ready_to_draft"))
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
        "PASS: URI COMPLETED THE FULL "
        "LETTER READINESS WORKFLOW."
    )

else:

    print(
        "FAIL: URI DID NOT REACH "
        "LETTER DRAFT READINESS."
    )


print()
print("=" * 65)
print("TEST COMPLETE")
print("=" * 65)
