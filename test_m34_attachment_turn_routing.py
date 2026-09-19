"""M34 attachment-turn candidate exposure: explicit current-turn state only."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from uri_core.app.server import AskRequest, _current_turn_attachment_references
from uri_core.core.canonical_execution import _execute_legacy_capability
from uri_core.core.decision_engine import build_decision_request, preselect_candidate_ids
from uri_core.core.model_providers.base import ModelResponse
from uri_core.core.native_tool_loop import run_native_tool_loop
from uri_core.core.turn_state import assemble_turn_state


class _Directory:
    def summaries(self):
        return [
            {"capability_id": "Gmail", "summary": "Email search", "actions": [], "reads_current_attachments": False},
            {"capability_id": "read_attached_file", "summary": "Read an attachment", "actions": [], "reads_current_attachments": True},
        ]


class AttachmentTurnStateTests(unittest.TestCase):
    def test_empty_current_turn_attachments_are_omitted(self):
        state = assemble_turn_state(user_text="check Gmail", session_id="s1", current_turn_attachments=[]).data
        self.assertNotIn("current_turn_attachments", state)

    def test_explicit_current_turn_attachment_is_projected(self):
        reference = {"file_id": "f1", "filename": "report.pdf", "media_type": "application/pdf", "size_bytes": 10}
        state = assemble_turn_state(user_text="summarize this", session_id="s1", current_turn_attachments=[reference]).data
        self.assertEqual(state["current_turn_attachments"], [reference])

    def test_decision_request_omits_empty_attachment_context(self):
        state = assemble_turn_state(user_text="check Gmail", session_id="s1").data
        self.assertNotIn("current_turn_attachments", build_decision_request(state))

    def test_decision_request_contains_explicit_attachment_context(self):
        reference = {"file_id": "f1", "filename": "report.pdf"}
        state = assemble_turn_state(
            user_text="summarize this", session_id="s1",
            current_turn_attachments=[reference],
        ).data
        self.assertEqual(
            build_decision_request(state)["current_turn_attachments"], [reference]
        )

    def test_attachment_reader_is_included_without_lexical_match(self):
        directory = _Directory()
        state = {
            "turn": {"user_text": "summarize this"},
            "active_pointer": {"capability_id": None},
            "current_turn_attachments": [{"file_id": "f1"}],
        }
        with patch(
            "uri_core.core.decision_engine.plausible_matches",
            return_value=[{"capability": "Gmail"}],
        ):
            candidates = preselect_candidate_ids(state, directory, limit=5)
        self.assertEqual(candidates, ["Gmail", "read_attached_file"])

    def test_old_session_file_is_not_a_candidate_signal_without_explicit_id(self):
        directory = _Directory()
        state = {"turn": {"user_text": "check Gmail"}, "active_pointer": {"capability_id": None}}
        with patch(
            "uri_core.core.decision_engine.plausible_matches",
            return_value=[{"capability": "Gmail"}],
        ):
            baseline = preselect_candidate_ids(state, directory, limit=5)
        # An old stored file cannot add a current-turn field or alter this
        # surface: only explicit AskRequest ids activate reader inclusion.
        self.assertNotIn("current_turn_attachments", state)
        self.assertEqual(baseline, ["Gmail"])


class AttachmentHandleValidationTests(unittest.TestCase):
    def _context(self, records):
        class _Store:
            def get(self, file_id):
                return records.get(file_id)

        return SimpleNamespace(file_store=_Store())

    def test_explicit_handle_is_projected_only_for_matching_session(self):
        reference = {"file_id": "f1", "filename": "report.pdf"}
        record = SimpleNamespace(session_id="s1", to_reference=lambda: reference)
        payload = AskRequest(session_id="s1", text="summarize this", attached_file_ids=["f1"])
        self.assertEqual(
            _current_turn_attachment_references(self._context({"f1": record}), payload),
            [reference],
        )

    def test_old_client_request_omits_attachment_handles(self):
        payload = AskRequest(session_id="s1", text="check Gmail")
        self.assertEqual(payload.attached_file_ids, [])
        self.assertEqual(_current_turn_attachment_references(self._context({}), payload), [])

    def test_cross_session_or_unknown_handle_fails_closed(self):
        record = SimpleNamespace(session_id="other-session", to_reference=lambda: {"file_id": "f1"})
        payload = AskRequest(session_id="s1", text="summarize this", attached_file_ids=["f1"])
        with self.assertRaises(HTTPException) as raised:
            _current_turn_attachment_references(self._context({"f1": record}), payload)
        self.assertEqual(raised.exception.status_code, 400)

    def test_blank_unknown_and_excessive_handles_fail_closed_at_ask_boundary(self):
        context = self._context({})
        for ids in ([""], ["unknown"], ["f1"] * 21):
            payload = AskRequest(session_id="s1", text="summarize this", attached_file_ids=ids)
            with self.assertRaises(HTTPException) as raised:
                _current_turn_attachment_references(context, payload)
            self.assertEqual(raised.exception.status_code, 400)


class NativeAttachmentContextTests(unittest.TestCase):
    def test_native_loop_exposes_the_validated_turn_projection_to_model(self):
        observed = {}

        def model(**kwargs):
            observed.update(kwargs)
            return ModelResponse(content="I can inspect it.", model="fake", provider="fake", tool_calls=())

        turn_state = SimpleNamespace(data={
            "current_turn_attachments": [{"file_id": "f1", "filename": "report.pdf"}]
        })
        orchestrator = SimpleNamespace(multi_action_dispatch=SimpleNamespace(registry=None))
        with patch(
            "uri_core.core.native_tool_loop.build_turn_state_and_directory",
            return_value=(turn_state, object()),
        ), patch("uri_core.core.native_tool_loop.build_tool_schemas", return_value=[]):
            result = run_native_tool_loop(
                orchestrator=orchestrator, session_id="s1", user_text="summarize this",
                principal=None, model_callable=model, capability_registry=object(),
                current_turn_attachments=turn_state.data["current_turn_attachments"],
            )
        self.assertEqual(result["tier"], "tier0")
        self.assertIn('"file_id": "f1"', observed["user"])


class CanonicalAttachmentDispatchTests(unittest.TestCase):
    def test_canonical_dispatch_passes_runtime_attachment_ids_not_action_inputs(self):
        captured = {}

        class _Gate:
            def execute_tool(self, capability, **kwargs):
                captured["capability"] = capability
                captured.update(kwargs)
                return {"status": "success", "data": {"status": "success"}}

        contract = {
            "capability": "read_attached_file",
            "actions": [{"name": "read_attached_file", "inputs": {"file_id": "model-id"}}],
        }
        _execute_legacy_capability(
            contract, orchestrator=SimpleNamespace(approval_gate=_Gate()), session_id="s1",
            user_text="summarize this", principal=None,
            current_turn_attachment_ids=["validated-id"],
        )
        self.assertEqual(captured["current_turn_attachment_ids"], ["validated-id"])
        self.assertNotIn("file_id", captured)


if __name__ == "__main__":
    unittest.main()
