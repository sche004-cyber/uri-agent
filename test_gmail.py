from uri_core.services.gmail_service import GmailService


def main():

    gmail = GmailService()

    print("=" * 50)
    print("URI GMAIL EVIDENCE SEARCH TEST")
    print("=" * 50)

    connection = gmail.connect()

    print()
    print("CONNECTION:")
    print(connection)

    queries = [
        "office order",
        "insurance",
        '"SBI General Insurance"',
    ]

    print()
    print("SEARCHING GMAIL...")

    result = gmail.search_evidence(
        queries
    )

    print()
    print("SEARCH RESULTS:")
    print(result)


if __name__ == "__main__":
    main()