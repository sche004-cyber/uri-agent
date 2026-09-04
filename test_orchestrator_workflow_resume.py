import os
import shutil
import unittest

from uri_core.core.orchestrator import (
    UriOrchestrator
)
from uri_core.core.workflow_executor import (
    WorkflowExecutor
)


class TestOrchestratorWorkflowResume(
    unittest.TestCase):

    TEST_STORAGE = "uri_workspace/test_workflow_resume"

    def setUp(self):

        if os.path.exists(
            self.TEST_STORAGE
        ):
            shutil.rmtree(
                self.TEST_STORAGE
            )

        self.orchestrator = UriOrchestrator()

        self.orchestrator.session_manager = (
            __import__(
                "uri_core.core.state",
                fromlist=["SessionManager"]
            ).SessionManager(
                storage_path=self.TEST_STORAGE
            )
        )

    def tearDown(self):

        if os.path.exists(
            self.TEST_STORAGE
        ):
            shutil.rmtree(
                self.TEST_STORAGE
            )

    def test_paused_workflow_resumes_after_user_answer(
        self
    ):

        session_id = "resume-session"

        session = (
            self.orchestrator.session_manager
            .get_session(session_id)
        )

        session.active_workflow = {
            "workflow_id": "resume-workflow",
            "status": "waiting_for_input",
            "steps": [
                {
                    "step_id": "step_1",
                    "capability": "first",
                    "status": "completed",
                    "depends_on": []
                },
                {
                    "step_id": "step_2",
                    "capability": "second",
                    "status": "waiting_for_input",
                    "depends_on": [
                        "step_1"
                    ]
                }
            ]
        }

        session.active_workflow_status = (
            "waiting_for_input"
        )

        session.active_workflow_required_field = (
            "subject"
        )

        executor = WorkflowExecutor()

        executor.register_handler(
            "second",
            lambda step, workflow: {
                "status": "success",
                "data": {
                    "draft_completed": True
                }
            }
        )

        self.orchestrator.workflow_executor = (
            executor
        )

        result = (
            self.orchestrator.process_user_input(
                session_id,
                "Renewal of group medical insurance"
            )
        )

        self.assertEqual(
            result["execution"]["status"],
            "success"
        )

        self.assertEqual(
            session.current_facts[
                "subject"
            ].value,
            "Renewal of group medical insurance"
        )

        self.assertIsNone(
            session.active_workflow
        )

    def test_resume_can_pause_for_next_field(
        self
    ):

        session_id = "resume-next-field"

        session = (
            self.orchestrator.session_manager
            .get_session(session_id)
        )

        session.active_workflow = {
            "workflow_id": "next-field",
            "status": "waiting_for_input",
            "steps": [
                {
                    "step_id": "step_1",
                    "capability": "clarify",
                    "status": "waiting_for_input",
                    "depends_on": []
                }
            ]
        }

        session.active_workflow_status = (
            "waiting_for_input"
        )

        session.active_workflow_required_field = (
            "subject"
        )

        executor = WorkflowExecutor()

        def clarify_handler(
            step,
            workflow
        ):

            return {
                "status":
                    "waiting_for_input",
                "message":
                    "What approval is being requested?",
                "required_field":
                    "approval_requested"
            }

        executor.register_handler(
            "clarify",
            clarify_handler
        )

        self.orchestrator.workflow_executor = (
            executor
        )

        result = (
            self.orchestrator.process_user_input(
                session_id,
                "Insurance renewal"
            )
        )

        self.assertEqual(
            result["execution"]["status"],
            "waiting_for_input"
        )

        self.assertEqual(
            session.active_workflow_required_field,
            "approval_requested"
        )

        self.assertEqual(
            session.current_facts[
                "subject"
            ].value,
            "Insurance renewal"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
