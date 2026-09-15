"""Layout-preserving PDF -> DOCX conversion (native-tool audit, Pilot 3).

Wraps `pdf2docx` (https://github.com/dothinking/pdf2docx) - a real,
existing library purpose-built for exactly this problem: it parses a
PDF's page layout (text blocks with real fonts/sizes/positions,
tables, images) and reconstructs it as an editable, structurally
faithful `.docx`, rather than the plain-text-extract-and-rebuild
approach `convert_document.py` used before this pilot (which discarded
layout, tables, fonts, and images entirely - honestly disclosed at the
time, but a real capability gap relative to what a user asking to
"convert this to Word" actually expects).

This is pure machinery, exactly like every other tool in this
codebase: it never decides content, never invents structure, and
reports honestly when conversion fails - it does not silently
substitute the plain-text path itself (the caller, convert_document.py,
owns that fallback decision and must surface it as degraded, not
success, per docs/plans/URI_NATIVE_TOOL_AUDIT.md Root Cause A's
established discipline).

Known, disclosed limitation (pdf2docx's own, not introduced here):
scanned/image-only PDF pages have no extractable text layout to
reconstruct - pdf2docx will produce a docx with those pages effectively
empty rather than inventing text. Callers needing OCR text from a
scanned page should use PDFReader (services/pdf_reader.py) instead;
this module is for born-digital PDFs with a real text/graphics layer.
"""

from __future__ import annotations

import os
from typing import Any, Dict


def convert_pdf_to_docx_preserving_layout(pdf_path: str, docx_path: str) -> Dict[str, Any]:
    """Converts pdf_path to docx_path using pdf2docx, preserving page
    size/orientation, margins, paragraph/heading structure, fonts and
    styles, spacing/alignment, tables (including borders/shading), and
    images - as faithfully as pdf2docx's own real layout analysis
    achieves, never faked. Returns {"status": "success"} with the real
    output path, or {"status": "error", "message": ...} on a genuine
    conversion failure - never raises, matching every other tool's own
    honesty discipline in this codebase."""

    if not os.path.exists(pdf_path):
        return {
            "status": "error",
            "message": f"Source PDF not found at {pdf_path}.",
        }

    try:
        from pdf2docx import Converter
    except ImportError as error:
        return {
            "status": "error",
            "message": "The layout-preserving PDF converter is not installed.",
            "error": str(error),
        }

    converter = None
    try:
        converter = Converter(pdf_path)
        converter.convert(docx_path)
    except Exception as error:
        return {
            "status": "error",
            "message": (
                "URI could not convert this PDF while preserving its "
                "layout - the page structure may be unsupported (e.g. "
                "a scanned/image-only PDF with no real text layer)."
            ),
            "error": str(error),
        }
    finally:
        if converter is not None:
            try:
                converter.close()
            except Exception:
                pass

    if not os.path.exists(docx_path):
        return {
            "status": "error",
            "message": "The converter did not produce an output file.",
        }

    return {
        "status": "success",
        "docx_path": docx_path,
        "preserved": [
            "page size/orientation", "margins", "paragraph structure",
            "fonts and styles", "spacing/alignment", "tables",
            "images",
        ],
        "not_preserved": [
            "exact pixel-level positioning for complex multi-column or "
            "overlapping layouts (pdf2docx approximates these as "
            "ordinary flowing paragraphs/tables)",
            "text on scanned/image-only pages (no OCR is performed by "
            "this path - see read_attached_file.py/pdf_reader.py for "
            "OCR text extraction instead)",
        ],
    }
