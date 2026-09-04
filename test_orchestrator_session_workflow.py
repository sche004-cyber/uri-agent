import os
import unittest

from uri_core.core.orchestrator import (
    UriOrchestrator
)
from uri_core.core.workflow_executor import (
    WorkflowExecutor
)


class TestOrchestratorSessionWorkflow(
    unittest.TestCase):

    def setUp(self):

        self.session_id = (
            "test-session-workflow"
        )

        session_file = os.path.join(
            "uri_workspace",
            "sessions",
            f"{self.session_id}.json"
        )

        if os.path.exists(session_file):
            os.remove(session_file)

        self.orchestrator = UriOrchestrator()

    def tearDown(self):

        session_file = os.path.join(
            "uri_workspace",
            "sessions",
            f"{self.session_id}.json"
        )

        if os.path.exists(session_file):
            os.remove(session_file)

    def test_session_is_created_for_workflow(
        self
    ):

        session = (
            self.orchestrator.session_manager
            .get_session(
                self.session_id
            )
        )

        self.assertEqual(
            session.session_id,
            self.session_id
        )

    def test_session_facts_are_used_for_clarification(
        self
    ):

        session = (
            self.orchestrator.session_manager
            .get_session(
                self.session_id
            )
        )

        session.current_facts[
            "subject"
        ] = "Insurance renewal"

        workflow = {
            "workflow_id": (
                "session-facts-workflow"
            ),
            "status": "pending",
            "steps": [
                {
                    "step_id": "step_1",
                    "capability": "clarify",
                    "status": "pending",
                    "depends_on": []
                }
            ]
        }

        executor = WorkflowExecutor()

        def clarify_handler(
            step,
            workflow
        ):

            return {
                "status": "success",
                "data": {
                    "subject_available": (
                        "subject"
                        in session.current_facts
                    )
                }
            }

        executor.register_handler(
            "clarify",
            clarify_handler
        )

        self.orchestrator.workflow_executor = (
            executor
        )

        self.orchestrator.workflow_planner.create_workflow = (
            lambda semantic_result, request_text: {
                "workflow": workflow
            }
        )

        self.orchestrator.capability_planner.plan = (
            lambda semantic_result: {
                "status": "planning_required"
            }
        )

        result = (
            self.orchestrator.process_user_input(
                self.session_id,
                "Continue the insurance task"
            )
        )

        self.assertEqual(
            result["execution"]["status"],
            "success"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
