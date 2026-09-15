"""Capability: convert an already-attached document into a different
file format (2026-09-12, User directive - "convert this into a word
file").

Today: PDF -> DOCX only, the concrete case reported.

Native-tool audit Pilot 3 (docs/plans/URI_NATIVE_TOOL_PILOTS.md): the
PRIMARY path is now real, layout-preserving conversion via
services/pdf_layout_converter.py (wraps `pdf2docx`) - page size/
orientation, margins, paragraph structure, fonts/styles, spacing,
tables, and images are reconstructed, not just extracted text. This
replaces plain-text-extraction-and-rebuild as the default outcome for
an ordinary "convert this to Word" request, which previously always
discarded layout - honestly disclosed at the time, but a real gap
relative to what a user asking to convert a document actually expects.

The plain-text path (services/pdf_reader.py + document_writer_service.py,
the same renderer generate_document.py uses) is kept as an honest
FALLBACK only - used when layout-preserving conversion genuinely fails
(reported "degraded", never "success"), and for the separate "convert
AND also edit the content" case (services/pdf_reader.py + Content edit is
a text-level operation pdf2docx's structural reconstruction cannot
accommodate; this is disclosed as reduced-fidelity too, not silently
presented as a full-fidelity conversion).

Stored through FileStore (containment-checked, size/type-validated,
session-scoped), so the result is downloadable via the existing GET
/files/{file_id}/content, same as generate_document/draft_institutional_
note/order.
"""

import os
import tempfile
from typing import Any, Dict, Optional

from uri_core.core.file_store import FileStore, FileValidationError, sanitize_filename
from uri_core.services.document_writer_service import DocumentWriterService
from uri_core.services.pdf_layout_converter import convert_pdf_to_docx_preserving_layout
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

        base_name = sanitize_filename(source.filename).rsplit(".", 1)[0]
        output_filename = f"{base_name}.docx"
        modification_requested = any(
            trigger in request_text for trigger in _MODIFICATION_TRIGGERS
        )

        # Primary path: real, layout-preserving conversion - never
        # attempted when the user also asked for a content edit, since
        # pdf2docx reconstructs the ORIGINAL PDF's structure and has no
        # way to accommodate Brain-revised text within it.
        if not modification_requested:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_docx_path = os.path.join(tmp_dir, output_filename)
                layout_result = convert_pdf_to_docx_preserving_layout(
                    source_path, tmp_docx_path
                )
                if layout_result.get("status") == "success":
                    with open(tmp_docx_path, "rb") as handle:
                        content_bytes = handle.read()
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
                        "edited": False,
                        "layout_preserved": True,
                        "preserved": layout_result.get("preserved"),
                        "not_preserved": layout_result.get("not_preserved"),
                        "message": (
                            "Converted to an editable .docx, preserving the "
                            "PDF's page layout, fonts, tables, and images as "
                            "faithfully as automated reconstruction allows."
                        ),
                    }
                # Real layout conversion failed - fall through to the
                # honest plain-text path below rather than failing the
                # whole request; the eventual status must say
                # "degraded", never "success", since layout genuinely
                # was not preserved.
                layout_failure_reason = layout_result.get("message")
        else:
            layout_failure_reason = None

        # Fallback path: plain text extraction + rebuild - used when
        # layout-preserving conversion failed, or when the user asked
        # to also edit the content (a text-level operation the layout
        # path cannot accommodate). Either way this is real output, but
        # never full-fidelity - reported "degraded", not "success".
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
        if modification_requested:
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

        if edited:
            message = (
                "Converted and applied your requested changes. Note: "
                "this is a plain-text conversion - original layout, "
                "tables, and fonts from the PDF are not preserved, "
                "since editing the content required rebuilding the "
                "document as plain text."
            )
        elif layout_failure_reason:
            message = (
                "URI could not preserve the original PDF's layout for "
                f"this file ({layout_failure_reason}), so it converted "
                "the extracted text instead. Original layout, tables, "
                "and fonts are not preserved in this file."
            )
        else:
            message = (
                "Converted to a plain-text .docx - original layout, "
                "tables, and fonts from the PDF are not preserved."
            )

        return {
            "status": "degraded",
            "file": record.to_reference(),
            "output_format": output_format,
            "source_filename": source.filename,
            "edited": edited,
            "layout_preserved": False,
            "message": message,
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
