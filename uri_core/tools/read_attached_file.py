"""M16 Priority 1: read a file the user attached to this conversation.

Pure machinery, exactly mirroring web_search.py/gmail_search.py: the
Brain decides whether reading an attachment is needed (it can see that
attachments exist from query_context's "attachments" section - see
orchestrator.py); this tool performs the real extraction and returns
the real text as evidence. It never decides what the document means,
never drafts an answer, and never invents content when extraction
fails or the document is empty.

Argument boundary, unchanged from every other capability: URI supplies
the arguments deterministically (session_id, from the real session),
never the model's proposed arguments - see orchestrator.py's
"only a plain capability-name string ever crosses this boundary".
Which file is read therefore follows from what the user actually
attached to THIS session, not from anything the Brain asserted.

Reuses services/file_extraction.extract_file_text (which in turn
reuses PDFReader/openpyxl/pytesseract) and core/file_store.FileStore
for containment-checked path resolution - no extraction, validation,
or path handling is reimplemented here.
"""

from uri_core.core.file_store import FileStore
from uri_core.services.file_extraction import extract_file_text

# How many of a session's attachments one call will read. Bounded so a
# session with many files can never produce an unbounded result.
MAX_FILES_PER_CALL = 3


class ReadAttachedFileTool:
    """The only capability that reads user-supplied file content."""

    def __init__(self, file_store=None):
        self._file_store = file_store or FileStore()

    def execute(self, **kwargs):

        session_id = kwargs.get("session_id")

        if not session_id:
            return {
                "status": "input_required",
                "message": (
                    "No conversation session was identified, so URI "
                    "could not tell which attachment to read."
                ),
            }

        attachments = self._file_store.list_for_session(session_id)

        if not attachments:
            return {
                "status": "not_found",
                "message": (
                    "No file has been attached to this conversation."
                ),
            }

        # Most recently attached first - the file the user most likely
        # means when they refer to "the attachment".
        attachments = list(reversed(attachments))[:MAX_FILES_PER_CALL]

        documents = []

        for record in attachments:

            path = self._file_store.path_for(record.file_id)

            if path is None:
                documents.append(
                    {
                        "filename": record.filename,
                        "status": "unreadable",
                        "error": "The stored file is no longer available.",
                    }
                )
                continue

            extraction = extract_file_text(path)

            documents.append(
                {
                    "filename": record.filename,
                    "media_type": record.media_type,
                    "size_bytes": record.size_bytes,
                    **extraction,
                }
            )

        readable = [
            document
            for document in documents
            if document.get("status") == "success"
        ]

        if not readable:
            # Every attachment failed or had nothing to read - report
            # that plainly rather than returning an empty "success".
            return {
                "status": "unreadable",
                "message": (
                    "URI could not read any text from the attached "
                    "file(s)."
                ),
                "documents": documents,
            }

        return {
            "status": "success",
            "message": (
                f"Read {len(readable)} attached file(s)."
            ),
            "documents": documents,
        }
