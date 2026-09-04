from uri_core.core.state import SessionState
from uri_core.services.evidence_learning_service import (
    EvidenceLearningService
)


print("=" * 65)
print("URI EVIDENCE LEARNING SERVICE TEST")
print("=" * 65)


# --------------------------------------------------
# CREATE URI SESSION
# --------------------------------------------------

session = SessionState(
    session_id="learning-test"
)


# --------------------------------------------------
# CREATE LEARNING SERVICE
# --------------------------------------------------

learner = EvidenceLearningService()


# --------------------------------------------------
# SAMPLE DOCUMENT 1
# --------------------------------------------------

print("\nDOCUMENT 1: INITIAL EVIDENCE")

document_1 = """
National Institute of Technology Sikkim intends to provide
Group Medical Insurance coverage to students for the
academic year 2026-27.

Approximately 850 students will be covered.

Approximately 560-600 students are currently covered
and require renewal.

Approximately 290 newly admitted students require
fresh coverage.

The quotation has been received from SBI General Insurance.
"""


source_1 = {
    "type": "gmail_attachment",
    "filename": "FINAL RATE QUOTE NIT SIKKIM.pdf",
    "message_id": "test_message_1",
    "thread_id": "test_thread_1"
}


result_1 = learner.learn_from_evidence(
    session=session,
    text=document_1,
    source=source_1
)


print("\nLEARNING RESULT:")

print(
    "Facts found:",
    result_1["facts_found"]
)

for item in result_1["learning_results"]:

    print(
        f"{item['name']} -> "
        f"{item['value']} "
        f"[{item['action']}]"
    )


# --------------------------------------------------
# SAMPLE DOCUMENT 2
# NEW INFORMATION
# --------------------------------------------------

print("\n" + "-" * 65)
print("DOCUMENT 2: NEWER EVIDENCE")
print("-" * 65)


document_2 = """
National Institute of Technology Sikkim confirms that
the Group Medical Insurance provider for academic year
2026-27 has been changed.

The approved insurer is New India Assurance.

Approximately 850 students will continue to be covered.
"""


source_2 = {
    "type": "office_order",
    "filename": "Insurance Approval Order.pdf",
    "message_id": "test_message_2",
    "thread_id": "test_thread_2"
}


result_2 = learner.learn_from_evidence(
    session=session,
    text=document_2,
    source=source_2
)


print("\nLEARNING RESULT:")

print(
    "Facts found:",
    result_2["facts_found"]
)

for item in result_2["learning_results"]:

    print(
        f"{item['name']} -> "
        f"{item['value']} "
        f"[{item['action']}]"
    )


# --------------------------------------------------
# FINAL URI MEMORY
# --------------------------------------------------

print("\n" + "=" * 65)
print("FINAL URI MEMORY")
print("=" * 65)


print("\nCURRENT FACTS:")

for name, fact in session.current_facts.items():

    print(
        f"{name} -> "
        f"{fact.value} "
        f"[{fact.status}]"
    )


print("\nHISTORICAL FACTS:")

for name, fact in session.historical_facts.items():

    print(
        f"{name} -> "
        f"{fact.value} "
        f"[{fact.status}]"
    )


print("\n" + "=" * 65)
print("TEST COMPLETE")
print("=" * 65)