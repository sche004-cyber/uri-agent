import os
import shutil
import unittest

from uri_core.core.facts import Fact
from uri_core.core.state import (
    SessionManager
)


class TestSessionPersistence(
    unittest.TestCase
):

    def setUp(self):

        self.storage_path = (
            "uri_workspace/test_sessions"
        )

        if os.path.exists(
            self.storage_path
        ):

            shutil.rmtree(
                self.storage_path
            )

    def tearDown(self):

        if os.path.exists(
            self.storage_path
        ):

            shutil.rmtree(
                self.storage_path
            )

    def test_session_survives_restart(self):

        manager_one = SessionManager(
            storage_path=self.storage_path
        )

        session = (
            manager_one.get_session(
                "restart-test"
            )
        )

        session.current_facts[
            "subject"
        ] = Fact(
            name="subject",
            value=(
                "Renewal of Group "
                "Medical Insurance"
            ),
            status="CONFIRMED",
            source="User clarification"
        )

        session.active_workflow = {
            "workflow_id": "workflow-001",
            "status":
                "waiting_for_input",
            "steps": [
                {
                    "step_id": "step_1",
                    "status": "completed"
                },
                {
                    "step_id": "step_2",
                    "status":
                        "waiting_for_input"
                }
            ]
        }

        session.active_workflow_status = (
            "waiting_for_input"
        )

        session.active_workflow_required_field = (
            "approval_requested"
        )

        session.active_workflow_question = (
            "What approval is being requested?"
        )

        manager_one.save_session(
            "restart-test"
        )

        # Simulate application restart.
        manager_two = SessionManager(
            storage_path=self.storage_path
        )

        restored_session = (
            manager_two.get_session(
                "restart-test"
            )
        )

        self.assertEqual(
            restored_session.session_id,
            "restart-test"
        )

        self.assertEqual(
            restored_session.current_facts[
                "subject"
            ].value,
            (
                "Renewal of Group "
                "Medical Insurance"
            )
        )

        self.assertEqual(
            restored_session.active_workflow_status,
            "waiting_for_input"
        )

        self.assertEqual(
            restored_session.active_workflow_required_field,
            "approval_requested"
        )

        self.assertEqual(
            restored_session.active_workflow[
                "workflow_id"
            ],
            "workflow-001"
        )

    def test_reset_removes_persisted_session(
        self
    ):

        manager = SessionManager(
            storage_path=self.storage_path
        )

        manager.get_session(
            "reset-test"
        )

        manager.save_session(
            "reset-test"
        )

        session_path = (
            manager._get_session_path(
                "reset-test"
            )
        )

        self.assertTrue(
            os.path.exists(
                session_path
            )
        )

        manager.reset_session(
            "reset-test"
        )

        self.assertFalse(
            os.path.exists(
                session_path
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
