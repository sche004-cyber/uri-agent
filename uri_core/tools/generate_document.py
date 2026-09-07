"""Capability: generate a real Office file (DOCX/XLSX/PPTX/PDF) from a
request (M19).

This is the generic counterpart to draft_institutional_note/
draft_institutional_order: it never assumes the document is an
institutional note or order, and it never emits a template. The
requested output FORMAT (docx/xlsx/pptx/pdf) is detected from the
request; the Brain then authors the actual content, exactly the same
way M17's institutional drafting does - by reusing
services/institutional_drafting.py's policy/evidence/soul assembly and
services/document_composer.py's Brain-authoring call, just without the
note/order-specific framing. The rendered bytes are stored through
FileStore (containment-checked, size/type-validated, session-scoped),
so the result is downloadable via the existing GET
/files/{file_id}/content - no second storage path.
"""

import re
from typing import Any, Dict, Optional

from uri_core.config.institutional_rules import load_institutional_rules
from uri_core.core.file_store import FileStore, FileValidationError, sanitize_filename
from uri_core.services.document_composer import DocumentComposer
from uri_core.services.drafting_guidance import build_drafting_brief
from uri_core.services.document_writer_service import DocumentWriterService
from uri_core.services.institutional_drafting import (
    extract_drafting_rules,
    gather_session_evidence,
    read_text_file,
    POLICY_PATH,
    SOUL_PATH,
)
from uri_core.services.office_document_writer import (
    render_pdf_bytes,
    render_pptx_bytes,
    render_xlsx_bytes,
)


_MEDIA_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "pdf": "application/pdf",
}

# Ordered so a more specific phrase ("slide deck") is checked before a
# more general one; the first match wins. Deliberately keyword-based
# (the same discipline drafting_guidance.classify_purpose already
# uses) - the FORMAT is the one thing that must be deterministic, since
# it decides which renderer runs; everything about the CONTENT is left
# to the Brain.
_FORMAT_KEYWORDS = (
    ("pptx", ("powerpoint", "presentation", "slide deck", "slides", "slideshow")),
    ("xlsx", ("excel", "spreadsheet", "workbook", "xlsx")),
    ("pdf", ("pdf",)),
)

_KIND_LABELS = {
    "pptx": "presentation",
    "xlsx": "spreadsheet",
    "pdf": "report",
    "docx": "report",
}


def infer_output_format(request_text: str, requested_output: str = "") -> str:
    """docx is the default - a generic written document is the common
    case, and always safe to open/edit further."""

    text = f"{requested_output} {request_text}".lower()
    for format_id, keywords in _FORMAT_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return format_id
    return "docx"


def _derive_filename(request_text: str, output_format: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", request_text)[:8]
    stem = "_".join(words) if words else "document"
    return sanitize_filename(f"{stem}.{output_format}")


class GenerateDocumentTool:
    """Detects the requested file format, has the Brain author the
    content (reusing the exact M17 drafting assembly), renders it into
    real Office bytes, and stores it via FileStore. `composer` is
    injectable for tests; the default lazily constructs the real
    (Ollama-backed) composer and falls back to a plain honest draft if
    the model is unreachable - this tool never requires a running model
    to return a file."""

    def __init__(self, composer: Optional[DocumentComposer] = None, file_store: Optional[FileStore] = None):
        self._composer = composer
        self._file_store = file_store or FileStore()

    def generate(self, **kwargs) -> Dict[str, Any]:
        request_text = kwargs.get("request_text", "") or ""
        session_id = kwargs.get("session_id")
        decision_context = kwargs.get("decision_context") or {}
        requested_output = kwargs.get("requested_output", "") or ""

        output_format = infer_output_format(request_text, requested_output)
        document_type = _KIND_LABELS.get(output_format, "report")

        rules = load_institutional_rules()
        policy_rules = extract_drafting_rules(read_text_file(POLICY_PATH))
        soul_text = read_text_file(SOUL_PATH)

        evidence = gather_session_evidence(session_id, self._file_store)
        if isinstance(decision_context.get("verified_evidence"), dict):
            evidence = {**decision_context["verified_evidence"], **evidence}

        preferences = {}
        if isinstance(decision_context.get("user_preferences"), dict):
            preferences = decision_context["user_preferences"]

        brief = build_drafting_brief(
            request_text=request_text,
            requested_output=requested_output,
            document_type=document_type,
            evidence=evidence,
            preferences=preferences,
            institutional_rules=rules,
            policy_rules=policy_rules,
        )
        # Additive-only field document_composer.py reads to shape the
        # Brain's output for a non-prose format; never set for note/
        # order drafting, which is unaffected.
        brief["output_format"] = output_format

        composer = self._composer or DocumentComposer()
        result = composer.compose(
            brief=brief,
            request_text=request_text,
            evidence=evidence,
            preferences=preferences,
            soul_text=soul_text,
        )
        body = result["body"]

        try:
            content_bytes = self._render(output_format, body)
        except Exception as error:
            return {
                "status": "error",
                "message": f"URI could not render the {output_format.upper()} file.",
                "error": str(error),
            }

        filename = _derive_filename(request_text, output_format)

        try:
            record = self._file_store.save(
                filename=filename,
                content=content_bytes,
                media_type=_MEDIA_TYPES.get(output_format, "application/octet-stream"),
                session_id=session_id,
            )
        except FileValidationError as error:
            return {
                "status": "error",
                "message": "URI generated the document but could not store it.",
                "error": str(error),
            }

        return {
            "status": "success",
            "file": record.to_reference(),
            "output_format": output_format,
            "composed_by": result["composed_by"],
            "detail": result.get("detail"),
            "preview": body[:500],
        }

    @staticmethod
    def _render(output_format: str, body: str) -> bytes:
        if output_format == "xlsx":
            return render_xlsx_bytes(body)
        if output_format == "pptx":
            return render_pptx_bytes(body)
        if output_format == "pdf":
            return render_pdf_bytes(body)
        return DocumentWriterService().render_docx_bytes(body)
