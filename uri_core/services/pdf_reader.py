from pathlib import Path
import shutil

import fitz  # PyMuPDF
import pytesseract
from PIL import Image


class PDFReader:
    """
    Reads text-based and scanned PDFs.

    Strategy:
    1. Try normal PDF text extraction.
    2. If insufficient text is found, use OCR.
    """

    def __init__(self):
        self.tesseract_path = (
            r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        )

        pytesseract.pytesseract.tesseract_cmd = (
            self.tesseract_path
        )

    def read_pdf(self, file_path: str) -> dict:

        path = Path(file_path)

        if not path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}"
            }

        try:

            document = fitz.open(str(path))

            pages_found = len(document)

            extracted_pages = []

            # -----------------------------------------
            # FIRST PASS: NORMAL TEXT EXTRACTION
            # -----------------------------------------

            for page_number in range(pages_found):

                page = document.load_page(page_number)

                text = page.get_text("text").strip()

                extracted_pages.append({
                    "page": page_number + 1,
                    "text": text
                })

            combined_text = "\n\n".join(
                page["text"]
                for page in extracted_pages
            ).strip()

            # If meaningful text exists, use it.
            if len(combined_text) >= 100:

                document.close()

                return {
                    "success": True,
                    "filename": path.name,
                    "pages_found": pages_found,
                    "method": "TEXT_EXTRACTION",
                    "pages": extracted_pages,
                    "text": combined_text
                }

            # -----------------------------------------
            # SECOND PASS: OCR FOR SCANNED PDFs
            # -----------------------------------------

            ocr_pages = []

            for page_number in range(pages_found):

                page = document.load_page(page_number)

                # Render page at higher resolution
                pix = page.get_pixmap(
                    matrix=fitz.Matrix(2, 2)
                )

                image = Image.frombytes(
                    "RGB",
                    [pix.width, pix.height],
                    pix.samples
                )

                ocr_text = pytesseract.image_to_string(
                    image,
                    lang="eng"
                ).strip()

                ocr_pages.append({
                    "page": page_number + 1,
                    "text": ocr_text
                })

            document.close()

            combined_ocr_text = "\n\n".join(
                page["text"]
                for page in ocr_pages
            ).strip()

            return {
                "success": True,
                "filename": path.name,
                "pages_found": pages_found,
                "method": "OCR",
                "pages": ocr_pages,
                "text": combined_ocr_text
            }

        except Exception as error:

            return {
                "success": False,
                "error": str(error)
            }