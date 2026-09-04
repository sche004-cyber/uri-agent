from uri_core.services.gmail_service import GmailService


print("=" * 60)
print("URI GMAIL SEARCH DIAGNOSTIC")
print("=" * 60)

gmail = GmailService()

print()
print("CONNECTING...")
print(gmail.connect())

print()
print("SEARCHING...")

result = gmail.search_evidence(
    queries=["SBI General Insurance"]
)

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

print(
    "Success:",
    result.get("success")
)

print(
    "Results:",
    result.get("results")
)

if result.get("results"):

    for index, group in enumerate(
        result["results"]
    ):

        print()
        print("GROUP", index + 1)
        print("Keys:", group.keys())

        print(
            "Messages found:",
            group.get("messages_found")
        )

        messages = group.get(
            "messages",
            []
        )

        print(
            "Actual messages:",
            len(messages)
        )

        if messages:

            print()
            print(
                "FIRST MESSAGE:"
            )

            print(
                messages[0]
            )


print()
print("=" * 60)
print("TEST COMPLETE")
print("=" * 60)