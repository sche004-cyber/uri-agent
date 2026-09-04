from uri_core.services.gmail_service import GmailService
from uri_core.services.pdf_reader import PDFReader
from uri_core.services.evidence_learning_service import (
    EvidenceLearningService
)


class EvidenceProcessor:
    """
    URI end-to-end documentary evidence processor.

    Pipeline:

    Gmail Search
        ↓
    Thread Reconstruction
        ↓
    PDF Attachment Detection
        ↓
    Temporary Download
        ↓
    OCR / PDF Reading
        ↓
    Fact Extraction
        ↓
    Fact Learning
        ↓
    Temporary File Cleanup
    """

    def __init__(self):

        self.gmail = GmailService()

        self.pdf_reader = PDFReader()

        self.learning_service = (
            EvidenceLearningService()
        )


    def process_gmail_query(
        self,
        query,
        session
    ) -> dict:

        documents_processed = []

        learning_results = []

        errors = []

        processed_threads = set()


        # =====================================================
        # CONNECT TO GMAIL
        # =====================================================

        connection = self.gmail.connect()

        if not connection.get("success"):

            return {
                "success": False,
                "error": "Gmail connection failed.",
                "message": connection.get(
                    "reason"
                ),
                "documents_processed": [],
                "learning_results": [],
                "errors": [
                    connection.get("reason")
                ]
            }


        # =====================================================
        # SEARCH GMAIL
        # =====================================================

        search_result = (
            self.gmail.search_evidence(
                queries=[query]
            )
        )


        if not search_result.get("success"):

            return {
                "success": False,
                "error": "Gmail search failed.",
                "message": search_result.get(
                    "reason"
                ),
                "documents_processed": [],
                "learning_results": [],
                "errors": [
                    search_result.get(
                        "reason"
                    )
                ]
            }


        # =====================================================
        # PROCESS SEARCH RESULTS
        # =====================================================

        result_groups = search_result.get(
            "results",
            []
        )


        for group in result_groups:

            messages = group.get(
                "messages",
                []
            )


            for message in messages:

                thread_id = message.get(
                    "thread_id"
                )


                # ---------------------------------------------
                # Skip duplicate threads
                # ---------------------------------------------

                if not thread_id:

                    continue


                if thread_id in processed_threads:

                    continue


                processed_threads.add(
                    thread_id
                )


                # =================================================
                # RECONSTRUCT THREAD
                # =================================================

                try:

                    thread_result = (
                        self.gmail.get_thread_evidence(
                            thread_id=thread_id
                        )
                    )

                except Exception as e:

                    errors.append(
                        f"Thread reconstruction failed "
                        f"for {thread_id}: {str(e)}"
                    )

                    continue


                if not thread_result.get("success"):

                    errors.append(
                        f"Unable to reconstruct thread "
                        f"{thread_id}"
                    )

                    continue


                attachments = thread_result.get(
                    "attachments",
                    []
                )


                # =================================================
                # FIND PDF ATTACHMENTS
                # =================================================

                pdf_attachments = []

                for attachment in attachments:

                    mime_type = attachment.get(
                        "mime_type",
                        ""
                    )

                    filename = attachment.get(
                        "filename",
                        ""
                    )


                    if (
                        mime_type == "application/pdf"
                        or filename.lower().endswith(
                            ".pdf"
                        )
                    ):

                        pdf_attachments.append(
                            attachment
                        )


                # =================================================
                # PROCESS EACH PDF
                # =================================================

                for attachment in pdf_attachments:

                    temporary_file_path = None


                    try:

                        filename = attachment.get(
                            "filename"
                        )

                        message_id = attachment.get(
                            "message_id"
                        )

                        attachment_id = attachment.get(
                            "attachment_id"
                        )


                        # -----------------------------------------
                        # DOWNLOAD TEMPORARILY
                        # -----------------------------------------

                        download_result = (
                            self.gmail.download_attachment(
                                message_id=message_id,
                                attachment_id=attachment_id,
                                filename=filename
                            )
                        )


                        if not download_result.get(
                            "success"
                        ):

                            errors.append(
                                f"Download failed: "
                                f"{filename}"
                            )

                            continue


                        temporary_file_path = (
                            download_result.get(
                                "file_path"
                            )
                        )


                        # -----------------------------------------
                        # READ PDF
                        # -----------------------------------------

                        pdf_result = (
                            self.pdf_reader.read_pdf(
                                temporary_file_path
                            )
                        )


                        if not pdf_result.get(
                            "success",
                            True
                        ):

                            errors.append(
                                f"PDF reading failed: "
                                f"{filename}"
                            )

                            continue


                        extracted_text = (
                            pdf_result.get(
                                "text",
                                ""
                            )
                        )


                        if not extracted_text.strip():

                            errors.append(
                                f"No readable text found "
                                f"in {filename}"
                            )

                            continue


                        # -----------------------------------------
                        # CREATE EVIDENCE SOURCE
                        # -----------------------------------------

                        source = {

                            "type":
                                "gmail_attachment",

                            "filename":
                                filename,

                            "message_id":
                                message_id,

                            "thread_id":
                                thread_id,

                            "query":
                                query
                        }


                        # -----------------------------------------
                        # LEARN FACTS
                        # -----------------------------------------

                        learning_result = (
                            self.learning_service
                            .learn_from_evidence(
                                session=session,
                                text=extracted_text,
                                source=source
                            )
                        )


                        learning_results.append(
                            learning_result
                        )


                        # -----------------------------------------
                        # RECORD DOCUMENT
                        # -----------------------------------------

                        documents_processed.append(
                            {

                                "filename":
                                    filename,

                                "thread_id":
                                    thread_id,

                                "message_id":
                                    message_id,

                                "method":
                                    pdf_result.get(
                                        "method",
                                        "UNKNOWN"
                                    ),

                                "pages":
                                    pdf_result.get(
                                        "pages",
                                        0
                                    ),

                                "facts_found":
                                    learning_result.get(
                                        "facts_found",
                                        0
                                    )
                            }
                        )


                    except Exception as e:

                        errors.append(
                            f"Error processing "
                            f"{attachment.get('filename')}: "
                            f"{str(e)}"
                        )


                    finally:

                        # -----------------------------------------
                        # ALWAYS DELETE TEMPORARY FILE
                        # -----------------------------------------

                        if temporary_file_path:

                            try:

                                self.gmail.delete_temporary_file(
                                    temporary_file_path
                                )

                            except Exception as e:

                                errors.append(
                                    f"Cleanup failed for "
                                    f"{attachment.get('filename')}: "
                                    f"{str(e)}"
                                )


        # =====================================================
        # FINAL RESULT
        # =====================================================

        success = (
            len(documents_processed) > 0
        )


        return {

            "success":
                success,

            "query":
                query,

            "documents_processed":
                documents_processed,

            "learning_results":
                learning_results,

            "errors":
                errors,

            "message":
                (
                    "Evidence processed successfully."
                    if success
                    else
                    "No processable PDF evidence found."
                )
        }