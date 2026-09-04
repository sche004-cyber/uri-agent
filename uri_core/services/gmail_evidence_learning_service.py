from uri_core.services.gmail_service import GmailService
from uri_core.services.pdf_reader import PDFReader
from uri_core.services.evidence_learning_service import (
    EvidenceLearningService
)


class GmailEvidenceLearningService:
    """
    Connects Gmail evidence with URI's learning system.

    Pipeline:

        Gmail Search
            ↓
        Thread Evidence
            ↓
        PDF Attachment
            ↓
        Temporary Download
            ↓
        PDF / OCR Reading
            ↓
        Evidence Learning
            ↓
        URI Memory
    """

    def __init__(self):

        self.gmail = GmailService()

        self.pdf_reader = PDFReader()

        self.learner = EvidenceLearningService()


    def connect(self):
        """
        Connect URI to Gmail in READ_ONLY mode.
        """

        return self.gmail.connect()


    def learn_from_search(
        self,
        session,
        queries,
        max_results=10
    ):
        """
        Search Gmail, process PDF attachments,
        extract evidence, and update URI memory.
        """

        connection = self.connect()

        if not connection.get("success"):

            return {
                "success": False,
                "error": "Could not connect to Gmail"
            }


        # ----------------------------------------------
        # SEARCH GMAIL
        # ----------------------------------------------

        search_result = self.gmail.search_evidence(
            queries=queries,
            max_results=max_results
        )

        if not search_result.get("success"):

            return {
                "success": False,
                "error": "Gmail search failed"
            }


        processed_files = []

        learning_results = []


        # ----------------------------------------------
        # PROCESS SEARCH RESULTS
        # ----------------------------------------------

        for query_result in search_result.get(
            "results",
            []
        ):

            for message in query_result.get(
                "messages",
                []
            ):

                message_id = message.get("id")

                thread_id = message.get("threadId")

                if not message_id or not thread_id:

                    continue


                # --------------------------------------
                # RECONSTRUCT THREAD
                # --------------------------------------

                thread_result = (
                    self.gmail.get_thread_evidence(
                        thread_id=thread_id
                    )
                )

                if not thread_result.get("success"):

                    continue


                # --------------------------------------
                # PROCESS PDF ATTACHMENTS
                # --------------------------------------

                for attachment in thread_result.get(
                    "attachments",
                    []
                ):

                    filename = attachment.get(
                        "filename",
                        ""
                    )

                    mime_type = attachment.get(
                        "mime_type",
                        ""
                    )

                    if mime_type != "application/pdf":

                        continue


                    # ----------------------------------
                    # DOWNLOAD TEMPORARILY
                    # ----------------------------------

                    download_result = (
                        self.gmail.download_attachment(
                            message_id=attachment[
                                "message_id"
                            ],
                            attachment_id=attachment[
                                "attachment_id"
                            ],
                            filename=filename
                        )
                    )

                    if not download_result.get(
                        "success"
                    ):

                        continue


                    file_path = download_result[
                        "file_path"
                    ]


                    try:

                        # ------------------------------
                        # READ PDF / OCR
                        # ------------------------------

                        pdf_result = (
                            self.pdf_reader.read_pdf(
                                file_path
                            )
                        )


                        if not pdf_result.get(
                            "success",
                            True
                        ):

                            continue


                        text = pdf_result.get(
                            "text",
                            ""
                        )


                        if not text.strip():

                            continue


                        # ------------------------------
                        # BUILD SOURCE METADATA
                        # ------------------------------

                        source = {
                            "type": (
                                "gmail_attachment"
                            ),
                            "filename": filename,
                            "message_id": attachment[
                                "message_id"
                            ],
                            "thread_id": thread_id
                        }


                        # ------------------------------
                        # URI LEARNING
                        # ------------------------------

                        learn_result = (
                            self.learner.learn_from_evidence(
                                session=session,
                                text=text,
                                source=source
                            )
                        )


                        processed_files.append(
                            filename
                        )


                        learning_results.append(
                            {
                                "filename": filename,
                                "result": learn_result
                            }
                        )


                    finally:

                        # ------------------------------
                        # DELETE TEMP FILE
                        # ------------------------------

                        self.gmail.delete_temp_file(
                            file_path
                        )


        return {
            "success": True,
            "files_processed": len(
                processed_files
            ),
            "files": processed_files,
            "learning_results": learning_results
        }