import os
import unittest
from unittest.mock import MagicMock

from uri_core.core.orchestrator import (
    UriOrchestrator
)


_SESSION_IDS = [
    "skill-router-shadow-1",
    "skill-router-shadow-2",
    "skill-router-shadow-3",
    "skill-router-shadow-4",
    "skill-router-shadow-5",
]


def _session_file(session_id):
    return os.path.join(
        "uri_workspace", "sessions", f"{session_id}.json"
    )


class TestOrchestratorSkillRouterShadow(
    unittest.TestCase
):
    """
    Skill Router V1 (ContextBudget -> SkillEvaluator) is wired into
    the orchestrator as a shadow evaluation only, mirroring the
    existing model-reasoning-shadow pattern.

    These tests assert it is observational: it must never change
    `plan` or `execution`, must degrade safely, and must record a
    single small AuditTrail event per turn.
    """

    def setUp(self):

        for session_id in _SESSION_IDS:
            path = _session_file(session_id)
            if os.path.exists(path):
                os.remove(path)

        self.orchestrator = UriOrchestrator()

        self.orchestrator.semantic_interpreter = MagicMock()

        self.orchestrator.semantic_interpreter.interpret.return_value = {
            "goal": "Draft an office note",
            "task_type": "document drafting",
            "domain": "administrative",
            "requested_output": "office note"
        }

        self.orchestrator.skill_memory = MagicMock()
        self.orchestrator.skill_memory.find_matching_skill.return_value = None

        self.orchestrator.capability_planner.plan = (
            lambda semantic_result: {
                "status": "capability_selected",
                "tool_name": "draft_institutional_note"
            }
        )

        self.orchestrator.dispatcher.execute_tool = MagicMock(
            return_value={
                "status": "success",
                "data": {"draft": "Office note generated."}
            }
        )

    def tearDown(self):

        for session_id in _SESSION_IDS:
            path = _session_file(session_id)
            if os.path.exists(path):
                os.remove(path)

    def test_shadow_result_is_attached_without_changing_plan_or_execution(self):

        result = self.orchestrator.process_user_input(
            session_id="skill-router-shadow-1",
            user_text="Draft an office note."
        )

        self.assertEqual(result["status"], "success")

        self.assertIn("skill_router_shadow", result)
        self.assertEqual(
            result["skill_router_shadow"]["status"],
            "shadow_completed"
        )

        # The live execution path is unchanged: still driven by
        # CapabilityPlanner/ToolDispatcher, not by the shadow.
        self.assertEqual(
            result["execution"]["tool"],
            "draft_institutional_note"
        )
        self.assertEqual(
            result["response"]["draft"],
            "Office note generated."
        )

    def test_shadow_agrees_with_planner_and_records_one_audit_event(self):

        self.orchestrator.process_user_input(
            session_id="skill-router-shadow-2",
            user_text="Draft an office note."
        )

        events = self.orchestrator.audit_trail.for_session(
            "skill-router-shadow-2"
        )

        self.assertEqual(len(events), 1)

        event = events[0]

        self.assertEqual(event.event_type, "skill_router_shadow_evaluation")
        self.assertEqual(event.capability, "draft_institutional_note")
        self.assertEqual(
            event.metadata["planner_tool_name"],
            "draft_institutional_note"
        )
        self.assertTrue(event.metadata["agrees_with_planner"])

    def test_disabled_flag_short_circuits_the_shadow(self):

        self.orchestrator.enable_skill_router_shadow = False

        result = self.orchestrator.process_user_input(
            session_id="skill-router-shadow-3",
            user_text="Draft an office note."
        )

        self.assertEqual(
            result["skill_router_shadow"]["status"],
            "shadow_disabled"
        )

        # Execution is still unaffected.
        self.assertEqual(
            result["execution"]["tool"],
            "draft_institutional_note"
        )

    def test_missing_registry_degrades_to_no_suitable_capability(self):

        self.orchestrator._skill_registry_items = []

        from uri_core.core.skill_evaluator import SkillEvaluator
        from uri_core.core.context_budget import ContextBudget

        self.orchestrator.skill_evaluator = SkillEvaluator(
            registry_items=[]
        )
        self.orchestrator.context_budget = ContextBudget(
            registry_items=[]
        )

        result = self.orchestrator.process_user_input(
            session_id="skill-router-shadow-4",
            user_text="Draft an office note."
        )

        shadow = result["skill_router_shadow"]

        self.assertEqual(shadow["status"], "shadow_completed")
        self.assertIsNone(shadow["result"]["best_match"])
        self.assertTrue(shadow["result"]["capability_gap"])

        # Still fully observational - execution is unaffected.
        self.assertEqual(
            result["execution"]["tool"],
            "draft_institutional_note"
        )

    def test_audit_failure_never_breaks_the_live_request(self):

        self.orchestrator.audit_trail.record = MagicMock(
            side_effect=RuntimeError("audit backend unavailable")
        )

        result = self.orchestrator.process_user_input(
            session_id="skill-router-shadow-5",
            user_text="Draft an office note."
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(
            result["execution"]["tool"],
            "draft_institutional_note"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
