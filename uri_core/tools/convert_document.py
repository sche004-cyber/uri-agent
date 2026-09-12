"""Capability: convert an already-attached document into a different
file format (2026-09-12, User directive - "convert this into a word
file").

Today: PDF -> DOCX only, the concrete case reported. Extracts real text
from the attached PDF (services/pdf_reader.py - real extraction, OCR
fallback for scanned pages, never invented content) and renders it into
a real DOCX via services/document_writer_service.py, the exact same
renderer generate_document.py already uses - no second rendering path.
Stored through FileStore (containment-checked, size/type-validated,
session-scoped), so the result is downloadable via the existing GET
/files/{file_id}/content, same as generate_document/draft_institutional_
note/order.
"""

from typing import Any, Dict, Optional

from uri_core.core.file_store import FileStore, FileValidationError, sanitize_filename
from uri_core.services.document_writer_service import DocumentWriterService
from uri_core.services.pdf_reader import PDFReader

# 2026-09-12 (User directive): "convert to word AND modify/update it to
# match my current stats" - a single-turn edit instruction alongside
# the conversion. Narrow trigger (a modification verb) so a plain
# "convert this to word" is never sent through the Brain unnecessarily.
_MODIFICATION_TRIGGERS = ("modify", "update", "change", "correct", "fix")


class ConvertDocumentTool:
    """`file_store` is injectable (see dispatcher.py's inspect-based
    constructor wiring) so this tool reads/writes the calling user's own
    FileStore, never an ambient default."""

    def __init__(self, file_store: Optional[FileStore] = None, composer=None):
        self._file_store = file_store or FileStore()
        self._composer = composer

    def convert(self, **kwargs: Any) -> Dict[str, Any]:
        session_id = kwargs.get("session_id")
        original_request_text = kwargs.get("request_text", "") or ""
        requested_output = (kwargs.get("requested_output", "") or "").lower()
        request_text = original_request_text.lower()

        if "docx" in requested_output or "word" in requested_output or "word" in request_text:
            output_format = "docx"
        else:
            # Only DOCX is implemented today; every other requested
            # output is an honest gap, never a silent substitution.
            return {
                "status": "not_implemented",
                "message": (
                    "URI can currently convert an attached PDF to a "
                    "Word (.docx) file only. Ask for a Word/docx "
                    "conversion, or a different capability for other "
                    "output formats."
                ),
            }

        attachments = (
            self._file_store.list_for_session(session_id) if session_id else []
        )
        pdf_attachments = [
            record for record in attachments if record.filename.lower().endswith(".pdf")
        ]

        if not pdf_attachments:
            return {
                "status": "input_required",
                "message": (
                    "URI needs a PDF attached to this conversation to "
                    "convert - attach the file, then ask again."
                ),
            }

        # Most recently attached PDF - StoredFile records are appended
        # in upload order, so the last match is the most recent one.
        source = pdf_attachments[-1]
        source_path = self._file_store.path_for(source.file_id)

        if source_path is None:
            return {
                "status": "error",
                "message": "URI could not locate the attached file's stored contents.",
            }

        extraction = PDFReader().read_pdf(source_path)

        if not extraction.get("success"):
            return {
                "status": "error",
                "message": (
                    "URI could not read the attached PDF: "
                    f"{extraction.get('error', 'unknown error')}"
                ),
            }

        text = extraction.get("text") or ""

        if not text.strip():
            return {
                "status": "error",
                "message": (
                    "URI extracted no readable text from the attached "
                    "PDF (it may be a blank or unsupported scan)."
                ),
            }

        edited = False
        if any(trigger in request_text for trigger in _MODIFICATION_TRIGGERS):
            revised = self._apply_modification(
                original_text=text,
                instruction=original_request_text,
                principal=kwargs.get("principal"),
            )
            if revised is not None:
                text = revised
                edited = True
            # A failed/unavailable edit attempt still produces the
            # unedited conversion below - never blocks the one thing
            # the User definitely asked for (a docx file) just because
            # the Brain-authored edit step didn't work this time.

        content_bytes = DocumentWriterService().render_docx_bytes(text)

        base_name = sanitize_filename(source.filename).rsplit(".", 1)[0]
        output_filename = f"{base_name}.docx"

        try:
            record = self._file_store.save(
                filename=output_filename,
                content=content_bytes,
                media_type=(
                    "application/vnd.openxmlformats-officedocument"
                    ".wordprocessingml.document"
                ),
                session_id=session_id,
            )
        except FileValidationError as error:
            return {
                "status": "error",
                "message": "URI converted the document but could not store it.",
                "error": str(error),
            }

        return {
            "status": "success",
            "file": record.to_reference(),
            "output_format": output_format,
            "source_filename": source.filename,
            "edited": edited,
            "message": (
                "Converted and applied your requested changes. Note: "
                "this is a plain-text conversion - original layout, "
                "tables, and fonts from the PDF are not preserved."
                if edited
                else (
                    "Converted to a plain-text .docx - original layout, "
                    "tables, and fonts from the PDF are not preserved."
                )
            ),
            "preview": text[:500],
        }

    def _apply_modification(
        self, *, original_text: str, instruction: str, principal: Any
    ) -> Optional[str]:
        """Has the Brain revise the extracted text per the user's own
        stated changes (e.g. "change my salary to 90000") - reuses
        institutional_drafting's exact composer/brief machinery
        generate_document.py already relies on, never a second drafting
        path. Returns None (never raises) on any failure, so the
        caller falls back to the unedited conversion rather than
        losing the file entirely."""

        try:
            from uri_core.services.document_composer import DocumentComposer
            from uri_core.services.drafting_guidance import build_drafting_brief

            brief = build_drafting_brief(
                request_text=instruction,
                requested_output="an updated version of the attached document",
                document_type="edited_document",
                evidence={"original_document_text": original_text},
            )

            composer = self._composer or DocumentComposer(principal=principal)
            result = composer.compose(
                brief=brief,
                request_text=instruction,
                evidence={"original_document_text": original_text},
                principal=principal,
            )
            body = result.get("body") if isinstance(result, dict) else None
            return body if isinstance(body, str) and body.strip() else None
        except Exception:
            return None
