"""M16 Priority 1: general text extraction from a user-supplied file.

Deliberately GENERAL, not PDF-only: a PDF, a plain-text/CSV/JSON file,
a spreadsheet, and an image all reach the Brain through the same
{status, text, ...} envelope, so the Brain reasons about "what this
document says" without needing to know which extractor produced it.

Reuses, never duplicates, the extraction that already exists:
    - PDF (including scanned/OCR)  -> services/pdf_reader.PDFReader,
      unmodified; the same reader the Gmail evidence pipeline already
      uses (see evidence_processor.py).
    - Spreadsheets                 -> openpyxl, the same library
      student_record_service.py already reads workbooks with.
    - Images                       -> pytesseract/PIL, already present
      as PDFReader's OCR dependency.

Honesty discipline, matching web_search.py/gmail_search.py: every real
outcome is reported distinctly - extracted text, an unsupported type,
an empty document, or a genuine extraction failure - and nothing is
ever invented. A file that cannot be read is reported as unreadable;
its content is never guessed at from the filename.

This module performs NO authorization and NO path resolution of its
own: it is given a path the Engine already validated and contained
(see core/file_store.FileStore.path_for). It never decides what a
document means - that is the Brain's job.
"""

import json
import os
from typing import Any, Dict

# Bounds how much extracted text is handed onward in one result. A
# large document must never blow up the Brain's context; the same
# "bounded reference, never an unbounded dump" discipline
# query_context.py/experience_store.py already apply.
MAX_EXTRACTED_CHARACTERS = 20000

TEXT_EXTENSIONS = frozenset({".txt", ".md", ".csv", ".json", ".log"})
IMAGE_EXTENSIONS = frozenset(
    {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}
)
SPREADSHEET_EXTENSIONS = frozenset({".xlsx", ".xls"})


def _truncate(text: str) -> Dict[str, Any]:

    if len(text) <= MAX_EXTRACTED_CHARACTERS:
        return {"text": text, "truncated": False}

    return {
        "text": text[:MAX_EXTRACTED_CHARACTERS],
        "truncated": True,
    }


def _extract_pdf(path: str) -> Dict[str, Any]:

    from uri_core.services.pdf_reader import PDFReader

    result = PDFReader().read_pdf(path)

    if not result.get("success"):
        return {
            "status": "unreadable",
            "error": result.get("error", "The PDF could not be read."),
        }

    return {
        "status": "success",
        "method": result.get("method"),
        "pages_found": result.get("pages_found"),
        "text": result.get("text", ""),
    }


def _extract_text_file(path: str) -> Dict[str, Any]:

    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return {
            "status": "success",
            "method": "TEXT_FILE",
            "text": handle.read(),
        }


def _extract_spreadsheet(path: str) -> Dict[str, Any]:

    from openpyxl import load_workbook

    workbook = load_workbook(path, data_only=True, read_only=True)

    lines = []

    for sheet in workbook.worksheets:

        lines.append(f"# Sheet: {sheet.title}")

        for row in sheet.iter_rows(values_only=True):

            cells = [
                "" if value is None else str(value) for value in row
            ]

            if any(cell.strip() for cell in cells):
                lines.append("\t".join(cells))

    workbook.close()

    return {
        "status": "success",
        "method": "SPREADSHEET",
        "text": "\n".join(lines),
    }


def _extract_image(path: str) -> Dict[str, Any]:

    import pytesseract
    from PIL import Image

    from uri_core.services.pdf_reader import PDFReader

    # Reuse PDFReader's already-configured tesseract binary path
    # rather than re-declaring it here.
    pytesseract.pytesseract.tesseract_cmd = PDFReader().tesseract_path

    with Image.open(path) as image:
        text = pytesseract.image_to_string(image, lang="eng").strip()

    return {"status": "success", "method": "OCR", "text": text}


def _extract_docx(path: str) -> Dict[str, Any]:

    import docx  # python-docx, declared in requirements.txt

    document = docx.Document(path)

    text = "\n".join(
        paragraph.text for paragraph in document.paragraphs
    )

    return {"status": "success", "method": "DOCX", "text": text}


_EXTRACTORS = [
    (frozenset({".pdf"}), _extract_pdf),
    (TEXT_EXTENSIONS, _extract_text_file),
    (SPREADSHEET_EXTENSIONS, _extract_spreadsheet),
    (IMAGE_EXTENSIONS, _extract_image),
    (frozenset({".docx"}), _extract_docx),
]


def extract_file_text(path: str) -> Dict[str, Any]:
    """Extracts readable text from one already-validated file path.

    Always returns a dict with a "status" of:
        success      - text was extracted (may still be empty, see
                       "empty" below, which is reported separately).
        empty        - the file was read successfully but contains no
                       readable text (e.g. a scanned page OCR found
                       nothing on). Distinct from a failure: the read
                       worked, the document genuinely has nothing.
        unsupported  - this type has no extractor. The file is still
                       stored; URI simply says so rather than
                       pretending to have read it.
        unreadable   - a real extraction failure, with the actual
                       error reported.

    Never raises: an unexpected failure in any extractor degrades to
    "unreadable" with the real exception text, so one bad document can
    never break a turn.
    """

    if not isinstance(path, str) or not os.path.exists(path):
        return {
            "status": "unreadable",
            "error": "The file is no longer available.",
        }

    extension = os.path.splitext(path)[1].lower()

    extractor = None

    for extensions, candidate in _EXTRACTORS:

        if extension in extensions:
            extractor = candidate
            break

    if extractor is None:
        return {
            "status": "unsupported",
            "media_kind": extension or "unknown",
            "message": (
                f"URI has no text extractor for '{extension or 'unknown'}' "
                "files. The file was stored but not read."
            ),
        }

    try:
        result = extractor(path)

    except Exception as error:
        return {"status": "unreadable", "error": str(error)}

    if result.get("status") != "success":
        return result

    text = (result.get("text") or "").strip()

    if not text:
        return {
            "status": "empty",
            "method": result.get("method"),
            "message": (
                "The file was read successfully but contains no "
                "readable text."
            ),
        }

    bounded = _truncate(text)

    payload = {
        "status": "success",
        "method": result.get("method"),
        "text": bounded["text"],
        "truncated": bounded["truncated"],
        "characters": len(text),
    }

    if result.get("pages_found") is not None:
        payload["pages_found"] = result["pages_found"]

    return payload
