import unittest
from unittest.mock import MagicMock

from uri_core.core.orchestrator import (
    UriOrchestrator
)


class TestOrchestratorWorkflowIntegration(
    unittest.TestCase
):

    def setUp(self):

        self.orchestrator = (
            UriOrchestrator()
        )

        self.orchestrator.semantic_interpreter = (
            MagicMock()
        )

        self.orchestrator.skill_memory = (
            MagicMock()
        )

        self.orchestrator.capability_planner = (
            MagicMock()
        )

    def test_planning_required_executes_workflow(self):

        self.orchestrator.semantic_interpreter.interpret.return_value = {
            "goal":
                "Renew the group medical insurance",
            "task_type":
                "administrative task",
            "domain":
                "insurance administration",
            "requested_output":
                "office note"
        }

        self.orchestrator.skill_memory.find_matching_skill.return_value = (
            None
        )

        self.orchestrator.capability_planner.plan.return_value = {
            "status":
                "planning_required",
            "tool_name": None
        }

        self.orchestrator.workflow_executor = (
            MagicMock()
        )

        self.orchestrator.workflow_executor.execute.return_value = {
            "status": "success",
            "workflow": {
                "workflow_id": "test",
                "status": "completed"
            },
            "execution_log": []
        }

        result = (
            self.orchestrator.process_user_input(
                session_id="test-session",
                user_text=(
                    "Renew the group medical insurance."
                )
            )
        )

        self.assertEqual(
            result["status"],
            "success"
        )

        self.assertEqual(
            result["plan"]["status"],
            "planning_required"
        )

        self.assertIsNotNone(
            result["workflow"]
        )

        self.assertEqual(
            result["execution"]["status"],
            "success"
        )

    def test_direct_capability_path_unchanged(self):

        self.orchestrator.semantic_interpreter.interpret.return_value = {
            "goal":
                "Draft an office note",
            "task_type":
                "document drafting",
            "domain":
                "administrative",
            "requested_output":
                "office note"
        }

        self.orchestrator.skill_memory.find_matching_skill.return_value = (
            None
        )

        self.orchestrator.capability_planner.plan.return_value = {
            "status":
                "capability_selected",
            "tool_name":
                "draft_institutional_note"
        }

        self.orchestrator.dispatcher.execute_tool = (
            MagicMock(
                return_value={
                    "status": "success",
                    "data": {
                        "draft":
                            "Office note generated."
                    }
                }
            )
        )

        self.orchestrator.skill_memory.learn_skill = (
            MagicMock()
        )

        result = (
            self.orchestrator.process_user_input(
                session_id="test-session",
                user_text="Draft an office note."
            )
        )

        self.assertEqual(
            result["status"],
            "success"
        )

        self.assertEqual(
            result["execution"]["tool"],
            "draft_institutional_note"
        )

        self.assertEqual(
            result["response"]["draft"],
            "Office note generated."
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
