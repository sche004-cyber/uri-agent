import os
import shutil
import unittest

from uri_core.core.orchestrator import UriOrchestrator
from uri_core.core.state import SessionManager


class TestOrchestratorWorkflowRecovery(
    unittest.TestCase
):

    TEST_STORAGE = "uri_workspace/test_recovery_integration"

    def setUp(self):

        if os.path.exists(
            self.TEST_STORAGE
        ):
            shutil.rmtree(
                self.TEST_STORAGE
            )

    def tearDown(self):

        if os.path.exists(
            self.TEST_STORAGE
        ):
            shutil.rmtree(
                self.TEST_STORAGE
            )

    def make_orchestrator(
        self
    ):

        orchestrator = UriOrchestrator()

        orchestrator.session_manager = (
            SessionManager(
                storage_path=self.TEST_STORAGE
            )
        )

        return orchestrator

    def make_workflow(
        self,
        status="waiting_for_input",
        step_status="waiting_for_input"
    ):

        return {
            "workflow_id": "wf-recovery-test-001",
            "schema_version": "1.0",
            "task": "noting",
            "goal": "Test recovery",
            "request_text": "Test recovery workflow",
            "semantic_context": {},
            "status": status,
            "created_at":
                "2026-09-03T00:00:00+00:00",
            "updated_at":
                "2026-09-03T00:00:00+00:00",
            "completed_at": None,
            "failed_at": None,
            "execution_history": [],
            "steps": [
                {
                    "step_id": "step_1",
                    "capability":
                        "test_capability",
                    "status": step_status,
                    "depends_on": [],
                    "created_at":
                        "2026-09-03T00:00:00+00:00",
                    "started_at":
                        "2026-09-03T00:00:00+00:00",
                    "completed_at": None,
                    "failed_at": None,
                    "updated_at":
                        "2026-09-03T00:00:00+00:00",
                    "output": None,
                    "result": None,
                    "error": None,
                    "execution_count": 1
                }
            ]
        }

    def test_running_workflow_requires_recovery_review(
        self
    ):

        manager = SessionManager(
            storage_path=self.TEST_STORAGE
        )

        session = manager.get_session(
            "recovery-running"
        )

        session.active_workflow = (
            self.make_workflow(
                status="running",
                step_status="running"
            )
        )

        session.active_workflow_status = (
            "running"
        )

        manager.save_session(
            "recovery-running"
        )

        orchestrator = self.make_orchestrator()

        result = orchestrator.process_user_input(
            "recovery-running",
            "continue"
        )

        self.assertEqual(
            result["execution"]["status"],
            "recovery_review"
        )

        self.assertEqual(
            result["execution"]["recovery"]["action"],
            "recovery_review"
        )

        restored = (
            orchestrator.session_manager.get_session(
                "recovery-running"
            )
        )

        self.assertEqual(
            restored.active_workflow_status,
            "recovery_review"
        )

    def test_invalid_workflow_is_rejected(
        self
    ):

        manager = SessionManager(
            storage_path=self.TEST_STORAGE
        )

        session = manager.get_session(
            "recovery-invalid"
        )

        workflow = self.make_workflow()

        del workflow["workflow_id"]

        session.active_workflow = workflow
        session.active_workflow_status = (
            "waiting_for_input"
        )

        manager.save_session(
            "recovery-invalid"
        )

        orchestrator = self.make_orchestrator()

        result = orchestrator.process_user_input(
            "recovery-invalid",
            "continue"
        )

        self.assertEqual(
            result["execution"]["status"],
            "recovery_rejected"
        )

        self.assertEqual(
            result["execution"]["recovery"]["action"],
            "reject"
        )

    def test_completed_workflow_is_not_reexecuted(
        self
    ):

        manager = SessionManager(
            storage_path=self.TEST_STORAGE
        )

        session = manager.get_session(
            "recovery-completed"
        )

        workflow = self.make_workflow(
            status="completed",
            step_status="completed"
        )

        workflow["steps"][0]["completed_at"] = (
            "2026-09-03T00:01:00+00:00"
        )

        workflow["completed_at"] = (
            "2026-09-03T00:01:00+00:00"
        )

        session.active_workflow = workflow
        session.active_workflow_status = (
            "completed"
        )

        manager.save_session(
            "recovery-completed"
        )

        orchestrator = self.make_orchestrator()

        result = orchestrator.process_user_input(
            "recovery-completed",
            "anything"
        )

        self.assertEqual(
            result["execution"]["status"],
            "already_complete"
        )

        restored = (
            orchestrator.session_manager.get_session(
                "recovery-completed"
            )
        )

        self.assertIsNone(
            restored.active_workflow
        )

    def test_waiting_workflow_enters_existing_resume_path(
        self
    ):

        orchestrator = self.make_orchestrator()

        session = (
            orchestrator.session_manager.get_session(
                "recovery-waiting"
            )
        )

        session.active_workflow = (
            self.make_workflow()
        )

        session.active_workflow_status = (
            "waiting_for_input"
        )

        session.active_workflow_required_field = (
            "subject"
        )

        # Use a fake executor so this test only verifies
        # that recovery reaches the normal resume path.
        class FakeExecutor:

            def execute(
                self,
                workflow
            ):

                workflow["status"] = (
                    "completed"
                )

                workflow["steps"][0][
                    "status"
                ] = "completed"

                workflow["steps"][0][
                    "completed_at"
                ] = "2026-09-03T00:02:00+00:00"

                workflow["completed_at"] = (
                    "2026-09-03T00:02:00+00:00"
                )

                return {
                    "status": "success",
                    "workflow": workflow,
                    "execution_log": []
                }

        orchestrator.workflow_executor = (
            FakeExecutor()
        )

        result = orchestrator.process_user_input(
            "recovery-waiting",
            "Administrative noting"
        )

        self.assertEqual(
            result["execution"]["status"],
            "success"
        )

        self.assertIsNone(
            session.active_workflow
        )


if __name__ == "__main__":
    unittest.main()
