from uri_core.services.gmail_service import GmailService
from uri_core.services.pdf_reader import PDFReader


print("=" * 60)
print("URI PDF OCR EVIDENCE READER TEST")
print("=" * 60)


# --------------------------------------------------
# CONNECT TO GMAIL
# --------------------------------------------------

gmail = GmailService()

print("\nCONNECTING TO GMAIL...\n")

connection = gmail.connect()

print(connection)

if not connection.get("success"):

    print("\nGMAIL CONNECTION FAILED.")

    raise SystemExit


# --------------------------------------------------
# SEARCH FOR INSURANCE EVIDENCE
# --------------------------------------------------

print("\nSEARCHING FOR INSURANCE EVIDENCE...\n")

search_result = gmail.search_evidence(
    queries=[
        '"SBI General Insurance"',
        "insurance"
    ]
)

if not search_result.get("success"):

    print("SEARCH FAILED")

    raise SystemExit


# --------------------------------------------------
# FIND THE BEST MESSAGE / THREAD
# --------------------------------------------------

selected_message = None


print("\nSEARCH RESULTS FOUND:\n")


# First preference:
# A message that already has a PDF attachment.

for result in search_result.get("results", []):

    for message in result.get("messages", []):

        attachments = message.get(
            "attachments",
            []
        )

        for attachment in attachments:

            filename = attachment.get(
                "filename",
                ""
            )

            if filename.lower().endswith(".pdf"):

                selected_message = message

                break

        if selected_message:

            break

    if selected_message:

        break


# Second preference:
# Any message containing SBI General Insurance
# in subject or snippet.

if not selected_message:

    for result in search_result.get("results", []):

        for message in result.get("messages", []):

            subject = message.get(
                "subject",
                ""
            )

            snippet = message.get(
                "snippet",
                ""
            )

            combined_text = (
                subject + " " + snippet
            ).upper()

            if (
                "SBI GENERAL INSURANCE"
                in combined_text
            ):

                selected_message = message

                break

        if selected_message:

            break


# Final fallback:
# Use any available message.

if not selected_message:

    for result in search_result.get("results", []):

        messages = result.get(
            "messages",
            []
        )

        if messages:

            selected_message = messages[0]

            break


if not selected_message:

    print("NO MESSAGE FOUND.")

    raise SystemExit


thread_id = selected_message.get(
    "thread_id"
)


print("=" * 60)
print("SELECTED MESSAGE")
print("=" * 60)

print(
    "Subject:",
    selected_message.get(
        "subject",
        ""
    )
)

print(
    "\nFrom:",
    selected_message.get(
        "from",
        ""
    )
)

print(
    "\nDate:",
    selected_message.get(
        "date",
        ""
    )
)

print(
    "\nThread ID:",
    thread_id
)


if not thread_id:

    print("\nTHREAD ID NOT FOUND.")

    raise SystemExit


# --------------------------------------------------
# RECONSTRUCT COMPLETE THREAD
# --------------------------------------------------

print("\nRECONSTRUCTING THREAD...\n")

thread_result = gmail.get_thread_evidence(
    thread_id
)


if not thread_result.get("success"):

    print("THREAD SEARCH FAILED:")

    print(thread_result)

    raise SystemExit


print("=" * 60)
print("THREAD SUMMARY")
print("=" * 60)

print(
    "Messages found:",
    thread_result.get(
        "messages_found",
        0
    )
)

print(
    "Attachments found:",
    thread_result.get(
        "attachments_found",
        0
    )
)


# --------------------------------------------------
# FIND THE BEST PDF ATTACHMENT
# --------------------------------------------------

selected_attachment = None


attachments = thread_result.get(
    "attachments",
    []
)


# Priority 1:
# FINAL RATE QUOTE PDF

for attachment in attachments:

    filename = attachment.get(
        "filename",
        ""
    )

    if (
        filename.lower().endswith(".pdf")
        and "RATE QUOTE" in filename.upper()
    ):

        selected_attachment = attachment

        break


# Priority 2:
# Any PDF containing SBI

if not selected_attachment:

    for attachment in attachments:

        filename = attachment.get(
            "filename",
            ""
        )

        if (
            filename.lower().endswith(".pdf")
            and "SBI" in filename.upper()
        ):

            selected_attachment = attachment

            break


# Priority 3:
# Any PDF

if not selected_attachment:

    for attachment in attachments:

        filename = attachment.get(
            "filename",
            ""
        )

        if filename.lower().endswith(".pdf"):

            selected_attachment = attachment

            break


if not selected_attachment:

    print("\nNO PDF ATTACHMENT FOUND IN THIS THREAD.")

    print("\nTHREAD MESSAGES:")

    for message in thread_result.get(
        "messages",
        []
    ):

        print(
            "-",
            message.get(
                "subject",
                ""
            )
        )

    raise SystemExit


# --------------------------------------------------
# DISPLAY SELECTED PDF
# --------------------------------------------------

print("\n" + "=" * 60)
print("SELECTED PDF")
print("=" * 60)

print(
    "Filename:",
    selected_attachment.get(
        "filename",
        ""
    )
)

print(
    "Message ID:",
    selected_attachment.get(
        "message_id",
        ""
    )
)

print(
    "MIME Type:",
    selected_attachment.get(
        "mime_type",
        ""
    )
)


# --------------------------------------------------
# DOWNLOAD TEMPORARILY
# --------------------------------------------------

print("\nDOWNLOADING TEMPORARILY...\n")


download_result = gmail.download_attachment(

    message_id=selected_attachment[
        "message_id"
    ],

    attachment_id=selected_attachment[
        "attachment_id"
    ],

    filename=selected_attachment[
        "filename"
    ]
)


print(download_result)


if not download_result.get("success"):

    print("\nDOWNLOAD FAILED")

    raise SystemExit


file_path = download_result.get(
    "file_path"
)


if not file_path:

    print("\nTEMPORARY FILE PATH NOT FOUND.")

    raise SystemExit


# --------------------------------------------------
# READ PDF
# --------------------------------------------------

print("\nREADING PDF WITH URI OCR...\n")


reader = PDFReader()


pdf_result = reader.read_pdf(
    file_path
)


# --------------------------------------------------
# DISPLAY RESULT
# --------------------------------------------------

print("\n" + "=" * 60)
print("PDF READING RESULT")
print("=" * 60)


if pdf_result.get("success"):

    print(
        "Filename:",
        pdf_result.get(
            "filename",
            ""
        )
    )

    print(
        "Pages found:",
        pdf_result.get(
            "pages_found",
            0
        )
    )

    print(
        "Method used:",
        pdf_result.get(
            "method",
            ""
        )
    )

    print("\nEXTRACTED TEXT PREVIEW\n")

    preview = pdf_result.get(
        "text",
        ""
    )[:5000]

    print(preview)


    if not preview.strip():

        print(
            "\nWARNING: NO TEXT WAS EXTRACTED."
        )

        print(
            "The PDF may require OCR."
        )


else:

    print(
        "PDF READING FAILED:"
    )

    print(pdf_result)


# --------------------------------------------------
# DELETE TEMPORARY PDF
# --------------------------------------------------

print("\nDELETING TEMPORARY PDF...\n")


delete_result = gmail.delete_temporary_file(
    file_path
)


print(delete_result)


print("\n" + "=" * 60)
print("URI PDF OCR TEST COMPLETE")
print("=" * 60)