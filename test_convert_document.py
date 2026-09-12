"""ConvertDocumentTool (2026-09-12): PDF -> DOCX conversion of an
already-attached file. Unit-level, with PDFReader/DocumentWriterService
mocked (no real PDF/OCR dependency needed to prove the tool's own
control flow: attachment lookup, format detection, error paths, and
FileStore threading)."""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from uri_core.core.file_store import FileStore
from uri_core.tools.convert_document import ConvertDocumentTool


class ConvertDocumentToolTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.file_store = FileStore(storage_dir=self.temp_dir.name)
        self.tool = ConvertDocumentTool(file_store=self.file_store)

    def _attach_pdf(self, session_id="s1", filename="Resume.pdf"):
        return self.file_store.save(
            filename=filename,
            content=b"%PDF-1.4 fake bytes",
            media_type="application/pdf",
            session_id=session_id,
        )

    def test_no_attachment_asks_for_one(self):
        result = self.tool.convert(
            session_id="s1", request_text="convert this to word"
        )
        self.assertEqual(result["status"], "input_required")

    def test_unsupported_output_format_is_honest(self):
        self._attach_pdf()
        result = self.tool.convert(
            session_id="s1", requested_output="excel spreadsheet"
        )
        self.assertEqual(result["status"], "not_implemented")

    @patch("uri_core.tools.convert_document.DocumentWriterService")
    @patch("uri_core.tools.convert_document.PDFReader")
    def test_successful_conversion_stores_a_real_docx(
        self, mock_reader_cls, mock_writer_cls
    ):
        self._attach_pdf()
        mock_reader_cls.return_value.read_pdf.return_value = {
            "success": True,
            "text": "Real extracted resume text.",
        }
        mock_writer_cls.return_value.render_docx_bytes.return_value = b"docx-bytes"

        result = self.tool.convert(
            session_id="s1", request_text="convert this into a word file"
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["output_format"], "docx")
        self.assertTrue(result["file"]["filename"].endswith(".docx"))

        stored_path = self.file_store.path_for(result["file"]["file_id"])
        self.assertIsNotNone(stored_path)
        with open(stored_path, "rb") as handle:
            self.assertEqual(handle.read(), b"docx-bytes")

    @patch("uri_core.tools.convert_document.PDFReader")
    def test_extraction_failure_is_reported_not_raised(self, mock_reader_cls):
        self._attach_pdf()
        mock_reader_cls.return_value.read_pdf.return_value = {
            "success": False,
            "error": "corrupt PDF",
        }

        result = self.tool.convert(
            session_id="s1", requested_output="docx"
        )

        self.assertEqual(result["status"], "error")
        self.assertIn("corrupt PDF", result["message"])

    @patch("uri_core.tools.convert_document.DocumentWriterService")
    @patch("uri_core.tools.convert_document.PDFReader")
    def test_modification_instruction_revises_the_text_via_the_composer(
        self, mock_reader_cls, mock_writer_cls
    ):
        self._attach_pdf()
        mock_reader_cls.return_value.read_pdf.return_value = {
            "success": True,
            "text": "Salary: 50000",
        }
        mock_writer_cls.return_value.render_docx_bytes.side_effect = (
            lambda text: text.encode()
        )
        fake_composer = MagicMock()
        fake_composer.compose.return_value = {"body": "Salary: 90000"}
        tool = ConvertDocumentTool(
            file_store=self.file_store, composer=fake_composer
        )

        result = tool.convert(
            session_id="s1",
            request_text="convert this to word and update my salary to 90000",
        )

        self.assertEqual(result["status"], "success")
        self.assertTrue(result["edited"])
        stored_path = self.file_store.path_for(result["file"]["file_id"])
        with open(stored_path, "rb") as handle:
            self.assertEqual(handle.read(), b"Salary: 90000")

    @patch("uri_core.tools.convert_document.DocumentWriterService")
    @patch("uri_core.tools.convert_document.PDFReader")
    def test_a_failed_edit_still_produces_the_unedited_conversion(
        self, mock_reader_cls, mock_writer_cls
    ):
        self._attach_pdf()
        mock_reader_cls.return_value.read_pdf.return_value = {
            "success": True,
            "text": "Salary: 50000",
        }
        mock_writer_cls.return_value.render_docx_bytes.side_effect = (
            lambda text: text.encode()
        )
        fake_composer = MagicMock()
        fake_composer.compose.side_effect = RuntimeError("model unreachable")
        tool = ConvertDocumentTool(
            file_store=self.file_store, composer=fake_composer
        )

        result = tool.convert(
            session_id="s1",
            request_text="convert this to word and update my salary to 90000",
        )

        self.assertEqual(result["status"], "success")
        self.assertFalse(result["edited"])
        stored_path = self.file_store.path_for(result["file"]["file_id"])
        with open(stored_path, "rb") as handle:
            self.assertEqual(handle.read(), b"Salary: 50000")

    @patch("uri_core.tools.convert_document.DocumentWriterService")
    @patch("uri_core.tools.convert_document.PDFReader")
    def test_plain_conversion_with_no_modification_verb_is_unedited(
        self, mock_reader_cls, mock_writer_cls
    ):
        self._attach_pdf()
        mock_reader_cls.return_value.read_pdf.return_value = {
            "success": True,
            "text": "Original text.",
        }
        mock_writer_cls.return_value.render_docx_bytes.return_value = b"docx-bytes"
        fake_composer = MagicMock()
        tool = ConvertDocumentTool(
            file_store=self.file_store, composer=fake_composer
        )

        result = tool.convert(session_id="s1", request_text="convert this to word")

        self.assertFalse(result["edited"])
        fake_composer.compose.assert_not_called()


if __name__ == "__main__":
    unittest.main()
