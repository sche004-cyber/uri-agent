import os
import shutil
import unittest

from uri_core.core.orchestrator import (
    UriOrchestrator
)
from uri_core.core.workflow_executor import (
    WorkflowExecutor
)


class TestOrchestratorAutoPersistence(
    unittest.TestCase):

    def setUp(self):

        self.storage_path = (
            "uri_workspace/sessions"
        )

        self.session_id = (
            "auto-persistence-test"
        )

        session_file = os.path.join(
            self.storage_path,
            f"{self.session_id}.json"
        )

        if os.path.exists(session_file):
            os.remove(session_file)

        self.orchestrator = (
            UriOrchestrator()
        )

    def tearDown(self):

        session_file = os.path.join(
            self.storage_path,
            f"{self.session_id}.json"
        )

        if os.path.exists(session_file):
            os.remove(session_file)

    def test_paused_workflow_is_saved_automatically(
        self
    ):

        session = (
            self.orchestrator.session_manager
            .get_session(
                self.session_id
            )
        )

        session.active_workflow = {
            "workflow_id": "auto-save",
            "status":
                "waiting_for_input",
            "steps": [
                {
                    "step_id": "step_1",
                    "capability": "clarify",
                    "status":
                        "waiting_for_input",
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
                    "What approval is required?",
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

        self.orchestrator.process_user_input(
            self.session_id,
            "Insurance renewal"
        )

        # Simulate restart.
        restarted_orchestrator = (
            UriOrchestrator()
        )

        restored_session = (
            restarted_orchestrator
            .session_manager
            .get_session(
                self.session_id
            )
        )

        self.assertEqual(
            restored_session.current_facts[
                "subject"
            ].value,
            "Insurance renewal"
        )

        self.assertEqual(
            restored_session.active_workflow_status,
            "waiting_for_input"
        )

        self.assertEqual(
            restored_session.active_workflow_required_field,
            "approval_requested"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
