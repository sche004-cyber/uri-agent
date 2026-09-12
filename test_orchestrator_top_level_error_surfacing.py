"""2026-09-12 (User directive): a dispatched tool's own real error/
input_required/not_implemented message must reach the top-level
result["error"] field - the one field http_uri_client.dart's failed-
turn rendering actually reads - not be silently replaced by a
content-free generic client-side string.

Root cause this guards against: orchestrator.py's capability_selected
branch set response["status"]="failed" on a real tool error but never
set response["error"] alongside it, even though the tool's own message
was sitting right there in response["response"]["message"].
"""

import json
import os
import tempfile
import unittest

from uri_core.core.approval_gate import ApprovalGate
from uri_core.core.audit_trail import AuditTrail
from uri_core.core.capability_registry import CapabilityRegistry
from uri_core.core.model_reasoning_gateway import ModelReasoningGateway
from uri_core.core.orchestrator import UriOrchestrator
from uri_core.core.skill_memory import SkillMemory
from uri_core.core.state import SessionManager


class _FixedSemanticInterpreter:
    def __init__(self, result: dict):
        self._result = result

    def interpret(self, user_text: str) -> dict:
        return self._result


class _FakeDispatcher:
    def __init__(self, tool_result: dict):
        self._tool_result = tool_result

    def execute_tool(self, tool_name, **kwargs):
        return {"status": "success", "data": self._tool_result}


def _write_registry(path, active_tools):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"active_tools": active_tools}, f)


SEMANTIC_RESULT = {
    "goal": "convert the attached pdf to word",
    "task_type": "document conversion",
    "domain": "office",
    "requested_output": "docx",
    "entities": [],
}


class TopLevelErrorSurfacingTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.registry_path = os.path.join(self.temp_dir.name, "registry.json")
        _write_registry(
            self.registry_path,
            {
                "convert_document": {
                    "file_path": "uri_core.tools.convert_document",
                    "class_name": "ConvertDocumentTool",
                    "method": "convert",
                    "status": "implemented",
                    "availability": "available",
                }
            },
        )
        self.capability_registry = CapabilityRegistry(
            registry_path=self.registry_path
        )

    def _orchestrator(self, tool_result: dict) -> UriOrchestrator:
        gateway = ModelReasoningGateway(
            registry_path=self.registry_path,
            model_callable=lambda request_json: json.dumps(
                {"action": {"capability": "convert_document"}}
            ),
        )
        dispatcher = _FakeDispatcher(tool_result)
        orchestrator = UriOrchestrator(
            semantic_interpreter=_FixedSemanticInterpreter(SEMANTIC_RESULT),
            model_reasoning_gateway=gateway,
            capability_registry=self.capability_registry,
            enable_model_reasoning_shadow=True,
            enable_skill_router_shadow=False,
            enable_response_narrative=False,
            session_manager=SessionManager(
                storage_path=os.path.join(self.temp_dir.name, "sessions")
            ),
        )
        orchestrator.approval_gate = ApprovalGate(
            dispatcher=dispatcher,
            capability_registry=self.capability_registry,
            audit_trail=AuditTrail(),
        )
        orchestrator.skill_memory = SkillMemory(
            storage_path=os.path.join(self.temp_dir.name, "skill_memory.json")
        )
        orchestrator.skill_memory.find_matching_skill = (
            lambda semantic_result: None
        )
        orchestrator._should_run_pre_execution_sanity_check = (
            lambda **kwargs: False
        )
        return orchestrator

    def test_tool_error_message_reaches_top_level_error_field(self):
        orchestrator = self._orchestrator(
            {
                "status": "error",
                "message": "URI could not read the attached PDF: corrupt file",
            }
        )

        result = orchestrator.process_user_input(
            session_id="s1", user_text="convert the attached pdf to word"
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(
            result["error"],
            "URI could not read the attached PDF: corrupt file",
        )

    def test_tool_input_required_message_also_reaches_top_level_error_field(self):
        orchestrator = self._orchestrator(
            {
                "status": "input_required",
                "message": "URI needs a PDF attached to this conversation to convert.",
            }
        )

        result = orchestrator.process_user_input(
            session_id="s2", user_text="convert the attached pdf to word"
        )

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(
            result["error"],
            "URI needs a PDF attached to this conversation to convert.",
        )


if __name__ == "__main__":
    unittest.main()
