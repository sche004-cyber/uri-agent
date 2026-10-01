import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from uri_core.services.pdf_layout_converter import inspect_docx_editability
from uri_core.tools.convert_document import ConvertDocumentTool
from uri_core.core.file_store import FileStore


def _docx(path: Path, document_xml: str, *, with_image: bool = False) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document_xml)
        if with_image:
            archive.writestr("word/media/image1.png", b"png")


class DocxTruthfulnessTests(unittest.TestCase):
    def test_raster_only_docx_is_not_editable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scan.docx"
            _docx(
                path,
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p/></w:body></w:document>',
                with_image=True,
            )
            result = inspect_docx_editability(str(path))
            self.assertFalse(result["editable"])
            self.assertEqual(result["images"], 1)
            self.assertEqual(result["editable_text_chars"], 0)

    def test_text_paragraphs_and_table_cells_are_editable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "text.docx"
            _docx(
                path,
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Hello</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Cell</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>',
            )
            result = inspect_docx_editability(str(path))
            self.assertTrue(result["editable"])
            self.assertGreaterEqual(result["paragraphs"], 2)
            self.assertEqual(result["table_cells"], 1)

    @patch("uri_core.tools.convert_document.convert_pdf_to_docx_preserving_layout")
    @patch("uri_core.tools.convert_document.PDFReader")
    def test_scanned_pdf_does_not_create_or_claim_editable_output(
        self, reader_cls, layout_convert
    ):
        with tempfile.TemporaryDirectory() as directory:
            store = FileStore(storage_dir=directory)
            store.save(
                filename="scan.pdf", content=b"%PDF scan",
                media_type="application/pdf", session_id="s1",
            )
            layout_convert.return_value = {
                "status": "error", "error_code": "no_editable_content",
                "message": "no editable content",
            }
            reader_cls.return_value.read_pdf.return_value = {
                "success": True, "method": "OCR", "text": "recognized text",
            }
            result = ConvertDocumentTool(file_store=store).convert(
                session_id="s1", request_text="convert this to Word"
            )
            self.assertEqual(result["status"], "unavailable")
            self.assertFalse(result["editable"])
            self.assertTrue(result["ocr_required"])
            self.assertEqual(len(store.list_for_session("s1")), 1)


class LmStudioVerificationTests(unittest.TestCase):
    @patch("uri_core.core.provider_keys.ProviderKeyStore")
    @patch("uri_core.core.provider_registry.ProviderConfigStore")
    @patch("uri_core.core.model_providers.OpenAICompatibleProvider")
    def test_lm_studio_discovers_and_verifies_without_api_key(
        self, provider_cls, config_store_cls, key_store_cls
    ):
        from uri_core.app import server

        server._verified_models_cache.clear()
        config_store_cls.return_value.get_provider_config.return_value = {
            "base_url": "http://127.0.0.1:1234"
        }
        key_store_cls.return_value.has_key.return_value = False
        provider = provider_cls.return_value
        provider.list_models.return_value = ["local/model-a"]
        provider.complete.return_value = MagicMock(content="OK")

        result = server.verify_provider("lm_studio", user_id="u-lm")

        self.assertTrue(result["verified"])
        self.assertEqual(result["verified_models"], ["local/model-a"])
        for call in provider_cls.call_args_list:
            self.assertIsNone(call.kwargs.get("api_key"))
            self.assertLessEqual(call.args[0].timeout_seconds, 5.0)
            self.assertEqual(call.args[0].base_url, "http://127.0.0.1:1234/v1")


class NeedleCanonicalWiringTests(unittest.TestCase):
    def _context(self):
        context = MagicMock()
        context.orchestrator.capability_feasibility.usable_ids.return_value = {
            "gmail_search"
        }
        context.orchestrator.approval_gate.execute_tool.return_value = {
            "status": "success",
            "data": {"status": "success", "messages": []},
        }
        return context

    @patch("uri_core.app.server._get_needle_bridge")
    @patch("uri_core.app.server._edge_settings_for_principal")
    def test_valid_proposal_crosses_uri_approval_gate_without_model_arguments(
        self, settings_store, get_bridge
    ):
        from uri_core.app import server

        settings_store.return_value.load.return_value = MagicMock(
            enabled=True,
            intelligence_mode="HYBRID",
            reply_confidence_threshold_percent=90,
        )
        get_bridge.return_value.return_value = {
            "capability_id": "Gmail.search_messages",
            "arguments": {"query": "model supplied and untrusted"},
            "score": 0.99,
            "provider_latency_ms": 12.4,
        }
        context = self._context()
        principal = MagicMock(user_id="u1")
        payload = MagicMock(
            text="show unread mail", session_id="s1", model_override=None
        )

        result, trace = server._edge_route_for_ask(
            context=context,
            principal=principal,
            payload=payload,
            current_turn_attachments=[],
            personalization_context=None,
        )

        self.assertEqual(trace["disposition"], "NEEDLE_INVOKED")
        self.assertEqual(result["execution"]["capability"], "gmail_search")
        _, kwargs = context.orchestrator.approval_gate.execute_tool.call_args
        self.assertEqual(kwargs["request_text"], "show unread mail")
        self.assertNotIn("query", kwargs)

    @patch("uri_core.app.server._get_needle_bridge")
    @patch("uri_core.app.server._edge_settings_for_principal")
    def test_low_confidence_proposal_escalates_without_execution(
        self, settings_store, get_bridge
    ):
        from uri_core.app import server

        settings_store.return_value.load.return_value = MagicMock(
            enabled=True,
            intelligence_mode="HYBRID",
            reply_confidence_threshold_percent=90,
        )
        get_bridge.return_value.return_value = {
            "capability_id": "Gmail.search_messages",
            "arguments": {},
            "score": 0.40,
            "provider_latency_ms": 10,
        }
        context = self._context()
        result, trace = server._edge_route_for_ask(
            context=context,
            principal=MagicMock(user_id="u1"),
            payload=MagicMock(text="search mail", session_id="s1", model_override=None),
            current_turn_attachments=[],
            personalization_context=None,
        )
        self.assertIsNone(result)
        self.assertEqual(trace["disposition"], "NEEDLE_ESCALATED")
        context.orchestrator.approval_gate.execute_tool.assert_not_called()


class RoutingTracePersistenceTests(unittest.TestCase):
    @patch("uri_core.core.edge.trace.EdgeRoutingTraceStore")
    @patch("uri_core.app.server._serving_model_for_turn")
    def test_finalizer_records_explicit_needle_disposition(
        self, serving_model, trace_store_cls
    ):
        from uri_core.app import server

        serving_model.return_value = {
            "provider_id": "ollama",
            "model": "qwen3.5:9b",
            "prompt_tokens": 10,
            "eval_tokens": 2,
            "duration_seconds": 0.25,
        }
        context = MagicMock()
        payload = MagicMock(session_id="s1", model_override=None)
        result = {
            "status": "success",
            "session_id": "s1",
            "response": {"message": "OK"},
            "_edge_routing": {
                "disposition": "NEEDLE_BYPASSED",
                "reason_codes": ("EXPLICIT_MODEL_OVERRIDE",),
                "latency_ms": 3,
            },
        }

        server._finalize_ask_response(
            context, "u1", payload, result, total_duration_seconds=0.5
        )

        event = trace_store_cls.return_value.record.call_args.args[0]
        self.assertEqual(event.decision, "NEEDLE_BYPASSED")
        self.assertEqual(event.latency_ms["total"], 500)


if __name__ == "__main__":
    unittest.main()
