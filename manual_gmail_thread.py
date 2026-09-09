from uri_core.services.gmail_service import GmailService


print("=" * 50)
print("URI GMAIL THREAD EVIDENCE TEST")
print("=" * 50)


gmail = GmailService()


print("\nCONNECTING TO GMAIL...\n")

connection = gmail.connect()

print(connection)


if not connection["success"]:

    print(
        "\nUnable to connect to Gmail."
    )

    raise SystemExit


print("\nSEARCHING FOR INSURANCE EVIDENCE...\n")


search_result = gmail.search_evidence(
    [
        '"SBI General Insurance"'
    ]
)


if not search_result["success"]:

    print(
        "Search failed."
    )

    raise SystemExit


results = search_result.get(
    "results",
    []
)


if not results:

    print(
        "No results found."
    )

    raise SystemExit


messages = results[0].get(
    "messages",
    []
)


if not messages:

    print(
        "No messages found."
    )

    raise SystemExit


first_message = messages[0]

thread_id = first_message.get(
    "thread_id"
)


print("SELECTED MESSAGE:")

print(
    first_message.get(
        "subject"
    )
)


print("\nTHREAD ID:")

print(thread_id)


print(
    "\nRECONSTRUCTING THREAD EVIDENCE...\n"
)


thread_result = (
    gmail.get_thread_evidence(
        thread_id
    )
)


print("=" * 50)

print(
    "THREAD EVIDENCE RESULT"
)

print("=" * 50)


print(thread_result)