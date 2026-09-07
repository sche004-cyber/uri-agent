"""M16 Priority 1: general (not PDF-only) text extraction. Every real
outcome - extracted, empty, unsupported, unreadable - must be reported
distinctly and honestly, and nothing may ever be invented. See
uri_core/services/file_extraction.py.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import patch

from uri_core.services import file_extraction
from uri_core.services.file_extraction import (
    MAX_EXTRACTED_CHARACTERS,
    extract_file_text,
)


class TextFileExtractionTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

    def _write(self, name, content, mode="w"):
        path = os.path.join(self.temp_dir.name, name)
        kwargs = {"encoding": "utf-8"} if mode == "w" else {}
        with open(path, mode, **kwargs) as handle:
            handle.write(content)
        return path

    def test_plain_text_is_extracted(self):
        path = self._write("note.txt", "Hello institutional world.")

        result = extract_file_text(path)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["method"], "TEXT_FILE")
        self.assertIn("institutional", result["text"])

    def test_csv_and_json_and_markdown_are_treated_as_text(self):
        for name, content in (
            ("data.csv", "a,b\n1,2"),
            ("data.json", json.dumps({"k": "v"})),
            ("doc.md", "# Heading"),
        ):
            result = extract_file_text(self._write(name, content))
            self.assertEqual(result["status"], "success", name)

    def test_empty_document_is_reported_as_empty_not_success(self):
        path = self._write("blank.txt", "   \n  ")

        result = extract_file_text(path)

        self.assertEqual(result["status"], "empty")
        self.assertNotIn("text", result)

    def test_unsupported_type_is_reported_honestly(self):
        path = self._write("archive.zip", "not really a zip")

        result = extract_file_text(path)

        self.assertEqual(result["status"], "unsupported")
        self.assertIn("no text extractor", result["message"])

    def test_missing_file_is_reported_as_unreadable(self):
        result = extract_file_text(
            os.path.join(self.temp_dir.name, "gone.txt")
        )

        self.assertEqual(result["status"], "unreadable")

    def test_long_text_is_bounded_and_flagged_as_truncated(self):
        path = self._write(
            "long.txt", "x" * (MAX_EXTRACTED_CHARACTERS + 500)
        )

        result = extract_file_text(path)

        self.assertEqual(result["status"], "success")
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["text"]), MAX_EXTRACTED_CHARACTERS)
        # The real, untruncated size is still reported honestly.
        self.assertEqual(
            result["characters"], MAX_EXTRACTED_CHARACTERS + 500
        )

    def test_extractor_failure_degrades_to_unreadable_not_raise(self):
        path = self._write("report.pdf", "not a real pdf")

        with patch(
            "uri_core.services.pdf_reader.PDFReader.read_pdf",
            side_effect=RuntimeError("boom"),
        ):
            result = extract_file_text(path)

        self.assertEqual(result["status"], "unreadable")
        self.assertIn("boom", result["error"])

    def test_a_genuinely_damaged_file_is_also_unreadable(self):
        # No mocking: a real, malformed PDF must be reported honestly
        # rather than surfacing as empty or invented content.
        path = self._write("broken.pdf", "not a real pdf at all")

        result = extract_file_text(path)

        self.assertEqual(result["status"], "unreadable")
        self.assertNotIn("text", result)


class PdfExtractionReusesExistingReaderTests(unittest.TestCase):
    """The PDF path must reuse services/pdf_reader.PDFReader (the same
    reader the Gmail evidence pipeline already uses), never a second
    implementation."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.path = os.path.join(self.temp_dir.name, "doc.pdf")
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("placeholder")

    def test_pdf_reader_result_is_relayed(self):
        with patch(
            "uri_core.services.pdf_reader.PDFReader.read_pdf",
            return_value={
                "success": True,
                "method": "OCR",
                "pages_found": 3,
                "text": "Scanned institutional content.",
            },
        ):
            result = extract_file_text(self.path)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["method"], "OCR")
        self.assertEqual(result["pages_found"], 3)
        self.assertIn("institutional", result["text"])

    def test_pdf_reader_failure_is_reported_not_invented(self):
        with patch(
            "uri_core.services.pdf_reader.PDFReader.read_pdf",
            return_value={"success": False, "error": "damaged file"},
        ):
            result = extract_file_text(self.path)

        self.assertEqual(result["status"], "unreadable")
        self.assertIn("damaged", result["error"])
        self.assertNotIn("text", result)


if __name__ == "__main__":
    unittest.main()
