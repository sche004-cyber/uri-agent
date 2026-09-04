from uri_core.core.state import SessionManager

from uri_core.services.evidence_processor import (
    EvidenceProcessor
)


print("=" * 65)
print("URI END-TO-END EVIDENCE PIPELINE TEST")
print("=" * 65)

print()


# =========================================================
# CREATE SESSION
# =========================================================

session_manager = SessionManager()

session = session_manager.get_session(
    "evidence_pipeline_test"
)


# =========================================================
# CREATE EVIDENCE PROCESSOR
# =========================================================

processor = EvidenceProcessor()


# =========================================================
# PROCESS GMAIL EVIDENCE
# =========================================================

print("SEARCHING AND PROCESSING GMAIL EVIDENCE...")
print()


result = processor.process_gmail_query(
    query="SBI General Insurance",
    session=session
)


# =========================================================
# PIPELINE RESULT
# =========================================================

print("=" * 65)
print("PIPELINE RESULT")
print("=" * 65)

print()

print(
    "Success:",
    result.get("success")
)
print("Error:", result.get("error"))
print("Message:", result.get("message"))
print("Details:", result)
print()

print(
    "Documents processed:",
    len(
        result.get(
            "documents_processed",
            []
        )
    )
)

print()


for document in result.get(
    "documents_processed",
    []
):

    print("DOCUMENT:")

    print(
        "Filename:",
        document.get("filename")
    )

    print(
        "Thread:",
        document.get("thread_id")
    )

    print(
        "Reading method:",
        document.get("method")
    )

    print(
        "Pages:",
        document.get("pages")
    )

    print()


# =========================================================
# LEARNING RESULTS
# =========================================================

print("=" * 65)
print("LEARNING RESULTS")
print("=" * 65)

print()


for learning in result.get(
    "learning_results",
    []
):

    print(
        "Facts found:",
        learning.get(
            "facts_found",
            0
        )
    )

    print()


    for fact in learning.get(
        "learning_results",
        []
    ):

        print(
            fact.get("name"),
            "->",
            fact.get("value"),
            "[",
            fact.get("action"),
            "]"
        )

    print()


# =========================================================
# URI MEMORY
# =========================================================

print("=" * 65)
print("URI MEMORY AFTER LEARNING")
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


print()

print("HISTORICAL FACTS:")


if not session.historical_facts:

    print("None")


else:

    for name, fact in (
        session.historical_facts.items()
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
# ERRORS
# =========================================================

if result.get("errors"):

    print()

    print("=" * 65)
    print("PIPELINE ERRORS")
    print("=" * 65)

    print()

    for error in result[
        "errors"
    ]:

        print("-", error)


print()

print("=" * 65)
print("URI EVIDENCE PIPELINE TEST COMPLETE")
print("=" * 65)