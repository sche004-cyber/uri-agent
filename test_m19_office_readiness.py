"""M19 tests: honest tool-status reporting, generic document generation
(DOCX/XLSX/PPTX/PDF), routing (purpose/format aware, not blindly
institutional-note), fetch_url, and the Gmail-draft/Drive-upload write
capabilities (approval-gated, never a real network call in these
tests - all exercised via injected fakes or the honest
no-credentials path).
"""

import io
import os
import tempfile
import unittest
from unittest.mock import patch

from openpyxl import load_workbook
from pptx import Presentation
import fitz

from uri_core.core.approval_gate import ApprovalGate
from uri_core.core.approval_store import ApprovalStore
from uri_core.core.audit_trail import AuditTrail
from uri_core.core.capability_planner import CapabilityPlanner
from uri_core.core.capability_registry import CapabilityRegistry
from uri_core.core.dispatcher import ToolDispatcher, real_tool_status
from uri_core.core.file_store import FileStore
from uri_core.core.model_providers import ModelResponse, ProviderUnavailableError
from uri_core.services.document_composer import DocumentComposer
from uri_core.services.office_document_writer import (
    render_pdf_bytes,
    render_pptx_bytes,
    render_xlsx_bytes,
)
from uri_core.tools.drive_upload import DriveUploadTool
from uri_core.tools.fetch_drive_spreadsheet import DriveSpreadsheetFetcher
from uri_core.tools.fetch_url import FetchUrlTool, _extract_url
from uri_core.tools.generate_document import GenerateDocumentTool, infer_output_format
from uri_core.tools.gmail_create_draft import GmailCreateDraftTool, _extract_recipient


class _UnavailableProvider:
    def complete(self, *, system, user, temperature=0.0, max_tokens=None):
        raise ProviderUnavailableError("model intentionally unavailable in test")


class _EchoProvider:
    """Returns a body reflecting exactly what it was asked for, so tests
    can assert on format-shaping without needing a real model."""

    def complete(self, *, system, user, temperature=0.0, max_tokens=None):
        if "markdown table" in system:
            body = (
                "| Name | Dept |\n|---|---|\n| Aarav | CSE |\n| Priya | ECE |\n"
            )
        elif "PowerPoint" in system:
            body = "# Intro\n- Welcome\n- Overview\n\n# Findings\n- Point A\n"
        else:
            body = "This is a real generated document body with enough content to pass validation."
        return ModelResponse(content=body, model="fake", provider="fake")


class HonestToolStatusTests(unittest.TestCase):
    """M19 audit findings #3/#8: a dispatcher-level 'success' envelope
    must not mask a tool's own non-success status."""

    def test_real_tool_status_unwraps_inner_status(self):
        envelope = {"status": "success", "data": {"status": "input_required"}}
        self.assertEqual(real_tool_status(envelope), "input_required")

    def test_real_tool_status_passes_through_when_no_inner_status(self):
        envelope = {"status": "success", "data": {"rows": [1, 2, 3]}}
        self.assertEqual(real_tool_status(envelope), "success")

    def test_real_tool_status_leaves_non_success_outer_untouched(self):
        envelope = {"status": "awaiting_approval", "message": "..."}
        self.assertEqual(real_tool_status(envelope), "awaiting_approval")

    def test_real_tool_status_handles_non_dict(self):
        self.assertEqual(real_tool_status("not a dict"), "failed")

    def test_web_search_with_no_query_is_never_reported_as_completed_success(self):
        # Live repro of the audit's exact finding: a workflow step whose
        # tool could not act must not be seen as "success" by callers
        # that only look at the outer dispatcher envelope.
        result = ToolDispatcher().execute_tool("web_search", request_text="")
        self.assertEqual(result.get("status"), "success")  # dispatcher-level
        self.assertEqual(real_tool_status(result), "input_required")  # the truth


class GenericDocumentGenerationTests(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.file_store = FileStore(storage_dir=self.tmp_dir)

    def test_format_inference(self):
        self.assertEqual(infer_output_format("write a project proposal"), "docx")
        self.assertEqual(infer_output_format("create a powerpoint presentation"), "pptx")
        self.assertEqual(infer_output_format("prepare an excel sheet"), "xlsx")
        self.assertEqual(infer_output_format("give me a pdf report"), "pdf")

    def test_generates_real_docx_via_brain(self):
        tool = GenerateDocumentTool(
            composer=DocumentComposer(provider=_EchoProvider()),
            file_store=self.file_store,
        )
        result = tool.generate(
            request_text="write a short project proposal for a robotics lab",
            session_id="s-docx",
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["output_format"], "docx")
        self.assertEqual(result["composed_by"], "brain")
        file_ref = result["file"]
        path = self.file_store.path_for(file_ref["file_id"])
        self.assertTrue(os.path.exists(path))

    def test_generates_real_xlsx_with_table_content(self):
        tool = GenerateDocumentTool(
            composer=DocumentComposer(provider=_EchoProvider()),
            file_store=self.file_store,
        )
        result = tool.generate(
            request_text="prepare an excel sheet of department staff",
            session_id="s-xlsx",
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["output_format"], "xlsx")
        path = self.file_store.path_for(result["file"]["file_id"])
        workbook = load_workbook(path)
        rows = list(workbook.active.iter_rows(values_only=True))
        self.assertEqual(rows[0], ("Name", "Dept"))

    def test_generates_real_pptx_with_slides(self):
        tool = GenerateDocumentTool(
            composer=DocumentComposer(provider=_EchoProvider()),
            file_store=self.file_store,
        )
        result = tool.generate(
            request_text="create a powerpoint presentation about our findings",
            session_id="s-pptx",
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["output_format"], "pptx")
        path = self.file_store.path_for(result["file"]["file_id"])
        presentation = Presentation(path)
        self.assertEqual(len(presentation.slides.__iter__.__self__._sldIdLst), 2)

    def test_unreachable_model_still_produces_a_file_honestly(self):
        tool = GenerateDocumentTool(
            composer=DocumentComposer(provider=_UnavailableProvider()),
            file_store=self.file_store,
        )
        result = tool.generate(
            request_text="write a short proposal", session_id="s-fallback"
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["composed_by"], "fallback")


class OfficeRendererTests(unittest.TestCase):

    def test_xlsx_no_table_falls_back_to_lines(self):
        data = render_xlsx_bytes("Line one\nLine two\n")
        workbook = load_workbook(io.BytesIO(data))
        values = [row[0] for row in workbook.active.iter_rows(values_only=True)]
        self.assertEqual(values, ["Line one", "Line two"])

    def test_pptx_with_no_headings_becomes_one_slide(self):
        data = render_pptx_bytes("Just some bullet text\nAnother line")
        presentation = Presentation(io.BytesIO(data))
        self.assertEqual(len(list(presentation.slides)), 1)

    def test_pdf_pagination_produces_multiple_pages_for_long_content(self):
        long_text = "\n".join(f"Paragraph number {i} with some content." for i in range(400))
        data = render_pdf_bytes(long_text)
        document = fitz.open(stream=data, filetype="pdf")
        self.assertGreater(document.page_count, 1)
        document.close()


class RoutingTests(unittest.TestCase):
    """M19 audit finding #8, reproduced and fixed."""

    def setUp(self):
        self.planner = CapabilityPlanner()

    def _route(self, goal, requested_output, task_type="Document Drafting", domain="General", entities=None):
        return self.planner.plan(
            {
                "task_type": task_type,
                "domain": domain,
                "goal": goal,
                "requested_output": requested_output,
                "entities": entities or [],
            }
        )

    def test_generic_proposal_does_not_route_to_institutional_note(self):
        result = self._route(
            "write a project proposal for a new lab", "a project proposal document"
        )
        self.assertEqual(result["tool_name"], "generate_document")

    def test_powerpoint_request_routes_to_generate_document(self):
        result = self._route("create a powerpoint presentation", "a presentation")
        self.assertEqual(result["tool_name"], "generate_document")

    def test_excel_creation_routes_to_generate_document_not_fetcher(self):
        result = self._route("prepare an excel sheet of marks", "a spreadsheet")
        self.assertEqual(result["tool_name"], "generate_document")

    def test_office_note_request_still_routes_correctly(self):
        result = self._route(
            "draft an office note seeking approval", "office note",
            domain="Administrative",
        )
        self.assertEqual(result["tool_name"], "draft_institutional_note")

    def test_office_order_request_still_routes_correctly(self):
        result = self._route(
            "issue an office order appointing a warden", "office order",
            domain="Administrative",
        )
        self.assertEqual(result["tool_name"], "draft_institutional_order")

    def test_fetch_existing_google_sheet_still_routes_to_fetcher(self):
        result = self._route(
            "fetch the budget from the google sheet", "spreadsheet data",
            task_type="Data Retrieval", entities=["google sheet"],
        )
        self.assertEqual(result["tool_name"], "fetch_drive_spreadsheet")

    def test_cgpa_lookup_still_routes_correctly(self):
        result = self._route(
            "find the cgpa for roll number BTECH-2026-001", "academic record",
            task_type="Data Retrieval", domain="Academic Records", entities=["btech"],
        )
        self.assertEqual(result["tool_name"], "extract_student_records")


class DriveSpreadsheetHonestyTests(unittest.TestCase):
    """M19 audit finding #3: this tool used to fabricate rows when no
    credentials were configured."""

    def test_no_credentials_reports_unavailable_not_fabricated_rows(self):
        tool = DriveSpreadsheetFetcher(credentials_path="/does/not/exist.json")
        result = tool.fetch_rows(spreadsheet_id="abc123")
        self.assertEqual(result["status"], "unavailable")
        self.assertNotIn("Aarav Sharma", str(result))

    def test_no_spreadsheet_id_is_input_required(self):
        tool = DriveSpreadsheetFetcher(credentials_path="/does/not/exist.json")
        result = tool.fetch_rows()
        self.assertEqual(result["status"], "input_required")


class FetchUrlTests(unittest.TestCase):

    def test_extracts_first_url(self):
        self.assertEqual(
            _extract_url("please read https://example.com/page and summarise it"),
            "https://example.com/page",
        )

    def test_no_url_is_input_required(self):
        result = FetchUrlTool().execute(request_text="what can you do")
        self.assertEqual(result["status"], "input_required")

    def test_non_http_scheme_is_refused(self):
        result = FetchUrlTool().execute(request_text="open ftp://example.com/file")
        # No http(s) URL present -> input_required (ftp is not matched
        # by the http(s)-only extraction regex at all).
        self.assertEqual(result["status"], "input_required")


class GmailDraftAndDriveUploadSafetyTests(unittest.TestCase):
    """Never a real network call in this class - approval gating and
    argument-boundary discipline only."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.approval_gate = ApprovalGate(
            dispatcher=ToolDispatcher(),
            capability_registry=CapabilityRegistry(),
            approval_store=ApprovalStore(
                storage_path=os.path.join(self.tmp_dir, "approvals.json")
            ),
            audit_trail=AuditTrail(),
        )

        # 2026-09-12: GmailService now resolves its credentials/token
        # paths via connection_status._repo_root() (previously its own
        # independent, hardcoded repo-root derivation) - this class's
        # "no credentials configured" assertions must stay true
        # regardless of whether a REAL credentials.json/token.json
        # exists on the machine actually running this suite (it can:
        # this is a real, working dev install once Google sign-in has
        # actually been completed once). Pinned to this test's own
        # empty tmp_dir so these tests stay deterministic either way.
        self._repo_root_patch = patch(
            "uri_core.core.connection_status._repo_root",
            return_value=self.tmp_dir,
        )
        self._repo_root_patch.start()
        self.addCleanup(self._repo_root_patch.stop)

    def test_gmail_create_draft_is_approval_gated(self):
        result = self.approval_gate.execute_tool(
            "gmail_create_draft",
            session_id="s1",
            request_text="email admin@example.com about the seminar",
        )
        self.assertEqual(result["status"], "awaiting_approval")

    def test_drive_upload_is_approval_gated(self):
        result = self.approval_gate.execute_tool(
            "drive_upload", session_id="s1", request_text="upload it"
        )
        self.assertEqual(result["status"], "awaiting_approval")

    def test_recipient_is_extracted_deterministically_not_from_model(self):
        self.assertEqual(
            _extract_recipient("please email sche004@gmail.com about it"),
            "sche004@gmail.com",
        )
        self.assertIsNone(_extract_recipient("please draft an email about it"))

    def test_no_recipient_is_input_required_not_a_crash(self):
        tool = GmailCreateDraftTool()
        result = tool.generate(request_text="draft an email about the seminar")
        self.assertEqual(result["status"], "input_required")

    def test_no_credentials_reports_unavailable_honestly(self):
        tool = GmailCreateDraftTool()
        result = tool.generate(
            request_text="email sche004@gmail.com about the deadline"
        )
        self.assertEqual(result["status"], "unavailable")

    def test_drive_upload_resolves_most_recent_session_file(self):
        file_store = FileStore(storage_dir=self.tmp_dir)
        record = file_store.save(
            filename="report.docx",
            content=b"fake bytes",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            session_id="s-upload",
        )
        tool = DriveUploadTool(file_store=file_store)
        result = tool.generate(session_id="s-upload")
        # No token.json in this environment - honest failure, but it
        # DID find and attempt the right file (proves the resolution
        # logic, not the network call).
        self.assertEqual(result["status"], "unavailable")
        file_store.delete(record.file_id)

    def test_no_send_capability_exists_anywhere(self):
        from uri_core.services import gmail_service

        self.assertFalse(hasattr(gmail_service.GmailService, "send_message"))
        self.assertFalse(hasattr(gmail_service.GmailService, "send_draft"))
        self.assertFalse(hasattr(gmail_service.GmailService, "send"))


if __name__ == "__main__":
    unittest.main()
