"""Proves the Issue-1 fix: a learned skill only ever accelerates tool
SELECTION - it must never substitute for actually executing the tool,
and must still go through approval when required. No Ollama/network
involved - semantic_interpreter and skill_memory are both controlled
directly."""

import json
import os
import tempfile
import unittest

from uri_core.core.approval_gate import ApprovalGate
from uri_core.core.approval_store import ApprovalStore
from uri_core.core.capability_registry import CapabilityRegistry
from uri_core.core.orchestrator import UriOrchestrator


class _FixedSemanticInterpreter:
    def __init__(self, result: dict):
        self._result = result

    def interpret(self, user_text: str) -> dict:
        return self._result


class _FakeSkillMemory:
    """A skill_memory double that always reports a match - the
    learned_skill branch's own concern (matching heuristics) is
    skill_memory.py's job, already tested elsewhere; this test suite
    is only about what happens once a match IS found."""

    def __init__(self, tool_name: str, success_count: int = 1):
        self.matched = {
            "task_type": "document drafting",
            "domain": "administrative",
            "tool_name": tool_name,
            "workflow": ["interpret_request", f"execute_{tool_name}"],
            "success_count": success_count,
        }
        self.learn_skill_calls = []

    def find_matching_skill(self, semantic_result):
        return dict(self.matched)

    def learn_skill(self, semantic_result, workflow, tool_name=None):
        self.learn_skill_calls.append(tool_name)
        self.matched["success_count"] += 1


SEMANTIC_RESULT = {
    "task_type": "document drafting",
    "domain": "administrative",
    "goal": "prepare a note",
    "requested_output": "office note",
    "entities": ["office note"],
}


def _orchestrator_with_temp_registry(entries: dict, skill_memory):
    temp_dir = tempfile.TemporaryDirectory()
    registry_path = os.path.join(
        temp_dir.name, "capabilities_registry.json"
    )
    with open(registry_path, "w", encoding="utf-8") as file:
        json.dump({"active_tools": entries}, file)

    capability_registry = CapabilityRegistry(registry_path=registry_path)
    approval_store = ApprovalStore(
        storage_path=os.path.join(temp_dir.name, "approvals.json")
    )

    orchestrator = UriOrchestrator(
        semantic_interpreter=_FixedSemanticInterpreter(SEMANTIC_RESULT),
        enable_model_reasoning_shadow=False,
        enable_skill_router_shadow=False,
    )
    orchestrator.skill_memory = skill_memory
    orchestrator.capability_planner.registry_path = registry_path
    orchestrator.capability_planner.capability_registry = (
        capability_registry
    )
    orchestrator.dispatcher.registry_path = registry_path
    orchestrator.capability_registry = capability_registry
    orchestrator.approval_gate = ApprovalGate(
        dispatcher=orchestrator.dispatcher,
        capability_registry=capability_registry,
        approval_store=approval_store,
        audit_trail=orchestrator.audit_trail,
    )

    return orchestrator, temp_dir


class LearnedSkillGenuinelyExecutesTests(unittest.TestCase):

    def test_learned_skill_actually_calls_the_dispatcher(self):
        skill_memory = _FakeSkillMemory("draft_institutional_note")
        orchestrator, temp_dir = _orchestrator_with_temp_registry(
            {
                "draft_institutional_note": {
                    "file_path": (
                        "uri_core/tools/draft_institutional_note.py"
                    ),
                    "class_name": "InstitutionalNoteDraftCmp",
                    "method": "generate",
                    "approval_requirement": "none",
                }
            },
            skill_memory,
        )
        self.addCleanup(temp_dir.cleanup)

        result = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        # Real execution happened - not the old fake "recognized"
        # message. The real tool actually ran and produced real
        # output.
        self.assertEqual(result["execution"]["status"], "success")
        self.assertEqual(result["execution"]["tool"], "draft_institutional_note")
        self.assertIn("note_sheet", result["response"])
        self.assertNotEqual(result["execution"]["status"], "workflow_recalled")

    def test_learned_skill_for_an_approval_required_capability_still_gates(
        self,
    ):
        skill_memory = _FakeSkillMemory("draft_institutional_note")
        orchestrator, temp_dir = _orchestrator_with_temp_registry(
            {
                "draft_institutional_note": {
                    "file_path": (
                        "uri_core/tools/draft_institutional_note.py"
                    ),
                    "class_name": "InstitutionalNoteDraftCmp",
                    "method": "generate",
                    "approval_requirement": "user_approval_required",
                }
            },
            skill_memory,
        )
        self.addCleanup(temp_dir.cleanup)

        result = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        # A "learned" capability that requires approval must still be
        # gated - "learned" never bypasses "approved".
        self.assertEqual(
            result["execution"]["status"], "awaiting_approval"
        )
        self.assertIn("action_id", result["response"])

    def test_repeated_calls_each_genuinely_re_execute(self):
        skill_memory = _FakeSkillMemory("draft_institutional_note")
        orchestrator, temp_dir = _orchestrator_with_temp_registry(
            {
                "draft_institutional_note": {
                    "file_path": (
                        "uri_core/tools/draft_institutional_note.py"
                    ),
                    "class_name": "InstitutionalNoteDraftCmp",
                    "method": "generate",
                    "approval_requirement": "none",
                }
            },
            skill_memory,
        )
        self.addCleanup(temp_dir.cleanup)

        first = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )
        second = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        self.assertEqual(first["execution"]["status"], "success")
        self.assertEqual(second["execution"]["status"], "success")
        self.assertIn("note_sheet", first["response"])
        self.assertIn("note_sheet", second["response"])

    def test_stale_learned_tool_name_surfaces_the_real_dispatcher_error(
        self,
    ):
        # The learned skill points at a tool_name no longer in the
        # registry - must surface the dispatcher's real error, never
        # a false "recognized" success.
        skill_memory = _FakeSkillMemory("a_tool_that_no_longer_exists")
        orchestrator, temp_dir = _orchestrator_with_temp_registry(
            {}, skill_memory
        )
        self.addCleanup(temp_dir.cleanup)

        result = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        self.assertEqual(result["execution"]["status"], "error")
        self.assertIn(
            "lacks the capability", result["response"]["message"]
        )

    def test_successful_learned_execution_still_bumps_success_count(
        self,
    ):
        skill_memory = _FakeSkillMemory(
            "draft_institutional_note", success_count=3
        )
        orchestrator, temp_dir = _orchestrator_with_temp_registry(
            {
                "draft_institutional_note": {
                    "file_path": (
                        "uri_core/tools/draft_institutional_note.py"
                    ),
                    "class_name": "InstitutionalNoteDraftCmp",
                    "method": "generate",
                    "approval_requirement": "none",
                }
            },
            skill_memory,
        )
        self.addCleanup(temp_dir.cleanup)

        orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        # learn_skill is called again on a fresh success, even though
        # this was a learned-path execution - re-learning/reinforcing
        # comes for free from reusing the capability_selected branch.
        self.assertEqual(
            skill_memory.learn_skill_calls,
            ["draft_institutional_note"],
        )

    def test_response_plan_reflects_the_learned_selection(self):
        skill_memory = _FakeSkillMemory("draft_institutional_note")
        orchestrator, temp_dir = _orchestrator_with_temp_registry(
            {
                "draft_institutional_note": {
                    "file_path": (
                        "uri_core/tools/draft_institutional_note.py"
                    ),
                    "class_name": "InstitutionalNoteDraftCmp",
                    "method": "generate",
                    "approval_requirement": "none",
                }
            },
            skill_memory,
        )
        self.addCleanup(temp_dir.cleanup)

        result = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        self.assertEqual(result["plan"]["status"], "capability_selected")
        self.assertEqual(
            result["plan"]["tool_name"], "draft_institutional_note"
        )
        self.assertEqual(result["plan"]["source"], "skill_memory")
        # Informational metadata about the match is still present.
        self.assertIsNotNone(result["learned_skill"])


if __name__ == "__main__":
    unittest.main()
