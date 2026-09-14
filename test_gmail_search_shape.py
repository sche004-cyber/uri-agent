"""Manual diagnostic, not an automated test: makes a REAL Gmail API
call against whatever account's credentials.json/token.json this
machine has, and prints real message subjects/senders/attachment IDs.

2026-09-12: this file's name matches `unittest discover`'s test_*.py
pattern, and its body used to run at module-import time - every
automated test run silently made a real Gmail search and dumped real
mailbox content (subjects, senders, attachment IDs) to test output.
Gating it behind __main__ so `python -m unittest discover` merely
imports (never executes) it; run it directly with
`python test_gmail_search_shape.py` for manual diagnosis only.
"""

from uri_core.services.gmail_service import GmailService


def main() -> None:
    print("=" * 60)
    print("URI GMAIL SEARCH DIAGNOSTIC")
    print("=" * 60)

    gmail = GmailService()

    print()
    print("CONNECTING...")
    print(gmail.connect())

    print()
    print("SEARCHING...")

    result = gmail.search_evidence(queries=["SBI General Insurance"])

    print()
    print("=" * 60)
    print("RAW SEARCH RESULT")
    print("=" * 60)

    print(result)

    print()
    print("=" * 60)
    print("STRUCTURE CHECK")
    print("=" * 60)

    print()
    print("Success:", result.get("success"))
    print("Results:", result.get("results"))

    if result.get("results"):
        for index, group in enumerate(result["results"]):
            print()
            print("GROUP", index + 1)
            print("Keys:", group.keys())
            print("Messages found:", group.get("messages_found"))

            messages = group.get("messages", [])
            print("Actual messages:", len(messages))

            if messages:
                print()
                print("FIRST MESSAGE:")
                print(messages[0])

    print()
    print("=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()