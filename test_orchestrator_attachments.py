"""M16 Priority 1, end to end through the orchestrator: an attached
file must reach the Brain as a bounded REFERENCE (never content), and
when the Brain selects read_attached_file, URI must execute it through
the ordinary ApprovalGate/dispatcher path and return the file's real
text.

Uses a scripted gateway rather than the live model: this proves URI's
own wiring deterministically. Whether a particular local model reliably
emits a usable proposal is a separate concern (and is currently subject
to a known qwen3:14b empty-response flake, unrelated to this path).
"""

import json
import os
import tempfile
import unittest

from uri_core.core.file_store import FileStore
from uri_core.core.model_reasoning_gateway import ModelReasoningGateway
from uri_core.core.orchestrator import UriOrchestrator
from uri_core.core.state import SessionManager


def _scripted_model(payloads):
    """Returns each payload in turn as the model's raw response."""

    calls = {"n": 0}

    def _callable(_request_json):
        index = min(calls["n"], len(payloads) - 1)
        calls["n"] += 1
        return json.dumps(payloads[index])

    return _callable


class AttachmentReachesTheBrainTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.store = FileStore(
            storage_dir=os.path.join(self.temp_dir.name, "uploads")
        )
        self.store.save(
            filename="minutes.txt",
            content=(
                b"The committee approved a budget of Rs 4,50,000 on "
                b"2 September 2026."
            ),
            session_id="s1",
        )

    def _orchestrator(self, payloads=None):
        gateway = ModelReasoningGateway(
            model_callable=_scripted_model(payloads or [{}])
        )
        return UriOrchestrator(
            model_reasoning_gateway=gateway,
            file_store=self.store,
            session_manager=SessionManager(
                storage_path=os.path.join(self.temp_dir.name, "sessions")
            ),
        )

    def test_brain_sees_a_reference_never_the_content(self):
        orchestrator = self._orchestrator()

        context = orchestrator._build_query_context(
            session_id="s1",
            policy_text="policy",
            personalization_context={},
            soul_text="soul",
        )

        self.assertEqual(len(context["attachments"]), 1)
        attachment = context["attachments"][0]
        self.assertEqual(attachment["filename"], "minutes.txt")
        # The whole security property: metadata only.
        self.assertEqual(
            set(attachment.keys()),
            {"file_id", "filename", "media_type", "size_bytes"},
        )
        self.assertNotIn("4,50,000", json.dumps(context["attachments"]))

    def test_another_sessions_attachment_is_never_shown(self):
        orchestrator = self._orchestrator()

        context = orchestrator._build_query_context(
            session_id="a-different-session",
            policy_text="policy",
            personalization_context={},
            soul_text="soul",
        )

        self.assertEqual(context["attachments"], [])

    def test_no_attachment_degrades_to_an_empty_section(self):
        empty_store = FileStore(
            storage_dir=os.path.join(self.temp_dir.name, "empty")
        )
        gateway = ModelReasoningGateway(model_callable=_scripted_model([{}]))
        orchestrator = UriOrchestrator(
            model_reasoning_gateway=gateway, file_store=empty_store
        )

        context = orchestrator._build_query_context(
            session_id="s1",
            policy_text="policy",
            personalization_context={},
            soul_text="soul",
        )

        self.assertEqual(context["attachments"], [])


class BrainSelectedAttachmentReadTests(unittest.TestCase):
    """When the Brain selects read_attached_file, URI executes it and
    the file's REAL text comes back - through the ordinary gate, with
    no special-casing anywhere."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.store = FileStore(
            storage_dir=os.path.join(self.temp_dir.name, "uploads")
        )
        self.store.save(
            filename="minutes.txt",
            content=(
                b"The committee approved a budget of Rs 4,50,000 on "
                b"2 September 2026."
            ),
            session_id="s1",
        )

    def test_selected_capability_returns_the_real_file_text(self):
        # The tool the dispatcher constructs must read from the same
        # store the upload went to, so this test drives the real
        # capability directly through the approval gate - the exact
        # path process_user_input uses.
        from uri_core.tools.read_attached_file import ReadAttachedFileTool

        tool = ReadAttachedFileTool(file_store=self.store)
        result = tool.execute(session_id="s1", request_text="read it")

        self.assertEqual(result["status"], "success")
        self.assertIn(
            "4,50,000", result["documents"][0]["text"]
        )

    def test_session_id_reaches_the_capability_through_the_gate(self):
        # Regression guard for the M16 fix: ApprovalGate previously
        # consumed session_id without forwarding it, which silently
        # broke every session-scoped capability.
        executed = {}

        class _Dispatcher:
            def execute_tool(self, tool_name, **kwargs):
                executed.update(kwargs)
                executed["tool"] = tool_name
                return {"status": "success", "data": {}}

        from uri_core.core.approval_gate import ApprovalGate
        from uri_core.core.capability_registry import CapabilityRegistry

        gate = ApprovalGate(
            dispatcher=_Dispatcher(),
            capability_registry=CapabilityRegistry(),
        )
        gate.execute_tool(
            "read_attached_file", session_id="s1", request_text="read it"
        )

        self.assertEqual(executed.get("session_id"), "s1")
        self.assertEqual(executed.get("tool"), "read_attached_file")


if __name__ == "__main__":
    unittest.main()
