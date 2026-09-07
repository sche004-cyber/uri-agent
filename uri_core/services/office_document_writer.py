"""M19: renders Brain-composed text into XLSX/PPTX/PDF bytes.

Mirrors document_writer_service.py's DOCX discipline exactly - pure
rendering, no reasoning, no reasoning about content, never writes to
disk itself (the caller, generate_document.py, hands the returned
bytes to FileStore, the one containment-checked/validated place a
generated file is stored). Reuses libraries already in this
repository's dependency set (openpyxl, already used for reading
spreadsheets; pymupdf/fitz, already used for reading PDFs) rather than
adding a new PDF-writing library.

Content shape the Brain is asked to produce (see generate_document.py's
prompt) and these functions parse:
  - XLSX: the same "|cell|cell|" markdown table syntax
    document_writer_service.py already parses for DOCX tables - the
    first row is treated as a header row.
  - PPTX: "# Slide Title" markdown headings, one per slide, with each
    following non-empty line becoming one bullet on that slide.
  - PDF: plain paragraphs, paginated by a generous line budget.
"""

import io
from typing import List

from openpyxl import Workbook
from openpyxl.styles import Font
from pptx import Presentation
import fitz


def _parse_markdown_table(text: str) -> List[List[str]]:
    """The same "|cell|cell|" parsing document_writer_service.py's
    _build_document already applies for DOCX tables, extracted here so
    both DOCX and XLSX rendering read identical table syntax the Brain
    was given identical instructions to produce. Returns every row
    found across the whole text (a document with more than one table is
    flattened into one sheet - deliberately simple, matching the scope
    of a single generated spreadsheet)."""

    rows: List[List[str]] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        if "---" in stripped:
            continue
        cells = [cell.strip() for cell in stripped.split("|")[1:-1]]
        rows.append(cells)
    return rows


def render_xlsx_bytes(content: str) -> bytes:
    """Renders markdown-table rows into a real .xlsx workbook (first
    row as header, bold). When the Brain's output contains no table at
    all, each non-empty line becomes one cell in column A instead of
    failing outright - a plain but honest spreadsheet rather than no
    file."""

    rows = _parse_markdown_table(content)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"

    if rows:
        for row_index, row in enumerate(rows, start=1):
            for col_index, value in enumerate(row, start=1):
                cell = sheet.cell(row=row_index, column=col_index, value=value)
                if row_index == 1:
                    cell.font = Font(bold=True)
    else:
        for row_index, line in enumerate(
            (line.strip() for line in content.split("\n") if line.strip()),
            start=1,
        ):
            sheet.cell(row=row_index, column=1, value=line)

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def render_pptx_bytes(content: str) -> bytes:
    """Renders "# Slide Title" sections into real presentation slides -
    each subsequent non-empty, non-heading line becomes one bullet on
    that slide. Content with no "# " headings at all becomes a single
    slide (title from the first non-empty line, the rest as bullets),
    so a Brain response that forgot the heading syntax still produces a
    real presentation rather than an empty one."""

    presentation = Presentation()
    title_and_content_layout = presentation.slide_layouts[1]

    slides: List[tuple] = []
    current_title = None
    current_bullets: List[str] = []

    def _flush():
        if current_title is not None or current_bullets:
            slides.append((current_title or "Untitled slide", list(current_bullets)))

    for raw_line in content.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# "):
            _flush()
            current_title = line[2:].strip()
            current_bullets = []
        else:
            bullet = line[2:].strip() if line.startswith("- ") else line
            current_bullets.append(bullet)
    _flush()

    if not slides:
        slides = [("Untitled presentation", [])]

    for title, bullets in slides:
        slide = presentation.slides.add_slide(title_and_content_layout)
        slide.shapes.title.text = title
        body = slide.placeholders[1].text_frame
        if bullets:
            body.text = bullets[0]
            for bullet in bullets[1:]:
                paragraph = body.add_paragraph()
                paragraph.text = bullet

    buffer = io.BytesIO()
    presentation.save(buffer)
    return buffer.getvalue()


# Rough character budget per PDF page - generous enough for a normal
# paragraph-per-page administrative document; a page that would overflow
# it simply continues onto the next page rather than being truncated.
_PDF_CHARS_PER_PAGE = 2800
_PDF_PAGE_RECT = fitz.paper_rect("a4")
_PDF_MARGIN = 50


def render_pdf_bytes(content: str) -> bytes:
    """Renders plain text into a real, paginated PDF using pymupdf -
    already a dependency of this repository for PDF *reading*, reused
    here for writing rather than adding a new PDF library."""

    document = fitz.open()
    paragraphs = content.split("\n")

    page = None
    text_box = None
    consumed = 0

    def _new_page():
        nonlocal page, text_box, consumed
        page = document.new_page(width=_PDF_PAGE_RECT.width, height=_PDF_PAGE_RECT.height)
        text_box = fitz.Rect(
            _PDF_MARGIN,
            _PDF_MARGIN,
            _PDF_PAGE_RECT.width - _PDF_MARGIN,
            _PDF_PAGE_RECT.height - _PDF_MARGIN,
        )
        consumed = 0

    _new_page()
    buffer_text = ""

    for paragraph in paragraphs:
        candidate = f"{buffer_text}\n{paragraph}" if buffer_text else paragraph
        if len(candidate) - consumed > _PDF_CHARS_PER_PAGE:
            page.insert_textbox(text_box, buffer_text, fontsize=11, fontname="helv")
            consumed += len(buffer_text)
            _new_page()
            buffer_text = paragraph
        else:
            buffer_text = candidate

    if buffer_text:
        page.insert_textbox(text_box, buffer_text, fontsize=11, fontname="helv")

    data = document.tobytes()
    document.close()
    return data
