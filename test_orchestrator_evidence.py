from uri_core.core.orchestrator import (
UriOrchestrator
)

print("=" * 65)
print("URI END-TO-END EVIDENCE WORKFLOW TEST")
print("=" * 65)

print()

# =========================================================

# CREATE URI

# =========================================================

uri = UriOrchestrator()

session_id = (
"orchestrator_evidence_test"
)

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

print(
"Task:",
message_result.get("task")
)

print(
"Next Question:",
message_result.get("next_question")
)

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

print(
"Success:",
evidence_result.get("success")
)

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

# CHECK MEMORY AFTER EVIDENCE

# =========================================================

session = (
uri.session_manager.get_session(
session_id
)
)

print("=" * 65)
print("MEMORY AFTER EVIDENCE LEARNING")
print("=" * 65)

print()

print("CURRENT FACTS:")

for name, fact in (
    session.current_facts.items()
):

    print(
        name,
        "->",
        fact.value,
        "[",
        fact.status,
        "]"
    )
# =========================================================

# START ADMINISTRATIVE TASK

# =========================================================

print()
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

print()

# =========================================================

# CHECK MEMORY AFTER TASK SWITCH

# =========================================================

session = (
uri.session_manager.get_session(
session_id
)
)

print("=" * 65)
print("MEMORY AFTER TASK SWITCH")
print("=" * 65)

print()

print("CURRENT FACTS:")

if not session.current_facts:

    print("None")

else:

    for name, fact in (
        session.current_facts.items()
    ):

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
print("TEST COMPLETE")
print("=" * 65)
