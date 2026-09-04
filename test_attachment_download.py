from pathlib import Path

from uri_core.services.gmail_service import GmailService


def main():

    print("=" * 50)
    print("URI ATTACHMENT DOWNLOAD TEST")
    print("=" * 50)

    gmail = GmailService()

    print("\nCONNECTING TO GMAIL...\n")

    connection = gmail.connect()

    print(connection)

    if not connection.get("success"):

        print("\nUnable to connect to Gmail.")

        return


    print("\nSEARCHING FOR INSURANCE EVIDENCE...\n")

    search_result = gmail.search_evidence(
        [
            '"SBI General Insurance"'
        ]
    )

    if not search_result.get("success"):

        print("\nSearch failed.")

        print(search_result)

        return


    selected_attachment = None


    for result in search_result.get(
        "results",
        []
    ):

        for message in result.get(
            "messages",
            []
        ):

            attachments = message.get(
                "attachments",
                []
            )

            if attachments:

                attachment = attachments[0]

                selected_attachment = {
                    "message_id": message[
                        "message_id"
                    ],

                    "filename": attachment[
                        "filename"
                    ],

                    "attachment_id": attachment[
                        "attachment_id"
                    ]
                }

                break

        if selected_attachment:

            break


    if not selected_attachment:

        print(
            "\nNo attachment was found "
            "for the test."
        )

        return


    print("=" * 50)
    print("SELECTED ATTACHMENT")
    print("=" * 50)

    print(
        "Filename:",
        selected_attachment["filename"]
    )

    print(
        "Message ID:",
        selected_attachment["message_id"]
    )


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


    print("DOWNLOAD RESULT:")

    print(download_result)


    if not download_result.get("success"):

        print("\nDownload failed.")

        return


    file_path = Path(
        download_result["file_path"]
    )


    print("\nVERIFYING TEMPORARY FILE...\n")

    print(
        "File exists:",
        file_path.exists()
    )

    if file_path.exists():

        print(
            "File size:",
            file_path.stat().st_size,
            "bytes"
        )


    print("\nDELETING TEMPORARY FILE...\n")

    delete_result = gmail.delete_temporary_file(
        str(file_path)
    )

    print("DELETE RESULT:")

    print(delete_result)


    print("\nVERIFYING CLEANUP...\n")

    print(
        "File still exists:",
        file_path.exists()
    )


    project_root = Path(__file__).resolve().parent

    temp_folder = (
        project_root /
        "temp_evidence"
    )


    if temp_folder.exists():

        remaining_files = list(
            temp_folder.iterdir()
        )

        print(
            "\nFILES REMAINING IN temp_evidence:"
        )

        if remaining_files:

            for file in remaining_files:

                print(
                    "-",
                    file.name
                )

        else:

            print(
                "None"
            )

    else:

        print(
            "\ntemp_evidence folder "
            "does not exist."
        )


    print("\n" + "=" * 50)
    print("TEST COMPLETE")
    print("=" * 50)


if __name__ == "__main__":

    main()