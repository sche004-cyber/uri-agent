import os
import unittest

from uri_core.core.orchestrator import UriOrchestrator
from uri_core.core.workflow_executor import WorkflowExecutor


class TestWorkflowRestartRecovery(unittest.TestCase):

    def setUp(self):

        self.session_id = "restart-recovery-test"

        self.session_file = os.path.join(
            "uri_workspace",
            "sessions",
            f"{self.session_id}.json"
        )

        if os.path.exists(self.session_file):
            os.remove(self.session_file)

    def tearDown(self):

        if os.path.exists(self.session_file):
            os.remove(self.session_file)

    def _create_executor(self, session):

        executor = WorkflowExecutor()

        def clarify_handler(step, workflow):

            if (
                "approval_requested"
                in session.current_facts
            ):

                return {
                    "status": "success",
                    "data": {
                        "approval": (
                            session.current_facts[
                                "approval_requested"
                            ].value
                        )
                    }
                }

            return {
                "status": "waiting_for_input",
                "message": (
                    "What approval is being requested?"
                ),
                "required_field": (
                    "approval_requested"
                )
            }

        executor.register_handler(
            "clarify",
            clarify_handler
        )

        return executor

    def test_workflow_survives_restart_and_resumes(
        self
    ):

        # -----------------------------------------
        # FIRST APPLICATION INSTANCE
        # -----------------------------------------

        orchestrator_one = UriOrchestrator()

        session_one = (
            orchestrator_one.session_manager
            .get_session(self.session_id)
        )

        workflow = {
            "workflow_id": "restart-workflow",
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

        orchestrator_one.workflow_executor = (
            self._create_executor(session_one)
        )

        orchestrator_one.workflow_planner.create_workflow = (
            lambda semantic_result, request_text: {
                "workflow": workflow
            }
        )

        orchestrator_one.capability_planner.plan = (
            lambda semantic_result: {
                "status": "planning_required"
            }
        )

        first_result = (
            orchestrator_one.process_user_input(
                self.session_id,
                "Continue insurance renewal"
            )
        )

        self.assertEqual(
            first_result["execution"]["status"],
            "waiting_for_input"
        )

        self.assertTrue(
            os.path.exists(self.session_file)
        )

        # -----------------------------------------
        # APPLICATION RESTART
        # -----------------------------------------

        orchestrator_two = UriOrchestrator()

        restored_session = (
            orchestrator_two.session_manager
            .get_session(self.session_id)
        )

        self.assertIsNotNone(
            restored_session.active_workflow
        )

        self.assertEqual(
            restored_session.active_workflow_status,
            "waiting_for_input"
        )

        self.assertEqual(
            restored_session.active_workflow_required_field,
            "approval_requested"
        )

        # -----------------------------------------
        # RESUME AFTER RESTART
        # -----------------------------------------

        orchestrator_two.workflow_executor = (
            self._create_executor(
                restored_session
            )
        )

        second_result = (
            orchestrator_two.process_user_input(
                self.session_id,
                (
                    "Approval for renewal "
                    "of the insurance policy"
                )
            )
        )

        self.assertEqual(
            second_result["execution"]["status"],
            "success"
        )

        self.assertIsNone(
            restored_session.active_workflow
        )

        # -----------------------------------------
        # VERIFY COMPLETED STATE SURVIVES RESTART
        # -----------------------------------------

        orchestrator_three = UriOrchestrator()

        final_session = (
            orchestrator_three.session_manager
            .get_session(self.session_id)
        )

        self.assertIsNone(
            final_session.active_workflow
        )

        self.assertIn(
            "approval_requested",
            final_session.current_facts
        )

        self.assertEqual(
            final_session.current_facts[
                "approval_requested"
            ].value,
            (
                "Approval for renewal "
                "of the insurance policy"
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
