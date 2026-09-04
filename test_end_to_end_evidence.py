from uri_core.core.orchestrator import UriOrchestrator


def print_facts(title, facts):
    print("=" * 65)
    print(title)
    print("=" * 65)
    print()

    if not facts:
        print("None")
    else:
        for name, fact in facts.items():
            print(
                name,
                "->",
                fact.value,
                "[",
                fact.status,
                "]"
            )

    print()


print("=" * 65)
print("URI END-TO-END EVIDENCE WORKFLOW TEST")
print("=" * 65)
print()


# =========================================================
# CREATE URI
# =========================================================

uri = UriOrchestrator()

session_id = "orchestrator_evidence_test"


# =========================================================
# INITIAL MESSAGE
# =========================================================

print("INITIAL USER MESSAGE:")

message_result = uri.process_message(
    session_id=session_id,
    message=(
        "I need information about the "
        "student medical insurance quotation."
    )
)

print("Task:", message_result.get("task"))
print("Next Question:", message_result.get("next_question"))
print()


# =========================================================
# RUN EVIDENCE PIPELINE
# =========================================================

print("SEARCHING DOCUMENTARY EVIDENCE...")
print()

evidence_result = uri.process_evidence(
    session_id=session_id,
    query="SBI General Insurance"
)

print("=" * 65)
print("EVIDENCE RESULT")
print("=" * 65)
print()

print("Success:", evidence_result.get("success"))

print(
    "Documents processed:",
    len(
        evidence_result.get(
            "documents_processed",
            []
        )
    )
)

print()


# =========================================================
# MEMORY AFTER EVIDENCE
# =========================================================

session = uri.session_manager.get_session(
    session_id
)

print_facts(
    "TASK FACTS AFTER EVIDENCE LEARNING",
    session.current_facts
)

print_facts(
    "EVIDENCE FACTS AFTER EVIDENCE LEARNING",
    session.evidence_facts
)


# =========================================================
# START NOTING TASK
# =========================================================

print("=" * 65)
print("STARTING NOTING TASK")
print("=" * 65)
print()

task_result = uri.process_message(
    session_id=session_id,
    message=(
        "Draft a noting regarding student "
        "medical insurance."
    )
)

print("Task:", task_result.get("task"))
print("Task Switched:", task_result.get("task_switched"))
print("Next Question:", task_result.get("next_question"))
print()


# =========================================================
# MEMORY AFTER TASK SWITCH
# =========================================================

session = uri.session_manager.get_session(
    session_id
)

print_facts(
    "TASK FACTS AFTER TASK SWITCH",
    session.current_facts
)

print_facts(
    "EVIDENCE FACTS AFTER TASK SWITCH",
    session.evidence_facts
)


# =========================================================
# RESULT
# =========================================================

print("=" * 65)

if session.evidence_facts:
    print("RESULT: EVIDENCE SURVIVED TASK SWITCH")
else:
    print("RESULT: EVIDENCE WAS LOST")

print("=" * 65)
print()
print("TEST COMPLETE")
print("=" * 65)
